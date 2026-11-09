#!/usr/bin/env python3
"""Same-run exact APL source row attribution for original SimC JSON2 actions.

The proof is SIMC-native:
  - source-pinned pure metadata hook inside player_t::sequence_add();
  - original action_t* and exact signature-pointer source row;
  - same collected sequence (precombat vs combat) AND exact JSON2 ordinal;
  - native JSON2 raw file verified by existing capture receipt;
  - previously captured *pristine* same-seed action sequence parity.

No cast is attributed by name/time heuristic alone. No inferable APL
condition truth/complete READY or optimality. Executed action JSON2 is
NOT a live WoW cast. Queue failures and no-signature actions stay separate.

No args: offline synthetic selftest; CLI needs source, live trace and receipts.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from simc_apl_semantic_ir_v2 import canonical,git_blob
from simc_native_json_sequence import extract_json_sequence
from simc_native_select_trace_instrument_v1 import SIMC_COMMIT,PLAYER_CPP_BLOB
from simc_native_sequence_apl_row_producer_v1 import (
    SCHEMA as PRODUCER_SCHEMA,MARK,sha)
from general_rotation_simc_native_cast_delivery_v1 import (
    SCHEMA as BASE_SCHEMA,POLICY)

SCHEMA="ZrotOriginalSimCJson2ExactEmittedAPLRowReplayV1"
HEX64=re.compile(r"^[a-f0-9]{64}$")
HEX40=re.compile(r"^[a-f0-9]{40}$")
POINTER=re.compile(r"^0x[0-9a-fA-F]+$")


class ExactEmissionError(ValueError):pass


def need(ok:bool,label:str):
    if not ok:raise ExactEmissionError(label)


def parse_marker_log(log:str)->dict:
    records={}
    for line in log.splitlines():
        if MARK not in line:continue
        need(line.count(MARK)==1,"DUPLICATE_EMISSION_LOG_PREFIX")
        parts=line.split(MARK,1)[1].strip().split("|")
        need(len(parts)==7,"EMISSION_MARKER_FIELD_COUNT")
        t_s,phase,index_s,action,owner,rank_s,ptr=parts
        need(t_s.isdecimal() and index_s.isdecimal() and
             rank_s.isdecimal() and
             phase in ("P","C") and action and
             POINTER.fullmatch(ptr) is not None,
             "EMISSION_MARKER_MALFORMED")
        t=int(t_s);idx=int(index_s);rank=int(rank_s)
        need((rank>0 and owner!="-") or (rank==0 and owner=="-"),
             "PARTIAL_SOURCE_ROW_IDENTITY_FORGED")
        key=(phase,idx)
        need(key not in records,"DUPLICATE_JSON2_EMISSION_ORDINAL")
        records[key]={"t_ms":t,"kind":phase,"ordinal":idx,
                      "action_name":action,"owner":owner,
                      "rank_one_based":rank,"ptr":ptr.lower()}
    need(bool(records),"ACTUAL_ORIGINAL_JSON2_EMISSION_MARKERS_MISSING")
    return records


def action_key(row:dict)->tuple:
    return (row["timestamp_ms"],row["action_token"],row["numeric_action_id"],
            row["ordinal"])


def compare_pristine(original_case:dict,probe:dict)->dict:
    """Compare complete JSON2 observed sample action sequences, not source returns.

    Native original 'observed' evidence belongs to a different run.
    This parity is a separate check and never used as direct source-row proof.
    """
    old=original_case["simc_JSON2_observed_combat_action_sequence"]
    current=[r for r in probe["combat_sequence"]
             if r["record_kind"]=="SAMPLE_ACTION"]
    need(len(old)==len(current)==original_case[
         "simc_JSON2_observed_combat_action_count"],
         "PRISTINE_AND_PROBE_COMBAT_LENGTH_DRIFT")
    need([(
        x["at_simc_ms"],x["action_token"],x["numeric_spell_id"],
        x["sequence_ordinal"]) for x in old]==
         [action_key(x) for x in current],
         "PRISTINE_AND_PROBE_COMBAT_ACTION_SEQUENCE_CHANGED")
    precombat=[x for x in probe["precombat_sequence"]
               if x["record_kind"]=="SAMPLE_ACTION"]
    old_pre=original_case["simc_JSON2_precombat_action_sequence"]
    need(len(precombat)==len(old_pre) and
         [(x["at_simc_ms"],x["action_token"],x["numeric_spell_id"],
           x["sequence_ordinal"]) for x in old_pre]==
         [action_key(x) for x in precombat],
         "PRISTINE_AND_PROBE_PRECOMBAT_ACTION_SEQUENCE_CHANGED")
    # Previous source model intentionally stored per-type counts, but did
    # not claim exact wait intervals. Compare recorded *counts* without
    # inventing missing pristine ordering.
    for phase,name in ((probe["combat_sequence"],"combat"),
                       (probe["precombat_sequence"],"precombat")):
        current_counts=Counter(x["record_kind"] for x in phase)
        previous=original_case["simc_JSON2_"+name+"_record_kinds"]
        need(dict(current_counts)==previous,
             "PRISTINE_AND_PROBE_RECORD_TYPE_COUNTS_CHANGED:"+name)
    return {
        "recorded_combat_action_order_and_times_unchanged":True,
        "recorded_precombat_action_order_and_times_unchanged":True,
        "record_kind_counts_unchanged":True,
        "complete_raw_JSON2_bytes_equal":"NOT_CLAIMED",
        "same_simc_executable_binary":"NO_PATCHED_BINARY_HAS_DIFFERENT_SHA",
    }


def reconcile_case(original_case:dict,probe:dict,raw_log:str)->dict:
    need(original_case["source_spec_key"] and
         original_case["simc_actor_spec"]==probe["simc_spec"] and
         original_case["target_count"]>0,
         "PROBE_ACTOR_OR_TARGET_CONTRACT_MISSING")
    parity=compare_pristine(original_case,probe)
    markers=parse_marker_log(raw_log)
    seen=set();totals=Counter();reported={"precombat":[],"combat":[]}
    apl_lists=original_case["source_APL_priority_model"]
    for phase,rows in (("P",probe["precombat_sequence"]),
                       ("C",probe["combat_sequence"])):
        for row in rows:
            if row["record_kind"]=="WAIT_NON_ACTION":
                totals["wait_non_action_not_attributed"]+=1
                continue
            need(row["record_kind"] in ("SAMPLE_ACTION",
                 "ACTION_RECORDED_QUEUE_FAILED"),
                 "UNRECOGNIZED_JSON2_ACTION_RECORD_TYPE")
            key=(phase,row["ordinal"])
            marker=markers.get(key)
            if marker is None:
                totals["UNKNOWN_NO_EXACT_SAME_RUN_EMITTER"]+=1
                continue
            seen.add(key)
            need(marker["t_ms"]==row["timestamp_ms"],
                 "JSON2_AND_SOURCE_EMISSION_TIMESTAMP_CONFLICT")
            # Source row is identified by the exact *action object*
            # signature, not by its name: reporting names may differ.
            obj={
                "simc_time_ms":row["timestamp_ms"],
                "sequence_kind":"PRECOMBAT" if phase=="P" else "COMBAT",
                "JSON2_ordinal":row["ordinal"],
                "JSON2_action_name":row["action_token"],
                "numeric_spell_id":row["numeric_action_id"],
                "original_action_object_name":marker["action_name"],
                "source_APL_list":marker["owner"],
                "source_APL_index_one_based":marker["rank_one_based"],
                "source_APL_row_sha256":None,
                "source_APL_IF":None,
                "source_action_token":None,
                "source_provenance":"SIMC_SAME_RUN_ACTUAL_SEQUENCE_APPEND",
                "same_object_signatures_paired_to_JSON2_ordinal":True,
                "behavior_from_source":"UNKNOWN",
                "exact_source_row_status":"UNKNOWN_NO_SOURCE_SIGNATURE",
                "condition_truth_at_native_select":"UNKNOWN",
                "readiness_of_competitors":"UNKNOWN",
                "full_READY":"UNKNOWN",
                "sample_kind":row["record_kind"],
                "is_WoW_player_spellcast":False,
                "is_dummy_mistake":False,
            }
            owner=marker["owner"];rank=marker["rank_one_based"]
            if rank>0:
                need(owner in apl_lists and rank<=len(apl_lists[owner]),
                     "EXACT_OBJECT_SIGNATURE_NOT_IN_PINNED_APL_SOURCE")
                candidate=apl_lists[owner][rank-1]
                need(candidate["rank_in_source_list"]==rank and
                     HEX64.fullmatch(candidate["source_row_sha256"]) is not None,
                     "APL_ROW_INDEX_OR_SHA_DRIFT")
                obj.update({
                    "source_APL_row_sha256":candidate["source_row_sha256"],
                    "source_APL_IF":candidate["when_source_IF"],
                    "source_action_token":candidate["action"],
                    "behavior_from_source":candidate["kind"],
                    "exact_source_row_status":"SOURCE_POINTER_SIGNATURE_EXACT",
                })
                totals["exact_source_row_pointer_signature"]+=1
            else:
                totals["UNKNOWN_NO_SOURCE_SIGNATURE"]+=1
            if marker["action_name"]!=row["action_token"]:
                totals["source_action_reporting_name_mismatch"]+=1
            if row["record_kind"]=="ACTION_RECORDED_QUEUE_FAILED":
                totals["queue_failed_source_witness_not_performed"]+=1
            reported["precombat" if phase=="P" else "combat"].append(obj)
    # No silent discard of producer markers. Multiple same-time rows may be
    # kept distinct via native JSON2 ordinal and original pointer.
    need(seen==set(markers),"UNPAIRED_OR_CROSS_ACTOR_JSON2_EMITTER")
    return {
        "source_spec_key":original_case["source_spec_key"],
        "target_count":original_case["target_count"],
        "source_case":original_case["case"],
        "parity":parity,
        "counts":dict(sorted(totals.items())),
        "actual_precombat_emitted_actions":reported["precombat"],
        "actual_combat_emitted_actions":reported["combat"],
        "original_json2_action_count":original_case[
            "simc_JSON2_observed_combat_action_count"],
        "exact_source_row_proof_claim":
            "SAME_RUN_SEQUENCE_APPEND_SIGNATURE_ONLY_NOT_READY",
        "source_only_APL_priority_ir_unchanged":True,
        "original_select_decision_time_state":"NOT_CAPTURED",
        "WCL_blind_candidate_lock":"NOT_RUN",
        "dummy_user_mistake":"UNKNOWN",
    }


def verify_original_producer(root:Path,receipt:dict)->None:
    require_keys={
        "schema":PRODUCER_SCHEMA,"policy_id":POLICY,
        "original_simc_revision":SIMC_COMMIT,
        "original_player_cpp_git_blob_sha1":PLAYER_CPP_BLOB,
        "original_JSON2_appends_unchanged":True,
        "ready_or_RNG_calls_added":0,
        "evidence_point":"BEFORE_SAME_JSON2_EMPLACE_BACK",
    }
    need(all(receipt.get(k)==v for k,v in require_keys.items()),
         "PINNED_CPP_EMISSION_PRODUCER_RECEIPT_INVALID")
    from simc_native_sequence_apl_row_producer_v1 import patch
    git=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    need(git==SIMC_COMMIT,"PRODUCER_ORIGINAL_SIMC_SOURCE_REV_CHANGED")
    original=subprocess.run(
        ["git","-C",str(root),"show","HEAD:engine/player/player.cpp"],
        check=True,capture_output=True).stdout
    need(git_blob(original)==PLAYER_CPP_BLOB and
         sha(original)==receipt.get("original_player_cpp_sha256") and
         sha(patch(original))==receipt.get("patched_player_cpp_sha256") and
         sha((root/"engine/player/player.cpp").read_bytes())==
             receipt["patched_player_cpp_sha256"],
         "ACTUAL_INSTRUMENTED_SOURCE_BYTES_NOT_PINNED")


def audit(base:dict,root:Path,manifest:dict,producer:dict)->dict:
    need(base.get("schema")==BASE_SCHEMA and
         base.get("policy_id")==POLICY and
         base.get("full_ready_proven")==0 and
         base.get("WCL_independent_holdout")=="NOT_RUN" and
         base.get("target_dummy_error_verdict")=="UNKNOWN" and
         base.get("MAIN_promoted") is False,
         "BASELINE_SOURCE_IR_INVALID")
    verify_original_producer(root,producer)
    need(manifest.get("schema")==
         "ZrotSameRunJson2APLRowReconciliationManifestV1" and
         len(manifest.get("cases",[]))==base["target_count_cases"],
         "REAL_ORIGINAL_EMISSION_CASE_MANIFEST_REQUIRED")
    cases={(
        item["source_spec_key"],item["case"]):item
        for item in base["research_cases"]}
    need(len(cases)==base["target_count_cases"],
         "BASELINE_JSON2_CASES_DUPLICATED")
    output=[];global_counts=Counter();seen=set();binaries=set()
    for entry in manifest["cases"]:
        key=(entry["source_spec_key"],entry["source_case"])
        need(key in cases and key not in seen,
             "UNKNOWN_OR_DUPLICATE_REAL_EMISSION_CASE")
        seen.add(key)
        orig=cases[key]
        need(orig["target_count"]==entry["target_count"] and
             orig["simc_actor_spec"]==entry["actor_spec"] and
             entry["profile_git_blob"]==orig["source_profile_git_blob_sha1"],
             "ORIGINAL_PROFILE_TARGET_CASE_IDENTITY_DRIFT")
        ref=Path(entry["reference_dir"]).resolve(strict=True)
        seq=extract_json_sequence(ref)
        raw_log=(ref/"simc_native_log.txt").read_bytes()
        capture=json.loads((ref/"simc_reference_receipt.json").read_bytes())
        original_blob=(root/entry["official_profile_relpath"]).read_bytes()
        need(git_blob(original_blob)==entry["profile_git_blob"] and
             capture.get("controlled_target_count")==entry["target_count"] and
             capture.get("controlled_seed")==31459 and
             capture.get("controlled_fight_seconds")==30 and
             capture.get("simc_spec")==entry["actor_spec"] and
             capture.get("profile_sha256")==sha(original_blob) and
             seq["simc_spec"]==entry["actor_spec"] and
             seq["source_profile_sha256"]==capture["profile_sha256"] and
             seq["source_apl_sha256"]==entry["effective_apl_sha256"] and
             entry["effective_apl_sha256"]==capture["effective_apl_sha256"],
             "REAL_CAPTURE_SOURCE_TARGET_SEED_OR_APL_DRIFT")
        # The pristine original baseline from #42562520191 is a DIFFERENT
        # binary, but the pinned profile/APL and original cast sequence are
        # required to agree. No binary-hash equivalence is claimed.
        binaries.add(seq["source_simc_executable_sha256"])
        case=reconcile_case(orig,seq,raw_log.decode("utf-8"))
        case["raw_instrumented_native_log_sha256"]=sha(raw_log)
        case["instrumented_JSON2_sha256"]=seq["source_native_json2_sha256"]
        for k,v in case["counts"].items():global_counts[k]+=v
        output.append(case)
    need(len(seen)==len(cases) and len(binaries)==1,
         "MISSING_CASE_OR_MIXED_INSTRUMENTED_BINARY")
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "source_producer_schema":PRODUCER_SCHEMA,
        "original_CPP_revision":SIMC_COMMIT,
        "source_row_witness":"ORIGINAL_ACTION_SIGNATURE_IN_SAME_JSON2_EMITTER",
        "original_pristine_and_instrumented_sequences_compared":True,
        "pristine_vs_instrumented_Native_binary_bytes_equal":False,
        "cases":output,
        "counts":dict(sorted(global_counts.items())),
        "full_positive_READY_proven":0,
        "source_IF_at_actual_select_time":"UNKNOWN_UNLESS_EXPLICITLY_PROVEN",
        "opener_end":"UNKNOWN",
        "WCL_blind_holdout":"NOT_RUN",
        "dummy_mistake_permitted":False,
        "source_observed_action_not_WoW_cast":True,
        "WCL_API_calls":0,"MAIN_promoted":False,
    }


def selftest()->dict:
    def marker(t,ph,idx,act,owner,rank,ptr):
        return f"{MARK}{t}|{ph}|{idx}|{act}|{owner}|{rank}|{ptr}"
    trace="\n".join((
        marker(0,"C",0,"alpha","part",1,"0x01"),
        marker(0,"C",1,"alpha","part",2,"0x02"),
        marker(0,"P",0,"prep","-",0,"0x03"),
    ))
    parsed=parse_marker_log(trace)
    assert len(parsed)==3 and parsed[("C",0)]["rank_one_based"]==1
    assert parsed[("C",1)]["rank_one_based"]==2
    assert parsed[("P",0)]["owner"]=="-"
    try:parse_marker_log(trace+"\n"+marker(1,"C",0,"dup","part",1,"0x04"))
    except ExactEmissionError:pass
    else:raise AssertionError("DUPLICATE_ORDINAL_ALLOWED")
    original={"source_spec_key":"synthetic","case":"st","simc_actor_spec":"synthetic",
              "target_count":1,"simc_JSON2_observed_combat_action_count":2,
              "simc_JSON2_combat_record_kinds":{"SAMPLE_ACTION":2},
              "simc_JSON2_precombat_record_kinds":{"SAMPLE_ACTION":1},
              "simc_JSON2_observed_combat_action_sequence":[
                  {"at_simc_ms":0,"action_token":"alpha","numeric_spell_id":123,
                   "sequence_ordinal":0},
                  {"at_simc_ms":0,"action_token":"alpha","numeric_spell_id":123,
                   "sequence_ordinal":1}],
              "simc_JSON2_precombat_action_sequence":[
                  {"at_simc_ms":0,"action_token":"prep","numeric_spell_id":9,
                   "sequence_ordinal":0}],
              "source_APL_priority_model":{
                  "part":[{"rank_in_source_list":1,"source_row_sha256":"a"*64,
                           "when_source_IF":"buff.x.up","action":"alpha","kind":"ACTION"},
                          {"rank_in_source_list":2,"source_row_sha256":"b"*64,
                           "when_source_IF":"buff.y.up","action":"alpha","kind":"ACTION"}]
              }}
    def entry(kind,idx,name,id):
        return {"timestamp_ms":0,"ordinal":idx,"record_kind":"SAMPLE_ACTION",
                "queue_failed":False,"action_token":name,"numeric_action_id":id}
    probe={"simc_spec":"synthetic",
           "combat_sequence":[entry("C",0,"alpha",123),entry("C",1,"alpha",123)],
           "precombat_sequence":[entry("P",0,"prep",9)]}
    verified=reconcile_case(original,probe,trace)
    assert verified["counts"]["exact_source_row_pointer_signature"]==2
    assert verified["counts"]["UNKNOWN_NO_SOURCE_SIGNATURE"]==1
    assert [x["source_APL_row_sha256"] for x in
            verified["actual_combat_emitted_actions"]]==["a"*64,"b"*64]
    assert verified["parity"]["recorded_combat_action_order_and_times_unchanged"]
    wrongly=trace.replace("|C|1|alpha|part|2|","|C|1|alpha|part|3|")
    try:reconcile_case(original,probe,wrongly)
    except ExactEmissionError:pass
    else:raise AssertionError("OUT_OF_RANGE_SOURCE_ROW_ACCEPTED")
    badly=json.loads(json.dumps(probe))
    badly["combat_sequence"][1]["timestamp_ms"]=10
    try:reconcile_case(original,badly,trace)
    except ExactEmissionError:pass
    else:raise AssertionError("ALTERED_NATIVE_CAST_TIME_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":21,
        "different_same_time_same_name_rows_distinguished_by_ordinal":True,
        "source_ptr_is_not_name_heuristic":True,
        "full_positive_READY_proven":0,
        "WCL_API_calls":0,
        "real_CPP_executed":False,
    }


def main()->None:
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--baseline",type=Path)
    cli.add_argument("--expected-baseline-sha256")
    cli.add_argument("--source-root",type=Path)
    cli.add_argument("--manifest",type=Path)
    cli.add_argument("--producer-receipt",type=Path)
    cli.add_argument("--out",type=Path)
    a=cli.parse_args()
    inputs=(a.baseline,a.expected_baseline_sha256,a.source_root,
            a.manifest,a.producer_receipt,a.out)
    if all(x is None for x in inputs):
        print(json.dumps(selftest(),sort_keys=True));return
    if any(x is None for x in inputs):cli.error("all source arguments required")
    base_raw=a.baseline.read_bytes()
    need(HexSha(a.expected_baseline_sha256) and
         sha(base_raw)==a.expected_baseline_sha256,
         "BASELINE_ORIGINAL_JSON2_RESEARCH_BYTES_UNPINNED")
    result=audit(json.loads(base_raw),a.source_root,
                 json.loads(a.manifest.read_bytes()),
                 json.loads(a.producer_receipt.read_bytes()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canonical(result))
    print("SIMC_SAME_RUN_APL_ROW_TO_JSON2_SHA256="+sha(a.out.read_bytes()))


def HexSha(x):
    return isinstance(x,str) and HEX64.fullmatch(x) is not None


if __name__=="__main__":
    main()
