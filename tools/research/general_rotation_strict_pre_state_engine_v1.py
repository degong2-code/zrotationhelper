#!/usr/bin/env python3
"""Spec-neutral strict-PRE transition replay for independent WCL research.

Discovery accepts ONLY normalized WCL-event transitions, never SimC APL
semantics or an observed cast as the answer. A state at decision t uses the
LATEST transition at time strictly < t. If latest prior transition is
expired, ambiguous at a timestamp, missing or unverified, it is UNKNOWN;
do not fall back to an older favorable transition.

WCL discovery snapshot creation is separate from *post-lock* semantic
gate mapping. Only a locked, separately auditable candidate mapping can
convert holdout snapshots to generic proof-engine Facts. Same-timestamp
and future events cannot enter PRE. Native and SimC are not required.

No fabricated mechanic truth, READY, optimality or dummy-error verdict.
"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from hashlib import sha256
import json
from collections import defaultdict

from general_rotation_decision_proof_engine_v1 import (
    Identity, Fact, DecisionProofError
)

SCHEMA="ZrotGeneralRotationStrictPreStateEngineV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
VERIFIED="VERIFIED_SOURCE_TRANSITION"
UNVERIFIED="UNVERIFIED_NORMALIZATION"
RAW_SOURCE="WCL_NORMALIZED_RAW_EVENT"
UNKNOWN="UNKNOWN"

class StrictPreError(ValueError):
    pass

def valid_hash(value:str)->bool:
    return isinstance(value,str) and len(value)==64 and all(
        char in "0123456789abcdef" for char in value
    )

def canonical(value)->bytes:
    return (json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode("utf-8")

@dataclass(frozen=True)
class Transition:
    source_event_id: str
    cohort_id: str
    scope: str
    actor_id: str
    signal: str
    t_ms: int
    value: bool|None
    valid_until_ms: int|None
    raw_receipt_sha256: str
    source_kind: str=RAW_SOURCE
    quality: str=UNVERIFIED

    def __post_init__(self):
        if not all(isinstance(x,str) and x for x in (
            self.source_event_id,self.cohort_id,self.scope,self.actor_id,self.signal
        )):
            raise StrictPreError("RAW_TRANSITION_IDENTITY_INCOMPLETE")
        if self.source_kind!=RAW_SOURCE:
            raise StrictPreError("WCL_BLIND_COHORT_CANNOT_IMPORT_SIMC_OR_GUIDE_FACTS")
        if self.quality not in (VERIFIED,UNVERIFIED):
            raise StrictPreError("RAW_TRANSITION_VALIDATION_QUALITY_UNKNOWN")
        if type(self.t_ms) is not int or self.t_ms<0:
            raise StrictPreError("RAW_TRANSITION_TIMESTAMP_INVALID")
        if self.value is not None and type(self.value) is not bool:
            raise StrictPreError("RAW_TRANSITION_VALUE_NOT_BOOLEAN_TRI_STATE")
        if self.valid_until_ms is not None and (
            type(self.valid_until_ms) is not int or
            self.valid_until_ms<=self.t_ms
        ):
            raise StrictPreError("RAW_TRANSITION_EXPIRY_INVALID")
        if not valid_hash(self.raw_receipt_sha256):
            raise StrictPreError("RAW_TRANSITION_RECEIPT_NOT_SOURCE_PINNED")

    def payload(self):
        return {
            "source_event_id":self.source_event_id,
            "cohort_id":self.cohort_id,
            "scope":self.scope,"actor_id":self.actor_id,
            "signal":self.signal,"t_ms":self.t_ms,
            "value":self.value,"valid_until_ms":self.valid_until_ms,
            "raw_receipt_sha256":self.raw_receipt_sha256,
            "source_kind":self.source_kind,"quality":self.quality,
        }

@dataclass(frozen=True)
class LockedCandidate:
    candidate_id: str
    candidate_source_sha256: str
    discovery_cohort_id: str
    frozen_lock_receipt_sha256: str
    signal_to_gate: tuple[tuple[str,str],...]

    def __post_init__(self):
        if not self.candidate_id or not self.discovery_cohort_id:
            raise StrictPreError("LOCK_IDENTITY_REQUIRED")
        if not (valid_hash(self.candidate_source_sha256)
                and valid_hash(self.frozen_lock_receipt_sha256)):
            raise StrictPreError("CANDIDATE_LOCK_PIN_MISSING")
        if (not self.signal_to_gate or
            len(set(g for _,g in self.signal_to_gate))!=len(self.signal_to_gate) or
            len(set(s for s,_ in self.signal_to_gate))!=len(self.signal_to_gate) or
            any(not s or not g for s,g in self.signal_to_gate)):
            raise StrictPreError("CANDIDATE_LOCK_SIGNAL_GATE_MAPPING_INCOMPLETE")

class StrictPreReplay:
    """Immutable, deterministic event index; event ordering never guessed."""

    def __init__(self,transitions:list[Transition]):
        by_event={}
        for t in transitions:
            earlier=by_event.get(t.source_event_id)
            if earlier is not None and earlier!=t:
                raise StrictPreError("DUPLICATED_EVENT_ID_WITH_CONFLICTING_SOURCE_PAYLOAD")
            by_event[t.source_event_id]=t
        self.ordered=tuple(sorted(by_event.values(),
            key=lambda e:(e.cohort_id,e.scope,e.actor_id,e.signal,
                          e.t_ms,e.source_event_id)))
        self.fingerprint=sha256(canonical([e.payload() for e in self.ordered])).hexdigest()
        index=defaultdict(lambda:defaultdict(list))
        for event in self.ordered:
            group=(event.cohort_id,event.scope,event.actor_id,event.signal)
            index[group][event.t_ms].append(event)
        self.index={}
        for group,times in index.items():
            ordered_times=tuple(sorted(times))
            self.index[group]=(
                ordered_times,
                tuple(tuple(times[t]) for t in ordered_times)
            )

    def snapshot(self,*,cohort_id:str,scope:str,actor_id:str,
                 at_ms:int,signals:tuple[str,...])->dict:
        if (not cohort_id or not scope or not actor_id or
            type(at_ms) is not int or at_ms<0 or
            not signals or len(set(signals))!=len(signals) or
            any(not isinstance(s,str) or not s for s in signals)):
            raise StrictPreError("SNAPSHOT_ACTOR_CLOCK_OR_SIGNAL_REQUEST_INVALID")
        states={}
        for signal in signals:
            times,groups=self.index.get((cohort_id,scope,actor_id,signal),((),()))
            pos=bisect_left(times,at_ms)-1
            if pos<0:
                states[signal]={"status":UNKNOWN,"reason":"NO_EARLIER_SOURCE_TRANSITION",
                                "value":None,"event_t_ms":None,
                                "source_event_id":None,"raw_receipt_sha256":None}
                continue
            group=groups[pos]
            previous_ms=times[pos]
            # Contradictory transitions at one prior timestamp have
            # no trustworthy order. Never choose by event or API page order.
            comparable={(e.value,e.valid_until_ms,e.quality) for e in group}
            if len(comparable)!=1:
                status=UNKNOWN;reason="AMBIGUOUS_SAME_PRIOR_TIMESTAMP"
            elif any(e.valid_until_ms is not None and
                     at_ms>=e.valid_until_ms for e in group):
                status=UNKNOWN;reason="LATEST_TRANSITION_EXPIRED_NO_OLDER_FALLBACK"
            elif any(e.quality!=VERIFIED for e in group):
                status=UNKNOWN;reason="UNVERIFIED_RAW_TRANSITION"
            elif group[0].value is None:
                status=UNKNOWN;reason="RAW_EVENT_STATE_UNKNOWN"
            else:
                status="KNOWN";reason="STRICT_EARLIER_VERIFIED_SOURCE_TRANSITION"
            event=min(group,key=lambda x:x.source_event_id)
            states[signal]={
                "status":status,"reason":reason,
                "value":event.value if status=="KNOWN" else None,
                "event_t_ms":previous_ms,
                "source_event_id":event.source_event_id if status=="KNOWN" else None,
                "raw_receipt_sha256":event.raw_receipt_sha256 if status=="KNOWN" else None,
            }
        result={
            "schema":SCHEMA,
            "cohort_id":cohort_id,"scope":scope,"actor_id":actor_id,
            "at_ms":at_ms,"signals":states,
            "input_event_set_sha256":self.fingerprint,
            "strict_PRE_latest_valid_transition_used":True,
            "SimC_APL_answer_injected":False,
            "state_is_not_full_spell_ready":True,
            "WCL_live_API_called":False,
        }
        result["snapshot_sha256"]=sha256(canonical(result)).hexdigest()
        return result

    def heldout_facts(self,snapshot:dict,identity:Identity,
                      lock:LockedCandidate)->list[Fact]:
        """Post-lock only. A lock's real-world independence needs external audit."""
        if (snapshot.get("schema")!=SCHEMA or
            snapshot.get("snapshot_sha256")!=sha256(canonical({
                k:v for k,v in snapshot.items() if k!="snapshot_sha256"
            })).hexdigest()):
            raise StrictPreError("SOURCE_SNAPSHOT_INTEGRITY_INVALID")
        if snapshot["input_event_set_sha256"]!=self.fingerprint:
            raise StrictPreError("SNAPSHOT_FROM_UNRELATED_RAW_EVENT_SET")
        # Unkeyed snapshot SHA alone does not prove the snapshot was
        # actually generated by this replay; independently regenerate
        # exact actor and signal state before materializing any Fact.
        restored=self.snapshot(
            cohort_id=snapshot["cohort_id"],scope=snapshot["scope"],
            actor_id=snapshot["actor_id"],at_ms=snapshot["at_ms"],
            signals=tuple(snapshot["signals"].keys()))
        if restored!=snapshot:
            raise StrictPreError("SNAPSHOT_VALUES_NOT_FROM_IMMUTABLE_PRE_REPLAY")
        if (snapshot["cohort_id"]==lock.discovery_cohort_id or
            snapshot["at_ms"]!=identity.t_ms or
            identity.source_sha256!=lock.candidate_source_sha256):
            raise StrictPreError("DISCOVERY_LEAKAGE_OR_LOCKED_SOURCE_IDENTITY_CHANGED")
        if identity.scope!=lock.candidate_id:
            raise StrictPreError("LOCKED_WCL_CANDIDATE_IDENTITY_MISMATCH")
        facts=[]
        for signal,gate in lock.signal_to_gate:
            raw=snapshot["signals"].get(signal)
            if raw is None:
                raise StrictPreError("LOCKED_SIGNAL_NOT_SNAPSHOTTED")
            if raw["status"]=="KNOWN":
                if raw["event_t_ms"]>=identity.t_ms:
                    raise StrictPreError("WCL_STRICT_EARLIER_TIMESTAMP_BROKEN")
                facts.append(Fact(identity,gate,raw["value"],
                    "INDEPENDENT_WCL_PRE","WCL_STRICT_PRE",
                    raw["event_t_ms"],raw["raw_receipt_sha256"]))
            else:
                facts.append(Fact(identity,gate,None,"UNOBSERVED",
                    "UNKNOWN",identity.t_ms,
                    "UNKNOWN:"+raw["reason"]))
        return facts


