#!/usr/bin/env python3
"""Independent Python AST replay of source-derived Native talent PRE operands.

Source facts come from the actual actor talent expression at each real IF
evaluation, not Native IF/ready/selection outcomes. Reuse the original
source-pointer audit and Rage/enemies PRE facts plus proven SimC source clock.
Mismatch is FAIL; missing symbols stay UNKNOWN. No WCL, no new gameplay claims.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import parse_profile, evaluate_ast, truth
from simc_native_if_pre_operand_replay_v1 import (
    verify_folder, parse_fact, exact_key, get_native_attempt,
    PINNED_FURY_BLOB,
)
from simc_native_if_source_clock_successor_v1 import (
    pre_facts, verify_clock_source,
)
from simc_native_if_talent_pre_instrument_v1 import (
    talent_inventory, MARK,
)

SCHEMA = "ZrotNativeSourceTalentPreIndependentAstV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"


class TalentReplayError(ValueError):
    pass


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def parse_talent(line, required):
    at = line.find(MARK)
    if at < 0:
        return None
    parts = line[at:].strip().split("|")
    if (len(parts) != 7 or not parts[1].isdigit()
        or not parts[3].isdigit() or parts[5] not in required):
        raise TalentReplayError("TALENT_PRE_RECORD_SCHEMA_OR_SYMBOL_CHANGED")
    try:
        value = float(parts[6])
    except (ValueError, OverflowError):
        raise TalentReplayError("TALENT_PRE_VALUE_INVALID")
    # Talent ranks may be numeric; never assume absent fields are 0.
    if not math.isfinite(value) or value < 0 or value > 100:
        raise TalentReplayError("TALENT_PRE_VALUE_NOT_BOUNDED")
    return {
        "time_ms": int(parts[1]), "list": parts[2],
        "ordinal": int(parts[3]), "native_name": parts[4],
        "symbol": parts[5], "value": value,
    }


def group_actual_pre_talents(native_log, symbols):
    """Pair facts with the same real ready-attempt boundary, preserving order."""
    expected = set(symbols)
    pending = None
    grouped = []
    for line in native_log.splitlines():
        resource = parse_fact(line)
        if resource:
            if pending is not None:
                raise TalentReplayError("UNMATCHED_PRE_FACT_BEFORE_NEXT_IF")
            pending = {"key": exact_key(resource), "values": {}}
            continue
        talent = parse_talent(line, expected)
        if talent is not None:
            if pending is None or exact_key(talent) != pending["key"]:
                raise TalentReplayError("TALENT_FACT_WITHOUT_MATCHED_PRE_IF_EVENT")
            if talent["symbol"] in pending["values"]:
                raise TalentReplayError("DUPLICATE_TALENT_FACT_FOR_IF")
            pending["values"][talent["symbol"]] = talent["value"]
            continue
        attempt = get_native_attempt(line)
        if attempt is not None and pending is not None:
            if exact_key(attempt) != pending["key"]:
                raise TalentReplayError("NATIVE_READY_ATTEMPT_BOUNDARY_CHANGED")
            if set(pending["values"]) != expected:
                raise TalentReplayError("INCOMPLETE_TALENT_FACT_IN_REAL_IF_EVENT")
            grouped.append(pending)
            pending = None
    if pending is not None:
        raise TalentReplayError("END_OF_LOG_UNMATCHED_TALENT_FACT")
    return grouped


def independent_if(expression, facts):
    result = truth(evaluate_ast(expression["ast"], facts))
    return None if result is None else int(bool(result))


def compare_actual(trace, ir, pinned_old, symbols, scenario):
    old_ledger = pinned_old["all_native_if_pre_fact_ledger"]
    real_groups = group_actual_pre_talents(trace, symbols)
    if len(real_groups) != len(old_ledger):
        raise TalentReplayError("NATIVE_IF_COUNTS_DIFFER_FROM_OLD_SOURCE_REPORTER")
    counts = Counter()
    examples = []
    unresolved = Counter()
    for i, (group, old) in enumerate(zip(real_groups, old_ledger)):
        original_key = (
            old["at_ms"], old["source_list"],
            old["source_index"] + 1, old["native_name"],
        )
        if group["key"] != original_key:
            raise TalentReplayError("TALENT_PRE_AND_APL_ROW_ORDER_DIFFER")
        name, index = old["source_list"], old["source_index"]
        source_row = ir["action_lists"][name][index]
        expr = source_row["expression_fields"].get("if")
        if (not expr
            or old["source_line_sha256"] != source_row["source_sha256"]
            or old["source_if"] != expr["source"]
            or old["source_if_symbols"] != expr["symbols"]):
            raise TalentReplayError("IF_SOURCE_PROVENANCE_DIFFER")
        base = pre_facts(old)
        old_result = independent_if(expr, base)
        expanded = {**base, **group["values"]}
        result = independent_if(expr, expanded)
        if old_result is not None:
            counts["source_clock_already_known"] += 1
            if result != old_result:
                raise TalentReplayError("LOST_PREVIOUS_SOURCE_CLOCK_PROOF")
        if result is None:
            counts["unknown"] += 1
            unresolved.update(set(expr["symbols"]) - set(expanded))
            continue
        if result != old["native_if_result_verification_only"]:
            raise TalentReplayError(
                "INDEPENDENT_TALENT_AST_NATIVE_IF_CONFLICT:" +
                scenario + ":" + name + ":" + str(index) + ":" + str(i))
        counts["independently_matched"] += 1
        if old_result is None:
            counts["newly_decidable_by_talent"] += 1
            if len(examples) < 12:
                examples.append({
                    "source_list": name, "source_index": index,
                    "at_ms": old["at_ms"],
                    "source_if": expr["source"],
                    "source_row_sha256": source_row["source_sha256"],
                    "actual_native_pre_talents": group["values"],
                    "independent_AST_bool": result,
                    "native_if_bool_verification_only":
                        old["native_if_result_verification_only"],
                })
    if (counts["independently_matched"] + counts["unknown"] != len(old_ledger)
        or counts["source_clock_already_known"] < 1):
        raise TalentReplayError("REPLAY_ACCOUNTING_INCOMPLETE")
    return {
        "real_native_IF_count": len(old_ledger),
        "counts": dict(sorted(counts.items())),
        "new_independently_decidable_examples": examples,
        "unresolved_symbol_incidences": dict(sorted(unresolved.items())),
    }


def run(profile_path, clock_source_path, st_dir, two_dir):
    verify_clock_source(clock_source_path.read_bytes())
    ir = parse_profile(profile_path.read_bytes(), require_source=True,
                       expected_git_blob=PINNED_FURY_BLOB)
    symbols = talent_inventory(ir)
    scenarios = {}
    counts = Counter()
    for label, folder, targets in (("st", st_dir, 1),
                                   ("two_target", two_dir, 2)):
        folder = folder.resolve(strict=True)
        old = verify_folder(folder, targets, ir)
        log = (folder / "simc_native_log.txt").read_bytes()
        result = compare_actual(log.decode("utf-8"), ir, old, symbols, label)
        if result["real_native_IF_count"] != (255 if targets == 1 else 222):
            raise TalentReplayError("PINNED_NATIVE_IF_COHORT_SIZE_DRIFT")
        scenarios[label] = {
            **result,
            "native_log_sha256": sha(log),
            "native_binary_sha256": old["native_binary_sha256"],
            "source_effective_apl_sha256": old["native_apl_sha256"],
        }
        counts.update(result["counts"])
    if (scenarios["st"]["native_binary_sha256"] !=
        scenarios["two_target"]["native_binary_sha256"]):
        raise TalentReplayError("NATIVE_BINARY_NOT_SAME_ST_2T")
    if counts["source_clock_already_known"] != 68:
        raise TalentReplayError("BASELINE_SOURCE_CLOCK_68_NOT_REPRODUCED")
    if counts["independently_matched"] + counts["unknown"] != 477:
        raise TalentReplayError("PINNED_NATIVE_IF_TOTAL_DRIFT")
    return {
        "schema": SCHEMA, "scope_policy_id": POLICY,
        "status": "ACTUAL_NATIVE_TALENT_PRE_OPERANDS_INDEPENDENT_AST_SUBSET",
        "APL_source_profile_git_blob": PINNED_FURY_BLOB,
        "source_derived_talent_symbols": symbols,
        "original_rage_enemies_time_matched": 68,
        "new_independent_talent_cases": counts["newly_decidable_by_talent"],
        "total_independently_matched": counts["independently_matched"],
        "remaining_UNKNOWN": counts["unknown"],
        "real_native_IF_events": 477,
        "st": scenarios["st"], "two_target": scenarios["two_target"],
        "source_readouts_not_native_IF_results": True,
        "Native_IF_truth_only_compared_after_AST": True,
        "Native_ready_boolean_as_AST_operand": False,
        "cross_actor_and_second_spec_parity": "NOT_PROVEN",
        "G4_full_readiness_and_selection": "NOT_PROVEN",
        "General_Rotation_complete": False,
        "WCL_API_calls": 0, "MAIN_promotion": False,
    }


def selftest():
    ir = parse_profile(
        b"actions=foo,if=talent.foo&rage>10\n",
        require_source=False,
    )
    symbols = talent_inventory(ir)
    assert symbols == ["talent.foo"]
    log = "\n".join((
        "ZROT_NATIVE_IF_FACT_V1|10|default|1|foo|1|3|20|1",
        MARK + "10|default|1|foo|talent.foo|1",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|foo|1",
    ))
    groups = group_actual_pre_talents(log, symbols)
    assert len(groups) == 1
    assert groups[0]["values"]["talent.foo"] == 1.0
    result = independent_if(
        ir["action_lists"]["default"][0]["expression_fields"]["if"],
        {"rage": 20, "talent.foo": 1},
    )
    assert result == 1
    assert independent_if(
        ir["action_lists"]["default"][0]["expression_fields"]["if"],
        {"rage": 20},
    ) is None
    for bad in (
        log.replace("talent.foo|1", "talent.foo|NaN"),
        log.replace("talent.foo|1", "talent.foo|1\n" +
                    MARK + "10|default|1|foo|talent.foo|1"),
        log.replace("|10|default|1|foo|talent.foo|1",
                    "|11|default|1|foo|talent.foo|1"),
        log.replace(MARK + "10|default|1|foo|talent.foo|1", ""),
    ):
        try:
            group_actual_pre_talents(bad, symbols)
        except TalentReplayError:
            pass
        else:
            raise AssertionError("MALFORMED_TALENT_EVIDENCE_ACCEPTED")
    return {
        "status": "PASS_OFFLINE_SYNTHETIC", "checks": 10,
        "actual_native_simc": "NOT_RUN", "WCL_API_calls": 0,
        "Native_truth_used_as_operand": False,
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
        p.error("provide all four pinned sources or none for synthetic selftest")
    blob = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
            "\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("xb") as f:
            f.write(blob)
        print("SIMC_NATIVE_TALENT_PRE_AST_SHA256=" + sha(blob))
    else:
        print(blob.decode(), end="")


if __name__ == "__main__":
    main()
