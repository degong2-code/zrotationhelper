#!/usr/bin/env python3
"""Incremental source-bounded Native IF GCD/cooldown replay.

Compares action-scoped gcd duration (NOT player GCD remains) and existing
cooldown_t::up() (NOT cooldown_t::is_ready() queueability) with the original
Native IF result only after independent typed AST computation. Reuses the
previous 273/477 Rage/enemies/time/talent/buff proof without rereading
readiness as ground-truth. Unknown state and absent named cooldown remain
UNKNOWN. Real Native ST/2T sequences are compared by the workflow.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile
from simc_native_if_pre_operand_replay_v1 import (
    verify_folder, parse_fact, exact_key, get_native_attempt, PINNED_FURY_BLOB,
)
from simc_native_if_source_clock_successor_v1 import pre_facts, verify_clock_source
from simc_native_if_talent_pre_instrument_v1 import talent_inventory
from simc_native_if_talent_pre_replay_v1 import (
    group_actual_pre_talents, independent_if,
)
from simc_native_if_buff_pre_instrument_v1 import buff_inventory
from simc_native_if_buff_pre_replay_v1 import (
    group_actual_pre_buffs, compare_with_previous,
)
from simc_native_if_action_gcd_cd_pre_instrument_v1 import (
    MARK, source_inventory, unsupported_inventory,
)

SCHEMA = "ZrotNativeActionGcdCooldownPreAstReplayV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"


class ScopedReplayError(ValueError):
    pass


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse_action_expr(line, allowed):
    pos = line.find(MARK)
    if pos < 0:
        return None
    parts = line[pos:].strip().split("|")
    if (len(parts) != 7 or not parts[1].isdigit()
        or not parts[3].isdigit() or parts[5] not in allowed):
        raise ScopedReplayError("SOURCE_ACTION_EXPR_PRE_MARKER_NOT_PINNED")
    try:
        value = float(parts[6])
    except (ValueError, OverflowError):
        raise ScopedReplayError("PRE_ACTION_EXPR_NONNUMERIC")
    if not math.isfinite(value):
        raise ScopedReplayError("PRE_ACTION_EXPR_NOT_FINITE")
    symbol = parts[5]
    missing = False
    if symbol == "gcd":
        if value < 0 or value > 60:
            raise ScopedReplayError("NATIVE_GCD_DURATION_INVALID")
    else:
        if value == -1:
            missing = True
        elif value not in (0, 1):
            raise ScopedReplayError("NATIVE_COOLDOWN_UP_EXPECTED_BOOLEAN")
    return {
        "time_ms": int(parts[1]), "list": parts[2],
        "ordinal": int(parts[3]), "native_name": parts[4],
        "symbol": symbol, "value": (None if missing else value),
        "missing_cooldown_identity": missing,
    }


def group_action_expr_pre(native_log, symbols):
    expected = set(symbols)
    pending = None
    result = []
    for line in native_log.splitlines():
        native_fact = parse_fact(line)
        if native_fact is not None:
            if pending is not None:
                raise ScopedReplayError("OVERLAPPING_PRE_IF_ACTION_EXPR_RECORDS")
            pending = {
                "key": exact_key(native_fact), "captured": {},
                "missing_cd": [],
            }
            continue
        event = parse_action_expr(line, expected)
        if event is not None:
            if pending is None or exact_key(event) != pending["key"]:
                raise ScopedReplayError("UNMATCHED_ACTION_EXPR_SOURCE_POINTER")
            if event["symbol"] in pending["captured"]:
                raise ScopedReplayError("DUPLICATED_ACTION_EXPR_AT_NATIVE_IF")
            pending["captured"][event["symbol"]] = event["value"]
            if event["missing_cooldown_identity"]:
                pending["missing_cd"].append(event["symbol"])
            continue
        attempt = get_native_attempt(line)
        if attempt is not None and pending is not None:
            if exact_key(attempt) != pending["key"]:
                raise ScopedReplayError("SOURCE_ACTION_EXPR_READY_ATTEMPT_MISMATCH")
            if set(pending["captured"]) != expected:
                raise ScopedReplayError("MISSING_SOURCE_ACTION_EXPR_PRE_FACT")
            result.append(pending)
            pending = None
    if pending is not None:
        raise ScopedReplayError("UNMATCHED_LAST_NATIVE_PRE_ACTION_EXPR")
    return result


def compare_with_buff_baseline(trace, official, old, talents, buffs, scoped, scenario):
    previous = compare_with_previous(
        trace, official, old, talents, buffs, scenario)
    talent_facts = group_actual_pre_talents(trace, talents)
    buff_facts = group_actual_pre_buffs(trace, buffs)
    scoped_facts = group_action_expr_pre(trace, scoped)
    ledger = old["all_native_if_pre_fact_ledger"]
    if not (len(ledger) == len(talent_facts) ==
            len(buff_facts) == len(scoped_facts)):
        raise ScopedReplayError("SOURCE_FACT_COHORT_LENGTH_DRIFT")
    counts = Counter()
    residuals = Counter()
    sample = []
    for i, (row, talent, buff, action) in enumerate(
        zip(ledger, talent_facts, buff_facts, scoped_facts)
    ):
        expected_key = (
            row["at_ms"], row["source_list"],
            row["source_index"] + 1, row["native_name"],
        )
        if any(x["key"] != expected_key for x in (talent, buff, action)):
            raise ScopedReplayError("NATIVE_ACTION_ROW_SOURCE_BOUNDARY_DIFFERS")
        source_row = official["action_lists"][row["source_list"]][row["source_index"]]
        expr = source_row["expression_fields"].get("if")
        if (not expr or row["source_line_sha256"] != source_row["source_sha256"]
            or row["source_if"] != expr["source"]
            or row["source_if_symbols"] != expr["symbols"]):
            raise ScopedReplayError("SOURCE_IF_APL_ROW_PROVENANCE_CHANGED")
        base = {
            **pre_facts(row),
            **talent["values"],
            **buff["values"],
        }
        old_result = independent_if(expr, base)
        # Absent named cooldown is NOT 0 or ready. Do not materialize None.
        new_facts = {
            **base,
            **{symbol: value for symbol, value in action["captured"].items()
               if value is not None},
        }
        new_result = independent_if(expr, new_facts)
        if old_result is not None:
            counts["prior_buff_known"] += 1
            if new_result != old_result:
                raise ScopedReplayError("273_PREVIOUS_PROOFS_REGRESSED")
        if action["missing_cd"]:
            counts["pre_named_cooldown_missing_at_if"] += 1
        if new_result is None:
            counts["unknown"] += 1
            residuals.update(set(expr["symbols"]) - set(new_facts))
            continue
        # Native truth remains ONLY a comparator, never a source value.
        if new_result != row["native_if_result_verification_only"]:
            raise ScopedReplayError(
                "INDEPENDENT_ACTION_EXPR_IF_NATIVE_CONFLICT:" +
                scenario + ":" + row["source_list"] +
                ":" + str(row["source_index"]) + ":" + str(i))
        counts["matched"] += 1
        if old_result is None:
            counts["newly_decidable_action_expr"] += 1
            if len(sample) < 12:
                sample.append({
                    "scenario": scenario,
                    "source_list": row["source_list"],
                    "source_index": row["source_index"],
                    "at_ms": row["at_ms"],
                    "source_if": expr["source"],
                    "source_line_sha256": row["source_line_sha256"],
                    "scoped_source_PRE": action["captured"],
                    "independent_result": new_result,
                    "native_IF_postcompute_comparator_only":
                        row["native_if_result_verification_only"],
                })
    prior = previous["counts"]["matched"]
    if (counts["prior_buff_known"] != prior or
        counts["matched"] + counts["unknown"] != len(ledger) or
        counts["matched"] - counts["prior_buff_known"] !=
            counts["newly_decidable_action_expr"]):
        raise ScopedReplayError("BASELINE_OR_REAL_COHORT_ACCOUNTING_FAILED")
    return {
        "native_IF_count": len(ledger),
        "counts": dict(sorted(counts.items())),
        "remaining_unknown_symbol_incidences": dict(sorted(residuals.items())),
        "newly_decidable_examples": sample,
        "previous_buff_source_counts": previous["counts"],
    }


def run(profile, clock, st, two):
    verify_clock_source(clock.read_bytes())
    ir = parse_profile(
        profile.read_bytes(), require_source=True,
        expected_git_blob=PINNED_FURY_BLOB,
    )
    talent, buff, scoped = (
        talent_inventory(ir), buff_inventory(ir), source_inventory(ir),
    )
    scenarios = {}
    overall = Counter()
    for label, directory, targets in (("st", st, 1), ("two_target", two, 2)):
        directory = directory.resolve(strict=True)
        native = verify_folder(directory, targets, ir)
        raw = (directory / "simc_native_log.txt").read_bytes()
        value = compare_with_buff_baseline(
            raw.decode("utf-8"), ir, native, talent, buff, scoped, label)
        if value["native_IF_count"] != (255 if targets == 1 else 222):
            raise ScopedReplayError("PINNED_NATIVE_IF_COUNTS_CHANGED")
        scenarios[label] = {
            **value,
            "native_binary_sha256": native["native_binary_sha256"],
            "native_log_sha256": sha(raw),
        }
        overall.update(value["counts"])
    if (scenarios["st"]["native_binary_sha256"] !=
        scenarios["two_target"]["native_binary_sha256"]):
        raise ScopedReplayError("ST_TWO_NATIVE_BINARY_IDENTITY_MISMATCH")
    if overall["prior_buff_known"] != 273:
        raise ScopedReplayError("273_BUFF_BASELINE_NOT_REPRODUCED")
    if overall["matched"] + overall["unknown"] != 477:
        raise ScopedReplayError("FULL_NATIVE_IF_COUNT_NOT_PRESERVED")
    return {
        "schema": SCHEMA,
        "policy_id": POLICY,
        "status": "ACTION_SCOPED_IF_OPERAND_REPLAY_NOT_ACTION_READY_PARITY",
        "official_profile_git_blob_sha1": PINNED_FURY_BLOB,
        "source_scoped_symbols": scoped,
        "unobserved_cooldown_suffixes_left_UNKNOWN": unsupported_inventory(ir),
        "prior_source_buff_independent_IF_checks": 273,
        "additional_source_scoped_independent_checks":
            overall["newly_decidable_action_expr"],
        "independently_replayed_IF_matches": overall["matched"],
        "remaining_IF_UNKNOWN": overall["unknown"],
        "native_IF_evaluations": 477,
        "st": scenarios["st"], "two_target": scenarios["two_target"],
        "GCD_meaning": "action GCD duration, NOT GCD remaining",
        "cooldown_ready_meaning": "cooldown_t::up(), NOT queueable cooldown_t::is_ready()",
        "unknown_cooldown_id_remains_UNKNOWN": True,
        "Native_IF_result_used_as_AST_fact": False,
        "native_ready_used_as_AST_fact": False,
        "independent_full_action_ready": "NOT_PROVEN",
        "independent_action_choice": "NOT_PROVEN",
        "Full_General_Rotation": "NOT_COMPLETE",
        "second_AST_implementation_oracle": False,
        "WCL_API_calls": 0, "MAIN_promoted": False,
    }


def selftest():
    from simc_apl_semantic_ir_v2 import parse_profile
    ir = parse_profile(
        b"actions=foo,if=gcd<=1.5&cooldown.bladestorm.ready\n",
        require_source=False,
    )
    scoped = source_inventory(ir)
    assert scoped == ["cooldown.bladestorm.ready", "gcd"]
    log = "\n".join((
        "ZROT_NATIVE_IF_FACT_V1|10|default|1|foo|1|3|20|1",
        MARK + "10|default|1|foo|cooldown.bladestorm.ready|1",
        MARK + "10|default|1|foo|gcd|1.5",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|foo|1",
    ))
    groups = group_action_expr_pre(log, scoped)
    assert len(groups) == 1
    assert groups[0]["captured"]["gcd"] == 1.5
    assert groups[0]["captured"]["cooldown.bladestorm.ready"] == 1
    expr = ir["action_lists"]["default"][0]["expression_fields"]["if"]
    assert independent_if(expr, {"gcd": 1.5,
                                 "cooldown.bladestorm.ready": 1}) == 1
    assert independent_if(expr, {"gcd": 1.5}) is None
    missing = log.replace("cooldown.bladestorm.ready|1",
                          "cooldown.bladestorm.ready|-1")
    groups = group_action_expr_pre(missing, scoped)
    assert groups[0]["captured"]["cooldown.bladestorm.ready"] is None
    assert independent_if(expr, {"gcd": groups[0]["captured"]["gcd"]}) is None
    adversaries = (
        log.replace("cooldown.bladestorm.ready|1",
                    "cooldown.bladestorm.ready|3"),
        log.replace("gcd|1.5", "gcd|nan"),
        log.replace("gcd|1.5", "gcd|1.5\n" + MARK + "10|default|1|foo|gcd|1.5"),
        log.replace("gcd|1.5", "gcd|1.5").replace(
            "ZROT_NATIVE_SELECT_V1|ATTEMPT|10",
            "ZROT_NATIVE_SELECT_V1|ATTEMPT|11",
        ),
        log.replace(MARK + "10|default|1|foo|gcd|1.5", ""),
    )
    for sample in adversaries:
        try:
            group_action_expr_pre(sample, scoped)
        except ScopedReplayError:
            pass
        else:
            raise AssertionError("ACCEPTED_UNSOURCED_ACTION_EXPR_NATIVE_FACT")
    return {
        "status": "PASS_OFFLINE_SYNTHETIC", "checks": 12,
        "Native_SimC_executed": False, "WCL_API_calls": 0,
        "Native_IF_result_used_as_AST_fact": False,
        "ready_queueable_equated_to_cooldown_up": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile", type=Path)
    p.add_argument("--official-sim-clock-source", type=Path)
    p.add_argument("--native-st-dir", type=Path)
    p.add_argument("--native-2t-dir", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    sources = (
        a.official_profile, a.official_sim_clock_source,
        a.native_st_dir, a.native_2t_dir,
    )
    if not any(sources):
        data = selftest()
    elif all(sources):
        data = run(*sources)
    else:
        p.error("provide all pinned sources or none")
    raw = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("xb") as f:
            f.write(raw)
        print("NATIVE_ACTION_GCD_COOLDOWN_IF_REPLAY_SHA256=" + sha(raw))
    else:
        print(raw.decode(), end="")


if __name__ == "__main__":
    main()
