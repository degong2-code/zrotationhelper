#!/usr/bin/env python3
"""Incremental Native PRE buff operand replay atop proven 210/477 talent result.

Official SimC source names and exact Native source-pointer row identity are
required. Independently AST-evaluate Rage/enemies/time/talent/buff facts;
Native IF truth is checked AFTER evaluation, not supplied as an input.
Unknown movement, boss events, cooldown, variables etc remain UNKNOWN.
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
    group_actual_pre_talents, compare_actual as compare_legacy_talents,
    independent_if,
)
from simc_native_if_buff_pre_instrument_v1 import buff_inventory, MARK

SCHEMA = "ZrotSourceNativeBuffPreIndependentAstV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"


class BuffReplayError(ValueError):
    pass


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def parse_buff(line, accepted):
    pos = line.find(MARK)
    if pos < 0:
        return None
    elements = line[pos:].strip().split("|")
    if (len(elements) != 7 or not elements[1].isdigit()
        or not elements[3].isdigit() or elements[5] not in accepted):
        raise BuffReplayError("BUFF_PRE_RECORD_SCHEMA_OR_SYMBOL_CHANGED")
    try:
        value = float(elements[6])
    except (ValueError, OverflowError):
        raise BuffReplayError("BUFF_PRE_VALUE_MALFORMED")
    if not math.isfinite(value):
        raise BuffReplayError("BUFF_PRE_VALUE_NONFINITE")
    prop = elements[5].rsplit(".", 1)[1]
    if prop in ("up", "down") and value not in (0.0, 1.0):
        raise BuffReplayError("BUFF_PRE_BOOLEAN_NOT_ZERO_ONE")
    if prop == "stack" and (value < 0 or value > 10000
                            or not value.is_integer()):
        raise BuffReplayError("BUFF_PRE_STACK_NOT_BOUNDED_INTEGER")
    return {
        "time_ms": int(elements[1]), "list": elements[2],
        "ordinal": int(elements[3]), "native_name": elements[4],
        "symbol": elements[5], "value": value,
    }


def group_actual_pre_buffs(native_log, symbols):
    expected = set(symbols)
    pending = None
    groups = []
    for line in native_log.splitlines():
        resource = parse_fact(line)
        if resource is not None:
            if pending is not None:
                raise BuffReplayError("BUFF_PRE_FACT_BOUNDARY_OVERLAP")
            pending = {"key": exact_key(resource), "values": {}}
            continue
        buff = parse_buff(line, expected)
        if buff is not None:
            if pending is None or exact_key(buff) != pending["key"]:
                raise BuffReplayError("BUFF_NOT_FROM_CURRENT_NATIVE_PRE_IF")
            if buff["symbol"] in pending["values"]:
                raise BuffReplayError("DUPLICATE_NATIVE_BUFF_AT_IF")
            pending["values"][buff["symbol"]] = buff["value"]
            continue
        attempt = get_native_attempt(line)
        if attempt is not None and pending is not None:
            if exact_key(attempt) != pending["key"]:
                raise BuffReplayError("NATIVE_BUFF_ATTEMPT_SOURCE_ROW_MISMATCH")
            if set(pending["values"]) != expected:
                raise BuffReplayError("NATIVE_BUFF_INVENTORY_FACT_INCOMPLETE")
            groups.append(pending)
            pending = None
    if pending is not None:
        raise BuffReplayError("UNMATCHED_BUFF_PRE_IF_AT_EOF")
    return groups


def compare_with_previous(trace, official, native_before, talents, buffs, scenario):
    """Recompute prior 210 source facts, then buff; fail on any regression."""
    previous = compare_legacy_talents(
        trace, official, native_before, talents, scenario)
    talent_rows = group_actual_pre_talents(trace, talents)
    buff_rows = group_actual_pre_buffs(trace, buffs)
    ledger = native_before["all_native_if_pre_fact_ledger"]
    if len(talent_rows) != len(buff_rows) or len(ledger) != len(buff_rows):
        raise BuffReplayError("REAL_SOURCE_IF_FACT_COHORT_LENGTH_CHANGED")
    counts = Counter()
    residuals = Counter()
    examples = []
    for i, (old, talent, buff) in enumerate(zip(ledger, talent_rows, buff_rows)):
        native_key = (old["at_ms"], old["source_list"],
                      old["source_index"] + 1, old["native_name"])
        if buff["key"] != native_key or talent["key"] != native_key:
            raise BuffReplayError("NATIVE_IF_ROW_FACT_IDENTITY_NOT_EXACT")
        rows = official["action_lists"][old["source_list"]]
        ir = rows[old["source_index"]]
        expr = ir["expression_fields"].get("if")
        if (not expr or ir["source_sha256"] != old["source_line_sha256"]
            or old["source_if"] != expr["source"]
            or old["source_if_symbols"] != expr["symbols"]):
            raise BuffReplayError("SOURCE_IF_PROVENANCE_MISMATCH")
        base = {**pre_facts(old), **talent["values"]}
        prior = independent_if(expr, base)
        expanded = {**base, **buff["values"]}
        new = independent_if(expr, expanded)
        if prior is not None:
            counts["prior_known"] += 1
            if new != prior:
                raise BuffReplayError("KNOWN_TALENT_AST_PROOF_REGRESSION")
        if new is None:
            counts["unknown"] += 1
            residuals.update(set(expr["symbols"]) - set(expanded))
            continue
        if new != old["native_if_result_verification_only"]:
            raise BuffReplayError(
                "SOURCE_BACKED_BUFF_AST_NATIVE_CONFLICT:" +
                scenario + ":" + old["source_list"] + ":" +
                str(old["source_index"]) + ":" + str(i))
        counts["matched"] += 1
        if prior is None:
            counts["new_by_buff"] += 1
            if len(examples) < 15:
                examples.append({
                    "source_list": old["source_list"],
                    "source_index": old["source_index"],
                    "at_ms": old["at_ms"],
                    "source_if": expr["source"],
                    "source_line_sha256": ir["source_sha256"],
                    "native_buff_pre_facts": buff["values"],
                    "independent_result": new,
                    "native_if_boolean_verification_only":
                        old["native_if_result_verification_only"],
                })
    if (counts["matched"] + counts["unknown"] != len(ledger)
        or counts["prior_known"] !=
            previous["counts"]["independently_matched"]
        or counts["matched"] - counts["prior_known"] != counts["new_by_buff"]):
        raise BuffReplayError("SOURCE_TALENT_BASELINE_OR_BUFF_COUNTS_CHANGED")
    return {
        "real_native_IF_count": len(ledger),
        "counts": dict(sorted(counts.items())),
        "remaining_unobserved_symbol_incidences": dict(sorted(residuals.items())),
        "new_independent_buff_examples": examples,
        "native_talent_baseline_counts": previous["counts"],
    }


def run(profile, sim_clock_source, one_dir, two_dir):
    verify_clock_source(sim_clock_source.read_bytes())
    ir = parse_profile(profile.read_bytes(), require_source=True,
                       expected_git_blob=PINNED_FURY_BLOB)
    talents, buffs = talent_inventory(ir), buff_inventory(ir)
    totals = Counter()
    cases = {}
    for name, root, targets in (("st", one_dir, 1),
                                ("two_target", two_dir, 2)):
        root = root.resolve(strict=True)
        old = verify_folder(root, targets, ir)
        raw_log = (root / "simc_native_log.txt").read_bytes()
        result = compare_with_previous(raw_log.decode("utf-8"), ir, old,
                                       talents, buffs, name)
        if result["real_native_IF_count"] != (255 if targets == 1 else 222):
            raise BuffReplayError("EXPECTED_NATIVE_IF_COHORT_CHANGED")
        cases[name] = {
            **result, "actual_native_log_sha256": sha(raw_log),
            "native_binary_sha256": old["native_binary_sha256"],
            "effective_APL_sha256": old["native_apl_sha256"],
        }
        totals.update(result["counts"])
    if cases["st"]["native_binary_sha256"] != cases["two_target"]["native_binary_sha256"]:
        raise BuffReplayError("NATIVE_BINARY_CHANGED_ACROSS_ST_TWO_TARGET")
    if totals["prior_known"] != 210:
        raise BuffReplayError("EXISTING_210_NATIVE_TALENT_PROOFS_NOT_PRESERVED")
    if totals["matched"] + totals["unknown"] != 477:
        raise BuffReplayError("NATIVE_477_COUNT_NOT_PRESERVED")
    return {
        "schema": SCHEMA, "scope_policy_id": POLICY,
        "status": "ACTUAL_NATIVE_BUFF_PRE_SOURCE_FACTS_AST_SUBSET_ONLY",
        "original_source_profile_git_blob": PINNED_FURY_BLOB,
        "source_derived_buff_symbols": buffs,
        "source_derived_talent_symbols": talents,
        "original_independent_IF_matches": 210,
        "additional_independent_buff_matched": totals["new_by_buff"],
        "independently_matched": totals["matched"],
        "remaining_IF_UNKNOWN": totals["unknown"],
        "native_IF_events": 477, "st": cases["st"], "two_target": cases["two_target"],
        "Native_IF_truth_used_as_AST_fact": False,
        "Native_ready_used_as_AST_fact": False,
        "same_timestamp_direct_native_PRE_observation_only": True,
        "independent_second_expression_oracle": False,
        "complete_General_Rotation_priority": False,
        "WCL_API_calls": 0, "MAIN_promotion": False,
    }


def selftest():
    symbols = ["buff.alpha.up", "buff.beta.stack"]
    good = "\n".join((
        "ZROT_NATIVE_IF_FACT_V1|10|default|1|foo|1|3|20|1",
        MARK + "10|default|1|foo|buff.alpha.up|1",
        MARK + "10|default|1|foo|buff.beta.stack|2",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|foo|1",
    ))
    groups = group_actual_pre_buffs(good, symbols)
    assert len(groups) == 1
    assert groups[0]["values"] == {
        "buff.alpha.up": 1.0, "buff.beta.stack": 2.0}
    bads = (
        good.replace("buff.alpha.up|1", "buff.alpha.up|NaN"),
        good.replace("buff.alpha.up|1", "buff.alpha.up|2"),
        good.replace("buff.beta.stack|2", "buff.beta.stack|2.5"),
        good.replace("buff.beta.stack|2", ""),
        good.replace("buff.beta.stack|2",
                     "buff.alpha.up|1\n" + MARK + "10|default|1|foo|buff.beta.stack|2"),
        good.replace("buff.alpha.up|1", "buff.invalid.up|1"),
        good.replace("buff.alpha.up|1", "buff.alpha.up|1").replace(
            "ZROT_NATIVE_SELECT_V1|ATTEMPT|10",
            "ZROT_NATIVE_SELECT_V1|ATTEMPT|11"),
    )
    for bad in bads:
        try: group_actual_pre_buffs(bad, symbols)
        except BuffReplayError: pass
        else: raise AssertionError("INVALID_NATIVE_BUFF_FACT_ACCEPTED")
    ir = parse_profile_for_test()
    expr = ir["action_lists"]["default"][0]["expression_fields"]["if"]
    assert independent_if(expr, {"rage": 20}) is None
    assert independent_if(expr, {"rage": 20, "buff.alpha.up": 1}) == 1
    return {"status": "PASS_OFFLINE_SYNTHETIC", "checks": 11,
            "Native_SimC": "NOT_RUN", "WCL_API_calls": 0,
            "native_IF_truth_as_operand": False}


def parse_profile_for_test():
    return parse_profile(
        b"actions=foo,if=buff.alpha.up&rage>10\n", require_source=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile", type=Path)
    p.add_argument("--official-sim-clock-source", type=Path)
    p.add_argument("--native-st-dir", type=Path)
    p.add_argument("--native-2t-dir", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    inputs = (a.official_profile, a.official_sim_clock_source,
              a.native_st_dir, a.native_2t_dir)
    if not any(inputs):
        data = selftest()
    elif all(inputs):
        data = run(*inputs)
    else:
        p.error("all four pinned source arguments required together")
    raw = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("xb") as f: f.write(raw)
        print("NATIVE_SOURCE_BUFF_PRE_AST_SHA256=" + sha(raw))
    else: print(raw.decode(), end="")


if __name__ == "__main__":
    main()
