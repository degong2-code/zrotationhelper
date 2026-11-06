#!/usr/bin/env python3
"""Strict replay of original source-line Arcane Orb ready() return branches.

This is an OBSERVATION of the actual C++ original branch path, not an
independently proven, full physical readiness oracle or gameplay advice.
No calls to ready/cooldown/RNG are made by the replay. Exact original
READY-root identity and original source action provenance are mandatory.

No arguments: synthetic negative tests for local no-parameters execution.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any

from general_rotation_arcane_orb_native_ready_stage_producer_v1 import (
    SCHEMA as PRODUCER,STAGE,PRE,READY_ROUTES,ACTION_ROUTES,PRE_SYMBOLS,
)
from general_rotation_time_scoped_priority_ir_v1 import SCHEMA as SWEEPS
from general_rotation_source_eligibility_decision_ir_v1 import POLICY

SCHEMA="ZrotOriginalArcaneOrbStrictReadyGateBranchPathV1"
STAGE_LOOKUP={
 "BASE":dict((name,(literal=="true")) for literal,name in READY_ROUTES),
 "ACTION":dict((name,(literal=="true")) for literal,name in ACTION_ROUTES),
}
class GateReplayError(ValueError):
    pass


def require(ok:bool,label:str)->None:
    if not ok:raise GateReplayError(label)


def _int(value:str,name:str)->int:
    require(re.fullmatch(r"-?[0-9]+",value) is not None,
            "MALFORMED_INTEGER_READY_STAGE_"+name)
    return int(value)


def _raw_PRE(raw:list[str])->dict[str,Any]:
    require(len(raw)==len(PRE_SYMBOLS)==16,"NATIVE_SOURCE_RAW_PRE_SHAPE")
    values={}
    for index,key in enumerate(PRE_SYMBOLS):
        if index in (2,3):
            try:value=float(raw[index])
            except ValueError as e:raise GateReplayError("READY_PRE_MANA_NOT_FLOAT") from e
            require(math.isfinite(value) and value>=0,"READY_PRE_MANA_NONFINITE")
        else:
            value=_int(raw[index],key)
        values[key]=value
    require(values["simc_ms"]>=0 and values["original_CPP_ready_root_id"]>0,
            "READY_PRE_ROOT_TIME_INVALID")
    require(values["cooldown_max_charges"]>=0 and
            values["cooldown_current_charge"]>=0 and
            values["cooldown_current_charge"]<=values["cooldown_max_charges"] and
            values["option_moving"] in (-1,0,1) and
            all(values[s] in (0,1) for s in (
                "option_cycle_targets","if_expr_present","sync_action_present",
                "executing_present","channeling_present")),
            "READY_PRE_SOURCE_BOUNDS_INVALID")
    # Raw timestamps are allowed negative: cooldowns already recovered,
    # negative GCD ready, or precombat absolute-ready values are distinct
    # from a false immediate negative spell-READY decision.
    return values


def replay(log:str,temporal:dict,producer:dict)->dict:
    require(temporal.get("schema")==SWEEPS and
            temporal.get("product_policy_id")==POLICY and
            temporal.get("independent_FULL_READY_proven")==0 and
            temporal.get("source_order_complete") is False and
            producer.get("schema")==PRODUCER and
            producer.get("source_revision")==
                "b522cded8c26b97dac03fdf56e57a03ec7e8faa6" and
            producer.get("official_action_cpp_git_blob_sha1")==
                "399ecd9453b3f30bfc2ebf2b3ffd8f56cce8f8d4" and
            producer.get("original_base_READY_return_branches")==7 and
            producer.get("original_ACTION_READY_return_branches")==12 and
            producer.get("new_ACTION_READY_calls")==0 and
            producer.get("new_RNG_calls")==0 and
            producer.get("new_cost_evaluations")==0 and
            producer.get("stage_marker")==STAGE and
            producer.get("source_root_PRE_marker")==PRE and
            producer.get("raw_source_PRE_fields")==list(PRE_SYMBOLS),
            "ORIGINAL_CPP_ARCANE_GATE_PRODUCER_PROVENANCE_FAILED")
    expected={}
    for sw in temporal["observed_time_scoped_selection_frontiers"]:
        for item in sw["observed_candidate_event_stream"]:
            if item.get("stage")!="ACTION_READY_CALLED" or
               item.get("source_action")!="arcane_orb":
                continue
            rid=item.get("original_action_ready_root_id")
            require(type(rid) is int and rid>0 and rid not in expected,
                    "DUPLICATE_ORIGINAL_CPP_ARCANE_READY_ROOT")
            require(type(item.get("simc_NATIVE_return_post_comparator")) is bool,
                    "ORIGINAL_POST_COMPARATOR_NOT_BOOLEAN")
            expected[rid]={
                "root":rid,"at_ms":sw["at_simc_ms"],
                "list":sw["source_list"],
                "source_row_sha256":item["source_row_sha256"],
                "source_ordinal":item["ordinal_one_based"],
                "original_NATIVE_POST":item["simc_NATIVE_return_post_comparator"],
                "observations":[],
            }
    require(len(expected)>0,"NO_ORIGINAL_CPP_ARCANE_ORB_READY_ROOTS")
    for raw in log.splitlines():
        is_pre=PRE in raw
        is_stage=STAGE in raw
        if not is_pre and not is_stage:continue
        if is_pre:
            require(raw.count(PRE)==1 and not is_stage,
                    "MALFORMED_OR_OVERLAPPED_CPP_READY_PRE_MARKERS")
            p=raw.split(PRE,1)[1].strip().split("|")
            state=_raw_PRE(p)
            rid=state["original_CPP_ready_root_id"]
            item=expected.get(rid)
            require(item is not None and state["simc_ms"]==item["at_ms"],
                    "READY_PRE_ROOT_OR_TIME_WRONG")
            item["observations"].append(("PRE",state))
        else:
            require(raw.count(STAGE)==1,
                    "MALFORMED_OR_REPEATED_CPP_BRANCH_MARK")
            p=raw.split(STAGE,1)[1].strip().split("|")
            require(len(p)==5,"READY_BRANCH_MARK_FIELDS_CHANGED")
            at,rid,phase,label,yes=p
            rid=_int(rid,"root")
            item=expected.get(rid)
            require(item is not None and _int(at,"simc_ms")==item["at_ms"] and
                    phase in STAGE_LOOKUP and
                    label in STAGE_LOOKUP[phase] and
                    yes in ("0","1") and
                    STAGE_LOOKUP[phase][label]==(yes=="1"),
                    "ORIGINAL_READY_BRANCH_SOURCE_ROUTE_OR_RETURN_MISMATCH")
            item["observations"].append((phase,label))
    totals=Counter()
    records=[]
    for rid,item in sorted(expected.items()):
        entries=item["observations"]
        # Current original Arcane Orb profile uses a single select root, no
        # cycle-target recursion; if this changes require a new nested scope
        # contract, never silently choose the final record of a shared root.
        require(len(entries)==3 and
                [k for k,_ in entries]==["PRE","BASE","ACTION"],
                "ORIGINAL_CPP_ARCANE_READY_NESTING_OR_COVERAGE_CHANGED")
        before=entries[0][1]
        base=entries[1][1]
        action=entries[2][1]
        require((base=="BASE_READY_TRUE")==
                (action!="ACTION_BASE_READY_FALSE"),
                "BASE_ACTION_GATE_SHORT_CIRCUIT_CONFLICT")
        check_success=STAGE_LOOKUP["ACTION"][action]
        require(item["original_NATIVE_POST"]==check_success,
                "CPP_NATIVE_RETURN_VS_READY_BRANCH_CONFLICT")
        totals["source_original_ready_roots"]+=1
        totals["action_stage_"+action]+=1
        totals["base_stage_"+base]+=1
        if check_success:totals["original_native_return_true"]+=1
        else:totals["original_native_return_false"]+=1
        records.append({
            "original_ready_root_id":rid,
            "at_simc_ms":item["at_ms"],
            "source_list":item["list"],
            "source_row_sha256":item["source_row_sha256"],
            "source_ordinal":item["source_ordinal"],
            "original_CPP_before_call_raw_PRE":before,
            "original_CXX_base_ready_return_stage":base,
            "original_CXX_action_ready_return_stage":action,
            "source_CXX_POST_selection_boolean":check_success,
            "independent_full_skill_READY_proven":False,
            "independent_prior_candidate_unavailable_proven":False,
            "user_dummy_error_verdict":"UNKNOWN",
        })
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "source_original_CPP_branch_path_observed":True,
        "original_READY_calls_added":0,
        "original_rng_calls_added":0,
        "original_source_if_re_evaluations_added":0,
        "original_target_select_calls_added":0,
        "counts":dict(sorted(totals.items())),
        "original_arcane_orb_ready_roots":records,
        "independent_full_action_READY_gate_closure":False,
        "original_CXX_results_are_POST_not_independent_PRE":True,
        "WCL_strict_timestamp_PRE_proven":False,
        "WoW_current_addon_API_proven":False,
        "WCL_API_calls":0,
    }


def selftest()->dict:
    state=list(map(str,[100,7,90,100,1,2,1000,0,0,0,-1,0,1,0,0,0]))
    assert _raw_PRE(state)["mana_current"]==90
    for change in ({3:"nan"},{4:"3"},{13:"9"},{1:"-1"}):
        bad=state.copy()
        for index,val in change.items():bad[index]=val
        try:_raw_PRE(bad)
        except GateReplayError:pass
        else:raise AssertionError("FORGED_OR_NONFINITE_NATIVE_CPP_PRE_ACCEPTED")
    assert STAGE_LOOKUP["ACTION"]["ACTION_RNG_FALSE_POSITIVE_TRUE"] is True
    assert STAGE_LOOKUP["BASE"]["BASE_RESOURCE_UNAFFORDABLE"] is False
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":7,"real_CPP_executed":False,
            "independent_FULL_READY_proven":0,"WCL_API_calls":0}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--temporal",type=Path)
    p.add_argument("--producer",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    inputs=(a.native_log,a.temporal,a.producer)
    if all(x is None for x in inputs):out=selftest()
    elif all(x is not None for x in inputs):
        out=replay(a.native_log.read_text(encoding="utf8"),
                   json.loads(a.temporal.read_bytes()),
                   json.loads(a.producer.read_bytes()))
    else:p.error("all three original Native sources required")
    data=(json.dumps(out,sort_keys=True,separators=(",",":"),
                     allow_nan=False)+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(data)
    else:
        import sys
        sys.stdout.buffer.write(data)

if __name__=="__main__":main()
