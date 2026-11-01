#!/usr/bin/env python3
"""Research-only link: pinned SimC readiness verdict -> source-obligation gate.

No current-game action, empirical validation, or production READY is emitted.
This adapter deliberately does not modify either existing evaluator.
Run without args for synthetic/offline regression (PyCharm friendly).
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import sys

# Import the pre-existing research modules, not recreated readiness logic.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for path in (HERE, ROOT / "02_SOURCE" / "runtime"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from simc_apl_readiness_provider import derive_readiness
from zrot_source_obligation_gate_v1 import (
    ContractViolation, ResearchGateResult, assess_from_existing_provider,
    synthetic_fixture, GATE_CANDIDATE, GATE_NEGATIVE, GATE_UNKNOWN,
)


@dataclass(frozen=True)
class BridgeVerdict:
    simc_action_token: str
    numeric_action_identity: int
    upstream_readiness: str
    source_gate: ResearchGateResult
    consumer_readiness: str = "UNKNOWN"
    evidence_level: str = "SYNTHETIC_OR_SHADOW_RESEARCH_ONLY"
    gameplay_recommendation_eligible: bool = False
    live_identity_certified: bool = False
    production_promotion: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def bridge(
    *,
    provider_contract: Mapping[str, Any],
    strict_pre_state: Any,
    spec_slug: str,
    build_key: str,
    apl_sha256: str,
    simc_action_token: str,
    binding: Mapping[str, Any],
    identity: Mapping[str, Any],
    source_inventory: Mapping[str, Any],
    action_policy: Mapping[str, Any],
    transitions: Sequence[Mapping[str, Any]],
    decision_timestamp_ms: int,
) -> BridgeVerdict:
    """Call the actual eight-dimension provider before the v1 source gate.

    `binding` is a typed, unverified *research join*; the numeric ID here is
    not asserted to be a certified Retail client action ID or WCL CAST ID.
    Downstream consumer readiness is ALWAYS UNKNOWN even if all synthetic
    hypotheses pass. WCL blind discovery must not consume this output.
    """
    if getattr(strict_pre_state, "decision_timestamp_ms", None) != decision_timestamp_ms:
        raise ContractViolation("BRIDGE_DECISION_TIMESTAMP_MISMATCH")
    if not callable(getattr(strict_pre_state, "validate", None)):
        raise ContractViolation("BRIDGE_STRICT_PRE_STATE_REQUIRED")
    strict_pre_state.validate()
    if not isinstance(simc_action_token, str) or not simc_action_token:
        raise ContractViolation("BRIDGE_ACTION_TOKEN_REQUIRED")
    if not isinstance(binding, Mapping):
        raise ContractViolation("BRIDGE_BINDING_REQUIRED")
    if binding.get("phase") != "POST_SIMC_HYPOTHESIS_RESEARCH_ONLY":
        raise ContractViolation("BRIDGE_BLIND_LANE_CONTAMINATION_FORBIDDEN")
    if binding.get("status") != "RESEARCH_UNVERIFIED":
        raise ContractViolation("BRIDGE_UNVERIFIED_IDENTITY_REQUIRED")
    if binding.get("simc_action_token") != simc_action_token:
        raise ContractViolation("BRIDGE_ACTION_TOKEN_MISMATCH")
    if type(binding.get("action_id")) is not int or binding["action_id"] <= 0:
        raise ContractViolation("BRIDGE_NUMERIC_ID_REQUIRED")
    if type(identity.get("action_id")) is not int or binding["action_id"] != identity["action_id"]:
        raise ContractViolation("BRIDGE_NUMERIC_ID_MISMATCH")
    if identity.get("spec_slug") != spec_slug or identity.get("build_key") != build_key:
        raise ContractViolation("BRIDGE_SPEC_BUILD_MISMATCH")
    if identity.get("source_sha256") != apl_sha256:
        raise ContractViolation("BRIDGE_APL_SOURCE_IDENTITY_MISMATCH")
    if not isinstance(binding.get("evidence_ref"), str) or not binding["evidence_ref"].strip():
        raise ContractViolation("BRIDGE_BINDING_EVIDENCE_REQUIRED")
    policies = provider_contract.get("actions")
    if not isinstance(policies, dict) or simc_action_token not in policies:
        raise ContractViolation("BRIDGE_APL_ACTION_NOT_DECLARED")

    upstream = derive_readiness(
        provider_contract, strict_pre_state,
        spec_slug=spec_slug, build_key=build_key, apl_sha256=apl_sha256,
    )[simc_action_token]
    gated = assess_from_existing_provider(
        existing_verdict=upstream,
        identity=identity,
        source_inventory=source_inventory,
        action_policy=action_policy,
        transitions=transitions,
        decision_timestamp_ms=decision_timestamp_ms,
    )
    return BridgeVerdict(
        simc_action_token=simc_action_token,
        numeric_action_identity=identity["action_id"],
        upstream_readiness=upstream.status,
        source_gate=gated,
    )


def self_test() -> dict[str, Any]:
    from copy import deepcopy
    from raid_dps.core.behavioral_evaluator import StrictPreStateProvider, StateTransition
    from simc_apl_readiness_provider import MANDATORY

    successes: list[str] = []

    def case(*, upstream_events=None, gate_events=None, mutate=None) -> dict[str, Any]:
        f = synthetic_fixture()
        f["source_inventory"]["declared_required_gate_ids"] = ["source_ability_gate"]
        f["action_policy"]["gates"] = [{
            "gate_id": "source_ability_gate", "mode": "REQUIRED", "op": "ge",
            "threshold": 1, "evidence_ref": "SYNTHETIC_SOURCE_GATE",
        }]
        policy = {
            "schema": "ZrotGenericReadinessRequirementsV1",
            "spec_slug": f["identity"]["spec_slug"],
            "build_key": f["identity"]["build_key"],
            "apl_sha256": f["identity"]["source_sha256"],
            "hypothesis_only": True,
            "actions": {"synthetic_cast": {
                "evidence_ref": "SYNTHETIC_APL_ROW",
                "dimensions": {d: {
                    "mode": "NOT_APPLICABLE", "reason": "synthetic waived",
                    "evidence_ref": "SYNTHETIC_WAIVER",
                } for d in MANDATORY},
            }},
        }
        policy["actions"]["synthetic_cast"]["dimensions"]["resource"] = {
            "mode": "ALL", "predicates": [{"feature":"resource", "op":"ge", "value":30}],
        }
        policy["actions"]["synthetic_cast"]["dimensions"]["cooldown_or_charge"] = {
            "mode": "ALL", "predicates": [{"feature":"charges", "op":"ge", "value":1}],
        }
        pre_events = upstream_events if upstream_events is not None else [
            (900,"resource",45), (900,"charges",1),
        ]
        state = StrictPreStateProvider().build(
            action_timestamp_ms=1000,
            transitions=[StateTransition(*e) for e in pre_events],
        )
        args = {
            "provider_contract": policy,
            "strict_pre_state": state,
            "spec_slug": f["identity"]["spec_slug"],
            "build_key": f["identity"]["build_key"],
            "apl_sha256": f["identity"]["source_sha256"],
            "simc_action_token": "synthetic_cast",
            "binding": {
                "phase": "POST_SIMC_HYPOTHESIS_RESEARCH_ONLY",
                "status": "RESEARCH_UNVERIFIED",
                "simc_action_token": "synthetic_cast",
                "action_id": f["identity"]["action_id"],
                "evidence_ref": "SYNTHETIC_JOIN_NOT_GAME_ID",
            },
            "identity": f["identity"],
            "source_inventory": f["source_inventory"],
            "action_policy": f["action_policy"],
            "transitions": gate_events if gate_events is not None else [
                {"gate_id":"source_ability_gate", "timestamp_ms":920,
                 "value":1,"status":"OBSERVED"},
            ],
            "decision_timestamp_ms": 1000,
        }
        if mutate is not None:
            mutate(args)
        return args

    def expect(name, args, upstream, gate):
        out = bridge(**args)
        assert out.upstream_readiness == upstream, (name, out)
        assert out.source_gate.status == gate, (name, out)
        assert out.consumer_readiness == "UNKNOWN", (name, out)
        assert not out.gameplay_recommendation_eligible and not out.production_promotion
        assert not out.live_identity_certified
        successes.append(name)

    def deny(name, args, msg):
        try:
            bridge(**args)
        except ContractViolation as err:
            assert str(err) == msg, (name, str(err))
        else:
            raise AssertionError("EXPECTED_FAIL_CLOSED:"+name)
        successes.append(name)

    expect("both_declared_candidate",case(),"READY",GATE_CANDIDATE)
    expect("upstream_missing_resource",case(upstream_events=[(900,"charges",1)]),"UNKNOWN",GATE_UNKNOWN)
    expect("upstream_not_ready",case(upstream_events=[(900,"charges",1),(900,"resource",10)]),"NOT_READY",GATE_NEGATIVE)
    expect("gate_missing",case(gate_events=[]),"READY",GATE_UNKNOWN)
    expect("gate_observed_negative",case(gate_events=[{"gate_id":"source_ability_gate","timestamp_ms":920,"value":0,"status":"OBSERVED"}]),"READY",GATE_NEGATIVE)
    expect("gate_same_timestamp",case(gate_events=[{"gate_id":"source_ability_gate","timestamp_ms":1000,"value":1,"status":"OBSERVED"}]),"READY",GATE_UNKNOWN)
    expect("gate_future_event",case(gate_events=[{"gate_id":"source_ability_gate","timestamp_ms":1001,"value":1,"status":"OBSERVED"}]),"READY",GATE_UNKNOWN)
    expect("upstream_same_timestamp",case(upstream_events=[(1000,"resource",45),(900,"charges",1)]),"UNKNOWN",GATE_UNKNOWN)
    expect("upstream_future_transition",case(upstream_events=[(1001,"resource",45),(900,"charges",1)]),"UNKNOWN",GATE_UNKNOWN)
    expect("gate_conflicting_same_prior_time",case(gate_events=[
        {"gate_id":"source_ability_gate","timestamp_ms":920,"value":1,"status":"OBSERVED"},
        {"gate_id":"source_ability_gate","timestamp_ms":920,"value":0,"status":"OBSERVED"},
    ]),"READY",GATE_UNKNOWN)
    expect("gate_policy_missing",case(mutate=lambda a:a["action_policy"].update(gates=[])),"READY",GATE_UNKNOWN)
    expect("upstream_policy_dimension_missing",case(mutate=lambda a:a["provider_contract"]["actions"]["synthetic_cast"]["dimensions"].pop("target")),"UNKNOWN",GATE_UNKNOWN)
    deny("identity_mismatch",case(mutate=lambda a:a["binding"].update(action_id=3)),"BRIDGE_NUMERIC_ID_MISMATCH")
    deny("apl_sha_mismatch",case(mutate=lambda a:a["identity"].update(source_sha256="c"*64)),"BRIDGE_APL_SOURCE_IDENTITY_MISMATCH")
    deny("blind_phase_forbidden",case(mutate=lambda a:a["binding"].update(phase="WCL_BLIND")),"BRIDGE_BLIND_LANE_CONTAMINATION_FORBIDDEN")
    deny("false_verified_binding_forbidden",case(mutate=lambda a:a["binding"].update(status="VERIFIED")),"BRIDGE_UNVERIFIED_IDENTITY_REQUIRED")
    deny("action_token_mismatch",case(mutate=lambda a:a["binding"].update(simc_action_token="other")),"BRIDGE_ACTION_TOKEN_MISMATCH")
    deny("timestamp_mismatch",case(mutate=lambda a:a.update(decision_timestamp_ms=999)),"BRIDGE_DECISION_TIMESTAMP_MISMATCH")
    deny("undeclared_action_token",case(mutate=lambda a:a["provider_contract"]["actions"].pop("synthetic_cast")),"BRIDGE_APL_ACTION_NOT_DECLARED")
    successes.append("upstream_type_"+str(type(derive_readiness(case()["provider_contract"],case()["strict_pre_state"],spec_slug="synthetic_spec",build_key="synthetic_build",apl_sha256="a"*64)["synthetic_cast"]).__name__))
    assert len(successes)==20
    return {"schema":"ZrotReadinessBridgeOfflineReceiptV1",
            "result":"PASS", "count":len(successes), "cases":successes,
            "source_gate":"RESEARCH_ONLY", "provider":"ACTUAL_SIMC_APL_READINESS_PROVIDER",
            "actual_wcl":"NOT_RUN", "native_simc":"NOT_RUN",
            "current_game_identity":"NOT_CERTIFIED", "production_ready_emitted":False}


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    print(json.dumps(self_test(),sort_keys=True,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
