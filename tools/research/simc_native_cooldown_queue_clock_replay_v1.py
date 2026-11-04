#!/usr/bin/env python3
"""Independent numeric cooldown queue clock comparison at actual PRE attempts.

Cooldown up: raw ready_time <= current_time.
When down: an action/player-bound cooldown may queue when source-computed
queueable threshold <= current_time. Missing-bound cooldowns are NOT
queueable. Native is_ready() is used ONLY as post-computation comparator.
All timestamps are integer milliseconds; any comparison within 1 ms is
UNKNOWN, never rounded into false/true. Producer's queueable threshold
comes from original cooldown_t::queueable(), not independent tolerance
calculation, and this is NOT an independent full readiness oracle.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile
from simc_native_if_pre_operand_replay_v1 import (
    PINNED_FURY_BLOB, verify_folder, exact_key, get_native_attempt,
)
from simc_native_ready_guard_witness_instrument_v1 import (
    BASE_READY_MARK, BASE_ACTION_MARK,
)
from simc_native_ready_guard_witness_replay_v1 import (
    read_guard, read_method_entry, replay_log,
)
from simc_native_cooldown_queue_clock_instrument_v1 import MARK

SCHEMA = "ZrotNativeSourceClockQueueabilityIndependentComparatorV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"


class NumericQueueError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_clock(line):
    index = line.find(MARK)
    if index < 0:
        return None
    parts = line[index:].strip().split("|")
    if len(parts) != 9 or not parts[1].isdigit() or not parts[3].isdigit():
        raise NumericQueueError("CLOCK_SOURCE_LOG_SCHEMA_INVALID")
    try:
        ready_time, action_bound, player_bound, queueable_time = (
            int(x) for x in parts[5:]
        )
    except ValueError:
        raise NumericQueueError("RAW_COOLDOWN_CLOCK_NOT_INTEGER")
    if action_bound not in (0,1) or player_bound not in (0,1):
        raise NumericQueueError("RAW_COOLDOWN_BOUND_FLAGS_NOT_BOOLEAN")
    if (not action_bound or not player_bound) and queueable_time != 0:
        raise NumericQueueError("UNBOUND_COOLDOWN_HAS_QUEUE_THRESHOLD")
    if not parts[2] or not parts[4]:
        raise NumericQueueError("RAW_CLOCK_SOURCE_IDENTITY_MISSING")
    return {
        "time_ms":int(parts[1]),"list":parts[2],
        "ordinal":int(parts[3]),"native_name":parts[4],
        "cooldown_ready_ms":ready_time,
        "has_bound_action":action_bound,"has_bound_player":player_bound,
        "queueable_ms":queueable_time,
    }


def numeric_ready(clock):
    now = clock["time_ms"]
    ready = clock["cooldown_ready_ms"]
    if abs(ready-now) <= 1:
        return None, "UNKNOWN_READY_CLOCK_BOUNDARY_WITHIN_1MS"
    if ready < now:
        return 1, "READY_TIME_PASSED"
    if not clock["has_bound_action"] or not clock["has_bound_player"]:
        return 0, "UNBOUND_COOLDOWN_NOT_QUEUEABLE"
    queueable = clock["queueable_ms"]
    if abs(queueable-now) <= 1:
        return None, "UNKNOWN_QUEUE_CLOCK_BOUNDARY_WITHIN_1MS"
    return (
        (1, "ACTION_BOUND_QUEUE_WINDOW_REACHED") if queueable < now
        else (0, "COOLDOWN_QUEUE_WINDOW_NOT_REACHED")
    )


def replay_clock_log(trace, ir):
    pending = None
    counts=Counter()
    reason_counts=Counter()
    source_negative=Counter()
    discrepancies=[]
    examples=[]
    for line in trace.splitlines():
        guard=read_guard(line)
        if guard is not None:
            if pending is not None:
                raise NumericQueueError("OVERLAPPING_ACTUAL_ATTEMPT")
            pending={"guard":guard, "clock":None,"base_action_entries":0,
                     "base_ready_entries":0}
            continue
        clock=read_clock(line)
        if clock is not None:
            if pending is None or pending["clock"] is not None:
                raise NumericQueueError("ORPHAN_OR_DUPLICATE_RAW_CLOCK")
            if exact_key(clock)!=exact_key(pending["guard"]):
                raise NumericQueueError("NUMERIC_QUEUE_PRE_SOURCE_POINTER_MISMATCH")
            pending["clock"]=clock
            continue
        for mark,prop in ((BASE_ACTION_MARK,"base_action_entries"),
                          (BASE_READY_MARK,"base_ready_entries")):
            entry=read_method_entry(line,mark)
            if entry is not None:
                if pending is not None and (
                    entry==(pending["guard"]["time_ms"],pending["guard"]["native_name"])):
                    pending[prop]+=1
                break
        else:
            native=get_native_attempt(line)
            if native is None:
                continue
            if pending is None or pending["clock"] is None:
                raise NumericQueueError("NATIVE_ATTEMPT_MISSING_NUMERIC_CLOCK_PRE")
            guard=pending["guard"]
            clock=pending["clock"]
            if exact_key(native)!=exact_key(clock):
                raise NumericQueueError("NATIVE_ATTEMPT_CLOCK_SOURCE_PROVENANCE_CHANGED")
            if (guard["list"] not in ir["action_lists"] or
                not 0<=guard["ordinal"]-1<len(ir["action_lists"][guard["list"]])):
                raise NumericQueueError("UNPINNED_ACTION_READY_SOURCE_POINTER")
            result,reason=numeric_ready(clock)
            counts["actual_attempts"]+=1
            reason_counts[reason]+=1
            if result is None:
                counts["unknown_numeric_clock"]+=1
            else:
                counts["numeric_clock_decidable"]+=1
                # Native cooldown_t::is_ready was sampled PRE earlier,
                # but does not contribute to the arithmetic decision.
                if result!=guard["cooldown_queueable"]:
                    discrepancies.append({
                        "source_key":exact_key(native),"computed":result,
                        "native_is_ready_PRE_comparator":guard["cooldown_queueable"],
                    })
                    raise NumericQueueError("INDEPENDENT_QUEUE_CLOCK_NATIVE_GUARD_CONFLICT")
                counts["numeric_clock_vs_native_cooldown_guard_matched"]+=1
                if (result==0 and pending["base_action_entries"]==1
                    and pending["base_ready_entries"]==1):
                    if native["ready"] != 0:
                        raise NumericQueueError(
                            "NUMERIC_QUEUE_NEGATIVE_BUT_NATIVE_ACTION_READY_TRUE")
                    counts["numeric_clock_proved_base_failure"]+=1
                    source_negative[reason]+=1
                    if len(examples)<12:
                        examples.append({
                            "source_list":guard["list"],"source_ordinal":guard["ordinal"],
                            "native_action":guard["native_name"],"at_ms":guard["time_ms"],
                            "raw_clock":clock,
                            "comparison_reason":reason,
                            "observed_native_action_ready_POST_ONLY":native["ready"],
                        })
            pending=None
    if pending is not None or not counts["actual_attempts"]:
        raise NumericQueueError("ORPHAN_LAST_CLOCK_OR_EMPTY_LOG")
    if (counts["numeric_clock_decidable"]+counts["unknown_numeric_clock"] !=
        counts["actual_attempts"] or
        counts["numeric_clock_vs_native_cooldown_guard_matched"] !=
        counts["numeric_clock_decidable"]):
        raise NumericQueueError("NUMERIC_CLOCK_ACCOUNTING_FAILED")
    return {
        "counts":dict(sorted(counts.items())),
        "source_numeric_reason_counts":dict(sorted(reason_counts.items())),
        "independent_queue_based_negative_guard_reasons":dict(sorted(source_negative.items())),
        "numeric_clock_proven_base_negative_samples":examples,
        "compare_only_native_cooldown_is_ready":True,
        "compare_only_native_action_ready":True,
        "independent_queueable_time_math":False,
        "independent_queueability_boolean_from_source_clocks":True,
        "full_native_ready_independently_proven":False,
    }


def run(profile, st, two, move_st, move_two):
    ir=parse_profile(profile.read_bytes(),require_source=True,
                     expected_git_blob=PINNED_FURY_BLOB)
    cases={}
    counts=Counter()
    for label,location,targets,expected in (
        ("stationary_st",st,1,1542),
        ("stationary_two_target",two,2,1030),
        ("moving_st",move_st,1,1650),
        ("moving_two_target",move_two,2,1186),
    ):
        location=location.resolve(strict=True)
        native=verify_folder(location,targets,ir)
        raw=(location/"simc_native_log.txt").read_bytes()
        replay=replay_clock_log(raw.decode(),ir)
        previous=replay_log(raw.decode(),ir)
        n=replay["counts"]["actual_attempts"]
        if (n!=expected or
            n!=previous["counts"]["native_ATTEMPT_records"] or
            n!=native["counts"]["all_native_action_ready_attempts"]):
            raise NumericQueueError("PRE_EXISTING_NATIVE_READY_ATTEMPTS_NOT_REPRODUCED")
        for field,value in replay["counts"].items():
            counts[field]+=value
        cases[label]={
            **replay,
            "prior_source_guard_negative_witnesses":
                previous["counts"].get("PROVEN_BASE_GUARD_NOT_READY",0),
            "native_binary_sha256":native["native_binary_sha256"],
            "native_log_sha256":sha(raw),
        }
    if len({v["native_binary_sha256"] for v in cases.values()}) != 1:
        raise NumericQueueError("NATIVE_BINARY_NOT_IDENTICAL_ACROSS_SCENARIOS")
    if counts["actual_attempts"]!=5408:
        raise NumericQueueError("ACTUAL_COHORT_SIZE_CHANGED")
    return {
        "schema":SCHEMA,
        "scope_policy_id":POLICY,
        "status":"SOURCE_CLOCK_COOLDOWN_QUEUEABILITY_PARTIAL_INDEPENDENT",
        "source_clock_based_counts":dict(sorted(counts.items())),
        "four_cases":cases,
        "single_official_fury_apl_blob":PINNED_FURY_BLOB,
        "clock_resolution": "integer_milliseconds",
        "boundary_policy":"WITHIN_1MS_UNKNOWN",
        "source_cooldown_ready_and_queueable_clocks_read_before_original":True,
        "native_cooldown_is_ready_not_used_as_calculation_input":True,
        "native_action_ready_not_used_as_calculation_input":True,
        "queueable_threshold_source_method_not_independently_rebuilt":True,
        "full_independent_readiness":False,
        "full_source_order_action_choice":False,
        "General_Rotation_complete":False,
        "MAIN_promoted":False,
        "WCL_API_calls":0,
    }


def selftest():
    sample=(
        MARK+"100|default|1|foo|300|1|1|80"
    )
    v=read_clock(sample)
    assert v["time_ms"]==100 and v["cooldown_ready_ms"]==300
    assert numeric_ready(v)==(1,"ACTION_BOUND_QUEUE_WINDOW_REACHED")
    v["queueable_ms"]=150
    assert numeric_ready(v)==(0,"COOLDOWN_QUEUE_WINDOW_NOT_REACHED")
    v["queueable_ms"]=100
    assert numeric_ready(v)[0] is None
    v["has_bound_action"]=0
    v["queueable_ms"]=0
    assert numeric_ready(v)==(0,"UNBOUND_COOLDOWN_NOT_QUEUEABLE")
    v["cooldown_ready_ms"]=99
    assert numeric_ready(v)[0] is None
    v["cooldown_ready_ms"]=50
    assert numeric_ready(v)==(1,"READY_TIME_PASSED")
    v["cooldown_ready_ms"]=300
    bad=[MARK+"100|default|1|foo|300|2|1|80",MARK+"100|default|1|foo|300|0|1|80"]
    for line in bad:
        try:read_clock(line)
        except NumericQueueError:pass
        else:raise AssertionError("INVALID_CLOCK_SOURCE_ACCEPTED")
    ir=parse_profile(b"actions=foo\n",require_source=False)
    raw="\n".join([
        "ZROT_NATIVE_READY_GUARDS_PRE_V1|100|default|1|foo|0|1|0|-1|-1",
        MARK+"100|default|1|foo|300|1|1|150",
        "ZROT_NATIVE_BASE_ACTION_READY_ENTER_V1|100|foo",
        "ZROT_NATIVE_BASE_READY_ENTER_V1|100|foo",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|100|default|default|1|foo|0",
    ])
    out=replay_clock_log(raw,ir)
    assert out["counts"]["numeric_clock_proved_base_failure"]==1
    assert out["counts"]["numeric_clock_vs_native_cooldown_guard_matched"]==1
    for malformed in (
        raw.replace("|foo|0|1|0|-1|-1","|foo|1|1|0|-1|-1"),
        raw.replace("|foo|300|1|1|150","|foo|300|1|1|80"),
        raw.replace("|foo|300|1|1|150","|foo|300|1|1|150\n"+MARK+"100|default|1|foo|300|1|1|150"),
    ):
        try:replay_clock_log(malformed,ir)
        except NumericQueueError:pass
        else:raise AssertionError("MISMATCHED_CLOCK_COOLDOWN_OR_DUPLICATE_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":15,
            "WCL_API_calls":0,"real_native_executed":False,
            "full_readiness_proven":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--native-st-dir",type=Path)
    p.add_argument("--native-2t-dir",type=Path)
    p.add_argument("--native-moving-st-dir",type=Path)
    p.add_argument("--native-moving-2t-dir",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    paths=(a.official_profile,a.native_st_dir,a.native_2t_dir,
           a.native_moving_st_dir,a.native_moving_2t_dir)
    if not any(paths):
        result=selftest()
    elif all(paths):
        result=run(*paths)
    else:p.error("all pinned Native source paths required together")
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
        print("NUMERIC_COOLDOWN_QUEUE_CLOCK_SHA256="+sha(raw))
    else:print(raw.decode(),end="")


if __name__=="__main__":
    main()
