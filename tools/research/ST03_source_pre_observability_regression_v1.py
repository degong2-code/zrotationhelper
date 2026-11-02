#!/usr/bin/env python3
"""ST-03 research-only observability regression. No WCL/SimC/Blizzard live IO."""
from __future__ import annotations

from copy import deepcopy
import json

import ST02_source_identity_regression_v1 as st02test
import ST03_source_pre_observability_v1 as st03
import simc_apl_readiness_provider as provider


def fixture(which="fury"):
    case = st02test.fixture(which)
    selector = case["selector"]
    action = next(x for x in json.loads(case["source_json"])["candidate_actions"]
                  if x["action"] == selector["action_token"])
    token = selector["action_token"]
    actor, target = "SYNTHETIC_ACTOR_1", "SYNTHETIC_TARGET_1"
    dims = {k: {"mode": "NOT_APPLICABLE", "reason": "fixture only",
                "evidence_ref": "SYNTHETIC_WAIVER"}
            for k in provider.MANDATORY}
    dims["resource"] = {"mode": "ALL", "predicates": [
        {"feature": "synthetic.cost_affordable", "op": "eq", "value": 1}]}
    contract = {
        "schema": "ZrotGenericReadinessRequirementsV1",
        "hypothesis_only": True,
        "spec_slug": selector["identity_spec"],
        "build_key": selector["profile_build"],
        "apl_sha256": selector["effective_apl_sha256"],
        "actions": {token: {"evidence_ref": "SYNTHETIC_ONLY",
                            "dimensions": dims}},
    }
    bindings = {}
    def bind(key):
        if key.startswith("target."):
            return {"scope": "TARGET", "subject_id": target,
                    "evidence_ref": "SYNTHETIC_SCOPE_DECLARATION"}
        if key.startswith("action.") or key.startswith("source_gate::"):
            return {"scope": "ACTION", "subject_id": token,
                    "evidence_ref": "SYNTHETIC_SCOPE_DECLARATION"}
        return {"scope": "ACTOR", "subject_id": actor,
                "evidence_ref": "SYNTHETIC_SCOPE_DECLARATION"}
    features = {"synthetic.cost_affordable"}
    for g in action["extra_source_obligations"]:
        features.update(g["required_state"])
        features.add("source_gate::" + g["id"])
    events = []
    for n, key in enumerate(sorted(features)):
        bindings[key] = bind(key)
        e = {
            "event_id": "synthetic_event_" + str(n),
            "timestamp_ms": 900 if key.startswith("source_gate::") else 850,
            "sequence": 0, "feature_key": key,
            "scope": bindings[key]["scope"],
            "subject_id": bindings[key]["subject_id"],
            "status": "OBSERVED", "value": 1, "valid": True,
            "producer_ref": "SYNTHETIC_GENERATOR_NOT_NATIVE",
            "evidence_ref": "SYNTHETIC_TRANSITION_FIXTURE",
        }
        events.append(e)
    ledger = {
        "schema": st03.SCHEMA, "phase": st03.PHASE,
        "provenance_class": "SYNTHETIC_TEST", "verified_producer": False,
        "decision_timestamp_ms": 1000,
        "decision_actor_id": actor, "decision_target_id": target,
        "action_token": token, "feature_bindings": bindings,
        "events": events,
    }
    ledger["ledger_sha256"] = st03.digest(events)
    return {"st02_case": case, "readiness_contract": contract,
            "ledger": ledger}


def change(case, feature, *, status=None, value=None, timestamp=None,
           valid=None, subject_id=None, append=False):
    ledger = case["ledger"]
    entry = next(x for x in ledger["events"] if x["feature_key"] == feature)
    if append:
        entry = deepcopy(entry)
        entry["event_id"] = entry["event_id"] + "_additional"
        ledger["events"].append(entry)
    if status is not None:
        entry["status"] = status
        if status != "OBSERVED":
            entry["value"] = None
    if value is not None:
        entry["value"] = value
    if timestamp is not None:
        entry["timestamp_ms"] = timestamp
    if valid is not None:
        entry["valid"] = valid
    if subject_id is not None:
        entry["subject_id"] = subject_id
    ledger["ledger_sha256"] = st03.digest(ledger["events"])


