#!/usr/bin/env python3
"""Fail-closed generic raw selection-PRE marker replayer.

This is separate from the producer. It validates actual source-pinned
action/list/ordinal and a set of typed raw operand observations, without
promoting method-entry PRE, independent gate truth, READY, or priority.
No user/character/log text is written to the compact receipt.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import parse_profile, git_blob
from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_select_pre_passive_producer_v1 import (
    SCHEMA as PRODUCER_SCHEMA, MARK, PHASE, READS
)

SCHEMA="ZrotGeneralRotationGenericSelectPREReplayV1"


class PassiveReplayError(ValueError):
    pass


def parse_marker_lines(text:str,receipt:dict,profile:bytes)->dict:
    if (receipt.get("schema")!=PRODUCER_SCHEMA or
        receipt.get("source_phase")!=PHASE or
        receipt.get("field_count")!=len(READS) or
        receipt.get("original_action_ready_call_count")!=1 or
        receipt.get("new_action_ready_calls")!=0):
        raise PassiveReplayError("UNPINNED_SOURCE_PRODUCER_RECEIPT")
    fields=receipt["fields"]
    by_id={x["field_id"]:x for x in fields}
    if len(by_id)!=len(READS) or {x["operand_name"] for x in fields}!=set(READS):
        raise PassiveReplayError("CAPTURE_FIELD_ID_OR_COVERAGE_DRIFT")
    original=parse_profile(profile,require_source=False)
    lists=original["action_lists"]
    source_identity=git_blob(profile)
    marked=[]
    for line in text.splitlines():
        if MARK not in line:
            continue
        if line.count(MARK)!=1:
            raise PassiveReplayError("AMBIGUOUS_RAW_SELECT_PRE_LOG_MARKER")
        marker=line.split(MARK,1)[1].strip()
        parts=marker.split("|")
        if len(parts)!=7:
            raise PassiveReplayError("INVALID_ORIGINAL_SELECT_PRE_FIELD_COUNT")
        at,owner,ordinal,native_name,field_id,kind,raw=parts
        if not at.isdigit() or not ordinal.isdigit() or not owner or not native_name:
            raise PassiveReplayError("INVALID_PRE_SELECTION_SCOPE")
        time=int(at); position=int(ordinal)
        if time<0 or position<1:
            raise PassiveReplayError("INVALID_SELECT_PRE_ORDINAL_OR_TIME")
        field=by_id.get(field_id)
        if not field or field["kind"]!=kind:
            raise PassiveReplayError("UNDECLARED_OR_TYPED_RAW_SELECT_PRE_FIELD")
        if kind=="bool":
            if raw not in ("0","1"):
                raise PassiveReplayError("INVALID_RAW_BOOLEAN")
            value=(raw=="1")
        elif kind=="int":
            if not re.fullmatch(r"-?[0-9]+",raw):
                raise PassiveReplayError("INVALID_RAW_INTEGER")
            value=int(raw)
        else:
            raise PassiveReplayError("UNSUPPORTED_GENERIC_SOURCE_READ_KIND")
        rows=lists.get(owner)
        if rows is None or position>len(rows):
            raise PassiveReplayError("ORIGINAL_APL_OWNER_OR_ORDINAL_UNMAPPED")
        source_row=rows[position-1]
        marked.append({
            "at_simc_ms":time, "list":owner,"ordinal_one_based":position,
            "native_action_identity_only":native_name,
            "source_action":source_row["action"],
            "source_row_sha256":source_row["source_sha256"],
            "field_id":field_id,"operand_name":field["operand_name"],
            "value":value,"phase":PHASE,
        })
    if not marked or len(marked)%len(fields):
        raise PassiveReplayError("INCOMPLETE_ORIGINAL_SELECT_PRE_CAPTURE_GROUPS")
    groups=[]
    occurrence=Counter()
    for start in range(0,len(marked),len(fields)):
        batch=marked[start:start+len(fields)]
        first=batch[0]
        key=(first["at_simc_ms"],first["list"],first["ordinal_one_based"],
             first["native_action_identity_only"],first["source_row_sha256"])
        if any(
            (x["at_simc_ms"],x["list"],x["ordinal_one_based"],
             x["native_action_identity_only"],x["source_row_sha256"])!=key
            for x in batch
        ):
            raise PassiveReplayError("ORIGINAL_PRE_BATCH_SOURCE_POINTER_CHANGED")
        ids=[x["field_id"] for x in batch]
        if len(ids)!=len(set(ids)) or set(ids)!=set(by_id):
            raise PassiveReplayError("MISSING_OR_DUPLICATE_PRE_OPERAND")
        idx=occurrence[key]
        occurrence[key]+=1
        groups.append({
            "at_simc_ms":first["at_simc_ms"],"source_list":first["list"],
            "source_ordinal_one_based":first["ordinal_one_based"],
            "source_row_sha256":first["source_row_sha256"],
            "same_time_source_occurrence":idx,
            "source_action":first["source_action"],
            "native_action_name_only":first["native_action_identity_only"],
            "raw_fields":{x["operand_name"]:x["value"] for x in batch},
        })
    matches=sum(x["source_action"]==x["native_action_name_only"] for x in groups)
    return {
        "schema":SCHEMA,"source_profile_git_blob_sha1":source_identity,
        "original_select_PRE_marker_count":len(marked),
        "original_select_PRE_attempt_count":len(groups),
        "exact_row_identity_matches_native_name":matches,
        "unmatched_name_alias_ambiguity":len(groups)-matches,
        "source_method_entry_PRE_proven":False,
        "source_selected_action_ready_independently_proven":False,
        "raw_capture_records_verified_as_new_selection_PRE":len(marked),
        "raw_gate_truth_proven":False,
        "recorded_input_operand_count":len(fields),
        "producer_source_provenance_receipt_required":True,
        "positive_READY_certified":0,
        "WCL_API_calls":0,
        "bounded_raw_attempt_examples":groups[:3],
        "all_attempts_retained_only_in_memory":True,
    }


def selftest():
    sample=(
        b'warrior="Synthetic"\nspec=fury\n'
        b'actions=/rampage\n'
    )
    ir=parse_profile(sample,require_source=False)
    row=ir["action_lists"]["default"][0]
    fields=[
        {"field_id":sha256(x.encode()).hexdigest(),
         "operand_name":x,"kind":READS[x][0]}
        for x in sorted(READS)
    ]
    receipt={
        "schema":PRODUCER_SCHEMA,"source_phase":PHASE,
        "field_count":len(fields),"fields":fields,
        "original_action_ready_call_count":1,
        "new_action_ready_calls":0
    }
    def marker(field,at=20,ordinal=1):
        value="2000" if field["kind"]=="int" else "1"
        return (MARK+f"{at}|default|{ordinal}|rampage|"+
                field["field_id"]+"|"+field["kind"]+"|"+value)
    trace="\n".join(marker(f) for f in fields)+"\n"
    out=parse_marker_lines(trace,receipt,sample)
    assert out["original_select_PRE_attempt_count"]==1
    assert out["original_select_PRE_marker_count"]==3
    assert out["bounded_raw_attempt_examples"][0]["source_row_sha256"]==row["source_sha256"]
    assert out["bounded_raw_attempt_examples"][0]["raw_fields"]["usable_while_casting"] is True
    assert out["source_method_entry_PRE_proven"] is False
    for bad in (
        trace.replace("|default|","|unknown|",1),
        trace.replace("|default|1|","|default|9|",1),
        trace.replace("|bool|1","|bool|2",1),
        trace.replace("|int|2000","|int|garbage",1),
        trace+"\n"+marker(fields[0]),
        trace.replace(fields[0]["field_id"],"0"*64,1),
    ):
        try:parse_marker_lines(bad,receipt,sample)
        except PassiveReplayError:pass
        else:raise AssertionError("MALFORMED_SOURCE_PRE_RECORD_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":11,"actual_Native_trace_replayed":False,
        "source_PRE_not_source_method_PRE":True,
        "positive_READY_certified":0,"WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--producer-receipt",type=Path)
    p.add_argument("--profile",type=Path)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    trio=(a.producer_receipt,a.profile,a.native_log)
    if all(x is None for x in trio):
        r=selftest()
    elif all(x is not None for x in trio):
        r=parse_marker_lines(a.native_log.read_text(encoding="utf-8"),
                             json.loads(a.producer_receipt.read_bytes()),
                             a.profile.read_bytes())
    else:p.error("producer-receipt, profile and native-log required together")
    raw=canonical(r)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as h:h.write(raw)
    else:print(raw.decode(),end="")


if __name__=="__main__":
    main()
