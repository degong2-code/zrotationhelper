# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


STRICT_PRE_CONTRACT = "state_timestamp_max_ms < decision_timestamp_ms"
PRIORITY_CONTRACT = "lower_integer_is_higher_priority"


class EvaluationContractError(ValueError):
    """Raised when a decision state or rule violates the evaluator contract."""


@dataclass(frozen=True)
class DecisionState:
    decision_timestamp_ms: int
    state_timestamp_max_ms: int | None
    values: Mapping[str, Any]
    spec_key: str | None = None
    build_key: str | None = None

    def validate_strict_pre(self) -> None:
        if self.state_timestamp_max_ms is None:
            return
        if self.state_timestamp_max_ms >= self.decision_timestamp_ms:
            raise EvaluationContractError(
                "STRICT_PRE_VIOLATION::"
                f"state_timestamp_max_ms={self.state_timestamp_max_ms}::"
                f"decision_timestamp_ms={self.decision_timestamp_ms}"
            )

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)


@dataclass(frozen=True)
class RuleCondition:
    key: str
    op: str
    value: Any = None

    def evaluate(self, state: DecisionState) -> bool:
        actual = state.get(self.key)

        if self.op == "truthy":
            return bool(actual)
        if self.op == "falsy":
            return not bool(actual)
        if self.op == "eq":
            return actual == self.value
        if self.op == "ne":
            return actual != self.value
        if self.op == "gt":
            return actual is not None and actual > self.value
        if self.op == "ge":
            return actual is not None and actual >= self.value
        if self.op == "lt":
            return actual is not None and actual < self.value
        if self.op == "le":
            return actual is not None and actual <= self.value
        if self.op == "contains":
            try:
                return self.value in actual
            except (TypeError, AttributeError):
                return False
        if self.op == "not_contains":
            try:
                return self.value not in actual
            except (TypeError, AttributeError):
                return True

        raise EvaluationContractError(f"UNSUPPORTED_CONDITION_OP::{self.op}")


@dataclass(frozen=True)
class RotationRule:
    rule_id: str
    priority: int
    recommended_action: str
    conditions: tuple[RuleCondition, ...] = ()
    alternative_action: str | None = None
    confidence: str | None = None
    evidence: tuple[str, ...] = ()
    observability_limitation: str | None = None
    reason: str | None = None

    def matches(self, state: DecisionState) -> bool:
        return all(condition.evaluate(state) for condition in self.conditions)


@dataclass(frozen=True)
class Recommendation:
    rule_id: str
    recommended_action: str
    priority: int
    alternative_action: str | None
    confidence: str | None
    evidence: tuple[str, ...]
    observability_limitation: str | None
    reason: str | None
    matched_conditions: tuple[RuleCondition, ...]
    decision_timestamp_ms: int
    spec_key: str | None
    build_key: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "recommended_action": self.recommended_action,
            "priority": self.priority,
            "alternative_action": self.alternative_action,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "observability_limitation": self.observability_limitation,
            "reason": self.reason,
            "matched_conditions": [
                {"key": c.key, "op": c.op, "value": c.value}
                for c in self.matched_conditions
            ],
            "decision_timestamp_ms": self.decision_timestamp_ms,
            "spec_key": self.spec_key,
            "build_key": self.build_key,
        }


@dataclass(frozen=True)
class EvaluationResult:
    recommendation: Recommendation | None
    evaluated_rule_ids: tuple[str, ...]
    rejected_rule_ids: tuple[str, ...]
    strict_pre_contract: str = STRICT_PRE_CONTRACT
    priority_contract: str = PRIORITY_CONTRACT

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation": (
                self.recommendation.to_dict()
                if self.recommendation is not None
                else None
            ),
            "evaluated_rule_ids": list(self.evaluated_rule_ids),
            "rejected_rule_ids": list(self.rejected_rule_ids),
            "strict_pre_contract": self.strict_pre_contract,
            "priority_contract": self.priority_contract,
        }


