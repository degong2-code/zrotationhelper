#!/usr/bin/env python3
"""Evidence-bounded Arcane Orb conditional opener decision hypotheses.

Combines ALREADY VERIFIED source snapshots and candidate order, then uses the
GENERIC sufficient_source_witness engine to explain the observed selected APL
IF and earlier same-spell IF FALSE. The other prior physical candidates remain
UNKNOWN; no whole-spell READY, WCL optimum or player practice verdict follows.

The source-derived precombat variable is not a directly observed source PRE
variable: every dependency retains this provenance distinction. SimC's
same-tick root-before-method ordering is NOT WCL Strict PRE.

No CLI arguments = deterministic synthetic source certificate self-test.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import Expression, ast_symbols, evaluate_ast, truth
from general_rotation_source_if_minimal_witness_v1 import (
    SCHEMA as WITNESS, sufficient_source_witness,
)
from general_rotation_arcane_orb_spec_state_pre_replay_v1 import (
    SCHEMA as SPEC, PROFILE_GIT_BLOB, TALENTS, BUFFS,
    FLOAT_KEY, _state_from_source,
)
from general_rotation_arcane_orb_selected_priority_context_v1 import (
    SCHEMA as PRIOR,
)
from general_rotation_source_eligibility_decision_ir_v1 import POLICY

SCHEMA="ZrotArcaneOrbSourceConditionalOpenerHypothesisV1"
PINS={
    "st":"36bae18a1a635a4955c5a10797a8c2762f8163423450556b1dcc956b64ba0482",
    "2t":"389e8fc4d5a95da1851feb1ac302f8b9e225885afbc46a041003d5ba19380417",
    "prior":"6c2431d3fca96da7b77569ddb90ae93b232109314e39b922dbce5b55534f4160",
}
class ConditionalSourceRuleError(ValueError):
    pass

def need(ok:bool,reason:str)->None:
    if not ok:raise ConditionalSourceRuleError(reason)

def _proven_original_root_fact(expr:str, record:dict,
                              *, expected:bool)->dict:
    pre=record["exact_original_spec_PRE"]
    facts,derived=_state_from_source(pre)
    stored=record["source_IF_independent_PRE_replay"]
    need(stored is expected and
         record["source_IF_expression"]==expr and
         record["IF_replay_classification"]==
           "INDEPENDENT_ORIGINAL_ROOT_SOURCE_AST_"+("TRUE" if expected else "FALSE"),
         "PRE_SOURCE_AST_ACTUAL_TRUE_FALSE_MISMATCH")
    ret=sufficient_source_witness(expr,facts,expected=expected)
    witness=ret["sufficient_fact_witness"]
    sources={}
    for key in witness:
        sources[key]=(
          "SOURCE_DERIVED_PROFILE_PRECOMBAT_FORMULA_NOT_DIRECT_ROOT_STATE"
          if key=="variable.aoe_count" else
          "SOURCE_DERIVED_EXACT_CPP_BUFF_ZERO"
          if key=="buff.arcane_surge.down" else
          "ORIGINAL_CPP_READ_ONLY_MAGE_PRE_BEFORE_INHERITED_READY"
        )
    if "variable.aoe_count" in witness:
        need(derived["variable.aoe_count"]["direct_original_cpp_variable_read"] is False,
             "SOURCE_DERIVED_VARIABLE_UNSAFE_PROVENANCE")
    return {
        "source_original_CPP_ready_root":record["root_id"],
        "at_simc_ms":record["simc_ms"],
        "source_list":record["source_list"],
        "source_ordinal":record["source_ordinal"],
        "source_row_sha256":record["source_row_sha256"],
        "source_expression":expr,
        "source_IF_independently_replayed_value":expected,
        "minimal_sufficient_facts":witness,
        "fact_provenance":sources,
        "all_available_source_symbols":ret["source_all_operand_names"],
        "witness_inclusion_minimal_not_unique":True,
        "source_APL_IF_is_not_entire_action_READY":True,
        "original_CPP_before_call_not_WCL_STRICT_PRE":True,
    }

def compose(spec:dict, prior:dict, *, case:str)->dict:
    need(case in ("st","2t") and
         spec.get("schema")==SPEC and
         prior.get("schema")==PRIOR and
         spec.get("product_policy_id")==POLICY and
         prior.get("product_policy_id")==POLICY and
         spec.get("profile_git_blob_sha1")==PROFILE_GIT_BLOB==
              prior.get("source_profile_git_blob_sha1") and
         spec.get("independent_complete_action_READY") is False and
         prior.get("independent_full_skill_READY_proven")==0 and
         prior.get("native_POST_false_not_independent_full_NOT_READY") is True and
         spec.get("target_count")==prior.get("target_count_scenario")==
              (1 if case=="st" else 2),
         "MATCHED_ORIGINAL_SOURCE_AND_READINESS_CONTRACT_REQUIRED")
    index={}
    for r in spec["all_source_root_independent_IF"]:
        rid=r["root_id"]
        need(type(rid) is int and rid>0 and rid not in index and
             r.get("full_independent_ready_gate_set_closed") is False,
             "DUPLICATED_OR_PROMOTED_SOURCE_READY_ROOT")
        index[rid]=r
    events=prior.get("selected_actions")
    expected_total=1 if case=="st" else 3
    need(isinstance(events,list) and len(events)==expected_total,
         "ORIGINAL_SELECTED_OPENER_EVENT_COUNT_CHANGED")
    winners=[]
    total=Counter()
    for event in events:
        rid=event["selected_root_CPP_ready_id"]
        p=index.get(rid)
        need(p is not None and
             p["simc_ms"]==event["simc_ms"] and
             p["source_list"]==event["selected_source_list"] and
             p["source_ordinal"]==event["selected_source_row_ordinal"] and
             p["original_cpp_SOURCE_RETURN_stage"]=="ACTION_READY_TRUE" and
             event["selected_root_CPP_returned_action_stage"]=="ACTION_READY_TRUE" and
             event["independent_prior_physical_NOT_READY_proven"] is False,
             "SELECTED_ORB_ACTUAL_NATIVE_SOURCE_GATE_IDENTITY_NOT_SAME")
        selected=_proven_original_root_fact(
            p["source_IF_expression"],p,expected=True)
        others=[]
        for old in event["source_earlier_candidates"]:
            before={
                "source_action":old["earlier_source_action"],
                "source_ordinal":old["earlier_source_ordinal"],
                "original_cpp_ready_root":old["earlier_CPP_ready_root_id"],
                "native_POST":old["earlier_native_POST"],
                "whole_ability_unavailable_independently_proven":False,
            }
            if old["earlier_source_action"]=="arcane_orb":
                prior_root=index.get(old["earlier_CPP_ready_root_id"])
                need(prior_root is not None and
                     old["earlier_source_branch_actual"]=="ACTION_APL_IF_FALSE" and
                     prior_root["original_cpp_SOURCE_RETURN_stage"]=="ACTION_APL_IF_FALSE" and
                     prior_root["simc_ms"]==event["simc_ms"] and
                     prior_root["source_list"]==event["selected_source_list"] and
                     prior_root["source_ordinal"]==old["earlier_source_ordinal"],
                     "EARLIER_ORB_FALSE_NOT_MATCHED_TO_ACTUAL_SOURCE_ROOT")
                before["source_IF_FALSE_witness"]=_proven_original_root_fact(
                    prior_root["source_IF_expression"],prior_root,expected=False)
                before["earlier_source_IF_decision"]="INDEPENDENT_SOURCE_PRE_AST_FALSE_AND_ORIGINAL_CXX_IF_FALSE"
                total["earlier_same_spell_source_if_false_explained"]+=1
            else:
                need(old["earlier_native_POST"] is False and
                     old["earlier_source_branch_actual"] is None,
                     "UNSUPPORTED_EARLIER_NON_ORB_CANDIDATE_REASON")
                before["earlier_source_IF_decision"]="UNKNOWN_ONLY_NATIVE_POST_FALSE"
                total["earlier_other_spell_ready_unknown"]+=1
            total["prior_original_source_candidates"]+=1
            others.append(before)
        total["selected_orb_same_root_IF_true_explained"]+=1
        winners.append({
            "original_cpp_selected_source_action":"arcane_orb",
            "simc_ms":event["simc_ms"],
            "target_count_scenario":spec["target_count"],
            "selected_source_APL_IF_TRUE":selected,
            "earlier_same_list_candidate_decisions":others,
            "original_cpp_selected_full_action_ready_observed":True,
            "independently_proven_positive_FULL_READY":False,
            "independently_proven_entire_prior_spell_NOT_READY":False,
            "general_rotation_opener_optimality_WCL_holdout":False,
            "gameplay_user_error_feedback":"UNKNOWN",
        })
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "source_simc_profile_git_blob_sha1":PROFILE_GIT_BLOB,
        "case":case,"source_context":"ORIGINAL_CXX_ACTUAL_30_SECOND_SELECT_REPLAY",
        "conditional_source_rule_hypotheses":winners,
        "counts":dict(sorted(total.items())),
        "source_truth_independently_replayed_from_original_root_facts":True,
        "derived_precombat_variable_not_runtime_observed":True,
        "effect_projection_validated":False,
        "independent_FULL_READY_proven":0,
        "WCL_independent_blind_holdout_done":False,
        "WoW_actual_addon_tested":False,
        "dummy_feedback_permitted":False,
        "WCL_API_calls":0,
    }

def read_pinned(folder:Path,priority_path:Path)->dict:
    need(folder.is_dir() and priority_path.is_file(),
         "SPEC_AND_ORIGINAL_CPP_SOURCE_RECEIPTS_REQUIRED")
    raw=priority_path.read_bytes()
    need(sha256(raw).hexdigest()==PINS["prior"],
         "PINNED_ORIGINAL_PRIOR_CPP_SOURCE_RECEIPT_CHANGED")
    prior=json.loads(raw)
    need(prior.get("schema")==PRIOR and
         prior.get("product_policy_id")==POLICY,
         "EARLIER_SOURCE_PRIORITY_MODEL_POLICY_MISMATCH")
    output={}
    counts=Counter()
    for case in ("st","2t"):
        file=folder/("zrot-arcane-orb-exact-spec-pre-"+case+".json")
        data=file.read_bytes()
        need(sha256(data).hexdigest()==PINS[case],
             "PINNED_ORIGINAL_SPEC_ROOT_PRE_BYTES_CHANGED")
        actual=json.loads(data)
        report=compose(actual,prior["cases"][case],case=case)
        output[case]=report
        counts.update(report["counts"])
    need(counts["selected_orb_same_root_IF_true_explained"]==4 and
         counts["earlier_same_spell_source_if_false_explained"]==2 and
         counts["earlier_other_spell_ready_unknown"]==8 and
         counts["prior_original_source_candidates"]==10,
         "ORIGINAL_ARCANE_ORB_CONDITIONAL_COHORT_MISMATCH")
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "case_results":output,
        "aggregate_counts":dict(sorted(counts.items())),
        "first_bounded_source_opener_explainable":True,
        "source_if_only_not_validated_physical_priority":True,
        "WCL_source_blind_holdout_performed":False,
        "safe_dummy_feedback_permitted":False,
        "WCL_API_calls":0,
    }

def selftest()->dict:
    for case,h in PINS.items():
        assert len(h)==64 and all(c in "0123456789abcdef" for c in h)
    source={
      "root_id":7,"simc_ms":1200,"source_list":"default",
      "source_ordinal":1,"source_row_sha256":"a"*64,
      "source_IF_expression":"talent.orb_mastery&active_enemies>=2",
      "source_IF_independent_PRE_replay":False,
      "IF_replay_classification":"INDEPENDENT_ORIGINAL_ROOT_SOURCE_AST_FALSE",
      "exact_original_spec_PRE":{
        "talent.splintering_sorcery":1,"talent.spellfire_spheres":0,
        "talent.orb_mastery":0,"talent.charged_orb":1,
        "buff.arcane_charge.stack":3,"buff.arcane_surge.stack":0,
        "buff.arcane_salvo.stack":2,"active_enemies":2,
        "cooldown.arcane_orb.charges_fractional":2.0,
      },
    }
    result=_proven_original_root_fact(
        source["source_IF_expression"],source,expected=False)
    assert result["minimal_sufficient_facts"]=={"talent.orb_mastery":0}
    try:_proven_original_root_fact(
        source["source_IF_expression"],source,expected=True)
    except ConditionalSourceRuleError:pass
    else:raise AssertionError("FALSE_ORIGINAL_SOURCE_IF_PROMOTED_TO_TRUE")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":5,"independent_FULL_READY_proven":0,
            "WCL_API_calls":0}

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec-evidence-dir",type=Path)
    p.add_argument("--earlier-source-priority-json",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.spec_evidence_dir is None and a.earlier_source_priority_json is None:
        result=selftest()
    elif a.spec_evidence_dir is not None and a.earlier_source_priority_json is not None:
        result=read_pinned(a.spec_evidence_dir,a.earlier_source_priority_json)
    else:p.error("both exact original SimC spec state and earlier source evidence required")
    buf=(json.dumps(result,sort_keys=True,separators=(",",":"),
                    ensure_ascii=False,allow_nan=False)+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(buf)
    else:
        import sys
        sys.stdout.buffer.write(buf)

if __name__=="__main__":main()
