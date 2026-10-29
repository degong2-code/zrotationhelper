#!/usr/bin/env python3
"""Strict, pinned-format SimulationCraft *performed action* event extractor.

This is a local reference-input adapter, NOT a full log parser or APL
prediction verifier. Action_t::execute() logs
  "<actor> performs Action '<token>' (<spell_id>) (<resource>)"
and sim_ostream prepends simulation seconds to each line in upstream
simulationcraft/simc commit 710c2408bfd3ae4df71b8cd55cdf01f63fd6c926.

Only rows matching that exact format are reported. Other log messages,
scheduled-but-not-performed actions, and unknown formats are never inferred
as actual decisions. A performed event can be an autoattack/proc/background
action; its APL-origin and foreground status remain UNKNOWN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from decimal import Decimal, InvalidOperation

REFERENCE_SOURCE_COMMIT="710c2408bfd3ae4df71b8cd55cdf01f63fd6c926"
PERFORMS = re.compile(
    r"^\s*(?P<seconds>-?\d+(?:\.\d+)?)\s+"
    r"(?P<actor>.+?) performs Action '(?P<token>[^']+)' "
    r"\((?P<spell_id>\d+)\) \((?P<resource>[^)]*)\)\s*$"
)
SIMC_TIME = re.compile(r"^\s*-?\d+(?:\.\d+)?\s+")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_native_reference(source_directory: Path) -> dict:
    """Read native capture's files only after SHA/size pinning; no I/O outside dir."""
    folder=source_directory.resolve(strict=True)
    receipt_path=folder/"simc_reference_receipt.json"
    receipt=json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema")!="ZrotSimcNativeReferenceCaptureV1":
        raise ValueError("NATIVE_RECEIPT_SCHEMA_UNSUPPORTED")
    if receipt.get("status") not in (
        "SIMC_NATIVE_CAPTURED_UNPARSED","SYNTHETIC_CAPTURE_TEST"):
        raise ValueError("NATIVE_RECEIPT_STATUS_UNSUPPORTED")
    output_map={}
    for record in receipt.get("outputs",[]):
        if not isinstance(record,dict):
            raise ValueError("INVALID_REFERENCE_OUTPUT_RECORD")
        name=record.get("file")
        if name not in ("simc_native_log.txt","simc_effective_actions.simc") \
                or name in output_map:
            raise ValueError("UNEXPECTED_OR_DUPLICATE_REFERENCE_FILE")
        file=(folder/name)
        if file.is_symlink() or not file.is_file():
            raise ValueError("REFERENCE_OUTPUT_NOT_REGULAR_FILE")
        raw=file.read_bytes()
        if digest(raw)!=record.get("sha256") or len(raw)!=record.get("bytes"):
            raise ValueError("REFERENCE_OUTPUT_HASH_OR_SIZE_MISMATCH")
        output_map[name]=raw
    if len(output_map)!=2:
        raise ValueError("REFERENCE_OUTPUT_INCOMPLETE")
    if digest(output_map["simc_effective_actions.simc"])!=receipt.get(
        "effective_apl_sha256"):
        raise ValueError("REFERENCE_APL_IDENTITY_MISMATCH")
    if digest(output_map["simc_native_log.txt"])!=receipt.get(
        "native_log_sha256"):
        raise ValueError("REFERENCE_LOG_IDENTITY_MISMATCH")
    try:
        log=output_map["simc_native_log.txt"].decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError("NATIVE_LOG_UTF8_REQUIRED") from e
    rows=[]
    action_like_unparsed=0
    for line_no,line in enumerate(log.splitlines(),1):
        match=PERFORMS.fullmatch(line)
        if not match:
            if " performs Action " in line:
                action_like_unparsed+=1
            continue
        part=match.groupdict()
        try:
            t_ms=int(Decimal(part["seconds"])*1000)
        except (InvalidOperation,OverflowError) as e:
            raise ValueError("INVALID_NATIVE_LOG_TIMESTAMP") from e
        action_id=int(part["spell_id"])
        rows.append({
            "source_line":line_no,"timestamp_ms":t_ms,
            "actor_literal":part["actor"],
            "action_token":part["token"],"spell_id":action_id,
            "source_event_kind":"SIMC_PERFORMS_ACTION",
            "foreground_or_apl_selected":"UNKNOWN",
            "resource_snapshot_verified":"NOT_PARSED",
        })
    if action_like_unparsed:
        status="PARTIAL_UNRECOGNIZED_PERFORMS_FORMAT"
    elif not rows:
        status="BLOCKED_NO_RECOGNIZED_PERFORMED_EVENTS"
    else:
        status="NATIVE_PERFORMED_EVENT_SYNTAX_EXTRACTED"
    return {
        "schema":"ZrotSimcNativePerformedEventsResearchV1",
        "status":status,
        "capture_kind":receipt["status"],
        "native_log_sha256":receipt["native_log_sha256"],
        "effective_apl_sha256":receipt["effective_apl_sha256"],
        "profile_sha256":receipt["profile_sha256"],
        "simc_executable_sha256":receipt["simc_executable_sha256"],
        "format_reference_upstream_commit":REFERENCE_SOURCE_COMMIT,
        "native_executable_format_equivalence":"UNVERIFIED",
        "performed_event_count":len(rows),
        "unrecognized_performs_event_count":action_like_unparsed,
        "performed_events":rows,
        "foreground_decisions_identified":"NOT_RUN",
        "native_readiness_reconstructed":"NOT_RUN",
        "state_replay_comparison":"NOT_RUN",
        "wcl_comparison":"NOT_RUN",
        "gameplay_rule_promotion":False,
    }


