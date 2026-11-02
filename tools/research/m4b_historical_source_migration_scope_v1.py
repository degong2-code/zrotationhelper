#!/usr/bin/env python3
"""M4B source migration scope: verify recovery receipt and missing dependencies.

Historical evidence is produced by an offline raw-archive audit. GitHub does
NOT contain the private original M4B ZIP, so this script verifies the published
sanitized receipt and current checkout dependency classification, NOT the 118
archived source bytes. It cannot authorize execution or product promotion.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/"docs/PRODUCT_MAIN_HISTORICAL_SOURCE_RECOVERY_20261102.json"
OLD_MISSING={
    "02_SOURCE/runtime/raid_dps/core/renderer.py",
    "02_SOURCE/runtime/raid_dps/core/wcl_client.py",
    "02_SOURCE/runtime/raid_dps/pipelines/orchestrator.py",
}
HISTORICAL_ONLY={
    "RUN_zRAID_MAIN.py",
    "02_SOURCE/runtime/raid_dps/pipelines/discovery_mining.py",
    "02_SOURCE/runtime/raid_dps/pipelines/independent_validation.py",
    "02_SOURCE/validation/generalization/FEX_FULL_ENGINE_SYNTHETIC_PROBE_v1.py",
}
RESEARCH_ONLY={
    "02_SOURCE/runtime/raid_dps/core/coverage.py",
    "02_SOURCE/runtime/raid_dps/core/identity.py",
    "02_SOURCE/runtime/raid_dps/core/prestate.py",
}
DEFAULT_NO_EXEC={
    "candidate_default_execution":"DISABLED",
    "historical_product_entrypoint_executed":False,
    "historical_product_runtime_executed":False,
    "current_client_action_ids_certified":0,
    "new_gameplay_ready_rules_certified":0,
    "FROZEN_modified":False,
    "GitHub_main_modified":False,
    "product_MAIN_promoted":False,
    "seq578":"FAILED_QUARANTINED_PRESERVED",
    "seq637":"UNKNOWN",
}
class MigrationScopeError(ValueError):pass


def evaluate(doc:dict,root:Path=ROOT)->dict:
    if not isinstance(doc,dict) or doc.get("schema")!="ZrotHistoricalProductSourceMigrationAssessmentV1":
        raise MigrationScopeError("SOURCE_RECOVERY_SCHEMA_INVALID")
    archive=doc.get("source",{})
    if (
        archive.get("source_archival_purpose")!="UNMODIFIED_HISTORICAL_FILES_FOR_PRIVATE_REVIEW"
        or archive.get("private_recovery_zip_n")!=118
        or archive.get("private_recovery_file_types")!={"py":15,"json":100,"md":3}
        or archive.get("per_file_source_copy_byte_parity")!="118_OF_118_PASS"
        or archive.get("snapshot_currentness")!="NOT_VERIFIED"
        or archive.get("original_archive_public_released") is not False
        or archive.get("full_private_source_inventory_map_sha256")!="510bb8341d1018e05eda7183e3f87c24d6f1c638a9f06498840c58f87888a6f8"
    ):
        raise MigrationScopeError("UNVERIFIED_PRIVATE_ARCHIVE_PROOF_OR_FALSE_CURRENTNESS")
    if (
        doc.get("verdict")!="HISTORICAL_SOURCE_RECOVERY_PASS__PRODUCT_MAIN_MIGRATION_BLOCKED"
        or doc.get("research",{}).get("locally_recovered_source_claim")!="NO_GITHUB_FULL_ARCHIVE_UPLOAD"
    ):
        raise MigrationScopeError("PRODUCT_MIGRATION_UNAUTHORIZED")
    authority=doc.get("authority",{})
    for k,v in DEFAULT_NO_EXEC.items():
        if authority.get(k)!=v:
            raise MigrationScopeError("ILLEGAL_PRODUCT_RUNTIME_CHANGE_"+k)
    if authority.get("canonical_registry")!="MISSING" or authority.get("current_pointer")!="MISSING" or authority.get("current_runtime_work_state")!="UNKNOWN":
        raise MigrationScopeError("FALSIFIED_CANONICAL_MAIN_AUTHORITY")
    conflicts=doc.get("historical_control_conflicts",{})
    if set(conflicts)!={"WORKFLOW_ID","ACTIVE_WORKFLOW_SHA","DEFAULT_ACTION"} or any(not isinstance(v,list) or len(v)!=2 or v[0]==v[1] for v in conflicts.values()):
        raise MigrationScopeError("MISSING_HISTORICAL_CONFLICTS")
    deps=doc.get("runtime_dependencies",{})
    expected={
        "missing_from_both_m4b_and_research":OLD_MISSING,
        "archived_original_present_but_missing_from_research":HISTORICAL_ONLY,
        "available_in_research_but_not_in_archival_m4b":RESEARCH_ONLY,
    }
    for field,items in expected.items():
        got=deps.get(field)
        if not isinstance(got,list) or set(got)!=items or len(got)!=len(items):
            raise MigrationScopeError("DEPENDENCY_SCOPE_MISMATCH_"+field)
        # A newly populated source path needs fresh comparison to original
        # bytes and semantics, never silent reclassification.
        for path in items:
            present=(root/path).is_file()
            should_exist=(field=="available_in_research_but_not_in_archival_m4b")
            if present!=should_exist:
                raise MigrationScopeError("CHECKOUT_CHANGE_NEEDS_REAUDIT_"+path)
    if deps.get("full_product_dependency_closure")!="NOT_COMPLETE" or deps.get("exact_source_merging_performed") is not False:
        raise MigrationScopeError("FALSE_PRODUCTION_COMPLETENESS")
    pins=doc.get("selected_historical_source_sha256",{})
    if not isinstance(pins,dict) or len(pins)!=7 or any(not isinstance(v,str) or len(v)!=64 for v in pins.values()):
        raise MigrationScopeError("SELECTED_ORIGINAL_SOURCE_PINS_INVALID")
    return {
        "schema":"ZrotM4BSourceRecoveryGithubScopeReceiptV1",
        "status":"PASS_GITHUB_DEPENDENCY_TRIAGE__MAIN_EXECUTION_BLOCKED",
        "historical_original_file_count":118,
        "historical_exact_bytes_verified_by":"LOCAL_ARCHIVE_AUDIT_NOT_BY_GITHUB_CI",
        "missing_runtime_dependency_count":len(OLD_MISSING),
        "original_source_not_in_research_count":len(HISTORICAL_ONLY),
        "github_research_only_dependency_count":len(RESEARCH_ONLY),
        "known_main_authority_conflict_count":3,
        "current_main_authority":"UNKNOWN",
        "product_run_executed":False,
        "production_promotion":False,
        "sha_receipt_source":"OFFLINE_LOCAL_VERIFICATION_REFERENCE_ONLY",
        "seq578":"FAILED_QUARANTINED_PRESERVED",
        "seq637":"UNKNOWN"
    }


def self_test(doc:dict)->int:
    n=0
    def reject_case(fn,tag):
        nonlocal n
        data=deepcopy(doc)
        fn(data)
        try:evaluate(data)
        except MigrationScopeError as exc:
            assert tag in str(exc),(tag,str(exc))
            n+=1
        else:
            raise AssertionError("INVALID_MIGRATION_STATE_ACCEPTED_"+tag)
    reject_case(lambda d:d["authority"].update({"product_MAIN_promoted":True}),"ILLEGAL_PRODUCT_RUNTIME_CHANGE")
    reject_case(lambda d:d["authority"].update({"candidate_default_execution":"RUN_ACTIVE"}),"ILLEGAL_PRODUCT_RUNTIME_CHANGE")
    reject_case(lambda d:d["authority"].update({"canonical_registry":"READY"}),"FALSIFIED_CANONICAL_MAIN")
    reject_case(lambda d:d["historical_control_conflicts"].pop("WORKFLOW_ID"),"MISSING_HISTORICAL_CONFLICTS")
    reject_case(lambda d:d["runtime_dependencies"]["missing_from_both_m4b_and_research"].pop(),"DEPENDENCY_SCOPE_MISMATCH")
    reject_case(lambda d:d["runtime_dependencies"].update({"full_product_dependency_closure":"COMPLETE"}),"FALSE_PRODUCTION_COMPLETENESS")
    reject_case(lambda d:d["source"].update({"private_recovery_zip_n":119}),"UNVERIFIED_PRIVATE_ARCHIVE")
    reject_case(lambda d:d["source"].update({"snapshot_currentness":"PROMOTED_MAIN"}),"UNVERIFIED_PRIVATE_ARCHIVE")
    return n


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--document",type=Path,default=DOC)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    payload=json.loads(args.document.read_text(encoding="utf-8"))
    receipt=evaluate(payload)
    if args.self_test:receipt["synthetic_policy_negative_cases"]=self_test(payload)
    print(json.dumps(receipt,indent=2,sort_keys=True))
