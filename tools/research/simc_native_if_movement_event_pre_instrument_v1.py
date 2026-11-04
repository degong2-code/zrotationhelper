#!/usr/bin/env python3
"""Passive, pinned SimC movement + simulated-event IF operand producer.

Reads *actual* current actor movement.distance and SimC event forecast
raid_event.movement.{in,distance} using their official expressions before
the original SINGLE IF evaluation. Does not confuse forecast with real
player movement, nor infer false/zero for a missing environmental event.
The recorder is source-generic, not a boss plan, and never supplies Native
ready or IF boolean as a Python AST operand.

No CLI parameters executes offline synthetic tests; real SimC requires
pinned upstream checkout/profile and original-vs-instrumented parity gate.
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
    PINNED_COMMIT, ACTION_CPP_BLOB, TARGET, BEFORE, AFTER,
    PatchError,
)
from simc_native_if_talent_pre_instrument_v1 import talent_inventory, SITE
from simc_native_if_buff_pre_instrument_v1 import buff_inventory
from simc_native_if_action_gcd_cd_pre_instrument_v1 import (
    instrument as instrument_action, source_inventory as action_inventory,
)

MARK = "ZROT_NATIVE_IF_MOVEMENT_EVENT_PRE_V1|"
PLAYER_CPP = "engine/player/player.cpp"
PLAYER_CPP_BLOB = "88e03a01ca87ff66fd3902c9d6e047fe1a03ecb8"
SIM_CPP = "engine/sim/sim.cpp"
SIM_CPP_BLOB = "ae5c258953787196e0aecad58814ff14d4cd2bed"
RAID_EVENT_CPP = "engine/sim/raid_event.cpp"
RAID_EVENT_CPP_BLOB = "544316e502df365277d6f4ac876f2e767ced6d4a"

# Generic SimC movement-state and scheduled-event expression families. We
# only admit event types and filters with verified source mechanics.
MOVEMENT_RE = re.compile(r"movement\.(?:distance|remains|speed)\Z")
EVENT_RE = re.compile(
    r"raid_event\.(?:movement|moving)\."
    r"(?:in|distance|distance_min|distance_max|up|remains|exists)\Z"
)
MAX_SYMBOLS = 32


class MovementPatchError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def inventory(ir: dict) -> list[str]:
    symbols = set()
    for rows in ir["action_lists"].values():
        for row in rows:
            expr = row["expression_fields"].get("if")
            if not expr:
                continue
            symbols.update(s for s in expr["symbols"]
                           if s.startswith("movement.") or
                           s.startswith("raid_event.movement.") or
                           s.startswith("raid_event.moving."))
    if not 1 <= len(symbols) <= MAX_SYMBOLS:
        raise MovementPatchError("SOURCE_MOVEMENT_INVENTORY_EMPTY_OR_OVERSIZED")
    if any(not (MOVEMENT_RE.fullmatch(s) or EVENT_RE.fullmatch(s))
           for s in symbols):
        raise MovementPatchError("UNSUPPORTED_SOURCE_MOVEMENT_EXPR")
    return sorted(symbols)


def official_source_contract(root: Path) -> dict:
    expected = (
        (PLAYER_CPP, PLAYER_CPP_BLOB),
        (SIM_CPP, SIM_CPP_BLOB),
        (RAID_EVENT_CPP, RAID_EVENT_CPP_BLOB),
    )
    sources = {}
    for name, blob in expected:
        raw = (root / name).read_bytes()
        if git_blob(raw) != blob:
            raise MovementPatchError("OFFICIAL_MOVEMENT_SOURCE_BLOB_CHANGED:" + name)
        sources[name] = raw.decode("utf-8")
    player = sources[PLAYER_CPP]
    sim = sources[SIM_CPP]
    event = sources[RAID_EVENT_CPP]
    # The PINNED source mechanics, not an assumed false movement flag.
    if not all(x in player for x in (
        'if ( splits[ 0 ] == "movement" )',
        'else if ( splits[ 1 ] == "distance" )',
        'return make_fn_expr( expression_str, [ this ] { return current.distance_to_move; } );',
    )):
        raise MovementPatchError("PLAYER_MOVEMENT_EXPRESSION_ROUTE_CHANGED")
    if not all(x in sim for x in (
        'util::str_compare_ci( splits[ 0 ], "raid_event" )',
        'raid_event_t::evaluate_raid_event_expression( this, type_or_name, filter, true, &is_constant );',
        'return std::make_unique<raid_event_expr_t>( this, type_or_name, filter );',
    )):
        raise MovementPatchError("SIM_EVENT_EXPRESSION_ROUTE_CHANGED")
    if not all(x in event for x in (
        'double raid_event_t::evaluate_raid_event_expression(',
        'if ( matching_events.empty() )',
        'if ( filter == "in" || filter == "cooldown" )',
        'return timespan_t::max().total_seconds();',
        'if ( filter == "distance" )',
        'return e->distance_max;',
    )):
        raise MovementPatchError("SIM_EVENT_NO_EVENT_OR_DISTANCE_SEMANTICS_CHANGED")
    return {
        "current_movement": "player_t::create_expression(movement.distance) reads current.distance_to_move",
        "future_event": "sim_t::create_expression(raid_event.movement.in/distance) delegates to raid_event_t expression",
        "no_matching_event_in": "SimC timespan_t::max() constant, not native movement",
        "no_matching_event_distance": "SimC constant zero, not evidence of real-world raid mechanics",
        "native_source_blobs": {
            PLAYER_CPP: PLAYER_CPP_BLOB,
            SIM_CPP: SIM_CPP_BLOB,
            RAID_EVENT_CPP: RAID_EVENT_CPP_BLOB,
        },
    }


def instrument(original: bytes, talents: list[str], buffs: list[str],
               actions: list[str], environments: list[str], *,
               strict: bool = True) -> bytes:
    if (environments != sorted(set(environments)) or not environments or
        len(environments) > MAX_SYMBOLS or any(
            not (MOVEMENT_RE.fullmatch(s) or EVENT_RE.fullmatch(s))
            for s in environments)):
        raise MovementPatchError("UNPINNED_OR_INVALID_ENVIRONMENT_SYMBOL_MANIFEST")
    previous = instrument_action(original, talents, buffs, actions,
                                 strict=strict).decode("utf-8")
    if previous.count(SITE) != 1 or MARK in previous:
        raise MovementPatchError("MOVEMENT_PRE_IF_SOURCE_PATCH_SITE_CHANGED")
    reads = []
    logs = []
    for i, symbol in enumerate(environments):
        path = "player" if MOVEMENT_RE.fullmatch(symbol) else "sim"
        reads.append(
            "    // Read Native expression BEFORE the one original IF success().\n"
            "    // Movement and simulated event forecast are distinct facts.\n"
            "    const double zrot_pre_environment_" + str(i) +
            ' = ' + path + '->create_expression( "' + symbol +
            '" )->eval();'
        )
        logs.append(
            '      sim->print_log( "' + MARK +
            '{}|{}|{}|{}|' + symbol + '|{:.17g}",\n'
            '        sim->current_time().total_millis(), zrot_source_list,\n'
            '        zrot_source_ordinal, name_str, zrot_pre_environment_' +
            str(i) + ' );'
        )
    pre = "\n".join(reads)
    lines = "\n".join(logs)
    amended = previous.replace(SITE, pre + "\n" + SITE, 1)
    log_scope_close = "    }\n    if ( !zrot_original_if_result )\n      return false;"
    if amended.count(log_scope_close) != 1:
        raise MovementPatchError("NATIVE_PRE_IF_LOG_SCOPE_CHANGED")
    amended = amended.replace(log_scope_close,
                              lines + "\n" + log_scope_close, 1)
    region = amended.split(BEFORE, 1)[1].split(AFTER, 1)[0]
    if (region.count("if_expr->success()") != 1 or
        amended.count(MARK) != len(environments) or
        amended.index(pre) >= amended.index(SITE) or
        amended.index(lines) <= amended.index(SITE)):
        raise MovementPatchError("NATIVE_PRE_IF_EVAL_COUNT_OR_ORDER_CHANGED")
    return amended.encode("utf-8")


def run(root: Path, profile: Path, expected_blob: str | None) -> dict:
    root = root.resolve(strict=True)
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if commit != PINNED_COMMIT:
        raise MovementPatchError("SIMC_OFFICIAL_SOURCE_COMMIT_CHANGED")
    official = official_source_contract(root)
    raw_profile = profile.read_bytes()
    if not expected_blob or git_blob(raw_profile) != expected_blob:
        raise MovementPatchError("OFFICIAL_APL_SOURCE_IDENTITY_CHANGED")
    ir = parse_profile(raw_profile, require_source=False)
    talents, buffs, actions, env = (
        talent_inventory(ir), buff_inventory(ir), action_inventory(ir),
        inventory(ir),
    )
    path = root / TARGET
    raw_action = path.read_bytes()
    if git_blob(raw_action) != ACTION_CPP_BLOB:
        raise MovementPatchError("ORIGINAL_ACTION_CPP_NOT_PRISTINE")
    modified = instrument(raw_action, talents, buffs, actions, env)
    path.write_bytes(modified)
    return {
        "schema": "ZrotNativeSimcMovementAndEventPrePatchV1",
        "scope_policy_id": "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
        "official_simc_commit": commit,
        "profile_git_blob": git_blob(raw_profile),
        "original_action_cpp_blob": ACTION_CPP_BLOB,
        "modified_action_cpp_sha256": sha(modified),
        "source_environment_symbols": env,
        "source_talent_symbols": talents,
        "source_buff_symbols": buffs,
        "source_action_scoped_symbols": actions,
        "source_environment_semantics": official,
        "native_IF_and_ready_not_AST_input": True,
        "one_original_if_evaluation": True,
        "native_nonperturbation": "NOT_YET_PROVEN",
        "future_event_is_not_realtime_game_observation": True,
        "WCL_API_calls": 0,
        "MAIN_promotion": False,
    }


def selftest():
    from simc_native_if_expression_instrument_v1 import OLD as IF_OLD
    ir = parse_profile(
        b"actions=x,if=talent.alpha&buff.beta.up&gcd<1.5&movement.distance>5\n"
        b"actions+=/y,if=raid_event.movement.in>45&raid_event.movement.distance>25&cooldown.foo.ready\n",
        require_source=False,
    )
    symbols = inventory(ir)
    assert symbols == [
        "movement.distance", "raid_event.movement.distance",
        "raid_event.movement.in"
    ]
    synthetic = (BEFORE + "  if ( !ready() ) return false;\n" +
                 IF_OLD + "\n  return true;\n}\n" + AFTER +
                 "  return true;\n}\n").encode()
    changed = instrument(
        synthetic, talent_inventory(ir), buff_inventory(ir),
        action_inventory(ir), symbols, strict=False).decode("utf-8")
    assert changed.count("if_expr->success()") == 1
    assert changed.count(MARK) == 3
    assert changed.count("ZROT_NATIVE_IF_ACTION_EXPR_PRE_V1|") == 2
    assert 'player->create_expression( "movement.distance" )->eval()' in changed
    assert 'sim->create_expression( "raid_event.movement.in" )->eval()' in changed
    assert changed.index('sim->create_expression( "raid_event.movement.in" )') < changed.index(SITE)
    assert changed.index(MARK) > changed.index(SITE)
    try:
        instrument(changed.encode(), talent_inventory(ir), buff_inventory(ir),
                   action_inventory(ir), symbols, strict=False)
    except ValueError:
        pass
    else:
        raise AssertionError("REPEATED_SOURCE_PROBE_ACCEPTED")
    malformed = parse_profile(
        b"actions=x,if=raid_event.movement.some_unsupported_field>1\n",
        require_source=False)
    try:
        inventory(malformed)
    except MovementPatchError:
        pass
    else:
        raise AssertionError("UNSUPPORTED_EVENT_FILTER_ACCEPTED")
    return {
        "status": "PASS_OFFLINE_SYNTHETIC",
        "checks": 12, "actual_native_simc": "NOT_RUN",
        "WCL_API_calls": 0, "simc_event_forecast_not_real_world_truth": True,
        "native_ready_used_as_AST_operand": False,
    }


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
        p.error("--simc-root and --official-profile required together")
    raw = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
           "\n").encode("utf-8")
    if a.receipt:
        a.receipt.parent.mkdir(parents=True, exist_ok=True)
        with a.receipt.open("xb") as f: f.write(raw)
    else:
        print(raw.decode(), end="")


if __name__ == "__main__":
    main()
