#!/usr/bin/env python3
"""Source-locked generic buff PRE-IF fact capture, building on Native talent V1.

Read APL-if buff names from the pinned profile (never infer from chosen casts),
then evaluate actor buff expressions immediately before the one original
if_expr->success(). Existing Rage/enemies, talent and source-pointer records
are preserved. No automatic decisions or WoW/WCL interaction.
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
    PatchError,
)
from simc_native_if_talent_pre_instrument_v1 import (
    instrument as instrument_talent,
    talent_inventory, SITE, MARK as TALENT_MARK, TalentPatchError,
)
from simc_native_if_pre_operand_instrument_v1 import OperandPatchError

MARK = "ZROT_NATIVE_IF_BUFF_PRE_V1|"
BUFF_PATTERN = re.compile(
    r"buff\.[a-z][a-z_0-9]*\.(?:up|down|stack|remains)\Z"
)
BUFF_CPP = "engine/buff/buff.cpp"
BUFF_BLOB = "6e9b1d8bcf6facea53d0f6e7ac573dfcf52e0a96"
PLAYER_CPP = "engine/player/player.cpp"
PLAYER_BLOB = "88e03a01ca87ff66fd3902c9d6e047fe1a03ecb8"
MAX_SYMBOLS = 48


class BuffPatchError(ValueError):
    pass


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def buff_inventory(ir):
    found = set()
    for rows in ir["action_lists"].values():
        for row in rows:
            expr = row["expression_fields"].get("if")
            if expr:
                found.update(s for s in expr["symbols"] if s.startswith("buff."))
    if not 1 <= len(found) <= MAX_SYMBOLS:
        raise BuffPatchError("EMPTY_OR_OVERSIZED_SOURCE_BUFF_INVENTORY")
    if any(not BUFF_PATTERN.fullmatch(s) for s in found):
        raise BuffPatchError("UNSUPPORTED_SOURCE_BUFF_EXPRESSION")
    return sorted(found)


def verify_official_semantics(root):
    buffs = (root / BUFF_CPP).read_bytes()
    player = (root / PLAYER_CPP).read_bytes()
    if git_blob(buffs) != BUFF_BLOB or git_blob(player) != PLAYER_BLOB:
        raise BuffPatchError("OFFICIAL_BUFF_OR_PLAYER_CPP_BLOB_CHANGED")
    b = buffs.decode("utf-8")
    p = player.decode("utf-8")
    expected = (
        'else if ( type == "up" )',
        'return buff->check() > 0;',
        'else if ( type == "down" )',
        'return buff->check() <= 0;',
        'else if ( type == "stack" )',
        'return buff->check();',
        'else if ( type == "remains" )',
        'return buff->remains();',
    )
    if any(b.count(token) != 1 for token in expected):
        raise BuffPatchError("PINNED_BUFF_EXPRESSION_SEMANTICS_NOT_PROVEN")
    if ('buff_t::find_expressable( buff_list, splits[ 1 ], this )' not in p
        or 'buff_t::create_expression( splits[ 1 ], splits[ 2 ], *buff )' not in p):
        raise BuffPatchError("PINNED_PLAYER_BUFF_SOURCE_ROUTE_CHANGED")


def instrument(original, talents, buffs, *, strict=True):
    if (buffs != sorted(set(buffs)) or not 1 <= len(buffs) <= MAX_SYMBOLS or
        any(not BUFF_PATTERN.fullmatch(s) for s in buffs)):
        raise BuffPatchError("SOURCE_BUFF_MANIFEST_NOT_CANONICAL")
    text = instrument_talent(original, talents, strict=strict).decode("utf-8")
    if text.count(SITE) != 1 or MARK in text:
        raise BuffPatchError("NATIVE_IF_BUFF_SOURCE_SITE_CHANGED")
    lines = []
    for i, symbol in enumerate(buffs):
        lines.append(
            '    // Read the native buff expression, not the native IF result.\n'
            '    const double zrot_pre_buff_' + str(i) +
            ' = player->create_expression( "' + symbol + '" )->eval();'
        )
    reads = "\n".join(lines)
    prints = "\n".join(
        '      sim->print_log( "' + MARK +
        '{}|{}|{}|{}|' + symbol + '|{:.17g}",\n'
        '        sim->current_time().total_millis(), zrot_source_list,\n'
        '        zrot_source_ordinal, name_str, zrot_pre_buff_' + str(i) + ' );'
        for i, symbol in enumerate(buffs)
    )
    text = text.replace(SITE, reads + "\n" + SITE, 1)
    # Append source facts at the end of the existing log branch; marker must
    # remain after one original Native IF call but before ready ATTEMPT log.
    tail = '    if ( !zrot_original_if_result )\n      return false;'
    if text.count(tail) != 1:
        raise BuffPatchError("NATIVE_IF_FINAL_BRANCH_ANCHOR_CHANGED")
    text = text.replace(tail, prints + "\n" + tail, 1)
    body = text.split(BEFORE, 1)[1].split(AFTER, 1)[0]
    if body.count("if_expr->success()") != 1:
        raise BuffPatchError("ORIGINAL_IF_EVALUATION_COUNT_CHANGED")
    if (text.index(reads) >= text.index(SITE)
        or text.index(prints) <= text.index(SITE)
        or text.count(MARK) != len(buffs)
        or text.count(TALENT_MARK) != len(talents)):
        raise BuffPatchError("PRE_SOURCE_BUFFER_OR_REPORT_ORDER_INVALID")
    return text.encode("utf-8")


def run(root, profile, expected_profile_git_blob):
    root = root.resolve(strict=True)
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True).stdout.strip()
    if commit != PINNED_COMMIT:
        raise BuffPatchError("OFFICIAL_SIMC_COMMIT_CHANGED")
    verify_official_semantics(root)
    raw = profile.read_bytes()
    if not expected_profile_git_blob or git_blob(raw) != expected_profile_git_blob:
        raise BuffPatchError("OFFICIAL_SIMC_PROFILE_NOT_PINNED")
    ir = parse_profile(raw, require_source=False)
    talents, buffs = talent_inventory(ir), buff_inventory(ir)
    action_path = root / TARGET
    original = action_path.read_bytes()
    if git_blob(original) != ACTION_CPP_BLOB:
        raise BuffPatchError("ACTION_CPP_SOURCE_BLOB_CHANGED")
    patched = instrument(original, talents, buffs)
    action_path.write_bytes(patched)
    return {
        "schema": "ZrotNativeSourceDerivedBuffPreOperandPatchV1",
        "official_simc_commit": commit,
        "official_profile_git_blob": git_blob(raw),
        "source_buff_cpp_blob": BUFF_BLOB,
        "source_player_cpp_blob": PLAYER_BLOB,
        "source_action_cpp_blob": ACTION_CPP_BLOB,
        "patched_action_cpp_sha256": sha(patched),
        "APL_if_talent_inventory": talents,
        "APL_if_buff_inventory": buffs,
        "native_buff_source_mapping": {
            "up": "buff_t::check()>0", "down": "buff_t::check()<=0",
            "stack": "buff_t::check()", "remains": "buff_t::remains()",
        },
        "snapshot_before_original_single_IF": True,
        "Native_IF_boolean_as_source_fact": False,
        "native_ready_boolean_as_source_fact": False,
        "pristine_vs_reporter_actions": "NOT_YET_VALIDATED",
        "WCL_API_calls": 0, "MAIN_promotion": False,
    }


def selftest():
    profile = parse_profile(
        b"actions=foo,if=talent.alpha&buff.bar.up\n"
        b"actions+=/bar,if=buff.foo.remains<gcd|buff.bar.stack>0\n",
        require_source=False)
    talents, buffs = talent_inventory(profile), buff_inventory(profile)
    assert talents == ["talent.alpha"]
    assert buffs == ["buff.bar.stack", "buff.bar.up", "buff.foo.remains"]
    sample = (BEFORE + "  if ( !ready() ) return false;\n" +
              IF_OLD + "\n  return true;\n}\n" + AFTER +
              "  return true;\n}\n").encode()
    changed = instrument(sample, talents, buffs, strict=False).decode()
    assert changed.count("if_expr->success()") == 1
    assert changed.count(MARK) == 3
    assert changed.count(TALENT_MARK) == 1
    assert changed.index('create_expression( "buff.bar.up" )') < changed.index(SITE)
    assert changed.index("zrot_original_if_result =") < changed.index(MARK)
    assert "ZROT_NATIVE_IF_FACT_V1" in changed
    try:
        instrument(changed.encode(), talents, buffs, strict=False)
    except (PatchError, OperandPatchError, TalentPatchError, BuffPatchError):
        pass
    else:
        raise AssertionError("DOUBLE_INSTRUMENTATION_ACCEPTED")
    for invalid in (["buff.bad.expr"], ["buff.bar.up", "buff.bar.up"]):
        try:
            instrument(sample, talents, invalid, strict=False)
        except BuffPatchError:
            pass
        else:
            raise AssertionError("UNSUPPORTED_BUFF_MANIFEST_ACCEPTED")
    return {"status": "PASS_OFFLINE_SYNTHETIC", "checks": 10,
            "real_native_simc": "NOT_RUN", "WCL_API_calls": 0,
            "IF_truth_used_as_operand": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root", type=Path)
    p.add_argument("--official-profile", type=Path)
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--receipt", type=Path)
    args = p.parse_args()
    if args.simc_root and args.official_profile:
        result = run(args.simc_root, args.official_profile,
                     args.expected_profile_git_blob)
    elif not args.simc_root and not args.official_profile:
        result = selftest()
    else:
        p.error("--simc-root and --official-profile required together")
    content = (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        with args.receipt.open("xb") as f: f.write(content)
    else:
        print(content.decode(), end="")


if __name__ == "__main__":
    main()
