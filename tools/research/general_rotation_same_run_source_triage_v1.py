#!/usr/bin/env python3
"""Offline, spec-neutral triage of original SimC return/emitter evidence.

Replays hash-pinned per-case output from an already completed original SimC
run against the official, pinned APL profiles. Reuses the typed APL parser.
It identifies which *source-state and dispatch evidence* is missing at
first-window decisions. NEVER upgrades a temporal pointer match into a
causal execution, physical READY, optimality or a dummy-player error.

No arguments: standalone offline synthetic regressions (PyCharm safe).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

from general_rotation_same_run_return_emitter_v1 import (
    SCHEMA as CASE_SCHEMA, POLICY, SIMC_COMMIT, LinkError,
)
from simc_apl_semantic_ir_v2 import (
    parse_profile, canonical, git_blob, AplError,
)

SCHEMA="ZrotGeneralRotationPinnedSameRunSourceBoundaryTriageV1"
RECEIPT_SCHEMA="ZrotGeneralRotationSameRunReturnEmitterBoundaryReceiptV1"
STATUS={
    "UNIQUE_SAME_RUN_RETURN_POINTER_ROW_TEMPORAL_WITNESS",
    "UNKNOWN_MULTIPLE_ROOT_RETURNS",
    "UNKNOWN_NO_ROOT_RETURN_BEFORE_EMITTER",
    "UNKNOWN_SOURCE_IDENTITY_MISMATCH",
    "UNKNOWN_EMITTER_NO_SOURCE_SIGNATURE",
}
EXPECTED_CASE_FIELDS={
    "spec","targets","profile_path","report_path",
}
HEX=set("0123456789abcdef")


class TriageError(ValueError):
    pass


def need(ok:bool,label:str)->None:
    if not ok:
        raise TriageError(label)


def digest(b:bytes)->str:
    return sha256(b).hexdigest()


def _duplicate_free(pairs):
    result={}
    for key,value in pairs:
        need(key not in result,"DUPLICATE_JSON_KEY")
        result[key]=value
    return result


def _load(path:Path)->tuple[dict,bytes]:
    need(path.is_file() and not path.is_symlink(),"INPUT_FILE_MISSING_OR_SYMLINK")
    raw=path.read_bytes()
    need(0<len(raw)<8_000_000,"INPUT_BYTES_MISSING_OR_EXCESSIVE")
    value=json.loads(raw,object_pairs_hook=_duplicate_free)
    need(isinstance(value,dict),"INPUT_JSON_NOT_OBJECT")
    return value,raw


def _sha_claim(value):
    return type(value) is str and len(value)==64 and all(c in HEX for c in value)


def _original_identity_receipt(receipt:dict)->list[dict]:
    need(isinstance(receipt,dict) and
         receipt.get("schema")==RECEIPT_SCHEMA and
         receipt.get("policy_id")==POLICY and
         receipt.get("source_simc_commit")==SIMC_COMMIT,
         "WRONG_PINNED_ORIGINAL_SOURCE_RECEIPT")
    v=receipt.get("validation")
    need(isinstance(v,dict) and
         v.get("final_run_id")==42581326058 and
         v.get("final_run_status")=="completed" and
         v.get("final_run_conclusion")=="success" and
         v.get("jobs_total")==v.get("jobs_success")==3 and
         v.get("native_official_cpp_build")=="PASS" and
         v.get("original_JSON2_action_order_time_id_ordinal_parity")=="149/149" and
         v.get("actual_source_row_selection_to_emission_causality_proven") is False and
         v.get("current_general_rotation_full_ready_proven")==0 and
         v.get("WCL_current_IR_holdout")=="NOT_RUN" and
         v.get("actual_target_dummy_user_error_verdict")=="UNKNOWN",
         "ORIGINAL_CI_OBSERVATION_SCOPE_INVALID")
    cases=v.get("cases")
    need(isinstance(cases,list) and len(cases)>=2,
         "MULTI_CASE_EVIDENCE_REQUIRED")
    need(v.get("original_emitter_records_total")==
         v.get("unique_temporal_same_run_pointer_row_candidates",0)+
         v.get("ambiguous_multi_root",0)+
         v.get("no_matching_root_before_emitter",0),
         "ORIGINAL_EMITTER_COUNT_NOT_PARTITIONED")
    return cases


def analyze(receipt:dict,
            profiles:dict[str,bytes],
            reports:dict[tuple[str,int],tuple[dict,bytes]],
            *,window_ms:int=10000)->dict:
    need(type(window_ms) is int and 1000<=window_ms<=30000,
         "FIRST_WINDOW_BUDGET_INVALID")
    declarations=_original_identity_receipt(receipt)
    source={}
    for spec,profile in profiles.items():
        need(type(spec) is str and bool(spec) and isinstance(profile,bytes),
             "SOURCE_SPEC_PROFILE_BYTES_INVALID")
        try:
            source[spec]=parse_profile(profile,require_source=False)
        except (AplError, UnicodeError) as exc:
            raise TriageError("PINNED_TYPED_APL_PARSE_FAILED") from exc
    keys=set()
    for case in declarations:
        need(isinstance(case,dict) and type(case.get("spec")) is str and
             type(case.get("targets")) is int and
             1<=case["targets"]<=8 and
             _sha_claim(case.get("report_sha256")),
             "DECLARED_CASE_IDENTITY_INVALID")
        key=(case["spec"],case["targets"])
        need(key not in keys,"DUPLICATE_DECLARED_CASE")
        keys.add(key)
    need(keys==set(reports) and set(profiles)=={k[0] for k in keys},
         "UNDECLARED_OR_MISSING_CASE_OR_PROFILE")

    results=[]
    all_counts=Counter()
    all_phases=Counter()
    all_conditions=Counter()
    all_phase_identity=Counter()
    window_if_symbols=Counter()
    window_source_rows=Counter()
    triage_rows=[]
    for decl in declarations:
        spec=decl["spec"];targets=decl["targets"]
        report,raw=reports[spec,targets]
        need(digest(raw)==decl["report_sha256"],
             "ORIGINAL_REPORT_SHA256_CHANGED")
        need(isinstance(report,dict) and report.get("schema")==CASE_SCHEMA
             and report.get("policy_id")==POLICY
             and report.get("selection_to_emission_causality_proven") is False
             and report.get("source_readiness_proven")==0
             and report.get("WCL_holdout")=="NOT_RUN"
             and report.get("dummy_error")=="UNKNOWN"
             and report.get("evidence_level")==
                 "SAME_RUN_TEMPORAL_SOURCE_IDENTITY_ONLY",
             "REPORT_CAUSAL_OR_READY_PROMOTION_OR_SCOPE_DRIFT")
        sample=report.get("sample")
        need(type(report.get("emitter_records")) is int and
             report["emitter_records"]>0 and
             isinstance(sample,list) and
             len(sample)==report["emitter_records"],
             "SOURCE_EMITTER_REPORT_TRUNCATED_NOT_EXHAUSTIVE")
        summary=Counter()
        phases=Counter()
        conditions=Counter()
        phase_identity=Counter()
        seen=set()
        p=source[spec]
        for event in sample:
            need(isinstance(event,dict) and
                 type(event.get("t_ms")) is int and event["t_ms"]>=0 and
                 event.get("emitter_phase") in ("P","C") and
                 type(event.get("emitter_ordinal")) is int and
                 event["emitter_ordinal"]>=0 and
                 isinstance(event.get("emitter_action"),str) and
                 bool(event["emitter_action"]) and
                 event.get("identity_status") in STATUS and
                 type(event.get("matching_root_return_count")) is int and
                 event["matching_root_return_count"]>=0 and
                 event.get("source_if_at_selection")=="UNKNOWN" and
                 event.get("complete_readiness")=="UNKNOWN" and
                 event.get("causal_scheduling")=="UNKNOWN" and
                 event.get("dummy_mistake")=="UNKNOWN",
                 "RAW_EMITTER_EVENT_SCOPE_MISSING_OR_PROMOTED")
            phase=event["emitter_phase"]
            ordinal=event["emitter_ordinal"]
            key=(phase,ordinal)
            need(key not in seen,"DUPLICATE_JSON2_ACTION_ORDINAL")
            seen.add(key)
            status=event["identity_status"]
            n=event["matching_root_return_count"]
            need((status.startswith("UNIQUE_") and n==1) or
                 (status=="UNKNOWN_MULTIPLE_ROOT_RETURNS" and n>1) or
                 (status in ("UNKNOWN_NO_ROOT_RETURN_BEFORE_EMITTER",
                             "UNKNOWN_EMITTER_NO_SOURCE_SIGNATURE") and n==0) or
                 status=="UNKNOWN_SOURCE_IDENTITY_MISMATCH",
                 "ROOT_RETURN_CARDINALITY_INCONSISTENT")
            owner=event.get("source_list")
            rank=event.get("source_row_rank")
            need(type(rank) is int and rank>=0
                 and ((rank==0 and owner=="-") or
                      (rank>0 and isinstance(owner,str) and owner in p["action_lists"]
                       and rank<=len(p["action_lists"][owner]))),
                 "PINNED_SOURCE_ROW_NOT_FOUND")
            source_row=p["action_lists"][owner][rank-1] if rank else None
            attr=(source_row["expression_fields"].get("if")
                  if source_row else None)
            symbols=attr["symbols"] if attr else []
            if source_row is None:
                condition="UNKNOWN_NO_SOURCE_ROW"
            elif attr:
                condition=("SOURCE_IF_REQUIRES_SAME_CALL_PRE"
                           if symbols else "CONSTANT_IF_NOT_READY_PROOF")
            else:
                condition="NO_EXPLICIT_IF_NOT_READY_PROOF"
            in_window=phase=="C" and event["t_ms"]<window_ms
            if status=="UNKNOWN_MULTIPLE_ROOT_RETURNS":
                next_capture="CAUSAL_SCHEDULE_DISPATCH_TOKEN_AMBIGUOUS_MULTI_ROOT"
            elif status=="UNKNOWN_NO_ROOT_RETURN_BEFORE_EMITTER":
                next_capture="ROOT_SELECTION_OBSERVATION_OR_EXEMPT_PATH_REQUIRED"
            elif status=="UNKNOWN_EMITTER_NO_SOURCE_SIGNATURE":
                next_capture="SOURCE_ROW_SIGNATURE_REQUIRED"
            elif status=="UNKNOWN_SOURCE_IDENTITY_MISMATCH":
                next_capture="MISMATCHED_RETURN_TO_EMITTER_SOURCE_IDENTITY"
            else:
                next_capture="CAUSAL_SCHEDULE_DISPATCH_TOKEN_NOT_PROVEN"
            summary[status]+=1
            phases[phase]+=1
            conditions[condition]+=1
            phase_identity[(phase,status)]+=1
            all_phase_identity[(phase,status)]+=1
            if in_window:
                for symbol in symbols:
                    window_if_symbols[symbol]+=1
                window_source_rows[(
                    spec,targets,owner,rank,
                    source_row["source_sha256"] if source_row else "-",
                    source_row["action"] if source_row else "-",
                    condition,status)]+=1
                triage_rows.append({
                    "source_spec":spec,"targets":targets,
                    "simc_emitter_t_ms":event["t_ms"],
                    "JSON2_emitter_ordinal":ordinal,
                    "source_profile_git_blob":p["source_git_blob_sha1"],
                    "source_list":owner,"source_rank":rank,
                    "source_row_sha256":(source_row["source_sha256"]
                                         if source_row else None),
                    "source_action":(source_row["action"]
                                     if source_row else None),
                    "behavior":(source_row["behavior"]
                                 if source_row else None),
                    "source_if":(attr["source"] if attr else None),
                    "missing_select_time_if_symbols":symbols,
                    "if_evidence_class":condition,
                    "identity_status":status,
                    "required_next_capture":next_capture,
                    "selection_time_if_truth":"UNKNOWN",
                    "selection_to_emission_causality":"UNKNOWN",
                    "physical_ready":"UNKNOWN",
                    "candidate_priority_vs_competitors":"UNKNOWN",
                    "WCL_blind_holdout":"NOT_RUN",
                    "user_dummy_error":"UNKNOWN",
                })
        need(dict(summary)==report.get("identity_counts") and
             sum(summary.values())==report["emitter_records"],
             "SOURCE_REPORT_COUNTS_NOT_REPLAYED")
        need(summary.get(
             "UNIQUE_SAME_RUN_RETURN_POINTER_ROW_TEMPORAL_WITNESS",0)
             ==decl["identity_candidates"] and
             summary.get("UNKNOWN_MULTIPLE_ROOT_RETURNS",0)
             ==decl["unknown_multi_root"] and
             summary.get("UNKNOWN_NO_ROOT_RETURN_BEFORE_EMITTER",0)
             ==decl["unknown_no_root"],
             "SOURCE_CASE_RECEIPT_AND_REPORT_DISAGREE")
        all_counts.update(summary)
        all_phases.update(phases)
        all_conditions.update(conditions)
        results.append({
            "source_spec":spec,"targets":targets,
            "source_profile_git_blob_sha1":p["source_git_blob_sha1"],
            "source_APL_rows":p["source_action_line_count"],
            "same_run_report_sha256":digest(raw),
            "emitter_records":len(sample),
            "identity_counts":dict(sorted(summary.items())),
            "phase_counts":dict(sorted(phases.items())),
            "phase_identity_counts":{
                phase:{status:phase_identity.get((phase,status),0)
                       for status in sorted(STATUS)
                       if phase_identity.get((phase,status),0)>0}
                for phase in ("P","C")},
            "source_if_observation_boundary_counts":
                dict(sorted(conditions.items())),
        })
    v=receipt["validation"]
    need(sum(all_counts.values())==v["original_emitter_records_total"] and
         all_counts.get("UNIQUE_SAME_RUN_RETURN_POINTER_ROW_TEMPORAL_WITNESS",0)
             ==v["unique_temporal_same_run_pointer_row_candidates"] and
         all_counts.get("UNKNOWN_MULTIPLE_ROOT_RETURNS",0)
             ==v["ambiguous_multi_root"] and
         all_counts.get("UNKNOWN_NO_ROOT_RETURN_BEFORE_EMITTER",0)
             ==v["no_matching_root_before_emitter"],
         "CROSS_SPEC_ORIGINAL_EMITTER_PROOF_COUNTS_DRIFT")
    # Deterministic triage order only. NOT gameplay action priority.
    triage_rows.sort(key=lambda r:(
        r["source_spec"],r["targets"],r["simc_emitter_t_ms"],
        r["JSON2_emitter_ordinal"]))
    focus=Counter()
    for item in triage_rows:
        focus[(item["identity_status"],
               item["required_next_capture"],
               item["if_evidence_class"])]+=1
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "source_SimC_commit":SIMC_COMMIT,
        "pinned_original_validation_run":v["final_run_id"],
        "source_boundary_evidence":"ORIGINAL_SAME_RUN_TEMPORAL_ONLY",
        "original_emitter_total":sum(all_counts.values()),
        "identity_counts":dict(sorted(all_counts.items())),
        "emitter_phase_counts":dict(sorted(all_phases.items())),
        "emitter_phase_identity_counts":{
            phase:{status:all_phase_identity.get((phase,status),0)
                   for status in sorted(STATUS)
                   if all_phase_identity.get((phase,status),0)>0}
            for phase in ("P","C")},
        "typed_source_IF_boundary_counts":dict(sorted(all_conditions.items())),
        "case_count":len(results),"cases":results,
        "first_window_ms_not_opener_end":window_ms,
        "first_window_combat_event_count":len(triage_rows),
        "first_window_evidence_gaps":triage_rows,
        "first_window_missing_IF_symbol_frequency":[
            {"symbol":symbol,"emitted_source_row_observations":count,
             "actual_original_select_PRE":"UNKNOWN"}
            for symbol,count in sorted(
                window_if_symbols.items(),key=lambda p:(-p[1],p[0]))],
        "first_window_source_row_capture_focus":[
            {"source_spec":spec,"targets":targets,
             "source_list":owner,"source_rank":rank,
             "source_row_sha256":row_sha,"source_action":action,
             "IF_class":condition,"identity_status":status,
             "emitted_first_window_occurrences":count,
             "source_IF_at_actual_select":"UNKNOWN",
             "actual_dispatch_proven":False,
             "gameplay_action_priority_rank":None}
            for (spec,targets,owner,rank,row_sha,action,condition,status),count
            in sorted(window_source_rows.items(),
                      key=lambda p:(-p[1],p[0]))],
        "first_window_capture_worklist":[{
            "identity_status":status,"required_capture":needed,
            "IF_class":condition,"occurrences":count,
            "priority_is_gameplay_priority":False}
            for (status,needed,condition),count in sorted(
                focus.items(),key=lambda x:(-x[1],x[0]))],
        "existing_original_JSON2_sample_action_parity":
            v["original_JSON2_action_order_time_id_ordinal_parity"],
        "same_run_true_dispatch_causality_proven":0,
        "source_IF_at_original_selected_action_proven":0,
        "complete_source_physical_READY_proven":0,
        "independent_competitor_READY_proven":0,
        "opener_end":"UNKNOWN","WCL_blind_holdout":"NOT_RUN",
        "dummy_trainer_wrong_skill":"UNKNOWN",
        "new_SimC_CXX_builds":0,"new_WCL_API_calls":0,"MAIN_promoted":False,
        "first_window_is_observation_only":True,
    }


def selftest()->dict:
    profile=(b'warrior="Probe"\nspec=fury\n'
             b'actions=/synthetic_strike,if=rage>=40\n'
             b'actions+=/synthetic_other\n')
    def event(t,ordinal,status,n,rank=1):
        return {"t_ms":t,"emitter_phase":"C",
                "emitter_ordinal":ordinal,"emitter_action":"synthetic",
                "source_list":"default","source_row_rank":rank,
                "matching_root_return_count":n,
                "identity_status":status,
                "source_if_at_selection":"UNKNOWN",
                "complete_readiness":"UNKNOWN",
                "causal_scheduling":"UNKNOWN",
                "dummy_mistake":"UNKNOWN"}
    unique="UNIQUE_SAME_RUN_RETURN_POINTER_ROW_TEMPORAL_WITNESS"
    multi="UNKNOWN_MULTIPLE_ROOT_RETURNS"
    absent="UNKNOWN_NO_ROOT_RETURN_BEFORE_EMITTER"
    reports={}
    declarations=[]
    for spec in ("dummy_a","dummy_b"):
        sample=[event(100,0,unique,1),event(300,1,multi,2),
                event(11000,2,absent,0,2)]
        report={"schema":CASE_SCHEMA,"policy_id":POLICY,
                "selection_to_emission_causality_proven":False,
                "source_readiness_proven":0,"WCL_holdout":"NOT_RUN",
                "dummy_error":"UNKNOWN",
                "evidence_level":"SAME_RUN_TEMPORAL_SOURCE_IDENTITY_ONLY",
                "sample":sample,"emitter_records":3,"identity_counts":{
                    unique:1,multi:1,absent:1}}
        raw=canonical(report)
        reports[(spec,1)]=(report,raw)
        declarations.append({
            "spec":spec,"targets":1,"report_sha256":digest(raw),
            "identity_candidates":1,"unknown_multi_root":1,
            "unknown_no_root":1})
    receipt={"schema":RECEIPT_SCHEMA,"policy_id":POLICY,
             "source_simc_commit":SIMC_COMMIT,
             "validation":{"final_run_id":42581326058,
                           "final_run_status":"completed",
                           "final_run_conclusion":"success",
                           "jobs_total":3,"jobs_success":3,
                           "native_official_cpp_build":"PASS",
                           "original_JSON2_action_order_time_id_ordinal_parity":"149/149",
                           "actual_source_row_selection_to_emission_causality_proven":False,
                           "current_general_rotation_full_ready_proven":0,
                           "WCL_current_IR_holdout":"NOT_RUN",
                           "actual_target_dummy_user_error_verdict":"UNKNOWN",
                           "original_emitter_records_total":6,
                           "unique_temporal_same_run_pointer_row_candidates":2,
                           "ambiguous_multi_root":2,
                           "no_matching_root_before_emitter":2,
                           "cases":declarations}}
    profile_map={spec:profile for spec in ("dummy_a","dummy_b")}
    value=analyze(receipt,profile_map,reports)
    assert value["original_emitter_total"]==6
    assert value["first_window_combat_event_count"]==4
    assert value["emitter_phase_identity_counts"]["C"][unique]==2
    assert value["first_window_missing_IF_symbol_frequency"]==[
        {"symbol":"rage","emitted_source_row_observations":4,
         "actual_original_select_PRE":"UNKNOWN"}]
    assert len(value["first_window_source_row_capture_focus"])==4
    assert value["typed_source_IF_boundary_counts"][
        "SOURCE_IF_REQUIRES_SAME_CALL_PRE"]==4
    assert value["typed_source_IF_boundary_counts"][
        "NO_EXPLICIT_IF_NOT_READY_PROOF"]==2
    assert value["same_run_true_dispatch_causality_proven"]==0
    assert value["complete_source_physical_READY_proven"]==0
    assert value["new_SimC_CXX_builds"]==0
    cases=0
    def fail_mutation(changer):
        nonlocal cases
        rr=json.loads(json.dumps(receipt))
        reports_copy={k:(json.loads(json.dumps(v[0])),v[1])
                      for k,v in reports.items()}
        changer(rr,reports_copy)
        try:analyze(rr,profile_map,reports_copy)
        except TriageError:
            cases+=1
        else:
            raise AssertionError("SOURCE_BOUNDARY_FORGED_PROOF_ACCEPTED")
    fail_mutation(lambda r,p:r["validation"].update(
        {"current_general_rotation_full_ready_proven":1}))
    fail_mutation(lambda r,p:r["validation"].update(
        {"final_run_conclusion":"failure"}))
    fail_mutation(lambda r,p:r["validation"].update(
        {"original_emitter_records_total":7}))
    fail_mutation(lambda r,p:r["validation"]["cases"][0].update(
        {"report_sha256":"0"*64}))
    fail_mutation(lambda r,p:p[("dummy_a",1)][0].update(
        {"selection_to_emission_causality_proven":True}))
    fail_mutation(lambda r,p:p[("dummy_a",1)][0]["sample"][0].update(
        {"matching_root_return_count":0}))
    fail_mutation(lambda r,p:p[("dummy_a",1)][0]["sample"][0].update(
        {"source_row_rank":99}))
    fail_mutation(lambda r,p:p[("dummy_a",1)][0]["sample"][0].update(
        {"source_if_at_selection":True}))
    fail_mutation(lambda r,p:p[("dummy_a",1)][0]["sample"][1].update(
        {"emitter_ordinal":0}))
    fail_mutation(lambda r,p:p[("dummy_a",1)][0]["sample"][1].update(
        {"causal_scheduling":"PROVEN"}))
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "cross_spec_test_cases":2,"source_rows_verified":6,
            "negative_controls":cases,"full_ready_proven":0,
            "CXX_builds":0,"WCL_calls":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pinned-receipt",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--first-window-ms",type=int,default=10000)
    args=p.parse_args()
    if not any((args.pinned_receipt,args.manifest,args.out)):
        print(json.dumps(selftest(),sort_keys=True))
        return
    need(args.pinned_receipt is not None and args.manifest is not None
         and args.out is not None,"EXPLICIT_RECEIPT_MANIFEST_AND_OUT_REQUIRED")
    receipt,_=_load(args.pinned_receipt)
    manifest,_=_load(args.manifest)
    need(manifest.get("schema")==
         "ZrotGeneralRotationBoundaryReplayPathsManifestV1"
         and manifest.get("policy_id")==POLICY
         and manifest.get("source_revision")==SIMC_COMMIT
         and isinstance(manifest.get("cases"),list),
         "REPLAY_PATH_MANIFEST_UNSUPPORTED")
    profiles={}
    reports={}
    for item in manifest["cases"]:
        need(isinstance(item,dict) and set(item)==EXPECTED_CASE_FIELDS,
             "MANIFEST_ENTRY_FIELDS_NOT_PINNED")
        spec=item["spec"];n=item["targets"]
        need(type(spec) is str and spec and type(n) is int and 1<=n<=8,
             "MANIFEST_SPEC_OR_TARGET_INVALID")
        key=(spec,n)
        need(key not in reports,"DUPLICATE_MANIFEST_CASE")
        profile_path=Path(item["profile_path"])
        need(profile_path.is_file() and not profile_path.is_symlink(),
             "OFFICIAL_SOURCE_PROFILE_FILE_MISSING")
        profile=profile_path.read_bytes()
        if spec in profiles:
            need(profiles[spec]==profile,"SAME_SPEC_PROFILE_BYTES_CHANGED")
        profiles[spec]=profile
        reports[key]=_load(Path(item["report_path"]))
    result=analyze(receipt,profiles,reports,window_ms=args.first_window_ms)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("xb") as stream:stream.write(canonical(result))
    print("PINNED_ORIGINAL_SOURCE_BOUNDARY_TRIAGE_SHA256="+
          digest(args.out.read_bytes()))
    print("FIRST_WINDOW_COMBAT_EMITTERS="+
          str(result["first_window_combat_event_count"]))
    print("SAME_RUN_TEMPORAL_MATCHES="+str(result["identity_counts"].get(
          "UNIQUE_SAME_RUN_RETURN_POINTER_ROW_TEMPORAL_WITNESS",0)))


if __name__=="__main__":
    main()
