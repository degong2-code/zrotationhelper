#!/usr/bin/env python3
"""Spec-neutral proof-carrying General Rotation IR decision replay.

Reuse source-pinned official SimC typed APL parser, its existing bounded
CALL/RUN/variable evaluator, and the independent tri-state READY proof core.
Never infer readiness from APL order, observed Native choice, WCL cast,
guide, skill frequency or unobserved addon state.

Required positive claim: exact action-row/time/occurrence identity, fully
independent true source gates, declared exhaustive route closure, and no
unmodelled source option. Otherwise UNKNOWN. Necessary false can exclude an
exact candidate, but external negative claims do not establish optimality.
The output is always an offline research hypothesis, NOT a validated opener,
real WoW recommendation or trainer error verdict.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from simc_apl_semantic_ir_v2 import (
    parse_profile, bounded_decision, canonical, git_blob, AplError
)
from general_rotation_source_hypothesis_ir_v1 import (
    compile_profile, HypothesisIRError
)
from general_rotation_simc_multi_spec_cold_start_v1 import load_manifest
from general_rotation_decision_proof_engine_v1 import (
    Identity, Fact, GateContract, decide_candidate, UNKNOWN, READY, NOT_READY,
    DecisionProofError
)

SCHEMA="ZrotGeneralRotationIRProofCarryingDecisionReplayV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

class ProofReplayError(ValueError): pass

@dataclass(frozen=True)
class CandidateEvidence:
    identity: Identity
    contract: GateContract
    facts: tuple[Fact,...]

def strict_source_row_checks(model:dict,parsed:dict):
    graph=model["source_only_priority_graph"]
    if model["source_git_blob"]!=parsed["source_git_blob_sha1"]:
        raise ProofReplayError("SOURCE_PROFILE_BLOB_MISMATCH")
    if set(graph["lists"])!=set(parsed["action_lists"]):
        raise ProofReplayError("SOURCE_APL_LIST_SET_MISMATCH")
    if graph["edges"]!=parsed["graph_edges"]:
        raise ProofReplayError("SOURCE_APL_CONTROL_GRAPH_CHANGED")
    for name,rows in graph["lists"].items():
        src_rows=parsed["action_lists"][name]
        if len(src_rows)!=len(rows):
            raise ProofReplayError("SOURCE_APL_ROW_COUNT_CHANGED")
        for i,(hyp,src) in enumerate(zip(rows,src_rows)):
            ident=hyp["identity"]
            if (ident["source_list"]!=name or ident["source_index"]!=i or
                ident["source_line"]!=src["source_line"] or
                ident["source_line_sha256"]!=src["source_sha256"] or
                hyp["source_text"]!=src["source_text"] or
                hyp["action"]!=src["action"] or hyp["behavior"]!=src["behavior"] or
                hyp["source_priority_ordinal"]!=i):
                raise ProofReplayError("SOURCE_APL_ROW_FINGERPRINT_OR_ORDER_CHANGED")
            conditions=hyp["conditions"]
            if set(conditions)!=set(src["expression_fields"]):
                raise ProofReplayError("SOURCE_EXPRESSION_FIELDS_CHANGED")
            for field,expr in src["expression_fields"].items():
                if (conditions[field]["source_ast"]!=expr["ast"] or
                    conditions[field]["raw_expression"]!=expr["source"] or
                    conditions[field]["symbols"]!=expr["symbols"]):
                    raise ProofReplayError("SOURCE_TYPED_EXPRESSION_DRIFT")

def source_pre_facts(records:dict, *, at_ms:int)->dict:
    """Explicit numeric facts. No bare numbers; no same-time/future facts.

    This is an offline input validator, not a raw-WCL data source verifier.
    WCL heldout snapshots need independent source provenance validation
    upstream before their numbers may be provided here.
    """
    if not isinstance(records,dict) or type(at_ms) is not int or at_ms<0:
        raise ProofReplayError("SOURCE_PRE_NUMERIC_FACTS_OR_TIME_INVALID")
    clean={}
    for symbol,record in records.items():
        if not isinstance(symbol,str) or not symbol or not isinstance(record,dict):
            raise ProofReplayError("SOURCE_PRE_NUMERIC_RECORD_INVALID")
        if set(record)!={"value","timestamp","provenance","receipt"}:
            raise ProofReplayError("SOURCE_PRE_RECORD_MUST_BE_EXACT_AND_RECEIPTED")
        if (record["provenance"]!="STRICT_PRE_OBSERVATION" or
            not isinstance(record["receipt"],str) or not record["receipt"] or
            type(record["timestamp"]) is not int or
            record["timestamp"]>=at_ms):
            raise ProofReplayError("SOURCE_PRE_SAME_TIME_FUTURE_OR_UNVERIFIED")
        value=record["value"]
        if type(value) not in (int,float):
            raise ProofReplayError("NUMERIC_PRE_FACT_MUST_BE_EXPLICIT")
        import math
        if not math.isfinite(value):
            raise ProofReplayError("NONFINITE_SOURCE_PRE_VALUE")
        clean[symbol]={
            "value":value,"timestamp":record["timestamp"],
            "provenance":record["provenance"]
        }
    return clean

def evaluate(model:dict,raw:bytes,at_ms:int,
             numeric_pre:dict,
             candidate_evidence:dict[tuple[str,int],CandidateEvidence]|None=None,
             *, start_list="default",occurrence:int=0)->dict:
    if model.get("schema")!="ZrotGeneralRotationSourceHypothesisIRV1":
        raise ProofReplayError("SOURCE_GENERAL_ROTATION_IR_SCHEMA_INVALID")
    if model.get("policy")!=POLICY or model.get("source_git_blob")!=git_blob(raw):
        raise ProofReplayError("UNPINNED_SOURCE_GENERAL_ROTATION_IR")
    if type(occurrence) is not int or occurrence<0:
        raise ProofReplayError("ACTION_OCCURRENCE_INVALID")
    parsed=parse_profile(raw,require_source=True,
                         expected_git_blob=model["source_git_blob"])
    strict_source_row_checks(model,parsed)
    safe_pre=source_pre_facts(numeric_pre,at_ms=at_ms)
    evidence=candidate_evidence or {}
    if not isinstance(evidence,dict):
        raise ProofReplayError("CANDIDATE_PROOF_MAPPING_INVALID")
    readiness={}
    proof_rows=[]
    counts=Counter()
    for source_list,rows in model["source_only_priority_graph"]["lists"].items():
        for idx,row in enumerate(rows):
            key=(source_list,idx)
            claim=evidence.get(key)
            status=UNKNOWN
            blockers=["NO_INDEPENDENT_SOURCE_ROUTE_AND_STATE_PROOF"]
            if claim is not None:
                if not isinstance(claim,CandidateEvidence):
                    raise ProofReplayError("CANDIDATE_PROOF_OBJECT_INVALID")
                ident=row["identity"]
                expected_id=Identity(
                    scope=source_list+"::"+row["action"],
                    source_sha256=ident["source_line_sha256"],
                    t_ms=at_ms,ordinal=idx,occurrence=occurrence
                )
                if claim.identity!=expected_id:
                    raise ProofReplayError("SOURCE_PROOF_ACTION_TIME_OR_OCCURRENCE_MISMATCH")
                if claim.contract.source_sha256!=expected_id.source_sha256:
                    raise ProofReplayError("SOURCE_ROUTE_CONTRACT_NOT_ON_THIS_ROW")
                # The current runtime does not independently implement
                # control action readiness or source option attributes.
                # Never leak a positive proof through an unsupported
                # target_if, moving, cycle, target_number, etc.
                source=row["source_text"]
                parsed_row=parsed["action_lists"][source_list][idx]
                attr_names={a["key"] for a in parsed_row["attributes"]}
                is_regular=(row["kind"]=="EXECUTABLE_SOURCE_CANDIDATE" and
                            row["behavior"]=="ACTION")
                verdict=decide_candidate(
                    claim.identity,claim.contract,claim.facts,
                    is_physical_action=is_regular
                )
                status=verdict["decision"]
                blockers=verdict["blockers"]
                if status==READY and attr_names-{"if"}:
                    status=UNKNOWN
                    blockers=["UNMODELLED_NON_IF_SOURCE_OPTIONS"]
                # Even a proof of a control row may not be treated as a
                # physical spell or as implicit source control action ready.
                if not is_regular:
                    status=UNKNOWN
                    blockers=["SOURCE_CONTROL_OR_SIDE_EFFECT_ROUTE_UNVERIFIED"]
                if (status==NOT_READY and not is_regular):
                    status=UNKNOWN
            readiness[source_list+":"+str(idx)]=status
            counts["source_"+status]+=1
            if claim is not None:
                proof_rows.append({
                    "source_list":source_list,
                    "source_index":idx,
                    "source_line_sha256":row["identity"]["source_line_sha256"],
                    "proof_status":status,
                    "blockers":blockers,
                    "native_observed_ready_used":False,
                })
    # All supplied evidence must match an exact original source row.
    for key in evidence:
        if (not isinstance(key,tuple) or len(key)!=2 or
            type(key[0]) is not str or type(key[1]) is not int or
            key[0] not in model["source_only_priority_graph"]["lists"] or
            not 0<=key[1]<len(model["source_only_priority_graph"]["lists"][key[0]])):
            raise ProofReplayError("ORPHAN_OR_UNPINNED_CANDIDATE_PROOF")
    try:
        result=bounded_decision(parsed,safe_pre,readiness,
                                timestamp=at_ms,start_list=start_list,
                                strict_pre=True)
    except AplError as exc:
        raise ProofReplayError("BOUNDED_APL_EVALUATOR_REJECTED_SOURCE") from exc
    outcome=result["result"]
    action_source=None
    if outcome["verdict"]=="HYPOTHETICAL_SOURCE_ROW":
        name=outcome["list"];idx=outcome["index"]
        winner=model["source_only_priority_graph"]["lists"][name][idx]
        if (winner["kind"]!="EXECUTABLE_SOURCE_CANDIDATE" or
            winner["behavior"]!="ACTION" or
            readiness[name+":"+str(idx)]!=READY):
            raise ProofReplayError("NON_EXECUTABLE_OR_UNKNOWN_SOURCE_ROW_SELECTED")
        action_source={
            "source_list":name,
            "source_index":idx,
            "source_line_sha256":winner["identity"]["source_line_sha256"],
            "source_action":winner["action"],
            "status":"HYPOTHETICAL_ONLY_NOT_NATIVE_OR_WCL_VERIFIED",
        }
    return {
        "schema":SCHEMA,"policy":POLICY,
        "source_spec":model["spec_key"],"class_key":model["class_key"],
        "source_git_blob":model["source_git_blob"],
        "decision_at_ms":at_ms,"source_occurrence":occurrence,
        "start_list":start_list,
        "source_typed_graph_verified":True,
        "candidate_proof_counts":dict(sorted(counts.items())),
        "source_proof_details":proof_rows,
        "bounded_source_result":outcome,
        "consulted_source_rows":result["consulted_source_rows"],
        "hypothetical_selected_source_row":action_source,
        "Native_spell_READY_proven":False,
        "WCL_independent_holdout_verified":False,
        "dummy_feedback_permitted":False,
        "source_order_optimality_proven":False,
        "WCL_API_calls":0,"MAIN_promoted":False
    }

def selftest()->dict:
    sample=(
        b"actions=alpha,if=active_enemies>=2\n"
        b"actions+=/beta,if=active_enemies<2\n"
    )
    from simc_apl_semantic_ir_v2 import git_blob
    m=compile_profile(sample,{"key":"sample_a","class_key":"class_a",
                              "git_blob":git_blob(sample)})
    rows=m["source_only_priority_graph"]["lists"]["default"]
    h=rows[1]["identity"]["source_line_sha256"]
    ident=Identity("default::beta",h,100,1,0)
    gates=GateContract("sample_a",("cooldown","resource","target"),h,
                       closed=True,closure_receipt="SYNTHETIC_ALL_ROUTE_CLOSED")
    proof=CandidateEvidence(ident,gates,tuple(
        Fact(ident,gate,True,"INDEPENDENT_WCL_PRE","WCL_STRICT_PRE",
             99,"SYNTHETIC_VERIFIED_TRANSITION")
        for gate in gates.required
    ))
    def pre(value,t=99):
        return {"active_enemies":{
            "value":value,"timestamp":t,
            "provenance":"STRICT_PRE_OBSERVATION",
            "receipt":"SYNTHETIC_NOT_REAL_WCL"}}
    yes=evaluate(m,sample,100,pre(1),{("default",1):proof})
    assert yes["bounded_source_result"]["verdict"]=="HYPOTHETICAL_SOURCE_ROW"
    assert yes["hypothetical_selected_source_row"]["source_action"]=="beta"
    assert yes["candidate_proof_counts"]["source_READY"]==1
    assert yes["dummy_feedback_permitted"] is False
    no=evaluate(m,sample,100,pre(1))
    assert no["bounded_source_result"]["reason"]=="ACTION_READINESS_UNOBSERVED"
    first=evaluate(m,sample,100,pre(2),{("default",1):proof})
    assert first["bounded_source_result"]["reason"]=="ACTION_READINESS_UNOBSERVED"
    blocked=evaluate(m,sample,100,pre(1,100),{("default",1):proof}) if False else None
    try:evaluate(m,sample,100,pre(1,100),{("default",1):proof})
    except ProofReplayError:pass
    else:raise AssertionError("SAME_TIME_PRE_ACCEPTED")
    try:evaluate(m,sample,100,pre(1),{("default",0):proof})
    except ProofReplayError:pass
    else:raise AssertionError("OTHER_ROW_PROOF_ACCEPTED")
    try:evaluate(m,sample,100,pre(1),{("default",5):proof})
    except ProofReplayError:pass
    else:raise AssertionError("ORPHAN_PROOF_ACCEPTED")
    wrong=dict(m,source_git_blob="a"*40)
    try:evaluate(wrong,sample,100,pre(1))
    except ProofReplayError:pass
    else:raise AssertionError("UNPINNED_IR_ACCEPTED")
    options=(b"actions=beta,cycle_targets=1\n")
    special=compile_profile(options,{"key":"sample_b","class_key":"class_b",
                             "git_blob":git_blob(options)})
    sha=special["source_only_priority_graph"]["lists"]["default"][0]["identity"]["source_line_sha256"]
    id2=Identity("default::beta",sha,100,0,0)
    ctr=GateContract("sample_b",("ready",),sha,
                     closed=True,closure_receipt="SYNTHETIC_CLOSED")
    ev=CandidateEvidence(id2,ctr,(Fact(id2,"ready",True,
               "INDEPENDENT_WCL_PRE","WCL_STRICT_PRE",99,"synthetic"),))
    fail=evaluate(special,options,100,{},{("default",0):ev})
    assert fail["bounded_source_result"]["reason"]=="ACTION_READINESS_UNOBSERVED"
    assert fail["candidate_proof_counts"]["source_READY"]==0
    control=b"actions=call_action_list,name=inner\nactions.inner=alpha\n"
    cm=compile_profile(control,{"key":"sample_c","class_key":"class_c",
                                "git_blob":git_blob(control)})
    z=evaluate(cm,control,100,{})
    assert z["bounded_source_result"]["reason"]=="ACTION_READINESS_UNOBSERVED"
    assert z["dummy_feedback_permitted"] is False
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":15,"generic_classes":3,
        "simc_original_Native_not_run":True,
        "real_WCL_holdout_not_run":True,
        "all_positive_READINESS_claims_synthetic_only":True,
        "WCL_API_calls":0,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.source_root and args.manifest:
        manifest=load_manifest(args.manifest)
        root=args.source_root.resolve(strict=True)
        rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                           check=True,capture_output=True,text=True).stdout.strip()
        if rev!=manifest["official_simc_commit"]:
            raise ProofReplayError("OFFICIAL_SIMC_SOURCE_PIN_DRIFT")
        reports=[]
        for spec in manifest["profiles"]:
            raw=(root/spec["profile"]).resolve(strict=True).read_bytes()
            model=compile_profile(raw,spec)
            # Without independently replayed state, no successful Native
            # readiness can be inferred from any source APL row.
            report=evaluate(model,raw,100,{},start_list="default")
            reports.append(report)
        result={"schema":"ZrotMultiSpecGeneralRotationIRProofReplayV1",
                "source_commit":rev,"reports":reports,
                "full_positive_ready_proven":False,
                "WCL_independent_holdout_completed":False,
                "native_cast_selection_parity_verified":False,
                "WCL_API_calls":0}
    elif not args.source_root and not args.manifest:
        result=selftest()
    else:p.error("both source root and pinned manifest required")
    raw=canonical(result)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("xb") as handle:handle.write(raw)
        print("GENERIC_ROTATION_IR_PROOF_REPLAY_SHA256="+sha256(raw).hexdigest())
    else:print(raw.decode(),end="")

if __name__=="__main__":
    main()
