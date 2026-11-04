#!/usr/bin/env python3
"""Tri-state source-guard evidence for actual SimC action_ready() attempts.

Uses direct *source predicate facts* captured before the original Native
action_ready() call, plus independent evidence that the base action_ready()
and base ready() methods both executed. Source-ordered negative base guards
can conclusively explain a NOT_READY outcome, but surviving all captured
base guards CANNOT prove READY: virtual subclass checks, casting/GCD,
target selection, line/sync cooldown and other checks may still fail.

This is a bounded base guard witness, NOT an independent implementation
of cooldown_t::is_ready(), usable_moving(), cost_affordable() or full Native
ready(). Native readiness is read only after the witness is derived to
detect conflicts. Missing/double method-entry markers mean UNKNOWN.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile
from simc_native_if_pre_operand_replay_v1 import (
    PINNED_FURY_BLOB, verify_folder, exact_key, get_native_attempt,
)
from simc_native_ready_guard_witness_instrument_v1 import (
    MARK, BASE_READY_MARK, BASE_ACTION_MARK,
)

SCHEMA = "ZrotNativeSourceBaseReadyGuardTriStateWitnessV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
INTS = {-1, 0, 1}


class ReadinessWitnessError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_guard(line):
    i = line.find(MARK)
    if i < 0:
        return None
    parts = line[i:].strip().split("|")
    if (len(parts) != 10 or not parts[1].isdigit()
        or not parts[3].isdigit()):
        raise ReadinessWitnessError("READINESS_SOURCE_FACT_FORMAT_CHANGED")
    try:
        v = [int(x) for x in parts[5:]]
    except ValueError:
        raise ReadinessWitnessError("READY_PRE_BOOLEAN_FACT_INVALID")
    if any(x not in INTS for x in v) or v[2] not in (0, 1):
        raise ReadinessWitnessError("READY_SOURCE_FACT_NOT_TRIVALUED")
    cd, icd, moving, usable, cost = v
    if ((moving == 0 and usable != -1) or
        (moving == 1 and (cd != 1 or icd != 1) and usable != -1) or
        ((cd != 1 or icd != 1 or (moving == 1 and usable != 1))
         and cost != -1)):
        raise ReadinessWitnessError("NATIVE_SOURCE_GUARD_SHORT_CIRCUIT_BROKEN")
    return {
        "time_ms": int(parts[1]), "list": parts[2],
        "ordinal": int(parts[3]), "native_name": parts[4],
        "cooldown_queueable": cd, "internal_cooldown_up": icd,
        "player_is_moving": moving, "action_usable_moving": usable,
        "source_cost_affordable": cost,
    }


def read_method_entry(line, token):
    i = line.find(token)
    if i < 0:
        return None
    fields = line[i:].strip().split("|")
    if len(fields) != 3 or not fields[1].isdigit() or not fields[2]:
        raise ReadinessWitnessError("BASE_METHOD_ENTRY_SOURCE_MARKER_INVALID")
    return int(fields[1]), fields[2]


def source_guard_verdict(pre: dict, action_entry: int,
                         ready_entry: int) -> tuple[str, str | None]:
    if action_entry != 1 or ready_entry != 1:
        return "UNKNOWN_BASE_METHOD_NOT_PROVEN_ON_THIS_ATTEMPT", None
    cd = pre["cooldown_queueable"]
    icd = pre["internal_cooldown_up"]
    moving = pre["player_is_moving"]
    usable = pre["action_usable_moving"]
    affordable = pre["source_cost_affordable"]
    if cd == 0:
        return "PROVEN_BASE_GUARD_NOT_READY", "cooldown_queueable"
    if cd != 1:
        return "UNKNOWN_NECESSARY_GUARD_MISSING", "cooldown_queueable"
    if icd == 0:
        return "PROVEN_BASE_GUARD_NOT_READY", "internal_cooldown_up"
    if icd != 1:
        return "UNKNOWN_NECESSARY_GUARD_MISSING", "internal_cooldown_up"
    if moving:
        if usable == 0:
            return "PROVEN_BASE_GUARD_NOT_READY", "movement_usable"
        if usable != 1:
            return "UNKNOWN_NECESSARY_GUARD_MISSING", "movement_usable"
    if affordable == 0:
        return "PROVEN_BASE_GUARD_NOT_READY", "cost_affordable"
    if affordable != 1:
        return "UNKNOWN_NECESSARY_GUARD_MISSING", "cost_affordable"
    return "UNKNOWN_BASE_GUARDS_PASS_BUT_MORE_REQUIRED", None


def replay_log(trace: str, ir: dict) -> dict:
    pending = []
    counts = Counter()
    failed_guards = Counter()
    selected_examples = []
    last_attempt = None
    for line in trace.splitlines():
        pre = read_guard(line)
        if pre is not None:
            if pre["list"] not in ir["action_lists"]:
                raise ReadinessWitnessError("UNKNOWN_SOURCE_LIST_ON_GUARD")
            rows = ir["action_lists"][pre["list"]]
            index = pre["ordinal"] - 1
            if index < 0 or index >= len(rows):
                raise ReadinessWitnessError("GUARD_SOURCE_POINTER_OUT_OF_RANGE")
            if pre["native_name"] != rows[index]["action"] and not (
                pre["native_name"] and rows[index]["action"]):
                raise ReadinessWitnessError("GUARD_SOURCE_ACTION_MISSING")
            pending.append({"pre": pre, "action_entries":0, "ready_entries":0,
                            "observed_method_names":Counter()})
            counts["PRE_source_guard_records"] += 1
            continue
        for marker, slot in ((BASE_ACTION_MARK, "action_entries"),
                             (BASE_READY_MARK, "ready_entries")):
            entry = read_method_entry(line, marker)
            if entry is not None:
                if pending and entry[0] == pending[-1]["pre"]["time_ms"]:
                    if entry[1] == pending[-1]["pre"]["native_name"]:
                        pending[-1][slot] += 1
                    else:
                        pending[-1]["observed_method_names"][entry[1]] += 1
                break
        else:
            attempt = get_native_attempt(line)
            if attempt is None:
                continue
            counts["native_ATTEMPT_records"] += 1
            if not pending:
                raise ReadinessWitnessError("NATIVE_ATTEMPT_WITHOUT_PRE_GUARD_FACT")
            group = pending.pop()
            if exact_key(group["pre"]) != exact_key(attempt):
                raise ReadinessWitnessError("NATIVE_PRE_GUARD_SOURCE_IDENTITY_MISMATCH")
            state, guard = source_guard_verdict(
                group["pre"], group["action_entries"], group["ready_entries"])
            counts[state] += 1
            if group["action_entries"] == 1:
                counts["base_action_ready_entered_once"] += 1
            if group["ready_entries"] == 1:
                counts["base_ready_entered_once"] += 1
            if group["action_entries"] > 1 or group["ready_entries"] > 1:
                counts["base_method_entry_ambiguous"] += 1
            if state == "PROVEN_BASE_GUARD_NOT_READY":
                failed_guards[guard] += 1
                if attempt["ready"] != 0:
                    raise ReadinessWitnessError(
                        "SOURCE_GUARD_PREDICTED_FALSE_BUT_NATIVE_READY_TRUE:")
                counts["source_negative_vs_native_false_MATCH"] += 1
                if len(selected_examples) < 14:
                    selected_examples.append({
                        "at_ms": attempt["time_ms"],
                        "source_list": attempt["list"],
                        "source_index": attempt["ordinal"] - 1,
                        "native_action": attempt["native_name"],
                        "base_guard_failed": guard,
                        "source_inputs": group["pre"],
                        "native_ready_verification_only": attempt["ready"],
                    })
            last_attempt = attempt
    if pending:
        raise ReadinessWitnessError("UNPAIRED_READY_GUARD_FACTS_AT_EOF")
    if (counts["PRE_source_guard_records"] != counts["native_ATTEMPT_records"] or
        counts["source_negative_vs_native_false_MATCH"] +
        sum(n for state,n in counts.items()
            if state.startswith("UNKNOWN_")) != counts["native_ATTEMPT_records"]):
        raise ReadinessWitnessError("SOURCE_GUARD_COHORT_ACCOUNTING_FAILED")
    if not last_attempt:
        raise ReadinessWitnessError("NO_NATIVE_READY_ATTEMPTS")
    return {
        "counts": dict(sorted(counts.items())),
        "negative_witness_guard_distribution": dict(sorted(failed_guards.items())),
        "negative_examples_not_priority_claims": selected_examples,
        "Native_ready_result_used_only_for_post_derived_comparison": True,
        "base_success_never_assumed_full_ready": True,
        "unentered_or_overridden_methods_are_UNKNOWN": True,
    }


def run(profile: Path, st: Path, two: Path, move_st: Path, move_two: Path) -> dict:
    ir = parse_profile(profile.read_bytes(), require_source=True,
                       expected_git_blob=PINNED_FURY_BLOB)
    out = {}
    combined = Counter()
    binaries = {}
    for label, directory, targets, expected in (
        ("stationary_st", st, 1, 1542),
        ("stationary_two_target", two, 2, 1030),
        ("moving_st", move_st, 1, None),
        ("moving_two_target", move_two, 2, None),
    ):
        directory = directory.resolve(strict=True)
        source = verify_folder(directory, targets, ir)
        raw = (directory/"simc_native_log.txt").read_bytes()
        one = replay_log(raw.decode("utf-8"), ir)
        n = one["counts"]["native_ATTEMPT_records"]
        if n != source["counts"]["all_native_action_ready_attempts"]:
            raise ReadinessWitnessError("READY_SOURCE_ATTEMPT_COUNT_CONFLICT")
        if expected is not None and n != expected:
            raise ReadinessWitnessError("PINNED_STATIONARY_READY_COHORT_DRIFT")
        if n < 1:
            raise ReadinessWitnessError("NO_ACTUAL_MOVING_READY_ATTEMPTS")
        one["actual_native_ready_attempts"] = n
        one["native_source_log_sha256"] = sha(raw)
        one["source_effective_APL_sha256"] = source["native_apl_sha256"]
        one["native_binary_sha256"] = source["native_binary_sha256"]
        out[label] = one
        binaries[label] = source["native_binary_sha256"]
        combined["total_attempts"] += n
        combined["source_negative_witnesses"] += one["counts"].get(
            "PROVEN_BASE_GUARD_NOT_READY", 0)
        combined["unknown_remaining"] += (
            n - one["counts"].get("PROVEN_BASE_GUARD_NOT_READY", 0))
    if len(set(binaries.values())) != 1:
        raise ReadinessWitnessError("DIFFERENT_NATIVE_BINARY_BETWEEN_FOUR_CASES")
    if combined["total_attempts"] < 2572:
        raise ReadinessWitnessError("NATIVE_READY_ATTEMPT_TOTAL_REGRESSION")
    return {
        "schema": SCHEMA, "policy_id": POLICY,
        "status": "BOUND_SOURCE_GUARD_NEGATIVE_WITNESS_NO_FULL_READY_PROOF",
        "four_cases": out,
        "source_guard_accounting": dict(combined),
        "pinned_official_Fury_profile_blob": PINNED_FURY_BLOB,
        "source_base_ready_necessary_guard_order": [
            "cooldown_queueable", "internal_cooldown_up",
            "movement_usable_if_moving", "cost_affordable"
        ],
        "native_guard_method_return_values_reused_as_source_operands": True,
        "independent_cooldown_mechanics": False,
        "independent_cost_and_movement_mechanics": False,
        "native_ready_bit_as_witness_input": False,
        "independent_full_ready_proven": False,
        "independent_positive_ready_proven": False,
        "independent_source_order_choice_proven": False,
        "actual_moving_cases_exercised": True,
        "WCL_API_calls": 0,
        "MAIN_promoted": False,
    }


def selftest() -> dict:
    synthetic = parse_profile(
        b"actions=foo,if=rage>1\n", require_source=False)
    examples = (
        ({"cooldown_queueable":0,"internal_cooldown_up":1,
          "player_is_moving":0,"action_usable_moving":-1,
          "source_cost_affordable":-1},
         "PROVEN_BASE_GUARD_NOT_READY", "cooldown_queueable"),
        ({"cooldown_queueable":1,"internal_cooldown_up":0,
          "player_is_moving":0,"action_usable_moving":-1,
          "source_cost_affordable":-1},
         "PROVEN_BASE_GUARD_NOT_READY", "internal_cooldown_up"),
        ({"cooldown_queueable":1,"internal_cooldown_up":1,
          "player_is_moving":1,"action_usable_moving":0,
          "source_cost_affordable":-1},
         "PROVEN_BASE_GUARD_NOT_READY", "movement_usable"),
        ({"cooldown_queueable":1,"internal_cooldown_up":1,
          "player_is_moving":0,"action_usable_moving":-1,
          "source_cost_affordable":0},
         "PROVEN_BASE_GUARD_NOT_READY", "cost_affordable"),
        ({"cooldown_queueable":1,"internal_cooldown_up":1,
          "player_is_moving":0,"action_usable_moving":-1,
          "source_cost_affordable":1},
         "UNKNOWN_BASE_GUARDS_PASS_BUT_MORE_REQUIRED", None),
    )
    for facts,state,reason in examples:
        assert source_guard_verdict(facts,1,1) == (state,reason)
        assert source_guard_verdict(facts,0,1)[0].startswith("UNKNOWN_")
    pre = read_guard(MARK+"10|default|1|foo|0|1|0|-1|-1")
    assert pre["cooldown_queueable"] == 0
    assert read_guard("random") is None
    assert read_method_entry(BASE_READY_MARK+"10|foo", BASE_READY_MARK) == (10,"foo")
    trace = "\n".join((
        MARK+"10|default|1|foo|0|1|0|-1|-1",
        BASE_ACTION_MARK+"10|foo",
        BASE_READY_MARK+"10|foo",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|foo|0",
    ))
    x = replay_log(trace, synthetic)
    assert x["counts"]["source_negative_vs_native_false_MATCH"] == 1
    for bad in (
        trace.replace("|foo|0\n","|foo|1\n"),
        trace.replace("|foo|0|1|0|-1|-1","|foo|0|1|0|0|-1"),
        trace.replace("|default|1|foo|0|1","|default|2|foo|0|1"),
    ):
        try:
            replay_log(bad, synthetic)
        except ReadinessWitnessError:
            pass
        else:
            raise AssertionError("INVALID_OR_TRUE_WHEN_FALSE_READY_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC", "checks":17,
            "real_Native_executed":False,"full_ready_proven":False,
            "WCL_API_calls":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--native-st-dir",type=Path)
    p.add_argument("--native-2t-dir",type=Path)
    p.add_argument("--native-moving-st-dir",type=Path)
    p.add_argument("--native-moving-2t-dir",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    inputs=(a.official_profile,a.native_st_dir,a.native_2t_dir,
            a.native_moving_st_dir,a.native_moving_2t_dir)
    if not any(inputs):
        result=selftest()
    elif all(inputs):
        result=run(*inputs)
    else:
        p.error("all five pinned inputs required for Native source-guard witness")
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
        print("SOURCE_BASE_GUARD_WITNESS_SHA256="+sha(raw))
    else:
        print(raw.decode(),end="")


if __name__=="__main__":
    main()
