#!/usr/bin/env python3
"""Generic verified SimC source-IF minimal PRE witness and missing-state frontier.

Consumes a SHA-pinned, ALREADY COMPILED original source-selected evidence
portfolio (not raw spell names, not WCL), and the existing tri-state AST and
partial minimal witness algorithm. Every occurrence remains source-row- and
original native call-scoped. Output identifies evidence savings and missing
source facts; it does NOT derive full READY, a competing action priority,
an opener exit or a target-dummy wrong-cast verdict.

Without CLI arguments, run deterministic spec-neutral synthetic self-test.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import zipfile

from simc_apl_semantic_ir_v2 import canonical, evaluate_ast, truth, ast_symbols
from general_rotation_source_if_minimal_witness_v1 import (
    sufficient_partial_source_witness
)

SCHEMA="ZrotGeneralRotationOriginalPartialSourceIFEvidenceFrontierV1"
MANIFEST="ZrotOriginalNativeSourceIFPortfolioPinnedArtifactV1"
SOURCE_CASE="ZrotGeneralRotationOriginalSelectedSourceEvidenceHypothesisBridgeV1"
SOURCE_PORTFOLIO="ZrotGeneralRotationOriginalSourceConditionalHypothesisPortfolioV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
HEX64=re.compile(r"^[a-f0-9]{64}$")
HEX40=re.compile(r"^[a-f0-9]{40}$")


class FrontierError(ValueError):
    pass


def must(value:bool,code:str)->None:
    if not value:raise FrontierError(code)


def audit_case(source:dict,definition:dict)->dict:
    must(type(source) is dict and source.get("schema")==SOURCE_CASE and
         source.get("policy_id")==POLICY and
         source.get("source_spec")==definition.get("spec_key") and
         source.get("target_count")==definition.get("target_count") and
         source.get("source_commit")==definition.get("source_commit") and
         source.get("source_full_READY_proven")==0 and
         source.get("competitor_ready_proven")==0 and
         source.get("source_order_priority_proven")==0 and
         source.get("opener_end")=="UNKNOWN" and
         source.get("dummy_wrong_skill")=="UNKNOWN" and
         source.get("MAIN_promoted") is False,
         "SOURCE_CASE_AUTHORITY_OR_STATE_CHANGED")
    graph=source.get("source_hypothesis_IR")
    must(type(graph) is dict and
         graph.get("source_git_blob")==definition.get("source_profile_blob") and
         graph.get("spec_key")==source["source_spec"] and
         graph.get("class_key")==source.get("class_key") and
         type(graph.get("source_only_priority_graph")) is dict,
         "SOURCE_PROFILE_GRAPH_PIN_NOT_PROVEN")
    lists=graph["source_only_priority_graph"].get("lists",{})
    must(type(lists) is dict and "default" in lists,
         "PINNED_SOURCE_LISTS_MISSING")
    proofs=source.get("exact_selected_occurrence_proofs")
    must(type(proofs) is list and
         len(proofs)==source.get("original_selected_source_rows") and
         len(proofs)==definition.get("expected_original_rows"),
         "SELECTED_ORIGINAL_OCCURRENCES_NOT_CONSERVED")
    seen_tokens=set()
    seen_calls=set()
    counts=Counter()
    missing=Counter()
    missing_early=Counter()
    minimal_records=[]
    unknown_records=[]
    total_observed=total_needed=total_source_symbols=0
    for row in proofs:
        must(type(row) is dict and
             row.get("observed_source_target_count")==source["target_count"] and
             type(row.get("original_selected_call_id")) is int and
             row["original_selected_call_id"]>0 and
             type(row.get("original_dispatch_token")) is int and
             row["original_dispatch_token"]>0 and
             type(row.get("original_simc_time_ms")) is int and
             row["original_simc_time_ms"]>=0 and
             row["original_selected_call_id"] not in seen_calls and
             row["original_dispatch_token"] not in seen_tokens and
             row.get("real_WoW_expected_action")=="UNKNOWN" and
             row.get("dummy_wrong_cast")=="UNKNOWN" and
             row.get("actual_spell_execution_completion")=="UNKNOWN" and
             row.get("source_ready_proof",{}).get("decision")=="UNKNOWN" and
             row.get("source_order_frontier",{}).get("decision")=="UNKNOWN",
             "SOURCE_NATIVE_OCCURRENCE_UNSAFE_OR_DUPLICATE")
        seen_calls.add(row["original_selected_call_id"])
        seen_tokens.add(row["original_dispatch_token"])
        key=row.get("source_identity",{})
        name=key.get("source_list")
        index=key.get("source_index")
        must(name in lists and type(index) is int and
             0<=index<len(lists[name]),"ORIGINAL_ROW_NOT_IN_PINNED_SOURCE")
        origin=lists[name][index]
        must(origin.get("identity")==key and
             origin.get("action")==row.get("source_action") and
             origin.get("behavior")==row.get("source_behavior") and
             origin.get("kind")==row.get("source_kind") and
             HEX64.fullmatch(key["source_line_sha256"]) is not None,
             "ORIGINAL_SELECTED_ACTION_ROW_SHA_OR_KIND_MISMATCH")
        condition=origin.get("conditions",{}).get("if")
        must(row.get("source_if_AST")==condition,
             "ORIGINAL_SOURCE_AST_CHANGED")
        facts=row.get("original_PRE_symbol_values")
        must(type(facts) is dict and all(
             type(k) is str and type(v) in (int,float,bool) and
             math.isfinite(float(v)) for k,v in facts.items()),
             "NATIVE_ORIGINAL_PRE_NUMERIC_FACTS_INVALID")
        stage=row.get("bounded_condition",{})
        state=stage.get("classification")
        must(state in ("IF_ORIGINAL_PRE_MATCH","IF_ORIGINAL_PRE_UNKNOWN",
                       "SOURCE_IF_ABSENT","SOURCE_APL_ONLY"),
             "SOURCE_NATIVE_IF_CLASS_UNRECOGNIZED")
        native=row.get("native_IF_post_comparator_only")
        counts[state]+=1
        ref={
            "original_selected_call_id":row["original_selected_call_id"],
            "original_dispatch_token":row["original_dispatch_token"],
            "original_simc_ms":row["original_simc_time_ms"],
            "source_list":name,"source_rank_zero_based":index,
            "source_row_sha256":key["source_line_sha256"],
            "source_action_from_original_row":row["source_action"],
        }
        if condition is None:
            must(state=="SOURCE_IF_ABSENT" and
                 native=="NOT_REACHED",
                 "SOURCE_ABSENT_IF_IMPUTED")
            continue
        ast=condition.get("source_ast")
        expr=condition.get("raw_expression")
        required=condition.get("symbols")
        must(type(ast) is list and type(expr) is str and
             type(required) is list and
             sorted(ast_symbols(ast))==required,
             "PINNED_AST_SYMBOL_CONTRACT_DRIFT")
        now=truth(evaluate_ast(ast,facts))
        if state=="IF_ORIGINAL_PRE_MATCH":
            must(now is True and native=="TRUE" and
                 stage.get("independent_condition") is True and
                 stage.get("source_guard_result")=="TRUE",
                 "SELECTED_SOURCE_IF_REPLAY_CONFLICT")
            witness=sufficient_partial_source_witness(
                expr,facts,expected=True)
            must(witness["source_IF_result"] is True,
                 "MINIMAL_WITNESS_NOT_SOURCE_TRUE")
            obs=set(required)&set(facts)
            total_source_symbols+=len(required)
            total_observed+=len(obs)
            total_needed+=len(witness["minimal_sufficient_PRE_facts"])
            minimal_records.append({
                **ref,
                "condition_source":expr,
                "all_source_operands":required,
                "observed_source_operands":sorted(obs),
                "source_IF_minimal_sufficient_PRE":witness[
                    "minimal_sufficient_PRE_facts"],
                "source_IF_unobserved_but_not_needed_for_this_occurrence":
                    witness["unobserved_source_operand_names"],
                "IF_true_native_comparator_independently_correlated":True,
                "full_READY":"UNKNOWN",
                "simultaneous_alternatives_READY":"UNKNOWN",
            })
        elif state=="IF_ORIGINAL_PRE_UNKNOWN":
            must(now is None and
                 stage.get("source_guard_result")=="UNKNOWN" and
                 stage.get("independent_condition") is None,
                 "UNKNOWN_SOURCE_IF_NOT_REPRODUCED")
            absent=sorted(set(required)-set(facts))
            missing.update(absent)
            if row["original_simc_time_ms"]<10000:
                missing_early.update(absent)
            unknown_records.append({
                **ref,"source_if":expr,
                "source_if_state":"UNKNOWN",
                "unobserved_source_operand_upper_bound_not_all_necessary":absent,
                "missing_is_not_a_proven_ready_or_priority_gate":True,
            })
        else:
            must(state=="SOURCE_APL_ONLY" and
                 now in (True,False) and native=="NOT_REACHED",
                 "NO_COMPARATOR_SOURCE_IF_CANNOT_BE_CERTIFIED")
    must(counts["IF_ORIGINAL_PRE_MATCH"]==
         source.get("independently_verified_source_IF_true") and
         counts["IF_ORIGINAL_PRE_UNKNOWN"]==
         source.get("source_IF_unknown") and
         counts["SOURCE_IF_ABSENT"]==source.get("source_APL_if_absent") and
         counts["SOURCE_APL_ONLY"]==
         source.get("source_IF_native_comparator_absent_but_AST_known"),
         "SOURCE_IF_CLASS_COUNTS_NOT_CONSERVED")
    return {
        "spec_key":source["source_spec"],"class_key":source["class_key"],
        "target_count":source["target_count"],
        "profile_git_blob_sha1":graph["source_git_blob"],
        "selected_original_source_occurrences":len(proofs),
        "source_IF_status_counts":dict(sorted(counts.items())),
        "source_IF_confirmed_true_minimal_records":minimal_records,
        "source_IF_unconfirmed_missing_PRE_records":unknown_records,
        "missing_symbol_occurrence_counts_NOT_actual_priority":
            dict(sorted(missing.items(),key=lambda x:(-x[1],x[0]))),
        "missing_first_10sec_symbol_counts_NOT_opener_end":
            dict(sorted(missing_early.items(),key=lambda x:(-x[1],x[0]))),
        "observed_source_IF_operand_instances_for_true_rows":total_observed,
        "minimally_necessary_observed_operand_instances_for_true_rows":
            total_needed,
        "total_source_symbol_instances_in_true_expressions":
            total_source_symbols,
        "all_full_physical_READY":"UNKNOWN",
        "causal_competing_priority":"UNKNOWN",
        "source_selection_is_not_actual_player_cast":True,
    }


def audit_pinned_archive(archive_path:Path,manifest_path:Path)->dict:
    manifest=json.loads(manifest_path.read_bytes())
    must(type(manifest) is dict and
         manifest.get("schema")==MANIFEST and
         manifest.get("source_commit")==
         "b522cded8c26b97dac03fdf56e57a03ec7e8faa6" and
         type(manifest.get("case_files")) is list and
         len(manifest["case_files"])>=2 and
         type(manifest.get("portfolio")) is dict,
         "PINNED_ORIGINAL_SOURCE_MANIFEST_INVALID")
    entries=[manifest["portfolio"]]+manifest["case_files"]
    paths=[e["path"] for e in entries]
    must(len(set(paths))==len(paths) and
         all(type(e) is dict and
             type(e.get("path")) is str and
             re.fullmatch(r"[a-z0-9_.-]+\.json",e["path"]) and
             type(e.get("sha256")) is str and
             HEX64.fullmatch(e["sha256"]) is not None
             for e in entries),
         "UNSAFE_OR_UNPINNED_ORIGINAL_SOURCE_MEMBERS")
    with zipfile.ZipFile(archive_path) as z:
        infos=z.infolist()
        must(len(infos)==len(paths) and
             set(x.filename for x in infos)==set(paths) and
             all(x.file_size<=2_000_000 and
                 x.compress_size<=2_000_000 for x in infos),
             "ORIGINAL_NATIVE_RECEIPT_ZIP_UNEXPECTED_FILES")
        docs={}
        for entry in entries:
            b=z.read(entry["path"])
            must(sha256(b).hexdigest()==entry["sha256"],
                 "ORIGINAL_NATIVE_SOURCE_CASE_SHA256_MISMATCH")
            docs[entry["path"]]=json.loads(b)
    portfolio=docs[manifest["portfolio"]["path"]]
    must(portfolio.get("schema")==SOURCE_PORTFOLIO and
         portfolio.get("policy_id")==POLICY and
         portfolio.get("source_ready_closed") is False and
         portfolio.get("full_positive_ready_proven")==0 and
         portfolio.get("MAIN_promoted") is False and
         portfolio.get("opener_end")=="UNKNOWN" and
         len(portfolio.get("source_cases",[]))==len(manifest["case_files"]),
         "ORIGINAL_PORTFOLIO_LIMITS_INVALID")
    cases=[]
    used=set()
    for entry in manifest["case_files"]:
        spec=entry.get("spec_key")
        count=entry.get("target_count")
        blob=entry.get("source_profile_blob")
        must(type(spec) is str and type(count) is int and
             1<=count<=40 and (spec,count) not in used and
             type(blob) is str and HEX40.fullmatch(blob) is not None,
             "DUPLICATE_OR_INVALID_SOURCE_CASE_MANIFEST")
        used.add((spec,count))
        definition={**entry,"source_commit":manifest["source_commit"]}
        case=docs[entry["path"]]
        proof=audit_case(case,definition)
        must(any(p.get("source_spec")==spec and
                 p.get("target_count")==count and
                 p.get("source_git_blob")==blob and
                 p.get("source_case_report_sha256")==
                     case.get("source_case_report_sha256")
                 for p in portfolio["source_cases"]),
             "ORIGINAL_PORTFOLIO_CASE_ATTRIBUTION_MISMATCH")
        cases.append(proof)
    totals=Counter()
    for c in cases:
        totals["selected"]+=c["selected_original_source_occurrences"]
        totals["IF_true"]+=len(c["source_IF_confirmed_true_minimal_records"])
        totals["IF_unknown"]+=len(c["source_IF_unconfirmed_missing_PRE_records"])
        totals["IF_absent"]+=c["source_IF_status_counts"].get("SOURCE_IF_ABSENT",0)
        totals["IF_no_comparator"]+=c["source_IF_status_counts"].get("SOURCE_APL_ONLY",0)
        totals["observed_operand_instances"]+=c[
            "observed_source_IF_operand_instances_for_true_rows"]
        totals["minimal_operand_instances"]+=c[
            "minimally_necessary_observed_operand_instances_for_true_rows"]
    must(totals["selected"]==portfolio.get("selected_samples_total") and
         totals["IF_true"]==portfolio.get("independent_original_source_IF_true_total") and
         totals["IF_unknown"]==portfolio.get("source_IF_UNKNOWN_total") and
         totals["IF_absent"]==portfolio.get("no_explicit_source_IF_total"),
         "ORIGINAL_SOURCE_PORTFOLIO_RECONCILIATION_FAILED")
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "source_commit":manifest["source_commit"],
        "source_case_count":len(cases),
        "original_source_member_sha256":{e["path"]:e["sha256"] for e in entries},
        "original_source_selected_occurrences":totals["selected"],
        "independently_verified_source_IF_true":totals["IF_true"],
        "source_IF_unknown":totals["IF_unknown"],
        "source_if_absent":totals["IF_absent"],
        "original_observed_operand_instances_in_verified_true_IF":
            totals["observed_operand_instances"],
        "inclusion_minimal_operand_instances_for_verified_true_IF":
            totals["minimal_operand_instances"],
        "observed_operand_instances_provably_unneeded_for_these_IF":
            totals["observed_operand_instances"]-totals["minimal_operand_instances"],
        "case_research_witnesses":cases,
        "opener_end":"UNKNOWN",
        "independent_complete_action_READY":0,
        "selected_action_optimality":"UNKNOWN",
        "WCL_blind_candidate_lock":"NOT_RUN",
        "WCL_API_calls":0,"new_SimC_CXX_builds":0,
        "dummy_wrong_cast":"UNKNOWN","MAIN_promoted":False,
    }


def selftest()->dict:
    from simc_apl_semantic_ir_v2 import Expression,ast_symbols
    source="a|b"
    expr={"raw_expression":source,"source_ast":Expression(source).parse(),
          "symbols":sorted(ast_symbols(Expression(source).parse()))}
    origin={"identity":{"source_list":"default","source_index":0,
                        "source_line":1,"source_line_sha256":"a"*64},
            "action":"invented_skill","behavior":"ACTION",
            "kind":"EXECUTABLE_SOURCE_CANDIDATE",
            "conditions":{"if":expr}}
    item={
        "observed_source_target_count":3,
        "original_selected_call_id":11,"original_dispatch_token":21,
        "original_simc_time_ms":900,
        "source_identity":origin["identity"],
        "source_action":origin["action"],
        "source_behavior":"ACTION",
        "source_kind":"EXECUTABLE_SOURCE_CANDIDATE",
        "source_if_AST":expr,
        "original_PRE_symbol_values":{"a":1},
        "bounded_condition":{"classification":"IF_ORIGINAL_PRE_MATCH",
                             "independent_condition":True,
                             "source_guard_result":"TRUE"},
        "native_IF_post_comparator_only":"TRUE",
        "source_ready_proof":{"decision":"UNKNOWN"},
        "source_order_frontier":{"decision":"UNKNOWN"},
        "actual_spell_execution_completion":"UNKNOWN",
        "real_WoW_expected_action":"UNKNOWN","dummy_wrong_cast":"UNKNOWN"}
    fake={"schema":SOURCE_CASE,"policy_id":POLICY,
          "source_spec":"newclass_spec","class_key":"newclass",
          "target_count":3,"source_commit":"c"*40,
          "source_full_READY_proven":0,"competitor_ready_proven":0,
          "source_order_priority_proven":0,"opener_end":"UNKNOWN",
          "dummy_wrong_skill":"UNKNOWN","MAIN_promoted":False,
          "source_hypothesis_IR":{
            "source_git_blob":"b"*40,"spec_key":"newclass_spec",
            "class_key":"newclass",
            "source_only_priority_graph":{"lists":{"default":[origin]}}},
          "exact_selected_occurrence_proofs":[item],
          "original_selected_source_rows":1,
          "independently_verified_source_IF_true":1,
          "source_IF_unknown":0,"source_APL_if_absent":0,
          "source_IF_native_comparator_absent_but_AST_known":0}
    definition={"spec_key":"newclass_spec","target_count":3,
                "source_commit":"c"*40,"source_profile_blob":"b"*40,
                "expected_original_rows":1}
    compiled=audit_case(fake,definition)
    assert len(compiled["source_IF_confirmed_true_minimal_records"])==1
    first=compiled["source_IF_confirmed_true_minimal_records"][0]
    assert first["source_IF_minimal_sufficient_PRE"]=={"a":1}
    assert first["source_IF_unobserved_but_not_needed_for_this_occurrence"]==["b"]
    import copy
    bad=0
    for alter in (
        lambda x:x["exact_selected_occurrence_proofs"][0]["bounded_condition"].update(
            source_guard_result="FALSE"),
        lambda x:x["exact_selected_occurrence_proofs"][0]["native_IF_post_comparator_only"].__class__,
        lambda x:x["exact_selected_occurrence_proofs"][0]["source_ready_proof"].update(
            decision="READY"),
        lambda x:x["exact_selected_occurrence_proofs"][0]["original_PRE_symbol_values"].update(
            a=0),
        lambda x:x["source_hypothesis_IR"]["source_only_priority_graph"]["lists"]["default"][0]["identity"].update(
            source_line_sha256="0"*64),
    ):
        obj=copy.deepcopy(fake)
        if bad==1:obj["exact_selected_occurrence_proofs"][0]["native_IF_post_comparator_only"]="FALSE"
        else:alter(obj)
        try:audit_case(obj,definition)
        except FrontierError:bad+=1
        else:raise AssertionError("FORGED_SOURCE_IF_EVIDENCE_ACCEPTED")
    assert bad==5
    return {"status":"PASS_OFFLINE_SYNTHETIC",
            "synthetic_new_class_source_witness":1,
            "fail_closed_mutations":bad,
            "source_FULL_READY_proven":0,
            "WCL_API_calls":0}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifact-zip",type=Path)
    ap.add_argument("--manifest",type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if not args.artifact_zip and not args.manifest:
        result=selftest()
    else:
        if not args.artifact_zip or not args.manifest:
            ap.error("--artifact-zip and --manifest required together")
        result=audit_pinned_archive(args.artifact_zip,args.manifest)
    raw=canonical(result)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes(raw)
        print(json.dumps({"status":"WRITTEN",
                          "sha256":sha256(raw).hexdigest(),
                          "bytes":len(raw)}))
    else:
        print(raw.decode(),end="")


if __name__=="__main__":
    main()
