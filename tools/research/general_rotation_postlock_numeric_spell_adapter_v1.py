#!/usr/bin/env python3
"""Post-lock generic numeric WCL spell -> all exact SimC APL row hypotheses.

Consumes the already frozen WCL numeric-only discovery plus a separately
pinned external SpecAdapter and a source-only SimC IR. This module MUST NOT
be imported by any WCL discovery/candidate producer.

An action name match against the external adapter is a *post-lock hypothesis*
only. An action_t ID is not automatically a Blizzard spell ID; an emitted WCL
cast doesn't prove button/manuality, identical talent build, full action READY,
which repeated APL row won, priority, opener end, or a dummy training error.

No arguments run two-class synthetic self-test without network.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
import argparse
import json
import re
from pathlib import Path

from simc_apl_semantic_ir_v2 import canonical,git_blob
from general_rotation_wcl_postlock_source_ir_bridge_v1 import (
    BINDING_SCHEMA,NUMERIC_SCHEMA,POLICY,EVIDENCE_SCHEMA,
    SOURCE_SCHEMA,load as load_json,postlock_source_probe
)

SCHEMA="ZrotGenericPostlockNumericSourceRowCandidateBindingV1"
ADAPTER_SCHEMA="ZrotSpecActionFamilyMechanicsAdapterV1"
HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")
ACTION=re.compile(r"^[a-z][a-z0-9_]{0,119}$")

class BindingError(ValueError):pass

def require(ok,code):
    if not ok: raise BindingError(code)

def sha(x:bytes)->str:return sha256(x).hexdigest()

def _assert_external_adapter(adapter:dict, raw:bytes, numeric:dict,
                             source_case:dict)->dict[int,dict]:
    """Never infer adapter validity from local class-conditional code."""
    require(type(adapter)==dict and
            adapter.get("schema")==ADAPTER_SCHEMA and
            adapter.get("scope_policy_id")==POLICY and
            sha(raw)==sha(canonical(adapter)) and
            adapter.get("allow_infer_exact_cd_from_gap") is False and
            adapter.get("allow_infer_availability_of_alternative") is False and
            adapter.get("allow_infer_priority_or_player_error") is False and
            adapter.get("protected_blind_lock_sha256")==numeric["lock_sha256"],
            "POSTLOCK_EXTERNAL_SPEC_ADAPTER_LOCK_OR_AUTHORITY_INVALID")
    claim=source_case
    spec=adapter.get("specialization",{})
    require(type(spec)==dict and
            type(spec.get("class"))==str and
            type(spec.get("spec"))==str and
            spec["class"].casefold()==claim["class_key"].casefold() and
            spec["spec"].casefold()==claim["source_spec"].casefold() and
            type(spec.get("spec_id")) is int and spec["spec_id"]>0,
            "ADAPTER_CLASS_SPEC_NOT_SOURCE_PROFILE")
    source=adapter.get("source_simc",{})
    require(type(source)==dict and
            source.get("repo")=="simulationcraft/simc" and
            source.get("revision")==
             "b522cded8c26b97dac03fdf56e57a03ec7e8faa6" and
            type(source.get("git_blob_sha1"))==str and
            HEX40.fullmatch(source["git_blob_sha1"]) and
            type(source.get("path"))==str and
            source["path"].startswith("engine/class_modules/") and
            source["path"].endswith(".cpp"),
            "ADAPTER_ORIGINAL_PINNED_SIMC_CLASS_MODULE_MISSING")
    candidates=adapter.get("candidates")
    require(type(candidates)==list and len(candidates)<=200 and
            candidates, "ADAPTER_NUMERIC_ACTIONS_REQUIRED")
    frozen=set(numeric["numeric_locked_spell_ids"])
    mapping={}
    for row in candidates:
        require(type(row)==dict and
                type(row.get("spell_id")) is int and
                row["spell_id"]>0 and
                row["spell_id"] in frozen and
                row["spell_id"] not in mapping and
                type(row.get("canonical_action")) is str and
                ACTION.fullmatch(row["canonical_action"]) and
                type(row.get("family")) is str and row["family"] and
                row.get("readiness")=="UNKNOWN" and
                row.get("manuality") in (
                     "DIRECT_SPELL_CANDIDATE","UNVERIFIED_AUTO_HYPOTHESIS"),
                "ADAPTER_NUMERIC_ID_TOKEN_OR_READINESS_INVALID")
        if "replaces" in row:
            require(type(row["replaces"]) is str and
                    ACTION.fullmatch(row["replaces"]) and
                    row["replaces"]!=row["canonical_action"],
                    "UNVERIFIED_REPLACEMENT_SOURCE_TOKEN")
        mapping[row["spell_id"]]=row
    require(set(mapping)==frozen,"FROZEN_WCL_NUMERIC_CANDIDATE_COVERAGE_NOT_EXACT")
    return mapping

def compile_binding(numeric:dict,source_case:dict,
                    adapter:dict,adapter_bytes:bytes)->dict:
    """Source hypotheses materialized only AFTER frozen WCL numeric lock."""
    require(type(numeric)==dict and
            numeric.get("schema")==NUMERIC_SCHEMA and
            numeric.get("source_APL_injected_in_numeric_phase") is False and
            numeric.get("candidate_set_changed_after_lock") is False and
            numeric.get("raw_discovery_and_holdout_independent_audit")=="NOT_RUN" and
            numeric.get("ready_or_priority_proven") is False and
            len(numeric.get("numeric_locked_spell_ids",[]))>0 and
            type(numeric.get("lock_sha256"))==str and
            HEX64.fullmatch(numeric["lock_sha256"]),
            "NUMERIC_WCL_FROZEN_LOCK_PRECONDITION_MISSING")
    require(type(source_case)==dict and
            source_case.get("schema")==EVIDENCE_SCHEMA and
            source_case.get("policy_id")==POLICY and
            source_case.get("WCL_independent_candidate_lock")=="NOT_RUN" and
            source_case.get("WCL_independent_holdout")=="NOT_RUN" and
            source_case.get("source_full_READY_proven")==0 and
            source_case.get("source_order_priority_proven")==0 and
            source_case.get("dummy_wrong_skill")=="UNKNOWN" and
            source_case.get("native_selected_used_as_positive_ready_input") is False,
            "SIMC_SOURCE_MODEL_MUST_REMAIN_SOURCE_HYPOTHESIS")
    graph=source_case.get("source_hypothesis_IR",{})
    require(type(graph)==dict and graph.get("schema")==SOURCE_SCHEMA and
            graph.get("evidence_status",{}).get(
                "validated_general_rotation_priority") is False and
            type(graph.get("source_git_blob")) is str and
            HEX40.fullmatch(graph["source_git_blob"]) and
            type(source_case.get("source_target_count",
                 source_case.get("target_count")))==int,
            "SIMC_SOURCE_PROFILE_PINNED_IR_REQUIRED")
    lookup=_assert_external_adapter(adapter,adapter_bytes,numeric,source_case)
    lists=graph["source_only_priority_graph"]["lists"]
    require(type(lists)==dict and lists,"SOURCE_APL_LIST_GRAPH_MISSING")
    indexed={}
    for list_name,rows in lists.items():
        require(type(list_name)==str and
                type(rows)==list,"SOURCE_APL_LIST_ROW_STRUCTURE_INVALID")
        for index,node in enumerate(rows):
            require(type(node)==dict and
                    node.get("identity",{}).get("source_index")==index and
                    node["identity"].get("source_list")==list_name,
                    "SOURCE_APL_ROW_IDENTITY_OR_RANK_DRIFT")
            if node["kind"]!="EXECUTABLE_SOURCE_CANDIDATE":continue
            token=node.get("action")
            require(type(token)==str and ACTION.fullmatch(token),
                    "SIMC_APL_ACTION_TOKEN_INVALID")
            indexed.setdefault(token,[]).append((list_name,index,node))
    mappings=[];summaries=[];counts=Counter(
        x["spell_id"] for x in numeric["numeric_casts"])
    for spell_id,external in sorted(lookup.items()):
        token=external["canonical_action"]
        rows=indexed.get(token,[])
        is_auto=(external["manuality"]=="UNVERIFIED_AUTO_HYPOTHESIS" or
                 external["family"]=="AUTO_ATTACK_UNSCORABLE")
        # Autoattack, even with a source APL row, must never be treated as
        # an explicit human action. Keep numeric ID and candidate info.
        if not is_auto:
            for list_name,index,node in rows:
                require(type(node["identity"].get("source_line_sha256"))==str
                        and HEX64.fullmatch(node["identity"][
                             "source_line_sha256"]),
                        "SIMC_SOURCE_ROW_SHA256_UNVERIFIED")
                mappings.append({
                    "spell_id":spell_id,
                    "source_list":list_name,
                    "source_index":index,
                    "source_row_sha256":
                        node["identity"]["source_line_sha256"],
                    # No WCL aura/resource numeric signal is authorized as a
                    # specific source expression operand just by the name.
                    "symbol_to_raw_signal":{}
                })
        summaries.append({
          "numeric_spell_id":spell_id,
          "external_adapter_action_token":token,
          "external_adapter_family":external["family"],
          "external_adapter_manuality":external["manuality"],
          "raw_WCL_casts_in_comparison":counts[spell_id],
          "exact_APL_source_rows_found":len(rows),
          "candidate_APL_rows_emitted":0 if is_auto else len(rows),
          "source_row_identity_status":(
             "AUTO_UNSCORABLE_NO_SELECTED_APL_CAST" if is_auto else
             "EXACT_EXTERNAL_TOKEN_SOURCE_CANDIDATE_UNVERIFIED_GAME_IDENTITY"
             if rows else "UNKNOWN_NO_EXACT_SOURCE_ACTION_TOKEN"),
          "parent_replaced_action_token_hypothesis":
             external.get("replaces"),
          "parent_action_token_present_in_source":(
             external.get("replaces") in indexed
             if external.get("replaces") else None),
          "player_actual_talent_and_buff_gate":"UNKNOWN",
          "independent_current_game_spell_id_validation":"NOT_RUN",
          "WCL_numeric_action_is_actual_player_button":"UNKNOWN",
          "source_runtime_selected_row":"UNKNOWN",
          "full_READY":"UNKNOWN",
          "gameplay_priority":"UNKNOWN"
        })
    require(len(mappings)<=200,
            "SOURCE_BINDING_ROW_COUNT_EXCEEDS_EXISTING_BRIDGE_CONTRACT")
    output={
      "schema":SCHEMA,"policy_id":POLICY,
      "frozen_numeric_phase_sha256":sha(canonical(numeric)),
      "frozen_numeric_lock_sha256":numeric["lock_sha256"],
      "source_case_sha256":sha(canonical(source_case)),
      "source_git_blob":graph["source_git_blob"],
      "source_spec":source_case["source_spec"],
      "source_target_count":source_case["target_count"],
      "external_adapter_bytes_sha256":sha(adapter_bytes),
      "external_adapter_status":"CANDIDATE_POSTLOCK_ONLY",
      "source_spell_ID_mapping_current_Retail_independently_audited":False,
      "actor_class_spec_match_to_source_model":"PROVEN_SOURCE_METADATA_ONLY",
      "WCL_actor_build_equivalence_to_SimC":"UNKNOWN",
      "WCL_target_count_to_SimC_source_context":"UNKNOWN",
      "numeric_candidate_summaries":summaries,
      "output_bindings":len(mappings),
      "numeric_candidates_covered_by_exact_non_auto_token":
        sum(x["candidate_APL_rows_emitted"]>0 for x in summaries),
      "numeric_candidate_CASTS_with_exact_token_hypothesis":
        sum(x["raw_WCL_casts_in_comparison"]
            for x in summaries if x["candidate_APL_rows_emitted"]>0),
      "excluded_auto_candidate_casts":
        sum(x["raw_WCL_casts_in_comparison"] for x in summaries
            if x["external_adapter_manuality"]=="UNVERIFIED_AUTO_HYPOTHESIS"),
      "allow_whole_spell_READY_from_mapping":False,
      "allow_selected_APL_row_from_cast":False,
      "allow_dummy_wrong_cast_from_mapping":False,
      "new_WCL_API_calls":0,
      "new_native_SimC_CXX_builds":0,
      "binding":{
        "schema":BINDING_SCHEMA,
        "policy_id":POLICY,
        "bound_numeric_lock_sha256":numeric["lock_sha256"],
        "source_profile_git_blob":graph["source_git_blob"],
        "source_spec":source_case["source_spec"],
        "source_target_count":source_case["target_count"],
        "binding_stage":"POST_LOCK_ONLY",
        "action_identity_and_mechanic_independently_audited":False,
        "build_equivalence_independently_verified":False,
        "WCL_target_count_at_cast_verified":False,
        "numeric_to_source_rows":mappings
      }
    }
    return output

def selftest()->dict:
    import copy
    from general_rotation_source_hypothesis_ir_v1 import compile_profile
    from general_rotation_wcl_postlock_source_ir_bridge_v1 import (
        numeric_frozen_boundary
    )
    from fresh_wcl_engine_v1 import canonical as native_canonical
    classes=[("warrior","fury"),("mage","arcane")]
    checks=0
    for cls,spec in classes:
        p=(cls+'="Synthetic"\nspec='+spec+'\n'
           'actions=alpha,if=buff.first.up\n'
           'actions+=/alpha,if=buff.second.up\n'
           'actions+=/omega,if=buff.third.up\n'
           'actions+=/auto_attack\n').encode()
        graph=compile_profile(p,{"key":spec,
                                 "class_key":cls,
                                 "git_blob":git_blob(p)})
        source_case={
          "schema":EVIDENCE_SCHEMA,
          "policy_id":POLICY,
          "class_key":cls,"source_spec":spec,"target_count":1,
          "source_hypothesis_IR":graph,
          "source_full_READY_proven":0,
          "source_order_priority_proven":0,
          "WCL_independent_candidate_lock":"NOT_RUN",
          "WCL_independent_holdout":"NOT_RUN",
          "dummy_wrong_skill":"UNKNOWN",
          "native_selected_used_as_positive_ready_input":False,
        }
        ids=(1201,1202)
        adapter={
          "schema":ADAPTER_SCHEMA,"scope_policy_id":POLICY,
          "specialization":{"class":cls.title(),"spec":spec.title(),
                            "spec_id":999},
          "source_simc":{"repo":"simulationcraft/simc",
             "revision":"b522cded8c26b97dac03fdf56e57a03ec7e8faa6",
             "path":"engine/class_modules/sc_dummy.cpp",
             "git_blob_sha1":"a"*40},
          "candidates":[
            {"spell_id":1201,"canonical_action":"alpha",
             "family":"SYNTHETIC_ALPHA",
             "manuality":"DIRECT_SPELL_CANDIDATE","readiness":"UNKNOWN"},
            {"spell_id":1202,"canonical_action":"auto_attack",
             "family":"AUTO_ATTACK_UNSCORABLE",
             "manuality":"UNVERIFIED_AUTO_HYPOTHESIS","readiness":"UNKNOWN"}],
          "allow_infer_exact_cd_from_gap":False,
          "allow_infer_availability_of_alternative":False,
          "allow_infer_priority_or_player_error":False,
          "protected_blind_lock_sha256":"1"*64,
        }
        numeric={
           "schema":NUMERIC_SCHEMA,
           "lock_sha256":"1"*64,
           "numeric_locked_spell_ids":[1201,1202],
           "numeric_casts":[{"event_id":"one","at_ms":2000,
                             "spell_id":1201},
                            {"event_id":"two","at_ms":3000,
                             "spell_id":1202}],
           "source_APL_injected_in_numeric_phase":False,
           "candidate_set_changed_after_lock":False,
           "raw_discovery_and_holdout_independent_audit":"NOT_RUN",
           "ready_or_priority_proven":False,
        }
        raw=canonical(adapter)
        result=compile_binding(numeric,source_case,adapter,raw)
        b=result["binding"]
        require(result["output_bindings"]==2 and
                result["numeric_candidates_covered_by_exact_non_auto_token"]==1
                and result["excluded_auto_candidate_casts"]==1 and
                len(b["numeric_to_source_rows"])==2 and
                result["allow_whole_spell_READY_from_mapping"] is False,
                "GENERIC_POSTLOCK_APL_MULTIPLE_ROW_SYNTHETIC_FAILED")
        checks+=1
        def must_reject(changed_numeric=None,changed_source=None,changed_adapter=None):
            nonlocal checks
            n=changed_numeric or numeric
            s=changed_source or source_case
            a=changed_adapter or adapter
            try:
                compile_binding(n,s,a,canonical(a))
            except BindingError: checks+=1
            else:raise AssertionError("UNVERIFIED_POSTLOCK_BINDING_ACCEPTED")
        v=copy.deepcopy(adapter);v["protected_blind_lock_sha256"]="0"*64
        must_reject(changed_adapter=v)
        v=copy.deepcopy(adapter);v["candidates"][0]["readiness"]="READY"
        must_reject(changed_adapter=v)
        v=copy.deepcopy(adapter);v["candidates"][0]["spell_id"]=999
        must_reject(changed_adapter=v)
        v=copy.deepcopy(adapter);v["allow_infer_priority_or_player_error"]=True
        must_reject(changed_adapter=v)
        v=copy.deepcopy(adapter);v["specialization"]["class"]="Other"
        must_reject(changed_adapter=v)
        v=copy.deepcopy(adapter);v["candidates"].append(
           copy.deepcopy(v["candidates"][1]))
        must_reject(changed_adapter=v)
        v=copy.deepcopy(adapter);v["source_simc"]["git_blob_sha1"]="x"*40
        must_reject(changed_adapter=v)
        v=copy.deepcopy(numeric);v["source_APL_injected_in_numeric_phase"]=True
        must_reject(changed_numeric=v)
        v=copy.deepcopy(source_case);v["source_full_READY_proven"]=1
        must_reject(changed_source=v)
    return {"schema":SCHEMA,"status":"PASS_TWO_CLASS_SYNTHETIC",
            "class_count":len(classes),
            "positive_cases":2,
            "negative_controls":checks-2,
            "multiple_APL_rows_preserved":True,
            "unverified_auto_excluded":True,
            "source_spell_identity_current_Retail_verified":False,
            "real_WCL_spell_to_SourceRow_guard_MATCH":0,
            "full_ready_proven":0,"dummy_error_proven":0,
            "WCL_API_calls":0,"SimC_CXX_builds":0}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--numeric-phase",type=Path)
    parser.add_argument("--source-case",type=Path)
    parser.add_argument("--external-adapter",type=Path)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if all(x is None for x in vars(args).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    require(all(x is not None for x in vars(args).values()),
            "EXPLICIT_NUMERIC_PHASE_SOURCE_MODEL_AND_ADAPTER_REQUIRED")
    numeric,_=load_json(args.numeric_phase)
    case,_=load_json(args.source_case)
    adapter,raw=load_json(args.external_adapter)
    result=compile_binding(numeric,case,adapter,raw)
    require(not args.out.exists(),
            "NO_OVERWRITE_SCIENTIFIC_BINDING_OUTPUT")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes(canonical(result))
    print("GENERIC_POSTLOCK_EXTERNAL_ADAPTER_BINDING_SHA256="+
          sha(args.out.read_bytes()))
    print("GENERIC_POSTLOCK_NUMERIC_CANDIDATES_LINKED="+
          str(result["numeric_candidates_covered_by_exact_non_auto_token"]))
    print("GENERIC_POSTLOCK_ACTION_GAMEPLAY_READY_PROVEN=0")

if __name__=="__main__":
    main()
