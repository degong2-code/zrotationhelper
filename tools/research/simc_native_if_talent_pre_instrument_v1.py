#!/usr/bin/env python3
"""Generic source-derived SimC talent PRE operand reporter (research only).

Build an inventory ONLY from official APL IF symbols. Insert passive, read-only
talent expression evaluation before the one original native IF evaluation,
using the exact player_t::create_expression("talent.*") source route.
Reuses the proven Rage/enemies and source-pointer reporters. Nothing is inferred
from native IF truth or chosen actions. No args = synthetic tests; no network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile, git_blob
from simc_native_if_expression_instrument_v1 import (
    PINNED_COMMIT, ACTION_CPP_BLOB, TARGET, BEFORE, AFTER, OLD as IF_OLD,
)
from simc_native_if_pre_operand_instrument_v1 import (
    instrument as instrument_original, NEW_LOG as OLD_PRE_FACT_LOG,
    OperandPatchError,
)

MARK = "ZROT_NATIVE_IF_TALENT_PRE_V1|"
SITE = "    const bool zrot_original_if_result = if_expr->success();"
TALENT_PATTERN = re.compile(
    r"talent\.[a-z][a-z_0-9]*(?:\.(?:enabled|disabled|rank))?\Z"
)
MAX_SYMBOLS = 32


class TalentPatchError(ValueError):
    pass


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def talent_inventory(ir: dict) -> list[str]:
    symbols = set()
    for rows in ir["action_lists"].values():
        for row in rows:
            expr = row["expression_fields"].get("if")
            if expr:
                symbols.update(
                    s for s in expr["symbols"] if s.startswith("talent.")
                )
    if not 1 <= len(symbols) <= MAX_SYMBOLS:
        raise TalentPatchError("EMPTY_OR_OVERSIZED_SOURCE_TALENT_INVENTORY")
    if any(not TALENT_PATTERN.fullmatch(s) for s in symbols):
        raise TalentPatchError("UNSUPPORTED_SOURCE_TALENT_EXPRESSION")
    return sorted(symbols)


def instrument(original: bytes, symbols: list[str], *, strict=True) -> bytes:
    if (symbols != sorted(set(symbols)) or
        not 1 <= len(symbols) <= MAX_SYMBOLS or
        any(not TALENT_PATTERN.fullmatch(s) for s in symbols)):
        raise TalentPatchError("TALENT_SYMBOL_MANIFEST_NOT_SOURCE_CANONICAL")
    text = instrument_original(original, strict=strict).decode("utf-8")
    if text.count(SITE) != 1 or text.count(OLD_PRE_FACT_LOG) != 1 or MARK in text:
        raise TalentPatchError("SOURCE_PRE_IF_PATCH_ANCHOR_CHANGED")
    reads = "\n".join(
        '    // Native talent expression is an actor constant, not the IF result.\n'
        '    const double zrot_pre_talent_' + str(i) +
        ' = player->create_expression( "' + symbol + '" )->eval();'
        for i, symbol in enumerate(symbols)
    )
    reports = "\n".join(
        '      sim->print_log( "' + MARK +
        '{}|{}|{}|{}|' + symbol + '|{:.17g}",\n'
        '        sim->current_time().total_millis(), zrot_source_list,\n'
        '        zrot_source_ordinal, name_str, zrot_pre_talent_' + str(i) +
        ' );'
        for i, symbol in enumerate(symbols)
    )
    updated = text.replace(SITE, reads + "\n" + SITE, 1)
    updated = updated.replace(OLD_PRE_FACT_LOG,
                              OLD_PRE_FACT_LOG + "\n" + reports, 1)
    region = updated.split(BEFORE, 1)[1].split(AFTER, 1)[0]
    if region.count("if_expr->success()") != 1:
        raise TalentPatchError("NATIVE_IF_EVALUATION_COUNT_MODIFIED")
    if updated.index(reads) > updated.index(SITE):
        raise TalentPatchError("TALENTS_NOT_READ_BEFORE_NATIVE_IF")
    if updated.count(MARK) != len(symbols):
        raise TalentPatchError("TALENT_FACT_REPORT_COUNT_MISMATCH")
    if updated.index(OLD_PRE_FACT_LOG) > updated.index(MARK):
        raise TalentPatchError("OLD_PRE_FACT_NOT_RETAINED")
    return updated.encode("utf-8")


def run(root: Path, profile: Path, expected_blob: str | None):
    root = root.resolve(strict=True)
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if commit != PINNED_COMMIT:
        raise TalentPatchError("OFFICIAL_SIMC_SOURCE_COMMIT_CHANGED")
    raw_profile = profile.read_bytes()
    if expected_blob and git_blob(raw_profile) != expected_blob:
        raise TalentPatchError("PINNED_APL_SOURCE_PROFILE_CHANGED")
    ir = parse_profile(raw_profile, require_source=False)
    inventory = talent_inventory(ir)
    original = (root / TARGET).read_bytes()
    if git_blob(original) != ACTION_CPP_BLOB:
        raise TalentPatchError("OFFICIAL_ACTION_CPP_BLOB_CHANGED")
    patched = instrument(original, inventory)
    (root / TARGET).write_bytes(patched)
    return {
        "schema": "ZrotNativeSourceDerivedTalentPreOperandPatchV1",
        "official_simc_commit": commit,
        "profile_source_git_blob_sha1": git_blob(raw_profile),
        "original_action_cpp_git_blob_sha1": ACTION_CPP_BLOB,
        "patched_action_cpp_sha256": sha(patched),
        "APL_IF_talent_inventory": inventory,
        "source_semantics": "player_t::create_expression(talent.*) actor constant",
        "talent_values_sampled_before_single_native_IF_evaluation": True,
        "Native_IF_outcome_used_as_operand": False,
        "native_ready_used_as_operand": False,
        "runtime_nonperturbation": "NOT_YET_VALIDATED",
        "WCL_API_calls": 0,
        "MAIN_promotion": False,
    }


def selftest():
    profile = parse_profile(
        b"actions=foo,if=talent.alpha&rage>=30\n"
        b"actions+=/bar,if=talent.beta.enabled|talent.alpha\n",
        require_source=False,
    )
    inventory = talent_inventory(profile)
    assert inventory == ["talent.alpha", "talent.beta.enabled"]
    example = (BEFORE + "  if ( !ready() ) return false;\n" +
               IF_OLD + "\n  return true;\n}\n" + AFTER +
               "  return true;\n}\n").encode()
    output = instrument(example, inventory, strict=False).decode()
    assert output.count("if_expr->success()") == 1
    assert output.count(MARK) == 2
    assert output.index('create_expression( "talent.alpha" )') < output.index(SITE)
    assert output.index("zrot_original_if_result =") < output.index(MARK)
    assert "ZROT_NATIVE_IF_FACT_V1" in output
    try:
        instrument(example, ["talent.not-valid"], strict=False)
    except TalentPatchError:
        pass
    else:
        raise AssertionError("ACCEPTED_UNSUPPORTED_SYMBOL")
    try:
        instrument(output.encode(), inventory, strict=False)
    except (TalentPatchError, OperandPatchError):
        pass
    else:
        raise AssertionError("ACCEPTED_DOUBLE_INSTRUMENT")
    try:
        talent_inventory(parse_profile(b"actions=foo,if=rage>30\n",
                                       require_source=False))
    except TalentPatchError:
        pass
    else:
        raise AssertionError("ACCEPTED_EMPTY_TALENT_LIST")
    return {"status": "PASS_OFFLINE_SYNTHETIC", "checks": 9,
            "real_native_simc": "NOT_RUN", "WCL_API_calls": 0,
            "claim_of_independent_IF_semantics": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root", type=Path)
    p.add_argument("--official-profile", type=Path)
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--receipt", type=Path)
    a = p.parse_args()
    if a.simc_root and a.official_profile:
        result = run(a.simc_root, a.official_profile,
                     a.expected_profile_git_blob)
    elif not a.simc_root and not a.official_profile:
        result = selftest()
    else:
        p.error("both --simc-root and --official-profile required")
    blob = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
            "\n").encode()
    if a.receipt:
        a.receipt.parent.mkdir(parents=True, exist_ok=True)
        with a.receipt.open("xb") as f:
            f.write(blob)
    else:
        print(blob.decode(), end="")


if __name__ == "__main__":
    main()
