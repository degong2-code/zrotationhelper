#!/usr/bin/env python3
"""Generic verified-checkpoint WCL raw actor -> numeric casts / strict PRE.

This is an independent WCL producer: NO SimC source/APL/guide/ability names.
Consumes one *already* collected official WCL raw checkpoint, its actor
identity-gate and actor-scoped blind replay; regenerates the raw page replay,
verifies the actor view and recorded receipt hashes, and extracts immutable
numeric casts and aura-active transitions. All times are normalized to
fight-start-relative ms. It never infers cooldown, resource, target count or
complete action READY from an observed WCL cast.

A separate producer function bridges *two disjoint* verified actor snapshots
plus the numeric candidate lock. WCL holdout provenance remains subject to
ranker/raw audits: report disjointness alone is not independent validation.

No flags -> fully synthetic test, no OAuth or WCL requests.
CLI --actor-root ... --out ... -> read-only existing snapshot conversion.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile

from fresh_wcl_engine_v1 import (
    replay,checked_pages,_ability,_num,_aura_transition,
    canonical,sha,EngineError,write_atomic
)
from wcl_actor_scoped_cohort_v1 import (
    identity_gate,scope_replay,ActorGateError
)
from wcl_blind_numeric_candidate_lock_v1 import (
    lock_candidates,LOCK_SCHEMA,BlindInputError
)

SCHEMA="ZrotWclRawActorStrictPreNumericTransportV1"
FIXTURE_SCHEMA="ZrotGenericWclPostlockSourceBridgeInputV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
RAW_SOURCE="WCL_NORMALIZED_RAW_EVENT"
VERIFIED="VERIFIED_SOURCE_TRANSITION"
ORIGIN="ATTESTED_RAW_WCL_REPLAY"
HASH=re.compile(r"^[0-9a-f]{64}$")
NAME=re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]*$")

class TransportError(ValueError):pass

def need(ok,code):
    if not ok:raise TransportError(code)

def read_json(path:Path)->dict:
    need(path.is_file() and not path.is_symlink(),"FILE_MISSING_OR_SYMLINK")
    raw=path.read_bytes()
    need(0<len(raw)<15_000_000,"JSON_INPUT_OUT_OF_BOUNDS")
    def unique(pairs):
        obj={}
        for k,v in pairs:
            need(k not in obj,"DUPLICATE_JSON_KEYS")
            obj[k]=v
        return obj
    def nonfinite(_):raise TransportError("NONFINITE_JSON")
    obj=json.loads(raw,object_pairs_hook=unique,parse_constant=nonfinite)
    need(type(obj)==dict,"JSON_ROOT_NOT_OBJECT")
    return obj

def _as_relative_ms(timestamp:int|float,start:int|float)->int:
    need(type(timestamp) in (int,float) and
         type(start) in (int,float) and
         float(timestamp).is_integer() and float(start).is_integer() and
         timestamp>=start,
         "NONINTEGRAL_OR_BEFORE_FIGHT_WCL_TIMESTAMP")
    diff=int(timestamp)-int(start)
    need(0<=diff<=3_600_000,"BOUNDED_WCL_FIGHT_RELATIVE_TIME_INVALID")
    return diff

def _raw_event_id(page_sha:str,ordinal:int,ev:dict)->str:
    return "raw_"+sha(canonical([page_sha,ordinal,ev]))[:40]

def actor_snapshot(raw_folder:Path,gate:dict,blind_view:dict,
                   original_receipt:dict,*,source_role:str="DISCOVERY")->dict:
    """Independent raw-page replay; no SimC meaning or post-lock mapping."""
    need(gate.get("schema")=="ZrotWclActorIdentityGateV1" and
         gate.get("status")=="ACTOR_FIGHT_SPEC_CLASS_MATCH" and
         gate.get("rank_source_verified") is False and
         gate.get("spec_build_equivalence_to_SimC")=="UNKNOWN" and
         isinstance(gate.get("source_metadata_sha256"),str) and
         HASH.fullmatch(gate["source_metadata_sha256"]),
         "ORIGINAL_ACTOR_GATE_PROVENANCE_NOT_VERIFIED")
    need(source_role in ("DISCOVERY","HOLDOUT"),
         "WCL_SOURCE_COHORT_ROLE_UNDECLARED")
    if source_role=="DISCOVERY":
        need(original_receipt.get("schema")==
             "ZrotWclActorScopedDiscoveryReceiptV1" and
             original_receipt.get("status")=="NUMERIC_DISCOVERY_ONLY" and
             original_receipt.get("scope_policy_id")==POLICY and
             original_receipt.get("actor_gate_sha256")==sha(canonical(gate)) and
             original_receipt.get("blind_actor_view_sha256")==sha(canonical(blind_view)) and
             original_receipt.get("readiness")=="UNKNOWN" and
             original_receipt.get("independent_holdout")=="NOT_RUN",
             "WCL_PRIOR_ACTOR_RECEIPT_OR_IDENTITY_CHANGED")
    else:
        need(original_receipt.get("schema")==
             "ZrotDisjointWclHoldoutObservedActionsV1" and
             original_receipt.get("scope_policy_id")==POLICY and
             original_receipt.get("status")==
              "DISJOINT_REPORT_HOLDOUT_OBSERVATION_ONLY" and
             original_receipt.get("holdout_source_report")==gate["report_code"] and
             original_receipt.get("holdout_source_fight")==gate["fight_id"] and
             original_receipt.get("holdout_actor_id")==gate["actor_id"] and
             original_receipt.get("different_report_from_discovery") is True and
             original_receipt.get("strict_pre_independently_recomputed") is True and
             original_receipt.get("candidate_set_frozen_before_holdout") is True and
             original_receipt.get("new_discovery_candidates_added")==0 and
             original_receipt.get("general_rotation_rule_promoted") is False and
             original_receipt.get("dummy_trainer_rule_ready") is False and
             original_receipt.get("cooldown_and_competing_action_readiness")=="UNKNOWN",
             "WCL_PRIOR_DISJOINT_HOLDOUT_RECEIPT_INVALID")
    raw=replay(raw_folder)
    view=scope_replay(raw,gate)
    need(view==blind_view and
         view.get("numeric_actor_scope_only") is True and
         view.get("cooldown_or_resource_readiness")=="UNKNOWN" and
         view.get("candidate_lock")=="NOT_IMPLEMENTED",
         "WCL_ACTOR_VIEW_NOT_REGENERATED_FROM_RAW_PAGES")
    identity=raw["identity"]
    need(identity.get("evidence_window")=="FIGHT_START_BOUNDED" and
         type(identity.get("requested_window_ms")) is int and
         1000<=identity["requested_window_ms"]<=60000,
         "WCL_RAW_NOT_FIGHT_START_BOUNDED")
    start=identity["start"]
    checkpoint=read_json(raw_folder/"checkpoint.json")
    pages=checked_pages(raw_folder,checkpoint)
    casts=[];transitions=[];events_seen=set();observed_counter=Counter()
    total=0;excluded_casts=0;skipped_unknown_aura=0
    actor=gate["actor_id"]
    for p in pages:
        source=read_json(raw_folder/p["file"])
        need(sha(canonical(source))==p["sha256"] and
             source.get("schema")=="FreshWCLPageV1" and
             source.get("start")==p["start"] and
             source.get("next")==p["next"] and
             len(source["events"])==p["event_count"],
             "PAGE_REPLAY_HASH_OR_COUNTS_CHANGED")
        for n,e in enumerate(source["events"]):
            need(type(e)==dict,"INVALID_RAW_EVENT_OBJECT")
            event_id=_raw_event_id(p["sha256"],n,e)
            need(event_id not in events_seen,"RAW_PAGE_EVENT_ID_COLLISION")
            events_seen.add(event_id)
            t=_as_relative_ms(e.get("timestamp"),start)
            total+=1
            typ=str(e.get("type","")).casefold()
            if typ in ("cast","begincast"):
                observed_actor=_num(e.get("sourceID"))
                spell=_ability(e)
                if observed_actor!=actor:
                    excluded_casts+=1
                elif spell is None or spell<=0:
                    # Do not turn a missing numeric ID into a spell name.
                    skipped_unknown_aura+=1
                else:
                    casts.append({
                      "event_id":event_id,"t_ms":t,
                      "spell_id":spell,"source_kind":RAW_SOURCE
                    })
                    observed_counter[(e["timestamp"],actor,spell)]+=1
            aura=_aura_transition(e)
            if aura is None or _num(e.get("targetID"))!=actor:
                continue
            spell=_ability(e)
            if spell is None or spell<=0:
                skipped_unknown_aura+=1
                continue
            value=aura["active"]
            need(value is None or type(value) is bool,
                 "RAW_AURA_BOOLEAN_TRI_STATE_INVALID")
            transitions.append({
              "source_event_id":event_id,
              "signal":"raw_aura_"+str(spell)+"_active",
              "t_ms":t,"value":value,
              "valid_until_ms":None,
              "raw_receipt_sha256":"__BOUND_AFTER_EVENTS__",
              "source_kind":RAW_SOURCE,"quality":VERIFIED
            })
    replay_counter=Counter(
      (x["timestamp"],x["source_actor_id"],x["ability_id"])
      for x in blind_view["decisions"])
    need(replay_counter==observed_counter,
         "ACTOR_CAST_EVENTS_DIVERGE_FROM_INDEPENDENT_REPLAY")
    need(len(casts)==blind_view["decision_count"] and
         len(casts)>0 and total==raw["event_count"],
         "ACTOR_SCOPED_REPLAY_COUNTS_NOT_CONSERVED")
    casts.sort(key=lambda x:(x["t_ms"],x["event_id"]))
    transitions.sort(key=lambda x:(x["t_ms"],x["source_event_id"]))
    raw_receipt_sha256=sha(canonical({
      "identity":identity,
      "actor_id":actor,
      "source_page_sha256":raw["source_page_sha256"],
      "actor_blind_view_sha256":sha(canonical(blind_view))
    }))
    for t in transitions:t["raw_receipt_sha256"]=raw_receipt_sha256
    # This numeric payload is blind by construction; class/spec strings,
    # source action names or SimC hypothesis do not cross this boundary.
    result={
      "schema":SCHEMA,"policy_id":POLICY,
      "origin":ORIGIN,
      "source_cohort_role":source_role,
      "report_code":gate["report_code"],
      "fight_id":gate["fight_id"],
      "actor_id":actor,
      "fight_start_abs_ms":int(start),
      "fight_end_abs_ms":int(gate["fight_end_ms"]),
      "evidence_window":"FIGHT_START_BOUNDED",
      "requested_window_ms":identity["requested_window_ms"],
      "raw_source_page_sha256":raw["source_page_sha256"],
      "source_replay_sha256":view["replay_sha256"],
      "raw_receipt_sha256":raw_receipt_sha256,
      "actor_gate_sha256":sha(canonical(gate)),
      "prior_original_actor_receipt_sha256":sha(canonical(original_receipt)),
      "raw_event_count":total,"actor_numeric_cast_count":len(casts),
      "other_actor_casts_excluded":excluded_casts,
      "unknown_numeric_id_events_excluded":skipped_unknown_aura,
      "raw_aura_boolean_transitions":len(transitions),
      "cast_events":casts,"transitions":transitions,
      "time_basis":"FIGHT_START_RELATIVE_INTEGER_MILLISECONDS",
      "strict_PRE_state_not_claimed_here":True,
      "same_timestamp_order_not_used_as_PRE":True,
      "numeric_resource_READINESS":"UNKNOWN",
      "target_count_at_cast":"UNKNOWN",
      "build_equivalent_to_SimC":"UNKNOWN",
      "independent_rank_or_holdout_proven":False,
      "prior_disjoint_report_holdout_recomputed":
           source_role=="HOLDOUT",
      "official_WCL_live_API_called_this_run":False,
      "source_gameplay_rule":"UNKNOWN",
      "MAIN_promoted":False,
    }
    result["numeric_transport_sha256"]=sha(canonical(result))
    return result

def _check_transport(t:dict)->None:
    need(type(t)==dict and t.get("schema")==SCHEMA and
         t.get("policy_id")==POLICY and t.get("origin")==ORIGIN and
         isinstance(t.get("numeric_transport_sha256"),str) and
         t["numeric_transport_sha256"]==sha(canonical({
          k:v for k,v in t.items() if k!="numeric_transport_sha256"})) and
         t.get("build_equivalent_to_SimC")=="UNKNOWN" and
         t.get("independent_rank_or_holdout_proven") is False and
         t.get("target_count_at_cast")=="UNKNOWN" and
         t.get("source_gameplay_rule")=="UNKNOWN" and
         t.get("source_cohort_role") in ("DISCOVERY","HOLDOUT") and
         t.get("prior_disjoint_report_holdout_recomputed") is
             (t["source_cohort_role"]=="HOLDOUT"),
         "WCL_RAW_TRANSPORT_INTEGRITY_OR_CLAIM_BOUNDARY_CHANGED")

def classify_cohort_identity(left:dict,right:dict)->dict:
    """Source-numeric-only exact/report overlap. Never infer independent actors.

    A newly fetched snapshot of a known report cannot be a blind holdout,
    even with a new revision, action ordinal, or different fight.
    """
    _check_transport(left)
    _check_transport(right)
    same_report=left["report_code"]==right["report_code"]
    same_fight=same_report and left["fight_id"]==right["fight_id"]
    same_actor=same_fight and left["actor_id"]==right["actor_id"]
    same_replay=left["source_replay_sha256"]==right["source_replay_sha256"]
    same_raw=left["raw_receipt_sha256"]==right["raw_receipt_sha256"]
    need(not same_raw or (same_report and same_fight and same_actor),
         "IDENTICAL_RAW_EVIDENCE_HAS_CONFLICTING_ACTOR_REPORT_IDENTITY")
    status=("EXACT_SAME_RAW_ACTOR_REPLAY" if same_actor and same_raw else
            "SAME_REPORT_FIGHT_ACTOR_DIFFERENT_SNAPSHOT" if same_actor else
            "SAME_REPORT_NOT_INDEPENDENT" if same_report else
            "DISTINCT_REPORT_NOT_YET_FULLY_INDEPENDENCE_AUDITED")
    return {
        "schema":"ZrotWclNumericSourceCohortOverlapV1",
        "policy_id":POLICY,
        "left_transport_sha256":left["numeric_transport_sha256"],
        "right_transport_sha256":right["numeric_transport_sha256"],
        "same_report":same_report,
        "same_fight":same_fight,
        "same_actor":same_actor,
        "same_actor_replay_sha256":same_replay,
        "same_raw_actor_snapshot_sha256":same_raw,
        "classification":status,
        "report_disjoint":not same_report,
        "valid_as_independent_holdout_against_other":False,
        "cannot_count_as_new_independent_cohort":same_report,
        "actual_independent_player_identity":"UNKNOWN",
        "WCL_source_readiness":"UNKNOWN",
        "validated_gameplay_priority":False
    }


def replicate_frozen_numeric_candidates(discovery:list[dict],
                                        newly_observed:dict,
                                        frozen_lock:dict,
                                        frozen_sha256:str,
                                        fixed_metrics:dict,
                                        *,already_seen_report_codes:tuple[str,...]=())->dict:
    """Cross-report numeric observation with immutable thresholds, not a holdout.

    A new report's observed spell IDs can only be evaluated against the
    previously frozen discovery candidate set. No new action can enter that
    set, and no observed cast can establish READY or mandatory priority.
    This is a product-level independent-report *candidate replay*, NOT an
    independently locked gameplay-rule holdout.
    """
    need(type(discovery)==list and 1<=len(discovery)<=100,
         "LOCKED_DISCOVERY_SOURCE_ROSTER_REQUIRED")
    for d in discovery:
        _check_transport(d)
        need(d["source_cohort_role"]=="DISCOVERY",
             "DISCOVERY_SOURCE_ROLE_UNVERIFIED")
    _check_transport(newly_observed)
    need(frozen_lock.get("schema")==LOCK_SCHEMA and
         frozen_lock.get("status")=="LOCKED_NUMERIC_ONLY" and
         frozen_lock.get("source_kind")==ORIGIN and
         frozen_lock.get("threshold_retuned_after_discovery") is False and
         frozen_lock.get("semantic_names_attached") is False and
         frozen_lock.get("gameplay_rule_claim") is False and
         frozen_lock.get("holdout_validated") is False and
         type(frozen_sha256)==str and HASH.fullmatch(frozen_sha256) and
         sha(canonical(frozen_lock))==frozen_sha256,
         "IMMUTABLE_NUMERIC_SOURCE_CANDIDATES_REQUIRED")
    old_hashes=sorted(x["source_replay_sha256"] for x in discovery)
    need(old_hashes==frozen_lock.get("source_replay_sha256") and
         len(set(old_hashes))==len(old_hashes),
         "NEW_REPORT_NOT_COMPARED_TO_THIS_LOCKED_DISCOVERY")
    old_reports={x["report_code"] for x in discovery}
    need(len(old_reports)==len(discovery) and
         newly_observed["report_code"] not in old_reports and
         newly_observed["source_replay_sha256"] not in old_hashes and
         type(already_seen_report_codes)==tuple and
         newly_observed["report_code"] not in already_seen_report_codes and
         all(isinstance(x,str) for x in already_seen_report_codes),
         "NEW_COHORT_REUSES_PREVIOUSLY_SEEN_REPORT")
    need(type(fixed_metrics)==dict and
         fixed_metrics.get("candidate_set_source")==
             "IMMUTABLE_DISCOVERY_LOCK_ONLY" and
         type(fixed_metrics.get("observed_threshold")) is int and
         1<=fixed_metrics["observed_threshold"]<=1000 and
         fixed_metrics.get("no_new_candidate_discovery_in_holdout") is True and
         fixed_metrics.get("no_threshold_retuning") is True,
         "LOCKED_NUMERIC_REOBSERVATION_METRIC_MUST_NOT_RETUNE")
    ids=set();rows=frozen_lock.get("candidates")
    need(type(rows)==list and len(rows)==frozen_lock.get("candidate_n") and
         len(rows)>0,"FROZEN_NUMERIC_CANDIDATE_SET_EMPTY")
    for row in rows:
        sid=row.get("action_spell_id")
        need(type(sid)==int and sid>0 and sid not in ids and
             row.get("semantic_name") is None and
             row.get("readiness")=="UNKNOWN" and
             row.get("priority_claim") is False and
             row.get("causality_claim") is False and
             row.get("gameplay_rule_claim") is False,
             "FROZEN_NUMERIC_CANDIDATES_NOT_BLIND")
        ids.add(sid)
    observations=Counter(x["spell_id"] for x in newly_observed["cast_events"])
    threshold=fixed_metrics["observed_threshold"]
    candidates=[{
      "action_spell_id":sid,
      "original_discovery_observed_casts":next(
         x["observed_event_count"] for x in rows
         if x["action_spell_id"]==sid),
      "new_report_numeric_casts":observations[sid],
      "previously_fixed_presence_threshold":threshold,
      "observed_at_least_fixed_threshold":observations[sid]>=threshold,
      "real_action_READY":"UNKNOWN",
      "necessary_or_mandatory_priority":"UNKNOWN",
      "player_cast_manual_action":"UNKNOWN"
    } for sid in sorted(ids)]
    return {
       "schema":"ZrotWclCrossReportLockedNumericCandidateReobservationV1",
       "policy_id":POLICY,
       "source_kind":"NUMERIC_WCL_ONLY",
       "status":"ADDITIONAL_DISTINCT_REPORT_REOBSERVATION_NOT_FORMAL_HOLDOUT",
       "original_frozen_discovery_lock_sha256":frozen_sha256,
       "old_discovery_replay_hashes":old_hashes,
       "new_report_numeric_transport_sha256":
          newly_observed["numeric_transport_sha256"],
       "new_report_disjoint_from_discovery":True,
       "new_report_disjoint_from_additional_exclusions":True,
       "new_cast_count":newly_observed["actor_numeric_cast_count"],
       "candidate_set_unchanged":True,
       "previously_fixed_metrics_sha256":sha(canonical(fixed_metrics)),
       "predeclared_numeric_presence_threshold":threshold,
       "candidates":candidates,
       "reobserved_locked_candidate_count":sum(
           v["observed_at_least_fixed_threshold"] for v in candidates),
       "original_frozen_candidate_count":len(candidates),
       "new_unlocked_numeric_spells_seen":len(set(observations)-ids),
       "no_new_candidates_added":True,
       "independent_research_holdout_validation":"NOT_RUN_FOR_THIS_REPORT",
       "new_WCL_spell_to_SimC_source_mapping":"UNKNOWN",
       "build_equivalence_to_SimC":"UNKNOWN",
       "target_count_at_cast":"UNKNOWN",
       "competing_action_READY_proven":0,
       "General_Rotation_rule_promoted":False,
       "dummy_wrong_cast_proven":False,
       "new_WCL_API_calls_in_this_comparison":0,
       "MAIN_promoted":False
    }


def disjoint_numeric_fixture(discovery:list[dict],holdout:dict,
                             frozen_lock:dict,frozen_lock_sha256:str)->dict:
    """Post-lock transport only. No source APL allowed in this signature."""
    need(type(discovery)==list and bool(discovery) and
         len(discovery)<=100,"BOUNDED_DISCOVERY_SNAPSHOTS_REQUIRED")
    for x in discovery:
        _check_transport(x)
        need(x["source_cohort_role"]=="DISCOVERY",
             "HOLDOUT_WAS_LEAKED_INTO_BLIND_DISCOVERY")
    _check_transport(holdout)
    need(holdout["source_cohort_role"]=="HOLDOUT",
         "UNVERIFIED_HOLDOUT_ROLE_IN_NUMERIC_FIXTURE")
    need(frozen_lock.get("schema")==LOCK_SCHEMA and
         frozen_lock.get("source_kind")==ORIGIN and
         frozen_lock.get("status")=="LOCKED_NUMERIC_ONLY" and
         frozen_lock.get("threshold_retuned_after_discovery") is False and
         frozen_lock.get("semantic_names_attached") is False and
         frozen_lock.get("gameplay_rule_claim") is False and
         sha(canonical(frozen_lock))==frozen_lock_sha256,
         "FROZEN_NUMERIC_DISCOVERY_LOCK_NOT_REUSABLE")
    replay_hashes=sorted(x["source_replay_sha256"] for x in discovery)
    need(replay_hashes==frozen_lock.get("source_replay_sha256") and
         len(set(replay_hashes))==len(discovery),
         "LOCK_NOT_GENERATED_FROM_THESE_DISCOVERY_ACTORS")
    reports=[x["report_code"] for x in discovery]
    need(len(set(reports))==len(reports) and
         holdout["report_code"] not in reports,
         "DISCOVERY_AND_HOLDOUT_REPORT_NOT_DISJOINT")
    roster={
      "source_kind":ORIGIN,
      "source_replay_sha256":replay_hashes,
      "frozen_min_observations":frozen_lock["prelocked_min_observations"],
      "report_fights":[{
         "report_code":x["report_code"],
         "fight_id":x["fight_id"],
         "source_replay_sha256":x["source_replay_sha256"]}
         for x in discovery]
    }
    return {
      "schema":FIXTURE_SCHEMA,"policy_id":POLICY,
      "discovery_roster":roster,
      "holdout":{
         "source_kind":ORIGIN,"cohort_id":"wcl_holdout_"+
           holdout["raw_receipt_sha256"][:16],
         "report_code":holdout["report_code"],
         "fight_id":holdout["fight_id"],
         "actor_id":str(holdout["actor_id"]),
         "raw_receipt_sha256":holdout["raw_receipt_sha256"]},
      "cast_events":holdout["cast_events"],
      "transitions":holdout["transitions"],
      "source_APL_or_SimC_present":False,
      "official_live_WCL_API_called_in_this_transport":False,
      "independent_WCL_holdout_proven":False,
      "general_rotation_rule_proven":False,
      "dummy_training_error_proven":False,
    }


def strict_pre_numeric_matrix(transport:dict)->dict:
    """Reusable WCL-only per-cast pre-state. No SimC or game semantics.

    Valid raw aura transitions must be strictly before the observed cast.
    At a disputed or same-timestamp event the existing StrictPreReplay
    yields UNKNOWN rather than choosing the favorable event by row order.
    Casts remain observations, never evidence of competing readiness.
    """
    from general_rotation_strict_pre_state_engine_v1 import (
        Transition,StrictPreReplay,VERIFIED as STRICT_VERIFIED
    )
    _check_transport(transport)
    casts=transport.get("cast_events")
    transitions=transport.get("transitions")
    need(type(casts)==list and type(transitions)==list and
         len(casts)==transport["actor_numeric_cast_count"] and
         len(transitions)==transport["raw_aura_boolean_transitions"] and
         0<len(casts)<=50000 and len(transitions)<=100000,
         "NUMERIC_PRE_MATRIX_RAW_ROW_COUNT_DRIFT")
    signals=tuple(sorted({r["signal"] for r in transitions}))
    need(len(signals)*len(casts)<=500000,
         "WCL_PRE_MATRIX_BOUNDED_SIGNALS_TIMES_CASTS")
    cohort="original_wcl_"+transport["source_cohort_role"].lower()
    scope=transport["report_code"]+"/"+str(transport["fight_id"])
    actor=str(transport["actor_id"])
    trans=[]
    for r in transitions:
        need(r.get("source_kind")==RAW_SOURCE and
             r.get("quality")==VERIFIED and
             r.get("raw_receipt_sha256")==transport["raw_receipt_sha256"] and
             isinstance(r.get("signal"),str) and
             NAME.fullmatch(r["signal"]) is not None and
             r.get("valid_until_ms") is None,
             "STRICT_PRE_RAW_TRANSITION_SOURCE_CHANGED")
        trans.append(Transition(
            r["source_event_id"],cohort,scope,actor,
            r["signal"],r["t_ms"],r["value"],
            r["valid_until_ms"],r["raw_receipt_sha256"],
            source_kind=RAW_SOURCE,quality=STRICT_VERIFIED))
    engine=StrictPreReplay(trans)
    rows=[];counts=Counter();used=set()
    for cast in casts:
        need(cast.get("source_kind")==RAW_SOURCE and
             type(cast.get("t_ms")) is int and cast["t_ms"]>=0 and
             type(cast.get("spell_id")) is int and
             cast["spell_id"]>0 and
             type(cast.get("event_id")) is str and
             cast["event_id"] not in used,
             "RAW_CAST_EVENT_IS_NOT_NUMERIC")
        used.add(cast["event_id"])
        snapshot=(engine.snapshot(
             cohort_id=cohort,scope=scope,actor_id=actor,
             at_ms=cast["t_ms"],signals=signals)
             if signals else None)
        facts=snapshot["signals"] if snapshot else {}
        for signal,entry in facts.items():
            counts[entry["status"]]+=1
            if entry["status"]=="KNOWN":
                need(entry["event_t_ms"]<cast["t_ms"] and
                     entry["source_event_id"] is not None and
                     entry["raw_receipt_sha256"]==
                       transport["raw_receipt_sha256"],
                     "WCL_WITNESS_NOT_FROM_STRICT_EARLIER_RAW")
            else:
                need(entry["value"] is None,
                     "WCL_UNKNOWN_PRE_WAS_FILLED_BY_INFERENCE")
                counts["UNKNOWN_REASON_"+entry["reason"]]+=1
        rows.append({
          "raw_cast_event_id":cast["event_id"],
          "t_ms":cast["t_ms"],
          "numeric_spell_id":cast["spell_id"],
          "strict_pre_signals":facts,
          "source_APL_semantics_injected":False,
          "complete_spell_READY":"UNKNOWN",
          "competing_spells_READY":"UNKNOWN",
        })
    output={
       "schema":"ZrotWclRawActorStrictPreNumericMatrixV1",
       "policy_id":POLICY,
       "source_numeric_transport_sha256":
         transport["numeric_transport_sha256"],
       "source_role":transport["source_cohort_role"],
       "raw_page_identity_sha256":transport["raw_receipt_sha256"],
       "source_event_set_sha256":engine.fingerprint,
       "cast_rows":len(rows),
       "signals_requested":len(signals),
       "signal_status_summary":dict(sorted(counts.items())),
       "per_numeric_cast":rows,
       "WCL_event_clock":"FIGHT_START_RELATIVE_INTEGER_MILLISECONDS",
       "all_known_facts_strictly_before_cast":True,
       "same_timestamp_not_used_as_state":True,
       "SimC_source_or_spell_names_injected":False,
       "complete_READY_proven":0,
       "competitor_priority_proven":0,
       "dummy_error_proven":0,
       "new_WCL_API_calls":0,
       "MAIN_promoted":False
    }
    output["matrix_sha256"]=sha(canonical(output))
    return output


def selftest()->dict:
    # Validate *actual producer format* with new cold-start files: a full
    # fake transport WCL report -> checkpoint -> replay -> actor gate -> lock.
    from pathlib import Path
    with tempfile.TemporaryDirectory(prefix="zrot-wcl-numeric-") as d:
        root=Path(d)
        def actor_bundle(code:str,modifier:int,role:str="DISCOVERY"):
            actor=42
            start=1000
            window=3000
            full_end=7000
            info={
              "report_code":code,"fight_id":1,"revision":2,
              "start":start,"end":start+window,
              "full_fight_end":full_end,
              "requested_window_ms":window,
              "evidence_window":"FIGHT_START_BOUNDED",
              "encounter_id":1,"difficulty":4
            }
            data={
              "reportData":{"report":{
               "code":code,"revision":2,
               "fights":[{"id":1,"startTime":start,
                         "endTime":full_end,"inProgress":False,
                         "friendlyPlayers":[42],
                         "friendlySpecs":["SpecA"],
                         "encounterID":1,"difficulty":4}],
               "masterData":{"actors":[{
                 "id":42,"name":"Synthetic","type":"Player",
                 "subType":"ClassA"}]}
              }}
            }
            gate=identity_gate(data,code,1,actor,"SpecA","ClassA")
            assert gate["fight_start_ms"]==start
            rows=[
              {"timestamp":1100,"type":"applybuff",
               "sourceID":actor,"targetID":actor,"abilityGameID":1001},
              {"timestamp":1500,"type":"cast",
               "sourceID":actor,"targetID":33,"abilityGameID":2001},
              {"timestamp":1500,"type":"removebuff",
               "sourceID":actor,"targetID":actor,"abilityGameID":1001},
              {"timestamp":1600,"type":"cast",
               "sourceID":99,"targetID":33,"abilityGameID":2001},
              {"timestamp":2000,"type":"cast",
               "sourceID":actor,"targetID":33,"abilityGameID":2001},
              {"timestamp":2500,"type":"applybuff",
               "sourceID":actor,"targetID":actor,"abilityGameID":1001},
            ]
            folder=root/code/"fight_1"
            folder.mkdir(parents=True)
            page={"schema":"FreshWCLPageV1","start":start,"next":None,
                  "events":rows}
            page_bytes=canonical(page)
            write_atomic(folder/"page_00000.json",page_bytes)
            state={
              "schema":"FreshWCLCheckpointV1","identity":info,
              "cursor":None,"pages":[{
                "file":"page_00000.json","sha256":sha(page_bytes),
                "start":start,"next":None,
                "event_count":len(rows)}],"complete":True}
            write_atomic(folder/"checkpoint.json",canonical(state))
            proof=replay(folder)
            view=scope_replay(proof,gate)
            lock=lock_candidates([view],min_observations=2,
                                 source_kind=ORIGIN)
            original_receipt={
               "schema":"ZrotWclActorScopedDiscoveryReceiptV1",
               "status":"NUMERIC_DISCOVERY_ONLY",
               "scope_policy_id":POLICY,
               "actor_gate_sha256":sha(canonical(gate)),
               "blind_actor_view_sha256":sha(canonical(view)),
               "readiness":"UNKNOWN","independent_holdout":"NOT_RUN"}
            if role=="HOLDOUT":
                original_receipt={
                  "schema":"ZrotDisjointWclHoldoutObservedActionsV1",
                  "scope_policy_id":POLICY,
                  "status":"DISJOINT_REPORT_HOLDOUT_OBSERVATION_ONLY",
                  "holdout_source_report":code,
                  "holdout_source_fight":1,
                  "holdout_actor_id":42,
                  "different_report_from_discovery":True,
                  "strict_pre_independently_recomputed":True,
                  "candidate_set_frozen_before_holdout":True,
                  "new_discovery_candidates_added":0,
                  "general_rotation_rule_promoted":False,
                  "dummy_trainer_rule_ready":False,
                  "cooldown_and_competing_action_readiness":"UNKNOWN"}
            transp=actor_snapshot(folder,gate,view,original_receipt,
                                  source_role=role)
            return folder,gate,view,original_receipt,lock,transp
        f1,g1,v1,r1,lock1,d1=actor_bundle("ReportABC1",0)
        f2,g2,v2,r2,lock2,d2=actor_bundle("ReportABC2",1,"HOLDOUT")
        need(d1["actor_numeric_cast_count"]==2 and
             d1["raw_aura_boolean_transitions"]==3 and
             d1["other_actor_casts_excluded"]==1 and
             d1["fight_start_abs_ms"]==1000 and
             d1["cast_events"][0]["t_ms"]==500,
             "RAW_TO_FIGHT_RELATIVE_WCL_ACTOR_NORMALIZATION_FAILED")
        need(d1["source_replay_sha256"]==v1["replay_sha256"],
             "NUMERIC_TRANSPORT_SOURCE_REPLAY_DRIFT")
        matrix=strict_pre_numeric_matrix(d1)
        state0=matrix["per_numeric_cast"][0]["strict_pre_signals"][
            "raw_aura_1001_active"]
        state1=matrix["per_numeric_cast"][1]["strict_pre_signals"][
            "raw_aura_1001_active"]
        need(matrix["cast_rows"]==2 and
             matrix["signals_requested"]==1 and
             state0["value"] is True and
             state0["event_t_ms"]<500 and
             state1["value"] is False and
             state1["event_t_ms"]<1000 and
             matrix["complete_READY_proven"]==0,
             "REUSABLE_NUMERIC_STRICT_PRE_MATRIX_INCORRECT")
        # The transported same-time remove is present; StrictPreReplay
        # (not this producer) must exclude it at the 500ms cast.
        from general_rotation_strict_pre_state_engine_v1 import (
            Transition,StrictPreReplay
        )
        t=[Transition(x["source_event_id"],"holdout","r/f","42",
              x["signal"],x["t_ms"],x["value"],None,
              x["raw_receipt_sha256"],quality=VERIFIED)
           for x in d1["transitions"]]
        replayer=StrictPreReplay(t)
        a=replayer.snapshot(cohort_id="holdout",scope="r/f",
                 actor_id="42",at_ms=500,signals=("raw_aura_1001_active",))
        b=replayer.snapshot(cohort_id="holdout",scope="r/f",
                 actor_id="42",at_ms=1000,signals=("raw_aura_1001_active",))
        need(a["signals"]["raw_aura_1001_active"]["value"] is True and
             b["signals"]["raw_aura_1001_active"]["value"] is False,
             "STRICT_PRE_SAME_TIMESTAMP_OR_FIGHT_CLOCK_MISALIGNED")
        # Exact identity, original report list and source view SHA are pinned
        # before constructing this separately reported research fixture.
        fixture=disjoint_numeric_fixture([d1],d2,lock1,
                                        sha(canonical(lock1)))
        need(classify_cohort_identity(d1,d1)["classification"]==
             "EXACT_SAME_RAW_ACTOR_REPLAY" and
             classify_cohort_identity(d1,d2)["report_disjoint"] is True,
             "WCL_COHORT_OVERLAP_GENERIC_GATE_FAILED")
        metrics={"candidate_set_source":"IMMUTABLE_DISCOVERY_LOCK_ONLY",
                 "observed_threshold":1,
                 "no_new_candidate_discovery_in_holdout":True,
                 "no_threshold_retuning":True}
        repeated=replicate_frozen_numeric_candidates(
            [d1],d2,lock1,sha(canonical(lock1)),metrics,
            already_seen_report_codes=("ReportABC1",))
        need(repeated["new_report_disjoint_from_discovery"] is True and
             repeated["reobserved_locked_candidate_count"]==1 and
             repeated["independent_research_holdout_validation"]==
                 "NOT_RUN_FOR_THIS_REPORT",
             "NUMERIC_FROZEN_CROSS_REPORT_REOBSERVATION_NOT_SAFE")
        need(fixture["holdout"]["report_code"]=="ReportABC2" and
             fixture["independent_WCL_holdout_proven"] is False and
             fixture["source_APL_or_SimC_present"] is False,
             "DISCOVERY_LOCK_DISJOINT_HOLDOUT_TRANSPORT_FAILED")
        negatives=0
        import copy
        def rejects(op):
            nonlocal negatives
            try:op()
            except (TransportError,EngineError,ActorGateError,BlindInputError):
                negatives+=1
            else:raise AssertionError("INVALID_RAW_WCL_TRANSPORT_WAS_ACCEPTED")
        rejects(lambda:actor_snapshot(f1,g1,v2,r1))
        rejects(lambda:actor_snapshot(f1,g1,v1,{**r1,
                 "blind_actor_view_sha256":"0"*64}))
        fake=copy.deepcopy(lock1);fake["semantic_names_attached"]=True
        rejects(lambda:disjoint_numeric_fixture(
            [d1],d2,fake,sha(canonical(fake))))
        rejects(lambda:disjoint_numeric_fixture(
            [d1],d2,lock1,"0"*64))
        rejects(lambda:disjoint_numeric_fixture(
            [d1],d1,lock1,sha(canonical(lock1))))
        rejects(lambda:disjoint_numeric_fixture(
            [d2],d1,lock1,sha(canonical(lock1))))
        rejects(lambda:replicate_frozen_numeric_candidates(
            [d1],d1,lock1,sha(canonical(lock1)),metrics))
        rejects(lambda:replicate_frozen_numeric_candidates(
            [d1],d2,lock1,sha(canonical(lock1)),
            {**metrics,"no_threshold_retuning":False}))
        rejects(lambda:replicate_frozen_numeric_candidates(
            [d1],d2,lock1,sha(canonical(lock1)),metrics,
            already_seen_report_codes=("ReportABC2",)))
        orig=(f1/"page_00000.json").read_bytes()
        (f1/"page_00000.json").write_bytes(orig.replace(b"2001",b"2002",1))
        rejects(lambda:actor_snapshot(f1,g1,v1,r1))
        need(negatives==10,"EXPECTED_ALL_NEGATIVE_CONTROLS")
        return {
            "schema":SCHEMA,"selftest":"PASS_OFFLINE_SYNTHETIC",
            "new_cold_start_snapshots":2,
            "generic_actor_scoped_transports":2,
            "strict_PRE_same_time_fence":"PASS",
            "strict_PRE_all_cast_numeric_matrix":"PASS",
            "disjoint_lock_fixture":"PASS",
            "cohort_identity_duplicate_vs_disjoint":"PASS",
            "frozen_numeric_candidate_cross_report_replay":"PASS",
            "negative_controls":negatives,
            "real_wcl_api_requests":0,
            "real_wcl_holdout_completed":False,
            "full_ready_proven":0,"dummy_error_proven":0
        }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--actor-root",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--role",choices=("discovery","holdout"),
                   default="discovery")
    p.add_argument("--discovery-lock",type=Path)
    p.add_argument("--holdout-contract",type=Path)
    a=p.parse_args()
    if a.actor_root is None and a.out is None:
        need(a.role=="discovery" and
             a.discovery_lock is None and a.holdout_contract is None,
             "SELFTEST_CANNOT_USE_PRODUCTION_SOURCE_ARGUMENTS")
        print(json.dumps(selftest(),sort_keys=True))
        return
    need(a.actor_root is not None and a.out is not None,
         "ACTUAL_RAW_ACTOR_ROOT_AND_OUTPUT_REQUIRED")
    root=a.actor_root.resolve(strict=True)
    derived=root/"derived"
    if a.role=="discovery":
        need(a.discovery_lock is None and a.holdout_contract is None,
             "DISCOVERY_CANNOT_LOAD_HOLDOUT_OR_LOCK_SEMANTICS")
        selection=read_json(derived/"selection.json")
        gate=read_json(derived/"identity.json")
        view=read_json(derived/"blind_replay.json")
        receipt=read_json(derived/"receipt.json")
    else:
        need(a.discovery_lock is not None and
             a.holdout_contract is not None,
             "REAL_HOLDOUT_REQUIRES_PREDECLARED_CONTRACT_AND_ORIGINAL_LOCK")
        from wcl_disjoint_holdout_v1 import (
             validate_contract,validate_frozen_lock,assess_holdout
        )
        from wcl_simc_postlock_real_audit_v1 import independently_replay_pre
        contract=validate_contract(read_json(a.holdout_contract))
        lock=validate_frozen_lock(a.discovery_lock.read_bytes(),contract)
        selection=read_json(derived/"source_selection.json")
        gate=read_json(derived/"identity_gate.json")
        view=read_json(derived/"blind_holdout_replay.json")
        receipt=read_json(derived/"holdout_observed_metrics.json")
        # Recompute from the archive independently, no trust in prior metrics.
        raw_base=root/"raw"/selection["report_code"]/(
            "fight_"+str(selection["fight_id"]))
        raw_events=[]
        for page in checked_pages(raw_base,
                read_json(raw_base/"checkpoint.json")):
            raw_events.extend(read_json(raw_base/page["file"])["events"])
        independent=independently_replay_pre(raw_events,gate["actor_id"])
        rebuilt=assess_holdout(contract,lock,selection,view,independent)
        need(all(receipt.get(k)==v for k,v in rebuilt.items()) and
             receipt.get("data_status")=="REAL_OFFICIAL_WCL_SNAPSHOT" and
             receipt.get("WCL_raw_event_count")==len(raw_events),
             "REAL_HOLDOUT_METRICS_DO_NOT_REPLAY_FROM_PRIOR_RAW")
    rawpath=(root/"raw"/selection["report_code"]/
            ("fight_"+str(selection["fight_id"]))).resolve(strict=True)
    need(rawpath.is_relative_to(root) and
         gate["report_code"]==selection["report_code"] and
         gate["fight_id"]==selection["fight_id"],
         "ACTOR_SOURCE_SELECTION_PATH_OR_IDENTITY_MISMATCH")
    result=actor_snapshot(rawpath,gate,view,receipt,
                          source_role=a.role.upper())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    need(not a.out.exists(),"OUTPUT_EXISTS_NO_SILENT_OVERWRITE")
    with a.out.open("xb") as f:f.write(canonical(result))
    print("WCL_ACTOR_REAL_RAW_NUMERIC_STRICT_PRE_SOURCE_SHA256="+
          sha(a.out.read_bytes()))
    print("WCL_ACTOR_REAL_RAW_TRANSPORT_COUNTS="+json.dumps({
        "raw_events":result["raw_event_count"],
        "actor_casts":result["actor_numeric_cast_count"],
        "actor_aura_transitions":result["raw_aura_boolean_transitions"],
        "other_actors_excluded":result["other_actor_casts_excluded"]
    },sort_keys=True))
    print("WCL_DISJOINT_REPORT_OBSERVATION_REPLAYED="+
          str(result["prior_disjoint_report_holdout_recomputed"]))
    print("WCL_REAL_ROTATION_PRIORITY_OR_DUMMY_VERIFIED=False")


if __name__=="__main__":
    main()
