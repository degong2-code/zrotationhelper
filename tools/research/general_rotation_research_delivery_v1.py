#!/usr/bin/env python3
"""Produce a trainer-facing *research* General Rotation IR from verified SimC E2E.

Does not reparse source or invent an opener. Uses the existing pinned
source-to-IF/ELSE program with actual original SimC source-return references.

This is NOT an addon execution rule set: every actual expected player action,
independent complete readiness, WCL causality and player mistake remains
UNKNOWN until authenticated *same-cohort* source and independent WCL evidence
justify promotion. Source-action returns include controls and non-casts.

Zero-argument mode runs synthetic checks; CLI accepts a *SHA-pinned* original
E2E JSON, so a bogus external JSON cannot be silently labeled official.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import canonical, git_blob
from general_rotation_simc_e2e_research_engine_v1 import (
    SCHEMA as INPUT_SCHEMA, POLICY, compile_spec
)

SCHEMA="ZrotGeneralRotationSourceEvidenceToTrainerResearchIRV1"
SPEC_SCHEMA="ZrotOneSpecSimCConditionalRotationResearchProgramV1"
NATIVE_CASE="ZrotOriginalNativeSourceReturnOpenerReferenceV1"
SHA=re.compile(r"^[0-9a-f]{64}$")


class DeliveryError(ValueError):pass


def require(x:bool,reason:str)->None:
    if not x:raise DeliveryError(reason)


def source_priority(rows:list[dict],*,list_name:str)->list[dict]:
    require(isinstance(rows,list) and all(isinstance(x,dict) for x in rows),
            "SOURCE_PRIORITY_ROWS_MISSING")
    result=[]
    for position,row in enumerate(rows,1):
        identity=row.get("identity",{})
        require(identity.get("source_list")==list_name and
                identity.get("source_index")==position-1 and
                row.get("priority_rank_in_list")==position and
                isinstance(identity.get("source_line"),int) and
                isinstance(identity.get("source_line_sha256"),str) and
                SHA.fullmatch(identity["source_line_sha256"]) is not None and
                row.get("independent_native_FULL_READY")=="UNKNOWN" and
                row.get("priority_is_local_to_source_list") is True and
                row.get("is_actual_WoW_player_spellcast")=="UNKNOWN",
                "SOURCE_ORDER_OR_READINESS_CLAIM_DRIFT")
        behavior=row["behavior"]
        require(behavior in ("ACTION","CALL","RUN","VARIABLE",
                            "SIDE_EFFECT_SOURCE_MODEL_UNVERIFIED",
                            "SWAP_UNSUPPORTED"),"SOURCE_BEHAVIOR_INVALID")
        require(row.get("when_source_if") is None or
                isinstance(row["when_source_if"],str),
                "SOURCE_IF_EXPRESSION_DRIFT")
        transfer=row.get("on_guard_true_and_native_ready")
        if behavior=="RUN":
            require(transfer=="QUEUE_RUN_CONTROL_THEN_NEXT_SELECTION_IN_DESTINATION",
                    "RUN_LIST_QUEUE_SEMANTICS_LOST")
        if behavior=="CALL":
            require(transfer=="CALL_CHILD_LIST_AND_RESUME_IF_NO_ACTION",
                    "CALL_LIST_FALLBACK_SEMANTICS_LOST")
        result.append({
            "rank_in_source_list":position,
            "action":row["action"],
            "kind":behavior,
            "when_source_IF":row["when_source_if"],
            "required_observation_symbols":
                sorted({s for names in row["condition_operands"].values()
                        for s in names}),
            "source_line":identity["source_line"],
            "source_row_sha256":identity["source_line_sha256"],
            "source_control_destination":row.get("source_control_destination"),
            "control_or_action_effect":transfer,
            "higher_source_priority_row_count":position-1,
            "source_when_true_and_READY":"CANDIDATE_NOT_PROVEN_READY",
            "source_when_false":"TRY_NEXT_ROW",
            "source_when_unknown":"UNKNOWN_DO_NOT_SKIP",
            "independent_native_READINESS":"UNKNOWN",
            "expected_player_skill":"UNKNOWN",
            "source_rank_is_not_optimality_proof":True,
        })
    return result


def summarize_case(case:dict,program:dict,*,spec_key:str)->dict:
    require(isinstance(case,dict) and case.get("schema")==NATIVE_CASE and
            case.get("source_profile_key")==spec_key and
            type(case.get("target_count")) is int and
            1<=case["target_count"]<=40 and
            type(case.get("research_sample_window_ms_NOT_opener_end")) is int,
            "SOURCE_NATIVE_CASE_NOT_PINNED")
    all_rows=case.get("all_original_CPP_source_return_actions")
    early=case.get("opener_window_original_CPP_returns")
    require(isinstance(all_rows,list) and len(all_rows)>0 and
            isinstance(early,list) and
            len(all_rows)==case.get("original_CPP_source_returned_actions_all") and
            case.get("actual_WoW_cast_sequence")=="UNKNOWN" and
            case.get("opener_termination_rule")=="UNKNOWN" and
            case.get("independently_complete_FULL_READY_proven")==0 and
            case.get("WCL_holdout_result")=="NOT_RUN" and
            case.get("practical_dummy_error_feedback_permitted") is False,
            "SOURCE_CHOICE_VS_PLAYER_CAST_CONTRACT_CHANGED")
    expected_early=[];last=-1;hist=Counter();missing=Counter()
    for i,source in enumerate(all_rows,1):
        name=source.get("source_list")
        rank=source.get("source_priority_rank")
        t=source.get("at_simc_ms")
        require(name in program and type(rank) is int and
                1<=rank<=len(program[name]) and
                source.get("original_CPP_choice_index")==i and
                type(t) is int and t>=last and
                source.get("target_count")==case["target_count"] and
                source.get("source_line_sha256")==
                   program[name][rank-1]["source_row_sha256"] and
                source.get("action")==program[name][rank-1]["action"] and
                source.get("source_behavior")==program[name][rank-1]["kind"] and
                source.get("is_performed_player_cast") is False and
                source.get("is_user_rotation_recommendation") is False and
                source.get("native_return_NOT_independent_FULL_READY") is True,
                "SOURCE_NATIVE_ROOT_CHOICE_AND_PRIORITY_LINE_NOT_SAME")
        last=t
        hist[source["source_behavior"]]+=1
        missing.update(source.get("source_IF_unobserved_operands",[]))
        if t<=case["research_sample_window_ms_NOT_opener_end"]:
            expected_early.append(source)
    require(len(expected_early)==len(early) and
            [x["original_CPP_choice_index"] for x in expected_early] ==
            [x["original_CPP_choice_index"] for x in early],
            "EARLY_SAMPLE_IS_NOT_EXACT_PREFIX_OF_ALL_SOURCE_RETURNS")
    # These are actual original C++ returns, but control rows are NOT casts.
    observed_preview=[]
    for x in early[:12]:
        observed_preview.append({
            "at_simc_ms":x["at_simc_ms"],
            "source_list":x["source_list"],
            "source_priority_rank":x["source_priority_rank"],
            "source_row_sha256":x["source_line_sha256"],
            "source_action":x["action"],
            "kind":x["source_behavior"],
            "source_IF_status":x["source_IF_status"],
            "unobserved_IF_symbols":x["source_IF_unobserved_operands"],
            "native_selected_source_action":True,
            "proven_player_cast":False,
            "independently_available_for_player":"UNKNOWN"
        })
    return {
        "case":case["case"],
        "targets_as_original_SimC_PRE":case["target_count"],
        "source_selection_count":len(all_rows),
        "source_selection_behavior_counts":dict(sorted(hist.items())),
        "initial_selection_window_ms_research_only":
            case["research_sample_window_ms_NOT_opener_end"],
        "initial_source_selection_count":len(early),
        "first_source_returns_not_first_casts":observed_preview,
        "missing_IF_state_symbols_by_occurrence":dict(sorted(
            missing.items(),key=lambda x:(-x[1],x[0]))),
        "source_selected_run_control_is_not_spell_cast":True,
        "actual_first_player_damage_cast":"UNKNOWN",
        "canonical_opener_cast_sequence":"UNKNOWN",
        "opener_end_transition":"UNKNOWN",
        "same_time_competing_action_readiness":"UNKNOWN",
        "independent_WCL_candidate_lock":"NOT_RUN",
        "independent_WCL_holdout":"NOT_RUN",
        "dummy_mistake_verdict":"UNKNOWN"
    }


def build(input_doc:dict,*,input_sha256:str)->dict:
    require(SHA.fullmatch(input_sha256) is not None,
            "SOURCE_INPUT_SHA256_REQUIRED")
    require(isinstance(input_doc,dict) and
            input_doc.get("schema")==INPUT_SCHEMA and
            input_doc.get("product_policy_id")==POLICY and
            isinstance(input_doc.get("models"),list) and
            len(input_doc["models"])>=2 and
            input_doc.get("source_to_conditional_graph_E2E_complete_for_pinned_profiles") is True and
            input_doc.get("full_dynamic_ready_state_and_global_optimality")=="UNKNOWN" and
            input_doc.get("WCL_blind_candidate_semantics_injected") is False and
            input_doc.get("WCL_holdout_completed") is False and
            input_doc.get("trainer_mistake_verdict")=="UNKNOWN",
            "UPSTREAM_SOURCE_E2E_AUTHORITY_OR_SCOPE_DRIFT")
    require(type(input_doc.get("native_reference_cases")) is int and
            type(input_doc.get("source_APL_rows_compiled")) is int,
            "UPSTREAM_SOURCE_COUNTS_NOT_TYPED")
    compiled=[];total_rows=0;source_returns=0;cases=0
    seen_spec=set();classes=set()
    for spec in input_doc["models"]:
        require(spec.get("schema")==SPEC_SCHEMA and
                spec.get("product_policy_id")==POLICY and
                spec.get("simultaneously_available_physical_priority_proven") is False and
                spec.get("opener_first_actual_player_cast")=="UNKNOWN" and
                spec.get("WCL_independent_holdout")=="NOT_RUN" and
                spec.get("user_target_dummy_error_verdict")=="UNKNOWN",
                "SPEC_PROGRAM_ALREADY_PROMOTED_OR_DRIFTED")
        key=spec.get("source_spec_key")
        clazz=spec.get("source_class_key")
        blob=spec.get("source_profile_git_blob_sha1")
        require(isinstance(key,str) and key and
                key not in seen_spec and isinstance(clazz,str) and clazz and
                isinstance(blob,str) and re.fullmatch("[0-9a-f]{40}",blob),
                "SPEC_IDENTITY_DUPLICATE_OR_UNPINNED")
        seen_spec.add(key);classes.add(clazz)
        raw_lists=spec["conditioned_opener_and_priority"]["all_ordered_source_IF_ELSE_lists"]
        require(isinstance(raw_lists,dict) and "default" in raw_lists and
                "precombat" in raw_lists,"PRECOMBAT_AND_DEFAULT_SOURCE_REQUIRED")
        lists={name:source_priority(rows,list_name=name)
               for name,rows in raw_lists.items()}
        source_rows=sum(len(rows) for rows in lists.values())
        require(source_rows==spec["source_APL_row_count"],
                "SOURCE_ROWS_MISSING_IN_DELIVERY")
        total_rows+=source_rows
        scenarios=spec["simc_native_observed_source_selection_cases"]
        result_cases={}
        for case in sorted(scenarios):
            result_cases[case]=summarize_case(scenarios[case],lists,
                                             spec_key=key)
            source_returns+=result_cases[case]["source_selection_count"]
            cases+=1
        # Never flatten RUN into a synchronous spell selection. Precombat
        # source list is a preparation declaration, not proof of actual casts.
        compiled.append({
            "source_spec_key":key,"source_class_key":clazz,
            "source_profile_git_blob_sha1":blob,
            "precombat_source_priority_not_observed_casts":
                lists["precombat"],
            "opener_source_hypothesis":{
                "early_source_priority_program":lists,
                "actual_opener_cast_order":"UNKNOWN",
                "opener_end_signal":"UNKNOWN",
                "initial_window_is_only_source_return_sample":True},
            "post_opener_IF_ELSE_priority":{
                "lists":lists,
                "entry_list":"default",
                "branch_control_structure":
                    spec["conditioned_opener_and_priority"]["source_list_call_graph"],
                "source_order_if_simultaneously_ready":"HYPOTHESIS_ONLY",
                "post_opener_specific_time_gate":"UNKNOWN"},
            "target_count_source_comparisons_not_verified_breakpoints":
                spec["conditioned_opener_and_priority"][
                    "target_count_source_comparisons_not_actual_breakpoints"],
            "observed_original_SimC_selection_cases":result_cases,
            "readiness_and_competitors":"UNKNOWN",
            "confidence":"PINNED_SIMC_APL_SOURCE_HYPOTHESIS_NOT_WCL_VALIDATED",
            "native_cpp_selection_is_not_player_cast":True,
            "WCL_blind_discovery_MUST_NOT_READ_this_model":True,
            "user_practice_expected_action":"UNKNOWN",
            "dummy_practice_mistake_verdict":"UNKNOWN",
        })
    require(len(classes)>=2 and
            total_rows==input_doc["source_APL_rows_compiled"] and
            source_returns==input_doc["original_cpp_selected_source_actions_bound"] and
            cases==input_doc["native_reference_cases"],
            "MULTISPEC_SOURCE_COHORT_ROW_COVERAGE_OR_COUNT_DRIFT")
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "original_source_E2E_input_sha256":input_sha256,
        "source_model_count":len(compiled),
        "distinct_classes":len(classes),
        "source_IF_ELSE_rows":total_rows,
        "original_SimC_source_returns_not_player_casts":source_returns,
        "source_target_case_count":cases,
        "research_models":compiled,
        "WCL_discovery_procedure":"RAW_NUMERIC_BLIND_CANDIDATE_LOCK_BEFORE_SIMC_COMPARISON",
        "WCL_holdout_rule":"DISJOINT_INDEPENDENT_AFTER_CANDIDATE_THRESHOLD_LOCK",
        "product_expected_casts_verified":0,
        "complete_READY_proven":0,
        "dummy_wrong_action_flags":0,
        "source_only_GENERAL_ROTATION_RESEARCH_NOT_READY_FOR_DUMMY":True,
        "WCL_API_calls":0,"WoW_addon_calls":0,
        "MAIN_promoted":False
    }


def selftest()->dict:
    from general_rotation_simc_e2e_research_engine_v1 import compile_spec
    from simc_apl_semantic_ir_v2 import git_blob
    # Source test does not know or require real specialization names.
    inputs=[]
    for spec,cls,spell,if_expr in (
        ("synthetic_one","unrelated_a","alpha","resource>=1"),
        ("synthetic_two","unrelated_b","beta","aura.x.up")):
        raw=("actions.precombat=prep\n"
             "actions=run_action_list,name=branch,if=active_enemies=1\n"
             "actions+=/fallback\n"
             "actions.branch="+spell+",if="+if_expr+"\n").encode()
        meta={"key":spec,"class_key":cls,"git_blob":git_blob(raw)}
        inputs.append(compile_spec(raw,meta,None))
    obj={
        "schema":INPUT_SCHEMA,"product_policy_id":POLICY,
        "models":inputs,"native_reference_cases":0,
        "source_APL_rows_compiled":8,
        "original_cpp_selected_source_actions_bound":0,
        "source_to_conditional_graph_E2E_complete_for_pinned_profiles":True,
        "full_dynamic_ready_state_and_global_optimality":"UNKNOWN",
        "WCL_blind_candidate_semantics_injected":False,
        "WCL_holdout_completed":False,
        "trainer_mistake_verdict":"UNKNOWN",
    }
    out=build(obj,input_sha256="0"*64)
    assert out["source_model_count"]==2 and out["source_IF_ELSE_rows"]==8
    assert out["source_target_case_count"]==0
    for x in out["research_models"]:
        assert x["opener_source_hypothesis"]["actual_opener_cast_order"]=="UNKNOWN"
        assert x["post_opener_IF_ELSE_priority"]["lists"]["branch"][0]["source_when_unknown"]=="UNKNOWN_DO_NOT_SKIP"
        assert x["post_opener_IF_ELSE_priority"]["lists"]["default"][0]["control_or_action_effect"]=="QUEUE_RUN_CONTROL_THEN_NEXT_SELECTION_IN_DESTINATION"
        assert x["dummy_practice_mistake_verdict"]=="UNKNOWN"
    # A forged readiness or cast report cannot be promoted by ingestion.
    contaminated=json.loads(json.dumps(obj))
    contaminated["models"][0]["opener_first_actual_player_cast"]="alpha"
    try:build(contaminated,input_sha256="0"*64)
    except DeliveryError:pass
    else:raise AssertionError("FAKE_OPENER_CAST_GOT_PROMOTED")
    contaminated=json.loads(json.dumps(obj))
    contaminated["models"][0]["conditioned_opener_and_priority"]["all_ordered_source_IF_ELSE_lists"]["branch"][0]["independent_native_FULL_READY"]="READY"
    try:build(contaminated,input_sha256="0"*64)
    except DeliveryError:pass
    else:raise AssertionError("FAKE_READY_GOT_PROMOTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":16,"specializations_unrelated":2,
            "generic_core_has_no_class_or_spell_branches":True,
            "independent_full_READY_proven":0,
            "WCL_API_calls":0}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-e2e",type=Path)
    p.add_argument("--expected-sha256")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.source_e2e is None:
        if a.expected_sha256 or a.out:
            p.error("source-e2e required with expected sha and output")
        print(json.dumps(selftest(),sort_keys=True))
        return
    require(a.expected_sha256 and SHA.fullmatch(a.expected_sha256) is not None
            and a.out is not None,
            "PINNED_SOURCE_INPUT_SHA_AND_OUT_REQUIRED")
    original=a.source_e2e.read_bytes()
    require(sha256(original).hexdigest()==a.expected_sha256,
            "ORIGINAL_SOURCE_E2E_RAW_BYTES_NOT_PINNED")
    r=build(json.loads(original),input_sha256=a.expected_sha256)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as out:
        out.write(canonical(r))
    print("ZROT_GENERAL_ROTATION_DELIVERY_RESEARCH_IR_SHA256="+
          sha256(a.out.read_bytes()).hexdigest())


if __name__=="__main__":
    main()
