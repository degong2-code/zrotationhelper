#!/usr/bin/env python3
"""Spec-neutral, open-world proof engine for General Rotation and dummy feedback.

This is a reusable decision engine, NOT a Fury/Warrior policy. SpecAdapters
supply source-pinned required gate names and independent state evaluators.
Everything missing is UNKNOWN. Observed Native ready/choice and repeated WCL
casts are *comparators*, never readiness truth. WCL facts require a state
transition with timestamp strictly less than the evaluated action timestamp;
a SimC source PRE read is explicitly a different provenance contract.

Negative independent necessary predicates may eliminate a skill. Positive
READY requires every declared necessary predicate independently true PLUS
an externally reviewed, source-pinned exhaustive route closure certificate.
No guessed or empty gate set may yield READY. Context without complete game
addon observability must not produce a dummy practice error verdict.

The engine is transport-, specialization-, and encounter-agnostic.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

SCHEMA = "ZrotGeneralRotationDecisionProofEngineV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
NOT_READY = "NOT_READY"
READY = "READY"
UNKNOWN = "UNKNOWN"
TRUSTED_BASIS = frozenset(("INDEPENDENT_SOURCE_REPLAY","INDEPENDENT_WCL_PRE"))
ALLOWED_BASIS = TRUSTED_BASIS | frozenset(("NATIVE_SOURCE_OBSERVED","NATIVE_READY_COMPARATOR","WCL_ACTION_OBSERVED","UNOBSERVED"))
CONTROL_COMMANDS = frozenset((
    "variable","call_action_list","run_action_list","swap_action_list",
    "sequence","strict_sequence","wait","pool_resource"
))

class DecisionProofError(ValueError):
    pass

@dataclass(frozen=True)
class Identity:
    scope: str
    source_sha256: str
    t_ms: int
    ordinal: int
    occurrence: int

    def __post_init__(self):
        if not self.scope or len(self.source_sha256)!=64 or not all(
            x in "0123456789abcdef" for x in self.source_sha256
        ) or self.t_ms<0 or self.ordinal<0 or self.occurrence<0:
            raise DecisionProofError("INVALID_EXACT_SOURCE_DECISION_IDENTITY")

@dataclass(frozen=True)
class Fact:
    identity: Identity
    gate: str
    value: bool|None
    basis: str
    captured: str
    event_t_ms: int
    receipt: str

    def __post_init__(self):
        if not self.gate or self.basis not in ALLOWED_BASIS:
            raise DecisionProofError("FACT_GATE_OR_BASIS_INVALID")
        if self.value is not None and type(self.value) is not bool:
            raise DecisionProofError("FACT_BOOLEAN_MUST_BE_EXPLICIT")
        if not self.receipt or not self.captured:
            raise DecisionProofError("FACT_PROVENANCE_REQUIRED")
        if self.captured=="WCL_STRICT_PRE":
            if self.event_t_ms>=self.identity.t_ms:
                raise DecisionProofError("WCL_SAME_TIMESTAMP_OR_FUTURE_LEAKAGE")
            if self.basis!="INDEPENDENT_WCL_PRE":
                raise DecisionProofError("WCL_PRE_CANNOT_BE_NATIVE_SOURCE")
        elif self.captured=="SIMC_ORIGINAL_METHOD_PRE":
            if self.event_t_ms!=self.identity.t_ms:
                raise DecisionProofError("SIMC_ORIGINAL_CALL_PRE_TIME_NOT_SOURCE_EXACT")
            if self.basis=="INDEPENDENT_WCL_PRE":
                raise DecisionProofError("SIMC_SOURCE_NOT_WCL_PRE")
        elif self.captured=="OBSERVED_POST_COMPARATOR":
            if self.basis in TRUSTED_BASIS:
                raise DecisionProofError("NATIVE_POST_CANNOT_BE_INDEPENDENT_PRE")
        elif self.captured=="UNKNOWN":
            if self.basis!="UNOBSERVED" or self.value is not None:
                raise DecisionProofError("UNKNOWN_EVIDENCE_MUST_BE_UNKNOWN")
        else:
            raise DecisionProofError("UNSUPPORTED_EVIDENCE_TIME_CONTRACT")

@dataclass(frozen=True)
class GateContract:
    source: str
    required: tuple[str,...]
    source_sha256: str
    closed: bool = False
    closure_receipt: str|None = None

    def __post_init__(self):
        if (not self.source or not self.required or
            len(set(self.required))!=len(self.required) or
            any(not v for v in self.required) or
            len(self.source_sha256)!=64 or
            any(c not in "0123456789abcdef" for c in self.source_sha256)):
            raise DecisionProofError("INCOMPLETE_OR_INVALID_GATE_CONTRACT")
        if self.closed and not self.closure_receipt:
            raise DecisionProofError("POSITIVE_ROUTE_CLOSURE_RECEIPT_REQUIRED")

def decide_candidate(identity:Identity,contract:GateContract,
                     facts:Iterable[Fact],is_physical_action:bool)->dict:
    """Necessary false => NOT_READY. Every proven gate plus closed route => READY."""
    if identity.source_sha256!=contract.source_sha256:
        raise DecisionProofError("CONTRACT_SOURCE_ROW_FINGERPRINT_MISMATCH")
    items=list(facts)
    by_gate={}
    for f in items:
        if f.identity!=identity:
            raise DecisionProofError("EVIDENCE_FROM_OTHER_TIME_ROW_OR_OCCURRENCE")
        if f.gate in by_gate:
            raise DecisionProofError("DUPLICATE_OR_CONTRADICTORY_GATE_EVIDENCE")
        if f.gate not in contract.required:
            raise DecisionProofError("GATE_UNDECLARED_IN_CONTRACT")
        by_gate[f.gate]=f
    independent_false=[]
    independent_true=[]
    source_observations=[]
    gaps=[]
    for gate in contract.required:
        f=by_gate.get(gate)
        if f is None:
            gaps.append(gate+":MISSING")
        elif f.basis not in TRUSTED_BASIS or f.value is None:
            gaps.append(gate+":NOT_INDEPENDENT")
            source_observations.append(gate) if f.basis!="UNOBSERVED" else None
        elif f.value:
            independent_true.append(gate)
        else:
            independent_false.append(gate)
    if not is_physical_action:
        return {"decision":UNKNOWN,"blockers":["APL_CONTROL_COMMAND"],
                "independent_false":[], "independent_true":independent_true,
                "source_only":source_observations,
                "missing_or_unverified":gaps,
                "positive_route_closed":False,
                "dummy_error_permitted":False}
    if independent_false:
        verdict=NOT_READY
        blockers=sorted(independent_false)
    elif not gaps and contract.closed:
        verdict=READY
        blockers=[]
    else:
        verdict=UNKNOWN
        blockers=(gaps if gaps else ["OPEN_WORLD_UNCLOSED_VIRTUAL_METHOD_ROUTE"])
        if not contract.closed:
            blockers=sorted(set(blockers+["OPEN_WORLD_UNCLOSED_VIRTUAL_METHOD_ROUTE"]))
    return {
        "decision":verdict,
        "blockers":blockers,
        "independent_false":sorted(independent_false),
        "independent_true":sorted(independent_true),
        "source_only":sorted(source_observations),
        "missing_or_unverified":sorted(gaps),
        "positive_route_closed":contract.closed,
        # Real dummy verdict additionally needs target addon-observability
        # coverage, held-out validation and a separately checked evaluator.
        "dummy_error_permitted":False,
    }

def evaluate_priority(candidates:list[dict],returned_index:int|None,
                      *,source_order_complete:bool,
                      native_selected_name:str|None=None)->dict:
    """Compute a *proof* frontier, never consume Native selection as readiness."""
    if not candidates or any(c.get("decision") not in (NOT_READY,READY,UNKNOWN)
                             for c in candidates):
        raise DecisionProofError("CANDIDATES_MISSING_TRI_STATE_PROOF")
    if returned_index is not None and not 0<=returned_index<len(candidates):
        raise DecisionProofError("SOURCE_WINNER_INDEX_NOT_IN_PROOF_FRONTIER")
    if returned_index is None:
        if source_order_complete and all(x["decision"]==NOT_READY for x in candidates):
            status="NO_ELIGIBLE_CANDIDATE_PROVEN"
        else:
            status="UNKNOWN"
        earlier=candidates
    else:
        earlier=candidates[:returned_index]
        if (source_order_complete and all(x["decision"]==NOT_READY for x in earlier)
            and candidates[returned_index]["decision"]==READY):
            status="SOURCE_ORDER_CHOICE_PROVEN_FOR_DECLARED_CONTRACT"
        else:
            status="UNKNOWN"
    counts=Counter(c["decision"] for c in earlier)
    return {
        "decision":status,
        "earlier_NOT_READY":counts[NOT_READY],
        "earlier_UNKNOWN":counts[UNKNOWN],
        "earlier_READY":counts[READY],
        "returned_READINESS":(candidates[returned_index]["decision"]
                              if returned_index is not None else None),
        "source_order_complete":bool(source_order_complete),
        "native_selection_used_as_readiness_input":False,
        "native_selected_name_POST_comparator_only":native_selected_name,
        "optimality_or_WCL_holdout_proven":False,
        "dummy_error_permitted":False,
    }

def selftest()->dict:
    h="a"*64
    k=Identity("source-list-alpha",h,100,1,0)
    spec=GateContract("SPEC_ALPHA",("if","cooldown","resource","target","spec_override"),h)
    def fact(name,value,basis="INDEPENDENT_SOURCE_REPLAY",
             captured="SIMC_ORIGINAL_METHOD_PRE",time=100):
        return Fact(k,name,value,basis,captured,time,"TEST_SOURCE_NO_NATIVE_INPUT")
    p=[fact(name,True) for name in spec.required]
    a=decide_candidate(k,spec,p,True)
    assert a["decision"]==UNKNOWN and "OPEN_WORLD_UNCLOSED_VIRTUAL_METHOD_ROUTE" in a["blockers"]
    ready_contract=GateContract("SPEC_ALPHA",spec.required,h,closed=True,
                                closure_receipt="SOURCE_GUARD_EXHAUSTIVENESS_TEST")
    b=decide_candidate(k,ready_contract,p,True)
    assert b["decision"]==READY and b["dummy_error_permitted"] is False
    c=decide_candidate(k,ready_contract,p[:-1],True)
    assert c["decision"]==UNKNOWN
    d=decide_candidate(k,spec,p[:-1]+[fact("spec_override",False)],True)
    assert d["decision"]==NOT_READY
    x=decide_candidate(k,spec,p[:-1]+[
        fact("spec_override",True,"NATIVE_READY_COMPARATOR",
             "OBSERVED_POST_COMPARATOR")],True)
    assert x["decision"]==UNKNOWN and "spec_override" in x["source_only"]
    control=decide_candidate(k,ready_contract,p,False)
    assert control["decision"]==UNKNOWN
    frontier=evaluate_priority([d,b],1,source_order_complete=True,
                               native_selected_name="second")
    assert frontier["decision"]=="SOURCE_ORDER_CHOICE_PROVEN_FOR_DECLARED_CONTRACT"
    assert evaluate_priority([d,a],1,source_order_complete=True)["decision"]==UNKNOWN
    assert evaluate_priority([d,b],1,source_order_complete=False)["decision"]==UNKNOWN
    assert evaluate_priority([d],None,source_order_complete=True)["decision"]=="NO_ELIGIBLE_CANDIDATE_PROVEN"
    # Different specialization has different declared gate set; generic
    # function stays unchanged.
    beta=GateContract("SPEC_BETA",("if","resource","transform"),h)
    assert decide_candidate(k,beta,[fact("if",True),fact("resource",True)],True)["decision"]==UNKNOWN
    tamper=[
        lambda:Fact(k,"if",True,"INDEPENDENT_WCL_PRE","WCL_STRICT_PRE",100,"receipt"),
        lambda:Fact(k,"if",True,"INDEPENDENT_WCL_PRE","WCL_STRICT_PRE",101,"receipt"),
        lambda:Fact(k,"if",True,"INDEPENDENT_SOURCE_REPLAY","OBSERVED_POST_COMPARATOR",100,"receipt"),
        lambda:decide_candidate(k,spec,p+[p[0]],True),
        lambda:decide_candidate(Identity("other",h,100,1,1),spec,p,True),
        lambda:GateContract("EMPTY",(),h,closed=True,closure_receipt="x"),
        lambda:GateContract("SPEC",("if",),h,closed=True),
    ]
    for bad in tamper:
        try:bad()
        except DecisionProofError:pass
        else:raise AssertionError("SOURCE_EVIDENCE_BYPASS_ACCEPTED")
    # Strict WCL proof: earlier event permitted, same/future forbidden.
    assert Fact(k,"if",True,"INDEPENDENT_WCL_PRE",
                "WCL_STRICT_PRE",99,"valid").value is True
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC","checks":20,
            "generic_spec_count":2,"Native_production":"NOT_RUN",
            "all_unknown_cannot_be_dummy_mistake":True,"WCL_API_calls":0}

def main():
    import json
    print(json.dumps(selftest(),sort_keys=True))

if __name__=="__main__":
    main()
