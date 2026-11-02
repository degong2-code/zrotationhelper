#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ST-03 isolated STRICT PRE observability bridge for source-specific gates.

PINNED SIMC RESEARCH LANE ONLY: do not import into WCL blind discovery.
Consumes an explicitly declared, integrity-checked feature transition ledger.
Reuses the existing StrictPreStateProvider, ST-02 source/identity compiler,
the real SimC readiness provider and ST-01 Source Obligation Gate. A transition
ledger's checksum is NOT a producer-authenticity or mechanic-verification proof.
Neither source requirements nor gate evaluations are certified gameplay truth.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_SOURCE" / "runtime"))
from raid_dps.core.behavioral_evaluator import (
    StrictPreStateProvider, StateTransition,
)
import ST02_source_identity_reconciliation_v1 as st02
import ST01_existing_simc_readiness_gate_regression_v1 as st01

SCHEMA = "ZrotST03DeclaredSourceTransitionLedgerV1"
PHASE = "POST_SIMC_HYPOTHESIS_RESEARCH_ONLY"
ORIGINS = ("SYNTHETIC_TEST", "EXTERNAL_DECLARED_UNVERIFIED")
SCOPES = ("ACTOR", "TARGET", "ACTION", "ENCOUNTER")
STATUSES = ("OBSERVED", "UNKNOWN", "UNOBSERVABLE")
FIELDS = frozenset((
    "event_id", "timestamp_ms", "sequence", "feature_key", "scope",
    "subject_id", "status", "value", "valid", "producer_ref", "evidence_ref",
))
HEX64 = frozenset("0123456789abcdef")


class ST03ContractError(ValueError):
    pass


