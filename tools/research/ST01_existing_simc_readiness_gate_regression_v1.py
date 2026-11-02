#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ST-01: isolated, offline SimC readiness -> source-obligation gate regression.

This shadow-only adapter imports the two UNMODIFIED upstream modules from this
script's directory. It calls the real SimC ``derive_readiness`` and passes its
real ``ReadinessVerdict`` instance into the original gate shim. No source
mechanics, live IDs, WCL blind discoveries, actions or gameplay recommendations
are inferred. Default invocation runs focused synthetic integration regression.

Never place this module in the independent WCL blind-discovery data path.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import importlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

DIR = Path(__file__).resolve().parent
GATE_SHA256 = "8477da762da67c94569b37728ecc5122a68399476789ae93e25e40c66773c7e7"
PROVIDER_GIT_BLOB_SHA1 = "e59d2ea46455fc3e764daddd0abc3a8b6cce4c0c"
PINNED_REPO_COMMIT = "bfe86b00d044f918d4e5399f39f2c44900574f20"
HEX64 = re.compile(r"[a-f0-9]{64}\Z")


class IntegrationError(ValueError):
    """A failed interface/identity check, never a user-facing rotation verdict."""


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_upstreams():
    """Fail closed if source bytes differ from the two recorded immutable inputs."""
    gate_path = DIR / "ZROT_Source_Obligation_Gate_v1.py"
    provider_path = DIR / "simc_apl_readiness_provider.py"
    if not gate_path.is_file() or not provider_path.is_file():
        raise IntegrationError("PINNED_UPSTREAM_FILE_MISSING")
    if hashlib.sha256(gate_path.read_bytes()).hexdigest() != GATE_SHA256:
        raise IntegrationError("SOURCE_GATE_SHA256_MISMATCH")
    if _git_blob_sha1(provider_path.read_bytes()) != PROVIDER_GIT_BLOB_SHA1:
        raise IntegrationError("SIMC_PROVIDER_GIT_BLOB_MISMATCH")
    gate = importlib.import_module("ZROT_Source_Obligation_Gate_v1")
    provider = importlib.import_module("simc_apl_readiness_provider")
    if getattr(gate, "PHASE", None) != "POST_SIMC_HYPOTHESIS_RESEARCH_ONLY":
        raise IntegrationError("SOURCE_GATE_RESEARCH_PHASE_MISMATCH")
    return provider, gate


def assess_from_actual_provider(
    *, readiness_contract: Mapping[str, Any], pre_state: object,
    binding: Mapping[str, Any], source_inventory: Mapping[str, Any],
    action_policy: Mapping[str, Any], transitions: Sequence[Mapping[str, Any]],
    decision_timestamp_ms: int,
):
    """Call the actual eight-dimension provider and the original gate shim.

    The typed binding distinguishes a SimC action key from a numeric action ID.
    A nonempty mapping reference is traceability only, NOT mapping validation.
    This interface is research/shadow-only; it cannot emit operational READY.
    """
    provider, gate = load_upstreams()
    if not isinstance(binding, Mapping):
        raise IntegrationError("MISSING_ACTION_BINDING")
    required_strings = ("simc_action_key", "spec_slug", "build_key",
                        "apl_sha256", "source_sha256", "mapping_evidence_ref")
    for key in required_strings:
        value = binding.get(key)
        if not isinstance(value, str) or not value.strip():
            raise IntegrationError("INVALID_ACTION_BINDING_" + key)
    if not HEX64.fullmatch(binding["apl_sha256"]) or not HEX64.fullmatch(binding["source_sha256"]):
        raise IntegrationError("ACTION_BINDING_INVALID_SHA256")
    if type(binding.get("action_id")) is not int or binding["action_id"] <= 0:
        raise IntegrationError("ACTION_BINDING_REQUIRES_NUMERIC_ACTION_ID")
    if not isinstance(readiness_contract, Mapping):
        raise IntegrationError("READINESS_CONTRACT_REQUIRED")
    for field in ("spec_slug", "build_key", "apl_sha256"):
        if readiness_contract.get(field) != binding[field]:
            raise IntegrationError("READINESS_BINDING_IDENTITY_MISMATCH_" + field)
    key = binding["simc_action_key"]
    if key not in readiness_contract.get("actions", {}):
        raise IntegrationError("SIMC_ACTION_KEY_NOT_IN_PINNED_CONTRACT")
    if type(decision_timestamp_ms) is not int or decision_timestamp_ms < 0:
        raise IntegrationError("INVALID_DECISION_TIMESTAMP")
    if getattr(pre_state, "decision_timestamp_ms", None) != decision_timestamp_ms:
        raise IntegrationError("PRE_STATE_TIMESTAMP_IDENTITY_MISMATCH")
    # Never silently join a symbolic SimC key to a numeric client/WCL ID.
    identity = {k: binding[k] for k in
                ("spec_slug", "build_key", "action_id", "source_sha256")}
    verdicts = provider.derive_readiness(
        readiness_contract, pre_state, spec_slug=binding["spec_slug"],
        build_key=binding["build_key"], apl_sha256=binding["apl_sha256"])
    verdict = verdicts.get(key)
    if type(verdict) is not provider.ReadinessVerdict:
        raise IntegrationError("NOT_REAL_READINESS_VERDICT")
    if type(verdict.status) is not str or verdict.status not in ("READY", "NOT_READY", "UNKNOWN"):
        raise IntegrationError("UNEXPECTED_READINESS_STATUS_TYPE")
    if verdict.empirical_authority != "NOT_VERIFIED":
        raise IntegrationError("PROVIDER_AUTHORITY_CLAIM_REJECTED")
    result = gate.assess_from_existing_provider(
        existing_verdict=verdict, identity=identity,
        source_inventory=source_inventory, action_policy=action_policy,
        transitions=transitions, decision_timestamp_ms=decision_timestamp_ms)
    if result.status not in (gate.GATE_CANDIDATE, gate.GATE_NEGATIVE, gate.GATE_UNKNOWN):
        raise IntegrationError("UNEXPECTED_SOURCE_GATE_VERDICT")
    if (result.user_recommendation_eligible is not False or
            result.frozen_or_main_promotion is not False or
            result.empirical_authority != "NOT_VERIFIED"):
        raise IntegrationError("SHADOW_ONLY_INVARIANT_BROKEN")
    return result


