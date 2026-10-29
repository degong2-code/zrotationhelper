#!/usr/bin/env python3
"""Reusable SimC hypothesis -> normalized WCL decision reconciler.

INPUTS: effective SimC APL hypothesis model + pinned APL text, pinned numeric
blind candidate-lock bytes, verified-by-caller identity mapping, normalized
WCL-shaped PRE transitions, and a SpecAdapter.

OUTPUTS: guarded MATCH_CANDIDATE, DIFFERENCE_CANDIDATE, or UNKNOWN. Never
optimality, a mandatory gameplay rule, or an independently verified lock.

This is a consumer of normalized WCL events; it does not fetch WCL or certify
independent discovery. Pass a current MAIN-approved input provider in production.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
from typing import Any, Iterable, Mapping

from post_lock_simc_wcl_guard_replay import _locked_numeric_actions
from simc_apl_priority_trace import CANDIDATE, trace_priority

@dataclass(frozen=True)
class ReplayIdentity:
    """Pinned source/build identity for a reproducible WCL replay cohort."""
    simc_spec: str
    adapter_spec_slug: str
    build_key: str
    profile_sha256: str
    apl_sha256: str
    blind_lock_sha256: str


@dataclass(frozen=True)
class NormalizedWclDecision:
    """An external collector's normalized *cast* and strictly-timed transitions.

    This structure itself does not prove the data was collected from WCL.
    """
    case_id: str
    adapter_spec_slug: str
    build_key: str
    cast_timestamp_ms: int
    observed_spell_id: int
    cast_scope: str
    transitions: tuple[StateTransition, ...]
    unobservable_keys: tuple[str, ...] = ()


class SimcWclReconciler:
    def __init__(self, *, source_model: Mapping[str, Any],
                 effective_apl_text: str, identity: ReplayIdentity,
                 blind_lock_bytes: bytes,
                 apl_token_to_numeric_spell_id: Mapping[str, int],
                 operand_to_pre_feature: Mapping[str, str],
                 spec_adapter: Any):
        self.model = source_model
        self.identity = identity
        self.adapter = spec_adapter
        self.operand_map = dict(operand_to_pre_feature)
        self.action_map = dict(apl_token_to_numeric_spell_id)
        if identity.adapter_spec_slug != getattr(spec_adapter, "spec_slug", None):
            raise ValueError("SPEC_ADAPTER_IDENTITY_MISMATCH")
        if identity.simc_spec != source_model.get("expected_spec"):
            raise ValueError("SIMC_SPEC_IDENTITY_MISMATCH")
        if identity.profile_sha256 != source_model.get("profile_sha256"):
            raise ValueError("PROFILE_IDENTITY_MISMATCH")
        if identity.apl_sha256 != source_model.get("apl_sha256"):
            raise ValueError("APL_IDENTITY_MISMATCH")
        if hashlib.sha256(effective_apl_text.encode("utf-8")).hexdigest() != identity.apl_sha256:
            raise ValueError("APL_SOURCE_BYTES_MISMATCH")
        if source_model.get("profile_spec_verified") is not True:
            raise ValueError("PROFILE_SPEC_UNVERIFIED")
        if source_model.get("profile_dependencies_verified") is not True:
            raise ValueError("PROFILE_DEPENDENCIES_UNVERIFIED")
        if source_model.get("actionable_general_rotation") is not False:
            raise ValueError("SOURCE_PROMOTED_PREMATURELY")
        if not identity.build_key or not identity.profile_sha256:
            raise ValueError("BUILD_OR_PROFILE_REQUIRED")
        self.locked_actions = _locked_numeric_actions(
            blind_lock_bytes, identity.blind_lock_sha256)
        if not self.action_map:
            raise ValueError("EMPTY_NUMERIC_ACTION_MAP")
        for token, numeric in self.action_map.items():
            if not token or type(numeric) is not int or numeric <= 0:
                raise ValueError("INVALID_ACTION_NUMERIC_MAP")

    def _ready(self, state):
        from raid_dps.core.behavioral_evaluator import ObservationStatus
        """Only explicitly observed PRE readiness; never guess from cooldown."""
        ready = {}
        for token in self.action_map:
            obs = state.features.get("readiness::" + token)
            if obs is None or obs.status is not ObservationStatus.OBSERVED:
                continue
            if obs.source_timestamp_ms is None:
                # No measured provenance -> no readiness claim.
                continue
            if obs.source_timestamp_ms >= state.decision_timestamp_ms:
                raise ValueError("READINESS_PRE_PROVENANCE_VIOLATION")
            if obs.value in ("READY", "NOT_READY", "UNKNOWN", "UNOBSERVABLE"):
                ready[token] = obs.value
        return ready

    def evaluate(self, row: NormalizedWclDecision):
        from raid_dps.core.behavioral_evaluator import StrictPreStateProvider, normalize_action
        base = {
            "case_id": row.case_id,
            "schema": "ZrotSimcWclDecisionReconciliationResearchV1",
            "source_apl_sha256": self.identity.apl_sha256,
            "blind_lock_sha256": self.identity.blind_lock_sha256,
            "independent_blind_lock_provenance": "UNVERIFIED",
            "WCL_source_provenance": "UNVERIFIED",
            "empirical_validation": "NOT_RUN",
            "authority_promotion": False,
        }

        def out(category, reason, *, token=None, predicted_id=None, trace=None):
            return {
                **base, "category": category, "reason": reason,
                "observed_spell_id": row.observed_spell_id,
                "simc_candidate_token": token,
                "simc_candidate_spell_id": predicted_id,
                "apl_trace_status": getattr(trace, "status", None),
                "apl_trace_reason": getattr(trace, "reason", None),
                "comparable": category in ("MATCH_CANDIDATE", "DIFFERENCE_CANDIDATE"),
                "gameplay_rule_promotion": False,
            }

        if not row.case_id:
            raise ValueError("DECISION_CASE_ID_REQUIRED")
        if row.adapter_spec_slug != self.identity.adapter_spec_slug:
            return out("EXCLUDED", "SPEC_MISMATCH")
        if row.build_key != self.identity.build_key:
            return out("EXCLUDED", "BUILD_MISMATCH")
        if row.cast_scope != "COMPARABLE_GCD_CAST":
            return out("EXCLUDED", "CAST_SCOPE_NOT_COMPARABLE")
        if type(row.cast_timestamp_ms) is not int or row.cast_timestamp_ms <= 0:
            raise ValueError("INVALID_DECISION_TIMESTAMP")
        if type(row.observed_spell_id) is not int or row.observed_spell_id <= 0:
            raise ValueError("INVALID_OBSERVED_SPELL_ID")
        if row.observed_spell_id not in self.locked_actions:
            return out("EXCLUDED", "OBSERVED_ACTION_NOT_BLIND_LOCKED")
        state = StrictPreStateProvider().build(
            action_timestamp_ms=row.cast_timestamp_ms,
            transitions=row.transitions,
            unobservable_keys=row.unobservable_keys,
        )
        ready = self._ready(state)
        trace = trace_priority(
            self.model, strict_pre_state=state,
            spec_slug=self.identity.simc_spec,
            operand_to_feature=self.operand_map,
            action_readiness=ready,
            expected_apl_sha256=self.identity.apl_sha256,
            expected_profile_sha256=self.identity.profile_sha256,
        )
        if trace.status != CANDIDATE:
            return out("UNKNOWN", "SIMC_APL_" + trace.reason, trace=trace)
        token = trace.candidate_action_token
        predicted_id = self.action_map.get(token)
        if predicted_id is None:
            return out("UNKNOWN", "SIMC_CANDIDATE_UNMAPPED", token=token, trace=trace)
        predicted_family = normalize_action(self.adapter, predicted_id)
        observed_family = normalize_action(self.adapter, row.observed_spell_id)
        if predicted_family is None or observed_family is None:
            return out("UNKNOWN", "ACTION_FAMILY_IDENTITY_UNVERIFIED",
                       token=token, predicted_id=predicted_id, trace=trace)
        if predicted_family == observed_family:
            return out("MATCH_CANDIDATE", "SAME_ACTION_FAMILY_NOT_VALIDATED",
                       token=token, predicted_id=predicted_id, trace=trace)
        return out("DIFFERENCE_CANDIDATE", "DIFFERENT_ACTION_FAMILY_NOT_CAUSAL",
                   token=token, predicted_id=predicted_id, trace=trace)

    def evaluate_many(self, rows: Iterable[NormalizedWclDecision]):
        """Batch over any spec/build-matched normalized cohort; no hardcoded size."""
        decisions = [self.evaluate(row) for row in rows]
        category_counts = Counter(r["category"] for r in decisions)
        comparable = sum(r["comparable"] for r in decisions)
        return {
            "schema": "ZrotSimcWclBatchReconciliationResearchV1",
            "cases": decisions,
            "input_count": len(decisions),
            "category_counts": dict(category_counts),
            "comparable_candidate_n": comparable,
            "difference_candidate_n": category_counts["DIFFERENCE_CANDIDATE"],
            "unresolved_n": category_counts["UNKNOWN"] + category_counts["EXCLUDED"],
            "blind_discovery_certification": "NOT_RUN",
            "actual_wcl_api_validation": "NOT_RUN",
            "gameplay_priority_validation": "NOT_RUN",
            "authority_promotion": False,
        }


def selftest():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '02_SOURCE' / 'runtime'))
    from raid_dps.core.behavioral_evaluator import StateTransition
    from raid_dps.specs.enhancement_shaman import ADAPTER as adapter
    from simc_apl_source_engine import ingest_actions
    import json
    profile = "spec=enhancement\n" \
              "actions=lightning_bolt,if=buff.foo.stack>=5\n" \
              "actions+=/stormstrike\n"
    h = hashlib.sha256(profile.encode()).hexdigest()
    profile_pin = "b" * 64
    model = ingest_actions(
        profile.encode(), expected_spec="enhancement",
        profile_spec="enhancement", profile_sha256=profile_pin,
        profile_dependencies_verified=True,
    )
    lock = {
        "schema":"ZrotWave3NumericCandidateLock",
        "status":"LOCKED_NUMERIC_ONLY",
        "candidate_n":2,
        "candidates":[{"action_spell_id":188196},{"action_spell_id":17364}],
        "semantic_names_attached":False, "gameplay_rule_claim":False,
        "threshold_retuned_after_discovery":False,
    }
    locked = json.dumps(lock, sort_keys=True).encode()
    identity = ReplayIdentity(
        simc_spec="enhancement", adapter_spec_slug=adapter.spec_slug,
        build_key="test_build", profile_sha256=profile_pin,
        apl_sha256=h, blind_lock_sha256=hashlib.sha256(locked).hexdigest(),
    )
    engine = SimcWclReconciler(
        source_model=model, effective_apl_text=profile, identity=identity,
        blind_lock_bytes=locked,
        apl_token_to_numeric_spell_id={
            "lightning_bolt":188196, "stormstrike":17364,
        },
        operand_to_pre_feature={"buff.foo.stack":"stack"},
        spec_adapter=adapter,
    )

    def fixture(case_id, observed_spell, *, stack=None,
                ready=None, timestamp=1000, build="test_build",
                scope="COMPARABLE_GCD_CAST"):
        events = []
        if stack is not None:
            events.append(StateTransition(timestamp-50, "stack", stack))
        if ready is not None:
            events.append(StateTransition(timestamp-40,
                            "readiness::lightning_bolt", ready))
        events.append(StateTransition(timestamp, "stack", 0))
        events.append(StateTransition(timestamp+20, "stack", 9))
        return NormalizedWclDecision(
            case_id=case_id, adapter_spec_slug=adapter.spec_slug,
            build_key=build, cast_timestamp_ms=timestamp,
            observed_spell_id=observed_spell, cast_scope=scope,
            transitions=tuple(events),
        )

    # Match with explicit PRE readiness.
    a = engine.evaluate(fixture("match", 188196, stack=5, ready="READY"))
    assert a["category"] == "MATCH_CANDIDATE", a
    # Different family -> tentative discrepancy only (never optimality).
    b = engine.evaluate(fixture("difference", 17364, stack=5, ready="READY"))
    assert b["category"] == "DIFFERENCE_CANDIDATE", b
    # Without observed readiness, high-priority SimC action is indeterminate.
    c = engine.evaluate(fixture("unknown_readiness", 17364, stack=5))
    assert c["category"] == "UNKNOWN" and "READINESS_UNKNOWN" in c["reason"], c
    # Missing operand is UNKNOWN, not false/fallback.
    d = engine.evaluate(fixture("missing_state", 17364, ready="READY"))
    assert d["category"] == "UNKNOWN" and "GUARD_UNKNOWN" in d["reason"], d
    e = engine.evaluate(fixture("build_mismatch", 17364, stack=5,
                                ready="READY", build="other"))
    assert e["category"] == "EXCLUDED"
    f = engine.evaluate(fixture("non_gcd", 17364, stack=5,
                                ready="READY", scope="NON_GCD"))
    assert f["category"] == "EXCLUDED"
    # Same-family upgraded action is an action-family match, not an ID mismatch.
    g = engine.evaluate(fixture("replacement", 452201, stack=5, ready="READY"))
    assert g["category"] == "EXCLUDED"  # not in numeric blind lock
    total = engine.evaluate_many([fixture("match", 188196, stack=5, ready="READY"),
                                  fixture("difference", 17364, stack=5, ready="READY"),
                                  fixture("unknown", 17364, stack=5)])
    assert total["input_count"] == 3 and total["comparable_candidate_n"] == 2
    assert total["difference_candidate_n"] == 1 and total["unresolved_n"] == 1
    assert total["authority_promotion"] is False
    # A valid looking SHA flag must not substitute independent WCL provenance.
    assert total["blind_discovery_certification"] == "NOT_RUN"
    print("SIMC_WCL_BATCH_RECONCILIATION_SELF_TEST=PASS")


if __name__ == "__main__":
    selftest()
