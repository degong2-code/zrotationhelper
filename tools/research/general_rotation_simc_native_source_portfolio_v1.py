#!/usr/bin/env python3
"""Source-pinned portfolio of original Native *opening samples* and priority IR.

Merge immutable, separately run original-SimC 1/2/3/5-target source-token
samples from multiple classes without pretending they share a native binary,
a C++ selected source row, dynamic readiness, or an opening/steady boundary.

The original two-class grid remains untouched. A marginal third-class
capture is composed with it only if source Git blobs/row counts and cohort
boundaries independently reconcile. Reuses existing SimC source compiler.
No new parser, Native simulation, or WCL action candidate generation.

Zero-argument safe synthetic identity and open-world selftest.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import re

from simc_apl_semantic_ir_v2 import canonical,git_blob
from general_rotation_simc_multi_spec_cold_start_v1 import load_manifest
from general_rotation_simc_e2e_research_engine_v1 import compile_spec
from general_rotation_simc_native_target_grid_v1 import SCHEMA as TWO_CLASS_SCHEMA
from general_rotation_simc_marginal_native_cold_start_v1 import SCHEMA as MARGINAL_SCHEMA

SCHEMA="ZrotGeneralRotationMultiClassOriginalNativeOpeningSourcePortfolioV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
TARGETS=(1,2,3,5)
HEX64=re.compile(r"[a-f0-9]{64}\Z")

class PortfolioError(ValueError):pass

def need(ok:bool,msg:str):
    if not ok:raise PortfolioError(msg)

def validate_target_cases(rows:list,source_key:str)->dict:
    need(type(rows) is list and len(rows)==len(TARGETS),
         "NATIVE_FOUR_TARGET_CASES_REQUIRED")
    if [r.get("target_count") for r in rows]!=list(TARGETS):
        raise PortfolioError("NATIVE_TARGET_ORDER_OR_IDENTITY_DRIFT")
    total=0
    compact=[]
    for case in rows:
        count=case["target_count"]
        need(type(case.get("sample_actions")) is int and case["sample_actions"]>0 and
             type(case.get("first_10sec_sample_count")) is int and
             0<case["first_10sec_sample_count"]<=case["sample_actions"] and
             case.get("opener_termination_timestamp")=="UNKNOWN" and
             case.get("Native_full_competing_READY")=="UNKNOWN" and
             case.get("source_APL_row_attribution")=="UNKNOWN_MULTIPLE_POSSIBLE_ROWS" and
             type(case.get("source_token_match_sample_count")) is int and
             0<=case["source_token_match_sample_count"]<=case["sample_actions"] and
             type(case.get("first_10sec_sample_actions_NOT_opener_end")) is list and
             len(case["first_10sec_sample_actions_NOT_opener_end"])==
                 case["first_10sec_sample_count"],
             "SOURCE_NATIVE_SAMPLE_READINESS_OR_PHASE_NOT_VERIFIED")
        prev=-1
        observations=[]
        for action in case["first_10sec_sample_actions_NOT_opener_end"]:
            t=action.get("at_simc_ms")
            require_name=action.get("action")
            need(type(t) is int and 0<=t<10000 and t>=prev and
                 type(require_name) is str and bool(require_name) and
                 action.get("source_row_identity_certified") is False and
                 action.get("Native_full_competing_READY")=="UNKNOWN" and
                 action.get("same_timestamp_is_not_strict_PRE") is True and
                 type(action.get("candidate_APL_source_rows_NOT_SELECTED")) is list,
                 "OBSERVED_NATIVE_TOKEN_NOT_STRICT_SOURCE_ROW_PROOF")
            prev=t
            observations.append({
                "original_simc_ms":t,
                "native_action_token":require_name,
                "possible_original_APL_source_rows_NOT_SELECTED":
                    action["candidate_APL_source_rows_NOT_SELECTED"],
                "actual_original_APL_row_selected":"UNKNOWN",
                "full_physical_READY":"UNKNOWN"
            })
        total+=case["sample_actions"]
        compact.append({
            "source_spec_key":source_key,
            "targets":count,
            "actual_native_sample_actions":case["sample_actions"],
            "native_first_10s_samples_NOT_opener_end_count":
                case["first_10sec_sample_count"],
            "native_first_10s_actions_NOT_necessarily_opener":observations,
            "possible_original_row_token_match_count":
                case["source_token_match_sample_count"],
            "opener_to_general_phase_condition":"UNKNOWN",
            "first_10s_sample_window_is_NOT_phase_boundary":True,
            "original_cpp_source_row_attribution":"UNKNOWN",
            "competing_full_READY":"UNKNOWN"
        })
    return {"cases":compact,"total":total}

def compose(manifest:dict,profiles:dict[str,tuple[bytes,dict]],
            old:dict,new:dict,*,old_sha:str,new_sha:str)->dict:
    need(type(manifest) is dict and type(profiles) is dict and
         old.get("schema")==TWO_CLASS_SCHEMA and
         new.get("schema")==MARGINAL_SCHEMA and
         old.get("policy_id")==new.get("policy_id")==POLICY and
         old.get("official_simc_source_commit")==
         new.get("pinned_simc_source_revision")==
         manifest.get("official_simc_commit") and
         all(type(h) is str and HEX64.fullmatch(h)
             for h in (old_sha,new_sha)),
         "INCOMPATIBLE_OR_UNPINNED_DISTINCT_NATIVE_COHORTS")
    pins=manifest["profiles"]
    pin_by_key={p["key"]:p for p in pins}
    need(len(pin_by_key)==len(pins)==len(profiles) and
         old.get("target_counts")==new.get("original_native_target_counts")==
         list(TARGETS) and
         type(old.get("source_native_cases")) is list and
         type(new.get("native_target_cases")) is list and
         old.get("source_profiles")==len(old["source_native_cases"]) and
         new.get("source_manifest_total_profiles")==len(pins) and
         new.get("previous_other_class_native_captures_rerun")==0,
         "PROFILE_COHORT_MEMBERSHIP_OR_TARGET_SET_DRIFT")
    histories={}
    previous_bin=set()
    for spec in old["source_native_cases"]:
        key=spec.get("source_spec_key")
        need(type(key) is str and key in pin_by_key and
             key not in histories and
             spec.get("source_class_key")==pin_by_key[key]["class_key"] and
             spec.get("source_profile_git_blob_sha1")==pin_by_key[key]["git_blob"] and
             spec.get("same_native_build_apl_seed_and_fight_window") is True and
             type(spec.get("capture_control_fingerprint")) is dict and
             type(spec.get("comparisons_to_ST")) is list and
             len(spec["comparisons_to_ST"])==3,
             "ORIGINAL_TWO_CLASS_EVIDENCE_PROFILE_OR_CONTROL_TAMPER")
        history=spec["capture_control_fingerprint"]
        need(type(history.get("simc_executable_sha256")) is str and
             HEX64.fullmatch(history["simc_executable_sha256"]),
             "ORIGINAL_TWO_CLASS_NATIVE_EXECUTABLE_HASH_MISSING")
        previous_bin.add(history["simc_executable_sha256"])
        histories[key]={"target_cases":spec["target_cases"],
                        "control":history,
                        "claimed_source_rows":spec["source_APL_action_count"],
                        "is_marginal":False}
    key=new.get("new_actual_native_spec_key")
    need(type(key) is str and key in pin_by_key and key not in histories and
         new.get("new_actual_native_profile_git_blob")==pin_by_key[key]["git_blob"] and
         new.get("native_captures_same_binary_APL_and_seed") is True and
         type(new.get("native_capture_controls")) is dict and
         new.get("new_original_native_CXX_builds_expected")==1 and
         new.get("opener_end_condition")=="UNKNOWN" and
         new.get("full_competing_action_READY_proven")==0 and
         new.get("WCL_blind_candidate_semantics_injected") is False and
         new.get("current_retail_gameplay_optimality_proven") is False,
         "MARGINAL_NEW_SPEC_NOT_INDEPENDENT_OPEN_WORLD_SOURCE")
    histories[key]={"target_cases":new["native_target_cases"],
                    "control":new["native_capture_controls"],
                    "claimed_source_rows":new["new_original_profile_APL_rows"],
                    "is_marginal":True}
    need(set(histories)==set(pin_by_key) and
         len({x["class_key"] for x in pins})>=3,
         "INCOMPLETE_MULTI_CLASS_NATIVE_PORTFOLIO")
    outputs=[]
    for p in pins:
        raw,meta=profiles[p["key"]]
        need(git_blob(raw)==p["git_blob"] and
             meta.get("key")==p["key"] and
             meta.get("class_key")==p["class_key"],
             "SOURCE_PROFILE_BYTES_OR_PIN_DRIFT")
        src=compile_spec(raw,p,None)
        state=histories[p["key"]]
        need(src["source_APL_row_count"]==state["claimed_source_rows"],
             "ORIGINAL_SOURCE_VS_NATIVE_APL_ROW_COUNT_CONFLICT")
        compact=validate_target_cases(state["target_cases"],p["key"])
        program=src["conditioned_opener_and_priority"]
        root_controls=[{
            "source_rank":r["priority_rank_in_list"],
            "original_source_behavior":r["behavior"],
            "original_source_if":r["when_source_if"],
            "source_control_destination":r["source_control_destination"],
            "control_runtime_ready":"UNKNOWN",
            "destination_ACTUALLY_entered":"UNKNOWN"
        } for r in program["all_ordered_source_IF_ELSE_lists"]["default"]
             if r["behavior"] in ("CALL","RUN")]
        outputs.append({
            "spec_key":p["key"],
            "class_key":p["class_key"],
            "original_profile_git_blob":p["git_blob"],
            "original_APL_rows":src["source_APL_row_count"],
            "original_APL_list_count":
                len(program["all_ordered_source_IF_ELSE_lists"]),
            "original_root_CALL_RUN_guard_hypotheses":root_controls,
            "source_hypotheses_are_NOT_ACTUAL_ready_or_selection":True,
            "actual_native_source_token_opening_samples":compact["cases"],
            "native_sample_total":compact["total"],
            "sample_control_executable_sha256":
                state["control"]["simc_executable_sha256"],
            "same_executable_across_this_spec_targets_only":True,
            "native_cross_run_binary_identity":(
                "NOT_ASSUMED_EQUAL_TO_OTHER_COHORTS"),
            "original_selection_row_and_exact_PRE":"UNKNOWN",
            "opener_end_condition":"UNKNOWN",
            "conditional_gameplay_priority_proven":False,
            "was_new_profile_cold_start":state["is_marginal"]
        })
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "pinned_original_simc_revision":manifest["official_simc_commit"],
        "original_class_count":len({p["class_key"] for p in pins}),
        "original_profiles":len(outputs),
        "source_APL_rows":sum(x["original_APL_rows"] for x in outputs),
        "native_sample_target_count_cases":len(outputs)*len(TARGETS),
        "original_native_action_tokens_observed":sum(
            x["native_sample_total"] for x in outputs),
        "source_model_with_native_sample_cohort_boundaries":outputs,
        "source_input_SHA256":{
            "historical_two_class_derived_artifact":old_sha,
            "new_marginal_third_class_derived_artifact":new_sha},
        "original_research_runs_have_distinct_provenance":True,
        "original_selected_APL_rows_still_NOT_proven_from_tokens":True,
        "opener_exit_condition":"UNKNOWN",
        "full_simultaneously_READY_priorities_proven":0,
        "WCL_blind_candidate_semantics_injected":False,
        "actual_target_dummy_wrong_cast":"UNKNOWN",
        "new_Native_CXX_build_for_this_join":0,
        "new_WCL_API_calls":0,"MAIN_promoted":False
    }

def selftest()->dict:
    # The current portfolio is an open-world join. Incomplete cohorts and
    # fabricated source identity MUST fail rather than generate a model.
    try:compose({"official_simc_commit":"wrong","profiles":[]},{},
                {"schema":TWO_CLASS_SCHEMA,"policy_id":POLICY},
                {"schema":MARGINAL_SCHEMA,"policy_id":POLICY},
                old_sha="0"*64,new_sha="1"*64)
    except PortfolioError:pass
    else:raise AssertionError("FABRICATED_NATIVE_PORTFOLIO_ACCEPTED")
    try:validate_target_cases([], "fake")
    except PortfolioError:pass
    else:raise AssertionError("MISSING_NATIVE_TARGETS_ACCEPTED")
    return {
        "status":"PASS_OFFLINE_PORTFOLIO_FAIL_CLOSED",
        "negative_contracts":2,
        "new_native_CXX_builds":0,
        "physical_READY_proven":0,
        "opener_end_proven":False
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--historical-grid",type=Path)
    p.add_argument("--new-marginal",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    items=(a.source_root,a.manifest,a.historical_grid,a.new_marginal)
    if not any(items):
        result=selftest()
    else:
        if not all(items):p.error("source root, manifest, historical-grid and new-marginal required")
        source_root=a.source_root.resolve(strict=True)
        manifest=load_manifest(a.manifest)
        actual=subprocess.run(["git","-C",str(source_root),"rev-parse","HEAD"],
                 check=True,capture_output=True,text=True).stdout.strip()
        need(actual==manifest["official_simc_commit"],"SOURCE_REVISION_NOT_PINNED")
        profiles={}
        for row in manifest["profiles"]:
            path=(source_root/row["profile"]).resolve(strict=True)
            need(path.is_relative_to(source_root),"SOURCE_PATH_ESCAPE")
            profiles[row["key"]]=(path.read_bytes(),row)
        old_raw=a.historical_grid.read_bytes()
        new_raw=a.new_marginal.read_bytes()
        result=compose(
            manifest,profiles,json.loads(old_raw),json.loads(new_raw),
            old_sha=sha256(old_raw).hexdigest(),
            new_sha=sha256(new_raw).hexdigest()
        )
    encoded=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(encoded)
        print(json.dumps({"written":str(a.out),
                          "sha256":sha256(encoded).hexdigest(),
                          "bytes":len(encoded)}))
    else:print(encoded.decode(),end="")

if __name__=="__main__":main()
