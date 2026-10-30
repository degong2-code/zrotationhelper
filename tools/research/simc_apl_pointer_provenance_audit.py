#!/usr/bin/env python3
"""Verify instrumented SimC native action-object -> effective APL row provenance.

Requires PINNED modified SimC JSON2 fields established by real pointer
identity, not names/time matching. Never infer fields for ordinary JSON2.
The association is an instantiated APL object; not proof the sample was the
selected foreground decision, the decision-time PRE state, or optimal play.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from simc_apl_syntax_inventory import parse as parse_apl
from simc_native_json_sequence import _raw_verified
from simc_apl_pointer_instrument import UPSTREAM_SHA

_SCHEMA="ZrotNativeSimcAplPointerProvenanceV1"
_PROOF="OWNING_LIST_SIGNATURE_POINTER_EQUALITY"


def _expected_rows(apl_bytes:bytes):
    try:
        decoded=apl_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError("EFFECTIVE_APL_ENCODING_INVALID") from e
    meta, lists=parse_apl(decoded)
    source_lines=decoded.splitlines()
    compiled={}
    for list_name,rows in lists.items():
        items=[]
        for index,row in enumerate(rows):
            raw_line=source_lines[row["line"]-1].strip()
            prefix,value=raw_line.split("=",1)
            if not prefix.startswith("actions"):
                raise ValueError("SOURCE_ROW_NOT_APL")
            if value.startswith("/"):
                value=value[1:]
            items.append({
                "list":list_name,"ordinal":index+1,
                "source_file_line":row["line"],"source_signature":value,
                "command":row["command"],"guard":row["condition"],
            })
        compiled[list_name]=items
    return compiled


def audit_native_provenance_from_parsed(native_json:dict,apl_bytes:bytes,
                                        *,effective_apl_sha256:str,
                                        expected_upstream_sha:str=UPSTREAM_SHA,
                                        require_callsite_proof:bool=False,
                                        require_selection_proof:bool=False):
    if expected_upstream_sha!=UPSTREAM_SHA:
        raise ValueError("INSTRUMENTED_UPSTREAM_PIN_MISMATCH")
    if hashlib.sha256(apl_bytes).hexdigest()!=effective_apl_sha256:
        raise ValueError("INSTRUMENTED_EFFECTIVE_APL_SHA_MISMATCH")
    if not isinstance(native_json,dict):
        raise ValueError("INSTRUMENTED_JSON2_ROOT_INVALID")
    sim=native_json.get("sim")
    players=sim.get("players") if isinstance(sim,dict) else None
    if not isinstance(players,list) or len(players)!=1:
        raise ValueError("INSTRUMENTED_JSON2_SINGLE_ACTOR_REQUIRED")
    player=players[0]
    collected=player.get("collected_data") if isinstance(player,dict) else None
    if not isinstance(collected,dict) or not isinstance(collected.get("action_sequence"),list):
        raise ValueError("INSTRUMENTED_JSON2_ACTION_SEQUENCE_REQUIRED")
    apl=_expected_rows(apl_bytes)
    statuses=Counter()
    callsite_counts=Counter()
    selection_counts=Counter()
    event_results=[]
    for sequence,key in [("PRECOMBAT","action_sequence_precombat"),("COMBAT","action_sequence")]:
        records=collected.get(key,[])
        if not isinstance(records,list):
            raise ValueError("INSTRUMENTED_SEQUENCE_NOT_LIST")
        for ordinal,record in enumerate(records):
            if not isinstance(record,dict):
                raise ValueError("INSTRUMENTED_SEQUENCE_ROW_INVALID")
            proof_keys=("zrot_apl_object_list","zrot_apl_object_ordinal",
                        "zrot_apl_object_signature","zrot_origin_proof")
            present=[k in record for k in proof_keys]
            status="NO_POINTER_PROVENANCE"
            matched=None
            if any(present):
                if not all(present):
                    raise ValueError("INSTRUMENTED_POINTER_PROVENANCE_PARTIAL")
                if record["zrot_origin_proof"]!=_PROOF:
                    raise ValueError("INSTRUMENTED_POINTER_PROOF_KIND_INVALID")
                name=record["zrot_apl_object_list"]
                ix=record["zrot_apl_object_ordinal"]
                signature=record["zrot_apl_object_signature"]
                if not isinstance(name,str) or not name or name not in apl:
                    status="SOURCE_APL_LIST_NOT_FOUND"
                elif type(ix) is not int or ix<1 or ix>len(apl[name]):
                    status="SOURCE_APL_ORDINAL_OUT_OF_RANGE"
                elif not isinstance(signature,str):
                    raise ValueError("INSTRUMENTED_POINTER_SIGNATURE_INVALID")
                else:
                    matched=apl[name][ix-1]
                    status=("POINTER_ROW_AND_EXACT_EFFECTIVE_APL_SIGNATURE_MATCH"
                            if matched["source_signature"]==signature else
                            "POINTER_ROW_MATCH_SIGNATURE_DRIFT_NEEDS_REVIEW")
            if record.get("queue_failed") is True and status.startswith("POINTER_"):
                status="QUEUE_FAILED_"+status
            if ("name" not in record or record.get("wait") is not None) and any(present):
                raise ValueError("INSTRUMENTED_NONACTION_WITH_POINTER")
            origin=record.get("zrot_sequence_origin_callsite")
            if origin is None:
                origin=("WAIT_NON_ACTION" if "wait" in record and "name" not in record
                        else "UNKNOWN_CALLSITE")
            allowed=("PRECOMBAT_DIRECT","FOREGROUND_EXECUTE_ACTION",
                     "QUEUED_SPECIALIZED_EXECUTE","VARIABLE_SIDE_EFFECT",
                     "UNKNOWN_CALLSITE","WAIT_NON_ACTION")
            if not isinstance(origin,str) or origin not in allowed:
                raise ValueError("INSTRUMENTED_SEQUENCE_CALLSITE_INVALID")
            if require_callsite_proof and origin=="UNKNOWN_CALLSITE" and "name" in record:
                raise ValueError("INSTRUMENTED_SEQUENCE_CALLSITE_MISSING")
            if (origin=="PRECOMBAT_DIRECT" and sequence!="PRECOMBAT"):
                raise ValueError("INSTRUMENTED_PRECOMBAT_CALLSITE_ON_COMBAT_RECORD")
            selection=record.get("zrot_foreground_selection_path")
            is_action="name" in record and record.get("wait") is None
            valid_selection=("SELECT_ACTION_FOREGROUND","STRICT_SEQUENCE",
                             "SPELL_QUEUED_ACTION","NOT_APPLICABLE",
                             "UNKNOWN_FOREGROUND_BRANCH")
            if not is_action:
                if selection is not None or origin not in ("WAIT_NON_ACTION",):
                    raise ValueError("INSTRUMENTED_WAIT_HAS_SELECTION_PROVENANCE")
                selection="WAIT_NON_ACTION"
            else:
                if selection is None:
                    selection="MISSING_SELECTION_PROVENANCE"
                if selection not in valid_selection+("MISSING_SELECTION_PROVENANCE",):
                    raise ValueError("INSTRUMENTED_SELECTION_BRANCH_INVALID")
                if origin=="FOREGROUND_EXECUTE_ACTION":
                    if selection=="NOT_APPLICABLE":
                        raise ValueError("INSTRUMENTED_FOREGROUND_BRANCH_NOT_APPLICABLE")
                    if require_selection_proof and selection in (
                        "MISSING_SELECTION_PROVENANCE","UNKNOWN_FOREGROUND_BRANCH"):
                        raise ValueError("INSTRUMENTED_FOREGROUND_SELECTION_UNPROVEN")
                else:
                    if require_selection_proof and selection!="NOT_APPLICABLE":
                        raise ValueError("INSTRUMENTED_NONFOREGROUND_SELECTION_CONFLICT")
                    if selection in ("SELECT_ACTION_FOREGROUND","STRICT_SEQUENCE",
                                     "SPELL_QUEUED_ACTION"):
                        raise ValueError("INSTRUMENTED_SELECTION_WITHOUT_FOREGROUND_CALLSITE")
            selection_counts[selection]+=1
            callsite_counts[origin]+=1
            statuses[status]+=1
            event_results.append({
                "sequence":sequence,"ordinal":ordinal,
                "native_action_token":record.get("name"),
                "native_action_object_id":record.get("id"),
                "native_action_timestamp_s":record.get("time"),
                "pointer_proof_status":status,
                "sequence_add_callsite":origin,
                "foreground_selection_path":selection,
                "foreground_apl_select_action_confirmed":
                    selection=="SELECT_ACTION_FOREGROUND"
                    and status=="POINTER_ROW_AND_EXACT_EFFECTIVE_APL_SIGNATURE_MATCH"
                    and origin=="FOREGROUND_EXECUTE_ACTION",
                "source_apl_list":matched["list"] if matched else None,
                "source_apl_rank":matched["ordinal"] if matched else None,
                "source_apl_file_line":matched["source_file_line"] if matched else None,
                "source_apl_command":matched["command"] if matched else None,
                "is_foreground_decision_certified":False,
                "own_timestamp_is_strict_pre":False,
            })
    return {
        "schema":_SCHEMA,
        "effective_apl_sha256":effective_apl_sha256,
        "source_upstream_commit_sha":expected_upstream_sha,
        "instrumentation_mechanism":_PROOF,
        "apl_lists":len(apl),
        "apl_source_rows":sum(len(r) for r in apl.values()),
        "native_sequence_rows":len(event_results),
        "pointer_status_counts":dict(sorted(statuses.items())),
        "sequence_callsite_status_counts":dict(sorted(callsite_counts.items())),
        "foreground_selection_path_counts":dict(sorted(selection_counts.items())),
        "source_bound_native_select_action_rows":sum(
            int(row["foreground_apl_select_action_confirmed"]) for row in event_results),
        "sequence_provenance":event_results,
        "source_binding_proof":"NATIVE_ACTION_OBJECT_POINTER_MATCH_ONLY",
        "selected_foreground_apl_action":"NOT_CERTIFIED",
        "strict_pre_state":"NOT_RUN",
        "verified_rotation_priority":"NOT_VALIDATED",
        "gameplay_rule_promotion":False,
    }


def audit_captured_native(root:Path,*,require_callsite_proof:bool=False,
                          require_selection_proof:bool=False):
    receipt,raw=_raw_verified(root)
    effective=(root/"simc_effective_actions.simc").read_bytes()
    if hashlib.sha256(effective).hexdigest()!=receipt["effective_apl_sha256"]:
        raise ValueError("EFFECTIVE_APL_RECEIPT_CHANGED")
    if not receipt.get("instrumented_upstream_sha256")==UPSTREAM_SHA:
        raise ValueError("INSTRUMENTED_UPSTREAM_RECEIPT_REQUIRED")
    if not isinstance(receipt.get("instrumented_binary_sha256"),str) or (
            receipt.get("instrumented_binary_sha256")!=receipt.get("simc_executable_sha256")):
        raise ValueError("INSTRUMENTED_BINARY_SHA_RECEIPT_REQUIRED")
    try:
        source=json.loads(raw)
    except (UnicodeDecodeError,json.JSONDecodeError) as e:
        raise ValueError("INSTRUMENTED_JSON2_INVALID") from e
    report=audit_native_provenance_from_parsed(
        source,effective,effective_apl_sha256=receipt["effective_apl_sha256"],
        require_callsite_proof=require_callsite_proof,
        require_selection_proof=require_selection_proof)
    report.update({
        "source_profile_sha256":receipt["profile_sha256"],
        "source_native_json2_sha256":receipt["native_json2_sha256"],
        "source_instrumented_executable_sha256":receipt["simc_executable_sha256"],
        "source_capture_receipt_status":receipt["status"],
    })
    return report


def selftest():
    effective=(b"spec=synthetic\n"
               b"actions=alpha,if=buff.a.up\n"
               b"actions+=/alpha,if=buff.b.up\n"
               b"actions+=/call_action_list,name=burst\n"
               b"actions.burst=beta\n")
    def native(name,rank,signature,**extra):
        return {"time":0.0,"name":name,"id":123,"queue_failed":False,
                "zrot_apl_object_list":"default","zrot_apl_object_ordinal":rank,
                "zrot_apl_object_signature":signature,"zrot_origin_proof":_PROOF,
                **extra}
    doc={"sim":{"players":[{"collected_data":{
        "action_sequence_precombat":[],
        "action_sequence":[native("alpha",1,"alpha,if=buff.a.up"),
                           native("alpha",2,"alpha,if=buff.b.up"),
                           native("beta",1,"beta",zrot_apl_object_list="burst")
                           ]
    }}]}}
    # The two alpha events at the *same time* have different pointer-backed
    # APL rows. No time/name uniqueness assumptions needed.
    first=audit_native_provenance_from_parsed(
        doc,effective,effective_apl_sha256=hashlib.sha256(effective).hexdigest())
    statuses=first["pointer_status_counts"]
    assert statuses=={"POINTER_ROW_AND_EXACT_EFFECTIVE_APL_SIGNATURE_MATCH":3},statuses
    assert [e["source_apl_rank"] for e in first["sequence_provenance"]]==[1,2,1]
    assert first["sequence_provenance"][2]["source_apl_list"]=="burst"
    assert not first["gameplay_rule_promotion"]
    assert first["sequence_callsite_status_counts"]=={"UNKNOWN_CALLSITE":3}
    added=json.loads(json.dumps(doc))
    for record in added["sim"]["players"][0]["collected_data"]["action_sequence"]:
        record["zrot_sequence_origin_callsite"]="FOREGROUND_EXECUTE_ACTION"
    classified=audit_native_provenance_from_parsed(
        added,effective,effective_apl_sha256=hashlib.sha256(effective).hexdigest(),
        require_callsite_proof=True)
    assert classified["sequence_callsite_status_counts"]=={"FOREGROUND_EXECUTE_ACTION":3}
    assert all(not x["foreground_apl_select_action_confirmed"]
               for x in classified["sequence_provenance"])
    selection_report=json.loads(json.dumps(added))
    row_list=selection_report["sim"]["players"][0]["collected_data"]["action_sequence"]
    for rec in row_list:
        rec["zrot_foreground_selection_path"]="SELECT_ACTION_FOREGROUND"
    strict=audit_native_provenance_from_parsed(
        selection_report,effective,
        effective_apl_sha256=hashlib.sha256(effective).hexdigest(),
        require_callsite_proof=True,require_selection_proof=True)
    assert strict["source_bound_native_select_action_rows"]==3
    assert strict["foreground_selection_path_counts"]=={"SELECT_ACTION_FOREGROUND":3}
    assert all(rec["is_foreground_decision_certified"] is False
               for rec in strict["sequence_provenance"])
    row_list[0]["zrot_foreground_selection_path"]="STRICT_SEQUENCE"
    row_list[1]["zrot_foreground_selection_path"]="SPELL_QUEUED_ACTION"
    mixed=audit_native_provenance_from_parsed(
        selection_report,effective,
        effective_apl_sha256=hashlib.sha256(effective).hexdigest(),
        require_callsite_proof=True,require_selection_proof=True)
    assert mixed["source_bound_native_select_action_rows"]==1
    row_list[1]["zrot_foreground_selection_path"]="NOT_APPLICABLE"
    try:audit_native_provenance_from_parsed(
        selection_report,effective,
        effective_apl_sha256=hashlib.sha256(effective).hexdigest(),
        require_callsite_proof=True,require_selection_proof=True)
    except ValueError as e:assert str(e)=="INSTRUMENTED_FOREGROUND_BRANCH_NOT_APPLICABLE"
    else:raise AssertionError("FALSE_FOREGROUND_PROOF_ACCEPTED")
    del row_list[1]["zrot_foreground_selection_path"]
    try:audit_native_provenance_from_parsed(
        selection_report,effective,
        effective_apl_sha256=hashlib.sha256(effective).hexdigest(),
        require_callsite_proof=True,require_selection_proof=True)
    except ValueError as e:assert str(e)=="INSTRUMENTED_FOREGROUND_SELECTION_UNPROVEN"
    else:raise AssertionError("MISSING_FOREGROUND_PROOF_ACCEPTED")
    try:audit_native_provenance_from_parsed(
        doc,effective,effective_apl_sha256=hashlib.sha256(effective).hexdigest(),
        require_callsite_proof=True)
    except ValueError as e:assert str(e)=="INSTRUMENTED_SEQUENCE_CALLSITE_MISSING"
    else:raise AssertionError("MISSING_CALLSITE_ACCEPTED")

    missing=json.loads(json.dumps(doc))
    for key in ("zrot_apl_object_list","zrot_apl_object_ordinal",
                "zrot_apl_object_signature","zrot_origin_proof"):
        del missing["sim"]["players"][0]["collected_data"]["action_sequence"][0][key]
    unknown=audit_native_provenance_from_parsed(
        missing,effective,effective_apl_sha256=hashlib.sha256(effective).hexdigest())
    assert unknown["pointer_status_counts"]["NO_POINTER_PROVENANCE"]==1
    drift=json.loads(json.dumps(doc))
    drift["sim"]["players"][0]["collected_data"]["action_sequence"][0]["zrot_apl_object_signature"]="modified_option=1"
    assert audit_native_provenance_from_parsed(
        drift,effective,effective_apl_sha256=hashlib.sha256(effective).hexdigest())[
            "pointer_status_counts"]["POINTER_ROW_MATCH_SIGNATURE_DRIFT_NEEDS_REVIEW"]==1
    tamper=json.loads(json.dumps(doc))
    del tamper["sim"]["players"][0]["collected_data"]["action_sequence"][0]["zrot_origin_proof"]
    try:audit_native_provenance_from_parsed(
        tamper,effective,effective_apl_sha256=hashlib.sha256(effective).hexdigest())
    except ValueError as e:assert str(e)=="INSTRUMENTED_POINTER_PROVENANCE_PARTIAL"
    else:raise AssertionError("PARTIAL_POINTER_PROVENANCE_ACCEPTED")
    for changed,err in [("0"*64,"INSTRUMENTED_EFFECTIVE_APL_SHA_MISMATCH")]:
        try:audit_native_provenance_from_parsed(doc,effective,effective_apl_sha256=changed)
        except ValueError as e:assert str(e)==err
        else:raise AssertionError("SOURCE_PIN_MISMATCH_ACCEPTED")
    print("SIMC_APL_POINTER_PROVENANCE_AUDIT_SELF_TEST=PASS DUPLICATE_ACTION_ROWS=2")


def main():
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture-dir",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test or args.capture_dir is None:
        selftest()
        return
    report=audit_captured_native(args.capture_dir)
    content=json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(content,encoding="utf-8")
        print("WROTE_SIMC_APL_POINTER_PROVENANCE_AUDIT")
    else:
        print(content)


if __name__=="__main__":
    main()