@dataclass(frozen=True)
class _FixtureObservation:
    value: object
    source_timestamp_ms: int | None
    status: str = "OBSERVED"


@dataclass
class _FixturePreState:
    decision_timestamp_ms: int
    features: dict[str, _FixtureObservation]

    def validate(self):
        # A focused test double for the PRE state *interface*, not a claim
        # that real WCL transition reconstruction has been validated here.
        for observation in self.features.values():
            if (observation.source_timestamp_ms is not None and
                    observation.source_timestamp_ms >= self.decision_timestamp_ms):
                raise ValueError("PRE_FEATURE_TIMESTAMP_LEAK")


def _fixture():
    provider, gate = load_upstreams()
    case = gate.synthetic_fixture()
    binding = {**case["identity"], "simc_action_key": "synthetic_spell_x",
               "apl_sha256": "b" * 64,
               "mapping_evidence_ref": "SYNTHETIC_TYPED_RELATION_UNVERIFIED"}
    dimensions = {
        name: {"mode": "NOT_APPLICABLE", "reason": "synthetic test only",
               "evidence_ref": "SYNTHETIC_WAIVER"}
        for name in provider.MANDATORY
    }
    dimensions["resource"] = {
        "mode": "ALL", "predicates": [
            {"feature": "simc_resource", "op": "ge", "value": 30}]}
    upstream_contract = {
        "schema": "ZrotGenericReadinessRequirementsV1",
        "spec_slug": binding["spec_slug"], "build_key": binding["build_key"],
        "apl_sha256": binding["apl_sha256"], "hypothesis_only": True,
        "actions": {binding["simc_action_key"]:
                    {"evidence_ref": "SYNTHETIC_APL_POLICY",
                     "dimensions": dimensions}},
    }
    case.pop("identity")
    case.pop("readiness_status")
    return {"readiness_contract": upstream_contract,
            "pre_state": _FixturePreState(1000, {"simc_resource": _FixtureObservation(40, 900)}),
            "binding": binding, **case}


