#!/usr/bin/env python3
"""Generic SimC-first conditional General Rotation *research* E2E.

Input: immutable SimC APL/profile -> existing typed AST and existing
source-hypothesis IR -> optional exact-root original Native SimC selection
receipts. Output: a fully ordered source IF/ELSE priority *hypothesis*,
precombat source plan, and source-grounded 30s selected-action references.

No class/spec/spell mechanics in Generic; source selection ≠ player casts.
CALL and RUN preserve their distinct source control-flow meanings. No
optimistic READY, WCL blind semantic injection, user practice verdict, or
guessed opener-termination transition.

Without arguments, safe zero-network synthetic self-test for PyCharm.
With --source-root and --manifest, produce source-only model; with
--evidence-dir and --trace-manifest, additionally reconcile actual original
SimC selection evidence for each scenario. Deterministic JSON bytes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from hashlib import sha256
import json
import re
from pathlib import Path
import subprocess
from typing import Any

from simc_apl_semantic_ir_v2 import canonical, git_blob
from general_rotation_simc_multi_spec_cold_start_v1 import load_manifest
from general_rotation_source_hypothesis_ir_v1 import compile_profile
from general_rotation_full_root_state_join_v1 import SCHEMA as NATIVE_SCHEMA

SCHEMA="ZrotGenericSimCSourceToConditionalPriorityOpenerResearchE2EV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
TRACE_MANIFEST_SCHEMA="ZrotOriginalNativeSourceRootTraceInputManifestV1"
CASE_NAME_RE=re.compile(r"[a-z0-9][a-z0-9_]{0,31}\Z")
HEX64=set("0123456789abcdef")
DEFAULT_OPENER_SAMPLE_MS=10000

class GenericRotationE2EError(ValueError):
    pass

def require(ok:bool,reason:str)->None:
    if not ok:raise GenericRotationE2EError(reason)

def _case_manifest(obj:dict,source_specs:set[str])->dict[str,list[dict]]:
    require(isinstance(obj,dict) and
            obj.get("schema")==TRACE_MANIFEST_SCHEMA and
            isinstance(obj.get("profiles"),list),
            "EXPLICIT_NATIVE_TRACE_MANIFEST_REQUIRED")
    cases={}
    for entry in obj["profiles"]:
        require(isinstance(entry,dict) and
                set(entry)=={"spec_key","cases"} and
                isinstance(entry["spec_key"],str) and
                entry["spec_key"] in source_specs and
                entry["spec_key"] not in cases and
                isinstance(entry["cases"],list) and entry["cases"],
                "DUPLICATE_OR_FOREIGN_NATIVE_TRACE_SPEC")
        seen=set()
        result=[]
        for case in entry["cases"]:
            require(isinstance(case,dict) and
                    set(case)=={"name","target_count","file","sha256"} and
                    isinstance(case["name"],str) and
                    CASE_NAME_RE.fullmatch(case["name"]) is not None and
                    type(case["target_count"]) is int and
                    1<=case["target_count"]<=40 and
                    case["name"] not in seen and
                    isinstance(case["sha256"],str) and
                    len(case["sha256"])==64 and
                    all(v in HEX64 for v in case["sha256"]),
                    "INVALID_TARGET_COUNT_OR_UNPINNED_SOURCE_TRACE")
            rel=Path(case["file"])
            require(not rel.is_absolute() and len(rel.parts)==1 and
                    rel.suffix==".json" and ".." not in rel.parts,
                    "NATIVE_EVIDENCE_PATH_TRAVERSAL_OR_NON_JSON")
            seen.add(case["name"])
            result.append(case)
        cases[entry["spec_key"]]=result
    require(set(cases)==source_specs,
            "NOT_ALL_SOURCE_SPECS_HAVE_DECLARED_NATIVE_EVIDENCE")
    return cases

def _source_program(model:dict)->dict:
    graph=model["source_only_priority_graph"]
    require(isinstance(graph,dict) and
            isinstance(graph.get("lists"),dict) and
            isinstance(graph.get("list_order"),list) and
            "default" in graph["lists"],
            "SOURCE_HYPOTHESIS_PRIORITY_GRAPH_MISSING")
    lists={}
    count=0
    missing_operands=set()
    for name in graph["list_order"]:
        require(name in graph["lists"],
                "SOURCE_PRIORITY_LIST_ORDER_NOT_RECONCILED")
        output=[]
        for rank,source in enumerate(graph["lists"][name],1):
            identity=source["identity"]
            require(identity["source_index"]==rank-1 and
                    identity["source_list"]==name and
                    source["source_priority_ordinal"]==rank-1 and
                    source["expected_ready"]=="UNKNOWN",
                    "SOURCE_PRIORITY_IDENTITY_OR_READY_IMPUTED")
            src=source["conditions"].get("if")
            raw_expr=src["raw_expression"] if src else None
            attrs=source["conditions"]
            operand_map={field:entry["symbols"]
                         for field,entry in attrs.items()}
            missing_operands.update(sum(operand_map.values(),[]))
            control=source["behavior"]
            require(control in ("ACTION","CALL","RUN","VARIABLE",
                                "SWAP_UNSUPPORTED",
                                "SIDE_EFFECT_SOURCE_MODEL_UNVERIFIED"),
                    "NEW_SOURCE_BEHAVIOR_UNSUPPORTED")
            call=source["control_destination"]
            if control in ("CALL","RUN"):
                require(isinstance(call,str) and call in graph["lists"],
                        "UNRESOLVED_ACTION_LIST_DESTINATION")
            if control=="RUN":
                transfer="QUEUE_RUN_CONTROL_THEN_NEXT_SELECTION_IN_DESTINATION"
            elif control=="CALL":
                transfer="CALL_CHILD_LIST_AND_RESUME_IF_NO_ACTION"
            elif control=="VARIABLE":
                transfer="SOURCE_VARIABLE_STATE_WRITE_NOT_A_CAST"
            elif control=="SWAP_UNSUPPORTED":
                transfer="UNKNOWN_UNSUPPORTED_SWAP"
            else:
                transfer="TRY_SOURCE_ACTION_IF_AND_READY_THEN_ELSE_NEXT"
            output.append({
                "source_list":name,
                "priority_rank_in_list":rank,
                "identity":identity,
                "action":source["action"],
                "behavior":control,
                "when_source_if":raw_expr,
                "condition_AST":src["source_ast"] if src else None,
                "condition_operands":operand_map,
                "other_source_attributes_are_not_ignored":
                    sorted(k for k in attrs if k!="if"),
                "candidate_source_contexts":source[
                    "context_hints_not_mechanic_truth"],
                "target_count_comparisons_not_verified_breakpoints":source[
                    "literal_target_count_comparisons_not_verified_breakpoints"],
                "source_control_destination":call,
                "on_guard_true_and_native_ready":transfer,
                "on_guard_false":"CONTINUE_NEXT_SOURCE_ROW",
                "on_guard_UNKNOWN":"DO_NOT_SELECT_OR_ASSUME_ELSE",
                "independent_native_FULL_READY":"UNKNOWN",
                "priority_is_local_to_source_list":True,
                "is_actual_WoW_player_spellcast":"UNKNOWN",
            })
            count+=1
        lists[name]=output
    require(count==model["coverage"]["source_action_rows"],
            "SOURCE_PRIORITY_ROW_LOSS")
    return {
        "schema":"ZrotSourceOrderedConditionalPriorityProgramV1",
        "entry_action_list":"default",
        "precombat_source_actions":lists.get("precombat",[]),
        "conditional_action_lists":lists,
        "source_list_call_graph":graph["edges"],
        "source_variable_definition_sites":graph["source_variable_sites"],
        "unresolved_source_state_operand_names":sorted(missing_operands),
        "run_list_is_NOT_synchronous_child_selection":True,
        "source_row_is_NOT_unconditional_cast":True,
        "priority_when_multiple_ready_is_source_order_only":True,
        "proven_optimality":False,
        "source_row_total":count,
    }

def _reconcile_original_native(original:dict,model:dict,case:dict,
                               *,opener_window_ms:int)->dict:
    require(original.get("schema")==NATIVE_SCHEMA and
            original.get("product_policy_id")==POLICY and
            original.get("source_profile_git_blob_sha1")==
              model["source_git_blob"] and
            original.get("target_count")==case["target_count"] and
            original.get("source_root_states_physically_before_native_READY") is True and
            original.get("complete_independent_full_READY_proven")==0 and
            original.get("gameplay_feedback_permitted") is False and
            original.get("WCL_candidate_holdout_proven") is False,
            "ORIGINAL_NATIVE_TRACE_PROVENANCE_AND_TARGET_MISMATCH")
    rows=original.get("source_selected_rows")
    need=original.get("all_returned_leaf_same_root_PRE_reconciled")
    require(isinstance(rows,list) and len(rows)>0 and
            len(rows)==need==original.get("all_original_source_returned_rows"),
            "ACTUAL_CPP_SOURCE_SELECTED_ROOT_COHORT_INCOMPLETE")
    actual=[]
    counts=Counter()
    conditions=Counter()
    missing=Counter()
    last_ms=-1
    roots=set()
    for i,record in enumerate(rows,1):
        owner=record.get("source_list")
        ordinal=record.get("source_ordinal")
        t=record.get("at_simc_ms")
        require(owner in model["source_only_priority_graph"]["lists"] and
                type(ordinal) is int and ordinal>0 and
                ordinal<=len(model["source_only_priority_graph"]["lists"][owner]) and
                type(t) is int and t>=0 and t>=last_ms and
                record.get("choice_index")==i and
                record.get("original_native_source_return_observed") is True and
                record.get("independent_full_READY_proven") is False and
                record.get("is_actual_player_spellcast_proven") is False and
                record.get("is_optimal_General_Rotation_rule") is False,
                "SOURCE_RETURN_NOT_ORIGINAL_SIMC_OR_ACTION_ORDER_DRIFT")
        last_ms=t
        rank=model["source_only_priority_graph"]["lists"][owner][ordinal-1]
        row_identity=rank["identity"]
        root=record.get("selected_CPP_ready_root_id")
        require(record.get("source_row_sha256")==
                    row_identity["source_line_sha256"] and
                record.get("action")==rank["action"] and
                type(root) is int and root>0 and root not in roots and
                record.get("original_CPP_before_READY_PRE",{}).get(
                    "exact_root_id_proven") is True and
                record["original_CPP_before_READY_PRE"].get(
                    "active_enemies")==case["target_count"] and
                record["original_CPP_before_READY_PRE"].get(
                    "not_WCL_STRICT_PRE") is True,
                "SOURCE_ROW_HASH_CPP_ROOT_OR_STRICT_PRE_MISMATCH")
        roots.add(root)
        reason=record.get("source_apl_IF",{})
        expr=rank["conditions"].get("if")
        require(reason.get("source_expression")==
                (expr["raw_expression"] if expr else None) and
                reason.get("independently_replayed_truth") in (True,False,None) and
                reason.get("original_native_POST_boolean_not_used_as_AST_fact") is True and
                record.get("prior_original_native_false_count",0)>=0,
                "ORIGINAL_SOURCE_IF_AT_SELECTED_ROOT_NOT_IDENTICAL")
        verdict=reason.get("result")
        require(verdict in ("NO_EXPLICIT_APL_IF",
                            "UNKNOWN_ADDITIONAL_APL_SYMBOLS",
                            "INDEPENDENT_SAME_ROOT_SOURCE_IF_TRUE",
                            "INDEPENDENT_SAME_ROOT_SOURCE_IF_FALSE"),
                "ORIGINAL_SOURCE_IF_EVIDENCE_CLASS_DRIFT")
        require(not (verdict.endswith("_TRUE") and
                     reason["independently_replayed_truth"] is not True),
                "FALSE_SOURCE_IF_PROMOTED_TO_TRUE")
        counts[rank["behavior"]]+=1
        conditions[verdict]+=1
        for symbol in reason.get("missing_explicit_symbols",[]):
            missing[symbol]+=1
        actual.append({
            "original_CPP_choice_index":i,
            "at_simc_ms":t,
            "target_count":case["target_count"],
            "source_list":owner,
            "source_priority_rank":ordinal,
            "source_line_sha256":row_identity["source_line_sha256"],
            "source_line":row_identity["source_line"],
            "action":rank["action"],
            "source_behavior":rank["behavior"],
            "selected_original_CPP_READY_root_id":root,
            "original_select_call_path_ids":record.get(
                "original_CPP_source_select_path"),
            "original_CPP_same_root_PRE":record["original_CPP_before_READY_PRE"],
            "source_IF_status":verdict,
            "source_IF_unobserved_operands":reason.get(
                "missing_explicit_symbols",[]),
            "native_original_return_selected":True,
            "native_return_NOT_independent_FULL_READY":True,
            "is_performed_player_cast":False,
            "is_user_rotation_recommendation":False,
            "dummy_user_error_verdict":"UNKNOWN",
        })
    return {
        "schema":"ZrotOriginalNativeSourceReturnOpenerReferenceV1",
        "case":case["name"],
        "source_profile_key":model["spec_key"],
        "target_count":case["target_count"],
        "original_CPP_source_returned_actions_all":len(actual),
        "reference_duration_ms_last_choice":last_ms,
        "research_sample_window_ms_NOT_opener_end":opener_window_ms,
        "opener_window_original_CPP_returns":[
            item for item in actual if item["at_simc_ms"]<=opener_window_ms],
        "all_original_CPP_source_return_actions":actual,
        "native_source_behavior_counts":dict(sorted(counts.items())),
        "source_IF_evidence_counts":dict(sorted(conditions.items())),
        "missing_source_IF_operand_frequency":dict(sorted(missing.items(),
                                         key=lambda v:(-v[1],v[0]))),
        "actual_WoW_cast_sequence":"UNKNOWN",
        "opener_termination_rule":"UNKNOWN",
        "independently_complete_FULL_READY_proven":0,
        "WCL_holdout_result":"NOT_RUN",
        "practical_dummy_error_feedback_permitted":False,
    }

def compile_spec(raw:bytes,metadata:dict,case_inputs:list[tuple[dict,dict]]|None,
                 *,opener_window_ms:int=DEFAULT_OPENER_SAMPLE_MS)->dict:
    require(type(opener_window_ms) is int and opener_window_ms>=0,
            "OPENER_RESEARCH_WINDOW_INVALID")
    model=compile_profile(raw,metadata)
    require(model.get("schema")=="ZrotGeneralRotationSourceHypothesisIRV1" and
            model.get("policy")==POLICY and
            model["source_git_blob"]==git_blob(raw),
            "EXISTING_GENERIC_APL_PARSER_MODEL_NOT_SOURCE_IDENTICAL")
    program=_source_program(model)
    contexts={}
    for case,actual in (case_inputs or []):
        require(case["name"] not in contexts,
                "DUPLICATE_TARGET_CASE_NATIVE_TRACE")
        contexts[case["name"]]=_reconcile_original_native(
            actual,model,case,opener_window_ms=opener_window_ms)
    return {
        "schema":"ZrotOneSpecSimCConditionalRotationResearchProgramV1",
        "product_policy_id":POLICY,
        "source_spec_key":model["spec_key"],
        "source_class_key":model["class_key"],
        "source_profile_git_blob_sha1":model["source_git_blob"],
        "source_profile_sha256":model["profile_sha256"],
        "source_APL_row_count":model["coverage"]["source_action_rows"],
        "conditioned_opener_and_priority":{
            "precombat_source_order":program["precombat_source_actions"],
            "main_source_action_list":"default",
            "all_ordered_source_IF_ELSE_lists":program[
                "conditional_action_lists"],
            "source_list_call_graph":program["source_list_call_graph"],
            "source_variable_sites":program[
                "source_variable_definition_sites"],
            "target_count_source_comparisons_not_actual_breakpoints":
                {listname:[
                    cmp for row in rows
                    for cmp in row[
                      "target_count_comparisons_not_verified_breakpoints"]]
                 for listname,rows in program[
                    "conditional_action_lists"].items()},
            "no_flattening_of_RUN_or_CALL":True,
            "source_program_complete_for_given_profile":True,
        },
        "unresolved_source_state_operand_names":program[
            "unresolved_source_state_operand_names"],
        "simc_native_observed_source_selection_cases":contexts,
        "observed_simc_source_return_case_count":len(contexts),
        "opener_first_actual_player_cast":"UNKNOWN",
        "simultaneously_available_physical_priority_proven":False,
        "conditional_source_APL_is_not_optimal_rotation":True,
        "WCL_independent_blind_candidate_lock":"NOT_RUN",
        "WCL_independent_holdout":"NOT_RUN",
        "Blizzard_live_addon_state_exposure":"NOT_TESTED",
        "user_target_dummy_error_verdict":"UNKNOWN",
        "MAIN_promoted":False,
    }

def run(source_root:Path,manifest_path:Path,
        *,evidence_dir:Path|None=None,trace_manifest:Path|None=None,
        opener_window_ms:int=DEFAULT_OPENER_SAMPLE_MS)->dict:
    require((evidence_dir is None)==(trace_manifest is None),
            "NATIVE_EVIDENCE_DIR_AND_TRACE_MANIFEST_REQUIRED_TOGETHER")
    manifest=load_manifest(manifest_path)
    root=source_root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
            check=True,capture_output=True,text=True).stdout.strip()
    require(rev==manifest["official_simc_commit"],
            "PINNED_OFFICIAL_SIMC_REVISION_CHANGED")
    mapping={}
    if evidence_dir is not None:
        mapping=_case_manifest(json.loads(trace_manifest.read_bytes()),
                               {m["key"] for m in manifest["profiles"]})
        evidence_dir=evidence_dir.resolve(strict=True)
    models=[]
    for meta in manifest["profiles"]:
        rel=Path(meta["profile"])
        path=(root/rel).resolve(strict=True)
        require(path.is_relative_to(root),
                "SIMC_PROFILE_REALPATH_OUTSIDE_OFFICIAL_SOURCE")
        raw=path.read_bytes()
        require(git_blob(raw)==meta["git_blob"],
                "PINNED_OFFICIAL_PROFILE_BLOB_DRIFT")
        data=[]
        for case in mapping.get(meta["key"],[]):
            p=(evidence_dir/case["file"]).resolve(strict=True)
            require(p.is_relative_to(evidence_dir),
                    "EVIDENCE_REALPATH_OUTSIDE_READONLY_DIR")
            buf=p.read_bytes()
            require(sha256(buf).hexdigest()==case["sha256"],
                    "EXACT_CPP_NATIVE_RECEIPT_SHA256_DRIFT")
            data.append((case,json.loads(buf)))
        models.append(compile_spec(raw,meta,data,
                     opener_window_ms=opener_window_ms))
    require(len({m["source_class_key"] for m in models})>=2,
            "TWO_DISTINCT_CLASSES_REQUIRED_GENERIC_E2E")
    return {
        "schema":SCHEMA,
        "product_policy_id":POLICY,
        "official_simc_commit":rev,
        "models":models,
        "distinct_class_count":len({m["source_class_key"] for m in models}),
        "source_APL_rows_compiled":sum(m["source_APL_row_count"] for m in models),
        "original_cpp_selected_source_actions_bound":sum(
            x["original_CPP_source_returned_actions_all"] for m in models
            for x in m["simc_native_observed_source_selection_cases"].values()),
        "native_reference_cases":sum(
            len(m["simc_native_observed_source_selection_cases"]) for m in models),
        "source_to_conditional_graph_E2E_complete_for_pinned_profiles":True,
        "full_dynamic_ready_state_and_global_optimality":"UNKNOWN",
        "real_player_opener_canonically_verified":False,
        "WCL_blind_candidate_semantics_injected":False,
        "WCL_holdout_completed":False,
        "WoW_live_addon_tested":False,
        "trainer_mistake_verdict":"UNKNOWN",
        "WCL_API_calls":0,
        "MAIN_promoted":False,
    }

def selftest()->dict:
    # Two independent specs are tested in CI using official pinned profiles
    # and four authentic original C++ source-choice receipts.
    raw=(
      b"actions.precombat=variable,name=z,op=set,value=2\n"
      b"actions.precombat+=/spell_alpha\n"
      b"actions=call_action_list,name=sub,if=active_enemies>=2\n"
      b"actions+=/filler,if=rage>=30\n"
      b"actions.sub=alpha,if=buff.x.up\n"
      b"actions.sub+=/beta\n"
    )
    from simc_apl_semantic_ir_v2 import parse_profile
    from general_rotation_source_hypothesis_ir_v1 import compile_profile
    meta={"key":"probe","class_key":"dummy","git_blob":git_blob(raw)}
    model=compile_profile(raw,meta)
    prog=_source_program(model)
    assert prog["source_row_total"]==6
    assert prog["conditional_action_lists"]["default"][0][
        "on_guard_true_and_native_ready"]=="CALL_CHILD_LIST_AND_RESUME_IF_NO_ACTION"
    assert prog["conditional_action_lists"]["default"][1][
        "on_guard_UNKNOWN"]=="DO_NOT_SELECT_OR_ASSUME_ELSE"
    spec=compile_spec(raw,meta,None)
    assert spec["observed_simc_source_return_case_count"]==0
    assert spec["opener_first_actual_player_cast"]=="UNKNOWN"
    # Forbid bogus binding of an unrelated source, even if an action has the
    # same name: the row SHA + ordinal + list + true exact root must match.
    sample={
      "schema":NATIVE_SCHEMA,"product_policy_id":POLICY,
      "source_profile_git_blob_sha1":meta["git_blob"],
      "target_count":1,
      "source_root_states_physically_before_native_READY":True,
      "complete_independent_full_READY_proven":0,
      "gameplay_feedback_permitted":False,
      "WCL_candidate_holdout_proven":False,
      "all_returned_leaf_same_root_PRE_reconciled":1,
      "all_original_source_returned_rows":1,
      "source_selected_rows":[{
        "choice_index":1,"source_list":"default","source_ordinal":2,
        "source_row_sha256":model["source_only_priority_graph"]["lists"][
            "default"][1]["identity"]["source_line_sha256"],
        "action":"filler","at_simc_ms":0,
        "selected_CPP_ready_root_id":9,
        "original_native_source_return_observed":True,
        "independent_full_READY_proven":False,
        "is_actual_player_spellcast_proven":False,
        "is_optimal_General_Rotation_rule":False,
        "original_CPP_source_select_path":[1],
        "original_CPP_before_READY_PRE":{
          "exact_root_id_proven":True,"active_enemies":1,
          "not_WCL_STRICT_PRE":True,"mana_pct":None},
        "source_apl_IF":{
          "source_expression":"rage>=30",
          "independently_replayed_truth":None,
          "result":"UNKNOWN_ADDITIONAL_APL_SYMBOLS",
          "missing_explicit_symbols":["rage"],
          "original_native_POST_boolean_not_used_as_AST_fact":True},
        "prior_original_native_false_count":0
      }]
    }
    case={"name":"st","target_count":1,"file":"x.json","sha256":"a"*64}
    linked=_reconcile_original_native(sample,model,case,opener_window_ms=10000)
    assert linked["original_CPP_source_returned_actions_all"]==1
    assert linked["source_IF_evidence_counts"]=={
        "UNKNOWN_ADDITIONAL_APL_SYMBOLS":1}
    for field,value in (
      ("source_row_sha256","f"*64),
      ("selected_CPP_ready_root_id",0),
      ("is_actual_player_spellcast_proven",True),
      ("at_simc_ms",-1),
    ):
        bad=copy.deepcopy(sample)
        bad["source_selected_rows"][0][field]=value
        try:_reconcile_original_native(bad,model,case,opener_window_ms=10000)
        except GenericRotationE2EError:pass
        else:raise AssertionError("FORGED_CPP_SOURCE_ROW_ACCEPTED:"+field)
    for wrong in (
       {"schema":TRACE_MANIFEST_SCHEMA,"profiles":[]},
       {"schema":TRACE_MANIFEST_SCHEMA,"profiles":[{
         "spec_key":"probe","cases":[{"name":"2t","target_count":0,
           "file":"a.json","sha256":"b"*64}]}]},
    ):
        try:_case_manifest(wrong,{"probe"})
        except GenericRotationE2EError:pass
        else:raise AssertionError("UNPINNED_NATIVE_TRACE_MANIFEST_ACCEPTED")
    return {
       "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
       "checks":13,
       "generic_source_profiles":True,
       "native_cpp_rebuilt":False,
       "WCL_API_calls":0,
       "no_FULL_READY_promoted":True,
    }

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root",type=Path)
    parser.add_argument("--manifest",type=Path)
    parser.add_argument("--evidence-dir",type=Path)
    parser.add_argument("--trace-manifest",type=Path)
    parser.add_argument("--opener-sample-window-ms",type=int,
                        default=DEFAULT_OPENER_SAMPLE_MS)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if args.source_root is None and args.manifest is None and \
       args.evidence_dir is None and args.trace_manifest is None:
        out=selftest()
    elif args.source_root is not None and args.manifest is not None:
        out=run(args.source_root,args.manifest,
             evidence_dir=args.evidence_dir,
             trace_manifest=args.trace_manifest,
             opener_window_ms=args.opener_sample_window_ms)
    else:
        parser.error("pinned official source and manifest required, or no args for synthetic")
    data=canonical(out)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes(data)
        print("GENERIC_SIMC_RESEARCH_E2E_SHA256="+sha256(data).hexdigest())
        print("GENERIC_SIMC_RESEARCH_E2E_OUTPUT="+str(args.out))
    else:
        import sys
        sys.stdout.buffer.write(data)

if __name__=="__main__":
    main()
