#!/usr/bin/env python3
"""Original native selected-IF gap planner, with no derived WoW priority.

Reads pinned per-case *actual* native replay JSON and original typed SimC APL.
Ranks missing source PRE operands by observed selection frequency and early
10-second sample counts. An actor's adapter field belongs only to that actor;
a missing symbol is an observability need, NOT inferred false or not-ready.

Classify exact nonforeground combat APL rows as source-declared use_off_gcd
candidate ONLY; a source flag is not the actual off-GCD execution witness.
No SimC build or WCL calls. No CLI flags -> synthetic tests (safe in PyCharm).
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile, git_blob, canonical
from general_rotation_original_dispatch_if_replay_v1 import SCHEMA as REPLAY_SCHEMA

SCHEMA="ZrotGeneralRotationOriginalIFMissingOperandPriorityWorklistV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
RECEIPT_SCHEMA="ZrotGenericOriginalDispatchSameCallSourceIFReplayReceiptV1"
FORE="SOURCE_IF_REPLAY_MATCH_ORIGINAL_NATIVE_SAME_CALL"
MISSING="UNKNOWN_SOURCE_IF_MISSING_VALID_ORIGINAL_PRE"
PLAIN="SOURCE_APL_NO_EXPLICIT_IF_NOT_READY_PROOF"


class GapError(ValueError):pass


def need(c:bool,reason:str):
    if not c:raise GapError(reason)


def load_json(path:Path)->tuple[dict,bytes]:
    need(path.is_file() and not path.is_symlink(),"INPUT_MISSING_OR_SYMLINK")
    raw=path.read_bytes()
    need(0<len(raw)<10_000_000,"INPUT_OUT_OF_BOUNDS")
    def nodup(pairs):
        out={}
        for k,v in pairs:
            need(k not in out,"DUPLICATE_JSON_KEY")
            out[k]=v
        return out
    obj=json.loads(raw,object_pairs_hook=nodup)
    need(type(obj)==dict,"NOT_JSON_OBJECT")
    return obj,raw


def evaluate(reports:list[tuple[dict,dict,bytes]], *,
             expected_total:int=203,expected_direct:int=147,
             window_ms:int=10000)->dict:
    """Each tuple is (original offline report, source case receipt, profile bytes)."""
    need(1000<=window_ms<=30000,"INVALID_WINDOW")
    need(len(reports)>0 and len(reports)==len({
        (c["spec"],c["target_count"]) for _,c,_ in reports
    }),"DUPLICATE_OR_MISSING_CASE")
    per_case=[];counts=Counter()
    symbol_frequency=defaultdict(Counter);first_symbol_frequency=defaultdict(Counter)
    symbol_combo=defaultdict(Counter);unknown_examples=[];alt_routes=[]
    source_rows=[]
    for report,case,profile in reports:
        need(report.get("schema")==REPLAY_SCHEMA and
             report.get("source_spec_label")==case["spec"] and
             report.get("target_count")==case["target_count"] and
             report.get("actual_original_emitter_records")>0 and
             report.get("full_physical_READY_proven")==0 and
             report.get("WCL_blind_holdout")=="NOT_RUN" and
             report.get("source_priority_competitors_proven")==0 and
             report.get("source_PRE_adapter_applies")==(
                 case["spec"]=="warrior_fury"),
             "ORIGINAL_REAL_CASE_BOUNDARY_INVALID")
        ast=parse_profile(profile,require_source=False)
        need(report["profile_git_blob"]==git_blob(profile),
             "SOURCE_PROFILE_DIGEST_CHANGED")
        per_case.append({"spec":case["spec"],
                         "target_count":case["target_count"],
                         "source_sha256":sha256(profile).hexdigest(),
                         "source_git_blob":git_blob(profile),
                         "replay_counts":report["source_IF_triage_counts"]})
        counts.update(report["source_IF_triage_counts"])
        for row in report["source_IF_exact_selected_rows"]:
            need(row["source_list"] in ast["action_lists"] and
                 0<row["source_rank"]<=len(ast["action_lists"][row["source_list"]]),
                 "SELECTED_ROW_OUTSIDE_ORIGINAL_SOURCE")
            source=ast["action_lists"][row["source_list"]][row["source_rank"]-1]
            need(row["source_row_sha256"]==source["source_sha256"] and
                 row["source_action"]==source["action"] and
                 row["source_if"]==(
                     None if "if" not in source["expression_fields"] else
                     source["expression_fields"]["if"]["source"]),
                 "SELECTED_ROW_NOT_ORIGINAL_PROFILE_SOURCE")
            if row["replay_verdict"]!=MISSING:
                continue
            need(row["source_if"] and
                 row["source_IF_independent_truth"]=="UNKNOWN" and
                 row["full_action_READY_proven"] is False,
                 "UNKNOWN_ROW_PROVENANCE_DRIFT")
            sym=set(row["source_if_symbols"])
            need(bool(sym),"UNKNOWN_IF_WITHOUT_SYMBOLS")
            # Claim *coverage demand*, not that these inputs alone will
            # close a short-circuit expression or prove physical READY.
            if report["source_PRE_adapter_applies"]:
                sym -= {"rage","buff.recklessness.up"}
            need(sym,"UNKNOWN_SOURCE_IF_MISSING_SYMBOL_SET_EMPTY")
            group=case["spec"]
            for s in sym:
                symbol_frequency[group][s]+=1
                if row["t_ms"]<window_ms:
                    first_symbol_frequency[group][s]+=1
            symbol_combo[group][tuple(sorted(sym))]+=1
            if len(unknown_examples)<25:
                unknown_examples.append({
                    "spec":group,"targets":case["target_count"],
                    "t_ms":row["t_ms"],"source_list":row["source_list"],
                    "source_rank":row["source_rank"],
                    "source_action":row["source_action"],
                    "missing_symbols":sorted(sym),
                    "original_if_status":"UNKNOWN"})
        for row in report["non_foreground_combat_emitter_rows"]:
            source=ast["action_lists"][row["source_list"]][row["source_rank"]-1]
            need(source["action"]==row["source_action"] and
                 row["missing_route"]=="UNKNOWN",
                 "UNPROVEN_ALTERNATIVE_COMBAT_ROUTE")
            attr={i["key"]:i["value"] for i in source["attributes"]}
            alt_routes.append({
                "spec":case["spec"],"targets":case["target_count"],
                "source_list":row["source_list"],
                "source_rank":row["source_rank"],
                "source_action":source["action"],
                "source_line":source["source_line"],
                "source_row_sha256":source["source_sha256"],
                "JSON2_ordinal":row["JSON2_ordinal"],
                "t_ms":row["t_ms"],
                "source_declares_use_off_gcd":attr.get("use_off_gcd")=="1",
                "source_value_use_off_gcd":attr.get("use_off_gcd"),
                "actual_native_off_gcd_queue_path":"UNKNOWN",
                "actual_native_off_gcd_execute_path":"UNKNOWN",
                "source_flag_not_causal_path_witness":True})
        source_rows.extend(report["source_IF_exact_selected_rows"])
    need(sum(counts.values())==expected_total and len(source_rows)==expected_direct,
         "PINNED_EMITTER_AND_APL_DIRECT_COUNTS_DRIFT")
    need(counts[MISSING]==78 and counts[PLAIN]==54 and
         counts[FORE]==15 and
         counts["PRECOMBAT_SEPARATE_ORIGINAL_EXECUTION_PATH"]==54 and
         counts["UNKNOWN_NON_FOREGROUND_COMBAT_EXECUTION_PATH"]==2 and
         len(alt_routes)==2,"PREVIOUS_VALIDATED_PROVENANCE_PARTITION_CHANGED")
    per_spec={}
    for spec in sorted(symbol_frequency):
        freq=symbol_frequency[spec]
        early=first_symbol_frequency[spec]
        ordered=sorted(freq,
                       key=lambda s:(-(2*early[s]+freq[s]),-early[s],s))
        per_spec[spec]={
          "candidate_source_PRE_fields":[
             {"symbol":s,"selected_unknown_IF_rows_with_dependency":freq[s],
              "first_10s_unknown_IF_rows_with_dependency":early[s],
              "observability_priority_score":2*early[s]+freq[s],
              "adding_field_alone_will_complete_IF_truth":"NOT_PROVEN"}
             for s in ordered],
          "missing_symbol_sets":[
             {"symbols":list(k),"unknown_selected_rows":v}
             for k,v in sorted(symbol_combo[spec].items(),
                               key=lambda kv:(-kv[1],kv[0]))[:20]],
        }
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "source_original_policy":"PINNED_ACTUAL_NATIVE_SAME_RUN_ONLY",
        "source_actual_emitter_records":expected_total,
        "source_original_foreground_selection_callsite":expected_direct,
        "selected_IF_source_triage":dict(sorted(counts.items())),
        "per_spec_missing_PRE_priority":per_spec,
        "missing_PRE_examples":unknown_examples,
        "nonforeground_combat_source_flag_triage":alt_routes,
        "precombat_records_not_misclassified_as_combat":True,
        "first_window_ms_NOT_opener_end":window_ms,
        "any_missing_ingredient_proven_false":False,
        "native_if_result_used_as_source_replay_input":False,
        "spell_based_generic_execution_rules_created":False,
        "full_READY_positive_proven":0,"WCL_holdout":"NOT_RUN",
        "dummy_wrong_cast":"UNKNOWN","new_CXX_builds":0,
        "new_WCL_API_calls":0,"MAIN_promoted":False}


def selftest()->dict:
    # Input contract negative tests cannot turn UNKNOWN into READY.
    empty={"schema":REPLAY_SCHEMA,"source_spec_label":"mage_arcane",
           "target_count":1,"actual_original_emitter_records":1,
           "source_PRE_adapter_applies":False,
           "full_physical_READY_proven":0,
           "source_priority_competitors_proven":0,
           "WCL_blind_holdout":"NOT_RUN",
           "source_IF_triage_counts":{},
           "profile_git_blob":"bad",
           "source_IF_exact_selected_rows":[],
           "non_foreground_combat_emitter_rows":[]}
    case={"spec":"mage_arcane","target_count":1}
    negatives=0
    for mutate in (
        {},
        {"target_count":2},
        {"source_PRE_adapter_applies":True},
        {"full_physical_READY_proven":1},
        {"source_priority_competitors_proven":1},
        {"WCL_blind_holdout":"PASS"},
    ):
        t={**empty,**mutate}
        try:evaluate([(t,case,b'mage="Synthetic"\nspec=arcane\nactions=arcane_blast\n')])
        except GapError:negatives+=1
        else:raise AssertionError("UNPINNED_ORIGINAL_SOURCE_ACCEPTED")
    need(negatives==6,"NEGATIVE_CONTROLS_FAILED")
    return {"schema":SCHEMA,"selftest":"PASS_OFFLINE_SYNTHETIC",
            "negative_controls":negatives,"new_CXX_builds":0,
            "WCL_API_calls":0,"full_READY_proven":0}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--receipt",type=Path)
    ap.add_argument("--artifact-root",type=Path)
    ap.add_argument("--source-root",type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if all(v is None for v in vars(args).values()):
        print(json.dumps(selftest(),sort_keys=True))
        return
    need(all(v is not None for v in vars(args).values()),
         "EXPLICIT_ACTUAL_REPLAY_INPUTS_REQUIRED")
    receipt,_=load_json(args.receipt)
    need(receipt.get("schema")==RECEIPT_SCHEMA and
         receipt.get("validation",{}).get("actions_id")==42587480633 and
         receipt.get("original_same_run_evidence",{}).get(
             "independently_replayed_source_if_matching_original_native",{}
             ).get("total")==15 and
         receipt.get("validation",{}).get("conclusion")=="success",
         "PINNED_PRIOR_REAL_SOURCE_IF_RECEIPT_INVALID")
    filenames={"warrior_fury":"MID2_Warrior_Fury.simc",
               "mage_arcane":"MID2_Mage_Arcane.simc"}
    payload=[]
    for item in receipt["original_same_run_evidence"]["exact_partition"].items():
        pass
    names={"warrior_fury_st","warrior_fury_2t",
           "mage_arcane_st","mage_arcane_2t"}
    need(set(receipt["validation"]["case_report_sha256"])==names,
         "EXACT_CASE_SOURCE_SHA256_ROSTER_DRIFT")
    for key in sorted(names):
        spec,mode=key.rsplit("_",1)
        file=args.artifact_root/(spec+"-"+mode+".json")
        report,raw=load_json(file)
        need(sha256(raw).hexdigest()==
             receipt["validation"]["case_report_sha256"][key],
             "REAL_ORIGINAL_SOURCE_IF_CASE_DIGEST_DRIFT")
        target=1 if mode=="st" else 2
        profile=(args.source_root/"profiles"/"MID2"/filenames[spec]).read_bytes()
        payload.append((report,{"spec":spec,"target_count":target},profile))
    result=evaluate(payload)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("xb") as f:f.write(canonical(result))
    print("ORIGINAL_SELECTED_SOURCE_IF_GAP_WORKLIST_SHA256="+
          sha256(args.out.read_bytes()).hexdigest())
    for spec,stats in result["per_spec_missing_PRE_priority"].items():
        print("ORIGINAL_SOURCE_MISSING_PRE_PRIORITY_"+spec+"="+
              json.dumps(stats["candidate_source_PRE_fields"][:12],
                         sort_keys=True))
    print("OFF_GCD_SOURCE_FLAG_ONLY_NOT_NATIVE_CAUSAL_PATH="+
          json.dumps(result["nonforeground_combat_source_flag_triage"],
                     sort_keys=True))


if __name__=="__main__":
    main()
