#!/usr/bin/env python3
"""Link source-backed foreground NOT_READY guards to both Slayer APL lists.

Spec identity is already locked in input receipts; action row names come from
the source-derived SimC IR, never WCL candidate discovery. Do not choose ST
or AoE without active_enemies at the WCL decision. A negative ready() guard
can remove rows in the SimC source model, but remaining rows are not proven
READY, and no player mistake or best-action conclusion follows.

The two branch counts are *mutually exclusive hypothetical branches*, never
two distinct gameplay opportunities. Safe no-arguments self-test.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from simc_ordered_if_else_general_rotation_ir_v1 import decide

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
IR_SHA="206e3a39d83d9abbe7e770ad6c7c963facc18c6485337b9734f6a9a3cdecc1d5"
READY_SHA="3be8e946b9b15f5ae8a5a5e1e29f7729d752ff93f461f1b4d37b2cb233b7f6e6"

class SourceGateError(ValueError):pass

def sha(data):return hashlib.sha256(data).hexdigest()

def read_pinned(path,expected):
    raw=path.read_bytes()
    if not 10<len(raw)<1_000_000 or sha(raw)!=expected:
        raise SourceGateError("SOURCE_RECEIPT_SHA_UNVERIFIED")
    def unique(pairs):
        obj={}
        for k,v in pairs:
            if k in obj:raise SourceGateError("DUPLICATE_JSON_KEY")
            obj[k]=v
        return obj
    return json.loads(raw,object_pairs_hook=unique)

def apply_lists(ir,ready):
    if (ir.get("schema")!="ZrotSimcSlayerConditionalPriorityResearchIRV1"
        or ir.get("scope_policy_id")!=POLICY
        or ready.get("schema")!="ZrotSourceReadyNegativeProofAndWclStrictPreV1"
        or ready.get("scope_policy_id")!=POLICY
        or ready.get("total_actor_casts")!=105
        or ready.get("source_model_false_ready_action_contexts")!=188
        or ready.get("game_cd_charge_state_verified") is not False
        or ir.get("active_enemies_at_WCL_cast")!="UNKNOWN"
        or ready.get("simc_patch_and_player_full_build_equivalence")!="UNKNOWN"):
        raise SourceGateError("IR_SOURCE_OR_NEGATIVE_GATE_AUTHORITY_CHANGED")
    ordered=ir.get("source_list_rows")
    if not isinstance(ordered,dict) or set(ordered)!={"slayer","slayer_aoe"}:
        raise SourceGateError("MISSING_SLAYER_BRANCH_IR")
    if len(ordered["slayer"])!=22 or len(ordered["slayer_aoe"])!=14:
        raise SourceGateError("PINNED_SOURCE_APL_ROW_COUNT_DRIFT")

    groups={}
    for role,expected in (("discovery",54),("holdout",51)):
        recorded=ready[role]["actions"]
        if len(recorded)!=expected:raise SourceGateError("WCL_ACTION_RECEIPT_COUNT_DRIFT")
        hero=ir["hero_gates_at_wcl"][role]
        for name in ordered:
            if hero[name]["verdict"]!="TALENT_GUARD_TRUE_TARGET_COUNT_UNKNOWN":
                raise SourceGateError("SOURCE_HERO_GUARD_NOT_PROVEN")
        counters={name:Counter() for name in ordered}
        rows=[]
        for i,item in enumerate(recorded):
            blocked=set(item["source_model_nonreadiness_proven_actions"])
            semantic=item["candidate_foreground_actions"]
            if blocked!={name for name,v in semantic.items()
                if v["source_ready_guard_status"]=="SOURCE_MODEL_BLOCKED_FOREGROUND"}:
                raise SourceGateError("NEGATIVE_SOURCE_CONTRADICTION")
            branch={}
            for name,ordered_rows in ordered.items():
                false_rows=[r["index"] for r in ordered_rows if r["action"] in blocked]
                other_rows=[r["index"] for r in ordered_rows if r["action"] not in blocked]
                if len(false_rows)+len(other_rows)!=len(ordered_rows):
                    raise SourceGateError("APL_ROWS_NOT_PARTITIONED")
                counters[name]["source_model_blocked_rows"]+=len(false_rows)
                counters[name]["unresolved_rows"]+=len(other_rows)
                readiness={str(index):"NOT_READY" for index in false_rows}
                guess=decide(ordered_rows,{},item["timestamp"],readiness)
                if guess["verdict"]!="UNKNOWN" or guess["expected_action"] is not None:
                    raise SourceGateError("UNVERIFIED_ACTION_PROMOTED")
                branch[name]={
                  "source_apl_row_count":len(ordered_rows),
                  "source_model_excluded_priority_indices":false_rows,
                  "still_unresolved_priority_indices":other_rows,
                  "full_replay_expected_spell":"UNKNOWN",
                  "target_count_condition":"UNKNOWN",
                  "branch_model_conditional_only":True
                }
            rows.append({
                "timestamp":item["timestamp"],
                "actual_numeric_spell_id":item["actual_numeric_spell_id"],
                "source_replacement_gate":item["strict_pre_replacement_gate"],
                "conditional_apl_candidates":branch,
                "selected_actual_apl_branch":"UNKNOWN",
                "expected_spell":"UNKNOWN",
                "dummy_wrong_action":"UNKNOWN"})
        groups[role]={
            "actual_cast_count":expected,
            "conditionally_excluded_rows_in_each_apl":{
                k:counters[k]["source_model_blocked_rows"] for k in ordered},
            "source_apl_rows_unresolved_in_each_apl":{
                k:counters[k]["unresolved_rows"] for k in ordered},
            "predicted_spell_readiness_positive_claims":0,
            "confirmed_player_error_count":0,
            "action_decisions":rows
        }
    return {
        "schema":"ZrotGeneralRotationConditionalSourceReadyRowFilterV1",
        "scope_policy_id":POLICY,
        "status":"SOURCE_BLOCKED_ROWS_MAPPED_TO_BOTH_APL_BRANCHES_BUT_TARGET_COUNT_UNKNOWN",
        "pinned_simc_apl_receipt_sha256":IR_SHA,
        "pinned_source_negative_ready_sha256":READY_SHA,
        "slayer_hero_gate":"PROVEN_IN_BOTH_WCL_SOURCE_COHORTS",
        "active_enemies_strict_pre":"UNKNOWN",
        "conditional_branches_mutually_exclusive":True,
        "total_actual_actor_casts":105,
        "source_model_blocked_rows_per_branch":{
            name:sum(groups[role]["conditionally_excluded_rows_in_each_apl"][name]
                     for role in groups) for name in ordered},
        "total_distinct_actual_gameplay_exclusions_claimed":None,
        "exact_alternative_cd_charges":"UNKNOWN",
        "spell_priority_or_dummy_mistakes_proven":False,
        "MAIN_promotion":False,
        **groups
    }


def selftest():
    from simc_ordered_if_else_general_rotation_ir_v1 import parse_condition
    rows=[{"index":0,"action":"bloodbath","if_ast":parse_condition(None)},
          {"index":1,"action":"bloodthirst","if_ast":parse_condition(None)},
          {"index":2,"action":"raging_blow","if_ast":parse_condition("rage>=30")}]
    present={str(i):"NOT_READY" for i in (1,2)}
    d=decide(rows,{},100,present)
    assert d["verdict"]=="UNKNOWN" and d["expected_action"] is None
    # Even source-blocking higher rows does not convert unrelated UNKNOWN
    # cooldowns into a READY action.
    shifted={str(i):"NOT_READY" for i in (0,1)}
    d=decide(rows,{},100,shifted)
    assert d["verdict"]=="UNKNOWN"
    allblocked={str(i):"NOT_READY" for i in (0,1,2)}
    d=decide(rows,{},100,allblocked)
    assert d["expected_action"] is None
    assert len(allblocked)==3
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":4,
            "real_WCL_SimC_sources_loaded":False,"wrong_cast_flags":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-ir",type=Path)
    p.add_argument("--source-negative",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.simc_ir is None and a.source_negative is None:
        result=selftest()
    elif a.simc_ir and a.source_negative:
        result=apply_lists(read_pinned(a.simc_ir,IR_SHA),
                           read_pinned(a.source_negative,READY_SHA))
    else:p.error("all pinned inputs required or neither for selftest")
    blob=(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("SIMC_CONDITIONAL_SOURCE_ROW_FILTER_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
