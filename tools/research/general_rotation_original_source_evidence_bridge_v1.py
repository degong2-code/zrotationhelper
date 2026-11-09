#!/usr/bin/env python3
"""Generic source-evidence -> General Rotation hypothesis/decision IR compiler.

Reuses the source-wide APL graph, exact same-call SimC PRE IF observations,
and open-world decision proof engine. Never promotes a selected action into
READY or an expected player cast. Every observation remains occurrence-scoped
and replayable through the original source AST, not aggregated into a rule.

No specialization-specific action rules. No arguments: synthetic selftest.
Production mode: explicitly pinned native four-case replay JSON, adapter and
original official source profiles. No WCL calls or new SimC C++ build.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from general_rotation_source_hypothesis_ir_v1 import (
    compile_profile, POLICY, SCHEMA as SOURCE_SCHEMA
)
from general_rotation_original_select_extra_pre_replay_v1 import (
    SCHEMA as NATIVE_SCHEMA, MATCH, NO_NATIVE, UNKNOWN as IF_UNKNOWN, NO_IF
)
from general_rotation_decision_proof_engine_v1 import (
    Identity, Fact, GateContract, decide_candidate, evaluate_priority, UNKNOWN
)
from simc_apl_semantic_ir_v2 import (
    canonical, evaluate_ast, truth, git_blob
)

SCHEMA="ZrotGeneralRotationOriginalSelectedSourceEvidenceHypothesisBridgeV1"
BATCH_SCHEMA="ZrotGeneralRotationOriginalSourceConditionalHypothesisPortfolioV1"
PINNED_RECEIPT_SCHEMA="ZrotGenericOriginalSourceSelectPREFieldExpansionReceiptV1"
SOURCE_REVISION="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
SHA64=re.compile(r"^[a-f0-9]{64}$")
BRANCH_SAFE=("SOURCE_APL_ONLY","IF_ORIGINAL_PRE_MATCH","IF_ORIGINAL_PRE_UNKNOWN",
             "SOURCE_IF_ABSENT")
_ALLOWED=(MATCH,NO_NATIVE,IF_UNKNOWN,NO_IF)


class BridgeError(ValueError):
    pass


def require(condition:bool, why:str)->None:
    if not condition:
        raise BridgeError(why)


def digest(data:bytes)->str:
    return sha256(data).hexdigest()


def load_json(path:Path)->tuple[dict,bytes]:
    require(path.is_file() and not path.is_symlink(),
            "EXPLICIT_NON_SYMLINKED_JSON_REQUIRED")
    data=path.read_bytes()
    require(0<len(data)<12_000_000, "SOURCE_JSON_SIZE_OR_EMPTY")
    def no_duplicates(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,"DUPLICATE_JSON_KEY")
            result[key]=value
        return result
    obj=json.loads(data,object_pairs_hook=no_duplicates)
    require(type(obj)==dict,"JSON_OBJECT_REQUIRED")
    return obj,data


def _source_class(profile:bytes)->str|None:
    rows=re.findall(r'(?m)^([a-z][a-z0-9_]*)="[^"\n]*"\s*$',
                    profile.decode("utf-8"))
    return rows[0] if len(rows)==1 else None


def _facts(fields:dict,allowed:set[str])->dict[str,float]:
    require(type(fields)==dict and set(fields)<=allowed,
            "UNDECLARED_OR_CROSS_CLASS_ORIGINAL_PRE_FIELD")
    converted={}
    for name,value in fields.items():
        require(type(value) in (int,float) and math.isfinite(float(value)),
                "ORIGINAL_PRE_FIELD_NONFINITE_OR_NONNUMERIC")
        converted[name]=float(value)
    return converted


def _native_state(row:dict)->str:
    require(row.get("original_native_IF_comparator") in
            ("TRUE","FALSE","NOT_REACHED"),"INVALID_NATIVE_IF_COMPARATOR")
    return row["original_native_IF_comparator"]


def _stage_guard(source:dict,row:dict,facts:dict,receipt_sha:str)->dict:
    condition=source["conditions"].get("if")
    witness=row["original_SOURCE_IF_evidence"]
    require(witness in _ALLOWED,"UNDECLARED_SOURCE_IF_EVIDENCE_KIND")
    native=_native_state(row)
    require(type(row.get("original_source_IF_independent_truth"))==str and
            row["original_source_IF_independent_truth"] in
            ("TRUE","FALSE","UNKNOWN"),"SOURCE_IF_TRUTH_ENUM_INVALID")
    if condition is None:
        require(witness==NO_IF and
                row["original_source_IF_independent_truth"]=="UNKNOWN" and
                native=="NOT_REACHED" and
                row.get("source_IF_required_symbols")==[] and
                row.get("unobserved_symbols")==[],
                "SOURCE_ROW_NO_IF_FORGED_AS_INDEPENDENT_TRUE")
        return {"classification":"SOURCE_IF_ABSENT",
                "source_guard_result":"SOURCE_TAUTOLOGY_NOT_PHYSICAL_READY",
                "independent_condition":None}
    require(row.get("source_IF_required_symbols")==condition["symbols"] and
            row.get("unobserved_symbols")==
              sorted(set(condition["symbols"])-set(facts)),
            "SOURCE_IF_REQUIRED_OR_MISSING_FIELDS_CHANGED")
    evaluated=truth(evaluate_ast(condition["source_ast"],facts))
    claimed=("UNKNOWN" if evaluated is None else
             ("TRUE" if evaluated else "FALSE"))
    require(claimed==row["original_source_IF_independent_truth"],
            "CLAIMED_SOURCE_IF_NOT_REPRODUCED_FROM_ORIGINAL_PRE")
    if evaluated is None:
        require(witness==IF_UNKNOWN,"MISSING_SOURCE_FACT_PROMOTED_TO_VERIFIED")
        return {"classification":"IF_ORIGINAL_PRE_UNKNOWN",
                "source_guard_result":"UNKNOWN",
                "independent_condition":None}
    if native=="NOT_REACHED":
        require(witness==NO_NATIVE,
                "NO_NATIVE_COMPARATOR_CANNOT_BE_SAME_CALL_MATCH")
        return {"classification":"SOURCE_APL_ONLY",
                "source_guard_result":claimed,
                "independent_condition":None}
    require(witness==MATCH and (native=="TRUE")==evaluated,
            "SOURCE_IF_NATIVE_COMPARATOR_DISAGREES")
    # Selected physical action cannot be justified with a false source IF.
    require(evaluated is True,"SELECTED_ACTION_WITH_FALSE_SOURCE_IF_CONTRADICTION")
    return {"classification":"IF_ORIGINAL_PRE_MATCH",
            "source_guard_result":"TRUE",
            "independent_condition":True}


def compile_case(profile:bytes,report:dict,adapter:dict,
                 *,case_receipt_sha256:str)->dict:
    """Compile a reusable APL source graph + exact occurrence evidence view."""
    require(SHA64.fullmatch(case_receipt_sha256) is not None,
            "PINNED_ACTUAL_CASE_REPORT_SHA256_REQUIRED")
    require(report.get("schema")==NATIVE_SCHEMA and
            report.get("policy_id")==POLICY and
            report.get("original_SimC_source_revision")==SOURCE_REVISION and
            report.get("source_if_comparator_not_replay_input") is True and
            report.get("source_if_not_full_physical_READY") is True and
            report.get("full_physical_READY_proven")==0 and
            report.get("competitor_ready_proven")==0 and
            report.get("actual_spell_execution_complete")=="UNKNOWN" and
            report.get("opener_end")=="UNKNOWN" and
            report.get("WCL_blind_holdout")=="NOT_RUN" and
            report.get("dummy_wrong_cast")=="UNKNOWN" and
            report.get("MAIN_promoted") is False,
            "NATIVE_SOURCE_EVIDENCE_PROOF_BOUNDARY_INVALID")
    require(adapter.get("policy_id")==POLICY and
            adapter.get("source_revision")==SOURCE_REVISION and
            report.get("source_adapter_sha256")==digest(canonical(adapter)),
            "NATIVE_SOURCE_ADAPTER_FINGERPRINT_CHANGED")
    class_key=_source_class(profile)
    require(class_key is not None and class_key==report.get("source_class"),
            "SOURCE_PROFILE_ACTOR_CLASS_DRIFT")
    matching=[x for x in adapter.get("profiles",[]) if
              x.get("actor_class")==class_key]
    require(len(matching)==1 and
            matching[0].get("profile_git_blob")==git_blob(profile) and
            report.get("original_profile_blob")==git_blob(profile),
            "ORIGINAL_SOURCE_PROFILE_IDENTITY_CHANGED")
    require(type(report.get("targets")) is int and
            1<=report["targets"]<=40 and
            type(report.get("source_spec")) is str and
            bool(report["source_spec"]),
            "ACTUAL_SOURCE_CASE_SCOPE_INVALID")
    declared={f["symbol"] for f in adapter.get("fields",[])
              if f.get("owner_class")==class_key}
    require(bool(declared) and len(declared)==len([
        f for f in adapter["fields"] if f.get("owner_class")==class_key
    ]),"DUPLICATE_CLASS_SOURCE_FIELD")
    graph=compile_profile(profile,{
        "key":report["source_spec"],"class_key":class_key,
        "git_blob":git_blob(profile)
    })
    require(graph["schema"]==SOURCE_SCHEMA and
            graph["source_git_blob"]==report["original_profile_blob"] and
            graph["evidence_status"]["complete_positive_READY_proven"] is False,
            "ORIGINAL_APL_SOURCE_HYPOTHESIS_COMPILER_DRIFT")
    raw_rows=report.get("selected_source_IF_samples")
    require(type(raw_rows)==list and
            len(raw_rows)==report.get("original_selected_direct_foreground") and
            report.get("native_if_comparator_count")>=0 and
            report.get("native_if_comparator_count")<=len(raw_rows),
            "ORIGINAL_SELECTED_SOURCE_SAMPLE_COVERAGE_DRIFT")
    used_tokens=set();used_callids=set();proofs=[];counts=Counter()
    by_row=defaultdict(lambda:Counter())
    source_lists=graph["source_only_priority_graph"]["lists"]
    for original in raw_rows:
        name=original.get("source_list")
        rank=original.get("source_rank")
        require(name in source_lists and type(rank) is int and
                1<=rank<=len(source_lists[name]),
                "EVIDENCE_APL_LIST_OR_RANK_NOT_IN_SOURCE")
        node=source_lists[name][rank-1]
        require(original.get("source_row_sha256")==node["identity"]["source_line_sha256"] and
                original.get("source_action")==node["action"],
                "SELECTED_SOURCE_EVIDENCE_ROW_HASH_OR_ACTION_CHANGED")
        t=original.get("t_ms");token=original.get("original_dispatch_token")
        call=original.get("original_selected_call_id")
        require(all(type(n) is int and n>=0 for n in (t,token,call)) and
                token>0 and call>0 and
                token not in used_tokens and call not in used_callids,
                "SELECTED_SOURCE_EXACT_OCCURRENCE_ID_NOT_UNIQUE")
        used_tokens.add(token);used_callids.add(call)
        require(original.get("original_physical_READY")=="UNKNOWN" and
                original.get("competitor_priority")=="UNKNOWN" and
                original.get("dummy_error")=="UNKNOWN",
                "OBSERVED_SELECTION_FALSIFIED_AS_GAMEPLAY_PROOF")
        facts=_facts(original.get("original_PRE_fields"),declared)
        stage=_stage_guard(node,original,facts,case_receipt_sha256)
        ident=Identity(
            scope=f"{report['source_spec']}:{report['targets']}:{name}",
            source_sha256=node["identity"]["source_line_sha256"],
            t_ms=t,ordinal=rank-1,occurrence=call
        )
        # Exact selected-source IF is a necessary condition only. All
        # non-IF Native virtual readiness/spec/cooldown gates are still open.
        gate=GateContract("ORIGINAL_SIMC_SOURCE_APL",
                          ("source_if","other_physical_ready_gates"),
                          node["identity"]["source_line_sha256"],
                          closed=False)
        verified=[]
        if stage["independent_condition"] is True:
            verified.append(Fact(
                ident,"source_if",True,"INDEPENDENT_SOURCE_REPLAY",
                "SIMC_ORIGINAL_METHOD_PRE",t,
                case_receipt_sha256))
        proof=decide_candidate(
            ident,gate,verified,node["kind"]=="EXECUTABLE_SOURCE_CANDIDATE")
        require(proof["decision"]==UNKNOWN and
                proof["positive_route_closed"] is False and
                proof["dummy_error_permitted"] is False,
                "SOURCE_IF_BRIDGE_ILLEGALLY_PROMOTED_ACTION_READY")
        # Reuse the existing proof frontier; a selected row alone is never
        # evidence that all earlier eligible rows were NOT_READY.
        frontier=evaluate_priority([proof],0,source_order_complete=False,
                                   native_selected_name=node["action"])
        require(frontier["decision"]==UNKNOWN and
                not frontier["source_order_complete"],
                "SELECTED_ACTION_PROMOTED_TO_COMPLETE_SOURCE_PRIORITY")
        counts[stage["classification"]]+=1
        by_row[(name,rank)] [stage["classification"]]+=1
        proofs.append({
            "original_simc_time_ms":t,
            "observed_source_target_count":report["targets"],
            "original_dispatch_token":token,
            "original_selected_call_id":call,
            "source_identity":node["identity"],
            "source_action":node["action"],
            "source_kind":node["kind"],
            "source_behavior":node["behavior"],
            "source_if_AST":node["conditions"].get("if"),
            "original_PRE_symbol_values":facts,
            "native_IF_post_comparator_only":_native_state(original),
            "bounded_condition":stage,
            "source_ready_proof":proof,
            "source_order_frontier":frontier,
            "actual_spell_execution_completion":"UNKNOWN",
            "real_WoW_expected_action":"UNKNOWN",
            "dummy_wrong_cast":"UNKNOWN"
        })
    require(sum(counts.values())==len(raw_rows) and
            len(raw_rows)==report["original_selected_direct_foreground"],
            "SOURCE_DECISION_OCCURRENCES_NOT_CONSERVED")
    require(counts["IF_ORIGINAL_PRE_MATCH"]==
            report["source_independent_IF_triage"].get(MATCH,0) and
            counts["SOURCE_IF_ABSENT"]==
            report["source_independent_IF_triage"].get(NO_IF,0) and
            counts["IF_ORIGINAL_PRE_UNKNOWN"]==
            report["source_independent_IF_triage"].get(IF_UNKNOWN,0) and
            counts["SOURCE_APL_ONLY"]==
            report["source_independent_IF_triage"].get(NO_NATIVE,0),
            "SOURCE_IF_TRIAGE_AGGREGATE_NOT_REPRODUCIBLE")
    nonforeground=report.get("nonforeground_combat_emitter_rows")
    require(type(nonforeground)==list,"NONFOREGROUND_ALTERNATIVE_ROUTE_INVENTORY_REQUIRED")
    # Never reinterpret source off-GCD metadata as an observed native route.
    for x in nonforeground:
        require(x.get("missing_route")=="UNKNOWN" and
                x.get("real_WoW_action")=="UNKNOWN",
                "NONFOREGROUND_NATIVE_ROUTE_FORGED")
    rows=[]
    for (name,rank),classifications in sorted(by_row.items()):
        node=source_lists[name][rank-1]
        rows.append({
            "source_identity":node["identity"],
            "source_action":node["action"],
            "source_if":node["conditions"].get("if"),
            "observed_selected_occurrences":sum(classifications.values()),
            "per_occurrence_IF_status_counts":dict(sorted(classifications.items())),
            "persistent_IF_rule_truth":"UNKNOWN",
            "positive_READY_rule":"UNKNOWN",
            "source_priority_rule":"UNKNOWN",
            "dummy_feedback_rule":"UNKNOWN"
        })
    opener_sample=[{
        "t_ms":x["original_simc_time_ms"],
        "source_identity":x["source_identity"],
        "action_name_from_source":x["source_action"],
        "if_witness":x["bounded_condition"]["classification"],
        "actual_CAST_proven":False,
        "source_priority_proven":False
    } for x in proofs if x["original_simc_time_ms"]<10000]
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "source_commit":SOURCE_REVISION,
        "source_case_report_sha256":case_receipt_sha256,
        "source_spec":report["source_spec"],
        "class_key":class_key,"target_count":report["targets"],
        "source_hypothesis_IR":graph,
        "exact_selected_occurrence_proofs":proofs,
        "source_row_occurrence_index":rows,
        "first_10s_bounded_selection_examples_not_opener_end":opener_sample,
        "original_selected_source_rows":len(proofs),
        "independently_verified_source_IF_true":counts["IF_ORIGINAL_PRE_MATCH"],
        "source_APL_if_absent":counts["SOURCE_IF_ABSENT"],
        "source_IF_unknown":counts["IF_ORIGINAL_PRE_UNKNOWN"],
        "source_IF_native_comparator_absent_but_AST_known":counts["SOURCE_APL_ONLY"],
        "selected_condition_status_counts":dict(sorted(counts.items())),
        "other_original_combat_paths_UNRESOLVED":nonforeground,
        "source_full_READY_proven":0,
        "competitor_ready_proven":0,
        "source_order_priority_proven":0,
        "native_selected_used_as_positive_ready_input":False,
        "WCL_independent_candidate_lock":"NOT_RUN",
        "WCL_independent_holdout":"NOT_RUN",
        "dummy_wrong_skill":"UNKNOWN",
        "opener_end":"UNKNOWN",
        "MAIN_promoted":False,
    }


def compile_portfolio(cases:list[dict])->dict:
    require(type(cases)==list and bool(cases),
            "NO_SOURCE_CASES_FOR_GENERIC_PORTFOLIO")
    kinds=set();totals=Counter();across=defaultdict(dict)
    for case in cases:
        require(case["schema"]==SCHEMA and
                case["source_full_READY_proven"]==0 and
                case["source_order_priority_proven"]==0 and
                case["WCL_independent_holdout"]=="NOT_RUN",
                "SOURCE_CASE_NOT_SAFE_FOR_CONDITIONAL_PORTFOLIO")
        key=(case["source_spec"],case["target_count"])
        require(key not in kinds,"DUPLICATE_SOURCE_SPEC_TARGET_CASE")
        kinds.add(key)
        totals["selected"]+=case["original_selected_source_rows"]
        totals["verified_IF"]+=case["independently_verified_source_IF_true"]
        totals["IF_unknown"]+=case["source_IF_unknown"]
        totals["IF_absent"]+=case["source_APL_if_absent"]
        totals["nonforeground"]+=len(case["other_original_combat_paths_UNRESOLVED"])
        for row in case["source_row_occurrence_index"]:
            ident=row["source_identity"]
            cross=(case["source_hypothesis_IR"]["source_git_blob"],
                   ident["source_list"],ident["source_index"])
            across[cross][case["target_count"]]={
                "selected_count":row["observed_selected_occurrences"],
                "verified_IF_count":row["per_occurrence_IF_status_counts"].get(
                    "IF_ORIGINAL_PRE_MATCH",0),
                "IF_unknown_count":row["per_occurrence_IF_status_counts"].get(
                    "IF_ORIGINAL_PRE_UNKNOWN",0)}
    # These are source-sample observations by target count, not switching
    # thresholds; multiple observed cases must not be pooled into priority.
    comparison=[{
        "source_profile_git_blob":key[0],
        "source_list":key[1],"source_index_zero_based":key[2],
        "per_target_observed_selection_counts":{
            str(n):v for n,v in sorted(value.items())},
        "observed_target_switch_threshold":"UNKNOWN",
        "simultaneously_ready_alternatives":"UNKNOWN"
    } for key,value in sorted(across.items())]
    return {
        "schema":BATCH_SCHEMA,"policy_id":POLICY,
        "source_cases":[{
            "source_spec":c["source_spec"],
            "class_key":c["class_key"],
            "target_count":c["target_count"],
            "source_git_blob":c["source_hypothesis_IR"]["source_git_blob"],
            "source_case_report_sha256":c["source_case_report_sha256"],
            "source_compiled_model_status":"SOURCE_HYPOTHESIS_WITH_EXACT_IF_PROOFS"
        } for c in cases],
        "selected_samples_total":totals["selected"],
        "independent_original_source_IF_true_total":totals["verified_IF"],
        "source_IF_UNKNOWN_total":totals["IF_unknown"],
        "no_explicit_source_IF_total":totals["IF_absent"],
        "unresolved_nonforeground_combat_total":totals["nonforeground"],
        "target_condition_observation_index":comparison,
        "runtime_expected_action":"UNKNOWN",
        "source_ready_closed":False,
        "opener_end":"UNKNOWN",
        "WCL_blind_candidate_lock":"NOT_RUN",
        "WCL_independent_holdout":"NOT_RUN",
        "dummy_wrong_cast":"UNKNOWN",
        "source_apl_models_reused":True,
        "full_positive_ready_proven":0,
        "WCL_API_calls":0,
        "new_SimC_CXX_builds":0,"MAIN_promoted":False
    }


def dummy_feedback_preview(occurrence:dict)->dict:
    """Downstream API: safe training feedback without claiming expected cast."""
    require(occurrence["source_ready_proof"]["decision"]==UNKNOWN and
            occurrence["source_order_frontier"]["decision"]==UNKNOWN and
            occurrence["real_WoW_expected_action"]=="UNKNOWN",
            "DUMMY_ERROR_GATE_BYPASSED")
    return {
        "actual_player_action":"UNKNOWN",
        "observed_simc_source_action":occurrence["source_action"],
        "expected_player_action":"UNKNOWN",
        "can_declare_wrong_rotation":False,
        "reason":"SOURCE_IF_ONLY_NO_COMPLETE_READY_OR_WCL_HOLDOUT",
        "source_if_evidence":occurrence["bounded_condition"]["classification"],
    }


def selftest()->dict:
    # Two independent classes with original APL guards, no spell hardcoding.
    from simc_apl_semantic_ir_v2 import git_blob
    from general_rotation_original_select_extra_pre_replay_v1 import SCHEMA as N
    warrior=(b'warrior="Synthetic"\nspec=fury\n'
             b'actions.precombat=snapshot_stats\n'
             b'actions=alpha,if=rage>=50\n'
             b'actions+=/beta\n'
             b'actions+=/gamma,if=buff.proc.react>0\n')
    mage=(b'mage="Synthetic"\nspec=arcane\n'
          b'actions.precombat=snapshot_stats\n'
          b'actions=delta,if=active_enemies>=2\n'
          b'actions+=/epsilon\n')
    adapter={
        "policy_id":POLICY,"source_revision":SOURCE_REVISION,
        "profiles":[
            {"actor_class":"warrior","profile_git_blob":git_blob(warrior)},
            {"actor_class":"mage","profile_git_blob":git_blob(mage)}
        ],
        "fields":[
            {"owner_class":"warrior","symbol":"rage"},
            {"owner_class":"mage","symbol":"active_enemies"}]
    }
    def build_report(source,spec,cls,targets,observations):
        graph=compile_profile(source,{
            "key":spec,"class_key":cls,"git_blob":git_blob(source)})
        rows=[]
        for i,(name,idx,facts,claim,native) in enumerate(observations):
            n=graph["source_only_priority_graph"]["lists"][name][idx]
            expr=n["conditions"].get("if")
            v=None if expr is None else truth(
                evaluate_ast(expr["source_ast"],facts))
            rows.append({
                "source_list":name,"source_rank":idx+1,
                "source_row_sha256":n["identity"]["source_line_sha256"],
                "source_action":n["action"],"t_ms":101+i*110,
                "original_dispatch_token":i+1,
                "original_selected_call_id":i+101,
                "original_PRE_fields":facts,
                "original_SOURCE_IF_evidence":claim,
                "original_source_IF_independent_truth":
                    "UNKNOWN" if v is None else ("TRUE" if v else "FALSE"),
                "original_native_IF_comparator":native,
                "source_IF_required_symbols":expr["symbols"] if expr else [],
                "unobserved_symbols":sorted(set(expr["symbols"])-set(facts))
                  if expr else [],
                "original_physical_READY":"UNKNOWN",
                "competitor_priority":"UNKNOWN",
                "dummy_error":"UNKNOWN"
            })
        return {
            "schema":N,"policy_id":POLICY,
            "original_SimC_source_revision":SOURCE_REVISION,
            "source_if_comparator_not_replay_input":True,
            "source_if_not_full_physical_READY":True,
            "source_adapter_sha256":digest(canonical(adapter)),
            "original_profile_blob":git_blob(source),
            "source_spec":spec,"source_class":cls,"targets":targets,
            "selected_source_IF_samples":rows,
            "original_selected_direct_foreground":len(rows),
            "native_if_comparator_count":sum(r["original_native_IF_comparator"]
                   !="NOT_REACHED" for r in rows),
            "source_independent_IF_triage":dict(Counter(
                r["original_SOURCE_IF_evidence"] for r in rows)),
            "nonforeground_combat_emitter_rows":[],
            "full_physical_READY_proven":0,"competitor_ready_proven":0,
            "actual_spell_execution_complete":"UNKNOWN",
            "opener_end":"UNKNOWN","WCL_blind_holdout":"NOT_RUN",
            "dummy_wrong_cast":"UNKNOWN","MAIN_promoted":False,
        }
    a=build_report(warrior,"warrior_fury","warrior",1,[
        ("default",0,{"rage":60},MATCH,"TRUE"),
        ("default",1,{},NO_IF,"NOT_REACHED"),
        ("default",2,{},IF_UNKNOWN,"NOT_REACHED")
    ])
    b=build_report(mage,"mage_arcane","mage",2,[
        ("default",0,{"active_enemies":2},MATCH,"TRUE"),
        ("default",1,{},NO_IF,"NOT_REACHED")
    ])
    x=compile_case(warrior,a,adapter,case_receipt_sha256="a"*64)
    y=compile_case(mage,b,adapter,case_receipt_sha256="b"*64)
    portfolio=compile_portfolio([x,y])
    require(x["independently_verified_source_IF_true"]==1 and
            x["source_IF_unknown"]==1 and
            x["source_APL_if_absent"]==1 and
            y["independently_verified_source_IF_true"]==1 and
            portfolio["selected_samples_total"]==5 and
            portfolio["independent_original_source_IF_true_total"]==2,
            "SYNTHETIC_TWO_CLASS_HYPOTHESIS_BRIDGE_FAILED")
    require(not dummy_feedback_preview(x["exact_selected_occurrence_proofs"][0])
            ["can_declare_wrong_rotation"],
            "SYNTHETIC_DUMMY_SAFETY_BYPASS")
    require(canonical(x)==canonical(compile_case(
        warrior,a,adapter,case_receipt_sha256="a"*64)),
        "NONDETERMINISTIC_GENERIC_COMPILATION")
    import copy
    wrong=[]
    def mutate(report,transform):
        changed=copy.deepcopy(report)
        transform(changed)
        try:compile_case(warrior,changed,adapter,
                         case_receipt_sha256="a"*64)
        except (BridgeError,ValueError):wrong.append(1)
        else:raise AssertionError("FORGED_SOURCE_PROOF_ACCEPTED")
    mutate(a,lambda r:r["selected_source_IF_samples"][0].update(
        source_row_sha256="f"*64))
    mutate(a,lambda r:r["selected_source_IF_samples"][0].update(
        original_source_IF_independent_truth="FALSE"))
    mutate(a,lambda r:r["selected_source_IF_samples"][0].update(
        original_PRE_fields={"rage":10}))
    mutate(a,lambda r:r["selected_source_IF_samples"][0].update(
        original_native_IF_comparator="FALSE"))
    mutate(a,lambda r:r["selected_source_IF_samples"][0].update(
        original_physical_READY="READY"))
    mutate(a,lambda r:r["selected_source_IF_samples"][1].update(
        original_selected_call_id=101))
    mutate(a,lambda r:r["selected_source_IF_samples"][0].update(
        original_PRE_fields={"active_enemies":2}))
    mutate(a,lambda r:r.update(WCL_blind_holdout="PASS"))
    mutate(a,lambda r:r["selected_source_IF_samples"][2].update(
        original_SOURCE_IF_evidence=MATCH))
    require(len(wrong)==9,"NEGATIVE_SOURCE_PROVENANCE_REGRESSION_NOT_RUN")
    return {
        "schema":SCHEMA,"status":"PASS_SYNTHETIC_TWO_CLASS_GENERIC_IR",
        "generic_classes_exercised":2,
        "distinct_targets_exercised":2,
        "exact_synthetic_selected_occurrences":5,
        "independent_source_if_matches":2,
        "negative_controls":len(wrong),
        "source_priority_rules_promoted":0,
        "positive_READY_promoted":0,
        "dummy_wrong_cast_promoted":0,
        "WCL_API_calls":0,"new_SimC_CXX_builds":0
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root",type=Path)
    parser.add_argument("--reports-root",type=Path)
    parser.add_argument("--adapter",type=Path)
    parser.add_argument("--verified-receipt",type=Path)
    parser.add_argument("--out-root",type=Path)
    args=parser.parse_args()
    if all(v is None for v in vars(args).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    require(all(v is not None for v in vars(args).values()),
            "EXPLICIT_SOURCE_PROVENANCE_INPUTS_REQUIRED")
    receipt,_=load_json(args.verified_receipt)
    require(receipt.get("schema")==PINNED_RECEIPT_SCHEMA and
            receipt.get("policy_id")==POLICY and
            receipt.get("official_simc_source_revision")==SOURCE_REVISION and
            receipt.get("actual_validation",{}).get("run_id")==42589894203 and
            receipt.get("actual_validation",{}).get("conclusion")=="success" and
            receipt.get("actual_validation",{}).get("original_unchanged_combat_action_order_time_ID_ordinal")=="149/149" and
            receipt.get("actual_validation",{}).get("original_APL_foreground_select_to_JSON2_causal_callsite")=="147/147" and
            receipt.get("scientific_claim_limits",{}).get("original_full_physical_READY_proven")==0,
            "PRIOR_PINNED_NATIVE_EVIDENCE_NOT_VERIFIED")
    adapter,_=load_json(args.adapter)
    require(adapter.get("source_revision")==SOURCE_REVISION and
            adapter.get("policy_id")==POLICY and
            len(adapter.get("fields",[]))==
              receipt["new_capture"]["field_count"],
            "SOURCE_ADAPTER_PLAN_FIELDS_DRIFT")
    reports=[];case_docs=[];source_profiles={}
    for c in receipt["actual_validation"]["per_case"]:
        key=c["spec"]+"-"+("st" if c["targets"]==1 else
                           str(c["targets"])+"t")
        expected=c["report_sha256"]
        path=args.reports_root/key/"exact-selected-extra-pre-if.json"
        native,raw=load_json(path)
        require(digest(raw)==expected,"PINNED_REAL_CASE_REPORT_HASH_MISMATCH")
        matches=[p for p in adapter.get("profiles",[]) if
                 p.get("actor_class")==native.get("source_class")]
        require(len(matches)==1,"NATIVE_SPEC_PROFILE_CLASS_NOT_BOUND")
        meta=matches[0]
        profpath=(args.source_root/meta["path"]).resolve(strict=True)
        root=args.source_root.resolve(strict=True)
        require(profpath.is_relative_to(root),
                "ORIGINAL_PROFILE_ESCAPED_SOURCE_ROOT")
        prof=profpath.read_bytes()
        require(git_blob(prof)==meta["profile_git_blob"],
                "OFFICIAL_PINNED_PROFILE_BLOB_CHANGED")
        out=compile_case(prof,native,adapter,
                         case_receipt_sha256=expected)
        require(out["source_spec"]==c["spec"] and
                out["target_count"]==c["targets"] and
                out["independently_verified_source_IF_true"]==
                c["source_IF_match"] and
                out["source_IF_unknown"]==c["unknown_PRE"] and
                out["source_APL_if_absent"]==c["no_explicit_IF"],
                "REAL_NATIVE_SOURCE_CASE_COMPILE_CHANGED")
        reports.append(out)
        case_docs.append((key,out))
    portfolio=compile_portfolio(reports)
    v=receipt["actual_validation"]
    require(portfolio["selected_samples_total"]==147 and
            portfolio["independent_original_source_IF_true_total"]==49 and
            portfolio["source_IF_UNKNOWN_total"]==44 and
            portfolio["no_explicit_source_IF_total"]==54 and
            portfolio["unresolved_nonforeground_combat_total"]==2 and
            v["selected_source_IF_independent_match"]==49 and
            v["missing_valid_original_PRE_for_source_IF"]==44,
            "PINNED_ORIGINAL_49_OF_147_SOURCE_IF_PORTFOLIO_DRIFT")
    args.out_root.mkdir(parents=True,exist_ok=True)
    results=[]
    for key,obj in case_docs:
        output=args.out_root/(key+"-source-hypothesis-evidence.json")
        require(not output.exists(),"OUTPUT_ALREADY_EXISTS_NO_REPLACE")
        with output.open("xb") as handle:handle.write(canonical(obj))
        results.append((key,digest(output.read_bytes())))
        print("GENERIC_SOURCE_HYPOTHESIS_CASE_SHA256_"+key+"="+results[-1][1])
    output=args.out_root/"generic-general-rotation-source-conditional-portfolio.json"
    require(not output.exists(),"OUTPUT_ALREADY_EXISTS_NO_REPLACE")
    with output.open("xb") as handle:handle.write(canonical(portfolio))
    print("GENERIC_SOURCE_HYPOTHESIS_PORTFOLIO_SHA256="+digest(output.read_bytes()))
    print("GENERIC_SOURCE_HYPOTHESIS_PROOF_COUNTS="+json.dumps({
      "selected":portfolio["selected_samples_total"],
      "source_if_true":portfolio["independent_original_source_IF_true_total"],
      "source_if_unknown":portfolio["source_IF_UNKNOWN_total"],
      "no_explicit_if":portfolio["no_explicit_source_IF_total"],
      "physical_ready":portfolio["full_positive_ready_proven"]},sort_keys=True))


if __name__=="__main__":
    main()
