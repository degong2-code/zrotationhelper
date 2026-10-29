#!/usr/bin/env python3
"""Bounded SimC precombat variable replay from an explicitly documented timeline.

Structural APL provides HYPOTHESES only. This interpreter needs the full
attested per-row execution order, strictly earlier state observations, and
unambiguous variable actions to derive precombat variable initialization.
It never presents derived values as independently observed live/WCL state.

No specialization semantics or historical 785-row fixtures are embedded.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Mapping

from simc_apl_condition_research import bind_strict_pre, evaluate
from simc_apl_variable_runtime import apply_variable


def replay_precombat(
    model: Mapping[str, Any], *,
    spec_slug: str,
    expected_apl_sha256: str,
    row_timeline: list[dict[str,Any]],
    source_transitions: list[Any],
) -> dict[str,Any]:
    """Replay attested precombat row order, fail-closed on unverifiable steps.

    Row events: {source_line, timestamp_ms, status=EXECUTED|SKIPPED,
                 evidence_ref}. The ordering/timing evidence is caller-supplied,
    NOT independently authenticated by this module. For nonvariable effects,
    source_transitions must independently provide post-effect observations.
    """
    if model.get("schema")!="ZrotGenericSimcAplSourceHypothesisV1" or \
            model.get("actionable_general_rotation") is not False:
        raise ValueError("NON_HYPOTHESIS_SOURCE_MODEL")
    if model.get("expected_spec")!=spec_slug or not spec_slug:
        raise ValueError("PRECOMBAT_SPEC_IDENTITY_MISMATCH")
    if model.get("apl_sha256")!=expected_apl_sha256 or not expected_apl_sha256:
        raise ValueError("PRECOMBAT_APL_SHA_MISMATCH")
    rows=[x for x in model.get("rows",[]) if x.get("list")=="precombat"]
    base={
        "schema":"ZrotSimcPrecombatVariableResearchV1",
        "source_apl_sha256":expected_apl_sha256,
        "spec_slug":spec_slug,
        "status":"BLOCKED",
        "variables":{},
        "variable_transitions":[],
        "visited_rows":0,
        "stop_reason":None,
        "external_timeline_evidence":"CALLER_ATTESTED_NOT_INDEPENDENTLY_VERIFIED",
        "native_simc_reconciliation":"NOT_RUN",
        "empirical_observation":False,
        "gameplay_rule_promotion":False,
    }
    if not rows:
        return {**base,"status":"NO_PRECOMBAT_VARIABLES","stop_reason":None}
    if not isinstance(row_timeline,list) or len(row_timeline)!=len(rows):
        return {**base,"stop_reason":"INCOMPLETE_PRECOMBAT_EXECUTION_TIMELINE"}
    from sys import path as sys_path
    # Only needed for local Strict PRE contract; no network or game runtime.
    from pathlib import Path as LocalPath
    runtime=str(LocalPath(__file__).resolve().parents[2]/"02_SOURCE"/"runtime")
    if runtime not in sys_path:
        sys_path.insert(0,runtime)
    from raid_dps.core.behavioral_evaluator import (
        StrictPreStateProvider,StateTransition)
    for tr in source_transitions:
        if not isinstance(tr,StateTransition):
            raise ValueError("PRECOMBAT_SOURCE_TRANSITION_TYPE")
    variables={}
    produced=[]
    previous_ts=None
    for row,event in zip(rows,row_timeline):
        line=row["source_line"]
        timestamp=event.get("timestamp_ms")
        if (type(timestamp) is not int or
            (previous_ts is not None and timestamp<=previous_ts) or
            timestamp>=0):
            return {**base,"variables":dict(variables),
                    "variable_transitions":[],
                    "visited_rows":base["visited_rows"],
                    "stop_reason":"INVALID_PRECOMBAT_TIMELINE_ORDER"}
        previous_ts=timestamp
        if event.get("source_line")!=line or \
                event.get("status") not in ("EXECUTED","SKIPPED") or \
                not isinstance(event.get("evidence_ref"),str) or \
                not event["evidence_ref"].strip():
            return {**base,"variables":dict(variables),
                    "stop_reason":"PRECOMBAT_ROW_ATTESTATION_REQUIRED"}
        base["visited_rows"]+=1
        if event["status"]=="SKIPPED":
            continue
        state=StrictPreStateProvider().build(
            action_timestamp_ms=timestamp,
            transitions=(*source_transitions,*produced))
        bound=bind_strict_pre(state,operand_to_feature={
            feature:feature for feature in state.features
            if feature not in ("",)
        })
        # A variable assignment is a deterministic APL computation, not
        # evidence that its values were actually observed in-game.
        def expr(src):
            bound_current=dict(bound)
            bound_current.update({"variable."+k:v for k,v in variables.items()})
            return evaluate(src,bound_values=bound_current,
                            decision_timestamp_ms=timestamp,
                            state_timestamp_max_ms=state.state_timestamp_max_ms)
        guard=row.get("guard")
        if guard is not None:
            verdict=expr(guard)
            if verdict.status!="TRUE":
                return {**base,"variables":dict(variables),
                        "visited_rows":base["visited_rows"],
                        "stop_reason":"PRECOMBAT_GUARD_"+verdict.status}
        if row["command_token"]!="variable":
            # Non-variable effects are never modeled by this module. The
            # next step's state must be externally provided; no fabricated
            # buff/resource/weapon activation transition is emitted.
            continue
        result=apply_variable(dict(row["params"]),variables,expr)
        if result.status!="APPLIED":
            return {**base,"variables":dict(variables),
                    "visited_rows":base["visited_rows"],
                    "stop_reason":result.reason}
        produced.append(StateTransition(
            timestamp_ms=timestamp,
            key="variable."+result.name,value=result.value))
    return {**base,"status":"SOURCE_DERIVED_HYPOTHESIS",
            "variables":variables,
            "variable_transitions":[
                {"timestamp_ms":t.timestamp_ms,"key":t.key,"value":t.value,
                 "provenance":"SOURCE_DERIVED_NOT_EMPIRICALLY_OBSERVED"}
                for t in produced],
            "stop_reason":None}


def selftest():
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"02_SOURCE"/"runtime"))
    from raid_dps.core.behavioral_evaluator import StateTransition,StrictPreStateProvider
    from simc_apl_source_engine import ingest_actions
    import hashlib
    source=(
        b"spec=enhancement\n"
        b"actions.precombat=snapshot_stats\n"
        b"actions.precombat+=/variable,name=trinket_priority,value=trinket.1.has_use_buff\n"
        b"actions.precombat+=/variable,name=threshold,op=setif,"
        b"condition=variable.trinket_priority,value=5,value_else=2\n"
        b"actions=stormstrike,if=buff.foo.stack>=variable.threshold\n"
    )
    model=ingest_actions(source,expected_spec="enhancement")
    expected=hashlib.sha256(source).hexdigest()
    rows=[r for r in model["rows"] if r["list"]=="precombat"]
    timeline=[
        {"source_line":r["source_line"],"timestamp_ms":-300+i*100,
         "status":"EXECUTED","evidence_ref":"SYNTHETIC_NOT_NATIVE_SIMC"}
        for i,r in enumerate(rows)
    ]
    args=dict(model=model,spec_slug="enhancement",
              expected_apl_sha256=expected,row_timeline=timeline,
              source_transitions=[StateTransition(-250,"trinket.1.has_use_buff",1)])
    outcome=replay_precombat(**args)
    assert outcome["status"]=="SOURCE_DERIVED_HYPOTHESIS",outcome
    assert outcome["variables"]=={"trinket_priority":1.0,"threshold":5.0}
    assert outcome["variable_transitions"][0]["timestamp_ms"]==-200
    assert not outcome["empirical_observation"] and not outcome["gameplay_rule_promotion"]
    # A source transition that occurs only at/following the variable's
    # decision time cannot influence that choice.
    late=replay_precombat(**(args|{
        "source_transitions":[StateTransition(-200,"trinket.1.has_use_buff",1)]}))
    assert late["status"]=="BLOCKED" and late["stop_reason"]=="VARIABLE_VALUE_UNKNOWN"
    incomplete=replay_precombat(**(args|{"row_timeline":timeline[:-1]}))
    assert incomplete["stop_reason"]=="INCOMPLETE_PRECOMBAT_EXECUTION_TIMELINE"
    reordered=[dict(x) for x in timeline]
    reordered[1]["timestamp_ms"]=-300
    assert replay_precombat(**(args|{"row_timeline":reordered}))[
        "stop_reason"]=="INVALID_PRECOMBAT_TIMELINE_ORDER"
    # It can supply a *research-only* value to a later decision; caller
    # must never mark this as independently observed gameplay evidence.
    events=[StateTransition(x["timestamp_ms"],x["key"],x["value"])
            for x in outcome["variable_transitions"]]
    ready=StrictPreStateProvider().build(
        action_timestamp_ms=10,transitions=events)
    assert ready.features["variable.threshold"].value==5
    print("SIMC_PRECOMBAT_VARIABLE_REPLAY_SELF_TEST=PASS")


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",type=Path)
    p.add_argument("--timeline",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test or (args.model is None and args.timeline is None):
        selftest()
        return
    if args.model is None or args.timeline is None:
        p.error("--model and --timeline are required")
    model=json.loads(args.model.read_text(encoding="utf-8"))
    data=json.loads(args.timeline.read_text(encoding="utf-8"))
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"02_SOURCE"/"runtime"))
    from raid_dps.core.behavioral_evaluator import StateTransition
    inputs=[StateTransition(int(x["timestamp_ms"]),str(x["key"]),x["value"])
            for x in data["source_transitions"]]
    result=replay_precombat(model,spec_slug=data["spec_slug"],
        expected_apl_sha256=model["apl_sha256"],
        row_timeline=data["row_timeline"],source_transitions=inputs)
    out=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(out,encoding="utf-8")
    else:
        print(out)


if __name__=="__main__":
    main()
