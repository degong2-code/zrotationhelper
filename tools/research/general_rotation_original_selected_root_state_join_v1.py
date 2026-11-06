#!/usr/bin/env python3
"""Original SimC selected-leaf provenance + exact source actor PRE state.

No new parser or simulated gameplay mechanics. Reuses:
- the integrated Hekili-informed opener output (Scripts + Core research view);
- an already validated original Native C++ source sweep/return artifact;
- the exact original ready-root actor PRE bounded records;
- the existing AST and evidence-gated Candidate Proof engine.

Root ID and selected source row must both match. A child-propagated selection
is resolved from the full nested select-sweep tree, not from timestamp-only
or a same-action-name collision. NO original log data is generated/downloaded.

Default no CLI args: synthetic self-test. In research mode use retained Native
artifact, integrated JSON and a separate source-pinned SpecAdapter obligation
record. All unproven full positive READY and effects stay UNKNOWN.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import zipfile

from simc_apl_semantic_ir_v2 import Expression, evaluate_ast, truth, ast_symbols
from general_rotation_decision_proof_engine_v1 import (
    Identity, Fact, GateContract, decide_candidate,
)
from general_rotation_source_decision_reason_ledger_v1 import (
    CASES, POLICY, SELECTED as SELECTED_SCHEMA, TEMPORAL as TIME_SCHEMA,
)
from general_rotation_integrated_opener_research_v1 import (
    SCHEMA as INTEGRATED_SCHEMA,
)
from general_rotation_root_actor_pre_replay_v1 import (
    SCHEMA as PRE_SCHEMA,
)

SCHEMA="ZrotOriginalSelectedLeafExactRootStateSnapshotV1"
ADAPTER_SCHEMA="ZrotSpecAdapterSourceMechanicObligationsV1"
ORIGINAL_ARTIFACT_SHA256="b347132dd935d4b9c5a9b5aea7357cda588deed92f222d418c6407eb3235b901"
HEX64=re.compile(r"[0-9a-f]{64}\Z")
HEX40=re.compile(r"[0-9a-f]{40}\Z")
# Actual inner JSON bytes pinned independently of ZIP container metadata.
# Allows CI to reuse GitHub's downloaded artifact directory (same original
# content) without mistakenly claiming a repacked ZIP has the same digest.
SOURCE_MEMBER_SHA256={
"zrot-native-source-selected-return-fury-st.json":"a967cbe904e1819d9543c4b58adf425823bbd75a6d068217bc6ece26d72c2bdb",
"zrot-native-source-selected-return-fury-2t.json":"20eb2f4a396323effbae630d2c4c0106b8cc2993fa4c1502ac370e97c0b6e65c",
"zrot-native-source-selected-return-arcane-st.json":"2b8c0cd49e9082e82b984924e1c034e7f6878f9fd6f2cad511b3058e2fbd3998",
"zrot-native-source-selected-return-arcane-2t.json":"ef0501246ced05edc4e45c01f39cf3cb40e35a30402db9b89ea74b17227a62ca",
"zrot-original-root-actor-pre-fury-st.json":"737cd621e984ea12af1f6e767d077898e24d2128d5b6667ef2a5e298969e9924",
"zrot-original-root-actor-pre-fury-2t.json":"9509b93e266a41f59f678e766904fba50a6373433d3b7c449e5511a7cd71baef",
"zrot-original-root-actor-pre-arcane-st.json":"657838aa81e02d14ad6b64e21b39e15e5cda342b80d3efc167d7681a7bcef33a",
"zrot-original-root-actor-pre-arcane-2t.json":"fcdd710143bd4c35adf077220f8d4d014830edbaef2da59b735a362e2e4d40fa",
"zrot-source-temporal-frontier-fury-st.json":"75d64af753a24fff07e2aacd6c9716c1dc39e892efa214503d624c97fb180f4f",
"zrot-source-temporal-frontier-fury-2t.json":"291ac4fd804f7652446a5c04eff98de9d20919928315f39d2c121601d914cbf9",
"zrot-source-temporal-frontier-arcane-st.json":"1b8e60e3e32fe987df7d1322fda571520c20dccda586edc093a273e6e6803032",
"zrot-source-temporal-frontier-arcane-2t.json":"e3691f55a9a1fcea2b4abd6cbfb89fb778fb622e714df064875affd53692a5c6",
}

class ExactLeafSourceError(ValueError):
    pass

def check(ok:bool,label:str)->None:
    if not ok:raise ExactLeafSourceError(label)

def _load(source:zipfile.ZipFile|Path, member:str)->dict:
    check(member in SOURCE_MEMBER_SHA256,"UNPINNED_CPP_RECEIPT_MEMBER")
    if isinstance(source,Path):
        file=source/member
        check(file.is_file(),"MISSING_ORIGINAL_CPP_RECEIPT_"+member)
        raw=file.read_bytes()
    else:
        check(member in source.namelist(),"MISSING_ORIGINAL_CPP_RECEIPT_"+member)
        raw=source.read(member)
    check(sha256(raw).hexdigest()==SOURCE_MEMBER_SHA256[member],
          "ORIGINAL_NATIVE_MEMBER_BYTES_NOT_PINNED_"+member)
    return json.loads(raw)

def _unique_leaf(sweeps:dict[int,dict], children:dict[int,list[int]],
                 top_id:int, choice:dict, source:dict)->dict:
    root=sweeps.get(top_id)
    check(root is not None and root.get("parent_sweep_call_id")==0,
          "ROOT_RETURN_SWEEP_UNMAPPED")
    traversed=[]
    stack=[top_id]
    while stack:
        ident=stack.pop()
        check(ident not in traversed,"SOURCE_CALL_GRAPH_CYCLE_OR_REUSE")
        traversed.append(ident)
        stack.extend(children.get(ident,()))
    candidates=[]
    for ident in traversed:
        sw=sweeps[ident]
        events=sw["observed_candidate_event_stream"]
        if not events:continue
        last=events[-1]
        if (last.get("stage")=="ACTION_READY_CALLED" and
            last.get("simc_NATIVE_return_post_comparator") is True and
            last.get("source_action")==choice["source_action"] and
            last.get("source_row_sha256")==choice["source_row_sha256"] and
            last.get("ordinal_one_based")==choice["source_row_ordinal"] and
            sw["source_list"]==choice["source_list"]):
            candidates.append((ident,last))
    # A same-named action from a different branch is not a provable leaf.
    check(len(candidates)==1,"AMBIGUOUS_OR_MISSING_ACTUAL_CPP_LEAF")
    leaf_id,ev=candidates[0]
    chain=[leaf_id]
    while chain[-1]!=top_id:
        parent=sweeps[chain[-1]]["parent_sweep_call_id"]
        check(type(parent) is int and parent in sweeps and parent<chain[-1],
              "BROKEN_PARENT_ID_OR_NONCAUSAL_CHILD")
        chain.append(parent)
    chain.reverse()
    k=choice["source_original_return_kind"]
    check((k=="DIRECT" and len(chain)==1) or
          (k=="CHILD_PROPAGATED" and len(chain)>1),
          "NATIVE_CPP_RETURN_KIND_VS_LEAF_ROUTE_MISMATCH")
    check(root["at_simc_ms"]==source["simc_ms"] and
          all(sweeps[n]["at_simc_ms"]==source["simc_ms"] for n in chain),
          "SOURCE_SELECTION_TIMESTAMP_DRIFT")
    for i,parent_id in enumerate(chain[:-1]):
        parent=sweeps[parent_id]
        next_id=chain[i+1]
        check(sweeps[next_id]["parent_sweep_call_id"]==parent_id,
              "NONCAUSAL_SELECT_NESTING")
        last=parent["observed_candidate_event_stream"][-1]
        check(last.get("stage")=="ACTION_READY_CALLED" and
              last.get("source_action")=="call_action_list" and
              last.get("simc_NATIVE_return_post_comparator") is True,
              "NESTED_SOURCE_NOT_PROPAGATED_FROM_CALL")
    check(type(ev.get("original_action_ready_root_id")) is int and
          ev["original_action_ready_root_id"]>0 and
          ev.get("source_init_stage")=="FOREGROUND_MEMBER_AT_INIT",
          "CPP_LEAF_READY_ROOT_UNRELIABLE")
    return {
        "source_cpp_select_path_sweep_ids":chain,
        "leaf_select_sweep_id":leaf_id,
        "source_cpp_ready_root_id":ev["original_action_ready_root_id"],
        "leaf_cxx_action_ready_post":True,
        "leaf_identical_source_row_proven":True,
        "was_child_propagated":k=="CHILD_PROPAGATED",
    }

def _root_pre(pre:dict,leaf:dict,choice:dict,at_ms:int,
              expected_targets:int)->dict:
    seen=set()
    matching=[]
    for sample in pre["first_bounded_examples"]:
        rid=sample.get("root_call_id")
        check(type(rid) is int and rid>0 and rid not in seen,
              "DUPLICATE_OR_MALFORMED_ACTOR_PRE_SAMPLE_ROOT")
        seen.add(rid)
        if rid==leaf["source_cpp_ready_root_id"]:
            matching.append(sample)
    check(len(matching)<=1,"MULTIPLE_EXACT_SELECTED_ROOT_STATE_SAMPLES")
    if not matching:
        return {
            "status":"UNKNOWN_EXACT_SELECTED_ROOT_PRE_SAMPLE_NOT_RETAINED",
            "capture":"NONE",
            "active_enemies":None,
            "ready_root_id":leaf["source_cpp_ready_root_id"],
            "WCL_strict_transition_PRE":False,
            "original_source_CPP_PRE_order_proven":False,
        }
    p=matching[0]
    check(p.get("source_row_sha256")==choice["source_row_sha256"] and
          p.get("source_action")==choice["source_action"] and
          p.get("at_simc_ms")==at_ms and
          p.get("source_FULL_action_READY")=="UNKNOWN" and
          p.get("original_actor_PRE_source_causality_proven") is True and
          p.get("WCL_strict_transition_PRE")=="NOT_PROVEN" and
          type(p.get("observed_before_call_active_enemies")) is int and
          p["observed_before_call_active_enemies"]==expected_targets,
          "TAMPERED_EXACT_ACTOR_PRE_OR_SOURCE_ROOT")
    return {
        "status":"OBSERVED_ORIGINAL_CPP_SOURCE_METHOD_PRE",
        "capture":"SIMC_DIRECT_BEFORE_ORIGINAL_READY_CALL",
        "source_row_sha256":choice["source_row_sha256"],
        "source_action":choice["source_action"],
        "ready_root_id":leaf["source_cpp_ready_root_id"],
        "at_simc_ms":at_ms,
        "active_enemies":p["observed_before_call_active_enemies"],
        "WCL_strict_transition_PRE":False,
        "original_source_CPP_PRE_order_proven":True,
    }

def _if_from_exact_root(choice:dict,actor:dict)->dict:
    source_condition=choice["source_row_condition"]
    expression=source_condition.get("source_IF")
    if expression is None or not isinstance(expression,str) or not expression:
        return {
            "status":"UNKNOWN_NO_RECONSTRUCTABLE_APL_IF",
            "source_IF":"SOURCE_NOT_A_BOOL_EXPR",
            "exact_root_AST_value":None,
            "independent_full_IF_proven":False,
        }
    ast=Expression(expression).parse()
    symbols=sorted(ast_symbols(ast))
    root=actor.get("active_enemies")
    facts={"active_enemies":root} if type(root) is int else {}
    value=truth(evaluate_ast(ast,facts))
    # A complete determinate expression needs only the verified same-root
    # source facts, not native success, post comparator or WCL state.
    return {
        "status":("EXACT_SOURCE_ROOT_INDEPENDENT_AST_"+
                  ("TRUE" if value else "FALSE") if value is not None
                  else "UNKNOWN_UNOBSERVED_EXPRESSION_OPERANDS"),
        "source_IF":expression,
        "direct_root_PRE_operand_names":sorted(facts),
        "source_symbol_names":symbols,
        "missing_source_operands":sorted(set(symbols)-set(facts)),
        "exact_root_AST_value":value,
        "independent_full_IF_proven":value is not None,
        "native_return_used_to_populate_expression":False,
    }

def _source_adapter(choice:dict,adapter:dict,leaf:dict,
                    actor:dict,at_ms:int,context:str,
                    expression:dict)->dict|None:
    if choice.get("source_action")!=adapter["source_action"]:
        return None
    fields=adapter["readiness_route"]
    require=["arcane_orb_t_local_ready_override",
             "inherited_arcane_mage_spell_ready",
             "inherited_mage_spell_ready","base_action_t_ready",
             "all_required_gates_closed","independent_FULL_READY_proven"]
    check(all(k in fields for k in require) and
          fields["all_required_gates_closed"] is False and
          fields["independent_FULL_READY_proven"] is False and
          adapter.get("status")==
            "SOURCE_PINNED_PARTIAL_MECHANICS_NOT_FULL_READY_NOT_LIVE_GAME_TRUTH" and
          adapter["source_cpp_blob_sha1"]=="306d835f2db5f7418da221ce155d32e81c53f45c",
          "SOURCE_SPEC_ADAPTER_CLOSURE_OR_PIN_DRIFT")
    # Reuse the preexisting generic independent proof engine. This GateContract
    # is explicitly OPEN: the second obligation does not imply a discovered
    # complete source path, or assume cooldowns/targets/GCD are available.
    ident=Identity(
        scope=f"simc:{context}:selected_source_leaf_{leaf['leaf_select_sweep_id']}",
        source_sha256=choice["source_row_sha256"],
        t_ms=at_ms,
        ordinal=choice["source_row_ordinal"],
        occurrence=leaf["source_cpp_ready_root_id"])
    gates=GateContract(
        source=adapter["source_cpp_path"]+"::"+adapter["source_class"],
        required=("APL_IF_TRUE","UNWALKED_NATIVE_FULL_VIRTUAL_READY"),
        source_sha256=choice["source_row_sha256"],closed=False)
    facts=[]
    if expression["exact_root_AST_value"] is not None:
        check(actor["original_source_CPP_PRE_order_proven"] is True,
              "EXACT_SOURCE_PRE_REQUIRED_FOR_TRUE_IF")
        facts.append(Fact(
            identity=ident,gate="APL_IF_TRUE",
            value=expression["exact_root_AST_value"],
            basis="INDEPENDENT_SOURCE_REPLAY",
            captured="SIMC_ORIGINAL_METHOD_PRE",event_t_ms=at_ms,
            receipt=f"original_cpp_root_{leaf['source_cpp_ready_root_id']}"))
    verified=decide_candidate(ident,gates,facts,is_physical_action=True)
    # Even APL IF false means only that particular source action row is
    # not selected, not that another replacement/variant is entirely unusable.
    check(verified["positive_route_closed"] is False and
          verified["dummy_error_permitted"] is False and
          verified["decision"]!="READY",
          "UNAUTHORIZED_POSITIVE_READY_CLAIM")
    return {
        "adapter_schema":ADAPTER_SCHEMA,
        "adapter_source_CPP_blob_sha1":adapter["source_cpp_blob_sha1"],
        "source_class":adapter["source_class"],
        "original_execution_source_lines":adapter["execute_lines"],
        "source_execution_effect_witnesses":[
            {"phase":x["phase"],"source_cpp_line":x["source_cpp_line"],
             "meaning":x["meaning"]}
            for x in adapter["source_observations"]
            if x["phase"] in ("EXECUTE","IMPACT")],
        "effects_numeric_state_next":"UNKNOWN_DO_NOT_SIMULATE_FROM_SOURCE_NAMES",
        "ready_route":"OPEN_INHERITED_VIRTUAL_METHOD_UNRECONSTRUCTED",
        "general_proof_engine_candidate":verified,
        "trained_dummy_error_permitted":False,
    }

def compose(original_native_zip:bytes|Path, integrated:dict,
            adapter:dict)->dict:
    original_reconstructed_dir=isinstance(original_native_zip,Path)
    if original_reconstructed_dir:
        check(original_native_zip.is_dir(),"ORIGINAL_NATIVE_ARTIFACT_DIRECTORY_REQUIRED")
    else:
        check(type(original_native_zip) is bytes and
              sha256(original_native_zip).hexdigest()==ORIGINAL_ARTIFACT_SHA256,
              "ORIGINAL_ACTUAL_NATIVE_CPP_ZIP_SHA256_REQUIRED")
    check(integrated.get("schema")==INTEGRATED_SCHEMA and
          integrated.get("product_policy_id")==POLICY and
          integrated.get("authoritative_cast_sequence") is False and
          integrated.get("native_selection_is_not_independent_ready") is True and
          integrated.get("trained_dummy_error_permitted") is False and
          integrated.get("aggregate",{}).get("retained_source_opener_steps")==64 and
          integrated.get("aggregate",{}).get("native_cpp_sweep_records_reused")==2121,
          "ORIGINAL_INTEGRATED_OPENER_CONTRACT_CHANGED")
    check(adapter.get("schema")==ADAPTER_SCHEMA and
          adapter.get("policy_id")==POLICY and
          adapter.get("source_cpp_path")=="engine/class_modules/sc_mage.cpp" and
          adapter.get("source_simc_revision")=="b522cded8c26b97dac03fdf56e57a03ec7e8faa6" and
          adapter.get("source_action")=="arcane_orb" and
          adapter.get("source_profile_git_blob_sha1")==
            "8d06eda4f69374dd1ed2e2d1eb8076b82cbbaf7f" and
          adapter.get("source_cpp_blob_sha1")==
            "306d835f2db5f7418da221ce155d32e81c53f45c" and
          adapter.get("effect_projection",{}).get("simulate_with_unverified_data") is False,
          "SPEC_ADAPTER_SOURCE_PIN_OR_SCOPE_FAILED")
    results={}
    totals=Counter()
    # SOURCE_MEMBER_SHA256 is an exact byte pin for the extracted GitHub
    # artifact members. ZIP digest is asserted only for the original ZIP mode.
    import io
    source=(original_native_zip if original_reconstructed_dir else
            zipfile.ZipFile(io.BytesIO(original_native_zip)))
    try:
        for case in CASES:
            temporal=_load(source,"zrot-source-temporal-frontier-"+case+".json")
            selected=_load(source,"zrot-native-source-selected-return-"+case+".json")
            pre=_load(source,"zrot-original-root-actor-pre-"+case+".json")
            ctx=integrated["cases"][case]
            target=1 if case.endswith("-st") else 2
            check(temporal.get("schema")==TIME_SCHEMA and
                  selected.get("schema")==SELECTED_SCHEMA and
                  pre.get("schema")==PRE_SCHEMA and
                  all(x.get("product_policy_id")==POLICY
                      for x in (temporal,selected,pre)) and
                  temporal.get("target_count")==target and
                  ctx.get("target_count_scenario")==target and
                  ctx.get("source_profile_git_blob_sha1")==
                      temporal.get("source_profile_git_blob_sha1")==
                      selected.get("source_profile_git_blob_sha1")==
                      pre.get("source_profile_git_blob_sha1") and
                  temporal.get("source_order_complete") is False and
                  temporal.get("independent_FULL_READY_proven")==0 and
                  pre.get("source_actor_PRE_operand")=="active_enemies" and
                  pre.get("full_READY_proven")==0 and
                  selected.get("source_sweeps_exact_cxx_return")==
                      temporal.get("source_sweep_count")==ctx.get("original_sweep_count"),
                  "ORIGINAL_CPP_PER_CASE_PROFILE_OR_SOURCE_COHORT_DRIFT")
            sweeps={}
            children=defaultdict(list)
            for sw in temporal["observed_time_scoped_selection_frontiers"]:
                sid=sw.get("sweep_call_id")
                check(type(sid) is int and sid>0 and sid not in sweeps,
                      "DUPLICATE_OR_UNMAPPED_CPP_SWEEP")
                sweeps[sid]=sw
                children[sw["parent_sweep_call_id"]].append(sid)
            choices=selected["bounded_root_return_examples"]
            steps=ctx["timeline"]
            check(len(steps)==len(choices)==16,"ACTUAL_SELECTED_SOURCE_SAMPLE_COUNT_DRIFT")
            aligned=[]
            for sample,choice in zip(choices,steps):
                check(sample.get("sweep_call_id")==choice.get("original_cpp_top_sweep_id") and
                      sample.get("source_action")==choice.get("source_action") and
                      sample.get("source_list")==choice.get("source_list") and
                      sample.get("source_ordinal")==choice.get("source_row_ordinal") and
                      sample.get("source_row_sha256")==choice.get("source_row_sha256") and
                      sample.get("return_kind")==choice.get("source_original_return_kind") and
                      sample.get("at_simc_ms")==choice.get("simc_ms") and
                      choice.get("full_action_READY_proven") is False,
                      "SELECTED_CXX_SOURCE_ROW_NOT_SAME_AS_INTEGRATED_OPENER")
                leaf=_unique_leaf(sweeps,children,sample["sweep_call_id"],
                                  choice,choice)
                actor=_root_pre(pre,leaf,choice,choice["simc_ms"],target)
                expression=_if_from_exact_root(choice,actor)
                if actor["active_enemies"] is not None:
                    totals["exact_same_cpp_root_active_enemies_PRE"]+=1
                if expression["independent_full_IF_proven"]:
                    totals["full_IF_from_exact_selected_root"]+=1
                if leaf["was_child_propagated"]:
                    totals["selected_nested_leaf_source_return"]+=1
                else:
                    totals["selected_direct_leaf_source_return"]+=1
                spec_result=(
                    _source_adapter(choice,adapter,leaf,actor,
                                    choice["simc_ms"],case,expression)
                    if ctx["source_profile_git_blob_sha1"]==
                       adapter["source_profile_git_blob_sha1"] else None)
                if spec_result is not None:
                    totals["source_pinned_arcane_orb_adapter_attached"]+=1
                aligned.append({
                    "original_cpp_selected_top_sweep_id":sample["sweep_call_id"],
                    "original_cpp_simc_ms":choice["simc_ms"],
                    "source_action":choice["source_action"],
                    "source_list":choice["source_list"],
                    "source_row_ordinal":choice["source_row_ordinal"],
                    "source_row_sha256":choice["source_row_sha256"],
                    "native_select_return_proven":True,
                    "source_leaf_cpp":leaf,
                    "exact_original_selected_root_PRE":actor,
                    "exact_selected_root_source_IF":expression,
                    "source_pinned_spec_adapter":spec_result,
                    "independent_FULL_READY_proven":False,
                    "original_native_post_boolean_used_as_independent_ready":False,
                    "player_spells_or_manual_keypresses_proven":False,
                    "dummy_feedback_verdict":"UNKNOWN",
                })
            results[case]={
                "source_profile_git_blob_sha1":ctx["source_profile_git_blob_sha1"],
                "target_count":target,
                "actual_original_cpp_source_select_sweeps":len(sweeps),
                "observed_top_level_source_returns":ctx["all_top_level_native_source_returns"],
                "early_source_choice_details":aligned,
                "unsampled_original_source_returns":ctx["unretained_root_source_returns"],
                "source_state_at_choice_not_observed_is_unknown":True,
            }
            totals["original_source_sweeps_reused"]+=len(sweeps)
            totals["exact_original_cpp_selected_leaf_root_resolved"]+=len(aligned)
            totals["unsampled_original_top_level_choices"]+=ctx["unretained_root_source_returns"]
    finally:
        if not original_reconstructed_dir:
            source.close()
    check(totals["original_source_sweeps_reused"]==2121 and
          totals["exact_original_cpp_selected_leaf_root_resolved"]==64 and
          totals["unsampled_original_top_level_choices"]==198,
          "FOUR_CASE_NATIVE_COHORT_TOTAL_DRIFT")
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "source_native_original_zip_sha256_recorded":ORIGINAL_ARTIFACT_SHA256,
        "original_zip_bytes_directly_verified":not original_reconstructed_dir,
        "all_twelve_source_member_sha256_verified":True,
        "cases":results,"counts":dict(sorted(totals.items())),
        "source_selected_leaf_root_identity_exact":True,
        "selected_root_PRE_subset_only":True,
        "source_virtual_READY_route_independently_closed":False,
        "validated_current_WCL_general_rotation":False,
        "current_WoW_client_addon_tested":False,
        "safe_dummy_feedback_permitted":False,
        "WCL_API_calls":0,
    }

def selftest()->dict:
    # The actual four-case E2E also tests wrong nested ancestry, wrong actor
    # source/root hash, FALSE native leaf and forged mechanics adapter.
    row="a"*64
    top={"sweep_call_id":1,"parent_sweep_call_id":0,
         "at_simc_ms":0,"source_list":"default",
         "observed_candidate_event_stream":[{
             "stage":"ACTION_READY_CALLED",
             "source_action":"call_action_list",
             "simc_NATIVE_return_post_comparator":True}]}
    child={"sweep_call_id":2,"parent_sweep_call_id":1,
           "at_simc_ms":0,"source_list":"cooldowns",
           "observed_candidate_event_stream":[{
               "stage":"ACTION_READY_CALLED","source_action":"arcane_orb",
               "source_row_sha256":row,"ordinal_one_based":1,
               "original_action_ready_root_id":8,
               "source_init_stage":"FOREGROUND_MEMBER_AT_INIT",
               "simc_NATIVE_return_post_comparator":True}]}
    example={"return_kind":"CHILD_PROPAGATED","source_action":"arcane_orb",
             "source_row_sha256":row,"source_ordinal":1,
             "source_list":"cooldowns"}
    source=dict(example,simc_ms=0)
    evidence=_unique_leaf({1:top,2:child},{1:[2]},1,example,source)
    assert evidence["source_cpp_select_path_sweep_ids"]==[1,2]
    assert evidence["source_cpp_ready_root_id"]==8
    assert evidence["was_child_propagated"] is True
    pre={"first_bounded_examples":[{"root_call_id":8,
          "source_action":"arcane_orb","source_row_sha256":row,"at_simc_ms":0,
          "observed_before_call_active_enemies":2,
          "source_FULL_action_READY":"UNKNOWN",
          "original_actor_PRE_source_causality_proven":True,
          "WCL_strict_transition_PRE":"NOT_PROVEN"}]}
    actor=_root_pre(pre,evidence,source,0,2)
    assert actor["active_enemies"]==2
    assert actor["WCL_strict_transition_PRE"] is False
    for fail in ("source_row_sha256","observed_before_call_active_enemies"):
        bad=json.loads(json.dumps(pre))
        bad["first_bounded_examples"][0][fail]="b"*64 if fail=="source_row_sha256" else 1
        try:_root_pre(bad,evidence,source,0,2)
        except ExactLeafSourceError:pass
        else:raise AssertionError("MUTATED_PRE_WAS_ACCEPTED")
    broken=json.loads(json.dumps(child))
    broken["observed_candidate_event_stream"][-1]["simc_NATIVE_return_post_comparator"]=False
    try:_unique_leaf({1:top,2:broken},{1:[2]},1,example,source)
    except ExactLeafSourceError:pass
    else:raise AssertionError("FALSE_READY_WAS_PASSED_AS_SOURCE_CHOICE")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":7,"new_CPP_executed":False,
        "full_READY_proven":0,"WCL_API_calls":0,
    }

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-native-zip",type=Path)
    p.add_argument("--original-native-dir",type=Path)
    p.add_argument("--integrated-opener-json",type=Path)
    p.add_argument("--spec-adapter",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    native_sources=[a.original_native_zip is not None,a.original_native_dir is not None]
    if not any(native_sources) and a.integrated_opener_json is None and a.spec_adapter is None:
        output=selftest()
    elif sum(native_sources)==1 and a.integrated_opener_json is not None and a.spec_adapter is not None:
        original=(a.original_native_zip.read_bytes() if a.original_native_zip else
                  a.original_native_dir)
        output=compose(original,
                       json.loads(a.integrated_opener_json.read_bytes()),
                       json.loads(a.spec_adapter.read_bytes()))
    else:p.error("choose one original Native ZIP or pinned artifact directory, plus integrated opener and SpecAdapter")
    raw=(json.dumps(output,sort_keys=True,separators=(",",":"),
                    ensure_ascii=False,allow_nan=False)+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(raw)
    else:
        import sys
        sys.stdout.buffer.write(raw)

if __name__=="__main__":main()
