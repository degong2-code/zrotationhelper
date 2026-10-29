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

from dataclasses import dataclass, asdict
from typing import Any, Mapping
import argparse
import json
import math
from pathlib import Path

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
    control_feature_keys: Mapping[str, str] | None = None,
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
    # Explicitly observed variable values may carry forward from earlier
    # decision scans. Never reinitialize persistent variables to zero.
    variable_values: dict[str, float] = {
        k[len("variable."):]: v for k, v in values.items()
        if k.startswith("variable.") and len(k) > len("variable.")
    }

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
            if command == "auto_attack":
                # auto_attack is not a normal GCD skill. SimC triggers it
                # only if swings have not already started. Do not treat
                # it as a recommended cast or silently skip unknown status.
                # A controlled "active" observation must be STRICT PRE.
                if set(params) - {"if", "sync_weapons"}:
                    return outcome(BLOCK, None, group_name, line,
                                   "UNSUPPORTED_AUTO_ATTACK_MODIFIERS")
                key = (control_feature_keys or {}).get("auto_attack_active")
                observation = (strict_pre_state.features.get(key)
                               if key is not None else None)
                status = getattr(getattr(observation, "status", None),
                                 "value", None)
                ts = getattr(observation, "source_timestamp_ms", None)
                raw = getattr(observation, "value", None)
                if (status != "OBSERVED" or ts is None or
                        ts >= strict_pre_state.decision_timestamp_ms or
                        type(raw) not in (bool, int) or raw not in (0, 1)):
                    events.append({"list": group_name, "line": line,
                                   "command": command, "kind": "CONTROL_STATE",
                                   "status": "UNKNOWN"})
                    return outcome(BLOCK, None, group_name, line,
                                   "AUTO_ATTACK_STATE_UNKNOWN")
                if not bool(raw):
                    events.append({"list": group_name, "line": line,
                                   "command": command, "kind": "CONTROL_STATE",
                                   "status": "START_REQUIRED"})
                    return outcome(BLOCK, None, group_name, line,
                                   "AUTO_ATTACK_START_REQUIRED")
                events.append({"list": group_name, "line": line,
                               "command": command, "kind": "CONTROL_STATE",
                               "status": "ALREADY_ACTIVE_SKIP"})
                continue
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
                # SimC APL variable operators. Persistent values must be
                # reconstructed from strict-PRE observations, not silently 0.
                if set(params) - {"name", "if", "op", "value",
                                  "value_else", "condition", "default"}:
                    return outcome(BLOCK, None, group_name, line,
                                   "UNSUPPORTED_VARIABLE_MODIFIERS")
                variable = params.get("name", "")
                op = params.get("op", "set")
                if not variable or not variable.replace("_", "").isalnum():
                    return outcome(BLOCK, None, group_name, line,
                                   "INVALID_VARIABLE_NAME")
                if "default" in params:
                    fallback = condition(params["default"])
                    if fallback.value is None:
                        return outcome(BLOCK, None, group_name, line,
                                       "VARIABLE_DEFAULT_" + fallback.status)
                    default_value = fallback.value
                else:
                    default_value = 0.0  # SimC documented initial default
                current = variable_values.get(variable)
                value_expr = params.get("value")
                if op == "reset":
                    new_value = default_value
                elif op == "setif":
                    if "condition" not in params or value_expr is None or \
                            "value_else" not in params:
                        return outcome(BLOCK, None, group_name, line,
                                       "VARIABLE_SETIF_ARGUMENTS_MISSING")
                    predicate = condition(params["condition"])
                    if predicate.status not in ("TRUE", "FALSE"):
                        return outcome(BLOCK, None, group_name, line,
                                       "VARIABLE_SETIF_" + predicate.status)
                    chosen = value_expr if predicate.status == "TRUE" \
                        else params["value_else"]
                    computed = condition(chosen)
                    if computed.value is None:
                        return outcome(BLOCK, None, group_name, line,
                                       "VARIABLE_VALUE_" + computed.status)
                    new_value = computed.value
                else:
                    if value_expr is None:
                        return outcome(BLOCK, None, group_name, line,
                                       "VARIABLE_VALUE_REQUIRED")
                    computed = condition(value_expr)
                    if computed.value is None:
                        return outcome(BLOCK, None, group_name, line,
                                       "VARIABLE_VALUE_" + computed.status)
                    argument = computed.value
                    if op == "set":
                        new_value = argument
                    elif op in ("floor", "ceil"):
                        new_value = float(
                            math.floor(argument) if op == "floor"
                            else math.ceil(argument))
                    else:
                        if current is None:
                            return outcome(BLOCK, None, group_name, line,
                                           "VARIABLE_PREVIOUS_VALUE_UNKNOWN")
                        try:
                            if op == "add":
                                new_value = current + argument
                            elif op == "sub":
                                new_value = current - argument
                            elif op == "mul":
                                new_value = current * argument
                            elif op == "div":
                                new_value = current / argument if argument else 0.0
                            elif op == "pow":
                                new_value = current ** argument
                            elif op == "mod":
                                new_value = math.fmod(current, argument)
                            elif op == "min":
                                new_value = min(current, argument)
                            elif op == "max":
                                new_value = max(current, argument)
                            else:
                                return outcome(BLOCK, None, group_name, line,
                                               "VARIABLE_OPERATION_NOT_SUPPORTED")
                        except (ZeroDivisionError, ValueError, OverflowError):
                            return outcome(BLOCK, None, group_name, line,
                                           "VARIABLE_ARITHMETIC_UNDEFINED")
                if isinstance(new_value, complex) or not math.isfinite(new_value):
                    return outcome(BLOCK, None, group_name, line,
                                   "VARIABLE_ARITHMETIC_UNDEFINED")
                variable_values[variable] = float(new_value)
                events.append({"list": group_name, "line": line,
                               "command": command, "kind": "VARIABLE_UPDATE",
                               "operator": op, "variable": variable,
                               "value": variable_values[variable]})
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
    # Persistent variables cannot be synthesized from a new scan's defaults.
    v = (
        b"spec=enhancement\n"
        b"actions=variable,name=counter,op=add,value=2\n"
        b"actions+=/variable,name=gate,op=setif,condition=variable.counter>=5,"
        b"value=1,value_else=0\n"
        b"actions+=/stormstrike,if=variable.gate=1\n"
        b"actions+=/lava_lash\n"
    )
    vm = ingest_actions(v, expected_spec="enhancement")
    vk = dict(kw, model=vm,
              expected_apl_sha256=hashlib.sha256(v).hexdigest())
    unknown_previous = trace_priority(
        **vk, action_readiness={"stormstrike": "READY", "lava_lash": "READY"})
    assert unknown_previous.reason == "VARIABLE_PREVIOUS_VALUE_UNKNOWN"
    carried = StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=(StateTransition(900, "previous_counter", 3),))
    carried_kw = dict(vk, strict_pre_state=carried,
                      operand_to_feature={"variable.counter":"previous_counter"})
    found = trace_priority(
        **carried_kw, action_readiness={"stormstrike": "READY"})
    assert found.candidate_action_token == "stormstrike", found
    assert any(e.get("operator") == "setif" and e.get("value") == 1.0
               for e in found.trace)
    # No source timestamp equality/future leakage.
    future = StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=(StateTransition(1000, "previous_counter", 3),
                     StateTransition(1001, "previous_counter", 100)))
    missing = trace_priority(
        **dict(carried_kw, strict_pre_state=future),
        action_readiness={"stormstrike": "READY"})
    assert missing.reason == "VARIABLE_PREVIOUS_VALUE_UNKNOWN"
    # 'reset' uses the SimC documented default, even without prior value.
    reset = b"spec=enhancement\n" \
            b"actions=variable,name=gate,op=reset,default=7\n" \
            b"actions+=/stormstrike,if=variable.gate=7\n"
    reset_model = ingest_actions(reset, expected_spec="enhancement")
    reset_result = trace_priority(
        **dict(kw, model=reset_model,
               expected_apl_sha256=hashlib.sha256(reset).hexdigest()),
        action_readiness={"stormstrike":"READY"})
    assert reset_result.candidate_action_token == "stormstrike"
    # Safe fail-closed on unsupported variable options.
    delayed = reset.replace(b"default=7", b"default=7,delay=0.5")
    delay_result = trace_priority(
        **dict(kw, model=ingest_actions(delayed, expected_spec="enhancement"),
               expected_apl_sha256=hashlib.sha256(delayed).hexdigest()),
        action_readiness={"stormstrike":"READY"})
    assert delay_result.reason == "UNSUPPORTED_VARIABLE_MODIFIERS"
    # All supported stateful operations use the *observed* previous value.
    op_expectations = {
        "add": 8, "sub": 4, "mul": 12, "div": 3, "pow": 36,
        "mod": 0, "min": 2, "max": 6,
    }
    observed_six = StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=(StateTransition(901, "previous_counter", 6),))
    for op, expected_value in op_expectations.items():
        fixture = (
            "spec=enhancement\n"
            f"actions=variable,name=counter,op={op},value=2\n"
            f"actions+=/stormstrike,if=variable.counter={expected_value}\n"
        ).encode()
        result = trace_priority(
            **dict(kw, model=ingest_actions(fixture, expected_spec="enhancement"),
                   strict_pre_state=observed_six,
                   operand_to_feature={"variable.counter":"previous_counter"},
                   expected_apl_sha256=hashlib.sha256(fixture).hexdigest()),
            action_readiness={"stormstrike":"READY"})
        assert result.status == CANDIDATE, (op, result.reason)
    # SimC's variable div-by-zero convention is 0 (different from guards).
    divide_zero = (
        b"spec=enhancement\n"
        b"actions=variable,name=counter,op=div,value=0\n"
        b"actions+=/stormstrike,if=variable.counter=0\n"
    )
    divide_result = trace_priority(
        **dict(kw, model=ingest_actions(divide_zero, expected_spec="enhancement"),
               strict_pre_state=observed_six,
               operand_to_feature={"variable.counter":"previous_counter"},
               expected_apl_sha256=hashlib.sha256(divide_zero).hexdigest()),
        action_readiness={"stormstrike":"READY"})
    assert divide_result.status == CANDIDATE
    # A declared default is not substituted for an unobserved *persistent*
    # previous value in a later scan.
    no_prior = (
        b"spec=enhancement\n"
        b"actions=variable,name=counter,op=add,default=3,value=2\n"
        b"actions+=/stormstrike\n"
    )
    unobserved_prior = trace_priority(
        **dict(kw, model=ingest_actions(no_prior, expected_spec="enhancement"),
               expected_apl_sha256=hashlib.sha256(no_prior).hexdigest()),
        action_readiness={"stormstrike":"READY"})
    assert unobserved_prior.reason == "VARIABLE_PREVIOUS_VALUE_UNKNOWN"
    # setif false branch and noninteger value rounding.
    for op, value, expected_value in (
        ("floor", 2.9, 2), ("ceil", 2.1, 3)):
        fixture = (
            "spec=enhancement\n"
            f"actions=variable,name=gate,op={op},value={value}\n"
            f"actions+=/stormstrike,if=variable.gate={expected_value}\n"
        ).encode()
        result = trace_priority(
            **dict(kw, model=ingest_actions(fixture, expected_spec="enhancement"),
                   expected_apl_sha256=hashlib.sha256(fixture).hexdigest()),
            action_readiness={"stormstrike":"READY"})
        assert result.status == CANDIDATE, op
    # The auto-attack control action is not a GCD recommendation. An active
    # PRE state may skip it; absent/late/inactive must not be assumed active.
    control_profile = (
        b"spec=enhancement\n"
        b"actions=auto_attack\n"
        b"actions+=/stormstrike,if=active_enemies>=2\n"
    )
    control_model = ingest_actions(control_profile, expected_spec="enhancement")
    ck = dict(kw, model=control_model,
              expected_apl_sha256=hashlib.sha256(control_profile).hexdigest(),
              control_feature_keys={"auto_attack_active":"auto_active"},
              action_readiness={"stormstrike":"READY"})
    no_auto_obs = trace_priority(**ck)
    assert no_auto_obs.reason == "AUTO_ATTACK_STATE_UNKNOWN"
    active = StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=(StateTransition(900,"auto_active",1),
                     StateTransition(910,"targets",2),
                     StateTransition(1000,"auto_active",0),
                     StateTransition(1001,"targets",0)))
    yes = trace_priority(**dict(ck,strict_pre_state=active))
    assert yes.status == CANDIDATE and yes.candidate_action_token == "stormstrike", yes
    assert any(e.get("status") == "ALREADY_ACTIVE_SKIP" for e in yes.trace)
    inactive = StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=(StateTransition(900,"auto_active",0),
                     StateTransition(910,"targets",2)))
    needs_start = trace_priority(**dict(ck,strict_pre_state=inactive))
    assert needs_start.reason == "AUTO_ATTACK_START_REQUIRED"
    future_only = StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=(StateTransition(1000,"auto_active",1),
                     StateTransition(1001,"auto_active",1),
                     StateTransition(900,"targets",2)))
    assert trace_priority(**dict(ck,strict_pre_state=future_only)).reason == \
        "AUTO_ATTACK_STATE_UNKNOWN"
    # Precombat variable values are not silently materialized. They must
    # be observed as prior persistent state, independent from APL source.
    initialized_profile = (
        b"spec=enhancement\n"
        b"actions.precombat=variable,name=pre_gate,op=set,value=2\n"
        b"actions=stormstrike,if=variable.pre_gate=2\n"
    )
    initialized_model = ingest_actions(initialized_profile,expected_spec="enhancement")
    pv = dict(kw,model=initialized_model,
              expected_apl_sha256=hashlib.sha256(initialized_profile).hexdigest(),
              operand_to_feature={"variable.pre_gate":"pre_gate"})
    no_precombat = trace_priority(**pv,action_readiness={"stormstrike":"READY"})
    assert no_precombat.reason == "GUARD_UNKNOWN"
    known_precombat = StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=(StateTransition(800,"pre_gate",2),))
    with_precombat = trace_priority(
        **dict(pv,strict_pre_state=known_precombat),
        action_readiness={"stormstrike":"READY"})
    assert with_precombat.candidate_action_token=="stormstrike"
    print("SIMC_APL_AUTO_ATTACK_AND_PRECOMBAT_BOUNDARY_SELF_TEST=PASS")
    print("SIMC_APL_VARIABLE_OPERATORS_AND_PRE_SELF_TEST=PASS")
    print("SIMC_APL_ORDERED_PRIORITY_TRAVERSAL_SELF_TEST=PASS")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Research-only SimC APL priority trace for a PRE snapshot")
    parser.add_argument("--model", type=Path,
                        help="JSON hypothesis emitted by simc_apl_source_engine.py")
    parser.add_argument("--snapshot", type=Path,
                        help="JSON with PRE transitions, operand map and readiness keys")
    parser.add_argument("--output", type=Path, help="Write trace JSON")
    parser.add_argument("--self-test", action="store_true")
    options = parser.parse_args()
    if options.self_test or (options.model is None and options.snapshot is None):
        selftest()
        return 0
    if options.model is None or options.snapshot is None:
        parser.error("--model and --snapshot must both be supplied")
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] /
                           "02_SOURCE" / "runtime"))
    from raid_dps.core.behavioral_evaluator import (
        StrictPreStateProvider, StateTransition, ObservationStatus)
    model = json.loads(options.model.read_text(encoding="utf-8"))
    data = json.loads(options.snapshot.read_text(encoding="utf-8"))
    ts = data["decision_timestamp_ms"]
    transitions = tuple(StateTransition(
        int(r["timestamp_ms"]), str(r["key"]), r["value"])
        for r in data["transitions"])
    state = StrictPreStateProvider().build(
        action_timestamp_ms=ts, transitions=transitions,
        required_keys=data.get("required_keys", ()),
        unobservable_keys=data.get("unobservable_keys", ()))
    readiness = {}
    for action, key in data["readiness_feature_keys"].items():
        obs = state.features.get(key)
        if (obs is not None and obs.status is ObservationStatus.OBSERVED
                and obs.source_timestamp_ms is not None
                and obs.value in ("READY", "NOT_READY", "UNKNOWN", "UNOBSERVABLE")):
            readiness[action] = obs.value
    # A completeness-checked readiness model can be supplied in the same
    # snapshot. It stays a SOURCE-DECLARED, UNVERIFIED hypothesis; it does
    # not replace an actual trusted strict-PRE readiness observation.
    if "readiness_contract" in data:
        from simc_apl_readiness_provider import derive_readiness
        contract_result=derive_readiness(
            data["readiness_contract"],state,
            spec_slug=data["spec_slug"],
            build_key=data["build_key"],
            apl_sha256=model["apl_sha256"],
        )
        for action, verdict in contract_result.items():
            prior=readiness.get(action)
            if prior is not None and prior not in ("UNKNOWN","UNOBSERVABLE") and \
                    verdict.status not in ("UNKNOWN",prior):
                raise ValueError("CONFLICTING_READINESS_EVIDENCE")
            if prior is None or prior in ("UNKNOWN","UNOBSERVABLE"):
                readiness[action]=verdict.status
    result = trace_priority(
        model, strict_pre_state=state,
        spec_slug=data["spec_slug"],
        operand_to_feature=data["operand_to_feature"],
        action_readiness=readiness,
        control_feature_keys=data.get("control_feature_keys", {}),
        expected_apl_sha256=model["apl_sha256"],
        expected_profile_sha256=model.get("profile_sha256"),
    )
    payload = {
        **asdict(result),
        "validation": "SIMC_APL_HYPOTHESIS_RESEARCH_ONLY",
        "readiness_provenance": ("SOURCE_DECLARED_REQUIREMENT_MODEL_UNVERIFIED"
                                if "readiness_contract" in data
                                else "EXPLICIT_STRICT_PRE_FEATURES"),
        "source_priority_is_optimal": False,
        "current_game_authority": "UNVERIFIED",
    }
    output = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
