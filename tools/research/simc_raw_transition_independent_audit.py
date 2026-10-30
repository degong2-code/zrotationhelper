#!/usr/bin/env python3
"""Independent byte-to-ledger recalculation for generic candidate PRE events.

Do NOT import producer/extraction functions. Reparse every raw NDJSON line,
compute each source-line hash and expected bridge transition from raw field
values, compare full ledger and SHA, and refuse added/changed event claims.
Proves equality to caller-provided bytes only; NOT data-collector authenticity,
timing semantics, SimC/Blizzard mechanics or trusted WCL state.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

_SHA=re.compile(r"^[a-f0-9]{64}$")
_RESULT="ZrotIndependentRawFeatureTransitionRowAuditV1"


def independent_raw_audit(model:dict,capture:dict,raw:bytes,output:dict)->dict:
    """Independent field-by-field recomputation, no producer helper calls."""
    if not isinstance(raw,bytes) or not raw.endswith(b"\n"):
        raise ValueError("INDEPENDENT_SOURCE_BYTES_INVALID")
    if not isinstance(output,dict) or output.get("schema")!=(
            "ZrotSourceByteReconstructedStrictPreFixtureV1"):
        raise ValueError("INDEPENDENT_PRODUCER_OUTPUT_SCHEMA")
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=capture.get("source_sha256") or digest!=output.get("source_raw_sha256"):
        raise ValueError("INDEPENDENT_RAW_SHA_MISMATCH")
    if len(raw)!=capture.get("source_bytes") or len(raw)!=output.get("source_bytes"):
        raise ValueError("INDEPENDENT_RAW_SIZE_MISMATCH")
    if capture.get("capture_ref")!=output.get("capture_ref") or (
            capture.get("capture_kind")!=output.get("capture_kind")):
        raise ValueError("INDEPENDENT_CAPTURE_IDENTITY_MISMATCH")
    if capture.get("source_authority")!="CALLER_SUPPLIED_UNVERIFIED" or (
            capture.get("source_event_semantics")!="FEATURE_CHANGE_NOT_SNAPSHOT"):
        raise ValueError("INDEPENDENT_CAPTURE_AUTHORITY_FORBIDDEN")
    if output.get("source_authenticity")!="NOT_INDEPENDENTLY_VERIFIED" or (
            output.get("gameplay_rule_promotion") is not False):
        raise ValueError("INDEPENDENT_OUTPUT_PREMATURE_AUTHORITY")
    fixture=output.get("fixture")
    if not isinstance(fixture,dict):
        raise ValueError("INDEPENDENT_FIXTURE_REQUIRED")
    for a,b in (("spec","expected_spec"),("source_apl_sha256","apl_sha256"),
                ("source_profile_sha256","profile_sha256"),
                ("source_simc_executable_sha256","simc_executable_sha256")):
        if capture.get(a)!=model.get(b):
            raise ValueError("INDEPENDENT_SOURCE_MODEL_PIN_MISMATCH_"+a)
        if fixture.get(a)!=capture.get(a):
            raise ValueError("INDEPENDENT_SOURCE_FIXTURE_PIN_MISMATCH_"+a)
    if fixture.get("synthetic_action_readiness")!={} or (
            fixture.get("independently_verified_producer") is not False):
        raise ValueError("INDEPENDENT_UNVERIFIED_READY_OR_PRODUCER")
    if (capture.get("capture_kind")=="SYNTHETIC_FEATURE_TRANSITIONS"
        and fixture.get("provenance_class")!="SYNTHETIC_TEST") or (
        capture.get("capture_kind")=="EXTERNAL_NORMALIZED_FEATURE_TRANSITIONS_UNVERIFIED"
        and fixture.get("provenance_class")!="EXTERNAL_CALLER_DECLARED_UNVERIFIED"):
        raise ValueError("INDEPENDENT_CAPTURE_KIND_CLASS_MISMATCH")
    transition_rows=fixture.get("transitions")
    receipts=output.get("source_line_receipts")
    if not isinstance(transition_rows,list) or not isinstance(receipts,list):
        raise ValueError("INDEPENDENT_TRANSITION_ARRAYS_REQUIRED")
    lines=raw.splitlines(keepends=True)
    if len(lines)!=len(transition_rows) or len(lines)!=len(receipts) or (
            len(lines)!=output.get("source_event_count")):
        raise ValueError("INDEPENDENT_EVENT_ROW_COUNT_MISMATCH")
    observed_ids=set()
    expected_transitions=[]
    expected_receipts=[]
    byte_offset=0
    for index,line in enumerate(lines):
        if not line.endswith(b"\n"):
            raise ValueError("INDEPENDENT_MALFORMED_LINE")
        stripped=line[:-1]
        if stripped.endswith(b"\r"):stripped=stripped[:-1]
        if not stripped:
            raise ValueError("INDEPENDENT_EMPTY_LINE")
        def pairs(items):
            result={}
            for key,val in items:
                if key in result:raise ValueError("INDEPENDENT_DUPLICATE_JSON_KEY")
                result[key]=val
            return result
        try:
            event=json.loads(stripped.decode("utf-8"),object_pairs_hook=pairs,
                             parse_constant=lambda _: (_ for _ in ()).throw(
                                 ValueError("INDEPENDENT_NONFINITE_NUMBER")))
        except (UnicodeDecodeError,json.JSONDecodeError) as e:
            raise ValueError("INDEPENDENT_MALFORMED_EVENT") from e
        if not isinstance(event,dict) or set(event)!={
                "event_kind","event_id","timestamp_ms","sequence","feature_key",
                "value","scope","valid"} or event.get("event_kind")!="FEATURE_TRANSITION":
            raise ValueError("INDEPENDENT_UNSUPPORTED_EVENT_TYPE")
        eid=event["event_id"]
        if not isinstance(eid,str) or not eid or eid in observed_ids:
            raise ValueError("INDEPENDENT_DUPLICATE_EVENT")
        observed_ids.add(eid)
        t=event["timestamp_ms"]
        n=event["sequence"]
        if type(t) is not int or t<0 or type(n) is not int or n<0:
            raise ValueError("INDEPENDENT_TIME_OR_SEQUENCE_INVALID")
        value=event["value"]
        if not (type(value) is bool or type(value) in (int,float)
                and math.isfinite(value)):
            raise ValueError("INDEPENDENT_VALUE_NOT_FINITE_NUMBER")
        key=event["feature_key"]
        if not isinstance(key,str) or not key or (
                event["scope"] not in ("ACTOR","TARGET","ENCOUNTER")) or (
                type(event["valid"]) is not bool):
            raise ValueError("INDEPENDENT_FEATURE_SCOPE_INVALID")
        evidence=f"raw-line:{index+1}:offset:{byte_offset}:sha256:{hashlib.sha256(stripped).hexdigest()}"
        expected_transitions.append({
            "timestamp_ms":t,"sequence":n,"feature_key":key,
            "value":value,"valid":event["valid"],
            "producer_ref":"raw-sha256:"+digest,"evidence_ref":evidence,
        })
        expected_receipts.append({
            "event_id":eid,"source_line":index+1,"byte_offset":byte_offset,
            "raw_line_sha256":hashlib.sha256(stripped).hexdigest(),
            "source_scope":event["scope"],"source_time_ms":t,
            "feature_key":key,"strictly_before_decision":t<fixture["decision_timestamp_ms"],
        })
        byte_offset+=len(line)
    if transition_rows!=expected_transitions or receipts!=expected_receipts:
        raise ValueError("INDEPENDENT_RAW_PROJECTION_DIVERGENCE")
    ledger_hash=hashlib.sha256(
        json.dumps(expected_transitions,ensure_ascii=False,sort_keys=True,
                   separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()
    if ledger_hash!=fixture.get("transitions_sha256"):
        raise ValueError("INDEPENDENT_TRANSITION_LEDGER_SHA_MISMATCH")
    count_pre=sum(int(x["valid"] and x["timestamp_ms"]<fixture["decision_timestamp_ms"])
                  for x in expected_transitions)
    return {
        "schema":_RESULT,"status":"RAW_ROW_PROJECTION_VERIFIED_UNTRUSTED_SOURCE",
        "source_raw_sha256":digest,
        "recalculated_transition_sha256":ledger_hash,
        "raw_record_count":len(lines),
        "strictly_before_decision_valid_record_count":count_pre,
        "source_authenticity":"NOT_INDEPENDENTLY_VERIFIED",
        "producer_semantic_truth":"NOT_INDEPENDENTLY_VERIFIED",
        "simc_native_decision_time_state":"NOT_CAPTURED",
        "readiness_producer":"NOT_VERIFIED",
        "gameplay_rule_promotion":False,
    }


def selftest():
    from simc_apl_source_engine import ingest_actions
    from simc_raw_transition_adapter import build_fixture_from_raw
    for spec in ("imaginary","enhancement","unholy"):
        model=ingest_actions(f"spec={spec}\nactions=alpha,if=buff.test.up\n".encode(),
                             expected_spec=spec)
        row={"event_kind":"FEATURE_TRANSITION","event_id":"one",
             "timestamp_ms":10,"sequence":0,"feature_key":"test",
             "value":True,"scope":"ACTOR","valid":True}
        raw=(json.dumps(row)+"\n").encode()
        digest=hashlib.sha256(raw).hexdigest()
        capture={
            "schema":"ZrotGenericRawFeatureTransitionCaptureV1",
            "spec":spec,"source_apl_sha256":model["apl_sha256"],
            "source_profile_sha256":model.get("profile_sha256"),
            "source_simc_executable_sha256":model.get("simc_executable_sha256"),
            "capture_kind":"EXTERNAL_NORMALIZED_FEATURE_TRANSITIONS_UNVERIFIED",
            "capture_ref":"synthetic:raw", "source_authority":"CALLER_SUPPLIED_UNVERIFIED",
            "source_event_semantics":"FEATURE_CHANGE_NOT_SNAPSHOT",
            "source_sha256":digest,"source_bytes":len(raw),
            "gameplay_rule_promotion":False,
        }
        out=build_fixture_from_raw(model,capture,raw,decision_timestamp_ms=20,
                                   operand_to_feature={"buff.test.up":"test"})
        good=independent_raw_audit(model,capture,raw,out)
        assert good["raw_record_count"]==1
        assert good["strictly_before_decision_valid_record_count"]==1
        import copy
        altered=copy.deepcopy(out)
        altered["fixture"]["transitions"][0]["value"]=False
        try:independent_raw_audit(model,capture,raw,altered)
        except ValueError as e:assert str(e)=="INDEPENDENT_RAW_PROJECTION_DIVERGENCE"
        else:raise AssertionError("PRODUCER_TAMPER_ACCEPTED")
        altered=copy.deepcopy(out)
        altered["source_line_receipts"][0]["raw_line_sha256"]="0"*64
        try:independent_raw_audit(model,capture,raw,altered)
        except ValueError as e:assert str(e)=="INDEPENDENT_RAW_PROJECTION_DIVERGENCE"
        else:raise AssertionError("FAKE_LINE_RECEIPT_ACCEPTED")
        altered=copy.deepcopy(out)
        altered["fixture"]["transitions_sha256"]="0"*64
        try:independent_raw_audit(model,capture,raw,altered)
        except ValueError as e:assert str(e)=="INDEPENDENT_TRANSITION_LEDGER_SHA_MISMATCH"
        else:raise AssertionError("FAKE_LEDGER_SHA_ACCEPTED")
        altered=copy.deepcopy(out)
        altered["fixture"]["synthetic_action_readiness"]={"alpha":"READY"}
        try:independent_raw_audit(model,capture,raw,altered)
        except ValueError as e:assert str(e)=="INDEPENDENT_UNVERIFIED_READY_OR_PRODUCER"
        else:raise AssertionError("FAKE_READY_ACCEPTED")
    print("SIMC_RAW_TRANSITION_INDEPENDENT_AUDIT_SELF_TEST=PASS SPECS=3 SYNTHETIC_ONLY")


def main():
    selftest()


if __name__=="__main__":
    main()
