#!/usr/bin/env python3
"""Disjoint WCL ranker holdout against an ALREADY FROZEN numeric discovery lock.

Research-only: does not open SimC, learn thresholds from holdout, or infer
available alternatives, causality, optimality, opener priority or dummy errors.
No-argument run is a safe offline self-test with no network or credentials.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/"tools"/"research"))
from fresh_wcl_engine_v1 import (canonical,sha,credentials,oauth_token,
                                  official_graphql,collect,replay)
from wcl_actor_scoped_cohort_v1 import scope_replay,write_once
from wcl_official_ranker_discovery_v1 import (
    RANK_QUERY,select_verified,RankSourceError,
)
from wcl_simc_postlock_real_audit_v1 import independently_replay_pre

SCHEMA="ZrotPredeclaredDisjointWclHoldoutV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

class HoldoutError(ValueError):
    """Fail-closed scientific holdout error."""


def validate_contract(c:dict)->dict:
    if not isinstance(c,dict) or c.get("schema")!=SCHEMA or c.get("scope_policy_id")!=POLICY:
        raise HoldoutError("PREDECLARED_SCOPE_CONTRACT_REQUIRED")
    d=c.get("frozen_discovery")
    h=c.get("holdout_source")
    m=c.get("locked_metrics")
    if not all(isinstance(x,dict) for x in (d,h,m)):
        raise HoldoutError("PREDECLARED_SUBCONTRACT_MISSING")
    if (not re.fullmatch(r"[0-9a-f]{64}",str(d.get("blind_lock_sha256","")))
            or type(d.get("fight_id")) is not int or type(d.get("actor_id")) is not int
            or not isinstance(d.get("report_code"),str) or not d["report_code"]
            or d.get("frozen_min_observations")!=2):
        raise HoldoutError("DISCOVERY_LOCK_IDENTITY_UNVERIFIED")
    if (h.get("rankings_page")!=1
            or type(h.get("min_page_position")) is not int
            or type(h.get("max_page_position")) is not int
            or not 2 <= h["min_page_position"] <= h["max_page_position"] <= 100
            or not 1<=h.get("max_metadata_candidates",0)<=15
            or not 1<=h.get("max_event_pages",0)<=5
            or not 1000<=h.get("opener_window_ms",0)<=60000
            or type(h.get("encounter_id")) is not int
            or type(h.get("difficulty")) is not int
            or h.get("forbid_same_report_code_as_discovery") is not True
            or h.get("forbid_same_report_fight_as_discovery") is not True
            or h.get("verify_actor_fight_spec_class") is not True
            or h.get("exact_official_rank_required") is not False):
        raise HoldoutError("PREDECLARED_SOURCE_FILTER_INVALID")
    if (m.get("candidate_set_source")!="IMMUTABLE_DISCOVERY_LOCK_ONLY"
            or m.get("retained_candidate_metric")!="HOLDOUT_CAST_EVENT_COUNT_AND_OBSERVED_AT_LEAST_ONCE"
            or m.get("observed_threshold")!=1
            or m.get("no_new_candidate_discovery_in_holdout") is not True
            or m.get("no_threshold_retuning") is not True
            or m.get("same_timestamp_state")!="EXCLUDE"
            or m.get("build_readiness_unknown_allowed") is not True
            or m.get("no_causal_priority_or_gameplay_promotion") is not True):
        raise HoldoutError("PREDECLARED_METRICS_CHANGED")
    return c


def validate_frozen_lock(raw:bytes,contract:dict)->dict:
    if sha(raw)!=contract["frozen_discovery"]["blind_lock_sha256"]:
        raise HoldoutError("IMMUTABLE_DISCOVERY_LOCK_SHA_MISMATCH")
    # Reject duplicate JSON keys / nonfinite values before trusting the lock.
    def pairs(p):
        out={}
        for key,value in p:
            if key in out: raise HoldoutError("DUPLICATE_LOCK_JSON_KEY")
            out[key]=value
        return out
    def nonfinite(_): raise HoldoutError("NONFINITE_LOCK_JSON")
    lock=json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)
    rows=lock.get("candidates") if isinstance(lock,dict) else None
    if (lock.get("schema")!="ZrotWave3NumericCandidateLock"
            or lock.get("status")!="LOCKED_NUMERIC_ONLY"
            or lock.get("source_kind")!="ATTESTED_RAW_WCL_REPLAY"
            or lock.get("prelocked_min_observations")!=contract["frozen_discovery"]["frozen_min_observations"]
            or lock.get("threshold_retuned_after_discovery") is not False
            or lock.get("semantic_names_attached") is not False
            or lock.get("gameplay_rule_claim") is not False
            or lock.get("holdout_validated") is not False
            or not isinstance(rows,list) or len(rows)!=lock.get("candidate_n")):
        raise HoldoutError("DISCOVERY_LOCK_SCIENTIFIC_CONTRACT_INVALID")
    seen=set()
    for row in rows:
        sid=row.get("action_spell_id")
        if (type(sid) is not int or sid<=0 or sid in seen
                or type(row.get("observed_event_count")) is not int
                or row["observed_event_count"]<2
                or row.get("semantic_name") is not None
                or row.get("priority_claim") is not False
                or row.get("causality_claim") is not False):
            raise HoldoutError("DISCOVERY_CANDIDATE_INVALID")
        seen.add(sid)
    return lock


def assess_holdout(c:dict,lock:dict, selection:dict,view:dict,independent_pre:list)->dict:
    d=c["frozen_discovery"]
    if selection.get("report_code")==d["report_code"]:
        raise HoldoutError("DISCOVERY_REPORT_REUSED_AS_HOLDOUT")
    if (selection.get("report_code"),selection.get("fight_id"),selection.get("actor_id"))==(
          d["report_code"],d["fight_id"],d["actor_id"]):
        raise HoldoutError("DISCOVERY_FIGHT_ACTOR_REUSED")
    pos=selection.get("ranking_page_position")
    h=c["holdout_source"]
    if (type(pos) is not int or not h["min_page_position"]<=pos<=h["max_page_position"]
            or selection.get("spec_class_identity")!="VERIFIED_AGAINST_REPORT"):
        raise HoldoutError("HOLDOUT_SOURCE_PREDECLARATION_VIOLATED")
    if view.get("decisions")!=independent_pre or not independent_pre:
        raise HoldoutError("INDEPENDENT_STRICT_PRE_DIVERGENCE")
    if (view.get("identity",{}).get("evidence_window")!="FIGHT_START_BOUNDED"
            or view["identity"].get("requested_window_ms")!=h["opener_window_ms"]
            or view.get("cooldown_or_resource_readiness")!="UNKNOWN"):
        raise HoldoutError("HOLDOUT_WINDOW_OR_READINESS_UNVERIFIED")
    counts=Counter(r["ability_id"] for r in independent_pre if type(r["ability_id"]) is int)
    rows=[]
    for row in lock["candidates"]:
        sid=row["action_spell_id"]
        count=counts.get(sid,0)
        rows.append({"action_spell_id":sid,
                     "discovery_observed_casts":row["observed_event_count"],
                     "holdout_observed_casts":count,
                     "holdout_observed_at_least_once":count>=c["locked_metrics"]["observed_threshold"],
                     "action_readiness":"UNKNOWN",
                     "priority_inference":False})
    return {
        "schema":"ZrotDisjointWclHoldoutObservedActionsV1",
        "scope_policy_id":POLICY,
        "status":"DISJOINT_REPORT_HOLDOUT_OBSERVATION_ONLY",
        "predeclared_contract_sha256":sha(canonical(c)),
        "unchanged_discovery_lock_sha256":d["blind_lock_sha256"],
        "holdout_source_report":selection["report_code"],
        "holdout_source_fight":selection["fight_id"],
        "holdout_actor_id":selection["actor_id"],
        "holdout_rank_page_position":pos,
        "exact_official_rank":selection["explicit_official_rank"],
        "different_report_from_discovery":True,
        "independent_player_identity":"UNKNOWN",
        "holdout_actor_cast_events":len(independent_pre),
        "strict_pre_independently_recomputed":True,
        "candidate_set_frozen_before_holdout":True,
        "frozen_threshold_not_recalibrated":True,
        "candidate_observations":rows,
        "reobserved_candidate_count":sum(v["holdout_observed_at_least_once"] for v in rows),
        "discovery_candidate_count":len(rows),
        "holdout_only_numeric_action_count":len(set(counts)-{v["action_spell_id"] for v in rows}),
        "new_discovery_candidates_added":0,
        "build_comparable_to_SimC":"UNKNOWN",
        "target_count_at_decision":"UNKNOWN",
        "cooldown_and_competing_action_readiness":"UNKNOWN",
        "causal_priority_or_optimality_proven":False,
        "general_rotation_rule_promoted":False,
        "dummy_trainer_rule_ready":False,
        "MAIN_promotion":False,
    }


def collect_holdout(c:dict, lock:dict, *,out_dir:Path,query)->dict:
    """Fetch only one predeclared, disjoint, identifiable ranker opener."""
    h=c["holdout_source"]; d=c["frozen_discovery"]
    ranking=query(RANK_QUERY, {"enc":h["encounter_id"],"class":h["class_name"],
                               "spec":h["spec_name"],"difficulty":h["difficulty"]})
    selected,meta,gate,selection=select_verified(
        query,ranking,encounter=h["encounter_id"],
        class_name=h["class_name"],spec_name=h["spec_name"],
        difficulty=h["difficulty"],max_rank=100,max_age_days=h["max_age_days"],
        max_candidates=h["max_metadata_candidates"],
        min_page_position=h["min_page_position"],
        max_page_position=h["max_page_position"],
        excluded_report_codes=(d["report_code"],))
    if selection["report_code"]==d["report_code"]:
        raise HoldoutError("DISCOVERY_REUSE")
    # Never save a numeric-candidate lock learned from the holdout.
    raw_root=out_dir/"raw"
    result=collect(query,selected["code"],selected["fight"],raw_root,
                   max_pages=h["max_event_pages"],window_ms=h["opener_window_ms"])
    if result["status"]!="COMPLETE_WINDOW":
        return {"status":"PARTIAL_HOLDOUT_NO_VALIDATION",
                "pages":result["pages"],"checkpoint":result["checkpoint"],
                "readiness":"UNKNOWN","candidate_validation":"NOT_RUN",
                "gameplay_rule":False}
    full=replay(raw_root/selected["code"]/f"fight_{selected['fight']}")
    view=scope_replay(full,gate)
    raw_events=[]
    for page in sorted((raw_root/selected["code"]/f"fight_{selected['fight']}").glob("page_*.json")):
        raw_events.extend(json.loads(page.read_bytes())["events"])
    pre=independently_replay_pre(raw_events,gate["actor_id"])
    assessed=assess_holdout(c,lock,selection,view,pre)
    assessed["WCL_raw_event_count"]=result["events"]
    assessed["WCL_raw_page_count"]=result["pages"]
    assessed["holdout_replay_sha256"]=view["replay_sha256"]
    assessed["data_status"]="REAL_OFFICIAL_WCL_SNAPSHOT"
    derived=out_dir/"derived"
    for file,obj in (
        ("source_selection.json",selection),
        ("identity_gate.json",gate),
        ("blind_holdout_replay.json",view),
        ("holdout_observed_metrics.json",assessed)
    ):
        if (derived/file).exists():
            raise HoldoutError("HOLDOUT_ARTIFACT_ALREADY_EXISTS")
    for file,obj in (
        ("source_selection.json",selection),
        ("identity_gate.json",gate),
        ("blind_holdout_replay.json",view),
        ("holdout_observed_metrics.json",assessed)
    ):
        write_once(derived/file,obj)
    return {"status":assessed["status"],
            "holdout_report_distinct":True,
            "ranking_page_position":selection["ranking_page_position"],
            "WCL_raw_event_count":result["events"],
            "WCL_raw_page_count":result["pages"],
            "WCL_actor_cast_count":len(pre),
            "frozen_discovery_candidate_count":len(lock["candidates"]),
            "reobserved_discovery_candidates":assessed["reobserved_candidate_count"],
            "holdout_metrics_sha256":sha(canonical(assessed)),
            "readiness":"UNKNOWN","independent_player":"UNKNOWN",
            "priority_validated":False,"holdout_live_api":"EXECUTED"}


def selftest()->dict:
    def cfg():
        return {
          "schema":SCHEMA,"scope_policy_id":POLICY,
          "frozen_discovery":{"report_code":"ABCDEF123456","fight_id":9,
            "actor_id":7,"blind_lock_sha256":"0"*64,"frozen_min_observations":2},
          "holdout_source":{"rankings_page":1,"min_page_position":2,
            "max_page_position":15,"max_metadata_candidates":10,
            "max_event_pages":5,"opener_window_ms":15000,
            "encounter_id":3420,"difficulty":4,"class_name":"Warrior",
            "spec_name":"Fury","forbid_same_report_code_as_discovery":True,
            "forbid_same_report_fight_as_discovery":True,
            "verify_actor_fight_spec_class":True,"exact_official_rank_required":False},
          "locked_metrics":{"candidate_set_source":"IMMUTABLE_DISCOVERY_LOCK_ONLY",
            "retained_candidate_metric":"HOLDOUT_CAST_EVENT_COUNT_AND_OBSERVED_AT_LEAST_ONCE",
            "observed_threshold":1,"no_new_candidate_discovery_in_holdout":True,
            "no_threshold_retuning":True,"same_timestamp_state":"EXCLUDE",
            "build_readiness_unknown_allowed":True,
            "no_causal_priority_or_gameplay_promotion":True}
        }
    c=cfg()
    lock={"schema":"ZrotWave3NumericCandidateLock","status":"LOCKED_NUMERIC_ONLY",
          "source_kind":"ATTESTED_RAW_WCL_REPLAY","prelocked_min_observations":2,
          "threshold_retuned_after_discovery":False,"semantic_names_attached":False,
          "gameplay_rule_claim":False,"holdout_validated":False,"candidate_n":2,
          "candidates":[
            {"action_spell_id":100,"observed_event_count":4,
             "semantic_name":None,"priority_claim":False,"causality_claim":False},
            {"action_spell_id":200,"observed_event_count":5,
             "semantic_name":None,"priority_claim":False,"causality_claim":False},
          ]}
    raw=canonical(lock);c["frozen_discovery"]["blind_lock_sha256"]=sha(raw)
    validate_contract(c);validate_frozen_lock(raw,c)
    selection={"report_code":"ZYXWVU123456","fight_id":18,"actor_id":3,
               "ranking_page_position":2,"spec_class_identity":"VERIFIED_AGAINST_REPORT",
               "explicit_official_rank":None}
    rows=[{"timestamp":100,"source_actor_id":3,"ability_id":100,
           "aura_pre":{},"readiness":"UNKNOWN"}]
    view={"identity":{"evidence_window":"FIGHT_START_BOUNDED",
                     "requested_window_ms":15000},
          "cooldown_or_resource_readiness":"UNKNOWN","decisions":rows}
    output=assess_holdout(c,lock,selection,view,rows)
    assert output["reobserved_candidate_count"]==1
    assert output["candidate_observations"][1]["holdout_observed_casts"]==0
    assert output["new_discovery_candidates_added"]==0
    assert output["cooldown_and_competing_action_readiness"]=="UNKNOWN"
    for changed,phrase in (
        ({**selection,"report_code":c["frozen_discovery"]["report_code"]},"DISCOVERY_REPORT"),
        ({**selection,"ranking_page_position":1},"SOURCE_PREDECLARATION")):
        try:assess_holdout(c,lock,changed,view,rows)
        except HoldoutError as ex:assert phrase in str(ex)
        else:raise AssertionError("CONTAMINATED_HOLDOUT_ACCEPTED")
    try:assess_holdout(c,lock,selection,view,rows[:-1])
    except HoldoutError as ex:assert "STRICT_PRE_DIVERGENCE" in str(ex)
    else:raise AssertionError("UNVERIFIED_PRE_ACCEPTED")
    try:validate_frozen_lock(raw+b" ",c)
    except HoldoutError as ex:assert "LOCK_SHA" in str(ex)
    else:raise AssertionError("MUTATED_LOCK_ACCEPTED")
    bad=json.loads(json.dumps(c));bad["locked_metrics"]["observed_threshold"]=2
    try:validate_contract(bad)
    except HoldoutError as ex:assert "METRICS_CHANGED" in str(ex)
    else:raise AssertionError("POSTHOC_THRESHOLD_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","assertion_groups":11,
            "actual_WCL_API_calls":0,"SimC_hypothesis_loaded":False,
            "real_holdout_observed":False,"gameplay_rule_promoted":False}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--live",action="store_true")
    ap.add_argument("--contract",type=Path)
    ap.add_argument("--discovery-lock",type=Path)
    ap.add_argument("--out-dir",type=Path)
    a=ap.parse_args()
    if a.self_test or not a.live:
        print(json.dumps(selftest(),sort_keys=True));return
    if not all([a.contract,a.discovery_lock,a.out_dir]):
        ap.error("--live requires --contract, --discovery-lock, --out-dir")
    # Scientific preflight and immutable source checks BEFORE OAuth/network.
    c=validate_contract(json.loads(a.contract.read_text()))
    lock=validate_frozen_lock(a.discovery_lock.read_bytes(),c)
    client,secret=credentials(None)
    token=oauth_token(client,secret)
    def query(q,v):return official_graphql(token,q,v)
    try:
        result=collect_holdout(c,lock,out_dir=a.out_dir,query=query)
    except (HoldoutError,RankSourceError) as exc:
        # No raw report or credential objects in errors.
        print(json.dumps({"status":"SCIENTIFIC_GATE_BLOCKED",
                          "error_type":type(exc).__name__,
                          "reason":str(exc)[:200],
                          "priority_validated":False},sort_keys=True))
        raise SystemExit(2)
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
