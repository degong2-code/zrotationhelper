#!/usr/bin/env python3
"""Bounded tri-state replay of real Native base action_ready postguard path.

Original SimC base action_ready() exit labels attest actual visited source
branches but are NOT independently derived full readiness. Only three
postguard predicates have separately sampled source PRE fields and an
independent Python Boolean: exact line cooldown ready time, requested
movement option, repeat-cast prohibition, plus cycle-target bypass.
Validate these numerical predicates only when Native source path reaches
the corresponding branch; no injected outcomes or extra target/sync/RNG
method calls. All missing base route, subclass overrides, target, movement
directionality, sync, RNG and IF conditions remain UNKNOWN for a complete
positive readiness proof.

Model scope: generic General Rotation, no raid/boss plan or WCL.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile
from simc_native_if_pre_operand_replay_v1 import (
    PINNED_FURY_BLOB, exact_key, get_native_attempt, verify_folder,
)
from simc_native_ready_guard_witness_replay_v1 import (
    read_guard, read_method_entry, replay_log
)
from simc_native_ready_guard_witness_instrument_v1 import BASE_ACTION_MARK
from simc_native_resource_cost_replay_v1 import replay_resource_trace
from simc_native_postguard_source_instrument_v1 import (
    LINE_MARK, CAST_MARK, EXIT_MARK, REASONS
)

SCHEMA="ZrotNativeSourcePostguardConditionalNumericWitnessV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

class PostguardReplayError(ValueError):
    pass

def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def parse_line(line:str):
    i=line.find(LINE_MARK)
    if i<0:return None
    p=line[i:].strip().split("|")
    if len(p)!=12 or not p[1].isdigit() or not p[3].isdigit() or not p[2] or not p[4]:
        raise PostguardReplayError("LINE_POSTGUARD_RAW_SOURCE_FORMAT")
    try: fields=[int(x) for x in p[5:]]
    except ValueError:raise PostguardReplayError("LINE_POSTGUARD_RAW_SOURCE_NONINTEGER")
    present,ready_ms,cycle,target_count,moving_option,moving,sync=fields
    if (present not in (0,1) or cycle not in (0,1) or moving not in (0,1)
        or sync not in (0,1) or target_count<0 or moving_option not in (-1,0,1)
        or (not present and ready_ms!=0)):
        raise PostguardReplayError("LINE_POSTGUARD_RAW_SOURCE_OUT_OF_RANGE")
    return {
        "time_ms":int(p[1]),"list":p[2],"ordinal":int(p[3]),"native_name":p[4],
        "line_cd_present":present,"line_cd_ready_ms":ready_ms,
        "cycle_targets":cycle,"target_count":target_count,
        "requested_moving":moving_option,"actor_moving":moving,
        "has_sync_action":sync,
    }

def parse_cast(line:str):
    i=line.find(CAST_MARK)
    if i<0:return None
    p=line[i:].strip().split("|")
    if len(p)!=11 or not p[1].isdigit() or not p[3].isdigit() or not p[2] or not p[4]:
        raise PostguardReplayError("CAST_POSTGUARD_RAW_SOURCE_FORMAT")
    try: values=[int(x) for x in p[5:]]
    except ValueError:raise PostguardReplayError("CAST_POSTGUARD_NONINTEGER")
    if any(x not in (0,1) for x in values):
        raise PostguardReplayError("CAST_POSTGUARD_BOOL_NOT_SOURCE_PINNED")
    rng,has_if,allow,last_same,last_positive,executing=values
    return {
        "time_ms":int(p[1]),"list":p[2],"ordinal":int(p[3]),"native_name":p[4],
        "skill_rng_condition":rng,"has_if":has_if,
        "allow_repeat_while_casting":allow,"last_action_is_self":last_same,
        "last_action_cast_positive":last_positive,"executing_self":executing,
    }

def parse_exit(line:str):
    i=line.find(EXIT_MARK)
    if i<0:return None
    p=line[i:].strip().split("|")
    if len(p)!=4 or not p[1].isdigit() or not p[2] or p[3] not in REASONS:
        raise PostguardReplayError("BASE_POSTGUARD_EXIT_RECORD_NOT_PINNED")
    return {"time_ms":int(p[1]),"name":p[2],"reason":p[3]}

def independent_postguard_subset(raw_line:dict,raw_cast:dict)->dict:
    if exact_key(raw_line)!=exact_key(raw_cast):
        raise PostguardReplayError("RAW_LINE_CAST_SOURCE_POINTER_NOT_EQUAL")
    now=raw_line["time_ms"]
    line_down=(raw_line["line_cd_ready_ms"]>now if raw_line["line_cd_present"]
               else None)
    moving_mismatch=(raw_line["requested_moving"]!=-1 and
                     raw_line["requested_moving"]!=raw_line["actor_moving"])
    repeat=(not raw_cast["allow_repeat_while_casting"] and
            ((raw_cast["last_action_is_self"] and
              raw_cast["last_action_cast_positive"]) or
             raw_cast["executing_self"]))
    cycle=(raw_line["cycle_targets"]==1 and raw_line["target_count"]>1)
    return {"line_cooldown_down":line_down,
            "moving_option_mismatch":bool(moving_mismatch),
            "repeat_cast_prohibited":bool(repeat),
            "cycle_targets_fast_path":bool(cycle),
            "target_selection_independently_known":False,
            "movement_directionality_independently_known":False,
            "sync_action_ready_independently_known":False,
            "skill_rng_independently_known":raw_cast["skill_rng_condition"]==0,
            "if_ast_independently_joined":False}

def replay_trace(trace:str,ir:dict):
    pending=None
    stack=[]
    c=Counter()
    exit_distribution=Counter()
    numeric_gates=Counter()
    unknowns=Counter()
    examples=[]
    for line in trace.splitlines():
        g=read_guard(line)
        if g is not None:
            if pending is not None or stack:
                raise PostguardReplayError("SOURCE_POSTGUARD_NESTED_ATTEMPTS_NOT_SUPPORTED")
            pending={"guard":g,"line":None,"cast":None,"exits":[]}
            continue
        l=parse_line(line)
        if l is not None:
            if pending is None or pending["line"] is not None or exact_key(l)!=exact_key(pending["guard"]):
                raise PostguardReplayError("POSTGUARD_LINE_PRE_POINTER_MISMATCH")
            pending["line"]=l
            continue
        cast=parse_cast(line)
        if cast is not None:
            if (pending is None or pending["line"] is None or pending["cast"] is not None
                or exact_key(cast)!=exact_key(pending["guard"])):
                raise PostguardReplayError("POSTGUARD_CAST_PRE_POINTER_MISMATCH")
            pending["cast"]=cast
            continue
        entry=read_method_entry(line,BASE_ACTION_MARK)
        if entry is not None:
            if pending is not None:
                stack.append(entry)
            continue
        exit_record=parse_exit(line)
        if exit_record is not None:
            if pending is None:
                c["unscoped_native_source_exits"]+=1
                continue
            if not stack:
                raise PostguardReplayError("BASE_ACTION_EXIT_WITHOUT_MATCHING_ENTRY")
            top=stack.pop()
            if top!=(exit_record["time_ms"],exit_record["name"]):
                raise PostguardReplayError("BASE_ACTION_EXIT_STACK_SOURCE_IDENTITY_MISMATCH")
            pending["exits"].append(exit_record)
            c["base_action_exit_events"]+=1
            continue
        attempt=get_native_attempt(line)
        if attempt is None:
            continue
        if (pending is None or pending["line"] is None or pending["cast"] is None
            or stack or exact_key(attempt)!=exact_key(pending["guard"])):
            raise PostguardReplayError("NATIVE_ATTEMPT_POSTGUARD_PRE_PAIR_INCOMPLETE")
        name=attempt["list"]
        idx=attempt["ordinal"]-1
        if name not in ir["action_lists"] or not 0<=idx<len(ir["action_lists"][name]):
            raise PostguardReplayError("NATIVE_ATTEMPT_SOURCE_APL_INDEX_CHANGED")
        c["actual_native_ATTEMPTS"]+=1
        raw_line=pending["line"]
        raw_cast=pending["cast"]
        independent=independent_postguard_subset(raw_line,raw_cast)
        matched=[e for e in pending["exits"]
                 if e["name"]==attempt["native_name"] and
                 e["time_ms"]==attempt["time_ms"]]
        if not matched:
            c["UNKNOWN_no_base_action_ready_exit"]+=1
            unknowns["subclass_override_or_unobserved"]+=1
        elif len(matched)!=1:
            c["UNKNOWN_ambiguous_base_action_ready_exit"]+=1
            unknowns["multiple_same_identity_base_returns"]+=1
        else:
            observed=matched[0]["reason"]
            exit_distribution[observed]+=1
            c["source_observed_base_exit"]+=1
            numeric_expected={
                "LINE_COOLDOWN_FALSE":("line_cooldown_down",True),
                "MOVING_OPTION_FALSE":("moving_option_mismatch",True),
                "REPEAT_CAST_FALSE":("repeat_cast_prohibited",True),
                "CYCLE_TRUE":("cycle_targets_fast_path",True),
            }
            if observed in numeric_expected:
                key,required=numeric_expected[observed]
                if independent[key] is None:
                    c["UNKNOWN_raw_numeric_predicate"]+=1
                elif independent[key]!=required:
                    raise PostguardReplayError(
                        "SOURCE_BASE_POSTGUARD_NATIVE_PATH_VS_RAW_NUMERIC_CONFLICT:"+observed)
                else:
                    c["independent_raw_predicate_matches_reached_native_guard"]+=1
                    numeric_gates[observed]+=1
                    if len(examples)<16:
                        examples.append({
                            "source_list":name,"source_index":idx,
                            "action":attempt["native_name"],"at_ms":attempt["time_ms"],
                            "independent_subset":independent,
                            "native_exit_source_verification_only":observed,
                        })
            elif observed=="FULL_BASE_TRUE":
                c["Native_base_full_path_true_not_independent_positive"]+=1
                unknowns["target_movement_directionality_and_other_positive_guards"]+=1
                # The direct numeric guards should all be false if the
                # actual base method reached its terminal true return.
                for key in ("line_cooldown_down","moving_option_mismatch","repeat_cast_prohibited"):
                    if independent[key] is True:
                        raise PostguardReplayError(
                            "SOURCE_BASE_FINAL_TRUE_CONTRADICTS_PRE_NUMERIC:"+key)
            else:
                unknowns["nonindependent_or_base_guard_branch_"+observed]+=1
            if observed in ("SKILL_RNG_TRUE","SKILL_RNG_FALSE") and not raw_cast["skill_rng_condition"]:
                raise PostguardReplayError("SKILL_RNG_EXIT_WITHOUT_SOURCE_GATE")
            if observed=="CYCLE_TRUE" and not independent["cycle_targets_fast_path"]:
                raise PostguardReplayError("CYCLE_NATIVE_SOURCE_EXIT_WITHOUT_PRE_GATE")
            if observed.endswith("FALSE") and attempt["ready"]==1:
                # Subclass might change the base result; retain a
                # diagnostic without falsely claiming universal causality.
                c["source_base_false_but_virtual_attempt_true_unknown_override"]+=1
            if observed=="FULL_BASE_TRUE" and attempt["ready"]==0:
                c["source_base_true_but_virtual_attempt_false_unknown_override"]+=1
        pending=None
    if pending is not None or stack or c["actual_native_ATTEMPTS"]<1:
        raise PostguardReplayError("UNPAIRED_POSTGUARD_SOURCE_AT_EOF")
    if (c["source_observed_base_exit"]+
        c["UNKNOWN_no_base_action_ready_exit"]+
        c["UNKNOWN_ambiguous_base_action_ready_exit"] !=
        c["actual_native_ATTEMPTS"]):
        raise PostguardReplayError("SOURCE_BASE_EXIT_COHORT_ACCOUNTING_CHANGED")
    return {
        "counts":dict(sorted(c.items())),
        "actual_source_base_exit_reason_distribution":dict(sorted(exit_distribution.items())),
        "numeric_guards_proved_at_native_branch":dict(sorted(numeric_gates.items())),
        "unknown_reasons":dict(sorted(unknowns.items())),
        "bounded_independent_numeric_examples":examples,
        "source_native_branch_return_is_observed_not_independent":True,
        "positive_action_ready_not_proven":True,
        "full_source_order_priority_not_proven":True,
    }

def run(profile:Path,st:Path,two:Path,moving_st:Path,moving_two:Path):
    ir=parse_profile(profile.read_bytes(),require_source=True,
                     expected_git_blob=PINNED_FURY_BLOB)
    cases={}
    overall=Counter()
    aggregate_exits=Counter()
    for label,root,targets,expected in (
        ("stationary_st",st,1,1542),
        ("stationary_two_target",two,2,1030),
        ("moving_st",moving_st,1,1650),
        ("moving_two_target",moving_two,2,1186)
    ):
        root=root.resolve(strict=True)
        provenance=verify_folder(root,targets,ir)
        raw=(root/"simc_native_log.txt").read_bytes()
        trace=raw.decode("utf-8")
        base=replay_log(trace,ir)
        resource=replay_resource_trace(trace,ir)
        x=replay_trace(trace,ir)
        counts=x["counts"]
        if (counts["actual_native_ATTEMPTS"]!=expected or
            base["counts"]["native_ATTEMPT_records"]!=expected or
            resource["counts"]["attempts"]!=expected or
            provenance["counts"]["all_native_action_ready_attempts"]!=expected):
            raise PostguardReplayError("PINNED_NATIVE_SOURCE_COHORT_CHANGED")
        for key,val in counts.items():
            overall[key]+=val
        aggregate_exits.update(x["actual_source_base_exit_reason_distribution"])
        cases[label]={
            **x,"native_log_sha256":sha(raw),
            "native_binary_sha256":provenance["native_binary_sha256"],
        }
    if overall["actual_native_ATTEMPTS"]!=5408 or len({
        c["native_binary_sha256"] for c in cases.values()})!=1:
        raise PostguardReplayError("ST_2T_MOVING_SOURCE_PARITY_NOT_PINNED")
    return {
        "schema":SCHEMA,"scope_policy_id":POLICY,
        "status":"SOURCE_BASE_POSTGUARD_EXIT_REACHABILITY_PLUS_BOUNDED_NUMERIC",
        "four_scenarios":cases,
        "totals":dict(sorted(overall.items())),
        "aggregate_actual_source_base_return_reasons":
            dict(sorted(aggregate_exits.items())),
        "native_source_branch_used_as_numeric_operand":False,
        "full_action_ready_independent":False,
        "full_general_rotation_priority_independent":False,
        "general_rotation_complete":False,
        "WCL_API_calls":0,"MAIN_promoted":False,
    }

def selftest():
    ir=parse_profile(b"actions=foo\n",require_source=False)
    line=parse_line(LINE_MARK+"100|default|1|foo|1|200|0|1|1|0|0")
    cast=parse_cast(CAST_MARK+"100|default|1|foo|0|0|0|1|1|0")
    f=independent_postguard_subset(line,cast)
    assert f["line_cooldown_down"] is True
    assert f["moving_option_mismatch"] is True
    assert f["repeat_cast_prohibited"] is True
    assert f["cycle_targets_fast_path"] is False
    trace="\n".join((
        "ZROT_NATIVE_READY_GUARDS_PRE_V1|100|default|1|foo|1|1|0|-1|1",
        LINE_MARK+"100|default|1|foo|1|200|0|1|1|0|0",
        CAST_MARK+"100|default|1|foo|0|0|0|1|1|0",
        BASE_ACTION_MARK+"100|foo",
        EXIT_MARK+"100|foo|LINE_COOLDOWN_FALSE",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|100|default|default|1|foo|0"
    ))
    x=replay_trace(trace,ir)
    assert x["counts"]["actual_native_ATTEMPTS"]==1
    assert x["counts"]["independent_raw_predicate_matches_reached_native_guard"]==1
    for malformed in (
        trace.replace("1|200|0|1|1|0|0","1|20|0|1|1|0|0"),
        trace.replace("ZROT_NATIVE_BASE_POST_EXIT_V1|100|foo|LINE_COOLDOWN_FALSE",
                      "ZROT_NATIVE_BASE_POST_EXIT_V1|100|bar|LINE_COOLDOWN_FALSE"),
        trace.replace("ZROT_NATIVE_SELECT_V1|ATTEMPT|100|default|default|1|foo|0",
                      "ZROT_NATIVE_SELECT_V1|ATTEMPT|100|default|default|2|foo|0"),
        trace.replace(CAST_MARK+"100|default|1|foo|0|0|0|1|1|0",""),
    ):
        try:replay_trace(malformed,ir)
        except PostguardReplayError:pass
        else:raise AssertionError("INVALID_SOURCE_POSTGUARD_EVIDENCE_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":15,
            "actual_native_run":False,"full_ready_proven":False,
            "WCL_API_calls":0}

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
    if not any(inputs):value=selftest()
    elif all(inputs):value=run(*inputs)
    else:p.error("all five pinned Native source inputs required")
    raw=(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
        print("NATIVE_POSTGUARD_SOURCE_NUMERIC_SHA256="+sha(raw))
    else:print(raw.decode(),end="")

if __name__=="__main__":main()
