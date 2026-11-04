#!/usr/bin/env python3
"""Source-pinned passive Native cooldown queue clock producer.

The previous bounded guard witness read native cooldown_t::is_ready().
This successor reads the raw cooldown.ready clock, current sim clock,
action/player binding, and queueable() threshold BEFORE the existing
single original action_ready() call. It never calls cooldown::is_ready()
a second time and never equates APL cooldown.X.ready (up) with queueable.
In replay, Native is_ready result is only a comparator after independent
Python time comparisons. The base readiness path and all unknowns remain.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile, git_blob
from simc_native_if_expression_instrument_v1 import PINNED_COMMIT, ACTION_CPP_BLOB
from simc_native_ready_guard_witness_instrument_v1 import (
    GuardPatchError, verify_source, patched_action, patched_player,
    PLAYER_CPP_BLOB, ACTION_CPP, PLAYER_CPP,
)
from simc_native_if_talent_pre_instrument_v1 import talent_inventory
from simc_native_if_buff_pre_instrument_v1 import buff_inventory
from simc_native_if_action_gcd_cd_pre_instrument_v1 import source_inventory
from simc_native_if_movement_event_pre_instrument_v1 import inventory

SCHEMA = "ZrotNativeRawCooldownQueueClockPreV1"
MARK = "ZROT_NATIVE_CD_QUEUE_CLOCK_PRE_V1|"
CD_CPP = "engine/sim/cooldown.cpp"
CD_BLOB = "b73f7963ffc7434ee1aa0853e8335b39fe4cf96d"
CD_HPP = "engine/sim/cooldown.hpp"
CD_HPP_BLOB = "d031d96592b635727f8c9c2b33b6d24b72190e89"


class QueueClockPatchError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_math_source(root: Path) -> dict:
    base = verify_source(root)
    cpp = (root / CD_CPP).read_bytes()
    hdr = (root / CD_HPP).read_bytes()
    if git_blob(cpp) != CD_BLOB or git_blob(hdr) != CD_HPP_BLOB:
        raise QueueClockPatchError("OFFICIAL_COOLDOWN_QUEUE_SOURCE_ID_CHANGED")
    src = cpp.decode("utf-8")
    anchors = (
        "timespan_t cooldown_t::queueable() const",
        "return ready - player->cooldown_tolerance();",
        "bool cooldown_t::is_ready() const",
        "if (up())",
        "if (!action || !player)",
        "return queueable() <= sim.current_time();",
        "bool cooldown_t::up() const",
        "{ return ready <= sim.current_time(); }",
    )
    for anchor in anchors:
        if src.count(anchor) != 1:
            raise QueueClockPatchError("PINNED_COOLDOWN_ARITHMETIC_CHANGED:" + anchor)
    return {
        **base,
        "queueable_source": "ready - player->cooldown_tolerance()",
        "is_ready_source": "up() OR (action_bound AND player_bound AND queueable() <= now)",
        "numeric_raw_fields": [
            "actual_current_ms", "cooldown_ready_ms",
            "has_bound_action", "has_bound_player",
            "cooldown_queueable_ms_if_bound",
        ],
        "queueable_is_distinct_from_APL_cooldown_ready_up": True,
    }


def extend_player(instrumented: bytes) -> bytes:
    src = instrumented.decode("utf-8")
    # Source-pointer variables are LOCAL to the previous guard logging
    # block. Insert within that block AFTER its complete guard print, not
    # directly before the call outside its scope (historical CI compile FAIL).
    ready_anchor = "    bool zrot_native_ready = a->action_ready();"
    guard_print_end = (
        "        zrot_moving, zrot_usable_move, zrot_cost_ok );"
    )
    if (src.count(ready_anchor) != 1 or
        src.count(guard_print_end) != 1 or MARK in src):
        raise QueueClockPatchError("ORIGINAL_SOURCE_SCOPED_GUARD_LOG_NOT_UNIQUE")
    additional = (
        "\n      // Raw source timestamps, never second is_ready() call.\n"
        "      // The existing source owner/ordinal remain in this C++ scope.\n"
        "      const auto* zrot_cd_clock = a->cooldown;\n"
        "      const int zrot_cd_action_bound = zrot_cd_clock && zrot_cd_clock->action ? 1 : 0;\n"
        "      const int zrot_cd_player_bound = zrot_cd_clock && zrot_cd_clock->player ? 1 : 0;\n"
        "      const auto zrot_cd_ready_ms = zrot_cd_clock ? zrot_cd_clock->ready.total_millis() : 0;\n"
        "      const auto zrot_queue_ms = ( zrot_cd_action_bound && zrot_cd_player_bound ) ?\n"
        "        zrot_cd_clock->queueable().total_millis() : 0;\n"
        '      sim->print_log( "' + MARK + '{}|{}|{}|{}|{}|{}|{}|{}",\n'
        "        sim->current_time().total_millis(), zrot_pre_owner,\n"
        "        zrot_pre_ordinal, a->name_str, zrot_cd_ready_ms,\n"
        "        zrot_cd_action_bound, zrot_cd_player_bound, zrot_queue_ms );"
    )
    out = src.replace(guard_print_end, guard_print_end + additional, 1)
    if (out.count(MARK) != 1 or out.count(ready_anchor) != 1 or
        out.count("a->cooldown->is_ready()") != 1 or
        out.index(guard_print_end) >= out.index(MARK) or
        out.index(MARK) >= out.index(ready_anchor)):
        raise QueueClockPatchError("QUEUE_CLOCK_SCOPED_PRE_ORIGINAL_CALL_CHANGED")
    return out.encode("utf-8")


def patch_originals(original_action: bytes, original_player: bytes,
                    talents: list[str], buffs: list[str], actions: list[str],
                    environments: list[str]) -> tuple[bytes, bytes]:
    action = patched_action(
        original_action, talents, buffs, actions, environments)
    player = extend_player(patched_player(original_player))
    return action, player


def run(root: Path, profile: Path, profile_blob: str) -> dict:
    root = root.resolve(strict=True)
    sha_upstream = subprocess.run(
        ["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True,
    ).stdout.strip()
    if sha_upstream != PINNED_COMMIT:
        raise QueueClockPatchError("OFFICIAL_SIMC_COMMIT_CHANGED")
    semantic = verify_math_source(root)
    original = profile.read_bytes()
    if not profile_blob or git_blob(original) != profile_blob:
        raise QueueClockPatchError("OFFICIAL_APL_PROFILE_CHANGED")
    ir = parse_profile(original, require_source=False)
    a, p = root / ACTION_CPP, root / PLAYER_CPP
    if (git_blob(a.read_bytes()) != ACTION_CPP_BLOB or
        git_blob(p.read_bytes()) != PLAYER_CPP_BLOB):
        raise QueueClockPatchError("NATIVE_SOURCE_NO_LONGER_PRISTINE")
    patched_a, patched_p = patch_originals(
        a.read_bytes(), p.read_bytes(),
        talent_inventory(ir), buff_inventory(ir),
        source_inventory(ir), inventory(ir))
    a.write_bytes(patched_a)
    p.write_bytes(patched_p)
    return {
        "schema": SCHEMA,
        "simc_upstream": sha_upstream,
        "official_profile_git_blob": profile_blob,
        "modified_action_cpp_sha256": sha(patched_a),
        "modified_player_cpp_sha256": sha(patched_p),
        "source_math_contract": semantic,
        "original_native_action_ready_calls": 1,
        "new_cooldown_is_ready_calls": 0,
        "native_readiness_as_independent_oracle": False,
        "native_nonperturbation": "NOT_YET_VERIFIED",
        "WCL_API_calls": 0,
        "MAIN_promoted": False,
    }


def selftest() -> dict:
    from simc_native_select_trace_instrument_v1 import START, END
    from simc_native_ready_guard_witness_instrument_v1 import patched_player
    raw = (
        START + "\n{\n"
        "  // Mark this action list as visited with the APL internal id\n"
        "    if ( a->action_ready() )\n"
        "          return real_a;\n"
        "        return a;\n"
        "  return nullptr;\n}\n" + END + "\n{}\n"
    ).encode()
    modified = extend_player(patched_player(raw, strict=False)).decode()
    assert modified.count(MARK) == 1
    assert modified.count("a->cooldown->is_ready()") == 1
    assert modified.count("a->action_ready()") == 1
    assert modified.index(MARK) < modified.index(
        "bool zrot_native_ready = a->action_ready();")
    assert modified.count("zrot_cd_clock->queueable()") == 1
    assert "zrot_cd_player_bound" in modified
    assert "zrot_cd_ready_ms" in modified
    try:
        extend_player(modified.encode())
    except QueueClockPatchError:
        pass
    else:
        raise AssertionError("DOUBLE_CLOCK_PRODUCER_ACCEPTED")
    return {
        "status":"PASS_OFFLINE_SYNTHETIC",
        "checks":8, "real_native_executed":False,
        "independent_full_readiness_proven":False,"WCL_API_calls":0,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root and a.official_profile:
        result=run(a.simc_root,a.official_profile,a.expected_profile_git_blob)
    elif not a.simc_root and not a.official_profile:
        result=selftest()
    else:
        p.error("both official simc root and profile are required")
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as out:out.write(raw)
    else:print(raw.decode(),end="")


if __name__=="__main__":
    main()
