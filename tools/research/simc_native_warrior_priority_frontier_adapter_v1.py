#!/usr/bin/env python3
"""Warrior source semantic adapter for generic source candidate frontier.

May *add* necessary-negative physical spell exclusions only if:
 - original Warrior ready() called exactly once for SAME Native APL row
 - original warrior_action_t::action_ready returned via base, not replacement
 - original action_t::action_ready source first-exit BASE_READY_FALSE
 - source raw distance/range or channel gate independently computes false
 - source observed Native attempt false (comparison only)
 - source operation is not an APL command/control.

NO independent positive ready or optimal priority is claimed. This module
contains Warrior-specific semantics, not the generic engine.
"""
from __future__ import annotations
from collections import Counter
from simc_native_warrior_spec_ready_replay_v1 import (
    read_warrior_ready,read_warrior_action,independent_warrior_numeric,
    WarriorReplayError
)

class WarriorPriorityAdapter:
    def __init__(self):
        self.counts=Counter()

    def consume(self,line:str,pending:dict|None):
        r=read_warrior_ready(line)
        if r is not None:
            if pending is None:
                self.counts["unscoped_ready"]+=1
            elif (r["time_ms"],r["native_name"])==(
                pending["pre"]["time_ms"],pending["pre"]["native_name"]):
                pending.setdefault("warrior_ready",[]).append(r)
            else:
                self.counts["nested_or_other_action_ready"]+=1
            return
        a=read_warrior_action(line)
        if a is not None:
            if pending is None:
                self.counts["unscoped_action_route"]+=1
            elif (a["time_ms"],a["native_name"])==(
                pending["pre"]["time_ms"],pending["pre"]["native_name"]):
                pending.setdefault("warrior_action",[]).append(a)
            else:
                self.counts["nested_or_other_action_route"]+=1

    def improve_negative(self,pending:dict,attempt:dict,row:dict)->dict:
        if row["status"].startswith("EXCLUDED_"):
            self.counts["already_independently_excluded"]+=1
            return row
        if row["source_action"] in (
            "variable","run_action_list","call_action_list",
            "swap_action_list","sequence","strict_sequence"):
            self.counts["APL_control_not_physical_spell"]+=1
            return row
        if row["source_base_exit_observed"]!="BASE_READY_FALSE":
            self.counts["not_source_base_ready_false"]+=1
            return row
        if (pending["base_action_entries"]!=1 or
            pending["base_ready_entries"]!=1 or attempt["ready"]!=0):
            self.counts["unproven_base_method_entry_or_false"]+=1
            return row
        ready=pending.get("warrior_ready",[])
        action=pending.get("warrior_action",[])
        if len(ready)!=1 or len(action)!=1:
            self.counts["unknown_warrior_method_path_identity"]+=1
            return row
        a=action[0];w=ready[0]
        if a["route"] not in (
            "NO_REPLACEMENT_OR_ZERO_DURATION",
            "REPLACEMENT_INACTIVE_QUALIFIED_BASE"
        ):
            self.counts["replacement_delegated_unknown"]+=1
            return row
        if a["source_native_action_ready_comparator"]!=attempt["ready"]:
            raise WarriorReplayError("WARRIOR_ROUTE_COMPARATOR_CONFLICT")
        if w["source_native_ready_boolean_comparator"]!=0:
            self.counts["warrior_source_positive_not_excludable"]+=1
            return row
        calc=independent_warrior_numeric(w)
        if not calc["compared"]:
            self.counts["warrior_raw_numeric_not_decidable"]+=1
            return row
        if calc["numeric_route"]=="DISTANCE_TOO_FAR":
            row["status"]="EXCLUDED_BY_INDEPENDENT_WARRIOR_DISTANCE_FALSE"
            row["source_exclusion_reason"]="warrior_distance_to_move_exceeds_range"
        elif calc["numeric_route"]=="CHANNELING_NOT_USABLE":
            row["status"]="EXCLUDED_BY_INDEPENDENT_WARRIOR_CHANNEL_FALSE"
            row["source_exclusion_reason"]="warrior_channel_or_bladestorm_blocks"
        else:
            self.counts["warrior_numeric_true_not_excludable"]+=1
            return row
        row["warrior_numeric_source"]={
            "distance_to_move":w["distance_to_move"],"range":w["range"],
            "channel_or_bladestorm_original_source_fact":
                w["source_original_channel_or_bladestorm"],
            "usable_while_channeling":w["usable_while_channeling"],
            "independently_recomputed_negative":calc["numeric_route"],
        }
        self.counts["new_source_warrior_numeric_exclusion"]+=1
        return row

    def summary(self)->dict:
        return dict(sorted(self.counts.items()))


def selftest():
    a=WarriorPriorityAdapter()
    pending={
        "pre":{"time_ms":10,"native_name":"foo"},
        "base_action_entries":1,"base_ready_entries":1,
    }
    a.consume("ZROT_WARRIOR_READY_PATH_PRE_V1|10|foo|DISTANCE_TOO_FAR|11|5|-1|0|0",pending)
    a.consume("ZROT_WARRIOR_ACTION_READY_PATH_PRE_V1|10|foo|NO_REPLACEMENT_OR_ZERO_DURATION|0",pending)
    row={
        "status":"UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED",
        "source_action":"foo",
        "source_base_exit_observed":"BASE_READY_FALSE",
        "source_exclusion_reason":None,
    }
    result=a.improve_negative(pending,{"ready":0},row)
    assert result["status"]=="EXCLUDED_BY_INDEPENDENT_WARRIOR_DISTANCE_FALSE"
    assert a.summary()["new_source_warrior_numeric_exclusion"]==1
    unchanged=a.improve_negative(pending,{"ready":0},dict(row,status="EXCLUDED_BY_INDEPENDENT_IF_FALSE_AND_BASE_EXIT"))
    assert unchanged["status"]=="EXCLUDED_BY_INDEPENDENT_IF_FALSE_AND_BASE_EXIT"
    none=a.improve_negative(dict(pending,warrior_ready=[]),{"ready":0},
                            dict(row,status="UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED"))
    assert none["status"]=="UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED"
    chan=WarriorPriorityAdapter()
    p=dict(pending,warrior_ready=[])
    chan.consume("ZROT_WARRIOR_READY_PATH_PRE_V1|10|foo|CHANNELING_NOT_USABLE|1|5|1|0|0",p)
    rr=chan.improve_negative(p,{"ready":0},
                             dict(row,status="UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED"))
    assert rr["status"]=="EXCLUDED_BY_INDEPENDENT_WARRIOR_CHANNEL_FALSE"
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":7,
            "WCL_API_calls":0,"full_positive_ready":False}

if __name__=="__main__":
    import json
    print(json.dumps(selftest(),sort_keys=True))
