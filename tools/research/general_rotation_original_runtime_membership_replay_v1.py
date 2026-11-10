#!/usr/bin/env python3
"""Generic original Native APL source -> initialized foreground action audit.

Consumes the same original SimC log as previously certified candidate-stage and
action_ready PRE/frontier. Each runtime list-entry inventory is joined to the
source-pinned original row by signature pointer, list and priority index, then
to original selected-root stage events. A missing row never implies NOT_READY.
No-arg runs synthetic fail-closed tests; CLI writes successor evidence only.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from general_rotation_original_attempt_frontier_v1 import (
    parse_markers, pointer, numeric, POLICY, REV, SCHEMA as FRONTIER_SCHEMA,
    BEGIN, SELECT, PRE, EXTRA, RESULT
)
from general_rotation_original_candidate_stage_replay_v1 import (
    load_stages, SCHEMA as STAGE_SCHEMA, MARK as STAGE_MARK
)

SCHEMA="ZrotOriginalNativeAPLSourceRuntimeMembershipReplayV1"
MARK="ZROT_ORIGINAL_APL_FOREGROUND_MEMBERSHIP_V1|"
SOURCE_SCHEMA="ZrotSourceFaithfulSimcAplSemanticIRV2"

class MembershipError(ValueError):pass

def need(ok,why):
    if not ok:raise MembershipError(why)

def load_inventory(log:str):
    result=[]
    for line_no,line in enumerate(log.splitlines()):
        if MARK not in line:continue
        need(line.count(MARK)==1,"DUPLICATED_APL_INVENTORY_MARKER")
        p=line.split(MARK,1)[1].strip().split("|")
        need(len(p)==9,"RUNTIME_INVENTORY_TOKEN_ARITY_DRIFT")
        t,actor,owner,rank,ptr,count,fg,bg,seq=p
        rank=numeric(rank);count=numeric(count)
        need(owner and re.fullmatch(r"[a-z0-9_]+",owner) is not None and
             rank>=1 and count in (0,1) and fg in ("0","1") and
             bg in ("-1","0","1") and seq in ("-1","0","1"),
             "RUNTIME_INVENTORY_SOURCE_OR_FLAG_INVALID")
        actor=pointer(actor)
        if count:
            ptr=pointer(ptr)
            need(bg in ("0","1") and seq in ("0","1"),
                 "BOUND_ACTION_HAS_MISSING_NATIVE_FLAGS")
        else:
            need(ptr in ("0x0","(nil)") and fg=="0" and bg==seq=="-1",
                 "UNBOUND_ACTION_HAS_FOREGROUND_OR_FLAGS")
        if fg=="1":
            need(count==1,"MULTI_OR_NULL_INSTANCE_CLAIMED_FOREGROUND")
        result.append({"line":line_no,"t_ms":numeric(t),"actor":actor,
                       "list":owner,"rank":rank,"ptr":ptr,"bound_count":count,
                       "foreground":fg=="1","background":bg,"sequence":seq})
    need(result and len(result)<=100000,"EMPTY_OR_UNBOUNDED_APL_RUNTIME_INVENTORY")
    return result

def class_for(x):
    if x["bound_count"]==0:return "NO_BOUND_NATIVE_ACTION_SIGNATURE"
    if x["foreground"]:return "IN_ORIGINAL_FOREGROUND_LIST"
    if x["background"]=="1" and x["sequence"]=="1":
        return "ABSENT_BACKGROUND_AND_SEQUENCE"
    if x["background"]=="1":return "ABSENT_BACKGROUND_FLAG"
    if x["sequence"]=="1":return "ABSENT_SEQUENCE_FLAG"
    return "ABSENT_UNKNOWN_INIT_OR_RUNTIME_CAUSE"

def audit(log:str,source:dict,stage:dict,frontier:dict):
    need(stage.get("schema")==STAGE_SCHEMA and
         frontier.get("schema")==FRONTIER_SCHEMA and
         stage.get("policy_id")==frontier.get("policy_id")==POLICY and
         stage.get("source_revision")==frontier.get("source_revision")==REV and
         stage.get("selected_root")==frontier.get("selected_root") and
         stage.get("source_spec")==frontier.get("source_spec") and
         stage.get("targets")==frontier.get("targets") and
         stage.get("current_Retail_priority")=="UNKNOWN" and
         source.get("schema")==SOURCE_SCHEMA,
         "UNBOUND_NATIVE_SOURCE_STAGE_OR_FRONTIER")
    roots,selects,pre,extra,returned=parse_markers(log)
    stages=load_stages(log)
    inventory=load_inventory(log)
    chosen=stage["selected_root"]
    token=chosen["dispatch_token"]
    need(token in roots and token in selects,"SELECTED_FOREGROUND_ROOT_MISSING")
    opening=roots[token];closing=selects[token]
    need(opening[0]<closing[0] and opening[2]==closing[2] and
         chosen["t_ms"]==opening[1]==closing[1],
         "SAME_ROOT_ACTOR_CLOCK_DRIFT")
    selected=[s for s in stages if
              opening[0]<s["line"]<closing[0] and
              s["t_ms"]==chosen["t_ms"] and s["stage"]=="ATTEMPT" and
              s["source_list"]==chosen["source_list"] and
              s["source_rank"]==chosen["source_rank"] and
              s["ptr"]==closing[3]]
    need(len(selected)==1,"SELECTED_STAGE_AMBIGUOUS_OR_ABSENT")
    choice=selected[0]
    source_list=chosen["source_list"]
    rows=source["action_lists"].get(source_list)
    need(rows and rows[chosen["source_rank"]-1]["action"]==chosen["source_action"],
         "SELECTED_SOURCE_ACTION_OR_LIST_DRIFT")
    n=len(rows)
    matches=[x for x in inventory if
             opening[0]<x["line"]<choice["line"] and
             x["list"]==source_list and x["actor"]==opening[2] and
             x["t_ms"]==chosen["t_ms"]]
    need(len(matches)>=n,"MISSING_SOURCE_LIST_RUNTIME_MEMBERSHIP_SNAPSHOT")
    last=matches[-n:]
    need([x["rank"] for x in last]==list(range(1,n+1)) and
         len({x["actor"] for x in last})==1 and
         last[-1]["line"]<choice["line"],
         "SOURCE_LIST_NATIVE_INVENTORY_NOT_CONTIGUOUS_AND_COMPLETE")
    # A runtime inventory is a list-entry observation. It precedes all later
    # candidate-stage and native action_ready events, never a POST fill for PRE.
    row_by_rank={x["rank"]:x for x in last}
    chosen_instance=row_by_rank[chosen["source_rank"]]
    need(chosen_instance["bound_count"]==1 and chosen_instance["foreground"] and
         chosen_instance["ptr"]==choice["ptr"] and
         chosen_instance["background"]=="0" and chosen_instance["sequence"]=="0",
         "SELECTED_ORIGINAL_ACTION_NOT_IN_INITIALIZED_FOREGROUND")
    observed=stage["source_rank_coverage"]
    need(len(observed)==chosen["source_rank"]-1,
         "MISSING_UPSTREAM_CANDIDATE_COVERAGE")
    native_stages=[x for x in stages if
                   opening[0]<x["line"]<closing[0] and
                   x["source_list"]==source_list and
                   x["t_ms"]==chosen["t_ms"]]
    result=[]
    for i,sr in enumerate(observed):
        rank=i+1;info=row_by_rank[rank]
        src=rows[i]
        need(sr["rank"]==rank and sr["source_action"]==src["action"] and
             sr["source_sha256"]==src["source_sha256"],
             "PRIOR_STAGE_SOURCE_RANK_OR_HASH_MISMATCH")
        visit=[e for e in native_stages if e["source_rank"]==rank and
               e["line"]<choice["line"]]
        prior_state=sr["native_visit_state"]
        if prior_state=="UNOBSERVED_IN_SAME_RUNTIME_SCAN":
            need(not visit,"STAGE_MARKER_PRESENT_BUT_PRIOR_CLAIMS_UNOBSERVED")
            state="UNOBSERVED"
        else:
            need(visit and info["bound_count"]==1 and info["foreground"] and
                 any(v["ptr"]==info["ptr"] for v in visit),
                 "RUNTIME_MEMBER_MISSING_FOR_NATIVE_VISITED_ROW")
            state="VISITED"
        reason=class_for(info)
        result.append({"rank":rank,"source_action":src["action"],
                       "source_behavior":src["behavior"],
                       "source_sha256":src["source_sha256"],
                       "runtime_signature_bound_count":info["bound_count"],
                       "native_foreground_membership":info["foreground"],
                       "native_background_flag":info["background"],
                       "native_sequence_flag":info["sequence"],
                       "runtime_membership_class":reason,
                       "same_root_stage_visit":state,
                       "original_action_ready_result":sr["original_action_ready_result"],
                       "instance_specific_reason_for_background_flag":"UNKNOWN",
                       "independent_physical_ready":"UNKNOWN"})
        if state=="UNOBSERVED":
            need(sr["original_action_ready_result"]=="NOT_CALLED",
                 "UNVISITED_NATIVE_ACTION_WAS_INFERRED_READY")
    absent=[x for x in result if x["same_root_stage_visit"]=="UNOBSERVED"]
    return {"schema":SCHEMA,"policy_id":POLICY,"source_revision":REV,
            "source_spec":stage["source_spec"],"targets":stage["targets"],
            "selected_root":chosen,
            "selected_root_original_foreground_membership":"PRESENT",
            "snapshot_list_source_row_count":n,
            "runtime_membership_snapshot_precedes_selected_ATTEMPT":True,
            "original_signature_source_row_binding":"EXACT_POINTER_MATCH",
            "same_root_upper_source_rows":result,
            "unvisited_source_row_membership_states":[
                {"rank":x["rank"],"action":x["source_action"],
                 "membership":x["runtime_membership_class"]}
                for x in absent],
            "classification_counts":dict(Counter(x["runtime_membership_class"] for x in result)),
            "source_rank_not_visited_is_NOT_READY":False,
            "native_background_flag_CAUSE":"UNKNOWN",
            "current_Retail_gameplay_ready":"UNKNOWN",
            "WCL_independent_holdout":"NOT_RUN",
            "General_Rotation_priority_promoted":0,
            "dummy_wrong_cast":"UNKNOWN",
            "MAIN_promoted":False}

def selftest():
    def row(name):
        return {"action":name,"behavior":"ACTION","source_sha256":"sha-"+name}
    source={"schema":SOURCE_SCHEMA,"action_lists":{"sub":[row("alpha"),row("beta"),row("gamma")]}}
    chosen={"t_ms":100,"call_id":10,"dispatch_token":1,
            "source_list":"sub","source_rank":3,"source_action":"gamma",
            "native_action_ready_return":True}
    above=[{"rank":1,"source_action":"alpha","source_sha256":"sha-alpha",
            "native_visit_state":"OBSERVED_NATIVE_ATTEMPT_FALSE",
            "original_action_ready_result":"FALSE"},
           {"rank":2,"source_action":"beta","source_sha256":"sha-beta",
            "native_visit_state":"UNOBSERVED_IN_SAME_RUNTIME_SCAN",
            "original_action_ready_result":"NOT_CALLED"}]
    stage={"schema":STAGE_SCHEMA,"policy_id":POLICY,"source_revision":REV,
           "source_spec":"synthetic","targets":1,"selected_root":chosen,
           "source_rank_coverage":above,"current_Retail_priority":"UNKNOWN"}
    frontier={"schema":FRONTIER_SCHEMA,"policy_id":POLICY,"source_revision":REV,
              "source_spec":"synthetic","targets":1,"selected_root":chosen}
    events=[BEGIN+"100|1|0x01"]
    def inv(rank,ptr,count,fg,bg,seq):
        return MARK+f"100|0x01|sub|{rank}|{ptr}|{count}|{fg}|{bg}|{seq}"
    events += [inv(1,"0x11",1,1,0,0),inv(2,"0x22",1,0,1,0),
               inv(3,"0x33",1,1,0,0)]
    def action(rank,ptr,call,res):
        return [STAGE_MARK+f"100|sub|sub|{rank}|{ptr}|ATTEMPT",
                PRE+f"100|{call}|sub|{rank}|{ptr}|0|0",
                EXTRA+f"100|{call}|{ptr}|"+'a'*64+"|1|1",
                RESULT+f"100|{call}|{ptr}|{res}"]
    events+=action(1,"0x11",9,0)+action(3,"0x33",10,1)
    events += [SELECT+"100|1|0x01|0x33"]
    original="\n".join(events)
    got=audit(original,source,stage,frontier)
    need(got["unvisited_source_row_membership_states"]==[
        {"rank":2,"action":"beta","membership":"ABSENT_BACKGROUND_FLAG"}] and
        got["General_Rotation_priority_promoted"]==0,
        "SYNTHETIC_ABSENT_BACKGROUND_FLAG_WRONGLY_PROMOTED")
    # A row may be in the initialized foreground list but not visited during
    # this call (e.g. random selection or early return). This is a valid
    # UNKNOWN path, NOT a proof of action readiness or of an invalid trace.
    present_but_unvisited=original.replace(
        inv(2,"0x22",1,0,1,0),inv(2,"0x22",1,1,0,0))
    valid_missing=audit(present_but_unvisited,source,stage,frontier)
    need(valid_missing["unvisited_source_row_membership_states"]==[
        {"rank":2,"action":"beta","membership":"IN_ORIGINAL_FOREGROUND_LIST"}] and
        valid_missing["source_rank_not_visited_is_NOT_READY"] is False,
        "UNVISITED_BUT_IN_FOREGROUND_OVERCLASSIFIED")
    neg=0
    for broken in (
        original.replace(inv(2,"0x22",1,0,1,0),""),
        original.replace(inv(3,"0x33",1,1,0,0),inv(3,"0x99",1,1,0,0)),
        original.replace(inv(1,"0x11",1,1,0,0),inv(1,"0x11",2,1,0,0)),
        original.replace(inv(1,"0x11",1,1,0,0),inv(1,"0x11",1,0,1,0)),
        original.replace(inv(2,"0x22",1,0,1,0),inv(2,"0x22",0,1,-1,-1)),
        original.replace(SELECT+"100|1|0x01|0x33",SELECT+"100|1|0x01|0x11"),
        original.replace(MARK,"CORRUPTED_MARKER")
    ):
        try:audit(broken,source,stage,frontier)
        except (MembershipError,ValueError):neg+=1
        else:raise AssertionError("ACCEPTED_INVALID_SOURCE_SIGNATURE_OR_VISIT")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls_rejected":neg,
            "physical_NOT_READY_claims":0,
            "WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--profile",type=Path)
    p.add_argument("--prior-stage",type=Path)
    p.add_argument("--prior-frontier",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(vars(a).values()),"EXPLICIT_NATIVE_SOURCE_MEMBERSHIP_INPUTS_REQUIRED")
    from simc_apl_semantic_ir_v2 import parse_profile, canonical,git_blob
    raw=a.profile.read_bytes();front=json.loads(a.prior_frontier.read_bytes())
    need(git_blob(raw)==front.get("source_profile_git_blob"),
         "ORIGINAL_SOURCE_PROFILE_BLOB_DRIFT")
    stage=json.loads(a.prior_stage.read_bytes())
    result=audit(a.native_log.read_text("utf-8"),
                 parse_profile(raw,require_source=False),stage,front)
    result["prior_stage_sha256"]=sha256(a.prior_stage.read_bytes()).hexdigest()
    result["prior_frontier_sha256"]=sha256(a.prior_frontier.read_bytes()).hexdigest()
    result["source_profile_git_blob"]=front["source_profile_git_blob"]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canonical(result))
    print("ORIGINAL_APL_SOURCE_RUNTIME_MEMBERSHIP_SHA256="+sha256(a.out.read_bytes()).hexdigest())
    print("ORIGINAL_APL_SOURCE_RUNTIME_MEMBERSHIP_COUNTS="+json.dumps({
        "targets":result["targets"],
        "selected_root":result["selected_root"],
        "classes":result["classification_counts"],
        "unvisited":result["unvisited_source_row_membership_states"]},
        sort_keys=True))

if __name__=="__main__":main()
