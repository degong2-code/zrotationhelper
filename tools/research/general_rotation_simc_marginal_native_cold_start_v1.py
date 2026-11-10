#!/usr/bin/env python3
"""Generic *marginal* Original SimC Native cold start for a new specialization.

Inputs: the existing cross-class pinned source manifest, ONE explicitly
selected specialization, 1/2/3/5-target original SimC capture receipts and
JSON2 records from one executable/seed/profile. Reuses the already validated
source program and native action-token grid analyzers rather than recapturing
previously researched classes.

This is source selection evidence, not a full same-root physical READY proof.
Action names may match multiple original APL rows. No timed 'opener end' is
inferred from an arbitrary sample window or a decaying initial burst buff.
No WoW/WCL calls or specialization rules in Generic.

PyCharm without Script Parameters: safe synthetic/offline self-test.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from simc_apl_semantic_ir_v2 import canonical,git_blob
from general_rotation_simc_multi_spec_cold_start_v1 import load_manifest
from general_rotation_simc_e2e_research_engine_v1 import compile_spec
from general_rotation_simc_native_target_grid_v1 import (
    TARGETS,examine,_compare_to_st,NativeGridError,
)
from simc_native_json_sequence import extract_json_sequence

SCHEMA="ZrotGenericSimCMarginalNewProfileNativeTargetGridV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
IDENT=re.compile("[a-z0-9][a-z0-9_]{0,63}\\Z")

class MarginalNativeError(ValueError):pass

def need(ok:bool,code:str):
    if not ok:raise MarginalNativeError(code)

def select_new_profile(manifest:dict,key:str)->dict:
    need(type(manifest) is dict and type(key) is str and
         IDENT.fullmatch(key) is not None and
         type(manifest.get("profiles")) is list,
         "INVALID_OR_UNPINNED_MARGINAL_PROFILE_REQUEST")
    rows=[p for p in manifest["profiles"] if p.get("key")==key]
    need(len(rows)==1,"MARGINAL_PROFILE_NOT_UNIQUE_IN_PINNED_MANIFEST")
    return rows[0]

def inspect_capture(receipt:dict,seq:dict,profile:dict,raw:bytes,
                    target_count:int,program:dict)->tuple[dict,dict]:
    need(type(target_count) is int and target_count in TARGETS and
         type(receipt) is dict and type(seq) is dict and
         type(profile) is dict and type(raw) is bytes,
         "UNTRUSTED_MARGINAL_CAPTURE_INPUT")
    expected_sha=sha256(raw).hexdigest()
    native_bin=receipt.get("simc_executable_sha256")
    need(receipt.get("status")=="SIMC_NATIVE_CAPTURED_UNPARSED" and
         receipt.get("controlled_target_count")==target_count and
         receipt.get("controlled_seed")==31459 and
         receipt.get("controlled_fight_seconds")==30 and
         receipt.get("controlled_fixed_time") is True and
         receipt.get("profile_sha256")==expected_sha and
         receipt.get("simc_spec")==profile["key"].split("_",1)[-1] and
         type(native_bin) is str and
         re.fullmatch("[a-f0-9]{64}",native_bin) is not None,
         "NATIVE_PROFILE_SEED_TARGET_OR_BINARY_IDENTITY_DRIFT")
    controls={k:receipt.get(k) for k in (
        "simc_executable_sha256","profile_sha256",
        "effective_apl_sha256","controlled_seed",
        "controlled_fight_seconds","controlled_fixed_time")}
    need(type(controls["effective_apl_sha256"]) is str and
         re.fullmatch("[a-f0-9]{64}",controls["effective_apl_sha256"]) is not None and
         seq.get("source_capture_status")=="SIMC_NATIVE_CAPTURED_UNPARSED" and
         seq.get("source_apl_sha256")==controls["effective_apl_sha256"] and
         seq.get("source_profile_sha256")==expected_sha and
         seq.get("source_simc_executable_sha256")==native_bin,
         "NATIVE_JSON2_AND_EFFECTIVE_APL_NOT_SAME_CAPTURE")
    case=examine(seq["combat_sequence"],program,target_count)
    need(case["sample_actions"]>0,"EMPTY_ACTUAL_NATIVE_SAMPLE")
    case["source_capture_receipt_sha256"]=sha256(canonical(receipt)).hexdigest()
    case["source_action_token_only_NOT_causal_root"]=True
    return case,controls

def run(source_root:Path,manifest_path:Path,captures_root:Path,
        spec_key:str)->dict:
    manifest=load_manifest(manifest_path)
    profile=select_new_profile(manifest,spec_key)
    root=source_root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       capture_output=True,text=True,check=True).stdout.strip()
    need(rev==manifest["official_simc_commit"],
         "MARGINAL_NATIVE_SOURCE_REVISION_DRIFT")
    path=(root/profile["profile"]).resolve(strict=True)
    need(path.is_relative_to(root),"MARGINAL_SOURCE_PATH_ESCAPE")
    raw=path.read_bytes()
    need(git_blob(raw)==profile["git_blob"],
         "MARGINAL_PROFILE_ORIGINAL_GIT_BLOB_MISMATCH")
    source=compile_spec(raw,profile,None)
    program=source["conditioned_opener_and_priority"][
        "all_ordered_source_IF_ELSE_lists"]
    need(source["source_APL_row_count"]==sum(map(len,program.values())),
         "SOURCE_ROW_COUNT_DRIFT_OR_UNBOUND_CONTROL")
    cases={}
    common=None
    for target_count in TARGETS:
        folder=captures_root/(spec_key+"-"+str(target_count)+"t")
        receipt=json.loads((folder/"simc_reference_receipt.json").read_bytes())
        seq=extract_json_sequence(folder)
        case,controls=inspect_capture(
            receipt,seq,profile,raw,target_count,program)
        if common is None:
            common=controls
        need(controls==common,
             "MARGINAL_TARGET_RUNS_DIFFERENT_BINARY_APL_PROFILE_SEED")
        cases[target_count]=case
    return {
        "schema":SCHEMA,
        "policy_id":POLICY,
        "pinned_simc_source_revision":rev,
        "source_manifest_total_profiles":len(manifest["profiles"]),
        "source_manifest_distinct_classes":len(set(
            p["class_key"] for p in manifest["profiles"])),
        "new_actual_native_spec_key":spec_key,
        "new_actual_native_profile_git_blob":profile["git_blob"],
        "new_original_profile_APL_rows":source["source_APL_row_count"],
        "new_original_source_action_lists":len(program),
        "native_captures_same_binary_APL_and_seed":True,
        "native_capture_controls":common,
        "original_native_target_counts":list(TARGETS),
        "native_target_cases":[cases[n] for n in TARGETS],
        "compared_to_native_ST":[_compare_to_st(cases[1],cases[n])
                                 for n in TARGETS if n!=1],
        "total_actual_SimC_sample_actions":sum(
            cases[n]["sample_actions"] for n in TARGETS),
        "previous_other_class_native_captures_rerun":0,
        "new_original_native_CXX_builds_expected":1,
        "new_WCL_API_calls":0,
        "source_control_guard_true_is_not_ACTION_READY":True,
        "original_native_CPP_root_or_row_attribution":"UNKNOWN",
        "source_control_CALL_RUN_actual_route":"UNKNOWN",
        "opener_end_condition":"UNKNOWN",
        "full_competing_action_READY_proven":0,
        "WCL_blind_candidate_semantics_injected":False,
        "current_retail_gameplay_optimality_proven":False,
        "target_dummy_wrong_cast":"UNKNOWN",
        "MAIN_promoted":False
    }

def selftest()->dict:
    # A marginal capture selects one profile from an independently validated
    # multi-class manifest, without replaying the classes already evidenced.
    manifest={"profiles":[
        {"key":"example_alpha","class_key":"alpha"},
        {"key":"example_beta","class_key":"beta"}]}
    need(select_new_profile(manifest,"example_beta")["class_key"]=="beta",
         "MARGINAL_MANIFEST_SELECT_FAILED")
    rejections=0
    for key,rows in [
        ("does_not_exist",manifest["profiles"]),
        ("example_beta",manifest["profiles"]+[manifest["profiles"][1]]),
        ("../example",manifest["profiles"]),
    ]:
        try:select_new_profile({"profiles":rows},key)
        except MarginalNativeError:rejections+=1
        else:raise AssertionError("UNSAFE_MARGINAL_PROFILE_ACCEPTED")
    # Reuse real shared analyzer's existing fake token exercise; no new
    # semantic source rule is introduced in this marginal adapter.
    mock={"default":[
        {"behavior":"ACTION","action":"test_cast",
         "priority_rank_in_list":1,
         "identity":{"source_line_sha256":"a"*64}}]}
    row={"timestamp_ms":0,"record_kind":"SAMPLE_ACTION",
         "action_token":"test_cast","queue_failed":False}
    evidence=examine([row],mock,1)
    need(evidence["sample_actions"]==1 and
         evidence["opener_termination_timestamp"]=="UNKNOWN" and
         evidence["Native_full_competing_READY"]=="UNKNOWN" and
         len(evidence["first_10sec_sample_actions_NOT_opener_end"])==1,
         "MARGINAL_NATIVE_SAMPLE_FALSIFIED_OPENER")
    return {
        "status":"PASS_SYNTHETIC_MARGINAL_NATIVE_COLD_START",
        "negative_profile_controls":rejections,
        "shared_native_sequence_analyzer_reused":True,
        "real_native_CXX_build_performed":False,
        "opener_end_proven":False,
        "full_READY_proven":False
    }

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--captures-root",type=Path)
    p.add_argument("--spec-key")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any((a.source_root,a.manifest,a.captures_root,a.spec_key)):
        output=selftest()
    else:
        if not all((a.source_root,a.manifest,a.captures_root,a.spec_key)):
            p.error("source-root, manifest, captures-root and spec-key must be supplied")
        output=run(a.source_root,a.manifest,a.captures_root,a.spec_key)
    serialized=canonical(output)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(serialized)
        print(json.dumps({"status":"WRITTEN",
                          "sha256":sha256(serialized).hexdigest(),
                          "bytes":len(serialized)}))
    else:
        print(serialized.decode(),end="")

if __name__=="__main__":
    main()
