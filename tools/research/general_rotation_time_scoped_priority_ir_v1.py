#!/usr/bin/env python3
"""General Rotation generic time-scoped selection frontier research IR.

Combines a strict C++ original select_action sweep trace with source-stage
eligibility IR. It maintains *each* sweep invocation and parent separately,
even when timestamps/list/source row repeat. Each returned Native
action_ready Boolean remains a post comparator and never an independent
proof of READY. No cross-list priority is asserted from timestamp grouping.
Source IR may be from ST, 2-target or AoE: target count is explicit provenance.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_source_eligibility_decision_ir_v1 import (
    SCHEMA as ELIGIBILITY_SCHEMA, POLICY
)
from general_rotation_call_scope_replay_v1 import SCHEMA as SWEEP_REPLAY_SCHEMA
from simc_apl_semantic_ir_v2 import parse_profile,git_blob

SCHEMA="ZrotGeneralRotationTimeScopedSourcePriorityObservationIRV1"
VALID_EVENTS=frozenset((
    "ACTION_READY_CALLED","BACKGROUND_SKIP_BEFORE_READY","WAIT_ON_READY_BREAK"))
HEX=re.compile(r"[a-f0-9]{64}\Z")

class TimeFrontierError(ValueError):pass

def compose(profile:bytes,source:dict,scoped:dict,*,target_count:int)->dict:
    if type(target_count) is not int or not 1<=target_count<=40:
        raise TimeFrontierError("TARGET_COUNT_EXPLICIT_REQUIRED")
    source_blob=git_blob(profile)
    if (source.get("schema")!=ELIGIBILITY_SCHEMA or
        scoped.get("schema")!=SWEEP_REPLAY_SCHEMA or
        source.get("product_policy_id")!=POLICY or
        source.get("source_profile_git_blob_sha1")!=source_blob or
        scoped.get("source_profile_git_blob_sha1")!=source_blob or
        source.get("source_order_complete") is not False or
        source.get("source_replay_full_READY_proven")!=0 or
        source.get("dummy_error_permitted") is not False or
        scoped.get("source_virtual_dispatch_exhaustive") is not False or
        scoped.get("full_READY_in_any_frontier_proven") is not False):
        raise TimeFrontierError("TIME_FRONTIER_SOURCE_OR_OPEN_WORLD_CONTRACT")
    rows=source.get("source_row_decisions")
    if not isinstance(rows,list) or not rows:
        raise TimeFrontierError("SOURCE_STAGE_ROW_LEDGER_REQUIRED")
    ledger={}
    for item in rows:
        h=item.get("source_row_sha256")
        if (not isinstance(h,str) or not HEX.fullmatch(h) or h in ledger
            or item.get("physical_action_ready_decision")!="UNKNOWN"
            or item.get("source_order_priority_decision")!="UNKNOWN"):
            raise TimeFrontierError("SOURCE_ROW_PROVENANCE_OR_STAGE_UNKNOWN")
        ledger[h]=item
    profile_lists=parse_profile(profile,require_source=False)["action_lists"]
    sweeps=scoped.get("source_sweep_frontiers")
    if not isinstance(sweeps,list) or not sweeps:
        raise TimeFrontierError("EXACT_SOURCE_SWEEP_RECORDS_REQUIRED")
    if len(sweeps)!=scoped.get("source_selection_sweeps_observed"):
        raise TimeFrontierError("SWEEP_COUNT_MISMATCH")
    seen=set()
    seen_root=set()
    output=[]
    counts=Counter()
    native_comparator=Counter()
    root_total=0
    nested=0
    uncertain_order=0
    time_groups=Counter()
    for sw in sweeps:
        sid=sw.get("sweep_call_id"); parent=sw.get("parent_sweep_call_id")
        t=sw.get("at_simc_ms");owner=sw.get("source_list")
        mode=sw.get("execute_type")
        random=sw.get("list_random");skill=sw.get("effective_skill")
        span=sw.get("source_list_span_size")
        events=sw.get("observed_candidate_events")
        if (type(sid) is not int or sid<=0 or sid in seen
            or type(parent) is not int or parent<0
            or (parent and parent not in seen) or
            type(t) is not int or t<0 or owner not in profile_lists
            or type(mode) is not int or
            type(span) is not int or span<0
            or type(random) not in (float,int) or
            type(skill) not in (float,int) or
            not isinstance(events,list) or
            sw.get("full_READY_proven") is not False or
            sw.get("complete_source_order_proven") is not False):
            raise TimeFrontierError("INVALID_OR_DUPLICATE_CAUSAL_SWEEP")
        seen.add(sid);nested+=int(parent!=0);time_groups[t]+=1
        observable=[]
        # Whether SimC uses random list selection or skill-induced RNG is
        # source-visible, but not a license to declare any priority optimal.
        source_order_eligible=(random==0 and skill==1)
        uncertain_order+=int(not source_order_eligible)
        for ev in events:
            kind=ev.get("stage")
            if kind not in VALID_EVENTS:
                raise TimeFrontierError("UNDECLARED_ORIGINAL_SWEEP_EVENT")
            counts[kind]+=1
            if kind=="WAIT_ON_READY_BREAK":
                observable.append({
                    "stage":kind,"source_native_name":ev.get("source_native_name"),
                    "source_row_identity":"UNKNOWN",
                    "physical_action_ready":"UNKNOWN",
                    "priority_verdict":"UNKNOWN"})
                continue
            h=ev.get("source_row_sha256")
            row=ledger.get(h)
            ordinal=ev.get("ordinal_one_based")
            if (row is None or not isinstance(ordinal,int) or ordinal<=0 or
                not any(x["list"]==owner and
                        x["ordinal_one_based"]==ordinal
                        for x in row["source_locations"]) or
                row["source_action"]!=ev.get("source_action")):
                raise TimeFrontierError("CROSS_SWEEP_APL_ROW_OR_LIST_IDENTITY_DRIFT")
            item={
                "stage":kind,
                "source_row_sha256":h,"source_action":row["source_action"],
                "ordinal_one_based":ordinal,
                "source_init_stage":row["initialization_stage"],
                "physical_native_object_identity_proven":False,
                "physical_action_ready":"UNKNOWN",
                "priority_verdict":"UNKNOWN"}
            if kind=="ACTION_READY_CALLED":
                rid=ev.get("root_call_id")
                comparator=ev.get("native_ready_post_comparator")
                proofs=ev.get("independent_method_local_false_rules")
                if (type(rid) is not int or rid<=0 or rid in seen_root or
                    type(comparator) is not bool or
                    not isinstance(proofs,list) or
                    any(not isinstance(x,str) or not x for x in proofs)):
                    raise TimeFrontierError("READY_ROOT_ID_OR_POST_COMPARATOR_NOT_EXACT")
                seen_root.add(rid);root_total+=1
                native_comparator[comparator]+=1
                item.update({
                    "original_action_ready_root_id":rid,
                    "simc_NATIVE_return_post_comparator":comparator,
                    "comparator_proves_independent_ready":False,
                    "independent_method_local_false_rules":proofs,
                    "method_false_does_not_prove_entire_action_NOT_READY":True})
            observable.append(item)
        output.append({
            "sweep_call_id":sid,"parent_sweep_call_id":parent,
            "at_simc_ms":t,"source_list":owner,
            "execute_type":mode,"source_list_random":random,
            "effective_skill_after_debuff":skill,
            "source_list_executable_span_size":span,
            "source_order_sampling_deterministic":source_order_eligible,
            "observed_candidate_event_stream":observable,
            "full_source_priority_frontier_closed":False,
            "conditional_priority_verdict":"UNKNOWN",
            "opener_optimality_proven":False})
    if (nested!=scoped.get("source_selection_nested_sweep_calls") or
        root_total!=scoped.get("selected_action_ready_original_calls") or
        root_total!=source.get("observed_original_ready_call_roots") or
        native_comparator[True]!=scoped.get(
            "original_native_ready_return_post_comparators",{}).get("true") or
        native_comparator[False]!=scoped.get(
            "original_native_ready_return_post_comparators",{}).get("false") or
        counts["WAIT_ON_READY_BREAK"]!=scoped.get("source_wait_on_ready_breaks") or
        counts["BACKGROUND_SKIP_BEFORE_READY"]!=scoped.get(
            "source_loop_skips_before_action_READY")):
        raise TimeFrontierError("SELECTION_SWEEP_AGGREGATES_NOT_RECONCILED")
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "source_profile_git_blob_sha1":source_blob,
        "target_count":target_count,
        "source_sweep_count":len(output),
        "nested_source_sweep_count":nested,
        "same_timestamp_multiple_distinct_sweeps":sum(
            c for c in time_groups.values() if c>1),
        "non_source_order_sweeps":uncertain_order,
        "original_ready_calls":root_total,
        "native_post_comparator_true":native_comparator[True],
        "native_post_comparator_false":native_comparator[False],
        "observed_candidate_event_types":dict(sorted(counts.items())),
        "observed_time_scoped_selection_frontiers":output,
        "early_observed_selection_frontiers":output[:12],
        "source_order_complete":False,
        "independent_FULL_READY_proven":0,
        "priority_rule_optimality_proven":False,
        "WCL_independent_blind_candidate_lock_maintained":True,
        "dummy_error_permitted":False,
        "WCL_API_calls":0
    }

def selftest():
    profile=b'warrior="Synthetic"\nspec=fury\nactions=/rampage\n'
    h=parse_profile(profile,require_source=False)["action_lists"]["default"][0]["source_sha256"]
    blob=git_blob(profile)
    loc={"list":"default","ordinal_one_based":1,"action":"rampage"}
    source={
        "schema":ELIGIBILITY_SCHEMA,"product_policy_id":POLICY,
        "source_profile_git_blob_sha1":blob,
        "source_row_decisions":[{
            "source_row_sha256":h,"source_action":"rampage",
            "source_locations":[loc],
            "initialization_stage":"FOREGROUND_MEMBER_AT_INIT",
            "physical_action_ready_decision":"UNKNOWN",
            "source_order_priority_decision":"UNKNOWN"}],
        "source_order_complete":False,
        "source_replay_full_READY_proven":0,
        "dummy_error_permitted":False,
        "observed_original_ready_call_roots":2
    }
    def attempt(rid,returned):
        return {"stage":"ACTION_READY_CALLED","root_call_id":rid,
                "source_row_sha256":h,"source_action":"rampage",
                "ordinal_one_based":1,
                "native_ready_post_comparator":returned,
                "independent_method_local_false_rules":[]}
    def sweep(id,parent,event):
        return {"sweep_call_id":id,"parent_sweep_call_id":parent,
            "at_simc_ms":100,"source_list":"default",
            "execute_type":0,"list_random":0.0,"effective_skill":1.0,
            "source_list_span_size":1,
            "observed_candidate_events":[event],
            "full_READY_proven":False,"complete_source_order_proven":False}
    scoped={
        "schema":SWEEP_REPLAY_SCHEMA,
        "source_profile_git_blob_sha1":blob,
        "source_virtual_dispatch_exhaustive":False,
        "full_READY_in_any_frontier_proven":False,
        "source_sweep_frontiers":[sweep(10,0,attempt(11,False)),
                                  sweep(20,0,attempt(21,True))],
        "source_selection_sweeps_observed":2,
        "source_selection_nested_sweep_calls":0,
        "selected_action_ready_original_calls":2,
        "original_native_ready_return_post_comparators":{"true":1,"false":1},
        "source_wait_on_ready_breaks":0,
        "source_loop_skips_before_action_READY":0
    }
    import copy
    a=compose(profile,source,scoped,target_count=2)
    assert a["source_sweep_count"]==2
    assert a["same_timestamp_multiple_distinct_sweeps"]==2
    assert a["native_post_comparator_false"]==1
    assert a["independent_FULL_READY_proven"]==0
    assert all(s["conditional_priority_verdict"]=="UNKNOWN"
               for s in a["observed_time_scoped_selection_frontiers"])
    forged=[
        dict(scoped,selected_action_ready_original_calls=1),
        dict(scoped,original_native_ready_return_post_comparators={
            "true":2,"false":0}),
        dict(scoped,source_sweep_frontiers=[
            sweep(10,0,attempt(11,False)),
            sweep(10,0,attempt(21,True))]),
        dict(scoped,source_sweep_frontiers=[
            sweep(10,0,attempt(11,False)),
            sweep(20,999,attempt(21,True))]),
        dict(scoped,source_sweep_frontiers=[
            sweep(10,0,attempt(11,False)),
            sweep(20,0,attempt(11,True))]),
    ]
    for bad in forged:
        try:compose(profile,source,bad,target_count=2)
        except TimeFrontierError:pass
        else:raise AssertionError("UNSCOPED_OR_SPOOFED_TEMPORAL_FRONTIER_ACCEPTED")
    try:compose(profile,source,scoped,target_count=0)
    except TimeFrontierError:pass
    else:raise AssertionError("TARGET_COUNT_NOT_EXPLICITLY_VALIDATED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":11,"actual_original_Native_replayed":False,
        "independent_FULL_READY_proven":0,
        "WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path)
    p.add_argument("--source-stage-ir",type=Path)
    p.add_argument("--original-sweep-replay",type=Path)
    p.add_argument("--target-count",type=int)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if all(x is None for x in (a.profile,a.source_stage_ir,a.original_sweep_replay,a.target_count)):
        result=selftest()
    elif all(x is not None for x in (a.profile,a.source_stage_ir,a.original_sweep_replay,a.target_count)):
        result=compose(a.profile.read_bytes(),
            json.loads(a.source_stage_ir.read_bytes()),
            json.loads(a.original_sweep_replay.read_bytes()),
            target_count=a.target_count)
    else:p.error("profile, stage IR, sweep replay and target count required together")
    raw=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
    else:print(raw.decode(),end="")

if __name__=="__main__":main()
