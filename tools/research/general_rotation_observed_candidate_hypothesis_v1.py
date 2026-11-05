#!/usr/bin/env python3
"""Extract bounded SimC-first General Rotation source priority hypotheses.

Consumes previously verified time-scoped selection frontiers and the exact
SimC source profile. No new SimC build or WCL fetch. The first-observed
selection window is NOT necessarily the combat opener. Native true/false is
only a comparator; no independent READY, winner, mandatory priority, or
threshold may be inferred from this evidence.

Source APL IF and target_if are preserved verbatim, without evaluating the
states that were not captured in Strict PRE. Output is a reusable hypothesis
registry for *post-lock* WCL comparison, never WCL-blind discovery input.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_time_scoped_priority_ir_v1 import SCHEMA as TIME_SCHEMA
from simc_apl_semantic_ir_v2 import parse_profile, git_blob
from general_rotation_source_eligibility_decision_ir_v1 import POLICY

SCHEMA="ZrotGeneralRotationObservedCandidateHypothesisV1"
COMPARISON_SCHEMA="ZrotGeneralRotationST2TSourceHypothesisComparisonV1"
OBSERVED_EVENTS={"ACTION_READY_CALLED", "BACKGROUND_SKIP_BEFORE_READY",
                 "WAIT_ON_READY_BREAK"}


class HypothesisError(ValueError):
    pass


def _row_key(owner,ordinal,source_hash):
    return owner+"|"+str(ordinal)+"|"+source_hash


def _assert_source(source, profile, window_ms):
    if type(window_ms) is not int or not 1<=window_ms<=120000:
        raise HypothesisError("EARLY_OBSERVATION_WINDOW_INVALID")
    if (not isinstance(source,dict) or source.get("schema")!=TIME_SCHEMA or
        source.get("product_policy_id")!=POLICY or
        source.get("source_profile_git_blob_sha1")!=git_blob(profile) or
        type(source.get("target_count")) is not int or
        not 1<=source["target_count"]<=40 or
        source.get("source_order_complete") is not False or
        source.get("independent_FULL_READY_proven")!=0 or
        source.get("priority_rule_optimality_proven") is not False or
        source.get("dummy_error_permitted") is not False or
        source.get("WCL_independent_blind_candidate_lock_maintained") is not True):
        raise HypothesisError("SOURCE_HYPOTHESIS_EVIDENCE_SCOPE_NOT_VERIFIED")
    rows=parse_profile(profile,require_source=False)["action_lists"]
    sweeps=source.get("observed_time_scoped_selection_frontiers")
    if not isinstance(sweeps,list) or not sweeps or len(sweeps)!=source.get("source_sweep_count"):
        raise HypothesisError("TIME_SCOPED_SOURCE_SWEEPS_REQUIRED")
    return rows,sweeps


def extract(profile:bytes, source:dict, *, window_ms:int=10000)->dict:
    lists,sweeps=_assert_source(source,profile,window_ms)
    earliest=min(s["at_simc_ms"] for s in sweeps)
    if type(earliest) is not int or earliest<0:
        raise HypothesisError("BAD_ORIGINAL_SELECTION_ANCHOR")
    seen_sweeps=set()
    seen_roots=set()
    candidate_rows={}
    early_sweep_summaries=[]
    counters=Counter()
    per_phase=defaultdict(Counter)
    edges=Counter()
    sweep_origin={}
    prev_anchor=None
    for sweep in sweeps:
        sid=sweep.get("sweep_call_id")
        parent=sweep.get("parent_sweep_call_id")
        t=sweep.get("at_simc_ms")
        owner=sweep.get("source_list")
        mode=sweep.get("execute_type")
        if (type(sid) is not int or sid<=0 or sid in seen_sweeps or
            type(parent) is not int or parent<0 or
            (parent and parent not in seen_sweeps) or
            type(t) is not int or t<earliest or
            owner not in lists or
            type(mode) is not int or
            sweep.get("full_source_priority_frontier_closed") is not False or
            sweep.get("conditional_priority_verdict")!="UNKNOWN" or
            sweep.get("opener_optimality_proven") is not False):
            raise HypothesisError("SWEEP_PROVENANCE_OR_UNCLOSED_FRONTIER_CHANGED")
        seen_sweeps.add(sid)
        phase="EARLY_OBSERVED_SELECTION" if t-earliest<window_ms else "LATER_OBSERVED_SELECTION"
        if parent:
            edges[(sweep_origin[parent],owner,phase)]+=1
        sweep_origin[sid]=owner
        stream=sweep.get("observed_candidate_event_stream")
        if not isinstance(stream,list):
            raise HypothesisError("SWEEP_EVENT_STREAM_REQUIRED")
        sweep_events=[]
        for ev in stream:
            kind=ev.get("stage")
            if kind not in OBSERVED_EVENTS:
                raise HypothesisError("SOURCE_EVENT_KIND_UNDECLARED")
            counters[kind]+=1
            per_phase[phase][kind]+=1
            if kind=="WAIT_ON_READY_BREAK":
                sweep_events.append({
                    "stage":kind, "source_native_name":ev.get("source_native_name"),
                    "source_row_identity":"UNKNOWN",
                    "readiness":"UNKNOWN"})
                continue
            ordinal=ev.get("ordinal_one_based")
            h=ev.get("source_row_sha256")
            if (type(ordinal) is not int or ordinal<=0 or
                ordinal>len(lists[owner]) or
                not isinstance(h,str) or h!=lists[owner][ordinal-1]["source_sha256"] or
                ev.get("source_action")!=lists[owner][ordinal-1]["action"]):
                raise HypothesisError("ORIGINAL_APL_LIST_ORDINAL_HASH_MISMATCH")
            row=lists[owner][ordinal-1]
            key=_row_key(owner,ordinal,h)
            if key not in candidate_rows:
                candidate_rows[key]={
                    "source_list":owner,"ordinal_one_based":ordinal,
                    "source_row_sha256":h,
                    "source_line":row["source_line"],
                    "source_action":row["action"],
                    "source_behavior":row["behavior"],
                    "source_attributes":{
                        x["key"]:x["value"] for x in row["attributes"]},
                    "if_source_expression":row["expression_fields"].get("if",{}).get("source"),
                    "if_state_dependencies":row["expression_fields"].get("if",{}).get("symbols",[]),
                    "target_if_source_expression":row["expression_fields"].get(
                        "target_if",{}).get("source"),
                    "target_if_state_dependencies":row["expression_fields"].get(
                        "target_if",{}).get("symbols",[]),
                    "source_original_selection_counts":{
                        "EARLY_OBSERVED_SELECTION":{"calls":0,"native_true":0,"native_false":0,
                                                     "background_skipped":0},
                        "LATER_OBSERVED_SELECTION":{"calls":0,"native_true":0,"native_false":0,
                                                     "background_skipped":0}},
                    "observed_source_method_local_false_rules":{},
                    "source_condition_truth_at_attempt":"UNKNOWN",
                    "physical_ready_at_attempt":"UNKNOWN",
                    "mandatory_priority":"UNKNOWN",
                    "WCL_independent_validation":"NOT_TESTED",
                    "hypothesis_type":"SIMC_SOURCE_CONDITION_NOT_VALIDATED_PRIORITY",
                }
            record=candidate_rows[key]
            counts=record["source_original_selection_counts"][phase]
            if kind=="BACKGROUND_SKIP_BEFORE_READY":
                counts["background_skipped"]+=1
                comparator=None
            else:
                rid=ev.get("original_action_ready_root_id")
                comparator=ev.get("simc_NATIVE_return_post_comparator")
                if (type(rid) is not int or rid<=0 or rid in seen_roots or
                    type(comparator) is not bool or
                    ev.get("comparator_proves_independent_ready") is not False or
                    ev.get("method_false_does_not_prove_entire_action_NOT_READY") is not True or
                    ev.get("physical_action_ready")!="UNKNOWN" or
                    ev.get("priority_verdict")!="UNKNOWN"):
                    raise HypothesisError("FORGED_OR_NATIVE_PROMOTED_READY_ROOT")
                seen_roots.add(rid)
                counts["calls"]+=1
                counts["native_true" if comparator else "native_false"]+=1
                raw_rules=ev.get("independent_method_local_false_rules")
                if not isinstance(raw_rules,list):
                    raise HypothesisError("MISSING_SCOPED_METHOD_WITNESSES")
                for rule in raw_rules:
                    if not isinstance(rule,str) or not rule:
                        raise HypothesisError("BAD_SOURCE_METHOD_LOCAL_RULE")
                    witness=record["observed_source_method_local_false_rules"]
                    witness[rule]=witness.get(rule,0)+1
            sweep_events.append({
                "stage":kind,"source_list":owner,"ordinal_one_based":ordinal,
                "source_row_sha256":h,"source_action":row["action"],
                "native_post_return_only":comparator,
                "source_condition_at_attempt":"UNKNOWN",
                "physical_ready_at_attempt":"UNKNOWN"})
        if len(early_sweep_summaries)<16 and phase=="EARLY_OBSERVED_SELECTION":
            early_sweep_summaries.append({
                "sweep_call_id":sid,"parent_sweep_call_id":parent,
                "at_simc_ms":t,"source_list":owner,"execute_type":mode,
                "observed_events":sweep_events[:20],
                "candidate_tail_truncated":len(sweep_events)>20,
                "independent_full_ready_proven":0})
        prev_anchor=t
    if counters["ACTION_READY_CALLED"]!=source.get("original_ready_calls"):
        raise HypothesisError("OBSERVED_ROOT_COUNT_NOT_RECONCILED")
    if (len(seen_sweeps)!=source.get("source_sweep_count") or
        counters["ACTION_READY_CALLED"]!=(
            source.get("native_post_comparator_true",0)+
            source.get("native_post_comparator_false",0))):
        raise HypothesisError("NATIVE_RETURN_COUNTERS_NOT_RECONCILED")
    expected_observed=source.get("observed_candidate_event_types",{})
    if any(counters[k]!=expected_observed.get(k,0)
           for k in OBSERVED_EVENTS):
        raise HypothesisError("SOURCE_EVENT_TYPE_COUNTER_DRIFT")
    candidates=sorted(candidate_rows.values(),
                      key=lambda r:(r["source_list"],r["ordinal_one_based"],
                                    r["source_row_sha256"]))
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "source_profile_git_blob_sha1":git_blob(profile),
        "target_count":source["target_count"],
        "observation_anchor":"FIRST_OBSERVED_SELECT_ACTION_SWEEP_NOT_COMBAT_START",
        "first_observed_selection_simc_ms":earliest,
        "early_observed_window_duration_ms":window_ms,
        "sweeps_covered":len(seen_sweeps),
        "ready_call_roots_covered":len(seen_roots),
        "source_behavior_hypotheses":candidates,
        "source_behavior_hypothesis_count":len(candidates),
        "first_bounded_observed_sweep_samples":early_sweep_summaries,
        "observed_recursive_source_list_edges":[{
            "parent_list":parent,"child_list":child,
            "phase":phase,"observed_recursive_calls":count,
            "source_control_action_winner_proven":False,
            "control_call_source_causality":"UNKNOWN"
        } for (parent,child,phase),count in sorted(edges.items())],
        "observed_event_counts":dict(sorted(counters.items())),
        "observed_phase_event_counts":{
            name:dict(sorted(counts.items()))
            for name,counts in sorted(per_phase.items())},
        "observed_IF_condition_traces_evaluated":False,
        "opener_skill_sequence_proven":False,
        "source_order_priority_complete":False,
        "independent_FULL_READY_proven":0,
        "WCL_blind_discovery_uncontaminated":True,
        "WCL_holdout_completed":False,
        "dummy_error_permitted":False,"WCL_API_calls":0
    }


def compare(st:dict,two:dict)->dict:
    if (st.get("schema")!=SCHEMA or two.get("schema")!=SCHEMA or
        st.get("product_policy_id")!=two.get("product_policy_id")!=POLICY or
        st.get("source_profile_git_blob_sha1")!=two.get("source_profile_git_blob_sha1") or
        st.get("target_count")!=1 or two.get("target_count")!=2 or
        st.get("early_observed_window_duration_ms")!=two.get(
            "early_observed_window_duration_ms") or
        st.get("independent_FULL_READY_proven")!=0 or
        two.get("independent_FULL_READY_proven")!=0 or
        st.get("WCL_blind_discovery_uncontaminated") is not True or
        two.get("WCL_blind_discovery_uncontaminated") is not True):
        raise HypothesisError("INCOMPATIBLE_OR_SOURCE_CONTAMINATED_ST_2T_HYPOTHESES")
    by_st={(x["source_list"],x["ordinal_one_based"],x["source_row_sha256"]):x
           for x in st["source_behavior_hypotheses"]}
    by_two={(x["source_list"],x["ordinal_one_based"],x["source_row_sha256"]):x
            for x in two["source_behavior_hypotheses"]}
    if len(by_st)!=len(st["source_behavior_hypotheses"]) or len(by_two)!=len(
       two["source_behavior_hypotheses"]):
        raise HypothesisError("DUPLICATE_CONDITIONAL_SOURCE_ROW_IN_HYPOTHESIS")
    summary=[]
    for key in sorted(set(by_st)|set(by_two)):
        a=by_st.get(key);b=by_two.get(key)
        if a and b and (
            a["if_source_expression"]!=b["if_source_expression"] or
            a["source_action"]!=b["source_action"] or
            a["source_behavior"]!=b["source_behavior"]):
            raise HypothesisError("SOURCE_CONDITION_OR_CONTROL_TYPE_CHANGED")
        left=a["source_original_selection_counts"]["EARLY_OBSERVED_SELECTION"] if a else {}
        right=b["source_original_selection_counts"]["EARLY_OBSERVED_SELECTION"] if b else {}
        names=("calls","native_true","native_false","background_skipped")
        summary.append({
            "source_list":key[0],"ordinal_one_based":key[1],
            "source_row_sha256":key[2],
            "source_action":(a or b)["source_action"],
            "source_behavior":(a or b)["source_behavior"],
            "source_if_expression":(a or b)["if_source_expression"],
            "source_if_state_dependencies":(a or b)["if_state_dependencies"],
            "early_native_ST":{n:left.get(n,0) for n in names},
            "early_native_2T":{n:right.get(n,0) for n in names},
            "observed_presence":(
                "BOTH" if a and b else "ONLY_ST" if a else "ONLY_2T"),
            "causality_of_difference":"UNKNOWN_SAMPLE_CONTEXT_CONFOUNDED",
            "target_count_threshold":"UNKNOWN",
            "priority_and_readiness":"UNKNOWN",
            "comparison_is_observational_only":True
        })
    return {
        "schema":COMPARISON_SCHEMA,"product_policy_id":POLICY,
        "source_profile_git_blob_sha1":st["source_profile_git_blob_sha1"],
        "source_conditions_consistent_across_targets":True,
        "early_selection_window_ms":st["early_observed_window_duration_ms"],
        "source_row_comparisons":summary,
        "source_row_comparison_count":len(summary),
        "ST_ready_call_roots":st["ready_call_roots_covered"],
        "two_target_ready_call_roots":two["ready_call_roots_covered"],
        "native_true_does_not_establish_optimal_priority":True,
        "target_count_switch_threshold_proven":False,
        "independent_READY_proven":0,"WCL_blind_candidate_lock_done":False,
        "dummy_error_permitted":False,"WCL_API_calls":0
    }


def selftest():
    from simc_apl_semantic_ir_v2 import parse_profile
    p=(b'warrior="Synthetic"\nspec=fury\n'
       b'actions=/call_action_list,name=burn,if=target.time_to_die>10\n'
       b'actions.burn=/rampage,if=rage>=80,target_if=max:debuff.stack\n')
    # Parser handles supported expressions; target_if=max:... is not
    # part of bounded expression grammar, so test with source-safe options.
    p=(b'warrior="Synthetic"\nspec=fury\n'
       b'actions=/call_action_list,name=burn,if=target.time_to_die>10\n'
       b'actions.burn=/rampage,if=rage>=80\n')
    parsed=parse_profile(p,require_source=False)["action_lists"]
    row=parsed["burn"][0]
    event={
        "stage":"ACTION_READY_CALLED",
        "source_list":"burn","ordinal_one_based":1,
        "source_row_sha256":row["source_sha256"],
        "source_action":"rampage",
        "original_action_ready_root_id":10,
        "simc_NATIVE_return_post_comparator":True,
        "comparator_proves_independent_ready":False,
        "independent_method_local_false_rules":[],
        "method_false_does_not_prove_entire_action_NOT_READY":True,
        "physical_action_ready":"UNKNOWN","priority_verdict":"UNKNOWN"}
    def temporal(n,duplicate=False):
        return {
            "schema":TIME_SCHEMA,"product_policy_id":POLICY,
            "source_profile_git_blob_sha1":git_blob(p),
            "target_count":n,"source_order_complete":False,
            "independent_FULL_READY_proven":0,
            "priority_rule_optimality_proven":False,
            "dummy_error_permitted":False,
            "WCL_independent_blind_candidate_lock_maintained":True,
            "source_sweep_count":2 if duplicate else 1,
            "observed_time_scoped_selection_frontiers":[{
                "sweep_call_id":2,"parent_sweep_call_id":0,
                "at_simc_ms":0,"source_list":"burn","execute_type":0,
                "full_source_priority_frontier_closed":False,
                "conditional_priority_verdict":"UNKNOWN",
                "opener_optimality_proven":False,
                "observed_candidate_event_stream":[event]},
                *([{"sweep_call_id":3,"parent_sweep_call_id":2,
                    "at_simc_ms":0,"source_list":"burn","execute_type":0,
                    "full_source_priority_frontier_closed":False,
                    "conditional_priority_verdict":"UNKNOWN",
                    "opener_optimality_proven":False,
                    "observed_candidate_event_stream":[
                        {**event,"original_action_ready_root_id":11}]}]
                  if duplicate else [])],
            "original_ready_calls":2 if duplicate else 1,
            "native_post_comparator_true":2 if duplicate else 1,
            "native_post_comparator_false":0,
            "observed_candidate_event_types":{
                "ACTION_READY_CALLED":2 if duplicate else 1}
        }
    one=extract(p,temporal(1),window_ms=10000)
    two=extract(p,temporal(2,duplicate=True),window_ms=10000)
    assert one["ready_call_roots_covered"]==1
    assert two["ready_call_roots_covered"]==2
    assert one["source_behavior_hypotheses"][0]["if_source_expression"]=="rage>=80"
    assert one["opener_skill_sequence_proven"] is False
    assert len(two["observed_recursive_source_list_edges"])==1
    dif=compare(one,two)
    assert dif["source_row_comparison_count"]==1
    assert dif["target_count_switch_threshold_proven"] is False
    import copy
    forged=copy.deepcopy(temporal(1))
    forged["observed_time_scoped_selection_frontiers"][0][
        "observed_candidate_event_stream"][0][
            "comparator_proves_independent_ready"]=True
    try:extract(p,forged)
    except HypothesisError:pass
    else:raise AssertionError("NATIVE_RESULT_PROMOTED_TO_INDEPENDENT_READY")
    wrong=copy.deepcopy(temporal(1))
    wrong["observed_time_scoped_selection_frontiers"][0][
        "observed_candidate_event_stream"][0]["source_row_sha256"]="0"*64
    try:extract(p,wrong)
    except HypothesisError:pass
    else:raise AssertionError("FORGED_SOURCE_APL_ROW_ACCEPTED")
    wrong=copy.deepcopy(two);wrong["source_profile_git_blob_sha1"]="0"*40
    try:compare(one,wrong)
    except HypothesisError:pass
    else:raise AssertionError("CROSS_PROFILE_TARGET_COMPARISON_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":10,"actual_original_native_profile_replayed":False,
        "independent_READY_proven":0,
        "WCL_API_calls":0
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile",type=Path)
    ap.add_argument("--st-time-ir",type=Path)
    ap.add_argument("--two-target-time-ir",type=Path)
    ap.add_argument("--early-window-ms",type=int,default=10000)
    ap.add_argument("--out-dir",type=Path)
    a=ap.parse_args()
    if all(x is None for x in (a.profile,a.st_time_ir,a.two_target_time_ir,a.out_dir)):
        result=selftest()
        print(canonical(result).decode(),end="")
    elif all(x is not None for x in (a.profile,a.st_time_ir,a.two_target_time_ir,a.out_dir)):
        p=a.profile.read_bytes()
        st=extract(p,json.loads(a.st_time_ir.read_bytes()),window_ms=a.early_window_ms)
        two=extract(p,json.loads(a.two_target_time_ir.read_bytes()),window_ms=a.early_window_ms)
        merged=compare(st,two)
        a.out_dir.mkdir(parents=True,exist_ok=True)
        for n,result in (("st",st),("2t",two),("st2t_comparison",merged)):
            with (a.out_dir/(n+".json")).open("xb") as f:f.write(canonical(result))
        print(canonical({"schema":SCHEMA,"status":"REAL_SOURCE_IR_REPLAYED",
            "ST_hypotheses":st["source_behavior_hypothesis_count"],
            "two_target_hypotheses":two["source_behavior_hypothesis_count"],
            "conditional_comparisons":merged["source_row_comparison_count"],
            "independent_READY_proven":0,"WCL_API_calls":0}).decode(),end="")
    else:ap.error("provide profile, ST IR, 2T IR and output directory together")


if __name__=="__main__":main()
