#!/usr/bin/env python3
"""Minimal next PRE capture requirements for exact original SimC emitted APL rows.

Consumes SAME-RUN original SimC JSON2 source row evidence. Classifies source
IF symbol dependencies with the existing SimC APL expression AST. Emits an
ordered *unobserved* capture frontier by case (spec, target_count, emitted
action/row identity) so a future original selection-time PRE producer can
capture only material missing values.

An emitted action at time t is NOT an original action_ready call at t; a
source IF expression is NOT proof of IF truth, READY, or priority. Original
PRE from DIFFERENT SimC runs must NEVER be joined by timestamp/name.

Default behavior for PyCharm: synthetic self-test, no network.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

from general_rotation_native_sequence_row_replay_v1 import SCHEMA as INPUT_SCHEMA
from general_rotation_simc_native_cast_delivery_v1 import POLICY
from simc_apl_semantic_ir_v2 import Expression, AplError, ast_symbols, canonical

SCHEMA="ZrotGeneralRotationExactAPLSourceIFDecisionPRECaptureFrontierV1"
HEX64=re.compile(r"^[a-f0-9]{64}$")
STATUSES={
    "SOURCE_EXACT_IF_OPERANDS_UNOBSERVED",
    "SOURCE_EXACT_NO_EXPLICIT_IF_NOT_READY_PROOF",
    "SOURCE_EXACT_CONSTANT_IF_NOT_SOURCE_READY_PROOF",
    "UNKNOWN_UNMAPPED_SOURCE_ROW",
    "UNKNOWN_UNPARSEABLE_SOURCE_IF",
}
NO_IF="SOURCE_EXACT_NO_EXPLICIT_IF_NOT_READY_PROOF"
WAIT="WAIT_NON_ACTION_NOT_SOURCE_ROW"


class CaptureFrontierError(ValueError): pass


def require(ok:bool,reason:str)->None:
    if not ok: raise CaptureFrontierError(reason)


def inspect_one(row:dict)->dict:
    """Ast dependency inventory, not action-time IF evaluation."""
    require(row.get("same_object_signatures_paired_to_JSON2_ordinal") is True and
            row.get("condition_truth_at_native_select")=="UNKNOWN" and
            row.get("readiness_of_competitors")=="UNKNOWN" and
            row.get("full_READY")=="UNKNOWN" and
            row.get("is_WoW_player_spellcast") is False and
            row.get("is_dummy_mistake") is False and
            row.get("sequence_kind") in ("COMBAT","PRECOMBAT") and
            type(row.get("simc_time_ms")) is int and
            row["simc_time_ms"]>=0,
            "ACTUAL_EMITTED_ROW_NOT_UNPROMOTED")
    exact=row.get("exact_source_row_status")
    if exact=="UNKNOWN_NO_SOURCE_SIGNATURE":
        require(row.get("source_APL_row_sha256") is None and
                row.get("source_APL_IF") is None,
                "UNKNOWN_SOURCE_ROW_WITH_FORGED_IF")
        status="UNKNOWN_UNMAPPED_SOURCE_ROW"
        symbols=[]
    else:
        require(exact=="SOURCE_POINTER_SIGNATURE_EXACT" and
                type(row.get("source_APL_index_one_based")) is int and
                row["source_APL_index_one_based"]>0 and
                type(row.get("source_APL_list")) is str and
                row["source_APL_list"] not in ("","-") and
                HEX64.fullmatch(row.get("source_APL_row_sha256","")) is not None,
                "ORIGINAL_APL_ROW_POINTER_SIGNATURE_UNVERIFIED")
        expr=row.get("source_APL_IF")
        if expr is None:
            symbols=[]
            status=NO_IF
        else:
            require(isinstance(expr,str) and expr and len(expr)<=8192,
                    "IF_SOURCE_LITERAL_NOT_BOUNDED")
            try:
                symbols=sorted(ast_symbols(Expression(expr).parse()))
            except AplError:
                status="UNKNOWN_UNPARSEABLE_SOURCE_IF"
                symbols=[]
            else:
                status=("SOURCE_EXACT_IF_OPERANDS_UNOBSERVED" if symbols
                        else "SOURCE_EXACT_CONSTANT_IF_NOT_SOURCE_READY_PROOF")
    require(status in STATUSES,"UNDECLARED_SOURCE_CONDITION_CLASS")
    return {
        "simc_ms":row["simc_time_ms"],
        "sequence_kind":row["sequence_kind"],
        "JSON2_ordinal":row["JSON2_ordinal"],
        "simc_action":row["JSON2_action_name"],
        "source_list":row.get("source_APL_list"),
        "source_row_index_1based":row.get("source_APL_index_one_based"),
        "source_row_sha256":row.get("source_APL_row_sha256"),
        "source_if_literal":row.get("source_APL_IF"),
        "unobserved_source_IF_symbols":symbols,
        "exact_source_row_status":exact,
        "if_status":status,
        "source_if_truth_at_actual_selection":"UNKNOWN",
        "candidate_competitor_ready":"UNKNOWN",
        "unique_causal_select_root_id":"NOT_OBSERVED_IN_THIS_JSON2_EMITTER",
        "source_IF_at_emission_not_select_PRE":True,
        "dummy_wrong_skill_verdict":"UNKNOWN",
    }


def compile_frontier(document:dict,*,raw_sha256:str,window_ms:int=10000,
                     source_root_if_prior_receipt:dict|None=None)->dict:
    require(isinstance(raw_sha256,str) and HEX64.fullmatch(raw_sha256) is not None and
            type(window_ms) is int and 1000<=window_ms<=30000 and
            document.get("schema")==INPUT_SCHEMA and
            document.get("policy_id")==POLICY and
            document.get("source_row_witness")==
                "ORIGINAL_ACTION_SIGNATURE_IN_SAME_JSON2_EMITTER" and
            document.get("original_pristine_and_instrumented_sequences_compared") is True and
            document.get("full_positive_READY_proven")==0 and
            document.get("opener_end")=="UNKNOWN" and
            document.get("WCL_blind_holdout")=="NOT_RUN" and
            document.get("dummy_mistake_permitted") is False and
            document.get("MAIN_promoted") is False,
            "ORIGINAL_SIMC_EMITTED_ROW_SCOPE_UNSUPPORTED")
    cases=document.get("cases")
    require(isinstance(cases,list) and len(cases)>=4,
            "CROSS_SPEC_AND_TARGET_CASES_REQUIRED")
    seen=set();totals=Counter();result=[]
    for case in cases:
        key=(case["source_spec_key"],case["source_case"])
        require(key not in seen and
                type(case.get("target_count")) is int and
                case["target_count"]>0 and
                case.get("original_select_decision_time_state")=="NOT_CAPTURED" and
                case["parity"]["recorded_combat_action_order_and_times_unchanged"] is True and
                case["parity"]["recorded_precombat_action_order_and_times_unchanged"] is True,
                "CROSS_CASE_IDENTITY_OR_PRISTINE_PARITY_INVALID")
        seen.add(key)
        counts=Counter();sym=Counter();examples=[];pre_count=0
        exact_all=0;all_count=0
        for name in ("actual_precombat_emitted_actions","actual_combat_emitted_actions"):
            prev_t=-1;prev_ordinal=-1
            for row in case[name]:
                require(row["simc_time_ms"]>=prev_t and
                        type(row["JSON2_ordinal"]) is int and
                        row["JSON2_ordinal"]>prev_ordinal and
                        row["sequence_kind"]==(
                            "PRECOMBAT" if name.startswith("actual_precombat")
                            else "COMBAT"),
                        "ORIGINAL_SEQUENCE_ORDER_CHANGED")
                prev_t=row["simc_time_ms"];prev_ordinal=row["JSON2_ordinal"]
                one=inspect_one(row)
                all_count+=1
                if one["exact_source_row_status"]=="SOURCE_POINTER_SIGNATURE_EXACT":
                    exact_all+=1
                counts[one["if_status"]]+=1
                # Only combat in bounded opener *sample*, not the entire
                # fight, is used for the capture priority backlog.
                if name=="actual_combat_emitted_actions" and row["simc_time_ms"]<window_ms:
                    for field in one["unobserved_source_IF_symbols"]:
                        sym[field]+=1
                    examples.append(one)
                elif name=="actual_precombat_emitted_actions":
                    pre_count+=1
        require(counts["SOURCE_EXACT_IF_OPERANDS_UNOBSERVED"]+
                counts[NO_IF]+
                counts["SOURCE_EXACT_CONSTANT_IF_NOT_SOURCE_READY_PROOF"]+
                counts["UNKNOWN_UNMAPPED_SOURCE_ROW"]+
                counts["UNKNOWN_UNPARSEABLE_SOURCE_IF"]==all_count,
                "SOURCE_IF_DECISION_STATUS_NOT_PARTITIONED")
        require(exact_all==case["counts"].get("exact_source_row_pointer_signature",0),
                "SOURCE_EXACT_SIGNATURE_COUNT_DRIFT")
        totals.update(counts)
        result.append({
            "source_spec_key":key[0],"source_case":key[1],
            "targets":case["target_count"],
            "emitted_total_precombat_and_combat":all_count,
            "exact_source_APL_signatures":exact_all,
            "classification_counts":dict(sorted(counts.items())),
            "first_window_ms_not_verified_opener_end":window_ms,
            "first_window_observed_action_rows":examples,
            "precombat_actions_kept_separate":pre_count,
            "missing_IF_operand_priority_by_emitted_action_frequency":[
                {"symbol":k,"source_rows_in_first_window":v,
                 "select_time_value":"UNKNOWN",
                 "producer_kind":"SOURCE_SCOPED_PRE_FIELD_REQUIRED"}
                for k,v in sorted(sym.items(),key=lambda e:(-e[1],e[0]))],
            "exact_select_root_link_between_CXX_and_emitter":"NOT_OBSERVED",
            "source_ready_and_priority_decision":"UNKNOWN",
            "observed_sample_opener_is_complete":False,
        })
    require(len({c["source_spec_key"] for c in result})>=2,
            "SECOND_CLASS_MISSING")
    # Separate original source-run IF facts can be reported as independent
    # audit inventory but NEVER attached to specific rows above. A matching
    # time or expression is not an identity link across SimC runs.
    prior={"available":False,"cannot_join_per_emitted_action":True}
    if source_root_if_prior_receipt is not None:
        p=source_root_if_prior_receipt
        require(p.get("schema")=="ZrotBranchOriginalRootManaAndNativeIFReceiptV1"
                and p.get("product_policy_id")==POLICY
                and p.get("official_simc_source_commit")==
                    document["original_CPP_revision"]
                and p.get("aggregates",{}).get("original_root_pre",0)>0
                and p.get("aggregates",{}).get("source_ast_native_conflict")==0
                and p.get("limits",{}).get("independent_full_ready_proven")==0
                and p.get("limits",{}).get("wcl_blind_holdout_current_ir") is False,
                "EXTERNAL_ROOT_IF_RECEIPT_NOT_SOURCE_PINNED")
        prior={
            "available":True,"independent_original_CPP_root_PRE_count":
                p["aggregates"]["original_root_pre"],
            "independent_original_CPP_bounded_AST_vs_native_IF_matches":
                p["aggregates"]["source_ast_native_match"],
            "cannot_join_per_emitted_action":True,
            "cross_run_exact_root_id_or_action_pointer_join":"NOT_AVAILABLE",
            "same_time_or_spell_name_JOIN_FORBIDDEN":True,
        }
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "actual_same_JSON2_emitter_source_sha256":raw_sha256,
        "source_case_count":len(result),"cases":result,
        "total_exact_emitted_source_rows":totals[NO_IF]+
            totals["SOURCE_EXACT_IF_OPERANDS_UNOBSERVED"]+
            totals["SOURCE_EXACT_CONSTANT_IF_NOT_SOURCE_READY_PROOF"]+
            totals["UNKNOWN_UNPARSEABLE_SOURCE_IF"],
        "total_if_dependency_classification_counts":dict(sorted(totals.items())),
        "separate_prior_original_root_if_evidence_not_joined":prior,
        "minimum_new_real_source_producer_obligation":
            "EXACT_SAME_RUN_SELECT_ROOT_ID_PLUS_APL_ROW_AND_PRE_OPERANDS",
        "same_run_source_select_IF_causality_proven":0,
        "independent_full_READY_proven":0,
        "WCL_blind_holdout":"NOT_RUN",
        "dummy_mistake_permitted":False,
        "WCL_API_calls":0,"MAIN_promoted":False,
    }


def selftest()->dict:
    def action(i,expr,kind="SOURCE_POINTER_SIGNATURE_EXACT"):
        exact=kind=="SOURCE_POINTER_SIGNATURE_EXACT"
        return {"sequence_kind":"COMBAT","simc_time_ms":i*300,
          "JSON2_ordinal":i,"JSON2_action_name":"synthetic",
          "source_APL_list":"test" if exact else "-",
          "source_APL_index_one_based":1 if exact else 0,
          "source_APL_row_sha256":"a"*64 if exact else None,
          "source_APL_IF":expr if exact else None,
          "exact_source_row_status":kind,
          "same_object_signatures_paired_to_JSON2_ordinal":True,
          "condition_truth_at_native_select":"UNKNOWN",
          "readiness_of_competitors":"UNKNOWN","full_READY":"UNKNOWN",
          "is_WoW_player_spellcast":False,"is_dummy_mistake":False}
    cases=[]
    for spec in ("unrelated_a","unrelated_b"):
        for name,target in (("st",1),("2t",2)):
            cases.append({
              "source_spec_key":spec,"source_case":name,"target_count":target,
              "original_select_decision_time_state":"NOT_CAPTURED",
              "parity":{"recorded_combat_action_order_and_times_unchanged":True,
                        "recorded_precombat_action_order_and_times_unchanged":True},
              "actual_precombat_emitted_actions":[],
              "actual_combat_emitted_actions":[
                action(0,"buff.charge.react&rage>=80"),
                action(1,None),
                action(2,None,"UNKNOWN_NO_SOURCE_SIGNATURE")],
              "counts":{"exact_source_row_pointer_signature":2},
            })
    doc={
      "schema":INPUT_SCHEMA,"policy_id":POLICY,
      "original_CPP_revision":"b522cded8c26b97dac03fdf56e57a03ec7e8faa6",
      "source_row_witness":"ORIGINAL_ACTION_SIGNATURE_IN_SAME_JSON2_EMITTER",
      "original_pristine_and_instrumented_sequences_compared":True,
      "full_positive_READY_proven":0,
      "opener_end":"UNKNOWN","WCL_blind_holdout":"NOT_RUN",
      "dummy_mistake_permitted":False,"MAIN_promoted":False,"cases":cases
    }
    result=compile_frontier(doc,raw_sha256="f"*64)
    assert result["total_exact_emitted_source_rows"]==8
    assert result["total_if_dependency_classification_counts"][
       "SOURCE_EXACT_IF_OPERANDS_UNOBSERVED"]==4
    assert result["same_run_source_select_IF_causality_proven"]==0
    assert result["cases"][0]["missing_IF_operand_priority_by_emitted_action_frequency"]==[
      {"symbol":"buff.charge.react","source_rows_in_first_window":1,
       "select_time_value":"UNKNOWN","producer_kind":"SOURCE_SCOPED_PRE_FIELD_REQUIRED"},
      {"symbol":"rage","source_rows_in_first_window":1,
       "select_time_value":"UNKNOWN","producer_kind":"SOURCE_SCOPED_PRE_FIELD_REQUIRED"}]
    forged=json.loads(json.dumps(doc))
    forged["cases"][0]["actual_combat_emitted_actions"][0][
        "condition_truth_at_native_select"]=True
    try:compile_frontier(forged,raw_sha256="f"*64)
    except CaptureFrontierError:pass
    else:raise AssertionError("FALSE_NATIVE_IF_TRUTH_PROMOTION")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "synthetic_cases":4,"tests":15,
            "condition_truth_or_full_READY_promotions":0,
            "same_timestamp_cross_run_join_attempts":0,
            "WCL_API_calls":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-exact-json",type=Path)
    p.add_argument("--expected-sha256")
    p.add_argument("--separate-root-if-receipt",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--first-window-ms",type=int,default=10000)
    a=p.parse_args()
    if a.source_exact_json is None:
        if a.expected_sha256 or a.out or a.separate_root_if_receipt:
            p.error("source-exact-json required")
        print(json.dumps(selftest(),sort_keys=True));return
    require(a.out is not None and
            isinstance(a.expected_sha256,str) and
            HEX64.fullmatch(a.expected_sha256) is not None,
            "EXACT_SOURCE_SHA_AND_OUT_REQUIRED")
    blob=a.source_exact_json.read_bytes()
    require(sha256(blob).hexdigest()==a.expected_sha256,
            "PINNED_SIMC_SOURCE_BYTES_CHANGED")
    separate=(json.loads(a.separate_root_if_receipt.read_bytes())
              if a.separate_root_if_receipt else None)
    result=compile_frontier(json.loads(blob),
                            raw_sha256=a.expected_sha256,
                            window_ms=a.first_window_ms,
                            source_root_if_prior_receipt=separate)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canonical(result))
    print("SIMC_EXACT_ROW_IF_CAPTURE_FRONTIER_SHA256="+sha256(
        a.out.read_bytes()).hexdigest())


if __name__=="__main__":
    main()
