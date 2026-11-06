#!/usr/bin/env python3
"""Exact-root Arcane Orb source IF evaluator using observed specialization PRE.

Inputs are a pinned original SimC source profile, per-root native action stage
evidence, and new passive class-specific PRE talent/buff/charge snapshots.
The source APL's precombat aoe_count assignment is explicitly verified and
marked SOURCE_DERIVED, not directly observed in the root PRE.

Strong invariants: *same root*, source row SHA/list/ordinal/time, original
profile Git blob, original original CPP stage, and source-AST independent
recomputation. A stage that short-circuited BEFORE IF is never said to have
evaluated IF in the original C++.

Default: synthetic zero-network self-test; no local parameters required.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path

from simc_apl_semantic_ir_v2 import (
    parse_profile, git_blob, evaluate_ast, ast_symbols, truth,
)
from general_rotation_arcane_orb_spec_state_pre_producer_v1 import (
    SCHEMA as PRODUCER, MARK, SYMBOLS, ORIGINAL_CPP_BLOB,
)
from general_rotation_arcane_orb_native_ready_stage_replay_v1 import (
    SCHEMA as NATIVE_GATE,
)
from general_rotation_source_eligibility_decision_ir_v1 import POLICY

SCHEMA="ZrotOriginalArcaneOrbExactSourceIFSpecPREDecisionV1"
PROFILE_GIT_BLOB="8d06eda4f69374dd1ed2e2d1eb8076b82cbbaf7f"
PRECOMBAT_SOURCE_LINE=(
 "actions.precombat+=/variable,name=aoe_count,op=set,"
 "value=2+(3*talent.spellfire_spheres)"
)
INT_KEYS=SYMBOLS[:-1]
FLOAT_KEY=SYMBOLS[-1]
TALENTS=("talent.splintering_sorcery","talent.spellfire_spheres",
         "talent.orb_mastery","talent.charged_orb")
BUFFS=("buff.arcane_charge.stack","buff.arcane_surge.stack",
       "buff.arcane_salvo.stack")

class OrbSpecPREReplayError(ValueError):
    pass

def need(ok:bool,code:str)->None:
    if not ok:raise OrbSpecPREReplayError(code)

def _parse(raw:list[str])->dict:
    need(len(raw)==len(SYMBOLS)==11,"SPEC_READY_PRE_FIELD_COUNT_DRIFT")
    result={}
    for index,key in enumerate(INT_KEYS):
        need(raw[index].isdigit(),"SPEC_RAW_CPP_INTEGER_PRE_INVALID_"+key)
        result[key]=int(raw[index])
    try:
        fraction=float(raw[10])
    except ValueError as e:
        raise OrbSpecPREReplayError("SPEC_RAW_CPP_CHARGES_FRACTION_NOT_NUMERIC") from e
    need(math.isfinite(fraction) and fraction>=0,
         "SPEC_RAW_CPP_CHARGES_FRACTION_OUT_OF_RANGE")
    result[FLOAT_KEY]=fraction
    need(result["ready_root_id"]>0 and result["at_simc_ms"]>=0 and
         1<=result["active_enemies"]<=40 and
         all(result[t] in (0,1) for t in TALENTS) and
         all(0<=result[b]<=50 for b in BUFFS),
         "ORIGINAL_MAGE_TALENT_BUFF_SOURCE_PRE_INVALID")
    return result

def _state_from_source(pre:dict)->tuple[dict,dict]:
    facts={k:pre[k] for k in TALENTS}
    facts.update({k:pre[k] for k in BUFFS})
    facts["active_enemies"]=pre["active_enemies"]
    facts[FLOAT_KEY]=pre[FLOAT_KEY]
    facts["buff.arcane_surge.down"]=1 if pre["buff.arcane_surge.stack"]==0 else 0
    # The APL variable is set precombat once in this source-profile, and
    # derived from separately source-observed Spellfire Spheres talent.
    # Do NOT say it was read directly from the native variable store.
    facts["variable.aoe_count"]=2+3*pre["talent.spellfire_spheres"]
    return facts,{
        "variable.aoe_count":{
            "value":facts["variable.aoe_count"],
            "provenance":"PINNED_PROFILE_PRECOMBAT_FORMULA_PLUS_ORIGINAL_TALENT_PRE",
            "direct_original_cpp_variable_read":False,
            "profile_precombat_line":PRECOMBAT_SOURCE_LINE,
            "precombat_action_confirmed_executed_at_root":False,
        },
        "buff.arcane_surge.down":{
            "value":facts["buff.arcane_surge.down"],
            "provenance":"EXACT_READY_ROOT_buff_t_check_zero",
        },
    }

def replay(log:str, gates:dict, profile:bytes,
           producer:dict, expected_targets:int)->dict:
    need(type(expected_targets) is int and expected_targets in (1,2),
         "PRE_TARGET_COUNT_UNPINNED")
    need(git_blob(profile)==PROFILE_GIT_BLOB,
         "DIFFERENT_ARCANE_PROFILE_CANNOT_USE_THIS_SOURCE_FORMULA")
    lines=profile.decode("utf8").splitlines()
    need(lines.count(PRECOMBAT_SOURCE_LINE)==1 and
         sum("variable,name=aoe_count" in l for l in lines)==1,
         "ORIGINAL_VARIABLE_AOE_COUNT_PRECOMBAT_REASSIGNMENT_AMBIGUOUS")
    need(producer.get("schema")==PRODUCER and
         producer.get("source_revision")==
           "b522cded8c26b97dac03fdf56e57a03ec7e8faa6" and
         producer.get("pristine_git_blob_sha1")==ORIGINAL_CPP_BLOB and
         producer.get("marker")==MARK and
         producer.get("source_pre_field_names")==list(SYMBOLS) and
         producer.get("original_CPP_base_ready_calls_per_virtual_ORB_invocation")==1 and
         producer.get("added_direct_action_ready_calls")==0 and
         producer.get("added_direct_rng_calls")==0 and
         producer.get("added_direct_cost_calls")==0 and
         producer.get("additional_read_only_buff_check_calls_per_orb_root")==3 and
         producer.get("additional_const_charges_fractional_calls_per_orb_root")==1 and
         gates.get("schema")==NATIVE_GATE and
         gates.get("product_policy_id")==POLICY and
         gates.get("source_original_CPP_branch_path_observed") is True and
         gates.get("independent_full_action_READY_gate_closure") is False,
         "ORIGINAL_NATIVE_SPEC_PRE_AND_GATE_CONTRACT_MISMATCH")

    source=parse_profile(profile,require_source=False)["action_lists"]
    expected={}
    for gate in gates["original_arcane_orb_ready_roots"]:
        rid=gate["original_ready_root_id"]
        need(type(rid) is int and rid>0 and rid not in expected,
             "DUPLICATE_CPP_ARCANE_READY_ROOT")
        expected[rid]=gate
    observed={}
    for line in log.splitlines():
        if MARK not in line:continue
        need(line.count(MARK)==1,"REPEATED_SPEC_PRE_MARKER")
        record=_parse(line.split(MARK,1)[1].strip().split("|"))
        rid=record["ready_root_id"]
        need(rid in expected and rid not in observed,
             "DUPLICATED_OR_FOREIGN_SPEC_READY_ROOT")
        observed[rid]=record
    need(set(observed)==set(expected),
         "NOT_ALL_ORIGINAL_ARCANE_ORB_ROOTS_HAVE_BEFORE_BASE_READY_SPEC_PRE")
    outcomes=Counter()
    selected=[]
    results=[]
    for rid,gate in sorted(expected.items()):
        pre=observed[rid]
        raw=gate["original_CPP_before_call_raw_PRE"]
        owner=gate["source_list"]
        ordinal=gate["source_ordinal"]
        need(pre["at_simc_ms"]==gate["at_simc_ms"]==
                 raw["simc_ms"] and
             pre["ready_root_id"]==rid==raw["original_CPP_ready_root_id"] and
             pre["active_enemies"]==expected_targets and
             owner in source and
             type(ordinal) is int and
             1<=ordinal<=len(source[owner]) and
             source[owner][ordinal-1]["source_sha256"]==
                gate["source_row_sha256"] and
             source[owner][ordinal-1]["action"]=="arcane_orb" and
             math.isclose(float(raw["cooldown_current_charge"]),
                          min(float(raw["cooldown_current_charge"]),
                              pre[FLOAT_KEY]),rel_tol=0.0,abs_tol=1e-7) and
             pre[FLOAT_KEY]<=raw["cooldown_max_charges"]+1e-7,
             "ACTUAL_READY_ROOT_SPEC_SOURCE_AND_PHYSICAL_CHARGE_DRIFT")
        fields,derived=_state_from_source(pre)
        original_if=source[owner][ordinal-1]["expression_fields"].get("if")
        expr=None if original_if is None else original_if["source"]
        if original_if is None:
            ast_result=None
            keys=[]
            result="NO_APL_IF"
        else:
            ast=original_if["ast"]
            keys=sorted(ast_symbols(ast))
            ast_result=truth(evaluate_ast(ast,fields))
            need(type(ast_result) is bool,
                 "STILL_UNOBSERVED_REAL_ARCANE_ORB_SOURCE_IF_OPERAND")
            result="INDEPENDENT_ORIGINAL_ROOT_SOURCE_AST_"+(
                "TRUE" if ast_result else "FALSE")
        native_stage=gate["original_CXX_action_ready_return_stage"]
        if native_stage=="ACTION_APL_IF_FALSE":
            need(ast_result is False,
                 "ORIGINAL_CPP_APL_IF_FALSE_CONFLICT_WITH_INDEPENDENT_PRE")
            outcomes["original_native_APL_IF_FALSE_matched_independent_PRE"]+=1
        elif native_stage=="ACTION_READY_TRUE":
            need(ast_result is True,
                 "ORIGINAL_CPP_READY_TRUE_WITH_FALSE_SOURCE_IF")
            outcomes["original_native_READY_TRUE_IF_PRE_matched"]+=1
        else:
            outcomes["original_cpp_short_circuited_before_APL_IF"]+=1
        outcomes[result]+=1
        outcomes["ready_root_spec_PRE_captured"]+=1
        if gate["source_CXX_POST_selection_boolean"]:
            selected.append({
                "root_id":rid,"simc_ms":pre["at_simc_ms"],
                "list":owner,"ordinal":ordinal,
                "talent_spellfire_spheres":pre["talent.spellfire_spheres"],
                "derived_aoe_count":fields["variable.aoe_count"],
                "arcane_charge_stack":pre["buff.arcane_charge.stack"],
                "arcane_salvo_stack":pre["buff.arcane_salvo.stack"],
                "arcane_surge_stack":pre["buff.arcane_surge.stack"],
                "orb_mastery_talent":pre["talent.orb_mastery"],
                "charged_orb_talent":pre["talent.charged_orb"],
                "fractional_charges":pre[FLOAT_KEY],
                "source_IF_result":result,
                "source_witness_not_independently_complete_ready":True,
            })
        results.append({
            "root_id":rid,"simc_ms":pre["at_simc_ms"],
            "source_list":owner,"source_ordinal":ordinal,
            "source_row_sha256":gate["source_row_sha256"],
            "original_cpp_SOURCE_RETURN_stage":native_stage,
            "source_IF_expression":expr,
            "source_IF_symbols":keys,
            "source_IF_independent_PRE_replay":ast_result,
            "IF_replay_classification":result,
            "original_CXX_IF_actually_evaluated":
                native_stage in ("ACTION_APL_IF_FALSE","ACTION_READY_TRUE"),
            "exact_original_spec_PRE":pre,
            "source_derived_state_with_separate_provenance":derived,
            "full_independent_ready_gate_set_closed":False,
            "dummy_feedback_verdict":"UNKNOWN",
        })
    need(len(results)==len(expected) and len(selected)==
         gates["counts"]["original_native_return_true"],
         "CPP_READY_AND_SPEC_PRE_INDEPENDENT_REPLAY_SIZE_DRIFT")
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "profile_git_blob_sha1":PROFILE_GIT_BLOB,
        "target_count":expected_targets,
        "counts":dict(sorted(outcomes.items())),
        "selected_original_cpp_arcane_orb_source_actions":selected,
        "all_source_root_independent_IF":results,
        "captured_same_original_CPP_root_ready_PRE":True,
        "source_derived_variable_is_not_direct_CPP_PRE":True,
        "independent_complete_action_READY":False,
        "independent_prior_physical_candidate_NOT_READY":False,
        "original_CPP_selected_action_is_not_user_cast":True,
        "WCL_strict_transition_PRE_proven":False,
        "WoW_client_addon_policy_compliance_tested":False,
        "WCL_API_calls":0,
    }

def selftest()->dict:
    valid=["0","27","2","1","0","1","0","4","0","12","1.5"]
    result=_parse(valid)
    assert result["ready_root_id"]==27
    facts,deriv=_state_from_source(result)
    assert facts["variable.aoe_count"]==2
    assert deriv["variable.aoe_count"]["direct_original_cpp_variable_read"] is False
    for index,v in ((3,"2"),(5,"-1"),(8,"NaN"),(10,"nan"),(1,"0"),(2,"0")):
        wrong=valid.copy()
        wrong[index]=v
        try:_parse(wrong)
        except OrbSpecPREReplayError:pass
        else:raise AssertionError("SYNTHETIC_SPEC_PRE_FRAUD_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":9,"native_CPP_actual_executed":False,
        "independent_COMPLETE_READY_proven":0,"WCL_API_calls":0
    }

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-native-log",type=Path)
    p.add_argument("--original-native-gates",type=Path)
    p.add_argument("--simc-profile",type=Path)
    p.add_argument("--producer",type=Path)
    p.add_argument("--target-count",type=int)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    args=(a.original_native_log,a.original_native_gates,a.simc_profile,
          a.producer,a.target_count)
    if all(x is None for x in args):
        result=selftest()
    elif all(x is not None for x in args):
        result=replay(
            a.original_native_log.read_text(encoding="utf8"),
            json.loads(a.original_native_gates.read_bytes()),
            a.simc_profile.read_bytes(),
            json.loads(a.producer.read_bytes()),a.target_count)
    else:p.error("all original Native root log/gates/actual profile/producer/targets are required")
    buf=(json.dumps(result,sort_keys=True,separators=(",",":"),
                    allow_nan=False)+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(buf)
    else:
        import sys
        sys.stdout.buffer.write(buf)

if __name__=="__main__":main()
