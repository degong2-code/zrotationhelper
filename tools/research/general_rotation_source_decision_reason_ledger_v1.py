#!/usr/bin/env python3
"""Hekili-informed source decision reason ledger from already captured Native receipts.

Pure offline, no C++ rebuild, no WCL calls and no in-game addon logic.
An observed Native action_ready return is POST evidence, NOT independent READY.
IF_FALSE can be claimed for one exact candidate only when its original,
source-root PRE AST and Native IF result independently match and were retained.
The original chosen-row receipt stores only 16 root examples per case; all
additional returns stay UNSAMPLED, never inferred from timestamps or counts.

Default (no arguments): synthetic, deterministic self-test.
--receipt-zip: replay the original instrumented Native receipt ZIP as offline
data, without reading raw actor logs or modifying the original source.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import zipfile

SCHEMA="ZrotOriginalSourceDecisionReasonLedgerV1"
SUMMARY="ZrotOriginalSourceDecisionReasonLedger4CaseSummaryV1"
PRODUCT="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
TEMPORAL="ZrotGeneralRotationTimeScopedSourcePriorityObservationIRV1"
SELECTED="ZrotOriginalSourceReturnedActionFrontierV1"
IF_PROOF="ZrotOriginalRootPREIndependentIFVsNativeComparatorV1"
SHA40=re.compile(r"[0-9a-f]{40}\Z")
SHA64=re.compile(r"[0-9a-f]{64}\Z")
NATIVE="ACTION_READY_CALLED"
BACKGROUND="BACKGROUND_SKIP_BEFORE_READY"
WAIT="WAIT_ON_READY_BREAK"
CONTROL=frozenset(("call_action_list","run_action_list","swap_action_list","variable"))
UNKNOWN="UNKNOWN"
CASES=("fury-st","fury-2t","arcane-st","arcane-2t")

class ReasonLedgerError(ValueError):
    pass

def _need(condition:bool,code:str)->None:
    if not condition:
        raise ReasonLedgerError(code)

def _sha(value:bytes)->str:
    return sha256(value).hexdigest()

def _source_label(action:str)->str:
    if action in CONTROL:return "SOURCE_CONTROL_NOT_USER_DAMAGE_SPELL"
    if action in ("auto_attack","potion","use_item","use_items"):
        return "NON_DAMAGE_OR_UTILITY_NOT_PROVEN_ROTATIONAL_CAST"
    return "SOURCE_ACTION_KIND_NOT_PROVEN_PHYSICAL_DAMAGE"

def compose(temporal:dict, selected:dict, if_proof:dict)->dict:
    """One target-count/spec case; no source profile or timestamps guessed."""
    blob=temporal.get("source_profile_git_blob_sha1")
    _need(isinstance(blob,str) and SHA40.fullmatch(blob) is not None,
          "SOURCE_PROFILE_PIN_REQUIRED")
    _need(temporal.get("schema")==TEMPORAL and
          selected.get("schema")==SELECTED and
          if_proof.get("schema")==IF_PROOF and
          all(v.get("product_policy_id")==PRODUCT for v in
              (temporal,selected,if_proof)) and
          all(v.get("source_profile_git_blob_sha1")==blob for v in
              (selected,if_proof)),
          "MULTISOURCE_SCHEMA_POLICY_OR_PROFILE_DRIFT")
    _need(temporal.get("independent_FULL_READY_proven")==0 and
          temporal.get("source_order_complete") is False and
          selected.get("independent_FULL_READY_proven")==0 and
          selected.get("complete_source_order_proven") is False and
          selected.get("practice_error_feedback_permitted") is False and
          selected.get("return_is_observed_original_simc_selection_not_independent_READY") is True and
          selected.get("prior_native_false_not_independently_proven_NOT_READY") is True and
          if_proof.get("independent_full_action_ready_proven")==0 and
          if_proof.get("source_order_complete") is False and
          if_proof.get("native_if_comparison_truth_is_post_only") is True and
          if_proof.get("dummy_feedback_permitted") is False and
          not if_proof.get("independent_ast_vs_original_native_if_conflicts") and
          if_proof.get("WCL_blind_semantics_injected") is False,
          "UNSUPPORTED_FULL_READY_OR_IF_PROOF_CONTRACT")
    target=temporal.get("target_count")
    _need(type(target) is int and 1<=target<=40,"TARGET_COUNT_EXPLICIT")
    sweep_records=temporal.get("observed_time_scoped_selection_frontiers")
    _need(isinstance(sweep_records,list) and len(sweep_records)==temporal.get("source_sweep_count") and
          len(sweep_records)==selected.get("source_sweeps_exact_cxx_return") and
          len(sweep_records)>0,"ORIGINAL_SWEEP_COHORT_NOT_IDENTICAL")
    sweeps={}
    by_root={}
    for sw in sweep_records:
        sid=sw.get("sweep_call_id")
        _need(type(sid) is int and sid>0 and sid not in sweeps and
              isinstance(sw.get("source_list"),str) and
              type(sw.get("at_simc_ms")) is int and
              isinstance(sw.get("observed_candidate_event_stream"),list) and
              sw.get("full_source_priority_frontier_closed") is False and
              sw.get("opener_optimality_proven") is False,
              "SOURCE_SWEEP_CAUSAL_IDENTITY_DRIFT")
        sweeps[sid]=sw
        for ev in sw["observed_candidate_event_stream"]:
            if ev.get("stage")!=NATIVE:continue
            rid=ev.get("original_action_ready_root_id")
            _need(type(rid) is int and rid>0 and rid not in by_root and
                  type(ev.get("simc_NATIVE_return_post_comparator")) is bool and
                  isinstance(ev.get("source_row_sha256"),str) and
                  SHA64.fullmatch(ev["source_row_sha256"]) is not None,
                  "NATIVE_READY_ROOT_ID_OR_EVENT_MALFORMED")
            by_root[rid]=(sw,ev)
    _need(len(by_root)==temporal.get("original_ready_calls"),
          "NATIVE_ROOT_COUNT_COHORT_DRIFT")
    proofs={}
    for sample in if_proof.get("first_bounded_comparisons",[]):
        rid=sample.get("root_id")
        pair=by_root.get(rid)
        _need(type(rid) is int and pair is not None and rid not in proofs,
              "IF_PROOF_ROOT_NOT_IN_ORIGINAL_CAUSAL_COHORT")
        sw,ev=pair
        _need(sample.get("source_row_sha256")==ev.get("source_row_sha256") and
              sample.get("ordinal_one_based")==ev.get("ordinal_one_based") and
              sample.get("source_list")==sw["source_list"] and
              sample.get("at_simc_ms")==sw["at_simc_ms"] and
              type(sample.get("ast_from_direct_original_PRE")) is bool and
              type(sample.get("original_native_if_return_comparator")) is bool and
              sample["ast_from_direct_original_PRE"]==
                  sample["original_native_if_return_comparator"] and
              sample.get("full_action_ready")==UNKNOWN,
              "IF_PRE_AND_NATIVE_SOURCE_ROW_OR_TRUTH_CONFLICT")
        proofs[rid]=sample
    _need(len(proofs)<=if_proof.get("native_if_independent_positive_comparison_count",-1),
          "SOURCE_IF_BOUNDED_SAMPLE_EXCEEDS_PROVEN_COHORT")
    examples=selected.get("bounded_root_return_examples")
    _need(isinstance(examples,list) and len(examples)>0 and len(examples)<=16,
          "RETURN_BOUNDED_ROOT_SAMPLES_REQUIRED")
    observed_returns=selected.get("counts",{})
    _need(type(observed_returns.get("root_sweep_returned_action_source_row")) is int and
          observed_returns["root_sweep_returned_action_source_row"]>=len(examples),
          "ROOT_RETURN_SAMPLE_EXCEEDS_ACTUAL")
    seen_root_sweeps=set()
    decisions=[]
    labels=Counter()
    all_priors=Counter()
    for item in examples:
        sid=item.get("sweep_call_id")
        sw=sweeps.get(sid)
        _need(type(sid) is int and sw is not None and sid not in seen_root_sweeps and
              sw.get("parent_sweep_call_id")==0 and
              item.get("at_simc_ms")==sw["at_simc_ms"] and
              item.get("full_READY")==UNKNOWN and
              item.get("return_kind") in ("DIRECT","CHILD_PROPAGATED") and
              isinstance(item.get("source_row_sha256"),str) and
              SHA64.fullmatch(item["source_row_sha256"]) is not None and
              type(item.get("source_ordinal")) is int and
              item["source_ordinal"]>0,
              "RETURN_EXAMPLE_WITHOUT_EXACT_NATIVE_ROOT")
        seen_root_sweeps.add(sid)
        events=sw["observed_candidate_event_stream"]
        _need(bool(events) and events[-1].get("stage")==NATIVE and
              events[-1].get("simc_NATIVE_return_post_comparator") is True,
              "SELECTED_RETURN_WITHOUT_FINAL_NATIVE_TRUE")
        last=events[-1]
        if item["return_kind"]=="DIRECT":
            _need(item["source_list"]==sw["source_list"] and
                  last.get("source_action")==item.get("source_action") and
                  last.get("ordinal_one_based")==item.get("source_ordinal") and
                  last.get("source_row_sha256")==item.get("source_row_sha256") and
                  last.get("source_action") not in ("call_action_list","variable"),
                  "DIRECT_CHOICE_NOT_LAST_SOURCE_ROW")
        else:
            _need(last.get("source_action")=="call_action_list",
                  "PROPAGATED_ROOT_LACKS_CALL_CONTROL")
            _need(any(n.get("parent_sweep_call_id")==sid for n in
                      sweep_records),
                  "PROPAGATED_ROOT_HAS_NO_NESTED_SWEEP")
        _need(item.get("prior_native_false_observed")==sum(
                  e.get("stage")==NATIVE and
                  e.get("simc_NATIVE_return_post_comparator") is False
                  for e in events[:-1]) and
              item.get("prior_background_skips_observed")==sum(
                  e.get("stage")==BACKGROUND for e in events[:-1]),
              "ROOT_RETURN_PRIOR_NATIVE_COMPARATORS_DISAGREE")
        evidence=[]
        for offset,ev in enumerate(events[:-1],1):
            stage=ev.get("stage")
            rid=ev.get("original_action_ready_root_id")
            if stage==BACKGROUND:
                reason="SOURCE_BACKGROUND_SKIP"
                native_post="NOT_CALLED"
            elif stage==WAIT:
                reason="WAIT_BREAK_NOT_ACTION_READINESS"
                native_post="NOT_CALLED"
            elif stage==NATIVE:
                native_post="TRUE" if ev["simc_NATIVE_return_post_comparator"] else "FALSE"
                if native_post=="FALSE":
                    reason=("SOURCE_IF_FALSE_INDEPENDENT_PRE_PROVEN"
                            if rid in proofs and
                            proofs[rid]["ast_from_direct_original_PRE"] is False
                            else "NATIVE_READY_FALSE_POST_ONLY")
                elif ev.get("source_action") in CONTROL:
                    reason="SOURCE_CONTROL_TRUE_CONTINUED_OR_NESTED"
                else:
                    reason="EARLIER_NATIVE_TRUE_UNRESOLVED_NO_NOT_READY_CLAIM"
            else:
                raise ReasonLedgerError("UNDECLARED_PRIOR_CANDIDATE_STAGE")
            all_priors[reason]+=1
            evidence.append({
                "observed_sequence_index":offset,
                "source_list":sw["source_list"],
                "source_action":ev.get("source_action"),
                "source_ordinal":ev.get("ordinal_one_based"),
                "source_row_sha256":ev.get("source_row_sha256"),
                "original_action_ready_root_id":rid if stage==NATIVE else None,
                "original_native_ready_post":native_post,
                "reason_code":reason,
                "candidate_independently_FULL_NOT_READY":False,
                "native_if_source_PRE_recomputed":rid in proofs if stage==NATIVE else False,
                "original_if_false_matched":reason=="SOURCE_IF_FALSE_INDEPENDENT_PRE_PROVEN"
            })
        labels[item["return_kind"]]+=1
        decision={
            "source_profile_git_blob_sha1":blob,
            "target_count":target,"top_level_sweep_id":sid,
            "at_simc_ms":sw["at_simc_ms"],
            "selection_mode_source_order_deterministic":
                sw.get("source_order_sampling_deterministic") is True,
            "selected_original_source":{
                "return_kind":item["return_kind"],
                "source_action":item["source_action"],
                "source_list":item["source_list"],
                "source_ordinal":item["source_ordinal"],
                "source_row_sha256":item["source_row_sha256"],
                "action_classification":_source_label(item["source_action"]),
                "original_cxx_return_observed":True,
                "independently_FULL_READY":UNKNOWN
            },
            "root_source_route":{
                "source_list":sw["source_list"],
                "final_source_control":last["source_action"],
                "native_post":True,
                "nested_leaf_trace_full_proven":False
            },
            "prior_candidate_evidence":evidence,
            "prior_independent_source_IF_false":sum(
                e["reason_code"]=="SOURCE_IF_FALSE_INDEPENDENT_PRE_PROVEN"
                for e in evidence),
            "prior_native_ready_false_post_only":sum(
                e["reason_code"]=="NATIVE_READY_FALSE_POST_ONLY" for e in evidence),
            "priority_optimality":UNKNOWN,
            "dummy_feedback_verdict":UNKNOWN
        }
        decisions.append(decision)
    _need(len(seen_root_sweeps)==len(examples),"DUPLICATED_ROOT_CHOICE_EXAMPLE")
    return {
        "schema":SCHEMA,"product_policy_id":PRODUCT,
        "source_profile_git_blob_sha1":blob,"target_count":target,
        "original_all_sweeps_reused":len(sweeps),
        "original_ready_roots_reused":len(by_root),
        "actual_top_level_choices_in_original_run":
            observed_returns["root_sweep_returned_action_source_row"],
        "root_chosen_return_examples_with_full_prior_event_stream":len(decisions),
        "root_chosen_return_examples_not_retained":
            observed_returns["root_sweep_returned_action_source_row"]-len(decisions),
        "bounded_independent_original_IF_root_proofs":len(proofs),
        "source_return_kinds_in_bounded_examples":dict(sorted(labels.items())),
        "prior_evidence_reason_counts":dict(sorted(all_priors.items())),
        "decisions":decisions,
        "native_post_is_not_independent_full_ready":True,
        "source_if_false_is_only_proven_for_specific_original_base_gate":True,
        "source_order_complete":False,
        "independent_FULL_READY_proven":0,
        "independent_entire_candidate_NOT_READY_proven":0,
        "priority_optimality_proven":0,
        "user_dummy_error_verdict_permitted":False,
        "WCL_API_calls":0,
    }

def replay_original_artifact(archive:Path,expected_sha256:str|None=None)->dict:
    data=archive.read_bytes()
    digest=_sha(data)
    if expected_sha256:
        _need(SHA64.fullmatch(expected_sha256) is not None and
              digest==expected_sha256,"SOURCE_ARTIFACT_ZIP_SHA256_MISMATCH")
    per_case={}
    total=Counter()
    with zipfile.ZipFile(archive) as z:
        names=set(z.namelist())
        for key in CASES:
            files={
                "temporal":"zrot-source-temporal-frontier-"+key+".json",
                "selected":"zrot-native-source-selected-return-"+key+".json",
                "proof":"zrot-native-root-if-proof-"+key+".json"
            }
            _need(set(files.values())<=names,"SOURCE_NATIVE_RECEIPT_MISSING:"+key)
            values={k:json.loads(z.read(v)) for k,v in files.items()}
            out=compose(values["temporal"],values["selected"],values["proof"])
            _need(out["target_count"]==(1 if key.endswith("-st") else 2),
                  "SOURCE_FOUR_CASE_TARGET_IDENTITY_CHANGED")
            per_case[key]=out
            total["all_original_sweeps"]+=out["original_all_sweeps_reused"]
            total["retained_root_choice_examples"]+=out[
                "root_chosen_return_examples_with_full_prior_event_stream"]
            total["unsampled_original_root_choices"]+=out[
                "root_chosen_return_examples_not_retained"]
            total["source_if_false_prior_witnesses"]+=out[
                "prior_evidence_reason_counts"].get(
                    "SOURCE_IF_FALSE_INDEPENDENT_PRE_PROVEN",0)
            total["native_ready_false_post_only_prior_witnesses"]+=out[
                "prior_evidence_reason_counts"].get("NATIVE_READY_FALSE_POST_ONLY",0)
    return {
        "schema":SUMMARY,"product_policy_id":PRODUCT,
        "source_artifact_zip_sha256":digest,
        "original_cases":list(CASES),
        "aggregate":dict(sorted(total.items())),
        "cases":per_case,
        "source_selection_and_exclusion_evidence_only":True,
        "native_ready_false_post_is_not_independent_mechanic_proof":True,
        "complete_positive_READY":0,"trainer_error_feedback_permitted":False,
        "WCL_API_calls":0,
    }

def selftest()->dict:
    h="a"*64
    b="b"*40
    root={
        "stage":NATIVE,"source_action":"run_action_list",
        "source_row_sha256":h,"ordinal_one_based":1,
        "original_action_ready_root_id":11,
        "simc_NATIVE_return_post_comparator":False
    }
    chosen={
        "stage":NATIVE,"source_action":"rampage",
        "source_row_sha256":"c"*64,"ordinal_one_based":2,
        "original_action_ready_root_id":12,
        "simc_NATIVE_return_post_comparator":True
    }
    sw={"sweep_call_id":1,"parent_sweep_call_id":0,
        "source_list":"default","at_simc_ms":100,
        "source_order_sampling_deterministic":True,
        "full_source_priority_frontier_closed":False,
        "opener_optimality_proven":False,
        "observed_candidate_event_stream":[root,chosen]}
    temporal={"schema":TEMPORAL,"product_policy_id":PRODUCT,
        "source_profile_git_blob_sha1":b,"target_count":2,
        "independent_FULL_READY_proven":0,"source_order_complete":False,
        "source_sweep_count":1,"original_ready_calls":2,
        "observed_time_scoped_selection_frontiers":[sw]}
    selected={"schema":SELECTED,"product_policy_id":PRODUCT,
        "source_profile_git_blob_sha1":b,"independent_FULL_READY_proven":0,
        "complete_source_order_proven":False,
        "practice_error_feedback_permitted":False,
        "return_is_observed_original_simc_selection_not_independent_READY":True,
        "prior_native_false_not_independently_proven_NOT_READY":True,
        "source_sweeps_exact_cxx_return":1,
        "counts":{"root_sweep_returned_action_source_row":1},
        "bounded_root_return_examples":[{
            "sweep_call_id":1,"at_simc_ms":100,"full_READY":UNKNOWN,
            "return_kind":"DIRECT","source_action":"rampage",
            "source_list":"default","source_ordinal":2,
            "source_row_sha256":"c"*64,
            "prior_native_false_observed":1,
            "prior_background_skips_observed":0}]}
    p={"root_id":11,"at_simc_ms":100,
       "source_row_sha256":h,"source_list":"default",
       "ordinal_one_based":1,"ast_from_direct_original_PRE":False,
       "original_native_if_return_comparator":False,
       "full_action_ready":UNKNOWN}
    proof={"schema":IF_PROOF,"product_policy_id":PRODUCT,
       "source_profile_git_blob_sha1":b,
       "independent_full_action_ready_proven":0,
       "source_order_complete":False,
       "native_if_comparison_truth_is_post_only":True,
       "dummy_feedback_permitted":False,
       "independent_ast_vs_original_native_if_conflicts":[],
       "native_if_independent_positive_comparison_count":1,
       "WCL_blind_semantics_injected":False,
       "first_bounded_comparisons":[p]}
    out=compose(temporal,selected,proof)
    assert out["prior_evidence_reason_counts"]=={
        "SOURCE_IF_FALSE_INDEPENDENT_PRE_PROVEN":1}
    assert out["independent_FULL_READY_proven"]==0
    assert out["root_chosen_return_examples_with_full_prior_event_stream"]==1
    import copy
    for mutate in (
        lambda t,s,f: t["observed_time_scoped_selection_frontiers"][0][
            "observed_candidate_event_stream"][0].update(
                original_action_ready_root_id=99),
        lambda t,s,f: s["bounded_root_return_examples"][0].update(
            source_row_sha256="e"*64),
        lambda t,s,f: f["first_bounded_comparisons"][0].update(
            ast_from_direct_original_PRE=True),
        lambda t,s,f: s["bounded_root_return_examples"][0].update(
            prior_native_false_observed=0),
        lambda t,s,f: t.update(independent_FULL_READY_proven=1),
        lambda t,s,f: t["observed_time_scoped_selection_frontiers"][0][
            "observed_candidate_event_stream"].append(
                dict(chosen,original_action_ready_root_id=13))
    ):
        t,s,f=copy.deepcopy((temporal,selected,proof))
        mutate(t,s,f)
        try:compose(t,s,f)
        except ReasonLedgerError:pass
        else:raise AssertionError("TAMPERED_SOURCE_REASON_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":9,"CXX_native_run":False,
            "independent_FULL_READY_proven":0,"WCL_API_calls":0}

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--receipt-zip",type=Path)
    p.add_argument("--expected-zip-sha256")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.receipt_zip is None:
        _need(a.expected_zip_sha256 is None,
              "EXPECTED_ZIP_SHA_WITHOUT_SOURCE_RECEIPT")
        report=selftest()
    else:
        report=replay_original_artifact(a.receipt_zip,
                                        a.expected_zip_sha256)
    data=json.dumps(report,sort_keys=True,ensure_ascii=False,
                    separators=(",",":"),allow_nan=False).encode()+b"\n"
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(data)
    else:sys.stdout.buffer.write(data)

if __name__=="__main__":
    main()
