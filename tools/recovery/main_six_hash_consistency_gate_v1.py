#!/usr/bin/env python3
"""Check a historical MAIN six-file hash attestation and fail-closed review scope.

Does NOT read the user's machine, execute the archived entrypoint, or resolve
authority conflicts. The six local hashes are user-reported and independently
matched against private M4B archive bytes outside this public CI.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/"docs/MAIN_SIX_LIVE_HASHES_SNAPSHOT_CONSISTENCY_20261102.json"
EXPECTED={
 "CURRENT_STATE.md":"eaaf836b3df05af8c75cea4e8d64bda1aed765c118b7b2c9b560ba7d59d54dc4",
 "RUN_zRAID_MAIN.py":"52f3f1222c601c6fe63b6c826cd1f9db7072c9c324c0386f18a1446194361ec5",
 "01_WORKFLOW/config/MAIN_CONTROL_PLANE.json":"2108740762ac2575d4f0c7a7ff86d086d674b7e531138f62b9dfd8d7aa6cd8f2",
 "03_DATA/03_MANIFESTS/MAIN_ENTRYPOINT_AUTHORITY.json":"334b9334f36578dcf052bb03c86882c8805a07d5fdc89829b108ec7aa1c64ac2",
 "01_WORKFLOW/prompts/current/PROMPT_SET_MANIFEST.json":"5a8d51d1d47a179b1bb8558fc5202a36354842794b7aa99acadb894d886bcbfa",
 "07_PACKAGES/03_HANDOFFS/LATEST_HANDOFF.json":"2a21b46ec6b3f6d225c5b01edf4eb9871bc8770868b902042646b8d1fe338ad6",
}
FEX="c9ba0657c0f5ed936acf41a839780d6b3c245e08757107a96fef6cc675b1dc2f"
FIRST="a3a30cc8f406216f9281109a3ffc357dba8306fafeb7b7a6f4fe090785e2d080"
OLD_ENTRY="b5838b0e0644b0efb7ec502d5adbb6c26e5006c4fe7da52fba2233c5d8d1a537"
OLD_CONFIG="40b5a0197fa3e90b354128729f5019630857577da2d326ef301af5be345e2e8a"
class ReviewError(ValueError): pass


def audit(data:dict)->dict:
    if data.get("schema")!="ZrotMainSixPinLocalSnapshotConsistencyV1":
        raise ReviewError("WRONG_ATTESTATION_SCHEMA")
    provenance=data.get("source_provenance",{})
    if (provenance.get("six_hashes")!="USER_PC_READ_ONLY_POWERSHELL_GET_FILEHASH_2026_11_02"
        or provenance.get("sha256_comparison")!="SIX_OF_SIX_EXACT"
        or provenance.get("current_runtime_whole_tree")!="NOT_VERIFIED"
        or provenance.get("private_source_uploaded_to_public_repo") is not False):
        raise ReviewError("FALSE_LIVE_OR_ARCHIVE_PROVENANCE")
    if data.get("verified_user_pc_files")!=EXPECTED:
        raise ReviewError("SIX_HASH_EVIDENCE_CHANGED")
    sources=data.get("archived_source_sha256",{})
    if sources.get("02_SOURCE/validation/generalization/FEX_FULL_ENGINE_SYNTHETIC_PROBE_v1.py")!=FEX:
        raise ReviewError("FEX_SOURCE_PIN_INVALID")
    if sources.get("02_SOURCE/validation/generalization/CROSS_SPEC_SYNTHETIC_PROBE_v1.py")!=FIRST:
        raise ReviewError("FIRST_SOURCE_PIN_INVALID")
    conflicts=data.get("verified_historical_internal_disagreements",{})
    expected=set(("CURRENT_STATE_vs_CONTROL","ENTRYPOINT_AUTHORITY_ENTRYPOINT_SHA",
      "ENTRYPOINT_AUTHORITY_CONFIG_SHA","PROMPT_MANIFEST_FEX_SHA",
      "LATEST_HANDOFF_ENTRYPOINT_SHA","DEFAULT_ACTION_DISAGREEMENT"))
    if set(conflicts)!=expected:raise ReviewError("HISTORICAL_CONFLICT_LOST")
    if (conflicts["ENTRYPOINT_AUTHORITY_ENTRYPOINT_SHA"].get("embedded_sha256")!=OLD_ENTRY
        or conflicts["ENTRYPOINT_AUTHORITY_ENTRYPOINT_SHA"].get("actual_sha256")!=EXPECTED["RUN_zRAID_MAIN.py"]
        or conflicts["ENTRYPOINT_AUTHORITY_CONFIG_SHA"].get("embedded_sha256")!=OLD_CONFIG
        or conflicts["ENTRYPOINT_AUTHORITY_CONFIG_SHA"].get("actual_sha256")!=EXPECTED["01_WORKFLOW/config/MAIN_CONTROL_PLANE.json"]):
        raise ReviewError("STALE_ENTRYPOINT_OR_CONFIG_PIN_CONCEALED")
    prompt=conflicts["PROMPT_MANIFEST_FEX_SHA"]
    if (prompt.get("declared_workflow")!="FEX_FULL_ENGINE_SYNTHETIC_PROBE_V1"
        or prompt.get("embedded_sha256")!=FIRST or prompt.get("FEX_actual_sha256")!=FEX):
        raise ReviewError("FEX_PROMPT_SOURCE_MISBIND_CONCEALED")
    if conflicts["LATEST_HANDOFF_ENTRYPOINT_SHA"].get("embedded_sha256")!=OLD_ENTRY:
        raise ReviewError("STALE_LATEST_HANDOFF_PIN_CONCEALED")
    if (conflicts["CURRENT_STATE_vs_CONTROL"].get("current_state_workflow")!="FIRST_CROSS_SPEC_SYNTHETIC_PROBE_V1"
        or conflicts["CURRENT_STATE_vs_CONTROL"].get("control_plane_workflow")!="FEX_FULL_ENGINE_SYNTHETIC_PROBE_V1"):
        raise ReviewError("HISTORICAL_WORKFLOW_SELECTION_CONFLICT_CONCEALED")
    if conflicts["DEFAULT_ACTION_DISAGREEMENT"].get("control_plane")!="RUN_ACTIVE" or conflicts["DEFAULT_ACTION_DISAGREEMENT"].get("entrypoint_authority")!="STATUS":
        raise ReviewError("HISTORICAL_DEFAULT_CONFLICT_CONCEALED")
    proposal=data.get("conditional_successor_proposal",{})
    for field in ("auto_modify_current_state","auto_modify_legacy_control_plane",
                  "auto_modify_legacy_handoff","auto_modify_registry_or_pointer","auto_RUN_ACTIVE"):
        if proposal.get(field) is not False:
            raise ReviewError("UNAUTHORIZED_AUTO_REPAIR_OR_EXECUTION")
    v=data.get("verdict",{})
    status={
      "six_local_files_match_archive":True,
      "stale_pin_conflict_persists":True,
      "current_MAIN_authority":"UNKNOWN",
      "FULL_ENGINE_CROSS_SPEC_GAMEPLAY_READY":"NOT_PROVEN",
      "product_main_promotion":False,
      "github_main_changed":False,
      "frozen_changed":False,
      "seq578":"FAILED_QUARANTINED_PRESERVED",
      "seq637":"UNKNOWN",
    }
    if any(v.get(k)!=value for k,value in status.items()):
        raise ReviewError("UNAUTHORIZED_PRODUCT_MAIN_OR_GAMEPLAY_CLAIM")
    return {
      "schema":"ZrotMainSixHashConsistencyCIReceiptV1",
      "status":"PASS_SIX_PIN_ATTESTATION__PRODUCT_MAIN_AUTHORITY_STILL_UNKNOWN",
      "reported_pc_hashes_match_original_archive":6,
      "historical_cross_doc_disagreements_preserved":len(expected),
      "explicit_stale_embedded_source_hashes":3,
      "automatic_repair":False,"original_source_run":False,
      "current_main_promotion":False,"frozen_modified":False,
      "seq578":"FAILED_QUARANTINED_PRESERVED","seq637":"UNKNOWN",
    }


def negative_tests(d:dict)->int:
    count=0
    def reject(fn,reason):
        nonlocal count
        tampered=deepcopy(d);fn(tampered)
        try:audit(tampered)
        except ReviewError as e:
            assert reason in str(e),(reason,str(e));count+=1
        else:raise AssertionError("AUTHORITY_OR_EVIDENCE_TAMPER_ACCEPTED")
    reject(lambda x:x["verified_user_pc_files"].update({"RUN_zRAID_MAIN.py":"0"*64}),"SIX_HASH_EVIDENCE_CHANGED")
    reject(lambda x:x["verified_historical_internal_disagreements"].pop("PROMPT_MANIFEST_FEX_SHA"),"HISTORICAL_CONFLICT_LOST")
    reject(lambda x:x["verified_historical_internal_disagreements"]["ENTRYPOINT_AUTHORITY_CONFIG_SHA"].update({"embedded_sha256":EXPECTED["01_WORKFLOW/config/MAIN_CONTROL_PLANE.json"]}),"STALE_ENTRYPOINT_OR_CONFIG_PIN_CONCEALED")
    reject(lambda x:x["conditional_successor_proposal"].update({"auto_RUN_ACTIVE":True}),"UNAUTHORIZED_AUTO_REPAIR_OR_EXECUTION")
    reject(lambda x:x["verdict"].update({"current_MAIN_authority":"PROMOTED"}),"UNAUTHORIZED_PRODUCT_MAIN_OR_GAMEPLAY_CLAIM")
    reject(lambda x:x["source_provenance"].update({"current_runtime_whole_tree":"PROVEN"}),"FALSE_LIVE_OR_ARCHIVE_PROVENANCE")
    return count


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,default=DOC)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    d=json.loads(args.manifest.read_text(encoding="utf-8"))
    receipt=audit(d)
    if args.self_test:receipt["negative_tests_passed"]=negative_tests(d)
    print(json.dumps(receipt,indent=2,sort_keys=True))
