#!/usr/bin/env python3
"""Independent audit of source-pinned native SimC selected APL row traces.

The producer instruments player_t::select_action(), verifies exact APL
signature pointer identity, and records actual action_ready() returns. This
auditor reconstructs nested native CALL recursion from ordered log markers;
RUN is never treated as a recursive CALL. Selected rows are attested native
source observations but NOT a validated independent APL interpreter, WCL
priority rule, cooldown/charge truth or dummy-error verdict.

Without inputs, runs safe synthetic trace tests.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
from collections import Counter
from simc_apl_semantic_ir_v2 import parse_profile

SCHEMA="ZrotNativeSelectAplRowProvenanceV1"
MARK="ZROT_NATIVE_SELECT_V1|"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

class AuditError(ValueError):pass

def sha(raw):return hashlib.sha256(raw).hexdigest()

def to_number(value, label):
    if not re.fullmatch(r"-?[0-9]+",str(value)):
        raise AuditError("INVALID_NATIVE_"+label)
    return int(value)

def audit_lines(lines,ir,*,max_selected=120):
    if ir.get("schema")!="ZrotSourceFaithfulSimcAplSemanticIRV2":
        raise AuditError("EFFECTIVE_APL_IR_SCHEMA_MISMATCH")
    source_lists=ir["action_lists"]
    stack=[]
    selected=[]
    attempts=Counter()
    unknown=Counter()
    decisions=Counter()
    markers=0
    for line in lines:
        where=line.find(MARK)
        if where<0:continue
        markers+=1
        # Log text is read only from the marker onward. No event timestamp
        # derived from SimC's human-readable lines or WCL data.
        fields=line[where:].strip().split("|")
        kind=fields[1] if len(fields)>1 else ""
        if kind=="ENTER":
            if len(fields)!=5:raise AuditError("ENTER_MARKER_FIELD_COUNT")
            ts=to_number(fields[2],"TIME")
            name,mode=fields[3:]
            if name not in source_lists:raise AuditError("NATIVE_APL_LIST_NOT_IN_EFFECTIVE_SOURCE")
            if mode not in ("FOREGROUND","OFF_GCD","CAST_WHILE_CASTING"):
                raise AuditError("UNKNOWN_NATIVE_EXECUTION_MODE")
            stack.append({"name":name,"mode":mode,"ts":ts,
                          "attempts":[],"last_child":None})
            decisions["native_select_calls"]+=1
            continue
        if not stack:raise AuditError("MARKER_OUTSIDE_NATIVE_SELECT_STACK")
        frame=stack[-1]
        if kind=="ATTEMPT":
            if len(fields)!=8:raise AuditError("ATTEMPT_MARKER_FIELD_COUNT")
            ts=to_number(fields[2],"TIME")
            name,owner=fields[3],fields[4]
            ordinal=to_number(fields[5],"ORDINAL")
            native_action=fields[6]
            state=to_number(fields[7],"READY")
            if state not in (0,1) or frame["name"]!=name:
                raise AuditError("NATIVE_ATTEMPT_CONTEXT_CONTRADICTION")
            record={"timestamp_ms":ts,"visited_list":name,
                "effective_apl_owner":owner,
                "effective_apl_ordinal_1based":ordinal,
                "native_action_name":native_action,
                "native_action_ready_result":state}
            if owner=="UNKNOWN" or ordinal==0:
                unknown["not_pointer_identified"]+=1
                record["effective_source_row"]=None
            elif owner in source_lists and 1<=ordinal<=len(source_lists[owner]):
                row=source_lists[owner][ordinal-1]
                record["effective_source_row"]={
                    "list":owner,"source_index":ordinal-1,
                    "source_text":row["source_text"],
                    "source_action":row["action"],
                    "source_file_line":row["source_line"],
                    "source_sha256":row["source_sha256"]}
            else:raise AuditError("NATIVE_SIGNATURE_POINTER_ROW_OUTSIDE_EFFECTIVE_APL")
            attempts["total"]+=1
            attempts["ready" if state else "not_ready"]+=1
            frame["attempts"].append(record)
            continue
        if kind not in ("RETURN","NO_ACTION"):
            raise AuditError("UNKNOWN_NATIVE_SELECT_EVENT_TYPE")
        if kind=="RETURN":
            if len(fields)!=6:raise AuditError("RETURN_MARKER_FIELD_COUNT")
            ts=to_number(fields[2],"TIME")
            owner,token,why=fields[3:]
            if owner!=frame["name"] or why not in ("DIRECT","CALL_RECURSION"):
                raise AuditError("RETURN_FRAME_LIST_OR_KIND_MISMATCH")
            if why=="DIRECT":
                if not frame["attempts"]:
                    raise AuditError("SOURCE_SELECTED_WITHOUT_READY_ATTEMPT")
                provenance=frame["attempts"][-1]
                if not provenance["native_action_ready_result"]:
                    raise AuditError("NATIVE_RETURNED_NOT_READY_ACTION")
            else:
                provenance=frame["last_child"]
                if not provenance:
                    raise AuditError("NATIVE_RECURSIVE_RETURN_WITHOUT_CHILD")
            if token!=provenance["native_action_name"]:
                raise AuditError("SOURCE_NATIVE_TOKEN_RETURN_CONTRADICTION")
        else:
            if len(fields)!=4:raise AuditError("NO_ACTION_MARKER_FIELD_COUNT")
            ts=to_number(fields[2],"TIME")
            owner=fields[3]
            if owner!=frame["name"]:raise AuditError("NO_ACTION_FRAME_MISMATCH")
            provenance=None
        stack.pop()
        if stack:
            stack[-1]["last_child"]=provenance
        elif frame["mode"]=="FOREGROUND":
            decisions["root_foreground_scans"]+=1
            if provenance is None:
                decisions["root_no_action"]+=1
            else:
                decisions["root_returned_action"]+=1
                if provenance["effective_source_row"] is None:
                    unknown["root_source_pointer_unknown"]+=1
                if len(selected)<max_selected:
                    selected.append({
                        "root_time_ms":frame["ts"],
                        "root_source_list":frame["name"],
                        "root_native_action":provenance["native_action_name"],
                        "selected_row_pointer_proof":provenance["effective_source_row"],
                        "native_action_ready_observed":True,
                        "full_APL_interpreter_parity":"NOT_TESTED",
                        "actual_player_optimality":"NOT_ESTABLISHED"})
    if stack:raise AuditError("UNBALANCED_NATIVE_SOURCE_RECURSION")
    if markers<1:raise AuditError("NO_NATIVE_SELECTION_TRACE")
    return {"schema":SCHEMA,"scope_policy_id":POLICY,
       "status":"NATIVE_SELECTED_SOURCE_ROWS_OBSERVED_INTERPRETER_PARITY_NOT_TESTED",
       "markers":markers,"source_action_ready_attempts":dict(attempts),
       "source_selection_calls":dict(decisions),
       "source_unknowns":dict(unknown),
       "selected_foreground_sample_limit":max_selected,
       "selected_foreground_root_examples":selected,
       "native_source_apl_rows":ir["source_action_line_count"],
       "native_selected_foreground_row_coverage":
          "PARTIAL_UNLESS_ALL_SELECTIONS_MATCH",
       "native_action_selection_parity_with_independent_engine":"NOT_RUN",
       "WCL_comparison_eligible":False,
       "dummy_mistake_eligible":False,
       "MAIN_promotion":False}

def audit_dir(folder,expected_targets):
    folder=folder.resolve(strict=True)
    receipt=json.loads((folder/"simc_reference_receipt.json").read_bytes())
    effective=(folder/"simc_effective_actions.simc").read_bytes()
    log=(folder/"simc_native_log.txt").read_bytes()
    if (receipt.get("schema")!="ZrotSimcNativeReferenceCaptureV1"
        or receipt.get("status")!="SIMC_NATIVE_CAPTURED_UNPARSED"
        or receipt.get("source_kind")!="LOCAL_SIMC_EXECUTABLE"
        or receipt.get("simc_spec")!="fury"
        or receipt.get("controlled_target_count")!=expected_targets
        or receipt.get("controlled_seed")!=31459
        or receipt.get("controlled_fight_seconds")!=30
        or receipt.get("effective_apl_sha256")!=sha(effective)
        or receipt.get("native_log_sha256")!=sha(log)
        or receipt.get("main_authority_promotion") is not False):
        raise AuditError("NATIVE_REFERENCE_IDENTITY_OR_COMPARABILITY_MISMATCH")
    ir=parse_profile(effective,require_source=False)
    if ir["source_action_line_count"]!=121:
        raise AuditError("PINNED_NATIVE_EFFECTIVE_APL_SOURCE_COUNT_CHANGED")
    result=audit_lines(log.decode("utf-8").splitlines(),ir)
    result["target_count_controlled"]=expected_targets
    result["native_binary_sha256"]=receipt["simc_executable_sha256"]
    result["native_effective_apl_sha256"]=sha(effective)
    result["source_native_log_sha256"]=sha(log)
    return result

def selftest():
    ir=parse_profile(
        b"actions=call_action_list,name=sub\n"
        b"actions+=/run_action_list,name=other\n"
        b"actions.sub=alpha\n"
        b"actions.other=beta\n",require_source=False)
    events=[
        "ZROT_NATIVE_SELECT_V1|ENTER|100|default|FOREGROUND",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|100|default|default|1|call_action_list|1",
        "ZROT_NATIVE_SELECT_V1|ENTER|100|sub|FOREGROUND",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|100|sub|sub|1|alpha|1",
        "ZROT_NATIVE_SELECT_V1|RETURN|100|sub|alpha|DIRECT",
        "ZROT_NATIVE_SELECT_V1|RETURN|100|default|alpha|CALL_RECURSION",
        "ZROT_NATIVE_SELECT_V1|ENTER|200|default|FOREGROUND",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|200|default|default|1|call_action_list|0",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|200|default|default|2|run_action_list|1",
        "ZROT_NATIVE_SELECT_V1|RETURN|200|default|run_action_list|DIRECT",
        "ZROT_NATIVE_SELECT_V1|ENTER|201|other|FOREGROUND",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|201|other|other|1|beta|1",
        "ZROT_NATIVE_SELECT_V1|RETURN|201|other|beta|DIRECT",
        "ZROT_NATIVE_SELECT_V1|ENTER|210|default|FOREGROUND",
        "ZROT_NATIVE_SELECT_V1|NO_ACTION|210|default"
    ]
    out=audit_lines(events,ir)
    assert out["source_selection_calls"]["root_foreground_scans"]==4
    assert out["source_selection_calls"]["root_returned_action"]==3
    assert out["source_action_ready_attempts"]["total"]==5
    assert out["selected_foreground_root_examples"][0]["root_native_action"]=="alpha"
    assert out["selected_foreground_root_examples"][1]["root_native_action"]=="run_action_list"
    assert out["selected_foreground_root_examples"][2]["root_native_action"]=="beta"
    assert out["source_unknowns"]=={}
    bad=events.copy();bad[5]=bad[5].replace("alpha","beta")
    try:audit_lines(bad,ir)
    except AuditError:pass
    else:raise AssertionError("ACCEPTED_BAD_NATIVE_RETURN_TOKEN")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":7,
        "real_native_SimC_loaded":False,"WCL_API_requests":0,
        "claim_of_independent_model_parity":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-st-dir",type=Path)
    p.add_argument("--native-2t-dir",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not a.native_st_dir and not a.native_2t_dir:
        r=selftest()
    elif a.native_st_dir and a.native_2t_dir:
        st=audit_dir(a.native_st_dir,1)
        tw=audit_dir(a.native_2t_dir,2)
        if (st["native_binary_sha256"]!=tw["native_binary_sha256"]
            or st["native_effective_apl_sha256"]!=tw["native_effective_apl_sha256"]):
            raise AuditError("NATIVE_ST_2T_BINARY_OR_APL_DRIFT")
        r={"schema":"ZrotNativeSimcSelectedRowTwoTargetAuditV1",
           "scope_policy_id":POLICY,
           "status":"NATIVE_SOURCE_SELECTED_ROWS_RECORDED_NOT_INDEPENDENT_MODEL_PARITY",
           "native_same_binary_effective_APL_st_and_2t":True,
           "st":st,"two_target":tw,"source_test_cases":2,
           "native_foreground_decisions_observed":
             sum(x["source_selection_calls"].get("root_returned_action",0)
                 for x in (st,tw)),
           "native_actual_selected_row_observation":True,
           "actual_native_choice_v2_model_parity":"NOT_YET_PROVEN",
           "opener_ST_2T_final_model_ready":False,
           "WCL_replay_allowed":False,"MAIN_promotion":False}
    else:p.error("both independent 1-target and 2-target native captures required")
    blob=(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("NATIVE_SOURCE_SELECTED_ROW_AUDIT_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
