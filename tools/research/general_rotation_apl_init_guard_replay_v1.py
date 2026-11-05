#!/usr/bin/env python3
"""Strict replay of actual original C++ action initialization guard returns.

One source-guaranteed failed verify_actor_*() means action_t::init() sets
background=true for that call. Guard-level evidence remains distinct from
subsequent foreground membership, action_ready and full priority proof.
Same source APL row can have multiple native instances; aggregate only,
never infer one-to-one without a physical action pointer/instance ID.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from general_rotation_apl_init_guard_probe_v1 import (
    MARK, SCHEMA as SOURCE_SCHEMA, GUARDS
)
from general_rotation_original_pre_capture_engine_v1 import canonical
from simc_apl_semantic_ir_v2 import parse_profile, git_blob

SCHEMA="ZrotGenericOriginalActionInitGuardReturnStrictReplayV1"


class InitGuardReplayError(ValueError):
    pass


def replay(log:str,profile:bytes,producer:dict)->dict:
    if (not isinstance(producer,dict)
        or producer.get("schema")!=SOURCE_SCHEMA
        or producer.get("source_guard_marker")!=MARK
        or producer.get("original_guard_calls")!=[
            "verify_actor_level","verify_actor_spec","verify_actor_weapon"]
        or producer.get("source_guard_call_count_delta")!=0
        or producer.get("positive_action_READY_proven")!=0):
        raise InitGuardReplayError("SOURCE_PINNED_INIT_GUARD_PRODUCER_REQUIRED")
    actions=parse_profile(profile,require_source=False)["action_lists"]
    completed=[]
    pending=None
    raw_guards=0
    def finish():
        nonlocal pending
        if pending is None:
            return
        evals=pending["evaluated"]
        if not evals or evals[0][0]!="level":
            raise InitGuardReplayError("SOURCE_INIT_GUARD_LEVEL_NOT_FIRST")
        for idx,(name,result) in enumerate(evals):
            if name!=GUARDS[idx]:
                raise InitGuardReplayError("SOURCE_INIT_GUARD_CALL_ORDER_CHANGED")
            if not result and idx!=len(evals)-1:
                raise InitGuardReplayError("ORIGINAL_FALSE_GUARD_DID_NOT_SHORT_CIRCUIT")
        if evals[-1][1] and len(evals)!=len(GUARDS):
            raise InitGuardReplayError("ORIGINAL_TRUE_GUARD_CHAIN_INCOMPLETE")
        negative=[name for name,result in evals if not result]
        completed.append({
            "source_action":pending["action"],
            "source_row_sha256":pending["row_hash"],
            "source_list":pending["owner"],
            "ordinal_one_based":pending["ordinal"],
            "native_name_identity_only":pending["native"],
            "evaluated_guards":[x[0] for x in evals],
            "failed_eligibility_guard":negative[0] if negative else None,
            "original_cpp_forces_background":bool(negative),
            "full_ACTION_READY_certified":False,
        })
        pending=None
    for line in log.splitlines():
        if MARK not in line:
            continue
        if line.count(MARK)!=1:
            raise InitGuardReplayError("AMBIGUOUS_SOURCE_INIT_GUARD_EVENT")
        p=line.split(MARK,1)[1].strip().split("|")
        if len(p)!=5:
            raise InitGuardReplayError("WRONG_SOURCE_GUARD_RECORD_FORMAT")
        owner,ord_s,native,guard,result=p
        if (not ord_s.isdigit() or not owner or not native
            or guard not in GUARDS or result not in ("0","1")):
            raise InitGuardReplayError("MALFORMED_SOURCE_INIT_GUARD_VALUE")
        ordinal=int(ord_s)
        rows=actions.get(owner)
        if rows is None or ordinal<1 or ordinal>len(rows):
            raise InitGuardReplayError("UNMAPPED_ORIGINAL_APL_INIT_GUARD_SOURCE")
        row=rows[ordinal-1]
        if guard=="level":
            finish()
            pending={
                "owner":owner,"ordinal":ordinal,"native":native,
                "row_hash":row["source_sha256"],
                "action":row["action"],"evaluated":[]
            }
        if (pending is None or
            (pending["owner"],pending["ordinal"],pending["native"])!=
            (owner,ordinal,native)):
            raise InitGuardReplayError("INIT_GUARD_NOT_IN_EXACT_ACTION_SOURCE_CONTEXT")
        pending["evaluated"].append((guard,result=="1"))
        if len(pending["evaluated"])>len(GUARDS):
            raise InitGuardReplayError("TOO_MANY_SOURCE_GUARD_EVALUATIONS")
        raw_guards+=1
    finish()
    if not completed or raw_guards==0:
        raise InitGuardReplayError("NO_OBSERVED_ORIGINAL_INIT_GUARD_CALLS")
    grouped={}
    by_failed_rows={}
    for row in completed:
        if row["failed_eligibility_guard"]:
            key=(row["source_action"],row["failed_eligibility_guard"])
            by_failed_rows.setdefault(key,set()).add(row["source_row_sha256"])
        a=row["source_action"]
        if a not in grouped:
            grouped[a]={
                "source_mapped_guard_invocations":0,
                "guard_true_calls_total":0,
                "guard_false_level":0,"guard_false_spec":0,
                "guard_false_weapon":0,
                "source_forced_background_instances":0,
                "all_observed_guards_passed_instances":0,
                "distinct_source_row_hashes":set()
            }
        x=grouped[a]
        x["source_mapped_guard_invocations"]+=1
        x["guard_true_calls_total"]+=len(row["evaluated_guards"]) - int(
            row["original_cpp_forces_background"])
        if row["failed_eligibility_guard"]:
            x["guard_false_"+row["failed_eligibility_guard"]]+=1
            x["source_forced_background_instances"]+=1
        else:
            x["all_observed_guards_passed_instances"]+=1
        x["distinct_source_row_hashes"].add(row["source_row_sha256"])
    return {
        "schema":SCHEMA,
        "original_source_profile_git_blob_sha1":git_blob(profile),
        "source_mapped_init_guard_invocations_total":len(completed),
        "original_guard_return_events":raw_guards,
        "original_cpp_short_circuit_order_verified_in_replay":True,
        "source_action_init_guard_evidence":{
            name:{
                **{k:v for k,v in x.items() if k!="distinct_source_row_hashes"},
                "distinct_source_rows":len(x["distinct_source_row_hashes"]),
            } for name,x in sorted(grouped.items())
        },
        "source_guard_failed_source_row_hashes":{
            f"{action}.{guard_name}":sorted(sha_set)
            for (action,guard_name),sha_set in sorted(by_failed_rows.items())
        },
        "bounded_failed_source_action_examples":[{
            "source_row_sha256":x["source_row_sha256"],
            "source_action":x["source_action"],
            "guard":x["failed_eligibility_guard"],
            "source_forced_background_at_init":True,
        } for x in completed if x["original_cpp_forces_background"]][:3],
        "source_guard_failed_forces_init_background":True,
        "source_guard_all_pass_does_not_prove_background_false":True,
        "individual_native_action_instance_identity_unproven":True,
        "positive_FULL_ACTION_READY_proven":0,
        "source_priority_complete":False,
        "WCL_API_calls":0,
        "raw_native_logs_exported":False
    }


def selftest()->dict:
    original=b'warrior="Synthetic"\nspec=fury\nactions=/rampage\n'
    receipt={
        "schema":SOURCE_SCHEMA,"source_guard_marker":MARK,
        "original_guard_calls":["verify_actor_level","verify_actor_spec",
                                "verify_actor_weapon"],
        "source_guard_call_count_delta":0,
        "positive_action_READY_proven":0
    }
    def event(guard,value,ordinal=1):
        return MARK+f"default|{ordinal}|rampage|{guard}|{value}"
    rows=[
        event("level",1),event("spec",1),event("weapon",0),
        event("level",1),event("spec",1),event("weapon",1)
    ]
    out=replay("\n".join(rows),original,receipt)
    assert out["source_action_init_guard_evidence"]["rampage"][
        "guard_false_weapon"]==1
    assert out["source_action_init_guard_evidence"]["rampage"][
        "source_forced_background_instances"]==1
    assert out["source_action_init_guard_evidence"]["rampage"][
        "all_observed_guards_passed_instances"]==1
    assert out["positive_FULL_ACTION_READY_proven"]==0
    for invalid in (
        rows[1:],
        [rows[0],rows[2],rows[1]],
        rows[:3]+[rows[2]],
        [event("level",0),event("weapon",1)],
        [event("level",1),event("spec",0),event("weapon",1)],
        [event("level",1,ordinal=2)],
        rows[:2],
    ):
        try:replay("\n".join(invalid),original,receipt)
        except InitGuardReplayError:pass
        else:raise AssertionError("MALFORMED_INIT_GUARD_SOURCE_REPLAY_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":11,
        "actual_original_native_guard_calls_observed":False,
        "positive_READY_certified":0,
        "WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--profile",type=Path)
    p.add_argument("--producer-receipt",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    req=(a.native_log,a.profile,a.producer_receipt)
    if all(x is None for x in req):
        result=selftest()
    elif all(x is not None for x in req):
        result=replay(
            a.native_log.read_text(encoding="utf8"),
            a.profile.read_bytes(),
            json.loads(a.producer_receipt.read_bytes()))
    else:p.error("native log, profile, producer receipt required together")
    data=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(data)
    else:print(data.decode(),end="")


if __name__=="__main__":
    main()
