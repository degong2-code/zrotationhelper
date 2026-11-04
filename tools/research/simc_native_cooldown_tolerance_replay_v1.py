#!/usr/bin/env python3
"""Independent exact-millisecond cooldown queue threshold from raw PRE.

Given source state (ready, raw actor override, sim default, bound flags,
current sim time), independently reconstruct both selected tolerance and
queueable time, and derive cooldown_t::is_ready() with exact integer <=.
Native cooldown_t::queueable(), previous source is_ready flag and action
ready flag serve ONLY as POST-decision comparators.

No invented tolerance from class, equipment, target dummy or raid event.
No float rounding or 1ms heuristic: pinned timespan_t uses millisecond
integer storage and source predicate uses <=. Full readiness/selection
remains unresolved; this proves ONLY the cooldown queue necessary guard.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile
from simc_native_if_pre_operand_replay_v1 import (
    PINNED_FURY_BLOB, verify_folder, get_native_attempt, exact_key
)
from simc_native_ready_guard_witness_replay_v1 import read_guard, replay_log
from simc_native_cooldown_queue_clock_replay_v1 import (
    read_clock, replay_clock_log
)
from simc_native_cooldown_tolerance_pre_instrument_v1 import MARK

SCHEMA = "ZrotNativeIndependentRawToleranceAndExactQueueReadyV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

class ToleranceReplayError(ValueError):
    pass


def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def read_tolerance(line:str):
    at=line.find(MARK)
    if at<0:
        return None
    fields=line[at:].strip().split("|")
    if len(fields)!=7 or not fields[1].isdigit() or not fields[3].isdigit():
        raise ToleranceReplayError("SOURCE_RAW_TOLERANCE_LOG_SHAPE_CHANGED")
    if not fields[2] or not fields[4]:
        raise ToleranceReplayError("MISSING_SOURCE_IDENTITY")
    try:
        actor=int(fields[5])
        default=int(fields[6])
    except ValueError:
        raise ToleranceReplayError("RAW_TOLERANCE_NOT_EXACT_INTEGER")
    if default<0:
        raise ToleranceReplayError("SIM_DEFAULT_COOLDOWN_TOLERANCE_NEGATIVE")
    return {
        "time_ms":int(fields[1]),
        "list":fields[2],
        "ordinal":int(fields[3]),
        "native_name":fields[4],
        "raw_actor_tolerance_ms":actor,
        "sim_default_tolerance_ms":default,
    }


def independent_raw_tolerance_queue(clock:dict, operand:dict):
    # Exact source timespan_t integer millisecond arithmetic.
    if exact_key(clock)!=exact_key(operand):
        raise ToleranceReplayError("SOURCE_PRE_CLOCK_AND_TOLERANCE_IDENTITY_CONFLICT")
    actor=operand["raw_actor_tolerance_ms"]
    default=operand["sim_default_tolerance_ms"]
    ready=clock["cooldown_ready_ms"]
    now=clock["time_ms"]
    bound=bool(clock["has_bound_action"] and clock["has_bound_player"])
    selected=default if actor<0 else actor
    if selected<0:
        raise ToleranceReplayError("NEGATIVE_SELECTED_SOURCE_TOLERANCE")
    if not clock["has_bound_player"] and actor!=0:
        raise ToleranceReplayError("UNBOUND_PLAYER_NOT_SENTINEL_RAW_TOLERANCE")
    source_queue=ready-selected if bound else None
    if ready<=now:
        result=1
        reason="READY_CLOCK_UP_EXACT"
    elif not bound:
        result=0
        reason="NOT_ACTION_AND_PLAYER_BOUND"
    elif source_queue<=now:
        result=1
        reason="SOURCE_NUMERIC_QUEUE_WINDOW_OPEN"
    else:
        result=0
        reason="SOURCE_NUMERIC_QUEUE_WINDOW_CLOSED"
    return {
        "numeric_cooldown_ready":result,
        "source_numeric_reason":reason,
        "selected_tolerance_ms":selected if clock["has_bound_player"] else None,
        "source_computed_queueable_ms":source_queue,
        "actor_raw_selects_sim_default":actor<0 if clock["has_bound_player"] else None,
    }


def replay_trace(log:str,ir:dict)->dict:
    pending=None
    counts=Counter()
    reasons=Counter()
    sampled=[]
    for line in log.splitlines():
        guard=read_guard(line)
        if guard is not None:
            if pending is not None:
                raise ToleranceReplayError("OVERLAPPING_NATIVE_READY_ATTEMPT")
            pending={"guard":guard,"clock":None,"tol":None}
            continue
        clock=read_clock(line)
        if clock is not None:
            if pending is None or pending["clock"] is not None:
                raise ToleranceReplayError("MISSING_OR_DUPLICATE_CLOCK")
            if exact_key(clock)!=exact_key(pending["guard"]):
                raise ToleranceReplayError("CLOCK_GUARD_ORIGIN_MISMATCH")
            pending["clock"]=clock
            continue
        tol=read_tolerance(line)
        if tol is not None:
            if pending is None or pending["clock"] is None or pending["tol"] is not None:
                raise ToleranceReplayError("MISSING_OR_DUPLICATE_TOLERANCE")
            if exact_key(tol)!=exact_key(pending["clock"]):
                raise ToleranceReplayError("TOLERANCE_CLOCK_ORIGIN_MISMATCH")
            pending["tol"]=tol
            continue
        attempt=get_native_attempt(line)
        if attempt is None:
            continue
        if pending is None or pending["clock"] is None or pending["tol"] is None:
            raise ToleranceReplayError("NATIVE_ACTION_ATTEMPT_UNPAIRED")
        if exact_key(attempt)!=exact_key(pending["tol"]):
            raise ToleranceReplayError("NATIVE_ATTEMPT_POINTER_CHANGED")
        r=pending["guard"]
        if (r["list"] not in ir["action_lists"] or
            type(r["ordinal"]) is not int or not 0<=r["ordinal"]-1<len(ir["action_lists"][r["list"]])):
            raise ToleranceReplayError("SOURCE_APL_INDEX_INVALID")
        calc=independent_raw_tolerance_queue(pending["clock"],pending["tol"])
        counts["attempts"]+=1
        reasons[calc["source_numeric_reason"]]+=1
        clock=pending["clock"]
        if calc["source_computed_queueable_ms"] is not None:
            counts["bound_queue_threshold_independently_computed"]+=1
            if calc["source_computed_queueable_ms"]!=clock["queueable_ms"]:
                raise ToleranceReplayError("INDEPENDENT_QUEUEABLE_TIME_NATIVE_COMPARATOR_CONFLICT")
            counts["computed_queue_threshold_native_exact_matched"]+=1
        elif clock["queueable_ms"]!=0:
            raise ToleranceReplayError("UNBOUND_QUEUE_CLOCK_NOT_SENTINEL")
        if calc["numeric_cooldown_ready"]!=r["cooldown_queueable"]:
            raise ToleranceReplayError("INDEPENDENT_NUMERIC_COOLDOWN_NATIVE_FLAG_CONFLICT")
        counts["independent_ready_boolean_native_is_ready_matched"]+=1
        if calc["source_numeric_reason"]=="SOURCE_NUMERIC_QUEUE_WINDOW_OPEN":
            counts["queue_open_but_cooldown_not_up"]+=1
        if calc["source_numeric_reason"]=="READY_CLOCK_UP_EXACT" and (
            abs(clock["time_ms"]-clock["cooldown_ready_ms"])<=1):
            counts["ready_clock_source_boundary_resolved_exactly"]+=1
        if (calc["source_computed_queueable_ms"] is not None and
            abs(calc["source_computed_queueable_ms"]-clock["time_ms"])<=1):
            counts["queue_clock_source_boundary_resolved_exactly"]+=1
        if len(sampled)<14 and (
            calc["source_numeric_reason"]!="READY_CLOCK_UP_EXACT" or
            abs(clock["time_ms"]-clock["cooldown_ready_ms"])<=1):
            sampled.append({
                "at_ms":attempt["time_ms"],
                "source_list":attempt["list"],
                "source_ordinal":attempt["ordinal"],
                "source_native_action":attempt["native_name"],
                "raw_clock":clock,
                "raw_tolerance":pending["tol"],
                "independent_computation":calc,
                "native_is_ready_comparator_after_calculation":r["cooldown_queueable"],
            })
        pending=None
    if pending is not None or not counts["attempts"]:
        raise ToleranceReplayError("END_OF_TRACE_UNPAIRED_OR_EMPTY")
    if counts["independent_ready_boolean_native_is_ready_matched"]!=counts["attempts"]:
        raise ToleranceReplayError("EXACT_COOLDOWN_RESULT_ACCOUNTING_FAILED")
    return {
        "counts":dict(sorted(counts.items())),
        "numeric_source_reason_counts":dict(sorted(reasons.items())),
        "bounded_source_examples":sampled,
        "full_native_ready_independently_reconstructed":False,
        "native_queueable_method_result_used_as_input":False,
        "native_cooldown_is_ready_used_as_input":False,
        "source_tolerance_selection_and_subtraction_independent":True,
    }


def run(profile:Path,st:Path,two:Path,move_st:Path,move_two:Path)->dict:
    ir=parse_profile(profile.read_bytes(),require_source=True,
                     expected_git_blob=PINNED_FURY_BLOB)
    cases={}
    overall=Counter()
    for label,root,target,expected in (
        ("stationary_st",st,1,1542),
        ("stationary_two_target",two,2,1030),
        ("moving_st",move_st,1,1650),
        ("moving_two_target",move_two,2,1186),
    ):
        source=verify_folder(root.resolve(strict=True),target,ir)
        raw=(root/"simc_native_log.txt").read_bytes()
        trace=raw.decode("utf-8")
        prior=replay_log(trace,ir)
        prior_clock=replay_clock_log(trace,ir)
        result=replay_trace(trace,ir)
        n=result["counts"]["attempts"]
        if (n!=expected or n!=prior["counts"]["native_ATTEMPT_records"]
            or n!=prior_clock["counts"]["actual_attempts"]
            or n!=source["counts"]["all_native_action_ready_attempts"]):
            raise ToleranceReplayError("PINNED_NATIVE_COHORT_COUNT_CHANGED")
        if result["counts"]["independent_ready_boolean_native_is_ready_matched"]!=n:
            raise ToleranceReplayError("EXACT_COOLDOWN_BOOLEAN_MISMATCH")
        for key,val in result["counts"].items():
            overall[key]+=val
        cases[label]={
            **result,
            "native_binary_sha256":source["native_binary_sha256"],
            "native_log_sha256":sha(raw),
            "prior_bounded_source_guard_negatives":
                prior["counts"].get("PROVEN_BASE_GUARD_NOT_READY",0),
        }
    if (overall["attempts"]!=5408 or
        len({x["native_binary_sha256"] for x in cases.values()})!=1):
        raise ToleranceReplayError("FOUR_CASE_SOURCE_PARITY_FAILED")
    return {
        "schema":SCHEMA,
        "policy_id":POLICY,
        "status":"SOURCE_RAW_TOLERANCE_EXACT_INTEGER_QUEUEABLE_BOOL_PARITY",
        "all_cases":cases,
        "totals":dict(sorted(overall.items())),
        "clock_unit":"exact_integer_milliseconds",
        "independently_computed_raw_actor_tolerance_selection":True,
        "independently_computed_queueable_time_subtraction":True,
        "independently_computed_ready_boolean":True,
        "native_method_values_only_POST_comparators":True,
        "full_native_ready_verified":False,
        "full_source_order_action_choice_verified":False,
        "complete_general_rotation":False,
        "WCL_API_calls":0,
        "MAIN_promoted":False,
    }


def selftest():
    from simc_apl_semantic_ir_v2 import parse_profile
    original=parse_profile(b"actions=foo\n",require_source=False)
    prefix="ZROT_NATIVE_CD_TOLERANCE_PRE_V1|"
    clock={
        "time_ms":100,"list":"default","ordinal":1,"native_name":"foo",
        "cooldown_ready_ms":300,"has_bound_action":1,
        "has_bound_player":1,"queueable_ms":150,
    }
    value=read_tolerance(prefix+"100|default|1|foo|-1|150")
    assert value["raw_actor_tolerance_ms"]==-1
    assert independent_raw_tolerance_queue(clock,value)["source_computed_queueable_ms"]==150
    assert independent_raw_tolerance_queue(clock,value)["numeric_cooldown_ready"]==0
    value["raw_actor_tolerance_ms"]=250
    assert independent_raw_tolerance_queue(clock,value)["numeric_cooldown_ready"]==1
    value["raw_actor_tolerance_ms"]=200
    assert independent_raw_tolerance_queue(clock,value)["numeric_cooldown_ready"]==1
    clock["cooldown_ready_ms"]=100
    assert independent_raw_tolerance_queue(clock,value)["numeric_cooldown_ready"]==1
    clock["cooldown_ready_ms"]=300
    clock["has_bound_action"]=0
    assert independent_raw_tolerance_queue(clock,value)["numeric_cooldown_ready"]==0
    clock["has_bound_action"]=1
    for line in (prefix+"100|default|1|foo|-1|bad",prefix+"100|default|1|foo|-1|-2"):
        try:read_tolerance(line)
        except ToleranceReplayError:pass
        else:raise AssertionError("MALFORMED_TOLERANCE_ACCEPTED")
    source="\n".join([
        "ZROT_NATIVE_READY_GUARDS_PRE_V1|100|default|1|foo|0|1|0|-1|-1",
        "ZROT_NATIVE_CD_QUEUE_CLOCK_PRE_V1|100|default|1|foo|300|1|1|150",
        prefix+"100|default|1|foo|-1|150",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|100|default|default|1|foo|0"
    ])
    got=replay_trace(source,original)
    assert got["counts"]["attempts"]==1
    assert got["counts"]["independent_ready_boolean_native_is_ready_matched"]==1
    for bad in (
        source.replace("|foo|-1|150","|foo|-1|149"),
        source.replace("|foo|0|1|0|-1|-1","|foo|1|1|0|-1|-1"),
        source.replace("ZROT_NATIVE_SELECT_V1|ATTEMPT|100|default|default|1|foo|0",
                       "ZROT_NATIVE_SELECT_V1|ATTEMPT|100|default|default|2|foo|0"),
    ):
        try:replay_trace(bad,original)
        except ToleranceReplayError:pass
        else:raise AssertionError("SPOOFED_OR_INCONSISTENT_SOURCE_ACCEPTED")
    return {
        "status":"PASS_OFFLINE_SYNTHETIC","checks":14,
        "native_not_run":True,"WCL_API_calls":0,
        "readiness_proven":False
    }


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
        p.error("all five pinned inputs required together")
    data=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(data)
        print("NATIVE_RAW_TOLERANCE_EXACT_QUEUE_SHA256="+sha(data))
    else:print(data.decode(),end="")


if __name__=="__main__":
    main()
