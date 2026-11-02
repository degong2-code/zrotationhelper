#!/usr/bin/env python3
"""Static research overlay comparison to archived private 124-file source.

Never executes or imports gameplay code. Historical source inventory is
a dated fingerprint, NOT present-day WoW gameplay/runtime authority.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/"docs/M4B_124_PRIVATE_SOURCE_AND_RESEARCH_OVERLAY_REVIEW_20261102.json"
EXPECTED={
"02_SOURCE/runtime/raid_dps/core/coverage.py":(2007,"30daad468f43ab012f4d85cb457ba838899bef5ddaf32acb4d14645043ba8147","b10d3ac8338a1734c8ff853b551445749959541f"),
"02_SOURCE/runtime/raid_dps/core/identity.py":(1880,"d2328bef5f7db3fa973cbb99b2125f13d796a5249be3c007219c38509965f8b6","191688a2bf2ce4cebe545f93b2ef56f2a0671a99"),
"02_SOURCE/runtime/raid_dps/core/prestate.py":(7448,"889fdd114f5a07d31612c0fc2a548ac0dfab1dc1d5738e8741f573194efd7d50","93e3ceacabf348d5fd9cdcc6aa612e940eccc54c")
}
class OverlayAuditError(ValueError):pass

def gitblob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\x00"+data).hexdigest()

def audit(doc:dict,root:Path=ROOT)->dict:
    if doc.get("schema")!="ZrotM4BHistorical124ReconciliationV1":
        raise OverlayAuditError("UNRECOGNIZED_RECONCILIATION_SCHEMA")
    source=doc.get("private_inputs",{})
    expected_source={
      "original_stage_registry_zip_sha256":"10375e43ac660e9cfa7e3d1b996aaedc08bac2dbd1eb6b431df030120cac379d",
      "stage_registry_sha256":"9b424b101e615c2f692a16e4aac9b2223a5f19048a3cad7bc5d9729d290bd16e",
      "composite_124_sha256":"46e3a2dd1b51465429932a03efb7345cae781c756137dea9a39c9c4bed152bf6",
      "total_unmodified_source_bytes_count":124,"python_compiled_static":21,
      "json_parsed_static":100,"stage_registry_o0_o8_topological_ast":"PASS",
      "raid_dps_static_import_target_occurrences":24,
      "raid_dps_import_resolved_in_124":21,
      "raid_dps_import_not_in_124":3,
      "archive_original_bytes_uploaded_to_GitHub":False,
      "dynamic_import_and_full_product_runtime":"NOT_VERIFIED"}
    if any(source.get(k)!=v for k,v in expected_source.items()):
        raise OverlayAuditError("PRIVATE_124_SOURCE_ATTESTATION_CHANGED")
    safety=doc.get("safety",{})
    pins={
      "MAIN_current_authority":"UNKNOWN",
      "CANONICAL_REGISTRY":"MISSING",
      "CURRENT_POINTER":"MISSING",
      "product_entrypoint_run":False,
      "product_MAIN_promotion":False,
      "FROZEN_mutation":False,
      "github_main_mutation":False,
      "seq578":"FAILED_QUARANTINED_PRESERVED",
      "seq637":"UNKNOWN"
    }
    if any(safety.get(k)!=v for k,v in pins.items()):
        raise OverlayAuditError("ILLEGAL_PRODUCT_MAIN_OR_FROZEN_PROMOTION")
    overlay=doc.get("research_direct_modules",{})
    if overlay.get("byte_equality_to_current_product")!="NOT_ESTABLISHED":
        raise OverlayAuditError("FALSE_CURRENT_PRODUCT_EQUIVALENCE")
    rows=overlay.get("modules",[])
    if len(rows)!=3 or {r.get("path") for r in rows}!=set(EXPECTED):
        raise OverlayAuditError("RESEARCH_OVERLAY_MISSING_OR_DUPLICATED")
    results=[]
    for item in sorted(rows,key=lambda x:x["path"]):
        path=item["path"]
        expected_size,expected_sha,expected_blob=EXPECTED[path]
        if (item.get("expected_historical_size")!=expected_size or
            item.get("expected_historical_sha256")!=expected_sha or
            item.get("expected_research_git_blob_sha1")!=expected_blob):
            raise OverlayAuditError("HISTORICAL_INVENTORY_PIN_CHANGED_"+path)
        source_path=root/path
        if not source_path.is_file():
            raise OverlayAuditError("RESEARCH_MODULE_MISSING_"+path)
        data=source_path.read_bytes()
        if gitblob(data)!=expected_blob:
            raise OverlayAuditError("RESEARCH_GIT_SOURCE_CHANGED_"+path)
        live_sha=hashlib.sha256(data).hexdigest()
        equality=(live_sha==expected_sha and len(data)==expected_size)
        results.append({"path":path,"checkout_bytes":len(data),"checkout_sha256":live_sha,
                        "historical_size":expected_size,"historical_sha256":expected_sha,
                        "byte_identical_to_inventory":equality,
                        "classification":"MATCH_HISTORICAL_INVENTORY" if equality else "SOURCE_VARIANT_REVIEW_REQUIRED"})
    matched=sum(r["byte_identical_to_inventory"] for r in results)
    return {
        "schema":"ZrotM4B124ResearchOverlayComparisonReceiptV1",
        "result":"PASS_DIAGNOSTIC_NO_AUTOMATIC_PROMOTION",
        "private_source_124_hash":"PINNED_OFFLINE_EVIDENCE_NOT_REPLAYED_IN_CI",
        "research_source_modules_compared":3,
        "historical_inventory_byte_match_count":matched,
        "historical_inventory_byte_mismatch_count":3-matched,
        "module_results":results,
        "static_direct_import_paths_known":True,
        "full_runtime_equivalence":"NOT_VERIFIED",
        "gameplay_readiness_certified":0,
        "main_product_promotion":False,
        "frozen_modified":False,
        "seq578":"FAILED_QUARANTINED_PRESERVED",
        "seq637":"UNKNOWN"}

def self_test(doc:dict)->int:
    n=0
    def reject(f,marker):
        nonlocal n
        d=deepcopy(doc);f(d)
        try:audit(d)
        except OverlayAuditError as e:
            assert marker in str(e),(marker,str(e));n+=1
        else:raise AssertionError("UNAUTHORIZED_PROMOTION_WAS_ACCEPTED")
    reject(lambda d:d["safety"].update({"product_MAIN_promotion":True}),"ILLEGAL_PRODUCT_MAIN")
    reject(lambda d:d["safety"].update({"seq637":"PASS"}),"ILLEGAL_PRODUCT_MAIN")
    reject(lambda d:d["private_inputs"].update({"total_unmodified_source_bytes_count":125}),"PRIVATE_124_SOURCE")
    reject(lambda d:d["research_direct_modules"].update({"byte_equality_to_current_product":"VERIFIED"}),"FALSE_CURRENT_PRODUCT")
    reject(lambda d:d["research_direct_modules"]["modules"][0].update({"expected_historical_sha256":"0"*64}),"HISTORICAL_INVENTORY_PIN_CHANGED")
    return n

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--manifest",type=Path,default=DOC)
    opts=parser.parse_args()
    document=json.loads(opts.manifest.read_text(encoding="utf-8"))
    receipt=audit(document)
    if opts.self_test:receipt["negative_contract_cases"]=self_test(document)
    print(json.dumps(receipt,sort_keys=True,indent=2))
