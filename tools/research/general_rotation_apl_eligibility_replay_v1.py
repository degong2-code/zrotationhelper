#!/usr/bin/env python3
"""Strict Original SimC action init/foreground candidate inventory replayer.

Source list/ordinal identity comes only from the supplied pinned APL profile,
not from name-matching or inferred source line. 'Not in foreground at init'
does not mean action NOT_READY, and an absent row does not prove a causal
reason for omission. Controlled hypothesis failure remains distinct.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from general_rotation_apl_eligibility_instrument_v1 import (
    SCHEMA as PRODUCER_SCHEMA, MARK, STAGES
)
from general_rotation_original_pre_capture_engine_v1 import canonical
from simc_apl_semantic_ir_v2 import parse_profile, git_blob

SCHEMA="ZrotGenericOriginalAPLInitializationEligibilityStrictReplayV1"


class EligibilityReplayError(ValueError):
    pass


def replay(native_log:str,profile:bytes,producer_receipt:dict)->dict:
    if (not isinstance(producer_receipt,dict) or
        producer_receipt.get("schema")!=PRODUCER_SCHEMA or
        producer_receipt.get("stage_inventory_marker")!=MARK or
        producer_receipt.get("source_stage_count")!=len(STAGES) or
        producer_receipt.get("source_action_ready_call_count_delta")!=0 or
        producer_receipt.get("positive_FULL_action_READY_proven")!=0):
        raise EligibilityReplayError("PINNED_ORIGINAL_INIT_PRODUCER_RECEIPT_REQUIRED")
    expected=[s for s,_ in STAGES]
    apl=parse_profile(profile,require_source=False)["action_lists"]
    observed={}
    stage_end={}
    real_rows=0
    stage_last=-1
    for line in native_log.splitlines():
        if MARK not in line:
            continue
        if line.count(MARK)!=1:
            raise EligibilityReplayError("AMBIGUOUS_OR_DUPLICATE_INIT_SOURCE_MARKER")
        fields=line.split(MARK,1)[1].strip().split("|")
        if len(fields)<2 or fields[0] not in ("ROW","END"):
            raise EligibilityReplayError("INVALID_INIT_INVENTORY_EVENT_KIND")
        kind,stage=fields[:2]
        if stage not in expected:
            raise EligibilityReplayError("UNDECLARED_CXX_INITIALIZATION_STAGE")
        stage_idx=expected.index(stage)
        if stage_idx<stage_last or (stage_idx>stage_last+1):
            raise EligibilityReplayError("NONMONOTONIC_INIT_STAGE_ORDER")
        stage_last=stage_idx
        if kind=="ROW":
            if len(fields)!=10 or stage in stage_end:
                raise EligibilityReplayError("INVALID_INIT_SOURCE_ROW_FORMAT")
            _,_,owner,ordinal_s,native,*bits=fields
            if not ordinal_s.isdigit() or not owner or not native:
                raise EligibilityReplayError("INVALID_ORIGINAL_APL_ROW_IDENTITY")
            if len(bits)!=5 or any(bit not in ("0","1") for bit in bits):
                raise EligibilityReplayError("NONBOOL_INIT_SOURCE_OPERAND")
            ordinal=int(ordinal_s)
            rows=apl.get(owner)
            if rows is None or ordinal<1 or ordinal>len(rows):
                raise EligibilityReplayError("UNRECOGNIZED_INIT_APL_SOURCE_ROW")
            row=rows[ordinal-1]
            action=row["action"]
            record={
                "source_action":action,
                "source_row_sha256":row["source_sha256"],
                "source_list":owner,
                "ordinal_one_based":ordinal,
                "native_name_identity_only":native,
                "background":bits[0]=="1",
                "foreground_member":bits[1]=="1",
                "active_list_member":bits[2]=="1",
                "actor_mainhand_weapon_none":bits[3]=="1",
                "actor_offhand_weapon_none":bits[4]=="1"
            }
            observed.setdefault(stage,[]).append(record)
            real_rows+=1
        else:
            if len(fields)!=5 or stage in stage_end:
                raise EligibilityReplayError("DUPLICATE_OR_BAD_INIT_STAGE_COMPLETION")
            _,_,reg_s,mapped_s,unmapped_s=fields
            if any(not v.isdigit() for v in (reg_s,mapped_s,unmapped_s)):
                raise EligibilityReplayError("NONINTEGER_SOURCE_INIT_STAGE_COUNTS")
            registered,mapped,unmapped=map(int,(reg_s,mapped_s,unmapped_s))
            if (registered!=mapped+unmapped or
                mapped!=len(observed.get(stage,[]))):
                raise EligibilityReplayError("INCONSISTENT_ORIGINAL_ACTION_REGISTRY_COUNTS")
            stage_end[stage]={
                "registered_action_instances":registered,
                "source_mapped_instances":mapped,
                "unmapped_action_instances":unmapped
            }
    if (set(stage_end)!=set(expected) or
        stage_last!=len(expected)-1 or real_rows==0):
        raise EligibilityReplayError("ORIGINAL_APL_SOURCE_INIT_STAGE_MISSING")
    # A source APL row may be mapped to multiple native action objects.
    # Group by source *action name*, with exact row/provenance checked above.
    by_stage={}
    by_source_row_at_stage={}
    for stage in expected:
        counts={}
        for row in observed.get(stage,[]):
            a=row["source_action"]
            if a not in counts:
                counts[a]={
                    "registered_mapped_instances":0,
                    "background_true":0,
                    "foreground_true":0,
                    "active_list_true":0,
                    "mainhand_weapon_none_true":0,
                    "offhand_weapon_none_true":0,
                    "distinct_source_rows":set(),
                }
            x=counts[a]
            x["registered_mapped_instances"]+=1
            x["background_true"]+=int(row["background"])
            x["foreground_true"]+=int(row["foreground_member"])
            x["active_list_true"]+=int(row["active_list_member"])
            x["mainhand_weapon_none_true"]+=int(row["actor_mainhand_weapon_none"])
            x["offhand_weapon_none_true"]+=int(row["actor_offhand_weapon_none"])
            x["distinct_source_rows"].add(row["source_row_sha256"])
        by_stage[stage]={
            name:dict((k,len(v) if k=="distinct_source_rows" else v)
                      for k,v in x.items())
            for name,x in sorted(counts.items())
        }
        by_hash={}
        for item in observed.get(stage,[]):
            h=item["source_row_sha256"]
            row=by_hash.setdefault(h,{
                "source_action":item["source_action"],
                "registered_mapped_instances":0,
                "background_true":0,"foreground_true":0,
                "active_list_true":0,"mainhand_weapon_none_true":0,
                "offhand_weapon_none_true":0})
            if row["source_action"]!=item["source_action"]:
                raise EligibilityReplayError("CROSS_ACTION_ROW_HASH_COLLISION")
            row["registered_mapped_instances"]+=1
            for name,key in (
                ("background_true","background"),
                ("foreground_true","foreground_member"),
                ("active_list_true","active_list_member"),
                ("mainhand_weapon_none_true","actor_mainhand_weapon_none"),
                ("offhand_weapon_none_true","actor_offhand_weapon_none")):
                row[name]+=int(item[key])
        by_source_row_at_stage[stage]=dict(sorted(by_hash.items()))
    source_actions=Counter(row["action"] for rows in apl.values() for row in rows)
    missing_by_stage={}
    for stage in expected:
        missing_by_stage[stage]={
            name:source_actions[name]
            for name in sorted(source_actions)
            if name not in by_stage[stage]
        }
    background_not_foreground={}
    weapon_missing_background_not_foreground={}
    for stage in expected:
        source_ids={}
        source_weapon_ids={}
        for row in observed.get(stage,[]):
            if row["background"] and not row["foreground_member"]:
                name=row["source_action"]
                source_ids.setdefault(name,set()).add(row["source_row_sha256"])
                if (row["actor_mainhand_weapon_none"] or
                    row["actor_offhand_weapon_none"]):
                    source_weapon_ids.setdefault(name,set()).add(row["source_row_sha256"])
        background_not_foreground[stage]={
            name:sorted(rows) for name,rows in sorted(source_ids.items())
        }
        weapon_missing_background_not_foreground[stage]={
            name:sorted(rows) for name,rows in sorted(source_weapon_ids.items())
        }
    no_source_cause="UNKNOWN_NO_CAUSAL_INIT_EXCLUSION_VERDICT"
    return {
        "schema":SCHEMA,
        "source_profile_git_blob_sha1":git_blob(profile),
        "source_initialization_stages":expected,
        "stage_registry_receipts":stage_end,
        "source_mapped_row_instances_total":real_rows,
        "source_action_stage_observations":by_stage,
        "source_row_stage_observations_by_sha256":by_source_row_at_stage,
        "source_stage_background_nonforeground_row_hashes_by_action":
            background_not_foreground,
        "source_stage_weapon_missing_background_nonforeground_row_hashes_by_action":
            weapon_missing_background_not_foreground,
        "source_apl_action_rows_not_seen_in_mapped_init_by_action":
            missing_by_stage,
        "unmapped_registry_instances_not_source_attributable":sum(
            x["unmapped_action_instances"] for x in stage_end.values()),
        "in_foreground_at_stage_is_not_ready_proof":True,
        "not_in_foreground_at_stage_is_not_NOT_READY_proof":True,
        "missing_mapped_row_causal_classification":no_source_cause,
        "positive_action_READY_certified":0,
        "full_source_virtual_dispatch_exhaustive":False,
        "target_dummy_error_verdict_permitted":False,
        "WCL_API_calls":0,
        "raw_native_actor_log_exported":False
    }


def selftest()->dict:
    from hashlib import sha256
    raw=b'warrior="Synthetic"\nspec=fury\nactions=/rampage\n'
    producer={
        "schema":PRODUCER_SCHEMA,
        "stage_inventory_marker":MARK,
        "source_stage_count":2,
        "source_action_ready_call_count_delta":0,
        "positive_FULL_action_READY_proven":0
    }
    def row(stage,bg,fg,mh,oh):
        return MARK+f"ROW|{stage}|default|1|rampage|{bg}|{fg}|1|{mh}|{oh}"
    def end(stage):
        return MARK+f"END|{stage}|1|1|0"
    lines=[
        row("INIT_ACTIONS_END",1,0,0,1),
        end("INIT_ACTIONS_END"),
        row("INIT_FINISHED_END",1,0,0,1),
        end("INIT_FINISHED_END")
    ]
    out=replay("\n".join(lines),raw,producer)
    assert out["source_action_stage_observations"][
        "INIT_ACTIONS_END"]["rampage"]["background_true"]==1
    assert out["source_action_stage_observations"][
        "INIT_FINISHED_END"]["rampage"]["foreground_true"]==0
    assert out["source_action_stage_observations"][
        "INIT_FINISHED_END"]["rampage"]["offhand_weapon_none_true"]==1
    assert out["positive_action_READY_certified"]==0
    assert out["missing_mapped_row_causal_classification"]=="UNKNOWN_NO_CAUSAL_INIT_EXCLUSION_VERDICT"
    forged=[
        lines+[lines[-1]],
        lines[1:],
        [x.replace("|1|1|0","|2|1|0") for x in lines],
        [x.replace("|default|1|rampage","|default|9|rampage")
         for x in lines],
        [x.replace("|rampage|1|0|1|0|1","|rampage|1|2|1|0|1") for x in lines],
        lines[:2],
        [lines[2],lines[3],lines[0],lines[1]],
    ]
    for records in forged:
        try:replay("\n".join(records),raw,producer)
        except EligibilityReplayError:pass
        else:raise AssertionError("INVALID_ORIGINAL_INIT_INVENTORY_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":12,
        "actual_original_CXX_init_instrumentation_executed":False,
        "positive_READY_certified":0,"WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--profile",type=Path)
    p.add_argument("--producer-receipt",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    required=(a.native_log,a.profile,a.producer_receipt)
    if all(x is None for x in required):
        result=selftest()
    elif all(x is not None for x in required):
        result=replay(a.native_log.read_text(encoding="utf8"),
                      a.profile.read_bytes(),
                      json.loads(a.producer_receipt.read_bytes()))
    else:p.error("native log, profile and producer receipt must be paired")
    raw=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
    else:print(raw.decode(),end="")


if __name__=="__main__":
    main()
