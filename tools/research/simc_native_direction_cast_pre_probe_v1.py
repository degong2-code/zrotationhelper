#!/usr/bin/env python3
"""Passive original-SimC source PRE direction/cast operand probe.

Adds ONE logging statement to the already instrumented original
player_t::select_action() PRE block, before the original action_ready()
call. It reads *fields only*. No additional action ready, usable_moving,
execute_time, gcd, directionality, RNG, target or cast method invocation.

This is SimC ORIGINAL METHOD PRE, not WCL strictly-earlier PRE. Original
source identity and deterministic unmodified-vs-instrumented action
sequence must be checked by the caller. A source predicate is not a
positive virtual-route closure or a dummy-practice mistake verdict.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess

from simc_apl_semantic_ir_v2 import git_blob
from simc_native_ready_guard_witness_replay_v1 import read_guard
from simc_native_postguard_source_replay_v1 import parse_cast
from simc_native_if_pre_operand_replay_v1 import exact_key

SCHEMA = "ZrotSourcePinnedOriginalDirectionCastPREProbeV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
PIN = "b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
PROFILE_BLOB = "3225992ed5b754ad5d61e8b785d9d859f1eed1be"
MARK = "ZROT_SOURCE_DIR_CAST_PRE_V1|"
PLAYER = "engine/player/player.cpp"
ORIGINAL_BLOBS = {
    "engine/action/action.cpp": "399ecd9453b3f30bfc2ebf2b3ffd8f56cce8f8d4",
    "engine/action/action.hpp": "19f1e8d31d6b7ea31c828e519735fafe83b8735d",
    "engine/player/player.cpp": "88e03a01ca87ff66fd3902c9d6e047fe1a03ecb8",
    "engine/player/player.hpp": "f2648bec55750fce281e52185966d0424961a5c6",
    "engine/sc_enums.hpp": "5540996e68990092ef4f7552549ba03b38871a56",
}
# These are SimC movement_direction_type enum values at the pinned commit.
NONE, OMNI, TOWARDS, AWAY, RANDOM = 0, 1, 2, 3, 4
POST_CAST_ANCHOR = "        a->player->executing == a ? 1 : 0 );"
ORIGINAL_READY_CALL = "    bool zrot_native_ready = a->action_ready();"


class SourceProbeError(ValueError):
    pass


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def verify_pristine_source(root: Path) -> dict:
    git = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True).stdout.strip()
    if git != PIN:
        raise SourceProbeError("PINNED_SIMC_REVISION_MISMATCH")
    verified = {}
    for rel, expected in ORIGINAL_BLOBS.items():
        raw = subprocess.run(
            ["git", "-C", str(root), "show", "HEAD:" + rel],
            check=True, capture_output=True).stdout
        if git_blob(raw) != expected:
            raise SourceProbeError("PINNED_SOURCE_GIT_BLOB_MISMATCH:" + rel)
        verified[rel] = expected
        if rel == "engine/action/action.cpp":
            a = raw.decode()
            for witness in (
                "if ( player->is_moving() && !usable_moving() )",
                "if ( usable_while_casting )",
                "player->gcd_ready > sim->current_time()",
                "bool action_t::has_movement_directionality() const",
                "movement_directionality == movement_direction_type::NONE ||",
                "movement_directionality == movement_direction_type::OMNI",
                "movement_direction_type m = player->movement_direction();",
            ):
                if witness not in a:
                    raise SourceProbeError("ACTION_SOURCE_SEMANTICS_CHANGED:" + witness)
        if rel == "engine/player/player.hpp":
            if (b"return current.movement_direction;" not in raw):
                raise SourceProbeError("PLAYER_DIRECTIONALITY_SOURCE_CHANGED")
        if rel == "engine/player/player.cpp":
            if b"return buffs.movement && buffs.movement -> check();" not in raw:
                raise SourceProbeError("IS_MOVING_SOURCE_CHANGED")
        if rel == "engine/sc_enums.hpp":
            enum = raw.decode().split("enum class movement_direction_type : int", 1)
            if len(enum) != 2:
                raise SourceProbeError("DIRECTION_ENUM_MISSING")
            body = enum[1].split("};", 1)[0]
            positions = [body.find(name + ",") for name in
                         ("NONE", "OMNI", "TOWARDS", "AWAY", "RANDOM")]
            if any(x < 0 for x in positions) or positions != sorted(positions):
                raise SourceProbeError("DIRECTION_ENUM_ORDER_CHANGED")
    return {"pinned_revision": PIN, "original_blobs": verified,
            "source_method_dispatch_still_unproven": True}


def extend_player(raw: bytes) -> bytes:
    text = raw.decode()
    if (text.count(POST_CAST_ANCHOR) != 1 or
        text.count(ORIGINAL_READY_CALL) != 1 or
        text.count("ZROT_NATIVE_POST_CAST_PRE_V1|") != 1 or
        MARK in text or
        text.index("ZROT_NATIVE_POST_CAST_PRE_V1|") >
        text.index(POST_CAST_ANCHOR) or
        text.index(POST_CAST_ANCHOR) > text.index(ORIGINAL_READY_CALL)):
        raise SourceProbeError("EXISTING_POST_CAST_SOURCE_PRE_CHAIN_NOT_UNIQUE")
    # All properties below are direct field reads. Do not call original
    # virtual or readiness methods a second time.
    add = (
        "\n      // Exact source action/list/ordinal PRE fields, no virtual calls.\n"
        '      sim->print_log( "' + MARK +
        '{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}",\n'
        "        sim->current_time().total_millis(), zrot_pre_owner,\n"
        "        zrot_pre_ordinal, a->name_str,\n"
        "        static_cast<int>( a->movement_directionality ),\n"
        "        static_cast<int>( a->player->current.movement_direction ),\n"
        "        a->usable_while_casting ? 1 : 0,\n"
        "        a->player->executing ? 1 : 0,\n"
        "        a->player->channeling ? 1 : 0,\n"
        "        a->player->gcd_ready.total_millis(), zrot_moving );"
    )
    output = text.replace(POST_CAST_ANCHOR, POST_CAST_ANCHOR + add, 1)
    if (output.count(ORIGINAL_READY_CALL) != 1 or
        output.count("a->action_ready()") != text.count("a->action_ready()") or
        output.count("a->usable_moving()") != text.count("a->usable_moving()") or
        output.count("a->cost_affordable()") != text.count("a->cost_affordable()") or
        output.count(MARK) != 1 or
        output.index(MARK) > output.index(ORIGINAL_READY_CALL)):
        raise SourceProbeError("ORIGINAL_READINESS_METHOD_COUNT_OR_ORDER_DRIFT")
    return output.encode()


def run_patch(root: Path, profile: Path, expected_profile_blob: str) -> dict:
    root = root.resolve(strict=True)
    if git_blob(profile.read_bytes()) != expected_profile_blob or expected_profile_blob != PROFILE_BLOB:
        raise SourceProbeError("SOURCE_PROFILE_NOT_PINNED")
    pin = verify_pristine_source(root)
    player = root / PLAYER
    changed = extend_player(player.read_bytes())
    # Only edit the prior producer's existing selection PRE source.
    player.write_bytes(changed)
    return {"schema": SCHEMA, "policy_id": POLICY,
            "official_source": pin, "modified_player_sha256": digest(changed),
            "original_ready_method_call_count_unchanged": True,
            "new_virtual_or_target_calls": 0,
            "new_post_source_comparator_as_operand": False,
            "original_NATIVE_and_pristine_behavior_parity": "NOT_YET_TESTED",
            "WCL_API_calls": 0, "positive_READY_certified": 0}


def parse_probe(line: str) -> dict | None:
    start = line.find(MARK)
    if start < 0:
        return None
    p = line[start:].strip().split("|")
    if len(p) != 12 or not p[1].isdigit() or not p[3].isdigit() or not p[2] or not p[4]:
        raise SourceProbeError("DIRECTION_CAST_PRE_SOURCE_MARKER_INVALID")
    try:
        fields = [int(v) for v in p[5:]]
    except ValueError as exc:
        raise SourceProbeError("DIRECTION_CAST_PRE_NONNUMERIC_FIELD") from exc
    action_dir, actor_dir, usable_cast, executing, channeling, gcd_ready_ms, is_moving = fields
    if (action_dir not in range(5) or actor_dir not in range(5) or
        any(v not in (0, 1) for v in (usable_cast, executing, channeling, is_moving))):
        raise SourceProbeError("DIRECTION_CAST_PRE_ENUM_OR_BOOL_OUT_OF_RANGE")
    return {"time_ms": int(p[1]), "list": p[2], "ordinal": int(p[3]),
            "native_name": p[4], "action_direction": action_dir,
            "actor_direction": actor_dir,
            "usable_while_casting": usable_cast,
            "actor_executing": executing, "actor_channeling": channeling,
            "gcd_ready_ms": gcd_ready_ms, "actor_is_moving": is_moving}


def independent_partial(raw: dict, guard: dict, cast: dict) -> dict:
    k = exact_key(raw)
    if (k != exact_key(guard) or k != exact_key(cast) or
        guard["player_is_moving"] != raw["actor_is_moving"]):
        raise SourceProbeError("ORIGINAL_PRE_SOURCE_POINTER_OR_MOVEMENT_MISMATCH")
    # Strictly the pinned base method's expression. Virtual dispatch and
    # subclass override are NOT established by these field reads.
    a, m = raw["action_direction"], raw["actor_direction"]
    direction_ok = a in (NONE, OMNI) or m == NONE or m == a
    cast_branch_bypassed = raw["usable_while_casting"] == 0
    # Existing postguard repeats are a separate necessary predicate.
    # Never treat the raw GCD clock as the virtual gcd() result.
    return {
        "base_directionality_numeric": direction_ok,
        "base_usable_while_casting_branch_bypassed": cast_branch_bypassed,
        "actor_moving_original_PRE": raw["actor_is_moving"],
        "actor_movement_direction_original_PRE": m,
        "action_directionality_original_PRE": a,
        "actor_gcd_ready_ms_original_PRE": raw["gcd_ready_ms"],
        "original_method_PRE_time_ms": k[0],
        "readiness_virtual_dispatch_closed": False,
        "CAST_GCD_full_route": "UNKNOWN",
        "MOVEMENT_full_route": "UNKNOWN",
        "physical_skill_READY": "UNKNOWN",
        "dummy_error_permitted": False,
    }


def audit_trace(trace: str, *, focus_key: tuple[int, str, int, str]) -> dict:
    if len(focus_key) != 4:
        raise SourceProbeError("FOCUSED_ORIGINAL_PRE_IDENTITY_REQUIRED")
    pending = None
    count = 0
    focus = []
    observed = Counter()
    for line in trace.splitlines():
        g = read_guard(line)
        if g is not None:
            if pending is not None and (
                    pending["cast"] is None or pending["probe"] is None):
                raise SourceProbeError("PREVIOUS_SOURCE_ATTEMPT_UNPAIRED")
            pending = {"guard": g, "cast": None, "probe": None}
            continue
        c = parse_cast(line)
        if c is not None:
            if (pending is None or pending["cast"] is not None or
                exact_key(c) != exact_key(pending["guard"])):
                raise SourceProbeError("POST_CAST_PRE_NOT_CURRENT_OR_DUPLICATED")
            pending["cast"] = c
            continue
        p = parse_probe(line)
        if p is None:
            continue
        if (pending is None or pending["probe"] is not None or
            pending["cast"] is None):
            raise SourceProbeError("DIRECTION_PRE_UNPAIRED_OR_DUPLICATED")
        witness = independent_partial(p, pending["guard"], pending["cast"])
        pending["probe"] = p
        count += 1
        observed["direction_base_true" if witness["base_directionality_numeric"]
                 else "direction_base_false"] += 1
        observed["cast_branch_bypassed" if witness["base_usable_while_casting_branch_bypassed"]
                 else "cast_branch_unresolved"] += 1
        if exact_key(p) == focus_key:
            focus.append({"source_key": list(focus_key),
                          "observed_direct_source_fields": p,
                          "independent_base_subpredicates": witness})
    if pending is not None and (
            pending["cast"] is None or pending["probe"] is None):
        raise SourceProbeError("TRUNCATED_FINAL_SOURCE_PRE_ATTEMPT")
    if count <= 0 or len(focus) != 1:
        raise SourceProbeError("EXACT_ORIGINAL_FOCUSED_ACTION_NOT_ONE")
    return {"schema": SCHEMA, "policy_id": POLICY, "scope": "SIMC_ORIGINAL_METHOD_PRE",
            "original_pre_attempts_with_fields": count,
            "raw_numeric_summary": dict(sorted(observed.items())),
            "one_exact_source_key": focus[0],
            "no_additional_original_virtual_method_calls": True,
            "original_choice_not_independent_proof": True,
            "WCL_strict_PRE_not_observed": True,
            "full_positive_READY_proven": 0, "dummy_error_permitted": False,
            "WCL_API_calls": 0}


def selftest() -> dict:
    synthetic_player = (
        'before\nZROT_NATIVE_POST_CAST_PRE_V1|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}\n'
        + POST_CAST_ANCHOR + "\n" + ORIGINAL_READY_CALL + "\nafter\n"
    ).encode()
    instrumented = extend_player(synthetic_player).decode()
    assert instrumented.count(MARK) == 1
    assert instrumented.count("a->action_ready()") == 1
    assert instrumented.index(MARK) < instrumented.index(ORIGINAL_READY_CALL)
    try:
        extend_player(instrumented.encode())
    except SourceProbeError:
        pass
    else:
        raise AssertionError("DUPLICATE_DIRECTION_CAST_PRODUCER_ACCEPTED")
    trace = "\n".join((
        "ZROT_NATIVE_READY_GUARDS_PRE_V1|20031|slayer|7|rampage|1|1|0|-1|1",
        "ZROT_NATIVE_POST_CAST_PRE_V1|20031|slayer|7|rampage|0|0|0|0|0|0",
        MARK + "20031|slayer|7|rampage|0|0|0|0|0|19000|0",
    ))
    focused = (20031, "slayer", 7, "rampage")
    r = audit_trace(trace, focus_key=focused)
    assert r["original_pre_attempts_with_fields"] == 1
    witness = r["one_exact_source_key"]["independent_base_subpredicates"]
    assert witness["base_directionality_numeric"] is True
    assert witness["base_usable_while_casting_branch_bypassed"] is True
    assert witness["physical_skill_READY"] == "UNKNOWN"
    # is_moving() and current.movement_direction are separate signals.
    marker = MARK + "20031|slayer|7|rampage|3|2|1|0|0|22000|0"
    negative = audit_trace(trace.splitlines()[0] + "\n" +
                           trace.splitlines()[1] + "\n" + marker + "\n",
                           focus_key=focused)
    n = negative["one_exact_source_key"]["independent_base_subpredicates"]
    assert n["base_directionality_numeric"] is False
    assert n["base_usable_while_casting_branch_bypassed"] is False
    for bad in (
        trace.replace("|19000|0", "|19000|1"),
        trace + "\n" + trace.splitlines()[-1],
        trace.replace("20031|slayer|7|rampage|0|0|0|0|0|19000|0",
                      "20031|slayer|6|rampage|0|0|0|0|0|19000|0"),
    ):
        try:
            audit_trace(bad, focus_key=focused)
        except SourceProbeError:
            pass
        else:
            raise AssertionError("FORGED_OR_DUPLICATED_SOURCE_PRE_ACCEPTED")
    return {"schema": SCHEMA, "status": "PASS_OFFLINE_SYNTHETIC",
            "checks": 12, "original_CXX_build": "NOT_RUN",
            "WCL_API_calls": 0, "full_positive_READY": 0}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root", type=Path)
    p.add_argument("--official-profile", type=Path)
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--receipt", type=Path)
    p.add_argument("--audit-log", type=Path)
    p.add_argument("--focus-time-ms", type=int)
    p.add_argument("--focus-list")
    p.add_argument("--focus-ordinal", type=int)
    p.add_argument("--focus-action")
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    patch_fields = (a.simc_root,a.official_profile,
                    a.expected_profile_git_blob,a.receipt)
    audit_fields = (a.audit_log,a.focus_time_ms,a.focus_list,
                    a.focus_ordinal,a.focus_action,a.out)
    if not any(patch_fields + audit_fields):
        result = selftest()
    elif all(patch_fields) and not any(audit_fields):
        result = run_patch(a.simc_root,a.official_profile,
                           a.expected_profile_git_blob)
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as out:
            out.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
        print("SOURCE_PASSIVE_DIRECTION_CAST_PATCH_SHA256=" +
              digest(a.receipt.read_bytes()))
        return
    elif all(v is not None for v in audit_fields) and not any(patch_fields):
        if a.focus_time_ms < 0 or a.focus_ordinal < 1:
            p.error("invalid focus time/ordinal")
        result=audit_trace(
            a.audit_log.read_text(),
            focus_key=(a.focus_time_ms,a.focus_list,
                       a.focus_ordinal,a.focus_action))
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:
            f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
        print("SOURCE_PASSIVE_DIRECTION_CAST_AUDIT_SHA256=" +
              digest(a.out.read_bytes()))
        return
    else:
        p.error("patch, audit, or no-arg synthetic mode; never mix modes")
    print(json.dumps(result,sort_keys=True))


if __name__ == "__main__":
    main()
