#!/usr/bin/env python3
"""Original C++ root-scoped raw mana PRE verifier, fail closed.

Uses exact RAII root and C++ source event order, not same-timestamp guessing
and not WoW/WCL timestamp-transition PRE. Native IF is never an input fact.
"""
from __future__ import annotations
import math
from hashlib import sha256
from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_root_actor_pre_producer_v1 import SCHEMA as ROOT_SCHEMA, MARK as ACTOR
from general_rotation_root_resource_pre_producer_v1 import SCHEMA as PRODUCER, MARK as MANA
from general_rotation_select_pre_passive_producer_v1 import REVISION
from general_rotation_call_scope_instrument_v1 import TRACE_MARK
from general_rotation_select_sweep_instrument_v1 import RESULT_MARK
from general_rotation_time_scoped_priority_ir_v1 import SCHEMA as TEMPORAL

SCHEMA="ZrotOriginalRootManaPRESourceOrderReplayV1"

class ManaReplayError(ValueError):pass

def replay(log:str,temporal:dict,root_receipt:dict,mana_receipt:dict)->dict:
    if (root_receipt.get("schema")!=ROOT_SCHEMA or
        mana_receipt.get("schema")!=PRODUCER or
        mana_receipt.get("source_revision")!=REVISION or
        mana_receipt.get("root_PRE_marker")!=MANA or
        mana_receipt.get("source_mana_fields")!=["mana_current","mana_max"] or
        mana_receipt.get("raw_value_format")!="IEEE754_DOUBLE_17_SIGNIFICANT_DIGITS" or
        mana_receipt.get("original_ready_calls_added")!=0 or
        mana_receipt.get("new_rng_or_resource_mutation_calls")!=0 or
        mana_receipt.get("previous_root_actor_pre_receipt_sha256")!=
            sha256(canonical(root_receipt)).hexdigest() or
        mana_receipt.get("source_before_sha256")!=root_receipt.get("source_after_sha256") or
        mana_receipt.get("original_git_blob_sha1")!=root_receipt.get("official_source_blob_sha1")):
        raise ManaReplayError("SOURCE_CHAIN_UNVERIFIED")
    if (temporal.get("schema")!=TEMPORAL or
        temporal.get("independent_FULL_READY_proven")!=0 or
        temporal.get("source_order_complete") is not False):
        raise ManaReplayError("SOURCE_TEMPORAL_IR_UNVERIFIED")
    expected={}
    for sweep in temporal["observed_time_scoped_selection_frontiers"]:
        for event in sweep["observed_candidate_event_stream"]:
            if event.get("stage")=="ACTION_READY_CALLED":
                root=event["original_action_ready_root_id"]
                if root in expected:raise ManaReplayError("DUPLICATE_ORIGINAL_ROOT")
                expected[root]=sweep["at_simc_ms"]
    if len(expected)!=temporal["original_ready_calls"]:
        raise ManaReplayError("TEMPORAL_ROOT_COUNT_CHANGED")
    frames={};complete=set();values={}
    for raw in log.splitlines():
        if TRACE_MARK in raw:
            if raw.count(TRACE_MARK)!=1:raise ManaReplayError("AMBIGUOUS_SCOPE")
            p=raw.split(TRACE_MARK,1)[1].strip().split("|")
            if len(p)!=10:raise ManaReplayError("SCOPE_SHAPE")
            at,event,kind,cid,parent,rid,method,owner,ordinal,name=p
            if kind!="SELECT":continue
            if (not at.isdigit() or not cid.isdigit() or not rid.isdigit()
                or int(cid)!=int(rid) or int(rid) not in expected
                or int(at)!=expected[int(rid)]):
                raise ManaReplayError("SCOPE_ORIGINAL_ROOT_MISMATCH")
            rid=int(rid)
            if event=="BEGIN":
                if rid in frames or rid in complete:raise ManaReplayError("DUPLICATE_BEGIN")
                frames[rid]={"actor":False,"mana":False,"result":False}
            elif event=="END":
                if frames.pop(rid,None)!={"actor":True,"mana":True,"result":True}:
                    raise ManaReplayError("MISSING_OR_UNORDERED_RESOURCE_PRE")
                complete.add(rid)
            else:raise ManaReplayError("SCOPE_DIRECTION")
        elif ACTOR in raw:
            if raw.count(ACTOR)!=1:raise ManaReplayError("DUPLICATE_ACTOR_MARK")
            p=raw.split(ACTOR,1)[1].strip().split("|")
            if len(p)!=4 or not p[0].isdigit() or not p[1].isdigit() or p[2]!="active_enemies":
                raise ManaReplayError("ACTOR_SHAPE")
            rid=int(p[1]);f=frames.get(rid)
            if f is None or f["actor"] or int(p[0])!=expected[rid]:
                raise ManaReplayError("ACTOR_OUTSIDE_ROOT")
            f["actor"]=True
        elif MANA in raw:
            if raw.count(MANA)!=1:raise ManaReplayError("DUPLICATE_MANA_MARK")
            p=raw.split(MANA,1)[1].strip().split("|")
            if len(p)!=4 or not p[0].isdigit() or not p[1].isdigit():
                raise ManaReplayError("MANA_SHAPE")
            rid=int(p[1]);f=frames.get(rid)
            if f is None or not f["actor"] or f["mana"] or f["result"] or int(p[0])!=expected[rid]:
                raise ManaReplayError("MANA_NOT_AFTER_ACTOR_PRE_BEFORE_RESULT")
            try:current=float(p[2]);maximum=float(p[3])
            except ValueError as e:raise ManaReplayError("MANA_NOT_NUMERIC") from e
            if (not math.isfinite(current) or not math.isfinite(maximum)
                or current<0 or maximum<0):
                raise ManaReplayError("MANA_NONFINITE_OR_NEGATIVE")
            values[rid]=None if maximum==0 else 100.0*current/maximum
            if values[rid] is not None and not math.isfinite(values[rid]):
                raise ManaReplayError("MANA_PERCENTAGE_NONFINITE")
            f["mana"]=True
        elif RESULT_MARK in raw:
            if raw.count(RESULT_MARK)!=1:raise ManaReplayError("AMBIGUOUS_READY_RESULT")
            p=raw.split(RESULT_MARK,1)[1].strip().split("|")
            if (len(p)!=3 or not p[0].isdigit() or not p[1].isdigit()
                or p[2] not in ("0","1")):
                raise ManaReplayError("READY_RESULT_SHAPE")
            rid=int(p[1]);f=frames.get(rid)
            if f is None or not f["mana"] or f["result"] or int(p[0])!=expected[rid]:
                raise ManaReplayError("RESULT_BEFORE_ORIGINAL_RAW_MANA")
            f["result"]=True
    if frames or len(complete)!=len(expected) or len(values)!=len(expected):
        raise ManaReplayError("ORIGINAL_MANA_ROOT_COVERAGE_INCOMPLETE")
    return {"schema":SCHEMA,"root_count":len(expected),"root_mana_pct":values,
            "positive_mana_pct_count":sum(v is not None for v in values.values()),
            "zero_max_unknown":sum(v is None for v in values.values()),
            "source_CXX_before_call":True,"not_WCL_strict_transition_pre":True,
            "full_READY_proven":0,"WCL_API_calls":0}

