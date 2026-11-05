#!/usr/bin/env python3
"""Strict source-order replay of original SimC root actor PRE active_enemies.

READS ARE FROM ACTUAL SIMC BEFORE a->action_ready(); each one is causally
between SELECT root BEGIN and original action_ready native result+END. This
is NOT a WCL state-transition reconstruction: same SimC millisecond is
permitted only because the instrumented original C++ execution point proves
ordering, not because timestamp equality is treated as an earlier event.

Native returned Boolean is NEVER used as an operand or readiness oracle.
The source AST may be independently determinate from a single observed
active_enemies value even if other symbols are logically irrelevant.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from general_rotation_call_scope_instrument_v1 import TRACE_MARK
from general_rotation_select_sweep_instrument_v1 import RESULT_MARK
from general_rotation_root_actor_pre_producer_v1 import (
    SCHEMA as PRODUCER_SCHEMA, MARK as PRE_MARK
)
from general_rotation_time_scoped_priority_ir_v1 import SCHEMA as TEMPORAL_SCHEMA
from general_rotation_source_eligibility_decision_ir_v1 import POLICY
from general_rotation_original_pre_capture_engine_v1 import canonical
from simc_apl_semantic_ir_v2 import parse_profile,git_blob,evaluate_ast,truth

SCHEMA="ZrotGeneralRotationOriginalRootActorPRESourceOrderReplayV1"

class SourceRootPREReplayError(ValueError):pass


def replay(log:str,profile:bytes,temporal:dict,producer:dict)->dict:
    if (producer.get("schema")!=PRODUCER_SCHEMA or
        producer.get("operand_symbol")!="active_enemies" or
        producer.get("operand_source_cpp")!="sim->active_enemies" or
        producer.get("root_PRE_marker")!=PRE_MARK or
        producer.get("original_action_ready_call_count")!=1 or
        producer.get("added_ready_calls")!=0 or
        producer.get("direct_before_call_snapshot_same_simc_tick") is not True or
        producer.get("WCL_latest_transition_before_t_claim") is not False):
        raise SourceRootPREReplayError("PINNED_ORIGINAL_ROOT_PRE_SOURCE_PRODUCER_REQUIRED")
    if (temporal.get("schema")!=TEMPORAL_SCHEMA or
        temporal.get("source_profile_git_blob_sha1")!=git_blob(profile) or
        temporal.get("product_policy_id")!=POLICY or
        temporal.get("source_order_complete") is not False or
        temporal.get("independent_FULL_READY_proven")!=0):
        raise SourceRootPREReplayError("SOURCE_SWEEP_TEMPORAL_EVIDENCE_REQUIRED")
    lists=parse_profile(profile,require_source=False)["action_lists"]
    temporal_roots={}
    for sweep in temporal["observed_time_scoped_selection_frontiers"]:
        owner=sweep["source_list"]
        for event in sweep["observed_candidate_event_stream"]:
            if event.get("stage")!="ACTION_READY_CALLED":continue
            rid=event["original_action_ready_root_id"]
            if rid in temporal_roots:
                raise SourceRootPREReplayError("DUPLICATE_SOURCE_ROOT_ID_IN_TEMPORAL")
            ordinal=event["ordinal_one_based"]
            row=lists[owner][ordinal-1]
            if (event["source_row_sha256"]!=row["source_sha256"] or
                event["source_action"]!=row["action"]):
                raise SourceRootPREReplayError("TEMPORAL_APL_SOURCE_ROW_MISMATCH")
            temporal_roots[rid]={
                "owner":owner,"ordinal":ordinal,
                "source_hash":row["source_sha256"],
                "source_action":row["action"],
                "source_if":row["expression_fields"].get("if"),
                "at_ms":sweep["at_simc_ms"],
                "native_post_comparator":event["simc_NATIVE_return_post_comparator"]
            }
    if len(temporal_roots)!=temporal["original_ready_calls"]:
        raise SourceRootPREReplayError("TEMPORAL_ROOT_COUNT_DRIFT")
    open_roots={}
    complete=[]
    seen=set()
    counts=Counter()
    rows=Counter()
    first_samples=[]
    for line in log.splitlines():
        if TRACE_MARK in line:
            if line.count(TRACE_MARK)!=1:
                raise SourceRootPREReplayError("AMBIGUOUS_ROOT_SCOPE_EVENT")
            args=line.split(TRACE_MARK,1)[1].strip().split("|")
            if len(args)!=10:
                raise SourceRootPREReplayError("ROOT_SCOPE_EVENT_SHAPE")
            (clock,event,kind,id_s,parent_s,root_s,method,
             owner,ordinal_s,native)=args
            if kind!="SELECT":continue
            if (not clock.isdigit() or event not in ("BEGIN","END") or
                not id_s.isdigit() or not root_s.isdigit() or
                not ordinal_s.isdigit() or not native or
                int(id_s)!=int(root_s) or method!="select_call"):
                raise SourceRootPREReplayError("SOURCE_ROOT_SCOPE_IDENTITY_CHANGED")
            rid=int(id_s);moment=int(clock)
            expected=temporal_roots.get(rid)
            if (expected is None or expected["owner"]!=owner or
                expected["ordinal"]!=int(ordinal_s) or
                expected["at_ms"]!=moment):
                raise SourceRootPREReplayError("ROOT_SCOPE_NOT_MATCHED_TO_EXACT_TEMPORAL_ROW")
            if event=="BEGIN":
                if rid in seen or rid in open_roots:
                    raise SourceRootPREReplayError("DUPLICATE_SOURCE_READY_ROOT")
                seen.add(rid)
                open_roots[rid]={
                    "at_ms":moment,"root_id":rid,"captured":None,"returned":None,
                    "pre_before_native_return":False}
            else:
                frame=open_roots.get(rid)
                if (frame is None or frame["captured"] is None or
                    frame["returned"] is None or
                    frame["returned"]!=expected["native_post_comparator"] or
                    not frame["pre_before_native_return"]):
                    raise SourceRootPREReplayError("UNCLOSED_OR_NONCAUSAL_SOURCE_ROOT_PRE")
                complete.append(frame)
                del open_roots[rid]
            continue
        if PRE_MARK in line:
            if line.count(PRE_MARK)!=1:
                raise SourceRootPREReplayError("MULTIPLE_SOURCE_PRE_MARKERS")
            args=line.split(PRE_MARK,1)[1].strip().split("|")
            if (len(args)!=4 or not args[0].isdigit() or
                not args[1].isdigit() or args[2]!="active_enemies" or
                not re.fullmatch(r"-?[0-9]+",args[3])):
                raise SourceRootPREReplayError("ROOT_ACTOR_PRE_OPERAND_FIELD_MALFORMED")
            moment,rid,value=int(args[0]),int(args[1]),int(args[3])
            frame=open_roots.get(rid)
            if (frame is None or frame["captured"] is not None or
                frame["returned"] is not None or
                moment!=frame["at_ms"] or not 0<=value<=10000):
                raise SourceRootPREReplayError("SAME_ROOT_ORDER_PRE_FIELD_MISSING_OR_CHANGED")
            frame["captured"]=value
            frame["pre_before_native_return"]=True
            counts["actual_original_simc_root_actor_PRE_observed"]+=1
            continue
        if RESULT_MARK in line:
            if line.count(RESULT_MARK)!=1:
                raise SourceRootPREReplayError("MULTIPLE_ORIGINAL_READY_RETURN_MARKERS")
            args=line.split(RESULT_MARK,1)[1].strip().split("|")
            if (len(args)!=3 or not args[0].isdigit() or
                not args[1].isdigit() or args[2] not in ("0","1")):
                raise SourceRootPREReplayError("READY_RETURN_SOURCE_RECORD_DRIFT")
            rid=int(args[1]);moment=int(args[0])
            frame=open_roots.get(rid)
            if (frame is None or frame["captured"] is None or
                frame["returned"] is not None or frame["at_ms"]!=moment):
                raise SourceRootPREReplayError("RETURN_BEFORE_SOURCE_OPERAND_OR_WRONG_ROOT")
            frame["returned"]=args[2]=="1"
            continue
    if (open_roots or len(seen)!=len(temporal_roots) or
        len(complete)!=len(temporal_roots) or
        counts["actual_original_simc_root_actor_PRE_observed"]!=len(complete)):
        raise SourceRootPREReplayError("INCOMPLETE_SOURCE_NATIVE_ROOT_PRE_COVERAGE")
    by_row={}
    for frame in complete:
        rid=frame["root_id"];root=temporal_roots[rid]
        expr=root["source_if"]
        if expr is None:
            counts["source_action_without_if"]+=1
            continue
        # Source reader captured before original action_ready call, not a
        # reconstructed WCL transition. The AST uses this audited source
        # value; native post comparator is deliberately not an input.
        direct={"active_enemies":frame["captured"]}
        derived=truth(evaluate_ast(expr["ast"],direct))
        if derived is None:
            verdict="UNKNOWN_MISSING_OTHER_SIMC_SOURCE_PRE_SYMBOLS"
            counts["if_unknown_after_active_enemies_source_PRE"]+=1
        else:
            verdict=("SIMC_SOURCE_PRE_IF_TRUE" if derived else "SIMC_SOURCE_PRE_IF_FALSE")
            counts["if_recomputed_from_original_actor_PRE"]+=1
            counts["if_recomputed_true" if derived else "if_recomputed_false"]+=1
        h=root["source_hash"]
        row=by_row.setdefault(h,{
            "source_action":root["source_action"],
            "source_if":expr["source"],
            "root_count":0,"source_PRE_recomputed_count":0,
            "source_PRE_unknown_count":0})
        row["root_count"]+=1
        row["source_PRE_recomputed_count"]+=int(derived is not None)
        row["source_PRE_unknown_count"]+=int(derived is None)
        if len(first_samples)<12:
            first_samples.append({
                "root_call_id":rid,"source_row_sha256":h,
                "source_action":root["source_action"],
                "source_if":expr["source"],
                "at_simc_ms":frame["at_ms"],
                "observed_before_call_active_enemies":frame["captured"],
                "original_actor_PRE_source_causality_proven":True,
                "recomputed_if":verdict,
                "native_return_only_comparator":frame["returned"],
                "source_FULL_action_READY":"UNKNOWN",
                "WCL_strict_transition_PRE":"NOT_PROVEN"
            })
    if sum(v["root_count"] for v in by_row.values()) != (
        counts["if_recomputed_from_original_actor_PRE"]+
        counts["if_unknown_after_active_enemies_source_PRE"]):
        raise SourceRootPREReplayError("SOURCE_IF_ROW_AGGREGATES_NOT_RECONCILED")
    return {
        "schema":SCHEMA,
        "product_policy_id":POLICY,
        "source_profile_git_blob_sha1":git_blob(profile),
        "original_native_root_pre_total":len(complete),
        "source_actor_PRE_operand":"active_enemies",
        "source_actor_PRE_semantics":"DIRECT_SIMC_CPP_BEFORE_ORIGINAL_READY_CALL",
        "same_clock_tick_accepted_only_with_CPP_SOURCE_ORDER_NOT_TRANSITION":True,
        "original_READY_call_added":0,
        "source_if_recomputed_only_from_actor_PRE":True,
        "native_POST_result_not_used_as_AST_fact":True,
        "counts":dict(sorted(counts.items())),
        "by_source_row_sha256":dict(sorted(by_row.items())),
        "first_bounded_examples":first_samples,
        "WCL_Strict_PRE_latest_transition_proven":False,
        "full_original_IF_coverage":False,
        "full_READY_proven":0,
        "source_priority_complete":False,
        "dummy_error_permitted":False,
        "WCL_API_calls":0
    }


def selftest():
    p=b'warrior="Synthetic"\nspec=fury\nactions=/foo,if=active_enemies>=2\n'
    source=parse_profile(p,require_source=False)["action_lists"]["default"][0]
    temporal={
        "schema":TEMPORAL_SCHEMA,"product_policy_id":POLICY,
        "source_profile_git_blob_sha1":git_blob(p),"source_order_complete":False,
        "independent_FULL_READY_proven":0,"original_ready_calls":1,
        "observed_time_scoped_selection_frontiers":[{
            "source_list":"default","at_simc_ms":100,
            "observed_candidate_event_stream":[{
                "stage":"ACTION_READY_CALLED","original_action_ready_root_id":7,
                "ordinal_one_based":1,"source_row_sha256":source["source_sha256"],
                "source_action":"foo","simc_NATIVE_return_post_comparator":True}]}]
    }
    producer={"schema":PRODUCER_SCHEMA,"operand_symbol":"active_enemies",
        "operand_source_cpp":"sim->active_enemies","root_PRE_marker":PRE_MARK,
        "original_action_ready_call_count":1,"added_ready_calls":0,
        "direct_before_call_snapshot_same_simc_tick":True,
        "WCL_latest_transition_before_t_claim":False}
    begin=TRACE_MARK+"100|BEGIN|SELECT|7|6|7|select_call|default|1|foo"
    pre=PRE_MARK+"100|7|active_enemies|2"
    result=RESULT_MARK+"100|7|1"
    end=TRACE_MARK+"100|END|SELECT|7|6|7|select_call|default|1|foo"
    real=replay("\n".join((begin,pre,result,end)),p,temporal,producer)
    assert real["counts"]["if_recomputed_from_original_actor_PRE"]==1
    assert real["counts"]["if_recomputed_true"]==1
    assert real["full_READY_proven"]==0
    invalid=(
        [begin,result,pre,end],
        [begin,pre,pre,result,end],
        [begin,pre,end],
        [begin,pre.replace("|7|active_enemies|","|8|active_enemies|"),result,end],
        [begin,pre.replace("|100|","|101|"),result,end],
        [begin,pre.replace("|2","|-1"),result,end],
        [begin,result,end],
    )
    for bad in invalid:
        try:replay("\n".join(bad),p,temporal,producer)
        except SourceRootPREReplayError:pass
        else:raise AssertionError("BAD_ROOT_ACTOR_PRE_SOURCE_EVENT_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":10,"physical_simc_cpp_executed":False,
        "WCL_latest_transition_before_t_claim":False,
        "positive_full_READY_proven":0,"WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--profile",type=Path)
    p.add_argument("--temporal-ir",type=Path)
    p.add_argument("--source-producer-receipt",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    req=(a.native_log,a.profile,a.temporal_ir,a.source_producer_receipt)
    if all(x is None for x in req):result=selftest()
    elif all(x is not None for x in req):
        result=replay(a.native_log.read_text(encoding="utf8"),
                      a.profile.read_bytes(),json.loads(a.temporal_ir.read_bytes()),
                      json.loads(a.source_producer_receipt.read_bytes()))
    else:p.error("all four pinned Native source evidence inputs required")
    data=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(data)
    else:print(data.decode(),end="")

if __name__=="__main__":main()
