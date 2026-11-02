#!/usr/bin/env python3
"""One bounded WCL high-ranker discovery -> actor identity -> snapshot -> PRE.

Only official public v2 API through authorized user client credentials.
No SimC inputs. Raw logs remain on the CI runner, not copied to GitHub source.
One ranker, one report/fight, max eight event pages. All WCL raw action
readiness and full talent/build state remain UNKNOWN unless later evidenced.
Default with no arguments is a complete synthetic offline regression.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib,json,os
from pathlib import Path
import sys,tempfile
from typing import Callable

from fresh_wcl_engine_v1 import collect,replay,canonical,sha,EngineError
from wcl_ranker_discovery_preflight_v1 import (
  credentials,post,graphql,select_encounter,ZONE_QUERY,RANK_QUERY,TOKEN,
  ACTOR_QUERY,PreflightError,
)
from wcl_ranked_actor_resolution_v1 import ranked_actor,ActorResolutionError
from wcl_blind_numeric_candidate_lock_v1 import lock_candidates,BlindInputError

SCHEMA="ZrotRankerOneFightFreshWCLPilotV1"
SCOPE="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

def _select_actor(query:Callable,zone_pattern:str):
    world=query(ZONE_QUERY,{}).get("worldData")
    selected=select_encounter(world,zone_pattern)
    if selected["status"]!="ZONE_AND_ENCOUNTER_SELECTED_FOR_RANKER_DISCOVERY":
        return None,"BLOCKED_ZONE_NOT_FOUND"
    encounter=query(RANK_QUERY,{"id":selected["encounter_id"]}).get("worldData",{}).get("encounter")
    if not isinstance(encounter,dict):
        return None,"BLOCKED_ENCOUNTER_RANKING_MISSING"
    ranks=encounter.get("characterRankings")
    rows=ranks.get("rankings") if isinstance(ranks,dict) else None
    if not isinstance(rows,list):
        return None,"BLOCKED_RANKING_ROWS_SCHEMA_UNKNOWN"
    # At most five report identity queries; do not use player names as output.
    for rank_index,row in enumerate(rows[:5],1):
        if not isinstance(row,dict) or not isinstance(row.get("report"),dict):
            continue
        r=row["report"];code=r.get("code");fight=r.get("fightID")
        if not isinstance(code,str) or type(fight) is not int:
            continue
        report_data=query(ACTOR_QUERY,{"code":code,"fight":fight}).get("reportData")
        report=report_data.get("report") if isinstance(report_data,dict) else None
        if not isinstance(report,dict):continue
        fights=report.get("fights")
        if not isinstance(fights,list) or len(fights)!=1:continue
        f=fights[0]
        if (not isinstance(f,dict) or f.get("id")!=fight or
            f.get("difficulty")!=4 or f.get("inProgress") is True):continue
        actors=report.get("masterData")
        if not isinstance(actors,dict):continue
        try:
            identity=ranked_actor(ranking_row=row,
                master_actors=actors.get("actors"),
                report_code=code,fight_id=fight)
        except ActorResolutionError:
            continue
        return {"report_code":code,"fight_id":fight,
                "actor_id":identity["actor_numeric_id"],
                "report_revision":report.get("revision"),
                "ranking_page_rank":rank_index,
                "zone_id":selected["zone_id"],
                "encounter_id":selected["encounter_id"],
                "class":"Warrior","spec_from_ranking_filter":"Fury",
                "individual_actual_spec":"UNKNOWN",
                "build_talents":"UNKNOWN"},"RANKER_REPORT_FIGHT_ACTOR_MATCHED"
    return None,"BLOCKED_TOP_FIVE_NO_UNIQUE_RANKER_ACTOR"

def _actor_scoped_pre(raw:dict,actor_id:int)->dict:
    if type(actor_id) is not int or actor_id<=0:raise ValueError("INVALID_ACTOR_ID")
    assert raw["schema"]=="FreshWCLReplayV1"
    derived={k:v for k,v in raw.items() if k!="replay_sha256"}
    derived["decisions"]=[
        d for d in raw["decisions"]
        if d.get("source_actor_id")==actor_id
    ]
    derived["decision_count"]=len(derived["decisions"])
    # The original full-fight replay fingerprint is retained separately;
    # numeric actor-scoped replay is SHA-pinned and can be independently
    # recomputed from raw pages inside this runner.
    derived["full_fight_parent_replay_sha256"]=raw["replay_sha256"]
    derived["numeric_actor_filter_id"]=actor_id
    derived["replay_sha256"]=sha(canonical(derived))
    return derived

def run(query:Callable,*,zone_pattern:str,out_dir:Path,max_pages:int=6)->dict:
    if not 1<=max_pages<=8:raise ValueError("PILOT_MAX_PAGES_1_TO_8")
    receipt={
      "schema":SCHEMA,"scope_policy_id":SCOPE,
      "status":"BLOCKED_UNRESOLVED","WCL_authenticated":True,
      "WCL_high_ranker_live_selected":False,
      "WCL_blind_candidate_lock":"NOT_CREATED",
      "WCL_independent_holdout":"NOT_RUN",
      "SimC_semantic_source_used":False,
      "addon_or_gameplay_rules_validated":False,
      "raw_ranker_name_persisted":False,
      "WCL_readiness":"UNKNOWN",
      "full_build_talents_verified":False,
    }
    try:
        selection,status=_select_actor(query,zone_pattern)
        if selection is None:
            receipt["status"]=status
            return receipt
        receipt["ranker_numeric_identity"] = selection
        receipt["WCL_high_ranker_live_selected"]=True
        def transport(q,v):
            return query(q,v)
        # This is one explicit public fight; snapshots are revision/checkpoint
        # protected by the existing FreshWCL engine.
        collected=collect(transport,selection["report_code"],
            selection["fight_id"],out_dir,max_pages=max_pages)
        receipt["fresh_snapshot_status"]=collected["status"]
        receipt["fresh_pages_written"]=collected["pages"]
        receipt["fresh_event_count"]=collected["events"]
        receipt["snapshot_report_revision"]=collected["identity"]["revision"]
        if receipt["snapshot_report_revision"]!=selection["report_revision"]:
            receipt["status"]="BLOCKED_RANKED_REPORT_REVISION_CHANGED"
            return receipt
        if collected["status"]!="COMPLETE":
            receipt["status"]="PARTIAL_SNAPSHOT_NO_REPLAY_NO_LOCK"
            return receipt
        folder=out_dir/selection["report_code"]/f"fight_{selection['fight_id']}"
        replayed=replay(folder)
        actor_pre=_actor_scoped_pre(replayed,selection["actor_id"])
        receipt["raw_full_replay_sha256"]=replayed["replay_sha256"]
        receipt["actor_scoped_pre_sha256"]=actor_pre["replay_sha256"]
        receipt["actor_cast_count"]=actor_pre["decision_count"]
        receipt["actor_numeric_ability_counts"]=[
          {"ability_id":aid,"observed_cast_count":n}
          for aid,n in sorted(Counter(
            d["ability_id"] for d in actor_pre["decisions"]
            if type(d["ability_id"]) is int and d["ability_id"]>0
          ).items())
        ]
        if not actor_pre["decisions"]:
            receipt["status"]="BLOCKED_NO_ACTOR_CASTS_IN_RAW_REPLAY"
            return receipt
        try:
            lock=lock_candidates([actor_pre],min_observations=2,
                                 source_kind="ATTESTED_RAW_WCL_REPLAY")
        except BlindInputError as exc:
            receipt["status"]="BLOCKED_BLIND_NUMERIC_LOCK_"+str(exc)
            return receipt
        lock_raw=canonical(lock)
        lock_sha=sha(lock_raw)
        (out_dir/"numeric_blind_candidate_lock.json").write_bytes(lock_raw)
        receipt["WCL_blind_candidate_lock"]="LOCKED_NUMERIC_ONLY_RAW_AUDIT_REQUIRED"
        receipt["numeric_blind_candidate_lock_sha256"]=lock_sha
        receipt["numeric_candidate_count"]=lock["candidate_n"]
        receipt["status"]="ACTUAL_FRESH_RANKER_WCL_PRE_AND_NUMERIC_LOCK_RESEARCH_ONLY"
        # Important: no player-facing recommendation or optimality claim.
    except (PreflightError,ActorResolutionError,EngineError,ValueError) as exc:
        receipt["status"]="BLOCKED_"+str(exc)
    return receipt

def self_test():
    actor=15;fight=9;code="ABCDEF123456"
    call=[]
    events=[
      {"timestamp":1020,"type":"applybuff","targetID":actor,"abilityGameID":444,"stack":1},
      {"timestamp":1030,"type":"cast","sourceID":actor,"abilityGameID":100},
      {"timestamp":1040,"type":"cast","sourceID":actor,"abilityGameID":100},
      {"timestamp":1040,"type":"removebuff","targetID":actor,"abilityGameID":444},
      {"timestamp":1050,"type":"cast","sourceID":actor,"abilityGameID":200},
      {"timestamp":1060,"type":"cast","sourceID":actor,"abilityGameID":100},
      {"timestamp":1070,"type":"cast","sourceID":21,"abilityGameID":999},
    ]
    base={"code":code,"revision":2,
          "fights":[{"id":fight,"startTime":1000,"endTime":2000,
                     "encounterID":5001,"difficulty":4,"inProgress":False}]}
    def query(q,v):
        call.append((q,v))
        if "zones" in q:
            return {"worldData":{"zones":[{"id":4000,"name":"The Voidspire",
              "frozen":False,"encounters":[{"id":5001,"name":"Fake"}]}]}}
        if "characterRankings" in q:
            return {"worldData":{"encounter":{"id":5001,"name":"Fake",
              "characterRankings":{"rankings":[
                {"report":{"code":code,"fightID":fight},"name":"Example"}
              ]}}}}
        if "masterData" in q:
            return {"reportData":{"report":{
                **base,"masterData":{"actors":[
                   {"id":actor,"name":"Example","type":"Player","subType":"Warrior"}
                ]}}}}
        if "FreshReport" in q:
            return {"reportData":{"report":base}}
        if "FreshEvents" in q:
            return {"reportData":{"report":{"events":{
              "data":events,"nextPageTimestamp":None}}}}
        raise AssertionError("UNKNOWN_WCL_QUERY")
    with tempfile.TemporaryDirectory(prefix="zrot_ranked_e2e_") as temp:
        r=run(query,zone_pattern="Voidspire",out_dir=Path(temp),max_pages=2)
        assert r["status"]=="ACTUAL_FRESH_RANKER_WCL_PRE_AND_NUMERIC_LOCK_RESEARCH_ONLY"
        assert r["ranker_numeric_identity"]["actor_id"]==actor
        assert r["fresh_snapshot_status"]=="COMPLETE"
        assert r["fresh_event_count"]==len(events)
        assert r["actor_cast_count"]==4
        assert r["numeric_candidate_count"]==1
        assert r["WCL_blind_candidate_lock"]=="LOCKED_NUMERIC_ONLY_RAW_AUDIT_REQUIRED"
        assert all(x["ability_id"]!=999 for x in r["actor_numeric_ability_counts"])
        assert r["addon_or_gameplay_rules_validated"] is False
        assert r["raw_ranker_name_persisted"] is False
        assert "Example" not in json.dumps(r)
        assert "simc" not in json.dumps(r).lower() or "semantics" not in json.dumps(r).lower()
        lock=json.loads((Path(temp)/"numeric_blind_candidate_lock.json").read_text())
        assert lock["status"]=="LOCKED_NUMERIC_ONLY"
        assert lock["candidates"][0]["action_spell_id"]==100
        assert len(call)<=6
        count=13
        altered=lambda q,v:query(q,v)
        # ranker metadata with nonunique actor identity must block collecting.
        def ambiguous(q,v):
            if "masterData" in q:
                j=query(q,v)
                j["reportData"]["report"]["masterData"]["actors"].append(
                    {"id":16,"name":"Example","type":"Player","subType":"Warrior"})
                return j
            return query(q,v)
        with tempfile.TemporaryDirectory(prefix="zrot_ranked_ambiguous_") as second:
            b=run(ambiguous,zone_pattern="Voidspire",out_dir=Path(second),max_pages=2)
            assert b["status"]=="BLOCKED_TOP_FIVE_NO_UNIQUE_RANKER_ACTOR"
            assert b["WCL_high_ranker_live_selected"] is False
            count+=2
        try:run(query,zone_pattern="Voidspire",out_dir=Path(temp),max_pages=0)
        except ValueError as exc:assert "PILOT_MAX_PAGES" in str(exc);count+=1
        else:raise AssertionError("OUT_OF_BOUNDS_PAGES_ACCEPTED")
    return {"result":"PASS","offline_case_count":count,
            "live_WCL_API_invocations":0,"actual_WCL_ranker_logs":"NOT_COLLECTED",
            "independent_WCL_cohort_holdout":"NOT_RUN",
            "simc_semantic_imports":0,
            "offline_source":"SYNTHETIC_WCL_RESPONSE_INJECTION"}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--live",action="store_true")
    ap.add_argument("--zone-match",default="Voidspire")
    ap.add_argument("--max-pages",type=int,default=6)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    if not a.live:
        result=self_test()
    elif credentials() is None:
        result={
         "schema":SCHEMA,"scope_policy_id":SCOPE,
         "status":"BLOCKED_MISSING_WCL_CLIENT_CREDENTIALS_IN_ACTIONS",
         "WCL_authenticated":False,"WCL_API_requests":0,
         "needed_repository_or_environment_secrets":["WCL_CLIENT_ID","WCL_CLIENT_SECRET"],
         "WCL_blind_candidate_lock":"NOT_CREATED",
         "SimC_semantic_source_used":False,
         "addon_or_gameplay_rules_validated":False
        }
    else:
        key,secret=credentials()
        try:
            bearer=post(TOKEN,{"client_id":key,"client_secret":secret,
                "grant_type":"client_credentials"}).get("access_token")
            if not isinstance(bearer,str) or len(bearer)<12:
                raise PreflightError("NO_ACCESS_TOKEN")
            with tempfile.TemporaryDirectory(prefix="zrot_live_wcl_ranked_") as private:
                result=run(lambda q,v:graphql(bearer,q,v),
                           zone_pattern=a.zone_match,
                           out_dir=Path(private),max_pages=a.max_pages)
        except PreflightError as exc:
            result={"schema":SCHEMA,"scope_policy_id":SCOPE,
                    "status":"BLOCKED_"+str(exc),
                    "WCL_authenticated":False,
                    "WCL_blind_candidate_lock":"NOT_CREATED",
                    "addon_or_gameplay_rules_validated":False}
    output=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(output,encoding="utf-8")
        print("WCL_FRESH_RANKED_PILOT_STATUS="+result["status"])
    else:
        print(output,end="")

if __name__=="__main__":main()
