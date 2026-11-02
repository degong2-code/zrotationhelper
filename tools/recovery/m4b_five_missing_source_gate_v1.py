#!/usr/bin/env python3
"""Fail-closed M4B missing-five source import recovery gate.

The manifest was derived by an independent offline AST parse of actual M4B
15 Python source files. This GitHub gate checks immutable metadata and
repository absence, not those private source bytes. Optional --candidate-zip
checks exact recovered bytes and safe paths, but NEVER imports or runs files.
No gameplay or MAIN authority promotion under any circumstances.
"""
from __future__ import annotations
import argparse
import io
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/"docs/M4B_MISSING_FIVE_DIRECT_IMPORT_RECOVERY_20261102.json"
SCHEMA="ZrotM4BMissingFiveDirectImportRecoveryV1"
EXPECTED={
"02_SOURCE/runtime/raid_dps/core/cohort.py":(6147,"e506e7a7073b88b3bad6909822f5289363bba92218de71f1003a7fc3fc2da600",1),
"02_SOURCE/runtime/raid_dps/core/evidence.py":(8791,"a5a4261168ffb172d95b655c9d320591e5400fe5bdb1425b1d3a54a0b581d27b",2),
"02_SOURCE/runtime/raid_dps/core/renderer.py":(13229,"7c0bf5e1b09d10aec09c89438b18cd302906acf73ef4f24fd6349526e004ca52",1),
"02_SOURCE/runtime/raid_dps/core/wcl_client.py":(13129,"452fb44c4c577b5bbb08ceb431013e165de57e62ef72f59500777d703e42ce24",2),
"02_SOURCE/runtime/raid_dps/pipelines/orchestrator.py":(19606,"fe398aa9238908c21af433ac5652f1730f66cd5dd0209722ebf6371b68d68d0d",5),
}
RESEARCH_ONLY={
"02_SOURCE/runtime/raid_dps/core/coverage.py",
"02_SOURCE/runtime/raid_dps/core/identity.py",
"02_SOURCE/runtime/raid_dps/core/prestate.py",
}

class SourceClosureFailure(ValueError):pass


