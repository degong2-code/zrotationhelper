#!/usr/bin/env python3
"""Independent numeric WCL observation lock for post-lock research.

Consumes ONLY the pinned, numeric FreshWCLReplayV1 output produced by
fresh_wcl_engine_v1.replay(). Does NOT import SimC, spell labels, APL or
guides. Preconfigured observation-count cutoff is recorded before exposure
to any SimC hypothesis. An observational lock does NOT validate a rotation
or prove that an action was ready or optimal.

Safe no-arg self-test synthesizes a WCL-shaped snapshot and replay.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT/"tools"/"engine_first") not in sys.path:
    sys.path.insert(0,str(ROOT/"tools"/"engine_first"))
from fresh_wcl_engine_v1 import canonical,sha,replay,collect

EXPECTED="FreshWCLReplayV1"
LOCK_SCHEMA="ZrotWave3NumericCandidateLock"

class BlindInputError(ValueError):
    pass

def _verify(proof:dict):
    if not isinstance(proof,dict) or proof.get("schema")!=EXPECTED:
        raise BlindInputError("REPLAY_SOURCE_SCHEMA")
    q=dict(proof)
    claim=q.pop("replay_sha256",None)
    if not isinstance(claim,str) or not re.fullmatch("[0-9a-f]{64}",claim) or sha(canonical(q))!=claim:
        raise BlindInputError("REPLAY_FINGERPRINT_MISMATCH")
    if proof.get("blind_numeric_only") is not True:
        raise BlindInputError("SEMANTIC_LEAKAGE_OR_NOT_BLIND")
    if proof.get("candidate_lock")!="NOT_IMPLEMENTED":
        raise BlindInputError("REPLAY_ALREADY_SEMANTICALLY_MODIFIED")
    if proof.get("cooldown_or_resource_readiness")!="UNKNOWN":
        raise BlindInputError("INFERRED_READINESS_NOT_ALLOWED")
    identity=proof.get("identity",{})
    if not isinstance(identity,dict) or not isinstance(identity.get("code"),str) or type(identity.get("fight")) is not int:
        raise BlindInputError("REPORT_FIGHT_IDENTITY_MISSING")
    if not isinstance(proof.get("decisions"),list):
        raise BlindInputError("DECISION_ROWS_MISSING")
    ids=set()
    for d in proof["decisions"]:
        if not isinstance(d,dict) or type(d.get("timestamp")) not in (int,float):
            raise BlindInputError("INVALID_CAST_TIMESTAMP")
        if d.get("readiness")!="UNKNOWN":
            raise BlindInputError("UNKNOWN_READINESS_OVERRIDDEN")
        a=d.get("ability_id")
        if a is not None and (type(a) is not int or a<=0):
            raise BlindInputError("INVALID_NUMERIC_ACTION")
        actor=d.get("source_actor_id")
        if actor is not None and type(actor) is not int:
            raise BlindInputError("ACTOR_NUMERIC_ONLY")
        if not isinstance(d.get("aura_pre"),dict):
            raise BlindInputError("STRICT_PRE_AURA_REQUIRED")
        if any(not str(k).isdigit() for k in d["aura_pre"]):
            raise BlindInputError("SEMANTIC_AURA_NAME_NOT_ALLOWED")
    return (identity["code"],identity["fight"])


def lock_candidates(proofs:list[dict],*,min_observations:int=2,source_kind:str="ATTESTED_RAW_WCL_REPLAY")->dict:
    if source_kind not in ("ATTESTED_RAW_WCL_REPLAY","SYNTHETIC_FIXTURE"):
        raise BlindInputError("SOURCE_PROVENANCE_NOT_ALLOWED")
    if type(min_observations) is not int or not 1<=min_observations<=1000:
        raise BlindInputError("BAD_PRELOCK_OBSERVATION_THRESHOLD")
    if not 1<=len(proofs)<=200:
        raise BlindInputError("BOUNDED_DISCOVERY_COHORT")
    used=set()
    tally=Counter()
    actor_counts=Counter()
    source_hashes=[]
    missing=0
    for proof in proofs:
        identity=_verify(proof)
        if identity in used:raise BlindInputError("DUPLICATE_DISCOVERY_FIGHT")
        used.add(identity)
        source_hashes.append(proof["replay_sha256"])
        for row in proof["decisions"]:
            action=row["ability_id"]
            if action is None:
                missing+=1
                continue
            # Frequency is only an observational candidate; neither priority
            # nor pairwise readiness is asserted by this lock.
            tally[action]+=1
            if row["source_actor_id"] is not None:
                actor_counts[action,row["source_actor_id"]]+=1
    candidates=[
        {
           "action_spell_id":aid,
           "observed_event_count":n,
           "distinct_numeric_actor_count":len({
               actor for spell,actor in actor_counts if spell==aid
           }),
           "semantic_name":None,"gameplay_rule_claim":False,
           "priority_claim":False,"causality_claim":False,
           "readiness":"UNKNOWN"
        }
        for aid,n in sorted(tally.items()) if n>=min_observations
    ]
    if not candidates:
        raise BlindInputError("NO_NUMERIC_CANDIDATES_AT_PRELOCK_THRESHOLD")
    lock={
       "schema":LOCK_SCHEMA,
       "status":"LOCKED_NUMERIC_ONLY",
       "source_kind":source_kind,
       "source_replay_sha256":sorted(source_hashes),
       "discovery_fight_count":len(proofs),
       "candidate_n":len(candidates),
       "candidates":candidates,
       "unidentified_numeric_action_count":missing,
       "prelocked_min_observations":min_observations,
       "threshold_retuned_after_discovery":False,
       "semantic_names_attached":False,
       "gameplay_rule_claim":False,
       "wcl_blind_candidate_producer":"NUMERIC_COUNTS_NO_SIMC_INPUT",
       "independent_fresh_WCL_data_verified":False if source_kind=="SYNTHETIC_FIXTURE" else "RAW_SOURCE_AUDIT_REQUIRED",
       "priority_optimality_or_causality_proven":False,
       "holdout_validated":False,
       "user_general_rotation_rule_eligible":False,
    }
    return lock


def selftest():
    def transport(q,v):
        if "FreshReport" in q:
            return {"reportData":{"report":{
               "code":"ABCDEF123456","revision":1,
               "fights":[{"id":1,"startTime":1000,"endTime":2500,
                          "encounterID":0,"difficulty":4,"inProgress":False}]
            }}}
        return {"reportData":{"report":{"events":{"data":[
            {"timestamp":1020,"type":"applybuff","targetID":7,"abilityGameID":444,"stack":1},
            {"timestamp":1030,"type":"cast","sourceID":7,"abilityGameID":100},
            {"timestamp":1040,"type":"cast","sourceID":7,"abilityGameID":200},
            {"timestamp":1040,"type":"removebuff","targetID":7,"abilityGameID":444},
            {"timestamp":1050,"type":"cast","sourceID":7,"abilityGameID":100},
            {"timestamp":1100,"type":"cast","sourceID":7,"abilityGameID":200},
            {"timestamp":1200,"type":"cast","sourceID":8,"abilityGameID":300},
        ],"nextPageTimestamp":None}}}}
    count=0
    with tempfile.TemporaryDirectory(prefix="zrot-wcl-blind-") as temp:
        root=Path(temp)
        collect(transport,"ABCDEF123456",1,root,max_pages=2)
        p=replay(root/"ABCDEF123456"/"fight_1")
        lock=lock_candidates([p],min_observations=2,source_kind="SYNTHETIC_FIXTURE")
        assert lock["status"]=="LOCKED_NUMERIC_ONLY"
        assert {r["action_spell_id"] for r in lock["candidates"]}=={100,200}
        assert lock["candidate_n"]==2
        assert lock["semantic_names_attached"] is False
        assert lock["threshold_retuned_after_discovery"] is False
        assert lock["gameplay_rule_claim"] is False
        assert lock["holdout_validated"] is False
        count+=6
        # Reuse existing post-lock guard's canonical lock reader, ensuring
        # the independent producer does not inject semantic content.
        if str(ROOT/"tools"/"research") not in sys.path:
            sys.path.insert(0,str(ROOT/"tools"/"research"))
        from post_lock_simc_wcl_guard_replay import _locked_numeric_actions
        raw=canonical(lock);digest=hashlib.sha256(raw).hexdigest()
        assert _locked_numeric_actions(raw,digest)=={100,200};count+=1
        for tweak,label in [
          (lambda x:x.update({"replay_sha256":"0"*64}),"REPLAY_FINGERPRINT"),
          (lambda x:x.update({"cooldown_or_resource_readiness":"READY"}),"INFERRED_READINESS"),
          (lambda x:x["decisions"][0].update({"readiness":"READY"}),"UNKNOWN_READINESS"),
          (lambda x:x["decisions"][0].update({"ability_id":"stormstrike"}),"INVALID_NUMERIC"),
          (lambda x:x["decisions"][0]["aura_pre"].update({"buff.foo":{}}),"SEMANTIC_AURA"),
        ]:
            q=json.loads(json.dumps(p))
            tweak(q)
            # Tampered replay SHA itself must always be rejected first; for
            # structural negatives, re-pin the synthetic digest and test gate.
            if label!="REPLAY_FINGERPRINT":
                q["replay_sha256"]=sha(canonical({k:v for k,v in q.items() if k!="replay_sha256"}))
            try:lock_candidates([q],source_kind="SYNTHETIC_FIXTURE",min_observations=2)
            except BlindInputError as ex:assert label in str(ex),str(ex)
            else:raise AssertionError("BLIND_TAMPER_ACCEPTED_"+label)
            count+=1
        for wrong,label in [
            (0,"BAD_PRELOCK"),
            (True,"BAD_PRELOCK"),
            (1001,"BAD_PRELOCK"),
        ]:
            try:lock_candidates([p],source_kind="SYNTHETIC_FIXTURE",min_observations=wrong)
            except BlindInputError as ex:assert label in str(ex)
            else:raise AssertionError("TUNED_THRESHOLD_ACCEPTED")
            count+=1
        try:lock_candidates([p,p],source_kind="SYNTHETIC_FIXTURE",min_observations=2)
        except BlindInputError as ex:assert "DUPLICATE_DISCOVERY" in str(ex)
        else:raise AssertionError("DISCOVERY_COHORT_DUPLICATE_ACCEPTED")
        count+=1
    return {"result":"PASS","synthetic_assertions":count,
            "actual_WCL_API_calls":0,
            "actual_WCL_ranker_cohort":"NOT_COLLECTED",
            "SimC_semantic_input":"NEVER_USED",
            "independent_holdout":"NOT_RUN",
            "rotation_priority_causality":"NOT_PROVEN"}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--replay-files",type=Path,nargs="+")
    ap.add_argument("--min-observations",type=int,default=2)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    if args.self_test or not args.replay_files:
        result=selftest()
    else:
        result=lock_candidates(
           [json.loads(p.read_text(encoding="utf-8")) for p in args.replay_files],
           min_observations=args.min_observations,
           source_kind="ATTESTED_RAW_WCL_REPLAY"
        )
    raw=canonical(result)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        if args.output.exists():
            raise SystemExit("LOCK_ALREADY_EXISTS_DO_NOT_OVERWRITE")
        args.output.write_bytes(raw)
        print("WCL_NUMERIC_CANDIDATE_LOCK_CREATED_SHA256="+sha(raw))
    else:
        print(raw.decode(),end="")

if __name__=="__main__":
    main()
