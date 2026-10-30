#!/usr/bin/env python3
"""Research-only source-accountable Strict-PRE fixture -> existing SimC runtime.

Uses the canonical APL structural IR, state requirements, and the existing
StrictPreStateProvider + trace_priority. Never synthesizes SimC/Blizzard
mechanics or Native PRE observations from an action_sequence snapshot.
The input is a pinned, caller-DECLARED transition ledger, not independent
evidence that a WCL/SimC state producer is correct.

READY/NOT_READY may ONLY be injected for clearly flagged synthetic tests;
real caller-declared ledgers leave all readiness UNKNOWN until an independently
validated readiness producer and mechanics policy exist.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"02_SOURCE"/"runtime"))
from raid_dps.core.behavioral_evaluator import StrictPreStateProvider, StateTransition
from simc_apl_conditional_ir import compile_structural_ir
from simc_apl_decision_graph import compile_decision_graph
from simc_apl_observability_contract import compile_requirements, audit_explicit_strict_pre
from simc_apl_condition_research import bind_strict_pre
from simc_apl_priority_trace import trace_priority

_SCHEMA="ZrotSimcSourceAccountableStrictPreFixtureV1"
_RESULT="ZrotSimcSourceAccountableStrictPreReplayV1"
_SHA=re.compile(r"^[a-f0-9]{64}$")
_ALLOWED_ORIGINS=("SYNTHETIC_TEST","EXTERNAL_CALLER_DECLARED_UNVERIFIED")
_LIMIT=50000


def transition_digest(rows:list[dict])->str:
    """Exact deterministic local row-integrity check, NOT producer validation."""
    return hashlib.sha256(
        json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False,
                   allow_nan=False).encode("utf-8")
    ).hexdigest()


def _number(v:Any)->bool:
    if type(v) is bool:return True
    if type(v) in (int,float):
        try:return math.isfinite(v)
        except (ValueError,OverflowError):return False
    return False


def replay_explicit_pre(model:dict,fixture:dict,*,graph:dict|None=None)->dict:
    if model.get("schema")!="ZrotGenericSimcAplSourceHypothesisV1":
        raise ValueError("PRE_SOURCE_MODEL_SCHEMA")
    if not isinstance(fixture,dict) or fixture.get("schema")!=_SCHEMA:
        raise ValueError("PRE_FIXTURE_SCHEMA")
    for input_key,model_key in (
        ("spec","expected_spec"),("source_apl_sha256","apl_sha256"),
        ("source_profile_sha256","profile_sha256"),
    ):
        if fixture.get(input_key)!=model.get(model_key):
            raise ValueError("PRE_FIXTURE_SOURCE_IDENTITY_"+input_key)
    binary=fixture.get("source_simc_executable_sha256")
    if binary!=model.get("simc_executable_sha256"):
        raise ValueError("PRE_FIXTURE_BINARY_SOURCE_MISMATCH")
    if model.get("actionable_general_rotation") is not False or (
            fixture.get("gameplay_rule_promotion") is not False):
        raise ValueError("PREMATURE_PRE_FIXTURE_AUTHORITY")
    origin=fixture.get("provenance_class")
    if origin not in _ALLOWED_ORIGINS:
        raise ValueError("UNVERIFIED_PRE_PRODUCER_MUST_NOT_CLAIM_CERTIFICATION")
    if fixture.get("independently_verified_producer") is not False:
        raise ValueError("UNVERIFIED_PRE_PRODUCER_MUST_NOT_CLAIM_VERIFIED")
    ts=fixture.get("decision_timestamp_ms")
    if type(ts) is not int or ts<0:
        raise ValueError("INVALID_PRE_DECISION_TIMESTAMP")
    row_data=fixture.get("transitions")
    if not isinstance(row_data,list) or len(row_data)>_LIMIT:
        raise ValueError("INVALID_PRE_TRANSITION_ROWS")
    checksum=fixture.get("transitions_sha256")
    if not isinstance(checksum,str) or not _SHA.fullmatch(checksum) or (
            transition_digest(row_data)!=checksum):
        raise ValueError("PRE_TRANSITION_LEDGER_SHA_MISMATCH")
    ir=compile_structural_ir(model)
    requirements=compile_requirements(ir,graph=graph)
    expected_graph=compile_decision_graph(ir) if graph is None else graph
    known={x["operand"] for x in requirements["required_state_operands"]}
    mapping=fixture.get("operand_to_feature")
    if not isinstance(mapping,dict) or (set(mapping)-known):
        raise ValueError("PRE_UNKNOWN_OR_INVALID_OPERAND_BINDING")
    if any(not isinstance(k,str) or not k or not isinstance(v,str) or not v
           for k,v in mapping.items()):
        raise ValueError("PRE_INVALID_EXPLICIT_BINDING")
    feature_owners={}
    for operand,feature in mapping.items():
        prior=feature_owners.setdefault(feature,operand)
        if prior!=operand:
            raise ValueError("PRE_AMBIGUOUS_FEATURE_IDENTITY")
    unobs=fixture.get("unobservable_features",[])
    if not isinstance(unobs,list) or any(not isinstance(x,str) or not x for x in unobs):
        raise ValueError("PRE_UNOBSERVABLE_FEATURES_INVALID")
    if len(unobs)!=len(set(unobs)):
        raise ValueError("PRE_DUPLICATE_UNOBSERVABLE_FEATURE")
    transitions=[]
    sources=[]
    for i,event in enumerate(row_data):
        if not isinstance(event,dict) or set(event)!={
                "timestamp_ms","sequence","feature_key","value","producer_ref",
                "evidence_ref","valid"}:
            raise ValueError("PRE_TRANSITION_ROW_CONTRACT")
        when=event["timestamp_ms"]
        seq=event["sequence"]
        feature=event["feature_key"]
        if type(when) is not int or type(seq) is not int or seq<0 or when<0:
            raise ValueError("PRE_TRANSITION_TIME_OR_SEQUENCE_INVALID")
        if not isinstance(feature,str) or not feature:
            raise ValueError("PRE_TRANSITION_FEATURE_INVALID")
        if type(event["valid"]) is not bool:
            raise ValueError("PRE_TRANSITION_VALIDITY_INVALID")
        for label in ("producer_ref","evidence_ref"):
            if not isinstance(event[label],str) or not event[label].strip():
                raise ValueError("PRE_TRANSITION_PROVENANCE_REQUIRED")
        # Reject unnamed/untrusted objects and nonfinite numbers rather
        # than asking the provider to reinterpret them.
        if not _number(event["value"]):
            raise ValueError("PRE_TRANSITION_NONNUMERIC_VALUE")
        transitions.append(StateTransition(
            when,feature,event["value"],sequence=seq,valid=event["valid"]))
        sources.append({"row":i,"feature_key":feature,"timestamp_ms":when,
                        "sequence":seq,"producer_ref":event["producer_ref"],
                        "evidence_ref":event["evidence_ref"],
                        "strict_pre_eligible":event["valid"] and when<ts
                                             and feature not in unobs})
    required_keys=sorted(set(mapping.values()))
    state=StrictPreStateProvider().build(
        action_timestamp_ms=ts,transitions=tuple(transitions),
        required_keys=required_keys,unobservable_keys=unobs)
    audit=audit_explicit_strict_pre(
        requirements,state,operand_to_feature=mapping)
    # Existing condition evaluator is the only numeric engine.
    observed_values=bind_strict_pre(state,operand_to_feature=mapping)
    strictly_past={o["operand"] for o in audit["operand_statuses"]
                   if o["status"]=="OBSERVED_STRICT_PRE_CLAIM"}
    if set(observed_values)!=strictly_past:
        raise ValueError("PRE_BINDER_AUDIT_INCONSISTENCY")
    readiness=fixture.get("synthetic_action_readiness",{})
    if not isinstance(readiness,dict):
        raise ValueError("PRE_READINESS_TEST_MAP_INVALID")
    if readiness and origin!="SYNTHETIC_TEST":
        raise ValueError("PRE_REAL_READINESS_NOT_AUTHORIZED")
    action_tokens={a["action_token"] for a in requirements["required_action_readiness"]}
    if (set(readiness)-action_tokens) or any(v not in ("READY","NOT_READY","UNKNOWN")
                                          for v in readiness.values()):
        raise ValueError("PRE_SYNTHETIC_READINESS_NOT_SOURCE_BOUND")
    trace=trace_priority(
        model,strict_pre_state=state,spec_slug=model["expected_spec"],
        operand_to_feature=mapping,action_readiness=readiness,
        expected_apl_sha256=model["apl_sha256"],
        expected_profile_sha256=model.get("profile_sha256"),
        decision_graph=expected_graph)
    # Never promote synthetic candidate/trace or caller-attested state.
    counts=Counter(x["status"] for x in audit["operand_statuses"])
    return {
        "schema":_RESULT,"spec":model["expected_spec"],
        "source_apl_sha256":model["apl_sha256"],
        "source_profile_sha256":model.get("profile_sha256"),
        "source_simc_executable_sha256":model.get("simc_executable_sha256"),
        "provenance_class":origin,
        "transitions_sha256":checksum,
        "decision_timestamp_ms":ts,
        "strict_pre_latest_observed_timestamp_ms":state.state_timestamp_max_ms,
        "strict_pre_excluded_same_timestamp_count":state.excluded_same_timestamp_n,
        "strict_pre_excluded_future_count":state.excluded_future_n,
        "strict_pre_excluded_invalid_count":state.invalid_transition_n,
        "source_transition_receipts":sources,
        "operand_diagnostics":audit["operand_statuses"],
        "operand_diagnostic_counts":dict(sorted(counts.items())),
        "synthetic_readiness_test_only":bool(readiness),
        "non_synthetic_readiness_all_unknown":origin!="SYNTHETIC_TEST",
        "trace_status":trace.status,
        "trace_reason":trace.reason,
        "trace_candidate_action_token":trace.candidate_action_token,
        "trace_source_line":trace.source_line,
        "trace_list":trace.list_name,
        "trace_events":list(trace.trace),
        "source_truth_status":"CALLER_DECLARED_NOT_INDEPENDENTLY_VERIFIED",
        "native_simc_decision_time_state":"NOT_CAPTURED",
        "native_foreground_parity":"NOT_VALIDATED",
        "blizzard_current_mechanics":"NOT_VERIFIED",
        "independent_wcl":"NOT_RUN",
        "actionable":False,"gameplay_rule_promotion":False,
    }


def selftest():
    from simc_apl_source_engine import ingest_actions
    import copy
    for spec,a,b in (("enhancement","alpha","beta"),
                     ("fury","gamma","delta"),
                     ("imaginary","one","two")):
        raw=(f"spec={spec}\nactions={a},if=buff.proof.stack>=3\n"
             f"actions+=/{b},if=active_enemies>=2\n").encode()
        model=ingest_actions(raw,expected_spec=spec)
        events=[
            {"timestamp_ms":900,"sequence":0,"feature_key":"stack",
             "value":4,"producer_ref":"synthetic:buff","evidence_ref":"fixture:1","valid":True},
            {"timestamp_ms":910,"sequence":0,"feature_key":"enemies",
             "value":2,"producer_ref":"synthetic:target","evidence_ref":"fixture:2","valid":True},
            {"timestamp_ms":1000,"sequence":0,"feature_key":"stack",
             "value":0,"producer_ref":"synthetic:buff","evidence_ref":"fixture:same","valid":True},
            {"timestamp_ms":1100,"sequence":0,"feature_key":"enemies",
             "value":0,"producer_ref":"synthetic:target","evidence_ref":"fixture:future","valid":True},
            {"timestamp_ms":800,"sequence":0,"feature_key":"stack",
             "value":1,"producer_ref":"synthetic:buff","evidence_ref":"fixture:invalid","valid":False},
        ]
        fixture={
            "schema":_SCHEMA,"spec":spec,
            "source_apl_sha256":model["apl_sha256"],
            "source_profile_sha256":model.get("profile_sha256"),
            "source_simc_executable_sha256":model.get("simc_executable_sha256"),
            "gameplay_rule_promotion":False,
            "provenance_class":"SYNTHETIC_TEST",
            "independently_verified_producer":False,
            "decision_timestamp_ms":1000,
            "operand_to_feature":{"buff.proof.stack":"stack","active_enemies":"enemies"},
            "unobservable_features":[],
            "transitions":events,"transitions_sha256":transition_digest(events),
            "synthetic_action_readiness":{a:"READY",b:"READY"},
        }
        success=replay_explicit_pre(model,fixture)
        assert success["trace_status"]=="HYPOTHESIS_CANDIDATE",success
        assert success["trace_candidate_action_token"]==a,success
        assert success["strict_pre_excluded_same_timestamp_count"]==1
        assert success["strict_pre_excluded_future_count"]==1
        assert success["strict_pre_excluded_invalid_count"]==1
        assert success["operand_diagnostic_counts"]=={"OBSERVED_STRICT_PRE_CLAIM":2}
        assert not success["gameplay_rule_promotion"]
        # Readiness may be unknown even with both numeric guards fully observed.
        uncertain=copy.deepcopy(fixture)
        uncertain["synthetic_action_readiness"]={}
        blocked=replay_explicit_pre(model,uncertain)
        assert blocked["trace_status"]=="BLOCKED",blocked
        assert blocked["trace_candidate_action_token"] is None
        # Missing semantic binding blocks or remains UNKNOWN, not false.
        unknown=copy.deepcopy(fixture)
        unknown["operand_to_feature"].pop("buff.proof.stack")
        if "synthetic_action_readiness" in unknown:
            unknown["synthetic_action_readiness"]={a:"READY",b:"READY"}
        result=replay_explicit_pre(model,unknown)
        assert result["trace_status"]=="BLOCKED"
        assert result["operand_diagnostic_counts"].get("UNKNOWN_UNBOUND")==1
        # Same-time-only input must not act as earlier-than-decision observation.
        same=copy.deepcopy(fixture)
        same["transitions"]=events[2:3]
        same["transitions_sha256"]=transition_digest(same["transitions"])
        result=replay_explicit_pre(model,same)
        assert result["trace_status"]=="BLOCKED"
        assert result["operand_diagnostic_counts"].get("UNKNOWN_NO_PRE_OBSERVATION")==2
        unobservable=copy.deepcopy(fixture)
        unobservable["unobservable_features"]=["stack"]
        result=replay_explicit_pre(model,unobservable)
        assert result["operand_diagnostic_counts"].get("UNOBSERVABLE")==1
        # Source integrity and producer claim checks must fail closed.
        tampered=copy.deepcopy(fixture)
        tampered["transitions"][0]["value"]=99
        try:replay_explicit_pre(model,tampered)
        except ValueError as e:assert str(e)=="PRE_TRANSITION_LEDGER_SHA_MISMATCH"
        else:raise AssertionError("TAMPERED_TRANSITIONS_ACCEPTED")
        for field,val,code in [
            ("source_apl_sha256","0"*64,"PRE_FIXTURE_SOURCE_IDENTITY_source_apl_sha256"),
            ("provenance_class","CERTIFIED_NATIVE","UNVERIFIED_PRE_PRODUCER_MUST_NOT_CLAIM_CERTIFICATION"),
            ("independently_verified_producer",True,"UNVERIFIED_PRE_PRODUCER_MUST_NOT_CLAIM_VERIFIED"),
        ]:
            bad=copy.deepcopy(fixture);bad[field]=val
            try:replay_explicit_pre(model,bad)
            except ValueError as e:assert str(e)==code,(field,str(e))
            else:raise AssertionError("UNAUTHORIZED_STATE_ACCEPTED")
        caller=copy.deepcopy(fixture)
        caller["provenance_class"]="EXTERNAL_CALLER_DECLARED_UNVERIFIED"
        caller["synthetic_action_readiness"]={}
        claimed=replay_explicit_pre(model,caller)
        assert claimed["trace_status"]=="BLOCKED"
        bad=copy.deepcopy(caller);bad["synthetic_action_readiness"]={a:"READY"}
        try:replay_explicit_pre(model,bad)
        except ValueError as e:assert str(e)=="PRE_REAL_READINESS_NOT_AUTHORIZED"
        else:raise AssertionError("UNVERIFIED_READY_ACCEPTED")
    print("SIMC_SOURCE_ACCOUNTABLE_STRICT_PRE_BRIDGE_SELF_TEST=PASS SPECS=3 SYNTHETIC_STATE_ONLY")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",type=Path)
    parser.add_argument("--fixture",type=Path)
    parser.add_argument("--graph",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test or args.model is None:
        selftest();return
    if args.fixture is None:parser.error("--fixture required")
    model=json.loads(args.model.read_text("utf-8"))
    fixture=json.loads(args.fixture.read_text("utf-8"))
    graph=json.loads(args.graph.read_text("utf-8")) if args.graph else None
    result=replay_explicit_pre(model,fixture,graph=graph)
    rendered=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(rendered,encoding="utf-8")
        print("WROTE_SOURCE_ACCOUNTABLE_STRICT_PRE_REPLAY")
    else:print(rendered)


if __name__=="__main__":
    main()
