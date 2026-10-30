#!/usr/bin/env python3
"""Compile any SimC conditional structural IR into a generic IF/ELSE decision graph.

This is a symbolic, executable-architecture *hypothesis*, not a gameplay
rotation and not a substitute for SimulationCraft runtime semantics. No
specialization, spell, boss, target, or empirical thresholds are embedded.

Each node explicitly distinguishes guard true/false/UNKNOWN, action
READY/NOT_READY/UNKNOWN, call_action_list return, run_action_list yield,
and non-action directives whose semantics are unresolved. Never turn
UNKNOWN into an ELSE edge. Refuse malformed or unpinned input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from simc_apl_conditional_ir import compile_structural_ir
from simc_apl_source_engine import ingest_actions

_SOURCE_SCHEMA = "ZrotGenericSimcConditionalPriorityStructuralIRV1"
_SHA = re.compile(r"^[0-9a-f]{64}$")
_CONTROL = ("CALL_LIST", "RUN_LIST")


def _operand_namespace(name: str) -> str:
    """Generic grammar namespace only, NOT a mechanic or readiness binding."""
    return name.split(".", 1)[0] if "." in name else "unqualified"


def compile_decision_graph(ir: dict) -> dict:
    if not isinstance(ir, dict) or ir.get("schema") != _SOURCE_SCHEMA:
        raise ValueError("STRUCTURAL_IR_SCHEMA_REQUIRED")
    if ir.get("gameplay_rule_promotion") is not False or (
            ir.get("complete_simc_execution") is not False):
        raise ValueError("SOURCE_IR_MUST_BE_UNVERIFIED")
    if not isinstance(ir.get("source_apl_sha256"), str) or not _SHA.fullmatch(
            ir["source_apl_sha256"]):
        raise ValueError("SOURCE_APL_SHA256_REQUIRED")
    spec = ir.get("spec")
    if not isinstance(spec, str) or not spec:
        raise ValueError("SOURCE_SPEC_REQUIRED")
    lists = ir.get("lists")
    if not isinstance(lists, dict) or not lists or "default" not in lists:
        raise ValueError("DEFAULT_APL_LIST_REQUIRED")
    nodes = {}
    list_entry = {}
    list_exit = {}
    readiness_tokens = set()
    operands = set()
    action_node_count = 0
    blockers = set()
    for list_name, rows in lists.items():
        if not isinstance(list_name, str) or not list_name or not isinstance(rows, list) or not rows:
            raise ValueError("INVALID_APL_LIST")
        list_entry[list_name] = rows[0].get("id")
        list_exit[list_name] = f"{list_name}:EXHAUSTED"
        nodes[list_exit[list_name]] = {
            "kind": "LIST_EXHAUSTED", "list_name": list_name,
            "on_exhaustion": "CALLER_DEFINED_RETURN_OR_YIELD",
        }
    for list_name, rows in lists.items():
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or row.get("id") != f"{list_name}:{index + 1}":
                raise ValueError("INVALID_ROW_ID_OR_ORDER")
            node_id = row["id"]
            if node_id in nodes:
                raise ValueError("DUPLICATE_GRAPH_NODE")
            next_node = (rows[index + 1]["id"] if index + 1 < len(rows)
                         else list_exit[list_name])
            operation = row.get("operation")
            command = row.get("command")
            guard = row.get("guard")
            if not isinstance(command, str) or not command:
                raise ValueError("INVALID_ACTION_TOKEN")
            if guard is not None and (not isinstance(guard, str) or not guard):
                raise ValueError("INVALID_GUARD")
            expressions = row.get("expressions")
            if not isinstance(expressions, dict):
                raise ValueError("INVALID_EXPRESSIONS")
            guard_record = expressions.get("if")
            if guard is not None and (
                    not isinstance(guard_record, dict)
                    or guard_record.get("source") != guard):
                raise ValueError("GUARD_EXPRESSION_NOT_PINNED")
            for part in expressions.values():
                if not isinstance(part, dict) or not isinstance(part.get("operands"), list):
                    raise ValueError("INVALID_EXPRESSION_OPERANDS")
                operands.update(part["operands"])
            obligations = row.get("unverified_semantic_obligations")
            if not isinstance(obligations, list):
                raise ValueError("MISSING_SEMANTIC_OBLIGATIONS")
            modifiers = row.get("modifiers")
            if not isinstance(modifiers, list) or any(
                    not isinstance(x, list) or len(x) != 2 for x in modifiers):
                raise ValueError("INVALID_MODIFIERS")
            if operation == "ACTION_TOKEN":
                readiness_tokens.add(command)
                action_node_count += 1
                modifiers_other_than_guard = [x[0] for x in modifiers if x[0] != "if"]
                true_path = {
                    "kind": "CHECK_ACTION_READINESS",
                    "action_token": command,
                    "ready": "HYPOTHESIS_ACTION_CANDIDATE"
                             if not modifiers_other_than_guard
                             else "BLOCK_UNRESOLVED_ACTION_MODIFIERS",
                    "not_ready": next_node,
                    "unknown": "BLOCK_READINESS_UNKNOWN",
                    "unobservable": "BLOCK_READINESS_UNOBSERVABLE",
                    "unresolved_modifiers": modifiers_other_than_guard,
                    "action_identity": "UNKNOWN",
                }
                if modifiers_other_than_guard:
                    blockers.add("UNRESOLVED_ACTION_MODIFIERS")
            elif operation in _CONTROL:
                callee = row.get("callee_list")
                if callee not in list_entry:
                    raise ValueError("UNRESOLVED_CALL_TARGET")
                true_path = {
                    "kind": "ENTER_SUBLIST", "entry": list_entry[callee],
                    "callee": callee,
                    "on_callee_exhausted": (next_node if operation == "CALL_LIST"
                                          else "BLOCK_RUN_LIST_NO_FALLTHROUGH"),
                    "call_semantics": operation,
                }
            else:
                true_path = {
                    "kind": "BLOCK_UNRESOLVED_CONTROL_SEMANTICS",
                    "operation": operation,
                }
                blockers.add(str(operation) + "_SEMANTICS")
            nodes[node_id] = {
                "kind": "IF_ELSE_PRIORITY_ROW",
                "source_line": row.get("source_line"),
                "source_empty_option_slots_ignored":row.get("source_empty_option_slots_ignored",0),
                "list_name": list_name,
                "priority_in_list": index + 1,
                "next_in_list": next_node,
                "command": command,
                "guard": guard,
                "guard_syntax": ("CONSTANT_TRUE" if guard is None
                                 else guard_record.get("status")),
                "if_true": true_path,
                "else_false": next_node if guard is not None else None,
                "if_unknown": "BLOCK_GUARD_UNKNOWN" if guard is not None else None,
                "unresolved_semantic_obligations": obligations,
                "promotion": "HYPOTHESIS_ONLY",
            }
    if action_node_count == 0:
        blockers.add("NO_ACTION_CANDIDATES")
    if len(nodes) - len(list_exit) != ir.get("total_rows"):
        raise ValueError("SOURCE_ROW_COVERAGE_MISMATCH")
    declared = ir.get("required_state_operands")
    if not isinstance(declared, list) or sorted(operands) != sorted(declared):
        raise ValueError("SOURCE_OPERAND_COVERAGE_MISMATCH")
    namespace_counts = {}
    for operand in sorted(operands):
        if not isinstance(operand, str) or not operand:
            raise ValueError("INVALID_OPERAND")
        namespace = _operand_namespace(operand)
        namespace_counts[namespace] = namespace_counts.get(namespace, 0) + 1
    return {
        "schema": "ZrotSimcGenericSymbolicDecisionGraphV1",
        "spec": spec,
        "source_apl_sha256": ir["source_apl_sha256"],
        "source_profile_sha256": ir.get("source_profile_sha256"),
        "source_simc_executable_sha256": ir.get("source_simc_executable_sha256"),
        "entrypoint": list_entry["default"],
        "precombat_entrypoint": list_entry.get("precombat"),
        "list_entries": list_entry,
        "list_exits": list_exit,
        "nodes": nodes,
        "source_row_count": ir["total_rows"],
        "source_empty_option_slots_ignored": ir.get("source_empty_option_slots_ignored",0),
        "action_candidate_rows": action_node_count,
        "required_state_operands": sorted(operands),
        "state_operand_namespace_counts": dict(sorted(namespace_counts.items())),
        "required_action_readiness_tokens": sorted(readiness_tokens),
        "unresolved_control_gates": sorted(blockers),
        "source_hypothesis_is_not_decision_proof": True,
        "unobserved_guard_never_falls_through": True,
        "unobserved_readiness_never_falls_through": True,
        "all_source_rows_mapped": True,
        "automatic_cross_specialization_compilation": True,
        "actual_simc_priority_equivalence": "NOT_VALIDATED",
        "wcl_independent_validation": "NOT_RUN",
        "verified_if_else_rotation": False,
        "gameplay_rule_promotion": False,
        "main_authority_promotion": False,
    }


def selftest():
    example = (
        "spec=synthetic\n"
        "actions=call_action_list,name=single,if=active_enemies=1\n"
        "actions+=/run_action_list,name=multi,if=active_enemies>1\n"
        "actions+=/fallback\n"
        "actions.single=alpha,if=buff.proc.up\n"
        "actions.single+=/beta\n"
        "actions.multi=variable,name=x,op=set,value=2\n"
        "actions.multi+=/gamma,target_if=min:dot.foo.remains\n"
    )
    for spec, first in (("synthetic", "alpha"), ("other_spec", "omega")):
        src = example.replace("spec=synthetic", f"spec={spec}").replace("alpha,if=", f"{first},if=")
        model = ingest_actions(src.encode(), expected_spec=spec)
        ir = compile_structural_ir(model)
        out = compile_decision_graph(ir)
        assert out["source_apl_sha256"] == hashlib.sha256(src.encode()).hexdigest()
        assert out["source_row_count"] == 7
        assert len(out["nodes"]) == 10   # seven source nodes + three list exits
        call = out["nodes"]["default:1"]
        run = out["nodes"]["default:2"]
        assert call["if_true"]["entry"] == "single:1"
        assert call["if_true"]["on_callee_exhausted"] == "default:2"
        assert call["else_false"] == "default:2"
        assert call["next_in_list"] == "default:2"
        assert call["if_unknown"] == "BLOCK_GUARD_UNKNOWN"
        assert run["if_true"]["on_callee_exhausted"] == "BLOCK_RUN_LIST_NO_FALLTHROUGH"
        assert out["nodes"]["default:3"]["if_true"]["not_ready"] == "default:EXHAUSTED"
        assert out["nodes"]["default:3"]["next_in_list"] == "default:EXHAUSTED"
        assert out["nodes"]["single:1"]["if_true"]["unknown"] == "BLOCK_READINESS_UNKNOWN"
        assert out["nodes"]["single:1"]["if_true"]["action_token"] == first
        assert out["nodes"]["multi:1"]["if_true"]["kind"] == "BLOCK_UNRESOLVED_CONTROL_SEMANTICS"
        assert out["nodes"]["multi:2"]["if_true"]["ready"] == "BLOCK_UNRESOLVED_ACTION_MODIFIERS"
        assert "dot.foo.remains" in out["required_state_operands"]
        assert "buff.proc.up" in out["required_state_operands"]
        assert out["state_operand_namespace_counts"]["buff"] == 1
        assert not out["gameplay_rule_promotion"]
    normalized = (
        b"spec=synthetic\nactions=alpha,,if=active_enemies=1\n")
    norm_ir = compile_structural_ir(ingest_actions(normalized,expected_spec="synthetic"))
    norm_graph = compile_decision_graph(norm_ir)
    assert norm_graph["source_empty_option_slots_ignored"] == 1
    assert norm_graph["nodes"]["default:1"]["source_empty_option_slots_ignored"] == 1
    assert norm_graph["nodes"]["default:1"]["guard"] == "active_enemies=1"
    tampered = compile_structural_ir(ingest_actions(example.encode(),expected_spec="synthetic"))
    tampered["source_apl_sha256"] = "not_sha"
    try:
        compile_decision_graph(tampered)
    except ValueError as e:
        assert str(e) == "SOURCE_APL_SHA256_REQUIRED"
    else:
        raise AssertionError("UNPINNED_SOURCE_ACCEPTED")
    print("SIMC_GENERIC_SYMBOLIC_IF_ELSE_GRAPH_SELF_TEST=PASS")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-ir", type=Path)
    p.add_argument("--actions-file", type=Path)
    p.add_argument("--spec")
    p.add_argument("--out", type=Path)
    p.add_argument("--self-test", action="store_true")
    opts = p.parse_args()
    if opts.self_test or (opts.source_ir is None and opts.actions_file is None):
        selftest()
        return
    if (opts.source_ir is None) == (opts.actions_file is None):
        p.error("Supply exactly one of --source-ir or --actions-file")
    if opts.source_ir:
        ir = json.loads(opts.source_ir.read_text(encoding="utf-8"))
    else:
        if not opts.spec:
            p.error("--spec is required with --actions-file")
        ir = compile_structural_ir(ingest_actions(
            opts.actions_file.read_bytes(), expected_spec=opts.spec))
    output = json.dumps(compile_decision_graph(ir), ensure_ascii=False,indent=2) + "\n"
    if opts.out:
        opts.out.parent.mkdir(parents=True,exist_ok=True)
        opts.out.write_text(output,encoding="utf-8")
        print("WROTE_SIMC_GENERIC_SYMBOLIC_DECISION_GRAPH")
    else:
        print(output)


if __name__ == "__main__":
    main()
