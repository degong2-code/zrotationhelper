#!/usr/bin/env python3
"""Bounded SimC APL priority traversal (research hypotheses, NOT gameplay advice).

Consumes a generic exported source model, actual strict-PRE state observations
and an explicit action-readiness map. No class/boss/sequence hardcodes.

Scope: ordered IF guards, nested call/run lists and same-scan variable sets.
Unsafe, unsupported or unobserved semantics BLOCK traversal at the first
higher-priority uncertain decision; unknown never means unavailable.
SimC source: simulationcraft/simc Wiki ActionLists (2026).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from simc_apl_condition_research import bind_strict_pre, evaluate

ALLOWED_SCHEMA = "ZrotGenericSimcAplSourceHypothesisV1"
BLOCK = "BLOCKED"
CANDIDATE = "HYPOTHESIS_CANDIDATE"
EXHAUSTED = "NO_DETERMINABLE_ACTION"

@dataclass(frozen=True)
class AplTrace:
    status: str
    candidate_action_token: str | None
    list_name: str | None
    source_line: int | None
    reason: str
    trace: tuple[dict[str, Any], ...]
    provenance: dict[str, Any]
    actionable: bool = False
    wcl_validation: str = "NOT_RUN"


def trace_priority(
    model: Mapping[str, Any],
    *,
    strict_pre_state: Any,
    spec_slug: str,
    operand_to_feature: Mapping[str, str],
    action_readiness: Mapping[str, str],
    expected_apl_sha256: str,
    expected_profile_sha256: str | None = None,
) -> AplTrace:
    """Traverse one SimC APL scan. Readiness must be external/observed.

    Even a found READY action is a *hypothesis* only; this API never promotes
    a General Rotation rule. Missing readiness or condition blocks, not skips.
    """
    if model.get("schema") != ALLOWED_SCHEMA:
        raise ValueError("UNSUPPORTED_HYPOTHESIS_SCHEMA")
    if model.get("expected_spec") != spec_slug or not spec_slug:
        raise ValueError("SPEC_IDENTITY_MISMATCH")
    if model.get("apl_sha256") != expected_apl_sha256 or not expected_apl_sha256:
        raise ValueError("APL_SOURCE_PIN_MISMATCH")
    if (expected_profile_sha256 is not None
            and model.get("profile_sha256") != expected_profile_sha256):
        raise ValueError("PROFILE_PIN_MISMATCH")
    if model.get("actionable_general_rotation") is not False:
        raise ValueError("PREMATURE_GAMEPLAY_PROMOTION")
    strict_pre_state.validate()
    values = bind_strict_pre(strict_pre_state,
                             operand_to_feature=operand_to_feature)
    groups: dict[str, list[dict]] = {k: [] for k in model.get("lists", [])}
    if "default" not in groups:
        raise ValueError("DEFAULT_ACTION_LIST_MISSING")
    for row in model.get("rows", []):
        list_name = row.get("list")
        if list_name not in groups:
            raise ValueError("INVALID_LIST_ROW")
        if row.get("hypothesis_only") is not True:
            raise ValueError("NON_HYPOTHESIS_ROW")
        groups[list_name].append(row)
    for name, rows in groups.items():
        seen = set()
        for index, row in enumerate(rows, 1):
            rank = row.get("list_rank")
            if type(rank) is not int or rank != index or rank in seen:
                raise ValueError("ROW_ORDER_NOT_PINNED")
            seen.add(rank)
    events: list[dict[str, Any]] = []
    variable_values: dict[str, float] = {}

    def outcome(status, token, list_name, line, reason):
        return AplTrace(
            status, token, list_name, line, reason, tuple(events),
            {"spec_slug": spec_slug, "apl_sha256": expected_apl_sha256,
             "profile_sha256": model.get("profile_sha256"),
             "strict_pre_timestamp_ms": strict_pre_state.state_timestamp_max_ms,
             "decision_timestamp_ms": strict_pre_state.decision_timestamp_ms},
        )

    def condition(expression):
        # Variables in the current pass overwrite only the corresponding
        # operands; all external values are explicit prior observations.
        bound = dict(values)
        bound.update({"variable." + k: v for k, v in variable_values.items()})
        return evaluate(expression, bound_values=bound,
                        decision_timestamp_ms=strict_pre_state.decision_timestamp_ms,
                        state_timestamp_max_ms=strict_pre_state.state_timestamp_max_ms)

    def visit(group_name: str, active: tuple[str, ...]):
        if group_name in active or len(active) >= 32:
            return outcome(BLOCK, None, group_name, None,
                           "APL_LIST_CYCLE_OR_DEPTH")
        rows = groups.get(group_name)
        if rows is None:
            return outcome(BLOCK, None, group_name, None, "UNRESOLVED_LIST")
        for row in rows:
            command = row["command_token"]
            line = row["source_line"]
            params = dict(row["params"])
            guard = row.get("guard")
            if guard is not None:
                test = condition(guard)
                events.append({"list": group_name, "line": line, "command": command,
                               "kind": "GUARD", "status": test.status})
                if test.status == "FALSE":
                    continue
                if test.status != "TRUE":
                    return outcome(BLOCK, None, group_name, line,
                                   "GUARD_" + test.status)
            if command in ("call_action_list", "run_action_list"):
                # 'name' is the only supported control modifier at this stage.
                if set(params) - {"name", "if"} or not params.get("name"):
                    return outcome(BLOCK, None, group_name, line,
                                   "UNSUPPORTED_LIST_MODIFIERS")
                target = params["name"]
                child = visit(target, (*active, group_name))
                if child.status != EXHAUSTED:
                    return child
                if command == "run_action_list":
                    return outcome(BLOCK, None, group_name, line,
                                   "RUN_LIST_YIELD_NO_FALLTHROUGH")
                continue
            if command == "variable":
                if set(params) - {"name", "if", "op", "value"}:
                    return outcome(BLOCK, None, group_name, line,
                                   "UNSUPPORTED_VARIABLE_MODIFIERS")
                variable = params.get("name", "")
                op = params.get("op", "set")
                if not variable or not variable.replace("_","").isalnum():
                    return outcome(BLOCK, None, group_name, line,
                                   "INVALID_VARIABLE_NAME")
                if op != "set" or "value" not in params:
                    return outcome(BLOCK, None, group_name, line,
                                   "VARIABLE_OPERATION_NOT_SUPPORTED")
                value = condition(params["value"])
                if value.status not in ("TRUE", "FALSE") or value.value is None:
                    return outcome(BLOCK, None, group_name, line,
                                   "VARIABLE_VALUE_" + value.status)
                variable_values[variable] = value.value
                events.append({"list": group_name, "line": line,
                               "command": command, "kind": "VARIABLE_SET",
                               "variable": variable})
                continue
            # Not safe to ignore directives that may change action flow.
            if row["role"] != "ACTION_TOKEN":
                return outcome(BLOCK, None, group_name, line,
                               "UNSUPPORTED_CONTROL_DIRECTIVE")
            # Unmodeled targeting, action timing and runtime effects matter.
            if set(params) - {"if"}:
                return outcome(BLOCK, None, group_name, line,
                               "UNSUPPORTED_ACTION_MODIFIERS")
            ready = action_readiness.get(command, "UNKNOWN")
            if ready not in ("READY", "NOT_READY", "UNKNOWN", "UNOBSERVABLE"):
                raise ValueError("INVALID_ACTION_READINESS")
            events.append({"list": group_name, "line": line, "command": command,
                           "kind": "ACTION_READINESS", "status": ready})
            if ready == "NOT_READY":
                continue
            if ready != "READY":
                return outcome(BLOCK, None, group_name, line,
                               "ACTION_READINESS_" + ready)
            return outcome(CANDIDATE, command, group_name, line,
                           "ORDERED_APL_READY_HYPOTHESIS_NOT_VALIDATED")
        return outcome(EXHAUSTED, None, group_name, None,
                       "NO_ACTION_IN_LIST")

    return visit("default", ())


def selftest():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] /
                           "02_SOURCE" / "runtime"))
    from raid_dps.core.behavioral_evaluator import (
        StrictPreStateProvider, StateTransition,
    )
    from simc_apl_source_engine import ingest_actions
    import hashlib
    p = (
        b"spec=enhancement\n"
        b"actions=variable,name=threshold,op=set,value=4\n"
        b"actions+=/call_action_list,name=burst,if=active_enemies=1\n"
        b"actions+=/lava_lash,if=active_enemies=1\n"
        b"actions+=/stormstrike\n"
        b"actions.burst=lightning_bolt,if=buff.foo.stack>=variable.threshold\n"
        b"actions.burst+=/frost_shock,if=talent.unknown.enabled\n"
    )
    model = ingest_actions(p, expected_spec="enhancement")
    state = StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=(StateTransition(900, "stack", 5),
                     StateTransition(900, "targets", 1),
                     StateTransition(1000, "stack", 0),
                     StateTransition(1001, "targets", 5)),
        required_keys=("stack", "targets"),
    )
    kw = dict(model=model, strict_pre_state=state,
              spec_slug="enhancement",
              operand_to_feature={
                  "active_enemies": "targets",
                  "buff.foo.stack": "stack",
                  "talent.unknown.enabled": "unknown"},
              expected_apl_sha256=hashlib.sha256(p).hexdigest())
    one = trace_priority(**kw,
                         action_readiness={"lightning_bolt": "READY",
                                           "lava_lash":"READY"})
    assert one.status == CANDIDATE and one.candidate_action_token == "lightning_bolt"
    assert one.source_line == 6 and not one.actionable
    assert one.provenance["strict_pre_timestamp_ms"] == 900
    two = trace_priority(**kw,
                         action_readiness={"lightning_bolt":"NOT_READY",
                                           "lava_lash":"READY"})
    assert two.status == BLOCK and two.reason == "GUARD_UNKNOWN"
    three = trace_priority(**kw,
                           action_readiness={"lightning_bolt":"UNKNOWN",
                                             "lava_lash":"READY"})
    assert three.status == BLOCK and three.reason == "ACTION_READINESS_UNKNOWN"
    # Resolve the unknown talent to false; child sublist exhausted and returns
    # to the next parent row if called with call_action_list.
    state2 = StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=(StateTransition(900, "stack", 5),
                     StateTransition(900, "targets", 1),
                     StateTransition(900, "known_talent", 0)))
    known = dict(kw, strict_pre_state=state2, operand_to_feature={
        **kw["operand_to_feature"], "talent.unknown.enabled":"known_talent"})
    four = trace_priority(**known, action_readiness={
        "lightning_bolt":"NOT_READY","lava_lash":"READY"})
    assert four.candidate_action_token == "lava_lash"
    # The run_action_list path does NOT return to the lower-priority parent.
    run_model = ingest_actions(p.replace(b"call_action_list", b"run_action_list"),
                               expected_spec="enhancement")
    no_fall = trace_priority(**(known | {
        "model": run_model,
        "expected_apl_sha256":hashlib.sha256(
            p.replace(b"call_action_list", b"run_action_list")).hexdigest()}),
        action_readiness={"lightning_bolt":"NOT_READY","lava_lash":"READY"})
    assert no_fall.status == BLOCK
    assert no_fall.reason == "RUN_LIST_YIELD_NO_FALLTHROUGH"
    modifier=ingest_actions(p.replace(b"actions.burst=lightning_bolt,",
                        b"actions.burst=lightning_bolt,target_if=min:remains,"),
                        expected_spec="enhancement")
    blocking=trace_priority(**(kw | {
        "model":modifier, "expected_apl_sha256":hashlib.sha256(
            p.replace(b"actions.burst=lightning_bolt,",
                      b"actions.burst=lightning_bolt,target_if=min:remains,")).hexdigest()}),
        action_readiness={"lightning_bolt":"READY"})
    assert blocking.reason == "UNSUPPORTED_ACTION_MODIFIERS"
    try:
        trace_priority(**(kw | {"expected_apl_sha256":"0"*64}),
                       action_readiness={"lightning_bolt":"READY"})
    except ValueError as e:
        assert str(e) == "APL_SOURCE_PIN_MISMATCH"
    else:
        raise AssertionError("UNPINNED_APL_ACCEPTED")
    print("SIMC_APL_ORDERED_PRIORITY_TRAVERSAL_SELF_TEST=PASS")


if __name__ == "__main__":
    selftest()