def selftest()->dict:
    h="a"*64
    def ev(i,t,v,cohort="holdout",signal="charge",
           until=None,quality=VERIFIED):
        return Transition(i,cohort,"report-1/fight-2","player-A",
                          signal,t,v,until,h,quality=quality)
    source=[
        ev("a1",10,False),ev("a2",20,True),
        ev("a3",30,False),ev("a4",30,True),
        ev("b1",5,True,signal="proc",until=15),
        ev("b2",25,False,signal="proc",quality=UNVERIFIED),
        ev("c1",12,True,cohort="discovery"),
        ev("a5",40,False),
    ]
    one=StrictPreReplay(source)
    two=StrictPreReplay(list(reversed(source))+[source[0]])
    assert one.fingerprint==two.fingerprint
    def snap(t,signals=("charge",)):
        return one.snapshot(cohort_id="holdout",scope="report-1/fight-2",
                            actor_id="player-A",at_ms=t,signals=signals)
    assert snap(20)["signals"]["charge"]["value"] is False
    assert snap(21)["signals"]["charge"]["value"] is True
    assert snap(30)["signals"]["charge"]["value"] is True
    assert snap(31)["signals"]["charge"]["reason"]=="AMBIGUOUS_SAME_PRIOR_TIMESTAMP"
    assert snap(40)["signals"]["charge"]["reason"]=="AMBIGUOUS_SAME_PRIOR_TIMESTAMP"
    assert snap(41)["signals"]["charge"]["value"] is False
    assert snap(15,("proc",))["signals"]["proc"]["reason"]=="LATEST_TRANSITION_EXPIRED_NO_OLDER_FALLBACK"
    assert snap(26,("proc",))["signals"]["proc"]["reason"]=="UNVERIFIED_RAW_TRANSITION"
    assert snap(21,("missing",))["signals"]["missing"]["value"] is None
    assert snap(21)["snapshot_sha256"]==two.snapshot(
        cohort_id="holdout",scope="report-1/fight-2",
        actor_id="player-A",at_ms=21,signals=("charge",))["snapshot_sha256"]
    lock=LockedCandidate("candidate-1","b"*64,"discovery","c"*64,
                         (("charge","cooldown_ready"),("missing","target_ready")))
    identity=Identity("candidate-1","b"*64,21,0,0)
    s=snap(21,("charge","missing"))
    facts=one.heldout_facts(s,identity,lock)
    assert facts[0].value is True and facts[0].event_t_ms==20
    assert facts[1].value is None and facts[1].basis=="UNOBSERVED"
    # No FULL READY without complete independent gates and reviewed
    # route coverage. Synthetic other-specialization gate sets are
    # routed through the same generic engine, not hardcoded here.
    from general_rotation_decision_proof_engine_v1 import (
        GateContract,decide_candidate,UNKNOWN as PROOF_UNKNOWN
    )
    contract=GateContract("SPEC-ONE",("cooldown_ready","target_ready"),
                          "b"*64,closed=False)
    result=decide_candidate(identity,contract,facts,True)
    assert result["decision"]==PROOF_UNKNOWN
    another_lock=LockedCandidate("candidate-2","d"*64,"discovery","e"*64,
                                 (("charge","special_proc"),))
    another_id=Identity("candidate-2","d"*64,21,0,0)
    another=one.heldout_facts(s,another_id,another_lock)
    assert another[0].value is True
    assert decide_candidate(another_id,GateContract(
        "SPEC-TWO",("special_proc",),"d"*64),another,True)["decision"]==PROOF_UNKNOWN
    poison=[
        lambda:Transition("evil","discovery","scope","actor","x",1,
                          True,None,h,source_kind="SIMC_APL"),
        lambda:StrictPreReplay([ev("same",1,True),ev("same",1,False)]),
        lambda:ev("bad",-1,True),
        lambda:one.heldout_facts(s,Identity("candidate-1","b"*64,22,0,0),lock),
        lambda:one.heldout_facts(s,Identity("candidate-1","b"*64,21,0,0),
                                 LockedCandidate("candidate-1","b"*64,"holdout","c"*64,
                                                 (("charge","cooldown_ready"),))),
        lambda:one.heldout_facts(dict(s,snapshot_sha256="0"*64),identity,lock),
        lambda:one.heldout_facts(
            dict(s,signals={**s["signals"],"charge":{
                **s["signals"]["charge"],"value":False}},
                snapshot_sha256=sha256(canonical({
                    **{k:v for k,v in s.items() if k!="snapshot_sha256"},
                    "signals":{**s["signals"],"charge":{
                        **s["signals"]["charge"],"value":False}}
                })).hexdigest()),identity,lock),
        lambda:one.heldout_facts(s,Identity("other","b"*64,21,0,0),lock),
        lambda:one.snapshot(cohort_id="holdout",scope="x",actor_id="player-A",
                            at_ms=20,signals=("a","a")),
    ]
    for attempt in poison:
        try:attempt()
        except (StrictPreError,DecisionProofError):pass
        else:raise AssertionError("STRICT_PRE_FENCE_OR_LOCK_BYPASS_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":24,"synthetic_specializations":2,
        "actual_WCL_live_calls":0,"actual_WCL_source_verified":False,
        "source_stage":"GENERIC_REPLAY_ONLY",
        "real_candidate_holdout_completed":False,
        "full_positive_ready_proven":False,
        "WCL_API_calls":0,
    }

def main():
    print(json.dumps(selftest(),sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    main()