def selftest():
    import tempfile
    with tempfile.TemporaryDirectory(prefix="zrot_simc_performs_") as td:
        root=Path(td)
        actions=b"spec=enhancement\nactions=stormstrike\n"
        logs=(
            b"-0.100 Player 'shaman' performs Action 'stormstrike' (17364) (100)\n"
            b"0.000 Player 'shaman' schedules execute for Action 'lava_lash' (60103)\n"
            b"0.100 Player 'shaman' performs Action 'lava_lash' (60103) (50)\n"
            b"0.200 Player 'pet' performs Action 'auto_attack' (0) (0)\n"
        )
        (root/"simc_effective_actions.simc").write_bytes(actions)
        (root/"simc_native_log.txt").write_bytes(logs)
        receipt={
            "schema":"ZrotSimcNativeReferenceCaptureV1",
            "status":"SYNTHETIC_CAPTURE_TEST",
            "effective_apl_sha256":digest(actions),
            "native_log_sha256":digest(logs),
            "profile_sha256":"a"*64,
            "simc_executable_sha256":"b"*64,
            "outputs":[
                {"file":"simc_effective_actions.simc",
                 "sha256":digest(actions),"bytes":len(actions)},
                {"file":"simc_native_log.txt",
                 "sha256":digest(logs),"bytes":len(logs)},
            ]}
        (root/"simc_reference_receipt.json").write_text(
            json.dumps(receipt),encoding="utf-8")
        result=extract_native_reference(root)
        assert result["performed_event_count"]==3
        assert result["status"]=="NATIVE_PERFORMED_EVENT_SYNTAX_EXTRACTED"
        assert [x["timestamp_ms"] for x in result["performed_events"]]==[-100,100,200]
        assert result["performed_events"][0]["spell_id"]==17364
        assert result["foreground_decisions_identified"]=="NOT_RUN"
        assert result["capture_kind"]=="SYNTHETIC_CAPTURE_TEST"
        (root/"simc_native_log.txt").write_bytes(logs+b"x")
        try:
            extract_native_reference(root)
        except ValueError as e:
            assert str(e)=="REFERENCE_OUTPUT_HASH_OR_SIZE_MISMATCH"
        else:
            raise AssertionError("CORRUPT_REFERENCE_ACCEPTED")
    print("SIMC_NATIVE_PERFORMED_EVENT_EXTRACTOR_SELF_TEST=PASS")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference-dir",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--self-test",action="store_true")
    opts=p.parse_args()
    if opts.self_test or opts.reference_dir is None:
        selftest()
        return
    result=extract_native_reference(opts.reference_dir)
    output=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
    if opts.out:
        opts.out.parent.mkdir(parents=True,exist_ok=True)
        opts.out.write_text(output,encoding="utf-8")
    else:
        print(output)


if __name__=="__main__":
    main()
