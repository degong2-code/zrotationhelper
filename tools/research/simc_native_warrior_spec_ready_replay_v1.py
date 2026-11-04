#!/usr/bin/env python3
"""SpecAdapter-only original Warrior virtual ready route and numeric guards.

Reconstruct only source-ranged numeric distance/channel predicates using
fields logged at original ready() execution. Never use Native actual
return/branch as Python numeric input. Original Warrior ready/action_ready
returns and action_t full-base source exit are postcomputation corroboration
ONLY. Replacement delegation, other class overrides, target specializations
and unobserved method paths remain UNKNOWN even when Native chose a spell.

Actual selected physical ability needs independent base ready, target,
subclass guards, positive APL, sync and all future WoW practice states
before being scored as fully READY or optimal.
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
    PINNED_FURY_BLOB, verify_folder, exact_key,get_native_attempt,
)
from simc_native_ready_guard_witness_replay_v1 import (
    read_guard,read_method_entry,replay_log,
)
from simc_native_ready_guard_witness_instrument_v1 import (
    BASE_READY_MARK, BASE_ACTION_MARK
)
from simc_native_postguard_source_replay_v1 import parse_exit
from simc_native_target_eligibility_source_replay_v1 import (
    parse_config,parse_target,independent_basic_target_truth,direct_path
)
from simc_native_warrior_spec_ready_instrument_v1 import (
    READY_MARK,ACTION_MARK
)
SCHEMA="ZrotWarriorSourceOverrideReadyNumericDistanceChannelV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
READY_STAGES=(
    "REPLACEMENT_DELEGATED","QUALIFIED_BASE_READY_FALSE",
    "DISTANCE_TOO_FAR","CHANNELING_NOT_USABLE",
    "QUALIFIED_BASE_AND_WARRIOR_READY_TRUE"
)
ACTION_STAGES=(
    "NO_REPLACEMENT_OR_ZERO_DURATION",
    "REPLACEMENT_DELEGATED",
    "REPLACEMENT_INACTIVE_QUALIFIED_BASE"
)
class WarriorReplayError(ValueError):pass

def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()

def read_warrior_ready(line:str)->dict|None:
    i=line.find(READY_MARK)
    if i<0:return None
    p=line[i:].strip().split("|")
    if len(p)!=9 or p[3] not in READY_STAGES:
        raise WarriorReplayError("WARRIOR_READY_SOURCE_RECORD_FORMAT")
    try:
        timestamp=int(p[1]);distance=float(p[4]);range_=float(p[5])
        channel=int(p[6]);allowed=int(p[7]);result=int(p[8])
    except ValueError:raise WarriorReplayError("WARRIOR_READY_SOURCE_NOT_NUMERIC")
    if (not math.isfinite(distance) or not math.isfinite(range_) or
        channel not in (-1,0,1) or allowed not in (0,1) or
        result not in (0,1) or not p[2]):
        raise WarriorReplayError("WARRIOR_READY_RAW_NUMERIC_OUT_OF_RANGE")
    return {"time_ms":timestamp,"native_name":p[2],"stage":p[3],
            "distance_to_move":distance,"range":range_,
            "source_original_channel_or_bladestorm":channel,
            "usable_while_channeling":allowed,
            "source_native_ready_boolean_comparator":result}

def read_warrior_action(line:str)->dict|None:
    i=line.find(ACTION_MARK)
    if i<0:return None
    p=line[i:].strip().split("|")
    if len(p)!=5 or p[3] not in ACTION_STAGES or p[4] not in ("0","1"):
        raise WarriorReplayError("WARRIOR_ACTION_SOURCE_RECORD_FORMAT")
    try:timestamp=int(p[1])
    except ValueError:raise WarriorReplayError("WARRIOR_ACTION_SOURCE_TIMESTAMP_INVALID")
    return {"time_ms":timestamp,"native_name":p[2],"route":p[3],
            "source_native_action_ready_comparator":int(p[4])}

def independent_warrior_numeric(row:dict)->dict:
    distance=row["distance_to_move"]
    range_=row["range"]
    beyond=distance>range_ and range_!=-1.0
    combined=row["source_original_channel_or_bladestorm"]
    stage=row["stage"]
    if stage in ("REPLACEMENT_DELEGATED","QUALIFIED_BASE_READY_FALSE"):
        return {"numeric_route":"UNKNOWN_DELEGATED_OR_BASE_NOT_REACHED",
                "distance_out_of_range":beyond,
                "channel_blocked":None,"compared":False}
    if stage=="DISTANCE_TOO_FAR":
        if not beyond:
            raise WarriorReplayError("SOURCE_WARRIOR_DISTANCE_EXIT_CONTRADICTS_RAW_RANGE")
        return {"numeric_route":"DISTANCE_TOO_FAR","distance_out_of_range":True,
                "channel_blocked":None,"compared":True}
    if beyond:
        raise WarriorReplayError("SOURCE_WARRIOR_LATER_EXIT_BUT_RANGE_EXCEEDED")
    if combined not in (0,1):
        raise WarriorReplayError("SOURCE_CHANNEL_GUARD_MISSING_AFTER_RANGE")
    blocked=bool(combined and not row["usable_while_channeling"])
    if stage=="CHANNELING_NOT_USABLE":
        if not blocked:
            raise WarriorReplayError("SOURCE_CHANNEL_EXIT_CONTRADICTS_NUMERIC_RAW_GUARD")
        return {"numeric_route":"CHANNELING_NOT_USABLE",
                "distance_out_of_range":False,
                "channel_blocked":blocked,"compared":True}
    if blocked or row["source_native_ready_boolean_comparator"]!=1:
        raise WarriorReplayError("WARRIOR_READY_SUCCESS_CONTRADICTS_RAW_GUARD")
    return {"numeric_route":"SOURCE_WARRIOR_RANGE_CHANNEL_PASS_ONLY",
            "distance_out_of_range":False,"channel_blocked":False,
            "compared":True}

def run_trace(trace:str,ir:dict)->dict:
    current=None
    counts=Counter()
    stages=Counter();routes=Counter();numeric=Counter()
    examples=[]
    for line in trace.splitlines():
        g=read_guard(line)
        if g is not None:
            if current is not None:raise WarriorReplayError("NESTED_NATIVE_SELECT_PRE")
            current={"key":exact_key(g),"ready":[],"action":[],"target":[],
                    "config":None,"exits":[],"base_action":0,"base_ready":0}
            continue
        config=parse_config(line)
        if config is not None:
            if current is None or current["config"] is not None or current["key"]!=exact_key(config):
                raise WarriorReplayError("WARRIOR_CONFIG_PRE_IDENTITY_MISMATCH")
            current["config"]=config
            continue
        w_ready=read_warrior_ready(line)
        if w_ready is not None:
            if current is None:
                counts["unscoped_Warrior_ready_returns"]+=1
            elif (w_ready["time_ms"],w_ready["native_name"])==(
                current["key"][0],current["key"][3]):
                current["ready"].append(w_ready)
            else:
                counts["other_action_warrior_ready_in_scope"]+=1
            continue
        w_action=read_warrior_action(line)
        if w_action is not None:
            if current is None:
                counts["unscoped_Warrior_action_ready_returns"]+=1
            elif (w_action["time_ms"],w_action["native_name"])==(
                current["key"][0],current["key"][3]):
                current["action"].append(w_action)
            else:
                counts["other_action_warrior_action_ready_in_scope"]+=1
            continue
        target=parse_target(line)
        if target is not None:
            if current is not None and (target["time_ms"],target["action"])==(
                current["key"][0],current["key"][3]):
                current["target"].append(target)
            continue
        for mark,k in ((BASE_READY_MARK,"base_ready"),(BASE_ACTION_MARK,"base_action")):
            entry=read_method_entry(line,mark)
            if entry is not None:
                if current is not None and entry==(current["key"][0],current["key"][3]):
                    current[k]+=1
                break
        else:
            e=parse_exit(line)
            if e is not None and current is not None and (
                e["time_ms"],e["name"])==(current["key"][0],current["key"][3]):
                current["exits"].append(e)
                continue
            attempt=get_native_attempt(line)
            if attempt is None:continue
            if current is None or current["key"]!=exact_key(attempt) or current["config"] is None:
                raise WarriorReplayError("WARRIOR_ATTEMPT_PRE_POINTER_INCOMPLETE")
            counts["Native_action_ready_attempts"]+=1
            key=current["key"]
            if key[1] not in ir["action_lists"] or not 1<=key[2]<=len(ir["action_lists"][key[1]]):
                raise WarriorReplayError("WARRIOR_PINNED_APL_SOURCE_ROW_MISSING")
            row=ir["action_lists"][key[1]][key[2]-1]
            positive_base=(len(current["exits"])==1 and
                           current["exits"][0]["reason"]=="FULL_BASE_TRUE" and
                           current["base_action"]==1 and
                           current["base_ready"]==1)
            original_target=None
            if (direct_path(current["config"]) and len(current["target"])==1):
                original_target=independent_basic_target_truth(current["target"][0])[0]
            if len(current["action"])!=1:
                counts["UNKNOWN_no_unique_Warrior_action_ready_route"]+=1
            else:
                a=current["action"][0]
                routes[a["route"]]+=1
                if a["source_native_action_ready_comparator"]!=attempt["ready"]:
                    raise WarriorReplayError("WARRIOR_ACTION_ROUTE_SOURCE_RETURN_VS_NATIVE_ATTEMPT_CONFLICT")
                counts["Warrior_action_ready_route_source_attested"]+=1
                if a["route"]=="REPLACEMENT_DELEGATED":
                    counts["UNKNOWN_Warrior_action_ready_replacement_delegation"]+=1
            if len(current["ready"])!=1:
                counts["UNKNOWN_no_unique_Warrior_ready_path"]+=1
            else:
                wr=current["ready"][0];stages[wr["stage"]]+=1
                calc=independent_warrior_numeric(wr)
                if calc["compared"]:
                    counts["Warrior_raw_numeric_range_channel_compared"]+=1
                    numeric[calc["numeric_route"]]+=1
                else:
                    counts["UNKNOWN_Warrior_ready_replacement_or_prior_base"]+=1
                if wr["stage"] in ("DISTANCE_TOO_FAR","CHANNELING_NOT_USABLE"):
                    if attempt["ready"]!=0:
                        raise WarriorReplayError("WARRIOR_READINESS_NUMERIC_NEGATIVE_WITH_NATIVE_TRUE")
                    counts["Warrior_numeric_necessary_failure"]+=1
                if (wr["stage"]=="QUALIFIED_BASE_AND_WARRIOR_READY_TRUE" and
                    original_target==1 and positive_base and len(current["action"])==1 and
                    current["action"][0]["route"]!="REPLACEMENT_DELEGATED" and
                    row["action"] not in ("run_action_list","call_action_list","variable")):
                    counts["physical_candidate_Warrior_range_channel_positive_and_base_target_positive"]+=1
                if len(examples)<20 and (calc["compared"] or positive_base):
                    examples.append({
                        "at_ms":key[0],"source_list":key[1],"source_index":key[2]-1,
                        "source_sha256":row["source_sha256"],
                        "ability":row["action"],
                        "warrior_source_ready_route":wr["stage"],
                        "original_action_source_route":
                            current["action"][0]["route"] if len(current["action"])==1 else None,
                        "independent_range_and_channel":calc,
                        "numeric_basic_target":original_target,
                        "source_full_base_exit":positive_base,
                        "Native_selected_boolean_comparator_only":attempt["ready"],
                        "independently_verified_complete_skill_ready":False,
                    })
            current=None
    if current is not None or counts["Native_action_ready_attempts"]==0:
        raise WarriorReplayError("WARRIOR_SOURCE_ATTEMPT_UNPAIRED_EOF")
    if (counts["Warrior_action_ready_route_source_attested"]+
        counts["UNKNOWN_no_unique_Warrior_action_ready_route"]!=
        counts["Native_action_ready_attempts"]):
        raise WarriorReplayError("WARRIOR_SOURCE_ROUTE_COHORT_ACCOUNTING_FAILURE")
    return {"counts":dict(sorted(counts.items())),
        "source_Warrior_ready_first_exit_distribution":dict(sorted(stages.items())),
        "source_Warrior_action_ready_delegation_distribution":dict(sorted(routes.items())),
        "independently_calculated_bounded_numeric_reasons":dict(sorted(numeric.items())),
        "bounded_examples":examples,
        "source_virtual_method_return_not_independent_operand":True,
        "warrior_replacement_delegation_not_independent":True,
        "full_positive_ability_ready_independently_verified":False,
        "full_General_Rotation_priority_verified":False}

def run(profile:Path,st:Path,two:Path,move_st:Path,move_two:Path)->dict:
    ir=parse_profile(profile.read_bytes(),require_source=True,expected_git_blob=PINNED_FURY_BLOB)
    cases={};totals=Counter();all_stages=Counter();all_routes=Counter();all_numeric=Counter()
    for name,folder,targets,num in (
        ("stationary_st",st,1,1542),("stationary_two_target",two,2,1030),
        ("moving_st",move_st,1,1650),("moving_two_target",move_two,2,1186)
    ):
        folder=folder.resolve(strict=True)
        proven=verify_folder(folder,targets,ir)
        raw=(folder/"simc_native_log.txt").read_bytes()
        trace=raw.decode("utf-8")
        prev=replay_log(trace,ir)
        report=run_trace(trace,ir)
        if (report["counts"]["Native_action_ready_attempts"]!=num or
            prev["counts"]["native_ATTEMPT_records"]!=num or
            proven["counts"]["all_native_action_ready_attempts"]!=num):
            raise WarriorReplayError("OFFICIAL_NATIVE_SCENARIO_COUNTS_DRIFT")
        totals.update({k:v for k,v in report["counts"].items()
                       if not k.startswith("unscoped_")})
        all_stages.update(report["source_Warrior_ready_first_exit_distribution"])
        all_routes.update(report["source_Warrior_action_ready_delegation_distribution"])
        all_numeric.update(report["independently_calculated_bounded_numeric_reasons"])
        cases[name]={**report,"native_log_sha256":sha(raw),
            "native_binary_sha256":proven["native_binary_sha256"]}
    if (totals["Native_action_ready_attempts"]!=5408 or
        len({v["native_binary_sha256"] for v in cases.values()})!=1):
        raise WarriorReplayError("SOURCE_WARRIOR_FOUR_COHORT_IDENTITY_CHANGED")
    return {"schema":SCHEMA,"product_policy":POLICY,
        "source_lane":"WARRIOR_SPEC_ADAPTER_NOT_GENERIC_ENGINE",
        "four_scenarios":cases,
        "totals":dict(sorted(totals.items())),
        "source_Warrior_ready_exit_distribution":dict(sorted(all_stages.items())),
        "source_action_ready_delegation_distribution":dict(sorted(all_routes.items())),
        "source_numeric_range_channel_distribution":dict(sorted(all_numeric.items())),
        "native_source_return_used_only_as_POST_comparator":True,
        "full_ability_READY_independent":False,
        "source_ordered_choice_independent":False,
        "WCL_API_calls":0,"MAIN_promoted":False}

def selftest():
    row={"time_ms":10,"native_name":"foo","stage":"DISTANCE_TOO_FAR",
         "distance_to_move":11.0,"range":5.0,
         "source_original_channel_or_bladestorm":-1,
         "usable_while_channeling":0,
         "source_native_ready_boolean_comparator":0}
    assert independent_warrior_numeric(row)["numeric_route"]=="DISTANCE_TOO_FAR"
    row["range"]=12
    try:independent_warrior_numeric(row)
    except WarriorReplayError:pass
    else:raise AssertionError("INVALID_RANGE_SOURCE_ACCEPTED")
    row.update(stage="CHANNELING_NOT_USABLE",range=5,distance_to_move=3,
               source_original_channel_or_bladestorm=1)
    assert independent_warrior_numeric(row)["channel_blocked"] is True
    row["stage"]="QUALIFIED_BASE_AND_WARRIOR_READY_TRUE"
    row["source_original_channel_or_bladestorm"]=0
    row["source_native_ready_boolean_comparator"]=1
    assert independent_warrior_numeric(row)["compared"] is True
    assert read_warrior_ready(
        READY_MARK+"10|foo|QUALIFIED_BASE_AND_WARRIOR_READY_TRUE|0|5|0|0|1")
    assert read_warrior_action(ACTION_MARK+"10|foo|NO_REPLACEMENT_OR_ZERO_DURATION|1")
    assert not read_warrior_ready("unrelated")
    ir=parse_profile(b"actions=foo\n",require_source=False)
    native="\n".join([
        "ZROT_NATIVE_READY_GUARDS_PRE_V1|10|default|1|foo|1|1|0|-1|1",
        "ZROT_NATIVE_TARGET_CONFIG_PRE_V1|10|default|1|foo|1|0|0|0|1",
        "ZROT_NATIVE_BASE_ACTION_READY_ENTER_V1|10|foo",
        "ZROT_NATIVE_BASE_READY_ENTER_V1|10|foo",
        READY_MARK+"10|foo|QUALIFIED_BASE_AND_WARRIOR_READY_TRUE|0|5|0|0|1",
        "ZROT_NATIVE_BASE_TARGET_DECISION_V1|10|foo|PASS|0|0|1|0|5|1|-1",
        "ZROT_NATIVE_BASE_POST_EXIT_V1|10|foo|FULL_BASE_TRUE",
        ACTION_MARK+"10|foo|NO_REPLACEMENT_OR_ZERO_DURATION|1",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|foo|1"
    ])
    result=run_trace(native,ir)
    assert result["counts"]["Native_action_ready_attempts"]==1
    assert result["counts"]["physical_candidate_Warrior_range_channel_positive_and_base_target_positive"]==1
    for tamper in (
        native.replace("QUALIFIED_BASE_AND_WARRIOR_READY_TRUE|0|5","DISTANCE_TOO_FAR|0|5"),
        native.replace("NO_REPLACEMENT_OR_ZERO_DURATION|1","NO_REPLACEMENT_OR_ZERO_DURATION|0"),
    ):
        try:run_trace(tamper,ir)
        except WarriorReplayError:pass
        else:raise AssertionError("CORRUPTED_WARRIOR_SOURCE_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":12,
        "actual_CXX_or_WCL_not_executed":True,"WCL_API_calls":0,
        "full_READY_not_proven":True}

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
    if not any(inputs):result=selftest()
    elif all(inputs):result=run(*inputs)
    else:p.error("all five Native source inputs required")
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
        print("NATIVE_WARRIOR_SPEC_READY_SOURCE_SHA256="+sha(raw))
    else:print(raw.decode(),end="")
if __name__=="__main__":main()
