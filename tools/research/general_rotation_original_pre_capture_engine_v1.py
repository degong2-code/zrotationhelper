#!/usr/bin/env python3
"""Spec-neutral, source-pinned Original PRE capture contract and replay.

Inputs: verified method-site audit + SpecAdapter operand declarations +
source-pinned UNKNOWN candidate worklist. Outputs: immutable typed capture
requests and a fail-closed reader. This does NOT execute or synthesize C++
instrumentation; a producer must implement requests and prove nonperturbation.

A correctly formatted raw observation is not an independent true readiness
predicate. READY closure, virtual dispatch and target-dummy verdicts remain
UNKNOWN until independently proven by separate engines.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from general_rotation_source_route_audit_v1 import SCHEMA as SOURCE_AUDIT_SCHEMA

SCHEMA = "ZrotGeneralRotationOriginalPRECaptureContractV1"
BOUND_SCHEMA = "ZrotGeneralRotationOriginalPREBoundRequestsV1"
REPLAY_SCHEMA = "ZrotGeneralRotationOriginalPRECaptureReplayV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
KINDS = frozenset(("bool", "int", "finite_float", "enum"))
CAPTURE_PHASE = "SIMC_ORIGINAL_METHOD_PRE"
ROW_HASH = re.compile(r"[0-9a-f]{64}\Z")
ANCHOR_HASH = re.compile(r"[0-9a-f]{64}\Z")
KEY = re.compile(r"[a-z][a-z0-9_]*\Z")
GATE = re.compile(r"[A-Z][A-Z0-9_]*\Z")


class CaptureContractError(ValueError):
    pass


def canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(value: dict) -> str:
    return sha256(canonical(value)).hexdigest()


@dataclass(frozen=True)
class Operand:
    """A semantic-layer declaration, not an executable C++ expression."""
    gate: str
    source_node: str
    name: str
    kind: str
    source_guard_sha256: str
    meaning: str

    def __post_init__(self):
        if (not GATE.fullmatch(self.gate) or
            not KEY.fullmatch(self.name) or
            not self.source_node or
            self.kind not in KINDS or
            not ANCHOR_HASH.fullmatch(self.source_guard_sha256) or
            not isinstance(self.meaning, str) or not self.meaning.strip()):
            raise CaptureContractError("INVALID_OPERAND_DECLARATION")


def compile_template(source_audit: dict, operands: tuple[Operand, ...]) -> dict:
    """Validate typed operand declarations against audited source guard sites."""
    if (not isinstance(source_audit, dict) or
        source_audit.get("schema") != SOURCE_AUDIT_SCHEMA or
        source_audit.get("source_static_route_claim") !=
            "PINNED_DECLARED_METHOD_SITES_ONLY" or
        source_audit.get("source_dispatch_exhaustive") is not False or
        source_audit.get("source_positive_READY_closure_eligible") is not False or
        source_audit.get("action_READY") != "UNKNOWN"):
        raise CaptureContractError("PINNED_OPEN_SOURCE_AUDIT_REQUIRED")
    methods = source_audit.get("source_method_evidence")
    if not isinstance(methods, list) or not methods:
        raise CaptureContractError("AUDITED_SOURCE_METHODS_REQUIRED")
    keyed = {m["node_key"]: m for m in methods}
    if len(keyed) != len(methods):
        raise CaptureContractError("DUPLICATE_AUDITED_METHOD_ID")
    fields = []
    seen = set()
    for op in operands:
        if not isinstance(op, Operand):
            raise CaptureContractError("OPERAND_TYPE_REQUIRED")
        unique = (op.gate, op.source_node, op.name)
        if unique in seen:
            raise CaptureContractError("DUPLICATE_CAPTURE_FIELD")
        seen.add(unique)
        method = keyed.get(op.source_node)
        if method is None or op.gate not in method["gate_hints"]:
            raise CaptureContractError("OPERAND_UNDECLARED_GATE_OR_METHOD")
        if op.source_guard_sha256 not in {
            g["fragment_sha256"] for g in method["guard_sites"]
        }:
            raise CaptureContractError("OPERAND_GUARD_NOT_SOURCE_AUDITED")
        field = {
            "gate": op.gate,
            "source_node": op.source_node,
            "operand_name": op.name,
            "value_kind": op.kind,
            "source_guard_fragment_sha256": op.source_guard_sha256,
            "meaning": op.meaning,
            "source_path": method["source_path"],
            "source_git_blob_sha1": method["source_git_blob_sha1"],
            "source_method_body_sha256": method["method_body_sha256"],
            "source_virtual_dispatch_unresolved":method["dispatch_unresolved"],
            "capture_phase":CAPTURE_PHASE,
            "CXX_read_expression":"NOT_DECLARED_UNTIL_PRODUCER_REVIEW",
            "raw_PRE_fact_available":False,
        }
        field["field_id"] = sha256(canonical({
            k: field[k] for k in (
                "gate", "source_node", "operand_name", "value_kind",
                "source_guard_fragment_sha256", "source_git_blob_sha1",
                "source_method_body_sha256", "capture_phase")
        })).hexdigest()
        fields.append(field)
    fields.sort(key=lambda x:(x["gate"], x["source_node"], x["operand_name"]))
    if not fields:
        raise CaptureContractError("EMPTY_SOURCE_CAPTURE_TEMPLATE")
    template = {
        "schema":SCHEMA, "policy":POLICY,
        "source_route_name":source_audit["source_route_name"],
        "source_root_method":source_audit["root_method"],
        "source_method_nodes_verified":source_audit["source_method_nodes_verified"],
        "field_count":len(fields), "fields":fields,
        "source_route_exhaustive":False,
        "dynamic_virtual_dispatch_verified":False,
        "capture_producer_implemented":False,
        "positive_READY_certified":0,
        "WCL_API_calls":0,
    }
    template["template_sha256"] = digest(template)
    return template


def bind_worklist(template: dict, worklist: dict) -> dict:
    """Attach source-row/time identity without inferring state or READY."""
    if not isinstance(template,dict) or template.get("schema") != SCHEMA:
        raise CaptureContractError("CAPTURE_TEMPLATE_REQUIRED")
    check = dict(template)
    claimed_hash = check.pop("template_sha256", None)
    if claimed_hash != digest(check):
        raise CaptureContractError("TEMPLATE_HASH_OR_FIELDS_CHANGED")
    if (not isinstance(worklist,dict) or
        worklist.get("schema") != "ZrotGeneralRotationSourceObligationWorklistV1" or
        worklist.get("source_route_name") != template["source_route_name"] or
        worklist.get("physical_skill_READY") != "UNKNOWN" or
        not ROW_HASH.fullmatch(str(worklist.get("source_row_sha256",""))) or
        type(worklist.get("at_simc_ms")) is not int or
        worklist["at_simc_ms"] < 0 or
        not worklist.get("source_action") or
        worklist.get("actual_dynamic_route_parity") != "UNKNOWN"):
        raise CaptureContractError("SOURCE_PINNED_UNKNOWN_WORKLIST_REQUIRED")
    gaps = worklist.get("required_source_evidence")
    if (not isinstance(gaps,list) or not gaps or
        len(gaps) != worklist.get("missing_gate_count") or
        len({x["gate"] for x in gaps}) != len(gaps)):
        raise CaptureContractError("SOURCE_GAP_COHORT_INVALID")
    requests = []
    uninstrumented = []
    for gap in sorted(gaps,key=lambda x:x["gate"]):
        if gap.get("skill_READY") != "UNKNOWN":
            raise CaptureContractError("SOURCE_GAP_WRONGLY_READY")
        nodes = {s["source_node_key"]:s for s in gap["source_site_candidates"]}
        if len(nodes)!=len(gap["source_site_candidates"]):
            raise CaptureContractError("DUPLICATE_SOURCE_GAP_SITE")
        selected = []
        for field in template["fields"]:
            if field["gate"] != gap["gate"]:
                continue
            site = nodes.get(field["source_node"])
            if site is None:
                continue
            if (site["source_git_blob_sha1"] != field["source_git_blob_sha1"] or
                site["method_body_sha256"] != field["source_method_body_sha256"]):
                raise CaptureContractError("CAPTURE_SITE_CHANGED_FROM_AUDIT")
            selected.append(field)
        if not selected:
            uninstrumented.append(gap["gate"])
        for field in selected:
            request={
                "request_id":field["field_id"],
                "gate":gap["gate"],
                "source_node":field["source_node"],
                "operand_name":field["operand_name"],
                "value_kind":field["value_kind"],
                "capture_phase":field["capture_phase"],
                "source_git_blob_sha1":field["source_git_blob_sha1"],
                "source_method_body_sha256":field["source_method_body_sha256"],
                "source_guard_fragment_sha256":field["source_guard_fragment_sha256"],
                "implementation_state":"PRODUCER_REQUEST_ONLY",
                "independent_gate_truth":"UNKNOWN",
            }
            requests.append(request)
    if len({x["request_id"] for x in requests}) != len(requests):
        raise CaptureContractError("BOUND_REQUEST_ID_REUSED")
    result={
        "schema":BOUND_SCHEMA, "policy":POLICY,
        "template_sha256":template["template_sha256"],
        "source_route_name":template["source_route_name"],
        "source_row_sha256":worklist["source_row_sha256"],
        "source_action":worklist["source_action"],
        "at_simc_ms":worklist["at_simc_ms"],
        "source_missing_gate_count":len(gaps),
        "requested_operand_count":len(requests),
        "gates_without_declared_operand_capture":sorted(uninstrumented),
        "requests":requests,
        "all_actual_capture_producers_proven":False,
        "source_route_exhaustive":False,
        "physical_skill_READY":"UNKNOWN",
        "dummy_error_permitted":False,
    }
    result["bound_request_sha256"]=digest(result)
    return result


def _valid_value(kind: str, value) -> bool:
    if kind=="bool":
        return type(value) is bool
    if kind=="int":
        return type(value) is int
    if kind=="finite_float":
        return type(value) in (int,float) and math.isfinite(value)
    if kind=="enum":
        return type(value) is str and bool(re.fullmatch(r"[A-Z][A-Z0-9_]*", value))
    raise CaptureContractError("UNKNOWN_CAPTURE_DATA_KIND")


def validate_pre_records(bound: dict, records: list[dict]) -> dict:
    """Check strict original PRE transport identity; no semantic truth inference.

    Records are not independently authenticated by this validator. The caller
    must separately verify its original source producer before they can be
    used as independent guard evidence by the decision proof engine.
    """
    if not isinstance(bound,dict) or bound.get("schema")!=BOUND_SCHEMA:
        raise CaptureContractError("BOUND_CAPTURE_CONTRACT_REQUIRED")
    clone=dict(bound)
    claimed=clone.pop("bound_request_sha256",None)
    if claimed!=digest(clone):
        raise CaptureContractError("BOUND_REQUEST_HASH_CHANGED")
    if not isinstance(records,list):
        raise CaptureContractError("CAPTURE_RECORDS_LIST_REQUIRED")
    requests={x["request_id"]:x for x in bound["requests"]}
    if len(requests)!=len(bound["requests"]):
        raise CaptureContractError("DUPLICATE_BOUND_REQUESTS")
    seen={}
    expected={
        "request_id","source_row_sha256","source_action","at_simc_ms",
        "observed_at_simc_ms","capture_phase","source_git_blob_sha1",
        "source_method_body_sha256","source_guard_fragment_sha256",
        "value","producer_receipt"
    }
    for rec in records:
        if not isinstance(rec,dict) or set(rec)!=expected:
            raise CaptureContractError("CAPTURE_RECORD_FIELDS_EXACTLY_REQUIRED")
        request=requests.get(rec["request_id"])
        if request is None or rec["request_id"] in seen:
            raise CaptureContractError("UNKNOWN_OR_DUPLICATE_CAPTURE_REQUEST")
        if (rec["source_row_sha256"] != bound["source_row_sha256"] or
            rec["source_action"] != bound["source_action"] or
            type(rec["at_simc_ms"]) is not int or
            rec["at_simc_ms"] != bound["at_simc_ms"] or
            type(rec["observed_at_simc_ms"]) is not int or
            rec["observed_at_simc_ms"] != bound["at_simc_ms"] or
            rec["capture_phase"] != CAPTURE_PHASE or
            any(rec[x] != request[x] for x in (
                "source_git_blob_sha1","source_method_body_sha256",
                "source_guard_fragment_sha256")) or
            not isinstance(rec["producer_receipt"],str) or
            not rec["producer_receipt"].strip()):
            raise CaptureContractError("SOURCE_PRE_IDENTITY_OR_RECEIPT_INVALID")
        if not _valid_value(request["value_kind"],rec["value"]):
            raise CaptureContractError("SOURCE_PRE_TYPED_VALUE_INVALID")
        seen[rec["request_id"]]=rec
    unresolved=[x for x in bound["requests"] if x["request_id"] not in seen]
    return {
        "schema":REPLAY_SCHEMA,
        "source_row_sha256":bound["source_row_sha256"],
        "at_simc_ms":bound["at_simc_ms"],
        "request_total":len(requests),
        "records_transport_validated":len(seen),
        "missing_request_count":len(unresolved),
        "missing_request_ids":[x["request_id"] for x in unresolved],
        "unaddressed_gate_count":len(bound["gates_without_declared_operand_capture"]),
        "transport_record_truth_claim":"FORMAT_AND_SOURCE_IDENTITY_ONLY",
        "producer_authenticity_and_nonperturbation_proven":False,
        "independent_full_gate_truth_proven":False,
        "full_virtual_route_closed":False,
        "physical_skill_READY":"UNKNOWN",
        "target_dummy_error_permitted":False,
    }


def selftest() -> dict:
    h="a"*64
    guard="b"*64
    site={
        "node_key":"generic_cast","source_path":"fixture.cpp",
        "source_git_blob_sha1":"c"*40,"method_body_sha256":h,
        "guard_sites":[{"fragment_sha256":guard}],
        "gate_hints":["CAST_GCD"],"dispatch_unresolved":True
    }
    route={
        "schema":SOURCE_AUDIT_SCHEMA,"source_static_route_claim":
            "PINNED_DECLARED_METHOD_SITES_ONLY",
        "source_dispatch_exhaustive":False,
        "source_positive_READY_closure_eligible":False,
        "action_READY":"UNKNOWN","source_route_name":"generic_fixture",
        "root_method":"generic_cast","source_method_nodes_verified":1,
        "source_method_evidence":[site]
    }
    operand=Operand("CAST_GCD","generic_cast","gcd_ready_ms","int",guard,
                    "original PRE GCD timestamp")
    template=compile_template(route,(operand,))
    assert template["field_count"]==1
    gap={
        "schema":"ZrotGeneralRotationSourceObligationWorklistV1",
        "source_route_name":"generic_fixture",
        "physical_skill_READY":"UNKNOWN","actual_dynamic_route_parity":"UNKNOWN",
        "source_row_sha256":h,"source_action":"cast","at_simc_ms":50,
        "missing_gate_count":2,
        "required_source_evidence":[
            {"gate":"CAST_GCD","skill_READY":"UNKNOWN",
             "source_site_candidates":[{
                 "source_node_key":"generic_cast","source_git_blob_sha1":"c"*40,
                 "method_body_sha256":h}]},
            {"gate":"BASE_VIRTUAL_COMPLETE","skill_READY":"UNKNOWN",
             "source_site_candidates":[]}
        ]
    }
    bound=bind_worklist(template,gap)
    assert bound["requested_operand_count"]==1
    assert bound["gates_without_declared_operand_capture"]==["BASE_VIRTUAL_COMPLETE"]
    assert validate_pre_records(bound,[])["physical_skill_READY"]=="UNKNOWN"
    request=bound["requests"][0]
    good={
        "request_id":request["request_id"],
        "source_row_sha256":h,"source_action":"cast",
        "at_simc_ms":50,"observed_at_simc_ms":50,
        "capture_phase":CAPTURE_PHASE,
        "source_git_blob_sha1":request["source_git_blob_sha1"],
        "source_method_body_sha256":request["source_method_body_sha256"],
        "source_guard_fragment_sha256":request["source_guard_fragment_sha256"],
        "value":1234, "producer_receipt":"SYNTHETIC_UNTRUSTED_PRODUCER"
    }
    outcome=validate_pre_records(bound,[good])
    assert outcome["records_transport_validated"]==1
    assert not outcome["producer_authenticity_and_nonperturbation_proven"]
    for bad in (
        dict(good,observed_at_simc_ms=51),
        dict(good,at_simc_ms=49),
        dict(good,source_row_sha256="f"*64),
        dict(good,source_action="other"),
        dict(good,value=True),
        dict(good,producer_receipt=""),
        dict(good,native_ready=True)
    ):
        try: validate_pre_records(bound,[bad])
        except CaptureContractError: pass
        else:raise AssertionError("FORGED_OR_NONPRE_RAW_RECORD_ACCEPTED")
    for invalid in (
        Operand("CAST_GCD","generic_cast","gcd_ready_ms","int","f"*64,"drift"),
        Operand("CAST_GCD","generic_cast","gcd_ready_ms","bool",guard,"duplicate type")
    ):
        if invalid.source_guard_sha256==guard:
            try:compile_template(route,(operand,invalid))
            except CaptureContractError:pass
            else:raise AssertionError("CONFLICTING_CAPTURE_DECLARATION_ACCEPTED")
        else:
            try:compile_template(route,(invalid,))
            except CaptureContractError:pass
            else:raise AssertionError("UNPINNED_CAPTURE_GUARD_ACCEPTED")
    return {
        "schema":SCHEMA, "status":"PASS_OFFLINE_SYNTHETIC",
        "checks":17,"synthetic_spec_count":1,
        "actual_source_producer_tested":False,
        "positive_READY_certified":0,"WCL_API_calls":0
    }


if __name__=="__main__":
    print(json.dumps(selftest(),sort_keys=True))
