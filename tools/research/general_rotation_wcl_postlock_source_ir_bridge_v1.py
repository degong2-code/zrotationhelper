#!/usr/bin/env python3
"""Reusable WCL blind numeric lock -> strict PRE -> post-lock General Rotation IR.

The discovery boundary accepts *only* a previously frozen numeric WCL lock,
a report/fight roster and numeric cast/transition rows. It cannot receive
SimC source, APL conditions, spell names, talent hints or class semantics.
Only a subsequent, explicit post-lock binding may introduce source APL rows.

A WCL raw-normalization receipt, a numeric lock and a synthetic self-test do
not by themselves certify an independent WCL holdout. The matched source
condition is a diagnostic candidate; a mapped WCL cast is never full READY,
mandatory priority, opener termination or wrong-dummy-cast proof.

No args -> synthetic self-test; explicit args -> offline evidence transport.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from general_rotation_strict_pre_state_engine_v1 import (
    Transition, StrictPreReplay, StrictPreError, VERIFIED, UNVERIFIED,
    RAW_SOURCE, canonical as canonical_pre
)
from general_rotation_source_hypothesis_ir_v1 import SCHEMA as SOURCE_SCHEMA
from general_rotation_original_source_evidence_bridge_v1 import (
    SCHEMA as EVIDENCE_SCHEMA
)
from simc_apl_semantic_ir_v2 import evaluate_ast, truth, canonical
from general_rotation_decision_proof_engine_v1 import (
    Identity, GateContract, decide_candidate, evaluate_priority, UNKNOWN
)
from post_lock_simc_wcl_guard_replay import _locked_numeric_actions

SCHEMA="ZrotGenericWclStrictPrePostlockSourceIRBridgeV1"
NUMERIC_SCHEMA="ZrotGenericIndependentWclNumericCohortV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
LOCK_SCHEMA="ZrotWave3NumericCandidateLock"
FIXTURE_SCHEMA="ZrotGenericWclPostlockSourceBridgeInputV1"
BINDING_SCHEMA="ZrotGenericWclPostlockNumericToSourceBindingV1"
HEX=re.compile(r"^[0-9a-f]{64}$")
TOKEN=re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]*$")
ALLOWED_ORIGIN=frozenset(("SYNTHETIC_FIXTURE",
                          "ATTESTED_RAW_WCL_REPLAY"))


class WclBridgeError(ValueError):
    pass


def need(ok:bool,reason:str):
    if not ok:raise WclBridgeError(reason)


def sha(raw:bytes)->str:return sha256(raw).hexdigest()


def load(path:Path)->tuple[dict,bytes]:
    need(path.is_file() and not path.is_symlink(),
         "PINNED_NON_SYMLINKED_SOURCE_REQUIRED")
    raw=path.read_bytes()
    need(0<len(raw)<15_000_000,"UNBOUNDED_OR_EMPTY_SOURCE")
    def unique(pairs):
        out={}
        for k,v in pairs:
            need(k not in out,"DUPLICATE_JSON_KEY")
            out[k]=v
        return out
    def nonfinite(_):raise WclBridgeError("NONFINITE_JSON_TOKEN")
    obj=json.loads(raw,object_pairs_hook=unique,parse_constant=nonfinite)
    need(type(obj)==dict,"JSON_OBJECT_REQUIRED")
    return obj,raw


def numeric_frozen_boundary(lock_bytes:bytes,expected_sha256:str,
                            discovery_roster:dict,holdout:dict,
                            events:list[dict])->dict:
    """WCL-only first phase: NO SimC IR argument and no source name lookup."""
    need(type(expected_sha256)==str and HEX.fullmatch(expected_sha256)
         and sha(lock_bytes)==expected_sha256,
         "FROZEN_NUMERIC_WCL_LOCK_SHA256_MISMATCH")
    ids=_locked_numeric_actions(lock_bytes,expected_sha256)
    def unique(pairs):
        out={}
        for k,v in pairs:
            need(k not in out,"DUPLICATE_WCL_LOCK_FIELD")
            out[k]=v
        return out
    lock=json.loads(lock_bytes,object_pairs_hook=unique,
                    parse_constant=lambda v:(_ for _ in ()).throw(
                        WclBridgeError("LOCK_NONFINITE")))
    origin=lock.get("source_kind")
    need(lock.get("schema")==LOCK_SCHEMA and
         lock.get("status")=="LOCKED_NUMERIC_ONLY" and
         origin in ALLOWED_ORIGIN and
         lock.get("threshold_retuned_after_discovery") is False and
         lock.get("semantic_names_attached") is False and
         lock.get("holdout_validated") is False and
         lock.get("gameplay_rule_claim") is False and
         type(lock.get("prelocked_min_observations")) is int and
         1<=lock["prelocked_min_observations"]<=1000,
         "WCL_NUMERIC_CANDIDATE_LOCK_STATE_CHANGED")
    for c in lock["candidates"]:
        need(c.get("action_spell_id") in ids and
             c.get("semantic_name") is None and
             c.get("readiness")=="UNKNOWN" and
             c.get("priority_claim") is False and
             c.get("causality_claim") is False,
             "LOCKED_NUMERIC_CANDIDATE_UPGRADED")
    need(len(ids)==len(lock["candidates"]),"DUPLICATED_NUMERIC_CANDIDATE_ID")
    replay_hashes=lock.get("source_replay_sha256")
    need(type(replay_hashes)==list and replay_hashes and
         all(type(x)==str and HEX.fullmatch(x) for x in replay_hashes) and
         len(set(replay_hashes))==len(replay_hashes) and
         len(replay_hashes)==lock.get("discovery_fight_count"),
         "LOCKED_DISCOVERY_REPLAY_HASHES_REQUIRED")
    need(type(discovery_roster)==dict and
         discovery_roster.get("source_kind")==origin and
         discovery_roster.get("source_replay_sha256")==sorted(replay_hashes) and
         discovery_roster.get("frozen_min_observations")==
           lock["prelocked_min_observations"],
         "DISCOVERY_ROSTER_NOT_LOCK_BOUND")
    rows=discovery_roster.get("report_fights")
    need(type(rows)==list and len(rows)==len(replay_hashes),
         "DISCOVERY_REPORT_ROSTER_INCOMPLETE")
    known_reports=set();source_receipts=set()
    for r in rows:
        need(type(r)==dict and type(r.get("report_code"))==str and
             bool(r["report_code"]) and
             type(r.get("fight_id")) is int and r["fight_id"]>0 and
             type(r.get("source_replay_sha256")) is str and
             r["source_replay_sha256"] in replay_hashes and
             r["report_code"] not in known_reports,
             "DISCOVERY_REPORT_IDENTITY_OR_DUPLICATE_INVALID")
        known_reports.add(r["report_code"])
        source_receipts.add(r["source_replay_sha256"])
    need(source_receipts==set(replay_hashes),
         "DISCOVERY_SOURCE_REPLAY_REPORT_1_TO_1_MISMATCH")
    need(type(holdout)==dict and
         holdout.get("source_kind")==origin and
         type(holdout.get("cohort_id"))==str and holdout["cohort_id"] and
         type(holdout.get("report_code"))==str and
         holdout.get("report_code") not in known_reports and
         type(holdout.get("fight_id")) is int and holdout["fight_id"]>0 and
         type(holdout.get("actor_id")) is str and holdout["actor_id"] and
         type(holdout.get("raw_receipt_sha256"))==str and
         HEX.fullmatch(holdout["raw_receipt_sha256"]),
         "HOLDOUT_REPORT_ACTOR_OR_ORIGIN_NOT_DISJOINT")
    scope=holdout["report_code"]+"/"+str(holdout["fight_id"])
    need(type(events)==list and events and len(events)<=50000,
         "BOUNDED_NUMERIC_HOLDOUT_CASTS_REQUIRED")
    numeric=[];seen=set()
    for e in events:
        need(type(e)==dict and set(e)=={
             "event_id","t_ms","spell_id","source_kind"} and
             type(e["event_id"]) is str and e["event_id"] and
             e["event_id"] not in seen and
             type(e["t_ms"]) is int and e["t_ms"]>=0 and
             type(e["spell_id"]) is int and e["spell_id"]>0 and
             e["source_kind"]==RAW_SOURCE,
             "NON_NUMERIC_OR_DUPLICATE_WCL_CAST")
        seen.add(e["event_id"])
        numeric.append({"event_id":e["event_id"],
                        "at_ms":e["t_ms"],"spell_id":e["spell_id"],
                        "frozen_numeric_candidate":e["spell_id"] in ids})
    numeric.sort(key=lambda x:(x["at_ms"],x["event_id"]))
    counts=Counter(c["spell_id"] for c in numeric)
    return {
        "schema":NUMERIC_SCHEMA,"policy_id":POLICY,
        "source_kind":origin,
        "lock_sha256":expected_sha256,
        "numeric_locked_spell_ids":sorted(ids),
        "discovery_roster_sha256":sha(canonical(discovery_roster)),
        "holdout_raw_receipt_sha256":holdout["raw_receipt_sha256"],
        "holdout_cohort_id":holdout["cohort_id"],
        "holdout_scope":scope,"holdout_actor":holdout["actor_id"],
        "declared_discovery_report_disjoint":True,
        "raw_discovery_and_holdout_independent_audit":"NOT_RUN",
        "strict_PRE_not_yet_computed":True,
        "numeric_casts":numeric,
        "candidate_observed_cast_counts":[
            {"spell_id":i,"count":counts.get(i,0)}
            for i in sorted(ids)],
        "noncandidate_holdout_spells":sorted(set(counts)-ids),
        "candidate_set_changed_after_lock":False,
        "source_APL_injected_in_numeric_phase":False,
        "holdout_is_actual_verified_WCL":False,
        "ready_or_priority_proven":False,
        "WCL_calls":0
    }


def _strict_transitions(numeric:dict,fixture:dict)->StrictPreReplay:
    rows=fixture.get("transitions")
    need(type(rows)==list and len(rows)<=100000,
         "BOUNDED_WCL_STRICT_PRE_TRANSITIONS_REQUIRED")
    trans=[]
    for x in rows:
        need(type(x)==dict and set(x)=={
             "source_event_id","signal","t_ms","value",
             "valid_until_ms","raw_receipt_sha256",
             "source_kind","quality"} and
             type(x["source_event_id"]) is str and x["source_event_id"] and
             type(x["signal"]) is str and TOKEN.fullmatch(x["signal"]) and
             x["source_kind"]==RAW_SOURCE and
             x["quality"] in (VERIFIED,UNVERIFIED) and
             x["raw_receipt_sha256"]==numeric["holdout_raw_receipt_sha256"],
             "UNPINNED_OR_SEMANTIC_WCL_PRE_TRANSITION")
        trans.append(Transition(
          x["source_event_id"],numeric["holdout_cohort_id"],
          numeric["holdout_scope"],numeric["holdout_actor"],
          x["signal"],x["t_ms"],x["value"],x["valid_until_ms"],
          x["raw_receipt_sha256"],source_kind=x["source_kind"],
          quality=x["quality"]))
    return StrictPreReplay(trans)


def postlock_source_probe(numeric:dict,fixture:dict,source_case:dict,
                          binding:dict)->dict:
    """Second phase only. An explicit binding is a hypothesis, not game truth."""
    need(numeric.get("schema")==NUMERIC_SCHEMA and
         numeric.get("source_APL_injected_in_numeric_phase") is False and
         numeric.get("candidate_set_changed_after_lock") is False and
         numeric.get("raw_discovery_and_holdout_independent_audit")=="NOT_RUN",
         "BLIND_NUMERIC_STAGE_CANNOT_BE_SEMANTICALLY_REWRITTEN")
    need(source_case.get("schema")==EVIDENCE_SCHEMA and
         source_case.get("policy_id")==POLICY and
         source_case.get("source_full_READY_proven")==0 and
         source_case.get("source_order_priority_proven")==0 and
         source_case.get("WCL_independent_candidate_lock")=="NOT_RUN" and
         source_case.get("WCL_independent_holdout")=="NOT_RUN" and
         source_case.get("dummy_wrong_skill")=="UNKNOWN" and
         source_case.get("native_selected_used_as_positive_ready_input") is False,
         "SOURCE_CASE_ALREADY_PROMOTED_AS_WCL_READINESS")
    graph=source_case.get("source_hypothesis_IR",{})
    need(graph.get("schema")==SOURCE_SCHEMA and
         graph.get("evidence_status",{}).get(
             "validated_general_rotation_priority") is False,
         "SOURCE_APL_GRAPH_NOT_HYPOTHESIS")
    need(type(binding)==dict and
         binding.get("schema")==BINDING_SCHEMA and
         binding.get("policy_id")==POLICY and
         binding.get("bound_numeric_lock_sha256")==numeric["lock_sha256"] and
         binding.get("source_profile_git_blob")==graph.get("source_git_blob") and
         binding.get("source_spec")==source_case.get("source_spec") and
         binding.get("source_target_count")==source_case.get("target_count") and
         binding.get("binding_stage")=="POST_LOCK_ONLY" and
         binding.get("action_identity_and_mechanic_independently_audited") is False and
         binding.get("build_equivalence_independently_verified") is False and
         binding.get("WCL_target_count_at_cast_verified") is False,
         "POSTLOCK_MAPPING_UNVERIFIED_CANNOT_BE_PROMOTED")
    mappings=binding.get("numeric_to_source_rows")
    need(type(mappings)==list and len(mappings)<=200,
         "POSTLOCK_NUMERIC_BINDINGS_MALFORMED")
    bound={};lists=graph["source_only_priority_graph"]["lists"]
    for m in mappings:
        need(type(m)==dict and set(m)=={
             "spell_id","source_list","source_index",
             "source_row_sha256","symbol_to_raw_signal"} and
             type(m["spell_id"]) is int and m["spell_id"]>0 and
             m["spell_id"] in numeric["numeric_locked_spell_ids"] and
             m["spell_id"] not in bound and
             type(m["source_list"]) is str and m["source_list"] in lists and
             type(m["source_index"]) is int and
             0<=m["source_index"]<len(lists[m["source_list"]]) and
             m["source_row_sha256"]==
              lists[m["source_list"]][m["source_index"]]["identity"][
                  "source_line_sha256"] and
             type(m["symbol_to_raw_signal"]) is dict,
             "NUMERIC_ACTION_TO_SOURCE_ID_NOT_POSTLOCK_PROVEN")
        node=lists[m["source_list"]][m["source_index"]]
        require_symbols=set(node["conditions"].get("if",{}).get("symbols",[]))
        symbols=m["symbol_to_raw_signal"]
        need(set(symbols)<=require_symbols and
             all(type(v)==str and TOKEN.fullmatch(v) for v in symbols.values()) and
             len(set(symbols.values()))==len(symbols),
             "UNDECLARED_RAW_SIGNAL_MAPPING_OR_DUPLICATE")
        bound[m["spell_id"]]=(node,m)
    replay=_strict_transitions(numeric,fixture)
    output=[];counts=Counter()
    for cast in numeric["numeric_casts"]:
        item=bound.get(cast["spell_id"])
        if item is None:
            counts["UNKNOWN_NO_POSTLOCK_SOURCE_BINDING"]+=1
            output.append({
              "raw_event_id":cast["event_id"],"at_ms":cast["at_ms"],
              "spell_id":cast["spell_id"],
              "postlock_source_row":"UNKNOWN",
              "source_if_hypothesis_at_WCL_PRE":"UNKNOWN",
              "WCL_strict_pre_state":"NOT_REQUESTED",
              "action_READY":"UNKNOWN","competitor_priority":"UNKNOWN",
              "dummy_wrong_cast":"UNKNOWN"})
            continue
        node,m=item
        cond=node["conditions"].get("if")
        s_to_raw=m["symbol_to_raw_signal"]
        signals=tuple(sorted(set(s_to_raw.values())))
        state=(replay.snapshot(
              cohort_id=numeric["holdout_cohort_id"],
              scope=numeric["holdout_scope"],
              actor_id=numeric["holdout_actor"],
              at_ms=cast["at_ms"],signals=signals)
              if signals else None)
        wcl_facts={}
        for symbol,signal in s_to_raw.items():
            evidence=state["signals"][signal]
            if evidence["status"]=="KNOWN" and evidence["value"] is not None:
                wcl_facts[symbol]={
                   "value":1.0 if evidence["value"] else 0.0,
                   "timestamp":evidence["event_t_ms"],
                   "provenance":"STRICT_PRE_OBSERVATION"}
        tested=(None if cond is None else
                truth(evaluate_ast(
                     cond["source_ast"],wcl_facts,
                     action_timestamp=cast["at_ms"],strict_pre=True)))
        guard=("SOURCE_IF_ABSENT_NOT_READY_PROOF" if cond is None else
               "TRUE" if tested is True else
               "FALSE" if tested is False else "UNKNOWN")
        counts[guard]+=1
        ident=Identity(
           scope="POSTLOCK_NUMERIC:"+str(cast["spell_id"]),
           source_sha256=node["identity"]["source_line_sha256"],
           t_ms=cast["at_ms"],
           ordinal=m["source_index"],
           occurrence=int(sha(cast["event_id"].encode())[:12],16))
        # No independent source->WCL field binding audit or build match.
        # Therefore even a verified numeric raw PRE signal cannot yet
        # become a proven necessary game gate. Only a hypothesis is exposed.
        gate=GateContract("UNVERIFIED_POSTLOCK_SOURCE",
                          ("source_if","virtual_method_ready",
                           "build_and_target_context"),
                          node["identity"]["source_line_sha256"],
                          closed=False)
        candidate=decide_candidate(
            ident,gate,[],node["kind"]=="EXECUTABLE_SOURCE_CANDIDATE")
        frontier=evaluate_priority(
            [candidate],0,source_order_complete=False,
            native_selected_name=None)
        need(candidate["decision"]==UNKNOWN and
             frontier["decision"]==UNKNOWN and
             not candidate["dummy_error_permitted"],
             "POSTLOCK_SOURCE_HYPOTHESIS_WRONGLY_PROVED_READY")
        output.append({
            "raw_event_id":cast["event_id"],"at_ms":cast["at_ms"],
            "spell_id":cast["spell_id"],
            "postlock_source_row":node["identity"],
            "postlock_source_candidate":node["action"],
            "source_if_hypothesis_at_WCL_PRE":guard,
            "WCL_strict_pre_state":state["signals"] if state else {},
            "WCL_strict_pre_facts_used_for_hypothesis":wcl_facts,
            "independent_source_action_numeric_mapping":"NOT_AUDITED",
            "build_and_WCL_target_equivalence":"UNKNOWN",
            "source_ready_proof":candidate,
            "source_priority_proof":frontier,
            "action_READY":"UNKNOWN",
            "competitor_priority":"UNKNOWN",
            "dummy_wrong_cast":"UNKNOWN"
        })
    return {
       "schema":SCHEMA,"policy_id":POLICY,
       "source_spec":source_case["source_spec"],
       "source_hypothesis_git_blob":graph["source_git_blob"],
       "source_case_sha256":sha(canonical(source_case)),
       "frozen_numeric_lock_sha256":numeric["lock_sha256"],
       "numeric_WCL_only_phase_sha256":sha(canonical(numeric)),
       "source_binding_sha256":sha(canonical(binding)),
       "holdout_evidence_source_kind":numeric["source_kind"],
       "source_wcl_binding_applied_only_after_lock":True,
       "raw_discovery_and_holdout_independent_audit":"NOT_RUN",
       "real_WCL_holdout_validated":False,
       "real_WCL_build_equivalence":"UNKNOWN",
       "WCL_target_count_at_action":"UNKNOWN",
       "source_vs_WCL_hypothesis_at_PRE_counts":dict(sorted(counts.items())),
       "per_numeric_cast_conditional_probes":output,
       "frozen_candidates_count":len(numeric["numeric_locked_spell_ids"]),
       "holdout_numeric_casts":len(numeric["numeric_casts"]),
       "complete_source_priority_proven":False,
       "physical_READY_proven":0,
       "real_General_Rotation_rule_promoted":False,
       "dummy_training_error_proven":False,
       "opener_end":"UNKNOWN","WCL_API_calls":0,
       "new_SimC_CXX_builds":0,"MAIN_promoted":False,
    }


def bridge(lock_raw:bytes,lock_sha256:str,fixture:dict,
           source_case:dict,binding:dict)->dict:
    need(fixture.get("schema")==FIXTURE_SCHEMA and
         fixture.get("policy_id")==POLICY,
         "OFFLINE_WCL_COHORT_INPUT_NOT_TYPED")
    numeric=numeric_frozen_boundary(
       lock_raw,lock_sha256,fixture["discovery_roster"],
       fixture["holdout"],fixture["cast_events"])
    result=postlock_source_probe(numeric,fixture,source_case,binding)
    result["numeric_phase"]=numeric
    return result


def selftest()->dict:
    # Source test is deliberately created AFTER an already frozen numeric
    # lock. Build profiles have no semantic access inside numeric phase.
    from general_rotation_source_hypothesis_ir_v1 import compile_profile
    from simc_apl_semantic_ir_v2 import git_blob
    import copy
    a="b"*64
    def fake_lock():
        data={
          "schema":LOCK_SCHEMA,"status":"LOCKED_NUMERIC_ONLY",
          "source_kind":"SYNTHETIC_FIXTURE",
          "source_replay_sha256":[a],
          "discovery_fight_count":1,
          "candidate_n":1,
          "candidates":[{
             "action_spell_id":1101,"observed_event_count":2,
             "distinct_numeric_actor_count":1,
             "semantic_name":None,"gameplay_rule_claim":False,
             "priority_claim":False,"causality_claim":False,
             "readiness":"UNKNOWN"}],
          "prelocked_min_observations":2,
          "threshold_retuned_after_discovery":False,
          "semantic_names_attached":False,"gameplay_rule_claim":False,
          "holdout_validated":False,
          "wcl_blind_candidate_producer":"NUMERIC_CAST_COUNTS_BLIND_INPUT",
          "independent_fresh_WCL_data_verified":False}
        return canonical(data)
    raw=fake_lock();h=sha(raw)
    roster={"source_kind":"SYNTHETIC_FIXTURE",
            "source_replay_sha256":[a],
            "frozen_min_observations":2,
            "report_fights":[{"report_code":"discovery-1",
                              "fight_id":1,"source_replay_sha256":a}]}
    holdout={"source_kind":"SYNTHETIC_FIXTURE",
             "cohort_id":"holdout-2","report_code":"holdout-2",
             "fight_id":4,"actor_id":"actor-synthetic",
             "raw_receipt_sha256":"c"*64}
    casts=[
        {"event_id":"cast-one","t_ms":1000,
         "spell_id":1101,"source_kind":RAW_SOURCE},
        {"event_id":"cast-other","t_ms":1100,
         "spell_id":9999,"source_kind":RAW_SOURCE}]
    def trans(i,t,v,*,quality=VERIFIED,until=None):
        return {"source_event_id":i,"signal":"raw.proc",
                "t_ms":t,"value":v,"valid_until_ms":until,
                "raw_receipt_sha256":holdout["raw_receipt_sha256"],
                "source_kind":RAW_SOURCE,"quality":quality}
    fixture={"schema":FIXTURE_SCHEMA,"policy_id":POLICY,
             "discovery_roster":roster,"holdout":holdout,
             "cast_events":casts,
             "transitions":[trans("old",900,True),
                            trans("same-time",1000,False)]}
    n=numeric_frozen_boundary(raw,h,roster,holdout,casts)
    need(n["source_APL_injected_in_numeric_phase"] is False and
         n["numeric_locked_spell_ids"]==[1101] and
         n["noncandidate_holdout_spells"]==[9999],
         "BLIND_NUMERIC_PHASE_DID_NOT_STAY_BLIND")
    def case(profile:str,cls:str,spec:str):
        raw_profile=(cls+'="Synthetic"\n'+'spec='+spec+'\n'+profile+'\n').encode()
        model=compile_profile(raw_profile,{
            "key":spec,"class_key":cls,"git_blob":git_blob(raw_profile)})
        return {
           "schema":EVIDENCE_SCHEMA,"policy_id":POLICY,
           "source_spec":spec,"class_key":cls,"target_count":1,
           "source_hypothesis_IR":model,
           "source_full_READY_proven":0,
           "source_order_priority_proven":0,
           "WCL_independent_candidate_lock":"NOT_RUN",
           "WCL_independent_holdout":"NOT_RUN",
           "dummy_wrong_skill":"UNKNOWN",
           "native_selected_used_as_positive_ready_input":False}
    w=case("actions=synthetic_alpha,if=buff.proc.up","warrior","fury")
    m=case("actions=synthetic_beta,if=buff.proc.up","mage","arcane")
    def bind(source):
        row=source["source_hypothesis_IR"][
            "source_only_priority_graph"]["lists"]["default"][0]
        return {
           "schema":BINDING_SCHEMA,"policy_id":POLICY,
           "bound_numeric_lock_sha256":h,
           "source_profile_git_blob":source["source_hypothesis_IR"][
               "source_git_blob"],
           "source_spec":source["source_spec"],"source_target_count":1,
           "binding_stage":"POST_LOCK_ONLY",
           "action_identity_and_mechanic_independently_audited":False,
           "build_equivalence_independently_verified":False,
           "WCL_target_count_at_cast_verified":False,
           "numeric_to_source_rows":[{
              "spell_id":1101,"source_list":"default",
              "source_index":0,
              "source_row_sha256":row["identity"]["source_line_sha256"],
              "symbol_to_raw_signal":{"buff.proc.up":"raw.proc"}}]}
    x=bridge(raw,h,fixture,w,bind(w));y=bridge(raw,h,fixture,m,bind(m))
    for result in (x,y):
        need(result["source_vs_WCL_hypothesis_at_PRE_counts"]["TRUE"]==1
             and result["source_vs_WCL_hypothesis_at_PRE_counts"][
                 "UNKNOWN_NO_POSTLOCK_SOURCE_BINDING"]==1 and
             result["physical_READY_proven"]==0 and
             not result["dummy_training_error_proven"],
             "MULTI_CLASS_BOUNDED_POSTLOCK_SOURCE_PROBE_FAILED")
    events=copy.deepcopy(fixture)
    events["transitions"]=[trans("same",1000,True)]
    same=bridge(raw,h,events,w,bind(w))
    need(same["per_numeric_cast_conditional_probes"][0][
         "source_if_hypothesis_at_WCL_PRE"]=="UNKNOWN",
         "WCL_SAME_TIMESTAMP_LEAKED_AS_PRE")
    ambiguity=copy.deepcopy(fixture)
    ambiguity["transitions"]=[trans("one",900,True),
                               trans("two",900,False)]
    checked=bridge(raw,h,ambiguity,w,bind(w))
    need(checked["per_numeric_cast_conditional_probes"][0][
         "source_if_hypothesis_at_WCL_PRE"]=="UNKNOWN",
         "WCL_AMBIGUOUS_PRE_WRONGLY_USED")
    negatives=0
    def must_fail(call):
        nonlocal negatives
        try:call()
        except (ValueError,StrictPreError):negatives+=1
        else:raise AssertionError("BLIND_TO_SOURCE_PROOF_BYPASS_ACCEPTED")
    must_fail(lambda:bridge(raw,"0"*64,fixture,w,bind(w)))
    roster_bad=copy.deepcopy(fixture)
    roster_bad["holdout"]["report_code"]="discovery-1"
    must_fail(lambda:bridge(raw,h,roster_bad,w,bind(w)))
    lock_bad=copy.deepcopy(json.loads(raw));lock_bad["semantic_names_attached"]=True
    fake=canonical(lock_bad)
    must_fail(lambda:bridge(fake,sha(fake),fixture,w,bind(w)))
    binding_bad=bind(w);binding_bad["bound_numeric_lock_sha256"]="0"*64
    must_fail(lambda:bridge(raw,h,fixture,w,binding_bad))
    binding_bad=bind(w);binding_bad["numeric_to_source_rows"][0][
        "source_row_sha256"]="0"*64
    must_fail(lambda:bridge(raw,h,fixture,w,binding_bad))
    binding_bad=bind(w);binding_bad["numeric_to_source_rows"][0][
        "symbol_to_raw_signal"]={"buff.proc.up":"some.unpinned","evil":"raw.proc"}
    must_fail(lambda:bridge(raw,h,fixture,w,binding_bad))
    forged=copy.deepcopy(w);forged["source_full_READY_proven"]=1
    must_fail(lambda:bridge(raw,h,fixture,forged,bind(w)))
    spoof=copy.deepcopy(fixture);spoof["cast_events"][0]["spell_id"]="synthetic_alpha"
    must_fail(lambda:bridge(raw,h,spoof,w,bind(w)))
    quality=copy.deepcopy(fixture)
    quality["transitions"][0]["quality"]=UNVERIFIED
    unknown=bridge(raw,h,quality,w,bind(w))
    need(unknown["per_numeric_cast_conditional_probes"][0][
         "source_if_hypothesis_at_WCL_PRE"]=="UNKNOWN",
         "UNVERIFIED_NORMALIZATION_WAS_TREATED_AS_VALID_PRE")
    return {"schema":SCHEMA,"status":"PASS_TWO_CLASS_SYNTHETIC",
            "separate_numeric_blind_phase":True,
            "reused_strict_pre_replay":True,
            "reused_source_hypothesis_and_proof_engine":True,
            "synthetic_source_classes_tested":2,
            "negative_controls":negatives,
            "WCL_real_holdout_verified":False,
            "source_if_state_probe_synthetic_tested":True,
            "full_READY_proven":0,
            "dummy_wrong_cast_proven":0,"new_WCL_API_calls":0,
            "new_SimC_CXX_builds":0}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frozen-lock",type=Path)
    ap.add_argument("--lock-sha256")
    ap.add_argument("--cohort-fixture",type=Path)
    ap.add_argument("--source-case",type=Path)
    ap.add_argument("--postlock-binding",type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if all(v is None for v in vars(args).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(v is not None for v in vars(args).values()),
         "FROZEN_NUMERIC_LOCK_AND_SEPARATE_POSTLOCK_INPUTS_REQUIRED")
    lock_raw=args.frozen_lock.read_bytes()
    fixture,_=load(args.cohort_fixture)
    source,_=load(args.source_case)
    binding,_=load(args.postlock_binding)
    result=bridge(lock_raw,args.lock_sha256,fixture,source,binding)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("xb") as handle:handle.write(canonical(result))
    print("GENERIC_WCL_STRICT_PRE_POSTLOCK_BRIDGE_SHA256="+
          sha(args.out.read_bytes()))
    print("GENERIC_WCL_STRICT_PRE_POSTLOCK_RESULTS="+
          json.dumps(result["source_vs_WCL_hypothesis_at_PRE_counts"],
                     sort_keys=True))
    print("WCL_INDEPENDENT_HOLDOUT_PROVEN="+
          str(result["real_WCL_holdout_validated"]))
    print("DUMMY_ERROR_PROVEN="+
          str(result["dummy_training_error_proven"]))


if __name__=="__main__":
    main()
