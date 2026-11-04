#!/usr/bin/env python3
"""Re-evaluate Native SimC movement and scheduled-event IF operands.

Reuse the validated 317/477 source-clock/talent/buff/action-context AST
baseline and add only source-observed movement.distance and
raid_event.movement.{in,distance}. Every record must share the exact
Native pre-IF decision source identity; Native IF Boolean is comparison
only AFTER Python AST replay. These simulation-derived event values are
NOT a target-dummy observation or encounter-specific advice.

Run without arguments for offline synthetic tests, or with official
pinned profile/clock and Native ST/2T directories for actual replay.
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
    verify_folder, parse_fact, exact_key, get_native_attempt,
    PINNED_FURY_BLOB,
)
from simc_native_if_source_clock_successor_v1 import pre_facts, verify_clock_source
from simc_native_if_talent_pre_instrument_v1 import talent_inventory
from simc_native_if_talent_pre_replay_v1 import (
    group_actual_pre_talents, independent_if,
)
from simc_native_if_buff_pre_instrument_v1 import buff_inventory
from simc_native_if_buff_pre_replay_v1 import group_actual_pre_buffs
from simc_native_if_action_gcd_cd_pre_instrument_v1 import source_inventory
from simc_native_if_action_gcd_cd_pre_replay_v1 import (
    group_action_expr_pre, compare_with_buff_baseline,
)
from simc_native_if_movement_event_pre_instrument_v1 import (
    MARK, inventory, MOVEMENT_RE, EVENT_RE,
)

SCHEMA = "ZrotNativeSimcMovementEventIndependentIfReplayV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"


class EnvironmentReplayError(ValueError):
    pass


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def parse_environment(line: str, accepted: set[str]) -> dict | None:
    at = line.find(MARK)
    if at < 0:
        return None
    parts = line[at:].strip().split("|")
    if (len(parts) != 7 or not parts[1].isdigit() or not parts[3].isdigit()
        or parts[5] not in accepted):
        raise EnvironmentReplayError("ENVIRONMENT_FACT_SCHEMA_OR_SYMBOL_MISMATCH")
    try:
        value = float(parts[6])
    except (ValueError, OverflowError):
        raise EnvironmentReplayError("SIMC_ENVIRONMENT_FACT_NONNUMERIC")
    if not math.isfinite(value):
        raise EnvironmentReplayError("SIMC_ENVIRONMENT_FACT_NONFINITE")
    symbol = parts[5]
    if (symbol.endswith(".distance") or symbol.endswith(".distance_min") or
        symbol.endswith(".distance_max")) and value < 0:
        raise EnvironmentReplayError("SIMC_NEGATIVE_MOVEMENT_DISTANCE")
    if (symbol.endswith(".in") or symbol.endswith(".remains")) and value < 0:
        raise EnvironmentReplayError("SIMC_NEGATIVE_EVENT_TIME")
    if symbol.endswith((".exists", ".up")) and value not in (0, 1):
        raise EnvironmentReplayError("SIMC_EVENT_BOOL_OUT_OF_BOUNDS")
    return {
        "time_ms": int(parts[1]), "list": parts[2],
        "ordinal": int(parts[3]), "native_name": parts[4],
        "symbol": symbol, "value": value,
    }


def group_environment_facts(trace: str, symbols: list[str]) -> list[dict]:
    expected = set(symbols)
    if not expected:
        raise EnvironmentReplayError("EMPTY_ENVIRONMENT_SOURCE_MANIFEST")
    pending = None
    groups = []
    for line in trace.splitlines():
        resource = parse_fact(line)
        if resource is not None:
            if pending is not None:
                raise EnvironmentReplayError("OVERLAPPING_ENVIRONMENT_PRE_IF_ROWS")
            pending = {"key": exact_key(resource), "facts": {}}
            continue
        env = parse_environment(line, expected)
        if env is not None:
            if pending is None or exact_key(env) != pending["key"]:
                raise EnvironmentReplayError("ENVIRONMENT_NOT_MATCHED_TO_SOURCE_PRE_IF")
            if env["symbol"] in pending["facts"]:
                raise EnvironmentReplayError("DUPLICATE_ENVIRONMENT_FACT_AT_IF")
            pending["facts"][env["symbol"]] = env["value"]
            continue
        attempt = get_native_attempt(line)
        if attempt is not None and pending is not None:
            if exact_key(attempt) != pending["key"]:
                raise EnvironmentReplayError("IF_ENVIRONMENT_ACTION_ROW_BOUNDARY_CHANGED")
            if set(pending["facts"]) != expected:
                raise EnvironmentReplayError("INCOMPLETE_ENVIRONMENT_FACT_MANIFEST")
            groups.append(pending)
            pending = None
    if pending is not None:
        raise EnvironmentReplayError("ENVIRONMENT_IF_ROW_UNPAIRED_AT_EOF")
    return groups


def compare_with_scoped_baseline(trace: str, ir: dict, native_before: dict,
                                 talents: list[str], buffs: list[str],
                                 scoped: list[str], envs: list[str],
                                 scenario: str) -> dict:
    previous = compare_with_buff_baseline(
        trace, ir, native_before, talents, buffs, scoped, scenario)
    rows = native_before["all_native_if_pre_fact_ledger"]
    tgroup = group_actual_pre_talents(trace, talents)
    bgroup = group_actual_pre_buffs(trace, buffs)
    sgroup = group_action_expr_pre(trace, scoped)
    egroup = group_environment_facts(trace, envs)
    if not (len(rows) == len(tgroup) == len(bgroup) == len(sgroup) == len(egroup)):
        raise EnvironmentReplayError("NATIVE_PRE_IF_COHORT_ALIGNMENT_CHANGED")
    counts = Counter()
    unresolved = Counter()
    samples = []
    distinct_observed = Counter()
    for index, (row, t, b, s, e) in enumerate(
        zip(rows, tgroup, bgroup, sgroup, egroup)
    ):
        k = (row["at_ms"], row["source_list"],
             row["source_index"] + 1, row["native_name"])
        if any(x["key"] != k for x in (t, b, s, e)):
            raise EnvironmentReplayError("EXACT_PRE_IF_SOURCE_POINTER_CHANGED")
        source = ir["action_lists"][row["source_list"]][row["source_index"]]
        expr = source["expression_fields"].get("if")
        if (expr is None or row["source_line_sha256"] != source["source_sha256"]
            or row["source_if"] != expr["source"]
            or row["source_if_symbols"] != expr["symbols"]):
            raise EnvironmentReplayError("SOURCE_APL_IF_SYMBOL_AND_HASH_NOT_MATCHED")
        base = {
            **pre_facts(row), **t["values"], **b["values"],
            **{symbol: value for symbol, value in s["captured"].items()
               if value is not None},
        }
        old_value = independent_if(expr, base)
        new_facts = {**base, **e["facts"]}
        result = independent_if(expr, new_facts)
        if old_value is not None:
            counts["previously_decidable"] += 1
            if old_value != result:
                raise EnvironmentReplayError("317_PRIOR_INDEPENDENT_IF_PROOFS_REGRESSED")
        for name in envs:
            distinct_observed[name] += 1
        if result is None:
            counts["unknown"] += 1
            unresolved.update(set(expr["symbols"]) - set(new_facts))
            continue
        if result != row["native_if_result_verification_only"]:
            raise EnvironmentReplayError(
                "INDEPENDENT_MOVEMENT_AST_NATIVE_IF_CONFLICT:" + scenario +
                ":" + row["source_list"] + ":" +
                str(row["source_index"]) + ":" + str(index))
        counts["matched"] += 1
        if old_value is None:
            counts["new_by_environment"] += 1
            if len(samples) < 16:
                samples.append({
                    "scenario": scenario,
                    "at_ms": row["at_ms"],
                    "source_list": row["source_list"],
                    "source_index": row["source_index"],
                    "source_if": expr["source"],
                    "source_hash": row["source_line_sha256"],
                    "simc_environment_native_pre": e["facts"],
                    "independent_ast_bool": result,
                    "native_if_bool_POST_computation_only":
                        row["native_if_result_verification_only"],
                })
    if (counts["previously_decidable"] != previous["counts"]["matched"] or
        counts["matched"] + counts["unknown"] != len(rows) or
        counts["new_by_environment"] !=
            counts["matched"] - counts["previously_decidable"]):
        raise EnvironmentReplayError("INDEPENDENT_ENVIRONMENT_REPLAY_ACCOUNTING_DRIFT")
    return {
        "native_actual_IF_count": len(rows),
        "counts": dict(sorted(counts.items())),
        "unresolved_symbol_incidences": dict(sorted(unresolved.items())),
        "new_matched_examples": samples,
        "source_observations_count_by_symbol": dict(sorted(distinct_observed.items())),
        "previously_matched_action_scoped_counts": previous["counts"],
    }


def run(profile: Path, clock: Path, st: Path, two: Path) -> dict:
    verify_clock_source(clock.read_bytes())
    ir = parse_profile(profile.read_bytes(), require_source=True,
                       expected_git_blob=PINNED_FURY_BLOB)
    talents, buffs, scoped, envs = (
        talent_inventory(ir), buff_inventory(ir), source_inventory(ir),
        inventory(ir),
    )
    cases = {}
    totals = Counter()
    for label, root, targets in (("st", st, 1), ("two_target", two, 2)):
        root = root.resolve(strict=True)
        old = verify_folder(root, targets, ir)
        raw = (root / "simc_native_log.txt").read_bytes()
        result = compare_with_scoped_baseline(raw.decode("utf-8"), ir, old,
                                              talents, buffs, scoped, envs, label)
        if result["native_actual_IF_count"] != (255 if targets == 1 else 222):
            raise EnvironmentReplayError("PINNED_REAL_NATIVE_IF_COHORT_CHANGED")
        cases[label] = {
            **result,
            "native_log_sha256": sha(raw),
            "instrumented_binary_sha256": old["native_binary_sha256"],
        }
        totals.update(result["counts"])
    if (cases["st"]["instrumented_binary_sha256"] !=
        cases["two_target"]["instrumented_binary_sha256"]):
        raise EnvironmentReplayError("ST_TWO_TARGET_NATIVE_BINARY_NOT_IDENTICAL")
    if totals["previously_decidable"] != 317:
        raise EnvironmentReplayError("PREVIOUS_ACTION_SCOPED_317_BASELINE_NOT_REPRODUCED")
    if totals["matched"] + totals["unknown"] != 477:
        raise EnvironmentReplayError("PINNED_477_NATIVE_IF_ACCOUNTING_CHANGED")
    return {
        "schema": SCHEMA,
        "scope_policy_id": POLICY,
        "status": "SOURCE_SIMC_ENVIRONMENT_IF_AST_SUBSET_NOT_ACTION_READY",
        "official_apl_profile_blob_sha1": PINNED_FURY_BLOB,
        "source_environment_symbols": envs,
        "previously_source_matched": 317,
        "newly_independent_environment_IF_matches": totals["new_by_environment"],
        "total_independent_IF_matches": totals["matched"],
        "remaining_IF_UNKNOWN": totals["unknown"],
        "actual_native_IF_count": 477,
        "st": cases["st"], "two_target": cases["two_target"],
        "environment_values_from": "SIMULATIONCRAFT_SOURCE_NATIVE_AT_IF",
        "missing_simc_event_constant_semantics_only": True,
        "simulated_future_event_not_real_game_forecast": True,
        "movement_not_required_for_stationary_branch": True,
        "Native_IF_boolean_used_as_AST_operand": False,
        "Native_action_ready_used_as_AST_operand": False,
        "independent_full_action_ready": False,
        "independent_action_selection": False,
        "general_rotation_completed": False,
        "WCL_API_calls": 0,
        "MAIN_promoted": False,
    }


def selftest() -> dict:
    from simc_apl_semantic_ir_v2 import parse_profile
    ir = parse_profile(
        b"actions=charge,if=time<=0.5|movement.distance>5\n"
        b"actions+=/heroic_leap,if=raid_event.movement.distance>25&raid_event.movement.in>45\n",
        require_source=False,
    )
    syms = inventory(ir)
    assert syms == [
        "movement.distance",
        "raid_event.movement.distance",
        "raid_event.movement.in",
    ]
    raw = "\n".join((
        "ZROT_NATIVE_IF_FACT_V1|10|default|1|charge|1|3|20|1",
        MARK + "10|default|1|charge|movement.distance|0",
        MARK + "10|default|1|charge|raid_event.movement.distance|0",
        MARK + "10|default|1|charge|raid_event.movement.in|99999999",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|charge|1",
    ))
    rows = group_environment_facts(raw, syms)
    assert len(rows) == 1 and rows[0]["facts"]["movement.distance"] == 0
    assert rows[0]["facts"]["raid_event.movement.in"] == 99999999
    expr = ir["action_lists"]["default"][0]["expression_fields"]["if"]
    assert independent_if(expr, {"time": 0.01, **rows[0]["facts"]}) == 1
    assert independent_if(expr, {"time": 2.0, **rows[0]["facts"]}) == 0
    event = ir["action_lists"]["default"][1]["expression_fields"]["if"]
    assert independent_if(event, rows[0]["facts"]) == 0
    for malformed in (
        raw.replace("movement.distance|0", "movement.distance|nan", 1),
        raw.replace("raid_event.movement.in|99999999", "raid_event.movement.in|-1"),
        raw.replace("raid_event.movement.distance|0", "raid_event.movement.distance|-2"),
        raw.replace(MARK + "10|default|1|charge|movement.distance|0", ""),
        raw.replace("raid_event.movement.distance|0", "movement.distance|0"),
        raw.replace("ZROT_NATIVE_SELECT_V1|ATTEMPT|10|",
                    "ZROT_NATIVE_SELECT_V1|ATTEMPT|11|"),
    ):
        try:
            group_environment_facts(malformed, syms)
        except EnvironmentReplayError:
            pass
        else:
            raise AssertionError("INVALID_OR_SPOOFED_ENVIRONMENT_EVIDENCE_ACCEPTED")
    return {
        "status": "PASS_OFFLINE_SYNTHETIC",
        "checks": 12,
        "source_simc_native_not_executed": True,
        "WCL_API_calls": 0,
        "synthetic_raid_event_not_realtime_truth": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile", type=Path)
    p.add_argument("--official-sim-clock-source", type=Path)
    p.add_argument("--native-st-dir", type=Path)
    p.add_argument("--native-2t-dir", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    sources = (a.official_profile, a.official_sim_clock_source,
               a.native_st_dir, a.native_2t_dir)
    if not any(sources):
        result = selftest()
    elif all(sources):
        result = run(*sources)
    else:
        p.error("four pinned inputs required together for real Native replay")
    blob = (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("xb") as f: f.write(blob)
        print("NATIVE_SIMC_MOVEMENT_EVENT_IF_AST_SHA256=" + sha(blob))
    else:
        print(blob.decode(), end="")


if __name__ == "__main__":
    main()
