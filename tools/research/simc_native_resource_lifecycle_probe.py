#!/usr/bin/env python3
"""Audit actual SimC resource INIT/RECALC observations, preserving actor spawn.

Two current/max feature rows per source-verified lifecycle function mark.
No direct-write inference, no synthetic initial t-1 event, no cross-spawn
state carry. Independent marker-to-byte projection; accepted PRE is time < t.
The source log is produced by a separate pinned, instrumented SimC build.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from simc_raw_transition_adapter import replay_from_raw

MARKER="ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|"
NUM=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
PATTERN=re.compile(
    r"ZROT_NATIVE_RESOURCE_LIFECYCLE_V1\|(-?\d+)\|(\d+)\|(-?\d+)\|"
    r"([a-z][a-z0-9_]*)\|("+NUM+r")\|("+NUM+r")\|(INIT|RECALC)\s*$"
)


def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def project_lifecycle_log(raw:bytes,expected_log_sha256:str)->dict:
    if not isinstance(raw,bytes) or not raw or len(raw)>3_000_000:
        raise ValueError("LIFECYCLE_LOG_BYTES_INVALID")
    if sha(raw)!=expected_log_sha256:raise ValueError("LIFECYCLE_LOG_SHA_MISMATCH")
    if not raw.endswith(b"\n"):raise ValueError("LIFECYCLE_LOG_FINAL_NEWLINE_REQUIRED")
    rows=[]
    offsets=[]
    actor_ids=set()
    events=Counter()
    offset=0
    negatives=0
    for line_no,part in enumerate(raw.splitlines(keepends=True),1):
        line=part[:-1].removesuffix(b"\r")
        if MARKER.encode() not in line:
            offset+=len(part);continue
        try:text=line.decode("utf-8")
        except UnicodeDecodeError as e:raise ValueError("LIFECYCLE_MARKER_NOT_UTF8") from e
        m=PATTERN.search(text)
        if m is None or text.count(MARKER)!=1:
            raise ValueError("LIFECYCLE_MARKER_MALFORMED")
        ms,actor,spawn,resource,current,maximum,kind=m.groups()
        ms=int(ms);actor=int(actor);spawn=int(spawn)
        current=float(current);maximum=float(maximum)
        if not math.isfinite(current) or not math.isfinite(maximum) or maximum<=0:
            raise ValueError("LIFECYCLE_RESOURCE_NONFINITE_OR_NONPOSITIVE_MAX")
        actor_ids.add(actor)
        if len(actor_ids)>1:raise ValueError("LIFECYCLE_MULTIPLE_ACTORS_UNRESOLVED")
        if ms<0:
            negatives+=1
            offset+=len(part)
            continue
        events[kind]+=1
        row={"native_event_timestamp_ms":ms,"source_log_line":line_no,
             "source_byte_offset":offset,"source_line_sha256":sha(line),
             "actor_index":actor,"actor_spawn_index":spawn,
             "resource_type":resource,"current":current,
             "maximum":maximum,"source_mutation_path":kind}
        rows.append(row)
        if len(rows)>20000:raise ValueError("LIFECYCLE_TOO_MANY_MARKERS")
        offset+=len(part)
    return {
        "schema":"ZrotNativeResourceLifecycleSourceProjectionV1",
        "source_log_sha256":expected_log_sha256,
        "source_log_bytes":len(raw),
        "lifecycle_rows":rows,
        "lifecycle_row_count":len(rows),
        "events_by_path":dict(sorted(events.items())),
        "negative_time_excluded":negatives,
        "actor_spawn_identities":sorted({(x["actor_index"],x["actor_spawn_index"])
                                         for x in rows}),
        "source_completeness":"PARTIAL_INIT_AND_RECALC_FUNCTION_ONLY",
        "direct_writes_in_other_functions":"NOT_VERIFIED",
        "gameplay_rule_promotion":False,
    }


def independent_lifecycle_audit(raw:bytes,produced:dict)->dict:
    """Recalculate source positions and values without regex/projection helper."""
    if sha(raw)!=produced.get("source_log_sha256"):
        raise ValueError("LIFECYCLE_INDEPENDENT_RAW_SHA")
    expected=[]
    count=Counter()
    skipped=0
    offset=0
    actors=set()
    for no,line in enumerate(raw.splitlines(keepends=True),1):
        if b"ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|" not in line:
            offset+=len(line);continue
        decoded=line[:-1].removesuffix(b"\r").decode("utf-8")
        if decoded.count(MARKER)!=1:
            raise ValueError("LIFECYCLE_INDEPENDENT_DUPLICATE_MARKER")
        parts=decoded.split(MARKER,1)[1].split("|")
        if len(parts)!=7:
            raise ValueError("LIFECYCLE_INDEPENDENT_FIELDS")
        time_s,actor_s,spawn_s,resource,curr_s,max_s,kind=parts
        t,a,b=int(time_s),int(actor_s),int(spawn_s)
        curr,mx=float(curr_s),float(max_s)
        if kind not in ("INIT","RECALC") or not re.fullmatch(r"[a-z][a-z0-9_]*",resource):
            raise ValueError("LIFECYCLE_INDEPENDENT_KIND_OR_RESOURCE")
        if not(math.isfinite(curr) and math.isfinite(mx) and mx>0):
            raise ValueError("LIFECYCLE_INDEPENDENT_VALUE")
        actors.add(a)
        if len(actors)>1:
            raise ValueError("LIFECYCLE_INDEPENDENT_MULTIPLE_ACTORS")
        if t<0:skipped+=1
        else:
            count[kind]+=1
            expected.append({
                "native_event_timestamp_ms":t,"source_log_line":no,
                "source_byte_offset":offset,
                "source_line_sha256":hashlib.sha256(
                    line[:-1].removesuffix(b"\r")).hexdigest(),
                "actor_index":a,"actor_spawn_index":b,
                "resource_type":resource,"current":curr,"maximum":mx,
                "source_mutation_path":kind,
            })
        offset+=len(line)
    if (expected!=produced.get("lifecycle_rows") or
        len(expected)!=produced.get("lifecycle_row_count") or
        dict(sorted(count.items()))!=produced.get("events_by_path") or
        skipped!=produced.get("negative_time_excluded") or
        sorted({(x["actor_index"],x["actor_spawn_index"]) for x in expected})
          !=produced.get("actor_spawn_identities") or
        offset!=produced.get("source_log_bytes")):
        raise ValueError("LIFECYCLE_INDEPENDENT_PROJECTION_DIVERGENCE")
    return {
        "schema":"ZrotNativeResourceLifecycleIndependentAuditV1",
        "status":"PASS_EXACT_NATIVE_SOURCE_LOG_RECALC",
        "source_log_sha256":sha(raw),
        "rows":len(expected),
        "actors":len(actors),
        "complete_resource_state":False,
    }


def lifecycle_pre_gate(model:dict,projection:dict,*,actor_identity:list[int],
                       decision_timestamp_ms:int):
    if not isinstance(actor_identity,list) or len(actor_identity)!=2 or (
        any(type(x) is not int for x in actor_identity)):
        raise ValueError("LIFECYCLE_REFERENCE_ACTOR_TUPLE_REQUIRED")
    if type(decision_timestamp_ms) is not int or decision_timestamp_ms<0:
        raise ValueError("LIFECYCLE_REFERENCE_TIME_INVALID")
    source_rows=projection["lifecycle_rows"]
    filtered=[r for r in source_rows
              if [r["actor_index"],r["actor_spawn_index"]]==actor_identity]
    event_rows=[]
    for row in filtered:
        for i,(suffix,value) in enumerate(
            (("current",row["current"]),("max",row["maximum"]))):
            event_rows.append({
                "event_kind":"FEATURE_TRANSITION",
                "event_id":f"native-lifecycle-{row['source_log_line']}-{suffix}",
                "timestamp_ms":row["native_event_timestamp_ms"],
                "sequence":row["source_log_line"]*2+i,
                "feature_key":f"native.resource.{suffix}.{row['resource_type']}",
                "value":value,"scope":"ACTOR","valid":True,
            })
    if not event_rows:
        return {
            "status":"NO_LIFECYCLE_EVENTS_FOR_SELECTED_ACTOR_SPAWN",
            "actor_identity":actor_identity,"source_rows":0,
            "strictly_before_selected_action":0,
            "trace_status":"BLOCKED",
            "complete":False,"readiness":"UNKNOWN",
        }
    raw=b"".join((json.dumps(row,sort_keys=True,separators=(",",":"))+"\n").encode()
                 for row in event_rows)
    receipt={
        "schema":"ZrotGenericRawFeatureTransitionCaptureV1",
        "spec":model["expected_spec"],
        "source_apl_sha256":model["apl_sha256"],
        "source_profile_sha256":model.get("profile_sha256"),
        "source_simc_executable_sha256":model.get("simc_executable_sha256"),
        "capture_kind":"EXTERNAL_NORMALIZED_FEATURE_TRANSITIONS_UNVERIFIED",
        "capture_ref":"native-lifecycle-log-sha256:"+projection["source_log_sha256"],
        "source_authority":"CALLER_SUPPLIED_UNVERIFIED",
        "source_event_semantics":"FEATURE_CHANGE_NOT_SNAPSHOT",
        "source_sha256":sha(raw),"source_bytes":len(raw),
        "gameplay_rule_promotion":False,
    }
    replay=replay_from_raw(model,receipt,raw,
        decision_timestamp_ms=decision_timestamp_ms,operand_to_feature={})
    result=replay["strict_pre_replay"]
    if result["trace_candidate_action_token"] is not None or (
        result["gameplay_rule_promotion"] is not False):
        raise ValueError("LIFECYCLE_UNVERIFIED_STATE_PRODUCED_ACTION")
    return {
        "status":"NATIVE_LIFECYCLE_OBSERVED_UNBOUND",
        "actor_identity":actor_identity,
        "source_rows":len(filtered),"derived_current_and_max_rows":len(event_rows),
        "strictly_before_selected_action":sum(
            int(row["native_event_timestamp_ms"]<decision_timestamp_ms)
            for row in filtered),
        "strict_pre_excluded_same_timestamp":result["strict_pre_excluded_same_timestamp_count"],
        "trace_status":result["trace_status"],
        "complete":False,"readiness":"UNKNOWN",
    }


def selftest():
    from simc_apl_source_engine import ingest_actions
    import copy
    def line(t,actor,spawn,resource,curr,mx,kind):
        return (f"0.0 foo ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|{t}|{actor}|{spawn}|"
                f"{resource}|{curr}|{mx}|{kind}\n").encode()
    for spec in ("enhancement","fury","unholy"):
        raw=b"begin\n"+line(-100,0,0,"mana",100,100,"INIT")+line(
            0,0,1,"mana",100,100,"INIT")+line(
            20,0,1,"mana",60,120,"RECALC")+line(
            30,0,1,"mana",50,120,"RECALC")
        projected=project_lifecycle_log(raw,sha(raw))
        assert projected["lifecycle_row_count"]==3
        assert projected["events_by_path"]=={"INIT":1,"RECALC":2}
        assert projected["negative_time_excluded"]==1
        assert independent_lifecycle_audit(raw,projected)["rows"]==3
        model=ingest_actions(
            (f"spec={spec}\nactions=test,if=mana>20\n").encode(),expected_spec=spec)
        pre=lifecycle_pre_gate(model,projected,actor_identity=[0,1],
                               decision_timestamp_ms=30)
        assert pre["source_rows"]==3 and pre["strictly_before_selected_action"]==2
        assert pre["strict_pre_excluded_same_timestamp"]==2
        assert pre["trace_status"]=="BLOCKED" and pre["readiness"]=="UNKNOWN"
        wrong=lifecycle_pre_gate(model,projected,actor_identity=[0,2],
                                 decision_timestamp_ms=30)
        assert wrong["status"]=="NO_LIFECYCLE_EVENTS_FOR_SELECTED_ACTOR_SPAWN"
        mutated=copy.deepcopy(projected)
        mutated["lifecycle_rows"][1]["current"]=999
        try:independent_lifecycle_audit(raw,mutated)
        except ValueError as e:assert str(e)=="LIFECYCLE_INDEPENDENT_PROJECTION_DIVERGENCE"
        else:raise AssertionError("MUTATED_LIFECYCLE_SOURCE_ACCEPTED")
        invalid=raw.replace(b"|RECALC\n",b"|UNKNOWN\n",1)
        try:project_lifecycle_log(invalid,sha(invalid))
        except ValueError as e:assert str(e)=="LIFECYCLE_MARKER_MALFORMED"
        else:raise AssertionError("INVALID_PATH_ACCEPTED")
        try:project_lifecycle_log(raw,"0"*64)
        except ValueError as e:assert str(e)=="LIFECYCLE_LOG_SHA_MISMATCH"
        else:raise AssertionError("SOURCE_LOG_SHA_MISMATCH_ACCEPTED")
    print("SIMC_NATIVE_RESOURCE_LIFECYCLE_AUDIT_SELF_TEST=PASS SPECS=3 SYNTHETIC_ONLY")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--log",type=Path)
    p.add_argument("--sha256")
    args=p.parse_args()
    if args.self_test or args.log is None:
        selftest();return
    if not args.sha256:p.error("--sha256 required with --log")
    raw=args.log.read_bytes()
    result=project_lifecycle_log(raw,args.sha256)
    audit=independent_lifecycle_audit(raw,result)
    print(json.dumps({
        "projection":{k:v for k,v in result.items() if k!="lifecycle_rows"},
        "independent_audit":audit},indent=2,sort_keys=True))


if __name__=="__main__":
    main()
