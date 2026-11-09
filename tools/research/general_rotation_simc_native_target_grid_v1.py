#!/usr/bin/env python3
"""Compare actual pinned Native SimC 1/2/3/5-target JSON2 action samples.

Uses existing verified capture producer, JSON2 extractor and source IF/ELSE
research engine. The exact source profile, Native binary, seed, fight duration
and effective APL must agree across all scenarios. Action tokens may match
multiple APL rows; never infer selected source rows, full READY or opener end.

No args -> offline source-neutral synthetic regression. Network-free consumer.
"""
from __future__ import annotations

import argparse
from collections import Counter
from difflib import SequenceMatcher
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from simc_apl_semantic_ir_v2 import canonical, git_blob
from simc_native_json_sequence import extract_json_sequence
from general_rotation_simc_e2e_research_engine_v1 import compile_spec
from general_rotation_simc_multi_spec_cold_start_v1 import load_manifest

SCHEMA = "ZrotSimcNativeCrossSpecTargetGridEvidenceV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SAMPLE_WINDOW_MS = 10000
TARGETS = (1, 2, 3, 5)


class NativeGridError(ValueError):
    pass


def require(ok: bool, code: str):
    if not ok:
        raise NativeGridError(code)


def examine(combat: list[dict], program: dict, count: int) -> dict:
    """Actual JSON2 sample actions, not source choice or PRE state."""
    require(type(count) is int and count > 0 and
            type(combat) is list and type(program) is dict,
            "SAMPLE_INPUT_INVALID")
    choices = {}
    for name, rows in program.items():
        require(type(name) is str and type(rows) is list,
                "SOURCE_LIST_MISSING")
        for r in rows:
            if r["behavior"] != "ACTION":
                continue
            choices.setdefault(r["action"], []).append({
                "list": name,
                "rank": r["priority_rank_in_list"],
                "source_line_sha256": r["identity"]["source_line_sha256"],
            })
    used = []
    queued = 0
    waited = 0
    previous = -1
    for row in combat:
        timestamp = row.get("timestamp_ms")
        require(type(timestamp) is int and timestamp >= 0 and timestamp >= previous,
                "NATIVE_ACTION_SEQUENCE_NOT_ORDERED")
        previous = timestamp
        kind = row.get("record_kind")
        if kind == "WAIT_NON_ACTION":
            waited += 1
            continue
        if kind == "ACTION_RECORDED_QUEUE_FAILED":
            queued += 1
            continue
        require(kind == "SAMPLE_ACTION" and
                type(row.get("action_token")) is str and
                bool(row["action_token"]) and
                row.get("queue_failed") is False,
                "NATIVE_ACTION_SEQUENCE_UNTRUSTED")
        token = row["action_token"]
        candidates = choices.get(token, [])
        used.append({
            "at_simc_ms": timestamp,
            "action": token,
            "candidate_APL_source_rows_NOT_SELECTED":
                candidates,
            "source_row_identity_certified": False,
            "same_timestamp_is_not_strict_PRE": True,
            "Native_full_competing_READY": "UNKNOWN",
        })
    early = [r for r in used if r["at_simc_ms"] < SAMPLE_WINDOW_MS]
    return {
        "target_count": count,
        "sample_actions": len(used),
        "queued_failed_excluded": queued,
        "wait_rows_excluded": waited,
        "first_10sec_sample_actions_NOT_opener_end": early,
        "first_10sec_sample_count": len(early),
        "sample_action_token_counts": dict(sorted(
            Counter(r["action"] for r in used).items())),
        "source_token_match_sample_count": sum(
            bool(r["candidate_APL_source_rows_NOT_SELECTED"]) for r in used),
        "source_APL_row_attribution": "UNKNOWN_MULTIPLE_POSSIBLE_ROWS",
        "opener_termination_timestamp": "UNKNOWN",
        "opener_termination_source_condition": "UNKNOWN",
        "first_real_player_cast": "UNKNOWN_NOT_WOW_CLIENT",
        "Native_full_competing_READY": "UNKNOWN",
        "simc_source_hypothesis_NOT_gameplay_optimality": True,
    }


