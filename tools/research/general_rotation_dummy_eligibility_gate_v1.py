#!/usr/bin/env python3
"""Generic evidence-gated General Rotation and dummy-error model eligibility.

This evaluator only reports whether all necessary claims are justified by
pinned source evidence. It never predicts or recommends a spell. UNKNOWN is
returned if any required source state is unobserved, contradictory, incomplete
or not independently validated. Safe no-argument mode: synthetic self-test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SCHEMA="ZrotPinnedDualCohortModelEligibilityInputV1"

class EligibilityError(ValueError):pass


def _read(path,expected_hash):
    raw=path.read_bytes()
    if len(raw)>200000 or hashlib.sha256(raw).hexdigest()!=expected_hash:
        raise EligibilityError("PINNED_RECEIPT_SHA_MISMATCH")
    def no_duplicates(pairs):
        d={}
        for key,value in pairs:
            if key in d:raise EligibilityError("DUPLICATE_JSON_FIELD")
            d[key]=value
        return d
    return json.loads(raw,object_pairs_hook=no_duplicates)


def evaluate(contract,build,state,postlock,holdout):
    if contract.get("schema")!=SCHEMA or contract.get("scope_policy_id")!=POLICY:
        raise EligibilityError("WRONG_PRODUCT_SCOPE")
    required=contract.get("required_for_priority")
    if (not isinstance(required,list) or len(required)!=8
        or len(set(required))!=8
        or contract.get("rule_output_when_missing")!="UNKNOWN"
        or contract.get("original_rule_promotions_allowed") is not False):
        raise EligibilityError("MODEL_AUTHORITY_CONTRACT_CHANGED")
    if any(x.get("scope_policy_id")!=POLICY for x in (build,state,postlock,holdout)):
        raise EligibilityError("SOURCE_SCOPE_MISMATCH")
    if (build.get("schema")!="ZrotPostLockWclSimcTalentSelectionAlignmentV1"
        or state.get("schema")!="ZrotPostLockDualCohortStateObservabilityV1"
        or postlock.get("schema")!="ZrotPostlockRealWclSimcNumericAuditV1"
        or holdout.get("schema")!="ZrotDisjointWclHoldoutObservedActionsV1"):
        raise EligibilityError("SOURCE_SCHEMAS_NOT_COMPATIBLE")
    source_lock=contract["sources"]["original_blind_lock_sha256"]
    if (postlock.get("source_lock_sha256")!=source_lock or
        holdout.get("unchanged_discovery_lock_sha256")!=source_lock or
        state.get("source_discovery_lock_sha256")!=source_lock):
        raise EligibilityError("DISCOVERY_LOCK_IDENTITY_DRIFT")
    if (build.get("same_WCL_build_between_cohorts") is not False or
        state.get("two_wcl_talent_tree_fingerprints_equal") is not False):
        raise EligibilityError("WCL_COHORT_BUILD_CONTRADICTION")
    if (holdout.get("different_report_from_discovery") is not True or
        holdout.get("candidate_set_frozen_before_holdout") is not True or
        holdout.get("frozen_threshold_not_recalibrated") is not True or
        holdout.get("new_discovery_candidates_added")!=0 or
        postlock.get("strict_pre_recomputed_from_raw") is not True or
        state.get("discovery",{}).get("same_timestamp_state_used") is not False or
        state.get("holdout",{}).get("same_timestamp_state_used") is not False):
        raise EligibilityError("INDEPENDENT_HOLDOUT_OR_STRICT_PRE_UNVERIFIED")
    locked=postlock.get("blind_locked_candidate_counts")
    observation=holdout.get("candidate_observations")
    if not isinstance(locked,list) or not isinstance(observation,list) or not locked:
        raise EligibilityError("ORIGINAL_CANDIDATES_NOT_FOUND")
    frozen={x["spell_id"]:x["observations"] for x in locked}
    observed={x["action_spell_id"]:x for x in observation}
    if frozen.keys()!=observed.keys() or any(observed[k]["discovery_observed_casts"]!=v
                                             for k,v in frozen.items()):
        raise EligibilityError("DISCOVERY_TO_HOLDOUT_CANDIDATE_DRIFT")
    if any(x.get("priority_inference") is not False for x in observation):
        raise EligibilityError("HOLDOUT_PRIORITY_LEAKAGE")

    checks={
      "full_build_equivalence_to_SimC":{
        "verdict":"UNKNOWN",
        "reason":"WCL_NUMERIC_NODE_DIFFERENCES_AND_EXTERNAL_TREE_PATCH_EQUIVALENCE_UNVERIFIED",
        "source":"postlock_build_alignment"},
      "real_target_count_strict_pre":{
        "verdict":"UNKNOWN",
        "reason":"OBSERVED_DAMAGE_TARGET_IDS_DO_NOT_PROVE_ACTIVE_ENEMY_COUNT",
        "source":"wcl_raw_state_observability"},
      "spell_manual_actionability":{
        "verdict":"UNKNOWN",
        "reason":"AUTO_ATTACK_PROC_AND_MANUAL_ACTION_NOT_MECHANICALLY_CLASSIFIED",
        "source":"postlock_numeric_actions"},
      "cooldown_and_charges":{
        "verdict":"UNKNOWN",
        "reason":"COOLDOWN_OR_CHARGE_STATE_NOT_INDEPENDENTLY_RECONSTRUCTED",
        "source":"wcl_raw_state_observability"},
      "resource_cost_and_scale":{
        "verdict":"UNKNOWN",
        "reason":"RESOURCE_PRE_PRESENT_BUT_SPELL_COST_AND_RAW_SCALE_UNVERIFIED",
        "source":"wcl_raw_state_observability"},
      "other_available_actions":{
        "verdict":"UNKNOWN",
        "reason":"CAST_OBSERVATION_DOES_NOT_PROVE_COMPETING_ABILITIES_READY",
        "source":"wcl_blind_casts"},
      "full_apl_selection_replay":{
        "verdict":"UNKNOWN",
        "reason":"FIRST_12_SIMC_ACTION_OVERLAP_IS_NOT_FULL_APL_EXECUTION",
        "source":"postlock_simc_public_prefix"},
      "independent_replicated_priority_holdout":{
        "verdict":"UNKNOWN",
        "reason":"DIFFERENT_REPORT_AND_CAST_REOBSERVATION_DO_NOT_PROVE_CAUSAL_PRIORITY",
        "source":"disjoint_holdout"}
    }
    if set(checks)!=set(required):
        raise EligibilityError("MANDATORY_ELIGIBILITY_GATES_MISSING")
    if (build.get("full_build_equivalence_to_current_SimC")!="UNKNOWN" or
        postlock.get("WCL_target_count_at_cast")!="UNKNOWN" or
        postlock.get("readiness_and_alternative_actions")!="UNKNOWN" or
        holdout.get("cooldown_and_competing_action_readiness")!="UNKNOWN" or
        holdout.get("causal_priority_or_optimality_proven") is not False):
        raise EligibilityError("RECEIPT_CLAIM_WAS_PROMOTED_WITHOUT_EVIDENCE")

    candidates=[
      {"numeric_spell_id":k,
       "discovery_casts":frozen[k],
       "holdout_casts":observed[k]["holdout_observed_casts"],
       "holdout_reobserved":observed[k]["holdout_observed_at_least_once"],
       "action_preference_status":"UNKNOWN",
       "trainer_mistake_classification":"UNKNOWN"}
      for k in sorted(frozen)
    ]
    return {
      "schema":"ZrotEvidenceGatedGeneralRotationTrainerEligibilityV1",
      "scope_policy_id":POLICY,
      "status":"SOURCE_CONSISTENT_BUT_REQUIRED_GAMEPLAY_STATES_UNKNOWN",
      "observed_same_spec_id_in_both_WCL_cohorts":(
        state["discovery"]["observed_combatantinfo_build"]["spec_id"]==
        state["holdout"]["observed_combatantinfo_build"]["spec_id"]),
      "same_talent_build_across_WCL_cohorts":False,
      "disjoint_report_holdout_reobserved_candidates":sum(x["holdout_reobserved"] for x in candidates),
      "observed_candidate_count":len(candidates),
      "frozen_lock_unchanged":True,
      "required_evidence_gates":checks,
      "action_candidates":candidates,
      "general_rotation_model_eligible":False,
      "opener_priority_rule_eligible":False,
      "dummy_practice_wrong_action_verdict":"UNKNOWN",
      "automatic_wrong_cast_flags":0,
      "actual_user_play_evaluated":False,
      "model_mismatch_is_player_error":False,
      "MAIN_promotion":False,
    }


def selftest():
    contract={"schema":SCHEMA,"scope_policy_id":POLICY,
              "required_for_priority":[
                "full_build_equivalence_to_SimC","real_target_count_strict_pre",
                "spell_manual_actionability","cooldown_and_charges",
                "resource_cost_and_scale","other_available_actions",
                "full_apl_selection_replay","independent_replicated_priority_holdout"],
              "rule_output_when_missing":"UNKNOWN",
              "original_rule_promotions_allowed":False,
              "sources":{"original_blind_lock_sha256":"a"*64}}
    build={"schema":"ZrotPostLockWclSimcTalentSelectionAlignmentV1",
           "scope_policy_id":POLICY,"same_WCL_build_between_cohorts":False,
           "full_build_equivalence_to_current_SimC":"UNKNOWN"}
    state={"schema":"ZrotPostLockDualCohortStateObservabilityV1",
           "scope_policy_id":POLICY,"source_discovery_lock_sha256":"a"*64,
           "two_wcl_talent_tree_fingerprints_equal":False,
           "discovery":{"same_timestamp_state_used":False,"observed_combatantinfo_build":{"spec_id":72}},
           "holdout":{"same_timestamp_state_used":False,"observed_combatantinfo_build":{"spec_id":72}}}
    post={"schema":"ZrotPostlockRealWclSimcNumericAuditV1",
          "scope_policy_id":POLICY,"source_lock_sha256":"a"*64,
          "strict_pre_recomputed_from_raw":True,"WCL_target_count_at_cast":"UNKNOWN",
          "readiness_and_alternative_actions":"UNKNOWN",
          "blind_locked_candidate_counts":[{"spell_id":1,"observations":10}]}
    hold={"schema":"ZrotDisjointWclHoldoutObservedActionsV1",
          "scope_policy_id":POLICY,"unchanged_discovery_lock_sha256":"a"*64,
          "different_report_from_discovery":True,
          "candidate_set_frozen_before_holdout":True,
          "frozen_threshold_not_recalibrated":True,
          "new_discovery_candidates_added":0,
          "cooldown_and_competing_action_readiness":"UNKNOWN",
          "causal_priority_or_optimality_proven":False,
          "candidate_observations":[{"action_spell_id":1,
             "discovery_observed_casts":10,"holdout_observed_casts":8,
             "holdout_observed_at_least_once":True,"priority_inference":False}]}
    r=evaluate(contract,build,state,post,hold)
    assert r["status"]=="SOURCE_CONSISTENT_BUT_REQUIRED_GAMEPLAY_STATES_UNKNOWN"
    assert r["automatic_wrong_cast_flags"]==0
    assert r["dummy_practice_wrong_action_verdict"]=="UNKNOWN"
    assert len(r["required_evidence_gates"])==8
    import copy
    for original,patch,reason in [
       ("hold",{"new_discovery_candidates_added":1},"HOLDOUT"),
       ("post",{"source_lock_sha256":"b"*64},"LOCK"),
       ("state",{"two_wcl_talent_tree_fingerprints_equal":True},"BUILD")]:
        args={"contract":contract,"build":build,"state":state,"post":post,"hold":hold}
        args[original]={**args[original],**patch}
        try:evaluate(args["contract"],args["build"],args["state"],args["post"],args["hold"])
        except EligibilityError as ex:assert reason in str(ex)
        else:raise AssertionError("PROMOTION_OR_CONTRADICTION_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","assertion_groups":7,
            "real_source_artifacts_loaded":False,
            "real_gameplay_priority_proven":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--contract",type=Path)
    p.add_argument("--build",type=Path)
    p.add_argument("--state",type=Path)
    p.add_argument("--postlock",type=Path)
    p.add_argument("--holdout",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if all(x is None for x in (a.contract,a.build,a.state,a.postlock,a.holdout)):
        result=selftest()
    elif all(x is not None for x in (a.contract,a.build,a.state,a.postlock,a.holdout)):
        c=json.loads(a.contract.read_bytes())
        sources=c["sources"]
        expected={"build":sources["wcl_simc_build_alignment_sha256"],
                  "state":sources["wcl_strict_pre_observability_sha256"],
                  "postlock":sources["frozen_discovery_vs_simc_postlock_sha256"],
                  "holdout":sources["disjoint_report_holdout_metrics_sha256"]}
        for v in expected.values():
            if not isinstance(v,str) or not re.fullmatch("[a-f0-9]{64}",v):
                raise EligibilityError("UNPINNED_SOURCE_RECEIPT")
        args={k:_read(getattr(a,k),v) for k,v in expected.items()}
        result=evaluate(c,args["build"],args["state"],args["postlock"],args["holdout"])
    else:p.error("all 5 evidence arguments required")
    raw=(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
        print("ROTATION_TRAINER_ELIGIBILITY_RECEIPT_SHA256="+hashlib.sha256(raw).hexdigest())
    else:print(raw.decode(),end="")

if __name__=="__main__":main()
