#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic observed-action evaluator for General Rotation rules.

This module deliberately owns no specialization semantics.  Action identity and
replacement semantics are supplied by the existing SpecAdapter contract.  State
is supplied by a strict-PRE provider, and readiness remains explicitly ternary.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


STRICT_PRE_CONTRACT = "latest valid transition timestamp < action timestamp"


class EvaluationStatus(str, Enum):
    RULE_APPLICABLE = "RULE_APPLICABLE"
    RULE_NOT_APPLICABLE = "RULE_NOT_APPLICABLE"
    ACTION_MATCH = "ACTION_MATCH"
    ACTION_MISMATCH = "ACTION_MISMATCH"
    ALTERNATIVE_ACCEPTABLE = "ALTERNATIVE_ACCEPTABLE"
    STATE_UNOBSERVABLE = "STATE_UNOBSERVABLE"
    READINESS_UNKNOWN = "READINESS_UNKNOWN"
    FIXTURE_INCOMPATIBLE = "FIXTURE_INCOMPATIBLE"
    EVALUATOR_ERROR = "EVALUATOR_ERROR"


class ObservationStatus(str, Enum):
    OBSERVED = "OBSERVED"
    UNKNOWN = "UNKNOWN"
    UNOBSERVABLE = "UNOBSERVABLE"


class ReadinessStatus(str, Enum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    UNKNOWN = "UNKNOWN"
    UNOBSERVABLE = "UNOBSERVABLE"


@dataclass(frozen=True)
class StateTransition:
    timestamp_ms: int
    key: str
    value: Any
    sequence: int = 0
    valid: bool = True


@dataclass(frozen=True)
class FeatureObservation:
    status: ObservationStatus
    value: Any = None
    source_timestamp_ms: int | None = None


@dataclass(frozen=True)
class StrictPreState:
    decision_timestamp_ms: int
    features: Mapping[str, FeatureObservation]
    state_timestamp_max_ms: int | None
    excluded_same_timestamp_n: int = 0
    excluded_future_n: int = 0
    invalid_transition_n: int = 0

    def validate(self) -> None:
        if self.state_timestamp_max_ms is not None and (
            self.state_timestamp_max_ms >= self.decision_timestamp_ms
        ):
            raise ValueError("STRICT_PRE_VIOLATION")


class StrictPreStateProvider:
    """Reconstruct state without same-timestamp or future leakage."""

    def build(
        self,
        *,
        action_timestamp_ms: int,
        transitions: Iterable[StateTransition],
        initial_values: Mapping[str, Any] | None = None,
        required_keys: Iterable[str] = (),
        unobservable_keys: Iterable[str] = (),
    ) -> StrictPreState:
        action_ts = int(action_timestamp_ms)
        unobservable = {str(key) for key in unobservable_keys}
        observations: dict[str, FeatureObservation] = {
            str(key): FeatureObservation(ObservationStatus.OBSERVED, value, None)
            for key, value in (initial_values or {}).items()
            if str(key) not in unobservable
        }
        same_n = 0
        future_n = 0
        invalid_n = 0
        applied_timestamps: list[int] = []

        ordered = sorted(
            transitions,
            key=lambda row: (int(row.timestamp_ms), int(row.sequence), str(row.key)),
        )
        for transition in ordered:
            ts = int(transition.timestamp_ms)
            if not transition.valid:
                invalid_n += 1
                continue
            if ts == action_ts:
                same_n += 1
                continue
            if ts > action_ts:
                future_n += 1
                continue
            key = str(transition.key)
            if key in unobservable:
                continue
            observations[key] = FeatureObservation(
                ObservationStatus.OBSERVED,
                transition.value,
                ts,
            )
            applied_timestamps.append(ts)

        for key in unobservable:
            observations[key] = FeatureObservation(ObservationStatus.UNOBSERVABLE)
        for raw_key in required_keys:
            key = str(raw_key)
            observations.setdefault(
                key,
                FeatureObservation(ObservationStatus.UNKNOWN),
            )

        state = StrictPreState(
            decision_timestamp_ms=action_ts,
            features=observations,
            state_timestamp_max_ms=max(applied_timestamps, default=None),
            excluded_same_timestamp_n=same_n,
            excluded_future_n=future_n,
            invalid_transition_n=invalid_n,
        )
        state.validate()
        return state


@dataclass(frozen=True)
class RuleCondition:
    key: str
    op: str
    value: Any = None


@dataclass(frozen=True)
class BehavioralRule:
    rule_id: str
    recommended_action: str | int
    conditions: tuple[RuleCondition, ...] = ()
    acceptable_alternatives: tuple[str | int, ...] = ()
    requires_recommended_ready: bool = True
    spec_slug: str | None = None
    build_key: str | None = None
    evidence_refs: tuple[str, ...] = ()
    hypothesis_source: str | None = None


@dataclass(frozen=True)
class FixtureObservation:
    fixture_id: str
    fixture_kind: str
    spec_slug: str
    build_key: str | None
    action_timestamp_ms: int
    actual_action: str | int
    strict_pre_state: StrictPreState
    readiness: Mapping[str, ReadinessStatus | str] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class BehavioralEvaluation:
    fixture_id: str
    rule_id: str
    statuses: tuple[EvaluationStatus, ...]
    actual_action_family: str | None = None
    recommended_action_family: str | None = None
    reason_code: str | None = None
    excluded_from_mismatch_denominator: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "rule_id": self.rule_id,
            "statuses": [status.value for status in self.statuses],
            "actual_action_family": self.actual_action_family,
            "recommended_action_family": self.recommended_action_family,
            "reason_code": self.reason_code,
            "excluded_from_mismatch_denominator": self.excluded_from_mismatch_denominator,
            "error": self.error,
        }


