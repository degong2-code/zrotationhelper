#!/usr/bin/env python3
"""SimC-first General Rotation: actual JSON2 action samples + source IF/ELSE IR.

Reuses:
  - pinned source-only research delivery (complete APL priority rows);
  - original SimC JSON2 action_sequence reader and raw SHA receipts;
  - existing official SimC capture script and exact profile source Git blobs.

Does not rewrite any APL condition, infer which source row fired merely from
a spell name, infer an opener-end boundary, or claim an observed action is
optimal. Source candidate rows include *all* possible matching APL rows.

No-argument PyCharm mode: offline synthetic checks, no network or SimC.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from simc_apl_semantic_ir_v2 import canonical, git_blob
from simc_native_json_sequence import extract_json_sequence
from general_rotation_research_delivery_v1 import (
    SCHEMA as SOURCE_IR_SCHEMA, POLICY
)

SCHEMA="ZrotSimCNativeObservedCastGeneralRotationResearchV1"
CASE_SCHEMA="ZrotSimCCastGeneralRotationCaseManifestV1"
HASH64=re.compile(r"^[0-9a-f]{64}$")
HASH40=re.compile(r"^[0-9a-f]{40}$")
PHASE="SIMC_JSON2_SAMPLE_ACTION_AT_OR_AFTER_T_NOT_STRICT_PRE"


class CastDeliveryError(ValueError):
    pass


def ensure(ok:bool,reason:str)->None:
    if not ok:raise CastDeliveryError(reason)


def source_candidates(model:dict,action:str)->list[dict]:
    """Action-name matching is a lookup hypothesis, NOT exact source-row proof."""
    all_lists=model["post_opener_IF_ELSE_priority"]["lists"]
    result=[]
    for list_name,rows in all_lists.items():
        for row in rows:
            if row["kind"]!="ACTION" or row["action"]!=action:
                continue
            result.append({
                "source_list":list_name,
                "source_priority_rank":row["rank_in_source_list"],
                "source_line":row["source_line"],
                "source_row_sha256":row["source_row_sha256"],
                "source_IF":row["when_source_IF"],
                "requires_unverified_state_symbols":
                    row["required_observation_symbols"],
                "source_row_actually_entered":"UNKNOWN",
                "condition_true_at_observed_action":"UNKNOWN",
                "independent_READY":"UNKNOWN",
            })
    return result


def sample(sequence:dict,model:dict)->dict:
    ensure(sequence.get("record_kind")=="SAMPLE_ACTION" and
           sequence.get("queue_failed") is False and
           isinstance(sequence.get("action_token"),str) and
           sequence["action_token"] and
           type(sequence.get("numeric_action_id")) is int and
           type(sequence.get("timestamp_ms")) is int and
           sequence["timestamp_ms"]>=0,
           "NOT_ACTUAL_JSON2_RECORDED_ACTION")
    candidates=source_candidates(model,sequence["action_token"])
    return {
        "at_simc_ms":sequence["timestamp_ms"],
        "sequence_ordinal":sequence["ordinal"],
        "action_token":sequence["action_token"],
        "numeric_spell_id":sequence["numeric_action_id"],
        "potential_APL_source_rows_by_action_name_ONLY":candidates,
        "exact_source_row_used":"UNKNOWN",
        "same_timestamp_SimC_snapshot_is_strict_PRE":False,
        "source_or_competitor_readiness":"UNKNOWN",
        "opener_phase_at_this_cast":"UNKNOWN",
        "user_mistake_proven":False,
    }


def one_case(model:dict,case_name:str,cast_seq:dict,*,window_ms:int)->dict:
    ensure(isinstance(cast_seq,dict) and
           cast_seq.get("schema")=="ZrotSimcNativeJson2ActionSequenceResearchV1"
           and cast_seq.get("status")=="SEQUENCE_SNAPSHOTS_EXTRACTED"
           and cast_seq.get("source_capture_status")=="SIMC_NATIVE_CAPTURED_UNPARSED"
           and cast_seq.get("source_capture_status")!="SYNTHETIC_CAPTURE_TEST"
           and cast_seq.get("sample_action_is_not_apl_decision_certification") is True
           and cast_seq.get("same_time_event_pre_leakage_forbidden") is True
           and isinstance(cast_seq.get("combat_sequence"),list)
           and isinstance(cast_seq.get("precombat_sequence"),list),
           "ONLY_REAL_RECEIPTED_SIMC_JSON2_CAPTURE_ALLOWED")
    case=model["observed_original_SimC_selection_cases"].get(case_name)
    ensure(isinstance(case,dict) and
           type(case.get("targets_as_original_SimC_PRE")) is int,
           "INCOMPLETE_SOURCE_SELECTION_CASE")
    pre=cast_seq["precombat_sequence"]
    combat=cast_seq["combat_sequence"]
    def classify(rows):
        return Counter(x["record_kind"] for x in rows)
    pre_summary=classify(pre)
    combat_summary=classify(combat)
    ensure(all(x.get("record_kind") in (
        "SAMPLE_ACTION","WAIT_NON_ACTION","ACTION_RECORDED_QUEUE_FAILED")
        for x in pre+combat),"UNDECLARED_JSON2_RECORD_TYPE")
    observed=[x for x in combat if x["record_kind"]=="SAMPLE_ACTION"]
    ensure(observed and all(x.get("queue_failed") is False for x in observed),
           "OBSERVED_ACTIONS_MISSING_OR_FAILED_QUEUE")
    early=[x for x in observed if x["timestamp_ms"]<window_ms]
    later=[x for x in observed if x["timestamp_ms"]>=window_ms]
    if pre_summary["SAMPLE_ACTION"]:
        precombat=[sample(x,model) for x in pre if x["record_kind"]=="SAMPLE_ACTION"]
    else:
        precombat=[]
    mapped=[sample(x,model) for x in observed]
    lookup=Counter("ROWS_FOUND" if x[
        "potential_APL_source_rows_by_action_name_ONLY"] else "SOURCE_MAPPING_UNKNOWN"
        for x in mapped)
    return {
        "case":case_name,
        "target_count":case["targets_as_original_SimC_PRE"],
        "original_simc_root_source_returns_not_casts":
            case["source_selection_count"],
        "simc_JSON2_precombat_record_kinds":dict(pre_summary),
        "simc_JSON2_combat_record_kinds":dict(combat_summary),
        "simc_JSON2_observed_combat_action_count":len(mapped),
        "simc_JSON2_observed_combat_action_sequence":mapped,
        "simc_JSON2_precombat_action_sequence":precombat,
        "source_action_name_candidate_coverage":dict(lookup),
        "opener_window_ms_for_observation_only":window_ms,
        "observed_first_window_actions":[x for x in mapped if
                                         x["at_simc_ms"]<window_ms],
        "observed_after_window_actions":[x for x in mapped if
                                         x["at_simc_ms"]>=window_ms],
        "first_simc_combat_action":mapped[0]["action_token"],
        "first_real_player_cast":"UNKNOWN",
        "opener_end_transition":"UNKNOWN",
        "actual_native_observation_is_not_independent_priority_proof":True,
        "source_APL_priority_model":model[
            "post_opener_IF_ELSE_priority"]["lists"],
        "source_APL_control_flow":model[
            "post_opener_IF_ELSE_priority"]["branch_control_structure"],
        "target_count_breakpoints_independently_proven":False,
        "WCL_holdout":"NOT_RUN",
        "dummy_error_verdict":"UNKNOWN",
    }


def build(source_ir:dict,captures:dict,*,source_ir_sha256:str,
          manifest:dict,window_ms:int=10000)->dict:
    ensure(HASH64.fullmatch(source_ir_sha256) is not None and
           type(window_ms) is int and 1000<=window_ms<=30000,
           "EXACT_HASH_AND_BOUNDED_WINDOW_REQUIRED")
    ensure(source_ir.get("schema")==SOURCE_IR_SCHEMA and
           source_ir.get("product_policy_id")==POLICY and
           source_ir.get("source_model_count")>=2 and
           source_ir.get("source_IF_ELSE_rows")>0 and
           source_ir.get("product_expected_casts_verified")==0 and
           source_ir.get("complete_READY_proven")==0 and
           source_ir.get("WCL_API_calls")==0 and
           source_ir.get("MAIN_promoted") is False,
           "SOURCE_IR_OR_EVIDENCE_PROMOTION_CONTRACT_CHANGED")
    ensure(manifest.get("schema")==CASE_SCHEMA and
           manifest.get("product_policy_id")==POLICY and
           isinstance(manifest.get("cases"),list) and
           len(manifest["cases"])>=4,
           "SOURCE_CAST_CASE_MANIFEST_INVALID")
    model_by_key={x["source_spec_key"]:x for x in source_ir["research_models"]}
    ensure(len(model_by_key)==source_ir["source_model_count"],
           "SPEC_MODELS_DUPLICATED")
    ordered=[];seen=set();binary_hashes=set();cohorts={}
    for entry in manifest["cases"]:
        key=entry["source_spec_key"]
        case=entry["source_case_key"]
        target=entry["target_count"]
        ensure((key,case) not in seen and
               key in model_by_key and
               case in model_by_key[key]["observed_original_SimC_selection_cases"] and
               type(target) is int and target>0 and
               target==model_by_key[key]["observed_original_SimC_selection_cases"][case][
                   "targets_as_original_SimC_PRE"],
               "INVALID_TARGET_CASE_OR_DUPLICATED_MANIFEST")
        seen.add((key,case))
        manifest_source=entry["source_profile_git_blob"]
        ensure(HASH40.fullmatch(manifest_source) is not None and
               manifest_source==model_by_key[key]["source_profile_git_blob_sha1"],
               "SOURCE_PROFILE_GIT_BLOB_NOT_MATCHED")
        seq=captures[(key,case)]
        ensure(seq["simc_spec"]==entry["simc_actor_spec"] and
               seq["source_profile_sha256"]==entry["profile_sha256"] and
               seq["source_apl_sha256"]==entry["effective_apl_sha256"] and
               HASH64.fullmatch(seq["source_native_json2_sha256"]) is not None and
               HASH64.fullmatch(seq["source_simc_executable_sha256"]) is not None,
               "ACTUAL_SOURCE_CAPTURE_PROFILE_OR_APL_MISMATCH")
        binary_hashes.add(seq["source_simc_executable_sha256"])
        old=cohorts.get(key)
        pair=(seq["source_profile_sha256"],seq["source_apl_sha256"])
        ensure(old is None or old==pair,
               "SPEC_CHANGED_PROFILE_OR_APL_BETWEEN_TARGET_COUNTS")
        cohorts[key]=pair
        item=one_case(model_by_key[key],case,seq,window_ms=window_ms)
        item["source_spec_key"]=key
        item["source_class_key"]=model_by_key[key]["source_class_key"]
        item["simc_actor_spec"]=entry["simc_actor_spec"]
        item["source_profile_git_blob_sha1"]=manifest_source
        item["source_simc_executable_sha256"]=seq[
            "source_simc_executable_sha256"]
        item["original_json2_sha256"]=seq["source_native_json2_sha256"]
        ordered.append(item)
    ensure(len(binary_hashes)==1 and
           len({x["source_spec_key"] for x in ordered})>=2 and
           sum(len(model_by_key[k]["observed_original_SimC_selection_cases"])
               for k in model_by_key)==len(seen),
           "REAL_CASE_COVERAGE_OR_SAME_EXECUTABLE_MISSING")
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "source_IR_input_SHA256":source_ir_sha256,
        "sample_phase":PHASE,"source_model_count":len(model_by_key),
        "target_count_cases":len(ordered),
        "single_native_simc_executable_SHA256":next(iter(binary_hashes)),
        "actual_simc_JSON2_observed_action_count":sum(
            c["simc_JSON2_observed_combat_action_count"] for c in ordered),
        "original_source_choice_count_not_casts":sum(
            c["original_simc_root_source_returns_not_casts"] for c in ordered),
        "research_cases":ordered,
        "initial_action_sequence_reconstructed":True,
        "opener_true_end_and_competing_READY":"UNKNOWN",
        "observed_action_name_does_not_prove_source_line":True,
        "post_opener_conditioned_source_program_complete":True,
        "WCL_blind_independent_lock":"NOT_RUN",
        "WCL_independent_holdout":"NOT_RUN",
        "target_dummy_error_verdict":"UNKNOWN",
        "verified_actual_user_player_rotation":False,
        "full_ready_proven":0,
        "current_retail_mechanics_blizzard_verified":False,
        "WCL_API_calls":0,"MAIN_promoted":False,
    }


def read_actual_capture(entry:dict)->dict:
    ref=Path(entry["reference_dir"]).resolve(strict=True)
    profile=Path(entry["official_profile"]).resolve(strict=True)
    source=profile.read_bytes()
    ensure(git_blob(source)==entry["source_profile_git_blob"],
           "OFFICIAL_PROFILE_SOURCE_GIT_BLOB_DRIFT")
    receipt=json.loads((ref/"simc_reference_receipt.json").read_bytes())
    ensure(receipt.get("status")=="SIMC_NATIVE_CAPTURED_UNPARSED" and
           receipt.get("controlled_target_count")==entry["target_count"] and
           type(receipt.get("controlled_seed")) is int and
           receipt["controlled_seed"]>0 and
           receipt.get("profile_sha256")==sha256(source).hexdigest() and
           receipt.get("simc_spec")==entry["simc_actor_spec"],
           "REAL_NATIVE_RECEIPT_TARGET_PROFILE_OR_SEED_INVALID")
    seq=extract_json_sequence(ref)
    ensure(seq["source_profile_sha256"]==receipt["profile_sha256"],
           "NATIVE_CAPTURE_PROFILE_BYTES_CHANGED")
    return seq


def selftest()->dict:
    def fake_row(action,kind,ordinal):
        return {"action":action,"kind":kind,"rank_in_source_list":ordinal+1,
            "source_line":3+ordinal,"source_row_sha256":format(ordinal+1,"064x"),
            "when_source_IF":"buff.example.up" if ordinal else None,
            "required_observation_symbols":["buff.example.up"],
            }
    def model(key,clazz,act):
        seqs={}
        for name,target in (("st",1),("2t",2)):
            seqs[name]={"targets_as_original_SimC_PRE":target,
                        "source_selection_count":3}
        return {"source_spec_key":key,"source_class_key":clazz,
                "source_profile_git_blob_sha1":"a"*40,
                "post_opener_IF_ELSE_priority":{
                    "lists":{"default":[fake_row("run_action_list", "RUN",0)],
                             "branch":[fake_row(act,"ACTION",0),
                                       fake_row(act,"ACTION",1)]},
                    "branch_control_structure":{}},
                "observed_original_SimC_selection_cases":seqs}
    def event(t,name,num,kind="SAMPLE_ACTION"):
        return {"record_kind":kind,"queue_failed":False if kind=="SAMPLE_ACTION" else None,
                "timestamp_ms":t,"action_token":name if kind=="SAMPLE_ACTION" else None,
                "numeric_action_id":num if kind=="SAMPLE_ACTION" else None,
                "ordinal":0}
    def seq(spec):
        return {"schema":"ZrotSimcNativeJson2ActionSequenceResearchV1",
            "status":"SEQUENCE_SNAPSHOTS_EXTRACTED",
            "source_capture_status":"SIMC_NATIVE_CAPTURED_UNPARSED",
            "sample_action_is_not_apl_decision_certification":True,
            "same_time_event_pre_leakage_forbidden":True,
            "simc_spec":spec,"source_profile_sha256":"b"*64,
            "source_apl_sha256":"c"*64,"source_native_json2_sha256":"d"*64,
            "source_simc_executable_sha256":"e"*64,
            "precombat_sequence":[],
            "combat_sequence":[event(0,"alpha" if spec=="one" else "beta",123),
                               event(11000,"auto_attack",0)]}
    models=[model("s1","class1","alpha"),model("s2","class2","beta")]
    source={"schema":SOURCE_IR_SCHEMA,"product_policy_id":POLICY,
        "source_model_count":2,"source_IF_ELSE_rows":6,
        "product_expected_casts_verified":0,"complete_READY_proven":0,
        "WCL_API_calls":0,"MAIN_promoted":False,
        "research_models":models}
    cases=[]
    captures={}
    for key,sp in (("s1","one"),("s2","two")):
        for name,num in (("st",1),("2t",2)):
            cases.append({"source_spec_key":key,"source_case_key":name,
                "target_count":num,"source_profile_git_blob":"a"*40,
                "simc_actor_spec":sp,"profile_sha256":"b"*64,
                "effective_apl_sha256":"c"*64})
            captures[key,name]=seq(sp)
    manifest={"schema":CASE_SCHEMA,"product_policy_id":POLICY,
              "cases":cases}
    r=build(source,captures,source_ir_sha256="f"*64,manifest=manifest)
    assert r["source_model_count"]==2 and r["target_count_cases"]==4
    assert r["actual_simc_JSON2_observed_action_count"]==8
    assert r["full_ready_proven"]==0
    for case in r["research_cases"]:
        a=case["observed_first_window_actions"][0]
        assert a["exact_source_row_used"]=="UNKNOWN"
        assert len(a["potential_APL_source_rows_by_action_name_ONLY"]) in (0,2)
        assert case["opener_end_transition"]=="UNKNOWN"
        assert case["dummy_error_verdict"]=="UNKNOWN"
        assert case["observed_after_window_actions"][0]["action_token"]=="auto_attack"
    forged=json.loads(json.dumps(manifest))
    forged["cases"][0]["target_count"]=2
    try:build(source,captures,source_ir_sha256="f"*64,manifest=forged)
    except CastDeliveryError:pass
    else:raise AssertionError("FORGED_TARGET_COUNT_ACCEPTED")
    forged_seq=json.loads(json.dumps(captures["s1","st"]))
    forged_seq["source_capture_status"]="SYNTHETIC_CAPTURE_TEST"
    original=captures["s1","st"]
    captures["s1","st"]=forged_seq
    try:build(source,captures,source_ir_sha256="f"*64,manifest=manifest)
    except CastDeliveryError:pass
    else:raise AssertionError("SYNTHETIC_CAPTURE_PROMOTED")
    captures["s1","st"]=original
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":23,"unrelated_specs":2,
            "source_APL_rows_reparsed":False,
            "same_timestamp_not_strict_PRE":True,
            "cast_source_row_unique_mapping_claims":0,
            "target_dummy_mistakes_proven":0,"WCL_API_calls":0}


def main()->None:
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source-research",type=Path)
    cli.add_argument("--expected-source-sha256")
    cli.add_argument("--case-manifest",type=Path)
    cli.add_argument("--out",type=Path)
    cli.add_argument("--window-ms",type=int,default=10000)
    a=cli.parse_args()
    if all(x is None for x in (a.source_research,a.expected_source_sha256,
                               a.case_manifest,a.out)):
        print(json.dumps(selftest(),sort_keys=True));return
    ensure(all(x is not None for x in (
        a.source_research,a.expected_source_sha256,a.case_manifest,a.out)) and
           isinstance(a.expected_source_sha256,str) and
           HASH64.fullmatch(a.expected_source_sha256) is not None,
           "SOURCE_MANIFEST_SHA256_OUT_REQUIRED")
    raw=a.source_research.read_bytes()
    ensure(sha256(raw).hexdigest()==a.expected_source_sha256,
           "SOURCE_RESEARCH_MODEL_HASH_MISMATCH")
    original=json.loads(raw)
    manifest=json.loads(a.case_manifest.read_bytes())
    captures={}
    for entry in manifest["cases"]:
        key=(entry["source_spec_key"],entry["source_case_key"])
        ensure(key not in captures,"CAPTURE_CASE_DUPLICATE")
        captures[key]=read_actual_capture(entry)
    result=build(original,captures,manifest=manifest,
                 source_ir_sha256=a.expected_source_sha256,window_ms=a.window_ms)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canonical(result))
    print("SIMC_FIRST_OBSERVED_CAST_GENERAL_ROTATION_RESEARCH_SHA256="+
          sha256(a.out.read_bytes()).hexdigest())


if __name__=="__main__":
    main()
