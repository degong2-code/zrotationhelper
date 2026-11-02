#!/usr/bin/env python3
"""Post-lock numeric talent/build/resource PRE observability, no gameplay priority.

Consumes existing WCL raw artifacts from two report-disjoint cohorts; never
opens SimC or makes network requests. WCL combatantinfo talent IDs are a raw
build fingerprint, NOT a validated SimC talent equivalence.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import groupby
import json
from pathlib import Path
import sys
from typing import Any

from wcl_simc_postlock_real_audit_v1 import _zip,independently_replay_pre
from wcl_simc_postlock_real_audit_v1 import _canonical as canonical,_sha as sha

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

class PreEvidenceError(ValueError): pass


def read_cohort(archive:dict[str,bytes],*,role:str):
    if role not in ("discovery","holdout"):raise PreEvidenceError("INVALID_COHORT_ROLE")
    prefix="derived/"
    gate_path=prefix+("identity.json" if role=="discovery" else "identity_gate.json")
    replay_path=prefix+("blind_replay.json" if role=="discovery" else "blind_holdout_replay.json")
    if gate_path not in archive or replay_path not in archive:raise PreEvidenceError("COHORT_IDENTITY_MISSING")
    gate=json.loads(archive[gate_path])
    view=json.loads(archive[replay_path])
    identity=view.get("identity",{})
    if any(identity.get(k)!=gate.get(v) for k,v in (
      ("report_code","report_code"),("fight_id","fight_id"),
      ("revision","report_revision"),("actor_id","actor_id"))):
        raise PreEvidenceError("COHORT_IDENTITY_MISMATCH")
    if (view.get("blind_numeric_only") is not True or
        view.get("cooldown_or_resource_readiness")!="UNKNOWN" or
        identity.get("evidence_window")!="FIGHT_START_BOUNDED" or
        identity.get("requested_window_ms")!=15000):
        raise PreEvidenceError("COHORT_PRE_WINDOW_NOT_BOUNDED")
    fingerprint=view.get("replay_sha256")
    if fingerprint!=sha(canonical({k:v for k,v in view.items() if k!="replay_sha256"})):
        raise PreEvidenceError("ACTOR_REPLAY_SHA_CHANGED")
    base=f"raw/{gate['report_code']}/fight_{gate['fight_id']}/"
    cpath=base+"checkpoint.json"
    if cpath not in archive:raise PreEvidenceError("RAW_CHECKPOINT_MISSING")
    checkpoint=json.loads(archive[cpath])
    if (checkpoint.get("complete") is not True or
        checkpoint.get("identity")!={k:v for k,v in identity.items()
          if k not in ("source_replay_sha256","actor_id")}):
        raise PreEvidenceError("CHECKPOINT_IDENTITY_OR_COMPLETE_FLAG")
    events=[]
    pages=checkpoint.get("pages",[])
    if not isinstance(pages,list) or not 1<=len(pages)<=5:
        raise PreEvidenceError("BOUNDED_PAGE_SET_NOT_FOUND")
    for n,p in enumerate(pages):
        name=f"page_{n:05d}.json"
        b=archive.get(base+name)
        if (p.get("file")!=name or b is None or sha(b)!=p.get("sha256")):
            raise PreEvidenceError("SOURCE_PAGE_SHA_OR_ORDER_MISMATCH")
        page=json.loads(b)
        if (page.get("schema")!="FreshWCLPageV1" or
            page.get("start")!=p.get("start") or
            page.get("next")!=p.get("next") or
            len(page.get("events",[]))!=p.get("event_count")):
            raise PreEvidenceError("RAW_PAGE_LEDGER_INVALID")
        events+=page["events"]
    if (len(events)!=view.get("event_count") or
        any(type(e.get("timestamp")) not in (int,float) or
            not identity["start"]<=e["timestamp"]<=identity["end"]
            for e in events)):
        raise PreEvidenceError("RAW_EVENT_COUNT_OR_TIMESTAMP_INVALID")
    recomputed=independently_replay_pre(events,gate["actor_id"])
    if recomputed!=view.get("decisions"):
        raise PreEvidenceError("INDEPENDENT_CAST_PRE_MISMATCH")
    return gate,view,events,len(pages)


def _numeric_talent_tree(info:dict):
    raw=info.get("talentTree")
    if not isinstance(raw,list):return None
    out=[]
    for t in raw:
        if not isinstance(t,dict):return None
        row=[]
        for k in ("id","nodeID","rank"):
            n=t.get(k)
            if type(n) is not int or n<0:return None
            row.append(n)
        out.append(row)
    # Preserve duplicates and choice ranks; no node ID semantics injected.
    out.sort()
    return out


def _resources(event:dict)->dict[int,dict]:
    raw=event.get("classResources")
    if not isinstance(raw,list):return {}
    out={}
    for item in raw:
        if not isinstance(item,dict):continue
        kind=item.get("type");amount=item.get("amount");maximum=item.get("max")
        if any(type(n) not in (int,float) or n<0 for n in (kind,amount,maximum)):
            continue
        if int(kind)!=kind or maximum<=0:continue
        kind=int(kind)
        if kind in out and out[kind]!={"raw_amount":amount,"raw_max":maximum}:
            raise PreEvidenceError("CONFLICTING_SAME_EVENT_RESOURCE_SNAPSHOT")
        out[kind]={"raw_amount":amount,"raw_max":maximum}
    return out


def summarize_pre(gate:dict,view:dict,events:list[dict],role:str,pages:int)->dict:
    actor=gate["actor_id"]
    ordered=sorted(enumerate(events),key=lambda x:(x[1]["timestamp"],x[0]))
    resource_state:dict[int,dict]={}
    combatant=None
    records=[]
    numeric_damage_targets=set()
    for ts,rows in groupby(ordered,key=lambda x:x[1]["timestamp"]):
        batch=list(rows)
        # FIRST snapshot all casts at t, THEN apply state changes stamped t.
        for _,event in batch:
            if event.get("sourceID")==actor and event.get("type") in ("cast","begincast"):
                values={str(kind):dict(values) for kind,values in sorted(resource_state.items())}
                ci=combatant if combatant is not None else None
                records.append({"timestamp":ts,
                                "ability_id":event.get("abilityGameID"),
                                "resource_pre":values,
                                "resource_present":bool(values),
                                "combatant_info_pre":ci is not None,
                                "observed_spec_id":ci["spec_id"] if ci else None})
        for _,event in batch:
            if event.get("type")=="damage" and event.get("sourceID")==actor:
                target=event.get("targetID")
                if type(target) is int: numeric_damage_targets.add(target)
            if event.get("sourceID")!=actor:continue
            if event.get("type")=="combatantinfo":
                tree=_numeric_talent_tree(event)
                spec=event.get("specID")
                if type(spec) is int and spec>0 and tree is not None and tree:
                    combatant={"spec_id":spec,
                               "talent_tree_hash":sha(canonical(tree)),
                               "talent_entry_count":len(tree),
                               "timestamp":ts}
            for kind,detail in _resources(event).items():
                resource_state[kind]={**detail,"source_event_timestamp":ts,
                                     "source_event_type":event.get("type")}
    if len(records)!=len(view["decisions"]):raise PreEvidenceError("CAST_COUNT_MISMATCH")
    for observed,replayed in zip(records,view["decisions"]):
        if (observed["timestamp"]!=replayed["timestamp"] or
            observed["ability_id"]!=replayed["ability_id"]):
            raise PreEvidenceError("CAST_EVENT_IDENTITY_DIVERGENCE")
        if any(val["source_event_timestamp"]>=observed["timestamp"]
               for val in observed["resource_pre"].values()):
            raise PreEvidenceError("SAME_TIMESTAMP_RESOURCE_LEAKAGE")
    cast_with_ci=[r for r in records if r["combatant_info_pre"]]
    ci_hashes={r["observed_spec_id"] for r in cast_with_ci}
    talents=[event for event in events if event.get("type")=="combatantinfo" and
             event.get("sourceID")==actor and _numeric_talent_tree(event)]
    captured=[x for x in talents if type(x.get("specID")) is int and
              x["timestamp"]<records[-1]["timestamp"]]
    last_build=None
    if captured:
        t=max(captured,key=lambda e:e["timestamp"])
        tree=_numeric_talent_tree(t)
        last_build={"spec_id":t["specID"],"talent_tree_numeric_entries":len(tree),
                    "talent_tree_sha256":sha(canonical(tree)),
                    "source_timestamp":t["timestamp"],
                    "usable_as_precise_SimC_build":False}
    types=sorted({k for r in records for k in r["resource_pre"]})
    coverage={
      k:{"casts_with_prior_snapshot":sum(k in r["resource_pre"] for r in records),
         "observed_type_id_numeric_only":True}
      for k in types
    }
    return {"cohort_role":role,"report_code":gate["report_code"],
            "fight_id":gate["fight_id"],"actor_id":actor,
            "WCL_page_count":pages,"WCL_raw_event_count":len(events),
            "cast_count":len(records),"cast_with_pre_combatantinfo_count":len(cast_with_ci),
            "cast_with_any_prior_resource_snapshot_count":sum(r["resource_present"] for r in records),
            "numeric_resource_type_PRE_coverage":coverage,
            "observed_combatantinfo_build":last_build,
            "observed_damage_target_id_count":len(numeric_damage_targets),
            "actual_active_enemy_count":"UNKNOWN",
            "resource_amount_scale_and_gameplay_semantics":"UNVERIFIED",
            "readiness":"UNKNOWN","same_timestamp_state_used":False,
            "can_claim_skill_priority":False}


def compare_sources(discovery_zip:Path,holdout_zip:Path,source_contract:Path,fixture:Path):
    c=json.loads(source_contract.read_text())
    fix=json.loads(fixture.read_text())
    if (c.get("schema")!="ZrotPredeclaredDisjointWclHoldoutV1" or
        c.get("scope_policy_id")!=POLICY or
        fix.get("wcl_blind_lock_sha256")!=c["frozen_discovery"]["blind_lock_sha256"]):
        raise PreEvidenceError("SOURCE_CONTRACT_OR_LOCK_ID_CHANGED")
    d_files=_zip(discovery_zip); h_files=_zip(holdout_zip)
    l=d_files.get("derived/blind_lock.json")
    if l is None or sha(l)!=c["frozen_discovery"]["blind_lock_sha256"]:
        raise PreEvidenceError("DISCOVERY_LOCK_SHA_MISMATCH")
    d_gate,d_view,d_events,d_pages=read_cohort(d_files,role="discovery")
    h_gate,h_view,h_events,h_pages=read_cohort(h_files,role="holdout")
    if (d_gate["report_code"]!=c["frozen_discovery"]["report_code"] or
        d_gate["fight_id"]!=c["frozen_discovery"]["fight_id"] or
        d_gate["actor_id"]!=c["frozen_discovery"]["actor_id"] or
        h_gate["report_code"]==d_gate["report_code"]):
        raise PreEvidenceError("SOURCE_COHORT_DISJOINTNESS_INVALID")
    d=summarize_pre(d_gate,d_view,d_events,"discovery",d_pages)
    h=summarize_pre(h_gate,h_view,h_events,"holdout",h_pages)
    db=d["observed_combatantinfo_build"]
    hb=h["observed_combatantinfo_build"]
    return {"schema":"ZrotPostLockDualCohortStateObservabilityV1",
            "scope_policy_id":POLICY,
            "status":"OBSERVED_RAW_STATE_ONLY_NO_PRIORITY_CLAIM",
            "source_holdout_contract_sha256":sha(canonical(c)),
            "source_discovery_lock_sha256":sha(l),
            "discovery":d,"holdout":h,
            "two_wcl_talent_tree_fingerprints_equal": (
                db["talent_tree_sha256"]==hb["talent_tree_sha256"]
                if db is not None and hb is not None else None),
            "does_WCL_build_match_SimC":"UNKNOWN",
            "WCL_vs_SimC_priority_proven":False,
            "general_rotation_rules_ready":False,
            "MAIN_promotion":False}


def selftest():
    gate={"report_code":"ABCDEF123456","fight_id":3,"actor_id":7}
    view={"decisions":[{"timestamp":100,"ability_id":1},
                       {"timestamp":110,"ability_id":2},
                       {"timestamp":120,"ability_id":3}]}
    events=[
      {"timestamp":90,"type":"combatantinfo","sourceID":7,"specID":72,
       "talentTree":[{"id":11,"nodeID":12,"rank":2}]},
      {"timestamp":100,"type":"cast","sourceID":7,"abilityGameID":1,
       "classResources":[{"type":1,"amount":10,"max":100}]},
      {"timestamp":110,"type":"resourcechange","sourceID":7,
       "classResources":[{"type":1,"amount":20,"max":100}]},
      {"timestamp":110,"type":"cast","sourceID":7,"abilityGameID":2},
      {"timestamp":120,"type":"cast","sourceID":7,"abilityGameID":3},
      {"timestamp":120,"type":"combatantinfo","sourceID":7,"specID":73,
       "talentTree":[{"id":11,"nodeID":12,"rank":1}]}]
    x=summarize_pre(gate,view,events,"synthetic",1)
    assert x["cast_count"]==3
    assert x["cast_with_pre_combatantinfo_count"]==3
    assert x["cast_with_any_prior_resource_snapshot_count"]==2
    assert x["numeric_resource_type_PRE_coverage"]["1"]["casts_with_prior_snapshot"]==2
    assert x["observed_combatantinfo_build"]["spec_id"]==72
    assert x["actual_active_enemy_count"]=="UNKNOWN"
    assert x["readiness"]=="UNKNOWN"
    assert _numeric_talent_tree({"talentTree":[{"id":1,"nodeID":2,"rank":1},
       {"id":3,"nodeID":2,"rank":2}]})==[[1,2,1],[3,2,2]]
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":8,
            "actual_WCL_data_read":False,"SimC_semantic_dependency":False,
            "real_priority_inference":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--discovery-zip",type=Path)
    p.add_argument("--holdout-zip",type=Path)
    p.add_argument("--source-contract",type=Path)
    p.add_argument("--discovery-fixture",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    inputs=(a.discovery_zip,a.holdout_zip,a.source_contract,a.discovery_fixture)
    if all(x is None for x in inputs): result=selftest()
    elif all(x is not None for x in inputs):
        result=compare_sources(*inputs)
    else:p.error("supply all four source inputs together")
    blob=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("DUAL_COHORT_OBSERVABILITY_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
