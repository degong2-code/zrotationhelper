#!/usr/bin/env python3
"""Bounded source-evidence Arcane 2T winner vs preceding APL decisions.

One record per actual original source row: selected Arcane Orb source IF TRUE,
earlier Orb source IF FALSE, earlier Prismatic/Clearcasting source-local READY
guards FALSE, and original C++ Barrage IF FALSE (unrecomputed; UNKNOWN
independent truth). No false-positive claim about full cooldown availability,
optimality, independent WCL behavior or permitted in-game addon visibility.

Extends existing generic DecisionReason contract using external source
provenance; not part of Hekili-style in-combat recommendation.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from general_rotation_arcane_competitor_native_route_replay_v1 import (
    SCHEMA as RIVAL,
)
from general_rotation_arcane_orb_conditional_source_model_v1 import (
    SCHEMA as ORB_MODEL,
)
from general_rotation_source_eligibility_decision_ir_v1 import POLICY

SCHEMA="ZrotArcane2TFullSourceRowDecisionReasonLedgerV1"
PIN_RIVAL="1f95b9acbea26421cb29e0a6e8252276ce404c8580a8d9fa276a029e93cccfbe"
PIN_ORB="b92946feacc6fd3d17b5aa280e91370842fdc85c6c7a41fd10ab7b1330ec08c6"

class RivalReasonLedgerError(ValueError):pass

def require(ok:bool,reason:str)->None:
    if not ok:raise RivalReasonLedgerError(reason)

def merge(rivals:dict,orb:dict)->dict:
    require(rivals.get("schema")==RIVAL and
            orb.get("schema")==ORB_MODEL and
            rivals.get("product_policy_id")==orb.get("product_policy_id")==POLICY and
            rivals.get("source_original_CPP_actual_branch_return_executed") is True and
            rivals.get("whole_ability_NOT_READY_proven") is False and
            rivals.get("entire_general_rotation_priority_optimality_proven") is False and
            orb.get("safe_dummy_feedback_permitted") is False and
            orb.get("WCL_source_blind_holdout_performed") is False,
            "SOURCE_RIVAL_AND_ORB_INDEPENDENT_CONTRACT_INVALID")
    decisions=orb["case_results"]["2t"]["conditional_source_rule_hypotheses"]
    rivals_rows=rivals["two_target_arcane_orb_source_prior_competitors"]
    require(len(decisions)==3 and len(rivals_rows)==2,
            "ORIGINAL_2T_SELECTION_SAMPLE_COUNT_CHANGED")
    orb_by_time={x["simc_ms"]:x for x in decisions}
    require(set(orb_by_time)=={0,7667,14950},
            "SOURCE_ORIGINAL_ARCANE_ORB_SELECTION_TIMES_CHANGED")
    totals=Counter()
    results=[]
    for item in rivals_rows:
        time=item["at_simc_ms"]
        original=orb_by_time.get(time)
        require(original is not None and
                item["chosen_original_cpp_arcane_orb_ready_root"]==
                original["selected_source_APL_IF_TRUE"]["source_original_CPP_ready_root"] and
                original["selected_source_APL_IF_TRUE"]["source_IF_independently_replayed_value"] is True,
                "CHOSEN_ORB_TRUE_MUST_BE_THE_SAME_ORIGINAL_CPP_ROOT")
        previous=original["earlier_same_list_candidate_decisions"]
        physical=item["source_prior_4_non_orb_candidate_original_CPP_root_evidence"]
        require(len(previous)==5 and len(physical)==4,
                "EXACT_SOURCE_CANDIDATE_LIST_NOT_COMPLETE")
        physic={(r["ordinal"],r["source_action"]):r for r in physical}
        require(len(physic)==4,"DUPLICATE_SOURCE_PHYSICAL_CANDIDATE")
        ledger=[]
        for src in previous:
            action=src["source_action"];order=src["source_ordinal"]
            if action=="arcane_orb":
                if_false=src.get("source_IF_FALSE_witness")
                require(order==2 and
                        if_false is not None and
                        if_false["source_IF_independently_replayed_value"] is False and
                        if_false["source_original_CPP_ready_root"]==
                            src["original_cpp_ready_root"] and
                        if_false["minimal_sufficient_facts"]==
                           {"talent.orb_mastery":0},
                        "EARLIER_ORB_INDEPENDENT_SOURCE_AST_FALSE_NOT_PROVEN")
                verdict="INDEPENDENT_SOURCE_ROW_IF_FALSE"
                reason="ORIGINAL_APL_IF_ORB_MASTERY_NOT_SELECTED"
                proof={"talent.orb_mastery":0}
                total=False
                totals["earlier_independent_source_IF_false"]+=1
            else:
                r=physic.get((order,action))
                require(r is not None and
                        r["source_root_id"]==src["original_cpp_ready_root"] and
                        r["at_ms"]==time and
                        r["original_native_POST"] is False,
                        "SOURCE_PHYSICAL_PRE_AND_CANDIDATE_NOT_SAME_ROOT")
                local=r["local_derived_ready_guard_FALSE_proven_independently"]
                if local:
                    state=r["exact_original_cpp_class_PRE"]
                    require(state is not None and state["buff_stack"]==0 and
                            r["original_action_ready_return_stage"]==
                                  "ACTION_BASE_READY_FALSE" and
                            r["original_class_ready_return_stage"] in (
                                "PRISMATIC_BUFF_NOT_PRESENT",
                                "MISSILES_CLEARCASTING_MISSING"),
                            "LOCAL_FALSE_READY_CLASS_GUARD_NOT_EXHAUSTIVE")
                    verdict="INDEPENDENT_SOURCE_LOCAL_READY_GUARD_FALSE"
                    reason=r["original_class_ready_return_stage"]
                    proof={"original_CPP_class_buff_check":0,
                           "source_readiness_class":action}
                    totals["earlier_independent_local_READY_false"]+=1
                else:
                    require(action=="arcane_barrage" and order==3 and
                            r["original_action_ready_return_stage"]==
                               "ACTION_APL_IF_FALSE",
                            "NATIVE_ONLY_PRIOR_SOURCE_UNKNOWN_WRONG_STAGE")
                    verdict="ORIGINAL_NATIVE_APL_IF_FALSE_INDEPENDENT_PRE_UNKNOWN"
                    reason="NATIVE_CPP_SOURCE_IF_FALSE_ONLY"
                    proof=None
                    totals["earlier_original_cpp_if_false_not_independently_replayed"]+=1
            total=verdict.startswith("INDEPENDENT_")
            ledger.append({
                "original_source_ordinal":order,
                "source_action":action,
                "original_cpp_ready_root_id":src["original_cpp_ready_root"],
                "native_CPP_source_POST_observed":False,
                "source_reason":reason,
                "decision_evidence_class":verdict,
                "source_independent_local_pre_witness":proof,
                "independent_entire_spell_NOT_READY_proven":False,
                "source_row_exclusion_condition_proven":total,
                "dummy_user_mistake_verdict":"UNKNOWN",
            })
            totals["prior_original_source_rows"]+=1
            if total:totals["source_row_exclusion_independently_supported"]+=1
        require([r["original_source_ordinal"] for r in ledger]==[1,2,3,4,5] and
                [r["source_action"] for r in ledger]==[
                  "prismatic_bolt","arcane_orb","arcane_barrage",
                  "arcane_missiles","prismatic_bolt"],
                "FIRST_2T_SOURCE_ORDER_NOT_RECONCILED")
        totals["original_cpp_selected_2T_orb_rows"]+=1
        results.append({
            "original_cpp_at_simc_ms":time,
            "target_count_scenario":2,
            "earlier_source_rows":ledger,
            "chosen_source_row_ordinal":6,
            "chosen_source_action":"arcane_orb",
            "chosen_CPP_ready_root_id":item["chosen_original_cpp_arcane_orb_ready_root"],
            "chosen_independently_replayed_source_APL_IF":True,
            "chosen_minimal_sufficient_source_facts":
               original["selected_source_APL_IF_TRUE"]["minimal_sufficient_facts"],
            "chosen_full_physical_READY_independently_proven":False,
            "earlier_all_possible_action_alternatives_exhaustively_proven":False,
            "WoW_dummy_error_verdict":"UNKNOWN",
        })
    require(totals["prior_original_source_rows"]==10 and
            totals["source_row_exclusion_independently_supported"]==8 and
            totals["earlier_independent_local_READY_false"]==6 and
            totals["earlier_independent_source_IF_false"]==2 and
            totals["earlier_original_cpp_if_false_not_independently_replayed"]==2,
            "BOUND_2T_EXPLANATION_CONFIDENCE_COUNTS_DRIFT")
    return {
      "schema":SCHEMA,"product_policy_id":POLICY,
      "research_context":"OFFLINE_SIMC_SOURCE_ST2T_NOT_ENCOUNTER",
      "source_candidate_order_and_return_proven":True,
      "two_target_winner_decisions":results,
      "counts":dict(sorted(totals.items())),
      "two_remaining_barrage_native_APL_IF_not_independently_replayed":True,
      "native_cpp_source_choice_not_WCL_ranker_holdout":True,
      "source_local_failure_not_skill_globally_unavailable":True,
      "general_rotation_priority_optimality_proven":False,
      "current_WoW_client_addon_observation_proven":False,
      "dummy_training_feedback_permitted":False,
      "WCL_API_calls":0,
    }

def read_pinned(competitor:Path,source_orb:Path)->dict:
    cp=competitor.read_bytes();op=source_orb.read_bytes()
    require(sha256(cp).hexdigest()==PIN_RIVAL and
            sha256(op).hexdigest()==PIN_ORB,
            "SOURCE_CPP_BRANCH_AND_SELECTED_ORB_ARTIFACT_BYTES_CHANGED")
    return merge(json.loads(cp),json.loads(op))

def selftest()->dict:
    assert len(PIN_ORB)==len(PIN_RIVAL)==64
    for s in (PIN_ORB,PIN_RIVAL):
        assert all(x in "0123456789abcdef" for x in s)
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":4,"actual_original_CXX_recompiled":False,
            "positive_full_ready_proven":0,"WCL_API_calls":0}

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--competitor-ready-evidence",type=Path)
    p.add_argument("--selected-orb-source-model",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.competitor_ready_evidence is None and a.selected_orb_source_model is None:
        obj=selftest()
    elif a.competitor_ready_evidence is not None and a.selected_orb_source_model is not None:
        obj=read_pinned(a.competitor_ready_evidence,a.selected_orb_source_model)
    else:p.error("both actual original CPP source receipts required")
    raw=(json.dumps(obj,sort_keys=True,separators=(",",":"),
                    ensure_ascii=False,allow_nan=False)+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(raw)
    else:
        import sys
        sys.stdout.buffer.write(raw)

if __name__=="__main__":main()