class GeneralRotationEvaluator:
    """Generic state -> recommendation evaluator.

    This class deliberately does not:
    - reconstruct combat state,
    - infer readiness,
    - contain specialization-specific mechanics,
    - claim optimality,
    - read network/WCL/SimC data.

    It only evaluates already-defined rules against an already-reconstructed
    strict-PRE decision state.
    """

    def evaluate(
        self,
        state: DecisionState,
        rules: Sequence[RotationRule],
    ) -> EvaluationResult:
        state.validate_strict_pre()

        ordered = sorted(
            rules,
            key=lambda rule: (rule.priority, rule.rule_id),
        )
        evaluated: list[str] = []
        rejected: list[str] = []

        for rule in ordered:
            evaluated.append(rule.rule_id)
            if not rule.matches(state):
                rejected.append(rule.rule_id)
                continue

            recommendation = Recommendation(
                rule_id=rule.rule_id,
                recommended_action=rule.recommended_action,
                priority=rule.priority,
                alternative_action=rule.alternative_action,
                confidence=rule.confidence,
                evidence=rule.evidence,
                observability_limitation=rule.observability_limitation,
                reason=rule.reason,
                matched_conditions=rule.conditions,
                decision_timestamp_ms=state.decision_timestamp_ms,
                spec_key=state.spec_key,
                build_key=state.build_key,
            )
            return EvaluationResult(
                recommendation=recommendation,
                evaluated_rule_ids=tuple(evaluated),
                rejected_rule_ids=tuple(rejected),
            )

        return EvaluationResult(
            recommendation=None,
            evaluated_rule_ids=tuple(evaluated),
            rejected_rule_ids=tuple(rejected),
        )


def synthetic_regression() -> dict[str, Any]:
    evaluator = GeneralRotationEvaluator()

    shared_rules = (
        RotationRule(
            rule_id="high_resource_proc",
            priority=10,
            recommended_action="spender_a",
            conditions=(
                RuleCondition("resource", "ge", 5),
                RuleCondition("proc", "truthy"),
            ),
            alternative_action="builder",
            confidence="SYNTHETIC",
            evidence=("synthetic_fixture",),
            reason="resource_and_proc",
        ),
        RotationRule(
            rule_id="multi_target",
            priority=20,
            recommended_action="cleave_a",
            conditions=(RuleCondition("targets", "ge", 3),),
            confidence="SYNTHETIC",
            evidence=("synthetic_fixture",),
            reason="target_count",
        ),
        RotationRule(
            rule_id="fallback",
            priority=100,
            recommended_action="builder",
            conditions=(),
            confidence="SYNTHETIC",
            evidence=("synthetic_fixture",),
            reason="fallback",
        ),
    )

    ref_state = DecisionState(
        decision_timestamp_ms=1000,
        state_timestamp_max_ms=999,
        values={"resource": 5, "proc": True, "targets": 1},
        spec_key="synthetic_reference",
        build_key="build_a",
    )
    contrast_state = DecisionState(
        decision_timestamp_ms=1000,
        state_timestamp_max_ms=999,
        values={"resource": 0, "proc": False, "targets": 4},
        spec_key="synthetic_contrast",
        build_key="build_b",
    )
    fallback_state = DecisionState(
        decision_timestamp_ms=1000,
        state_timestamp_max_ms=999,
        values={"resource": 0, "proc": False, "targets": 1},
        spec_key="synthetic_contrast",
        build_key="build_b",
    )

    ref = evaluator.evaluate(ref_state, shared_rules)
    contrast = evaluator.evaluate(contrast_state, shared_rules)
    fallback = evaluator.evaluate(fallback_state, shared_rules)

    strict_pre_rejected = False
    try:
        evaluator.evaluate(
            DecisionState(
                decision_timestamp_ms=1000,
                state_timestamp_max_ms=1000,
                values={"resource": 10, "proc": True, "targets": 1},
            ),
            shared_rules,
        )
    except EvaluationContractError:
        strict_pre_rejected = True

    deterministic_a = evaluator.evaluate(ref_state, shared_rules).to_dict()
    deterministic_b = evaluator.evaluate(ref_state, shared_rules).to_dict()

    checks = {
        "reference_action": (
            ref.recommendation is not None
            and ref.recommendation.recommended_action == "spender_a"
        ),
        "contrast_action": (
            contrast.recommendation is not None
            and contrast.recommendation.recommended_action == "cleave_a"
        ),
        "fallback_action": (
            fallback.recommendation is not None
            and fallback.recommendation.recommended_action == "builder"
        ),
        "strict_pre_rejects_same_timestamp": strict_pre_rejected,
        "deterministic": deterministic_a == deterministic_b,
        "priority_order": (
            ref.evaluated_rule_ids
            and ref.evaluated_rule_ids[0] == "high_resource_proc"
        ),
        "ir_serializable_shape": (
            ref.to_dict()["recommendation"]["recommended_action"]
            == "spender_a"
        ),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "reference": ref.to_dict(),
        "contrast": contrast.to_dict(),
        "fallback": fallback.to_dict(),
    }