def self_test():
    provider, gate = load_upstreams()
    passed: list[str] = []

    def check(name, mutate, expected):
        case = _fixture()
        mutate(case)
        result = assess_from_actual_provider(**case)
        assert result.status == expected, (name, result)
        assert result.input_readiness in ("READY", "NOT_READY", "UNKNOWN")
        assert not result.user_recommendation_eligible and not result.frozen_or_main_promotion
        passed.append(name)

    def reject(name, mutate, expected_error):
        case = _fixture()
        mutate(case)
        try:
            assess_from_actual_provider(**case)
        except (gate.ContractViolation, IntegrationError, ValueError) as exc:
            assert expected_error in str(exc), (name, str(exc), expected_error)
            passed.append(name)
        else:
            raise AssertionError("SHOULD_HAVE_REJECTED_" + name)

    def update_pre_resource(case, *, value=None, missing=False):
        if missing:
            case["pre_state"].features.pop("simc_resource")
        else:
            case["pre_state"].features["simc_resource"] = _FixtureObservation(value, 900)

    check("real_provider_ready_research_candidate", lambda c: None, gate.GATE_CANDIDATE)
    check("real_provider_not_ready_observed_negative",
          lambda c: update_pre_resource(c, value=5), gate.GATE_NEGATIVE)
    check("real_provider_unknown_missing_pre_resource",
          lambda c: update_pre_resource(c, missing=True), gate.GATE_UNKNOWN)
    check("real_provider_incomplete_dimension_unknown",
          lambda c: c["readiness_contract"]["actions"]["synthetic_spell_x"]["dimensions"].pop("target"), gate.GATE_UNKNOWN)
    check("source_gate_missing_declared_required",
          lambda c: c["action_policy"]["gates"].pop(), gate.GATE_UNKNOWN)
    check("source_gate_unverified_waiver_unknown",
          lambda c: c["action_policy"]["gates"][1].update(mode="NOT_APPLICABLE"), gate.GATE_UNKNOWN)
    check("source_gate_evidence_waiver_research_candidate",
          lambda c: c["action_policy"]["gates"][1].update(mode="NOT_APPLICABLE",reason="synthetic", evidence_ref="fixture"), gate.GATE_CANDIDATE)
    check("source_gate_unobserved_unknown",
          lambda c: c["transitions"].pop(), gate.GATE_UNKNOWN)
    check("same_timestamp_not_pre",
          lambda c: c["transitions"][1].update(timestamp_ms=1000), gate.GATE_UNKNOWN)
    check("future_timestamp_not_pre",
          lambda c: c["transitions"][1].update(timestamp_ms=1100), gate.GATE_UNKNOWN)
    check("conflicting_latest_pre_unknown",
          lambda c: c["transitions"].append({"gate_id":"resource_gate","timestamp_ms":950,"value":0,"status":"OBSERVED"}), gate.GATE_UNKNOWN)
    check("later_unresolved_pre_unknown",
          lambda c: c["transitions"].append({"gate_id":"resource_gate","timestamp_ms":990,"value":None,"status":"UNKNOWN"}), gate.GATE_UNKNOWN)
    check("source_disqualifier_has_precedence",
          lambda c: c["transitions"][1].update(value=5), gate.GATE_NEGATIVE)
    reject("build_identity_mismatch",lambda c:c["binding"].update(build_key="wrong_build"), "READINESS_BINDING_IDENTITY_MISMATCH_build_key")
    reject("action_id_identity_mismatch",lambda c:c["binding"].update(action_id=2), "IDENTITY_MISMATCH_action_id")
    reject("source_sha_identity_mismatch",lambda c:c["binding"].update(source_sha256="c"*64), "IDENTITY_MISMATCH_source_sha256")
    reject("apl_sha_identity_mismatch",lambda c:c["binding"].update(apl_sha256="c"*64), "READINESS_BINDING_IDENTITY_MISMATCH_apl_sha256")
    reject("unmapped_simc_symbol_rejected",lambda c:c["binding"].update(simc_action_key="not_in_contract"), "SIMC_ACTION_KEY_NOT_IN_PINNED_CONTRACT")
    reject("missing_mapping_evidence_rejected",lambda c:c["binding"].update(mapping_evidence_ref=""), "INVALID_ACTION_BINDING_mapping_evidence_ref")
    reject("non_numeric_action_id_rejected",lambda c:c["binding"].update(action_id="987654321"), "ACTION_BINDING_REQUIRES_NUMERIC_ACTION_ID")
    reject("wrong_pre_timestamp_rejected",lambda c:setattr(c["pre_state"], "decision_timestamp_ms",999), "PRE_STATE_TIMESTAMP_IDENTITY_MISMATCH")
    reject("missing_provider_policy_waiver_rejected",lambda c:c["readiness_contract"]["actions"]["synthetic_spell_x"]["dimensions"]["target"].update(mode="NOT_APPLICABLE", evidence_ref=""), "UNJUSTIFIED_READINESS_WAIVER")
    # Directly feed a genuine (but forged-authority) provider type into the
    # unchanged gate shim. No SimpleNamespace substitutes are involved.
    direct = gate.synthetic_fixture()
    real_verdict = provider.ReadinessVerdict("READY", "SYNTHETIC_TEST", empirical_authority="NOT_VERIFIED")
    result = gate.assess_from_existing_provider(existing_verdict=real_verdict,
        **{key: value for key, value in direct.items() if key != "readiness_status"})
    assert result.status == gate.GATE_CANDIDATE
    passed.append("real_ReadinessVerdict_bridge_accepts_unverified")
    try:
        gate.assess_from_existing_provider(
            existing_verdict=provider.ReadinessVerdict("READY", "FORGED", empirical_authority="VERIFIED"),
            **{key: value for key, value in direct.items() if key != "readiness_status"})
    except gate.ContractViolation as exc:
        assert str(exc) == "UNVERIFIED_UPSTREAM_AUTHORITY_REQUIRED"
    else:
        raise AssertionError("FORGED_AUTHORITY_ACCEPTED")
    passed.append("real_ReadinessVerdict_forged_authority_rejected")
    return {
        "schema": "ZrotST01ActualProviderGateOfflineReceiptV1",
        "result": "PASS", "passed": len(passed), "cases": passed,
        "provider_repo_commit": PINNED_REPO_COMMIT,
        "provider_git_blob_sha1": PROVIDER_GIT_BLOB_SHA1,
        "gate_sha256": GATE_SHA256,
        "evidence": "ACTUAL_PROVIDER_FUNCTION_AND_VERDICT_OFFLINE_SYNTHETIC_ONLY",
        "source_inventory_completeness": "DECLARED_CANDIDATE_ONLY",
        "wcl_blind_semantic_uses": 0,
        "user_recommendation_eligible": False,
        "main_or_frozen_promotion": False,
        "actual_live_api_wcl_simc_gameplay": "NOT_RUN",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true",
                        help="Focused offline regression (same as default).")
    args = parser.parse_args()
    print(json.dumps(self_test(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
