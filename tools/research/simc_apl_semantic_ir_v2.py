#!/usr/bin/env python3
"""SimC APL semantic IR v2 — lossless source inventory and bounded evaluator.

Research-first. Full syntax coverage of the pinned Fury MID2 profile is NOT
equivalent to full SimulationCraft engine parity. Native action readiness,
target selection, target_if, usable conditions, variable timing, GCD, execute
and precombat side effects still require independent source/native validation.
Never infer readiness from WCL action frequency.

No CLI arguments: offline synthetic regression, no network and no credentials.
--profile: exact pinned SimC Git blob, source-complete typed action/list IR.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
PROFILE_GIT_BLOB = "3225992ed5b754ad5d61e8b785d9d859f1eed1be"
SCHEMA = "ZrotSourceFaithfulSimcAplSemanticIRV2"

ROW = re.compile(r"^actions(?:\.([a-z][a-z_0-9]*))?(\+?=)(?:/)?(.+)$")
COMMAND = re.compile(r"^[a-z][a-z_0-9]*$")
IDENT = r"[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_0-9]+)*"
NUMBER = r"(?:[0-9]+\.[0-9]+|[0-9]+)"
OPERATORS = ("~!=", "~<=", "~>=", "~=", "~<", "~>", "!=", "<=", ">=",
             "%%", "<?", ">?", "&", "|", "^", "<", ">", "=", "+",
             "-", "*", "%", "!", "@", "(", ")")
TOKEN_PATTERN = re.compile(
    r"(?:~!=|~<=|~>=|~=|~<|~>|!=|<=|>=|%%|<\?|>\?|"
    r"[&|^<>=+\-*%!@()]|"
    + NUMBER + r"|" + IDENT + r")"
)
EXPR_ATTRIBUTES = {
    "if", "condition", "value", "value_else", "target_if",
    "interrupt_if", "cancel_if", "early_chain_if", "sec", "extra_amount"
}
CONTROL = {"call_action_list", "run_action_list", "swap_action_list"}
VARIABLE_OPS = {"set", "setif", "reset", "floor", "ceil", "add", "sub", "mul", "div", "min", "max"}
PREC = {
    "|": 10, "^": 20, "&": 30,
    "=": 40, "!=": 40, "<": 40, "<=": 40, ">": 40, ">=": 40,
    "~=": 40, "~!=": 40, "~<": 40, "~<=": 40, "~>": 40, "~>=": 40,
    "<?": 50, ">?": 50, "+": 60, "-": 60,
    "*": 70, "%": 70, "%%": 70,
}
PREFIX = {"!", "+", "-", "@"}

class AplError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_blob(value: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(value)).encode("ascii") + b"\0" + value
    ).hexdigest()


def tokenize(expr: str):
    if not isinstance(expr, str) or not expr or len(expr) > 3000:
        raise AplError("EXPRESSION_EMPTY_OR_OVERSIZED")
    result = []
    pos = 0
    while pos < len(expr):
        match = TOKEN_PATTERN.match(expr, pos)
        if not match:
            raise AplError("UNRECOGNIZED_EXPRESSION_AT_" + str(pos) + ":" + expr[pos:pos + 16])
        result.append(match.group())
        pos = match.end()
    if len(result) > 800:
        raise AplError("EXPRESSION_TOKEN_BUDGET")
    return result


class Expression:
    def __init__(self, source: str):
        self.source = source
        self.words = tokenize(source)
        self.at = 0

    def peek(self):
        return self.words[self.at] if self.at < len(self.words) else None

    def consume(self, expected=None):
        value = self.peek()
        if value is None or (expected is not None and value != expected):
            raise AplError("INVALID_EXPRESSION_AT_" + str(self.at))
        self.at += 1
        return value

    def prefix(self):
        token = self.consume()
        if token in PREFIX:
            return ["unary", token, self.expr(80)]
        if token == "(":
            value = self.expr(0)
            self.consume(")")
            return value
        if re.fullmatch(NUMBER, token):
            return ["number", float(token)]
        if re.fullmatch(IDENT, token):
            if self.peek() == "(":
                self.consume("(")
                arg = self.expr(0)
                self.consume(")")
                if token not in ("floor", "ceil"):
                    raise AplError("UNSUPPORTED_FUNCTION_" + token)
                return ["function", token, arg]
            return ["symbol", token]
        raise AplError("EXPRESSION_OPERAND_MISSING_" + token)

    def expr(self, minimum=0):
        left = self.prefix()
        while self.peek() in PREC and PREC[self.peek()] >= minimum:
            op = self.consume()
            right = self.expr(PREC[op] + 1)
            left = ["binary", op, left, right]
        return left

    def parse(self):
        ast = self.expr(0)
        if self.peek() is not None:
            raise AplError("TRAILING_EXPRESSION_TOKENS_" + str(self.at))
        return ast


def ast_symbols(node):
    if node[0] == "symbol":
        return {node[1]}
    if node[0] == "number":
        return set()
    if node[0] in ("unary", "function"):
        return ast_symbols(node[2])
    if node[0] == "binary":
        return ast_symbols(node[2]) | ast_symbols(node[3])
    raise AplError("INVALID_AST_KIND")


def truth(value):
    if value is None:
        return None
    if type(value) not in (float, int, bool):
        raise AplError("NON_NUMERIC_EXPRESSION_VALUE")
    if not math.isfinite(float(value)):
        return None
    return value != 0


def _safe_number(value):
    if type(value) not in (float, int, bool):
        return None
    try:
        numeric = float(value)
    except (OverflowError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def evaluate_ast(node, facts, *, action_timestamp=None, strict_pre=False):
    """Numbers plus UNKNOWN; NO implicit WoW state lookup.

    facts: {symbol: number} in synthetic source-matched tests or
    {symbol: {value:number, timestamp:number, provenance:'STRICT_PRE_OBSERVATION'}}
    for separately verified actual decision replay. If strict_pre=True, bare
    numbers / undefined provenance are UNKNOWN, and timestamps >= action t
    never leak.
    """
    kind = node[0]
    if kind == "number":
        return node[1]
    if kind == "symbol":
        record = facts.get(node[1])
        if isinstance(record, dict):
            if record.get("provenance") != "STRICT_PRE_OBSERVATION":
                return None
            ts = record.get("timestamp")
            if (type(ts) not in (int, float) or
                type(action_timestamp) not in (int, float) or
                ts >= action_timestamp):
                return None
            return _safe_number(record.get("value"))
        return None if strict_pre else _safe_number(record)
    if kind in ("unary", "function"):
        value = evaluate_ast(node[2], facts, action_timestamp=action_timestamp,
                             strict_pre=strict_pre)
        if value is None:
            return None
        if kind == "function":
            return float(math.floor(value) if node[1] == "floor" else math.ceil(value))
        return {"!": lambda x: float(not truth(x)), "+": lambda x: x,
                "-": lambda x: -x, "@": abs}[node[1]](value)
    if kind != "binary":
        raise AplError("UNKNOWN_AST_KIND")
    op = node[1]
    left = evaluate_ast(node[2], facts, action_timestamp=action_timestamp,
                        strict_pre=strict_pre)
    if op in ("&", "|"):
        p = truth(left)
        if (op == "&" and p is False) or (op == "|" and p is True):
            return float(p)
    right = evaluate_ast(node[3], facts, action_timestamp=action_timestamp,
                         strict_pre=strict_pre)
    if op in ("&", "|", "^"):
        a, b = truth(left), truth(right)
        if op == "&":
            return 0.0 if a is False or b is False else (
                1.0 if a is True and b is True else None)
        if op == "|":
            return 1.0 if a is True or b is True else (
                0.0 if a is False and b is False else None)
        return None if a is None or b is None else float(a != b)
    if left is None or right is None:
        return None
    try:
        if op == "+": result = left + right
        elif op == "-": result = left - right
        elif op == "*": result = left * right
        elif op == "%": result = left / right  # SimC division
        elif op == "%%": result = math.fmod(left, right)  # SimC remainder
        elif op == "<?": result = max(left, right)
        elif op == ">?": result = min(left, right)
        else:
            fuzzy = op.startswith("~")
            compare = op[1:] if fuzzy else op
            eps = 1e-9 if fuzzy else 0
            if compare == "=": result = abs(left - right) <= eps
            elif compare == "!=": result = abs(left - right) > eps
            elif compare == "<": result = left < right - eps
            elif compare == "<=": result = left <= right + eps
            elif compare == ">": result = left > right + eps
            elif compare == ">=": result = left >= right - eps
            else: raise AplError("BAD_COMPARISON_" + op)
        return _safe_number(result)
    except (ZeroDivisionError, ValueError, OverflowError):
        return None


def split_options(source):
    result = []
    depth = 0
    start = 0
    for index, char in enumerate(source):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0: raise AplError("BAD_OPTION_PARENS")
        elif char == "," and depth == 0:
            result.append(source[start:index])
            start = index + 1
    if depth: raise AplError("UNTERMINATED_OPTION_PARENS")
    result.append(source[start:])
    return result


def _interpret_class(command, attributes):
    if command in CONTROL:
        return "CALL" if command == "call_action_list" else (
            "RUN" if command == "run_action_list" else "SWAP_UNSUPPORTED")
    if command == "variable":
        return "VARIABLE"
    if command in {"auto_attack", "snapshot_stats"}:
        return "SIDE_EFFECT_SOURCE_MODEL_UNVERIFIED"
    return "ACTION"


def parse_profile(raw, *, require_source=True, expected_git_blob=PROFILE_GIT_BLOB):
    if require_source:
        if (not isinstance(expected_git_blob,str) or
            not re.fullmatch(r"[a-f0-9]{40}",expected_git_blob)):
            raise AplError("EXACT_SOURCE_GIT_BLOB_REQUIRED")
        if git_blob(raw) != expected_git_blob:
            raise AplError("PINNED_PROFILE_SOURCE_BLOB_MISMATCH")
    decoded = raw.decode("utf-8")
    lists = {}
    parsed = 0
    non_action_lines = 0
    dependencies = defaultdict(list)
    variables = defaultdict(list)
    for source_line, text in enumerate(decoded.splitlines(), 1):
        if not text.startswith("actions"):
            non_action_lines += 1
            continue
        m = ROW.fullmatch(text)
        if not m:
            raise AplError("UNPARSED_SOURCE_ACTION_LINE_" + str(source_line))
        list_name, mode, remainder = m.groups()
        list_name = list_name or "default"
        if mode == "=":
            if list_name in lists:
                raise AplError("ACTION_LIST_REINITIALIZED_" + list_name)
            lists[list_name] = []
        elif list_name not in lists:
            raise AplError("UNDEFINED_LIST_APPENDED_" + list_name)
        pieces = split_options(remainder)
        command = pieces[0]
        if not COMMAND.fullmatch(command):
            raise AplError("UNRECOGNIZED_SOURCE_ACTION_" + command)
        attributes = []
        indexed = {}
        compiled = {}
        for entry in pieces[1:]:
            key, sep, value = entry.partition("=")
            if not sep or not COMMAND.fullmatch(key) or not value:
                raise AplError("MALFORMED_ACTION_ATTRIBUTE_AT_" + str(source_line))
            if key in indexed:
                raise AplError("DUPLICATE_ACTION_ATTRIBUTE_" + key)
            attributes.append({"key": key, "value": value})
            indexed[key] = value
            if key in EXPR_ATTRIBUTES:
                ast = Expression(value).parse()
                compiled[key] = {"source": value, "ast": ast,
                                 "symbols": sorted(ast_symbols(ast))}
        behavior = _interpret_class(command, indexed)
        if behavior in ("CALL", "RUN", "SWAP_UNSUPPORTED"):
            name = indexed.get("name")
            if not name or not COMMAND.fullmatch(name):
                raise AplError("LIST_CALL_WITHOUT_VALID_NAME")
            dependencies[list_name].append({
                "destination": name, "kind": behavior,
                "source_line": source_line})
        if behavior == "VARIABLE":
            name = indexed.get("name")
            if not name or not COMMAND.fullmatch(name):
                raise AplError("VARIABLE_WITHOUT_NAME")
            operation = indexed.get("op", "set")
            if operation not in VARIABLE_OPS:
                raise AplError("UNSUPPORTED_VARIABLE_OP_" + operation)
            if operation == "setif" and not all(
                 key in compiled for key in ("value", "value_else", "condition")):
                raise AplError("INCOMPLETE_VARIABLE_SETIF")
            variables[name].append({
                "source_line": source_line, "operation": operation,
                "list": list_name, "index": len(lists[list_name])})
        row = {
            "list": list_name, "index": len(lists[list_name]),
            "source_line": source_line,
            "source_text": text, "source_sha256": sha256(text.encode("utf-8")),
            "action": command, "behavior": behavior,
            "attributes": attributes, "expression_fields": compiled,
            "source_priority_is_ordered": True,
            "gameplay_ready": "UNKNOWN",
            "native_SimC_action_ready_parity": "NOT_PROVEN",
        }
        lists[list_name].append(row)
        parsed += 1
    for from_list, targets in dependencies.items():
        for target in targets:
            if target["destination"] not in lists:
                raise AplError("UNDECLARED_LIST_TARGET_" + target["destination"])
    if "default" not in lists:
        raise AplError("DEFAULT_ACTION_LIST_MISSING")
    visiting = set()
    visited = set()
    def walk(name):
        if name in visiting:raise AplError("CYCLIC_ACTION_LIST_" + name)
        if name in visited:return
        visiting.add(name)
        for edge in dependencies[name]:
            walk(edge["destination"])
        visiting.remove(name)
        visited.add(name)
    for name in lists:walk(name)
    count = sum(len(items) for items in lists.values())
    if count != parsed:
        raise AplError("SOURCE_LINE_RECONCILIATION_FAILED")
    controls = Counter(r["behavior"] for items in lists.values() for r in items)
    used_expressions = Counter(k for group in lists.values()
                              for r in group for k in r["expression_fields"])
    source_tokens = {symbol for items in lists.values()
                      for r in items for c in r["expression_fields"].values()
                      for symbol in c["symbols"]}
    variable_duplicates = {name: rows for name, rows in variables.items()
                           if len(rows) > 1}
    return {
        "schema": SCHEMA, "scope_policy_id": POLICY,
        "source_git_blob_sha1": git_blob(raw),
        "source_sha256": sha256(raw), "profile_size": len(raw),
        "source_action_line_count": parsed,
        "non_action_profile_line_count": non_action_lines,
        "action_lists": lists,
        "action_list_counts": {k: len(v) for k, v in lists.items()},
        "graph_edges": dict(dependencies),
        "variable_definitions": dict(variables),
        "duplicate_variable_definition_sites": variable_duplicates,
        "control_counts": dict(controls),
        "expression_attribute_counts": dict(used_expressions),
        "source_symbol_dependencies": sorted(source_tokens),
        "expression_syntax_coverage": "COMPLETE_FOR_THIS_PINNED_PROFILE",
        "source_list_graph_coverage": "COMPLETE_FOR_THIS_PINNED_PROFILE",
        "semantic_runtime_equivalence_to_native_SimC": "NOT_YET_TESTED",
        "precombat_to_opener_native_equivalence": "NOT_YET_TESTED",
        "model_ready_for_WCL_priority_comparison": False,
        "WCL_evidence_consulted_in_candidate_compilation": False,
        "MAIN_promotion": False,
    }


def _source_attributes(row):
    return {a["key"]: a["value"] for a in row["attributes"]}


def variable_effect(row, facts, *, timestamp=None, strict_pre=False):
    """Bounded variable calculation; unknown expression never implies zero."""
    if row["behavior"] != "VARIABLE":
        raise AplError("NON_VARIABLE_ACTION_AS_VARIABLE")
    fields = _source_attributes(row)
    op = fields.get("op", "set")
    name = fields["name"]
    exprs = row["expression_fields"]
    def value(k):
        return evaluate_ast(exprs[k]["ast"], facts,
                            action_timestamp=timestamp,
                            strict_pre=strict_pre) if k in exprs else None
    before = facts.get("variable." + name)
    if isinstance(before, dict):
        before = before.get("value")
    old = _safe_number(before)
    if op == "set":
        result = value("value")
    elif op == "setif":
        clause = truth(value("condition"))
        t, f = value("value"), value("value_else")
        result = t if clause is True else f if clause is False else (
            t if t is not None and t == f else None)
    elif op == "reset":
        result = float(fields.get("default", "0"))
    elif op in ("floor", "ceil"):
        v = value("value")
        result = None if v is None else float(math.floor(v) if op == "floor" else math.ceil(v))
    else:
        # These exist in the wider SimC grammar but are not source-validated
        # for exact side-effect behavior by the pinned Fury fixture.
        result = None
    return {"name": name, "operation": op, "value": result,
            "status": "EVALUATED" if result is not None else "UNKNOWN",
            "native_side_effect_equivalence": "NOT_PROVEN"}


def bounded_decision(ir, facts, readiness, *, timestamp=None,
                     start_list="default", budget=300, strict_pre=False):
    """Safe, conservative flow evaluator for source-ordered list control.

    Distinguishes CALL fallback from RUN transfer. Only externally evidenced
    row readiness may yield a HYPOTHETICAL selected action; no automatic
    readiness for auto_attack, racials, trinkets, variables, or ordinary spells.
    No native parity or user-error claim.
    """
    lists = ir["action_lists"]
    if start_list not in lists:raise AplError("START_LIST_NOT_FOUND")
    copied = dict(facts)
    consulted = []
    steps = 0
    def examine(name, stack):
        nonlocal steps
        if name in stack:raise AplError("DYNAMIC_CYCLE")
        for row in lists[name]:
            steps += 1
            if steps > budget:
                return {"verdict": "UNKNOWN", "reason": "EXECUTION_BUDGET_EXCEEDED"}
            attrs = row["expression_fields"]
            cond = evaluate_ast(attrs["if"]["ast"], copied,
                                action_timestamp=timestamp,
                                strict_pre=strict_pre) if "if" in attrs else 1.0
            ck = truth(cond)
            if ck is False:
                continue
            consulted.append({"list": name, "index": row["index"],
                              "source_line": row["source_line"],
                              "guard": "TRUE" if ck is True else "UNKNOWN"})
            if ck is None:
                return {"verdict": "UNKNOWN", "reason": "CONDITION_UNOBSERVED",
                        "blocking_source_line": row["source_line"]}
            behavior = row["behavior"]
            if behavior == "RUN":
                # Native run_action_list_t is ACTION_OTHER, not ACTION_CALL:
                # it is QUEUED and execute() changes active_action_list
                # asynchronously. The next execute_action() evaluates that
                # destination and restores the caller after selection.
                # Recurse here and choosing its first row *now* was wrong.
                dest = _source_attributes(row)["name"]
                return {
                    "verdict": "HYPOTHETICAL_RUN_LIST_CONTROL_ACTION",
                    "source_list": name,
                    "source_index": row["index"],
                    "destination": dest,
                    "state_change_event": "AFTER_QUEUED_RUN_ACTION_EXECUTES",
                    "next_scan_active_list_if_executed": dest,
                    "native_action_selected_now": "run_action_list",
                    "foreground_spell_selected_now": None,
                    "native_runtime_parity_proven": False,
                    "dummy_error_verdict": "UNKNOWN"
                }
            if behavior == "CALL":
                # Native call_action_list_t is ACTION_CALL; select_action()
                # recursively evaluates the target in the same scan and
                # falls back to caller if the target returns no action.
                dest = _source_attributes(row)["name"]
                result = examine(dest, stack + [name])
                if result is not None:
                    return result
                continue
            if behavior == "SWAP_UNSUPPORTED":
                return {"verdict": "UNKNOWN", "reason": "SWAP_LIST_NOT_IMPLEMENTED"}
            if behavior == "VARIABLE":
                v = variable_effect(row, copied, timestamp=timestamp, strict_pre=strict_pre)
                if v["status"] != "EVALUATED":
                    return {"verdict": "UNKNOWN", "reason": "VARIABLE_VALUE_UNOBSERVED",
                            "variable": v["name"]}
                copied["variable." + v["name"]] = v["value"]
                continue
            k = name + ":" + str(row["index"])
            state = readiness.get(k, "UNKNOWN")
            if state not in ("READY", "NOT_READY", "UNKNOWN"):
                raise AplError("INVALID_READINESS_VERDICT")
            if state == "NOT_READY":
                continue
            if state == "UNKNOWN":
                return {"verdict": "UNKNOWN", "reason": "ACTION_READINESS_UNOBSERVED",
                        "blocking_source_line": row["source_line"]}
            return {"verdict": "HYPOTHETICAL_SOURCE_ROW",
                    "action": row["action"], "list": name,
                    "index": row["index"], "source_line": row["source_line"],
                    "native_SimC_parity_proven": False,
                    "WCL_priority_verified": False,
                    "dummy_error_verdict": "UNKNOWN"}
        return None
    result = examine(start_list, [])
    return {"result": result if result is not None else {
                "verdict": "UNKNOWN", "reason": "NO_ACTION_AVAILABLE"},
            "consulted_source_rows": consulted,
            "readiness_derived_from_SimC_profile": False,
            "model_gameplay_authority": "RESEARCH_ONLY"}


def bounded_control_step(ir, facts, readiness, control, *,
                         timestamp=None, strict_pre=False):
    """Synthetic/native-replay scaffolding for one select_action scan.

    State describes the SimC active APL and pending restore list. A queued
    run control action takes effect only on its execute() event, represented
    by a separate accepted transition here; this is NOT a game action cast.
    Native scheduling and chooser equivalence still require validation.
    """
    if not isinstance(control, dict):
        raise AplError("CONTROL_STATE_REQUIRED")
    active = control.get("active_list", "default")
    restore = control.get("restore_list")
    if active not in ir["action_lists"]:
        raise AplError("CONTROL_ACTIVE_LIST_NOT_IN_SOURCE")
    if restore is not None and restore not in ir["action_lists"]:
        raise AplError("CONTROL_RESTORE_LIST_NOT_IN_SOURCE")
    prior = {"active_list": active, "restore_list": restore}
    outcome = bounded_decision(
        ir, facts, readiness, timestamp=timestamp, start_list=active,
        strict_pre=strict_pre)
    result = outcome["result"]
    updated = dict(prior)
    kind = result["verdict"]
    if kind == "HYPOTHETICAL_RUN_LIST_CONTROL_ACTION":
        if restore is not None:
            # It could be nested source state. A real player_t only captures
            # restore_action_list if nullptr, so keep original restore.
            updated["restore_list"] = restore
        else:
            updated["restore_list"] = active
        updated["active_list"] = result["destination"]
        phase = "QUEUED_RUN_EXECUTED_MODEL_TRANSITION"
    elif restore is not None:
        # Native player_t::execute_action restores after select_action
        # even if select_action returns nullptr. Never skip this restore.
        updated = {"active_list": restore, "restore_list": None}
        phase = "MODEL_RESTORE_AFTER_NEXT_SELECT"
    else:
        phase = "NO_LIST_TRANSITION"
    return {
        "result": result,
        "state_before": prior,
        "state_after_model": updated,
        "phase": phase,
        "full_native_event_order_parity": "NOT_PROVEN",
        "WCL_recommendation_authorized": False,
        "actual_native_select_trace_required": True
    }


def selftest():
    assert Expression("3%2").parse() == [
        "binary", "%", ["number", 3.0], ["number", 2.0]]
    cases = [
        ("3%2", {}, 1.5), ("9%%2.5", {}, 1.5),
        ("1+2*3", {}, 7), ("(1+2)*3", {}, 9),
        ("floor(-2.5)", {}, -3), ("ceil(2.2)", {}, 3),
        ("@(-3)", {}, 3), ("4<?7", {}, 7), ("4>?7", {}, 4),
        ("3&4", {}, 1), ("0|9", {}, 1), ("1^1", {}, 0),
        ("trinket.1.cooldown.duration%%cooldown.recklessness.duration=0",
         {"trinket.1.cooldown.duration": 120,
          "cooldown.recklessness.duration": 60}, 1),
        ("0.5+1", {}, 1.5),
    ]
    for s, f, expected in cases:
        actual = evaluate_ast(Expression(s).parse(), f)
        if actual is None or abs(actual - expected) > 1e-9:
            raise AssertionError(("EXPRESSION_MISMATCH", s, actual, expected))
    assert evaluate_ast(Expression("unknown&0").parse(), {}) == 0
    assert evaluate_ast(Expression("unknown|1").parse(), {}) == 1
    assert evaluate_ast(Expression("unknown|0").parse(), {}) is None
    # Strict PRE is explicitly enforced, regardless of expression truth.
    assert evaluate_ast(Expression("rage>=100").parse(), {
        "rage": {"value": 120, "timestamp": 100,
                 "provenance": "STRICT_PRE_OBSERVATION"}},
        action_timestamp=100, strict_pre=True) is None
    assert evaluate_ast(Expression("rage>=100").parse(), {
        "rage": {"value": 120, "timestamp": 99,
                 "provenance": "STRICT_PRE_OBSERVATION"}},
        action_timestamp=100, strict_pre=True) == 1
    for x in ("a;evil", "foo(x)", "(a+b", "a??b", "a/b"):
        try: Expression(x).parse()
        except AplError: pass
        else: raise AssertionError(("BAD_EXPRESSION_ACCEPTED", x))
    simple = (
       b"actions=call_action_list,name=sub\n"
       b"actions+=/filler\n"
       b"actions.sub=alpha,if=rage>=100\n"
       b"actions.sub+=/beta\n"
    )
    ir = parse_profile(simple, require_source=False)
    assert ir["source_action_line_count"] == 4
    a = bounded_decision(ir, {"rage": 50},
                         {"sub:1": "NOT_READY", "default:1": "READY"})
    assert a["result"]["action"] == "filler"
    b = bounded_decision(ir, {"rage": 150},
                         {"sub:0": "READY", "default:1": "READY"})
    assert b["result"]["action"] == "alpha"
    c = bounded_decision(ir, {"rage": 150},
                         {"sub:0": "UNKNOWN", "default:1": "READY"})
    assert c["result"]["verdict"] == "UNKNOWN"
    run_profile = simple.replace(b"call_action_list", b"run_action_list")
    native_run_ir = parse_profile(run_profile, require_source=False)
    d = bounded_decision(native_run_ir,
                         {"rage": 50}, {"sub:1": "NOT_READY",
                                       "default:0": "READY", "default:1": "READY"})
    assert d["result"]["verdict"] == "HYPOTHETICAL_RUN_LIST_CONTROL_ACTION"
    assert d["result"]["foreground_spell_selected_now"] is None
    assert d["result"]["destination"] == "sub"
    # The first scan selects a quiet run control action. NOT alpha, beta
    # or the caller's filler. In the following scan, if the destination has
    # no eligible action, caller filler is still NOT selected that scan.
    first=bounded_control_step(native_run_ir, {"rage":50},
        {"default:0":"READY", "default:1":"READY", "sub:1":"NOT_READY"}, {})
    assert first["phase"]=="QUEUED_RUN_EXECUTED_MODEL_TRANSITION"
    assert first["state_after_model"]=={
        "active_list":"sub","restore_list":"default"}
    second=bounded_control_step(native_run_ir, {"rage":50},
        {"default:1":"READY", "sub:1":"NOT_READY"},
        first["state_after_model"])
    assert second["result"]["verdict"]=="UNKNOWN"
    assert second["phase"]=="MODEL_RESTORE_AFTER_NEXT_SELECT"
    assert second["state_after_model"]=={
        "active_list":"default","restore_list":None}
    third=bounded_control_step(native_run_ir, {"rage":50},
        {"default:0":"NOT_READY","default:1":"READY"}, second["state_after_model"])
    assert third["result"]["action"]=="filler"
    # A runnable destination action is selected only on the NEXT scan.
    first=bounded_control_step(native_run_ir, {"rage":150},
        {"default:0":"READY","sub:0":"READY"}, {})
    second=bounded_control_step(native_run_ir, {"rage":150},
        {"sub:0":"READY"}, first["state_after_model"])
    assert first["result"]["foreground_spell_selected_now"] is None
    assert second["result"]["action"]=="alpha"
    assert second["state_after_model"]=={
        "active_list":"default","restore_list":None}
    var = (
        b"actions=variable,name=x,op=setif,value=5,value_else=2,condition=rage>=100\n"
        b"actions+=/filler,if=variable.x=5\n"
    )
    e = bounded_decision(parse_profile(var, require_source=False),
                         {"rage": 120}, {"default:1": "READY"})
    assert e["result"]["action"] == "filler"
    f = bounded_decision(parse_profile(var, require_source=False),
                         {}, {"default:1": "READY"})
    assert f["result"]["verdict"] == "UNKNOWN"
    assert Expression("1-2+3").parse()[0] == "binary"
    sample2=b"actions=spell,if=rage>30\n"
    assert parse_profile(sample2,require_source=True,
                         expected_git_blob=git_blob(sample2))["source_action_line_count"]==1
    try:parse_profile(sample2,require_source=True,
                      expected_git_blob="a"*40)
    except AplError:pass
    else:raise AssertionError("SOURCE_PIN_BYPASSED")
    return {"status": "PASS_OFFLINE_SYNTHETIC", "checks": 48,
            "source_SimC_profile_loaded": False,
            "WCL_observations_used": False,
            "native_SimC_parity_proven": False,
            "trainer_mistake_verdict": "UNKNOWN"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--expected-git-blob",default=PROFILE_GIT_BLOB,
                        help="Pinned official source Git blob SHA1; override for other specs/builds")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    value = (parse_profile(args.profile.read_bytes(),
                           expected_git_blob=args.expected_git_blob)
             if args.profile else selftest())
    blob = canonical(value)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("xb") as output: output.write(blob)
        print("SIMC_SEMANTIC_IR_V2_SHA256=" + sha256(blob))
    else:
        print(blob.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