def _condition_value(condition: RuleCondition, actual: Any) -> bool:
    op = condition.op
    expected = condition.value
    if op == "truthy":
        return bool(actual)
    if op == "falsy":
        return not bool(actual)
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "gt":
        return actual > expected
    if op == "ge":
        return actual >= expected
    if op == "lt":
        return actual < expected
    if op == "le":
        return actual <= expected
    if op == "contains":
        return expected in actual
    if op == "not_contains":
        return expected not in actual
    raise ValueError("UNSUPPORTED_CONDITION_OP::" + str(op))


def _family_index(adapter: Any) -> tuple[dict[str, str], dict[int, str]]:
    by_key: dict[str, str] = {}
    by_id: dict[int, str] = {}
    for family in adapter.action_families():
        key = str(family.key)
        if not key or key in by_key:
            raise ValueError("INVALID_OR_DUPLICATE_ACTION_FAMILY::" + key)
        by_key[key] = key
        for raw_id in tuple(family.base_action_ids) + tuple(family.upgraded_action_ids):
            action_id = int(raw_id)
            prior = by_id.get(action_id)
            if prior is not None and prior != key:
                raise ValueError("AMBIGUOUS_ACTION_ID::" + str(action_id))
            by_id[action_id] = key
    return by_key, by_id


def normalize_action(adapter: Any, action: str | int) -> str | None:
    by_key, by_id = _family_index(adapter)
    if isinstance(action, bool):
        return None
    if isinstance(action, int):
        return by_id.get(action)
    token = str(action).strip()
    if token in by_key:
        return token
    try:
        return by_id.get(int(token))
    except ValueError:
        return None


