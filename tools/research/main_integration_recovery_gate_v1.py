#!/usr/bin/env python3
"""MAIN integration gate: historical compatibility review, never promotion.

No product entrypoint, WCL, SimC or network request. GitHub main is NOT the
local product MAIN. Requires actual current Runtime/Registry/Pointer and
resolved pins before any product promotion. This script audits ONLY the
provided historical evidence and exact Git blobs in this research checkout.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
DOCUMENT=ROOT/"docs"/"MAIN_INTEGRATION_RECOVERY_EVIDENCE_20261102.json"
SCHEMA="ZrotMainIntegrationRecoveryEvidenceV1"
EXPECTED_MAIN="4790f77f76a75f26ff0558d1d18c16cd9d630c4b"
REQUIRED=(
    "03_DATA/03_MANIFESTS/CANONICAL_REGISTRY.json",
    "03_DATA/03_MANIFESTS/CURRENT_POINTER.json",
)
RESEARCH_ONLY={
    "product_main_promotion":"BLOCKED",
    "research_ST01_ST06_production_promotion":False,
    "frozen_mutated":False,
    "github_main_mutated":False,
    "current_authority_recovered":False,
}
class IntegrationContractError(ValueError):
    pass


def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\x00"+data).hexdigest()


def audit(document:dict, root:Path=ROOT)->dict:
    if not isinstance(document,dict) or document.get("schema")!=SCHEMA:
        raise IntegrationContractError("INVALID_RECOVERY_EVIDENCE_SCHEMA")
    if document.get("main_product_promotion")!="BLOCKED":
        raise IntegrationContractError("UNAUTHORIZED_MAIN_PROMOTION")
    for field,expected in RESEARCH_ONLY.items():
        if document.get(field)!=expected:
            raise IntegrationContractError("INCONSISTENT_UNPROMOTED_BOUNDARY_"+field)
    missing=document.get("missing_current_authority")
    if not isinstance(missing,list) or any(x not in missing for x in REQUIRED):
        raise IntegrationContractError("CANONICAL_MISSING_FILE_NOT_RETAINED")
    history=document.get("historical_snapshots")
    if (not isinstance(history,list) or len(history)!=2
        or {x.get("id") for x in history}!={"M4A","M4B"}
        or {x.get("manifest_payload_hashes") for x in history}!={"54/54_PASS","118/118_PASS"}
        or any(x.get("authority_claim")!="NONE_SOURCE_BYTES_FOR_REVIEW_ONLY" for x in history)):
        raise IntegrationContractError("HISTORICAL_AUTHORITY_FALSE_PROMOTION")
    conflicts=document.get("archival_control_conflicts")
    if (not isinstance(conflicts,list) or
        {x.get("id") for x in conflicts}!={"WORKFLOW_ID","ACTIVE_WORKFLOW_SHA","DEFAULT_ACTION"}):
        raise IntegrationContractError("AUTHORITY_CONFLICTS_NOT_FULLY_RETAINED")
    for item in conflicts:
        values=[v for k,v in item.items() if k!="id"]
        if len(values)!=2 or not all(isinstance(v,str) and v for v in values) or values[0]==values[1]:
            raise IntegrationContractError("HISTORICAL_CONFLICT_INVALID_OR_ERASED")
    git=document.get("github")
    if not isinstance(git,dict) or git.get("observed_main_sha")!=EXPECTED_MAIN:
        raise IntegrationContractError("GITHUB_MAIN_BASE_NOT_PINNED")
    if git.get("observed_main_files")!=["README.md"]:
        raise IntegrationContractError("GITHUB_MAIN_PRODUCT_AUTHORITY_NOT_DEMONSTRATED")
    expected=git.get("old_m4b_to_research_exact_git_blob_sha")
    if not isinstance(expected,dict) or len(expected)!=4:
        raise IntegrationContractError("MISSING_FOCUSED_COMPAT_SOURCE_PINS")
    proofs=[]
    for rel,pin in sorted(expected.items()):
        if not isinstance(rel,str) or not rel.startswith("02_SOURCE/"):
            raise IntegrationContractError("UNSCOPED_COMPAT_FILE")
        path=root/rel
        if not path.is_file():
            raise IntegrationContractError("MISSING_RESEARCH_SOURCE_"+rel)
        sha=git_blob(path.read_bytes())
        if sha!=pin:
            raise IntegrationContractError("HISTORICAL_BYTE_COMPAT_CONFLICT_"+rel)
        proofs.append({"path":rel,"git_blob_sha1":sha,"byte_match":True})
    absences=git.get("known_missing_from_research_branch")
    if not isinstance(absences,list) or len(absences)!=4:
        raise IntegrationContractError("MISSING_PRODUCT_SOURCE_SCOPE_LOST")
    if any((root/rel).exists() for rel in absences):
        raise IntegrationContractError("RESEARCH_SNAPSHOT_SCOPE_CHANGED_REVIEW_REQUIRED")
    return {
        "schema":"ZrotMainIntegrationRecoveryFocusedGateReceiptV1",
        "status":"PASS_HISTORICAL_SOURCE_COMPATIBILITY__PRODUCT_MAIN_BLOCKED",
        "verified_historical_git_blobs":proofs,
        "verified_historical_count":len(proofs),
        "historical_snapshot_claim":"READ_ONLY_INTEGRITY_NOT_AUTHORITY",
        "current_product_main_runtime":"UNKNOWN",
        "canonical_registry":"MISSING",
        "active_pointer":"MISSING",
        "main_git_branch_product_authority":"NOT_ESTABLISHED",
        "research_staging_compatible_for_review":True,
        "research_full_product_equivalence":"NOT_PROVEN",
        "main_product_promotion":False,
        "shared_frozen_mutation":False,
        "seq578":"FAILED_QUARANTINED_PRESERVED",
        "seq637":"UNKNOWN",
        "actual_live_api_simc_wcl":"NOT_RUN"
    }


def self_test(document:dict):
    assert audit(document)["verified_historical_count"]==4
    count=0
    def rejected(modify,tag):
        nonlocal count
        d=deepcopy(document);modify(d)
        try:audit(d)
        except IntegrationContractError as e:
            assert tag in str(e),(tag,str(e))
            count+=1
        else:raise AssertionError("INVALID_PROMOTION_POLICY_ACCEPTED_"+tag)
    rejected(lambda d:d.__setitem__("main_product_promotion","APPROVED"),"UNAUTHORIZED_MAIN_PROMOTION")
    rejected(lambda d:d.__setitem__("current_authority_recovered",True),"INCONSISTENT_UNPROMOTED_BOUNDARY")
    rejected(lambda d:d["missing_current_authority"].remove(REQUIRED[0]),"CANONICAL_MISSING_FILE_NOT_RETAINED")
    rejected(lambda d:d["archival_control_conflicts"].pop(),"AUTHORITY_CONFLICTS_NOT_FULLY_RETAINED")
    rejected(lambda d:d["github"]["old_m4b_to_research_exact_git_blob_sha"].update(
        {"02_SOURCE/runtime/raid_dps/specs/protocol.py":"0"*40}),"HISTORICAL_BYTE_COMPAT_CONFLICT")
    rejected(lambda d:d["github"].update({"observed_main_files":["README.md","RUN_zRAID_MAIN.py"]}),"GITHUB_MAIN_PRODUCT_AUTHORITY_NOT_DEMONSTRATED")
    return count


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--audit",type=Path,default=DOCUMENT)
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    data=json.loads(args.audit.read_text(encoding="utf-8"))
    output=audit(data)
    if args.self_test:
        output["focused_negative_self_test_cases"]=self_test(data)
        output["focused_negative_self_test_status"]="PASS"
    print(json.dumps(output,sort_keys=True,indent=2))

if __name__=="__main__":
    main()
