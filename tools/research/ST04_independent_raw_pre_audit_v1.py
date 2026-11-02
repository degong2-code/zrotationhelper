#!/usr/bin/env python3
"""Independent ST-04 reviewer: raw bytes + frozen structural contracts.

This file does NOT import ST-03, ST-04 producer, ST-02 or their helper
functions. Computes byte hashes, raw row projection, latest STRICT PRE,
diagnostic statuses and candidate-only gating from original supplied NDJSON.
Raw equality does not attest event authenticity or native SimC mechanics.
NOT for WCL blind discovery, gameplay recommendations, or MAIN promotion.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

RAW_FIELDS = frozenset((
    "event_id", "timestamp_ms", "sequence", "feature_key", "scope",
    "subject_id", "status", "value", "valid", "producer_ref", "evidence_ref",
))
OPS = {
    "eq": lambda x, y: x == y, "ne": lambda x, y: x != y,
    "lt": lambda x, y: x < y, "le": lambda x, y: x <= y,
    "gt": lambda x, y: x > y, "ge": lambda x, y: x >= y,
}


class ST04IndependentFailure(ValueError):
    pass


def _pairs(items):
    result = {}
    for k, v in items:
        if k in result:
            raise ST04IndependentFailure("INDEPENDENT_DUPLICATE_JSON_KEY")
        result[k] = v
    return result


def _reject_nonfinite(_):
    raise ST04IndependentFailure("INDEPENDENT_NONFINITE_RAW_NUMBER")


def _raw_bytes(raw: bytes):
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or not raw:
        raise ST04IndependentFailure("INDEPENDENT_RAW_BYTES_INVALID")
    events, lines = [], []
    offset = 0
    for lineno, exact_line in enumerate(raw.splitlines(keepends=True), 1):
        try:
            item = json.loads(
                exact_line.decode("utf-8"), object_pairs_hook=_pairs,
                parse_constant=_reject_nonfinite)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ST04IndependentFailure("INDEPENDENT_RAW_PARSE_FAILURE") from exc
        if not isinstance(item, dict) or set(item) != RAW_FIELDS:
            raise ST04IndependentFailure("INDEPENDENT_RAW_ROW_CONTRACT")
        events.append(item)
        lines.append({
            "source_line": lineno, "offset": offset,
            "raw_line_sha256": hashlib.sha256(exact_line).hexdigest(),
            "event_id": item["event_id"],
        })
        offset += len(exact_line)
    return events, lines


def _canonical_digest(items: list[dict]) -> str:
    return hashlib.sha256(
        json.dumps(items,sort_keys=True,separators=(",",":"),
                   ensure_ascii=False,allow_nan=False).encode("utf-8")
    ).hexdigest()


def check_raw_projection(raw: bytes, capture: Mapping[str, Any],
                         ledger: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict:
    """Independently recreate complete ledger and source-line receipts."""
    events, lines = _raw_bytes(raw)
    d = hashlib.sha256(raw).hexdigest()
    if (capture.get("raw_sha256") != d or capture.get("raw_size_bytes") != len(raw)
            or receipt.get("raw_sha256") != d or receipt.get("raw_size_bytes") != len(raw)):
        raise ST04IndependentFailure("INDEPENDENT_RAW_BYTES_SHA_MISMATCH")
    if (capture.get("schema") != "ZrotST04RawFeatureCaptureV1"
            or capture.get("phase") != "POST_SIMC_HYPOTHESIS_RESEARCH_ONLY"
            or capture.get("source_authority") != "CALLER_SUPPLIED_UNVERIFIED"
            or capture.get("verified_producer") is not False
            or capture.get("gameplay_promotion") is not False
            or capture.get("event_semantics") != "DECLARED_FEATURE_CHANGE_NOT_SNAPSHOT"):
        raise ST04IndependentFailure("INDEPENDENT_CAPTURE_AUTHORITY")
    origin = {
        "SYNTHETIC_FEATURE_TRANSITIONS": "SYNTHETIC_TEST",
        "EXTERNAL_FEATURE_TRANSITIONS_UNVERIFIED": "EXTERNAL_DECLARED_UNVERIFIED",
    }.get(capture.get("capture_kind"))
    if origin is None:
        raise ST04IndependentFailure("INDEPENDENT_CAPTURE_KIND")
    expected_ledger = {
        "schema": "ZrotST03DeclaredSourceTransitionLedgerV1",
        "phase": "POST_SIMC_HYPOTHESIS_RESEARCH_ONLY",
        "provenance_class": origin, "verified_producer": False,
        "decision_timestamp_ms": capture.get("decision_timestamp_ms"),
        "decision_actor_id": capture.get("decision_actor_id"),
        "decision_target_id": capture.get("decision_target_id"),
        "action_token": capture.get("action_token"),
        "feature_bindings": capture.get("feature_bindings"),
        "events": events,
        "ledger_sha256": _canonical_digest(events),
    }
    if ledger != expected_ledger:
        raise ST04IndependentFailure("INDEPENDENT_LEDGER_PROJECTION_CONFLICT")
    if receipt != {
        "schema": "ZrotST04RawProjectionReceiptV1",
        "capture_ref": capture.get("capture_ref"),
        "raw_sha256": d, "raw_size_bytes": len(raw),
        "raw_line_receipts": lines,
        "source_authenticity": "NOT_INDEPENDENTLY_VERIFIED",
        "mechanic_truth": "NOT_VERIFIED",
        "wcl_blind_semantic_use": False,
        "product_promotion": False,
    }:
        raise ST04IndependentFailure("INDEPENDENT_LINE_RECEIPT_CONFLICT")
    return {"raw_sha256": d, "event_count": len(events),
            "row_projection": "INDEPENDENT_MATCH_UNTRUSTED_SOURCE"}


def _latest(key: str, ledger: Mapping[str, Any], events: list[dict]):
    binding = ledger["feature_bindings"].get(key)
    if binding is None:
        return ("UNKNOWN_UNMAPPED", None, None)
    if binding["scope"] == "TARGET" and ledger["decision_target_id"] is None:
        return ("UNKNOWN_TARGET_IDENTITY", None, None)
    eligible = {}
    decision_time = ledger["decision_timestamp_ms"]
    for event in events:
        if (event["feature_key"] == key and event["valid"] is True
                and event["scope"] == binding["scope"]
                and event["subject_id"] == binding["subject_id"]
                and event["timestamp_ms"] < decision_time):
            eligible.setdefault(event["timestamp_ms"], set()).add(
                (event["status"], event["value"]))
    if not eligible:
        return ("UNKNOWN_NO_STRICT_PRE", None, None)
    latest_time = max(eligible)
    last_set = eligible[latest_time]
    if len(last_set) != 1:
        return ("UNKNOWN_CONFLICTING_PRE", None, None)
    state, value = next(iter(last_set))
    if state != "OBSERVED":
        return ("UNKNOWN_LATEST_PRE" if state == "UNKNOWN" else "UNOBSERVABLE_PRE",
                latest_time, None)
    return ("OBSERVED_STRICT_PRE_UNVERIFIED", latest_time, float(value))


def check_pre_decision(raw: bytes, capture: Mapping[str, Any],
                       ledger: Mapping[str, Any], projection: Mapping[str, Any],
                       st02_case: Mapping[str, Any], readiness_contract: Mapping[str, Any],
                       result: Mapping[str, Any]) -> dict:
    """Independent PRE+gate comparison. Does not certify state producer truth."""
    evidence = check_raw_projection(raw, capture, ledger, projection)
    events, _ = _raw_bytes(raw)
    source = json.loads(st02_case["source_json"])
    selector = st02_case["selector"]
    action = [a for a in source["candidate_actions"]
              if a["action"] == selector["action_token"] and
                 a["spec"] == selector["source_spec"]]
    if len(action) != 1:
        raise ST04IndependentFailure("INDEPENDENT_SOURCE_ACTION_AMBIGUOUS")
    required = {g["id"]: tuple(g["required_state"])
                for g in action[0]["extra_source_obligations"]}
    features = {feature for values in required.values() for feature in values}
    for policy in readiness_contract.get("actions", {}).values():
        for dimension in policy.get("dimensions", {}).values():
            for predicate in dimension.get("predicates", []):
                features.add(predicate["feature"])
    observed = {key: _latest(key,ledger,events) for key in features}
    calculated = {
        name: {
            "status": observed[name][0],
            "latest_pre_timestamp_ms": (
                str(observed[name][1]) if observed[name][1] is not None else "UNKNOWN"),
        } for name in sorted(features)}
    if calculated != result.get("required_state_diagnostics"):
        raise ST04IndependentFailure("INDEPENDENT_STATE_DIAGNOSTIC_CONFLICT")

    declared = {d["gate_id"]: d for d in st02_case["declared_gates"]}
    expected_gate_diagnostics = {}
    negative = False
    unknown = False
    for gid, state_keys in sorted(required.items()):
        gate_status, gate_time, gate_value = _latest("source_gate::"+gid, ledger,events)
        missing = next((observed[key][0] for key in state_keys
                        if observed[key][0] != "OBSERVED_STRICT_PRE_UNVERIFIED"),None)
        if missing is not None:
            reason = "UNKNOWN_SOURCE_PREREQUISITE_" + missing
        elif gate_status != "OBSERVED_STRICT_PRE_UNVERIFIED":
            reason = gate_status
        elif gate_time < max(observed[key][1] for key in state_keys):
            reason = "UNKNOWN_STALE_GATE_BEFORE_SOURCE_STATE"
        elif result["source_coverage_status"] != "DECLARED_SOURCE_COVERAGE_CANDIDATE_ONLY":
            reason = "UNKNOWN_SOURCE_POLICY_INCOMPLETE"
        else:
            reason = "SOURCE_GATE_DECLARED_PRE_UNVERIFIED"
        expected_gate_diagnostics[gid] = reason
        if reason != "SOURCE_GATE_DECLARED_PRE_UNVERIFIED":
            unknown = True
        else:
            policy = declared.get(gid)
            if not policy or policy.get("mode") != "REQUIRED" or policy.get("op") not in OPS:
                unknown = True
            else:
                value = policy.get("threshold")
                if type(value) not in (int, float) or not math.isfinite(value):
                    unknown = True
                elif not OPS[policy["op"]](gate_value, value):
                    negative = True
    if expected_gate_diagnostics != result.get("source_gate_diagnostics"):
        raise ST04IndependentFailure("INDEPENDENT_GATE_DIAGNOSTIC_CONFLICT")
    if len(declared) != len(required):
        unknown = True
    upstream = result.get("upstream_readiness")
    if upstream not in ("READY","NOT_READY","UNKNOWN"):
        raise ST04IndependentFailure("INDEPENDENT_BAD_UPSTREAM_VERDICT")
    if upstream == "NOT_READY" or negative:
        expected_status = "OBSERVED_NEGATIVE_RESEARCH_ONLY"
    elif upstream == "UNKNOWN" or unknown:
        expected_status = "UNKNOWN"
    else:
        expected_status = "ALL_DECLARED_GATES_PASS_RESEARCH_ONLY"
    if expected_status != result.get("status"):
        raise ST04IndependentFailure("INDEPENDENT_RESEARCH_VERDICT_CONFLICT")

    time = ledger["decision_timestamp_ms"]
    counters = {
        "excluded_same_timestamp_n": sum(
            e["valid"] is True and e["timestamp_ms"] == time for e in events),
        "excluded_future_n": sum(
            e["valid"] is True and e["timestamp_ms"] > time for e in events),
        "excluded_invalid_n": sum(e["valid"] is False for e in events),
    }
    if any(result.get(k) != v for k,v in counters.items()):
        raise ST04IndependentFailure("INDEPENDENT_TIME_COUNTER_CONFLICT")
    if (result.get("ledger_sha256") != ledger["ledger_sha256"]
        or result.get("provenance_class") != ledger["provenance_class"]
        or result.get("source_authenticity") != "NOT_INDEPENDENTLY_VERIFIED"
        or result.get("live_gameplay_readiness_certified") != 0
        or result.get("authority_promotion") is not False
        or result.get("user_recommendation_eligible") is not False):
        raise ST04IndependentFailure("INDEPENDENT_AUTHORITY_BOUNDARY")
    return {
        "schema":"ZrotST04IndependentRawPreAuditV1",
        "status":"INDEPENDENT_MATCH_UNTRUSTED_SOURCE",
        **evidence,
        "checked_state_features":len(features),
        "checked_source_gates":len(required),
        "producer_authenticity":"NOT_VERIFIED",
        "mechanic_semantics":"NOT_VERIFIED",
        "independent_wcl_blind":"NOT_RUN",
        "gameplay_ready_certified":0,
        "main_or_frozen_promotion":False,
    }
