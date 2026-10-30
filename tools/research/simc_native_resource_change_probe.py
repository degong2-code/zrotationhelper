#!/usr/bin/env python3
"""Extract actual native SimC resource-mutation log markers into audited PRE rows.

Input is a raw SimC log captured from the separately compiled, source-pinned
instrumented executable, NOT inferred changes between action snapshots.
All values have native event timestamps, which MUST remain < action time to
serve as PRE. Exact resource names and actor index/spawn are retained.
Completeness is PARTIAL (unobserved initial/max/direct-write changes stay
UNKNOWN). Parser never certifies a usable SimC operand or action readiness.
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

_MARKER="ZROT_NATIVE_RESOURCE_V1|"
_NUMBER=r"[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?"
_PATTERN=re.compile(
    r"ZROT_NATIVE_RESOURCE_V1\|(-?\d+)\|(\d+)\|(-?\d+)\|"
    r"([a-z][a-z0-9_]*)\|("+_NUMBER+r")\|("+_NUMBER+r")\|(GAIN|LOSS)\s*$"
)
_LIMIT=20000
_MAX_LOG_BYTES=3_000_000


def digest(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def _log_lines(raw:bytes):
    if not isinstance(raw,bytes) or not raw or len(raw)>_MAX_LOG_BYTES:
        raise ValueError("NATIVE_RESOURCE_RAW_LOG_SIZE_LIMIT")
    if not raw.endswith(b"\n"):
        raise ValueError("NATIVE_RESOURCE_LOG_FINAL_NEWLINE_REQUIRED")
    offset=0
    for number,row in enumerate(raw.splitlines(keepends=True),1):
        if not row.endswith(b"\n"):
            raise ValueError("NATIVE_RESOURCE_LOG_LINE_TERMINATOR")
        line=row[:-1]
        if line.endswith(b"\r"):line=line[:-1]
        try:text=line.decode("utf-8")
        except UnicodeDecodeError as e:raise ValueError("NATIVE_RESOURCE_LOG_NOT_UTF8") from e
        yield number,offset,line,text
        offset+=len(row)


def native_log_to_ndjson(raw:bytes,*,expected_log_sha256:str)->dict:
    if digest(raw)!=expected_log_sha256:
        raise ValueError("NATIVE_RESOURCE_SOURCE_LOG_SHA_MISMATCH")
    events=[]
    receipts=[]
    actor_keys=set()
    excluded_negative=0
    for number,offset,raw_line,text in _log_lines(raw):
        if _MARKER not in text:continue
        found=_PATTERN.search(text)
        if found is None or text.count(_MARKER)!=1:
            raise ValueError("NATIVE_RESOURCE_MARKER_MALFORMED")
        when,actor,spawn,resource,value,delta,direction=found.groups()
        when=int(when);actor=int(actor);spawn=int(spawn)
        value=float(value);delta=float(delta)
        if not math.isfinite(value) or not math.isfinite(delta) or delta<=0:
            raise ValueError("NATIVE_RESOURCE_MARKER_VALUE_INVALID")
        if actor_keys and (actor,spawn) not in actor_keys:
            raise ValueError("NATIVE_RESOURCE_MULTIPLE_ACTORS_UNRESOLVED")
        actor_keys.add((actor,spawn))
        if when<0:
            excluded_negative+=1
            continue
        if len(events)>=_LIMIT:
            raise ValueError("NATIVE_RESOURCE_EVENT_LIMIT")
        events.append({
            "event_kind":"FEATURE_TRANSITION",
            "event_id":f"native-log-line-{number}",
            "timestamp_ms":when,
            "sequence":number,
            "feature_key":"native.resource.current."+resource,
            "value":value,
            "scope":"ACTOR",
            "valid":True,
        })
        receipts.append({
            "source_log_line":number,"source_byte_offset":offset,
            "source_log_line_sha256":digest(raw_line),
            "native_actor_index":actor,"native_actor_spawn_index":spawn,
            "resource_type":resource,"native_event_timestamp_ms":when,
            "direction":direction,"native_reported_actual_amount":delta,
        })
    body=b"".join((json.dumps(e,sort_keys=True,separators=(",",":"),
                               ensure_ascii=False,allow_nan=False)+"\n").encode()
                  for e in events)
    return {
        "schema":"ZrotNativeSimcResourceLogTransitionProjectionV1",
        "source_kind":"INSTRUMENTED_SIMC_ACTUAL_PLAYER_RESOURCE_CHANGE_MARKERS",
        "source_log_sha256":expected_log_sha256,
        "source_log_bytes":len(raw),
        "source_event_count":len(events),
        "excluded_negative_timestamp_events":excluded_negative,
        "actor_identity_tuple":list(next(iter(actor_keys))) if actor_keys else None,
        "source_line_receipts":receipts,
        "projected_ndjson":body,
        "projected_sha256":digest(body),
        "source_completeness":"PARTIAL_GAIN_LOSS_ONLY_NO_INITIAL_MAX_DIRECT_WRITES",
        "event_time_is_not_action_decision_time":True,
        "state_meaning":"REPORTED_RESOURCE_CURRENT_ONLY_NOT_READINESS",
        "gameplay_rule_promotion":False,
    }


def audit_native_projection_independently(raw:bytes,output:dict)->dict:
    """Re-scan source log markers and rebuild row projection without helpers."""
    if output.get("schema")!="ZrotNativeSimcResourceLogTransitionProjectionV1":
        raise ValueError("NATIVE_RESOURCE_PROJECTION_SCHEMA")
    if hashlib.sha256(raw).hexdigest()!=output.get("source_log_sha256"):
        raise ValueError("NATIVE_RESOURCE_INDEPENDENT_SOURCE_SHA")
    markers=[]
    offset=0
    negatives=0
    receipts=[]
    for ln,line in enumerate(raw.splitlines(keepends=True),1):
        if b"ZROT_NATIVE_RESOURCE_V1|" not in line:
            offset+=len(line);continue
        try:
            text=line.decode().rstrip("\r\n")
        except UnicodeDecodeError as e:
            raise ValueError("NATIVE_RESOURCE_INDEPENDENT_DECODING") from e
        # Independent parsing contract: partition by the marker rather than
        # reusing _PATTERN or _log_lines from the producer.
        if text.count(_MARKER)!=1:
            raise ValueError("NATIVE_RESOURCE_INDEPENDENT_MARKER_DUPLICATE")
        record=text.split(_MARKER,1)[1].split("|")
        if len(record)!=7:
            raise ValueError("NATIVE_RESOURCE_INDEPENDENT_FIELDS")
        time_s,actor_s,spawn_s,res,value_s,delta_s,kind=record
        try:t,actor,spawn=int(time_s),int(actor_s),int(spawn_s)
        except ValueError as e:raise ValueError("NATIVE_RESOURCE_INDEPENDENT_ACTOR_TIME") from e
        if not re.fullmatch(r"[a-z][a-z0-9_]*",res) or kind not in ("GAIN","LOSS"):
            raise ValueError("NATIVE_RESOURCE_INDEPENDENT_RESOURCE_TYPE")
        try:value,delta=float(value_s),float(delta_s)
        except ValueError as e:raise ValueError("NATIVE_RESOURCE_INDEPENDENT_VALUES") from e
        if not (math.isfinite(value) and math.isfinite(delta) and delta>0):
            raise ValueError("NATIVE_RESOURCE_INDEPENDENT_INVALID_DELTA")
        if t<0:
            negatives+=1
        else:
            markers.append({
                "event_kind":"FEATURE_TRANSITION",
                "event_id":f"native-log-line-{ln}",
                "timestamp_ms":t,"sequence":ln,
                "feature_key":"native.resource.current."+res,
                "value":value,"scope":"ACTOR","valid":True,
            })
            original=line[:-1].removesuffix(b"\r")
            receipts.append({
                "source_log_line":ln,"source_byte_offset":offset,
                "source_log_line_sha256":hashlib.sha256(original).hexdigest(),
                "native_actor_index":actor,"native_actor_spawn_index":spawn,
                "resource_type":res,"native_event_timestamp_ms":t,
                "direction":kind,"native_reported_actual_amount":delta,
            })
        offset+=len(line)
    expected=(b"".join(
        (json.dumps(e,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
        for e in markers))
    if (expected!=output.get("projected_ndjson") or
            receipts!=output.get("source_line_receipts") or
            negatives!=output.get("excluded_negative_timestamp_events") or
            len(markers)!=output.get("source_event_count") or
            hashlib.sha256(expected).hexdigest()!=output.get("projected_sha256")):
        raise ValueError("NATIVE_RESOURCE_INDEPENDENT_PROJECTION_DIVERGENCE")
    return {
        "schema":"ZrotNativeSimcIndependentResourceLogAuditV1",
        "status":"PASS_NATIVE_LOG_MARKERS_TO_EXPLICIT_EVENT_BYTES",
        "count":len(markers),
        "source_log_sha256":hashlib.sha256(raw).hexdigest(),
        "source_completeness":"PARTIAL",
        "user_actionable":False,
    }


def native_resource_pre_gate(model:dict,raw_log:bytes,*,decision_timestamp_ms:int,
                             expected_log_sha256:str):
    native=native_log_to_ndjson(raw_log,expected_log_sha256=expected_log_sha256)
    independent=audit_native_projection_independently(raw_log,native)
    result={
        "schema":"ZrotNativeSimcResourceStrictPreBoundaryV1",
        "source_log_sha256":native["source_log_sha256"],
        "native_resource_event_count":native["source_event_count"],
        "source_line_receipts":native["source_line_receipts"],
        "independent_log_recalculation":independent,
        "timestamp_ms":decision_timestamp_ms,
        "native_actual_state_transitions_complete":False,
        "readiness":"UNKNOWN",
        "gameplay_rule_promotion":False,
    }
    if native["source_event_count"]==0:
        result["state_status"]="NO_NONNEGATIVE_RESOURCE_MUTATION_EVENTS"
        return result
    manifest={
        "schema":"ZrotGenericRawFeatureTransitionCaptureV1",
        "spec":model["expected_spec"],
        "source_apl_sha256":model["apl_sha256"],
        "source_profile_sha256":model.get("profile_sha256"),
        "source_simc_executable_sha256":model.get("simc_executable_sha256"),
        "capture_kind":"EXTERNAL_NORMALIZED_FEATURE_TRANSITIONS_UNVERIFIED",
        "capture_ref":"native-simc-log-sha256:"+native["source_log_sha256"],
        "source_authority":"CALLER_SUPPLIED_UNVERIFIED",
        "source_event_semantics":"FEATURE_CHANGE_NOT_SNAPSHOT",
        "source_sha256":native["projected_sha256"],
        "source_bytes":len(native["projected_ndjson"]),
        "gameplay_rule_promotion":False,
    }
    bridge=replay_from_raw(model,manifest,native["projected_ndjson"],
        decision_timestamp_ms=decision_timestamp_ms,operand_to_feature={})
    result["strict_pre_state_observation"]=bridge["strict_pre_replay"][
        "operand_diagnostic_counts"]
    result["source_byte_projection"]=bridge["independent_raw_recalculation"]["status"]
    result["trace_status"]=bridge["strict_pre_replay"]["trace_status"]
    result["trace_candidate_action_token"]=bridge["strict_pre_replay"][
        "trace_candidate_action_token"]
    result["accepted_strictly_earlier_raw_events"]=bridge[
        "independent_raw_recalculation"]["strictly_before_decision_valid_record_count"]
    result["state_status"]="NATIVE_RESOURCE_MUTATIONS_OBSERVED_BUT_UNBOUND"
    if result["trace_candidate_action_token"] is not None:
        raise ValueError("NATIVE_RESOURCE_UNKNOWN_MAPPING_UNSAFE_ACTION")
    return result


def selftest():
    from simc_apl_source_engine import ingest_actions
    import copy
    def marker(time,actor,resource,value,direction="GAIN",delta=4):
        return (f"0.000 probe ZROT_NATIVE_RESOURCE_V1|{time}|{actor}|0|"
                f"{resource}|{value}|{delta}|{direction}\n").encode()
    for spec,name in (("enhancement","alpha"),("fury","beta"),("unholy","gamma")):
        raw=b"start\n"+marker(-100,1,"rage",0)+marker(900,1,"rage",45)+marker(
            1000,1,"rage",40,"LOSS",5)+marker(1100,1,"rage",42)
        result=native_log_to_ndjson(raw,expected_log_sha256=digest(raw))
        assert result["source_event_count"]==3
        assert result["excluded_negative_timestamp_events"]==1
        assert audit_native_projection_independently(raw,result)["count"]==3
        model=ingest_actions(f"spec={spec}\nactions={name},if=rage>25\n".encode(),
                             expected_spec=spec)
        status=native_resource_pre_gate(model,raw,decision_timestamp_ms=1000,
                                        expected_log_sha256=digest(raw))
        assert status["accepted_strictly_earlier_raw_events"]==1
        assert status["trace_status"]=="BLOCKED"
        assert status["readiness"]=="UNKNOWN"
        assert not status["gameplay_rule_promotion"]
        tampered=copy.deepcopy(result)
        tampered["source_line_receipts"][0]["resource_type"]="mana"
        try:audit_native_projection_independently(raw,tampered)
        except ValueError as e:
            assert str(e)=="NATIVE_RESOURCE_INDEPENDENT_PROJECTION_DIVERGENCE"
        else:raise AssertionError("MUTATED_SOURCE_RECEIPT_ACCEPTED")
        for bad,code in [
            (raw.replace(b"|GAIN\n",b"|ERROR\n",1),"NATIVE_RESOURCE_MARKER_MALFORMED"),
            (raw+marker(1200,2,"rage",50),"NATIVE_RESOURCE_MULTIPLE_ACTORS_UNRESOLVED"),
        ]:
            try:native_log_to_ndjson(bad,expected_log_sha256=digest(bad))
            except ValueError as e:assert str(e)==code,str(e)
            else:raise AssertionError("INVALID_NATIVE_RESOURCE_EVENT_ACCEPTED")
        try:native_log_to_ndjson(raw,expected_log_sha256="0"*64)
        except ValueError as e:assert str(e)=="NATIVE_RESOURCE_SOURCE_LOG_SHA_MISMATCH"
        else:raise AssertionError("SOURCE_SHA_MISMATCH_ACCEPTED")
    print("SIMC_NATIVE_RESOURCE_MUTATION_LOG_PRODUCER_SELF_TEST=PASS SPECS=3 SYNTHETIC_SOURCE_LOG_ONLY")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--raw-log",type=Path)
    p.add_argument("--expected-sha256")
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    if args.self_test or args.raw_log is None:
        selftest();return
    raw=args.raw_log.read_bytes()
    if not args.expected_sha256:
        p.error("--expected-sha256 mandatory to prevent unpinned log input")
    result=native_log_to_ndjson(raw,expected_log_sha256=args.expected_sha256)
    audit=audit_native_projection_independently(raw,result)
    summary={k:v for k,v in result.items() if k!="projected_ndjson"}
    summary["independent_audit"]=audit
    if args.output:
        args.output.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
        print("WROTE_NATIVE_RESOURCE_PROJECTION_SUMMARY_ONLY")
    else:print(json.dumps(summary,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
