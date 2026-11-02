#!/usr/bin/env python3
"""Research overlay AST interface compatibility review, never product execution.

This gate checks public checkout source bytes and callable signatures against
an independent offline AST audit of 124 private historical files. The private
sources remain absent from GitHub. No importlib, subprocess, network or runtime
module import is used. A structural PASS is not gameplay or MAIN promotion.
"""
from __future__ import annotations
import argparse
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/"docs/MAIN_124_FEX_STATIC_INTERFACE_COMPATIBILITY_20261102.json"
PINS={
 "02_SOURCE/runtime/raid_dps/core/coverage.py":(
   "30daad468f43ab012f4d85cb457ba838899bef5ddaf32acb4d14645043ba8147",
   "b10d3ac8338a1734c8ff853b551445749959541f",
   "coverage_record","function","NO_POSITIONAL_FIVE_KEYWORDS"),
 "02_SOURCE/runtime/raid_dps/core/identity.py":(
   "d2328bef5f7db3fa973cbb99b2125f13d796a5249be3c007219c38509965f8b6",
   "191688a2bf2ce4cebe545f93b2ef56f2a0671a99",
   "event_ability_id","function","ONE_POSITIONAL"),
 "02_SOURCE/runtime/raid_dps/core/prestate.py":(
   "889fdd114f5a07d31612c0fc2a548ac0dfab1dc1d5738e8741f573194efd7d50",
   "93e3ceacabf348d5fd9cdcc6aa612e940eccc54c",
   "AuraIdIndex","class_init","ONE_POSITIONAL"),
}
class CompatibilityError(ValueError):pass

