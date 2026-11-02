#!/usr/bin/env python3
"""ST-02 source/identity regression with pinned research docs and real ST-01 bridge.

Only SYNTHETIC transition values are used. No live game, WCL or SimC runs.
Run in-repo without arguments or with --self-test. No secrets or network.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_SOURCE" / "runtime"))

from raid_dps.core.behavioral_evaluator import StrictPreStateProvider, StateTransition
import ST02_source_identity_reconciliation_v1 as st02
import ST01_existing_simc_readiness_gate_regression_v1 as st01

SOURCE_PATH = ROOT / "docs/BR_SIMC_MINIMUM_READINESS_SOURCE_GAP_20261031.json"
IDENTITY_PATH = ROOT / "docs/BR_SIMC_EXTERNAL_GAME_SPELL_ID_CANDIDATE_20261031.json"
SOURCE_SHA = "e437da47d632737c9eacc3901c945590aff0308b"
IDENTITY_SHA = "2e933135877704b257237ef465025e532a14b9c0"


def fixture(which="fury"):
    raw_source = SOURCE_PATH.read_bytes()
    raw_identity = IDENTITY_PATH.read_bytes()
    source = json.loads(raw_source)
    ids = json.loads(raw_identity)
    if which == "fury":
        source_spec, id_spec, token = "fury", "fury_warrior", "rampage"
    elif which == "havoc":
        source_spec, id_spec, token = "havoc", "havoc_demon_hunter", "felblade"
    else:
        raise AssertionError("UNKNOWN_TEST_FIXTURE")
    action = next(x for x in source["candidate_actions"] if x["action"] == token)
    candidate = next(x for x in ids["candidates"] if x["action_token"] == token)
    native_id = candidate["native_action_t_id"]
    game_id = candidate["candidate_game_spell_id"]
    selector = {
        "source_spec": source_spec, "identity_spec": id_spec,
        "action_token": token,
        "simc_action_object_id": native_id,
        "candidate_game_spell_id": game_id,
        "effective_apl_sha256": action["effective_apl_sha256"],
        "profile_build": action["profile_build"],
        "spec_scope_evidence_ref": "PINNED_SOURCE_AND_IDENTITY_DOCS_UNVERIFIED",
        "mapping_evidence_ref": "TYPED_SOURCE_POINTER_CANDIDATE_ONLY",
    }
    edges = [
        {"from": {"kind": "SIMC_APL_ACTION_TOKEN", "id": token},
         "to": {"kind": "SIMC_ACTION_OBJECT_ID", "id": native_id},
         "status": "UNVERIFIED_CANDIDATE",
         "evidence_ref": "PINNED_SIMC_SOURCE_POINTER"},
        {"from": {"kind": "SIMC_ACTION_OBJECT_ID", "id": native_id},
         "to": {"kind": "GAME_SPELL_ID_CANDIDATE", "id": game_id},
         "status": "UNVERIFIED_CANDIDATE",
         "evidence_ref": "PUBLIC_ID_CANDIDATE_NOT_CURRENT_GAME"},
    ]
    policy = [
        {"gate_id": entry["id"], "source_symbol": entry["source_symbol"],
         "required_state": entry["required_state"],
         "source_manifest_blob_sha1": SOURCE_SHA,
         "evidence_ref": "SYNTHETIC_GATE_VALUE_NOT_LIVE_MECHANIC",
         "mode": "REQUIRED", "op": "eq", "threshold": 1}
        for entry in action["extra_source_obligations"]
    ]
    return {
        "source_json": raw_source, "source_blob_sha1": SOURCE_SHA,
        "identity_json": raw_identity, "identity_blob_sha1": IDENTITY_SHA,
        "selector": selector, "relation_edges": edges, "declared_gates": policy,
    }


def integrate(case, *, remove_transition=None, negative=None, same_time=None,
              upstream_resource=40):
    audit, compiled = st02.reconcile(**case)
    binding = {
        **compiled["identity"],
        "simc_action_key": case["selector"]["action_token"],
        "apl_sha256": case["selector"]["effective_apl_sha256"],
        "mapping_evidence_ref": case["selector"]["mapping_evidence_ref"],
    }
    # Readiness inputs are deliberately SYNTHETIC. No static source cost claim.
    import simc_apl_readiness_provider as provider
    dims = {
        dim: {"mode": "NOT_APPLICABLE", "reason": "synthetic fixture",
              "evidence_ref": "ST02_SYNTHETIC"}
        for dim in provider.MANDATORY
    }
    dims["resource"] = {"mode": "ALL", "predicates": [
        {"feature": "synthetic.cost_affordable", "op": "eq", "value": 1}
    ]}
    contract = {
        "schema": "ZrotGenericReadinessRequirementsV1",
        "hypothesis_only": True,
        "spec_slug": binding["spec_slug"], "build_key": binding["build_key"],
        "apl_sha256": binding["apl_sha256"],
        "actions": {binding["simc_action_key"]: {
            "evidence_ref": "ST02_SYNTHETIC",
            "dimensions": dims}},
    }
    state = StrictPreStateProvider().build(
        action_timestamp_ms=1000, transitions=[
            StateTransition(900, "synthetic.cost_affordable",
                            1 if upstream_resource >= 30 else 0)])
    transitions = []
    for gate_id in compiled["source_inventory"]["declared_required_gate_ids"]:
        if gate_id == remove_transition:
            continue
        val = 0 if gate_id == negative else 1
        stamp = 1000 if gate_id == same_time else 900
        transitions.append({"gate_id": gate_id, "timestamp_ms": stamp,
                            "value": val, "status": "OBSERVED"})
    verdict = st01.assess_from_actual_provider(
        readiness_contract=contract, pre_state=state, binding=binding,
        source_inventory=compiled["source_inventory"],
        action_policy=compiled["action_policy"],
        transitions=transitions, decision_timestamp_ms=1000)
    return audit, verdict


def self_test():
    passed = []

    def check(name, work):
        work()
        passed.append(name)

    def raises(name, mutate, error):
        case = fixture()
        mutate(case)
        try:
            st02.reconcile(**case)
        except st02.ST02ContractError as exc:
            assert error in str(exc), (name, str(exc), error)
        else:
            raise AssertionError(name + "_NOT_REJECTED")
        passed.append(name)

    for which in ("fury", "havoc"):
        def positive(w=which):
            audit, compiled = st02.reconcile(**fixture(w))
            assert audit.coverage_status == "DECLARED_SOURCE_COVERAGE_CANDIDATE_ONLY"
            assert audit.identity_status == "TYPED_RELATIONS_UNVERIFIED_CANDIDATE"
            assert audit.gameplay_ready_certified == 0
            assert audit.user_recommendation_eligible is False
            assert audit.authority_promotion is False
            assert len(audit.accepted_gate_ids) == 2
            assert len(compiled["source_inventory"]["declared_required_gate_ids"]) == 2
        check(which + "_pinned_coverage_candidate_only", positive)

        def real_bridge(w=which):
            audit, verdict = integrate(fixture(w))
            assert verdict.status == "ALL_DECLARED_GATES_PASS_RESEARCH_ONLY"
            assert verdict.user_recommendation_eligible is False
            assert audit.gameplay_ready_certified == 0
        check(which + "_actual_ST01_provider_bridge", real_bridge)

        def negative(w=which):
            gate_id = fixture(w)["declared_gates"][0]["gate_id"]
            _, verdict = integrate(fixture(w), negative=gate_id)
            assert verdict.status == "OBSERVED_NEGATIVE_RESEARCH_ONLY"
        check(which + "_synthetic_observed_negative", negative)

        def missing_pre(w=which):
            gate_id = fixture(w)["declared_gates"][0]["gate_id"]
            _, verdict = integrate(fixture(w), remove_transition=gate_id)
            assert verdict.status == "UNKNOWN"
        check(which + "_missing_pre_unknown", missing_pre)

    check("upstream_known_negative", lambda: (
        lambda r: (_ for _ in ()).throw(AssertionError(r))
        if r.status != "OBSERVED_NEGATIVE_RESEARCH_ONLY" else None
    )(integrate(fixture(), upstream_resource=0)[1]))

    def missing_gate():
        c = fixture()
        c["declared_gates"].pop()
        audit, verdict = integrate(c)
        assert audit.coverage_status == "UNKNOWN_INCOMPLETE_SOURCE_DECLARATION"
        assert len(audit.missing_gate_ids) == 1 and verdict.status == "UNKNOWN"
    check("missing_source_gate_fail_closed", missing_gate)

    def waiver_unknown():
        c = fixture()
        c["declared_gates"][0].update(mode="NOT_APPLICABLE",
                                       reason="asserted but not certified")
        audit, verdict = integrate(c)
        assert len(audit.unverified_gate_ids) == 1 and verdict.status == "UNKNOWN"
    check("unverified_waiver_fail_closed", waiver_unknown)

    for field, value in (("source_symbol", "fabricated_symbol"),
                         ("required_state", ["fabricated_feature"]),
                         ("source_manifest_blob_sha1", "0" * 40),
                         ("evidence_ref", "")):
        def mismatch(f=field, v=value):
            c = fixture()
            c["declared_gates"][0][f] = v
            audit, verdict = integrate(c)
            assert audit.coverage_status == "UNKNOWN_INCOMPLETE_SOURCE_DECLARATION"
            assert verdict.status == "UNKNOWN"
        check("provenance_" + field + "_unknown", mismatch)

    def same_time():
        c = fixture()
        gid = c["declared_gates"][0]["gate_id"]
        _, verdict = integrate(c, same_time=gid)
        assert verdict.status == "UNKNOWN"
    check("same_timestamp_not_pre", same_time)

    raises("tampered_source_blob",
           lambda c: c.update(source_json=c["source_json"] + b" "),
           "SOURCE_OBLIGATION_SOURCE_BYTES_MISMATCH")
    raises("tampered_identity_blob",
           lambda c: c.update(identity_json=c["identity_json"] + b" "),
           "IDENTITY_SOURCE_BYTES_MISMATCH")
    raises("cross_action_identity_mismatch",
           lambda c: c["selector"].update(candidate_game_spell_id=1234),
           "SOURCE_CANDIDATE_ID_MISMATCH")
    raises("wrong_action_object_id",
           lambda c: c["selector"].update(simc_action_object_id=1234),
           "SOURCE_CANDIDATE_ID_MISMATCH")
    raises("incorrect_apl_pin",
           lambda c: c["selector"].update(effective_apl_sha256="a"*64),
           "SOURCE_APL_VERSION_MISMATCH")
    raises("wrong_profile_build",
           lambda c: c["selector"].update(profile_build="live_unverified"),
           "SOURCE_BUILD_SCOPE_MISMATCH")
    raises("missing_explicit_relation",
           lambda c: c["relation_edges"].pop(),
           "TWO_EXPLICIT_IDENTITY_LINKS_REQUIRED")
    raises("numeric_equal_not_implicit_mapping",
           lambda c: c["relation_edges"][1]["to"].update(id=12345),
           "IDENTITY_RELATION_MISMATCH")
    raises("unsupported_semantic_relation",
           lambda c: c["relation_edges"][1]["status"].__class__ and
           c["relation_edges"][1].update(status="CERTIFIED"),
           "IDENTITY_AUTHORITY_NOT_ESTABLISHED")
    raises("WCL_identity_pre_lock_forbidden",
           lambda c: c["relation_edges"][1]["to"].update(kind="WCL_CAST_EVENT_ID"),
           "WCL_PRE_LOCK_SEMANTIC_RELATION_FORBIDDEN")
    raises("duplicate_gate",
           lambda c: c["declared_gates"].append(deepcopy(c["declared_gates"][0])),
           "DUPLICATE_DECLARED_GATE")
    raises("invented_source_gate",
           lambda c: c["declared_gates"][0].update(gate_id="MADE_UP_GATE"),
           "UNDECLARED_GATE_ID")
    raises("missing_cross_spec_evidence",
           lambda c: c["selector"].update(spec_scope_evidence_ref=""),
           "MISSING_spec_scope_evidence_ref")
    raises("missing_mapping_evidence",
           lambda c: c["selector"].update(mapping_evidence_ref=""),
           "MISSING_mapping_evidence_ref")

    return {
        "schema": "ZrotST02PinnedSourceIdentityOfflineReceiptV1",
        "status": "PASS", "count": len(passed), "cases": passed,
        "source_git_blob": SOURCE_SHA, "identity_git_blob": IDENTITY_SHA,
        "source_examples": ["fury:rampage", "havoc:felblade"],
        "evidence": "SOURCE_PINNED_STRUCTURAL_AND_SYNTHETIC_INTEGRATION_ONLY",
        "source_inventory_exhaustiveness": "NOT_CERTIFIED",
        "typed_identity": "UNVERIFIED_CANDIDATE",
        "current_gameplay_ready_certified": 0,
        "wcl_blind_candidate_lock": "NOT_RUN",
        "simc_live": "NOT_RUN", "wcl_live": "NOT_RUN",
        "main_or_frozen_promotion": False, "seq637": "UNKNOWN",
    }


if __name__ == "__main__":
    receipt = self_test()
    print(json.dumps(receipt, sort_keys=True, indent=2))
