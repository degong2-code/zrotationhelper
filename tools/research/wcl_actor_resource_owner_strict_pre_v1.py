#!/usr/bin/env python3
"""WCL actor-owned classResources Strict PRE — source/target provenance gate.

WCL raw events attach a resource snapshot to either source or target. For
this recorded API shape resourceActor=1 selects sourceID, =2 selects targetID.
A player's outgoing damage event generally contains the enemy's resources;
"sourceID == player" alone is NOT an ownership test.

Replay rule: for a cast at t, only a validated resource snapshot from a
strictly earlier timestamp (<t) can be used. Retain raw power type/amount/max
without inferring spell cost, rage scaling, GCD or competing-spell readiness.
Offline defaults to synthetic regression; no network, no secrets.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import groupby
import json
from pathlib import Path

from wcl_dual_cohort_state_observability_v1 import read_cohort
from wcl_simc_postlock_real_audit_v1 import _zip, _canonical as canonical, _sha as sha

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

class ResourceOwnerError(ValueError):pass


def resource_owner(event:dict, actor_id:int)->str:
    ra=event.get("resourceActor")
    if type(ra) is not int: return "UNDETERMINED"
    if ra==1:
        return ("ACTOR_OWNED_SOURCE" if event.get("sourceID")==actor_id
                else "DIFFERENT_SOURCE")
    if ra==2:
        return ("ACTOR_OWNED_TARGET" if event.get("targetID")==actor_id
                else "DIFFERENT_TARGET")
    return "UNDETERMINED"


def parse_resources(event:dict)->dict[int,dict]:
    entries=event.get("classResources")
    if entries is None:return {}
    if not isinstance(entries,list):raise ResourceOwnerError("RESOURCE_FIELDS_NOT_LIST")
    output={}
    for r in entries:
        if not isinstance(r,dict):raise ResourceOwnerError("RESOURCE_ENTRY_NOT_OBJECT")
        typ=r.get("type");amount=r.get("amount");maximum=r.get("max")
        if (type(typ) is not int or typ<0 or type(amount) not in (int,float)
                or type(maximum) not in (int,float)
                or not 0<=amount<=maximum or maximum<=0):
            raise ResourceOwnerError("INVALID_RAW_RESOURCE_VALUE")
        data={"raw_amount":amount,"raw_max":maximum}
        if typ in output and output[typ]!=data:
            raise ResourceOwnerError("CONFLICTING_RESOURCE_TYPE_IN_ONE_EVENT")
        output[typ]=data
    return output


def reconstruct(events:list[dict],actor_id:int, expected_casts:list[dict])->dict:
    if type(actor_id) is not int or actor_id<=0:raise ResourceOwnerError("INVALID_ACTOR")
    # Sorting uses original index for stable event-order diagnostics but
    # never regards same-timestamp source order as strict predecessor.
    ordered=sorted(enumerate(events),key=lambda row:(row[1]["timestamp"],row[0]))
    state={}
    cast_records=[]
    rejected=Counter()
    sources=Counter()
    accepted_events=0
    cast_events_with_own_at_t=0
    own_types=Counter()
    for ts,it in groupby(ordered,key=lambda row:row[1]["timestamp"]):
        batch=[v for _,v in it]
        for e in batch:
            if e.get("sourceID")!=actor_id or e.get("type") not in ("cast","begincast"):
                continue
            owned_at_t=resource_owner(e,actor_id) in ("ACTOR_OWNED_SOURCE","ACTOR_OWNED_TARGET")
            if owned_at_t and parse_resources(e):
                cast_events_with_own_at_t+=1
            pre={str(k):{
                "raw_amount":v["raw_amount"],"raw_max":v["raw_max"],
                "source_timestamp":v["timestamp"],
                "source_event_type":v["event_type"],
                "owner_proof":v["owner_proof"],
                "snapshot_age_ms":ts-v["timestamp"]}
                for k,v in sorted(state.items())}
            if any(v["snapshot_age_ms"]<=0 for v in pre.values()):
                raise ResourceOwnerError("SAME_TIMESTAMP_RESOURCE_LEAK")
            cast_records.append({"timestamp":ts,"ability_id":e.get("abilityGameID"),
                 "resource_pre":pre,
                 "readiness":"UNKNOWN","cost":"UNKNOWN",
                 "active_target_count":"UNKNOWN"})
        # Only after all same-time actions are recorded may their event
        # resource snapshots enter the state for future timestamps.
        for e in batch:
            if "classResources" not in e or not e["classResources"]:continue
            owner=resource_owner(e,actor_id)
            if owner not in ("ACTOR_OWNED_SOURCE","ACTOR_OWNED_TARGET"):
                if e.get("sourceID")==actor_id or e.get("targetID")==actor_id:
                    rejected[owner]+=1
                continue
            values=parse_resources(e)
            if not values:continue
            accepted_events+=1
            sources[owner]+=1
            for kind,value in values.items():
                own_types[kind]+=1
                state[kind]={**value,"timestamp":ts,
                             "event_type":e.get("type"),"owner_proof":owner}
    if len(cast_records)!=len(expected_casts):
        raise ResourceOwnerError("STRICT_PRE_CAST_COUNT_MISMATCH")
    for a,b in zip(cast_records,expected_casts):
        if a["timestamp"]!=b["timestamp"] or a["ability_id"]!=b["ability_id"]:
            raise ResourceOwnerError("STRICT_PRE_CAST_IDENTITY_MISMATCH")

    coverage=Counter(str(k) for r in cast_records for k in r["resource_pre"])
    ages=[x["snapshot_age_ms"] for rec in cast_records for x in rec["resource_pre"].values()]
    all_damage_target_ids=sorted({
        e.get("targetID") for e in events
        if e.get("sourceID")==actor_id and e.get("type")=="damage"
        and type(e.get("targetID")) is int and e["targetID"]>0
    })
    return {
        "actor_cast_count":len(cast_records),
        "actor_owned_resource_snapshot_events":accepted_events,
        "owner_proof_event_counts":dict(sorted(sources.items())),
        "wrong_or_unproven_owner_events_rejected":dict(sorted(rejected.items())),
        "actor_owned_raw_resource_type_sample_counts":{
            str(k):v for k,v in sorted(own_types.items())},
        "strict_pre_cast_coverage_by_raw_power_type":{
            k:{"casts_with_prior_owned_snapshot":v,
               "casts_without_prior_owned_snapshot":len(cast_records)-v}
            for k,v in sorted(coverage.items())},
        "casts_with_any_owned_strict_pre_snapshot":sum(bool(r["resource_pre"]) for r in cast_records),
        "casts_with_same_timestamp_owned_snapshot_not_used":cast_events_with_own_at_t,
        "strict_pre_snapshot_age_ms_min":min(ages) if ages else None,
        "strict_pre_snapshot_age_ms_max":max(ages) if ages else None,
        "resource_state_at_first_cast":cast_records[0]["resource_pre"] if cast_records else {},
        "distinct_damage_target_ids_observed":len(all_damage_target_ids),
        "active_enemies_at_each_cast":"UNKNOWN",
        "resource_types_gameplay_semantics":"UNVERIFIED",
        "resource_amount_gameplay_scale":"UNVERIFIED",
        "unobserved_resource_transitions_possible":True,
        "resource_cost_cooldown_charge_or_gcd_readiness":"UNKNOWN",
        "candidate_pre_snapshots":cast_records,
    }


def study(discovery_zip:Path,holdout_zip:Path):
    result={}
    for kind,path in (("discovery",discovery_zip),("holdout",holdout_zip)):
        gate,view,events,pages=read_cohort(_zip(path),role=kind)
        data=reconstruct(events,gate["actor_id"],view["decisions"])
        data["report_code"]=gate["report_code"]
        data["fight_id"]=gate["fight_id"]
        data["raw_event_count"]=len(events)
        data["verified_source_pages"]=pages
        data["prior_legacy_resource_observability_status"]="SUPERSEDED_UNGATED_RESOURCE_OWNER"
        result[kind]=data
    if result["discovery"]["report_code"]==result["holdout"]["report_code"]:
        raise ResourceOwnerError("DISCOVERY_HOLDOUT_REPORT_COLLISION")
    return {"schema":"ZrotActorOwnedWclResourceStrictPreCorrectionV1",
        "scope_policy_id":POLICY,
        "status":"ACTOR_OWNED_STRICT_PRE_SNAPSHOT_OBSERVATIONS_ONLY",
        "resource_owner_mapping":{
          "resourceActor_1":"sourceID",
          "resourceActor_2":"targetID",
          "unsupported_or_missing":"UNOBSERVABLE"},
        "time_policy":"latest actor-owned resource snapshot with timestamp < cast timestamp",
        "discovery":result["discovery"],"holdout":result["holdout"],
        "wrong_owner_resource_contamination_prevented":True,
        "actual_active_target_count":"UNKNOWN",
        "readiness_or_priority_verified":False,
        "dummy_error_verdict":"UNKNOWN",
        "MAIN_promotion":False}


def selftest():
    events=[
      {"timestamp":100,"type":"damage","sourceID":7,"targetID":8,
       "resourceActor":2,"classResources":[{"type":3,"amount":70,"max":100}]},
      {"timestamp":100,"type":"cast","sourceID":7,"targetID":8,"abilityGameID":100,
       "resourceActor":1,"classResources":[{"type":1,"amount":200,"max":1300}]},
      {"timestamp":105,"type":"damage","sourceID":8,"targetID":7,
       "resourceActor":2,"classResources":[{"type":1,"amount":210,"max":1300}]},
      {"timestamp":105,"type":"cast","sourceID":7,"targetID":8,"abilityGameID":101,
       "resourceActor":1,"classResources":[{"type":1,"amount":220,"max":1300}]},
      {"timestamp":110,"type":"cast","sourceID":7,"targetID":8,"abilityGameID":102,
       "resourceActor":1,"classResources":[{"type":1,"amount":240,"max":1300}]},
    ]
    expect=[{"timestamp":x,"ability_id":y} for x,y in ((100,100),(105,101),(110,102))]
    out=reconstruct(events,7,expect)
    assert out["actor_cast_count"]==3
    assert out["actor_owned_raw_resource_type_sample_counts"]=={"1":4}
    assert out["strict_pre_cast_coverage_by_raw_power_type"]["1"]["casts_with_prior_owned_snapshot"]==2
    assert out["wrong_or_unproven_owner_events_rejected"]=={"DIFFERENT_TARGET":1}
    assert out["resource_state_at_first_cast"]=={}
    assert out["candidate_pre_snapshots"][1]["resource_pre"]["1"]["raw_amount"]==200
    assert out["candidate_pre_snapshots"][2]["resource_pre"]["1"]["raw_amount"]==220
    assert "3" not in out["strict_pre_cast_coverage_by_raw_power_type"]
    assert out["resource_cost_cooldown_charge_or_gcd_readiness"]=="UNKNOWN"
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":9,
        "WCL_live_API_calls":0,"priority_claim":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--discovery-zip",type=Path)
    p.add_argument("--holdout-zip",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.discovery_zip is None and a.holdout_zip is None:result=selftest()
    elif a.discovery_zip and a.holdout_zip:result=study(a.discovery_zip,a.holdout_zip)
    else:p.error("both WCL zipped evidence inputs required")
    blob=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("ACTOR_RESOURCE_PROVENANCE_STRICT_PRE_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
