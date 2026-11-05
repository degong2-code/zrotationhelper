#!/usr/bin/env python3
"""Generic source-stage General Rotation Decision IR for exact APL provenance.

The three inputs are independently replayed actual Original SimC evidence:
1. source actor/init_foreground inventory,
2. original action_t::init verifier returns (short-circuit preserved),
3. strict selected a->action_ready call roots and scoped method witnesses.

A source row can have multiple constructed native action objects, or multiple
identical source identities. No source-hash aggregate is a physical object ID.
Initialization and runtime attempts are deliberately separate axes. A certified
initialization rejection is NOT a candidate READY/NOT_READY or a dummy error.

This IR never changes the WCL-blind independent discovery path or declares
General Rotation source-order completeness. It is a reusable evidentiary layer,
not a Fury-specific rule policy.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_decision_proof_engine_v1 import (
    evaluate_priority, UNKNOWN
)
from general_rotation_apl_eligibility_replay_v1 import (
    SCHEMA as INIT_SCHEMA
)
from general_rotation_apl_init_guard_replay_v1 import (
    SCHEMA as GUARD_SCHEMA
)
from general_rotation_call_scope_replay_v1 import (
    SCHEMA as CALL_SCHEMA
)
from simc_apl_semantic_ir_v2 import parse_profile, git_blob

SCHEMA="ZrotGeneralRotationSourceStageEligibilityDecisionIRV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
HEX64=re.compile(r"[a-f0-9]{64}\Z")
STAGES=("INIT_ACTIONS_END","INIT_FINISHED_END")
INT_FIELDS=(
    "registered_mapped_instances","background_true","foreground_true",
    "active_list_true","mainhand_weapon_none_true","offhand_weapon_none_true")
GUARD_FIELDS=(
    "observed_init_guard_invocations","guard_false_level",
    "guard_false_spec","guard_false_weapon",
    "all_observed_guard_checks_passed")


class SourceStageIRError(ValueError):
    pass


def _check_rows(rows:dict,known:dict,fields:tuple[str,...],label:str):
    if not isinstance(rows,dict):
        raise SourceStageIRError(label+"_SOURCE_ROW_RECEIPT_REQUIRED")
    totals=0
    for h,data in rows.items():
        if h not in known or not HEX64.fullmatch(h):
            raise SourceStageIRError(label+"_UNKNOWN_SOURCE_APL_ROW")
        if not isinstance(data,dict) or data.get("source_action")!=known[h][0]["action"]:
            raise SourceStageIRError(label+"_SOURCE_ACTION_IDENTITY_DRIFT")
        if any(type(data.get(x)) is not int or data[x]<0 for x in fields):
            raise SourceStageIRError(label+"_INVALID_NONNEGATIVE_COUNTS")
        field0=fields[0]
        n=data[field0]
        if label.startswith("INIT"):
            if any(data[x]>n for x in fields[1:]):
                raise SourceStageIRError(label+"_IMPOSSIBLE_ACTOR_STATE_COUNT")
        else:
            failures=sum(data[x] for x in (
                "guard_false_level","guard_false_spec","guard_false_weapon"))
            if failures+data["all_observed_guard_checks_passed"]!=n:
                raise SourceStageIRError(label+"_GUARD_SOURCE_SHORT_CIRCUIT_COUNT")
        totals+=n
    return totals


def _clean_nonnegative_counter(rows:dict,known:dict,label:str):
    if not isinstance(rows,dict):
        raise SourceStageIRError(label+"_SOURCE_COUNTER_NOT_A_MAP")
    total=0
    for h,n in rows.items():
        if h not in known or type(n) is not int or n<=0:
            raise SourceStageIRError(label+"_UNMAPPED_SOURCE_ROW_OR_BAD_COUNT")
        total+=n
    return total


def compose(profile:bytes,init:dict,guards:dict,calls:dict)->dict:
    if not all(isinstance(x,dict) for x in (init,guards,calls)):
        raise SourceStageIRError("THREE_INDEPENDENT_SOURCE_REPLAYS_REQUIRED")
    if (init.get("schema")!=INIT_SCHEMA or guards.get("schema")!=GUARD_SCHEMA
        or calls.get("schema")!=CALL_SCHEMA):
        raise SourceStageIRError("SOURCE_REPLAYER_SCHEMA_MISMATCH")
    profile_blob=git_blob(profile)
    if (any(x!=profile_blob for x in (
            init.get("source_profile_git_blob_sha1"),
            guards.get("original_source_profile_git_blob_sha1"),
            calls.get("source_profile_git_blob_sha1")))
        or calls.get("root_and_parent_id_source")!=
             "EXPLICIT_GLOBAL_UNIQUE_CXX_RAII_STACK"
        or calls.get("source_virtual_dispatch_exhaustive") is not False
        or calls.get("positive_FULL_action_READY_proven")!=0
        or init.get("positive_action_READY_certified")!=0
        or guards.get("positive_FULL_ACTION_READY_proven")!=0
        or init.get("not_in_foreground_at_stage_is_not_NOT_READY_proof") is not True
        or guards.get("source_guard_failed_forces_init_background") is not True):
        raise SourceStageIRError("SOURCE_PROVENANCE_OR_OPEN_WORLD_GUARD_INVARIANT")
    parsed=parse_profile(profile,require_source=False)
    known=defaultdict(list)
    for owner,items in parsed["action_lists"].items():
        for ordinal,item in enumerate(items,1):
            h=item["source_sha256"]
            if not HEX64.fullmatch(h):
                raise SourceStageIRError("UNPINNED_NATIVE_SOURCE_ROW_HASH")
            known[h].append({
                "list":owner,"ordinal_one_based":ordinal,
                "action":item["action"]
            })
    if not known or any(len({x["action"] for x in locations})!=1
                       for locations in known.values()):
        raise SourceStageIRError("HASH_COLLISION_WITH_DIFFERENT_SOURCE_ACTIONS")
    by_stage=init.get("source_row_stage_observations_by_sha256")
    if not isinstance(by_stage,dict) or set(by_stage)!=set(STAGES):
        raise SourceStageIRError("MISSING_ORIGINAL_INIT_STAGE_ROW_INVENTORY")
    for stage in STAGES:
        count=_check_rows(by_stage[stage],known,INT_FIELDS,"INIT_"+stage)
        stage_record=init.get("stage_registry_receipts",{}).get(stage,{})
        if count!=stage_record.get("source_mapped_instances"):
            raise SourceStageIRError("SOURCE_MAPPED_INIT_TOTAL_DOES_NOT_RECONCILE")
    guard_rows=guards.get("source_row_init_guard_evidence_by_sha256")
    actual_guard_total=_check_rows(guard_rows,known,GUARD_FIELDS,"ORIGINAL_INIT_GUARD")
    if actual_guard_total!=guards.get("source_mapped_init_guard_invocations_total"):
        raise SourceStageIRError("ORIGINAL_INIT_GUARD_TOTAL_DOES_NOT_RECONCILE")
    attempts=calls.get("action_ready_call_roots_by_source_row_sha256")
    skips=calls.get("source_loop_background_skips_by_source_row_sha256")
    if _clean_nonnegative_counter(attempts,known,"SOURCE_READY_ROOT")!=calls.get(
            "selected_action_ready_original_calls"):
        raise SourceStageIRError("ACTUAL_ACTION_READY_ROOT_COUNT_MISMATCH")
    if _clean_nonnegative_counter(skips,known,"ORIGINAL_BACKGROUND_SKIP")!=calls.get(
            "source_loop_skips_before_action_READY"):
        raise SourceStageIRError("ACTUAL_SOURCE_SKIP_COUNT_MISMATCH")
    neg_calls=calls.get("independent_negative_method_calls_by_source_row_sha256")
    if not isinstance(neg_calls,dict):
        raise SourceStageIRError("NEGATIVE_METHOD_SOURCE_ROW_RECEIPT_REQUIRED")
    negative_by_row=defaultdict(dict)
    negative_total=0
    for key,n in neg_calls.items():
        if (not isinstance(key,str) or len(key)<66
            or key[64]!="." or key[:64] not in known
            or not key[65:] or type(n) is not int or n<=0):
            raise SourceStageIRError("NEGATIVE_METHOD_PROOF_NOT_SOURCE_GROUNDED")
        negative_by_row[key[:64]][key[65:]]=n
        negative_total+=n
    if negative_total!=calls.get("certified_false_method_returns"):
        raise SourceStageIRError("NEGATIVE_METHOD_SOURCE_COUNT_MISMATCH")
    rows=[]
    outcomes=Counter()
    confirmed_init_false=0
    physically_ambiguous=0
    for h,locations in sorted(known.items()):
        action=locations[0]["action"]
        by_init={
            stage:by_stage[stage].get(h)
            for stage in STAGES
        }
        finished=by_init["INIT_FINISHED_END"]
        current_guard=guard_rows.get(h)
        roots=attempts.get(h,0)
        skip_count=skips.get(h,0)
        method_neg=negative_by_row.get(h,{})
        fail_names=([
            name.removeprefix("guard_false_")
            for name in ("guard_false_level","guard_false_spec","guard_false_weapon")
            if current_guard and current_guard[name]>0
        ])
        rejected=sum(current_guard["guard_false_"+n] for n in fail_names) if current_guard else 0
        if (current_guard and finished and rejected>finished["background_true"]):
            raise SourceStageIRError("INIT_GUARD_FALSE_NOT_REFLECTED_IN_BACKGROUND")
        if (roots>0 and not finished):
            # Native attempts cannot be attributed to a source row which
            # this initialized actor never registered as mapped.
            raise SourceStageIRError("READY_ATTEMPT_NOT_PRESENT_IN_SOURCE_INIT")
        if len(locations)>1:
            init_state="DUPLICATE_SOURCE_ROW_IDENTITY_UNKNOWN"
            physically_ambiguous+=1
        elif finished is None:
            init_state="NOT_OBSERVED_IN_SOURCE_MAPPED_INIT_UNKNOWN"
        elif fail_names:
            init_state="SOURCE_INIT_GUARD_FALSE"
        elif finished["foreground_true"]==0:
            init_state="NOT_IN_FOREGROUND_AT_INIT"
        else:
            init_state="FOREGROUND_MEMBER_AT_INIT"
        if roots:
            runtime="ACTION_READY_CALLED"
        elif skip_count:
            runtime="BACKGROUND_SKIPPED_IN_SELECTION_LOOP"
        else:
            runtime="NO_ACTION_READY_CALL_OBSERVED_IN_BOUNDED_WINDOW"
        full_chain=(
            len(locations)==1 and
            rejected>0 and
            current_guard is not None and
            finished is not None and
            by_init["INIT_ACTIONS_END"] is not None and
            roots==0 and
            current_guard["observed_init_guard_invocations"]==
                finished["registered_mapped_instances"]==
                by_init["INIT_ACTIONS_END"]["registered_mapped_instances"]==
                rejected and
            finished["background_true"]==rejected and
            by_init["INIT_ACTIONS_END"]["background_true"]==rejected and
            finished["foreground_true"]==0 and
            by_init["INIT_ACTIONS_END"]["foreground_true"]==0
        )
        if full_chain:
            confirmed_init_false+=1
        outcomes[(init_state,runtime)]+=1
        rows.append({
            "source_row_sha256":h,"source_action":action,
            "source_locations":locations,
            "exact_unique_APL_source_location":len(locations)==1,
            "initialization_stage":init_state,
            "source_original_init_guard_failed_types":fail_names,
            "source_original_init_guard_observed_invocations":
                current_guard["observed_init_guard_invocations"] if current_guard else 0,
            "init_action_registered_instances":
                finished["registered_mapped_instances"] if finished else 0,
            "init_background_true_instances":
                finished["background_true"] if finished else 0,
            "init_foreground_true_instances":
                finished["foreground_true"] if finished else 0,
            "init_to_foreground_negative_causal_chain_proven":full_chain,
            "selection_stage":runtime,
            "original_action_ready_called_count":roots,
            "source_background_loop_skips_count":skip_count,
            "independent_method_negative_calls":dict(sorted(method_neg.items())),
            "method_negative_is_not_whole_action_NOT_READY":True,
            "physical_action_ready_decision":UNKNOWN,
            "source_order_priority_decision":UNKNOWN,
            "dummy_error_permitted":False,
        })
    priority=evaluate_priority(
        [{"decision":UNKNOWN} for _ in rows],
        None,source_order_complete=False)
    assert priority["decision"]=="UNKNOWN"
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "source_profile_git_blob_sha1":profile_blob,
        "source_stage_provenance":[INIT_SCHEMA,GUARD_SCHEMA,CALL_SCHEMA],
        "source_row_count":len(rows),
        "physical_source_row_ambiguous_count":physically_ambiguous,
        "observed_original_ready_call_roots":
            calls["selected_action_ready_original_calls"],
        "original_init_guard_fails_source_rows_confirmed":
            confirmed_init_false,
        "source_row_stage_outcome_counts":{
            f"{a}|{b}":n for (a,b),n in sorted(outcomes.items())
        },
        "source_row_decisions":rows,
        "source_frontier_proof":priority,
        "semantic_scope":"SIMC_SOURCE_INITIALIZATION_AND_BOUNDED_SELECTION_ONLY",
        "source_replay_full_READY_proven":0,
        "source_order_complete":False,
        "WCL_blind_candidate_discovery_semantics_injected":False,
        "actual_WCL_holdout_completed":False,
        "dummy_error_permitted":False,
        "WCL_API_calls":0
    }


def selftest()->dict:
    from hashlib import sha256
    profile=b'warrior="Synthetic"\nspec=fury\nactions=/rampage\n'
    action=parse_profile(profile,require_source=False)["action_lists"]["default"][0]
    h=action["source_sha256"]
    blob=git_blob(profile)
    def init_row(bg,fg):
        return {
            "source_action":"rampage","registered_mapped_instances":1,
            "background_true":bg,"foreground_true":fg,
            "active_list_true":0,"mainhand_weapon_none_true":0,
            "offhand_weapon_none_true":1
        }
    init={
        "schema":INIT_SCHEMA,"source_profile_git_blob_sha1":blob,
        "source_row_stage_observations_by_sha256":{
            "INIT_ACTIONS_END":{h:init_row(1,0)},
            "INIT_FINISHED_END":{h:init_row(1,0)}},
        "stage_registry_receipts":{
            stage:{"source_mapped_instances":1,
                   "registered_action_instances":1,
                   "unmapped_action_instances":0}
            for stage in STAGES},
        "positive_action_READY_certified":0,
        "not_in_foreground_at_stage_is_not_NOT_READY_proof":True
    }
    guard={
        "schema":GUARD_SCHEMA,
        "original_source_profile_git_blob_sha1":blob,
        "source_mapped_init_guard_invocations_total":1,
        "source_row_init_guard_evidence_by_sha256":{
            h:{"source_action":"rampage",
               "observed_init_guard_invocations":1,
               "guard_false_level":0,"guard_false_spec":0,
               "guard_false_weapon":1,
               "all_observed_guard_checks_passed":0}},
        "positive_FULL_ACTION_READY_proven":0,
        "source_guard_failed_forces_init_background":True
    }
    calls={
        "schema":CALL_SCHEMA,"source_profile_git_blob_sha1":blob,
        "root_and_parent_id_source":
            "EXPLICIT_GLOBAL_UNIQUE_CXX_RAII_STACK",
        "source_virtual_dispatch_exhaustive":False,
        "positive_FULL_action_READY_proven":0,
        "action_ready_call_roots_by_source_row_sha256":{},
        "source_loop_background_skips_by_source_row_sha256":{},
        "independent_negative_method_calls_by_source_row_sha256":{},
        "selected_action_ready_original_calls":0,
        "source_loop_skips_before_action_READY":0,
        "certified_false_method_returns":0
    }
    import copy
    actual=compose(profile,init,guard,calls)
    assert actual["original_init_guard_fails_source_rows_confirmed"]==1
    row=actual["source_row_decisions"][0]
    assert row["initialization_stage"]=="SOURCE_INIT_GUARD_FALSE"
    assert row["init_to_foreground_negative_causal_chain_proven"] is True
    assert row["physical_action_ready_decision"]=="UNKNOWN"
    assert actual["source_frontier_proof"]["decision"]=="UNKNOWN"
    for changed in (
        ("profile",b'warrior="Other"\nspec=fury\nactions=/rampage\n'),
        ("init",dict(init,source_profile_git_blob_sha1="0"*40)),
        ("guard",dict(guard,source_mapped_init_guard_invocations_total=2)),
        ("call",dict(calls,selected_action_ready_original_calls=1)),
        ("init",dict(init,source_row_stage_observations_by_sha256={
            "INIT_ACTIONS_END":{h:init_row(0,0)},
            "INIT_FINISHED_END":{h:init_row(0,0)}})),
    ):
        kind,bad=changed
        arguments={
            "profile":profile,"init":init,"guards":guard,"calls":calls
        }
        arguments[{"profile":"profile","init":"init","guard":"guards",
                   "call":"calls"}[kind]]=bad
        try:compose(**arguments)
        except SourceStageIRError:pass
        else:raise AssertionError("INCONSISTENT_SOURCE_STAGE_RECEIPT_ACCEPTED:"+kind)
    # A healthy foreground source row and an actual READY *call* are still
    # not a positive READY answer.
    fg=copy.deepcopy(init)
    for stage in STAGES:fg["source_row_stage_observations_by_sha256"][stage][h]=init_row(0,1)
    okg=copy.deepcopy(guard)
    rowg=okg["source_row_init_guard_evidence_by_sha256"][h]
    rowg["guard_false_weapon"]=0
    rowg["all_observed_guard_checks_passed"]=1
    activity=dict(calls,
        action_ready_call_roots_by_source_row_sha256={h:2},
        selected_action_ready_original_calls=2)
    healthy=compose(profile,fg,okg,activity)["source_row_decisions"][0]
    assert healthy["selection_stage"]=="ACTION_READY_CALLED"
    assert healthy["physical_action_ready_decision"]=="UNKNOWN"
    assert healthy["source_order_priority_decision"]=="UNKNOWN"
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":12,
        "source_init_negative_causality_proven_in_synthetic":True,
        "actual_original_Native_replayed":False,
        "positive_FULL_READY_proven":0,
        "dummy_verdict_permitted":False,
        "WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path)
    p.add_argument("--init-replay",type=Path)
    p.add_argument("--guard-replay",type=Path)
    p.add_argument("--call-replay",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    args=(a.profile,a.init_replay,a.guard_replay,a.call_replay)
    if all(x is None for x in args):result=selftest()
    elif all(x is not None for x in args):
        result=compose(
            a.profile.read_bytes(),
            json.loads(a.init_replay.read_bytes()),
            json.loads(a.guard_replay.read_bytes()),
            json.loads(a.call_replay.read_bytes()))
    else:p.error("provide all four source replay receipts and profile")
    raw=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
    else:print(raw.decode(),end="")


if __name__=="__main__":
    main()
