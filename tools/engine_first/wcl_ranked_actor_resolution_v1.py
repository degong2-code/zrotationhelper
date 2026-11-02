#!/usr/bin/env python3
"""Match one officially ranked WCL report+fight+player to an actor numeric ID.

All character names are ephemeral inputs; outputs contain numeric actor ID,
rank, exact report/fight, and confidence boundaries only. No SimC imports.
WCL ranking spec filter is not independent combatant-spec proof.
"""
from __future__ import annotations
import argparse,json,re

SCHEMA="ZrotWCLRankedActorIdentityV1"

class ActorResolutionError(ValueError):pass

def require(ok,msg):
    if not ok:raise ActorResolutionError(msg)

def ranked_actor(*,ranking_row:dict,master_actors:list,
                 report_code:str,fight_id:int,
                 expected_class:str="Warrior",expected_spec:str="Fury"):
    require(isinstance(ranking_row,dict),"INVALID_RANKING_ROW")
    require(isinstance(report_code,str) and re.fullmatch("[A-Za-z0-9]{6,40}",report_code) is not None,
            "INVALID_REPORT_CODE")
    require(type(fight_id) is int and fight_id>0,"INVALID_FIGHT_ID")
    require(isinstance(master_actors,list) and master_actors,"MASTER_ACTORS_REQUIRED")
    report=ranking_row.get("report")
    require(isinstance(report,dict),"RANKED_REPORT_REQUIRED")
    require(report.get("code")==report_code,"RANKING_REPORT_MISMATCH")
    require(report.get("fightID")==fight_id,"RANKING_FIGHT_MISMATCH")
    require(expected_class=="Warrior" and expected_spec=="Fury",
            "EXACT_PILOT_SPEC_NOT_MATCHED")
    claimed_id=ranking_row.get("actorID")
    if claimed_id is None:claimed_id=ranking_row.get("actorId")
    if claimed_id is not None:
        require(type(claimed_id) is int and claimed_id>0,"RANKED_ACTOR_ID_NOT_NUMERIC")
    name=ranking_row.get("name")
    if name is not None:
        require(isinstance(name,str) and name.strip(),"RANKER_NAME_MALFORMED")
    require(name is not None or claimed_id is not None,
            "RANKER_NEITHER_NAME_NOR_ACTOR_ID")
    options=[]
    for actor in master_actors:
        if not isinstance(actor,dict):continue
        aid=actor.get("id")
        if type(aid) is not int or aid<=0:continue
        if str(actor.get("type","")).casefold()!="player":continue
        if str(actor.get("subType","")).casefold()!=expected_class.casefold():continue
        if claimed_id is not None and aid!=claimed_id:continue
        if name is not None:
            aname=actor.get("name")
            if not isinstance(aname,str) or aname.casefold()!=name.casefold():continue
        options.append(aid)
    require(len(options)==1,"RANKER_ACTOR_MATCH_NONUNIQUE_OR_MISSING")
    return {
      "schema":SCHEMA,"report_code":report_code,"fight_id":fight_id,
      "actor_numeric_id":options[0],
      "identity_crosscheck":"EXACT_REPORT_FIGHT_AND_SINGLE_PLAYER_CLASS_MATCH",
      "ranked_name_ephemeral_not_output":True,
      "ranked_api_spec_filter":expected_spec,
      "individual_combatant_spec_independently_observed":False,
      "combatant_talent_build_verified":False,
      "strict_pre_state_reconstructed":False,
      "cooldown_or_resource_readiness":"UNKNOWN",
      "WCL_observed_action_priority_claim":"NONE",
      "simc_semantic_answers_injected_into_blind_lane":False,
    }

def self_test():
    a={"report":{"code":"ABCDEF123456","fightID":9},"name":"Sample"}
    actors=[
      {"id":15,"name":"Sample","type":"Player","subType":"Warrior"},
      {"id":21,"name":"Sample","type":"Pet","subType":"Warrior"},
      {"id":16,"name":"Different","type":"Player","subType":"Warrior"},
      {"id":22,"name":"Sample","type":"Player","subType":"Mage"},
    ]
    def resolve(row=a,objs=actors):
        return ranked_actor(ranking_row=row,master_actors=objs,report_code="ABCDEF123456",fight_id=9)
    out=resolve()
    assert out["actor_numeric_id"]==15
    assert not out["individual_combatant_spec_independently_observed"]
    assert "Sample" not in json.dumps(out)
    assert out["cooldown_or_resource_readiness"]=="UNKNOWN"
    count=4
    for wrong,objs,expected in [
      ({**a,"report":{"code":"OTHERREPORT","fightID":9}},actors,"REPORT_MISMATCH"),
      ({**a,"report":{"code":"ABCDEF123456","fightID":10}},actors,"FIGHT_MISMATCH"),
      ({**a,"name":"Missing"},actors,"NONUNIQUE_OR_MISSING"),
      ({**a,"name":"Sample"},actors+[{"id":99,"name":"Sample","type":"Player","subType":"Warrior"}],"NONUNIQUE_OR_MISSING"),
      ({**a,"actorID":16},actors,"NONUNIQUE_OR_MISSING"),
      ({**a,"actorID":"15"},actors,"NOT_NUMERIC"),
      ({"report":a["report"]},actors,"NEITHER_NAME_NOR_ACTOR_ID"),
      ({**a,"actorID":15},actors,"IGNORED"),
    ]:
        if expected=="IGNORED":
            assert resolve(wrong,objs)["actor_numeric_id"]==15
        else:
            try:resolve(wrong,objs)
            except ActorResolutionError as e:assert expected in str(e),(expected,str(e))
            else:raise AssertionError("BAD_RANKER_IDENTITY_ACCEPTED "+expected)
        count+=1
    return {"result":"PASS","checks":count,
            "real_WCL_actor_identity":"NOT_RUN",
            "player_names_emitted":False,
            "SimC_label_injection":False}

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--self-test",action="store_true")
    x=a.parse_args()
    print(json.dumps(self_test(),indent=2))

if __name__=="__main__":main()
