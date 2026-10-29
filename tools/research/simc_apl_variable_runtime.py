#!/usr/bin/env python3
"""Reusable numeric SimC APL variable operations, research semantics.

All expression values come from an explicit evaluator with bounded state.
No automatic cooldown/resource/item semantics. Prior variable value is UNKNOWN
unless supplied or previously assigned within a verified scan.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Mapping, MutableMapping, Any


@dataclass(frozen=True)
class VariableUpdate:
    status: str  # APPLIED or BLOCKED
    reason: str
    name: str | None = None
    operator: str | None = None
    value: float | None = None


def apply_variable(
    params: Mapping[str, str], variables: MutableMapping[str, float],
    expression: Callable[[str], Any],
) -> VariableUpdate:
    """Evaluate one already-guard-approved variable APL line.

    No operation may quietly substitute initial/default for an unknown
    persistent variable. A reset/set is safe without prior value.
    """
    name = params.get("name", "")
    op = params.get("op", "set")
    if set(params) - {"name","if","op","value","value_else","condition","default"}:
        return VariableUpdate("BLOCKED", "UNSUPPORTED_VARIABLE_MODIFIERS")
    if not name or not name.replace("_","").isalnum():
        return VariableUpdate("BLOCKED", "INVALID_VARIABLE_NAME")
    def value_of(src: str, issue: str):
        result = expression(src)
        if result.value is None:
            return None, issue + result.status
        return result.value, None
    if "default" in params:
        default, err = value_of(params["default"], "VARIABLE_DEFAULT_")
        if err:
            return VariableUpdate("BLOCKED", err)
    else:
        default = 0.0
    current = variables.get(name)
    if op == "reset":
        final = default
    elif op == "setif":
        if not all(k in params for k in ("condition","value","value_else")):
            return VariableUpdate("BLOCKED","VARIABLE_SETIF_ARGUMENTS_MISSING")
        pred = expression(params["condition"])
        if pred.status not in ("TRUE","FALSE"):
            return VariableUpdate("BLOCKED","VARIABLE_SETIF_" + pred.status)
        chosen = params["value"] if pred.status == "TRUE" else params["value_else"]
        final,err = value_of(chosen,"VARIABLE_VALUE_")
        if err:
            return VariableUpdate("BLOCKED",err)
    else:
        if "value" not in params:
            return VariableUpdate("BLOCKED","VARIABLE_VALUE_REQUIRED")
        argument,err = value_of(params["value"],"VARIABLE_VALUE_")
        if err:
            return VariableUpdate("BLOCKED",err)
        if op == "set":
            final=argument
        elif op in ("floor","ceil"):
            final=float(math.floor(argument) if op=="floor" else math.ceil(argument))
        else:
            if op not in ("add","sub","mul","div","pow","mod","min","max"):
                return VariableUpdate("BLOCKED","VARIABLE_OPERATION_NOT_SUPPORTED")
            if current is None:
                return VariableUpdate("BLOCKED","VARIABLE_PREVIOUS_VALUE_UNKNOWN")
            try:
                if op=="add": final=current+argument
                elif op=="sub": final=current-argument
                elif op=="mul": final=current*argument
                elif op=="div": final=current/argument if argument else 0.0
                elif op=="pow": final=current**argument
                elif op=="mod": final=math.fmod(current,argument)
                elif op=="min": final=min(current,argument)
                else: final=max(current,argument)
            except (ZeroDivisionError,ValueError,OverflowError):
                return VariableUpdate("BLOCKED","VARIABLE_ARITHMETIC_UNDEFINED")
    if isinstance(final,complex):
        return VariableUpdate("BLOCKED","VARIABLE_ARITHMETIC_UNDEFINED")
    try:
        final=float(final)
    except (TypeError,ValueError,OverflowError):
        return VariableUpdate("BLOCKED","VARIABLE_ARITHMETIC_UNDEFINED")
    if not math.isfinite(final):
        return VariableUpdate("BLOCKED","VARIABLE_ARITHMETIC_UNDEFINED")
    variables[name]=final
    return VariableUpdate("APPLIED","VARIABLE_UPDATE",name,op,final)
