#!/usr/bin/env python3
"""Research-only readiness *coverage* audit, NOT a readiness engine.

Demonstrates the existing eight-dimension provider's declaration-completeness
gap using synthetic Strict PRE, and audits a separate pinned source obligation
inventory without granting READY, selected-action, or gameplay authority.
No spec-specific conditions in this module; all source obligations are data.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "BR_SIMC_MINIMUM_READINESS_SOURCE_GAP_20261031.json"
sys.path.insert(0, str(ROOT / "02_SOURCE" / "runtime"))
from raid_dps.core.behavioral_evaluator import StrictPreStateProvider, StateTransition
from simc_apl_readiness_provider import derive_readiness, MANDATORY

MANIFEST_SCHEMA = "ZrotBranchSimcReadinessSourceGapV1"
AUDIT_SCHEMA = "ZrotResearchReadinessCoverageAuditV1"


def source_gates(manifest: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """Return external source-declared specialization obligations only."""
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("SOURCE_GAP_SCHEMA_MISMATCH")
    if manifest.get("owner") != "BR-SIMC-APL-BOOTSTRAP":
        raise ValueError("SOURCE_GAP_OWNER_MISMATCH")
    if (manifest.get("authority") != "SOURCE_PINNED_BRANCH_HYPOTHESIS_ONLY"
        or manifest.get("user_if_else_promotion") is not False
        or manifest.get("readiness_outcome") != "UNKNOWN"):
        raise ValueError("SOURCE_GAP_UNAUTHORIZED_READINESS_CLAIM")
    if tuple(manifest.get("provider_mandatory_dimensions", ())) != MANDATORY:
        raise ValueError("SOURCE_GAP_COMMON_PROVIDER_DIMENSIONS_DRIFT")
    if not manifest.get("provider_rejects_undeclared_dimensions"):
        raise ValueError("SOURCE_GAP_PROVIDER_BEHAVIOR_DRIFT")
    items = manifest.get("candidate_actions")
    if not isinstance(items, list) or not items:
        raise ValueError("SOURCE_GAP_EMPTY_ACTIONS")
    result: dict[str, tuple[str, ...]] = {}
    for item in items:
        key = item.get("spec", "") + "/" + item.get("action", "")
        if (key in result or "/" not in key or key.startswith("/")
            or key.endswith("/") or not item.get("effective_apl_sha256")):
            raise ValueError("SOURCE_GAP_ACTION_IDENTITY_INVALID")
        extras = item.get("extra_source_obligations")
        if not isinstance(extras, list) or not extras:
            raise ValueError("SOURCE_GAP_MISSING_EXTRA_SOURCE_OBLIGATIONS")
        names: list[str] = []
        for entry in extras:
            name = entry.get("id")
            if (not isinstance(name, str) or not name
                or not entry.get("source_symbol")
                or not entry.get("source_truth")
                or entry.get("live_status") != "UNKNOWN"
                or not isinstance(entry.get("required_state"), list)
                or not entry["required_state"]
                or not all(isinstance(x, str) and x for x in entry["required_state"])):
                raise ValueError("SOURCE_GAP_UNSUPPORTED_OR_INCOMPLETE_GATE")
            if name in names:
                raise ValueError("SOURCE_GAP_DUPLICATE_GATE")
            names.append(name)
        result[key] = tuple(names)
    return result


def audit_coverage(manifest: dict[str, Any], declarations: dict[str, Any]) -> dict[str, Any]:
    """Check full source gate declaration WITHOUT evaluating action readiness.

    Declarations merely show intent to observe and validate gates, not
    satisfaction or actual game-mechanic agreement. A READY claim is forbidden.
    """
    expected = source_gates(manifest)
    if declarations.get("schema") != "ZrotReadinessCoverageDeclarationProposalV1":
        raise ValueError("COVERAGE_DECLARATION_SCHEMA")
    if declarations.get("source_sha256") != hashlib.sha256(
        (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest():
        raise ValueError("COVERAGE_SOURCE_CANONICAL_PIN_MISMATCH")
    if (declarations.get("hypothesis_only") is not True
        or declarations.get("ready_claim") is not False):
        raise ValueError("COVERAGE_PRODUCTION_READINESS_FORBIDDEN")
    entries = declarations.get("actions")
    if not isinstance(entries, dict) or set(entries) != set(expected):
        raise ValueError("COVERAGE_ACTION_SET_MISMATCH")
    outcomes = {}
    for key, needed in expected.items():
        row = entries[key]
        if not isinstance(row, dict):
            raise ValueError("COVERAGE_ACTION_NOT_OBJECT")
        actual = row.get("declared_gate_ids")
        if (not isinstance(actual, list)
            or any(not isinstance(v, str) for v in actual)
            or len(actual) != len(set(actual))):
            raise ValueError("COVERAGE_BAD_DECLARED_IDS")
        if set(actual) - set(needed):
            raise ValueError("COVERAGE_UNAUTHORIZED_EXTRA_GATE_ID")
        missing = sorted(set(needed) - set(actual))
        outcomes[key] = {
            "status": "BLOCKED_MISSING_SOURCE_GATES" if missing
                      else "DECLARED_ONLY_LIVE_READINESS_STILL_UNKNOWN",
            "required_gate_ids": list(needed),
            "undeclared_gate_ids": missing,
            "ready_certified": False,
        }
    return {
        "schema": AUDIT_SCHEMA,
        "source_only": True,
        "provider_contract_modified": False,
        "actions": outcomes,
        "ready_certified": 0,
        "gameplay_rule_promotion": False,
        "wcl_blind_discovery": "NOT_RUN",
    }


def _canonical_source_hash(obj: dict[str, Any]) -> str:
    return hashlib.sha256(
        (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()


def _provider_gap_synthetic() -> dict[str, str]:
    """Use actual current provider; no mocks of its readiness logic."""
    signature = "f" * 64
    spec = "synthetic_spec"
    policy = {
        "schema": "ZrotGenericReadinessRequirementsV1",
        "spec_slug": spec, "build_key": "synthetic_build",
        "apl_sha256": signature, "hypothesis_only": True,
        "actions": {
            "synthetic_action": {
                "evidence_ref": "SYNTHETIC_DECLARED_ONLY",
                "dimensions": {key: {
                    "mode": "ALL",
                    "predicates": [{"feature": "core." + key, "op": "eq", "value": 1}],
                } for key in MANDATORY},
            }
        },
    }
    def state(extra: tuple[tuple[int, str, int], ...] = ()):
        events = [StateTransition(900, "core." + dim, 1) for dim in MANDATORY]
        events.extend(StateTransition(t, k, v) for t, k, v in extra)
        return StrictPreStateProvider().build(
            action_timestamp_ms=1000, transitions=events
        )
    kwargs = {"spec_slug": spec, "build_key": "synthetic_build",
              "apl_sha256": signature}
    bare = derive_readiness(policy, state(), **kwargs)["synthetic_action"]
    assert bare.status == "READY" and bare.empirical_authority == "NOT_VERIFIED"
    # This READY cannot account for an actual source-required additional
    # cooldown, equipment restriction, dynamic cost or movement gate.
    extra_dim = copy.deepcopy(policy)
    extra_dim["actions"]["synthetic_action"]["dimensions"]["equipment"] = {
        "mode": "ALL", "predicates": [
            {"feature": "external.equipment", "op": "eq", "value": 1}
        ]
    }
    try:
        derive_readiness(extra_dim, state(), **kwargs)
    except ValueError as e:
        assert str(e) == "UNRECOGNIZED_READINESS_DIMENSION"
    else:
        raise AssertionError("UNDECLARED_NINTH_DIMENSION_ACCEPTED")

    # Existing categories can represent SOME extra source gates if explicitly
    # declared within one existing dimension. This does not prove completeness
    # of source-gate coverage, full resource semantics, or optimality.
    folded = copy.deepcopy(policy)
    folded["actions"]["synthetic_action"]["dimensions"]["cooldown_or_charge"][
        "predicates"
    ].append({"feature": "source.required_shared_cd", "op": "eq", "value": 1})
    missing = derive_readiness(folded, state(), **kwargs)["synthetic_action"]
    blocked = derive_readiness(folded, state(((910, "source.required_shared_cd", 0),)),
                               **kwargs)["synthetic_action"]
    observed = derive_readiness(folded, state(((910, "source.required_shared_cd", 1),)),
                                **kwargs)["synthetic_action"]
    same_time = derive_readiness(folded, state(((1000, "source.required_shared_cd", 1),)),
                                 **kwargs)["synthetic_action"]
    assert (missing.status, blocked.status, observed.status, same_time.status) == (
        "UNKNOWN", "NOT_READY", "READY", "UNKNOWN"
    )
    # The provider's comparator only accepts constant numeric values.
    feature_compare = copy.deepcopy(policy)
    feature_compare["actions"]["synthetic_action"]["dimensions"]["resource"][
        "predicates"
    ] = [{"feature": "rage", "op": "ge", "value": "dynamic_cost"}]
    try:
        derive_readiness(feature_compare, state(), **kwargs)
    except ValueError as e:
        assert str(e) == "INVALID_READINESS_PREDICATE"
    else:
        raise AssertionError("UNSUPPORTED_FEATURE_TO_FEATURE_COMPARISON_ACCEPTED")

    return {
        "eight_declared_only": "READY_DESPITE_UNDECLARED_SOURCE_GATES",
        "ninth_key": "UNRECOGNIZED_READINESS_DIMENSION",
        "folded_extra_missing": missing.status,
        "folded_extra_false": blocked.status,
        "folded_extra_true": observed.status + "_RESEARCH_UNVERIFIED",
        "folded_extra_same_time": same_time.status,
        "dynamic_feature_comparator": "INVALID_READINESS_PREDICATE",
    }


def selftest() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual = source_gates(manifest)
    assert len(actual) >= 2 and all(len(x) >= 1 for x in actual.values())
    source_hash = _canonical_source_hash(manifest)
    claim = {
        "schema": "ZrotReadinessCoverageDeclarationProposalV1",
        "source_sha256": source_hash, "hypothesis_only": True,
        "ready_claim": False,
        "actions": {k: {"declared_gate_ids": []} for k in actual},
    }
    empty = audit_coverage(manifest, claim)
    assert all(x["status"] == "BLOCKED_MISSING_SOURCE_GATES"
               for x in empty["actions"].values())
    complete = copy.deepcopy(claim)
    complete["actions"] = {k: {"declared_gate_ids": list(v)}
                           for k, v in actual.items()}
    ok = audit_coverage(manifest, complete)
    assert all(x["status"] == "DECLARED_ONLY_LIVE_READINESS_STILL_UNKNOWN"
               for x in ok["actions"].values())
    assert ok["ready_certified"] == 0
    for mutation in (
        lambda p: p.update(ready_claim=True),
        lambda p: p.update(source_sha256="0" * 64),
        lambda p: p["actions"][next(iter(p["actions"]))]["declared_gate_ids"].append(
            "unsubstantiated_source_gate"
        ),
    ):
        tampered = copy.deepcopy(complete)
        mutation(tampered)
        try:
            audit_coverage(manifest, tampered)
        except ValueError:
            pass
        else:
            raise AssertionError("SOURCE_COVERAGE_MUTATION_ACCEPTED")
    source_bad = copy.deepcopy(manifest)
    source_bad["candidate_actions"][0]["extra_source_obligations"][0][
        "live_status"
    ] = "READY"
    try:
        source_gates(source_bad)
    except ValueError:
        pass
    else:
        raise AssertionError("SOURCE_DECLARED_READY_ACCEPTED")
    gap = _provider_gap_synthetic()
    print("SIMC_READINESS_SOURCE_COVERAGE_COMPAT_SELF_TEST=PASS")
    print(json.dumps({
        "schema": AUDIT_SCHEMA,
        "source_manifest_sha256_canonical": source_hash,
        "source_gate_count_by_action": {k: len(v) for k, v in actual.items()},
        "provider_probe": gap,
        "ready_certified": 0,
        "gameplay_rule_promotion": False,
        "actual_wcl_or_retail_validation": "NOT_RUN",
    }, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    selftest()
