#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""zRotationHelper: branch-local, generic, source-obligation *research gate*.

Purpose
-------
Wrap (DO NOT replace) the existing SimC APL 8-dimension research-readiness
provider. Catch missing source-specific requirements, identity drift, and
STRICT-PRE unknowns before emitting a candidate actionability hypothesis.

This file has no production/gameplay authority. It never outputs READY and
never emits a recommendation. Its source inventory is a declared candidate,
not independently verified Blizzard/current-game source completeness.

Dependencies: Python 3.10+ standard library only. No Git, WCL, SimC or network.
Run without arguments to print a synthetic demonstration; --self-test checks
fail-closed behavior and prints a compact test receipt.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

SCHEMA = "ZrotSourceObligationGateV1"
PHASE = "POST_SIMC_HYPOTHESIS_RESEARCH_ONLY"
GATE_CANDIDATE = "ALL_DECLARED_GATES_PASS_RESEARCH_ONLY"
GATE_NEGATIVE = "OBSERVED_NEGATIVE_RESEARCH_ONLY"
GATE_UNKNOWN = "UNKNOWN"
_ALLOWED_OPS = {"eq", "ne", "ge", "gt", "le", "lt"}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ContractViolation(ValueError):
    """An identity/schema violation must not be treated as a normal result."""


@dataclass(frozen=True)
class ResearchGateResult:
    status: str
    reason: str
    input_readiness: str
    missing_gate_ids: tuple[str, ...]
    unknown_gate_ids: tuple[str, ...]
    negative_gate_ids: tuple[str, ...]
    accepted_gate_ids: tuple[str, ...]
    decision_timestamp_ms: int
    evidence_level: str = "SHADOW_ONLY"
    empirical_authority: str = "NOT_VERIFIED"
    user_recommendation_eligible: bool = False
    frozen_or_main_promotion: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest(value: Any) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ContractViolation("INVALID_SOURCE_SHA256")
    return value


def _identity(candidate: Mapping[str, Any], requested: Mapping[str, Any]) -> None:
    """No name-based fuzzy join or version/build fallback."""
    for field in ("spec_slug", "build_key", "action_id", "source_sha256"):
        if field not in requested or field not in candidate:
            raise ContractViolation("MISSING_IDENTITY_" + field)
        a, b = candidate[field], requested[field]
        if field == "action_id":
            if type(a) is not int or type(b) is not int or a <= 0 or b <= 0:
                raise ContractViolation("INVALID_NUMERIC_ACTION_ID")
        elif field == "source_sha256":
            _digest(a)
            _digest(b)
        elif not isinstance(a, str) or not a or not isinstance(b, str) or not b:
            raise ContractViolation("INVALID_IDENTITY_" + field)
        if a != b:
            raise ContractViolation("IDENTITY_MISMATCH_" + field)


def _finite(value: Any) -> float | None:
    if type(value) not in (float, int):
        return None
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _predicate(op: str, observed: Any, threshold: Any) -> bool | None:
    actual, bound = _finite(observed), _finite(threshold)
    if actual is None or bound is None or op not in _ALLOWED_OPS:
        return None
    return {"eq": lambda: actual == bound,
            "ne": lambda: actual != bound,
            "ge": lambda: actual >= bound,
            "gt": lambda: actual > bound,
            "le": lambda: actual <= bound,
            "lt": lambda: actual < bound}[op]()


def _latest_pre(gate_id: str, events: Sequence[Mapping[str, Any]], timestamp_ms: int) -> Any | None:
    """Latest valid observation with t_event < t_action; conflicts stay unknown.

    A same-time or future observation is excluded even if it would be helpful.
    When latest PRE observations conflict at the same timestamp, UNKNOWN wins.
    """
    # A more recent PRE transition with an unresolved observation shadows an
    # older measured value; silently falling back would fabricate continuity.
    eligible: list[tuple[int, float | None]] = []
    for e in events:
        if not isinstance(e, Mapping) or e.get("gate_id") != gate_id:
            continue
        t = e.get("timestamp_ms")
        if type(t) is not int or t >= timestamp_ms:
            continue
        val = _finite(e.get("value")) if e.get("status") == "OBSERVED" else None
        eligible.append((t, val))
    if not eligible:
        return None
    latest = max(t for t, _ in eligible)
    values = {v for t, v in eligible if t == latest}
    return next(iter(values)) if len(values) == 1 else None


