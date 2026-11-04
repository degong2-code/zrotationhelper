#!/usr/bin/env python3
"""Pinned source-PRE raw queue tolerance operand producer.

Observe unmodified SimC cooldown.ready, actor cooldown_tolerance_,
sim.default_cooldown_tolerance and existing native queueable() clock at
the SAME action selection attempt before original single action_ready().
The Python replay independently selects the tolerance and subtracts it
from the source ready clock. The native queueable() clock is comparator
ONLY and never an input to calculation. All underlying SimC timespan_t
clock values are exact integer milliseconds, not rounded floats.

The existing PRE guard source instrumentation and Native sequence
comparison still apply; no second original readiness call is allowed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from simc_apl_semantic_ir_v2 import git_blob, parse_profile
from simc_native_if_expression_instrument_v1 import PINNED_COMMIT, ACTION_CPP_BLOB
from simc_native_ready_guard_witness_instrument_v1 import (
    PLAYER_CPP_BLOB, ACTION_CPP, PLAYER_CPP,
)
from simc_native_cooldown_queue_clock_instrument_v1 import (
    patch_originals, verify_math_source, MARK as BASE_MARK,
)
from simc_native_if_talent_pre_instrument_v1 import talent_inventory
from simc_native_if_buff_pre_instrument_v1 import buff_inventory
from simc_native_if_action_gcd_cd_pre_instrument_v1 import source_inventory
from simc_native_if_movement_event_pre_instrument_v1 import inventory

MARK = "ZROT_NATIVE_CD_TOLERANCE_PRE_V1|"
SCHEMA = "ZrotNativeRawCooldownToleranceClockPreV1"
PLAYER_CPP_BLOB_PIN = "88e03a01ca87ff66fd3902c9d6e047fe1a03ecb8"
PLAYER_HPP_BLOB_PIN = "f2648bec55750fce281e52185966d0424961a5c6"
SIM_HPP_BLOB_PIN = "fb5632bb94e3285d197f3ed52ca3ae63ed3b5761"
TIMESPAN_HPP_BLOB_PIN = "7662db9bbb64c2ccc5906058ff310fff64726cd5"

class ToleranceProducerError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_tolerance_source(root: Path) -> dict:
    contract = verify_math_source(root)
    pin = {
        "engine/player/player.cpp": PLAYER_CPP_BLOB_PIN,
        "engine/player/player.hpp": PLAYER_HPP_BLOB_PIN,
        "engine/sim/sim.hpp": SIM_HPP_BLOB_PIN,
        "engine/util/timespan.hpp": TIMESPAN_HPP_BLOB_PIN,
    }
    src = {}
    for p, expected in pin.items():
        data = (root/p).read_bytes()
        if git_blob(data) != expected:
            raise ToleranceProducerError("OFFICIAL_TOLERANCE_SOURCE_DRIFT:"+p)
        src[p] = data.decode("utf-8")
    player = src["engine/player/player.cpp"]
    if ("timespan_t player_t::cooldown_tolerance() const" not in player or
        "return cooldown_tolerance_ < timespan_t::zero() ? sim -> default_cooldown_tolerance : cooldown_tolerance_;" not in player):
        raise ToleranceProducerError("SOURCE_ACTOR_TOLERANCE_SELECTION_CHANGED")
    player_header = src["engine/player/player.hpp"]
    sim_header = src["engine/sim/sim.hpp"]
    time_header = src["engine/util/timespan.hpp"]
    for pat, content in (
        ("timespan_t  cooldown_tolerance_;", player_header),
        ("timespan_t  default_cooldown_tolerance;",sim_header),
        ("constexpr time_t total_millis() const",time_header),
        ("return time;",time_header),
    ):
        if pat not in content:
            raise ToleranceProducerError("SOURCE_TOLERANCE_NUMERIC_FIELD_CHANGED:"+pat)
    return {
        **contract,
        "pinned_files":pin,
        "raw_clock_unit":"integer_milliseconds",
        "raw_tolerance_select":"actor_override_ms < 0 ? sim_default_ms : actor_override_ms",
        "source_queueable":"cooldown_ready_ms - selected_tolerance_ms",
        "source_is_ready":"ready_ms<=now_ms || (action_bound && player_bound && queueable_ms<=now_ms)",
    }


def extend_player(previous: bytes) -> bytes:
    text=previous.decode("utf-8")
    # The previous producer's C++ local source pointer, bound flags and
    # cooldown ready times all belong to this same logging block.
    close = (
        "        zrot_cd_action_bound, zrot_cd_player_bound, zrot_queue_ms );"
    )
    original = "    bool zrot_native_ready = a->action_ready();"
    if text.count(close)!=1 or text.count(original)!=1 or MARK in text:
        raise ToleranceProducerError("PREVIOUS_COOLDOWN_SCOPE_OR_ORIGINAL_CALL_NOT_UNIQUE")
    extra=(
        "\n      // Raw tolerance SOURCE INPUTS (not player->cooldown_tolerance()).\n"
        "      const auto zrot_tol_actor_raw = zrot_cd_player_bound ?\n"
        "        zrot_cd_clock->player->cooldown_tolerance_.total_millis() : 0;\n"
        "      const auto zrot_tol_sim_default = sim->default_cooldown_tolerance.total_millis();\n"
        '      sim->print_log( "' + MARK + '{}|{}|{}|{}|{}|{}",\n'
        "        sim->current_time().total_millis(), zrot_pre_owner,\n"
        "        zrot_pre_ordinal, a->name_str, zrot_tol_actor_raw,\n"
        "        zrot_tol_sim_default );"
    )
    out=text.replace(close,close+extra,1)
    if (out.count(MARK)!=1 or out.count(BASE_MARK)!=1 or
        out.index(BASE_MARK)>out.index(MARK) or
        out.index(MARK)>out.index(original) or
        out.count(original)!=1 or
        out.count("a->cooldown->is_ready()")!=1):
        raise ToleranceProducerError("ORIGINAL_PRE_READY_COUNT_OR_SCOPE_CHANGED")
    return out.encode()


def run(root:Path, profile:Path, expected_blob:str|None)->dict:
    root=root.resolve(strict=True)
    commit=subprocess.run(
        ["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    if commit!=PINNED_COMMIT:
        raise ToleranceProducerError("PINNED_UPSTREAM_COMMIT_CHANGED")
    source=verify_tolerance_source(root)
    raw=profile.read_bytes()
    if not expected_blob or git_blob(raw)!=expected_blob:
        raise ToleranceProducerError("PINNED_PROFILE_CHANGED")
    original_a,original_p=root/ACTION_CPP,root/PLAYER_CPP
    if (git_blob(original_a.read_bytes())!=ACTION_CPP_BLOB or
        git_blob(original_p.read_bytes())!=PLAYER_CPP_BLOB):
        raise ToleranceProducerError("ORIGINAL_CPP_SOURCES_NOT_PRISTINE")
    ir=parse_profile(raw,require_source=False)
    action,prior_player=patch_originals(
        original_a.read_bytes(),original_p.read_bytes(),
        talent_inventory(ir),buff_inventory(ir),
        source_inventory(ir),inventory(ir))
    player=extend_player(prior_player)
    original_a.write_bytes(action)
    original_p.write_bytes(player)
    return {
        "schema":SCHEMA,
        "policy":"ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
        "source_contract":source,
        "official_simc_commit":commit,
        "profile_blob":git_blob(raw),
        "instrumented_action_cpp_sha256":sha(action),
        "instrumented_player_cpp_sha256":sha(player),
        "added_native_ready_calls":0,
        "native_queueable_value_comparator_only":True,
        "source_raw_tolerance_read_pre_action":True,
        "nonperturbation":"NOT_YET_PROVEN",
        "WCL_API_calls":0,
        "MAIN_promoted":False,
    }


def selftest():
    from simc_native_select_trace_instrument_v1 import START,END
    from simc_native_ready_guard_witness_instrument_v1 import patched_player
    from simc_native_cooldown_queue_clock_instrument_v1 import extend_player as old
    synthetic=(
        START+"\n{\n"
        "  // Mark this action list as visited with the APL internal id\n"
        "    if ( a->action_ready() )\n"
        "          return real_a;\n"
        "        return a;\n"
        "  return nullptr;\n}\n"+END+"\n{}\n"
    ).encode()
    transformed=extend_player(old(patched_player(synthetic,strict=False)))
    source=transformed.decode()
    assert source.count(MARK)==1
    assert source.count(BASE_MARK)==1
    assert source.count("a->action_ready()")==1
    assert source.count("a->cooldown->is_ready()")==1
    assert source.count("cooldown_tolerance_.total_millis()")==1
    assert source.count("default_cooldown_tolerance.total_millis()")==1
    assert source.index(BASE_MARK)<source.index(MARK)<source.index("bool zrot_native_ready = a->action_ready();")
    assert source.index("zrot_cd_action_bound")<source.index(MARK)
    try:
        extend_player(transformed)
    except ToleranceProducerError:
        pass
    else:
        raise AssertionError("DOUBLE_PROBE_NOT_REJECTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":9,
            "native_simc_not_run":True,"WCL_API_calls":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root and a.official_profile:
        result=run(a.simc_root,a.official_profile,
                   a.expected_profile_git_blob)
    elif not a.simc_root and not a.official_profile:
        result=selftest()
    else:
        p.error("both --simc-root and --official-profile required")
    data=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as f:f.write(data)
    else:print(data.decode(),end="")


if __name__=="__main__":
    main()