def audit(doc:dict,root:Path=ROOT)->dict:
    if doc.get("schema")!=SCHEMA or doc.get("source_zip_sha256")!="1cfdff330d90fbf1f25081cc92955e1dddf287840bc015fcc4707bfb1f0098af":
        raise SourceClosureFailure("M4B_PROVENANCE_PIN")
    for key,expected in {
        "historical_modules_ast_parsed":15,
        "historical_python_sha_verified":15,
        "required_raid_dps_module_imports":14,
        "distinct_target_modules":8,
        "missing_direct_modules":5,
        "research_only_modules":3,
        "source_bytes_recovered":None,
        "current_gameplay_ready_certified":0,
        "original_bytes_in_git":False,
        "original_source_restored":False,
        "same_source_zip_public":False,
        "main_or_frozen_promotion":False,
        "seq578":"FAILED_QUARANTINED_PRESERVED",
        "seq637":"UNKNOWN",
        "default_product_execution":"DISABLED",
        "canonical_registry":"MISSING",
        "main_active_pointer":"MISSING",
    }.items():
        if key=="source_bytes_recovered":continue
        if doc.get(key)!=expected:raise SourceClosureFailure("SOURCE_CLOSURE_SCOPE_OR_AUTHORITY_"+key)
    records=doc.get("missing")
    if not isinstance(records,list) or len(records)!=len(EXPECTED):
        raise SourceClosureFailure("FIVE_MISSING_SOURCE_LIST_REQUIRED")
    found={}
    for r in records:
        p=r.get("path")
        if p in found or p not in EXPECTED or (root/p).is_file():
            raise SourceClosureFailure("SOURCE_PATH_DUPLICATE_UNEXPECTED_OR_REAUDIT_REQUIRED")
        size,sha,importers=EXPECTED[p]
        if (r.get("expected_size_bytes")!=size or r.get("expected_sha256")!=sha
            or len(r.get("imported_by",[]))!=importers
            or not all(s.startswith("02_SOURCE/runtime/raid_dps/pipelines/")
                       for s in r["imported_by"])
            or r.get("source_bytes_recovered") is not False
            or r.get("sha_evidence")!="historical SOURCE_INVENTORY metadata only"):
            raise SourceClosureFailure("MISSING_SOURCE_METADATA_MISMATCH_"+p)
        found[p]=r
    research=doc.get("research_only")
    if not isinstance(research,list) or set(research)!=RESEARCH_ONLY or len(research)!=3:
        raise SourceClosureFailure("RESEARCH_ONLY_MODULE_SCOPE")
    if not all((root/p).is_file() for p in RESEARCH_ONLY):
        raise SourceClosureFailure("RESEARCH_DEPENDENCY_SOURCE_MISSING")
    if doc.get("scope_limit")!="direct static package imports only; runtime dynamic/transitive dependency completeness NOT_PROVEN":
        raise SourceClosureFailure("FALSE_COMPLETE_DEPENDENCY_CLAIM")
    return {"schema":"ZrotM4BFiveMissingModulesGitHubGateReceiptV1",
            "status":"PASS_METADATA_AND_REPOSITORY_ABSENCE__MAIN_BLOCKED",
            "historical_ast_evidence":"OFFLINE_PRIVATE_SOURCE_REPLAY_NOT_IN_GITHUB_CI",
            "previous_missing_count":3,
            "corrected_minimum_direct_missing_count":5,
            "full_source_bytes_in_github":False,
            "safe_recovered_original_bytes":0,
            "current_product_main_recovered":False,
            "gameplay_ready_certified":0,
            "promotion":False,
            "seq578":"FAILED_QUARANTINED_PRESERVED",
            "seq637":"UNKNOWN"}


