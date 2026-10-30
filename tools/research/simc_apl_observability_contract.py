#!/usr/bin/env python3
"""Generic SimC APL observation requirements: automatic, not observed gameplay.

Consumes the existing structural IR and canonical decision graph. Produces a
source-referenced inventory of state operands, action readiness and unsupported
semantics. Optional explicit Strict-PRE state/binding auditing is diagnostics
only; it never creates ability identity, mechanics policy or recommendation.

No specialization, ability name, boss, or empirical threshold is hardcoded.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

from simc_apl_decision_graph import compile_decision_graph
from simc_apl_readiness_provider import MANDATORY

_SCHEMA = "ZrotSimcGenericObservationRequirementsV1"
_IR_SCHEMA = "ZrotGenericSimcConditionalPriorityStructuralIRV1"


def compile_requirements(ir: Mapping[str, Any], *, graph=None) -> dict:
    if not isinstance(ir, dict) or ir.get("schema") != _IR_SCHEMA:
        raise ValueError("OBSERVABILITY_SOURCE_IR_REQUIRED")
    expected = compile_decision_graph(ir)
    if graph is not None and graph != expected:
        raise ValueError("OBSERVABILITY_GRAPH_CANONICAL_MISMATCH")
    graph = expected
    operands: dict[str, list[dict]] = {}
    expressions_unresolved = []
    action_sources: dict[str, list[dict]] = {}
    controls: list[dict] = []
    for list_name, rows in ir["lists"].items():
        for row in rows:
            node_id = row["id"]
            node = graph["nodes"][node_id]
            place = {"node_id":node_id, "source_line":row["source_line"],
                     "list_name":list_name}
            if row["operation"] == "ACTION_TOKEN":
                action_sources.setdefault(row["command"], []).append(place)
            elif row["operation"] not in ("CALL_LIST", "RUN_LIST"):
                controls.append({
                    **place, "operation":row["operation"],
                    "semantics":"UNKNOWN_UNVERIFIED_CONTROL",
                })
            for field, expr in row["expressions"].items():
                status = expr["status"]
                if status != "SYNTAX_PARSED_OPERANDS_UNBOUND":
                    expressions_unresolved.append({
                        **place, "field":field,
                        "expression_source":expr["source"], "reason":status,
                    })
                for operand in expr["operands"]:
                    if not isinstance(operand, str) or not operand:
                        raise ValueError("INVALID_OBSERVATION_OPERAND")
                    operands.setdefault(operand, []).append({
                        **place, "expression_field":field,
                        "expression_status":status,
                    })
            if node["kind"] != "IF_ELSE_PRIORITY_ROW":
                raise ValueError("SOURCE_GRAPH_ROW_NOT_FOUND")
    if sorted(operands) != graph["required_state_operands"]:
        raise ValueError("OBSERVATION_OPERAND_COVERAGE_MISMATCH")
    if sorted(action_sources) != graph["required_action_readiness_tokens"]:
        raise ValueError("OBSERVATION_ACTION_COVERAGE_MISMATCH")
    return {
        "schema":_SCHEMA,
        "spec":ir["spec"],
        "source_apl_sha256":graph["source_apl_sha256"],
        "source_profile_sha256":graph["source_profile_sha256"],
        "source_simc_executable_sha256":graph["source_simc_executable_sha256"],
        "source_row_count":graph["source_row_count"],
        "input_graph_exactly_recompiled":True,
        "required_state_operands":[{
            "operand":k,
            "namespace":k.split(".",1)[0] if "." in k else "unqualified",
            "source_references":v,
            "semantic_binding":"UNBOUND",
            "strict_pre_observation":"UNKNOWN",
        } for k,v in sorted(operands.items())],
        "required_action_readiness":[{
            "action_token":k, "source_references":v,
            "required_dimensions":list(MANDATORY),
            "ability_identity":"UNKNOWN",
            "requirements_policy":"NOT_SUPPLIED",
            "status":"UNKNOWN",
        } for k,v in sorted(action_sources.items())],
        "control_semantics_requirements":controls,
        "unsupported_expression_fields":expressions_unresolved,
        "unverified_semantic_obligations":ir["semantic_gap_count_by_row"],
        "operand_requirement_count":len(operands),
        "readiness_requirement_count":len(action_sources),
        "unsupported_expression_count":len(expressions_unresolved),
        "no_implicit_operand_identity_mapping":True,
        "no_implicit_readiness_or_ability_id":True,
        "unobserved_not_equivalent_to_false":True,
        "claim":"SOURCE_DERIVED_REQUIREMENTS_ONLY",
        "actual_strict_pre_observation":"NOT_RUN",
        "actual_simc_priority_equivalence":"NOT_VALIDATED",
        "independent_wcl_validation":"NOT_RUN",
        "gameplay_rule_promotion":False,
    }


def _finite_numeric(value: Any) -> bool:
    if type(value) is bool:
        return True
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except (ValueError, OverflowError):
        return False


def audit_explicit_strict_pre(
    contract: Mapping[str, Any], state: Any, *,
    operand_to_feature: Mapping[str, str],
) -> dict:
    """Audit only an explicitly provided state and operand identity map.

    Source requirements alone do not supply semantic operand bindings. PRE
    timestamp provenance must be strictly less than the decision timestamp.
    An OBSERVED feature is a caller-provided claim, not independently verified
    WCL, Blizzard mechanics, or executable SimC state.
    """
    if contract.get("schema") != _SCHEMA:
        raise ValueError("OBSERVABILITY_CONTRACT_SCHEMA")
    state.validate()
    if not isinstance(operand_to_feature, dict):
        raise ValueError("INVALID_EXPLICIT_OPERAND_MAPPING")
    known = {x["operand"] for x in contract["required_state_operands"]}
    if set(operand_to_feature) - known:
        raise ValueError("UNEXPECTED_OPERAND_BINDING")
    per_operand = []
    summary = Counter()
    for entry in contract["required_state_operands"]:
        operand = entry["operand"]
        feature = operand_to_feature.get(operand)
        provenance_time = None
        if feature is None:
            status = "UNKNOWN_UNBOUND"
        elif not isinstance(feature, str) or not feature:
            raise ValueError("INVALID_EXPLICIT_FEATURE_BINDING")
        else:
            obs = state.features.get(feature)
            if obs is None:
                status = "UNKNOWN_NO_PRE_OBSERVATION"
            else:
                observed_status = getattr(obs.status, "value", obs.status)
                timestamp = obs.source_timestamp_ms
                if observed_status == "UNOBSERVABLE":
                    status = "UNOBSERVABLE"
                elif observed_status != "OBSERVED":
                    status = "UNKNOWN_NO_PRE_OBSERVATION"
                elif timestamp is None:
                    status = "UNKNOWN_NO_SOURCE_TIMESTAMP"
                elif timestamp >= state.decision_timestamp_ms:
                    raise ValueError("OBSERVATION_NOT_STRICT_PRE")
                elif not _finite_numeric(obs.value):
                    status = "UNKNOWN_NONNUMERIC"
                else:
                    status = "OBSERVED_STRICT_PRE_CLAIM"
                    provenance_time = timestamp
        summary[status] += 1
        per_operand.append({
            "operand":operand, "explicit_feature":feature,
            "status":status, "source_timestamp_ms":provenance_time,
            "feature_identity_authority":"CALLER_DECLARED_UNVERIFIED",
        })
    return {
        "schema":"ZrotSimcGenericObservationAuditV1",
        "spec":contract["spec"],
        "source_apl_sha256":contract["source_apl_sha256"],
        "decision_timestamp_ms":state.decision_timestamp_ms,
        "operand_statuses":per_operand,
        "operand_status_counts":dict(sorted(summary.items())),
        "operand_requirement_count":len(per_operand),
        "readiness_requirement_count":contract["readiness_requirement_count"],
        "readiness_decisions":"ALL_UNKNOWN_NO_POLICY",
        "invalid_same_timestamp_events_excluded":state.excluded_same_timestamp_n,
        "future_events_excluded":state.excluded_future_n,
        "invalid_transitions_excluded":state.invalid_transition_n,
        "observation_provenance":"EXPLICIT_CALLER_SUPPLIED_PRE_CLAIMS_ONLY",
        "empirical_state_validation":"NOT_RUN",
        "gameplay_rule_promotion":False,
    }


def selftest() -> None:
    from simc_apl_source_engine import ingest_actions
    from simc_apl_conditional_ir import compile_structural_ir
    runtime = Path(__file__).resolve().parents[2] / "02_SOURCE" / "runtime"
    sys.path.insert(0,str(runtime))
    from raid_dps.core.behavioral_evaluator import StrictPreStateProvider, StateTransition

    for spec, first in (("enhancement","alpha"),("fury","omega"),("imaginary","zeta")):
        source=(
            f"spec={spec}\n"
            f"actions={first},if=buff.test.stack>=2&active_enemies=1\n"
            "actions+=/beta,target_if=min:dot.foo.remains\n"
            "actions+=/variable,name=gate,op=set,value=resource.mana\n"
            "actions+=/gamma,if=unsupported~expression\n"
        ).encode()
        model=ingest_actions(source, expected_spec=spec)
        ir=compile_structural_ir(model)
        graph=compile_decision_graph(ir)
        manifest=compile_requirements(ir,graph=graph)
        assert manifest["source_apl_sha256"] == hashlib.sha256(source).hexdigest()
        required={x["operand"] for x in manifest["required_state_operands"]}
        assert required=={"buff.test.stack","active_enemies","dot.foo.remains","resource.mana"}
        assert set(x["action_token"] for x in manifest["required_action_readiness"]) == {first,"beta","gamma"}
        assert all(x["status"]=="UNKNOWN" and x["ability_identity"]=="UNKNOWN"
                   and len(x["required_dimensions"])==8
                   for x in manifest["required_action_readiness"])
        assert manifest["unsupported_expression_count"] == 1
        assert manifest["control_semantics_requirements"][0]["operation"] == "VARIABLE_UPDATE"
        assert not manifest["gameplay_rule_promotion"]
        snap=StrictPreStateProvider().build(
            action_timestamp_ms=1000,
            transitions=(
                StateTransition(900,"stacks",2),
                StateTransition(1000,"stacks",100),
                StateTransition(1010,"stacks",200),
                StateTransition(850,"targets",1),
                StateTransition(850,"mana",40),
            ),required_keys=("stacks","targets","mana","missing"),
            unobservable_keys=("hidden",))
        report=audit_explicit_strict_pre(manifest,snap,operand_to_feature={
            "buff.test.stack":"stacks",
            "active_enemies":"targets",
            "dot.foo.remains":"hidden",
            "resource.mana":"missing",
        })
        assert report["operand_status_counts"]=={
            "OBSERVED_STRICT_PRE_CLAIM":2,
            "UNKNOWN_NO_PRE_OBSERVATION":1,
            "UNOBSERVABLE":1,
        }, report
        assert report["invalid_same_timestamp_events_excluded"]==1
        assert report["future_events_excluded"]==1
        assert report["readiness_decisions"]=="ALL_UNKNOWN_NO_POLICY"
        assert not report["gameplay_rule_promotion"]
        empty=audit_explicit_strict_pre(manifest,snap,operand_to_feature={})
        assert empty["operand_status_counts"]=={"UNKNOWN_UNBOUND":4}
        modified=json.loads(json.dumps(graph))
        modified["source_apl_sha256"]="0"*64
        try:
            compile_requirements(ir,graph=modified)
        except ValueError as e:
            assert str(e)=="OBSERVABILITY_GRAPH_CANONICAL_MISMATCH"
        else:
            raise AssertionError("TAMPERED_GRAPH_ACCEPTED")
        try:
            audit_explicit_strict_pre(manifest,snap,operand_to_feature={"unknown":"stacks"})
        except ValueError as e:
            assert str(e)=="UNEXPECTED_OPERAND_BINDING"
        else:
            raise AssertionError("UNEXPECTED_MAPPING_ACCEPTED")
    print("SIMC_GENERIC_OBSERVABILITY_CONTRACT_SELF_TEST=PASS SPECS=3")


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-ir",type=Path)
    p.add_argument("--graph",type=Path)
    p.add_argument("--snapshot",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test or args.source_ir is None:
        selftest()
        return
    ir=json.loads(args.source_ir.read_text(encoding="utf-8"))
    graph=(json.loads(args.graph.read_text(encoding="utf-8"))
           if args.graph is not None else None)
    result=compile_requirements(ir,graph=graph)
    if args.snapshot is not None:
        sys.path.insert(0,str(Path(__file__).resolve().parents[2] / "02_SOURCE" / "runtime"))
        from raid_dps.core.behavioral_evaluator import StrictPreStateProvider, StateTransition
        supplied=json.loads(args.snapshot.read_text(encoding="utf-8"))
        transitions=tuple(StateTransition(int(t["timestamp_ms"]),t["key"],t["value"])
                          for t in supplied["transitions"])
        state=StrictPreStateProvider().build(
            action_timestamp_ms=int(supplied["decision_timestamp_ms"]),
            transitions=transitions,
            required_keys=supplied.get("required_keys",()),
            unobservable_keys=supplied.get("unobservable_keys",()))
        result["explicit_pre_audit"]=audit_explicit_strict_pre(
            result,state,operand_to_feature=supplied.get("operand_to_feature",{}))
    output=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(output,encoding="utf-8")
        print("WROTE_SIMC_GENERIC_OBSERVATION_REQUIREMENTS")
    else:
        print(output)


if __name__=="__main__":
    main()
