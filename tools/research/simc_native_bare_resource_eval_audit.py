#!/usr/bin/env python3
"""Compare actual Native bare-resource ref evaluations to epoch-bound Strict PRE.

A matched predecessor is a PARTIAL PRODUCER observation, not certified state.
The eval marker itself is NEVER a PRE transition; decision is SELECT_BEGIN.
A logged expression is not independently attributed to an APL source row.
No readiness, priority, gameplay authority or WCL claim is made.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import re
from pathlib import Path

from simc_native_epoch_sequence_audit import (
    parse_epoch_native_log, independent_epoch_audit, sha,
)

MARK = "ZROT_NATIVE_APL_RESOURCE_EVAL_V1|"
NUMBER = r"[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][-+]?\\d+)?"
REGEX = re.compile(
    r"ZROT_NATIVE_APL_RESOURCE_EVAL_V1\\|(\\d+)\\|(-?\\d+)\\|(\\d+)\\|"
    r"(-?\\d+)\\|(\\d+)\\|(-?\\d+)\\|([a-z][a-z0-9_]*)\\|(" + NUMBER + r")\\s*$"
)
PRODUCERS = frozenset(("GAIN", "LOSS", "INIT", "RECALC"))
SCHEMA = "ZrotNativeBareResourceRuntimeVsEpochStrictPreAuditV1"


def _identity(e: dict) -> tuple:
    return (e["thread"], e["iteration"], e["reset_boundary_sequence"],
            e["actor"], e["spawn"])


def _parse_evaluations(raw: bytes, projection: dict) -> list[dict]:
    # Independently re-check raw marker bytes instead of trusting a producer
    # summary or the selected-action diagnostic values.
    evaluations = []
    seen = {(x["thread"], x["sequence"]) for x in
            projection["events"] + projection["reset_boundaries"]}
    for line_index, line in enumerate(raw.splitlines(), 1):
        if MARK.encode() not in line:
            continue
        s = line.decode("utf-8")
        if s.count(MARK) != 1:
            raise ValueError("EVAL_DUPLICATED_RAW_MARKER")
        matched = REGEX.search(s)
        if matched is None:
            raise ValueError("EVAL_RAW_MARKER_FORMAT")
        thread, iteration, seq, t, actor, spawn, resource, value = matched.groups()
        thread, iteration, seq, t, actor, spawn = map(
            int, (thread, iteration, seq, t, actor, spawn))
        value = float(value)
        if not math.isfinite(value) or not (0 <= thread and 0 <= seq):
            raise ValueError("EVAL_NONFINITE_OR_INVALID_SEQUENCE")
        if (thread, seq) in seen:
            raise ValueError("EVAL_SOURCE_SEQUENCE_COLLISION")
        seen.add((thread, seq))
        reset = [x["sequence"] for x in projection["reset_boundaries"]
                 if x["thread"] == thread and x["iteration"] == iteration
                 and x["sequence"] < seq]
        evaluations.append({
            "thread": thread, "iteration": iteration, "sequence": seq,
            "time_ms": t, "actor": actor, "spawn": spawn,
            "resource": resource, "value": value, "source_log_line": line_index,
            "reset_boundary_sequence": max(reset) if reset else None,
        })
    return evaluations


def audit(raw: bytes, expected_sha256: str) -> dict:
    # Uses the existing independent epoch source-byte validator; its
    # projection does not contain these new expression-evaluation markers.
    projection = parse_epoch_native_log(raw, expected_sha256)
    independent = independent_epoch_audit(raw, projection)
    if independent["status"] != "PASS_EPOCH_NATIVE_SOURCE_BYTES_INDEPENDENT_RECALC":
        raise ValueError("EVAL_EPOCH_INDEPENDENT_AUDIT_FAILED")
    evals = _parse_evaluations(raw, projection)
    event_groups = defaultdict(list)
    history = defaultdict(list)
    for event in projection["events"]:
        if event["kind"] in ("SELECT_BEGIN", "SELECT_END"):
            event_groups[_identity(event)].append(event)
        if event["kind"] in PRODUCERS:
            history[(_identity(event), event["resource"])].append(event)
    for rows in event_groups.values():
        rows.sort(key=lambda e: e["sequence"])
    for rows in history.values():
        rows.sort(key=lambda e: e["sequence"])

    # Link selection BEGIN/END from source identity and counter, never
    # from print order, diagnostic value or timestamp alone.
    windows = defaultdict(list)
    for identity, events in event_groups.items():
        begin = None
        for event in events:
            if event["kind"] == "SELECT_BEGIN":
                if begin is not None:
                    raise ValueError("EVAL_OVERLAPPING_NATIVE_SELECTION")
                begin = event
            else:
                if begin is None or begin["sequence"] >= event["sequence"]:
                    raise ValueError("EVAL_UNPAIRED_NATIVE_SELECTION_END")
                windows[identity].append((begin, event))
                begin = None
        if begin is not None:
            raise ValueError("EVAL_UNPAIRED_NATIVE_SELECTION_BEGIN")

    counts = Counter()
    examples = []
    within = 0
    for item in evals:
        identity = _identity(item)
        relevant = [(b, e) for b, e in windows.get(identity, ())
                    if b["sequence"] < item["sequence"] < e["sequence"]]
        predecessor = None
        begin = None
        if item["reset_boundary_sequence"] is None:
            status = "UNKNOWN_NO_SOURCE_RESET_EPOCH"
        elif len(relevant) != 1:
            status = "UNKNOWN_OUTSIDE_EXACT_SELECTION_WINDOW"
        else:
            begin, end = relevant[0]
            within += 1
            if item["time_ms"] != begin["time_ms"]:
                status = "UNKNOWN_EVAL_NOT_AT_DECISION_TIMESTAMP"
            else:
                rows = history.get((identity, item["resource"]), ())
                # Any resource write at/after selection start and before
                # the eval means this was not an unchanged PRE state.
                during = [x for x in rows if begin["sequence"] <= x["sequence"] <
                          item["sequence"]]
                # All source mutations must respect the sequence/time ordering
                # of the same epoch; future lines cannot backdate PRE.
                contradictory = [x for x in rows if
                    (x["sequence"] < begin["sequence"] and
                     x["time_ms"] > begin["time_ms"]) or
                    (x["sequence"] >= begin["sequence"] and
                     x["time_ms"] < begin["time_ms"])]
                same = [x for x in rows if
                        x["sequence"] < begin["sequence"] and
                        x["time_ms"] == begin["time_ms"]]
                eligible = [x for x in rows if
                            x["sequence"] < begin["sequence"] and
                            x["time_ms"] < begin["time_ms"]]
                if contradictory:
                    status = "UNKNOWN_SEQUENCE_TIMESTAMP_CONTRADICTION"
                elif during:
                    status = "UNKNOWN_SOURCE_WRITE_DURING_SELECTION"
                elif same:
                    status = "SAME_TIMESTAMP_EXCLUDED_NOT_STRICT_PRE"
                elif not eligible:
                    status = "UNKNOWN_NO_STRICTLY_PRIOR_PRODUCER"
                else:
                    predecessor = eligible[-1]
                    if math.isclose(item["value"], predecessor["current"],
                                    abs_tol=1e-7, rel_tol=1e-9):
                        status = "MATCH_OBSERVED_PRE_PARTIAL_PRODUCER"
                    else:
                        status = "CONFLICT_POSSIBLE_MISSING_PRODUCER_WRITE"
        counts[status] += 1
        if len(examples) < 25:
            examples.append({
                "status": status, "expression_resource": item["resource"],
                "actual_evaluated_value": item["value"],
                "source_eval_sequence": item["sequence"],
                "source_eval_time_ms": item["time_ms"],
                "selection_begin_sequence": begin["sequence"] if begin else None,
                "selection_begin_time_ms": begin["time_ms"] if begin else None,
                "previous_source_value": predecessor["current"] if predecessor else None,
                "previous_source_time_ms": predecessor["time_ms"] if predecessor else None,
                "reset_sequence": item["reset_boundary_sequence"],
                "actor_spawn": [item["actor"], item["spawn"]],
            })
    return {
        "schema": SCHEMA,
        "source_log_sha256": expected_sha256,
        "upstream_epoch_independent_recalculation": independent["status"],
        "native_evaluation_count": len(evals),
        "evaluations_inside_exact_selection_window": within,
        "counts": dict(sorted(counts.items())),
        "examples_max_25": examples,
        "runtime_expression_source_row_identity": "UNKNOWN_NOT_BOUND_TO_APL_SOURCE_ROW",
        "same_time_source_is_strict_pre": False,
        "evaluated_value_inserted_as_strict_pre": False,
        "native_diagnostic_snapshot_used_as_pre": False,
        "full_producer_write_coverage_verified": False,
        "certified_strict_pre_operand_count": 0,
        "action_readiness": "UNKNOWN",
        "native_action_parity": "NOT_VALIDATED",
        "gameplay_rule_promotion": False,
    }


def selftest() -> None:
    def reset(seq: int, it: int = 0) -> bytes:
        return f"ZROT_NATIVE_RESET_BOUNDARY_V1|0|{it}|{seq}|0\\n".encode()
    def event(kind: str, seq: int, t: int, cur: float = 10,
              it: int = 0) -> bytes:
        resource = "rage" if kind in PRODUCERS else "none"
        a = (f"ZROT_NATIVE_EVENT_V2|{kind}|0|{it}|{seq}|{t}|0|1|"
             f"{resource}|{cur if resource != 'none' else 0}|"
             f"{100 if resource != 'none' else 0}\\n")
        if kind in ("GAIN", "LOSS"):
            b = f"ZROT_NATIVE_RESOURCE_V1|{t}|0|1|rage|{cur}|5|{kind}\\n"
        elif kind in ("INIT", "RECALC"):
            b = f"ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|{t}|0|1|rage|{cur}|100|{kind}\\n"
        elif kind == "SELECT_BEGIN":
            b = f"ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|{t}|0|1\\n"
        else:
            b = f"ZROT_NATIVE_SELECT_RESOURCE_END_V1|{t}|0|1|100\\n"
        return (a + b).encode()
    def ev(seq: int, t: int, val: float) -> bytes:
        return (f"ZROT_NATIVE_APL_RESOURCE_EVAL_V1|0|0|{seq}|{t}|0|1|rage|{val}\\n").encode()
    def run(raw: bytes) -> dict:
        return audit(raw, sha(raw))
    base = reset(0) + event("INIT", 1, 0) + event("SELECT_BEGIN", 2, 10)
    success = base + ev(3, 10, 10) + event("SELECT_END", 4, 10)
    out = run(success)
    assert out["counts"] == {"MATCH_OBSERVED_PRE_PARTIAL_PRODUCER": 1}, out
    assert not out["evaluated_value_inserted_as_strict_pre"]
    assert out["certified_strict_pre_operand_count"] == 0
    conflict = base + ev(3, 10, 17) + event("SELECT_END", 4, 10)
    assert run(conflict)["counts"] == {"CONFLICT_POSSIBLE_MISSING_PRODUCER_WRITE": 1}
    same = reset(0) + event("INIT", 1, 10) + event("SELECT_BEGIN", 2, 10)
    same += ev(3, 10, 10) + event("SELECT_END", 4, 10)
    assert run(same)["counts"] == {"SAME_TIMESTAMP_EXCLUDED_NOT_STRICT_PRE": 1}
    after = base + ev(3, 11, 10) + event("SELECT_END", 4, 10)
    assert run(after)["counts"] == {"UNKNOWN_EVAL_NOT_AT_DECISION_TIMESTAMP": 1}
    during = base + event("GAIN", 3, 10, 11) + ev(4, 10, 11) + event("SELECT_END", 5, 10)
    assert run(during)["counts"] == {"UNKNOWN_SOURCE_WRITE_DURING_SELECTION": 1}
    missing = reset(0) + event("SELECT_BEGIN", 1, 10)
    missing += ev(2, 10, 10) + event("SELECT_END", 3, 10)
    assert run(missing)["counts"] == {"UNKNOWN_NO_STRICTLY_PRIOR_PRODUCER": 1}
    outside = base + event("SELECT_END", 3, 10) + ev(4, 10, 10)
    assert run(outside)["counts"] == {"UNKNOWN_OUTSIDE_EXACT_SELECTION_WINDOW": 1}
    duplicate = base + ev(2, 10, 10) + event("SELECT_END", 4, 10)
    for bad in (duplicate, success.replace(b"|rage|10\\n", b"|rage|not-a-number\\n")):
        try:
            run(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("EVAL_FAKE_NATIVE_EVENT_ACCEPTED")
    try:
        audit(success, "0" * 64)
    except ValueError:
        pass
    else:
        raise AssertionError("EVAL_LOG_SHA_NOT_CHECKED")
    print("SIMC_NATIVE_BARE_RESOURCE_EVAL_EPOCH_AUDIT_SELF_TEST=PASS SYNTHETIC_ONLY")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--native-log", type=Path)
    p.add_argument("--log-sha256")
    args = p.parse_args()
    if args.self_test or args.native_log is None:
        selftest()
    else:
        if not args.log_sha256:
            p.error("--log-sha256 required")
        print(json.dumps(audit(args.native_log.read_bytes(), args.log_sha256),
                         indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