def audit_candidate_bytes(raw: bytes, expected: dict = EXPECTED) -> dict:
    """Accept canonical POSIX or Windows PowerShell Compress-Archive paths.

    Only exactly named, size/hash-pinned files may appear. Empty directory
    entries emitted by Compress-Archive are ignored; no source is executed.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.testzip() is not None:
            raise SourceClosureFailure("CANDIDATE_ZIP_CRC_FAIL")
        normalized = {}
        for info in z.infolist():
            logical = info.filename.replace("\\", "/")
            parts = PurePosixPath(logical).parts
            if (not logical or logical.startswith("/")
                    or ".." in parts or "." in parts or ":" in logical):
                raise SourceClosureFailure("CANDIDATE_UNSAFE_PATH")
            mode = info.external_attr >> 16
            if info.create_system == 3 and (mode & 0o170000) == 0o120000:
                raise SourceClosureFailure("CANDIDATE_SYMLINK_REJECTED")
            if logical.endswith("/"):
                if info.file_size != 0:
                    raise SourceClosureFailure("CANDIDATE_NONEMPTY_DIRECTORY")
                continue
            if logical in normalized:
                raise SourceClosureFailure("CANDIDATE_ZIP_FILESET_DUPLICATE")
            normalized[logical] = info
        required = {"payload/" + p for p in expected}
        if set(normalized) != required:
            raise SourceClosureFailure("CANDIDATE_ZIP_FILESET_MISMATCH")
        for name, info in normalized.items():
            payload = z.read(info)
            n, digest, _ = expected[name.removeprefix("payload/")]
            if len(payload) != n or hashlib.sha256(payload).hexdigest() != digest:
                raise SourceClosureFailure("CANDIDATE_SOURCE_BYTES_MISMATCH")
    return {"status": "EXACT_FIVE_HISTORICAL_SOURCE_BYTES_VERIFIED_ONLY",
            "source_count": len(expected), "product_runtime_executed": False,
            "product_main_promotion": False}


def audit_candidate_zip(path: Path) -> dict:
    return audit_candidate_bytes(path.read_bytes())


def zip_format_self_test() -> dict:
    """No historical source bytes: synthetic ZIPs test path handling only."""
    fake_path = "02_SOURCE/runtime/raid_dps/core/cohort.py"
    good = b"safe-synthetic"
    digest = hashlib.sha256(good).hexdigest()
    expected = {fake_path: (len(good), digest, 1)}
    good_win = "payload\\" + fake_path.replace("/", "\\")
    good_posix = "payload/" + fake_path

    def build(items):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for name, body in items:
                z.writestr(name, body)
        return buf.getvalue()

    positive = [
        build([("payload\\02_SOURCE\\", b""), (good_win, good)]),
        build([(good_posix, good)]),
    ]
    for raw in positive:
        assert audit_candidate_bytes(raw, expected)["source_count"] == 1

    cases = (
        ([(good_win, b"bad-synthetic")], "CANDIDATE_SOURCE_BYTES_MISMATCH"),
        ([(good_win, good), (good_posix, good)], "CANDIDATE_ZIP_FILESET_DUPLICATE"),
        ([(good_win, good), ("payload\\..\\traverse.py", b"evil")], "CANDIDATE_UNSAFE_PATH"),
        ([(good_win, good), ("payload\\extra.py", b"oops")], "CANDIDATE_ZIP_FILESET_MISMATCH"),
    )
    for items, expected_error in cases:
        try:
            audit_candidate_bytes(build(items), expected)
        except SourceClosureFailure as exc:
            assert expected_error in str(exc), (expected_error, str(exc))
        else:
            raise AssertionError("UNSAFE_CANDIDATE_ZIP_ACCEPTED")
    return {"synthetic_windows_format_positive": 1,
            "synthetic_posix_format_positive": 1,
            "synthetic_format_negative_cases": len(cases),
            "historical_raw_bytes_read_in_test": False}


def self_test(doc:dict):
    count=0
    def reject(mut,phrase):
        nonlocal count
        data=deepcopy(doc);mut(data)
        try:audit(data)
        except SourceClosureFailure as e:
            assert phrase in str(e),(phrase,str(e))
            count+=1
        else:raise AssertionError("ILLEGAL_CLOSURE_ACCEPTED")
    reject(lambda d:d.update({"missing_direct_modules":3}),"SOURCE_CLOSURE_SCOPE_OR_AUTHORITY")
    reject(lambda d:d.update({"main_or_frozen_promotion":True}),"SOURCE_CLOSURE_SCOPE_OR_AUTHORITY")
    reject(lambda d:d["missing"].pop(),"FIVE_MISSING_SOURCE_LIST")
    reject(lambda d:d["missing"][0].update({"source_bytes_recovered":True}),"MISSING_SOURCE_METADATA_MISMATCH")
    reject(lambda d:d["missing"][0].update({"expected_sha256":"0"*64}),"MISSING_SOURCE_METADATA_MISMATCH")
    reject(lambda d:d.update({"original_source_restored":True}),"SOURCE_CLOSURE_SCOPE_OR_AUTHORITY")
    reject(lambda d:d.update({"default_product_execution":"RUN_ACTIVE"}),"SOURCE_CLOSURE_SCOPE_OR_AUTHORITY")
    reject(lambda d:d.update({"scope_limit":"complete"}),"FALSE_COMPLETE_DEPENDENCY_CLAIM")
    return count


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--document",type=Path,default=DOC)
    p.add_argument("--candidate-zip",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    doc=json.loads(args.document.read_text(encoding="utf-8"))
    result=audit(doc)
    if args.self_test:
        result["negative_contract_tests"]=self_test(doc)
        result["zip_format_self_test"]=zip_format_self_test()
    if args.candidate_zip:result["optional_historical_bytes"]=audit_candidate_zip(args.candidate_zip)
    print(json.dumps(result,sort_keys=True,indent=2))
