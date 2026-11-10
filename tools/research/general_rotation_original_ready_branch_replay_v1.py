#!/usr/bin/env python3
"""Exact original Native action_ready() branch, joined to one source-root call.

All branch observations occur INSIDE the original call, strictly between
existing SELECT PRE and POST markers. They are not PRE gameplay observations.
Original source APL row, call id, action pointer and actor must agree; a
missing or ambiguous branch is UNKNOWN, not NOT_READY / incorrect gameplay.
No-args mode is a safe synthetic regression.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from general_rotation_original_attempt_frontier_v1 import (
    POLICY,REV,SCHEMA as FRONTIER_SCHEMA,parse_markers, pointer,numeric,
    PRE,EXTRA,RESULT,BEGIN,SELECT
)
from general_rotation_original_candidate_stage_replay_v1 import SCHEMA as STAGE_SCHEMA
from general_rotation_original_ready_branch_probe_v1 import MARK

SCHEMA="ZrotOriginalNativeSameCallBranchOutcomeReplayV1"
PLAN_SCHEMA="ZrotOriginalNativeSameCallBranchFocusPlanV1"
BASE={
 "BASE_COOLDOWN_NOT_READY",
 "BASE_INTERNAL_COOLDOWN_DOWN",
 "BASE_MOVING_UNUSABLE",
 "BASE_RESOURCE_NOT_AFFORDABLE",
 "BASE_CAST_WHILE_CASTING_EXECUTION_TIME",
 "BASE_GCD_WHILE_CASTING",
 "BASE_READY_TRUE",
}
COMPOSITE={"COMPOSITE_BASE_READY_FALSE","COMPOSITE_SOURCE_IF_FALSE"}

class BranchReplayError(ValueError):pass
def need(ok,label):
    if not ok:raise BranchReplayError(label)

def collect(log):
    rows=[]
    for line_no,text in enumerate(log.splitlines()):
        if MARK not in text:continue
        need(text.count(MARK)==1,"MULTIPLE_NATIVE_BRANCH_MARKERS_ON_LINE")
        x=text.split(MARK,1)[1].strip().split("|")
        need(len(x)==4,"NATIVE_BRANCH_MARKER_ARITY_CHANGED")
        t,actor,action,code=x
        need(code in BASE|COMPOSITE,"UNTRUSTED_NATIVE_BRANCH_ENUM")
        rows.append({"line":line_no,"t_ms":numeric(t),
                     "actor":pointer(actor),"action":pointer(action),
                     "reason":code})
    need(rows and len(rows)<200000,"EMPTY_OR_OVERSIZED_ORIGINAL_BRANCH_LOG")
    return rows

def interpret(events,native_result):
    """Branch return outcome only; neither independence nor WoW READY."""
    codes=[e["reason"] for e in events]
    base=[x for x in codes if x in BASE]
    outer=[x for x in codes if x in COMPOSITE]
    need(len(base)<=1 and len(outer)<=1,
         "REENTRANT_OR_AMBIGUOUS_ORIGINAL_READY_CALL")
    if outer==["COMPOSITE_BASE_READY_FALSE"]:
        need(native_result is False,"ORIGINAL_BASE_FALSE_BUT_RETURN_TRUE")
        if len(base)==1 and base[0]!="BASE_READY_TRUE":
            need(codes.index(base[0])<codes.index(outer[0]),
                 "BASE_REASON_RECORDED_AFTER_COMPOSITE_RETURN")
            return "NATIVE_BASE_BRANCH_"+base[0],base[0]
        need(not base or base==["BASE_READY_TRUE"],
             "INVALID_BASE_MARKER_FORMAT")
        # A subclass can fail before calling base action_t::ready(). We
        # cannot conclude which virtual override rejected the ability.
        return "NATIVE_OVERRIDE_READY_FALSE_CAUSE_UNKNOWN","UNKNOWN"
    if outer==["COMPOSITE_SOURCE_IF_FALSE"]:
        need(native_result is False,"SOURCE_IF_FALSE_BUT_ORIGINAL_RETURN_TRUE")
        need(base==["BASE_READY_TRUE"] or not base,
             "BASE_READY_FALSE_CONFLICTS_WITH_COMPOSITE_IF_FALSE")
        return "NATIVE_ORIGINAL_IF_FAILED_IN_CALL","SOURCE_IF_GUARD"
    if not outer:
        # No marker of a failed base/if branch: may be target selection,
        # sync, skill, moving option, another Native guard, or an override.
        if native_result:
            return "NATIVE_ORIGINAL_RETURN_TRUE_CAUSE_UNSPECIFIED","UNKNOWN"
        return "NATIVE_FALSE_LATER_OR_OVERRIDE_CAUSE_UNKNOWN","UNKNOWN"
    raise BranchReplayError("INVALID_OUTER_BRANCH_SEQUENCE")

def replay(log,frontier,stage,plan):
    need(plan.get("schema")==PLAN_SCHEMA and
         frontier.get("schema")==FRONTIER_SCHEMA and
         stage.get("schema")==STAGE_SCHEMA and
         plan.get("policy_id")==frontier.get("policy_id")==stage.get("policy_id")==POLICY and
         plan.get("source_revision")==frontier.get("source_revision")==stage.get("source_revision")==REV and
         plan.get("spec_key")==frontier.get("source_spec")==stage.get("source_spec") and
         plan.get("source_profile_git_blob")==frontier.get("source_profile_git_blob") and
         stage.get("selected_root")==frontier.get("selected_root") and
         plan.get("targets")==stage.get("targets")==frontier.get("targets") and
         frontier.get("physical_ability_ready_independent_of_Native_result")=="UNKNOWN" and
         frontier.get("WoW_current_Retail_priority")=="UNKNOWN" and
         stage.get("full_CALL_RUN_return_stack")=="UNKNOWN" and
         stage.get("native_post_not_independent_physical_ready") is True and
         stage.get("MAIN_promoted") is False,
         "UNBOUND_OR_PROMOTED_NATIVE_SOURCE_COHORT")
    selected=frontier["selected_root"]
    for k in ("t_ms","source_list","source_rank","source_action"):
        need(plan["selected_root"][k]==selected[k],"SELECTED_ORIGINAL_SOURCE_ROOT_DRIFT")
    begins,selects,pres,extras,returns=parse_markers(log)
    token=selected["dispatch_token"]
    need(token in begins and token in selects,"ORIGINAL_ROOT_BOUNDS_MISSING")
    opening=begins[token];closing=selects[token]
    need(opening[0]<closing[0] and opening[1]==closing[1]==selected["t_ms"] and
         opening[2]==closing[2],"FOREIGN_ORIGINAL_FOREGROUND_ROOT")
    branches=collect(log)
    calls={x["call_id"]:x for x in frontier["all_same_foreground_original_attempts_before_selected"]}
    need(len(calls)==frontier["preceding_attempt_count"]+1,"DUPLICATED_OR_MISSING_NATIVE_ATTEMPTS")
    result=[]
    for focus in plan["focus"]:
        rank=focus["source_rank"]
        need(type(rank) is int and 1<=rank<selected["source_rank"] and
             focus["source_list"]==selected["source_list"],
             "FOCUS_NOT_UPSTREAM_OF_EXACT_SELECTED_APL_ROOT")
        row=stage["source_rank_coverage"][rank-1]
        need(row["rank"]==rank and row["source_action"]==focus["source_action"] and
             row["native_visit_state"] in
             ("OBSERVED_NATIVE_ATTEMPT_FALSE","OBSERVED_NATIVE_ATTEMPT_TRUE") and
             row["physical_mechanic_ready"]=="UNKNOWN" and
             row["original_call_id"] is not None,
             "FOCUSED_SOURCE_ROW_NOT_NATIVE_ATTEMPT")
        id_=row["original_call_id"]
        need(id_ in calls and id_ in pres and id_ in returns,
             "NO_NATIVE_CALL_ID_FOR_FOCUS")
        attempt=calls[id_]
        before=pres[id_];after=returns[id_]
        need(attempt["list"]==selected["source_list"] and
             attempt["rank"]==rank and
             attempt["source_sha256"]==row["source_sha256"] and
             attempt["action"]==row["source_action"] and
             (attempt["original_action_ready_return"]=="TRUE")==after[3] and
             (row["original_action_ready_result"]=="TRUE")==after[3] and
             before["ptr"]==after[2] and
             before["t_ms"]==after[1]==selected["t_ms"] and
             opening[0]<before["line"]<after[0]<closing[0],
             "DIFFERENT_NATIVE_ACTION_CALL_OR_WRONG_PRE_POST_ORDER")
        bound=[b for b in branches if
               before["line"]<b["line"]<after[0] and
               b["t_ms"]==selected["t_ms"] and
               b["actor"]==opening[2] and b["action"]==before["ptr"]]
        need(len(bound)<=3,"EXCESSIVE_EVENTS_DURING_ONE_ORIGINAL_ACTION_READY")
        verdict,reason=interpret(bound,after[3])
        result.append({"source_rank":rank,"source_action":row["source_action"],
              "source_sha256":row["source_sha256"],"original_call_id":id_,
              "original_selected_root":selected,
              "original_NATIVE_action_ready_result":row["original_action_ready_result"],
              "in_call_native_branch_markers":[b["reason"] for b in bound],
              "native_causal_branch_classification":verdict,
              "first_original_ready_failure_guard":reason,
              "source_IF_independent_PRE_state":row["independent_IF_at_ATTEMPT_PRE"],
              "independent_physical_WoW_READY":"UNKNOWN",
              "source_APL_priority_user_promoted":False})
    need(len(result)==len(plan["focus"]),"UNVERIFIED_FOCUS_CARDINALITY")
    return {"schema":SCHEMA,"policy_id":POLICY,"source_revision":REV,
            "source_spec":plan["spec_key"],"targets":plan["targets"],
            "selected_root":selected,"focused_original_native_calls":result,
            "observed_original_branch_cause_scope":"ORIGINAL_SIMC_ACTION_READY_IN_CALL_ONLY",
            "no_additional_Native_ready_or_IF_calls":True,
            "source_IF_POST_not_independent_PRE":True,
            "complete_CALL_RUN_return_stack":"UNKNOWN",
            "WCL_blind_candidate_lock":"NOT_RUN",
            "physical_Retail_mechanic_READY":"UNKNOWN",
            "current_Retail_optimal_priority":"UNKNOWN",
            "General_Rotation_priority_rules_promoted":0,
            "target_dummy_wrong_cast":"UNKNOWN","MAIN_promoted":False}

def selftest():
    before=lambda code,n=1: [{"reason":code,"line":n}]
    good,why=interpret(before("BASE_COOLDOWN_NOT_READY")+before("COMPOSITE_BASE_READY_FALSE",2),False)
    need(good=="NATIVE_BASE_BRANCH_BASE_COOLDOWN_NOT_READY" and
         why=="BASE_COOLDOWN_NOT_READY","BASE_CAUSE_NOT_JOINED")
    safe,_=interpret([],False)
    need(safe=="NATIVE_FALSE_LATER_OR_OVERRIDE_CAUSE_UNKNOWN",
         "MISSING_CAUSAL_MARKER_MUST_REMAIN_UNKNOWN")
    safe2,_=interpret(before("COMPOSITE_BASE_READY_FALSE"),False)
    need(safe2=="NATIVE_OVERRIDE_READY_FALSE_CAUSE_UNKNOWN",
         "SUBCLASS_OVERRIDE_WAS_ASSUMED_READY")
    no=0
    for events,answer in (
        ([{"reason":"BASE_COOLDOWN_NOT_READY","line":1},
          {"reason":"BASE_INTERNAL_COOLDOWN_DOWN","line":2}],False),
        ([{"reason":"COMPOSITE_BASE_READY_FALSE","line":1},
          {"reason":"BASE_COOLDOWN_NOT_READY","line":2}],False),
        ([{"reason":"BASE_READY_TRUE","line":1},
          {"reason":"COMPOSITE_BASE_READY_FALSE","line":2},
          {"reason":"COMPOSITE_SOURCE_IF_FALSE","line":3}],False),
        ([{"reason":"BASE_COOLDOWN_NOT_READY","line":1},
          {"reason":"COMPOSITE_BASE_READY_FALSE","line":2}],True),
        ([{"reason":"BASE_COOLDOWN_NOT_READY","line":1},
          {"reason":"COMPOSITE_SOURCE_IF_FALSE","line":2}],False),
    ):
        try:interpret(events,answer)
        except BranchReplayError:no+=1
        else:raise AssertionError("AMBIGUOUS_ORIGINAL_CXX_BRANCH_ACCEPTED")
    need(no==5,"MISSING_BRANCH_REPLAY_NEGATIVES")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls":no,
            "missing_marker_infers_NOT_READY":False,
            "no_SimC_or_WCL_calls":True,
            "current_Retail_physical_READY":"UNKNOWN"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--prior-frontier",type=Path)
    p.add_argument("--prior-stage",type=Path)
    p.add_argument("--plan",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any(v is not None for v in vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(v is not None for v in vars(a).values()),"FULL_ORIGINAL_ROOT_PROOF_REQUIRED")
    log=a.native_log.read_text("utf-8")
    front=json.loads(a.prior_frontier.read_bytes())
    stage=json.loads(a.prior_stage.read_bytes())
    plan=json.loads(a.plan.read_bytes())
    evidence=replay(log,front,stage,plan)
    raw=(json.dumps(evidence,sort_keys=True,separators=(",",":"))+"\n").encode()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(raw)
    print("ORIGINAL_NATIVE_CAUSAL_BRANCH_SHA256="+sha256(raw).hexdigest())
    print("ORIGINAL_NATIVE_CAUSAL_BRANCH_COUNTS="+json.dumps({
        "root":evidence["selected_root"],
        "focused":[{"rank":x["source_rank"],
                    "cause":x["native_causal_branch_classification"],
                    "branch":x["in_call_native_branch_markers"]}
                   for x in evidence["focused_original_native_calls"]]},sort_keys=True))

if __name__=="__main__":main()
