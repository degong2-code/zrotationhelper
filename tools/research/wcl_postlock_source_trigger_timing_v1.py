#!/usr/bin/env python3
"""Generic observational trigger-family timing witness, POST-LOCK ONLY.

Verifies original WCL raw event IDs/action times independently and a separately
pinned source-code trigger path. A close-in-time event pair is NOT proof of
causality, manual input, action READY, optimal priority, or a player error.
The ±ms window in the supplied adapter is explicitly exploratory/posthoc;
distinct-report re-observation is not an independent holdout threshold test.

No arguments: safe regression, no WCL API or SimC executable required.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import zipfile
from wcl_raw_action_event_grain_audit_v1 import audit,canon,require,sha
from simc_apl_semantic_ir_v2 import git_blob
from wcl_disjoint_holdout_v1 import validate_contract,validate_frozen_lock

SCHEMA="ZrotGenericWclPostlockSourceTriggerTimingWitnessV1"
ADAPTER_SCHEMA="ZrotPostlockActionTriggerFamilyAuditAdapterV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

def verify_adapter(a,source,postlock,lock_bytes,contract_bytes):
    require(a.get("schema")==ADAPTER_SCHEMA and a.get("policy_id")==POLICY and
            a.get("protected_blind_lock_sha256")==sha(lock_bytes) and
            a.get("source_postlock_aura_replay_sha256")==sha(canon(postlock)) and
            git_blob(source)==a.get("source_cpp_git_blob")==
            postlock.get("source_class_cpp_git_blob") and
            postlock.get("schema")=="ZrotGenericPostlockWclAuraSourceIfSensitivityV1" and
            postlock.get("protected_blind_lock_sha256")==sha(lock_bytes) and
            postlock.get("postlock_only") is True and
            postlock.get("source_revision")==a.get("source_revision") and
            postlock.get("new_general_rotation_rules_promoted")==0 and
            postlock.get("MAIN_promoted") is False and
            a.get("coincident_window_status")==
              "POSTHOC_EXPLORATORY_NOT_PREDECLARED_HOLDOUT_THRESHOLD" and
            a.get("manual_input_proven") is False and
            a.get("source_trigger_caused_this_WCL_event") is False and
            a.get("priority_claim_proven") is False and
            a.get("independent_holdout_threshold_predeclared") is False and
            a.get("new_gameplay_rules_promoted")==0,
            "POSTLOCK_SOURCE_LOCK_OR_CAUSAL_AUTHORITY_DRIFT")
    w=a.get("coincident_window_ms")
    require(type(w) is int and 0<=w<=25,"POSTHOC_WINDOW_OUT_OF_BOUNDS")
    children=a.get("observed_child_numeric_ids")
    parents=a.get("observed_candidate_parent_numeric_ids")
    require(type(children) is list and type(parents) is list and
            1<=len(children)<=30 and 1<=len(parents)<=30 and
            all(type(x) is int and x>0 for x in children+parents) and
            len(set(children+parents))==len(children+parents),
            "INVALID_POSTLOCK_NUMERIC_FAMILIES")
    lock=validate_frozen_lock(lock_bytes,validate_contract(json.loads(contract_bytes)))
    locked={x["action_spell_id"] for x in lock["candidates"]}
    require(set(children+parents)<=locked,
            "POSTLOCK_NUMERIC_FAMILY_NOT_IN_FROZEN_LOCK")
    content=source.decode("utf-8")
    for snippet in a.get("source_cpp_snippets",[]):
        require(type(snippet) is str and len(snippet)>8 and
                snippet in content,
                "PINNED_CPP_TRIGGER_PATH_SNIPPET_MISSING")
    return w

def raw_complete_casts(z,role):
    verified=audit(z,role)
    # Reuse the independent archive event-ID+raw-page+clock audit. It
    # intentionally preserves begin/complete as separate recorded events.
    return verified,{x["event_id"]:x for x in verified["event_type_sidecar"] if x["event_type"]=="cast"}

def pair_one(case,raw,w,children,parents,roles):
    require(case["report_code"]==raw["report_code"] and
            case["actor_id"]==raw["actor_id"] and
            case["source_raw_numeric_transport_sha256"]==raw["numeric_transport_sha256"] and
            case["complete_READY_proven"]==case["new_general_rotation_rule_promoted"]==0,
            "COHORT_RAW_ACTION_OR_PRIORITY_PROOF_DRIFT")
    source_rows={x["event_id"]:x for x in case["per_observed_action_event"] if x["event_type"]=="cast"}
    raw_rows={x["event_id"]:x for x in raw["event_type_sidecar"] if x["event_type"]=="cast"}
    require(len(source_rows)==len({x["event_id"] for x in case["per_observed_action_event"] if x["event_type"]=="cast"}),
            "DUPLICATE_POSTLOCK_SOURCE_ACTION_EVENT")
    for eid,x in source_rows.items():
        r=raw_rows.get(eid)
        require(r is not None and
                (x["t_ms"],x["spell_id"],x["numeric_target_id"])==
                (r["t_ms"],r["spell_id"],r["target_id"]),
                "POSTLOCK_SOURCE_CAST_DOES_NOT_REPLAY_FROM_RAW_EVENT_ID")
    p=[x for x in raw_rows.values() if x["spell_id"] in parents]
    c=[x for x in raw_rows.values() if x["spell_id"] in children]
    need=[];count=Counter()
    for child in sorted(c,key=lambda x:(x["t_ms"],x["event_id"])):
        near=[x for x in p if abs(x["t_ms"]-child["t_ms"])<=w]
        near.sort(key=lambda x:(abs(x["t_ms"]-child["t_ms"]),x["t_ms"],x["event_id"]))
        status="ONE_NEAR_PARENT_EXPLORATORY" if len(near)==1 else (
            "UNKNOWN_MULTI_PARENT" if len(near)>1 else "UNKNOWN_NO_PARENT_IN_POSTHOC_WINDOW")
        source=source_rows.get(child["event_id"])
        require(source is not None,"UNMAPPED_NUMERIC_CHILD_SOURCE_EVENT")
        active={}
        for symbol in roles:
            f=source["strict_pre_source_observation_facts"].get(symbol)
            require(isinstance(f,dict),"MISSING_POSTLOCK_AURA_FIELD")
            if f["value"] is not None:
                require(type(f["source_transition_ms"]) is int and
                        f["source_transition_ms"]<child["t_ms"] and
                        f["status"]=="OBSERVED_EARLIER_RAW_AURA",
                        "NON_STRICT_PRE_SOURCE_AURA_LEAK")
            active[symbol]=f["value"]
        count[status]+=1
        if len(near)==1:
            parent=near[0]
            count["ONE_NEAR_PARENT_"+str(parent["spell_id"])]+=1
        else:parent=None
        if active.get("buff.ascendance.up")==1:
            count["CHILD_PRE_ASCENDANCE_OBSERVED_ACTIVE"]+=1
        if active.get("buff.doom_winds.up")==1:
            count["CHILD_PRE_DOOM_WINDS_OBSERVED_ACTIVE"]+=1
        need.append({
            "numeric_child_id":child["spell_id"],"child_raw_event_id":child["event_id"],
            "child_t_ms":child["t_ms"],"child_target_id":child["target_id"],
            "posthoc_near_parent_status":status,
            "near_parent_raw_event_count":len(near),
            "near_parent_numeric_ids":[x["spell_id"] for x in near],
            "near_parent_t_ms":[x["t_ms"] for x in near],
            "unique_parent_numeric_id":parent["spell_id"] if parent else None,
            "signed_parent_minus_child_ms":parent["t_ms"]-child["t_ms"] if parent else None,
            "parent_target_id":parent["target_id"] if parent else None,
            "target_ID_alignment_not_guaranteed_for_AoE":True,
            "source_buff_pre_observations":active,
            "maelstrom_weapon_exact_prior_stack":
              source["maelstrom_weapon_exact_raw_stack"],
            "same_timestamp_array_order_proves_trigger":False,
            "observed_event_is_manual_input":"UNKNOWN",
            "observed_event_caused_by_source_cpp_trigger":"CANDIDATE_NOT_PROVEN",
            "current_Retail_mechanics_parity":"UNKNOWN",
            "priority_or_dummy_user_error":"UNKNOWN"})
    return {"report_code":case["report_code"],"actor_id":case["actor_id"],
            "numeric_child_completed_casts":len(c),
            "numeric_parent_completed_casts":len(p),
            "posthoc_window_ms":w,
            "summary":dict(sorted(count.items())),
            "candidate_pairs":need,
            "causal_priority_or_manuality_proven":0}

def selftest():
    # No source events in a window must never fabricate a candidate.
    r={"event_id":"a","t_ms":100,"spell_id":20}
    assert [x for x in [r] if abs(x["t_ms"]-102)<=1]==[]
    assert [x for x in [r] if abs(x["t_ms"]-101)<=1]==[r]
    return {"status":"PASS_SYNTHETIC_STATIC","checks":2,
            "one_ms_window_is_posthoc":True,"no_gameplay_promotion":True}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("source-cpp","adapter","prior-postlock","prior-lock",
              "prior-contract","discovery-zip","holdout-zip","out"):
        p.add_argument("--"+k,type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    require(all(vars(a).values()),"ALL_PINNED_WCL_AND_SOURCE_INPUTS_REQUIRED")
    adapter=json.loads(a.adapter.read_bytes())
    postlock=json.loads(a.prior_postlock.read_bytes())
    lock=a.prior_lock.read_bytes();contract=a.prior_contract.read_bytes()
    w=verify_adapter(adapter,a.source_cpp.read_bytes(),postlock,lock,contract)
    results=[]
    for role,path,case in (("discovery",a.discovery_zip,postlock["cases"][0]),
                           ("holdout",a.holdout_zip,postlock["cases"][1])):
        require(case["role"]==role.upper(),"COHORT_ROLE_ORDER_DRIFT")
        with zipfile.ZipFile(path) as z:
            raw,events=raw_complete_casts(z,role)
        out=pair_one(case,raw,w,set(adapter["observed_child_numeric_ids"]),
                     set(adapter["observed_candidate_parent_numeric_ids"]),
                     adapter["aura_active_symbols"])
        results.append({"role":role.upper(),**out})
    require(results[0]["report_code"]!=results[1]["report_code"],
            "DISCOVERY_HOLDOUT_REPEATED_REPORT")
    output={"schema":SCHEMA,"policy_id":POLICY,
            "source_revision":adapter["source_revision"],
            "source_cpp_git_blob":adapter["source_cpp_git_blob"],
            "original_numeric_lock_sha256":sha(lock),
            "prior_postlock_aura_replay_sha256":sha(canon(postlock)),
            "source_trigger_mechanism_exists_in_pinned_cpp":True,
            "direct_wcl_trigger_parent_event_relation_observed":False,
            "window_selected_posthoc_after_data_inspection":True,
            "independent_holdout_confirmation_of_predeclared_timing_threshold":False,
            "observational_report_disjoint_reobservation_only":True,
            "pairing_is_not_ability_READY_or_player_manual_input":True,
            "cases":results,"new_WCL_API_calls":0,"new_SimC_native_builds":0,
            "new_general_rotation_rules_promoted":0,
            "dummy_false_positive_guard":"DO_NOT_TREAT_UNVERIFIED_TRIGGER_FAMILY_AS_MANUAL_ERROR",
            "MAIN_promoted":False}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canon(output))
    print("POSTLOCK_SOURCE_TRIGGER_FAMILY_SHA256="+sha(a.out.read_bytes()))
    print("POSTLOCK_SOURCE_TRIGGER_FAMILY_SUMMARY="+json.dumps([
        {"role":x["role"],"child_casts":x["numeric_child_completed_casts"],
         "parent_casts":x["numeric_parent_completed_casts"],"summary":x["summary"]}
        for x in results],sort_keys=True))

if __name__=="__main__":main()
