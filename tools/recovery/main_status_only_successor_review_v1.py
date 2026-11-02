#!/usr/bin/env python3
"""Status-only MAIN successor *review* (no gameplay/runtime integration).

This tool reads exactly two branch-local JSON files, verifies their bytes and
constraints, and prints a non-actionable status. It never imports old product
code, loads .env, accesses network, launches a subprocess, dispatches Inbox,
or writes output files. Does NOT authorize or promote product MAIN.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "active/branches/BR-MAIN-STATUS-ONLY-20261102/MAIN_AUTHORITY_STATUS_ONLY_CANDIDATE_V1.json"
EVIDENCE = ROOT / "docs/MAIN_SIX_LIVE_HASHES_SNAPSHOT_CONSISTENCY_20261102.json"
EVIDENCE_GIT_BLOB_SHA1 = "675b081a5ff82b58a2b5497ca3aa0a9dc6a38b0e"
PARENT_REVIEW_HEAD = "5411e34d0cae4d6e354433666c17240d37188148"
GITHUB_MAIN_HEAD = "4790f77f76a75f26ff0558d1d18c16cd9d630c4b"
FEX_SHA = "c9ba0657c0f5ed936acf41a839780d6b3c245e08757107a96fef6cc675b1dc2f"
FIRST_SHA = "a3a30cc8f406216f9281109a3ffc357dba8306fafeb7b7a6f4fe090785e2d080"
CANDIDATE_IDS = {
    "FEX_FULL_ENGINE_SYNTHETIC_PROBE_V1": FEX_SHA,
    "FIRST_CROSS_SPEC_SYNTHETIC_PROBE_V1": FIRST_SHA,
}
ALLOWED = {"READ_CANDIDATE_STATUS", "VALIDATE_CANDIDATE_CONTRACT"}
FORBIDDEN = {
    "RUN_ACTIVE", "LEGACY_RUN_zRAID_MAIN", "DISPATCH_INBOX", "RUN_SIMC",
    "CALL_WCL", "WRITE_MAIN_STATE", "WRITE_POINTER", "PROMOTE_FROZEN",
}
PINNED_READS = {
    "active/branches/BR-MAIN-STATUS-ONLY-20261102/MAIN_AUTHORITY_STATUS_ONLY_CANDIDATE_V1.json",
    "docs/MAIN_SIX_LIVE_HASHES_SNAPSHOT_CONSISTENCY_20261102.json",
}
GATES = {
    "latest_runtime_authority_verified",
    "latest_work_state_verified",
    "selected_workflow_evidence_verified",
    "old_historical_conflicts_disposition_approved",
    "dispatcher_pre_status_side_effect_controlled",
    "full_product_source_runtime_compatibility_verified",
    "independent_focused_behavior_validation",
    "total_authorized_for_live_activation",
}
INVARIANTS = {
    "GitHub_main_changed": False,
    "MAIN_CURRENT_STATE_changed": False,
    "canonical_registry_created": False,
    "current_pointer_created": False,
    "product_default_action_changed": False,
    "archived_control_plane_changed": False,
    "FROZEN_changed": False,
    "Seq578": "FAILED_QUARANTINED_PRESERVED",
    "Seq637": "UNKNOWN",
    "gameplay_ready_action_count": 0,
    "WCL_blind_semantic_join": "FORBIDDEN_PRE_LOCK",
}


class ReviewContractError(ValueError):
    pass


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()


def _strict_keys(obj: dict, allowed: set[str], label: str) -> None:
    if not isinstance(obj, dict) or set(obj) != allowed:
        raise ReviewContractError("UNKNOWN_AUTHORITY_FIELD_" + label)


def validate(candidate: dict, evidence: dict) -> dict:
    _strict_keys(candidate, {
        "schema", "candidate_id", "owner", "lifecycle", "base",
        "workflow_authority", "status_adapter_contract", "historical_conflicts",
        "promotion_gates", "invariants", "verdict",
    }, "ROOT")
    _strict_keys(candidate["base"], {
        "github_repository", "github_review_branch", "github_review_head_sha",
        "github_product_main_head_sha", "product_main_status",
        "evidence_path", "evidence_git_blob_sha1", "evidence_scope",
    }, "BASE")
    _strict_keys(candidate["workflow_authority"], {
        "current_approved_runtime", "current_approved_work_state",
        "selection_state", "selected_workflow_id", "candidates",
        "false_authority_forbidden", "preferred_workflow_id",
    }, "WORKFLOW")
    _strict_keys(candidate["status_adapter_contract"], {
        "only_command", "default_operation", "allowed_operations",
        "forbidden_operations", "read_only_input_allowlist",
        "execution_backend", "product_live_call_count",
    }, "ADAPTER")
    _strict_keys(candidate["historical_conflicts"], {
        "workflow_id_conflict", "prompt_sha_id_binding",
        "default_action_conflict", "stale_entrypoint_or_config_sha_occurrences",
        "reconciled_six_pc_hashes", "corrected_sources_applied_to_product_main",
    }, "CONFLICTS")
    if not isinstance(candidate, dict) or candidate.get("schema") != "ZrotMainAuthoritySuccessorStatusOnlyCandidateV1":
        raise ReviewContractError("UNKNOWN_CANDIDATE_SCHEMA")
    if candidate.get("lifecycle") != "BRANCH_CANDIDATE_NOT_PROMOTED":
        raise ReviewContractError("LIFECYCLE_PROMOTION_FORBIDDEN")

    base = candidate.get("base", {})
    if (base.get("github_repository") != "degong2-code/zrotationhelper"
            or base.get("github_review_head_sha") != PARENT_REVIEW_HEAD
            or base.get("github_product_main_head_sha") != GITHUB_MAIN_HEAD
            or base.get("product_main_status") != "README_ONLY_NOT_VERIFIED_PRODUCT_RUNTIME"
            or base.get("evidence_path") != "docs/MAIN_SIX_LIVE_HASHES_SNAPSHOT_CONSISTENCY_20261102.json"
            or base.get("evidence_git_blob_sha1") != EVIDENCE_GIT_BLOB_SHA1
            or base.get("evidence_scope") != "USER_REPORTED_6_LOCAL_SHA_MATCH_ARCHIVED_PRIVATE_M4B"):
        raise ReviewContractError("STALE_OR_FORGED_BASE_PROVENANCE")

    wf = candidate.get("workflow_authority", {})
    if (wf.get("current_approved_runtime") != "UNKNOWN"
            or wf.get("current_approved_work_state") != "UNKNOWN"
            or wf.get("selection_state") != "UNRESOLVED_NEEDS_MAIN_APPROVED_EVIDENCE"
            or wf.get("selected_workflow_id") is not None
            or wf.get("preferred_workflow_id") is not None
            or wf.get("false_authority_forbidden") is not True):
        raise ReviewContractError("AUTOMATIC_WORKFLOW_SELECTION_FORBIDDEN")

    rows = wf.get("candidates", [])
    if not isinstance(rows, list) or len(rows) != 2 or {x.get("id") for x in rows} != set(CANDIDATE_IDS):
        raise ReviewContractError("HISTORICAL_WORKFLOW_ALTERNATIVES_LOST")
    expected_refs = {
        "FEX_FULL_ENGINE_SYNTHETIC_PROBE_V1": {"MAIN_CONTROL_PLANE.json", "LATEST_HANDOFF.json"},
        "FIRST_CROSS_SPEC_SYNTHETIC_PROBE_V1": {"CURRENT_STATE.md", "MAIN_ENTRYPOINT_AUTHORITY.json"},
    }
    for row in rows:
        _strict_keys(row, {"id", "historical_source_sha256", "historical_observed_refs", "status"}, "WORKFLOW_CANDIDATE")
        ident = row["id"]
        if (row.get("historical_source_sha256") != CANDIDATE_IDS[ident]
                or row.get("status") != "HISTORICAL_CANDIDATE_NOT_APPROVED"
                or set(row.get("historical_observed_refs", ())) != expected_refs[ident]
                or len(row["historical_observed_refs"]) != 2):
            raise ReviewContractError("HISTORICAL_WORKFLOW_PIN_CHANGED")

    adapter = candidate.get("status_adapter_contract", {})
    if (adapter.get("only_command") != "STATUS_ONLY"
            or adapter.get("default_operation") != "READ_CANDIDATE_STATUS"
            or set(adapter.get("allowed_operations", ())) != ALLOWED
            or len(adapter.get("allowed_operations", ())) != 2
            or set(adapter.get("forbidden_operations", ())) != FORBIDDEN
            or len(adapter.get("forbidden_operations", ())) != len(FORBIDDEN)
            or set(adapter.get("read_only_input_allowlist", ())) != PINNED_READS
            or len(adapter.get("read_only_input_allowlist", ())) != 2
            or adapter.get("execution_backend") != "NONE_NO_DISPATCHER_NO_SUBPROCESS_NO_IMPORT_LEGACY_MODULES"
            or adapter.get("product_live_call_count") != 0):
        raise ReviewContractError("EXECUTION_OR_INPUT_ALLOWLIST_VIOLATION")

    conflicts = candidate.get("historical_conflicts", {})
    if (conflicts.get("workflow_id_conflict") != "FIRST_CROSS_SPEC_VS_FEX"
            or conflicts.get("prompt_sha_id_binding") != "PROMPT_NAMES_FEX_BUT_SHA_MATCHES_FIRST"
            or conflicts.get("default_action_conflict") != "RUN_ACTIVE_VS_STATUS"
            or conflicts.get("stale_entrypoint_or_config_sha_occurrences") != 4
            or conflicts.get("reconciled_six_pc_hashes") != 6
            or conflicts.get("corrected_sources_applied_to_product_main") is not False):
        raise ReviewContractError("HISTORICAL_CONFLICT_CONCEALED")

    gates = candidate.get("promotion_gates", {})
    if set(gates) != GATES or any(gates[k] is not False for k in GATES):
        raise ReviewContractError("UNAUTHORIZED_PROMOTION_GATE")

    inv = candidate.get("invariants", {})
    if inv != INVARIANTS or candidate.get("verdict") != "REVIEW_ONLY_STATUS_SAFE__ACTIVE_AUTHORITY_NOT_SELECTED":
        raise ReviewContractError("SHARED_AUTHORITY_OR_FROZEN_MUTATION")

    if evidence.get("schema") != "ZrotMainSixPinLocalSnapshotConsistencyV1":
        raise ReviewContractError("BASE_EVIDENCE_SCHEMA_INVALID")
    if evidence.get("source_provenance", {}).get("sha256_comparison") != "SIX_OF_SIX_EXACT":
        raise ReviewContractError("BASE_LOCAL_SIX_SHA_UNVERIFIED")
    if len(evidence.get("verified_user_pc_files", {})) != 6:
        raise ReviewContractError("BASE_SIX_HASH_COUNT_CHANGED")
    source_sha = evidence.get("archived_source_sha256", {})
    if (source_sha.get("02_SOURCE/validation/generalization/FEX_FULL_ENGINE_SYNTHETIC_PROBE_v1.py") != FEX_SHA
            or source_sha.get("02_SOURCE/validation/generalization/CROSS_SPEC_SYNTHETIC_PROBE_v1.py") != FIRST_SHA):
        raise ReviewContractError("BASE_HISTORICAL_WORKFLOW_SOURCE_MISMATCH")
    old = evidence.get("verified_historical_internal_disagreements", {})
    if len(old) != 6 or evidence.get("verdict", {}).get("current_MAIN_authority") != "UNKNOWN":
        raise ReviewContractError("BASE_CONFLICT_OR_UNKNOWN_AUTHORITY_LOST")

    return {
        "schema": "ZrotStatusOnlySuccessorAuthorityReviewReceiptV1",
        "result": "PASS_STATUS_ONLY_PROPOSAL__NO_MAIN_PROMOTION",
        "selected_workflow_id": None,
        "verified_historical_alternatives": 2,
        "historical_PC_file_hashes_pinned": 6,
        "known_historical_conflict_groups": 6,
        "allowed_nonexecuting_operations": sorted(ALLOWED),
        "latest_authoritative_runtime": "UNKNOWN",
        "latest_authoritative_work_state": "UNKNOWN",
        "runtime_or_inbox_executed": False,
        "gameplay_ready_rules": 0,
        "product_MAIN_promoted": False,
        "FROZEN_changed": False,
        "Seq578": "FAILED_QUARANTINED_PRESERVED",
        "Seq637": "UNKNOWN",
    }


def verify_sources() -> tuple[dict, dict]:
    blob = EVIDENCE.read_bytes()
    if git_blob_sha1(blob) != EVIDENCE_GIT_BLOB_SHA1:
        raise ReviewContractError("BASE_EVIDENCE_GIT_BLOB_CHANGED")
    source = CANDIDATE.read_bytes()
    return json.loads(source), json.loads(blob)


def self_test(candidate: dict, evidence: dict) -> dict:
    successes = 0
    def reject(modifier, expected):
        nonlocal successes
        c, e = deepcopy(candidate), deepcopy(evidence)
        modifier(c, e)
        try:
            validate(c, e)
        except ReviewContractError as error:
            assert expected in str(error), (expected, str(error))
            successes += 1
        else:
            raise AssertionError("ILLEGAL_STATUS_AUTHORITY_ACCEPTED")
    reject(lambda c, e: c["workflow_authority"].update({"selected_workflow_id": "FEX_FULL_ENGINE_SYNTHETIC_PROBE_V1"}), "AUTOMATIC_WORKFLOW_SELECTION")
    reject(lambda c, e: c["workflow_authority"].update({"preferred_workflow_id": "FIRST_CROSS_SPEC_SYNTHETIC_PROBE_V1"}), "AUTOMATIC_WORKFLOW_SELECTION")
    reject(lambda c, e: c["status_adapter_contract"].update({"default_operation": "RUN_ACTIVE"}), "EXECUTION_OR_INPUT")
    reject(lambda c, e: c["status_adapter_contract"]["allowed_operations"].append("RUN_ACTIVE"), "EXECUTION_OR_INPUT")
    reject(lambda c, e: c["status_adapter_contract"]["forbidden_operations"].remove("DISPATCH_INBOX"), "EXECUTION_OR_INPUT")
    reject(lambda c, e: c["promotion_gates"].update({"selected_workflow_evidence_verified": True}), "UNAUTHORIZED_PROMOTION")
    reject(lambda c, e: c["invariants"].update({"Seq578": "PASS"}), "SHARED_AUTHORITY")
    reject(lambda c, e: c["base"].update({"github_product_main_head_sha": "0" * 40}), "STALE_OR_FORGED")
    reject(lambda c, e: e["verified_user_pc_files"].pop("RUN_zRAID_MAIN.py"), "BASE_SIX_HASH")
    reject(lambda c, e: e["archived_source_sha256"].update({"02_SOURCE/validation/generalization/FEX_FULL_ENGINE_SYNTHETIC_PROBE_v1.py": "0" * 64}), "BASE_HISTORICAL_WORKFLOW")
    reject(lambda c, e: c["historical_conflicts"].update({"default_action_conflict": "RESOLVED"}), "HISTORICAL_CONFLICT")
    reject(lambda c, e: c.update({"lifecycle": "PROMOTED"}), "LIFECYCLE_PROMOTION")
    reject(lambda c, e: c.update({"run_command": "RUN_ACTIVE"}), "UNKNOWN_AUTHORITY_FIELD_ROOT")
    reject(lambda c, e: c["workflow_authority"].update({"autostart": True}), "UNKNOWN_AUTHORITY_FIELD_WORKFLOW")
    reject(lambda c, e: c["status_adapter_contract"].update({"legacy_entrypoint": "RUN_zRAID_MAIN.py"}), "UNKNOWN_AUTHORITY_FIELD_ADAPTER")
    return {"status": "PASS", "negative_regressions": successes,
            "live_runtime_execution": False, "source_code_execution": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="read and print review-only status; default")
    parser.add_argument("--self-test", action="store_true", help="synthetic negative contract tests")
    args = parser.parse_args()
    try:
        candidate, evidence = verify_sources()
        result = validate(candidate, evidence)
        if args.self_test:
            result["self_test"] = self_test(candidate, evidence)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, AssertionError) as error:
        print(json.dumps({"result": "FAIL_CLOSED", "error": str(error),
                          "runtime_executed": False, "MAIN_promoted": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
