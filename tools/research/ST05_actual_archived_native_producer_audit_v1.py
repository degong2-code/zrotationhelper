#!/usr/bin/env python3
"""ST-05: offline replay of byte-pinned ACTUAL archived SimC native markers.

Uses existing source-epoch and bare-resource auditors without modifying them.
Actual archive from pinned GitHub Actions source run is public-profile proof.
This file never infers source-specific spell readiness or current Retail rules.
Run with --archive path/to/zip; --self-test also checks wrong-byte rejection.
Only reads bytes, emits one safe summary; no live API/WCL/SimC.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from simc_native_bare_resource_eval_audit import audit as native_eval_audit

ROOT=Path(__file__).resolve().parents[2]
NATIVE_DOC=ROOT/"docs/BR_SIMC_ARCHIVED_NATIVE_FULL_ROW_REPLAY_20261031.json"
ACTION_DOC=ROOT/"docs/BR_SIMC_ARCHIVED_NATIVE_ACTION_ID_EVIDENCE_20261031.json"
SOURCE_DOC=ROOT/"docs/BR_SIMC_MINIMUM_READINESS_SOURCE_GAP_20261031.json"
RESOURCE_EVAL="ZROT_NATIVE_APL_RESOURCE_EVAL_V1|"
NATIVE_V2="ZROT_NATIVE_EVENT_V2|"
IF_MARK="ZROT_NATIVE_APL_IF_GUARD_V1|"
SELECT_MARK="ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|"


class PinnedNativeEvidenceError(ValueError):
    pass


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def _must(condition:bool,code:str)->None:
    if not condition:
        raise PinnedNativeEvidenceError(code)


def _docs():
    n=json.loads(NATIVE_DOC.read_text(encoding="utf-8"))
    a=json.loads(ACTION_DOC.read_text(encoding="utf-8"))
    s=json.loads(SOURCE_DOC.read_text(encoding="utf-8"))
    _must(n.get("schema")=="ZrotArchivedNativeMarkerIndependentRawReplayV12","BAD_NATIVE_PROOF_SCHEMA")
    _must(a.get("schema")=="ZrotArchivedNativeMarkerObjectIdEvidenceV11","BAD_ACTION_PROOF_SCHEMA")
    _must(s.get("schema")=="ZrotBranchSimcReadinessSourceGapV1","BAD_SOURCE_GATES_SCHEMA")
    _must(n.get("original_native_run_id")==a.get("archived_native_workflow_run")==41084262760,
          "NATIVE_RUN_ID_MISMATCH")
    _must(n.get("upstream_simc_sha")==a.get("original_upstream_commit")==s.get("simc_upstream_commit"),
          "PINNED_SIMC_UPSTREAM_MISMATCH")
    _must(n.get("original_zip_sha256")==a.get("downloaded_zip_sha256"),
          "ORIGINAL_ZIP_PIN_MISMATCH")
    _must(n.get("original_effective_apl_export_bytes_available") is False,
          "FULL_APL_EXPORT_NOT_AVAILABLE_EXPECTED")
    _must(n.get("readiness_certified")==0 and a["totals"]["readiness_certified"]==0,
          "UNEXPECTED_PREVIOUS_READINESS_CERTIFICATION")
    return n,a,s


def review(archive_bytes:bytes)->dict:
    """Recompute from raw archived bytes, no stubs or synthetic substitutes."""
    native_doc,action_doc,source_doc=_docs()
    _must(isinstance(archive_bytes,bytes) and bool(archive_bytes),"MISSING_OR_EMPTY_ARCHIVE")
    digest=sha(archive_bytes)
    _must(digest==native_doc["original_zip_sha256"],"ARCHIVED_NATIVE_ZIP_SHA_MISMATCH")
    import io
    try:
        z=ZipFile(io.BytesIO(archive_bytes))
        _must(z.testzip() is None,"ARCHIVED_NATIVE_ZIP_CRC_FAIL")
        names=set(z.namelist())
        profile_results=[]
        actual_profiles={x["spec"]:x for x in action_doc["profiles"]}
        seen_source_gates=set()
        for source_action in source_doc["candidate_actions"]:
            spec=source_action["spec"]
            _must(spec in native_doc["profiles"] and spec in actual_profiles,
                  "NATIVE_PROFILE_SCOPE_NOT_FOUND")
            manifest=native_doc["profiles"][spec]
            matched_action=actual_profiles[spec]
            _must(manifest["marker_decoded_sha256"]==matched_action["marker_decoded_sha256"],
                  "NATIVE_DECODED_HASH_DOC_CONFLICT")
            _must(manifest["marker_compressed_sha256"]==matched_action["marker_compressed_sha256"],
                  "NATIVE_COMPRESSED_HASH_DOC_CONFLICT")
            _must(manifest["archived_effective_apl_sha256"]==source_action["effective_apl_sha256"],
                  "PINNED_SOURCE_APL_HASH_SCOPE_CONFLICT")
            name="zrot-marker-proof/"+spec+".zrot_native_markers.txt.gz"
            _must(name in names,"NATIVE_PROFILE_MARKER_GZIP_MISSING")
            gz=z.read(name)
            _must(sha(gz)==manifest["marker_compressed_sha256"],
                  "NATIVE_MARKER_COMPRESSED_SHA_MISMATCH")
            try: raw=gzip.decompress(gz)
            except (EOFError, OSError) as exc:
                raise PinnedNativeEvidenceError("NATIVE_MARKER_GZIP_INVALID") from exc
            _must(sha(raw)==manifest["marker_decoded_sha256"],
                  "NATIVE_MARKER_DECODED_SHA_MISMATCH")
            _must(raw.endswith(b"\n"),"NATIVE_MARKER_FINAL_NEWLINE_MISSING")
            # This parser independently audits native epoch-byte projection and
            # distinguishes evaluated resources from prior source state.
            actual=native_eval_audit(raw,sha(raw))
            _must(actual["independent_epoch_raw_audit"]==
                  "PASS_EPOCH_NATIVE_SOURCE_BYTES_INDEPENDENT_RECALC",
                  "ACTUAL_NATIVE_EPOCH_INDEPENDENT_AUDIT_NOT_PASS")
            counts=Counter()
            for line in raw.splitlines():
                if RESOURCE_EVAL.encode() in line: counts["eval"]+=1
                if NATIVE_V2.encode() in line: counts["source_event"]+=1
                if IF_MARK.encode() in line and b"|BEGIN|" in line: counts["if_begin"]+=1
                if SELECT_MARK.encode() in line: counts["select_entry"]+=1
            _must(actual["native_evaluation_count"]==counts["eval"]==
                  matched_action["bare_resource_eval_count"],
                  "ACTUAL_NATIVE_EVAL_COUNT_CONFLICT")
            _must(counts["if_begin"]==matched_action["original_if_guard_begin_count"]==
                  manifest["native_if_guard_count"],"NATIVE_GUARD_COUNT_CONFLICT")
            _must(counts["source_event"]==matched_action["native_epoch_event_count"],
                  "NATIVE_SOURCE_EVENT_COUNT_CONFLICT")
            _must(counts["select_entry"]>0,"NATIVE_SELECTION_PRODUCER_UNOBSERVED")
            _must(sum(actual["counts"].values())==actual["native_evaluation_count"],
                  "NATIVE_EVAL_CLASSIFICATION_DENOMINATOR")
            _must(actual["certified_operand_values"]==0 and
                  actual["readiness"]=="UNKNOWN" and
                  actual["complete_producer_coverage"] is False and
                  actual["eval_used_as_strict_pre"] is False and
                  actual["gameplay_rule_promotion"] is False,
                  "UNAUTHORIZED_SOURCE_READINESS_CLAIM")
            # No source-specific readiness markers have been independently
            # mapped from the archive; do NOT attach native resource/current
            # values to spec-specific obligations or feed ST01 as READY.
            gate_ids=[gate["id"] for gate in
                      source_action.get("extra_source_obligations",[])]
            _must(bool(gate_ids) and all(g not in seen_source_gates for g in gate_ids),
                  "INVALID_SOURCE_GATE_SCOPE")
            seen_source_gates.update(gate_ids)
            profile_results.append({
                "profile":spec,
                "action_token_source_candidate":source_action["action"],
                "marker_decoded_sha256":sha(raw),
                "native_resource_evaluation_count":counts["eval"],
                "native_if_evaluation_count":counts["if_begin"],
                "source_epoch_event_count":counts["source_event"],
                "native_selection_entry_count":counts["select_entry"],
                "native_eval_vs_prior_source_counts":actual["counts"],
                "native_evaluation_inside_selection_n":actual["evaluations_inside_selection"],
                "source_epoch_independent_audit":actual["independent_epoch_raw_audit"],
                "source_gate_obligation_ids":sorted(gate_ids),
                "source_gate_readiness_state":{
                    gate:"UNKNOWN_NO_CERTIFIED_SPECIFIC_NATIVE_PRODUCER_BINDING"
                    for gate in sorted(gate_ids)
                },
                "ready_certified":0,"gameplay_promotion":False,
            })
    except (BadZipFile,KeyError) as exc:
        raise PinnedNativeEvidenceError("INVALID_OR_INCOMPLETE_PINNED_ARCHIVE") from exc
    _must(len(profile_results)==2,"UNEXPECTED_SCOPE_COUNT")
    return {
        "schema":"ZrotST05ActualArchivedNativeSourceProducerAuditV1",
        "status":"PASS_SOURCE_BYTE_REPLAY_NOT_READINESS",
        "actual_native_run_id":native_doc["original_native_run_id"],
        "archive_sha256":digest,
        "pinned_simc_upstream_commit":native_doc["upstream_simc_sha"],
        "profiles":profile_results,
        "native_resource_eval_total":sum(
            x["native_resource_evaluation_count"] for x in profile_results),
        "original_native_log_capture":"ACTUAL_PINNED_PUBLIC_PROFILE_MARKER_ARCHIVE",
        "source_producer_semantics":"PARTIAL_NATIVE_RESOURCE_AND_DIRECT_IF_MARKERS",
        "current_client_mechanic_verification":"NOT_RUN",
        "complete_resource_write_coverage":"NOT_VERIFIED",
        "source_specific_gate_producer_provenance":"UNKNOWN",
        "source_to_ST03_positive_gate_input":"FORBIDDEN_WITH_CURRENT_EVIDENCE",
        "readiness_certified":0,"user_rotation_rule_promotion":False,
        "wcl_blind_candidates_injected":0,
        "main_frozen_promotion":False,"seq578":"FAILED_QUARANTINED",
        "seq637":"UNKNOWN",
    }


def selftest(archive:bytes)->dict:
    proof=review(archive)
    try:
        mutated=bytearray(archive)
        mutated[len(mutated)//2]^=1
        review(bytes(mutated))
    except PinnedNativeEvidenceError as exc:
        _must(str(exc)=="ARCHIVED_NATIVE_ZIP_SHA_MISMATCH",
              "MUTATED_ARCHIVE_REJECTED_FOR_WRONG_REASON")
    else:
        raise AssertionError("MODIFIED_NATIVE_ZIP_NOT_REJECTED")
    return {**proof,"source_tamper_regression":"PASS_REJECT_TAMPERED_BYTES"}


if __name__=="__main__":
    args=argparse.ArgumentParser()
    args.add_argument("--archive",type=Path,required=True)
    args.add_argument("--self-test",action="store_true")
    params=args.parse_args()
    raw=params.archive.read_bytes()
    result=selftest(raw) if params.self_test else review(raw)
    print(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False))