def selftest():
    passed = []

    def expect(name, case, status, *, diagnostic=None):
        result = st03.evaluate(**case)
        assert result.status == status, (name, result)
        assert result.live_gameplay_readiness_certified == 0
        assert result.user_recommendation_eligible is False
        assert result.authority_promotion is False
        assert result.wcl_blind_lock == "NOT_RUN"
        if diagnostic:
            key, fragment = diagnostic
            assert fragment in result.source_gate_diagnostics[key], (name, result)
        passed.append(name)
        return result

    def reject(name, case, code):
        try:
            st03.evaluate(**case)
        except (st03.ST03ContractError, ValueError) as exc:
            assert code in str(exc), (name, str(exc))
            passed.append(name)
        else:
            raise AssertionError("SHOULD_REJECT_" + name)

    for which in ("fury", "havoc"):
        c = fixture(which)
        expected_gates = c["st02_case"]["declared_gates"]
        gid = expected_gates[0]["gate_id"]
        gkey = "source_gate::" + gid
        sfeature = next(x for x in c["ledger"]["feature_bindings"]
                        if x != "synthetic.cost_affordable"
                        and not x.startswith("source_gate::"))
        expect(which + "_synthetic_full_pre_candidate", c,
               "ALL_DECLARED_GATES_PASS_RESEARCH_ONLY")
        z = fixture(which); change(z, sfeature, timestamp=1000)
        r = expect(which + "_state_same_time_unknown", z, "UNKNOWN")
        assert r.excluded_same_timestamp_n == 1
        z = fixture(which); change(z, sfeature, timestamp=1001)
        r = expect(which + "_state_future_unknown", z, "UNKNOWN")
        assert r.excluded_future_n == 1
        z = fixture(which); change(z, sfeature, valid=False)
        r = expect(which + "_invalid_state_unknown", z, "UNKNOWN")
        assert r.excluded_invalid_n == 1
        z = fixture(which); change(z, sfeature, status="UNKNOWN", timestamp=950, append=True)
        expect(which + "_later_unknown_shadows_old_pre", z, "UNKNOWN")
        z = fixture(which); change(z, sfeature, value=0, append=True)
        expect(which + "_conflicting_same_time_unknown", z, "UNKNOWN")
        z = fixture(which); change(z, gkey, timestamp=1000)
        expect(which + "_gate_same_time_unknown", z, "UNKNOWN")
        z = fixture(which); change(z, gkey, value=0)
        expect(which + "_gate_explicit_negative", z,
               "OBSERVED_NEGATIVE_RESEARCH_ONLY")
        z = fixture(which); change(z, "synthetic.cost_affordable", value=0)
        expect(which + "_provider_observed_negative", z,
               "OBSERVED_NEGATIVE_RESEARCH_ONLY")
        z = fixture(which); change(z, sfeature, timestamp=950)
        expect(which + "_stale_gate_before_source_state", z, "UNKNOWN",
               diagnostic=(gid, "UNKNOWN_STALE_GATE_BEFORE_SOURCE_STATE"))
        z = fixture(which); z["ledger"]["feature_bindings"].pop(sfeature)
        # Input ledger event now unbound; should reject rather than accept.
        reject(which + "_unbound_feature_rejected", z, "ST03_UNBOUND_TRANSITION_FEATURE")
    z = fixture("havoc")
    z["ledger"]["decision_target_id"] = None
    expect("havoc_unknown_missing_target_context", z, "UNKNOWN")
    z = fixture("havoc")
    key = "target.position_relation"
    change(z, key, subject_id="SYNTHETIC_OTHER_TARGET")
    expect("havoc_target_switch_not_old_target", z, "UNKNOWN")
    z = fixture("fury"); change(z, "synthetic.cost_affordable", timestamp=1000)
    r = expect("provider_same_time_unknown", z, "UNKNOWN")
    assert r.upstream_readiness == "UNKNOWN"
    z = fixture("fury"); change(z, "synthetic.cost_affordable", status="UNOBSERVABLE")
    expect("provider_unobservable_unknown", z, "UNKNOWN")
    z = fixture("fury"); change(z, "synthetic.cost_affordable", value=0, append=True)
    expect("provider_conflicting_pre_unknown", z, "UNKNOWN")
    z = fixture("fury"); z["ledger"]["events"][0]["evidence_ref"] = ""
    z["ledger"]["ledger_sha256"] = st03.digest(z["ledger"]["events"])
    reject("missing_event_provenance_rejected", z, "ST03_TRANSITION_EVIDENCE_REQUIRED")
    z = fixture("fury"); z["ledger"]["events"][0]["value"] = float("nan")
    reject("nonfinite_value_rejected", z, "ST03_NONFINITE_OR_INVALID_LEDGER_JSON")
    z = fixture("fury"); z["ledger"]["events"][0]["event_id"] = z["ledger"]["events"][1]["event_id"]
    z["ledger"]["ledger_sha256"] = st03.digest(z["ledger"]["events"])
    reject("duplicate_event_id_rejected", z, "ST03_DUPLICATE_EVENT_ID")
    z = fixture("fury"); z["ledger"]["verified_producer"] = True
    reject("forged_verified_producer_rejected", z, "UNVERIFIED_PRODUCER_CANNOT_CLAIM_AUTHORITY")
    z = fixture("fury"); z["ledger"]["phase"] = "WCL_BLIND"
    reject("blind_semantic_leak_rejected", z, "ST03_SCHEMA_OR_LANE_MISMATCH")
    z = fixture("fury"); z["ledger"]["events"][0]["value"] = 0
    reject("tampered_event_digest_rejected", z, "ST03_LEDGER_SHA256_MISMATCH")
    z = fixture("fury"); z["ledger"]["feature_bindings"]["synthetic.cost_affordable"]["subject_id"] = "OTHER_ACTOR"
    reject("actor_binding_mismatch_rejected", z, "ACTOR_FEATURE_BINDING_MISMATCH")
    z = fixture("havoc"); z["ledger"]["feature_bindings"]["target.position_relation"]["subject_id"] = "OTHER_TARGET"
    reject("target_binding_mismatch_rejected", z, "TARGET_FEATURE_BINDING_MISMATCH")
    z = fixture("fury"); z["st02_case"]["selector"]["candidate_game_spell_id"] = 1234
    reject("source_identity_drift_rejected", z, "SOURCE_CANDIDATE_ID_MISMATCH")
    z = fixture("fury"); z["st02_case"]["declared_gates"].pop()
    expect("missing_source_obligation_is_unknown", z, "UNKNOWN")
    z = fixture("fury"); z["st02_case"]["declared_gates"][0]["evidence_ref"] = ""
    expect("unverified_source_gate_is_unknown", z, "UNKNOWN")
    z = fixture("fury"); z["ledger"]["provenance_class"] = "EXTERNAL_DECLARED_UNVERIFIED"
    r = expect("external_declared_still_no_authority", z,
               "ALL_DECLARED_GATES_PASS_RESEARCH_ONLY")
    assert r.source_authenticity == "NOT_INDEPENDENTLY_VERIFIED"
    return {
        "schema": "ZrotST03SourcePreObservabilityOfflineReceiptV1",
        "result": "PASS", "count": len(passed), "cases": passed,
        "evidence": "PINNED_SOURCE_UNVERIFIED_LEDGER_SYNTHETIC_ONLY",
        "source_specific_game_mechanics_verified": False,
        "native_production_state": "NOT_CAPTURED",
        "independent_wcl_blind": "NOT_RUN",
        "real_wcl_simc_blizzard_gameplay": "NOT_RUN",
        "gameplay_readiness_certified": 0,
        "authority_promotion": False, "seq637": "UNKNOWN",
    }


if __name__ == "__main__":
    print(json.dumps(selftest(), ensure_ascii=False, indent=2, sort_keys=True))
