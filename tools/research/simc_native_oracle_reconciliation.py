#!/usr/bin/env python3
"""Generic native SimC performed-action / APL hypothesis comparison.

Native "performs" lines can be procs, background or autoattack, NOT
necessarily foreground APL choices. Caller-claimed foreground status does
not certify it. Outputs are provisional and never gameplay rules.
"""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
import json

from simc_apl_source_engine import ingest_actions
from simc_apl_priority_trace import trace_priority, CANDIDATE
from simc_native_performed_events import extract_native_reference


def reconcile(reference_dir, *, spec_slug, build_key, cases):
    """Consume pinned native evidence and a batch of explicit PRE snapshots."""
    root=Path(reference_dir).resolve(strict=True)
    native=extract_native_reference(root)  # verified native log / APL bytes
    receipt=json.loads((root/"simc_reference_receipt.json").read_text("utf-8"))
    if not spec_slug or spec_slug!=receipt.get("simc_spec"):
        raise ValueError("NATIVE_ORACLE_SPEC_MISMATCH")
    if not isinstance(build_key,str) or not build_key:
        raise ValueError("NATIVE_ORACLE_BUILD_LABEL_REQUIRED")
    model=ingest_actions(
        (root/"simc_effective_actions.simc").read_bytes(),
        expected_spec=spec_slug,profile_sha256=receipt["profile_sha256"],
        simc_executable_sha256=receipt["simc_executable_sha256"],
        profile_spec=spec_slug,profile_dependencies_verified=True)
    if model["apl_sha256"]!=native["effective_apl_sha256"]:
        raise ValueError("NATIVE_APL_SHA_MISMATCH")
    if not isinstance(cases,list):
        raise ValueError("CASES_MUST_BE_LIST")
    events={x["source_line"]:x for x in native["performed_events"]}
    import sys
    root_runtime=str(Path(__file__).resolve().parents[2]/"02_SOURCE"/"runtime")
    if root_runtime not in sys.path:
        sys.path.insert(0,root_runtime)
    from raid_dps.core.behavioral_evaluator import (
        StrictPreStateProvider, StateTransition, ObservationStatus)
    out=[]
    seen=set()
    for n,case in enumerate(cases):
        if not isinstance(case,dict):
            raise ValueError("INVALID_ORACLE_CASE")
        line=case.get("native_source_line")
        if type(line) is not int or line in seen:
            raise ValueError("DUPLICATE_OR_INVALID_NATIVE_EVENT")
        seen.add(line)
        event=events.get(line)
        base={
            "case_id":case.get("case_id",str(n+1)),"native_source_line":line,
            "native_action_token":event["action_token"] if event else None,
            "native_timestamp_ms":event["timestamp_ms"] if event else None,
        }
        def append(cat,why,trace=None):
            out.append({
                **base,"category":cat,"reason":why,
                "predicted_action_token":getattr(trace,"candidate_action_token",None),
                "predicted_apl_line":getattr(trace,"source_line",None),
                "foreground_certified":False,"source_state_certified":False,
                "gameplay_rule_promotion":False})
        if event is None:
            append("EXCLUDED","NO_MATCHING_NATIVE_EVENT")
            continue
        if (case.get("native_event_scope")!="CALLER_ATTESTED_FOREGROUND_APL"
            or not isinstance(case.get("scope_evidence_ref"),str)
            or not case["scope_evidence_ref"].strip()):
            append("EXCLUDED","FOREGROUND_APL_ORIGIN_UNVERIFIED")
            continue
        if (type(case.get("decision_timestamp_ms")) is not int or
            case["decision_timestamp_ms"]!=event["timestamp_ms"] or
            case.get("actor_literal")!=event["actor_literal"]):
            append("EXCLUDED","NATIVE_EVENT_TIME_OR_ACTOR_MISMATCH")
            continue
        if (case.get("spec_slug")!=spec_slug or
            case.get("build_key")!=build_key or
            case.get("source_apl_sha256")!=model["apl_sha256"]):
            append("EXCLUDED","SPEC_BUILD_APL_IDENTITY_MISMATCH")
            continue
        if not isinstance(case.get("transitions"),list):
            append("UNKNOWN","MISSING_PRE_STATE")
            continue
        try:
            steps=[]
            for r in case["transitions"]:
                if type(r.get("timestamp_ms")) is not int:
                    raise ValueError("INVALID_PRE_EVENT_TIMESTAMP")
                steps.append(StateTransition(r["timestamp_ms"],str(r["key"]),r["value"]))
            state=StrictPreStateProvider().build(
                action_timestamp_ms=event["timestamp_ms"],
                transitions=steps,required_keys=case.get("required_keys",()),
                unobservable_keys=case.get("unobservable_keys",()))
            bindings=case.get("operand_to_feature",{})
            control=case.get("control_feature_keys",{})
            ready_keys=case.get("readiness_feature_keys",{})
            if not all(isinstance(x,dict) for x in (bindings,control,ready_keys)):
                raise ValueError("INVALID_BINDING_MAP")
            readiness={}
            for token,key in ready_keys.items():
                obs=state.features.get(key)
                if (obs is not None and obs.status is ObservationStatus.OBSERVED
                    and obs.source_timestamp_ms is not None and
                    obs.source_timestamp_ms<event["timestamp_ms"] and
                    obs.value in ("READY","NOT_READY","UNKNOWN","UNOBSERVABLE")):
                    readiness[token]=obs.value
            trace=trace_priority(
                model,strict_pre_state=state,spec_slug=spec_slug,
                operand_to_feature=bindings,action_readiness=readiness,
                control_feature_keys=control,
                expected_apl_sha256=model["apl_sha256"],
                expected_profile_sha256=model["profile_sha256"])
        except (ValueError,KeyError,TypeError,AttributeError):
            append("UNKNOWN","PRE_STATE_OR_TRACE_UNSUPPORTED")
            continue
        if trace.status!=CANDIDATE:
            append("UNKNOWN","APL_"+trace.reason,trace)
        elif trace.candidate_action_token==event["action_token"]:
            append("PROVISIONAL_MATCH","SAME_ACTION_TOKEN_NOT_CERTIFIED",trace)
        else:
            append("PROVISIONAL_DIFFERENCE",
                   "TOKEN_DIFFERENCE_BACKGROUND_OR_REPLACEMENT_UNEXCLUDED",trace)
    summary=Counter(x["category"] for x in out)
    return {
        "schema":"ZrotSimcNativeOracleReconciliationResearchV1",
        "source_kind":native["capture_kind"],
        "native_capture_status":native["status"],
        "source_apl_sha256":model["apl_sha256"],
        "source_native_log_sha256":native["native_log_sha256"],
        "source_profile_sha256":model["profile_sha256"],
        "spec_slug":spec_slug,"build_key":build_key,
        "build_identity_certification":"CALLER_DECLARED_NOT_VERIFIED",
        "native_event_count":native["performed_event_count"],
        "native_unrecognized_event_count":native["unrecognized_performs_event_count"],
        "input_case_count":len(out),"category_counts":dict(summary),
        "cases":out,
        "foreground_event_certification":"NOT_RUN",
        "simc_native_decision_state_reconstructed":"NOT_RUN",
        "actual_simc_apl_equivalence":"NOT_VALIDATED",
        "wcl_independent_validation":"NOT_RUN",
        "gameplay_rule_promotion":False,"authority_promotion":False,
    }