def selftest():
    actor=ACTOR+"100|7|active_enemies|2"
    mana=MANA+"100|7|95|100"
    begin=TRACE_MARK+"100|BEGIN|SELECT|7|0|7|select_call|default|1|foo"
    end=TRACE_MARK+"100|END|SELECT|7|0|7|select_call|default|1|foo"
    result=RESULT_MARK+"100|7|1"
    root={"schema":ROOT_SCHEMA,"source_after_sha256":"0"*64,
          "official_source_blob_sha1":"0"*40}
    receipt={"schema":PRODUCER,"source_revision":REVISION,"root_PRE_marker":MANA,
             "source_mana_fields":["mana_current","mana_max"],
             "raw_value_format":"IEEE754_DOUBLE_17_SIGNIFICANT_DIGITS",
             "original_ready_calls_added":0,"new_rng_or_resource_mutation_calls":0,
             "previous_root_actor_pre_receipt_sha256":sha256(canonical(root)).hexdigest(),
             "source_before_sha256":"0"*64,"original_git_blob_sha1":"0"*40}
    temporal={"schema":TEMPORAL,"independent_FULL_READY_proven":0,
              "source_order_complete":False,"original_ready_calls":1,
              "observed_time_scoped_selection_frontiers":[{
                  "at_simc_ms":100,"observed_candidate_event_stream":[{
                      "stage":"ACTION_READY_CALLED","original_action_ready_root_id":7}]}]}
    def verify(events):return replay("\n".join(events),temporal,root,receipt)
    assert verify([begin,actor,mana,result,end])["root_mana_pct"][7]==95
    assert verify([begin,actor,MANA+"100|7|0|0",result,end])["zero_max_unknown"]==1
    for bad in (
        [begin,mana,actor,result,end],[begin,actor,result,mana,end],
        [begin,actor,mana,mana,result,end],[begin,actor,MANA+"100|8|95|100",result,end],
        [begin,actor,MANA+"101|7|95|100",result,end],
        [begin,actor,MANA+"100|7|nan|100",result,end],
        [begin,actor,result,end]):
        try:verify(bad)
        except ManaReplayError:pass
        else:raise AssertionError("UNPINNED_MANA_PRE_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC","checks":9,
            "native_CXX_executed":False,"full_READY_proven":0,"WCL_API_calls":0}

if __name__=="__main__":
    print(canonical(selftest()).decode(),end="")
