#!/usr/bin/env python3
"""Hekili-informed, original Native SimC-bound General Rotation opener view.

Combines three EXISTING source-derived layers (not a new competing parser):
* Core/decision: exact source-return choice & per-prior reason ledger.
* Scripts: original APL source IF string -> existing typed SimC Expression AST.
* State: actual selection timestamps + source-root PRE observability, with an
  isolated synthetic-only state transition test, never a made-up future state.

No new game addon, current-season optimum, WCL oracle, or validated READY.
The original return artefact deliberately has 16 detailed root choices/case;
198 unsampled source choices are NOT backfilled.
Without CLI arguments: safe, zero-network synthetic regression.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any

from simc_apl_semantic_ir_v2 import Expression, ast_symbols, evaluate_ast, truth
from general_rotation_source_hypothesis_ir_v1 import source_contexts
from general_rotation_source_decision_reason_ledger_v1 import (
    SUMMARY as REASON_SUMMARY, SCHEMA as REASON_SCHEMA, PRODUCT as POLICY,
    CASES
)
from general_rotation_root_actor_pre_replay_v1 import SCHEMA as ROOT_PRE_SCHEMA

SCHEMA = "ZrotIntegratedHekiliInformedNativeOpenerResearchV1"
SYNTHETIC = "ZrotOfflineStateSyntheticTransitionContractV1"
PROFILE = re.compile(r"[0-9a-f]{40}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
KINDS = {
    "run_action_list": "SOURCE_RUN_LIST_CONTROL_NOT_PLAYER_CAST",
    "call_action_list": "SOURCE_CALL_LIST_CONTROL_NOT_PLAYER_CAST",
    "swap_action_list": "SOURCE_SWAP_LIST_CONTROL_NOT_PLAYER_CAST",
    "variable": "SOURCE_VARIABLE_SIDE_EFFECT_NOT_PLAYER_CAST",
    "auto_attack": "SOURCE_AUTO_ATTACK_SETUP_NOT_PLAYER_CAST_PROOF",
    "potion": "SOURCE_CONSUMABLE_NOT_PLAYER_DAMAGE_SKILL",
    "use_item": "SOURCE_ITEM_USE_NOT_PLAYER_DAMAGE_SKILL",
    "use_items": "SOURCE_ITEMS_LIST_CONTROL_NOT_PLAYER_DAMAGE_SKILL",
    "snapshot_stats": "SOURCE_SNAPSHOT_SIDE_EFFECT_NOT_PLAYER_CAST",
}
ALLOWED_REASONS = frozenset((
    "SOURCE_IF_FALSE_INDEPENDENT_PRE_PROVEN",
    "NATIVE_READY_FALSE_POST_ONLY",
    "SOURCE_CONTROL_TRUE_CONTINUED_OR_NESTED",
    "SOURCE_BACKGROUND_SKIP",
    "WAIT_BREAK_NOT_ACTION_READINESS",
    "EARLIER_NATIVE_TRUE_UNRESOLVED_NO_NOT_READY_CLAIM",
))
class OpenerIntegrationError(ValueError):
    pass

def require(good:bool,label:str)->None:
    if not good:raise OpenerIntegrationError(label)

def finite(value:Any)->bool:
    return type(value) in (int,float) and math.isfinite(value)

def simulate_synthetic_state(state:dict,delta:dict)->dict:
    """A **synthetic-only** deterministic state effect example.

    Physical spell mechanics are never derived from name/observed casts.
    All effects require explicit caller-owned source & time, and their
    simulated values must not be used as actual Strict PRE facts.
    """
    require(state.get("schema")==SYNTHETIC and state.get("mode")=="SYNTHETIC_ONLY",
            "LIVE_DATA_CANNOT_ENTER_SYNTHETIC_STATE_ENGINE")
    require(delta.get("provenance")=="EXPLICIT_SYNTHETIC_FIXTURE" and
            type(delta.get("at_ms")) is int and delta["at_ms"]>state["at_ms"] and
            isinstance(delta.get("add"),dict),
            "EXPLICIT_VALIDATED_STATE_DELTA_REQUIRED")
    out=copy.deepcopy(state)
    for symbol,amount in delta["add"].items():
        require(isinstance(symbol,str) and symbol and finite(amount),
                "MALFORMED_STATE_EFFECT")
        before=out["facts"].get(symbol)
        if before is None:
            out["facts"][symbol]=None  # Missing state cannot become known.
        else:
            require(finite(before),"INVALID_PRIOR_SYNTHETIC_FACT")
            now=before+amount
            require(finite(now),"NONFINITE_SYNTHETIC_FORECAST")
            out["facts"][symbol]=now
    out["at_ms"]=delta["at_ms"]
    out["model_provenance"]="SYNTHETIC_COUNTERFACTUAL_NOT_WOW_OBSERVATION"
    return out

def _condition_for_source_row(row:dict|None, chosen:dict)->dict:
    if row is None:
        return {
            "source_IF":"UNKNOWN_NOT_RETAINED",
            "condition":"UNKNOWN",
            "unobserved_operands":[],
            "source_IF_row_identity_proven":False,
            "source_IF_state_at_choice_independently_reconstructed":False}
    require(row.get("source_action")==chosen["source_action"],
            "SOURCE_PRE_CONDITION_ACTION_IDENTITY_DRIFT")
    cond=row.get("source_if")
    if cond is None:
        return {
            "source_IF":None,"condition":"NO_EXPLICIT_SOURCE_IF",
            "unobserved_operands":[],
            "source_IF_row_identity_proven":True,
            "source_IF_state_at_choice_independently_reconstructed":False}
    require(isinstance(cond,str) and bool(cond),"SOURCE_IF_MUST_BE_NONEMPTY")
    ast=Expression(cond).parse()
    symbols=sorted(ast_symbols(ast))
    # In aggregate root-PRE receipts, an IF from an identical source line
    # might belong to a DIFFERENT attempt. Never infer values or a true IF
    # at the selected action's time from a row-aggregate or Native success.
    literal=truth(evaluate_ast(ast,{}))
    only_source_literals=not symbols
    return {
        "source_IF":cond,
        "condition":("SOURCE_LITERAL_"+("TRUE" if literal else "FALSE")
                     if only_source_literals and literal is not None
                     else "UNKNOWN_MISSING_EXACT_SELECTED_ROOT_FACTS"),
        "unobserved_operands":[
            {"symbol":s,"semantic_group":source_contexts(s),
             "state_at_choice":"UNKNOWN"} for s in symbols],
        "source_IF_row_identity_proven":True,
        "source_IF_state_at_choice_independently_reconstructed":False,
        "source_condition_evidence":"SOURCE_ROW_AGGREGATE_NOT_EXACT_CHOSEN_ROOT",
    }

def compose(reason:dict, original_actor_pre:dict[str,dict])->dict:
    require(reason.get("schema")==REASON_SUMMARY and
            reason.get("product_policy_id")==POLICY and
            reason.get("complete_positive_READY")==0 and
            reason.get("trainer_error_feedback_permitted") is False and
            reason.get("original_cases")==list(CASES),
            "REASON_PROOF_MODEL_OR_POLICY_INVALID")
    cases=reason.get("cases")
    require(isinstance(cases,dict) and set(cases)==set(CASES) and
            set(original_actor_pre)==set(CASES),
            "EXACT_FOUR_ACTUAL_SOURCE_CASES_REQUIRED")
    output={}
    count=Counter()
    for name in CASES:
        ledger=cases[name]
        pre=original_actor_pre[name]
        target=1 if name.endswith("-st") else 2
        blob=ledger.get("source_profile_git_blob_sha1")
        require(ledger.get("schema")==REASON_SCHEMA and
                ledger.get("product_policy_id")==POLICY and
                type(ledger.get("target_count")) is int and
                ledger["target_count"]==target and
                isinstance(blob,str) and PROFILE.fullmatch(blob) is not None and
                pre.get("schema")==ROOT_PRE_SCHEMA and
                pre.get("source_profile_git_blob_sha1")==blob and
                pre.get("source_actor_PRE_operand")=="active_enemies" and
                pre.get("full_READY_proven")==0 and
                pre.get("dummy_error_permitted") is False,
                "SOURCE_PRE_OR_LEDGER_CAUSAL_PROVENANCE_MISMATCH")
        rows=pre.get("by_source_row_sha256")
        require(isinstance(rows,dict),"ORIGINAL_ACTOR_SOURCE_ROWS_REQUIRED")
        selections=ledger.get("decisions")
        require(isinstance(selections,list) and len(selections)==16 and
                ledger.get("root_chosen_return_examples_with_full_prior_event_stream")==16 and
                ledger.get("source_order_complete") is False and
                ledger.get("independent_FULL_READY_proven")==0 and
                ledger.get("independent_entire_candidate_NOT_READY_proven")==0 and
                ledger.get("user_dummy_error_verdict_permitted") is False,
                "ORIGINAL_SELECTED_RECEIPT_CONTRACT_MISMATCH")
        results=[]
        last_t=-1
        last_id=-1
        for sequence,decision in enumerate(selections,1):
            t=decision.get("at_simc_ms")
            sid=decision.get("top_level_sweep_id")
            chosen=decision.get("selected_original_source")
            require(type(t) is int and t>=last_t and type(sid) is int and
                    sid>last_id and isinstance(chosen,dict) and
                    chosen.get("original_cxx_return_observed") is True and
                    chosen.get("independently_FULL_READY")=="UNKNOWN",
                    "INVALID_OR_NONMONOTONIC_NATIVE_RETURN_SOURCE_EVENT")
            last_t=t;last_id=sid
            action=chosen.get("source_action")
            hashvalue=chosen.get("source_row_sha256")
            require(isinstance(action,str) and action and
                    isinstance(hashvalue,str) and HASH.fullmatch(hashvalue) is not None,
                    "NATIVE_SOURCE_ACTION_HASH_MISSING")
            priors=decision.get("prior_candidate_evidence")
            require(isinstance(priors,list) and
                    all(x.get("reason_code") in ALLOWED_REASONS and
                        x.get("candidate_independently_FULL_NOT_READY") is False
                        for x in priors),
                    "SOURCE_REASON_NOT_EXPLICITLY_EVIDENCED")
            ifdetails=_condition_for_source_row(rows.get(hashvalue),chosen)
            action_kind=KINDS.get(
                action,"SOURCE_ACTION_POTENTIALLY_EXECUTABLE_NOT_PROVEN_SPELL_CAST")
            count[action_kind]+=1
            result={
                "ordinal_in_retained_original_return_stream":sequence,
                "simc_ms":t,
                "original_cpp_top_sweep_id":sid,
                "source_list":chosen.get("source_list"),
                "source_row_ordinal":chosen.get("source_ordinal"),
                "source_action":action,
                "source_row_sha256":hashvalue,
                "source_original_return_kind":chosen.get("return_kind"),
                "source_native_observed_choice":True,
                "source_action_kind":action_kind,
                "observed_native_CXX_return_not_user_cast":True,
                "source_row_condition":ifdetails,
                "source_reason_counts":dict(sorted(Counter(
                    x["reason_code"] for x in priors).items())),
                "rejected_candidate_count_in_current_source_sweep":len(priors),
                "independent_IF_false_on_prior_controls_only":sum(
                    x["reason_code"]=="SOURCE_IF_FALSE_INDEPENDENT_PRE_PROVEN"
                    for x in priors),
                "own_spell_cast_observed":False,
                "full_action_READY_proven":False,
                "full_prior_skill_NOT_READY_proven":False,
                "predicted_actual_next_state":{
                    "status":"UNKNOWN_UNVALIDATED_SPELL_EFFECT_AND_EVENT_ORDER",
                    "resource":"UNKNOWN","buff":"UNKNOWN",
                    "cooldown":"UNKNOWN","target_state":"UNKNOWN"},
                "feedback_verdict":"UNKNOWN",
            }
            results.append(result)
        require(results[0]["simc_ms"]==0,
                "NO_ZERO_TIME_NATIVE_SOURCE_OPENER_ANCHOR")
        output[name]={
            "source_profile_git_blob_sha1":blob,
            "target_count_scenario":target,
            "observation_kind":"ORIGINAL_SOURCE_NATIVE_SELECT_RETURN_SAMPLES",
            "original_sweep_count":ledger["original_all_sweeps_reused"],
            "all_top_level_native_source_returns":ledger[
                "actual_top_level_choices_in_original_run"],
            "retained_root_selected_source_steps":len(results),
            "unretained_root_source_returns":ledger[
                "root_chosen_return_examples_not_retained"],
            "first_return_at_ms":results[0]["simc_ms"],
            "last_retained_return_at_ms":results[-1]["simc_ms"],
            "timeline":results,
            "opener_optimality_proven":False,
            "full_native_state_transition_parity_proven":False,
            "independent_full_action_READY_proven":0,
        }
    require(sum(c["original_sweep_count"] for c in output.values())==
            reason["aggregate"]["all_original_sweeps"]==2121 and
            sum(c["retained_root_selected_source_steps"] for c in output.values())==64 and
            sum(c["unretained_root_source_returns"] for c in output.values())==198,
            "CROSS_CASE_NATIVE_SOURCE_COHORT_COUNTS_DRIFT")
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "architecture_boundary":{
            "source_condition_parser":"EXISTING_SIMC_APL_TYPED_AST",
            "source_decision_reasons":"EXISTING_ORIGINAL_CXX_REASON_LEDGER",
            "state_snapshot":"EXPLICIT_ORIGINAL_NATIVE_TIMESTAMP_AND_TARGET_SCENARIO",
            "state_transition":"NOT_SIMULATED_WITHOUT_VERIFIED_EFFECTS",
            "spec_adapter":"DEFERRED_MECHANIC_MAPPING_NO_CLASS_HARDCODE",
            "addon_mode":"OFFLINE_RESEARCH_NO_IN_GAME_DECISION_ENGINE",
            "inspiration":"HEKILI_CORE_SCRIPTS_STATE_CLASSES_BUT_NOT_LIVE_SOURCE_PORT"
        },
        "cases":output,
        "aggregate":{
            "native_cpp_sweep_records_reused":2121,
            "retained_source_opener_steps":64,
            "original_unretained_source_returns":198,
            "selected_source_action_kinds":dict(sorted(count.items())),
        },
        "authoritative_cast_sequence":False,
        "source_opener_hypothesis_baseline_only":True,
        "native_selection_is_not_independent_ready":True,
        "current_WCL_blind_validation_performed":False,
        "trained_dummy_error_permitted":False,
        "WCL_API_calls":0,
    }

def selftest()->dict:
    state={"schema":SYNTHETIC,"mode":"SYNTHETIC_ONLY",
           "at_ms":0,"facts":{"mana.pct":70.0,"buff.example.up":None}}
    out=simulate_synthetic_state(state,{
        "provenance":"EXPLICIT_SYNTHETIC_FIXTURE",
        "at_ms":1500,"add":{"mana.pct":-15,"buff.example.up":1}})
    assert out["facts"]=={"mana.pct":55.0,"buff.example.up":None}
    assert state["facts"]=={"mana.pct":70.0,"buff.example.up":None}
    assert out["model_provenance"]=="SYNTHETIC_COUNTERFACTUAL_NOT_WOW_OBSERVATION"
    for bad in (
        ({"schema":SYNTHETIC,"mode":"REAL_OBSERVED","at_ms":0,"facts":{}},
         {"provenance":"EXPLICIT_SYNTHETIC_FIXTURE","at_ms":1,"add":{}}),
        (state,{"provenance":"NATIVE_POST","at_ms":1,"add":{"mana.pct":1}}),
        (state,{"provenance":"EXPLICIT_SYNTHETIC_FIXTURE","at_ms":0,"add":{}}),
        (state,{"provenance":"EXPLICIT_SYNTHETIC_FIXTURE","at_ms":1,
                "add":{"mana.pct":float("nan")}}),
    ):
        try:simulate_synthetic_state(*bad)
        except OpenerIntegrationError:pass
        else:raise AssertionError("UNVERIFIED_FORECAST_ACCEPTED")
    assert _condition_for_source_row(None,{"source_action":"spell"})["condition"]=="UNKNOWN"
    cond=_condition_for_source_row({"source_action":"spell","source_if":"active_enemies=2"},
                                   {"source_action":"spell"})
    assert cond["condition"]=="UNKNOWN_MISSING_EXACT_SELECTED_ROOT_FACTS"
    assert cond["unobserved_operands"][0]["symbol"]=="active_enemies"
    assert _condition_for_source_row({"source_action":"spell","source_if":"1"},
                                    {"source_action":"spell"})["condition"]=="SOURCE_LITERAL_TRUE"
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":10,"current_wow_client_run":False,
            "native_CXX_rebuilt":False,"WCL_API_calls":0}

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reason-json",type=Path)
    p.add_argument("--original-native-receipts-dir",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.reason_json is None and a.original_native_receipts_dir is None:
        obj=selftest()
    elif a.reason_json is None or a.original_native_receipts_dir is None:
        p.error("both existing original-source receipts and reason JSON required")
    else:
        reason=json.loads(a.reason_json.read_bytes())
        before={}
        for case in CASES:
            file=a.original_native_receipts_dir/(
                "zrot-original-root-actor-pre-"+case+".json")
            before[case]=json.loads(file.read_bytes())
        obj=compose(reason,before)
    encoded=(json.dumps(obj,sort_keys=True,separators=(",",":"),
                        ensure_ascii=False,allow_nan=False)+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(encoded)
    else:
        import sys
        sys.stdout.buffer.write(encoded)

if __name__=="__main__":main()
