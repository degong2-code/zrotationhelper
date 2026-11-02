#!/usr/bin/env python3
"""Strict, bounded WCL v2 top-ranker discovery preflight (no event collection).

Designed for GitHub Actions: use OAuth secrets in memory only, never print them,
never persist bearer token or raw player names. Source is official WCL rankings
JSON; do not select a ranked character from guessed report/actor identity.
No-argument operation = offline self-test, --live required for WCL calls.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from wcl_ranked_actor_resolution_v1 import ranked_actor,ActorResolutionError

TOKEN="https://www.warcraftlogs.com/oauth/token"
API="https://www.warcraftlogs.com/api/v2/client"
SCHEMA="ZrotFreshWCLRankedFuryPreflightV1"
ZONE_QUERY="query { worldData { zones { id name frozen encounters { id name } } } }"
RANK_QUERY="""query($id:Int!){worldData{encounter(id:$id){
 id name characterRankings(className:"Warrior",specName:"Fury",difficulty:4,page:1)
}}}"""
ACTOR_QUERY="""query($code:String!,$fight:Int!){reportData{report(code:$code){
 code revision fights(fightIDs:[$fight],translate:false){id startTime endTime difficulty inProgress}
 masterData(translate:false){actors{id name type subType}}
}}}"""

class PreflightError(ValueError):
    pass

def require(cond,code):
    if not cond:raise PreflightError(code)

def credentials():
    key=os.environ.get("WCL_CLIENT_ID") or os.environ.get("WCL_ID")
    secret=os.environ.get("WCL_CLIENT_SECRET") or os.environ.get("WCL_SECRET")
    if not key or not secret:return None
    return key,secret

def post(endpoint,request_body,*,bearer=None):
    if endpoint not in (TOKEN,API):raise PreflightError("UNAPPROVED_NETWORK_ENDPOINT")
    data=(urlencode(request_body).encode() if endpoint==TOKEN
          else json.dumps(request_body,separators=(",",":")).encode())
    headers={"User-Agent":"zRotationHelper-GeneralRotation/1","Content-Type":(
       "application/x-www-form-urlencoded" if endpoint==TOKEN else "application/json")}
    if bearer is not None:
        headers["Authorization"]="Bearer "+bearer
    elif endpoint==TOKEN:
        require("client_id" in request_body and "client_secret" in request_body,
                "CLIENT_CREDENTIAL_REQUIRED")
    req=Request(endpoint,data=data,headers=headers,method="POST")
    try:
        with urlopen(req,timeout=25) as response:
            raw=response.read(8_000_001)
        if len(raw)>8_000_000:raise PreflightError("BOUND_RESPONSE_TOO_LARGE")
        result=json.loads(raw)
    except (URLError,HTTPError,ValueError,OSError):
        # No error body or request contents logged: credentials never escape.
        raise PreflightError("WCL_AUTH_OR_GRAPHQL_HTTP_FAILED") from None
    require(isinstance(result,dict),"WCL_JSON_OBJECT_REQUIRED")
    if result.get("errors"):raise PreflightError("WCL_GRAPHQL_RETURNED_ERRORS")
    return result

def graphql(bearer,q,variables=None):
    result=post(API,{"query":q,"variables":variables or {}},bearer=bearer)
    obj=result.get("data")
    require(isinstance(obj,dict),"WCL_GRAPHQL_DATA_MISSING")
    return obj

def select_encounter(zone_data,zone_match):
    require(isinstance(zone_data,dict),"WORLD_DATA_NOT_OBJECT")
    zones=zone_data.get("zones")
    require(isinstance(zones,list),"WORLD_ZONES_SCHEMA")
    matched=[]
    for z in zones:
        if (not isinstance(z,dict) or type(z.get("id")) is not int
            or not isinstance(z.get("name"),str)):continue
        if zone_match.casefold() not in z["name"].casefold():continue
        if z.get("frozen") is not False:continue
        encounters=z.get("encounters") or []
        for e in encounters:
            if (isinstance(e,dict) and type(e.get("id")) is int
                and isinstance(e.get("name"),str) and e["name"]):
                matched.append({"zone_id":z["id"],"zone_name":z["name"],
                                "encounter_id":e["id"],"encounter_name":e["name"]})
    if not matched:
        return {"status":"BLOCKED_NO_MATCHING_UNFROZEN_RAID_ZONE",
                "matching_zone_count":0,
                "zone_count_inspected":len(zones)}
    # deterministic metadata-only selection: never infer boss priority semantics.
    selected=min(matched,key=lambda x:(x["zone_id"],x["encounter_id"]))
    return {"status":"ZONE_AND_ENCOUNTER_SELECTED_FOR_RANKER_DISCOVERY",
            **selected,"matching_encounter_count":len(matched)}

def parse_rankers(result):
    require(isinstance(result,dict),"RANKING_OBJECT_REQUIRED")
    data=result.get("rankings")
    if not isinstance(data,list):
        return {"status":"BLOCKED_RANKING_JSON_SCHEMA_UNKNOWN",
                "top_level_keys":sorted(result.keys()),
                "rankings_collection_found":False}
    picked=[]
    for rank,item in enumerate(data[:50],1):
        if not isinstance(item,dict):continue
        report=item.get("report")
        if not isinstance(report,dict):continue
        code=report.get("code")
        fight=report.get("fightID")
        actor=(item.get("actorID") if type(item.get("actorID")) is int
               else item.get("actorId"))
        if type(actor) is not int:actor=report.get("actorID")
        if (isinstance(code,str) and re.fullmatch(r"[a-zA-Z0-9]{6,40}",code)
            and type(fight) is int and fight>=1):
            picked.append({"ranking_page_rank":rank,"report_code":code,
                           "fight_id":fight,
                           "actor_numeric_id":actor if type(actor) is int and actor>0 else None,
                           "ranker_identity_status":(
                             "NUMERIC_ACTOR_REPORTED_UNVERIFIED"
                             if type(actor) is int and actor>0
                             else "UNKNOWN_ACTOR_ID")})
    return {"status":("RANKED_REPORT_AND_FIGHT_IDENTIFIED" if picked
                      else "BLOCKED_RANKING_ROWS_LACK_REPORT_FIGHT"),
            "ranked_report_candidates":picked[:5],
            "ranking_page_length":len(data),
            "first_ranking_row_keys":sorted(data[0].keys()) if data and isinstance(data[0],dict) else [],
            "first_report_keys":sorted(data[0]["report"].keys()) if data and isinstance(data[0],dict) and isinstance(data[0].get("report"),dict) else [],
            "ranker_actor_id_fully_verified":False,
            "prelock_WCL_blind_candidate_created":False}

def live(zone_match="Voidspire"):
    result={"schema":SCHEMA,"scope_policy_id":
      "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
      "stage":"RANKER_SELECTION_ONLY","credentials_exposed":False,
      "wcl_api_invoked":False,"actual_events_collected":0,
      "WCL_ranker_exact_actor_verified":False,
      "WCL_blind_candidate_lock":"NOT_CREATED",
      "WCL_holdout":"NOT_RUN","SimC_semantic_leakage":False,
      "rotation_priority_proven":False}
    pair=credentials()
    if not pair:
        result["status"]="BLOCKED_MISSING_WCL_CLIENT_CREDENTIALS_IN_ACTIONS"
        result["needed_repository_or_environment_secrets"]=["WCL_CLIENT_ID","WCL_CLIENT_SECRET"]
        return result
    # OAuth tokens remain in memory and are never serialized into result.
    try:
        token=post(TOKEN,{"client_id":pair[0],"client_secret":pair[1],
                          "grant_type":"client_credentials"}).get("access_token")
        require(isinstance(token,str) and len(token)>10,"OAUTH_ACCESS_TOKEN_MISSING")
        result["wcl_api_invoked"]=True
        zones=graphql(token,ZONE_QUERY).get("worldData")
        z=select_encounter(zones,zone_match)
        result["selected_zone"]=z
        if z["status"]!="ZONE_AND_ENCOUNTER_SELECTED_FOR_RANKER_DISCOVERY":
            result["status"]=z["status"];return result
        encounter=graphql(token,RANK_QUERY,{"id":z["encounter_id"]}).get("worldData",{}).get("encounter")
        require(isinstance(encounter,dict),"RANKED_ENCOUNTER_SCHEMA_MISSING")
        ranking_obj=encounter.get("characterRankings")
        result["rankings"]=parse_rankers(ranking_obj)
        result["status"]=result["rankings"]["status"]
        # Exact ranker -> report -> fight -> actor mapping must be verified
        # BEFORE any raw fight event collection. Names remain only in memory.
        if result["status"]=="RANKED_REPORT_AND_FIGHT_IDENTIFIED":
            rows=ranking_obj.get("rankings",[])
            for item in rows[:5]:
                if not isinstance(item,dict) or not isinstance(item.get("report"),dict):
                    continue
                c=item["report"].get("code")
                fid=item["report"].get("fightID")
                if not isinstance(c,str) or not re.fullmatch(r"[A-Za-z0-9]{6,40}",c):
                    continue
                if type(fid) is not int or fid<=0:continue
                rd=graphql(token,ACTOR_QUERY,{"code":c,"fight":fid}).get("reportData")
                if not isinstance(rd,dict):continue
                report=rd.get("report")
                if not isinstance(report,dict):continue
                if report.get("code")!=c or type(report.get("revision")) is not int:continue
                fights=report.get("fights",[])
                if not isinstance(fights,list) or len(fights)!=1:continue
                fight=fights[0]
                if (fight.get("id")!=fid or fight.get("difficulty")!=4
                    or fight.get("inProgress") is True):continue
                md=report.get("masterData")
                if not isinstance(md,dict):continue
                try:
                    match=ranked_actor(ranking_row=item,
                        master_actors=md.get("actors"),
                        report_code=c,fight_id=fid)
                except ActorResolutionError:
                    continue
                result["ranker_actor_match"]=match
                result["ranked_report_revision"]=report["revision"]
                result["WCL_ranker_exact_actor_verified"]=True
                result["status"]="RANKED_REPORT_FIGHT_ACTOR_NUMERIC_ID_CONFIRMED"
                break
            if not result["WCL_ranker_exact_actor_verified"]:
                result["status"]="BLOCKED_RANKER_ACTOR_IDENTITY_NOT_UNIQUE_OR_UNOBSERVED"
    except PreflightError as ex:
        result["status"]="BLOCKED_"+str(ex)
    return result

def self_test():
    tests=0
    z={"zones":[{"id":4000,"name":"The Voidspire","frozen":False,
                 "encounters":[{"id":5001,"name":"Synthetic Alpha"}]}]}
    a=select_encounter(z,"Voidspire")
    assert a["encounter_id"]==5001;tests+=1
    rank={"rankings":[{"report":{"code":"ABCDEF123","fightID":7},"actorID":14}]}
    x=parse_rankers(rank)
    assert x["status"]=="RANKED_REPORT_AND_FIGHT_IDENTIFIED";tests+=1
    assert x["ranked_report_candidates"][0]["actor_numeric_id"]==14;tests+=1
    assert x["ranker_actor_id_fully_verified"] is False;tests+=1
    assert parse_rankers({"count":100})["status"]=="BLOCKED_RANKING_JSON_SCHEMA_UNKNOWN";tests+=1
    assert select_encounter({"zones":[{**z["zones"][0],"frozen":True}]},"Voidspire")["status"]=="BLOCKED_NO_MATCHING_UNFROZEN_RAID_ZONE";tests+=1
    assert parse_rankers({"rankings":[{"report":{"code":"abc","fightID":7}}]})["status"]=="BLOCKED_RANKING_ROWS_LACK_REPORT_FIGHT";tests+=1
    assert live.__defaults__==("Voidspire",);tests+=1
    return {"result":"PASS","offline_assertions":tests,
            "live_WCL_requests":0,"rankers_discovered":"SYNTHETIC_ONLY"}

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--self-test",action="store_true")
    a.add_argument("--live",action="store_true")
    a.add_argument("--zone-match",default="Voidspire")
    a.add_argument("--out",type=Path)
    x=a.parse_args()
    result=live(x.zone_match) if x.live else self_test()
    raw=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if x.out:
        x.out.parent.mkdir(parents=True,exist_ok=True)
        x.out.write_text(raw,encoding="utf-8")
        print("WCL_RANKER_PREFLIGHT_STATUS="+str(result["status"] if x.live else result["result"]))
    else:print(raw,end="")

if __name__=="__main__":main()
