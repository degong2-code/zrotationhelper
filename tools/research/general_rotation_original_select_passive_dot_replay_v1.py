#!/usr/bin/env python3
"""Compare pinned SimC APL IF against source-order DoT facts BEFORE Native ready.

Original SELECT PRE call ID/actor/action ptr + exact source row + action
timestamp are required; missing/foreign facts are UNKNOWN. The in-function
snapshot at timestamp t is *not* a strict transition observed < t, so this
reports two distinct verdicts: source-order same-call IF and Strict PRE UNKNOWN.
Never infer independent physical READY, current WoW priority or dummy error.
No-args: safe synthetic regression in PyCharm.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from simc_apl_semantic_ir_v2 import parse_profile,git_blob,evaluate_ast,truth
from general_rotation_original_attempt_frontier_v1 import (
    parse_markers, pointer, numeric, SCHEMA as FRONTIER_SCHEMA
)
from general_rotation_original_candidate_stage_replay_v1 import SCHEMA as STAGE_SCHEMA
from general_rotation_original_select_passive_dot_v1 import (
    MARK, PLAN_SCHEMA as DOT_PLAN_SCHEMA, digest,canonical
)

SCHEMA="ZrotOriginalSelectedSameCallSourceOrderedDotReplayV1"
ADAPTER_SCHEMA="ZrotOriginalSelectedSourceOrderedDotReplayPlanV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
REV="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"

class DotReplayError(ValueError):pass
def need(ok,why):
    if not ok:raise DotReplayError(why)

def parse_dot(log,sha):
    by_id={}
    for line_no,line in enumerate(log.splitlines()):
        if MARK not in line:continue
        need(line.count(MARK)==1,"DUPLICATE_MARKER_ON_LINE")
        p=line.split(MARK,1)[1].strip().split("|")
        need(len(p)==9,"DOT_MARKER_ARITY_DRIFT")
        t,c,actor,act,targ,present,ticking,rem,plan_sha=p
        id_=numeric(c);n=numeric(t)
        need(id_>0 and id_ not in by_id and
             plan_sha==sha and present in ("0","1") and
             ticking in ("0","1") and
             math.isfinite(float(rem)) and float(rem)>=0 and
             (present=="1" or (ticking=="0" and float(rem)==0)) and
             (ticking=="1" or float(rem)==0),
             "DOT_MARKER_ID_DIGEST_OR_VALUE_INVALID")
        by_id[id_]={"line":line_no,"call_id":id_,"t_ms":n,
                    "actor_ptr":pointer(actor),"action_ptr":pointer(act),
                    "target_ptr":pointer(targ),"object_present":present=="1",
                    "ticking":int(ticking),"remaining_seconds":float(rem)}
    need(by_id and len(by_id)<200000,"EMPTY_OR_OVERSIZED_DOT_MARKERS")
    return by_id

def guard(focus,selected,row,source,seen,talent):
    expr=source["expression_fields"].get("if")
    need(expr is not None and row["source_action"]==source["action"],
         "SOURCE_IF_OR_ORIGINAL_ACTION_ROW_DRIFT")
    evidence={"dot."+focus["dot_name"]+".remains":seen["remaining_seconds"],
              "time":selected["t_ms"]/1000.0}
    if source["action"]==focus["dot_name"]:
        evidence["ticking"]=float(seen["ticking"])
    for symbol in expr["symbols"]:
        if symbol in talent:
            evidence[symbol]=talent[symbol]
    unresolved=sorted(set(expr["symbols"])-set(evidence))
    value=evaluate_ast(expr["ast"],evidence)
    boolean=truth(value)
    result="SOURCE_ORDER_PRE_IF_"+("TRUE" if boolean else "FALSE") if boolean is not None else "SOURCE_ORDER_PRE_IF_UNKNOWN"
    return {"source_if":expr["source"],"source_symbols":expr["symbols"],
            "observed_source_order_facts":{x:evidence[x] for x in sorted(evidence) if x in expr["symbols"]},
            "unresolved_symbols":unresolved,"source_order_IF_verdict":result,
            "strict_timestamp_lt_IF_verdict":"UNKNOWN"}

def replay(log,source_bytes,frontier,stage,plan,dot_plan,trait):
    need(plan.get("schema")==ADAPTER_SCHEMA and dot_plan.get("schema")==DOT_PLAN_SCHEMA and
         plan.get("policy_id")==dot_plan.get("policy_id")==POLICY and
         plan.get("source_revision")==dot_plan.get("source_revision")==REV and
         plan.get("spec_key")==frontier.get("source_spec")==stage.get("source_spec") and
         frontier.get("schema")==FRONTIER_SCHEMA and
         stage.get("schema")==STAGE_SCHEMA and
         frontier.get("source_revision")==stage.get("source_revision")==REV and
         plan.get("source_profile_git_blob")==frontier.get("source_profile_git_blob")==
           dot_plan.get("source_profile_git_blob")==git_blob(source_bytes) and
         stage.get("selected_root")==frontier.get("selected_root") and
         stage.get("full_CALL_RUN_return_stack")=="UNKNOWN" and
         frontier.get("physical_ability_ready_independent_of_Native_result")=="UNKNOWN" and
         plan.get("targets")==frontier.get("targets")==stage.get("targets") and
         plan.get("source_dot_action")==dot_plan.get("source_dot_action") and
         plan.get("expected_dot_plan_sha256")==digest(canonical(dot_plan)),
         "UNBOUND_ORIGINAL_SOURCE_APL_AND_READY_TRACE_PROVENANCE")
    need(trait.get("original_source_parse_and_DBC_proven") is True and
         trait.get("source_profile_git_blob")==plan["source_profile_git_blob"] and
         trait.get("source_revision")==REV and
         trait.get("General_Rotation_priority_promoted")==0 and
         trait.get("WCL_independent_blind")=="NOT_RUN",
         "ORIGINAL_STATIC_TALENT_SOURCE_COULD_NOT_BE_PROVEN")
    known_talents={}
    for symbol,id_ in plan["talent_symbols"].items():
        need(symbol.startswith("talent.") and symbol.endswith(".enabled"),
             "INVALID_TALENT_OPERAND")
        matches=[x for x in trait["cases"] if
                 x["trait_name"]==id_["trait_name"] and
                 x["trait_node"]==id_["trait_node"] and
                 x["trait_entry"]==id_["trait_entry"] and
                 x["trait_spell"]==id_["trait_spell"]]
        need(len(matches)==1,"TALENT_ID_NOT_PINNED")
        if matches[0]["source_profile_status"]=="PROFILE_SELECTED_RANK":
            need(matches[0]["source_profile_allocated_rank"]>0,
                 "SOURCE_TALENT_RANK_NOT_SELECTED")
            known_talents[symbol]=1.0
        elif matches[0]["source_profile_status"]=="PROFILE_NOT_SELECTED_NOT_GRANTED":
            need(matches[0]["source_profile_allocated_rank"]==0 and
                 matches[0]["source_dbc_free_grant_to_spec"] is False,
                 "SOURCE_PROFILE_UNSELECTED_CONFLICT")
            known_talents[symbol]=0.0
        else:
            # Free-grant-only without an actual runtime subtree witness is not TRUE.
            need(matches[0]["source_profile_status"]=="PROFILE_UNSELECTED_BUT_FREE_GRANTED",
                 "TALENT_STATUS_NOT_REPRODUCIBLE")
    ast=parse_profile(source_bytes,require_source=True,
                      expected_git_blob=plan["source_profile_git_blob"])
    begins,selects,pres,extras,rets=parse_markers(log)
    captured=parse_dot(log,digest(canonical(dot_plan)))
    selected=frontier["selected_root"]
    for key in ("t_ms","source_list","source_rank","source_action"):
        need(plan["selected_root"][key]==selected[key],"SELECTED_ROOT_WAS_CHANGED")
    dispatch=selected["dispatch_token"]
    need(dispatch in begins and dispatch in selects,
         "SELECTED_DISPATCH_BOUNDARY_MISSING")
    begin=begins[dispatch];end=selects[dispatch]
    need(begin[0]<end[0] and begin[1]==end[1]==selected["t_ms"] and
         begin[2]==end[2],"SELECTED_SOURCE_ROOT_OR_ACTOR_CHANGED")
    focus=[]
    actions=ast["action_lists"][selected["source_list"]]
    for spec in plan["focus"]:
        rank=spec["source_rank"]
        need(type(rank)==int and 1<=rank<selected["source_rank"] and
             spec["source_list"]==selected["source_list"] and
             spec["dot_name"]==plan["source_dot_action"],
             "FOCUS_NOT_A_PRECEDING_SOURCE_ACTION")
        row=stage["source_rank_coverage"][rank-1]
        action=actions[rank-1]
        need(row["rank"]==rank and
             row["source_action"]==spec["source_action"]==action["action"] and
             row["source_sha256"]==action["source_sha256"] and
             row["native_visit_state"]=="OBSERVED_NATIVE_ATTEMPT_FALSE" and
             row["physical_mechanic_ready"]=="UNKNOWN" and
             row["independent_IF_at_ATTEMPT_PRE"]=="UNKNOWN",
             "NOT_ORIGINAL_UNKNOWN_SOURCE_IF_OR_NATIVE_CALL")
        id_=row["original_call_id"]
        need(id_ is not None and id_ in pres and id_ in rets and id_ in captured,
             "DOT_PRE_INSTRUMENTATION_NOT_BOUND_TO_ORIGINAL_CALL_ID")
        pre=pres[id_];post=rets[id_];obs=captured[id_]
        need(begin[0]<pre["line"]<obs["line"]<post[0]<end[0] and
             pre["ptr"]==post[2]==obs["action_ptr"] and
             begin[2]==obs["actor_ptr"] and
             pre["t_ms"]==post[1]==obs["t_ms"]==selected["t_ms"] and
             obs["target_ptr"]!="0x0" and
             row["original_action_ready_result"]=="FALSE" and
             post[3] is False,
             "DOT_CAPTURE_TIME_POINTER_ACTOR_OR_READY_LEAKAGE")
        evidence=guard(spec,selected,row,action,obs,known_talents)
        focus.append({
          "source_list":selected["source_list"],"rank":rank,
          "source_action":action["action"],"source_row_sha256":action["source_sha256"],
          "original_native_call_id":id_,"original_native_return":"FALSE",
          "dot_snapshot":{"target_ptr":obs["target_ptr"],
              "object_already_present":obs["object_present"],
              "ticking":obs["ticking"],"remains_seconds":obs["remaining_seconds"],
              "read_method":"player_t::find_dot;dot_t::is_ticking;dot_t::remains",
              "source_order_before_original_ready":True,
              "timestamp_less_than_action":False},
          **evidence,
          "original_native_IF_comparator_observed":"NOT_RE_EVALUATED",
          "independent_physical_READY":"UNKNOWN",
          "current_Retail_priority":"UNKNOWN"
        })
    need(len(focus)==plan["expected_focus_count"],"MISSING_SOURCE_FOCUS_ROW")
    return {"schema":SCHEMA,"policy_id":POLICY,"source_revision":REV,
            "spec_key":plan["spec_key"],"profile_git_blob":plan["source_profile_git_blob"],
            "selected_root":selected,"targets":plan["targets"],"observed_focused":focus,
            "source_order_pre_before_ready":True,
            "Strict_PRE_timestamp_lt_action":"NOT_PROVEN",
            "source_order_PRE_is_not_independent_WoW_transition":True,
            "original_source_IF_not_a_native_ready_verdict":True,
            "original_new_ready_calls":0,
            "complete_CALL_RUN_return_stack":"UNKNOWN",
            "WCL_blind_candidate_lock":"NOT_RUN",
            "opener_and_general_rotation_user_rules":"UNKNOWN",
            "current_Retail_mechanics":"UNKNOWN",
            "target_dummy_wrong_cast":"UNKNOWN",
            "new_user_general_rotation_rules_promoted":0,
            "MAIN_promoted":False}

def selftest():
    from simc_apl_semantic_ir_v2 import Expression
    spec={"dot_name":"synthetic_dot"}
    selected={"t_ms":940}
    row={"source_action":"synthetic_dot"}
    actions={"action":"synthetic_dot",
             "expression_fields":{"if":{"source":"!ticking",
               "ast":Expression("!ticking").parse(),"symbols":["ticking"]}}}
    got=guard(spec,selected,row,actions,{"talent.synthetic.enabled":1},{
         "ticking":0,"remaining_seconds":0})
    need(got["source_order_IF_verdict"]=="SOURCE_ORDER_PRE_IF_TRUE" and
         got["strict_timestamp_lt_IF_verdict"]=="UNKNOWN",
         "IN_CALL_DOT_NOT_STRICT_PRE")
    raw=MARK+"940|8|0x12|0x14|0x16|0|0|0|"+("a"*64)
    captured=parse_dot(raw,"a"*64)
    need(captured[8]["ticking"]==0 and not captured[8]["object_present"],
         "ABSENT_DOT_ZERO_NOT_HANDLED")
    n=0
    for bad in (
      raw+"\n"+raw,
      raw.replace("|0|0|0|","|0|1|0|"),
      raw.replace("|0|0|0|","|0|0|2|"),
      raw.replace("|"+("a"*64),"|"+("b"*64)),
      raw.replace("|0|0|0|","|2|0|0|"),
    ):
      try:parse_dot(bad,"a"*64)
      except DotReplayError:n+=1
      else:raise AssertionError("INVALID_OR_DUPLICATE_DOT_TRACE_ACCEPTED")
    need(n==5,"DOT_REPLAY_NEGATIVE_REGRESSION")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls":n,
            "source_order_PRE_distinct_from_Strict_PRE":True,
            "missing_observation_promoted_to_READY":False,
            "original_native_calls_added":0,"WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--profile",type=Path)
    p.add_argument("--prior-frontier",type=Path)
    p.add_argument("--prior-stage",type=Path)
    p.add_argument("--dot-adapter",type=Path)
    p.add_argument("--plan",type=Path)
    p.add_argument("--talent-evidence",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if all(x is None for x in vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(x is not None for x in vars(a).values()),"ALL_ORIGINAL_SOURCE_REPLAY_INPUTS_REQUIRED")
    log=a.native_log.read_text("utf-8")
    result=replay(log,a.profile.read_bytes(),
                  json.loads(a.prior_frontier.read_bytes()),
                  json.loads(a.prior_stage.read_bytes()),
                  json.loads(a.plan.read_bytes()),
                  json.loads(a.dot_adapter.read_bytes()),
                  json.loads(a.talent_evidence.read_bytes()))
    raw=canonical(result)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(raw)
    print("SOURCE_ORDER_DOT_IF_REPLAY_SHA256="+digest(raw))
    print("SOURCE_ORDER_DOT_IF_FOCUSED="+json.dumps(
      [{"rank":x["rank"],"action":x["source_action"],
        "if":x["source_order_IF_verdict"],
        "dot":x["dot_snapshot"]["ticking"],
        "remains":x["dot_snapshot"]["remains_seconds"]}
       for x in result["observed_focused"]],sort_keys=True))

if __name__=="__main__":
    main()
