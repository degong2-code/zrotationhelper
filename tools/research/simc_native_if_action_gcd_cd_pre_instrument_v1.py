#!/usr/bin/env python3
"""Generic pinned Native PRE-IF actor GCD and cooldown expression recorder.

The SimC APL symbol 'gcd' is action_t::gcd() (action duration), NOT GCD
remaining; 'cooldown.X.ready' maps to cooldown_t::up(), NOT the queueable
cooldown_t::is_ready() check in action_t::ready(). This recorder adds only
source-driven observed operands to the existing source-pointer/resource/
talent/buff producer. Unknown cooldown identity must be logged UNKNOWN (-1),
never auto-created or implicitly read as ready. Native action-ready and IF
truth are never inputs to the independent expression evaluator.
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
    PINNED_COMMIT, ACTION_CPP_BLOB, TARGET, BEFORE, AFTER, PatchError,
)
from simc_native_if_talent_pre_instrument_v1 import (
    talent_inventory, SITE, MARK as TALENT_MARK,
)
from simc_native_if_buff_pre_instrument_v1 import (
    buff_inventory, instrument as instrument_buff,
    verify_official_semantics as verify_buff_source,
    MARK as BUFF_MARK,
)

MARK = "ZROT_NATIVE_IF_ACTION_EXPR_PRE_V1|"
SIMC_SOURCE_COMMIT = PINNED_COMMIT
ACTION_CPP = "engine/action/action.cpp"
PLAYER_CPP = "engine/player/player.cpp"
PLAYER_CPP_BLOB = "88e03a01ca87ff66fd3902c9d6e047fe1a03ecb8"
COOLDOWN_CPP = "engine/sim/cooldown.cpp"
COOLDOWN_CPP_BLOB = "b73f7963ffc7434ee1aa0853e8335b39fe4cf96d"
CD_RE = re.compile(r"cooldown\.([a-z][a-z_0-9]*)\.ready\Z")
MAX_SOURCE_SYMBOLS = 32


class ActionExprPatchError(ValueError):
    pass


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_inventory(ir):
    symbols = set()
    for rows in ir["action_lists"].values():
        for row in rows:
            if "if" not in row["expression_fields"]:
                continue
            for symbol in row["expression_fields"]["if"]["symbols"]:
                if symbol == "gcd" or symbol.startswith("cooldown."):
                    symbols.add(symbol)
    if not 1 <= len(symbols) <= MAX_SOURCE_SYMBOLS:
        raise ActionExprPatchError("ACTION_EXPR_SOURCE_INVENTORY_EMPTY_OR_TOO_LARGE")
    if any(s != "gcd" and not CD_RE.fullmatch(s) for s in symbols):
        raise ActionExprPatchError("UNSUPPORTED_APL_ACTION_EXPR")
    return sorted(symbols)


def verify_semantics(root):
    verify_buff_source(root)
    files = (
        (ACTION_CPP, ACTION_CPP_BLOB),
        (PLAYER_CPP, PLAYER_CPP_BLOB),
        (COOLDOWN_CPP, COOLDOWN_CPP_BLOB),
    )
    data = {}
    for file, blob in files:
        raw = (root / file).read_bytes()
        if git_blob(raw) != blob:
            raise ActionExprPatchError("OFFICIAL_SIMC_SOURCE_NOT_PINNED:" + file)
        data[file] = raw.decode("utf-8")
    action = data[ACTION_CPP]
    player = data[PLAYER_CPP]
    cooldown = data[COOLDOWN_CPP]
    required = {
        ACTION_CPP: (
            'if ( name == "gcd" )',
            'return make_mem_fn_expr( name, *this, &action_t::gcd );',
            'timespan_t action_t::gcd() const',
            'if ( !ready() )',
            'if ( if_expr && !if_expr->success() )',
        ),
        PLAYER_CPP: (
            'cooldown_t* player_t::find_cooldown( util::string_view name ) const',
            'return find_vector_member( cooldown_list, name );',
        ),
        COOLDOWN_CPP: (
            'else if ( name == "up" || name == "ready" )',
            'return make_mem_fn_expr( "cooldown_up", *this, &cooldown_t::up );',
            'bool cooldown_t::up() const',
            '{ return ready <= sim.current_time(); }',
            'bool cooldown_t::is_ready() const',
        ),
    }
    for p, anchors in required.items():
        for anchor in anchors:
            if data[p].count(anchor) != 1:
                raise ActionExprPatchError("SOURCE_SEMANTIC_ANCHOR_CHANGED:" + p)
    if 'if ( !cooldown->is_ready() )' not in action:
        raise ActionExprPatchError("NATIVE_READY_QUEUEABILITY_GUARD_CHANGED")
    if 'return queueable() <= sim.current_time();' not in cooldown:
        raise ActionExprPatchError("NATIVE_COOLDOWN_QUEUE_TOLERANCE_CHANGED")
    return {
        "gcd_source": "action_t::create_expression(gcd)->action_t::gcd()",
        "cooldown_expr_source": "cooldown_t::create_expression(ready)->cooldown_t::up()",
        "native_ready_source": "action_t::ready()->cooldown_t::is_ready()",
        "ready_is_not_cooldown_up": True,
        "gcd_is_not_gcd_remaining": True,
    }


def instrument(original, talents, buffs, action_symbols, *, strict=True):
    if (action_symbols != sorted(set(action_symbols))
        or not 1 <= len(action_symbols) <= MAX_SOURCE_SYMBOLS
        or any(s != "gcd" and not CD_RE.fullmatch(s)
               for s in action_symbols)):
        raise ActionExprPatchError("UNPINNED_ACTION_SYMBOL_INVENTORY")
    source = instrument_buff(original, talents, buffs, strict=strict).decode("utf-8")
    if source.count(SITE) != 1 or MARK in source:
        raise ActionExprPatchError("NATIVE_ACTION_PRE_IF_SITE_CHANGED")
    reads = []
    logs = []
    for i, symbol in enumerate(action_symbols):
        if symbol == "gcd":
            reads.append(
                "    // Exact action-context GCD duration, NOT remaining global cooldown.\n"
                "    const double zrot_pre_action_expr_" + str(i) +
                " = gcd().total_seconds();"
            )
            fmt_spec = "{:.17g}"
        else:
            match = CD_RE.fullmatch(symbol)
            name = match.group(1)
            reads.append(
                "    // Read existing cooldown only. -1 explicitly means UNKNOWN;\n"
                "    // never call get_cooldown() which can mutate actor state.\n"
                "    const auto* zrot_source_cd_" + str(i) +
                ' = player->find_cooldown( "' + name + '" );\n'
                "    const int zrot_pre_action_expr_" + str(i) +
                " = zrot_source_cd_" + str(i) +
                " ? ( zrot_source_cd_" + str(i) +
                "->up() ? 1 : 0 ) : -1;"
            )
            fmt_spec = "{}"
        logs.append(
            '      sim->print_log( "' + MARK + '{}|{}|{}|{}|' +
            symbol + "|" + fmt_spec + '",\n'
            "        sim->current_time().total_millis(), zrot_source_list,\n"
            "        zrot_source_ordinal, name_str, zrot_pre_action_expr_" + str(i) +
            " );"
        )
    reads_block = "\n".join(reads)
    log_block = "\n".join(logs)
    updated = source.replace(SITE, reads_block + "\n" + SITE, 1)
    tail = "    }\n    if ( !zrot_original_if_result )\n      return false;"
    if updated.count(tail) != 1:
        raise ActionExprPatchError("ORIGINAL_LOG_SCOPE_ANCHOR_CHANGED")
    updated = updated.replace(tail, log_block + "\n" + tail, 1)
    region = updated.split(BEFORE, 1)[1].split(AFTER, 1)[0]
    if (region.count("if_expr->success()") != 1 or
        updated.count(MARK) != len(action_symbols) or
        updated.count(TALENT_MARK) != len(talents) or
        updated.count(BUFF_MARK) != len(buffs) or
        updated.index(reads_block) >= updated.index(SITE) or
        updated.index(log_block) <= updated.index(SITE)):
        raise ActionExprPatchError("PRE_IF_SINGLE_EVALUATION_OR_LOG_ORDER_CHANGED")
    return updated.encode("utf-8")


def run(root, profile, expected_profile_git_blob):
    root = root.resolve(strict=True)
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, check=True, text=True,
    ).stdout.strip()
    if commit != SIMC_SOURCE_COMMIT:
        raise ActionExprPatchError("OFFICIAL_SIMC_COMMIT_MISMATCH")
    semantics = verify_semantics(root)
    raw = profile.read_bytes()
    if not expected_profile_git_blob or git_blob(raw) != expected_profile_git_blob:
        raise ActionExprPatchError("OFFICIAL_SOURCE_PROFILE_BLOB_MISMATCH")
    ir = parse_profile(raw, require_source=False)
    talents, buffs, actions = talent_inventory(ir), buff_inventory(ir), source_inventory(ir)
    path = root / TARGET
    original = path.read_bytes()
    if git_blob(original) != ACTION_CPP_BLOB:
        raise ActionExprPatchError("ORIGINAL_ACTION_CPP_NOT_PRISTINE")
    patched = instrument(original, talents, buffs, actions)
    path.write_bytes(patched)
    return {
        "schema": "ZrotNativeActionScopedGcdAndCooldownPreProducerV1",
        "official_simc_commit": commit,
        "profile_git_blob": git_blob(raw),
        "original_action_cpp_git_blob": ACTION_CPP_BLOB,
        "original_cooldown_cpp_git_blob": COOLDOWN_CPP_BLOB,
        "original_player_cpp_git_blob": PLAYER_CPP_BLOB,
        "output_source_sha256": sha(patched),
        "APL_if_talent_inventory": talents,
        "APL_if_buff_inventory": buffs,
        "APL_if_action_expr_inventory": actions,
        "semantics": semantics,
        "native_IF_result_only_verification": True,
        "native_ready_used_as_AST_operand": False,
        "unknown_cooldown_identity": "SENTINEL_MINUS_ONE_NOT_ZERO",
        "single_native_if_evaluation": True,
        "native_nonperturbation": "NOT_YET_VERIFIED",
        "WCL_API_calls": 0, "MAIN_promotion": False,
    }


def selftest():
    from simc_native_if_expression_instrument_v1 import OLD as IF_OLD
    from simc_apl_semantic_ir_v2 import parse_profile
    synthetic = parse_profile(
        b"actions=x,if=talent.alpha&buff.beta.up&gcd<1.5\n"
        b"actions+=/y,if=cooldown.bladestorm.ready&rage>10\n",
        require_source=False,
    )
    talents, buffs, scoped = (
        talent_inventory(synthetic), buff_inventory(synthetic),
        source_inventory(synthetic),
    )
    assert scoped == ["cooldown.bladestorm.ready", "gcd"]
    example = (BEFORE + "  if ( !ready() ) return false;\n" +
               IF_OLD + "\n  return true;\n}\n" + AFTER +
               "  return true;\n}\n").encode()
    output = instrument(example, talents, buffs, scoped, strict=False).decode()
    assert output.count("if_expr->success()") == 1
    assert output.count(MARK) == 2
    assert output.count(BUFF_MARK) == 1 and output.count(TALENT_MARK) == 1
    assert output.index("gcd().total_seconds()") < output.index(SITE)
    assert output.index('find_cooldown( "bladestorm" )') < output.index(SITE)
    assert " : -1;" in output and "->up() ? 1 : 0" in output
    assert output.index(MARK) > output.index(SITE)
    for invalid in (["gcd", "gcd"], ["cooldown.foo.remains"], ["cooldown.foo.ready", "gcd"]):
        if invalid == ["cooldown.foo.ready", "gcd"]:
            continue
        try:
            instrument(example, talents, buffs, invalid, strict=False)
        except ActionExprPatchError:
            pass
        else:
            raise AssertionError("UNSAFE_ACTION_EXPR_SOURCE_ACCEPTED")
    try:
        instrument(output.encode(), talents, buffs, scoped, strict=False)
    except (ActionExprPatchError, PatchError, Exception):
        pass
    else:
        raise AssertionError("DOUBLE_INSTRUMENTED_NATIVE_SOURCE_ACCEPTED")
    return {
        "status": "PASS_OFFLINE_SYNTHETIC", "checks": 10,
        "actual_native_compiled": False, "WCL_API_calls": 0,
        "full_ready_parity": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root", type=Path)
    p.add_argument("--official-profile", type=Path)
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--receipt", type=Path)
    a = p.parse_args()
    if a.simc_root and a.official_profile:
        data = run(a.simc_root, a.official_profile,
                   a.expected_profile_git_blob)
    elif not a.simc_root and not a.official_profile:
        data = selftest()
    else:
        p.error("both --simc-root and --official-profile required")
    raw = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if a.receipt:
        a.receipt.parent.mkdir(parents=True, exist_ok=True)
        with a.receipt.open("xb") as f:
            f.write(raw)
    else:
        print(raw.decode(), end="")


if __name__ == "__main__":
    main()
