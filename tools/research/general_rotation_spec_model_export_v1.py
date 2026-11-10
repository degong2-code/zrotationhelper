#!/usr/bin/env python3
"""Produce one concrete, readable General Rotation *research draft* per spec.

The SAME source-neutral converter handles any pinned SimC class/spec manifest:
- all exact source-ordered APL actions and control/variable rows, IF/ELSE
  conditions, and precombat sources (not falsely called a combat opener);
- ST, 2-target, AoE, talent/build source-guard context branches;
- independently source-pinned original Native opening *samples* when supplied.

Native action names are not guaranteed unique APL selected rows, and an APL
source IF TRUE is not READY or optimal. The generated models are a useful
executable-research contract for subsequent same-root PRE and WCL post-lock
validation, NOT an addon action recommendation. No specialization rules in
Generic. Default PyCharm/no args: synthetic fail-closed selftest.

The caller must provide explicit source root/manifest/scenario matrix, and,
optionally, a SHA256-pinned previously verified Native sample portfolio.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from simc_apl_semantic_ir_v2 import canonical,git_blob
from general_rotation_source_hypothesis_ir_v1 import compile_profile
from general_rotation_simc_e2e_research_engine_v1 import compile_spec
from general_rotation_simc_multi_spec_cold_start_v1 import load_manifest
from general_rotation_source_guard_scenario_frontier_v1 import (
    control_guard_frontier,SourceGuardFrontierError,
    MATRIX as MATRIX_SCHEMA,
    POLICY,
    REV,
)
from general_rotation_simc_native_source_portfolio_v1 import SCHEMA as NATIVE_SCHEMA

SCHEMA="ZrotGeneralRotationPerSpecializationResearchDraftV1"
INDEX_SCHEMA="ZrotGeneralRotationPerSpecExportIndexV1"
HEX64=re.compile(r"[a-f0-9]{64}\Z")
KEY=re.compile(r"[a-z0-9][a-z0-9_]{0,63}\Z")

class ExportError(ValueError): pass

def need(condition:bool,code:str)->None:
    if not condition:raise ExportError(code)

def row_export(row:dict,index:int,list_name:str)->dict:
    identity=row.get("identity")
    need(type(identity) is dict and
         identity.get("source_list")==list_name and
         identity.get("source_index")==index and
         row.get("source_priority_ordinal")==index and
         row.get("expected_ready")=="UNKNOWN",
         "SOURCE_APL_PRIORITY_PROVENANCE_OR_READY_TAMPERED")
    behavior=row.get("behavior")
    need(behavior in {"ACTION","CALL","RUN","VARIABLE",
                      "SIDE_EFFECT_SOURCE_MODEL_UNVERIFIED",
                      "SWAP_UNSUPPORTED"},
         "UNKNOWN_SOURCE_APL_CONTROL_BEHAVIOR")
    conditions=row.get("conditions",{})
    need(type(conditions) is dict and
         all(type(k) is str and type(v) is dict and
             type(v.get("raw_expression")) is str and
             type(v.get("source_ast")) is list and
             type(v.get("symbols")) is list
             for k,v in conditions.items()),
         "SOURCE_APL_CONDITIONS_UNVERIFIED")
    dest=row.get("control_destination")
    need((behavior not in {"CALL","RUN","SWAP_UNSUPPORTED"} and dest is None)
         or (behavior in {"CALL","RUN","SWAP_UNSUPPORTED"} and type(dest) is str),
         "CONTROL_DESTINATION_INCONSISTENT")
    ident_sha=identity.get("source_line_sha256")
    need(type(ident_sha) is str and HEX64.fullmatch(ident_sha)
         and type(row.get("source_text")) is str and
         sha256(row["source_text"].encode()).hexdigest()==ident_sha,
         "PINNED_ORIGINAL_APL_SOURCE_LINE_HASH_MISMATCH")
    return {
        "rank_one_based":index+1,
        "source_list":list_name,
        "source_line":identity["source_line"],
        "source_sha256":ident_sha,
        "source_text_exact":row["source_text"],
        "source_action":row["action"],
        "behavior":behavior,
        "control_destination":dest,
        "if_original":conditions.get("if",{}).get("raw_expression"),
        "all_compiled_source_expression_fields":{
            k:{"source":v["raw_expression"],
               "required_symbols":v["symbols"],
               "typed_AST":v["source_ast"]}
            for k,v in sorted(conditions.items())},
        "required_state_inputs":sorted(set(
            name for v in conditions.values() for name in v["symbols"])),
        "source_priority_order":"TOP_TO_BOTTOM_IF_GUARD_AND_NATIVE_READY",
        "source_conditional_if_else":"IF source guard true AND native ready THEN attempt action; ELSE next ranked row",
        "source_local_IF_FALSE_excludes_this_row_only":True,
        "positive_native_READY_certified":"UNKNOWN",
        "priority_over_other_simultaneously_available_actions":"SOURCE_APL_HYPOTHESIS_ONLY",
        "WoW_expected_cast":"UNKNOWN",
    }

def render_spec(model:dict,scenario_rows:list[dict],native:dict|None)->dict:
    need(type(model) is dict and
         model.get("schema")=="ZrotGeneralRotationSourceHypothesisIRV1" and
         model.get("policy")==POLICY and
         type(scenario_rows) is list and bool(scenario_rows),
         "PINNED_SOURCE_HYPOTHESIS_REQUIRED")
    graph=model["source_only_priority_graph"]
    lists=graph["lists"]
    need("default" in lists and type(graph.get("list_order")) is list
         and set(graph["list_order"])==set(lists),
         "SOURCE_LIST_GRAPH_NOT_COMPLETE")
    ordered={}
    for name in graph["list_order"]:
        ordered[name]=[row_export(r,i,name) for i,r in enumerate(lists[name])]
    count=sum(map(len,ordered.values()))
    need(count==model["coverage"]["source_action_rows"],
         "SOURCE_APL_ROW_NOT_PRESERVED")
    context_outputs=[]
    ids=set()
    for scenario in scenario_rows:
        sid=scenario["scenario_id"]
        need(type(sid) is str and KEY.fullmatch(sid)
             and sid not in ids and
             scenario.get("spec_key")==model["spec_key"],
             "SPEC_SCENARIO_DUPLICATE_OR_WRONG_OWNER")
        ids.add(sid)
        result=control_guard_frontier(
            model,scenario["source_facts"],scenario["target_count"])
        # The frontier is only source IF evaluation; even a TRUE source guard
        # does not prove that any earlier non-control row was NOT_READY.
        controls=result["source_control_guard_frontier"]
        context_outputs.append({
            "name":sid,
            "assumed_target_count":scenario["target_count"],
            "source_facts_explicitly_assumed":scenario["source_facts"],
            "source_root_controls_in_original_order":controls,
            "source_guard_true_destinations_not_ACTUAL_entered":[
                c["source_destination"] for c in controls
                if c["source_if_under_explicit_synthetic_facts"]=="TRUE"],
            "source_guard_unknown_possible_destinations":[
                c["source_destination"] for c in controls
                if c["source_if_under_explicit_synthetic_facts"]=="UNKNOWN"],
            "source_guard_false_control_destinations":[
                c["source_destination"] for c in controls
                if c["source_if_under_explicit_synthetic_facts"]=="FALSE"],
            "source_guard_is_NOT_full_control_readiness":True,
            "actual_list_entry":"UNKNOWN",
        })
    examples=[]
    if native is not None:
        need(type(native) is dict and
             native.get("spec_key")==model["spec_key"] and
             native.get("class_key")==model["class_key"] and
             native.get("original_profile_git_blob")==model["source_git_blob"] and
             native.get("original_APL_rows")==count and
             native.get("original_APL_list_count")==len(ordered) and
             native.get("original_selection_row_and_exact_PRE")=="UNKNOWN" and
             native.get("opener_end_condition")=="UNKNOWN" and
             native.get("conditional_gameplay_priority_proven") is False,
             "NATIVE_PORTFOLIO_NOT_MATCHING_EXACT_SOURCE_SPEC")
        for case in native["actual_native_source_token_opening_samples"]:
            sample=case.get("native_first_10s_actions_NOT_necessarily_opener")
            need(type(sample) is list and
                 len(sample)==case.get("native_first_10s_samples_NOT_opener_end_count")
                 and len(sample)>0 and
                 case.get("first_10s_sample_window_is_NOT_phase_boundary") is True and
                 case.get("original_cpp_source_row_attribution")=="UNKNOWN" and
                 case.get("competing_full_READY")=="UNKNOWN",
                 "NATIVE_FIRST_WINDOW_NOT_AN_OPENER_CERTIFICATE")
            examples.append({
                "target_count":case["targets"],
                "first_10s_observed_original_SimC_action_tokens":[
                    {"at_ms":r["original_simc_ms"],
                     "action":r["native_action_token"],
                     "source_row":"UNKNOWN"}
                    for r in sample],
                "all_30s_native_actions_observed":case["actual_native_sample_actions"],
                "opener_end_condition":"UNKNOWN",
                "player_cast_or_source_row_verdict":"UNKNOWN",
            })
    return {
        "schema":SCHEMA,
        "policy_id":POLICY,
        "spec_key":model["spec_key"],
        "class_key":model["class_key"],
        "source_profile_git_blob":model["source_git_blob"],
        "source_profile_sha256":model["profile_sha256"],
        "source_APL_rows_preserved":count,
        "source_action_lists_preserved":len(ordered),
        "general_rotation":{
            "precombat_source_plan_NOT_combat_opener":
                ordered.get("precombat",[]),
            "priority_entry_list":"default",
            "all_source_ordered_IF_ELSE_priority_lists":ordered,
            "all_source_LIST_call_run_edges":graph["edges"],
            "source_variable_definition_sites":graph["source_variable_sites"],
            "contextual_ST_2T_AOE_build_source_routes":context_outputs,
        },
        "opener":{
            "source_precombat_candidates_NOT_canonical_opener":
                len(ordered.get("precombat",[])),
            "actual_original_SimC_first_10s_action_samples_NOT_opener_boundary":
                examples,
            "source_opener_end_condition":"UNKNOWN",
            "observed_First_10s_is_NOT_phase_end":True,
        },
        "proof":{
            "source_APL_order_and_conditions":"PINNED_SOURCE",
            "scenario_conditions":"SYNTHETIC_SOURCE_FACTS",
            "native_samples":"PINNED_OTHER_RUNS" if examples else "NOT_SUPPLIED",
            "actual_native_SOURCE_selected_row":"UNKNOWN",
            "strict_actual_same_root_PRE":"UNKNOWN",
            "preceding_action_FULL_READY":"UNKNOWN",
            "source_order_priority_is_not_current_Retail_optimality":True,
            "independent_WCL_blind_holdout":"NOT_PERFORMED_FOR_THIS_EXPORT",
            "current_Retail_priority_verified":False,
            "dummy_user_error_verdict":"UNKNOWN",
            "MAIN_promoted":False,
        },
    }

def pretty_cell(value:object)->str:
    return str(value).replace("|","\\|").replace("\n"," ")

def render_markdown(spec:dict)->str:
    need(spec.get("schema")==SCHEMA and
         spec["proof"]["current_Retail_priority_verified"] is False,
         "NON_HYPOTHETICAL_MODEL_CANNOT_RENDER_AS_SOURCE_DRAFT")
    g=spec["general_rotation"]
    lines=[
        "# General Rotation 연구 초안 — `"+spec["spec_key"]+"`",
        "",
        "> 이 문서는 고정 SimC 원본 APL의 **조건부 우선순위 가설**입니다.",
        "> **실전 최적성·현재 Retail 패치·전체 READY·허수아비 오답 판정은 검증되지 않았습니다.**",
        "> 조건식이 TRUE여도 앞선 행동이나 전체 사용 가능 여부 때문에 실제 선택이 달라질 수 있습니다.",
        "",
        "## 오프닝: 확정된 것과 미확정된 것",
        "",
        "**전투 전(precombat) 원본 소스 순서** — 실제 피해 오프닝 시전 순서가 아닙니다:",
        ""
    ]
    for row in g["precombat_source_plan_NOT_combat_opener"]:
        lines.append(f'- {row["rank_one_based"]}. `{row["source_action"]}`'
                     + (f' — IF `{row["if_original"]}`' if row["if_original"] else "")
                     + f' (원본 L{row["source_line"]})')
    lines.extend(["","**원본 Native 전투 시작 직후 행동 표본** — 처음 10초는 임의 관측 구간이며 오프닝 종료 기준이 아닙니다:",""])
    if spec["opener"]["actual_original_SimC_first_10s_action_samples_NOT_opener_boundary"]:
        for case in spec["opener"]["actual_original_SimC_first_10s_action_samples_NOT_opener_boundary"]:
            first=case["first_10s_observed_original_SimC_action_tokens"]
            summary=" → ".join("`"+r["action"]+"`" for r in first[:12])
            if len(first)>12:summary+=" → …"
            lines.append(f'- {case["target_count"]}타겟 (관측 {len(first)}건): {summary}')
    else:
        lines.append("- 원본 Native 표본 미제공 (SOURCE_ONLY)")
    lines.extend(["","**오프닝 → 일반 우선순위 전환:** UNKNOWN. 시간이나 처음 10초를 종료 조건으로 사용하지 않습니다.","",
                  "## 타겟 수·특성별 소스 진입 조건 (가상 입력)",
                  "","여기서 TRUE는 해당 *소스 IF*만 참이라는 의미입니다. 실제 리스트 진입·스킬 READY는 아닙니다.",""])
    for case in g["contextual_ST_2T_AOE_build_source_routes"]:
        lines.extend([f'### {case["name"]}: {case["assumed_target_count"]}타겟',
                      "","가정 상태: "+", ".join(
                        f'`{k}={v}`' for k,v in sorted(
                            case["source_facts_explicitly_assumed"].items())),
                      "","| 원본 루트 우선순위 | CALL / RUN | 조건 결과 |","|---|---|---|"])
        for control in case["source_root_controls_in_original_order"]:
            lines.append(f'| {control["source_rank_one_based"]} | '
                         f'{control["source_control"]} `{control["source_destination"]}` | '
                         f'{control["source_if_under_explicit_synthetic_facts"]} |')
        lines.append("")
    lines.extend(["## 전체 General Rotation 소스 우선순위 (손실 없는 모든 APL 행)","",
                  "각 리스트의 번호는 **해당 리스트 내부 우선순위**입니다. CALL은 자식 결과 후 복귀할 수 있지만 RUN은 제어 이관입니다. "
                  "다른 리스트의 번호를 합쳐 전역 우선순위로 해석하지 않습니다.",""])
    for name,rows in g["all_source_ordered_IF_ELSE_priority_lists"].items():
        lines.extend([f"### `{name}` ({len(rows)}행)","","| 우선순위 | 행동 / 제어 | 조건 (원본) | 원본 위치 |",
                      "|---:|---|---|---|"])
        for r in rows:
            item=("`"+r["source_action"]+"`")
            if r["behavior"] in {"CALL","RUN","SWAP_UNSUPPORTED"}:
                item=r["behavior"]+" `"+str(r["control_destination"])+"`"
            elif r["behavior"]=="VARIABLE":
                item="VARIABLE `"+r["source_action"]+"` (시전 아님)"
            elif r["behavior"]=="SIDE_EFFECT_SOURCE_MODEL_UNVERIFIED":
                item+=" (실제 시전 여부 미확인)"
            cond=("`"+pretty_cell(r["if_original"])+"`"
                  if r["if_original"] is not None else "IF 없음")
            extra=[x for x in r["all_compiled_source_expression_fields"] if x!="if"]
            if extra: cond+="; 기타 표현식: "+", ".join("`"+x+"`" for x in extra)
            lines.append(f'| {r["rank_one_based"]} | {item} | {cond} | L{r["source_line"]} |')
        lines.extend(["","<details>","<summary>원본 옵션·상태에 관한 주의</summary>","",
                      "표에 표시되지 않은 스킬 옵션·비표현식 속성은 JSON 모델의 `source_text_exact`에 원본 그대로 남겨두었습니다. "
                      "조건이 참이어도 스킬의 전체 사용 가능성, 실제 실행 및 올바른 사용자 시전이라는 뜻은 아닙니다.",
                      "","</details>",""])
    lines.extend(["## 증거와 미완료 판정","",
                  "- SOURCE: 원본 프로필 Git blob 및 모든 APL 행·순서·표현식 보존.",
                  "- NATIVE: 기록된 행동 이름·시각은 해당 SimC 실행의 표본. 정확한 소스 선택 행과 Strict PRE는 미확인.",
                  "- 아직 필요한 것: 오프닝 종료의 원본 상태 전이, 앞선 후보의 개별 READY/NOT_READY, 독립 WCL blind 고정 후보와 postlock 대조.",
                  "- 실제 허수아비 사용자의 실수: **UNKNOWN**.",""])
    return "\n".join(lines)

def run(source_root:Path,manifest_path:Path,scenario_path:Path,
        portfolio_path:Path|None=None,portfolio_hash:str|None=None)->dict:
    need((portfolio_path is None)==(portfolio_hash is None),
         "NATIVE_PORTFOLIO_PATH_AND_SHA_MUST_BE_SUPPLIED_TOGETHER")
    manifest=load_manifest(manifest_path)
    matrix=json.loads(scenario_path.read_bytes())
    root=source_root.resolve(strict=True)
    revision=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                            check=True,capture_output=True,text=True).stdout.strip()
    need(revision==manifest["official_simc_commit"]==REV and
         matrix.get("schema")==MATRIX_SCHEMA and
         matrix.get("source_revision")==REV and
         matrix.get("policy_id")==POLICY and
         matrix.get("semantic_provenance")==
           "EXPLICIT_SYNTHETIC_SOURCE_FACTS_NOT_NATIVE_PRE_NOT_WCL_OBSERVATION"
         and type(matrix.get("scenarios")) is list,
         "PINNED_SOURCE_OR_GUARD_MATRIX_CONTRACT_DRIFT")
    portfolios={}
    if portfolio_path is not None:
        need(type(portfolio_hash) is str and HEX64.fullmatch(portfolio_hash),
             "UNPINNED_NATIVE_PORTFOLIO_SHA256_REQUIRED")
        raw=portfolio_path.read_bytes()
        need(sha256(raw).hexdigest()==portfolio_hash,
             "ORIGINAL_NATIVE_PORTFOLIO_SHA256_MISMATCH")
        portfolio=json.loads(raw)
        need(portfolio.get("schema")==NATIVE_SCHEMA and
             portfolio.get("policy_id")==POLICY and
             portfolio.get("pinned_original_simc_revision")==REV and
             portfolio.get("original_research_runs_have_distinct_provenance") is True and
             portfolio.get("original_selected_APL_rows_still_NOT_proven_from_tokens") is True and
             portfolio.get("opener_exit_condition")=="UNKNOWN" and
             portfolio.get("full_simultaneously_READY_priorities_proven")==0 and
             portfolio.get("WCL_blind_candidate_semantics_injected") is False,
             "EXTERNAL_NATIVE_PORTFOLIO_UNTRUSTED_OR_OVERCLAIMS")
        lst=portfolio.get("source_model_with_native_sample_cohort_boundaries")
        need(type(lst) is list and len(lst)==len(manifest["profiles"]),
             "PORTFOLIO_PROFILE_COVERAGE_DRIFT")
        portfolios={m["spec_key"]:m for m in lst}
        need(len(portfolios)==len(lst),"DUPLICATE_NATIVE_SPEC_PORTFOLIO")
    output={}
    expected=set()
    for info in manifest["profiles"]:
        key=info["key"]
        expected.add(key)
        raw=(root/info["profile"]).resolve(strict=True)
        need(raw.is_relative_to(root),"ORIGINAL_SOURCE_PROFILE_PATH_ESCAPE")
        data=raw.read_bytes()
        need(git_blob(data)==info["git_blob"],
             "SOURCE_PROFILE_GIT_BLOB_DRIFT")
        source=compile_profile(data,info)
        # Reuse full source E2E compiler as a consistency oracle. Do not
        # implement an alternative parser or source-list ordering here.
        e2e=compile_spec(data,info,None)
        need(e2e["source_APL_row_count"]==source["coverage"]["source_action_rows"] and
             len(e2e["conditioned_opener_and_priority"]["all_ordered_source_IF_ELSE_lists"])==
                source["coverage"]["action_lists"] and
             e2e["simc_native_observed_source_selection_cases"]=={} and
             e2e["opener_first_actual_player_cast"]=="UNKNOWN",
             "EXISTING_TYPED_SOURCE_IR_AND_E2E_DISAGREE")
        scenarios=[s for s in matrix["scenarios"] if s.get("spec_key")==key]
        need(scenarios,"SPECIALIZATION_TARGET_BUILD_COVERAGE_MISSING")
        output[key]=render_spec(source,scenarios,portfolios.get(key))
    need(set(portfolios).issubset(output) and
         set(output)==expected and len(output)==len(manifest["profiles"]),
         "CROSS_CLASS_SOURCE_MODEL_PORTFOLIO_INCOMPLETE")
    return output

def selftest()->dict:
    sample=(b"actions.precombat=spell_pre\n"
            b"actions=call_action_list,name=single,if=active_enemies=1\n"
            b"actions+=/run_action_list,name=aoe,if=active_enemies>1\n"
            b"actions.single=spell_one,if=buff.test.up\n"
            b"actions.aoe=spell_many\n")
    m={"key":"fake_spec","class_key":"fiction",
       "git_blob":git_blob(sample)}
    source=compile_profile(sample,m)
    cases=[{"spec_key":"fake_spec","scenario_id":"single",
            "target_count":1,"source_facts":{"active_enemies":1}},
           {"spec_key":"fake_spec","scenario_id":"aoe",
            "target_count":3,"source_facts":{"active_enemies":3}}]
    result=render_spec(source,cases,None)
    need(result["source_APL_rows_preserved"]==5 and
         result["source_action_lists_preserved"]==4 and
         len(result["general_rotation"]["precombat_source_plan_NOT_combat_opener"])==1 and
         result["general_rotation"]["contextual_ST_2T_AOE_build_source_routes"][0][
             "source_guard_true_destinations_not_ACTUAL_entered"]==["single"] and
         result["general_rotation"]["contextual_ST_2T_AOE_build_source_routes"][1][
             "source_guard_true_destinations_not_ACTUAL_entered"]==["aoe"] and
         result["opener"]["source_opener_end_condition"]=="UNKNOWN" and
         "SOURCE" in render_markdown(result),
         "GENERIC_SOURCE_TO_READABLE_SPEC_ROTATION_FAILED")
    rejected=0
    bad=json.loads(json.dumps(source))
    bad["source_only_priority_graph"]["lists"]["single"][0]["expected_ready"]="READY"
    try:render_spec(bad,cases,None)
    except ExportError:rejected+=1
    else:raise AssertionError("IMPUTED_READY_ACCEPTED")
    bad2=json.loads(json.dumps(source))
    bad2["source_only_priority_graph"]["lists"]["single"][0]["source_text"]="TAMPERED"
    try:render_spec(bad2,cases,None)
    except ExportError:rejected+=1
    else:raise AssertionError("SOURCE_TEXT_TAMPER_ACCEPTED")
    return {"status":"PASS_GENERIC_READABLE_SPEC_EXPORT",
            "synthetic_profile_rows":5,"synthetic_spec_contexts":2,
            "fail_closed_negative_cases":rejected,
            "ready_imputed":False,"native_observation_invented":False,
            "opener_end_imputed":False}

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root",type=Path)
    parser.add_argument("--manifest",type=Path)
    parser.add_argument("--scenarios",type=Path)
    parser.add_argument("--portfolio",type=Path)
    parser.add_argument("--portfolio-sha256")
    parser.add_argument("--out-dir",type=Path)
    a=parser.parse_args()
    if not any((a.source_root,a.manifest,a.scenarios,a.portfolio)):
        data=selftest()
        print(canonical(data).decode(),end="")
        return
    if not all((a.source_root,a.manifest,a.scenarios,a.out_dir)):
        parser.error("source-root manifest scenarios out-dir required")
    data=run(a.source_root,a.manifest,a.scenarios,
             a.portfolio,a.portfolio_sha256)
    a.out_dir.mkdir(parents=True,exist_ok=True)
    files={}
    for key,spec in data.items():
        encoded=canonical(spec)
        markdown=render_markdown(spec).encode("utf-8")
        file_json=a.out_dir/(key+".json")
        file_md=a.out_dir/(key+".md")
        need(not file_json.exists() and not file_md.exists(),
             "EXISTING_MODEL_ARTIFACT_MUST_NOT_BE_OVERWRITTEN")
        file_json.write_bytes(encoded)
        file_md.write_bytes(markdown)
        files[key]={"json_sha256":sha256(encoded).hexdigest(),
                    "md_sha256":sha256(markdown).hexdigest(),
                    "source_APL_rows":spec["source_APL_rows_preserved"],
                    "target_build_scenarios":len(spec["general_rotation"][
                        "contextual_ST_2T_AOE_build_source_routes"]),
                    "original_Native_10s_cases":len(spec["opener"][
                        "actual_original_SimC_first_10s_action_samples_NOT_opener_boundary"])}
    manifest={"schema":INDEX_SCHEMA,"policy":POLICY,
              "source_revision":REV,
              "files":files,
              "all_specs":len(files),
              "total_source_APL_rows":sum(x["source_APL_rows"] for x in files.values()),
              "source_APL_only_not_validated_gameplay":True,
              "opener_end":"UNKNOWN",
              "actual_player_training_error":"UNKNOWN"}
    index=a.out_dir/"INDEX.json"
    need(not index.exists(),"EXISTING_MODEL_INDEX_MUST_NOT_BE_OVERWRITTEN")
    index.write_bytes(canonical(manifest))
    print(json.dumps({"status":"MODELS_WRITTEN",
                      "index_sha256":sha256(index.read_bytes()).hexdigest(),
                      **manifest},ensure_ascii=False,sort_keys=True))

if __name__=="__main__":main()
