#!/usr/bin/env python3
"""Join all retained original SimC source-selected ROOT actions with actual PRE.

Existing original C++ was already passively instrumented. This module does
not rebuild a parallel APL parser or evaluate any readiness again. It joins
all original select_action returned source rows to their exact (possibly
nested) action_ready root by sweep ID / source row SHA, and the *same root*
PRE active_enemies and original resource numerator/max that were physically
read before the native action_ready() call. All original C++ root PRE records
and original selected returns MUST have been fully and independently replayed.

A source AST IF can be calculated from the exact original source PRE facts,
but an IF TRUE is NOT full physical READY, optimality or user guidance.
No secret WoW addon values, in-combat automation or WCL candidate injection.

No CLI parameters: bounded synthetic regression, safe for PyCharm.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import Expression,ast_symbols,evaluate_ast,truth,git_blob,parse_profile
from general_rotation_original_selected_root_state_join_v1 import _unique_leaf,ExactLeafSourceError
from general_rotation_original_selection_return_replay_v1 import SCHEMA as CHOICE_SCHEMA
from general_rotation_root_actor_pre_replay_v1 import SCHEMA as ACTOR_SCHEMA
from general_rotation_root_resource_pre_replay_v1 import SCHEMA as MANA_SCHEMA
from general_rotation_time_scoped_priority_ir_v1 import SCHEMA as SWEEP_SCHEMA
from general_rotation_source_eligibility_decision_ir_v1 import POLICY

SCHEMA="ZrotOriginalSourceAllRootSelectedStateV1"
HEX64=re.compile(r"[0-9a-f]{64}\Z")


class FullRootStateError(ValueError):
    pass


def need(ok:bool,label:str)->None:
    if not ok:raise FullRootStateError(label)


def _canonical_root_keys(mapping:dict)->dict:
    """Unify verified integer ID keys from direct replay and JSON string keys."""
    need(isinstance(mapping,dict),"SOURCE_ROOT_MAP_REQUIRED")
    fixed={}
    for raw,val in mapping.items():
        need((type(raw) is int and raw>0) or
             (type(raw) is str and raw.isdecimal() and
              str(int(raw))==raw and int(raw)>0),
             "INVALID_CPP_READY_ROOT_KEY")
        key=str(raw)
        need(key not in fixed,"ALIAS_OR_DUPLICATED_CPP_ROOT_ID")
        fixed[key]=val
    return fixed


def _cpp_leaf(sweeps:dict, children:dict, event:dict)->dict:
    item={
        "source_original_return_kind":event["return_kind"],
        "source_action":event["source_action"],
        "source_row_sha256":event["source_row_sha256"],
        "source_list":event["source_list"],
        "source_row_ordinal":event["source_ordinal"],
        "simc_ms":event["at_simc_ms"],
    }
    try:
        return _unique_leaf(sweeps,children,event["sweep_call_id"],item,item)
    except (ExactLeafSourceError,KeyError) as e:
        raise FullRootStateError("UNVERIFIED_NATIVE_SOURCE_LEAF_OR_ANCESTRY") from e


def join(temporal:dict, selected:dict, actor:dict, mana:dict,
         profile:bytes, target_count:int)->dict:
    """Full exact root-source ID join. No timestamp-only fallback."""
    need(type(target_count) is int and target_count>0,"TARGET_CONTEXT_EXPLICIT")
    blob=git_blob(profile)
    need(temporal.get("schema")==SWEEP_SCHEMA and
         selected.get("schema")==CHOICE_SCHEMA and
         actor.get("schema")==ACTOR_SCHEMA and
         mana.get("schema")==MANA_SCHEMA and
         temporal.get("product_policy_id")==POLICY and
         selected.get("product_policy_id")==POLICY and
         actor.get("product_policy_id")==POLICY and
         all(d.get("source_profile_git_blob_sha1")==blob for d in
             (temporal,selected,actor)) and
         temporal.get("target_count")==target_count and
         temporal.get("source_order_complete") is False and
         temporal.get("independent_FULL_READY_proven")==0 and
         selected.get("independent_FULL_READY_proven")==0 and
         actor.get("full_READY_proven")==0 and
         mana.get("full_READY_proven")==0 and
         selected.get("return_is_observed_original_simc_selection_not_independent_READY") is True and
         actor.get("source_actor_PRE_semantics")==
            "DIRECT_SIMC_CPP_BEFORE_ORIGINAL_READY_CALL" and
         actor.get("native_POST_result_not_used_as_AST_fact") is True and
         mana.get("source_CXX_before_call") is True and
         mana.get("not_WCL_strict_transition_pre") is True,
         "ORIGINAL_SOURCE_NATIVE_STATE_CONTRACT_MISMATCH")

    sweeps={}
    children=defaultdict(list)
    roots={}
    for sweep in temporal["observed_time_scoped_selection_frontiers"]:
        sid=sweep["sweep_call_id"]
        need(type(sid) is int and sid>0 and sid not in sweeps,
             "SOURCE_SELECTION_SWEEP_ID_NOT_UNIQUE")
        sweeps[sid]=sweep
        children[sweep["parent_sweep_call_id"]].append(sid)
        for ev in sweep["observed_candidate_event_stream"]:
            if ev.get("stage")!="ACTION_READY_CALLED":
                continue
            rid=ev.get("original_action_ready_root_id")
            need(type(rid) is int and rid>0 and rid not in roots,
                 "SOURCE_READY_ROOT_ID_NOT_UNIQUE")
            roots[rid]=(sweep,ev)
    ready_count=temporal.get("original_ready_calls")
    need(len(roots)==ready_count==actor.get("original_native_root_pre_total")==
         actor.get("all_exact_root_PRE_retained_count")==mana.get("root_count"),
         "SOURCE_ROOT_COHORT_NOT_FULLY_PRESERVED")
    original_actor=_canonical_root_keys(
        actor.get("all_exact_source_root_PRE_by_id"))
    original_mana=_canonical_root_keys(mana.get("root_mana_pct"))
    need(isinstance(original_actor,dict) and isinstance(original_mana,dict) and
         set(original_actor)==set(original_mana)==
             set(str(n) for n in roots),
         "SOURCE_ACTOR_MANA_PRE_SAME_ROOT_COVERAGE_BROKEN")
    source_lists=parse_profile(profile,require_source=False)["action_lists"]
    examples=selected.get("all_original_root_source_return_rows")
    original_count=selected.get("counts",{}).get(
        "root_sweep_returned_action_source_row")
    need(isinstance(examples,list) and len(examples)>0 and
         len(examples)==selected.get("all_original_root_return_count")==
            original_count,
         "ACTUAL_ALL_NATIVE_SOURCE_RETURNS_NOT_RETAINED")
    seen=set()
    records=[]
    aggregates=Counter()
    for index,entry in enumerate(examples,1):
        sid=entry.get("sweep_call_id")
        need(type(sid) is int and sid in sweeps and sid not in seen and
             sweeps[sid].get("parent_sweep_call_id")==0 and
             entry.get("full_READY")=="UNKNOWN" and
             entry.get("native_source_return_not_executed_cast") is True,
             "DUPLICATE_OR_FOREIGN_SOURCE_RETURN")
        seen.add(sid)
        owner=entry.get("source_list")
        ordinal=entry.get("source_ordinal")
        need(isinstance(owner,str) and owner in source_lists and
             type(ordinal) is int and 1<=ordinal<=len(source_lists[owner]),
             "RETURN_APL_SOURCE_LIST_ROW_NOT_FOUND")
        source=source_lists[owner][ordinal-1]
        need(source.get("source_sha256")==entry.get("source_row_sha256") and
             source.get("action")==entry.get("source_action") and
             isinstance(entry.get("source_row_sha256"),str) and
             HEX64.fullmatch(entry["source_row_sha256"]) is not None,
             "SOURCE_RETURN_PROFILE_ROW_HASH_NOT_IDENTICAL")
        source_if=source["expression_fields"].get("if")
        source_expression=None if source_if is None else source_if["source"]
        need(entry.get("source_if")==source_expression,
             "SOURCE_IF_EXPRESSION_RESTORED_INCORRECTLY")
        leaf=_cpp_leaf(sweeps,children,entry)
        rid=leaf["source_cpp_ready_root_id"]
        sw,ev=roots[rid]
        pre=original_actor[str(rid)]
        mana_pct=original_mana[str(rid)]
        need(pre.get("root_call_id")==rid and
             pre.get("source_row_sha256")==entry["source_row_sha256"] and
             pre.get("source_action")==entry["source_action"] and
             pre.get("source_list")==owner and
             pre.get("source_ordinal")==ordinal and
             pre.get("at_simc_ms")==entry.get("at_simc_ms")==
                 sw.get("at_simc_ms") and
             pre.get("original_cpp_pre_before_native_result_proven") is True and
             pre.get("not_WCL_transition_PRE") is True and
             pre.get("native_action_ready_POST") is True and
             ev.get("simc_NATIVE_return_post_comparator") is True and
             type(pre.get("observed_before_call_active_enemies")) is int and
             pre["observed_before_call_active_enemies"]==target_count and
             (mana_pct is None or
              (type(mana_pct) in (int,float) and math.isfinite(mana_pct)
               and mana_pct>=0)),
             "ORIGINAL_CPP_SELECTED_SOURCE_ROOT_PRE_IDENTITY_DRIFT")
        facts={"active_enemies":pre["observed_before_call_active_enemies"]}
        if mana_pct is not None:
            facts["mana.pct"]=mana_pct
        if source_if is None:
            result="NO_EXPLICIT_APL_IF"
            deps=[]
            missing=[]
            value=None
        else:
            ast=source_if["ast"]
            deps=sorted(ast_symbols(ast))
            value=truth(evaluate_ast(ast,facts))
            missing=sorted(set(deps)-set(facts))
            result=("INDEPENDENT_SAME_ROOT_SOURCE_IF_"+("TRUE" if value else "FALSE")
                    if value is not None else
                    "UNKNOWN_ADDITIONAL_APL_SYMBOLS")
        aggregates[result]+=1
        if value is False:
            aggregates["SOURCE_AST_CONFLICT_WITH_SELECTED_NATIVE_POST_TRUE"]+=1
        if leaf["was_child_propagated"]:
            aggregates["child_source_leaf"]=aggregates["child_source_leaf"]+1
        else:
            aggregates["direct_source_leaf"]=aggregates["direct_source_leaf"]+1
        if mana_pct is not None:
            aggregates["original_mana_PRE_observable"]+=1
        record={
            "choice_index":index,
            "at_simc_ms":entry["at_simc_ms"],
            "target_count_scenario":target_count,
            "top_level_original_cpp_sweep_id":sid,
            "selected_CPP_ready_root_id":rid,
            "original_CPP_source_select_path":leaf["source_cpp_select_path_sweep_ids"],
            "return_kind":entry["return_kind"],
            "source_list":owner,
            "source_ordinal":ordinal,
            "source_row_sha256":entry["source_row_sha256"],
            "action":entry["source_action"],
            "original_CPP_before_READY_PRE":{
                "active_enemies":facts["active_enemies"],
                "mana_pct":mana_pct,
                "mana_pct_status":("OBSERVED_BEFORE_ORIGINAL_READY" if mana_pct is not None
                                   else "UNKNOWN_ZERO_MANA_RESOURCE_MAX"),
                "exact_root_id_proven":True,
                "not_WCL_STRICT_PRE":True,
            },
            "source_apl_IF":{
                "source_expression":source_expression,
                "symbols":deps,"missing_explicit_symbols":missing,
                "independently_replayed_truth":value,"result":result,
                "original_native_POST_boolean_not_used_as_AST_fact":True,
            },
            "prior_original_native_false_count":entry["prior_native_false_observed"],
            "original_native_source_return_observed":True,
            "independent_full_READY_proven":False,
            "independent_prior_physical_NOT_READY_proven":False,
            "is_actual_player_spellcast_proven":False,
            "is_optimal_General_Rotation_rule":False,
            "dummy_user_error_verdict":"UNKNOWN",
        }
        records.append(record)
    need(len(seen)==original_count,"ALL_NATIVE_RETURN_SWEEPS_NOT_REPLAYED")
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "source_profile_git_blob_sha1":blob,
        "original_native_select_sweep_count":len(sweeps),
        "all_original_READY_root_PRE_count":len(roots),
        "source_root_states_physically_before_native_READY":True,
        "all_original_source_returned_rows":original_count,
        "all_returned_leaf_same_root_PRE_reconciled":len(records),
        "target_count":target_count,
        "source_if_independent_PRE_truth_counts":dict(sorted(aggregates.items())),
        "source_selected_rows":records,
        "complete_independent_full_READY_proven":0,
        "WCL_candidate_holdout_proven":False,
        "gameplay_feedback_permitted":False,
        "WCL_API_calls":0,
    }


def selftest()->dict:
    # This contract is tested against the actual four 30s original official
    # Native streams in CI; local fixtures focus on the narrow guarded join.
    from general_rotation_original_selected_root_state_join_v1 import _unique_leaf
    row="a"*64
    sample={"sweep_call_id":12,"at_simc_ms":0,"return_kind":"DIRECT",
            "source_list":"default","source_ordinal":1,"source_action":"foo",
            "source_row_sha256":row}
    sw={"sweep_call_id":12,"parent_sweep_call_id":0,
        "at_simc_ms":0,"source_list":"default",
        "observed_candidate_event_stream":[{
            "stage":"ACTION_READY_CALLED",
            "source_action":"foo","source_row_sha256":row,
            "ordinal_one_based":1,"source_init_stage":"FOREGROUND_MEMBER_AT_INIT",
            "original_action_ready_root_id":13,
            "simc_NATIVE_return_post_comparator":True}]}
    leaf=_cpp_leaf({12:sw},{},sample)
    assert leaf["source_cpp_ready_root_id"]==13
    assert leaf["was_child_propagated"] is False
    assert _canonical_root_keys({13:{"t":0}})=={"13":{"t":0}}
    assert _canonical_root_keys({"13":95.0})=={"13":95.0}
    try:_canonical_root_keys({13:95.0,"13":95.0})
    except FullRootStateError:pass
    else:raise AssertionError("ALIAS_ROOT_ID_ACCEPTED")
    import copy
    for bad in ("source_action","source_row_sha256","return_kind"):
        wrong=copy.deepcopy(sample)
        wrong[bad]="bar" if bad=="source_action" else ("b"*64 if bad=="source_row_sha256" else "CHILD_PROPAGATED")
        try:_cpp_leaf({12:sw},{},wrong)
        except FullRootStateError:pass
        else:raise AssertionError("SOURCE_ROOT_LEAF_TAMPER_NOT_REJECTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":8,"native_CPP_rebuilt":False,
            "independent_full_READY_proven":0,"WCL_API_calls":0}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--temporal",type=Path)
    p.add_argument("--selected",type=Path)
    p.add_argument("--actor-PRE",type=Path)
    p.add_argument("--mana-PRE",type=Path)
    p.add_argument("--simc-profile",type=Path)
    p.add_argument("--target-count",type=int)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    items=(a.temporal,a.selected,a.actor_PRE,a.mana_PRE,
           a.simc_profile,a.target_count)
    if all(v is None for v in items):
        value=selftest()
    elif all(v is not None for v in items):
        value=join(*[
            json.loads(x.read_bytes()) for x in
            (a.temporal,a.selected,a.actor_PRE,a.mana_PRE)],
            a.simc_profile.read_bytes(),a.target_count)
    else:
        p.error("all existing original Native source receipts/profile and target-count required")
    blob=(json.dumps(value,sort_keys=True,separators=(",",":"),
                     ensure_ascii=False,allow_nan=False)+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(blob)
    else:
        import sys
        sys.stdout.buffer.write(blob)


if __name__=="__main__":main()
