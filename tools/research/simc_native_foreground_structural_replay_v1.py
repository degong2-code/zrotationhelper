#!/usr/bin/env python3
"""Independent Python structure replay of real native SimC select_action traces.

Inputs: pinned original Fury profile/effective APL, native C++ reporter markers,
and independently validated pointer-source result receipt.  The Python
replayer decides the first selected action from a source AST *row sequence*
and observed native action_ready booleans, compares its choice against native
RETURN markers and pointer-identified selected rows.

This is intentionally CONDITIONAL ON NATIVE READY() RESULTS. It proves
structural scan/CALL/RUN consistency, NOT ability readiness, expression
semantics, or full interpreter/native outcome parity. WCL is not used.

No arguments -> offline synthetic regression. No network, no credentials.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import parse_profile
from simc_native_select_trace_audit_v1 import audit_dir
from simc_native_select_trace_instrument_v1 import MARK

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
UPSTREAM_PROFILE_BLOB="3225992ed5b754ad5d61e8b785d9d859f1eed1be"
AUDIT_SCHEMA="ZrotNativeSimcSelectedRowTwoTargetAuditV1"
SCHEMA="ZrotNativeSimcConditionalScanStructureReplayV1"
MODES={"FOREGROUND","OFF_GCD","CAST_WHILE_CASTING"}
class StructuralError(ValueError): pass


def sha(value:bytes): return hashlib.sha256(value).hexdigest()


def unpack_marker(line):
    index=line.find(MARK)
    if index<0:return None
    pieces=line[index:].strip().split("|")
    typ=pieces[1] if len(pieces)>1 else ""
    lengths={"ENTER":5,"ATTEMPT":8,"RETURN":6,"NO_ACTION":4}
    if typ not in lengths or len(pieces)!=lengths[typ]:
        raise StructuralError("NATIVE_MARKER_SCHEMA_INVALID")
    if not re.fullmatch(r"[0-9]+",pieces[2]):
        raise StructuralError("NATIVE_MARKER_TIME_INVALID")
    timestamp=int(pieces[2])
    if typ=="ENTER":
        if pieces[4] not in MODES:
            raise StructuralError("NATIVE_MODE_UNKNOWN")
        return {"type":typ,"t":timestamp,"list":pieces[3],"mode":pieces[4]}
    if typ=="ATTEMPT":
        if (not re.fullmatch(r"[0-9]+",pieces[5])
            or pieces[7] not in ("0","1")):
            raise StructuralError("NATIVE_ATTEMPT_NUMERIC_INVALID")
        return {"type":typ,"t":timestamp,"list":pieces[3],
                "owner":pieces[4],"ordinal":int(pieces[5]),
                "native_name":pieces[6],"ready":int(pieces[7])}
    if typ=="RETURN":
        if pieces[5] not in ("DIRECT","CALL_RECURSION"):
            raise StructuralError("NATIVE_RETURN_KIND_UNKNOWN")
        return {"type":typ,"t":timestamp,"list":pieces[3],
                "native_name":pieces[4],"reason":pieces[5]}
    return {"type":typ,"t":timestamp,"list":pieces[3]}


def root_foreground_groups(log):
    stack=[]
    capture=None
    roots=[]
    all_markers=0
    for line in log.splitlines():
        mark=unpack_marker(line)
        if mark is None:continue
        all_markers+=1
        typ=mark["type"]
        if typ=="ENTER":
            if not stack:
                capture=[] if mark["mode"]=="FOREGROUND" else None
            stack.append(mark["list"])
            if capture is not None:capture.append(mark)
            continue
        if not stack or mark["list"]!=stack[-1]:
            raise StructuralError("NATIVE_LIST_STACK_OR_EVENT_ORDER_INVALID")
        if capture is not None:capture.append(mark)
        if typ=="ATTEMPT":continue
        stack.pop()
        if not stack and capture is not None:
            if len(capture)<2:raise StructuralError("EMPTY_FOREGROUND_SCAN")
            roots.append(capture)
            capture=None
    if stack:raise StructuralError("NATIVE_SELECTION_STACK_UNBALANCED")
    if not roots:raise StructuralError("NO_REAL_NATIVE_FOREGROUND_SCANS")
    return roots,all_markers


def attrs(row):
    return {x["key"]:x["value"] for x in row["attributes"]}


def replay_group(group,source_lists):
    """Return derived winner without using a native RETURN as selection input."""
    cursor=0
    measures=Counter()
    path=[]
    index_order=[]
    def take():
        nonlocal cursor
        if cursor>=len(group):
            raise StructuralError("NATIVE_SELECT_ENDED_EARLY")
        item=group[cursor]
        cursor+=1
        return item
    def scan():
        intro=take()
        if intro["type"]!="ENTER":
            raise StructuralError("SOURCE_REPLAY_MISSING_LIST_ENTER")
        listed=intro["list"]
        if listed not in source_lists:
            raise StructuralError("NATIVE_SOURCE_LIST_NOT_PRESENT")
        rows=source_lists[listed]
        last_index=-1
        measures["select_action_scans"]+=1
        while True:
            event=take()
            if event["list"]!=listed:
                raise StructuralError("NATIVE_SOURCE_LIST_MISMATCH")
            if event["type"]=="NO_ACTION":
                measures["returned_null"]+=1
                return None
            if event["type"]!="ATTEMPT":
                raise StructuralError("NATIVE_RETURN_WITHOUT_READY_EVIDENCE")
            measures["native_ready_lookups"]+=1
            n=event["ordinal"]-1
            if event["owner"]!=listed or not 0<=n<len(rows):
                raise StructuralError("NATIVE_SOURCE_POINTER_MISSING_OR_WRONG")
            if n<=last_index:
                # C++ select_action has a source-controlled RNG/skill path.
                # This condition cannot be explained by ordinary priority
                # scanning, so fail rather than claim deterministic parity.
                raise StructuralError("NON_MONOTONE_APL_SCAN_UNSUPPORTED_RANDOM_OR_SKILL")
            last_index=n
            row=rows[n]
            path.append({"source_list":listed,"source_index":n,
                         "source_line":row["source_line"],
                         "command":row["action"],
                         "native_ready_bit":event["ready"]})
            index_order.append((listed,n))
            if event["ready"]==0:
                measures["native_unready_skipped"]+=1
                continue
            if row["action"]=="variable":
                measures["native_variable_side_effects"]+=1
                continue
            if row["action"]=="call_action_list":
                target=attrs(row).get("name")
                if not target or target not in source_lists:
                    raise StructuralError("NATIVE_CALL_DESTINATION_ABSENT")
                measures["ready_call_actions"]+=1
                child=scan()
                if child is None:
                    measures["call_fallback_null"]+=1
                    continue
                returned=take()
                if (returned["type"]!="RETURN" or
                    returned["list"]!=listed or
                    returned["reason"]!="CALL_RECURSION" or
                    returned["native_name"]!=child["native_name"]):
                    raise StructuralError("NATIVE_CALL_RETURN_NOT_SOURCE_REPLAY")
                measures["call_returned_child"]+=1
                return child
            # RUN is ACTION_OTHER. Its direct return is the list-control
            # action *now*, never the first action of the destination list.
            returned=take()
            if (returned["type"]!="RETURN" or
                returned["list"]!=listed or
                returned["reason"]!="DIRECT" or
                returned["native_name"]!=event["native_name"]):
                raise StructuralError("NATIVE_SELECTED_ACTION_DIFFERS_FROM_SOURCE_SCAN")
            measures["direct_ready_selected"]+=1
            if row["action"]=="run_action_list":
                measures["native_run_selected_not_recursed"]+=1
            return {"list":listed,"index":n,"native_name":event["native_name"],
                    "source_action":row["action"],
                    "source_sha256":row["source_sha256"],
                    "source_line":row["source_line"]}
    winner=scan()
    if cursor!=len(group):
        raise StructuralError("TRAILING_NATIVE_SELECT_EVENTS_NOT_REPLAYED")
    return winner,dict(measures),path


def verify_capture(folder,expected,oracle):
    folder=folder.resolve(strict=True)
    base=audit_dir(folder,expected)
    log=(folder/"simc_native_log.txt").read_bytes()
    effective=(folder/"simc_effective_actions.simc").read_bytes()
    source=parse_profile(effective,require_source=True,
                         expected_git_blob=UPSTREAM_PROFILE_BLOB)
    if (base["source_native_log_sha256"]!=sha(log)
        or base["native_effective_apl_sha256"]!=sha(effective)
        or base["source_selection_calls"]!=oracle["source_selection_calls"]
        or base["source_action_ready_attempts"]!=oracle["source_action_ready_attempts"]
        or base["selected_foreground_root_examples"]!=oracle["selected_foreground_root_examples"]):
        raise StructuralError("NATIVE_INDEPENDENT_EVIDENCE_RECEIPT_CHANGED")
    groups,marker_count=root_foreground_groups(log.decode("utf-8"))
    if len(groups)!=oracle["source_selection_calls"]["root_foreground_scans"]:
        raise StructuralError("NATIVE_FOREGROUND_ROOT_COUNT_MISMATCH")
    outcomes=[]
    totals=Counter()
    example_cursor=0
    for serial,group in enumerate(groups):
        winner,measure,path=replay_group(group,source["action_lists"])
        totals.update(measure)
        expected_winner=None
        if winner is None:
            totals["root_no_action"]+=1
        else:
            if example_cursor>=len(oracle["selected_foreground_root_examples"]):
                raise StructuralError("NATIVE_SELECTION_RECEIPT_TRUNCATED")
            reference=oracle["selected_foreground_root_examples"][example_cursor]
            example_cursor+=1
            source_ptr=reference["selected_row_pointer_proof"]
            if (winner["list"]!=source_ptr["list"] or
                winner["index"]!=source_ptr["source_index"] or
                winner["source_sha256"]!=source_ptr["source_sha256"] or
                winner["native_name"]!=reference["root_native_action"]):
                raise StructuralError("INDEPENDENT_SOURCE_SCAN_VS_NATIVE_SELECTED_POINTER_MISMATCH")
            totals["root_returned_action"]+=1
            expected_winner=source_ptr
        if len(outcomes)<12:
            outcomes.append({
                "scan_index":serial,"source_list":group[0]["list"],
                "time_ms":group[0]["t"],
                "native_selected_source_row":expected_winner,
                "selected_model_winner_given_native_ready_bits":winner,
                "attempted_apl_rows":path[:40],
                "all_attempt_rows_observed":len(path),
                "ready_meaning":"NATIVE_SOURCE_ACTION_READY_ORACLE_ONLY",
                "source_condition_semantics_independently_verified":False})
    if (example_cursor!=len(oracle["selected_foreground_root_examples"]) or
        totals["root_returned_action"]!=oracle["source_selection_calls"]["root_returned_action"] or
        totals["root_no_action"]!=oracle["source_selection_calls"]["root_no_action"]):
        raise StructuralError("NATIVE_ORACLE_ROOT_RESULT_RECONCILIATION_FAILED")
    return {
        "controlled_target_count":expected,
        "source_profile_git_blob_sha1":source["source_git_blob_sha1"],
        "native_binary_sha256":oracle["native_binary_sha256"],
        "native_effective_apl_sha256":base["native_effective_apl_sha256"],
        "original_log_sha256":base["source_native_log_sha256"],
        "foreground_root_scans":len(groups),
        "foreground_replay_counts":dict(totals),
        "parent_Calls_and_RUNs_source_control_parity_given_native_ready_bits":
            "PASS_CONDITIONAL_SOURCE_ORDER_REPLAY",
        "native_ability_readiness_independently_derived":False,
        "root_examples":outcomes,
        "native_marker_count":marker_count}


def run(st_dir,two_dir,oracle_file):
    source_bytes=oracle_file.read_bytes()
    native=json.loads(source_bytes)
    if (native.get("schema")!=AUDIT_SCHEMA or native.get("scope_policy_id")!=POLICY
        or native.get("native_same_binary_effective_APL_st_and_2t") is not True
        or native.get("native_foreground_decisions_observed")!=190
        or native.get("actual_native_choice_v2_model_parity")!="NOT_YET_PROVEN"
        or native.get("WCL_replay_allowed") is not False):
        raise StructuralError("NATIVE_SELECTED_SOURCE_ORACLE_NOT_VERIFIED")
    st=verify_capture(st_dir,1,native["st"])
    two=verify_capture(two_dir,2,native["two_target"])
    if (st["native_binary_sha256"]!=two["native_binary_sha256"] or
        st["native_effective_apl_sha256"]!=two["native_effective_apl_sha256"]):
        raise StructuralError("NATIVE_ST_2T_BUILD_OR_APL_DRIFT")
    if st["foreground_root_scans"]!=118 or two["foreground_root_scans"]!=96:
        raise StructuralError("NATIVE_SOURCE_SAMPLE_SCOPE_CHANGED")
    return {"schema":SCHEMA,"scope_policy_id":POLICY,
        "status":"SOURCE_SELECTION_STRUCTURE_CONDITIONAL_NATIVE_READY_INPUT_PASS",
        "source_oracle_receipt_sha256":sha(source_bytes),
        "native_same_source_and_binary_ST_2T":True,
        "total_foreground_root_scans":214,
        "source_structure_replay_accepted_roots":214,
        "real_native_foreground_selected_rows":190,
        "native_true_false_ready_inputs_used":True,
        "independent_simc_if_expression_parity":"NOT_TESTED",
        "independent_spell_ready_and_resource_parity":"NOT_TESTED",
        "full_General_Rotation_model_complete":False,
        "WCL_comparison_eligible":False,"MAIN_promotion":False,
        "st":st,"two_target":two}


def selftest():
    ir=parse_profile(
        b"actions=call_action_list,name=sub\n"
        b"actions+=/run_action_list,name=dest\n"
        b"actions.sub=alpha\n"
        b"actions.dest=beta\n",require_source=False)
    # The CALL returns nullptr; the caller must then return RUN itself.
    example=[
      "ZROT_NATIVE_SELECT_V1|ENTER|0|default|FOREGROUND",
      "ZROT_NATIVE_SELECT_V1|ATTEMPT|0|default|default|1|call_action_list|1",
      "ZROT_NATIVE_SELECT_V1|ENTER|0|sub|FOREGROUND",
      "ZROT_NATIVE_SELECT_V1|ATTEMPT|0|sub|sub|1|alpha|0",
      "ZROT_NATIVE_SELECT_V1|NO_ACTION|0|sub",
      "ZROT_NATIVE_SELECT_V1|ATTEMPT|0|default|default|2|run_action_list|1",
      "ZROT_NATIVE_SELECT_V1|RETURN|0|default|run_action_list|DIRECT"
    ]
    groups,count=root_foreground_groups("\n".join(example))
    assert count==7 and len(groups)==1
    win,measures,path=replay_group(groups[0],ir["action_lists"])
    assert win["source_action"]=="run_action_list"
    assert win["list"]=="default" and win["index"]==1
    assert measures["call_fallback_null"]==1
    assert measures["native_run_selected_not_recursed"]==1
    assert len(path)==3
    again=example.copy()
    again[-1]=again[-1].replace("run_action_list|DIRECT","alpha|DIRECT")
    try:replay_group(root_foreground_groups("\n".join(again))[0][0],ir["action_lists"])
    except StructuralError:pass
    else:raise AssertionError("WRONG_NATIVE_SELECTED_ROW_ACCEPTED")
    again=example.copy()
    again[-2]=again[-2].replace("default|2|","default|1|")
    try:replay_group(root_foreground_groups("\n".join(again))[0][0],ir["action_lists"])
    except StructuralError:pass
    else:raise AssertionError("NONMONOTONIC_ROW_INDEX_ACCEPTED")
    # A successful recursive call must not fall back to the next caller row.
    success=example[:3]+[
      "ZROT_NATIVE_SELECT_V1|ATTEMPT|0|sub|sub|1|alpha|1",
      "ZROT_NATIVE_SELECT_V1|RETURN|0|sub|alpha|DIRECT",
      "ZROT_NATIVE_SELECT_V1|RETURN|0|default|alpha|CALL_RECURSION"]
    w,m,_=replay_group(root_foreground_groups("\n".join(success))[0][0],ir["action_lists"])
    assert w["source_action"]=="alpha"
    assert m["call_returned_child"]==1
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":10,
            "native_source_replay_real_loaded":False,
            "gameplay_if_and_readiness_parity_proven":False,
            "WCL_API_calls":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-st-dir",type=Path)
    p.add_argument("--native-2t-dir",type=Path)
    p.add_argument("--native-selection-receipt",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    files=(args.native_st_dir,args.native_2t_dir,args.native_selection_receipt)
    if all(v is None for v in files):data=selftest()
    elif all(v is not None for v in files):
        data=run(*files)
    else:p.error("all three source evidence inputs required or none")
    blob=(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(",",":"))+"\n").encode()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("xb") as f:f.write(blob)
        print("SOURCE_ONLY_NATIVE_SELECT_STRUCTURE_REPLAY_SHA256="+sha(blob))
    else:print(blob.decode(),end="")


if __name__=="__main__":
    main()
