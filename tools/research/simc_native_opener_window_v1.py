#!/usr/bin/env python3
"""Create an observed opener-window research fixture from a pinned native SimC
reference capture. Reuses JSON2 extraction and SimC APL IR. Not a rotation
recommendation, nor an empirical WCL validation or Strict PRE state.

Safe default without CLI parameters: offline self-test. No network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from simc_native_json_sequence import extract_json_sequence
from simc_apl_source_engine import ingest_actions
from simc_apl_conditional_ir import compile_structural_ir

SCHEMA="ZrotObservedSimcOpenerWindowCandidateV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

def build(reference_dir:Path,*,window_seconds:float=15.,expected_spec:str|None=None)->dict[str,Any]:
    if not isinstance(window_seconds,(int,float)) or isinstance(window_seconds,bool) or not 0<window_seconds<=120:
        raise ValueError("INVALID_OPENER_OBSERVATION_WINDOW")
    root=reference_dir.resolve(strict=True)
    seq=extract_json_sequence(root)
    spec=seq["simc_spec"]
    if expected_spec is not None and expected_spec!=spec:
        raise ValueError("SPEC_IDENTITY_MISMATCH")
    receipt=json.loads((root/"simc_reference_receipt.json").read_text(encoding="utf-8"))
    source_bytes=(root/"simc_effective_actions.simc").read_bytes()
    if hashlib.sha256(source_bytes).hexdigest()!=seq["source_apl_sha256"]:
        raise ValueError("SOURCE_APL_SHA256_MISMATCH")
    source=ingest_actions(source_bytes,expected_spec=spec)
    ir=compile_structural_ir(source)
    # These are sample action records, not a proof of actual APL priority or of
    # the source action selected at a particular Strict PRE decision state.
    precombat=seq["precombat_sequence"]
    all_combat=seq["combat_sequence"]
    in_window=[x for x in all_combat if 0<=x["time_seconds"]<window_seconds]
    observed=[x for x in in_window if x["record_kind"]=="SAMPLE_ACTION"]
    queued=[x for x in in_window if x["record_kind"]=="ACTION_RECORDED_QUEUE_FAILED"]
    waiting=[x for x in in_window if x["record_kind"]=="WAIT_NON_ACTION"]
    if any(x["queue_failed"] for x in observed):
        raise ValueError("QUEUED_FAILED_MISCLASSIFIED_AS_PERFORMED")
    result={
      "schema":SCHEMA,"scope_policy_id":POLICY,
      "source_kind":"SIMC_NATIVE_JSON2_CAPTURE",
      "simc_spec":spec,
      "source_capture_status":seq["source_capture_status"],
      "source_native_executable_sha256":seq["source_simc_executable_sha256"],
      "source_profile_sha256":seq["source_profile_sha256"],
      "source_apl_sha256":source["apl_sha256"],
      "source_native_json2_sha256":seq["source_native_json2_sha256"],
      "precombat_observed_record_count":len(precombat),
      "precombat_records":precombat[:50],
      "precombat_action_list_rows":len(ir["lists"].get("precombat",[])),
      "precombat_not_interpreted_as_combat_opener":True,
      "opener_observation_window_seconds":window_seconds,
      "opener_observed_action_count":len(observed),
      "opener_observed_actions":[{
        "timestamp_ms":x["timestamp_ms"],
        "record_ordinal":x["ordinal"],
        "action_token":x["action_token"],
        "numeric_spell_id":x["numeric_action_id"],
        "resources_snapshot_at_action_time":x["resources_snapshot"],
        "buffs_snapshot_at_action_time":x["buffs_snapshot"],
        "cooldowns_snapshot_at_action_time":x["cooldowns_snapshot"],
        "strict_pre_status":"UNVERIFIED_AT_ACTION_TIMESTAMP",
        "source_APL_row_mapping":"UNKNOWN",
      } for x in observed],
      "opener_queue_failed_record_count":len(queued),
      "opener_wait_record_count":len(waiting),
      "post_window_observation_record_count":len(all_combat)-len(in_window),
      "original_simc_APL_required_state_operands":ir["required_state_operands"],
      "original_APL_target_breakpoint_guards":[{
        "list":name,"guard":row["guard"],"source_line":row["source_line"]
      } for name,rows in ir["lists"].items() for row in rows
          if row["guard"] is not None and "active_enemies" in row["guard"]],
      "phase_label":"OBSERVED_FIRST_SECONDS_NOT_PROVEN_COMPLETE_OPENER",
      "actual_SimC_executable_capture":seq["source_capture_status"]=="SIMC_NATIVE_CAPTURED_UNPARSED",
      "snapshot_state_is_not_strict_PRE":True,
      "opener_sequence_optimality":"NOT_PROVEN",
      "WCL_independent_candidate_lock":"NOT_RUN",
      "WCL_ranker_validation":"NOT_RUN",
      "ready_for_target_dummy_mistake_feedback":False,
      "MAIN_or_FROZEN_promoted":False,
    }
    if not result["opener_observed_actions"]:
        result["phase_label"]="UNKNOWN_NO_ACTIONS_OBSERVED_IN_WINDOW"
    return result

def selftest()->dict:
    with tempfile.TemporaryDirectory(prefix="zrot-native-opener-") as temp:
        root=Path(temp)
        actions=b"spec=fury\nactions.precombat=snapshot_stats\nactions=rampage,if=rage>=80\nactions+=/bloodthirst\n"
        log=b"0.000 Player 'Fake' performs Action 'rampage' (184367) (80)\n"
        data={"sim":{"players":[{"collected_data":{
          "action_sequence_precombat":[{"time":-0.5,"name":"snapshot_stats","id":0}],
          "action_sequence":[
            {"time":0.0,"name":"rampage","id":184367,"resources":{"rage":80},"buffs":[]},
            {"time":0.0,"wait":0.15},
            {"time":0.5,"name":"bloodthirst","id":23881,"queue_failed":True},
            {"time":1.0,"name":"bloodthirst","id":23881,"resources":{"rage":100}},
            {"time":15.0,"name":"rampage","id":184367},
          ]
        }}]}}
        files={
         "simc_effective_actions.simc":actions,
         "simc_native_log.txt":log,
         "simc_native_sequence.json":json.dumps(data).encode(),
        }
        for name,raw in files.items():(root/name).write_bytes(raw)
        r={
          "schema":"ZrotSimcNativeReferenceCaptureV1","status":"SYNTHETIC_CAPTURE_TEST",
          "simc_spec":"fury","profile_sha256":"a"*64,
          "simc_executable_sha256":"b"*64,
          "effective_apl_sha256":hashlib.sha256(actions).hexdigest(),
          "native_json2_sha256":hashlib.sha256(files["simc_native_sequence.json"]).hexdigest(),
          "native_log_sha256":hashlib.sha256(log).hexdigest(),
          "outputs":[{"file":name,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)} for name,raw in files.items()],
        }
        (root/"simc_reference_receipt.json").write_text(json.dumps(r),encoding="utf-8")
        a=build(root,window_seconds=15.,expected_spec="fury")
        checks=[]
        def check(label,assertion):
            if not assertion:raise AssertionError(label)
            checks.append(label)
        check("precombat_is_distinct",a["precombat_observed_record_count"]==1)
        check("apl_precombat_count",a["precombat_action_list_rows"]==1)
        check("only_performed_not_queued",a["opener_observed_action_count"]==2)
        check("performed_actions",[x["action_token"] for x in a["opener_observed_actions"]]==["rampage","bloodthirst"])
        check("wait_not_cast",a["opener_wait_record_count"]==1)
        check("queued_not_cast",a["opener_queue_failed_record_count"]==1)
        check("post_opener_exact_boundary",a["post_window_observation_record_count"]==1)
        check("numeric_id_captured",a["opener_observed_actions"][0]["numeric_spell_id"]==184367)
        check("no_strict_pre_assumption",a["snapshot_state_is_not_strict_PRE"] is True)
        check("not_live_gameplay",a["actual_SimC_executable_capture"] is False)
        check("no_wcl_lock",a["WCL_independent_candidate_lock"]=="NOT_RUN")
        check("no_gameplay_promotion",a["ready_for_target_dummy_mistake_feedback"] is False)
        check("general_apl_operand","rage" in a["original_simc_APL_required_state_operands"])
        try:build(root,expected_spec="other")
        except ValueError as e:check("wrong_spec_rejected","SPEC_IDENTITY" in str(e))
        else:raise AssertionError("MISMATCHED_SPEC_ACCEPTED")
        try:build(root,window_seconds=0)
        except ValueError as e:check("bad_window_rejected","INVALID_OPENER" in str(e))
        else:raise AssertionError("INVALID_WINDOW_ACCEPTED")
        (root/"simc_native_sequence.json").write_bytes(files["simc_native_sequence.json"]+b" ")
        try:build(root)
        except ValueError as e:check("tamper_rejected","SHA_OR_SIZE_MISMATCH" in str(e))
        else:raise AssertionError("TAMPER_ACCEPTED")
    return {"result":"PASS","offline_case_count":len(checks),
            "actual_native_simc_run":"NOT_RUN_IN_SELFTEST",
            "WCL_replay":"NOT_RUN",
            "source_usage":"EXISTING_PINNED_JSON2_AND_APL_IR" }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--reference-dir",type=Path)
    ap.add_argument("--spec")
    ap.add_argument("--window-seconds",type=float,default=15.)
    ap.add_argument("--out",type=Path)
    x=ap.parse_args()
    if x.self_test or x.reference_dir is None:
        result=selftest()
    else:
        result=build(x.reference_dir,expected_spec=x.spec,window_seconds=x.window_seconds)
    out=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if x.out:
        x.out.parent.mkdir(parents=True,exist_ok=True)
        x.out.write_text(out,encoding="utf-8")
        print("WROTE_SIMC_NATIVE_OPENER_SAMPLE_CANDIDATE")
    else:print(out,end="")

if __name__=="__main__":
    main()
