#!/usr/bin/env python3
"""Spec-agnostic evidence-gated WCL opener practice replay, source APL IR first.

Consumes fixed SHA-checked research receipts; emits actual, expected, current
conditions, and safely UNKNOWN reasoning per cast. No inferred enemy count,
cooldown readiness, resource scale or automatic/manual actionability.
No-argument run is fully synthetic. Actual run is offline from prior artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
IR_SHA="206e3a39d83d9abbe7e770ad6c7c963facc18c6485337b9734f6a9a3cdecc1d5"
RESOURCE_SHA="49011a2bda4e7b1bd9bf17e3301e2eb6aac23a808dd8c892c6f0384be871c585"

class EvaluatorError(ValueError):pass

def read_pinned(path,expect):
    raw=path.read_bytes()
    if not 10<len(raw)<800000 or hashlib.sha256(raw).hexdigest()!=expect:
        raise EvaluatorError("RECEIPT_INPUT_SHA_MISMATCH")
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise EvaluatorError("DUPLICATE_JSON_KEY")
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=unique)

def active_guard_entries(entries):
    if not isinstance(entries,dict):raise EvaluatorError("HERO_GUARD_MISSING")
    true=[name for name,item in entries.items()
          if item.get("verdict")=="TALENT_GUARD_TRUE_TARGET_COUNT_UNKNOWN"]
    false=[name for name,item in entries.items()
          if item.get("verdict")=="TALENT_GUARD_FALSE_BRANCH_EXCLUDED"]
    unknown=[name for name,item in entries.items()
             if item.get("verdict") not in
             ("TALENT_GUARD_TRUE_TARGET_COUNT_UNKNOWN",
              "TALENT_GUARD_FALSE_BRANCH_EXCLUDED")]
    return true,false,unknown

def branch_guard(hero,source_rows,active_enemy_fact,cast_ts):
    """Three-valued route for *_aoe plus ST, no damage-target approximation."""
    good,bad,unknown=active_guard_entries(hero)
    for name in good:
        if name not in source_rows:
            raise EvaluatorError("SELECTED_HERO_LIST_UNAVAILABLE")
    if unknown:
        return {"verdict":"UNKNOWN","reason":"HERO_BRANCH_NOT_CONFIRMED",
                "candidate_lists":sorted(good+unknown)}
    if not good:
        return {"verdict":"UNKNOWN","reason":"NO_ACTIVE_HERO_ACTION_LIST",
                "candidate_lists":[]}
    # Optional caller-supplied target count must be an independently verified
    # strict PRE active_enemies observation; raw damage counts never qualify.
    enemy_count=None
    if isinstance(active_enemy_fact,dict):
        ts=active_enemy_fact.get("timestamp")
        if (active_enemy_fact.get("provenance")=="STRICT_PRE_ACTIVE_ENEMIES"
            and type(ts) in (int,float) and ts<cast_ts
            and type(active_enemy_fact.get("value")) is int
            and active_enemy_fact["value"]>=1):
            enemy_count=active_enemy_fact["value"]
    if enemy_count is None:
        return {"verdict":"UNKNOWN","reason":"WCL_ACTIVE_ENEMIES_STRICT_PRE_NOT_OBSERVED",
                "candidate_lists":sorted(good),"target_count":"UNKNOWN"}
    suffix="_aoe" if enemy_count>1 else ""
    selected=sorted(n for n in good if
        (n.endswith("_aoe") if suffix else not n.endswith("_aoe")))
    if len(selected)!=1:
        return {"verdict":"UNKNOWN","reason":"TARGET_COUNT_ACTION_LIST_BRANCH_AMBIGUOUS",
                "candidate_lists":sorted(good),"target_count":enemy_count}
    return {"verdict":"BRANCH_STRUCTURALLY_ELIGIBLE_NOT_PRIORITY_VALIDATED",
            "action_list":selected[0],"target_count":enemy_count,
            "priority_or_readiness_validated":False}

def evaluate(ir,resource):
    if (ir.get("schema")!="ZrotSimcSlayerConditionalPriorityResearchIRV1"
        or resource.get("schema")!="ZrotActorOwnedWclResourceStrictPreCorrectionV1"
        or ir.get("scope_policy_id")!=POLICY or resource.get("scope_policy_id")!=POLICY):
        raise EvaluatorError("SOURCE_SCHEMA_OR_SCOPE_DRIFT")
    if (ir.get("recommendation_eligible") is not False
        or ir.get("dummy_mistake_verdict")!="UNKNOWN"
        or resource.get("readiness_or_priority_verified") is not False
        or resource.get("wrong_owner_resource_contamination_prevented") is not True):
        raise EvaluatorError("PREMATURE_SOURCE_PRIORITY_PROMOTION")
    raw=ir.get("source_list_rows")
    if not isinstance(raw,dict) or set(raw)!={"slayer","slayer_aoe"}:
        raise EvaluatorError("MISSING_SOURCE_APL_LISTS")
    feedback={}
    for role in ("discovery","holdout"):
        sample=resource[role]
        gate=ir["hero_gates_at_wcl"][role]
        records=sample["candidate_pre_snapshots"]
        if (sample["actor_cast_count"]!=len(records)
            or sample["resource_cost_cooldown_charge_or_gcd_readiness"]!="UNKNOWN"
            or ir.get("active_enemies_at_WCL_cast")!="UNKNOWN"):
            raise EvaluatorError("SOURCE_PRE_OR_READINESS_DRIFT")
        items=[]
        for i,row in enumerate(records):
            ts=row["timestamp"]
            if type(ts) not in (int,float):
                raise EvaluatorError("INVALID_ACTION_TIMESTAMP")
            pre=row.get("resource_pre",{})
            for power,details in pre.items():
                if details.get("source_timestamp",ts)>=ts or
                   details.get("owner_proof") not in ("ACTOR_OWNED_SOURCE","ACTOR_OWNED_TARGET"):
                    raise EvaluatorError("INVALID_RESOURCE_PRE_PROOF")
            # No exact active enemy count exists in this WCL source.
            route=branch_guard(gate,raw,None,ts)
            items.append({
                "decision_index":i,
                "timestamp":ts,
                "actual_numeric_spell_id":row["ability_id"],
                "expected_spell":"UNKNOWN",
                "observed_condition":{
                    "hero_gate":route["candidate_lists"],
                    "active_enemies":"UNKNOWN",
                    "actor_owned_resource_type_ids":sorted(pre),
                    "actor_owned_resource_pre_timestamp_proven":True,
                    "cooldown_and_competing_action_ready":"UNKNOWN",
                    "spell_is_manual_action":"UNKNOWN"},
                "candidate_apl_lists":route["candidate_lists"],
                "why_not_scored":route["reason"],
                "recommended_correction":"UNKNOWN",
                "mistake_verdict":"UNKNOWN",
                "error_flag":False
            })
        feedback[role]={
            "report_code":sample["report_code"],
            "actor_casts_evaluated":len(items),
            "confirmed_player_owned_resource_pre":sum(bool(r["resource_pre"]) for r in records),
            "target_count_unknown_casts":sum(x["observed_condition"]["active_enemies"]=="UNKNOWN" for x in items),
            "priority_error_flags":sum(x["error_flag"] for x in items),
            "practice_feedback":items}
    return {
        "schema":"ZrotSimcHypothesisToDummyFeedbackEvidenceGateV1",
        "scope_policy_id":POLICY,
        "status":"REAL_WCL_ACTIONS_EVALUATED_UNKNOWN_NO_FALSE_MISTAKES",
        "input_simc_ir_sha256":IR_SHA,
        "input_corrected_actor_resource_sha256":RESOURCE_SHA,
        "candidate_action_lists":"SOURCE_DERIVED",
        "ready_condition_truth_is_not_target_count_truth":True,
        "actual_real_user_dummy_session":"NOT_OBSERVED",
        "discovery":feedback["discovery"],
        "holdout":feedback["holdout"],
        "total_player_actions_evaluated":sum(v["actor_casts_evaluated"] for v in feedback.values()),
        "wrong_rotation_actions_confirmed":0,
        "readiness_claims_made":0,
        "General_Rotation_model_promoted":False,
        "MAIN_promotion":False}

def selftest():
    lists={"slayer":[{"action":"recklessness"}],"slayer_aoe":[{"action":"whirlwind"}]}
    gates={"slayer":{"verdict":"TALENT_GUARD_TRUE_TARGET_COUNT_UNKNOWN"},
           "slayer_aoe":{"verdict":"TALENT_GUARD_TRUE_TARGET_COUNT_UNKNOWN"},
           "thane":{"verdict":"TALENT_GUARD_FALSE_BRANCH_EXCLUDED"},
           "thane_aoe":{"verdict":"TALENT_GUARD_FALSE_BRANCH_EXCLUDED"}}
    missing=branch_guard(gates,lists,None,100)
    assert missing["verdict"]=="UNKNOWN" and len(missing["candidate_lists"])==2
    bad_fact={"value":1,"timestamp":100,"provenance":"STRICT_PRE_ACTIVE_ENEMIES"}
    assert branch_guard(gates,lists,bad_fact,100)["verdict"]=="UNKNOWN"
    bad_fact["timestamp"]=99
    assert branch_guard(gates,lists,bad_fact,100)["action_list"]=="slayer"
    bad_fact["value"]=2
    assert branch_guard(gates,lists,bad_fact,100)["action_list"]=="slayer_aoe"
    bad_fact["provenance"]="DAMAGE_TARGETS_LAST_15_SECONDS"
    assert branch_guard(gates,lists,bad_fact,100)["verdict"]=="UNKNOWN"
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":5,
            "WCL_API_calls":0,"false_error_flags":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-ir",type=Path)
    p.add_argument("--actor-owned-resource",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.source_ir is None and args.actor_owned_resource is None:
        result=selftest()
    elif args.source_ir and args.actor_owned_resource:
        result=evaluate(read_pinned(args.source_ir,IR_SHA),
                        read_pinned(args.actor_owned_resource,RESOURCE_SHA))
    else:p.error("provide both pinned sources or neither")
    blob=(json.dumps(result,sort_keys=True,ensure_ascii=False,separators=(",",":"))+"\n").encode()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("xb") as f:f.write(blob)
        print("REAL_GENERAL_ROTATION_DUMMY_UNKNOWN_EVALUATION_SHA256="+hashlib.sha256(blob).hexdigest())
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
