#!/usr/bin/env python3
"""Original source-return branches for earlier ST/2T Arcane Mage competitors.

The generic source-return stage and the specialization READY override stage
are recorded as separate evidence axes, both keyed by the SAME original
SimC action_ready() root ID. The original Native action priority decision
remains separate from whole-ability mechanical availability or optimality.

In particular prismatic_bolt_t::ready and arcane_missiles_t::ready may
reject BEFORE action_t::ready executes. A missing BASE event is not silently
inferred to be TRUE. Positive full physical READY remains unsupported.

CLI no-parameters: synthetic no-network source strictness test.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from general_rotation_arcane_competitor_native_route_producer_v1 import (
    SCHEMA as PRODUCER,MARK_ACTION,MARK_CLASS,MARK_PRE,RIVALS
)
from general_rotation_arcane_orb_native_ready_stage_producer_v1 import (
    READY_ROUTES,ACTION_ROUTES
)
from general_rotation_time_scoped_priority_ir_v1 import SCHEMA as TEMPORAL
from general_rotation_source_eligibility_decision_ir_v1 import POLICY

SCHEMA="ZrotOriginalArcaneThreeCompetitorNativeExactReadyRouteV1"
SOURCE_REVS="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
GATES={
    "BASE":dict((name,lit=="true") for lit,name in READY_ROUTES),
    "ACTION":dict((name,lit=="true") for lit,name in ACTION_ROUTES),
}
CANDIDATES=("prismatic_bolt","arcane_orb","arcane_barrage","arcane_missiles",
            "prismatic_bolt","arcane_orb")
TARGET_TIMES=(7667,14950)

class RivalNativeRouteError(ValueError):pass

def need(ok:bool,why:str)->None:
    if not ok:raise RivalNativeRouteError(why)

def _integer(raw:str,reason:str)->int:
    need(re.fullmatch(r"[0-9]+",raw) is not None,
         "NON_INTEGER_SOURCE_CPP_BRANCH_"+reason)
    return int(raw)

def _read(log:str,marker:str,nfields:int)->list[list[str]]:
    out=[]
    for line in log.splitlines():
        if marker not in line:continue
        need(line.count(marker)==1,
             "REPEATED_ORIGINAL_CPP_SOURCE_MARKER:"+marker)
        fields=line.split(marker,1)[1].strip().split("|")
        need(len(fields)==nfields,
             "CHANGED_ORIGINAL_CPP_SOURCE_FIELDS:"+marker)
        out.append(fields)
    return out

def replay(log:str,temporal:dict,producer:dict)->dict:
    need(temporal.get("schema")==TEMPORAL and
         temporal.get("product_policy_id")==POLICY and
         temporal.get("source_order_complete") is False and
         temporal.get("independent_FULL_READY_proven")==0 and
         temporal.get("target_count")==2 and
         producer.get("schema")==PRODUCER and
         producer.get("source_revision")==SOURCE_REVS and
         producer.get("stage_marker")==MARK_ACTION and
         producer.get("derived_return_marker")==MARK_CLASS and
         producer.get("derived_pre_marker")==MARK_PRE and
         producer.get("added_action_READY_calls")==0 and
         producer.get("added_RNG_calls")==0 and
         producer.get("added_cost_affordable_calls")==0 and
         producer.get("added_target_selection_calls")==0 and
         producer.get("extra_read_only_buff_check_PER_derived_READY")==1 and
         producer.get("sources")==list(RIVALS),
         "ORIGINAL_NATIVE_COMPETITOR_ROOT_SOURCE_CONTRACT_DRIFT")
    all_rows={}
    snapshots=[]
    for sweep in temporal["observed_time_scoped_selection_frontiers"]:
        swid=sweep["sweep_call_id"]
        for item in sweep["observed_candidate_event_stream"]:
            if (item.get("stage")!="ACTION_READY_CALLED" or
                item.get("source_action") not in RIVALS):
                continue
            rid=item["original_action_ready_root_id"]
            need(type(rid) is int and rid>0 and rid not in all_rows,
                 "DUPLICATE_SOURCE_COMPETITOR_READY_ROOT")
            need(type(item.get("simc_NATIVE_return_post_comparator")) is bool,
                 "SOURCE_COMPETITOR_ORIGINAL_CPP_POST_NOT_BOOLEAN")
            all_rows[rid]={
                "source_root_id":rid,"at_ms":sweep["at_simc_ms"],
                "source_list":sweep["source_list"],
                "source_action":item["source_action"],
                "ordinal":item["ordinal_one_based"],
                "source_row_sha256":item["source_row_sha256"],
                "original_native_POST":item["simc_NATIVE_return_post_comparator"],
                "events":[],
            }
        if (sweep["at_simc_ms"] in TARGET_TIMES and
            sweep["source_list"]=="spellslinger"):
            es=[e for e in sweep["observed_candidate_event_stream"]
                if e.get("stage")=="ACTION_READY_CALLED"]
            if (len(es)==6 and tuple(e["source_action"] for e in es)==CANDIDATES
                and all(e["simc_NATIVE_return_post_comparator"] is False
                        for e in es[:5])
                and es[5]["simc_NATIVE_return_post_comparator"] is True):
                snapshots.append((sweep,es))
    need(len(all_rows)>8,"EMPTY_CPP_COMPETITOR_READY_COHORT")
    need(len(snapshots)==2 and
         set(sweep["at_simc_ms"] for sweep,_ in snapshots)==set(TARGET_TIMES),
         "ORIGINAL_SOURCE_PRIOR_SELECTED_SWEEP_IDENTITY_CHANGED")
    for fields in _read(log,MARK_ACTION,5):
        ms,rid,phase,label,boolval=fields
        at=_integer(ms,"time");id_=_integer(rid,"id")
        row=all_rows.get(id_)
        need(row is not None and row["at_ms"]==at and
             phase in GATES and label in GATES[phase] and
             boolval in ("0","1") and
             GATES[phase][label]==(boolval=="1"),
             "FOREIGN_OR_FAKE_ORIGINAL_CPP_ACTION_GATE_BRANCH")
        row["events"].append((phase,label,boolval=="1"))
    for fields in _read(log,MARK_PRE,6):
        ms,rid,which,buff,initial,delay=fields
        at=_integer(ms,"time");id_=_integer(rid,"id")
        row=all_rows.get(id_)
        need(row is not None and row["at_ms"]==at and
             which==row["source_action"] and
             which in ("prismatic_bolt","arcane_missiles") and
             _integer(buff,"buff")<=50 and
             initial in ("0","1") and delay in ("0","1"),
             "UNTRUSTED_CPP_SPECIALIZATION_PRE")
        row["events"].append(("CLASS_PRE",{
            "buff_stack":int(buff),"gained_initial_clearcasting":int(initial),
            "allow_arcane_missiles_delay":int(delay)}))
    for fields in _read(log,MARK_CLASS,5):
        ms,rid,which,label,result=fields
        at=_integer(ms,"time");id_=_integer(rid,"id")
        row=all_rows.get(id_)
        valid=("PRISMATIC_BUFF_NOT_PRESENT","CLASS_BASE_READY_DELEGATED"
               ) if which=="prismatic_bolt" else (
               "MISSILES_CLEARCASTING_MISSING",
               "MISSILES_IMMEDIATE_CLEARCAST_DELAY","CLASS_BASE_READY_DELEGATED")
        need(row is not None and row["at_ms"]==at and
             which==row["source_action"] and label in valid and
             result in ("0","1") and
             (result=="0" if label!="CLASS_BASE_READY_DELEGATED" else True),
             "INVALID_CPP_SPECIALIZATION_CLASS_READY_RETURN")
        row["events"].append(("CLASS",label,result=="1"))
    totals=Counter()
    validated={}
    for rid,row in sorted(all_rows.items()):
        # Methods log at actual execution order: PRE class then maybe BASE
        # then CLASS return, finally ACTION ready outcome. Base may be
        # skipped for derived false local guards, never treated as TRUE.
        seq=row["events"]
        names=[e[0] for e in seq]
        who=row["source_action"]
        if who=="arcane_barrage":
            need(names==["BASE","ACTION"],
                 "BARRAGE_UNEXPECTED_VIRTUAL_READY_BRANCH_PATH")
            base=seq[0];end=seq[1]
            class_reason=None
            derived=None
        else:
            need(names in (
                ["CLASS_PRE","CLASS","ACTION"],
                ["CLASS_PRE","BASE","CLASS","ACTION"]),
                "NONDETERMINISTIC_DERIVED_NATIVE_READY_SOURCE_BRANCH_ORDER")
            pre=seq[0][1]
            class_event=seq[-2]
            end=seq[-1]
            base=seq[1] if len(seq)==4 else None
            class_reason=class_event[1]
            derived=pre
            if class_reason=="PRISMATIC_BUFF_NOT_PRESENT":
                need(who=="prismatic_bolt" and pre["buff_stack"]==0 and
                     class_event[2] is False and base is None,
                     "PRISMATIC_GUARD_FALSE_NOT_SOURCE_FACT_PROVEN")
                totals["independently_reconstructed_local_prismatic_missing_buff"]+=1
            elif class_reason=="MISSILES_CLEARCASTING_MISSING":
                need(who=="arcane_missiles" and pre["buff_stack"]==0 and
                     class_event[2] is False and base is None,
                     "MISSILES_CLEARCASTING_GUARD_NOT_SOURCE_FACT_PROVEN")
                totals["independently_reconstructed_local_missiles_no_clearcasting"]+=1
            elif class_reason=="MISSILES_IMMEDIATE_CLEARCAST_DELAY":
                need(who=="arcane_missiles" and pre["buff_stack"]>0 and
                     pre["gained_initial_clearcasting"]==1 and
                     pre["allow_arcane_missiles_delay"]==0 and base is None and
                     class_event[2] is False,
                     "MISSILES_INITIAL_CLEARCAST_DELAY_NOT_SOURCE_PROVEN")
                totals["independently_reconstructed_local_missiles_initial_delay"]+=1
            else:
                need(class_reason=="CLASS_BASE_READY_DELEGATED" and base is not None and
                     class_event[2]==base[2] and
                     not (who=="prismatic_bolt" and pre["buff_stack"]==0) and
                     not (who=="arcane_missiles" and pre["buff_stack"]==0),
                     "BASE_READY_DELEGATION_SOURCE_RETURN_MISMATCH")
            if class_reason!="CLASS_BASE_READY_DELEGATED":
                need(end[1]=="ACTION_BASE_READY_FALSE",
                     "CLASS_READY_FALSE_WITH_ACTION_READY_TRUE")
        need(end[0]=="ACTION" and end[2]==row["original_native_POST"],
             "ACTION_READY_STAGE_ORIGINAL_CPP_POST_CONFLICT")
        if base is not None:
            need(base[0]=="BASE" and
                 base[2]==(end[1]!="ACTION_BASE_READY_FALSE"),
                 "BASE_READY_AND_NATIVE_ACTION_SHORTCIRCUIT_INVALID")
        totals["all_competitor_ready_roots"]+=1
        totals["action_stage_"+end[1]]+=1
        if class_reason:totals["class_stage_"+class_reason]+=1
        validated[rid]={
            **{k:v for k,v in row.items() if k!="events"},
            "original_base_ready_return_stage":None if base is None else base[1],
            "original_class_ready_return_stage":class_reason,
            "exact_original_cpp_class_PRE":derived,
            "original_action_ready_return_stage":end[1],
            "local_derived_ready_guard_FALSE_proven_independently":
                class_reason in (
                  "PRISMATIC_BUFF_NOT_PRESENT",
                  "MISSILES_CLEARCASTING_MISSING",
                  "MISSILES_IMMEDIATE_CLEARCAST_DELAY"
                ),
            "independent_whole_ability_global_NOT_READY_proven":False,
            "independent_positive_full_READY_proven":False,
            "dummy_error_feedback":"UNKNOWN",
        }
    explained=[]
    for sweep,es in sorted(snapshots,key=lambda x:x[0]["at_simc_ms"]):
        prior=[]
        for ev in es[:5]:
            if ev["source_action"]=="arcane_orb":
                continue
            entry=validated[ev["original_action_ready_root_id"]]
            need(entry["source_action"]==ev["source_action"] and
                 entry["source_list"]=="spellslinger" and
                 entry["at_ms"]==sweep["at_simc_ms"] and
                 entry["ordinal"]==ev["ordinal_one_based"] and
                 entry["original_native_POST"] is False,
                 "EARLIER_ORIGINAL_CPP_CANDIDATE_IDENTITY_CHANGED")
            totals["earlier_2T_competitor_NATIVE_FALSE"]+=1
            if entry["local_derived_ready_guard_FALSE_proven_independently"]:
                totals["earlier_local_source_ready_false_independently_proven"]+=1
            if entry["original_action_ready_return_stage"]=="ACTION_APL_IF_FALSE":
                totals["earlier_original_native_APL_IF_false"]+=1
            prior.append(entry)
        need(len(prior)==4,"EXPECTED_FOUR_2T_PRIOR_NON_ORB_SPELL_ROWS")
        explained.append({
            "at_simc_ms":sweep["at_simc_ms"],
            "chosen_original_cpp_arcane_orb_ready_root":es[-1]["original_action_ready_root_id"],
            "source_prior_4_non_orb_candidate_original_CPP_root_evidence":prior,
            "source_ahead_orb_row2_handled_by_separately_certified_IF_FALSE":True,
            "total_earlier_candidate_count":5,
            "independently_reconstructed_complete_physical_PRIORITY":False,
            "WoW_actual_user_cast_not_proven":True,
        })
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "source_original_CPP_actual_branch_return_executed":True,
        "native_CPP_original_selected_action_is_not_player_action":True,
        "target_scenarios":2,
        "counts":dict(sorted(totals.items())),
        "two_target_arcane_orb_source_prior_competitors":explained,
        "whole_ability_NOT_READY_proven":False,
        "entire_general_rotation_priority_optimality_proven":False,
        "WCL_independent_blind_holdout_executed":False,
        "original_CPP_NEW_READY_COST_RNG_calls":0,
        "dummy_error_feedback_permitted":False,
        "WCL_API_calls":0,
    }

def selftest()->dict:
    assert GATES["ACTION"]["ACTION_APL_IF_FALSE"] is False
    assert GATES["ACTION"]["ACTION_READY_TRUE"] is True
    assert GATES["BASE"]["BASE_RESOURCE_UNAFFORDABLE"] is False
    for s in ("-1","bad","+7","1.0"):
        try:_integer(s,"negative")
        except RivalNativeRouteError:pass
        else:raise AssertionError("INVALID_NATIVE_CPP_NUMERIC_STAGE_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":7,"actual_CPP_executed":False,
        "independent_full_READY_proven":0,"WCL_API_calls":0,
    }

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-log",type=Path)
    parser.add_argument("--temporal",type=Path)
    parser.add_argument("--producer",type=Path)
    parser.add_argument("--out",type=Path)
    a=parser.parse_args()
    inputs=(a.native_log,a.temporal,a.producer)
    if all(x is None for x in inputs):
        output=selftest()
    elif all(x is not None for x in inputs):
        output=replay(a.native_log.read_text(encoding="utf8"),
                      json.loads(a.temporal.read_bytes()),
                      json.loads(a.producer.read_bytes()))
    else:parser.error("original log, temporal frontier and producer receipt all required")
    data=(json.dumps(output,sort_keys=True,separators=(",",":"),
                     ensure_ascii=False,allow_nan=False)+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(data)
    else:
        import sys
        sys.stdout.buffer.write(data)

if __name__=="__main__":main()
