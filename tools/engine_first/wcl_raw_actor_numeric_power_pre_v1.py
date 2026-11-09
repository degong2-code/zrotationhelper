#!/usr/bin/env python3
"""Generic actor-owned *numeric* WCL resource strict-PRE transport.

Deliberately reuses the existing independent WCL resource_owner/reconstruct
engine, raw checkpoint SHA replay, and actor numeric transport. Numeric
classResources are never fed into the boolean-only StrictPreReplay. A WCL
resource power type and raw amount are observations, NOT named Rage/Mana
without a separate externally verified SpecAdapter + units contract.
No automatic WCL -> source APL readiness/optimality/trainer promotion.

No arguments: safe synthetic tests; production: offline prior raw actor root
and matching numeric transport JSON, no credentials.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path

from fresh_wcl_engine_v1 import (
    replay,checked_pages,_num,_ability,canonical,sha
)
from wcl_raw_actor_numeric_transport_v1 import (
    actor_snapshot,read_json,_check_transport,RAW_SOURCE,ORIGIN,POLICY
)
from wcl_actor_resource_owner_strict_pre_v1 import (
    reconstruct,resource_owner,parse_resources,ResourceOwnerError
)

SCHEMA="ZrotGenericWclActorOwnedNumericResourcePreV1"

class NumericPreError(ValueError):pass

def need(ok,tag):
    if not ok:raise NumericPreError(tag)

def power_cast_matrix(events:list,actor_id:int,fight_start_ms:int,
                      transported_casts:list[dict],
                      raw_numeric_receipt_sha256:str)->dict:
    """Actor-scoped raw numeric resource PRE; original clock, no future."""
    need(type(actor_id)==int and actor_id>0 and
         type(fight_start_ms)==int and fight_start_ms>=0 and
         type(transported_casts)==list and transported_casts and
         type(raw_numeric_receipt_sha256)==str and
         len(raw_numeric_receipt_sha256)==64,
         "RESOURCE_PRE_NUMERIC_ACTOR_OR_TIME_BASE_UNVERIFIED")
    need(type(events)==list and 0<len(events)<=100000,
         "BOUNDED_RAW_EVENTS_REQUIRED")
    raw_casts=[]
    for e in events:
        need(type(e)==dict and type(e.get("timestamp")) in (int,float) and
             math.isfinite(float(e["timestamp"])) and
             float(e["timestamp"]).is_integer(),
             "RESOURCE_RAW_EVENT_TIME_NOT_INTEGER")
        if (e.get("sourceID")==actor_id and
            str(e.get("type","")).casefold() in ("cast","begincast")):
            raw_casts.append({
               "timestamp":e["timestamp"],
               "ability_id":_ability(e)
            })
    needed=Counter((fight_start_ms+x["t_ms"],x["spell_id"])
                   for x in transported_casts)
    got=Counter((x["timestamp"],x["ability_id"]) for x in raw_casts)
    need(needed==got and len(raw_casts)==len(transported_casts),
         "RAW_RESOURCE_CASTS_NOT_IDENTICAL_TO_ACTOR_NUMERIC_TRANSPORT")
    # Existing research engine is independently tested and enforces
    # same-timestamp exclusion before applying resource transitions.
    source=reconstruct(events,actor_id,raw_casts)
    need(source["actor_cast_count"]==len(transported_casts) and
         source["unobserved_resource_transitions_possible"] is True and
         source["resource_cost_cooldown_charge_or_gcd_readiness"]=="UNKNOWN",
         "EXISTING_GENERIC_RESOURCE_STRICT_PRE_ENGINE_CHANGED")
    sorted_casts=defaultdict(list)
    for row in transported_casts:
        sorted_casts[(fight_start_ms+row["t_ms"],row["spell_id"])].append(row)
    out=[];statuses=Counter();known=Counter()
    for row in source["candidate_pre_snapshots"]:
        at=row["timestamp"];idnum=row["ability_id"]
        pool=sorted_casts[(at,idnum)]
        need(bool(pool),"RESOURCE_PRE_CAST_EVENT_ID_NOT_MATCHED")
        cast=pool.pop(0)
        typed={}
        for kind,prior in row["resource_pre"].items():
            timestamp=prior["source_timestamp"]
            age=prior["snapshot_age_ms"]
            amount=prior["raw_amount"];maximum=prior["raw_max"]
            need(type(timestamp) in (int,float) and timestamp<at and
                 type(age) in (int,float) and age>0 and
                 age==at-timestamp and
                 type(amount) in (int,float) and
                 type(maximum) in (int,float) and
                 math.isfinite(float(amount)) and
                 math.isfinite(float(maximum)) and
                 0<=amount<=maximum and maximum>0 and
                 prior["owner_proof"] in (
                      "ACTOR_OWNED_SOURCE","ACTOR_OWNED_TARGET"),
                 "RESOURCE_VALUE_OWNER_OR_STRICT_PRE_TIME_INVALID")
            t_ms=timestamp-fight_start_ms
            need(t_ms>=0 and t_ms<cast["t_ms"],
                 "RESOURCE_EVENT_OUTSIDE_FIGHT_OR_SAME_TIME_PRE")
            typed[kind]={
               "status":"OBSERVED_PRIOR_NUMERIC_RAW_ONLY",
               "raw_amount":amount,
               "raw_maximum":maximum,
               "raw_power_type":int(kind),
               "strict_prior_at_ms":int(t_ms),
               "observed_before_cast_ms":cast["t_ms"],
               "snapshot_age_ms":age,
               "owner_proof":prior["owner_proof"],
               "source_event_type":prior["source_event_type"],
               "source_checkpoint_raw_receipt_sha256":
                    raw_numeric_receipt_sha256,
               "game_resource_units_conversion":"UNKNOWN",
               "game_resource_kind_semantics":"UNKNOWN",
               "resource_spend_ability_cost":"UNKNOWN"
            }
            known[kind]+=1
        statuses["CAST_WITH_NUMERIC_PRIOR" if typed else
                 "CAST_RESOURCE_UNOBSERVED"]+=1
        out.append({
           "numeric_raw_cast_event_id":cast["event_id"],
           "t_ms":cast["t_ms"],
           "numeric_spell_id":cast["spell_id"],
           "numeric_resource_strict_pre":typed,
           "full_GCD_cooldown_charge_resource_READY":"UNKNOWN",
           "source_spell_or_priority_injected":False,
           "target_count_at_action":"UNKNOWN",
           "dummy_wrong_spell":"UNKNOWN",
        })
    need(all(not value for value in sorted_casts.values()) and
         len(out)==len(transported_casts),
         "NUMERIC_PRE_ALL_ACTOR_CASTS_NOT_ACCOUNTED")
    result={
        "schema":SCHEMA,"policy_id":POLICY,
        "status":"ACTOR_OWNED_RAW_RESOURCE_STRICT_PRE_OBSERVATION",
        "raw_actor_numeric_receipt_sha256":raw_numeric_receipt_sha256,
        "actor_casts":len(out),
        "actor_owned_source_resource_events":
          source["owner_proof_event_counts"].get("ACTOR_OWNED_SOURCE",0),
        "actor_owned_target_resource_events":
          source["owner_proof_event_counts"].get("ACTOR_OWNED_TARGET",0),
        "actor_owned_resource_snapshot_events":
          source["actor_owned_resource_snapshot_events"],
        "wrong_or_unproven_owner_events_rejected":
          source["wrong_or_unproven_owner_events_rejected"],
        "numeric_raw_power_type_prior_counts":dict(sorted(known.items())),
        "casts_with_any_owned_strict_PRE_resource":
          source["casts_with_any_owned_strict_pre_snapshot"],
        "casts_with_same_timestamp_owner_snapshot_excluded":
          source["casts_with_same_timestamp_owned_snapshot_not_used"],
        "per_cast_status":dict(sorted(statuses.items())),
        "per_numeric_cast":out,
        "raw_power_unit_to_game_resource_scale":"UNKNOWN",
        "observed_resource_snapshot_may_be_stale":True,
        "gcd_cooldown_charge_competing_action_READY":"UNKNOWN",
        "actual_SimC_source_IF_recomputed":False,
        "General_Rotation_rule_promoted":False,
        "dummy_wrong_cast_proven":0,
        "new_WCL_API_calls":0,
        "MAIN_promoted":False
    }
    result["resource_pre_matrix_sha256"]=sha(canonical(result))
    return result

def from_existing_actor_root(root:Path,transport:dict)->dict:
    """Re-open original raw pages; reject tampered actor/view/checkpoint."""
    _check_transport(transport)
    role=transport["source_cohort_role"]
    need(role in ("DISCOVERY","HOLDOUT"),"RAW_NUMERIC_SOURCE_ROLE_UNKNOWN")
    derived=root/"derived"
    if role=="DISCOVERY":
        paths=("selection.json","identity.json","blind_replay.json",
               "receipt.json")
    else:
        paths=("source_selection.json","identity_gate.json",
               "blind_holdout_replay.json","holdout_observed_metrics.json")
    selection,gate,view,receipt=[read_json(derived/f) for f in paths]
    need(selection["report_code"]==transport["report_code"] and
         selection["fight_id"]==transport["fight_id"] and
         gate["actor_id"]==transport["actor_id"],
         "NUMERIC_POWER_ACTOR_OR_FIGHT_SCOPE_MISMATCH")
    folder=root/"raw"/selection["report_code"]/(
        "fight_"+str(selection["fight_id"]))
    from wcl_raw_actor_numeric_transport_v1 import actor_snapshot
    restored=actor_snapshot(folder,gate,view,receipt,source_role=role)
    need(restored["numeric_transport_sha256"]==
         transport["numeric_transport_sha256"],
         "RAW_RESOURCE_SOURCE_NOT_MATCHING_EXISTING_ACTOR_SNAPSHOT")
    chk=read_json(folder/"checkpoint.json")
    pages=checked_pages(folder,chk)
    events=[]
    for page in pages:
        obj=read_json(folder/page["file"])
        need(sha(canonical(obj))==page["sha256"],
             "RESOURCE_EVENT_PAGE_CHECKSUM_DIFFERENT")
        events.extend(obj["events"])
    output=power_cast_matrix(
         events,gate["actor_id"],transport["fight_start_abs_ms"],
         transport["cast_events"],transport["raw_receipt_sha256"])
    output["raw_source_actor_numeric_transport_sha256"] = (
         transport["numeric_transport_sha256"])
    output["raw_source_page_sha256"]=transport["raw_source_page_sha256"]
    output["source_report_scope"]="PINNED_NUMERIC_WCL_ONLY"
    output["resource_pre_matrix_sha256"]=sha(canonical({
         k:v for k,v in output.items() if k!="resource_pre_matrix_sha256"}))
    return output

def selftest():
    actor=42;start=1000
    def res(t,owner,source,target,typ,amount,maxi):
        return {"timestamp":t,"type":"damage",
          "sourceID":source,"targetID":target,
          "resourceActor":owner,
          "classResources":[{"type":typ,"amount":amount,"max":maxi}]}
    def cast(t,spell):
        return {"timestamp":t,"sourceID":actor,"targetID":89,
                "type":"cast","abilityGameID":spell}
    rows=[
       res(1120,1,42,89,1,100,1000),
       res(1150,1,99,89,1,999,1000),  # wrong-owner excluded
       cast(1200,2001),
       res(1200,1,42,89,1,200,1000),  # same time, cannot leak
       res(1250,2,99,42,0,25,100),    # target ownership valid
       cast(1300,2002)
    ]
    casts=[
       {"event_id":"one","t_ms":200,"spell_id":2001,"source_kind":RAW_SOURCE},
       {"event_id":"two","t_ms":300,"spell_id":2002,"source_kind":RAW_SOURCE}
    ]
    a=power_cast_matrix(rows,actor,start,casts,"c"*64)
    r=a["per_numeric_cast"]
    need(a["actor_casts"]==2 and
         r[0]["numeric_resource_strict_pre"]["1"]["raw_amount"]==100 and
         r[1]["numeric_resource_strict_pre"]["1"]["raw_amount"]==200 and
         r[1]["numeric_resource_strict_pre"]["0"]["raw_amount"]==25 and
         a["actor_owned_resource_snapshot_events"]==3 and
         a["casts_with_same_timestamp_owner_snapshot_excluded"]==0,
         "STRICT_PRE_NUMERIC_RESOURCE_OWNERSHIP_OR_SOURCE_TIME_FAILED")
    # If resource recorded on the cast itself, reconstruct must mark that
    # source as same-time but not use it at the same cast.
    own=cast(1400,2003);own.update({
       "resourceActor":1,
       "classResources":[{"type":1,"amount":250,"max":1000}]
    })
    both=rows+[own]
    three=casts+[{"event_id":"three","t_ms":400,
                  "spell_id":2003,"source_kind":RAW_SOURCE}]
    b=power_cast_matrix(both,actor,start,three,"c"*64)
    need(b["casts_with_same_timestamp_owner_snapshot_excluded"]==1 and
         b["per_numeric_cast"][2]["numeric_resource_strict_pre"][
             "1"]["raw_amount"]==200,
         "CAST_TIMESTAMP_RESOURCE_WAS_USED_AS_PRE")
    n=0
    def fail(fn):
        nonlocal n
        try:fn()
        except (NumericPreError,ResourceOwnerError):n+=1
        else:raise AssertionError("INVALID_RESOURCE_PRE_ACCEPTED")
    fail(lambda:power_cast_matrix(rows,99,start,casts,"c"*64))
    bad=rows+[res(1100,1,42,89,1,float("inf"),float("inf"))]
    fail(lambda:power_cast_matrix(bad,actor,start,casts,"c"*64))
    fail(lambda:power_cast_matrix(rows,actor,start,casts[:-1],"c"*64))
    fail(lambda:power_cast_matrix(rows,actor,2000,casts,"c"*64))
    need(n==4,"EXPECTED_RESOURCE_PRE_NEGATIVE_CONTROLS")
    return {
       "schema":SCHEMA,"status":"PASS_SYNTHETIC_TWO_NUMERIC_POWER_TYPES",
       "reused_existing_actor_resource_owner_reconstruct":True,
       "strictly_earlier_numeric_source_snapshots":True,
       "same_time_cast_resource_rejected_as_PRE":True,
       "source_and_target_owner_paths_tested":True,
       "wrong_owner_event_excluded":True,
       "negative_controls":n,
       "real_WCL_new_collection":"NOT_RUN",
       "source_APL_IF_rule_proven":0,
       "full_READY_proven":0,
       "dummy_wrong_cast_proven":0
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--actor-root",type=Path)
    ap.add_argument("--numeric-transport",type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    if all(v is None for v in vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(v is not None for v in vars(a).values()),
         "ORIGINAL_RAW_ROOT_AND_PINNED_NUMERIC_TRANSPORT_REQUIRED")
    need(not a.out.exists(),"RESOURCE_MATRIX_OVERWRITE_FORBIDDEN")
    source=read_json(a.numeric_transport)
    result=from_existing_actor_root(a.actor_root,source)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_bytes(canonical(result))
    print("GENERIC_WCL_RAW_RESOURCE_STRICT_PRE_SHA256="+sha(a.out.read_bytes()))
    print("GENERIC_WCL_RAW_RESOURCE_PRE_COVERAGE="+json.dumps({
      "actor_casts":result["actor_casts"],
      "casts_with_owned_pre":result["casts_with_any_owned_strict_PRE_resource"],
      "raw_power_types":result["numeric_raw_power_type_prior_counts"],
      "excluded_same_cast_resource":
        result["casts_with_same_timestamp_owner_snapshot_excluded"]
    },sort_keys=True))
    print("GAME_RESOURCE_UNIT_OR_COOLDOWN_READINESS_PROVEN=False")

if __name__=="__main__":
    main()