@dataclass(frozen=True)
class ST03Receipt:
    status: str
    source_coverage_status: str
    typed_identity_status: str
    upstream_readiness: str
    required_state_diagnostics: dict[str, dict[str, str]]
    source_gate_diagnostics: dict[str, str]
    excluded_same_timestamp_n: int
    excluded_future_n: int
    excluded_invalid_n: int
    ledger_sha256: str
    provenance_class: str
    source_authenticity: str = "NOT_INDEPENDENTLY_VERIFIED"
    mechanic_semantic_verification: str = "NOT_RUN"
    wcl_blind_lock: str = "NOT_RUN"
    live_gameplay_readiness_certified: int = 0
    user_recommendation_eligible: bool = False
    authority_promotion: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(
        rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")).hexdigest()


def _positive_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _validate_ledger(ledger: Mapping[str, Any], action: str, ts: int,
                     mandatory: set[str]) -> tuple[list[dict], dict, int, int, int]:
    if ledger.get("schema") != SCHEMA or ledger.get("phase") != PHASE:
        raise ST03ContractError("ST03_SCHEMA_OR_LANE_MISMATCH")
    if ledger.get("provenance_class") not in ORIGINS or ledger.get("verified_producer") is not False:
        raise ST03ContractError("UNVERIFIED_PRODUCER_CANNOT_CLAIM_AUTHORITY")
    if ledger.get("decision_timestamp_ms") != ts or type(ts) is not int or ts < 0:
        raise ST03ContractError("ST03_DECISION_TIMESTAMP_MISMATCH")
    if ledger.get("action_token") != action:
        raise ST03ContractError("ST03_ACTION_TOKEN_MISMATCH")
    actors = (ledger.get("decision_actor_id"), ledger.get("decision_target_id"))
    if not _positive_string(actors[0]):
        raise ST03ContractError("ACTOR_IDENTITY_REQUIRED")
    if actors[1] is not None and not _positive_string(actors[1]):
        raise ST03ContractError("INVALID_TARGET_IDENTITY")
    bindings = ledger.get("feature_bindings")
    if not isinstance(bindings, dict):
        raise ST03ContractError("EXPLICIT_FEATURE_BINDINGS_REQUIRED")
    for key, bind in bindings.items():
        if (not _positive_string(key) or not isinstance(bind, dict)
                or set(bind) != {"scope", "subject_id", "evidence_ref"}
                or bind.get("scope") not in SCOPES
                or not _positive_string(bind.get("subject_id"))
                or not _positive_string(bind.get("evidence_ref"))):
            raise ST03ContractError("INVALID_TYPED_FEATURE_BINDING")
        if bind["scope"] == "ACTOR" and bind["subject_id"] != actors[0]:
            raise ST03ContractError("ACTOR_FEATURE_BINDING_MISMATCH")
        if bind["scope"] == "TARGET" and actors[1] is not None and bind["subject_id"] != actors[1]:
            raise ST03ContractError("TARGET_FEATURE_BINDING_MISMATCH")
        if bind["scope"] == "ACTION" and bind["subject_id"] != action:
            raise ST03ContractError("ACTION_FEATURE_BINDING_MISMATCH")
    if not mandatory.issubset(set(bindings)):
        # Report absent feature as unknown instead of inventing a producer.
        pass
    events = ledger.get("events")
    if not isinstance(events, list) or len(events) > 50000:
        raise ST03ContractError("INVALID_LEDGER_ROWS")
    expected_digest = ledger.get("ledger_sha256")
    try:
        computed_digest = digest(events)
    except (TypeError, ValueError) as exc:
        raise ST03ContractError("ST03_NONFINITE_OR_INVALID_LEDGER_JSON") from exc
    if (not isinstance(expected_digest, str) or len(expected_digest) != 64
            or set(expected_digest) - HEX64 or expected_digest != computed_digest):
        raise ST03ContractError("ST03_LEDGER_SHA256_MISMATCH")
    ids: set[str] = set()
    same = future = invalid = 0
    for ev in events:
        if not isinstance(ev, dict) or set(ev) != FIELDS:
            raise ST03ContractError("ST03_TRANSITION_ROW_SHAPE")
        key, ident = ev["feature_key"], ev["event_id"]
        if not _positive_string(ident) or ident in ids:
            raise ST03ContractError("ST03_DUPLICATE_EVENT_ID")
        ids.add(ident)
        if not _positive_string(key) or key not in bindings:
            raise ST03ContractError("ST03_UNBOUND_TRANSITION_FEATURE")
        if (type(ev["timestamp_ms"]) is not int or ev["timestamp_ms"] < 0
                or type(ev["sequence"]) is not int or ev["sequence"] < 0
                or type(ev["valid"]) is not bool or ev["scope"] not in SCOPES
                or not _positive_string(ev["subject_id"])
                or ev["status"] not in STATUSES):
            raise ST03ContractError("ST03_TRANSITION_TYPES")
        if not _positive_string(ev["producer_ref"]) or not _positive_string(ev["evidence_ref"]):
            raise ST03ContractError("ST03_TRANSITION_EVIDENCE_REQUIRED")
        if ev["status"] == "OBSERVED":
            if not _number(ev["value"]):
                raise ST03ContractError("ST03_NONFINITE_OR_NONNUMERIC_OBSERVATION")
        elif ev["value"] is not None:
            raise ST03ContractError("ST03_UNOBSERVED_HAS_VALUE")
        if not ev["valid"]:
            invalid += 1
        elif ev["timestamp_ms"] == ts:
            same += 1
        elif ev["timestamp_ms"] > ts:
            future += 1
    return events, bindings, same, future, invalid


def _latest(events: list[dict], key: str, binding: Mapping[str, str] | None,
            ts: int, decision_target_id: str | None) -> tuple[str, int | None, float | None]:
    if binding is None:
        return "UNKNOWN_UNMAPPED", None, None
    if binding["scope"] == "TARGET" and decision_target_id is None:
        return "UNKNOWN_TARGET_IDENTITY", None, None
    rows = [ev for ev in events
            if ev["feature_key"] == key and ev["valid"]
            and ev["scope"] == binding["scope"]
            and ev["subject_id"] == binding["subject_id"]
            and ev["timestamp_ms"] < ts]
    if not rows:
        return "UNKNOWN_NO_STRICT_PRE", None, None
    latest = max(ev["timestamp_ms"] for ev in rows)
    final = [ev for ev in rows if ev["timestamp_ms"] == latest]
    sig = {(ev["status"], ev["value"]) for ev in final}
    if len(sig) != 1:
        return "UNKNOWN_CONFLICTING_PRE", None, None
    row = final[0]
    if row["status"] != "OBSERVED":
        return ("UNKNOWN_LATEST_PRE" if row["status"] == "UNKNOWN" else "UNOBSERVABLE_PRE"), latest, None
    return "OBSERVED_STRICT_PRE_UNVERIFIED", latest, float(row["value"])


def evaluate(
    *, st02_case: Mapping[str, Any], readiness_contract: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> ST03Receipt:
    """Source-pinned structural observability + original actual-provider bridge.

    Source-gate OBSERVED numeric events are externally declared evaluations:
    never compute mechanic predicates from user-provided values. Require each
    declared source required-state prerequisite to be observed before the gate
    event, or suppress that gate event. No fallback to stale observation.
    """
    audit, compiled = st02.reconcile(**st02_case)
    selector = st02_case["selector"]
    token = selector["action_token"]
    source = json.loads(st02_case["source_json"])
    action = next(x for x in source["candidate_actions"]
                  if x["spec"] == selector["source_spec"] and x["action"] == token)
    requirements = {g["id"]: tuple(g["required_state"])
                    for g in action["extra_source_obligations"]}
    if set(requirements) != set(compiled["source_inventory"]["declared_required_gate_ids"]):
        raise ST03ContractError("ST02_SOURCE_REQUIRED_STATE_DRIFT")
    provider_features = set()
    for action_policy in readiness_contract.get("actions", {}).values():
        for dimension in action_policy.get("dimensions", {}).values():
            for rule in dimension.get("predicates", ()):
                provider_features.add(rule.get("feature"))
    provider_features = {x for x in provider_features if isinstance(x, str)}
    required_keys = set(provider_features)
    for states in requirements.values():
        required_keys.update(states)
    gate_names = {"source_gate::" + gid for gid in requirements}
    all_keys = required_keys | gate_names
    ts = ledger.get("decision_timestamp_ms")
    events, bindings, same, future, invalid = _validate_ledger(
        ledger, token, ts, all_keys)
    if set(bindings) - all_keys:
        raise ST03ContractError("ST03_EXTRA_BINDING_NOT_IN_SOURCE_OR_PROVIDER")
    # Gate decisions always belong to the selected action, never the target.
    for gate_name in gate_names:
        b = bindings.get(gate_name)
        if b is not None and (b["scope"] != "ACTION" or b["subject_id"] != token):
            raise ST03ContractError("SOURCE_GATE_MUST_BE_ACTION_SCOPED")
    state_statuses = {}
    selected = {}
    for key in sorted(required_keys):
        state_statuses[key] = _latest(
            events, key, bindings.get(key), ts, ledger.get("decision_target_id"))
        if state_statuses[key][0] == "OBSERVED_STRICT_PRE_UNVERIFIED":
            selected[key] = state_statuses[key]
    # Reuse the real provider; observed features ONLY, no initial values.
    # Conflicting and unobservable later states cannot fall back to older rows.
    pre_state = StrictPreStateProvider().build(
        action_timestamp_ms=ts,
        transitions=[StateTransition(time, key, value)
                     for key, (_, time, value) in selected.items()],
        required_keys=sorted(required_keys),
        unobservable_keys=[key for key in required_keys if key not in selected],
    )
    pre_state.validate()
    gate_transitions = []
    gate_diagnostics: dict[str, str] = {}
    for gid, states in sorted(requirements.items()):
        key = "source_gate::" + gid
        s, when, value = _latest(
            events, key, bindings.get(key), ts, ledger.get("decision_target_id"))
        prerequisite_times = []
        for feature in states:
            feature_status, seen_at, _ = state_statuses[feature]
            if feature_status != "OBSERVED_STRICT_PRE_UNVERIFIED":
                gate_diagnostics[gid] = "UNKNOWN_SOURCE_PREREQUISITE_" + feature_status
                break
            prerequisite_times.append(seen_at)
        else:
            if s != "OBSERVED_STRICT_PRE_UNVERIFIED":
                gate_diagnostics[gid] = s
            elif when < max(prerequisite_times):
                gate_diagnostics[gid] = "UNKNOWN_STALE_GATE_BEFORE_SOURCE_STATE"
            elif audit.coverage_status != "DECLARED_SOURCE_COVERAGE_CANDIDATE_ONLY":
                gate_diagnostics[gid] = "UNKNOWN_SOURCE_POLICY_INCOMPLETE"
            else:
                gate_transitions.append({
                    "gate_id": gid, "timestamp_ms": when, "value": value,
                    "status": "OBSERVED"})
                gate_diagnostics[gid] = "SOURCE_GATE_DECLARED_PRE_UNVERIFIED"
    binding = {
        **compiled["identity"], "simc_action_key": token,
        "apl_sha256": selector["effective_apl_sha256"],
        "mapping_evidence_ref": selector["mapping_evidence_ref"],
    }
    verdict = st01.assess_from_actual_provider(
        readiness_contract=readiness_contract, pre_state=pre_state,
        binding=binding, source_inventory=compiled["source_inventory"],
        action_policy=compiled["action_policy"],
        transitions=gate_transitions, decision_timestamp_ms=ts)
    if verdict.user_recommendation_eligible or verdict.frozen_or_main_promotion:
        raise ST03ContractError("ST03_UNAUTHORIZED_ACTIONABILITY")
    return ST03Receipt(
        status=verdict.status, source_coverage_status=audit.coverage_status,
        typed_identity_status=audit.identity_status,
        upstream_readiness=verdict.input_readiness,
        required_state_diagnostics={
            k: {"status": v[0],
                "latest_pre_timestamp_ms": str(v[1]) if v[1] is not None else "UNKNOWN"}
            for k, v in sorted(state_statuses.items())},
        source_gate_diagnostics=gate_diagnostics,
        excluded_same_timestamp_n=same, excluded_future_n=future,
        excluded_invalid_n=invalid, ledger_sha256=ledger["ledger_sha256"],
        provenance_class=ledger["provenance_class"])
