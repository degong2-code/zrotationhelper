#!/usr/bin/env python3
"""ST-04 exact raw NDJSON -> ST-03 ledger adapter, RESEARCH ONLY.

No native SimC, WCL, or Blizzard claim. Capture is caller supplied, and SHA256
authenticates equality to supplied bytes, NOT the upstream event producer.
Do not import this module into blind WCL discovery (post-SimC lane only).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

import ST03_source_pre_observability_v1 as st03

SCHEMA = "ZrotST04RawFeatureCaptureV1"
ORIGINS = {
    "SYNTHETIC_FEATURE_TRANSITIONS": "SYNTHETIC_TEST",
    "EXTERNAL_FEATURE_TRANSITIONS_UNVERIFIED": "EXTERNAL_DECLARED_UNVERIFIED",
}
LIMIT_BYTES = 3_000_000
LIMIT_ROWS = 20_000


class ST04CaptureError(ValueError):
    pass


def _object_pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ST04CaptureError("RAW_DUPLICATE_JSON_KEY")
        result[k] = v
    return result


def _bad_number(_):
    raise ST04CaptureError("RAW_NONFINITE_CONSTANT")


def reconstruct(raw: bytes, capture: Mapping[str, Any]) -> tuple[dict, dict]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= LIMIT_BYTES:
        raise ST04CaptureError("INVALID_RAW_BYTE_SIZE")
    if not raw.endswith(b"\n"):
        raise ST04CaptureError("RAW_FINAL_NEWLINE_REQUIRED")
    if not isinstance(capture, Mapping) or capture.get("schema") != SCHEMA:
        raise ST04CaptureError("CAPTURE_SCHEMA")
    if capture.get("phase") != st03.PHASE:
        raise ST04CaptureError("BLIND_WCL_SEMANTIC_LEAKAGE_FORBIDDEN")
    kind = capture.get("capture_kind")
    if kind not in ORIGINS or capture.get("source_authority") != "CALLER_SUPPLIED_UNVERIFIED":
        raise ST04CaptureError("CAPTURE_AUTHORITY_UNVERIFIED_ONLY")
    if capture.get("verified_producer") is not False or capture.get("gameplay_promotion") is not False:
        raise ST04CaptureError("CAPTURE_PREMATURE_PROMOTION")
    if capture.get("event_semantics") != "DECLARED_FEATURE_CHANGE_NOT_SNAPSHOT":
        raise ST04CaptureError("RAW_SNAPSHOT_OR_POST_ACTION_FORBIDDEN")
    digest = hashlib.sha256(raw).hexdigest()
    if capture.get("raw_sha256") != digest or capture.get("raw_size_bytes") != len(raw):
        raise ST04CaptureError("RAW_SOURCE_BYTES_SHA_MISMATCH")
    if not isinstance(capture.get("feature_bindings"), dict) or not isinstance(capture.get("capture_ref"), str) or not capture["capture_ref"].strip():
        raise ST04CaptureError("CAPTURE_PROVENANCE_OR_BINDINGS_MISSING")
    for key in ("decision_timestamp_ms", "decision_actor_id",
                "decision_target_id", "action_token"):
        if key not in capture:
            raise ST04CaptureError("CAPTURE_MISSING_" + key)
    events = []
    receipts = []
    offset = 0
    for number, line in enumerate(raw.splitlines(keepends=True), 1):
        if number > LIMIT_ROWS:
            raise ST04CaptureError("RAW_ROW_LIMIT")
        if not line.endswith(b"\n") or not line[:-1].strip():
            raise ST04CaptureError("RAW_LINE_INVALID")
        try:
            event = json.loads(
                line.decode("utf-8"), object_pairs_hook=_object_pairs,
                parse_constant=_bad_number,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ST04CaptureError("INVALID_RAW_JSON") from exc
        if not isinstance(event, dict) or set(event) != st03.FIELDS:
            raise ST04CaptureError("RAW_ROW_MUST_BE_EXPLICIT_TYPED_FEATURE_TRANSITION")
        events.append(event)
        receipts.append({
            "source_line": number, "offset": offset,
            "raw_line_sha256": hashlib.sha256(line).hexdigest(),
            "event_id": event["event_id"],
        })
        offset += len(line)
    ledger = {
        "schema": st03.SCHEMA,
        "phase": st03.PHASE,
        "provenance_class": ORIGINS[kind],
        "verified_producer": False,
        "decision_timestamp_ms": capture["decision_timestamp_ms"],
        "decision_actor_id": capture["decision_actor_id"],
        "decision_target_id": capture["decision_target_id"],
        "action_token": capture["action_token"],
        "feature_bindings": capture["feature_bindings"],
        "events": events,
        "ledger_sha256": st03.digest(events),
    }
    return ledger, {
        "schema": "ZrotST04RawProjectionReceiptV1",
        "capture_ref": capture["capture_ref"],
        "raw_sha256": digest, "raw_size_bytes": len(raw),
        "raw_line_receipts": receipts,
        "source_authenticity": "NOT_INDEPENDENTLY_VERIFIED",
        "mechanic_truth": "NOT_VERIFIED",
        "wcl_blind_semantic_use": False,
        "product_promotion": False,
    }


def run(*, raw: bytes, capture: Mapping[str, Any],
        st02_case: Mapping[str, Any], readiness_contract: Mapping[str, Any]):
    """Audit before accepting result; no recommendation/READY authority."""
    ledger, projected = reconstruct(raw, capture)
    # Independent byte-to-ledger audit must not import this producer.
    import ST04_independent_raw_pre_audit_v1 as reviewer
    reviewer.check_raw_projection(raw, capture, ledger, projected)
    result = st03.evaluate(
        st02_case=st02_case,
        readiness_contract=readiness_contract, ledger=ledger)
    review = reviewer.check_pre_decision(raw, capture, ledger, projected,
                                         st02_case, readiness_contract,
                                         result.to_dict())
    return result, projected, review
