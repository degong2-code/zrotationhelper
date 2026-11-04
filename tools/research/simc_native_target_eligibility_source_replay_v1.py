#!/usr/bin/env python3
"""Strict source-PRE numeric target eligibility and partial positive path audit.

Original base action_t::target_ready checks source sleeping, composite
invulnerability and source actual distance once, preserving short circuit.
Recompute its result from observed SOURCE INPUTS in Python; never use the
stage/native result as a numeric input. Missing original base implementation,
custom target_if/cycle/target_number, subclass target_ready and action_ready
remain UNKNOWN. No positive full action readiness or optimality is implied.

Produces first useful target eligibility evidence for actual selected rows.
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
    PINNED_FURY_BLOB,verify_folder,exact_key,get_native_attempt,
)
from simc_native_ready_guard_witness_replay_v1 import (
    read_guard,read_method_entry
)
from simc_native_ready_guard_witness_instrument_v1 import (
    BASE_ACTION_MARK,BASE_READY_MARK
)
from simc_native_postguard_source_replay_v1 import parse_exit
from simc_native_target_eligibility_source_instrument_v1 import MARK,CFG
from simc_native_if_false_priority_frontier_v1 import source_if_samples
from simc_native_if_pre_operand_replay_v1 import parse_fact

SCHEMA="ZrotNativeBaseTargetEligibilitySourceNumericPartialPositiveV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

class TargetReplayError(ValueError):pass

def sha(raw:bytes):return hashlib.sha256(raw).hexdigest()

def parse_config(line:str)->dict|None:
    at=line.find(CFG)
    if at<0:return None
    f=line[at:].strip().split("|")
    if len(f)!=10 or not f[1].isdigit() or not f[3].isdigit() or not f[2] or not f[4]:
        raise TargetReplayError("DIRECT_SOURCE_CONFIG_FORMAT_CHANGED")
    try: vals=[int(v) for v in f[5:]]
    except ValueError:raise TargetReplayError("SOURCE_TARGET_CONFIG_NON_INTEGER")
    basic,cycle_targets,cycle_players,number,has_target=vals
    if any(x not in (0,1) for x in (basic,cycle_targets,cycle_players,has_target)) or number<0:
        raise TargetReplayError("SOURCE_TARGET_CONFIG_NOT_BOUNDED")
    return {
        "time_ms":int(f[1]),"list":f[2],"ordinal":int(f[3]),
        "native_name":f[4],"target_if_NONE":basic,
        "cycle_targets":cycle_targets,"cycle_players":cycle_players,
        "option_target_number":number,"original_target_present":has_target,
    }

def parse_target(line:str)->dict|None:
    at=line.find(MARK)
    if at<0:return None
    f=line[at:].strip().split("|")
    if len(f)!=11 or not f[1].isdigit() or not f[2] or f[3] not in (
        "SLEEP","INVULNERABLE","RANGE","PASS"):
        raise TargetReplayError("BASE_TARGET_SOURCE_TRACE_SCHEMA_CHANGED")
    try:
        ints=[int(f[i]) for i in (4,5,6,7)]
        vals=[float(f[i]) for i in (8,9,10)]
    except ValueError:raise TargetReplayError("BASE_TARGET_SOURCE_TRACE_VALUES_INVALID")
    if (any(not math.isfinite(v) for v in vals)
        or ints[0] not in (0,1) or ints[1] not in (-1,0,1)
        or ints[2] not in (-1,1) or ints[3] not in (-1,0,1)):
        raise TargetReplayError("BASE_TARGET_SOURCE_VALUE_OUT_OF_RANGE")
    return {
        "time_ms":int(f[1]),"action":f[2],"native_stage_comparator_only":f[3],
        "source_sleep":ints[0],"source_invulnerable":ints[1],
        "source_invuln_check_was_reached":ints[2],
        "source_distance_enabled":ints[3],
        "source_range":vals[0],"source_combat_reach":vals[1],
        "source_distance":vals[2],
    }

def independent_basic_target_truth(f:dict)->tuple[int,str]:
    if f["source_sleep"]==1:
        return 0,"SOURCE_TARGET_SLEEPING"
    if f["source_invuln_check_was_reached"]!=1:
        raise TargetReplayError("SLEEP_FALSE_WITHOUT_INVULNERABILITY_PRE_FACT")
    if f["source_invulnerable"]==1:
        return 0,"SOURCE_TARGET_INVULNERABLE"
    if f["source_invulnerable"]!=0:
        raise TargetReplayError("SOURCE_INVULNERABLE_FACT_UNKNOWN_AT_EVALUATED_GATE")
    if f["source_distance_enabled"]==-1:
        raise TargetReplayError("TARGET_DISTANCE_GUARD_NOT_RECORDED_AFTER_INVULN")
    if f["source_distance_enabled"]==0:
        if f["source_distance"]!=-1:
            raise TargetReplayError("DISABLED_DISTANCE_HAS_SOURCE_DISTANCE_VALUE")
        return 1,"SOURCE_TARGET_NO_DISTANCE_RESTRICTION"
    if f["source_range"]<=0 or f["source_distance"]<0:
        raise TargetReplayError("RANGE_ENABLED_WITHOUT_VALID_DISTANCE_SOURCE")
    if f["source_distance"]>f["source_range"]+f["source_combat_reach"]:
        return 0,"SOURCE_DISTANCE_EXCEEDS_ACTION_RANGE_PLUS_REACH"
    return 1,"SOURCE_TARGET_WITHIN_RANGE"

def target_stage_to_bool(stage:str)->int:
    return int(stage=="PASS")

def direct_path(config:dict)->bool:
    return bool(config["target_if_NONE"] and not config["cycle_targets"]
                and not config["cycle_players"]
                and config["option_target_number"]==0)

def source_scan(trace:str,ir:dict,if_samples:list[dict])->dict:
    current=None
    counters=Counter()
    reasons=Counter()
    source_exits=Counter()
    stage_dist=Counter()
    examples=[]
    cursor=0
    for line in trace.splitlines():
        g=read_guard(line)
        if g is not None:
            if current is not None:raise TargetReplayError("NATIVE_PRE_SOURCE_OVERLAP")
            current={"key":exact_key(g),"config":None,"targets":[],
                     "base_entries":0,"ready_entries":0,"exits":[],"if":None}
            continue
        config=parse_config(line)
        if config is not None:
            if current is None or current["config"] is not None or exact_key(config)!=current["key"]:
                raise TargetReplayError("TARGET_CONFIG_NOT_EXACT_PRE_ACTION")
            current["config"]=config
            continue
        base_target=parse_target(line)
        if base_target is not None:
            if current is None:
                counters["unscoped_original_target_ready_calls"]+=1
                continue
            if (base_target["time_ms"],base_target["action"])==(
                current["key"][0],current["key"][3]):
                current["targets"].append(base_target)
            else:
                counters["other_action_target_ready_calls_inside_source_attempt"]+=1
            continue
        for marker,prop in ((BASE_ACTION_MARK,"base_entries"),
                            (BASE_READY_MARK,"ready_entries")):
            entry=read_method_entry(line,marker)
            if entry is not None:
                if current is not None and entry==(current["key"][0],current["key"][3]):
                    current[prop]+=1
                break
        else:
            e=parse_exit(line)
            if e is not None and current is not None:
                if (e["time_ms"],e["name"])==(current["key"][0],current["key"][3]):
                    current["exits"].append(e)
                continue
            fact=parse_fact(line)
            if fact is not None:
                if cursor>=len(if_samples) or if_samples[cursor]["key"]!=exact_key(fact):
                    raise TargetReplayError("IF_SOURCE_EVENT_NOT_CHRONOLOGICAL")
                if current is None or current["key"]!=if_samples[cursor]["key"]:
                    raise TargetReplayError("IF_EVENT_OUTSIDE_ITS_ACTION_ATTEMPT")
                current["if"]=if_samples[cursor]
                cursor+=1
                continue
            attempt=get_native_attempt(line)
            if attempt is None:continue
            if current is None or current["config"] is None or current["key"]!=exact_key(attempt):
                raise TargetReplayError("SELECTED_SOURCE_ATTEMPT_HAS_NO_PRE_TARGET_FACTS")
            key=current["key"]
            if key[1] not in ir["action_lists"] or not 1<=key[2]<=len(ir["action_lists"][key[1]]):
                raise TargetReplayError("PINNED_APL_ROW_MISSING")
            row=ir["action_lists"][key[1]][key[2]-1]
            counters["attempts"]+=1
            exits=current["exits"]
            if len(exits)==1:source_exits[exits[0]["reason"]]+=1
            status="UNKNOWN_TARGET_OVERRIDE_OR_DYNAMIC"
            good=None
            why=None
            if not direct_path(current["config"]):
                counters["UNKNOWN_dynamic_target_selection_route"]+=1
            elif len(exits)!=1:
                counters["UNKNOWN_base_action_ready_not_unique"]+=1
            elif len(current["targets"])!=1:
                counters["UNKNOWN_no_single_original_base_target_ready"]+=1
            else:
                observed=current["targets"][0]
                good,why=independent_basic_target_truth(observed)
                if good!=target_stage_to_bool(observed["native_stage_comparator_only"]):
                    raise TargetReplayError("INDEPENDENT_SOURCE_TARGET_VS_ORIGINAL_METHOD_EXIT_CONFLICT")
                counters["base_target_numeric_comparator_MATCH"]+=1
                reasons[why]+=1
                stage_dist[observed["native_stage_comparator_only"]]+=1
                state=exits[0]["reason"]
                if state=="TARGET_FALSE" and good!=0:
                    raise TargetReplayError("SOURCE_TARGET_FALSE_EXIT_BUT_BASIC_TARGET_TRUE")
                if state!="TARGET_FALSE" and good!=1:
                    raise TargetReplayError("SOURCE_BASE_NEXT_GUARD_REACHED_BUT_TARGET_FALSE")
                if good:
                    counters["base_direct_target_eligible_but_full_ready_UNKNOWN"]+=1
                    status="SOURCE_BASE_TARGET_NUMERIC_ELIGIBLE_ONLY"
                else:
                    counters["base_direct_target_ineligible_numeric"]+=1
                    status="SOURCE_BASE_TARGET_NUMERIC_EXCLUDED"
                if (row["action"] not in ("variable","run_action_list","call_action_list")
                    and current["base_entries"]==1 and
                    current["ready_entries"]==1 and
                    state=="FULL_BASE_TRUE" and good==1):
                    counters["physical_candidate_full_base_success_with_numeric_target_but_SUBCLASS_UNKNOWN"]+=1
            if len(examples)<20 and (status!="UNKNOWN_TARGET_OVERRIDE_OR_DYNAMIC" or
                                     (exits and exits[0]["reason"]=="TARGET_FALSE")):
                examples.append({"at_ms":key[0],"source_list":key[1],
                     "source_index":key[2]-1,"source_sha256":row["source_sha256"],
                     "action":row["action"],"target_route_status":status,
                     "source_first_exit":exits[0]["reason"] if len(exits)==1 else None,
                     "numeric_target_source_result":good,"numeric_reason":why,
                     "Native_ready_comparator_only":attempt["ready"],
                     "full_positive_ready_proven":False})
            current=None
    if current is not None or cursor!=len(if_samples) or not counters["attempts"]:
        raise TargetReplayError("TARGET_READY_COHORT_PRE_INCOMPLETE")
    return {
        "counts":dict(sorted(counters.items())),
        "numeric_target_source_reason_distribution":dict(sorted(reasons.items())),
        "Native_base_target_stage_distribution":dict(sorted(stage_dist.items())),
        "source_first_exit_reachability":dict(sorted(source_exits.items())),
        "source_target_eligible_examples":examples,
        "original_source_target_ready_boolean_USED_AS_OPERAND":False,
        "base_target_predicate_independently_calculated_from_source_inputs":True,
        "original_target_source_fields_not_independently_derived":True,
        "full_subclass_ready_independent":False,
        "full_priority_independent":False,
    }

def run(profile:Path,st:Path,two:Path,mst:Path,mtwo:Path):
    ir=parse_profile(profile.read_bytes(),require_source=True,
                     expected_git_blob=PINNED_FURY_BLOB)
    cases={}
    totals=Counter()
    for label,folder,targets,nif,nattempts in (
        ("stationary_st",st,1,255,1542),("stationary_two_target",two,2,222,1030),
        ("moving_st",mst,1,253,1650),("moving_two_target",mtwo,2,223,1186)):
        folder=folder.resolve(strict=True)
        prev=verify_folder(folder,targets,ir)
        raw=(folder/"simc_native_log.txt").read_bytes()
        trace=raw.decode("utf-8")
        samples=source_if_samples(trace,ir,prev)
        if len(samples)!=nif:raise TargetReplayError("EXISTING_INDEPENDENT_IF_FACT_COUNT_DRIFT")
        result=source_scan(trace,ir,samples)
        if result["counts"]["attempts"]!=nattempts:
            raise TargetReplayError("PINNED_FURY_NATIVE_ACTUAL_ATTEMPTS_DRIFT")
        totals.update(result["counts"])
        cases[label]={
            **result,"Native_log_sha256":sha(raw),
            "Native_binary_sha256":prev["native_binary_sha256"],
            "official_APL_sha256":prev["native_apl_sha256"]}
    if (totals["attempts"]!=5408 or
        len({x["Native_binary_sha256"] for x in cases.values()})!=1):
        raise TargetReplayError("FOUR_SCENARIO_TARGET_PROOF_ACCOUNTING_CHANGED")
    return {
        "schema":SCHEMA,"policy":POLICY,
        "status":"ORIGINAL_BASE_TARGET_ELIGIBILITY_NUMERIC_BOUNDED",
        "four_cases":cases,"totals":dict(sorted(totals.items())),
        "source_target_base_numeric_used_only_when_direct_and_unique":True,
        "native_source_target_verdict_POST_COMPARATOR_ONLY":True,
        "full_positive_action_ready_independently_proven":False,
        "General_Rotation_full_priority_independent":False,
        "WCL_API_calls":0,"MAIN_promoted":False}

def selftest():
    good={"source_sleep":0,"source_invulnerable":0,
          "source_invuln_check_was_reached":1,"source_distance_enabled":1,
          "source_range":5.0,"source_combat_reach":1.0,"source_distance":6.0}
    assert independent_basic_target_truth(good)[0]==1
    far={**good,"source_distance":6.001}
    assert independent_basic_target_truth(far)[0]==0
    sleeping={**good,"source_sleep":1,"source_invulnerable":-1,
              "source_invuln_check_was_reached":-1,"source_distance_enabled":-1,
              "source_distance":-1}
    assert independent_basic_target_truth(sleeping)[0]==0
    immune={**good,"source_invulnerable":1,"source_distance_enabled":-1}
    assert independent_basic_target_truth(immune)[0]==0
    no_distance={**good,"source_distance_enabled":0,"source_distance":-1}
    assert independent_basic_target_truth(no_distance)[0]==1
    line=MARK+"100|foo|PASS|0|0|1|1|5|1|6"
    assert parse_target(line)["source_distance"]==6
    cfg=parse_config(CFG+"100|default|1|foo|1|0|0|0|1")
    assert direct_path(cfg)
    assert not direct_path({**cfg,"option_target_number":2})
    ir=parse_profile(b"actions=foo\n",require_source=False)
    raw="\n".join((
        "ZROT_NATIVE_READY_GUARDS_PRE_V1|100|default|1|foo|1|1|0|-1|1",
        CFG+"100|default|1|foo|1|0|0|0|1",
        "ZROT_NATIVE_BASE_ACTION_READY_ENTER_V1|100|foo",
        "ZROT_NATIVE_BASE_READY_ENTER_V1|100|foo",
        line,
        "ZROT_NATIVE_BASE_POST_EXIT_V1|100|foo|FULL_BASE_TRUE",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|100|default|default|1|foo|1"))
    proof=source_scan(raw,ir,[])
    assert proof["counts"]["base_target_numeric_comparator_MATCH"]==1
    assert proof["counts"]["physical_candidate_full_base_success_with_numeric_target_but_SUBCLASS_UNKNOWN"]==1
    for bad in (
        raw.replace("|PASS|0|0|1|1|5|1|6","|RANGE|0|0|1|1|5|1|6"),
        raw.replace("ZROT_NATIVE_BASE_POST_EXIT_V1|100|foo|FULL_BASE_TRUE",
                    "ZROT_NATIVE_BASE_POST_EXIT_V1|100|foo|TARGET_FALSE"),
        raw.replace(CFG+"100|default|1|foo",CFG+"101|default|1|foo")):
        try:source_scan(bad,ir,[])
        except TargetReplayError:pass
        else:raise AssertionError("WRONG_OR_UNPINNED_TARGET_VERDICT_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":13,
            "Native_actual_not_executed":True,"WCL_API_calls":0,
            "full_ready_not_proven":True}

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
    if not any(inputs):out=selftest()
    elif all(inputs):out=run(*inputs)
    else:p.error("all five pinned source inputs required")
    data=(json.dumps(out,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(data)
        print("NATIVE_SOURCE_NUMERIC_TARGET_ELIGIBILITY_SHA256="+sha(data))
    else:print(data.decode(),end="")
if __name__=="__main__":main()
