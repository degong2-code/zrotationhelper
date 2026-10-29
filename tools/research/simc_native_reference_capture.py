#!/usr/bin/env python3
"""Capture local SimulationCraft *native* action log and effective APL.

This is a reference acquisition producer, not a combat-log state parser and
not a SimC APL emulator. Only an actual completed local SimC invocation can
qualify as a native-reference capture; synthetic test receipts are distinct.

The log may contain character/gear identity. Keep artifacts LOCAL and PRIVATE.
No shell, no credential use, no network request or repository upload.
Official documentation: simulationcraft/simc Wiki/Output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from simc_apl_source_engine import (
    SourceContractError, _profile_fields, _text, _fingerprint,
    ingest_actions, sha
)


def _secure_capture_dir(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    if not out.is_dir():
        raise SourceContractError("REFERENCE_OUTPUT_NOT_DIRECTORY")
    for name in ("simc_native_log.txt","simc_effective_actions.simc",
                 "simc_reference_receipt.json"):
        if (out/name).exists():
            raise SourceContractError("REFERENCE_OUTPUT_ALREADY_EXISTS")


def _resolve_binary(binary: Path | None) -> Path:
    selected = str(binary) if binary is not None else (
        os.environ.get("SIMC_BIN") or shutil.which("simc") or shutil.which("simc.exe"))
    if not selected:
        raise SourceContractError("SIMC_EXECUTABLE_NOT_FOUND")
    path=Path(selected).expanduser().resolve(strict=True)
    if not path.is_file():
        raise SourceContractError("SIMC_BINARY_NOT_FILE")
    return path


def capture_reference(
    *, profile_file: Path, expected_spec: str, out_dir: Path,
    simc_executable: Path | None = None, timeout_seconds: int = 180,
    runner=None,
    synthetic_test: bool = False,
) -> dict[str, Any]:
    """Capture native log from exactly one actor; no actions are inferred.

    'runner' injection exists solely for offline synthetic regression.
    Such receipts can never be marked as an actual SimC run.
    """
    if runner is not None and not synthetic_test:
        raise SourceContractError("INJECTED_RUNNER_MUST_BE_SYNTHETIC")
    if timeout_seconds < 1 or timeout_seconds > 3600:
        raise SourceContractError("INVALID_REFERENCE_TIMEOUT")
    profile=profile_file.expanduser().resolve(strict=True)
    if not profile.is_file():
        raise SourceContractError("REFERENCE_PROFILE_NOT_FILE")
    raw=profile.read_bytes()
    fields=_profile_fields(_text(raw))
    if fields["spec"]!=expected_spec or fields["actor_count"]!=1:
        raise SourceContractError("REFERENCE_PROFILE_IDENTITY_MISMATCH")
    if fields["external_profile_dependencies_detected"]:
        raise SourceContractError("UNPINNED_PROFILE_DEPENDENCIES")
    executable=_resolve_binary(simc_executable)
    destination=out_dir.expanduser().resolve()
    _secure_capture_dir(destination)
    action_file=destination/"simc_effective_actions.simc"
    log_file=destination/"simc_native_log.txt"
    command=[
        str(executable),str(profile),
        "iterations=1","threads=1","calculate_scale_factors=0",
        "log=1","log_spell_id=1",
        "save_actions="+str(action_file),
        "output="+str(log_file),
    ]
    if runner is None:
        runner=subprocess.run
    try:
        result=runner(command,cwd=str(profile.parent),
                      capture_output=True,check=False,
                      timeout=timeout_seconds,shell=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise SourceContractError("SIMC_NATIVE_REFERENCE_EXECUTION_FAILED") from e
    if result.returncode!=0:
        # No stdout/stderr in exceptions; logs can contain private identity.
        raise SourceContractError("SIMC_NATIVE_REFERENCE_NONZERO_EXIT")
    if not action_file.is_file() or not action_file.stat().st_size:
        raise SourceContractError("SIMC_NATIVE_ACTION_EXPORT_MISSING")
    if not log_file.is_file() or not log_file.stat().st_size:
        raise SourceContractError("SIMC_NATIVE_LOG_MISSING")
    apl_bytes=action_file.read_bytes()
    # Parse and verify source's structural integrity without interpreting log.
    model=ingest_actions(
        apl_bytes,expected_spec=expected_spec,
        profile_sha256=sha(raw),profile_spec=expected_spec,
        simc_executable_sha256=_fingerprint(executable),
        input_contains_custom_apl=fields["custom_apl_in_profile"],
        profile_dependencies_verified=True)
    receipt={
        "schema":"ZrotSimcNativeReferenceCaptureV1",
        "status":"SYNTHETIC_CAPTURE_TEST" if synthetic_test else "SIMC_NATIVE_CAPTURED_UNPARSED",
        "source_kind":"LOCAL_SIMC_EXECUTABLE",
        "simc_executable_sha256":_fingerprint(executable),
        "profile_sha256":sha(raw),
        "effective_apl_sha256":sha(apl_bytes),
        "native_log_sha256":_fingerprint(log_file),
        "simc_spec":expected_spec,
        "action_list_count":model["action_list_count"],
        "apl_row_count":model["apl_row_count"],
        "outputs":[
            {"file":action_file.name,"sha256":sha(apl_bytes),
             "bytes":action_file.stat().st_size},
            {"file":log_file.name,"sha256":_fingerprint(log_file),
             "bytes":log_file.stat().st_size},
        ],
        "native_action_log_parsed":"NOT_RUN",
        "state_snapshot_reconstructed":"NOT_RUN",
        "precombat_variable_lifetime_verified":"NOT_RUN",
        "decision_rule_match_validated":"NOT_RUN",
        "wcl_api_replay":"NOT_RUN",
        "actionable_rotation":False,
        "main_authority_promotion":False,
        "log_contains_private_information_possible":True,
    }
    (destination/"simc_reference_receipt.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return receipt


def selftest():
    import tempfile
    from types import SimpleNamespace
    with tempfile.TemporaryDirectory(prefix="zrot_simc_reference_") as td:
        root=Path(td)
        binary=root/"synthetic_simc_binary"
        binary.write_bytes(b"placeholder; not executed")
        profile=root/"actor.simc"
        profile.write_text('shaman="Test"\nspec=enhancement\n'
                           'actions=stormstrike,if=active_enemies=1\n',
                           encoding="utf-8")
        output=root/"receipt"
        def fake_simc(command, **kwargs):
            assert kwargs["shell"] is False and kwargs["check"] is False
            assert "log=1" in command and "log_spell_id=1" in command
            action=Path(next(x.split("=",1)[1] for x in command
                             if x.startswith("save_actions=")))
            log=Path(next(x.split("=",1)[1] for x in command
                          if x.startswith("output=")))
            action.write_text(profile.read_text(encoding="utf-8"),encoding="utf-8")
            log.write_text("SYNTHETIC LOG; NOT A REAL SIMC RUN\n",encoding="utf-8")
            return SimpleNamespace(returncode=0)
        receipt=capture_reference(
            profile_file=profile,expected_spec="enhancement",
            out_dir=output,simc_executable=binary,
            runner=fake_simc,synthetic_test=True)
        assert receipt["status"]=="SYNTHETIC_CAPTURE_TEST"
        assert receipt["native_action_log_parsed"]=="NOT_RUN"
        assert receipt["apl_row_count"]==1
        assert receipt["actionable_rotation"] is False
        assert (output/"simc_reference_receipt.json").exists()
        try:
            capture_reference(
                profile_file=profile,expected_spec="enhancement",
                out_dir=output,simc_executable=binary,
                runner=fake_simc,synthetic_test=True)
        except SourceContractError as e:
            assert str(e)=="REFERENCE_OUTPUT_ALREADY_EXISTS"
        else:
            raise AssertionError("OVERWRITE_ACCEPTED")
        try:
            capture_reference(
                profile_file=profile,expected_spec="enhancement",
                out_dir=root/"bad",simc_executable=binary,
                runner=fake_simc,synthetic_test=False)
        except SourceContractError as e:
            assert str(e)=="INJECTED_RUNNER_MUST_BE_SYNTHETIC"
        else:
            raise AssertionError("FAKE_RUNNER_AS_REAL_ACCEPTED")
    print("SIMC_NATIVE_REFERENCE_CAPTURE_CONTRACT_SELF_TEST=PASS")


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path)
    p.add_argument("--spec")
    p.add_argument("--simc-bin",type=Path)
    p.add_argument("--out-dir",type=Path)
    p.add_argument("--timeout",type=int,default=180)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test:
        selftest()
        return 0
    if args.profile is None or not args.spec:
        p.error("--profile and --spec required")
    out=args.out_dir or (args.profile.parent/"zrot_simc_reference")
    receipt=capture_reference(
        profile_file=args.profile,expected_spec=args.spec,
        simc_executable=args.simc_bin,out_dir=out,timeout_seconds=args.timeout)
    print("SIMC_NATIVE_REFERENCE_CAPTURED_UNPARSED")
    print("ARTIFACT_DIR="+str(out.resolve()))
    print("RECEIPT="+str((out/"simc_reference_receipt.json").resolve()))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