def assess(
    *, identity: Mapping[str, Any], source_inventory: Mapping[str, Any],
    action_policy: Mapping[str, Any], readiness_status: str,
    transitions: Sequence[Mapping[str, Any]], decision_timestamp_ms: int,
) -> ResearchGateResult:
    """Perform post-hypothesis gating; this MUST NOT enter blind WCL discovery.

    The inventory and policy may be from the same producer, so equality of
    gate IDs is only a STRUCTURAL check, never source completeness proof.
    """
    if type(decision_timestamp_ms) is not int or decision_timestamp_ms < 0:
        raise ContractViolation("INVALID_DECISION_TIMESTAMP")
    if source_inventory.get("schema") != SCHEMA:
        raise ContractViolation("INVENTORY_SCHEMA_MISMATCH")
    if action_policy.get("schema") != SCHEMA:
        raise ContractViolation("POLICY_SCHEMA_MISMATCH")
    if source_inventory.get("phase") != PHASE or action_policy.get("phase") != PHASE:
        raise ContractViolation("BLIND_DISCOVERY_SEMANTIC_LEAKAGE_FORBIDDEN")
    _identity(source_inventory, identity)
    _identity(action_policy, identity)
    if readiness_status not in ("READY", "NOT_READY", "UNKNOWN"):
        raise ContractViolation("INVALID_EXISTING_READINESS_STATUS")
    if not isinstance(transitions, Sequence) or isinstance(transitions, (str, bytes)):
        raise ContractViolation("INVALID_TRANSITIONS")
    expected = source_inventory.get("declared_required_gate_ids")
    gates = action_policy.get("gates")
    if not isinstance(expected, list) or not isinstance(gates, list) or not expected:
        raise ContractViolation("INVALID_SOURCE_GATE_DECLARATION")
    if any(not isinstance(g, str) or not g for g in expected) or len(expected) != len(set(expected)):
        raise ContractViolation("INVALID_OR_DUPLICATE_INVENTORY_GATE_ID")
    if any(not isinstance(g, dict) or not isinstance(g.get("gate_id"), str) or not g["gate_id"] for g in gates):
        raise ContractViolation("INVALID_POLICY_GATE")
    actual_ids = [g["gate_id"] for g in gates]
    if len(actual_ids) != len(set(actual_ids)):
        raise ContractViolation("DUPLICATE_POLICY_GATE")
    unexpected = set(actual_ids) - set(expected)
    if unexpected:
        raise ContractViolation("UNDECLARED_SOURCE_GATE")

    missing = set(expected) - set(actual_ids)
    unknown = set()
    negative = set()
    accepted = set()
    for gate in gates:
        gate_id = gate["gate_id"]
        mode = gate.get("mode")
        if mode == "NOT_APPLICABLE":
            # A waiver is not mechanic truth merely because it exists.
            if not isinstance(gate.get("reason"), str) or not gate["reason"].strip() or \
               not isinstance(gate.get("evidence_ref"), str) or not gate["evidence_ref"].strip():
                unknown.add(gate_id)
            else:
                accepted.add(gate_id)
            continue
        if mode != "REQUIRED":
            unknown.add(gate_id)
            continue
        if not isinstance(gate.get("evidence_ref"), str) or not gate["evidence_ref"].strip():
            unknown.add(gate_id)
            continue
        observed = _latest_pre(gate_id, transitions, decision_timestamp_ms)
        truth = _predicate(gate.get("op"), observed, gate.get("threshold"))
        if truth is None:
            unknown.add(gate_id)
        elif truth:
            accepted.add(gate_id)
        else:
            negative.add(gate_id)

    # Policy is research-only irrespective of any producer-supplied flags.
    if readiness_status == "NOT_READY" or negative:
        status, reason = GATE_NEGATIVE, "OBSERVED_DISQUALIFIER_RESEARCH_ONLY"
    elif readiness_status != "READY":
        status, reason = GATE_UNKNOWN, "UPSTREAM_READINESS_UNKNOWN"
    elif missing or unknown:
        status, reason = GATE_UNKNOWN, "MISSING_OR_UNOBSERVABLE_SOURCE_GATE"
    elif source_inventory.get("source_completeness") != "DECLARED_CANDIDATE":
        status, reason = GATE_UNKNOWN, "SOURCE_COVERAGE_NOT_DECLARED"
    else:
        status, reason = GATE_CANDIDATE, "ALL_DECLARED_GATES_SATISFIED_NOT_CERTIFIED"
    return ResearchGateResult(
        status, reason, readiness_status,
        tuple(sorted(missing)), tuple(sorted(unknown)),
        tuple(sorted(negative)), tuple(sorted(accepted)),
        decision_timestamp_ms)


