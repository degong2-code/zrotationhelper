#!/usr/bin/env python3
"""Independent IF replay for *actual moving* SimC Native ST and 2T cohorts.

Reuse original source-pin and generic AST replay code; deliberately do not
apply the stationary 477/317 case counts to the moving cohort. The actor
movement state and future simulated event forecast are observed together,
but the forecast is NOT automatically observable in WoW. Readiness and
action choice remain unproven. No WCL queries or encounter-specific plans.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile, git_blob
from simc_native_if_pre_operand_replay_v1 import (
    PINNED_FURY_BLOB, verify_folder,
)
from simc_native_if_source_clock_successor_v1 import verify_clock_source
from simc_native_if_talent_pre_instrument_v1 import talent_inventory
from simc_native_if_buff_pre_instrument_v1 import buff_inventory
from simc_native_if_action_gcd_cd_pre_instrument_v1 import source_inventory
from simc_native_if_movement_event_pre_instrument_v1 import inventory
from simc_native_if_movement_event_pre_replay_v1 import (
    compare_with_scoped_baseline, group_environment_facts,
)

POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SCHEMA = "ZrotActualNativeMovingCohortIndependentIfV1"
DERIVED_PROFILE_BLOB = "063cce2e3072e8bd9ae52f42118971c684e46f12"


class MovingCohortError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pinned_moving_profile(raw: bytes, derived: bytes) -> dict:
    if git_blob(raw) != PINNED_FURY_BLOB:
        raise MovingCohortError("OFFICIAL_PROFILE_SOURCE_BLOB_CHANGED")
    if derived != raw + b"\nfight_style=LightMovement\n":
        raise MovingCohortError("DERIVED_MOVEMENT_PROFILE_NOT_EXACT")
    if git_blob(derived) != DERIVED_PROFILE_BLOB:
        raise MovingCohortError("DERIVED_PROFILE_GIT_BLOB_CHANGED")
    return {
        "pinned_original_profile_blob_sha1": PINNED_FURY_BLOB,
        "pinned_derived_movement_blob_sha1": DERIVED_PROFILE_BLOB,
        "source_profile_addition_only": "fight_style=LightMovement",
    }


def audit(ir: dict, observed: dict, scenario: dict, trace: str,
          source_talents: list[str], source_buffs: list[str],
          source_actions: list[str], source_envs: list[str],
          label: str, expected: int) -> dict:
    records = observed["all_native_if_pre_fact_ledger"]
    if len(records) != expected:
        raise MovingCohortError("MOVING_NATIVE_PRE_COHORT_COUNT_DRIFT")
    proof = compare_with_scoped_baseline(
        trace, ir, observed, source_talents, source_buffs,
        source_actions, source_envs, label
    )
    counts = proof["counts"]
    if counts["matched"] + counts["unknown"] != expected:
        raise MovingCohortError("MOVING_NATIVE_AST_ACCOUNTING_DRIFT")
    grouped = group_environment_facts(trace, source_envs)
    if len(grouped) != expected:
        raise MovingCohortError("MOVING_NATIVE_ACTOR_FACT_COUNT_DRIFT")
    movement_positive = 0
    future_event_positive = 0
    for g in grouped:
        values = g["facts"]
        if values["movement.distance"] > 0:
            movement_positive += 1
        if 0 < values["raid_event.movement.in"] < 30:
            future_event_positive += 1
    if movement_positive <= 0 or future_event_positive <= 0:
        raise MovingCohortError("ACTUAL_MOVING_STATE_OR_SCHEDULED_EVENT_MISSING")
    if movement_positive != scenario["nonzero_actor_movement_PRE_observations"]:
        raise MovingCohortError("MOVING_COHORT_PRE_FACT_COUNT_CONFLICT")
    if (scenario["native_if_pre_observation_count"] != expected or
        scenario["pristine_instrumented_action_sequence_exact"] is not True):
        raise MovingCohortError("PRISTINE_MOVING_NATIVE_SEQUENCE_PROOF_MISSING")
    # Note: conditions evaluated while distance>0 may short circuit in
    # other operands; count actual Native IF evaluations separately.
    move_dependent = Counter()
    for row, group in zip(records, grouped):
        source = ir["action_lists"][row["source_list"]][row["source_index"]]
        expr = source["expression_fields"].get("if")
        if not expr:
            raise MovingCohortError("NO_PINNED_SOURCE_EXPRESSION_FOR_NATIVE_IF")
        if group["facts"]["movement.distance"] > 0:
            move_dependent["native_IF_with_positive_actor_movement"] += 1
            if "movement.distance" in expr["symbols"]:
                move_dependent["native_IF_with_positive_movement_and_movement_condition"] += 1
        if any(sym.startswith("raid_event.movement.") for sym in expr["symbols"]):
            move_dependent["native_IF_referencing_scheduled_movement_event"] += 1
    return {
        "target_count": 1 if label == "st" else 2,
        "Native_IF_count": expected,
        "independent_AST_matched": counts["matched"],
        "UNKNOWN": counts["unknown"],
        "new_decidable_by_environment": counts.get("new_by_environment", 0),
        "prior_decidable_before_environment": counts["previously_decidable"],
        "source_replay_counts": counts,
        "source_unknown_symbol_incidence": proof["unresolved_symbol_incidences"],
        "actual_positive_movement_PRE_IF_count": movement_positive,
        "actual_upcoming_event_PRE_IF_count": future_event_positive,
        "moving_decision_context_counts": dict(sorted(move_dependent.items())),
        "performed_actions_identical_original_vs_instrumented": True,
        "actual_source_evidence": "Native sourced event/actor PRE + official APL",
        "Native_IF_or_ready_boolean_as_AST_operand": False,
    }


def run(original_profile: Path, derived_profile: Path, clock: Path,
        movement_proof: Path, st: Path, two: Path) -> dict:
    original = original_profile.read_bytes()
    pinned = pinned_moving_profile(original, derived_profile.read_bytes())
    verify_clock_source(clock.read_bytes())
    ir = parse_profile(original, require_source=True,
                       expected_git_blob=PINNED_FURY_BLOB)
    proof_raw = movement_proof.read_bytes()
    scenario = json.loads(proof_raw)
    if (scenario.get("schema") != "ZrotNativeGenericSimcLightMovementScenarioV1"
        or scenario.get("status") !=
        "GENERIC_MOVEMENT_NATIVE_NONPERTURBATION_AND_EVENT_FORECAST_OBSERVED"
        or scenario.get("general_rotation_priority_validated") is not False
        or scenario.get("Native_ready_independent") is not False):
        raise MovingCohortError("ACTUAL_NATIVE_MOVING_SCENARIO_RECEIPT_INVALID")
    source_talents = talent_inventory(ir)
    source_buffs = buff_inventory(ir)
    source_actions = source_inventory(ir)
    source_envs = inventory(ir)
    outcomes = {}
    totals = Counter()
    for label, directory, targets, expected, scenario_key in (
        ("st", st, 1, 253, "st"),
        ("two_target", two, 2, 223, "2t"),
    ):
        directory = directory.resolve(strict=True)
        old = verify_folder(directory, targets, ir)
        raw = (directory / "simc_native_log.txt").read_bytes()
        one = audit(ir, old, scenario["scenarios"][scenario_key],
                    raw.decode("utf-8"), source_talents, source_buffs,
                    source_actions, source_envs, label, expected)
        one["native_source_log_sha256"] = sha(raw)
        one["native_binary_sha256"] = old["native_binary_sha256"]
        one["native_effective_apl_sha256"] = old["native_apl_sha256"]
        outcomes[label] = one
        totals["IF"] += one["Native_IF_count"]
        totals["matched"] += one["independent_AST_matched"]
        totals["unknown"] += one["UNKNOWN"]
        totals["positive_distance"] += one["actual_positive_movement_PRE_IF_count"]
    if (outcomes["st"]["native_binary_sha256"] !=
        outcomes["two_target"]["native_binary_sha256"] or
        outcomes["st"]["native_effective_apl_sha256"] !=
        outcomes["two_target"]["native_effective_apl_sha256"] or
        totals["IF"] != 476 or totals["matched"]+totals["unknown"] != 476
        or totals["positive_distance"] != 17):
        raise MovingCohortError("MOVING_ST_TWO_TARGET_SOURCE_PARITY_FAILED")
    return {
        "schema": SCHEMA,
        "scope_policy_id": POLICY,
        "status": "REAL_MOVING_NATIVE_IF_AST_SUBSET_NOT_FULL_ACTION_READY",
        "profile_source_proof": pinned,
        "source_environment_symbols": source_envs,
        "source_movement_scenario_sha256": sha(proof_raw),
        "moving_Native_IF_total": totals["IF"],
        "moving_independent_AST_matched": totals["matched"],
        "moving_IF_UNKNOWN": totals["unknown"],
        "moving_positive_distance_PRE_count": totals["positive_distance"],
        "st": outcomes["st"],
        "two_target": outcomes["two_target"],
        "actual_movement_exercised": True,
        "moving_event_is_SimC_forecast_not_WoW_forecast": True,
        "source_comparison_before_native_truth": True,
        "Native_IF_truth_used_as_AST_fact": False,
        "Native_ready_used_as_AST_fact": False,
        "full_action_ready_independently_proven": False,
        "full_General_Rotation_priority_complete": False,
        "WCL_API_calls": 0,
        "MAIN_promoted": False,
    }


def selftest() -> dict:
    from simc_apl_semantic_ir_v2 import parse_profile
    from simc_native_if_movement_event_pre_replay_v1 import (
        independent_if, group_environment_facts
    )
    source = parse_profile(
        b"actions=charge,if=time<=0.5|movement.distance>5\n"
        b"actions+=/heroic_leap,if=raid_event.movement.in>4&raid_event.movement.distance>5\n",
        require_source=False
    )
    rows = source["action_lists"]["default"]
    first = rows[0]["expression_fields"]["if"]
    second = rows[1]["expression_fields"]["if"]
    actual = {
        "time": 8,
        "movement.distance": 10,
        "raid_event.movement.in": 6,
        "raid_event.movement.distance": 15,
    }
    assert independent_if(first, actual) == 1
    assert independent_if(second, actual) == 1
    assert independent_if(first, {"time": 8}) is None
    assert independent_if(second, {"raid_event.movement.in":6}) is None
    assert independent_if(first, {"time":8,"movement.distance":0}) == 0
    original = b"actions=charge\n"
    try:
        pinned_moving_profile(original, original+b"\nfight_style=Patchwerk\n")
    except MovingCohortError:
        pass
    else:
        raise AssertionError("NON_MOVEMENT_PROFILE_NOT_REJECTED")
    fake = "\n".join((
        "ZROT_NATIVE_IF_FACT_V1|10|default|1|charge|1|3|20|1",
        "ZROT_NATIVE_IF_MOVEMENT_EVENT_PRE_V1|10|default|1|charge|movement.distance|10",
        "ZROT_NATIVE_IF_MOVEMENT_EVENT_PRE_V1|10|default|1|charge|raid_event.movement.distance|15",
        "ZROT_NATIVE_IF_MOVEMENT_EVENT_PRE_V1|10|default|1|charge|raid_event.movement.in|6",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|charge|1",
    ))
    groups=group_environment_facts(fake, [
        "movement.distance", "raid_event.movement.distance", "raid_event.movement.in"
    ])
    assert len(groups) == 1 and groups[0]["facts"]["movement.distance"] == 10
    return {
        "status": "PASS_OFFLINE_SYNTHETIC",
        "checks": 9,
        "moving_native_run": False,
        "WCL_API_calls": 0,
        "Native_IF_truth_as_AST_fact": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile", type=Path)
    p.add_argument("--moving-profile", type=Path)
    p.add_argument("--official-sim-clock-source", type=Path)
    p.add_argument("--native-moving-scenario-proof", type=Path)
    p.add_argument("--native-moving-st-dir", type=Path)
    p.add_argument("--native-moving-2t-dir", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    inp = (args.official_profile, args.moving_profile,
           args.official_sim_clock_source, args.native_moving_scenario_proof,
           args.native_moving_st_dir, args.native_moving_2t_dir)
    if not any(inp):
        data = selftest()
    elif all(inp):
        data = run(*inp)
    else:
        p.error("all 6 pinned arguments required for actual moving replay")
    raw = (json.dumps(data, sort_keys=True, separators=(",", ":"))+"\n").encode()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("xb") as output:
            output.write(raw)
        print("REAL_MOVING_NATIVE_AST_SHA256="+sha(raw))
    else:
        print(raw.decode(), end="")


if __name__ == "__main__":
    main()
