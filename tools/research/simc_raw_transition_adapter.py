#!/usr/bin/env python3
"""Byte-pinned generic source event adapter for the existing Strict-PRE bridge.

Accepts only explicit FEATURE_TRANSITION event rows in immutable UTF-8 NDJSON
capture bytes, NOT SimC action_sequence's post/at-action state snapshots.
Raw bytes and each exact source line are hashed. This verifies reconstruction
and attribution to supplied bytes, NEVER authenticity of a caller's capture,
Blizzard mechanics, SimC producer timing or true in-game readiness.
No class/boss/ability logic; unobserved state remains UNKNOWN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from simc_strict_pre_source_bridge import transition_digest, replay_explicit_pre

_SCHEMA="ZrotGenericRawFeatureTransitionCaptureV1"
_RESULT="ZrotSourceByteReconstructedStrictPreFixtureV1"
_MAX_BYTES=3_000_000
_MAX_EVENTS=20000
_TYPES=("SYNTHETIC_FEATURE_TRANSITIONS","EXTERNAL_NORMALIZED_FEATURE_TRANSITIONS_UNVERIFIED")
_FIELDS=frozenset(("event_kind","event_id","timestamp_ms","sequence","feature_key",
                   "value","scope","valid"))
_SHA="0123456789abcdef"


def _digest(blob:bytes)->str:
    return hashlib.sha256(blob).hexdigest()


def _load_json_no_duplicate_keys(raw:bytes)->dict:
    def pairs(items):
        obj={}
        for k,v in items:
            if k in obj:
                raise ValueError("RAW_EVENT_DUPLICATE_JSON_KEY")
            obj[k]=v
        return obj
    def invalid_constant(_:str):
        raise ValueError("RAW_EVENT_NONFINITE_NUMBER")
    try:
        data=json.loads(raw.decode("utf-8"),object_pairs_hook=pairs,
                        parse_constant=invalid_constant)
    except (UnicodeDecodeError,json.JSONDecodeError) as e:
        raise ValueError("RAW_EVENT_INVALID_UTF8_JSON") from e
    if not isinstance(data,dict):
        raise ValueError("RAW_EVENT_NOT_OBJECT")
    return data


def _is_number(v:Any)->bool:
    if type(v) is bool:return True
    if type(v) not in (int,float):return False
    try:return math.isfinite(v)
    except (ValueError,OverflowError):return False


def _assert_capture(capture:dict,raw:bytes,model:dict)->None:
    if not isinstance(capture,dict) or capture.get("schema")!=_SCHEMA:
        raise ValueError("RAW_CAPTURE_SCHEMA")
    for a,b in (("spec","expected_spec"),("source_apl_sha256","apl_sha256"),
                ("source_profile_sha256","profile_sha256"),
                ("source_simc_executable_sha256","simc_executable_sha256")):
        if capture.get(a)!=model.get(b):
            raise ValueError("RAW_CAPTURE_IDENTITY_"+a)
    if capture.get("capture_kind") not in _TYPES or (
            capture.get("source_authority")!="CALLER_SUPPLIED_UNVERIFIED"):
        raise ValueError("RAW_CAPTURE_CANNOT_ASSERT_TRUST")
    if capture.get("source_event_semantics")!="FEATURE_CHANGE_NOT_SNAPSHOT":
        raise ValueError("RAW_SNAPSHOT_NOT_A_TRANSITION")
    if capture.get("gameplay_rule_promotion") is not False:
        raise ValueError("RAW_CAPTURE_PREMATURE_PROMOTION")
    source=capture.get("capture_ref")
    if not isinstance(source,str) or not source.strip() or len(source)>256:
        raise ValueError("RAW_CAPTURE_REF_INVALID")
    if not isinstance(raw,bytes) or not 0<len(raw)<=_MAX_BYTES:
        raise ValueError("RAW_CAPTURE_SIZE_INVALID")
    if capture.get("source_bytes")!=len(raw) or capture.get("source_sha256")!=_digest(raw):
        raise ValueError("RAW_CAPTURE_BYTES_OR_SHA_MISMATCH")


def _read_lines(raw:bytes):
    if not raw.endswith(b"\n"):
        raise ValueError("RAW_EVENT_NDJSON_FINAL_NEWLINE_REQUIRED")
    result=[]
    offset=0
    for row_num,line in enumerate(raw.splitlines(keepends=True),start=1):
        if not line.endswith(b"\n"):
            raise ValueError("RAW_EVENT_LINE_TERMINATOR_REQUIRED")
        content=line[:-1]
        if content.endswith(b"\r"):
            content=content[:-1]
        if not content:
            raise ValueError("RAW_EVENT_EMPTY_LINE")
        doc=_load_json_no_duplicate_keys(content)
        result.append((row_num,offset,content,doc))
        offset+=len(line)
        if len(result)>_MAX_EVENTS:
            raise ValueError("RAW_EVENT_COUNT_LIMIT")
    return result


def build_fixture_from_raw(model:dict,capture:dict,raw:bytes,*,decision_timestamp_ms:int,
                           operand_to_feature:dict[str,str],
                           unobservable_features:list[str]|None=None)->dict:
    """Derive every transition from exact raw line content; no source copying."""
    _assert_capture(capture,raw,model)
    if type(decision_timestamp_ms) is not int or decision_timestamp_ms<0:
        raise ValueError("RAW_DECISION_TIMESTAMP_INVALID")
    if not isinstance(operand_to_feature,dict):
        raise ValueError("RAW_OPERAND_MAPPING_REQUIRED")
    source_rows=_read_lines(raw)
    ids=set()
    feature_scopes={}
    transitions=[]
    receipts=[]
    for row_num,offset,line,event in source_rows:
        if set(event)!=_FIELDS or event.get("event_kind")!="FEATURE_TRANSITION":
            raise ValueError("RAW_EVENT_NOT_EXPLICIT_TRANSITION")
        eid=event["event_id"]
        if not isinstance(eid,str) or not eid or len(eid)>128 or eid in ids:
            raise ValueError("RAW_EVENT_DUPLICATE_OR_INVALID_ID")
        ids.add(eid)
        time=event["timestamp_ms"]
        order=event["sequence"]
        key=event["feature_key"]
        if type(time) is not int or time<0 or (
                type(order) is not int or order<0):
            raise ValueError("RAW_EVENT_TIME_OR_SEQUENCE_INVALID")
        if not isinstance(key,str) or not key or len(key)>256:
            raise ValueError("RAW_EVENT_FEATURE_INVALID")
        if event["scope"] not in ("ACTOR","TARGET","ENCOUNTER"):
            raise ValueError("RAW_EVENT_SCOPE_INVALID")
        # Without target GUID/instance identity, a target-scoped observation
        # cannot be safely keyed across switches. Do not mix it into actor PRE.
        if event["scope"]=="TARGET":
            raise ValueError("RAW_TARGET_SUBJECT_IDENTITY_NOT_IMPLEMENTED")
        previous_scope=feature_scopes.setdefault(key,event["scope"])
        if previous_scope!=event["scope"]:
            raise ValueError("RAW_FEATURE_SCOPE_COLLISION")
        if type(event["valid"]) is not bool or not _is_number(event["value"]):
            raise ValueError("RAW_EVENT_STATE_VALUE_INVALID")
        receipt=f"raw-line:{row_num}:offset:{offset}:sha256:{_digest(line)}"
        transitions.append({
            "timestamp_ms":time,"sequence":order,"feature_key":key,
            "value":event["value"],"valid":event["valid"],
            "producer_ref":f"raw-sha256:{_digest(raw)}",
            "evidence_ref":receipt,
        })
        receipts.append({"event_id":eid,"source_line":row_num,
                         "byte_offset":offset,"raw_line_sha256":_digest(line),
                         "source_scope":event["scope"],
                         "source_time_ms":time,"feature_key":key,
                         "strictly_before_decision":time<decision_timestamp_ms})
    origin=("SYNTHETIC_TEST" if capture["capture_kind"]=="SYNTHETIC_FEATURE_TRANSITIONS"
            else "EXTERNAL_CALLER_DECLARED_UNVERIFIED")
    fixture={
        "schema":"ZrotSimcSourceAccountableStrictPreFixtureV1",
        "spec":model["expected_spec"],"source_apl_sha256":model["apl_sha256"],
        "source_profile_sha256":model.get("profile_sha256"),
        "source_simc_executable_sha256":model.get("simc_executable_sha256"),
        "gameplay_rule_promotion":False,
        "provenance_class":origin,
        "independently_verified_producer":False,
        "decision_timestamp_ms":decision_timestamp_ms,
        "operand_to_feature":operand_to_feature,
        "unobservable_features":unobservable_features or [],
        "synthetic_action_readiness":{},
        "transitions":transitions,
        "transitions_sha256":transition_digest(transitions),
    }
    return {
        "schema":_RESULT,
        "source_raw_sha256":_digest(raw),
        "source_bytes":len(raw),
        "capture_ref":capture["capture_ref"],
        "capture_kind":capture["capture_kind"],
        "source_event_count":len(source_rows),
        "source_line_receipts":receipts,
        "fixture":fixture,
        "source_integrity":"EXACT_CAPTURE_BYTES_AND_EACH_LINE_RECOMPUTED",
        "source_authenticity":"NOT_INDEPENDENTLY_VERIFIED",
        "event_transition_semantic_truth":"NOT_INDEPENDENTLY_VERIFIED",
        "native_action_sequence_snapshot_reinterpretation":"FORBIDDEN",
        "native_decision_time_pre":"NOT_CAPTURED",
        "gameplay_rule_promotion":False,
    }


def replay_from_raw(model:dict,capture:dict,raw:bytes,*,decision_timestamp_ms:int,
                    operand_to_feature:dict[str,str],
                    unobservable_features:list[str]|None=None,graph:dict|None=None):
    output=build_fixture_from_raw(
        model,capture,raw,decision_timestamp_ms=decision_timestamp_ms,
        operand_to_feature=operand_to_feature,
        unobservable_features=unobservable_features)
    # An independent byte/row reviewer must recalculate before downstream
    # decision trace; a caller must not trust the above output blindly.
    from simc_raw_transition_independent_audit import independent_raw_audit
    audit=independent_raw_audit(model,capture,raw,output)
    if audit["status"]!="RAW_ROW_PROJECTION_VERIFIED_UNTRUSTED_SOURCE":
        raise ValueError("RAW_RECALC_NOT_ACCEPTED")
    output["independent_raw_recalculation"]=audit
    output["strict_pre_replay"]=replay_explicit_pre(
        model,output["fixture"],graph=graph)
    if output["strict_pre_replay"]["gameplay_rule_promotion"] is not False:
        raise ValueError("RAW_REPLAY_PREMATURE_PROMOTION")
    return output


def selftest():
    from simc_apl_source_engine import ingest_actions
    import copy
    for spec,token in (("enhancement","alpha"),("unholy","beta"),
                       ("unseen_spec","gamma")):
        model=ingest_actions((f"spec={spec}\nactions={token},if=buff.foo.stack>=2\n"
                              "actions+=/zz_other\n").encode(),expected_spec=spec)
        rows=[
            {"event_kind":"FEATURE_TRANSITION","event_id":"before",
             "timestamp_ms":900,"sequence":0,"feature_key":"stack",
             "value":4,"scope":"ACTOR","valid":True},
            {"event_kind":"FEATURE_TRANSITION","event_id":"same",
             "timestamp_ms":1000,"sequence":0,"feature_key":"stack",
             "value":0,"scope":"ACTOR","valid":True},
            {"event_kind":"FEATURE_TRANSITION","event_id":"future",
             "timestamp_ms":1001,"sequence":0,"feature_key":"stack",
             "value":1,"scope":"ACTOR","valid":True},
        ]
        raw=b"".join((json.dumps(r,sort_keys=True,separators=(",",":"))+"\n").encode()
                     for r in rows)
        manifest={
            "schema":_SCHEMA,"spec":spec,
            "source_apl_sha256":model["apl_sha256"],
            "source_profile_sha256":model.get("profile_sha256"),
            "source_simc_executable_sha256":model.get("simc_executable_sha256"),
            "capture_kind":"SYNTHETIC_FEATURE_TRANSITIONS",
            "capture_ref":"test:ndjson:1",
            "source_authority":"CALLER_SUPPLIED_UNVERIFIED",
            "source_event_semantics":"FEATURE_CHANGE_NOT_SNAPSHOT",
            "source_sha256":_digest(raw),"source_bytes":len(raw),
            "gameplay_rule_promotion":False,
        }
        out=replay_from_raw(model,manifest,raw,decision_timestamp_ms=1000,
            operand_to_feature={"buff.foo.stack":"stack"})
        rec=out["strict_pre_replay"]
        assert out["independent_raw_recalculation"]["status"]=="RAW_ROW_PROJECTION_VERIFIED_UNTRUSTED_SOURCE"
        assert rec["operand_diagnostic_counts"]=={"OBSERVED_STRICT_PRE_CLAIM":1}
        assert rec["strict_pre_excluded_same_timestamp_count"]==1
        assert rec["strict_pre_excluded_future_count"]==1
        assert rec["trace_status"]=="BLOCKED" and rec["trace_candidate_action_token"] is None
        assert rec["non_synthetic_readiness_all_unknown"] is False
        assert out["gameplay_rule_promotion"] is False
        external=dict(manifest,capture_kind="EXTERNAL_NORMALIZED_FEATURE_TRANSITIONS_UNVERIFIED")
        out=replay_from_raw(model,external,raw,decision_timestamp_ms=1000,
            operand_to_feature={"buff.foo.stack":"stack"})
        assert out["strict_pre_replay"]["non_synthetic_readiness_all_unknown"] is True
        bad=dict(manifest,source_sha256="0"*64)
        try:replay_from_raw(model,bad,raw,decision_timestamp_ms=1000,
             operand_to_feature={"buff.foo.stack":"stack"})
        except ValueError as e:assert str(e)=="RAW_CAPTURE_BYTES_OR_SHA_MISMATCH"
        else:raise AssertionError("RAW_SHA_TAMPER_ACCEPTED")
        snapshot=raw.replace(b"FEATURE_TRANSITION",b"ACTION_SEQUENCE_SNAPSHOT")
        replaced=dict(manifest,source_sha256=_digest(snapshot),source_bytes=len(snapshot))
        try:replay_from_raw(model,replaced,snapshot,decision_timestamp_ms=1000,
             operand_to_feature={"buff.foo.stack":"stack"})
        except ValueError as e:assert str(e)=="RAW_EVENT_NOT_EXPLICIT_TRANSITION"
        else:raise AssertionError("ACTION_SNAPSHOT_AS_TRANSITION_ACCEPTED")
        duplicated=raw+raw.splitlines(keepends=True)[0]
        duplicate=dict(manifest,source_sha256=_digest(duplicated),source_bytes=len(duplicated))
        try:replay_from_raw(model,duplicate,duplicated,decision_timestamp_ms=1000,
             operand_to_feature={"buff.foo.stack":"stack"})
        except ValueError as e:assert str(e)=="RAW_EVENT_DUPLICATE_OR_INVALID_ID"
        else:raise AssertionError("DUPLICATE_EVENT_ACCEPTED")
        missing=json.loads(json.dumps(rows))
        missing[0].pop("event_id")
        altered=b"".join((json.dumps(r)+"\n").encode() for r in missing)
        manifest_bad=dict(manifest,source_sha256=_digest(altered),source_bytes=len(altered))
        try:replay_from_raw(model,manifest_bad,altered,decision_timestamp_ms=1000,
             operand_to_feature={"buff.foo.stack":"stack"})
        except ValueError as e:assert str(e)=="RAW_EVENT_NOT_EXPLICIT_TRANSITION"
        else:raise AssertionError("MISSING_EVENT_ID_ACCEPTED")
        target_event=dict(rows[0],scope="TARGET")
        target_raw=(json.dumps(target_event)+"\n").encode()
        target_capture=dict(manifest,source_sha256=_digest(target_raw),
                            source_bytes=len(target_raw))
        try:build_fixture_from_raw(model,target_capture,target_raw,
             decision_timestamp_ms=1000,operand_to_feature={"buff.foo.stack":"stack"})
        except ValueError as e:assert str(e)=="RAW_TARGET_SUBJECT_IDENTITY_NOT_IMPLEMENTED"
        else:raise AssertionError("UNQUALIFIED_TARGET_STATE_ACCEPTED")
        colliding=[dict(rows[0]),dict(rows[1],scope="ENCOUNTER",event_id="other_scope")]
        collision_raw=b"".join((json.dumps(row)+"\n").encode() for row in colliding)
        collision_capture=dict(manifest,source_sha256=_digest(collision_raw),
                               source_bytes=len(collision_raw))
        try:build_fixture_from_raw(model,collision_capture,collision_raw,
             decision_timestamp_ms=1000,operand_to_feature={"buff.foo.stack":"stack"})
        except ValueError as e:assert str(e)=="RAW_FEATURE_SCOPE_COLLISION"
        else:raise AssertionError("MIXED_SCOPE_FEATURE_ACCEPTED")
        forged=dict(manifest,source_authority="BLIZZARD_VERIFIED")
        try:replay_from_raw(model,forged,raw,decision_timestamp_ms=1000,
             operand_to_feature={"buff.foo.stack":"stack"})
        except ValueError as e:assert str(e)=="RAW_CAPTURE_CANNOT_ASSERT_TRUST"
        else:raise AssertionError("FAKE_AUTHORITY_ACCEPTED")
    print("SIMC_RAW_BYTE_PRE_TRANSITION_ADAPTER_SELF_TEST=PASS SPECS=3 SYNTHETIC_ONLY")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",type=Path)
    p.add_argument("--raw-ndjson",type=Path)
    p.add_argument("--capture",type=Path)
    p.add_argument("--decision-time-ms",type=int)
    p.add_argument("--operand-map",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test or args.model is None:
        selftest();return
    for field in ("raw_ndjson","capture","decision_time_ms","operand_map"):
        if getattr(args,field) is None:
            p.error("--raw-ndjson, --capture, --decision-time-ms and --operand-map required")
    model=json.loads(args.model.read_text("utf-8"))
    capture=json.loads(args.capture.read_text("utf-8"))
    mapping=json.loads(args.operand_map.read_text("utf-8"))
    out=replay_from_raw(model,capture,args.raw_ndjson.read_bytes(),
                        decision_timestamp_ms=args.decision_time_ms,
                        operand_to_feature=mapping)
    rendered=json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(rendered,"utf-8")
        print("WROTE_RAW_BYTE_VERIFIED_SOURCE_PRE_REPLAY")
    else:print(rendered)


if __name__=="__main__":
    main()