def assess_from_existing_provider(
    *, existing_verdict: object,
    identity: Mapping[str, Any], source_inventory: Mapping[str, Any],
    action_policy: Mapping[str, Any], transitions: Sequence[Mapping[str, Any]],
    decision_timestamp_ms: int,
) -> ResearchGateResult:
    """Thin adapter for simc_apl_readiness_provider.ReadinessVerdict.

    Uses the existing eight-dimensional evaluator's result; does not
    implement its predicates or declare it independently verified.
    """
    if getattr(existing_verdict, "empirical_authority", None) != "NOT_VERIFIED":
        raise ContractViolation("UNVERIFIED_UPSTREAM_AUTHORITY_REQUIRED")
    return assess(
        identity=identity, source_inventory=source_inventory,
        action_policy=action_policy,
        readiness_status=getattr(existing_verdict, "status", None),
        transitions=transitions, decision_timestamp_ms=decision_timestamp_ms)


def synthetic_fixture() -> dict[str, Any]:
    """Names/IDs and observations are fabricated fixtures, NOT real WoW data."""
    ident = {"spec_slug": "synthetic_spec", "build_key": "synthetic_build",
             "action_id": 987654321, "source_sha256": "a" * 64}
    source = {"schema": SCHEMA, "phase": PHASE, **ident,
              "declared_required_gate_ids": ["cooldown_gate", "resource_gate"],
              "source_completeness": "DECLARED_CANDIDATE"}
    policy = {"schema": SCHEMA, "phase": PHASE, **ident, "gates": [
        {"gate_id": "cooldown_gate", "mode": "REQUIRED", "op": "le",
         "threshold": 0, "evidence_ref": "SYNTHETIC_COOLDOWN"},
        {"gate_id": "resource_gate", "mode": "REQUIRED", "op": "ge",
         "threshold": 30, "evidence_ref": "SYNTHETIC_COST"},
    ]}
    transitions = [
        {"gate_id": "cooldown_gate", "timestamp_ms": 900, "value": 0, "status": "OBSERVED"},
        {"gate_id": "resource_gate", "timestamp_ms": 950, "value": 45, "status": "OBSERVED"},
    ]
    return {"identity": ident, "source_inventory": source, "action_policy": policy,
            "readiness_status": "READY", "transitions": transitions,
            "decision_timestamp_ms": 1000}