class BehavioralEvaluator:
    """Compare one external rule with one observed action, fail-closed."""

    def evaluate(
        self,
        *,
        rule: BehavioralRule,
        fixture: FixtureObservation,
        adapter: Any,
    ) -> BehavioralEvaluation:
        try:
            return self._evaluate(rule=rule, fixture=fixture, adapter=adapter)
        except Exception as exc:  # contract errors become explicit data, not mismatches
            return BehavioralEvaluation(
                fixture_id=fixture.fixture_id,
                rule_id=rule.rule_id,
                statuses=(EvaluationStatus.EVALUATOR_ERROR,),
                reason_code="EVALUATOR_EXCEPTION",
                excluded_from_mismatch_denominator=True,
                error=type(exc).__name__ + "::" + str(exc),
            )

    def _evaluate(
        self,
        *,
        rule: BehavioralRule,
        fixture: FixtureObservation,
        adapter: Any,
    ) -> BehavioralEvaluation:
        state = fixture.strict_pre_state
        state.validate()
        if state.decision_timestamp_ms != int(fixture.action_timestamp_ms):
            return self._terminal(rule, fixture, EvaluationStatus.FIXTURE_INCOMPATIBLE, "TIMESTAMP_MISMATCH")
        if str(getattr(adapter, "spec_slug", "")) != fixture.spec_slug:
            return self._terminal(rule, fixture, EvaluationStatus.FIXTURE_INCOMPATIBLE, "ADAPTER_SPEC_MISMATCH")
        if rule.spec_slug is not None and rule.spec_slug != fixture.spec_slug:
            return self._terminal(rule, fixture, EvaluationStatus.FIXTURE_INCOMPATIBLE, "RULE_SPEC_MISMATCH")
        if rule.build_key is not None and rule.build_key != fixture.build_key:
            return self._terminal(rule, fixture, EvaluationStatus.FIXTURE_INCOMPATIBLE, "RULE_BUILD_MISMATCH")
        if str(rule.hypothesis_source or "").upper() == "SIMC_GROUND_TRUTH":
            return self._terminal(rule, fixture, EvaluationStatus.FIXTURE_INCOMPATIBLE, "SIMC_GROUND_TRUTH_FORBIDDEN")

        for condition in rule.conditions:
            observed = state.features.get(condition.key)
            if observed is None or observed.status in {
                ObservationStatus.UNKNOWN,
                ObservationStatus.UNOBSERVABLE,
            }:
                return self._terminal(rule, fixture, EvaluationStatus.STATE_UNOBSERVABLE, "CONDITION_STATE_UNAVAILABLE")
            if not _condition_value(condition, observed.value):
                return self._terminal(rule, fixture, EvaluationStatus.RULE_NOT_APPLICABLE, "CONDITION_FALSE")

        recommended = normalize_action(adapter, rule.recommended_action)
        actual = normalize_action(adapter, fixture.actual_action)
        alternatives = {
            normalized
            for normalized in (
                normalize_action(adapter, item)
                for item in rule.acceptable_alternatives
            )
            if normalized is not None
        }
        if recommended is None or actual is None:
            return self._terminal(rule, fixture, EvaluationStatus.FIXTURE_INCOMPATIBLE, "ACTION_NOT_IN_ADAPTER")

        if rule.requires_recommended_ready:
            raw = fixture.readiness.get(recommended, ReadinessStatus.UNKNOWN)
            try:
                readiness = raw if isinstance(raw, ReadinessStatus) else ReadinessStatus(str(raw))
            except ValueError:
                return self._terminal(rule, fixture, EvaluationStatus.FIXTURE_INCOMPATIBLE, "INVALID_READINESS_VALUE")
            if readiness in {ReadinessStatus.UNKNOWN, ReadinessStatus.UNOBSERVABLE}:
                return BehavioralEvaluation(
                    fixture_id=fixture.fixture_id,
                    rule_id=rule.rule_id,
                    statuses=(EvaluationStatus.READINESS_UNKNOWN,),
                    actual_action_family=actual,
                    recommended_action_family=recommended,
                    reason_code="RECOMMENDED_READINESS_UNKNOWN",
                    excluded_from_mismatch_denominator=True,
                )
            if readiness is ReadinessStatus.NOT_READY:
                return BehavioralEvaluation(
                    fixture_id=fixture.fixture_id,
                    rule_id=rule.rule_id,
                    statuses=(EvaluationStatus.RULE_NOT_APPLICABLE,),
                    actual_action_family=actual,
                    recommended_action_family=recommended,
                    reason_code="RECOMMENDED_ACTION_NOT_READY",
                    excluded_from_mismatch_denominator=True,
                )

        if actual == recommended:
            action_status = EvaluationStatus.ACTION_MATCH
        elif actual in alternatives:
            action_status = EvaluationStatus.ALTERNATIVE_ACCEPTABLE
        else:
            action_status = EvaluationStatus.ACTION_MISMATCH
        return BehavioralEvaluation(
            fixture_id=fixture.fixture_id,
            rule_id=rule.rule_id,
            statuses=(EvaluationStatus.RULE_APPLICABLE, action_status),
            actual_action_family=actual,
            recommended_action_family=recommended,
            reason_code=action_status.value,
            excluded_from_mismatch_denominator=False,
        )

    @staticmethod
    def _terminal(
        rule: BehavioralRule,
        fixture: FixtureObservation,
        status: EvaluationStatus,
        reason: str,
    ) -> BehavioralEvaluation:
        return BehavioralEvaluation(
            fixture_id=fixture.fixture_id,
            rule_id=rule.rule_id,
            statuses=(status,),
            reason_code=reason,
            excluded_from_mismatch_denominator=True,
        )


def summarize(
    results: Sequence[BehavioralEvaluation],
    *,
    fixture_kinds: Sequence[str],
) -> dict[str, Any]:
    counts = Counter(status.value for result in results for status in result.statuses)
    denominator = sum(1 for result in results if not result.excluded_from_mismatch_denominator)
    mismatch_n = counts[EvaluationStatus.ACTION_MISMATCH.value]
    kinds = {str(kind).upper() for kind in fixture_kinds}
    empirical_ran = bool(kinds) and kinds <= {"EMPIRICAL"}
    return {
        "case_n": len(results),
        "status_counts": {status.value: counts[status.value] for status in EvaluationStatus},
        "mismatch_denominator_n": denominator,
        "mismatch_n": mismatch_n,
        "unknown_or_unobservable_counted_as_mismatch": False,
        "strict_pre_contract": STRICT_PRE_CONTRACT,
        "synthetic_validation": "PASS" if kinds and kinds <= {"SYNTHETIC"} else "MIXED_OR_NOT_RUN",
        "empirical_validation": "PASS" if empirical_ran else "NOT_RUN",
        "authority_promotion": False,
        "general_rotation_ir_frozen": False,
        "general_rotation_baseline_mutated": False,
        "gameplay_rule_promotion": False,
    }