def _compare_to_st(st: dict, other: dict) -> dict:
    left=[r["action"] for r in st["first_10sec_sample_actions_NOT_opener_end"]]
    right=[r["action"] for r in other["first_10sec_sample_actions_NOT_opener_end"]]
    matcher=SequenceMatcher(None,left,right,autojunk=False)
    return {
        "from_target_count":st["target_count"],
        "to_target_count":other["target_count"],
        "early_sample_action_token_overlap_ratio_NOT_priority":
            round(matcher.ratio(),6),
        "early_actions_identical":left==right,
        "first_10sec_action_count_from":len(left),
        "first_10sec_action_count_to":len(right),
        "different_sequence_does_NOT_identify_action_cause":True,
    }


def run(source_root: Path, manifest_path: Path, captures_root: Path) -> dict:
    manifest=load_manifest(manifest_path)
    root=source_root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       check=True,capture_output=True,text=True).stdout.strip()
    require(rev==manifest["official_simc_commit"],
            "SIMC_SOURCE_REVISION_NOT_PINNED")
    cases=[]
    for spec in manifest["profiles"]:
        profile=(root/spec["profile"]).resolve(strict=True)
        require(profile.is_relative_to(root),"SOURCE_PATH_TRAVERSAL")
        raw=profile.read_bytes()
        require(git_blob(raw)==spec["git_blob"],
                "ORIGINAL_PROFILE_BLOB_MISMATCH")
        program=compile_spec(raw,spec,None)["conditioned_opener_and_priority"][
            "all_ordered_source_IF_ELSE_lists"]
        captures={}
        common=None
        for count in TARGETS:
            folder=captures_root/(spec["key"]+"-"+str(count)+"t")
            receipt=json.loads((folder/"simc_reference_receipt.json").read_bytes())
            require(receipt.get("status")=="SIMC_NATIVE_CAPTURED_UNPARSED" and
                    receipt.get("controlled_target_count")==count and
                    receipt.get("controlled_seed")==31459 and
                    receipt.get("controlled_fight_seconds")==30 and
                    receipt.get("controlled_fixed_time") is True and
                    type(receipt.get("simc_executable_sha256")) is str and
                    len(receipt["simc_executable_sha256"])==64 and
                    receipt.get("simc_spec")==(
                        spec["key"].split("_",1)[-1]) and
                    receipt.get("profile_sha256")==sha256(raw).hexdigest(),
                    "NATIVE_CAPTURE_OR_CASE_IDENTITY_DRIFT")
            compare={k:receipt[k] for k in (
                "simc_executable_sha256","profile_sha256",
                "effective_apl_sha256","controlled_seed",
                "controlled_fight_seconds","controlled_fixed_time")}
            if common is None:
                common=compare
            require(compare==common,
                    "TARGET_CASES_DIFFERENT_BINARY_BUILD_APL_OR_SEED")
            seq=extract_json_sequence(folder)
            require(seq["source_capture_status"]=="SIMC_NATIVE_CAPTURED_UNPARSED" and
                    seq["source_apl_sha256"]==compare["effective_apl_sha256"] and
                    seq["source_profile_sha256"]==compare["profile_sha256"] and
                    seq["source_simc_executable_sha256"]==compare["simc_executable_sha256"],
                    "JSON2_SEQUENCE_SOURCE_NOT_VERIFIED")
            captures[count]=examine(seq["combat_sequence"],program,count)
            captures[count]["input_capture_receipt_sha256"]=sha256(
                canonical(receipt)).hexdigest()
        cases.append({
            "source_spec_key":spec["key"],
            "source_class_key":spec["class_key"],
            "source_profile_git_blob_sha1":spec["git_blob"],
            "source_APL_action_count":sum(len(v) for v in program.values()),
            "same_native_build_apl_seed_and_fight_window":True,
            "capture_control_fingerprint":common,
            "target_cases":[captures[n] for n in TARGETS],
            "comparisons_to_ST":[_compare_to_st(captures[1],captures[n])
                                 for n in TARGETS if n!=1],
            "3plus_native_action_sequence_observed":
                captures[3]["sample_actions"]>0 and
                captures[5]["sample_actions"]>0,
            "source_APL_IF_condition_complete":True,
            "phase_label_opener_until_time_unknown":True,
            "actual_gameplay_priority_verified":False,
        })
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "official_simc_source_commit":rev,
        "target_counts":list(TARGETS),
        "source_profiles":len(cases),
        "source_APL_rows_total":sum(c["source_APL_action_count"] for c in cases),
        "source_native_cases":cases,
        "direct_native_CPP_selected_row_proof":False,
        "native_JSON2_sample_action_validated":True,
        "opener_end_condition":"UNKNOWN",
        "full_competing_action_READY_proven":0,
        "independent_WCL_holdout_involved":False,
        "WCL_API_calls":0,
        "dummy_training_expected_player_cast":"UNKNOWN",
        "MAIN_promoted":False,
    }