def self_test() -> dict[str, Any]:
    from copy import deepcopy
    passed: list[str] = []

    def run(name: str, mutate, expected: str) -> None:
        case = synthetic_fixture()
        mutate(case)
        result = assess(**case)
        assert result.status == expected, (name, result)
        assert result.user_recommendation_eligible is False
        assert result.frozen_or_main_promotion is False
        assert result.empirical_authority == "NOT_VERIFIED"
        passed.append(name)

    run("complete_declared_candidate", lambda f: None, GATE_CANDIDATE)
    run("policy_missing_required_gate", lambda f: f["action_policy"]["gates"].pop(), GATE_UNKNOWN)
    run("unverified_source_inventory", lambda f: f["source_inventory"].update(source_completeness="UNKNOWN"), GATE_UNKNOWN)
    run("unknown_upstream", lambda f: f.update(readiness_status="UNKNOWN"), GATE_UNKNOWN)
    run("observed_upstream_negative", lambda f: f.update(readiness_status="NOT_READY"), GATE_NEGATIVE)
    run("missing_observation", lambda f: f["transitions"].pop(), GATE_UNKNOWN)
    run("same_timestamp_not_visible", lambda f: f["transitions"][1].update(timestamp_ms=1000), GATE_UNKNOWN)
    run("future_transition_not_visible", lambda f: f["transitions"][1].update(timestamp_ms=1001), GATE_UNKNOWN)
    run("older_prior_survives_future", lambda f: f["transitions"].append({"gate_id":"resource_gate", "timestamp_ms":1001,"value":0,"status":"OBSERVED"}), GATE_CANDIDATE)
    run("observed_disqualifier", lambda f: f["transitions"][1].update(value=12), GATE_NEGATIVE)
    run("negative_even_if_other_gate_missing", lambda f: (f["action_policy"]["gates"].pop(0), f["transitions"][1].update(value=12)), GATE_NEGATIVE)
    run("conflicting_same_time_pre", lambda f: f["transitions"].append({"gate_id":"resource_gate","timestamp_ms":950,"value":5,"status":"OBSERVED"}), GATE_UNKNOWN)
    run("later_unresolved_pre_overrides_older", lambda f: f["transitions"].append({"gate_id":"resource_gate","timestamp_ms":990,"value":None,"status":"UNKNOWN"}), GATE_UNKNOWN)
    run("unjustified_waiver_unknown", lambda f: f["action_policy"]["gates"][1].update(mode="NOT_APPLICABLE"), GATE_UNKNOWN)
    run("evidence_backed_waiver_candidate_only", lambda f: f["action_policy"]["gates"][1].update(mode="NOT_APPLICABLE",reason="synthetic only",evidence_ref="FIXTURE"), GATE_CANDIDATE)
    run("non_numeric_observation_unknown", lambda f: f["transitions"][1].update(value="45"), GATE_UNKNOWN)
    run("nan_observation_unknown", lambda f: f["transitions"][1].update(value=float("nan")), GATE_UNKNOWN)

    for field, new_value in [("build_key", "wrong_build"),
                             ("action_id", 1),
                             ("source_sha256", "c" * 64)]:
        case = synthetic_fixture()
        case["identity"][field] = new_value
        try:
            assess(**case)
        except ContractViolation as exc:
            assert str(exc) == "IDENTITY_MISMATCH_" + field
        else:
            raise AssertionError("MISSING_IDENTITY_REJECTION:" + field)
        passed.append("identity_reject_" + field)

    case = synthetic_fixture()
    case["action_policy"]["phase"] = "WCL_BLIND"
    try:
        assess(**case)
    except ContractViolation as exc:
        assert str(exc) == "BLIND_DISCOVERY_SEMANTIC_LEAKAGE_FORBIDDEN"
    else:
        raise AssertionError("WCL_BLIND_SEMANTIC_LEAK_ACCEPTED")
    passed.append("blind_WCL_semantic_leak_rejected")

    case = synthetic_fixture()
    case["action_policy"]["gates"].append(deepcopy(case["action_policy"]["gates"][0]))
    try:
        assess(**case)
    except ContractViolation as exc:
        assert str(exc) == "DUPLICATE_POLICY_GATE"
    else:
        raise AssertionError("DUPLICATE_ACCEPTED")
    passed.append("duplicate_gate_rejected")

    from types import SimpleNamespace
    fixture = synthetic_fixture()
    verified = assess_from_existing_provider(
        existing_verdict=SimpleNamespace(status="READY",empirical_authority="NOT_VERIFIED"),
        **{k:v for k,v in fixture.items() if k!="readiness_status"})
    assert verified.status == GATE_CANDIDATE and not verified.user_recommendation_eligible
    passed.append("existing_eight_dimension_provider_bridge")
    try:
        assess_from_existing_provider(
            existing_verdict=SimpleNamespace(status="READY",empirical_authority="VERIFIED"),
            **{k:v for k,v in fixture.items() if k!="readiness_status"})
    except ContractViolation as exc:
        assert str(exc) == "UNVERIFIED_UPSTREAM_AUTHORITY_REQUIRED"
    else:
        raise AssertionError("FALSIFIED_UPSTREAM_AUTHORITY_ACCEPTED")
    passed.append("upstream_authority_claim_rejected")

    return {"schema": "ZrotSourceObligationGateSelfTestV1",
            "result": "PASS", "count": len(passed), "cases": passed,
            "evidence_level": "SYNTHETIC_STATIC_ONLY",
            "real_wcl": "NOT_RUN", "real_simc": "NOT_RUN",
            "live_client_gameplay": "NOT_VERIFIED", "production_promotion": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = self_test()
    else:
        result = {"mode": "SYNTHETIC_DEMO_ONLY", **assess(**synthetic_fixture()).to_dict()}
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
