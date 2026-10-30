#!/usr/bin/env python3
"""Build a cross-specialization conditional-priority hypothesis IR from SimC APL.

This is a *complete structural transcription* of the supplied APL, NOT a
complete semantic interpreter. Every row and modifier is kept, including
precombat, calls, variables and effects. An unresolved action/readiness is
NEVER promoted into a gameplay priority rule.

Unlike one-state traces, the IR can be consumed by a future decision-tree
compiler and is valid for any supplied specialization and build profile.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from simc_apl_source_engine import ingest_actions
from simc_apl_condition_research import _Parser

_CONTROL = {
    "call_action_list": "CALL_LIST",
    "run_action_list": "RUN_LIST",
    "variable": "VARIABLE_UPDATE",
    "cycling_variable": "CYCLING_VARIABLE",
    "pool_resource": "POOL_RESOURCE",
    "auto_attack": "AUTO_ATTACK_STATE",
    "snapshot_stats": "STAT_SNAPSHOT",
    "wait": "WAIT",
    "wait_fixed": "WAIT",
    "stop_moving": "MOVEMENT_CONTROL",
    "start_moving": "MOVEMENT_CONTROL",
    "retarget": "TARGET_CONTROL",
    "cancel_buff": "BUFF_CONTROL",
    "swap_action_list": "LIST_CONTROL",
    "invoke_external_buff": "EXTERNAL_BUFF_REQUEST",
}
_CONDITIONAL_OPERANDS = ("if", "target_if", "condition", "value", "value_else", "default")
_TARGET_MODS = {"target", "target_if", "cycle_targets", "max_cycle_targets"}
_ACTION_TIMING = {"line_cd", "use_off_gcd", "use_while_casting",
                  "wait_on_ready", "interrupt", "interrupt_if", "sync", "moving"}
_ACTION_SCOPE = {"name", "slot", "slots", "pre_pot_time", "for_next",
                 "extra_amount", "wait", "sec"}


def _expression(expr: str) -> dict[str, Any]:
    """Syntax only; every runtime state operand is still UNKNOWN."""
    try:
        ast = _Parser(expr).parse()
    except Exception:
        return {"status": "UNSUPPORTED_EXPRESSION_SYNTAX", "operands": [], "source": expr}
    found: set[str] = set()
    def scan(tree):
        if tree[0] == "variable":
            found.add(tree[1])
        elif tree[0] in ("unary", "function"):
            scan(tree[2])
        elif tree[0] == "binary":
            scan(tree[2])
            scan(tree[3])
    scan(ast)
    return {"status": "SYNTAX_PARSED_OPERANDS_UNBOUND",
            "operands": sorted(found), "source": expr}


def compile_structural_ir(source_model: dict) -> dict:
    if source_model.get("schema") != "ZrotGenericSimcAplSourceHypothesisV1":
        raise ValueError("INVALID_SIMC_APL_SOURCE_MODEL")
    if source_model.get("actionable_general_rotation") is not False:
        raise ValueError("GAMEPLAY_MODEL_NOT_ALLOWED")
    lists = source_model.get("lists", [])
    if not isinstance(lists, list) or len(set(lists)) != len(lists) or "default" not in lists:
        raise ValueError("INVALID_ACTION_LISTS")
    nodes = {name: [] for name in lists}
    gap = Counter()
    syntax = Counter()
    all_features: set[str] = set()
    for raw in source_model.get("rows", []):
        list_name = raw.get("list")
        if list_name not in nodes:
            raise ValueError("ROW_REFERENCES_UNDECLARED_LIST")
        rank = raw.get("list_rank")
        if type(rank) is not int or rank != len(nodes[list_name]) + 1:
            raise ValueError("NON_SEQUENTIAL_PRIORITY_ROW")
        if raw.get("hypothesis_only") is not True:
            raise ValueError("UNVERIFIED_PRODUCTION_RULE")
        pairs = raw.get("params", [])
        if not isinstance(pairs, list) or any(not isinstance(p, list) or len(p)!=2 for p in pairs):
            raise ValueError("INVALID_APL_PARAMETERS")
        if len({p[0] for p in pairs}) != len(pairs):
            raise ValueError("AMBIGUOUS_DUPLICATE_MODIFIER")
        params = dict(pairs)
        command = raw.get("command_token", "")
        kind = _CONTROL.get(command, "ACTION_TOKEN")
        line = raw.get("source_line")
        if type(line) is not int or line <= 0:
            raise ValueError("INVALID_SOURCE_LINE")
        expressions = {}
        for key in _CONDITIONAL_OPERANDS:
            if key in params:
                # target_if has selector prefix; the selector requires
                # target-scoped state and cannot be decided by a local guard.
                val = params[key]
                if key == "target_if":
                    selector = val.split(":", 1)
                    expr = selector[-1]
                else:
                    expr = val
                expressions[key] = _expression(expr)
                syntax[expressions[key]["status"]] += 1
                all_features.update(expressions[key]["operands"])
                if expressions[key]["status"] != "SYNTAX_PARSED_OPERANDS_UNBOUND":
                    gap["EXPRESSION_SYNTAX_UNSUPPORTED"] += 1
        obligations = set()
        if kind == "ACTION_TOKEN":
            obligations.update(("SPELL_IDENTITY", "SPELL_READINESS", "ACTION_EFFECTS"))
        elif kind == "CALL_LIST" or kind == "RUN_LIST":
            obligations.add("LIST_CONTROL_FLOW")
        elif kind == "VARIABLE_UPDATE":
            obligations.add("VARIABLE_LIFETIME_AND_OPERATIONS")
        else:
            obligations.add(kind + "_SEMANTICS")
        if params.get("if") is not None:
            obligations.add("STATE_OPERAND_BINDING")
        for mod in params:
            if mod in _TARGET_MODS:
                obligations.add("TARGET_IDENTITY_AND_SELECTION")
            if mod in _ACTION_TIMING:
                obligations.add("ACTION_TIMING_AND_COOLDOWN")
            if mod in _ACTION_SCOPE and kind == "ACTION_TOKEN":
                obligations.add("ACTION_OPTION_SEMANTICS")
            if mod not in set(_CONDITIONAL_OPERANDS) | _TARGET_MODS | _ACTION_TIMING | _ACTION_SCOPE | {"op"}:
                obligations.add("UNCLASSIFIED_MODIFIER_" + mod)
        target_list = raw.get("call_target")
        if kind in ("CALL_LIST", "RUN_LIST") and target_list not in nodes:
            raise ValueError("UNRESOLVED_LIST_TARGET")
        node = {
            "id": f"{list_name}:{rank}",
            "source_line": line,
            "source_empty_option_slots_ignored": raw.get("ignored_empty_option_slots",0),
            "list_name": list_name,
            "priority_in_list": rank,
            "operation": kind,
            "command": command,
            "guard": raw.get("guard"),
            "expressions": expressions,
            "modifiers": pairs,
            "callee_list": target_list,
            "on_guard_false": "NEXT_IN_LIST",
            "on_readiness_not_ready": "NEXT_IN_LIST" if kind == "ACTION_TOKEN" else None,
            "on_unknown_state": "BLOCK_UNRESOLVED",
            "on_callee_exhausted": ("NEXT_IN_LIST" if kind == "CALL_LIST" else
                                    "RESTART_TOP_WITH_DELAY" if kind == "RUN_LIST"
                                    else None),
            "unverified_semantic_obligations": sorted(obligations),
            "promotion": "HYPOTHESIS_ONLY",
        }
        nodes[list_name].append(node)
        for o in obligations:
            gap[o] += 1
    if sum(len(x) for x in nodes.values()) != source_model.get("apl_row_count"):
        raise ValueError("APL_ROW_COUNT_MISMATCH")
    return {
        "schema":"ZrotGenericSimcConditionalPriorityStructuralIRV1",
        "spec":source_model["expected_spec"],
        "source_apl_sha256":source_model["apl_sha256"],
        "source_profile_sha256":source_model.get("profile_sha256"),
        "source_simc_executable_sha256":source_model.get("simc_executable_sha256"),
        "lists":nodes,
        "priority_entry_list":"default",
        "precombat_is_distinct": "precombat" in nodes,
        "total_rows":sum(len(r) for r in nodes.values()),
        "source_empty_option_slots_ignored":sum(n["source_empty_option_slots_ignored"]
                                                  for rows in nodes.values() for n in rows),
        "condition_expression_diagnostics":dict(syntax),
        "required_state_operands":sorted(all_features),
        "semantic_gap_count_by_row":dict(sorted(gap.items(),key=lambda kv:(-kv[1],kv[0]))),
        "all_rows_preserved":True,
        "conditional_structure_only":True,
        "complete_simc_execution":False,
        "verified_if_else_rotation":False,
        "gameplay_rule_promotion":False,
        "wcl_reconciliation":"NOT_RUN",
    }


def selftest():
    source=(
        "spec=enhancement\n"
        "actions=auto_attack\n"
        "actions+=/variable,name=threshold,value=3\n"
        "actions+=/call_action_list,name=st,if=active_enemies=1\n"
        "actions+=/run_action_list,name=aoe,if=active_enemies>1\n"
        "actions.st=stormstrike,if=buff.foo.stack>=variable.threshold\n"
        "actions.st+=/lava_lash,target_if=min:dot.flame_shock.remains\n"
        "actions.aoe=pool_resource,for_next=1,extra_amount=40\n"
        "actions.aoe+=/crash_lightning,if=active_enemies>2\n"
    )
    model=ingest_actions(source.encode(), expected_spec="enhancement")
    out=compile_structural_ir(model)
    assert out["total_rows"]==8 and out["all_rows_preserved"]
    assert set(out["lists"])=={"default","st","aoe"}
    assert out["lists"]["default"][0]["operation"]=="AUTO_ATTACK_STATE"
    assert out["lists"]["default"][2]["on_callee_exhausted"]=="NEXT_IN_LIST"
    assert out["lists"]["default"][3]["on_callee_exhausted"]=="RESTART_TOP_WITH_DELAY"
    assert out["lists"]["st"][1]["operation"]=="ACTION_TOKEN"
    assert "TARGET_IDENTITY_AND_SELECTION" in out["lists"]["st"][1]["unverified_semantic_obligations"]
    assert "POOL_RESOURCE_SEMANTICS" in out["lists"]["aoe"][0]["unverified_semantic_obligations"]
    assert "buff.foo.stack" in out["required_state_operands"]
    assert "variable.threshold" in out["required_state_operands"]
    assert out["gameplay_rule_promotion"] is False
    assert out["complete_simc_execution"] is False
    # Second spec: no hardcoded action semantics.
    fury=source.replace("enhancement","fury").replace("stormstrike","rampage")
    alt=compile_structural_ir(ingest_actions(fury.encode(),expected_spec="fury"))
    assert alt["total_rows"]==8 and alt["spec"]=="fury"
    assert alt["lists"]["st"][0]["command"]=="rampage"
    assert alt["lists"]["st"][0]["guard"]==out["lists"]["st"][0]["guard"]
    print("SIMC_GENERIC_CONDITIONAL_PRIORITY_IR_SELF_TEST=PASS")


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actions-file",type=Path)
    parser.add_argument("--spec",type=str)
    parser.add_argument("--source-model",type=Path)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test or (args.source_model is None and args.actions_file is None):
        selftest()
        return
    if args.source_model is None:
        if args.spec is None:
            parser.error("--spec required with --actions-file")
        model=ingest_actions(args.actions_file.read_bytes(),expected_spec=args.spec)
    else:
        model=json.loads(args.source_model.read_text(encoding="utf-8"))
    ir=compile_structural_ir(model)
    txt=json.dumps(ir,ensure_ascii=False,indent=2)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(txt,encoding="utf-8")
        print("WROTE_SIMC_CONDITIONAL_PRIORITY_STRUCTURAL_IR")
    else:
        print(txt)


if __name__=="__main__":
    main()