def blob_sha1(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()

def accept_signature(tree:ast.Module,symbol:str,kind:str)->bool:
    obj=next((n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==symbol),None)
    if kind=="function":
        if not isinstance(obj,ast.FunctionDef):return False
        a=obj.args
        if symbol=="coverage_record":
            return (
                not a.posonlyargs and not a.args and a.vararg is None
                and a.kwarg is None
                and [k.arg for k in a.kwonlyargs]==[
                  "field","covered","total","semantic_mask","semantic_route"]
                and len(a.kw_defaults)==5
                and a.kw_defaults[:3]==[None,None,None]
            )
        return (
            symbol=="event_ability_id" and len(a.posonlyargs)==0
            and [x.arg for x in a.args]==["event"] and not a.defaults
            and a.vararg is None and a.kwarg is None and not a.kwonlyargs
        )
    if kind!="class_init" or not isinstance(obj,ast.ClassDef):return False
    fn=next((n for n in obj.body if isinstance(n,ast.FunctionDef) and n.name=="__init__"),None)
    if fn is None:return False
    a=fn.args
    return (not a.posonlyargs and [x.arg for x in a.args]==["self","events"]
            and not a.defaults and a.vararg is None and a.kwarg is None
            and not a.kwonlyargs)

def check_manifest(d:dict):
    if d.get("schema")!="ZrotMain124FexStaticInterfaceCompatibilityCandidateV1":
        raise CompatibilityError("DOCUMENT_SCHEMA_NOT_RECOGNIZED")
    src=d.get("source_provenance",{})
    contract={
      "private_historical_124_zip_sha256":"46e3a2dd1b51465429932a03efb7345cae781c756137dea9a39c9c4bed152bf6",
      "private_local_independent_receipt_sha256":"7a3dfc30bad818199f15288f2f380867a7a8997105c20bc9c7e39024fb5f97a7",
      "private_original_file_count":124,"python_ast_source_files":21,
      "json_parse_sources":100,"private_archive_raw_bytes_in_github":False,
      "private_source_audited_local_no_gameplay_execution":True,
    }
    if any(src.get(k)!=v for k,v in contract.items()):
        raise CompatibilityError("PRIVATE_HISTORICAL_AUDIT_PROVENANCE_CHANGED")
    e=d.get("static_dependency_evidence",{})
    expected={
      "raid_dps_module_internal_python_count":16,
      "direct_from_import_edges_total":43,
      "direct_archived_symbol_imports":29,
      "archived_direct_symbol_exports_found":29,
      "archived_direct_symbol_export_mismatches":0,
      "direct_archived_submodule_import_edges":11,
      "direct_research_external_module_import_edges":3,
      "external_three_historical_SHA_comparison":"3_OF_3_PASS_PREVIOUS_CI_41390523985",
      "all_43_edges_behaviorally_executed":False,
      "dynamic_import_closure_verified":False,
    }
    if any(e.get(k)!=v for k,v in expected.items()):
        raise CompatibilityError("ARCHIVED_AST_INTERFACE_SCOPE_CHANGED")
    f=d.get("fex_evidence",{})
    expected_fex={
      "bound_source_module_count":10,"bound_sha256_matches":10,
      "bound_sha256_mismatches":0,
      "archived_fex_report_status":"PASS",
      "archived_fex_synthetic_case_n":2,
      "archived_fex_synthetic_case_pass":2,
      "declared_required_capability_areas":11,
      "declared_covered_capability_areas":11,
      "all_11_capability_areas_behaviorally_validated":False,
      "actual_behavioral_claim":"PARTIAL__RUNTIME_SURFACE_AND_ADAPTER_CONTRACT_EXECUTED",
      "general_rotation_current_gameplay_certified":0,
      "full_spec_rotation_optimality_certified":False,
    }
    if any(f.get(k)!=v for k,v in expected_fex.items()):
        raise CompatibilityError("FEX_EVIDENCE_OVERCLAIM_OR_CHANGED")
    if (d.get("research_metadata_promotion_prohibited") is not True
        or d.get("current_MAIN_authority")!="UNKNOWN"
        or d.get("current_ACTIVE_workflow") is not None
        or d.get("legacy_inbox_dispatcher_executed") is not False
        or d.get("FROZEN_changed") is not False
        or d.get("Seq578")!="FAILED_QUARANTINED_PRESERVED"
        or d.get("Seq637")!="UNKNOWN"):
        raise CompatibilityError("SHARED_AUTHORITY_OR_EXECUTION_CHANGE")
    rows=d.get("public_research_bridge",[])
    if not isinstance(rows,list) or len(rows)!=3 or {r.get("path") for r in rows}!=set(PINS):
        raise CompatibilityError("RESEARCH_PUBLIC_BRIDGE_MODULE_LIST")
    for row in rows:
        sha,blob,sym,kind,call=PINS[row["path"]]
        if (row.get("historical_sha256")!=sha
            or row.get("github_git_blob_sha1")!=blob
            or row.get("symbol")!=sym or row.get("kind")!=kind
            or row.get("call_form")!=call
            or row.get("historical_caller")!="02_SOURCE/runtime/raid_dps/pipelines/prestate_coverage.py"):
            raise CompatibilityError("IMPORT_INTERFACE_PIN_CHANGED_"+row["path"])
    return rows

def check_repo_sources(rows:list,root:Path=ROOT)->list[dict]:
    out=[]
    for row in sorted(rows,key=lambda r:r["path"]):
        path=row["path"]
        file=root/path
        if not file.is_file() or file.is_symlink():
            raise CompatibilityError("PUBLIC_RESEARCH_SOURCE_MISSING_"+path)
        b=file.read_bytes()
        if (blob_sha1(b)!=row["github_git_blob_sha1"]
            or hashlib.sha256(b).hexdigest()!=row["historical_sha256"]):
            raise CompatibilityError("PUBLIC_SOURCE_HASH_OR_BLOB_MISMATCH_"+path)
        tree=ast.parse(b,filename=path)
        if not accept_signature(tree,row["symbol"],row["kind"]):
            raise CompatibilityError("IMPORT_CALL_SIGNATURE_MISMATCH_"+path)
        out.append({"path":path,"symbol":row["symbol"],
                    "hash_matches_historical_inventory":True,
                    "AST_signature_accepts_historical_call_form":True})
    return out

def self_test(d:dict,rows:list)->dict:
    n=0
    def reject(change,label):
        nonlocal n
        obj=deepcopy(d);change(obj)
        try:check_manifest(obj)
        except CompatibilityError as e:
            assert label in str(e),(label,str(e));n+=1
        else:raise AssertionError("WRONG_CLAIM_ACCEPTED")
    reject(lambda x:x["fex_evidence"].update({"all_11_capability_areas_behaviorally_validated":True}),"FEX_EVIDENCE_OVERCLAIM")
    reject(lambda x:x["fex_evidence"].update({"archived_fex_synthetic_case_n":11}),"FEX_EVIDENCE_OVERCLAIM")
    reject(lambda x:x["static_dependency_evidence"].update({"archived_direct_symbol_export_mismatches":1}),"ARCHIVED_AST_INTERFACE")
    reject(lambda x:x.update({"current_ACTIVE_workflow":"FEX_FULL_ENGINE_SYNTHETIC_PROBE_V1"}),"SHARED_AUTHORITY")
    reject(lambda x:x.update({"Seq578":"PASS"}),"SHARED_AUTHORITY")
    reject(lambda x:x["public_research_bridge"][0].update({"historical_sha256":"0"*64}),"IMPORT_INTERFACE_PIN_CHANGED")
    reject(lambda x:x["source_provenance"].update({"private_archive_raw_bytes_in_github":True}),"PRIVATE_HISTORICAL_AUDIT")
    # Isolated AST mutations: no original sources executed or altered on disk.
    positives=0
    for row in rows:
        tree=ast.parse((ROOT/row["path"]).read_bytes())
        assert accept_signature(tree,row["symbol"],row["kind"])
        positives+=1
        target=next(n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==row["symbol"])
        target.name="BROKEN_EXPORTED_SYMBOL"
        assert not accept_signature(tree,row["symbol"],row["kind"])
        n+=1
    return {"result":"PASS","contract_negative_cases":n,"ast_public_source_positive_cases":positives,
            "source_runtime_execution":False}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--manifest",type=Path,default=DOC)
    args=ap.parse_args()
    doc=json.loads(args.manifest.read_text(encoding="utf-8"))
    rows=check_manifest(doc)
    present=check_repo_sources(rows)
    receipt={"schema":"ZrotMain124FexResearchBridgeGateReceiptV1",
        "result":"PASS_AST_AND_HISTORICAL_PIN_COMPATIBILITY_ONLY",
        "archive_source_ast_replay_here":False,
        "historical_124_private_source_attested_offline":True,
        "historical_import_edges":43,"historical_import_symbol_export_checks":29,
        "fex_exact_bound_sources":10,"fex_synthetic_behavior_cases":2,
        "fex_declared_capabilities":11,"fex_complete_behavior_evidence":False,
        "research_actual_source_pins_and_AST_signatures":present,
        "product_runtime_execution":False,"product_MAIN_promotion":False,
        "Seq578":"FAILED_QUARANTINED_PRESERVED","Seq637":"UNKNOWN"}
    if args.self_test:receipt["self_test"]=self_test(doc,rows)
    print(json.dumps(receipt,sort_keys=True,indent=2))
