#!/usr/bin/env python3
"""Source-stamped Native bare-resource expression eval vs Strict PRE audit.

A logged evaluation is never a PRE transition. Source-row attribution and
complete producer write coverage remain UNKNOWN; no readiness/rule promotion.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
import re
from pathlib import Path

from simc_native_epoch_sequence_audit import (
    parse_epoch_native_log, independent_epoch_audit, sha
)

MARK = "ZROT_NATIVE_APL_RESOURCE_EVAL_V1|"
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
REGEX = re.compile(
    r"ZROT_NATIVE_APL_RESOURCE_EVAL_V1\|(\d+)\|(-?\d+)\|(\d+)\|"
    r"(-?\d+)\|(\d+)\|(-?\d+)\|([a-z][a-z0-9_]*)\|(" + NUMBER + r")\s*$"
)
TRANSITIONS = {"GAIN", "LOSS", "INIT", "RECALC"}


def identity(row):
    return (row["thread"], row["iteration"], row["reset_boundary_sequence"],
            row["actor"], row["spawn"])


def audit(raw: bytes, expected_sha: str) -> dict:
    projected = parse_epoch_native_log(raw, expected_sha)
    proof = independent_epoch_audit(raw, projected)
    if proof["status"] != "PASS_EPOCH_NATIVE_SOURCE_BYTES_INDEPENDENT_RECALC":
        raise ValueError("NATIVE_EVAL_SOURCE_INDEPENDENCE_FAILED")

    events = projected["events"]
    reset = projected["reset_boundaries"]
    seen = {(row["thread"], row["sequence"]) for row in events + reset}
    evals = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        if MARK.encode() not in line:
            continue
        source = line.decode("utf-8")
        if source.count(MARK) != 1:
            raise ValueError("NATIVE_EVAL_DUPLICATED_MARKER")
        match = REGEX.search(source)
        if not match:
            raise ValueError("NATIVE_EVAL_UNPARSEABLE_MARKER")
        values = match.groups()
        thread, iteration, seq, t, actor, spawn = map(int, values[:6])
        value = float(values[7])
        if thread < 0 or seq < 0 or not math.isfinite(value):
            raise ValueError("NATIVE_EVAL_INVALID_SOURCE_VALUES")
        if (thread, seq) in seen:
            raise ValueError("NATIVE_EVAL_DUPLICATE_SOURCE_SEQUENCE")
        seen.add((thread, seq))
        matching_reset = [r["sequence"] for r in reset
                          if r["thread"] == thread and r["iteration"] == iteration
                          and r["sequence"] < seq]
        evals.append(dict(thread=thread, iteration=iteration, sequence=seq,
                          time_ms=t, actor=actor, spawn=spawn, resource=values[6],
                          value=value, source_log_line=line_number,
                          reset_boundary_sequence=max(matching_reset)
                          if matching_reset else None))

    selections = defaultdict(list)
    history = defaultdict(list)
    for item in events:
        key = identity(item)
        if item["kind"] in ("SELECT_BEGIN", "SELECT_END"):
            selections[key].append(item)
        elif item["kind"] in TRANSITIONS:
            history[(key, item["resource"])].append(item)
    windows = defaultdict(list)
    for key, rows in selections.items():
        current = None
        for item in sorted(rows, key=lambda r: r["sequence"]):
            if item["kind"] == "SELECT_BEGIN":
                if current:
                    raise ValueError("NATIVE_EVAL_OVERLAPPING_SELECTION")
                current = item
            else:
                if not current or current["sequence"] >= item["sequence"]:
                    raise ValueError("NATIVE_EVAL_ORPHAN_SELECTION_END")
                windows[key].append((current, item))
                current = None
        if current:
            raise ValueError("NATIVE_EVAL_ORPHAN_SELECTION_BEGIN")
    counts = Counter()
    examples = []
    in_window = 0
    for row in evals:
        key = identity(row)
        found = [(a,b) for a,b in windows.get(key, [])
                 if a["sequence"] < row["sequence"] < b["sequence"]]
        begin = None
        prev = None
        if row["reset_boundary_sequence"] is None:
            status = "UNKNOWN_MISSING_RESET"
        elif len(found) != 1:
            status = "UNKNOWN_NOT_IN_EXACT_SELECTION"
        else:
            begin, end = found[0]
            in_window += 1
            if row["time_ms"] != begin["time_ms"]:
                status = "UNKNOWN_EVAL_TIME_NOT_DECISION_TIME"
            else:
                source = history.get((key, row["resource"]), [])
                during = [x for x in source
                          if begin["sequence"] <= x["sequence"] < row["sequence"]]
                contradiction = [x for x in source if
                    (x["sequence"] < begin["sequence"] and
                     x["time_ms"] > begin["time_ms"]) or
                    (x["sequence"] >= begin["sequence"] and
                     x["time_ms"] < begin["time_ms"])]
                same = [x for x in source if
                        x["sequence"] < begin["sequence"]
                        and x["time_ms"] == begin["time_ms"]]
                eligible = [x for x in source if
                            x["sequence"] < begin["sequence"]
                            and x["time_ms"] < begin["time_ms"]]
                if contradiction:
                    status = "UNKNOWN_SOURCE_TIME_SEQUENCE_CONTRADICTION"
                elif during:
                    status = "UNKNOWN_WRITE_DURING_SELECTION"
                elif same:
                    status = "SAME_TIME_NOT_STRICT_PRE"
                elif not eligible:
                    status = "UNKNOWN_NO_EARLIER_SOURCE"
                else:
                    prev = max(eligible, key=lambda x:x["sequence"])
                    status = ("MATCH_PARTIAL_PRODUCER" if math.isclose(
                        row["value"], prev["current"],
                        rel_tol=1e-9, abs_tol=1e-7)
                        else "CONFLICT_POSSIBLE_UNOBSERVED_WRITE")
        counts[status] += 1
        if len(examples) < 25:
            examples.append(dict(status=status, resource=row["resource"],
                                 actual_eval=row["value"], eval_seq=row["sequence"],
                                 decision_seq=begin["sequence"] if begin else None,
                                 decision_ms=begin["time_ms"] if begin else None,
                                 previous_value=prev["current"] if prev else None,
                                 previous_ms=prev["time_ms"] if prev else None,
                                 reset_seq=row["reset_boundary_sequence"]))
    return dict(schema="ZrotNativeBareResourceRuntimeVsEpochStrictPreAuditV1",
                source_log_sha256=expected_sha, native_evaluation_count=len(evals),
                evaluations_inside_selection=in_window,
                evaluated_resource_counts=dict(sorted(Counter(e["resource"] for e in evals).items())),
                counts=dict(sorted(counts.items())), examples_max_25=examples,
                independent_epoch_raw_audit=proof["status"],
                source_row_identity="UNKNOWN",
                eval_used_as_strict_pre=False, diagnostic_used_as_pre=False,
                same_timestamp_is_pre=False, complete_producer_coverage=False,
                certified_operand_values=0, readiness="UNKNOWN",
                actual_native_action_parity="NOT_VALIDATED",
                gameplay_rule_promotion=False)


def selftest() -> None:
    def reset(seq): return f"ZROT_NATIVE_RESET_BOUNDARY_V1|0|0|{seq}|0\n".encode()
    def event(kind,seq,t,current=10):
        res = "rage" if kind in TRANSITIONS else "none"
        first = f"ZROT_NATIVE_EVENT_V2|{kind}|0|0|{seq}|{t}|0|1|{res}|{current if res!='none' else 0}|{100 if res!='none' else 0}\n"
        if kind in ("INIT","RECALC"):
            second=f"ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|{t}|0|1|rage|{current}|100|{kind}\n"
        elif kind in ("GAIN","LOSS"):
            second=f"ZROT_NATIVE_RESOURCE_V1|{t}|0|1|rage|{current}|5|{kind}\n"
        elif kind=="SELECT_BEGIN":
            second=f"ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|{t}|0|1\n"
        else:
            second=f"ZROT_NATIVE_SELECT_RESOURCE_END_V1|{t}|0|1|100\n"
        return (first + second).encode()
    def expression(seq,t,value):
        return f"ZROT_NATIVE_APL_RESOURCE_EVAL_V1|0|0|{seq}|{t}|0|1|rage|{value}\n".encode()
    def evaluate(raw): return audit(raw,sha(raw))["counts"]
    start=reset(0)+event("INIT",1,0)+event("SELECT_BEGIN",2,10)
    end=event("SELECT_END",4,10)
    assert evaluate(start+expression(3,10,10)+end)=={"MATCH_PARTIAL_PRODUCER":1}
    assert evaluate(start+expression(3,10,15)+end)=={"CONFLICT_POSSIBLE_UNOBSERVED_WRITE":1}
    assert evaluate(reset(0)+event("INIT",1,10)+event("SELECT_BEGIN",2,10)+
                    expression(3,10,10)+end)=={"SAME_TIME_NOT_STRICT_PRE":1}
    assert evaluate(start+expression(3,11,10)+end)=={"UNKNOWN_EVAL_TIME_NOT_DECISION_TIME":1}
    assert evaluate(start+event("GAIN",3,10)+expression(4,10,10)+
                    event("SELECT_END",5,10))=={"UNKNOWN_WRITE_DURING_SELECTION":1}
    assert evaluate(reset(0)+event("SELECT_BEGIN",1,10)+expression(2,10,10)+
                    event("SELECT_END",3,10))=={"UNKNOWN_NO_EARLIER_SOURCE":1}
    assert evaluate(start+event("SELECT_END",3,10)+expression(4,10,10))=={
        "UNKNOWN_NOT_IN_EXACT_SELECTION":1}
    for broken in (start+expression(2,10,10)+end,
                   start+expression(3,10,"nope")+end):
        try: evaluate(broken)
        except ValueError: pass
        else: raise AssertionError("SYNTHETIC_FALSE_EVIDENCE_ACCEPTED")
    try: audit(start+expression(3,10,10)+end, "0"*64)
    except ValueError: pass
    else: raise AssertionError("SOURCE_LOG_SHA_NOT_ENFORCED")
    print("SIMC_NATIVE_BARE_RESOURCE_EVAL_EPOCH_AUDIT_SELF_TEST=PASS SYNTHETIC_ONLY")


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--native-log",type=Path)
    p.add_argument("--log-sha256")
    a=p.parse_args()
    if a.self_test or not a.native_log:
        selftest()
    else:
        if not a.log_sha256:p.error("--log-sha256 required")
        print(json.dumps(audit(a.native_log.read_bytes(),a.log_sha256),
                         sort_keys=True,indent=2))


if __name__=="__main__":
    main()
