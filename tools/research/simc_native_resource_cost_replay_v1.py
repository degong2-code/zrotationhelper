#!/usr/bin/env python3
"""Source-gated independent numeric PRE resource affordability in actual SimC.

Only actions where original action_t::cost_affordable() was entered in
PRE-guard context and (for resource!=NONE) original base
player_t::resource_available() was also entered can be independently
evaluated. Dynamic action_t::cost() is read from its ORIGINAL invocation,
never computed or called again. Replay calculates the boolean using the
source-guaranteed comparison and checks the native PRE cost guard only
AFTER independent evaluation. Missing subclass/base-entry is UNKNOWN.

Full action readiness, cost() dynamic modifier semantics and optimal
source-order action choice remain unresolved.
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
    PINNED_FURY_BLOB, verify_folder, exact_key, get_native_attempt,
)
from simc_native_ready_guard_witness_replay_v1 import (
    read_guard, read_method_entry, replay_log,
)
from simc_native_ready_guard_witness_instrument_v1 import (
    BASE_ACTION_MARK, BASE_READY_MARK,
)
from simc_native_cooldown_tolerance_replay_v1 import (
    replay_trace as verify_tolerance_replay,
)
from simc_native_resource_cost_pre_instrument_v1 import (
    ACTION_MARK, PLAYER_MARK,
)

SCHEMA = "ZrotNativeSourceBaseResourceCostNumericPreReplayV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"


class NumericResourceError(ValueError):
    pass


def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def read_cost(line:str):
    i=line.find(ACTION_MARK)
    if i<0:return None
    f=line[i:].strip().split("|")
    if len(f)!=6 or not f[1].isdigit() or not f[2]:
        raise NumericResourceError("ACTION_BASE_COST_SOURCE_MARKER_INVALID")
    try:
        r=int(f[3]);none=int(f[4]);cost=float(f[5])
    except ValueError:
        raise NumericResourceError("ACTION_BASE_COST_SOURCE_VALUE_INVALID")
    if not math.isfinite(cost) or none not in (0,1):
        raise NumericResourceError("ACTION_COST_NONFINITE_OR_NONE_FLAG_INVALID")
    if none==1 and cost!=0:
        raise NumericResourceError("NONE_RESOURCE_COST_NONZERO")
    return {"time_ms":int(f[1]),"native_action":f[2],
            "resource_id":r,"resource_none":none,"cost":cost}


def read_base_resource(line:str):
    i=line.find(PLAYER_MARK)
    if i<0:return None
    f=line[i:].strip().split("|")
    if len(f)!=6 or not f[1].isdigit():
        raise NumericResourceError("PLAYER_BASE_RESOURCE_SOURCE_MARKER_INVALID")
    try:
        r=int(f[2]);cost=float(f[3]);current=float(f[4]);infinite=int(f[5])
    except ValueError:
        raise NumericResourceError("PLAYER_BASE_RESOURCE_SOURCE_VALUE_INVALID")
    if (not math.isfinite(cost) or not math.isfinite(current)
        or infinite not in (0,1)):
        raise NumericResourceError("PLAYER_BASE_RESOURCE_NUMERIC_FACT_INVALID")
    return {"time_ms":int(f[1]),"resource_id":r,"cost":cost,
            "current":current,"infinite":infinite}


def independent_numeric_resource(cost:dict,base:dict|None):
    if cost["resource_none"]==1:
        return 1,"RESOURCE_NONE_BASE_ACTION_SHORT_CIRCUIT"
    if base is None:
        return None,"UNKNOWN_PLAYER_RESOURCE_BASE_METHOD_NOT_PROVEN"
    if (base["resource_id"]!=cost["resource_id"] or
        base["time_ms"]!=cost["time_ms"] or
        base["cost"]!=cost["cost"]):
        raise NumericResourceError("BASE_RESOURCE_ACTION_COST_FACT_ORIGIN_MISMATCH")
    if base["cost"]<=0:
        return 1,"COST_NONPOSITIVE"
    if base["infinite"]:
        return 1,"SOURCE_RESOURCE_INFINITE"
    if base["current"]>=base["cost"]:
        return 1,"RESOURCE_CURRENT_AT_LEAST_ACTUAL_COST"
    return 0,"SOURCE_RESOURCE_INSUFFICIENT"


def replay_resource_trace(trace:str,ir:dict):
    candidate=None
    base=None
    current=None
    n=Counter()
    reasons=Counter()
    unknown=Counter()
    samples=[]
    for line in trace.splitlines():
        item=read_cost(line)
        if item is not None:
            if current is None:
                if candidate is not None:
                    n["discarded_unpaired_base_cost_observations"]+=1
                candidate=item
                base=None
            continue
        resource=read_base_resource(line)
        if resource is not None:
            if (current is None and candidate is not None and
                candidate["resource_none"]==0 and
                candidate["time_ms"]==resource["time_ms"] and
                candidate["resource_id"]==resource["resource_id"] and
                candidate["cost"]==resource["cost"]):
                if base is not None:
                    raise NumericResourceError("DUPLICATE_BASE_RESOURCE_OBSERVATION")
                base=resource
            continue
        guard=read_guard(line)
        if guard is not None:
            if current is not None:
                raise NumericResourceError("NESTED_NATIVE_READY_SOURCE_GROUP")
            if (guard["list"] not in ir["action_lists"] or
                not 0<=guard["ordinal"]-1<len(ir["action_lists"][guard["list"]])):
                raise NumericResourceError("SOURCE_APL_GUARD_ROW_OUT_OF_RANGE")
            paired=(candidate is not None and
                    candidate["time_ms"]==guard["time_ms"] and
                    candidate["native_action"]==guard["native_name"])
            current={"guard":guard,
                     "cost":candidate if paired else None,
                     "base":base if paired else None,
                     "action_entries":0,"ready_entries":0}
            candidate=None
            base=None
            continue
        for mark,key in ((BASE_ACTION_MARK,"action_entries"),
                         (BASE_READY_MARK,"ready_entries")):
            entry=read_method_entry(line,mark)
            if entry is not None:
                if (current is not None and
                    entry==(current["guard"]["time_ms"],
                            current["guard"]["native_name"])):
                    current[key]+=1
                break
        else:
            attempt=get_native_attempt(line)
            if attempt is None:continue
            if current is None or exact_key(attempt)!=exact_key(current["guard"]):
                raise NumericResourceError("NATIVE_READY_ATTEMPT_SOURCE_POINTER_MISMATCH")
            n["attempts"]+=1
            g=current["guard"]
            if g["source_cost_affordable"]==-1:
                n["cost_gated_off_by_earlier_guard"]+=1
            elif current["cost"] is None:
                n["cost_unknown_no_base_action_entry"]+=1
                unknown["action_cost_base_override_or_unobserved"]+=1
            else:
                if current["cost"]["resource_none"]:
                    n["base_resource_NONE"]+=1
                elif current["base"] is None:
                    n["cost_unknown_no_player_resource_base_entry"]+=1
                    unknown["player_resource_base_override_or_unobserved"]+=1
                result,why=independent_numeric_resource(
                    current["cost"],current["base"])
                if result is None:
                    n["cost_UNKNOWN"]+=1
                else:
                    n["cost_numerically_independent"]+=1
                    reasons[why]+=1
                    if result!=g["source_cost_affordable"]:
                        raise NumericResourceError(
                            "INDEPENDENT_SOURCE_COST_NUMERIC_VS_NATIVE_PRE_CONFLICT")
                    n["cost_numeric_vs_original_PRE_guard_matched"]+=1
                    if result==0:
                        n["cost_numeric_proved_false"]+=1
                        if (current["action_entries"]==1 and
                            current["ready_entries"]==1):
                            if attempt["ready"]!=0:
                                raise NumericResourceError(
                                    "NUMERIC_INSUFFICIENT_COST_BUT_NATIVE_ACTION_READY_TRUE")
                            n["necessary_base_cost_negative_PROVEN"]+=1
                    if len(samples)<14 and (result==0 or
                                            why=="RESOURCE_NONE_BASE_ACTION_SHORT_CIRCUIT"):
                        samples.append({
                            "source_list":attempt["list"],
                            "source_ordinal":attempt["ordinal"],
                            "native_action":attempt["native_name"],
                            "at_ms":attempt["time_ms"],
                            "base_cost_source":current["cost"],
                            "base_player_resource_source":current["base"],
                            "numeric_pre_cost_result":result,
                            "source_reason":why,
                            "native_PRE_cost_guard_POST_comparator":
                                g["source_cost_affordable"],
                        })
            current=None
    if current is not None or not n["attempts"]:
        raise NumericResourceError("TRAILING_SOURCE_ATTEMPT_OR_NO_EVIDENCE")
    if (n["cost_gated_off_by_earlier_guard"]+
        n["cost_unknown_no_base_action_entry"]+
        n["cost_numerically_independent"]+
        n["cost_UNKNOWN"]!=n["attempts"]):
        raise NumericResourceError("RESOURCE_COHORT_SOURCE_ACCOUNTING_FAILED")
    return {
        "counts":dict(sorted(n.items())),
        "numeric_reason_counts":dict(sorted(reasons.items())),
        "missing_base_route_counts":dict(sorted(unknown.items())),
        "bounded_examples":samples,
        "native_cost_return_compared_only_after_numeric":True,
        "resource_cost_original_execution_only":True,
        "base_resource_method_required_for_non_none":True,
        "full_action_ready_independent":False,
    }


def run(profile:Path,st:Path,two:Path,move_st:Path,move_two:Path):
    ir=parse_profile(profile.read_bytes(),require_source=True,
                     expected_git_blob=PINNED_FURY_BLOB)
    result={}
    totals=Counter()
    for label,folder,targets,expected in (
        ("stationary_st",st,1,1542),
        ("stationary_two_target",two,2,1030),
        ("moving_st",move_st,1,1650),
        ("moving_two_target",move_two,2,1186),
    ):
        folder=folder.resolve(strict=True)
        provenance=verify_folder(folder,targets,ir)
        raw=(folder/"simc_native_log.txt").read_bytes()
        trace=raw.decode("utf-8")
        old=replay_log(trace,ir)
        queue=verify_tolerance_replay(trace,ir)
        one=replay_resource_trace(trace,ir)
        if (one["counts"]["attempts"]!=expected or
            old["counts"]["native_ATTEMPT_records"]!=expected or
            queue["counts"]["attempts"]!=expected or
            provenance["counts"]["all_native_action_ready_attempts"]!=expected):
            raise NumericResourceError("PREVIOUS_NATIVE_READINESS_COHORT_DRIFT")
        if one["counts"].get("necessary_base_cost_negative_PROVEN",0)>old["counts"][
            "PROVEN_BASE_GUARD_NOT_READY"] if "PROVEN_BASE_GUARD_NOT_READY" in old["counts"] else False:
            raise NumericResourceError("NEGATIVE_BASE_COST_WITNESS_OVERRUN")
        result[label]={
            **one,
            "native_source_log_sha256":sha(raw),
            "native_binary_sha256":provenance["native_binary_sha256"],
            "previous_bounded_base_cost_negative_count":
                old["negative_witness_guard_distribution"].get("cost_affordable",0),
        }
        totals.update({k:v for k,v in one["counts"].items()
                       if k not in ("discarded_unpaired_base_cost_observations",)})
    if totals["attempts"]!=5408 or len({
        q["native_binary_sha256"] for q in result.values()})!=1:
        raise NumericResourceError("ACTUAL_SOURCE_CASE_OR_BINARY_NOT_IDENTICAL")
    return {
        "schema":SCHEMA,
        "policy_id":POLICY,
        "status":"ACTUAL_NATIVE_SOURCE_COST_NUMERIC_SUBSET_ONLY",
        "source_facts":"ORIGINAL_BASE_ACTION_COST_AND_BASE_PLAYER_RESOURCE_PRE_METHOD",
        "four_scenarios":result,
        "totals":dict(sorted(totals.items())),
        "native_cost_and_resource_boolean_comparison_only_AFTER_python":True,
        "source_override_paths_preserved_UNKNOWN":True,
        "action_cost_modifier_not_independently_derived":True,
        "full_native_action_ready_independent":False,
        "selected_skill_priority_independent":False,
        "WCL_API_calls":0,
        "MAIN_promoted":False,
    }


def selftest():
    from simc_apl_semantic_ir_v2 import parse_profile
    ir=parse_profile(b"actions=foo\n",require_source=False)
    c=read_cost(ACTION_MARK+"10|foo|1|0|20.5")
    r=read_base_resource(PLAYER_MARK+"10|1|20.5|15|0")
    assert independent_numeric_resource(c,r)==(0,"SOURCE_RESOURCE_INSUFFICIENT")
    r["current"]=25
    assert independent_numeric_resource(c,r)[0]==1
    r["current"]=15
    r["infinite"]=1
    assert independent_numeric_resource(c,r)[0]==1
    none=read_cost(ACTION_MARK+"10|foo|0|1|0")
    assert independent_numeric_resource(none,None)[0]==1
    assert independent_numeric_resource(c,None)[0] is None
    for raw in (ACTION_MARK+"10|foo|1|0|nan",
                PLAYER_MARK+"10|1|20|nan|0"):
        try:read_cost(raw) if raw.startswith(ACTION_MARK) else read_base_resource(raw)
        except NumericResourceError:pass
        else:raise AssertionError("NONFINITE_RESOURCE_VALUE_ACCEPTED")
    raw="\n".join([
        ACTION_MARK+"10|foo|1|0|20.5",
        PLAYER_MARK+"10|1|20.5|15|0",
        "ZROT_NATIVE_READY_GUARDS_PRE_V1|10|default|1|foo|1|1|0|-1|0",
        "ZROT_NATIVE_BASE_ACTION_READY_ENTER_V1|10|foo",
        "ZROT_NATIVE_BASE_READY_ENTER_V1|10|foo",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|foo|0",
    ])
    got=replay_resource_trace(raw,ir)
    assert got["counts"]["cost_numerically_independent"]==1
    assert got["counts"]["necessary_base_cost_negative_PROVEN"]==1
    for bad in (
        raw.replace("|20.5|15|0","|20.5|25|0"),
        raw.replace("|foo|1|0|20.5","|foo|1|0|nan"),
        raw.replace("ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|foo|0",
                    "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|2|foo|0"),
    ):
        try:replay_resource_trace(bad,ir)
        except NumericResourceError:pass
        else:raise AssertionError("SPOOFED_NUMERIC_COST_SOURCE_ACCEPTED")
    return {
        "status":"PASS_OFFLINE_SYNTHETIC","checks":13,
        "real_native_run":False,"full_ready_proven":False,"WCL_API_calls":0,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--native-st-dir",type=Path)
    p.add_argument("--native-2t-dir",type=Path)
    p.add_argument("--native-moving-st-dir",type=Path)
    p.add_argument("--native-moving-2t-dir",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    inputs=(args.official_profile,args.native_st_dir,args.native_2t_dir,
            args.native_moving_st_dir,args.native_moving_2t_dir)
    if not any(inputs):
        value=selftest()
    elif all(inputs):
        value=run(*inputs)
    else:
        p.error("all five actual Native source paths required")
    raw=(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("xb") as f:f.write(raw)
        print("NATIVE_BASE_RESOURCE_COST_NUMERIC_SHA256="+sha(raw))
    else:print(raw.decode(),end="")


if __name__=="__main__":
    main()