def selftest() -> dict:
    program={
        "default":[{"behavior":"ACTION","action":"alpha",
                    "priority_rank_in_list":1,
                    "identity":{"source_line_sha256":"a"*64}},
                   {"behavior":"CALL","action":"call_action_list",
                    "priority_rank_in_list":2,
                    "identity":{"source_line_sha256":"b"*64}}],
        "aoe":[{"behavior":"ACTION","action":"alpha",
                "priority_rank_in_list":1,
                "identity":{"source_line_sha256":"c"*64}}]}
    def action(token,t,kind="SAMPLE_ACTION"):
        return {"action_token":token,"timestamp_ms":t,
                "queue_failed":kind=="ACTION_RECORDED_QUEUE_FAILED",
                "record_kind":kind}
    valid=[action("alpha",0),action("alpha",0,"ACTION_RECORDED_QUEUE_FAILED"),
           action(None,50,"WAIT_NON_ACTION"),action("omega",100)]
    r=examine(valid,program,3)
    require(r["sample_actions"]==2 and
            r["queued_failed_excluded"]==1 and
            r["wait_rows_excluded"]==1 and
            len(r["first_10sec_sample_actions_NOT_opener_end"][0][
                "candidate_APL_source_rows_NOT_SELECTED"])==2 and
            r["source_token_match_sample_count"]==1 and
            r["opener_termination_timestamp"]=="UNKNOWN" and
            _compare_to_st(examine(valid,program,1),r)[
                "early_actions_identical"] is True,
            "SYNTHETIC_SAMPLE_CONTRACT_FAILED")
    bad=0
    for sequence in (
        [action("alpha",5),action("alpha",4)],
        [action("alpha",0,kind="BAD_KIND")],
        [action("alpha",-1)],
    ):
        try:examine(sequence,program,5)
        except NativeGridError:bad+=1
        else:raise AssertionError("INVALID_NATIVE_SEQUENCE_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC",
            "positive_synthetic_contracts":1,
            "negative_fail_closed_cases":bad,
            "full_READY_inferred":False,"opener_end_inferred":False,
            "WCL_API_calls":0}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-root",type=Path)
    ap.add_argument("--manifest",type=Path)
    ap.add_argument("--captures-root",type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if not any((args.source_root,args.manifest,args.captures_root)):
        result=selftest()
    else:
        if not all((args.source_root,args.manifest,args.captures_root)):
            ap.error("Source root, manifest and captures root are required")
        result=run(args.source_root,args.manifest,args.captures_root)
    data=canonical(result)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes(data)
        print(json.dumps({"status":"WRITTEN","sha256":sha256(data).hexdigest(),
                          "bytes":len(data)}))
    else:print(data.decode(),end="")


if __name__=="__main__":
    main()
