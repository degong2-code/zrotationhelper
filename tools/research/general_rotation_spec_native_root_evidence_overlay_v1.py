#!/usr/bin/env python3
"""Attach exact original SimC selected-source PRE witnesses to one spec model.

Input is an independently SHA256-pinned General Rotation per-spec source draft,
plus ONE OR MORE independently SHA256-pinned selected-source Original Native
same-run PRE summaries. Overlay makes source-row selected/IF claims only for
their exact original root (target, original call ID, pointer-derived original
dispatch, timestamp). It NEVER projects source-row selection to a future
player choice, an unavailable alternative, or an opener termination.

This is a generic engine: no Shaman, spec, spell, talent or boss rules.
No-argument PyCharm run is a safe synthetic/fail-closed test.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import canonical,evaluate_ast,truth,git_blob
from general_rotation_source_hypothesis_ir_v1 import compile_profile
from general_rotation_spec_model_export_v1 import render_spec,SCHEMA as DRAFT_SCHEMA

SCHEMA="ZrotGeneralRotationSpecEvidenceBoundNativeSelectedRootSuccessorV1"
NATIVE="ZrotOriginalSimCSelectedSameCallExtraPRESourceIFReplayV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SHA=re.compile(r"[a-f0-9]{64}\Z")

class OverlayError(ValueError):pass

def need(ok,why):
    if not ok:raise OverlayError(why)

def _load(path:Path,expected_sha:str)->dict:
    need(type(expected_sha) is str and SHA.fullmatch(expected_sha) is not None,
         "EXPLICIT_SHA256_PIN_REQUIRED")
    raw=path.read_bytes()
    need(sha256(raw).hexdigest()==expected_sha,
         "EXACT_SAME_COHORT_SOURCE_ARTIFACT_HASH_MISMATCH")
    data=json.loads(raw)
    need(type(data) is dict,"INVALID_SIGNED_RESEARCH_DOCUMENT")
    return data

def overlay(draft:dict,roots:list[tuple[dict,str]])->dict:
    need(type(draft) is dict and draft.get("schema")==DRAFT_SCHEMA and
         draft.get("policy_id")==POLICY and
         draft["proof"].get("current_Retail_priority_verified") is False and
         draft["proof"].get("strict_actual_same_root_PRE")=="UNKNOWN" and
         draft["proof"].get("preceding_action_FULL_READY")=="UNKNOWN" and
         type(roots) is list and roots,
         "SOURCE_DRAFT_OR_PRE_PROOF_SCOPE_OVERCLAIMED")
    out=deepcopy(draft)
    g=out["general_rotation"]["all_source_ordered_IF_ELSE_priority_lists"]
    original_count=out["source_APL_rows_preserved"]
    need(original_count==sum(map(len,g.values())),
         "SOURCE_APL_ROW_COUNT_CHANGED")
    for name,rows in g.items():
        for i,r in enumerate(rows,1):
            need(r["source_list"]==name and r["rank_one_based"]==i and
                 r["positive_native_READY_certified"]=="UNKNOWN" and
                 r["WoW_expected_cast"]=="UNKNOWN",
                 "SYNTHETIC_OR_NATIVE_READY_TAMPERED")
    cases=[]
    allroots=set()
    row_counts=Counter()
    native_if_counts=Counter()
    for proof,proof_sha in roots:
        need(type(proof_sha) is str and SHA.fullmatch(proof_sha) is not None and
             type(proof) is dict and proof.get("schema")==NATIVE and
             proof.get("policy_id")==POLICY and
             proof.get("source_spec")==out["spec_key"] and
             proof.get("source_class")==out["class_key"] and
             proof.get("original_profile_blob")==out["source_profile_git_blob"] and
             type(proof.get("targets")) is int and 1<=proof["targets"]<=40 and
             type(proof.get("selected_source_IF_samples")) is list and
             proof.get("full_physical_READY_proven")==0 and
             proof.get("competitor_ready_proven")==0 and
             proof.get("dummy_wrong_cast")=="UNKNOWN" and
             proof.get("opener_end")=="UNKNOWN" and
             proof.get("source_if_comparator_not_replay_input") is True and
             proof.get("original_selected_direct_foreground")==
               len(proof["selected_source_IF_samples"]),
             "NATIVE_SELECTED_SOURCE_ROOT_CONTRACT_VIOLATED")
        n=proof["targets"]
        sample=[]
        for selected in proof["selected_source_IF_samples"]:
            name=selected.get("source_list")
            rank=selected.get("source_rank")
            t=selected.get("t_ms")
            call=selected.get("original_selected_call_id")
            dispatch=selected.get("original_dispatch_token")
            need(name in g and type(rank) is int and 1<=rank<=len(g[name]) and
                 type(t) is int and t>=0 and
                 type(call) is int and call>0 and
                 type(dispatch) is int and dispatch>0 and
                 type(selected.get("source_action")) is str and
                 type(selected.get("original_PRE_fields")) is dict and
                 selected.get("original_physical_READY")=="UNKNOWN" and
                 selected.get("competitor_priority")=="UNKNOWN",
                 "SELECTED_SOURCE_ROOT_ID_OR_PRE_TAMPERED")
            key=(n,call,dispatch)
            need(key not in allroots,"CROSS_COHORT_OR_DUPLICATE_SOURCE_ROOT")
            allroots.add(key)
            row=g[name][rank-1]
            need(row["source_action"]==selected["source_action"] and
                 row["source_sha256"]==selected["source_row_sha256"],
                 "ORIGINAL_APL_ROW_NOT_EXACT_SELECTED_ROOT")
            fields=row["all_compiled_source_expression_fields"]
            expr=fields.get("if")
            native=selected.get("original_native_IF_comparator")
            category=selected.get("original_SOURCE_IF_evidence")
            known=selected.get("original_source_IF_independent_truth")
            facts=selected["original_PRE_fields"]
            need(all(type(x) is str and type(v) in (float,int)
                     for x,v in facts.items()),
                 "ORIGINAL_PRE_FACT_NOT_NUMERIC")
            if expr is None:
                need(known=="UNKNOWN" and native=="NOT_REACHED" and
                     category=="SOURCE_APL_NO_EXPLICIT_IF_NOT_READY_PROOF",
                     "NO_IF_ROW_FALSE_SOURCE_TRUTH")
                state="NO_IF"
            else:
                actual=truth(evaluate_ast(expr["typed_AST"],facts))
                state="UNKNOWN" if actual is None else "TRUE" if actual else "FALSE"
                need(state==known and state!="FALSE",
                     "ORIGINAL_SELECTED_ROW_SOURCE_IF_NOT_TRUE")
                if native=="TRUE":
                    # Native's comparator is a bounded POST witness, not
                    # an independent source-state fact. When facts are absent,
                    # keep the source-AST replay UNKNOWN even if Native TRUE.
                    if state=="TRUE":
                        need(category==
                             "SOURCE_IF_EXTRA_ORIGINAL_PRE_AST_MATCH_NATIVE_COMPARATOR",
                             "KNOWN_SOURCE_PRE_NOT_INDEPENDENTLY_MATCHED")
                        state="TRUE_MATCH_NATIVE"
                    else:
                        need(state=="UNKNOWN" and category==
                             "UNKNOWN_SOURCE_IF_EXTRA_PRE_INCOMPLETE",
                             "NATIVE_POST_USED_TO_FILL_MISSING_PRE")
                        state="UNKNOWN"
                else:
                    need(native=="NOT_REACHED",
                         "NATIVE_COMPARATOR_FALSE_FOR_SELECTED_SOURCE")
                    if state=="TRUE":
                        need(category==
                             "SOURCE_IF_EXTRA_ORIGINAL_PRE_AST_KNOWN_NO_NATIVE_COMPARATOR",
                             "KNOWN_PRE_WITHOUT_COMPARATOR_MISLABELED")
                        state="TRUE_NO_NATIVE_COMPARATOR"
                    else:
                        need(state=="UNKNOWN" and category==
                             "UNKNOWN_SOURCE_IF_EXTRA_PRE_INCOMPLETE",
                             "MISSING_PRE_WITHOUT_COMPARATOR_MISLABELED")
                        state="UNKNOWN"
            native_if_counts[state]+=1
            row_counts[(name,rank)]+=1
            if t<10000:
                sample.append({
                    "original_SimC_time_ms":t,
                    "original_selected_source_list":name,
                    "original_selected_source_rank":rank,
                    "original_source_action":row["source_action"],
                    "original_source_row_sha256":row["source_sha256"],
                    "source_selected_root_call_id":call,
                    "source_IF_evidence_at_this_root":state,
                    "original_PRE_reproduced_exactly_at_this_root":facts,
                    "original_native_full_READINESS":"UNKNOWN",
                    "all_prior_competing_source_rows_excluded":"UNKNOWN",
                    "opener_end_event_at_this_time":"UNKNOWN",
                    "WoW_expected_spell":"UNKNOWN"
                })
        need(sample,"NO_INITIAL_NATIVE_SOURCE_SELECTED_ROOTS")
        cases.append({
            "observed_target_count":n,
            "original_native_source_evidence_sha256":proof_sha,
            "root_selected_count":len(proof["selected_source_IF_samples"]),
            "first10s_exact_source_selected_roots_NOT_opener_end":sample,
            "selected_root_source_rows_certain":True,
            "global_competing_READY_certified":False
        })
    need(len({c["observed_target_count"] for c in cases})==len(cases),
         "DUPLICATE_TARGET_RUNS_NO_INDEPENDENT_PROVENANCE")
    for (name,rank),times in row_counts.items():
        r=g[name][rank-1]
        r["exact_original_native_selected_source_roots_observed"]=times
        r["source_selected_in_specific_SimC_run_only"]=True
        r["positive_native_READY_certified"]="UNKNOWN"
        r["priority_over_other_simultaneously_available_actions"]="SOURCE_APL_HYPOTHESIS_ONLY"
        r["WoW_expected_cast"]="UNKNOWN"
    need(sum(map(len,g.values()))==original_count,
         "MODEL_SOURCE_ROW_COUNT_CHANGED_DURING_OVERLAY")
    out["original_selected_root_evidence_successor"]={
        "schema":SCHEMA,
        "actual_source_selected_direct_count":sum(x["root_selected_count"] for x in cases),
        "actual_source_selected_initial_10s_count":sum(
            len(x["first10s_exact_source_selected_roots_NOT_opener_end"])
            for x in cases),
        "condition_verdicts_at_exact_native_roots":dict(sorted(native_if_counts.items())),
        "per_target_cases":cases,
        "recorded_source_selected_row_and_partial_PRE":True,
        "same_native_action_ready_METHOD_called_without_extra_instrument_calls":True,
        "all_remaining_nonobserved_potential_source_actions_NOT_READY":"UNKNOWN",
        "physical_ready_all_competitors":"UNKNOWN",
        "opener_end_transition":"UNKNOWN",
        "current_Retail_general_rotation_completed":False,
    }
    out["proof"]["actual_native_SOURCE_selected_row"]="VERIFIED_FOR_EXACT_ROOTS_ONLY"
    out["proof"]["strict_actual_same_root_PRE"]="SELECTED_SOURCE_FIELDS_ONLY"
    out["proof"]["preceding_action_FULL_READY"]="UNKNOWN"
    out["proof"]["current_Retail_priority_verified"]=False
    return out

def markdown_evidence(model:dict)->str:
    obj=model["original_selected_root_evidence_successor"]
    lines=[f'# `{model["spec_key"]}` — 원본 SimC 우선순위 근거 보강',
      "","> 이 문서는 기존 General Rotation 초안의 **정확한 선택 APL 행과 부분 PRE**를 추가 기록한다.",
      "> 원본 선택이 확인돼도 경쟁 스킬의 READY, 오프닝 종료와 현재 Retail 최적성을 증명하지 않는다.",
      "",
      f'원본 SELECT 직접 선택 {obj["actual_source_selected_direct_count"]}회, '
      f'첫 10초 중 {obj["actual_source_selected_initial_10s_count"]}회. '
      f'조건 판정 {obj["condition_verdicts_at_exact_native_roots"]}.',
      ""]
    for case in obj["per_target_cases"]:
        lines.extend([f'## {case["observed_target_count"]}타겟 — 원본 첫 10초 선택 소스',
                      "","| 시각(ms) | 선택 APL 리스트 / 순위 | 스킬 / 제어 | IF 증거 |",
                      "|---:|---|---|---|"])
        for r in case["first10s_exact_source_selected_roots_NOT_opener_end"][:30]:
            lines.append(f'| {r["original_SimC_time_ms"]} | '
                         f'`{r["original_selected_source_list"]}` '
                         f'#{r["original_selected_source_rank"]} | '
                         f'`{r["original_source_action"]}` | '
                         f'{r["source_IF_evidence_at_this_root"]} |')
        lines.extend(["","**근거:** 개별 SELECT 호출과 출력 행이 같은 원본 실행에 속함. "
                      "행동을 언제나 사용해야 한다거나 다른 선택이 실수라는 주장은 불가.",""])
    lines.extend(["## 아직 검증할 조건","",
        "- 오프닝 종료의 실제 상태 전이, 모든 앞선 후보의 물리적 READY/NOT_READY",
        "- 동일 특성·빌드와 현재 패치에서의 WCL blind 잠금 후 행동 대조",
        "- WoW 허수아비에서 해당 시점 상태 관측 가능 여부 및 오류 교정",
        "",
        "**최종 로테이션·사용자 실수 판정: UNKNOWN**.",""])
    return "\n".join(lines)

def selftest()->dict:
    sample=(b"actions=call_action_list,name=single,if=active_enemies=1\n"
            b"actions.single=spell_a,if=buff.test.up\n")
    src=compile_profile(sample,{"key":"fictional_spec","class_key":"fictional",
        "git_blob":git_blob(sample)})
    draft=render_spec(src,[{"spec_key":"fictional_spec","scenario_id":"single",
       "target_count":1,"source_facts":{"active_enemies":1}}],None)
    selected={"t_ms":210,"source_list":"single","source_rank":1,
       "original_selected_call_id":25,"original_dispatch_token":8,
       "source_action":"spell_a",
       "source_row_sha256":draft["general_rotation"][
             "all_source_ordered_IF_ELSE_priority_lists"]["single"][0]["source_sha256"],
       "original_PRE_fields":{"buff.test.up":1.0},
       "original_source_IF_independent_truth":"TRUE",
       "original_native_IF_comparator":"TRUE",
       "original_SOURCE_IF_evidence":
         "SOURCE_IF_EXTRA_ORIGINAL_PRE_AST_MATCH_NATIVE_COMPARATOR",
       "original_physical_READY":"UNKNOWN","competitor_priority":"UNKNOWN"}
    proof={"schema":NATIVE,"policy_id":POLICY,"source_spec":"fictional_spec",
       "source_class":"fictional","original_profile_blob":git_blob(sample),
       "targets":1,"selected_source_IF_samples":[selected],
       "original_selected_direct_foreground":1,"full_physical_READY_proven":0,
       "competitor_ready_proven":0,"dummy_wrong_cast":"UNKNOWN","opener_end":"UNKNOWN",
       "source_if_comparator_not_replay_input":True}
    out=overlay(draft,[(proof,"a"*64)])
    need(out["proof"]["actual_native_SOURCE_selected_row"]==
         "VERIFIED_FOR_EXACT_ROOTS_ONLY" and
         out["proof"]["preceding_action_FULL_READY"]=="UNKNOWN" and
         out["original_selected_root_evidence_successor"][
             "actual_source_selected_direct_count"]==1 and
         "spell_a" in markdown_evidence(out),
         "SOURCE_ROW_SELECTED_DID_NOT_UPDATE_RESEARCH_OUTPUT")
    negatives=0
    for field,value in [
        ("source_row_sha256","0"*64),
        ("original_native_IF_comparator","FALSE"),
        ("original_source_IF_independent_truth","FALSE"),
        ("original_physical_READY","READY")]:
        bad=deepcopy(proof)
        bad["selected_source_IF_samples"][0][field]=value
        try:overlay(draft,[(bad,"a"*64)])
        except OverlayError:negatives+=1
        else:raise AssertionError("UNTRUSTED_NATIVE_ROOT_PROMOTED")
    # The Native original IF may be TRUE while the independent source AST
    # cannot be reproduced from a smaller PRE field adapter. It stays UNKNOWN.
    incomplete=deepcopy(proof)
    incomplete["selected_source_IF_samples"][0]["original_PRE_fields"]={}
    incomplete["selected_source_IF_samples"][0]["original_source_IF_independent_truth"]="UNKNOWN"
    incomplete["selected_source_IF_samples"][0]["original_SOURCE_IF_evidence"]=(
        "UNKNOWN_SOURCE_IF_EXTRA_PRE_INCOMPLETE")
    uncertainty=overlay(draft,[(incomplete,"a"*64)])
    need(uncertainty["original_selected_root_evidence_successor"][
         "condition_verdicts_at_exact_native_roots"]=={"UNKNOWN":1},
         "UNOBSERVED_PRE_FILLED_FROM_NATIVE_POST_COMPARATOR")
    return {"status":"PASS_GENERIC_NATIVE_ROOT_SOURCE_EVIDENCE_OVERLAY",
       "positive_synthetic_roots":1,"unknown_native_comparator_preserved":1,
       "negative_rejected":negatives,
       "source_order_preserved":True,
       "physical_ready_proven":False,"current_Retail_optimality_proven":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--draft",type=Path)
    p.add_argument("--draft-sha256")
    p.add_argument("--native-root",type=Path,action="append",default=[])
    p.add_argument("--native-root-sha256",action="append",default=[])
    p.add_argument("--out",type=Path)
    p.add_argument("--markdown",type=Path)
    a=p.parse_args()
    if not any((a.draft,a.native_root,a.out,a.markdown,a.draft_sha256,
                a.native_root_sha256)):
        print(canonical(selftest()).decode(),end="")
        return
    if not (a.draft and a.draft_sha256 and a.out and a.markdown and
            len(a.native_root)==len(a.native_root_sha256)>=1):
        p.error("Pinned draft + per-native SHA root + both outputs required")
    draft=_load(a.draft,a.draft_sha256)
    roots=[(_load(f,h),h) for f,h in zip(a.native_root,a.native_root_sha256)]
    out=overlay(draft,roots)
    # Refuse silent overwrite to preserve immutable standalone model exports.
    for f in (a.out,a.markdown):
        if f.exists():raise OverlayError("REFUSE_EXISTING_RESEARCH_ARTIFACT_OVERWRITE")
        f.parent.mkdir(parents=True,exist_ok=True)
    encoded=canonical(out)
    md=markdown_evidence(out).encode()
    a.out.write_bytes(encoded)
    a.markdown.write_bytes(md)
    print(json.dumps({"status":"SOURCE_ROW_SELECTED_EVIDENCE_OVERLAY_WRITTEN",
          "sha256":sha256(encoded).hexdigest(),
          "markdown_sha256":sha256(md).hexdigest(),
          "spec":out["spec_key"],
          "real_source_select_count":out["original_selected_root_evidence_successor"][
              "actual_source_selected_direct_count"],
          "conditional_ready_complete":False},sort_keys=True))

if __name__=="__main__":main()