def selftest():
    import tempfile
    from simc_native_performed_events import digest
    with tempfile.TemporaryDirectory(prefix="zrot_native_oracle_") as td:
        p=Path(td)
        apl=(b"spec=synthetic\n"
             b"actions=alpha,if=active_enemies>=2\n"
             b"actions+=/beta\n")
        log=(b"0.100 Actor performs Action 'alpha' (101) (50)\n"
             b"0.200 Actor performs Action 'beta' (102) (40)\n"
             b"0.300 Actor performs Action 'alpha' (101) (30)\n"
             b"0.400 Pet performs Action 'alpha' (101) (0)\n")
        (p/"simc_effective_actions.simc").write_bytes(apl)
        (p/"simc_native_log.txt").write_bytes(log)
        receipt={
            "schema":"ZrotSimcNativeReferenceCaptureV1",
            "status":"SYNTHETIC_CAPTURE_TEST","simc_spec":"synthetic",
            "effective_apl_sha256":digest(apl),"native_log_sha256":digest(log),
            "profile_sha256":"a"*64,"simc_executable_sha256":"b"*64,
            "outputs":[
                {"file":"simc_effective_actions.simc",
                 "sha256":digest(apl),"bytes":len(apl)},
                {"file":"simc_native_log.txt",
                 "sha256":digest(log),"bytes":len(log)}],
        }
        (p/"simc_reference_receipt.json").write_text(
            json.dumps(receipt),encoding="utf-8")
        def case(line,t,ready="READY",attested=True,actor="Actor"):
            return {
                "native_source_line":line,"decision_timestamp_ms":t,
                "actor_literal":actor,"spec_slug":"synthetic",
                "build_key":"fixture","source_apl_sha256":digest(apl),
                "native_event_scope":("CALLER_ATTESTED_FOREGROUND_APL"
                    if attested else "UNKNOWN"),
                "scope_evidence_ref":"SYNTHETIC" if attested else None,
                "transitions":[
                    {"timestamp_ms":t-50,"key":"enemies","value":2},
                    {"timestamp_ms":t-10,"key":"alpha_ready","value":ready},
                    {"timestamp_ms":t,"key":"enemies","value":0},
                    {"timestamp_ms":t+20,"key":"enemies","value":0}],
                "operand_to_feature":{"active_enemies":"enemies"},
                "readiness_feature_keys":{"alpha":"alpha_ready"},
            }
        cases=[case(1,100),case(2,200),case(3,300,None),
               case(4,400,attested=False,actor="Pet")]
        result=reconcile(p,spec_slug="synthetic",build_key="fixture",
                         cases=cases)
        assert result["category_counts"]=={
            "PROVISIONAL_MATCH":1,"PROVISIONAL_DIFFERENCE":1,
            "UNKNOWN":1,"EXCLUDED":1},result
        assert result["actual_simc_apl_equivalence"]=="NOT_VALIDATED"
        assert all(not x["foreground_certified"] for x in result["cases"])
        try:reconcile(p,spec_slug="synthetic",build_key="fixture",
                      cases=[cases[0],cases[0]])
        except ValueError as e:
            assert str(e)=="DUPLICATE_OR_INVALID_NATIVE_EVENT"
        else:raise AssertionError("DUPLICATE_ACCEPTED")
        (p/"simc_native_log.txt").write_bytes(log+b"changed")
        try:reconcile(p,spec_slug="synthetic",build_key="fixture",cases=cases)
        except ValueError as e:
            assert str(e)=="REFERENCE_OUTPUT_HASH_OR_SIZE_MISMATCH"
        else:raise AssertionError("CORRUPTED_SOURCE_ACCEPTED")
    print("SIMC_NATIVE_ORACLE_RECONCILIATION_SELF_TEST=PASS")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference-dir",type=Path)
    p.add_argument("--cases-file",type=Path)
    p.add_argument("--spec")
    p.add_argument("--build-key")
    p.add_argument("--out",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test or (a.reference_dir is None and a.cases_file is None):
        selftest()
        return
    if not all((a.reference_dir,a.cases_file,a.spec,a.build_key)):
        p.error("--reference-dir, --cases-file, --spec and --build-key required")
    rows=json.loads(a.cases_file.read_text(encoding="utf-8"))["cases"]
    result=reconcile(a.reference_dir,spec_slug=a.spec,
                     build_key=a.build_key,cases=rows)
    text=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(text,encoding="utf-8")
    else:
        print(text)


if __name__=="__main__":
    main()
