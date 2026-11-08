#!/usr/bin/env python3
"""Generic source-pinned SimC IF/ELSE state-conditioned research evaluator.

Core: existing typed APL parser + existing independent gate proof engine.
State: strictly validated external PRE values, distinctly scoped local APL
variable effects. Source CALL and RUN remain different; controls are UNKNOWN
unless *explicitly synthetic* assumptions are passed for tests, never a
positive gameplay proof. Every earlier candidate includes a reason.

No Native selected return, WCL cast, or Hekili recommendation may supply a
READY fact. A source-ready result here is hypothetical, not proof of actual
SimC native parity, player optimality, or a target-dummy mistake.

Zero arguments: deterministic offline synthetic regression for PyCharm.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path

from simc_apl_semantic_ir_v2 import (
    parse_profile, git_blob, canonical, ast_symbols, evaluate_ast,
    truth, variable_effect, AplError
)
from general_rotation_ir_proof_replay_v1 import (
    CandidateEvidence, source_pre_facts, ProofReplayError
)
from general_rotation_decision_proof_engine_v1 import (
    Identity, decide_candidate, READY, NOT_READY, UNKNOWN,
)
from general_rotation_source_hypothesis_ir_v1 import compile_profile

SCHEMA="ZrotGenericSimCStateConditionedCandidateEvaluatorV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SOURCE_BEHAVIORS={
    "ACTION","VARIABLE","CALL","RUN","SWAP_UNSUPPORTED",
    "SIDE_EFFECT_SOURCE_MODEL_UNVERIFIED"
}
CONTROL_ASSUME="SYNTHETIC_CONTROL_ASSUMED_READY"

class StateConditionedError(ValueError): pass

def must(value:bool,code:str)->None:
    if not value:raise StateConditionedError(code)

def evaluate(raw:bytes,expected_git_blob:str, *,
             at_ms:int,
             external_strict_pre:dict,
             proofs:dict[tuple[str,int],CandidateEvidence]|None=None,
             synthetic_control_ready:set[tuple[str,int]]|None=None,
             start_list:str="default",
             occurrence:int=0,
             max_rows:int=400)->dict:
    """One bounded original APL source selection scan; no future state prediction."""
    must(type(at_ms) is int and at_ms>=0 and
         type(occurrence) is int and occurrence>=0 and
         type(max_rows) is int and 0<max_rows<=10000,
         "SOURCE_EVALUATION_TIME_OR_BUDGET_INVALID")
    must(isinstance(expected_git_blob,str) and
         git_blob(raw)==expected_git_blob,
         "SOURCE_PROFILE_GIT_BLOB_MISMATCH")
    parsed=parse_profile(raw,require_source=True,
                         expected_git_blob=expected_git_blob)
    lists=parsed["action_lists"]
    must(start_list in lists,"START_LIST_NOT_PRESENT_IN_SOURCE")
    # An input fact is accepted only if independently receipted and strictly
    # BEFORE the examined action time; no zero-filling or same-time leak.
    try:
        clean=source_pre_facts(external_strict_pre,at_ms=at_ms)
    except ProofReplayError as e:
        raise StateConditionedError("INVALID_WCL_STRICT_PRE_SOURCE_FACT") from e
    # After temporal validation, project only these approved numeric values
    # into the internal source interpreter. A locally computed SimC variable
    # may then be a number without impersonating a WCL Strict PRE event.
    env={k:v["value"] for k,v in clean.items()}
    source_external_keys=set(env)
    derived={}
    evidence=proofs if proofs is not None else {}
    ctrl=synthetic_control_ready if synthetic_control_ready is not None else set()
    must(isinstance(evidence,dict) and isinstance(ctrl,set),
         "READINESS_PROOF_OR_CONTROL_ASSUMPTION_NOT_MAPPING")
    for key,claim in evidence.items():
        must(isinstance(key,tuple) and len(key)==2 and
             isinstance(key[0],str) and type(key[1]) is int and
             key[0] in lists and 0<=key[1]<len(lists[key[0]]) and
             isinstance(claim,CandidateEvidence),
             "ORPHAN_OR_INVALID_SOURCE_GATE_PROOF")
    for key in ctrl:
        must(isinstance(key,tuple) and len(key)==2 and
             key[0] in lists and type(key[1]) is int and
             0<=key[1]<len(lists[key[0]]) and
             lists[key[0]][key[1]]["behavior"] in ("CALL","RUN"),
             "SYNTHETIC_CONTROL_ASSUMPTION_FOR_NON_CONTROL_ROW")
    ledger=[]
    counts=Counter()
    budget=0
    assumptions=bool(ctrl)
    def ready_for(name:str,row:dict):
        idx=row["index"]
        claim=evidence.get((name,idx))
        if claim is None:
            return UNKNOWN,["INDEPENDENT_PHYSICAL_READY_GATE_NOT_SUPPLIED"]
        expected=Identity(
            scope=name+"::"+row["action"],
            source_sha256=row["source_sha256"],
            t_ms=at_ms,ordinal=idx,occurrence=occurrence)
        must(claim.identity==expected and
             claim.contract.source_sha256==row["source_sha256"],
             "SOURCE_GATE_IDENTITY_TIME_OCCURRENCE_OR_SHA_MISMATCH")
        verdict=decide_candidate(
            claim.identity,claim.contract,claim.facts,
            is_physical_action=row["behavior"]=="ACTION")
        status=verdict["decision"]
        blockers=verdict["blockers"]
        # A non-IF source option has unresolved action semantics unless an
        # independent SpecAdapter supports it; a true guard doesn't erase it.
        option_keys={v["key"] for v in row["attributes"]}
        if status==READY and option_keys-{"if"}:
            status=UNKNOWN
            blockers=["UNMODELLED_NON_IF_ACTION_OPTIONS"]
        return status,blockers
    def walk(name:str,stack:tuple[str,...]):
        nonlocal budget
        must(name in lists and name not in stack,
             "DYNAMIC_CALL_RECURSION_OR_MISSING_SOURCE_LIST")
        for row in lists[name]:
            budget+=1
            if budget>max_rows:
                counts["UNKNOWN"]+=1
                return {"status":"UNKNOWN","reason":"EVALUATION_BUDGET_EXHAUSTED"}
            behavior=row["behavior"]
            must(behavior in SOURCE_BEHAVIORS,
                 "UNSUPPORTED_GENERIC_SOURCE_BEHAVIOR")
            fields=row["expression_fields"]
            expr=fields.get("if")
            symbols=sorted(ast_symbols(expr["ast"])) if expr else []
            # Only prevalidated external PRE or locally derived APL values
            # enter evaluate_ast; strict_pre=False is safe *after* validation.
            result=truth(evaluate_ast(expr["ast"],env)) if expr else True
            missing=[s for s in symbols if s not in env]
            record={
                "source_list":name,"priority_ordinal":row["index"]+1,
                "source_line":row["source_line"],
                "source_row_sha256":row["source_sha256"],
                "action":row["action"],"behavior":behavior,
                "if_source":expr["source"] if expr else None,
                "if_result":("UNKNOWN" if result is None else
                             "TRUE" if result else "FALSE"),
                "source_missing_operand_names":missing,
                "readiness":None,
                "reason":None,
                "ready_gate_contract_result_not_global_native_verification":False,
                "user_cast_or_rotation_optimality_proven":False,
            }
            ledger.append(record)
            if result is False:
                record["reason"]="SOURCE_APL_IF_FALSE"
                counts["IF_FALSE"]+=1
                continue
            if result is None:
                record["reason"]="SOURCE_APL_IF_UNKNOWN"
                counts["UNKNOWN"]+=1
                return {"status":"UNKNOWN","reason":"SOURCE_APL_IF_UNKNOWN",
                        "blocking_source":record["source_row_sha256"]}
            if behavior=="VARIABLE":
                try:effect=variable_effect(row,env,strict_pre=False)
                except (AplError,ValueError) as e:
                    raise StateConditionedError(
                        "INVALID_SOURCE_VARIABLE_EXPRESSION") from e
                record["variable_effect"]=effect
                if effect["status"]!="EVALUATED":
                    record["reason"]="VARIABLE_SEMANTICS_OR_OPERAND_UNKNOWN"
                    counts["UNKNOWN"]+=1
                    return {"status":"UNKNOWN","reason":record["reason"],
                            "blocking_source":record["source_row_sha256"]}
                target="variable."+effect["name"]
                # Runtime-derived SimC variables do not rewrite external PRE.
                must(target not in source_external_keys,
                     "SOURCE_VARIABLE_CONFLICTS_WITH_STRICT_EXTERNAL_PRE")
                v=effect["value"]
                must(type(v) in (float,int) and math.isfinite(v),
                     "UNTRUSTED_VARIABLE_RESULT")
                env[target]=v
                derived[target]={
                    "value":v,
                    "source_row_sha256":row["source_sha256"],
                    "source_list":name,"source_ordinal":row["index"]+1,
                    "provenance":"SIMC_SOURCE_VARIABLE_DERIVED_THIS_SCAN",
                    "actual_original_CPP_variable_assignment_verified":False,
                    "WCL_STRICT_PRE_observation":False,
                }
                record["reason"]="SIMC_SOURCE_VARIABLE_DERIVED_THIS_SCAN"
                counts["VARIABLE_DERIVED"]+=1
                continue
            if behavior in ("CALL","RUN"):
                if (name,row["index"]) not in ctrl:
                    record["readiness"]=UNKNOWN
                    record["reason"]="CONTROL_NATIVE_READINESS_UNPROVEN"
                    counts["UNKNOWN"]+=1
                    return {"status":"UNKNOWN","reason":record["reason"],
                            "blocking_source":record["source_row_sha256"]}
                record["readiness"]=CONTROL_ASSUME
                record["reason"]="SYNTHETIC_ONLY_CONTROL_GUARD"
                counts["SYNTHETIC_CONTROL"]+=1
                target=next((a["value"] for a in row["attributes"]
                             if a["key"]=="name"),None)
                must(target in lists,
                     "SOURCE_CONTROL_DESTINATION_MISSING")
                if behavior=="RUN":
                    return {
                        "status":"SYNTHETIC_QUEUED_RUN_CONTROL_NOT_SPELL",
                        "source_list":name,"source_ordinal":row["index"]+1,
                        "next_list_if_EXECUTE_observed":target,
                        "target_list_executed_now":False,
                        "actual_native_execute_event_proven":False,
                    }
                nested=walk(target,stack+(name,))
                if nested is None:
                    record["reason"]="SYNTHETIC_CALL_CHILD_EMPTY_FALLBACK"
                    continue
                return nested
            if behavior!="ACTION":
                record["reason"]="SOURCE_NON_PHYSICAL_EFFECT_UNVERIFIED"
                counts["UNKNOWN"]+=1
                return {"status":"UNKNOWN","reason":record["reason"],
                        "blocking_source":record["source_row_sha256"]}
            status,why=ready_for(name,row)
            record["readiness"]=status
            record["ready_gate_blockers"]=why
            record["ready_gate_contract_result_not_global_native_verification"]=status!=UNKNOWN
            if status==NOT_READY:
                record["reason"]="INDEPENDENT_NECESSARY_GATE_FALSE"
                counts["READY_FALSE"]+=1
                continue
            if status==UNKNOWN:
                record["reason"]="FULL_READY_SOURCE_PROOF_UNKNOWN"
                counts["UNKNOWN"]+=1
                return {"status":"UNKNOWN","reason":record["reason"],
                        "blocking_source":record["source_row_sha256"]}
            record["reason"]="SOURCE_FULL_GATE_CONTRACT_CLOSED"
            counts["SYNTHETIC_PROVEN_GATE_SELECTION"]+=1
            return {
                "status":"HYPOTHETICAL_SOURCE_CHOICE_NOT_NATIVE_OR_WCL",
                "action":row["action"],
                "source_list":name,"source_ordinal":row["index"]+1,
                "source_row_sha256":row["source_sha256"],
                "synthetic_or_external_gate_certificate_provided":True,
                "real_native_parity_proven":False,
            }
        return None
    result=walk(start_list,())
    if result is None:
        result={"status":"NO_ELIGIBLE_ACTION_UNDER_SUPPLIED_SOURCE_CONTRACT",
                "real_native_no_action_equivalence_proven":False}
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "source_git_blob_sha1":expected_git_blob,
        "decision_at_ms":at_ms,"source_occurrence":occurrence,
        "evaluated_start_list":start_list,
        "input_external_PRE_observation_count":len(clean),
        "input_external_PRE_time_contract":"STRICTLY_BEFORE_ACTION_T",
        "source_local_variables":derived,
        "source_reason_ledger":ledger,
        "reason_counts":dict(sorted(counts.items())),
        "result":result,
        "synthetic_control_assumptions_used":assumptions,
        "derived_variables_not_external_WCL_PRE":True,
        "entire_original_SimC_native_runtime_parity_verified":False,
        "WoW_combat_addon_state_observed":False,
        "WCL_blind_independent_holdout_done":False,
        "dummy_trainer_error_permitted":False,
        "WCL_API_calls":0,
    }

def selftest()->dict:
    from general_rotation_decision_proof_engine_v1 import (
        GateContract,Fact,DecisionProofError
    )
    source=(b"actions=variable,name=threshold,op=set,value=30\n"
            b"actions+=/call_action_list,name=sub,if=active_enemies=1\n"
            b"actions+=/blast,if=rage>=variable.threshold\n"
            b"actions.sub=alpha,if=buff.x.up\n")
    blob=git_blob(source)
    parsed=parse_profile(source,require_source=True,expected_git_blob=blob)
    blast=parsed["action_lists"]["default"][2]
    ident=Identity(scope="default::blast",source_sha256=blast["source_sha256"],
                   t_ms=100,ordinal=2,occurrence=0)
    contract=GateContract(source="SYNTHETIC_COMPLETE_ROUTE",
                          required=("test_ready",),
                          source_sha256=ident.source_sha256,
                          closed=True,closure_receipt="SYNTHETIC_ONLY")
    def fact(ok:bool)->Fact:
        return Fact(identity=ident,gate="test_ready",value=ok,
                    basis="INDEPENDENT_SOURCE_REPLAY",
                    captured="SIMC_ORIGINAL_METHOD_PRE",
                    event_t_ms=100,receipt="SYNTHETIC_ONLY")
    def pre(**values):
        return {k:{"value":v,"timestamp":99,
                   "provenance":"STRICT_PRE_OBSERVATION",
                   "receipt":"SYNTHETIC_PRE_ONLY"} for k,v in values.items()}
    proof={( "default",2):CandidateEvidence(ident,contract,(fact(True),))}
    a=evaluate(source,blob,at_ms=100,
        external_strict_pre=pre(rage=40,active_enemies=2),
        proofs=proof)
    assert a["result"]["action"]=="blast"
    assert a["source_local_variables"]["variable.threshold"]["value"]==30.0
    assert a["source_local_variables"]["variable.threshold"][
            "WCL_STRICT_PRE_observation"] is False
    assert a["source_reason_ledger"][1]["reason"]=="SOURCE_APL_IF_FALSE"
    b=evaluate(source,blob,at_ms=100,
        external_strict_pre=pre(rage=20,active_enemies=2),proofs=proof)
    assert b["result"]["status"].startswith("NO_ELIGIBLE_ACTION")
    c=evaluate(source,blob,at_ms=100,
        external_strict_pre=pre(active_enemies=2),proofs=proof)
    assert c["result"]["status"]=="UNKNOWN"
    d=evaluate(source,blob,at_ms=100,
        external_strict_pre=pre(rage=40,active_enemies=2))
    assert d["result"]["reason"]=="FULL_READY_SOURCE_PROOF_UNKNOWN"
    negative={( "default",2):CandidateEvidence(ident,contract,(fact(False),))}
    n=evaluate(source,blob,at_ms=100,
        external_strict_pre=pre(rage=40,active_enemies=2),proofs=negative)
    assert n["source_reason_ledger"][-1]["readiness"]==NOT_READY
    e=evaluate(source,blob,at_ms=100,
        external_strict_pre=pre(rage=40,active_enemies=1),
        proofs=proof,synthetic_control_ready={("default",1)})
    assert e["result"]["status"]=="UNKNOWN"  # child alpha missing evidence
    run_source=source.replace(b"call_action_list",b"run_action_list")
    run=evaluate(run_source,git_blob(run_source),at_ms=100,
        external_strict_pre=pre(active_enemies=1),
        synthetic_control_ready={("default",1)})
    assert run["result"]["status"]=="SYNTHETIC_QUEUED_RUN_CONTROL_NOT_SPELL"
    assert run["result"]["target_list_executed_now"] is False
    assert run["result"]["actual_native_execute_event_proven"] is False
    # Opener action at t=0: only PRE from t<0 is admissible.
    opener=evaluate(source,blob,at_ms=0,
        external_strict_pre={
            "active_enemies":{"value":2,"timestamp":-1,
             "provenance":"STRICT_PRE_OBSERVATION","receipt":"SYNTHETIC_NEGATIVE_PRE"}})
    assert opener["result"]["status"]=="UNKNOWN"
    assert opener["decision_at_ms"]==0
    try:
        evaluate(source,blob,at_ms=0,
            external_strict_pre={
              "active_enemies":{"value":2,"timestamp":0,
               "provenance":"STRICT_PRE_OBSERVATION","receipt":"SYNTHETIC_SAME_T"}})
    except StateConditionedError:pass
    else:raise AssertionError("OPENER_SAME_TIMESTAMP_STATE_LEAKAGE")
    for fake in (
       {"rage":{"value":40,"timestamp":100,
                "provenance":"STRICT_PRE_OBSERVATION","receipt":"x"}},
       {"rage":40},
    ):
        try:evaluate(source,blob,at_ms=100,external_strict_pre=fake)
        except StateConditionedError:pass
        else:raise AssertionError("UNVERIFIED_EXTERNAL_STATE_ACCEPTED")
    badproof=CandidateEvidence(
        Identity(scope="default::blast",source_sha256=ident.source_sha256,
                 t_ms=101,ordinal=2,occurrence=0),
        contract,(fact(True),))
    try:evaluate(source,blob,at_ms=100,
                 external_strict_pre=pre(rage=40,active_enemies=2),
                 proofs={("default",2):badproof})
    except StateConditionedError:pass
    else:raise AssertionError("FOREIGN_TIME_GATE_EVIDENCE_ACCEPTED")
    try:evaluate(source,blob,at_ms=100,external_strict_pre={},
                 synthetic_control_ready={("default",2)})
    except StateConditionedError:pass
    else:raise AssertionError("PHYSICAL_ACTION_LAUNDERED_AS_CONTROL")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":14,"source_variables_work_after_STRICT_PRE_projection":True,
        "source_CALL_RUN_distinct_without_native_promotion":True,
        "actual_CPP_or_WCL_executed":False,"WCL_API_calls":0
    }

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path)
    p.add_argument("--expected-git-blob")
    p.add_argument("--snapshot",type=Path,
                   help="Strict PRE numeric JSON dictionary with receipts")
    p.add_argument("--at-ms",type=int)
    p.add_argument("--start-list",default="default")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.profile is None and a.snapshot is None and a.at_ms is None:
        result=selftest()
    elif a.profile is not None and a.snapshot is not None and a.at_ms is not None:
        must(a.profile.suffix==".simc","PROFILE_EXTENSION_INVALID")
        raw=a.profile.read_bytes()
        result=evaluate(
            raw,a.expected_git_blob or git_blob(raw),
            at_ms=a.at_ms,
            external_strict_pre=json.loads(a.snapshot.read_bytes()),
            start_list=a.start_list)
    else:p.error("--profile, --snapshot and --at-ms are required together")
    encoded=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(encoded)
        print("STATE_CONDITIONED_SOURCE_RESEARCH_IR_SHA256="+sha256(encoded).hexdigest())
        print("STATE_CONDITIONED_SOURCE_RESEARCH_IR_OUTPUT="+str(a.out))
    else:
        import sys
        sys.stdout.buffer.write(encoded)

if __name__=="__main__":main()
