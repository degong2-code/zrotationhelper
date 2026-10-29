#!/usr/bin/env python3
"""Spec-agnostic, STRICT-PRE readiness *hypothesis* provider for SimC APL.

Does NOT infer the source of a cooldown, a spell cost, charges, GCD, range,
target validity or spec mechanics. Every mandatory applicability dimension
must be explicitly checked or waived with evidence before a candidate READY.
The policy itself remains RESEARCH_UNVERIFIED until independently certified.
No WCL/Blizzard network, no automatic rule promotion.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

MANDATORY = (
    "ability_learned", "cooldown_or_charge", "resource",
    "gcd", "cast_state", "movement", "range", "target",
)
OPS = frozenset(("eq", "ne", "gt", "ge", "lt", "le"))


@dataclass(frozen=True)
class ReadinessVerdict:
    status: str   # READY, NOT_READY, UNKNOWN
    reason: str
    unknown_features: tuple[str, ...] = ()
    inspected_features: tuple[str, ...] = ()
    policy_evidence: str | None = None
    empirical_authority: str = "NOT_VERIFIED"


def _number(v: Any):
    if type(v) is bool:
        return float(v)
    if type(v) in (int, float):
        try:
            n = float(v)
            return n if math.isfinite(n) else None
        except (ValueError, OverflowError):
            return None
    return None


def _predicate(rule: Mapping[str, Any], state) -> tuple[str, str | None]:
    """Evaluate one externally-defined PRE feature predicate without guesses."""
    key = rule.get("feature")
    op = rule.get("op")
    cmp = _number(rule.get("value"))
    if not isinstance(key, str) or not key or op not in OPS or cmp is None:
        raise ValueError("INVALID_READINESS_PREDICATE")
    observation = state.features.get(key)
    if observation is None:
        return "UNKNOWN", key
    obs_status = getattr(observation.status, "value", observation.status)
    if obs_status != "OBSERVED":
        return "UNKNOWN", key
    ts = observation.source_timestamp_ms
    if ts is None:
        # An initial value without a provenance timestamp must not assert
        # actual WCL/combat cooldown readiness.
        return "UNKNOWN", key
    if ts >= state.decision_timestamp_ms:
        raise ValueError("READINESS_FEATURE_NOT_STRICT_PRE")
    actual = _number(observation.value)
    if actual is None:
        return "UNKNOWN", key
    truth = {
        "eq": lambda: actual == cmp, "ne": lambda: actual != cmp,
        "gt": lambda: actual > cmp, "ge": lambda: actual >= cmp,
        "lt": lambda: actual < cmp, "le": lambda: actual <= cmp,
    }[op]()
    return ("PASS" if truth else "FAIL"), key


def _dimension(block: Mapping[str, Any], state) -> tuple[str, set[str], set[str]]:
    if not isinstance(block, dict):
        raise ValueError("INVALID_READINESS_DIMENSION")
    if block.get("mode") == "NOT_APPLICABLE":
        evidence = block.get("evidence_ref")
        reason = block.get("reason")
        if not isinstance(evidence, str) or not evidence.strip() or \
                not isinstance(reason, str) or not reason.strip():
            raise ValueError("UNJUSTIFIED_READINESS_WAIVER")
        if block.keys() - {"mode", "evidence_ref", "reason"}:
            raise ValueError("AMBIGUOUS_READINESS_WAIVER")
        return "PASS", set(), set()
    if block.get("mode") not in ("ALL", "ANY"):
        raise ValueError("INVALID_READINESS_DIMENSION_MODE")
    preds=block.get("predicates")
    if not isinstance(preds, list) or not preds:
        raise ValueError("EMPTY_READINESS_DIMENSION")
    responses = [_predicate(x,state) for x in preds]
    inspected = {key for status,key in responses if key and status!="UNKNOWN"}
    unknown = {key for status,key in responses if key and status=="UNKNOWN"}
    statuses = [status for status,_ in responses]
    if block["mode"]=="ALL":
        if "FAIL" in statuses:
            return "FAIL", set(), inspected
        if "UNKNOWN" in statuses:
            return "UNKNOWN", unknown, inspected
        return "PASS", set(), inspected
    if "PASS" in statuses:
        return "PASS", set(), inspected
    if "UNKNOWN" in statuses:
        return "UNKNOWN", unknown, inspected
    return "FAIL", set(), inspected


def derive_readiness(
    contract: Mapping[str, Any], state, *,
    spec_slug: str, build_key: str, apl_sha256: str,
) -> dict[str, ReadinessVerdict]:
    """Calculate readiness statuses WITHOUT claiming game/truth authority.

    Every dimension must have an explicit source-accountable policy. A missing
    dimension makes READY impossible. A known disqualifying requirement can
    establish NOT_READY even if other requirements are unobserved.
    """
    state.validate()
    if contract.get("schema")!="ZrotGenericReadinessRequirementsV1":
        raise ValueError("READINESS_CONTRACT_SCHEMA")
    for field,value in (("spec_slug",spec_slug),("build_key",build_key),
                        ("apl_sha256",apl_sha256)):
        if not value or contract.get(field)!=value:
            raise ValueError("READINESS_CONTRACT_IDENTITY_MISMATCH_"+field)
    if contract.get("hypothesis_only") is not True:
        raise ValueError("READINESS_CLAIM_AUTHORITY_FORBIDDEN")
    policies=contract.get("actions")
    if not isinstance(policies, dict) or not policies:
        raise ValueError("READINESS_ACTION_POLICIES_EMPTY")
    result={}
    for action,policy in policies.items():
        if not isinstance(action,str) or not action or not isinstance(policy,dict):
            raise ValueError("INVALID_READINESS_ACTION")
        evidence=policy.get("evidence_ref")
        if not isinstance(evidence,str) or not evidence.strip():
            raise ValueError("ACTION_READINESS_EVIDENCE_REQUIRED")
        dimensions=policy.get("dimensions",{})
        if not isinstance(dimensions,dict):
            raise ValueError("INVALID_READINESS_DIMENSIONS")
        extras=set(dimensions)-set(MANDATORY)
        if extras:
            raise ValueError("UNRECOGNIZED_READINESS_DIMENSION")
        if set(MANDATORY)-set(dimensions):
            result[action]=ReadinessVerdict(
                "UNKNOWN","INCOMPLETE_READINESS_DIMENSION_COVERAGE",
                (),(),evidence)
            continue
        statuses=[]
        unresolved=set()
        inspected=set()
        for key in MANDATORY:
            status,missing,seen=_dimension(dimensions[key],state)
            statuses.append(status)
            unresolved.update(missing)
            inspected.update(seen)
        if "FAIL" in statuses:
            status,reason="NOT_READY","OBSERVED_DISQUALIFYING_REQUIREMENT"
        elif "UNKNOWN" in statuses:
            status,reason="UNKNOWN","MISSING_OR_UNOBSERVABLE_REQUIREMENT"
        else:
            status,reason="READY","ALL_DECLARED_REQUIREMENTS_SATISFIED"
        result[action]=ReadinessVerdict(
            status,reason,tuple(sorted(unresolved)),
            tuple(sorted(inspected)),evidence)
    return result


def selftest():
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/
                          "02_SOURCE"/"runtime"))
    from raid_dps.core.behavioral_evaluator import (
        StrictPreStateProvider,StateTransition,
    )
    policy={
        "schema":"ZrotGenericReadinessRequirementsV1",
        "spec_slug":"synthetic_spec","build_key":"synthetic_build",
        "apl_sha256":"b"*64,"hypothesis_only":True,
        "actions":{"spell_x":{"evidence_ref":"synthetic_contract",
            "dimensions":{dim:{"mode":"NOT_APPLICABLE",
                "reason":"synthetic waived only",
                "evidence_ref":"synthetic_contract"}
                for dim in MANDATORY}}},
    }
    policy["actions"]["spell_x"]["dimensions"]["cooldown_or_charge"]={
        "mode":"ANY","predicates":[
            {"feature":"cooldown_ms","op":"le","value":0},
            {"feature":"charges","op":"ge","value":1},
        ]}
    policy["actions"]["spell_x"]["dimensions"]["resource"]={
        "mode":"ALL","predicates":[
            {"feature":"resource","op":"ge","value":30},
        ]}
    def state(events):
        return StrictPreStateProvider().build(
            action_timestamp_ms=1000,
            transitions=[StateTransition(*e) for e in events])
    args=dict(spec_slug="synthetic_spec",build_key="synthetic_build",
              apl_sha256="b"*64)
    observed=state([(900,"charges",1),(900,"resource",40)])
    ready=derive_readiness(policy,observed,**args)["spell_x"]
    assert ready.status=="READY" and ready.empirical_authority=="NOT_VERIFIED"
    noresource=derive_readiness(
        policy,state([(900,"charges",1)]),**args)["spell_x"]
    assert noresource.status=="UNKNOWN" and noresource.unknown_features==("resource",)
    failed=derive_readiness(
        policy,state([(900,"charges",0),(900,"cooldown_ms",500),
                      (900,"resource",40)]),**args)["spell_x"]
    assert failed.status=="NOT_READY"
    # Future / same-time measurements MUST NOT leak into the decision.
    later=derive_readiness(
        policy,state([(1000,"charges",1),(1001,"resource",40)]),
        **args)["spell_x"]
    assert later.status=="UNKNOWN"
    # Missing one whole dimension prevents READY even with all predicates.
    incomplete={**policy,"actions":{"spell_x":{
        **policy["actions"]["spell_x"],
        "dimensions":{k:v for k,v in
          policy["actions"]["spell_x"]["dimensions"].items() if k!="target"}}}}
    assert derive_readiness(incomplete,observed,**args)["spell_x"].status=="UNKNOWN"
    # Unjustified NOT_APPLICABLE must fail, not silently allow READY.
    malformed={**policy,"actions":{"spell_x":{
        **policy["actions"]["spell_x"],"dimensions":{
            **policy["actions"]["spell_x"]["dimensions"],
            "target":{"mode":"NOT_APPLICABLE"}}}}}
    try:derive_readiness(malformed,observed,**args)
    except ValueError as e:
        assert str(e)=="UNJUSTIFIED_READINESS_WAIVER"
    else:raise AssertionError("UNJUSTIFIED_WAIVER_ACCEPTED")
    print("SIMC_GENERIC_PRE_READINESS_SELF_TEST=PASS")


if __name__=="__main__":
    selftest()
