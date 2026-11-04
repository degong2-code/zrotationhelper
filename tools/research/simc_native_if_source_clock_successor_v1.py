#!/usr/bin/env python3
"""Provenance-limited clock operand replay of 477 pinned Native PRE-IF facts.

Reuse the verified Rage/active_enemies AST and receipt; add only time,
whose SimC meaning is source-pinned to event_mgr.current_time. Do not
treat Native IF truth, ready(), or missing buff/talent/variable as inputs.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from simc_apl_semantic_ir_v2 import Expression, parse_profile, evaluate_ast, truth
from simc_native_if_ledger_offline_replay_v1 import (
    reevaluate as baseline_replay, PINNED_NATIVE_FACT_RECEIPT_SHA256,
    PINNED_PROFILE_BLOB, POLICY,
)

SCHEMA = "ZrotNativePreIfSourceClockSuccessorV1"
SIMC = "b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
CLOCK_BLOB = "ae5c258953787196e0aecad58814ff14d4cd2bed"
CLOCK_SITE = (b'if ( name_str == "time" )\n'
              b'    return make_ref_expr( name_str, event_mgr.current_time );')
PROVEN = frozenset(("rage", "active_enemies", "time"))
BASELINE_KNOWN = frozenset((
    "MATCH_AST_FROM_PRE_OPERANDS", "MATCH_AST_DETERMINATE_WITH_MISSING_SYMBOLS",
))


class ClockEvidenceError(ValueError):
    pass


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def git_blob(blob):
    return hashlib.sha1(b"blob " + str(len(blob)).encode() + b"\0" + blob).hexdigest()


def verify_clock_source(blob):
    if git_blob(blob) != CLOCK_BLOB or blob.count(CLOCK_SITE) != 1:
        raise ClockEvidenceError("OFFICIAL_SIMC_TIME_BINDING_NOT_VERIFIED")


def pre_facts(row):
    t, r, enemies = (
        row["at_ms"], row["pre_primary_resource_value"], row["pre_active_enemies"])
    if type(t) is not int or not -3600000 <= t <= 86400000:
        raise ClockEvidenceError("INVALID_PRE_IF_TIME")
    if type(r) not in (float, int) or not math.isfinite(r):
        raise ClockEvidenceError("INVALID_PRE_IF_RESOURCE")
    if type(enemies) is not int or not 0 <= enemies <= 10000:
        raise ClockEvidenceError("INVALID_PRE_IF_TARGET_COUNT")
    return {"rage": r, "active_enemies": enemies, "time": t / 1000.0}


def independent(expr, facts):
    value = truth(evaluate_ast(expr["ast"], facts))
    return None if value is None else int(bool(value))


def replay(profile, receipt):
    base = baseline_replay(profile, receipt)
    if (base["known_native_IF_checks_correctly_recomputed"] != 66 or
        base["IF_checks_with_unverified_other_operands"] != 411):
        raise ClockEvidenceError("PINNED_BASELINE_66_411_CHANGED")
    counts = Counter()
    missing = Counter()
    new_by_expr = Counter()
    per = {}
    sample = []
    for label, expected in (("st", 255), ("two_target", 222)):
        ledger = receipt[label]["all_native_if_pre_fact_ledger"]
        if len(ledger) != expected:
            raise ClockEvidenceError("PINNED_IF_LEDGER_LENGTH_CHANGED")
        local = Counter()
        for rec in ledger:
            name, idx = rec["source_list"], rec["source_index"]
            rows = profile["action_lists"].get(name)
            if rows is None or type(idx) is not int or not 0 <= idx < len(rows):
                raise ClockEvidenceError("MISSING_SOURCE_APL_ROW")
            row = rows[idx]
            expr = row["expression_fields"].get("if")
            if (not expr or row["source_sha256"] != rec["source_line_sha256"]
                or rec["source_if"] != expr["source"]
                or rec["source_if_symbols"] != expr["symbols"]):
                raise ClockEvidenceError("SOURCE_IF_IDENTITY_CHANGED")
            facts = pre_facts(rec)
            value = independent(expr, facts)
            known_before = rec["derived_AST_status"] in BASELINE_KNOWN
            if value is None:
                if known_before:
                    raise ClockEvidenceError("LOST_EXISTING_PROOF")
                local["unknown"] += 1
                missing.update(set(expr["symbols"]) - PROVEN)
                continue
            # Native truth is a comparator AFTER the independent AST result.
            if value != rec["native_if_result_verification_only"]:
                raise ClockEvidenceError("CLOCK_AST_VS_NATIVE_IF_CONFLICT:" +
                                         label + ":" + name + ":" + str(idx))
            local["matched"] += 1
            if known_before:
                local["legacy_matched"] += 1
            else:
                local["new_matches"] += 1
                new_by_expr[expr["source"]] += 1
                if len(sample) < 12:
                    sample.append({"scenario": label, "source_list": name,
                                   "source_index": idx, "source_if": expr["source"],
                                   "time_seconds": facts["time"],
                                   "source_sha256": row["source_sha256"],
                                   "independent_bool": value,
                                   "native_bool_comparison_only":
                                       rec["native_if_result_verification_only"]})
        if local["matched"] + local["unknown"] != expected:
            raise ClockEvidenceError("SCENARIO_COUNTS_CHANGED")
        per[label] = dict(sorted(local.items()))
        counts.update(local)
    if counts["legacy_matched"] != 66 or counts["matched"] + counts["unknown"] != 477:
        raise ClockEvidenceError("BASELINE_NOT_PRESERVED")
    return {
        "schema": SCHEMA, "policy": POLICY, "simc_commit": SIMC,
        "fury_profile_git_blob": PINNED_PROFILE_BLOB,
        "sim_clock_git_blob": CLOCK_BLOB,
        "time_source": "sim_t::create_expression(time) -> event_mgr.current_time",
        "time_value": "pre-existing Native IF evaluation timestamp at_ms / 1000",
        "not_a_WCL_Strict_PRE_transition": True,
        "baseline_known": 66, "additional_known": counts["new_matches"],
        "independently_known": counts["matched"], "unknown": counts["unknown"],
        "native_if_evaluations": 477,
        "scenarios": per, "unbound_operand_incidence": dict(sorted(missing.items())),
        "newly_decidable_expressions": dict(sorted(new_by_expr.items())),
        "newly_decidable_samples": sample,
        "supported_symbols": sorted(PROVEN),
        "native_if_boolean_as_operand": False,
        "native_ready_boolean_as_operand": False,
        "second_independent_AST_oracle": False,
        "native_simc_rerun": False, "WCL_API_calls": 0,
        "action_ready_and_selection_parity": "UNKNOWN",
        "General_Rotation_complete": False, "MAIN_promotion": False,
    }


def selftest():
    def decide(expression, timestamp):
        row = {"at_ms": timestamp, "pre_primary_resource_value": 30.0,
               "pre_active_enemies": 2, "native_if_result_verification_only": 0}
        return independent({"ast": Expression(expression).parse()}, pre_facts(row))
    assert decide("time<=0.5|buff.unknown.up", 0) == 1
    assert decide("time<=0.5|buff.unknown.up", 1000) is None
    assert decide("time>0.5&buff.unknown.up", 0) == 0
    assert decide("time>0.5&buff.unknown.up", 1000) is None
    assert decide("rage>=30&active_enemies=2", 1000) == 1
    assert decide("buff.unknown.up", 0) is None
    base = {"at_ms": 0, "pre_primary_resource_value": 10.0,
            "pre_active_enemies": 1, "native_if_result_verification_only": 0}
    assert pre_facts(base) == pre_facts({
        **base, "native_if_result_verification_only": 1,
        "native_ready_verification_only": 1})
    for bad in ({**base, "at_ms": True},
                {**base, "pre_primary_resource_value": float("nan")},
                {**base, "pre_active_enemies": -1}):
        try:
            pre_facts(bad)
        except ClockEvidenceError:
            pass
        else:
            raise AssertionError("INVALID_FACT_ACCEPTED")
    try:
        verify_clock_source(b"not the pinned source")
    except ClockEvidenceError:
        pass
    else:
        raise AssertionError("UNVERIFIED_SOURCE_ACCEPTED")
    return {"status": "PASS_OFFLINE_SYNTHETIC", "checks": 11,
            "native_simc_rerun": False, "WCL_API_calls": 0,
            "second_independent_AST_oracle": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile", type=Path)
    p.add_argument("--official-sim-clock-source", type=Path)
    p.add_argument("--native-pre-fact-receipt", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    fields = (a.official_profile, a.official_sim_clock_source,
              a.native_pre_fact_receipt)
    if not any(fields):
        result = selftest()
    elif all(fields):
        verify_clock_source(a.official_sim_clock_source.read_bytes())
        source_bytes = a.native_pre_fact_receipt.read_bytes()
        if sha(source_bytes) != PINNED_NATIVE_FACT_RECEIPT_SHA256:
            raise ClockEvidenceError("PINNED_NATIVE_FACT_RECEIPT_CHANGED")
        profile = parse_profile(a.official_profile.read_bytes(),
                                require_source=True,
                                expected_git_blob=PINNED_PROFILE_BLOB)
        result = replay(profile, json.loads(source_bytes))
    else:
        p.error("three pinned inputs together, or none for self-test")
    result_bytes = (json.dumps(result, sort_keys=True,
                               separators=(",", ":")) + "\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("xb") as f:
            f.write(result_bytes)
        print("SOURCE_CLOCK_SUCCESSOR_SHA256=" + sha(result_bytes))
    else:
        print(result_bytes.decode(), end="")


if __name__ == "__main__":
    main()
