#!/usr/bin/env python3
"""Content-pinned research successor gate. Never modifies product MAIN.

The successor is an immutable RESEARCH source candidate, not a recovery of
the user's latest local MAIN Runtime or a gameplay readiness certification.
Review contract inputs before using the historical snapshot as evidence.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"active/branches/BR-RESEARCH-SUCCESSOR-20261102/RESEARCH_SUCCESSOR_BASELINE_CANDIDATE_V1.json"
SCHEMA="ZrotResearchSuccessorBaselineCandidateV1"
UNRESOLVED=("03_DATA/03_MANIFESTS/CANONICAL_REGISTRY.json","03_DATA/03_MANIFESTS/CURRENT_POINTER.json",
            "APPROVED_CURRENT_RUNTIME_WORK_STATE","ACTIVE_PRODUCTION_MANIFEST")
STAGES=tuple("ST0"+str(i) for i in range(1,7))


class ResearchBaselineError(ValueError): pass


def git_blob(data:bytes)->str:
    return sha1(b"blob "+str(len(data)).encode("ascii")+b"\x00"+data).hexdigest()


def audit(manifest:dict,base:Path=ROOT)->dict:
    if not isinstance(manifest,dict) or manifest.get("schema")!=SCHEMA:
        raise ResearchBaselineError("UNKNOWN_BASELINE_SCHEMA")
    if (manifest.get("designation")!="CANDIDATE_RESEARCH_BASELINE_NOT_PRODUCT_MAIN"
        or manifest.get("owner_scope")!="BRANCH_LOCAL_PORTABLE_CANDIDATE"):
        raise ResearchBaselineError("UNAUTHORIZED_PRODUCT_AUTHORITY")
    if manifest.get("parent_review_sha")!="9cc87e3f8ac6a717e32563ff3269ad4fc83fffc2":
        raise ResearchBaselineError("STALE_OR_UNPINNED_REVIEW_BASE")
    prior=manifest.get("historical_product_baseline",{})
    if (prior.get("status")!="NOT_RECOVERED"
        or prior.get("default_execution")!="DISABLED"
        or not prior.get("historical_frozen_immutable")
        or prior.get("M4A_payload")!="54/54_OFFLINE_SHA_CRC_PASS_HISTORICAL_ONLY"
        or prior.get("M4B_payload")!="118/118_OFFLINE_SHA_CRC_PASS_HISTORICAL_ONLY"):
        raise ResearchBaselineError("PRODUCT_MAIN_CURRENTNESS_FALSE_ASSERTION")
    if not isinstance(prior.get("missing_required"),list) or any(
        x not in prior["missing_required"] for x in UNRESOLVED):
        raise ResearchBaselineError("MISSING_PRODUCT_AUTHORITY_UNACKNOWLEDGED")
    if set(prior.get("conflicting_historical_pins",()))!={
        "WORKFLOW_ID","ACTIVE_WORKFLOW_SHA","DEFAULT_ACTION"}:
        raise ResearchBaselineError("HISTORICAL_PIN_CONFLICT_LOST")
    main=manifest.get("github_main",{})
    if (main.get("commit")!="4790f77f76a75f26ff0558d1d18c16cd9d630c4b"
        or main.get("role")!="README_ONLY_BOOTSTRAP_NOT_PRODUCT_RUNTIME"
        or main.get("modify") is not False):
        raise ResearchBaselineError("GITHUB_MAIN_NOT_PRODUCT_AUTHORITY")
    lifecycle=manifest.get("lifecycle",{})
    expected={
        "status":"BRANCH_VALIDATED_RESEARCH_CANDIDATE_ONLY",
        "source_complete":"NOT_PROVEN","source_producer_complete":"NOT_PROVEN",
        "current_game_id":"UNKNOWN","gameplay_ready_certified":0,
        "user_action_eligible":False,"wcl_independent_blind_lock":"NOT_RUN_IN_THIS_BUNDLE",
        "simc_blind_join":"FORBIDDEN_PRE_LOCK",
        "WCL_causality_or_priority":"NOT_CERTIFIED","blizzard_current":"NOT_VERIFIED",
        "main_product_promotion":False,"frozen_promotion":False,
        "shared_runtime_mutation":False,"active_pointer_mutation":False,
        "seq578":"FAILED_QUARANTINED_PRESERVED","seq637":"UNKNOWN"
    }
    if any(lifecycle.get(k)!=v for k,v in expected.items()):
        raise ResearchBaselineError("ILLEGAL_LIFECYCLE_OR_PROMOTION")
    source=manifest.get("research_source",{})
    pins=source.get("pinned_git_blobs")
    if (not isinstance(pins,dict) or len(pins)!=21
        or source.get("all_pins")!="EXACT_PIN_MATCH_REQUIRED"):
        raise ResearchBaselineError("SOURCE_PIN_MANIFEST_INCOMPLETE")
    verified=[]
    for path,expected_sha in sorted(pins.items()):
        if (not isinstance(path,str) or path.startswith("/") or ".." in Path(path).parts
            or not (path.startswith("tools/research/") or path.startswith("docs/")
                    or path.startswith("02_SOURCE/"))
            or not isinstance(expected_sha,str) or len(expected_sha)!=40):
            raise ResearchBaselineError("UNSAFE_OR_INVALID_SOURCE_PIN")
        actual=base/path
        if not actual.is_file() or git_blob(actual.read_bytes())!=expected_sha:
            raise ResearchBaselineError("SOURCE_FILE_MISSING_OR_CHANGED:"+path)
        verified.append(path)
    for missing in ("RUN_zRAID_MAIN.py","03_DATA/03_MANIFESTS/CURRENT_POINTER.json",
                    "03_DATA/03_MANIFESTS/CANONICAL_REGISTRY.json"):
        if (base/missing).exists():
            raise ResearchBaselineError("PRODUCT_RUNTIME_NEWLY_PRESENT_REVALIDATION_REQUIRED")
    prior_ci=manifest.get("validation",{}).get("prior_evidence",{})
    if not isinstance(prior_ci,dict) or set(prior_ci)!=set(STAGES)|{"MAIN_REVIEW"}:
        raise ResearchBaselineError("STAGE_EVIDENCE_INCOMPLETE")
    if any(not isinstance(prior_ci[s].get("run_id"),int) or
           prior_ci[s]["run_id"]<=0 for s in (*STAGES,"MAIN_REVIEW")):
        raise ResearchBaselineError("INVALID_PINNED_RUN_IDS")
    val=manifest.get("validation",{})
    if (val.get("successor_ci")!="NOT_VALIDATED_UNTIL_ACTUAL_GITHUB_RUN"
        or val.get("product_main_integration")!="NOT_EXECUTED"
        or val.get("ST06_cpp_rebuild")!="NOT_INCLUDED_REUSE_PINNED_RUN"):
        raise ResearchBaselineError("REUSED_NATIVE_EVIDENCE_MISREPRESENTED")
    return {
        "schema":"ZrotResearchSuccessorBaselineGateReceiptV1",
        "status":"PASS_RESEARCH_SOURCE_PINS__PRODUCT_MAIN_BLOCKED",
        "pinned_source_file_count":len(verified),
        "pinned_source_files":verified,
        "historical_main_state":"NOT_RECOVERED",
        "verified_gameplay_ready_n":0,
        "source_gate_current_client_authority":"NOT_VERIFIED",
        "WCL_BLIND_LOCK":"NOT_RUN_IN_THIS_BUNDLE",
        "prior_ST01_ST06_ci":"REFERENCED_NOT_RERUN_AS_NATIVE",
        "production_runtime_status":"NOT_RUN",
        "main_product_promotion":False,"active_pointer_promotion":False,
        "seq578":"FAILED_QUARANTINED_PRESERVED","seq637":"UNKNOWN"
    }


def selftest(base:dict)->int:
    n=0
    def invalid(modify,label):
        nonlocal n
        d=deepcopy(base);modify(d)
        try:audit(d)
        except ResearchBaselineError as e:
            assert label in str(e),(label,str(e))
            n+=1
        else:
            raise AssertionError("ILLEGAL_STATE_WAS_ACCEPTED:"+label)
    invalid(lambda d:d["lifecycle"].update({"main_product_promotion":True}),"ILLEGAL_LIFECYCLE")
    invalid(lambda d:d["lifecycle"].update({"gameplay_ready_certified":1}),"ILLEGAL_LIFECYCLE")
    invalid(lambda d:d["historical_product_baseline"].update({"status":"RECOVERED"}),"PRODUCT_MAIN_CURRENTNESS")
    invalid(lambda d:d["historical_product_baseline"]["missing_required"].remove(UNRESOLVED[0]),"MISSING_PRODUCT_AUTHORITY")
    invalid(lambda d:d["research_source"]["pinned_git_blobs"].update({
        "tools/research/ST03_source_pre_observability_v1.py":"0"*40}),"SOURCE_FILE_MISSING_OR_CHANGED")
    invalid(lambda d:d["validation"].update({"ST06_cpp_rebuild":"PASS_THIS_RUN"}),"REUSED_NATIVE_EVIDENCE")
    invalid(lambda d:d["lifecycle"].update({"simc_blind_join":"ALLOW"}),"ILLEGAL_LIFECYCLE")
    invalid(lambda d:d["github_main"].update({"role":"PRODUCT_MAIN"}),"GITHUB_MAIN_NOT_PRODUCT")
    return n


if __name__=="__main__":
    arg=argparse.ArgumentParser()
    arg.add_argument("--manifest",type=Path,default=MANIFEST)
    arg.add_argument("--self-test",action="store_true")
    opts=arg.parse_args()
    source=json.loads(opts.manifest.read_text(encoding="utf-8"))
    proof=audit(source)
    if opts.self_test:
        proof["negative_regression_passed"]=selftest(source)
    print(json.dumps(proof,sort_keys=True,indent=2))
