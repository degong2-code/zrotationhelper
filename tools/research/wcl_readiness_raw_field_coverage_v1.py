#!/usr/bin/env python3
"""Postlock WCL two-cohort cooldown/charge evidence COVERAGE audit.

This intentionally cannot derive ready/not-ready from cast gaps, proc guesses,
ordinary damage timestamps, or an absent field. It inventories explicit
potential cooldown/charge keys and event categories in ORIGINAL WCL raw
source evidence and reports whether a trusted readiness PRE fact exists.

No WCL API, no secrets and no user-data collection. Default self-test.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from wcl_dual_cohort_state_observability_v1 import read_cohort
from wcl_simc_postlock_real_audit_v1 import _zip, _canonical as canonical, _sha as sha

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
FIELDS=("cooldown","charge","recharge","reset","ready")
EXACT_WCL_FIELD_AUTHORITY:tuple[str,...]=()  # No approved gameplay state mapping.

def classify(events,actor,expected_casts):
    relevant=[e for e in events
        if e.get("sourceID")==actor or e.get("targetID")==actor]
    types=Counter(str(e.get("type")) for e in relevant)
    possible=Counter()
    examples={}
    for event in relevant:
        for key in event:
            if any(term in key.casefold() for term in FIELDS):
                possible[key]+=1
                if key not in examples:
                    examples[key]={"type":event.get("type"),
                                   "actor_is_source":event.get("sourceID")==actor,
                                   "actor_is_target":event.get("targetID")==actor}
    casts=sum(e.get("sourceID")==actor and
         e.get("type") in ("cast","begincast") for e in events)
    if casts!=expected_casts:raise ValueError("ORIGINAL_WCL_CAST_REPLAY_MISMATCH")
    return {"actor_relevant_events":len(relevant),
      "verified_actor_cast_count":casts,
      "actor_relevant_event_types":dict(sorted(types.items())),
      "potential_readiness_like_field_occurrences":dict(sorted(possible.items())),
      "potential_field_examples_without_values":examples,
      "explicit_readiness_field_mappings_certified":list(EXACT_WCL_FIELD_AUTHORITY),
      "complete_cooldown_charge_and_proc_transitions_observed":"UNKNOWN",
      "direct_competing_action_readiness_strict_pre":"UNKNOWN",
      "negative_inference_from_missing_fields":False,
      "cooldown_inference_from_cast_interval":False,
      "approved_priority_rules":0}

def run(discovery,holdout):
    result={}
    for kind,path,cnt in (("discovery",discovery,54),("holdout",holdout,51)):
        gate,view,events,pages=read_cohort(_zip(path),role=kind)
        if len(view["decisions"])!=cnt:raise ValueError("CAST_COUNT_DRIFT")
        row=classify(events,gate["actor_id"],cnt)
        row["raw_event_count"]=len(events)
        row["report_code"]=gate["report_code"]
        row["source_pages_verified"]=pages
        result[kind]=row
    if result["discovery"]["report_code"]==result["holdout"]["report_code"]:
        raise ValueError("COHORT_REPORT_REUSE")
    return {"schema":"ZrotWclReadinessRawFieldCoverageV1",
       "scope_policy_id":POLICY,
       "status":"RAW_SOURCE_FIELD_INVENTORY_NOT_PROOF_OF_ABSENCE",
       "total_cast_decisions":105,"source_evidence_disjoint":True,
       "discovery":result["discovery"],"holdout":result["holdout"],
       "gameplay_CD_ready_verified":False,
       "addon_implementation_required_for_additional_observability":"RESEARCH_CANDIDATE",
       "general_priority_promoted":False,"MAIN_promotion":False}

def selftest():
    events=[
       {"timestamp":100,"type":"cast","sourceID":7,"targetID":9,
        "abilityGameID":335097},
       {"timestamp":110,"type":"unknown","sourceID":7,"targetID":9,
        "cooldownRemaining":100,"charges":2},
       {"timestamp":120,"type":"cast","sourceID":7,"targetID":9,
        "abilityGameID":335097},
       {"timestamp":130,"type":"damage","sourceID":9,"targetID":7}]
    result=classify(events,7,2)
    assert result["verified_actor_cast_count"]==2
    assert result["potential_readiness_like_field_occurrences"]=={
        "charges":1,"cooldownRemaining":1}
    assert result["direct_competing_action_readiness_strict_pre"]=="UNKNOWN"
    assert result["negative_inference_from_missing_fields"] is False
    assert result["cooldown_inference_from_cast_interval"] is False
    assert result["approved_priority_rules"]==0
    return {"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":6,"WCL_API_requests":0,"player_errors_claimed":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--discovery-zip",type=Path)
    p.add_argument("--holdout-zip",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.discovery_zip is None and args.holdout_zip is None:obj=selftest()
    elif args.discovery_zip and args.holdout_zip:
        obj=run(args.discovery_zip,args.holdout_zip)
    else:p.error("both source archives required, or neither for safe self-test")
    blob=canonical(obj)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("xb") as f:f.write(blob)
        print("WCL_CD_CHARGE_RAW_COVERAGE_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
