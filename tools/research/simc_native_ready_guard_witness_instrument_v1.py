#!/usr/bin/env python3
"""Pinned passive PRE guard witness at real SimC select_action attempts.

Record source-verified *operands* for the first five generic
action_t::ready() guards, plus separate proof that both base
action_t::action_ready() and action_t::ready() were entered. These
observations are neither complete readiness nor a generic caster
ready predicate. Native ready() and action_ready() are still called
exactly once by the original selection path; never use their result
as an input to the independent tri-state evaluator.

IMPORTANT: virtual usable_moving() and cost_affordable() are read as
source guard operands only on the same short-circuit path that the
base ready() would traverse. Pristine-vs-instrumented Native action
sequence nonperturbation is necessary for trust; missing base-entry
evidence requires UNKNOWN for subclass/override paths.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from simc_apl_semantic_ir_v2 import git_blob
from simc_native_if_expression_instrument_v1 import (
    PINNED_COMMIT, ACTION_CPP_BLOB, BEFORE, AFTER, PatchError,
)
from simc_native_if_movement_event_pre_instrument_v1 import (
    instrument as instrument_environment, inventory as environment_inventory,
    official_source_contract,
)
from simc_native_if_talent_pre_instrument_v1 import talent_inventory
from simc_native_if_buff_pre_instrument_v1 import buff_inventory
from simc_native_if_action_gcd_cd_pre_instrument_v1 import source_inventory
from simc_apl_semantic_ir_v2 import parse_profile
from simc_native_select_trace_instrument_v1 import (
    instrument as instrument_select,
    PLAYER_CPP_BLOB, START, END, CHECK, PinError,
)
from simc_native_if_action_gcd_cd_pre_instrument_v1 import verify_semantics

SCHEMA = "ZrotNativeActualReadyBaseGuardPreWitnessPatchV1"
MARK = "ZROT_NATIVE_READY_GUARDS_PRE_V1|"
BASE_READY_MARK = "ZROT_NATIVE_BASE_READY_ENTER_V1|"
BASE_ACTION_MARK = "ZROT_NATIVE_BASE_ACTION_READY_ENTER_V1|"
CD_CPP_BLOB = "b73f7963ffc7434ee1aa0853e8335b39fe4cf96d"
ACTION_HPP_BLOB = "19f1e8d31d6b7ea31c828e519735fafe83b8735d"
ACTION_CPP = Path("engine/action/action.cpp")
PLAYER_CPP = Path("engine/player/player.cpp")
READY_SITE = "bool action_t::ready()\n{\n"
A_READY_SITE = "bool action_t::action_ready()\n{\n"

class GuardPatchError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_source(root: Path) -> dict:
    source = official_source_contract(root)
    semantics = verify_semantics(root)
    action_header = (root / "engine/action/action.hpp").read_bytes()
    if git_blob(action_header) != ACTION_HPP_BLOB:
        raise GuardPatchError("PINNED_PUBLIC_ACTION_API_SOURCE_CHANGED")
    txt = action_header.decode("utf-8")
    for val in ("virtual bool ready();", "virtual bool action_ready();",
                "virtual bool usable_moving() const;",
                "virtual bool cost_affordable();",
                "cooldown_t* cooldown, *internal_cooldown;"):
        if txt.count(val) != 1:
            raise GuardPatchError("ACTION_HEADER_VIRTUAL_GUARD_CONTRACT_CHANGED")
    cpp = (root / ACTION_CPP).read_bytes()
    player = (root / PLAYER_CPP).read_bytes()
    if (git_blob(cpp) != ACTION_CPP_BLOB or
        git_blob(player) != PLAYER_CPP_BLOB or
        git_blob((root / "engine/sim/cooldown.cpp").read_bytes()) != CD_CPP_BLOB):
        raise GuardPatchError("PINNED_PRISTINE_READY_SOURCE_MISMATCH")
    ready = cpp.decode().split(READY_SITE,1)[1].split("\nvoid action_t::init()",1)[0]
    guards = (
        "if ( !cooldown->is_ready() )",
        "if ( internal_cooldown->down() )",
        "if ( player->is_moving() && !usable_moving() )",
        "if ( !cost_affordable() )",
    )
    positions = []
    for guard in guards:
        if ready.count(guard) != 1:
            raise GuardPatchError("BASE_READY_SOURCE_GUARD_CHANGED")
        positions.append(ready.index(guard))
    if positions != sorted(positions):
        raise GuardPatchError("BASE_READY_GUARD_ORDER_CHANGED")
    return {
        "source_contract": source,
        "source_action_context": semantics,
        "source_header_blob": ACTION_HPP_BLOB,
        "proven_base_ready_guard_order": [
            "cooldown_queueable", "internal_cooldown_up",
            "moving_usable", "cost_affordable",
        ],
        "subclass_overrides_possible": True,
    }


def patched_action(raw: bytes, talents: list[str], buffs: list[str],
                   actions: list[str], environments: list[str],
                   *, strict: bool = True) -> bytes:
    text = instrument_environment(
        raw, talents, buffs, actions, environments, strict=strict
    ).decode("utf-8")
    if text.count(READY_SITE) != 1 or text.count(A_READY_SITE) != 1:
        raise GuardPatchError("BASE_READY_FUNCTION_SITES_NOT_UNIQUE")
    if BASE_READY_MARK in text or BASE_ACTION_MARK in text:
        raise GuardPatchError("BASE_READY_ALREADY_INSTRUMENTED")
    header1 = (
        READY_SITE +
        '  // Source method entry, not Native ready() result.\n'
        '  if ( sim->log && player && !player->is_pet() && !player->is_enemy() )\n'
        '    sim->print_log( "' + BASE_READY_MARK + '{}|{}",\n'
        '      sim->current_time().total_millis(), name_str );\n'
    )
    header2 = (
        A_READY_SITE +
        '  // Source method entry, not Native action_ready() result.\n'
        '  if ( sim->log && player && !player->is_pet() && !player->is_enemy() )\n'
        '    sim->print_log( "' + BASE_ACTION_MARK + '{}|{}",\n'
        '      sim->current_time().total_millis(), name_str );\n'
    )
    text = text.replace(READY_SITE, header1, 1)
    text = text.replace(A_READY_SITE, header2, 1)
    # Other functions in action.cpp may contain unrelated IF evaluations.
    # Enforce exactly one original IF call within this action_ready() only.
    original_action_ready = text.split(BEFORE, 1)[1].split(AFTER, 1)[0]
    if (original_action_ready.count("if_expr->success()") != 1 or
        text.count(BASE_READY_MARK) != 1 or
        text.count(BASE_ACTION_MARK) != 1):
        raise GuardPatchError("SOURCE_GUARD_ENTRY_ORIGINAL_IF_COUNT_CHANGED")
    return text.encode("utf-8")


def patched_player(raw: bytes, *, strict: bool = True) -> bytes:
    text = instrument_select(raw, enforce_pin=strict).decode("utf-8")
    prefix = (
        "    // Capture the return of the SAME native readiness call; never call twice.\n"
        "    bool zrot_native_ready = a->action_ready();"
    )
    if text.count(prefix) != 1 or MARK in text:
        raise GuardPatchError("ORIGINAL_READY_SELECTION_CALLSITE_CHANGED")
    patch = (
        '    // Source PRE-guard inputs, not the action_ready result.\n'
        '    // Compute virtual predicates only along the base short-circuit path.\n'
        '    if ( sim->log && !is_pet() && !is_enemy() )\n'
        '    {\n'
        '      const int zrot_cd_queue = a->cooldown ? ( a->cooldown->is_ready() ? 1 : 0 ) : -1;\n'
        '      const int zrot_icd_up = a->internal_cooldown ? ( a->internal_cooldown->down() ? 0 : 1 ) : -1;\n'
        '      const int zrot_moving = a->player->is_moving() ? 1 : 0;\n'
        '      const int zrot_usable_move =\n'
        '        ( zrot_moving && zrot_cd_queue == 1 && zrot_icd_up == 1 ) ?\n'
        '          ( a->usable_moving() ? 1 : 0 ) : -1;\n'
        '      const bool zrot_gates_before_cost =\n'
        '        zrot_cd_queue == 1 && zrot_icd_up == 1 &&\n'
        '        ( !zrot_moving || zrot_usable_move == 1 );\n'
        '      const int zrot_cost_ok = zrot_gates_before_cost ?\n'
        '        ( a->cost_affordable() ? 1 : 0 ) : -1;\n'
        '      unsigned zrot_pre_ordinal = 0;\n'
        '      std::string zrot_pre_owner = "UNKNOWN";\n'
        '      if ( a->action_list && a->signature )\n'
        '      {\n'
        '        const auto& zrot_owner = *a->action_list;\n'
        '        for ( std::size_t zrot_k = 0; zrot_k < zrot_owner.action_list.size(); ++zrot_k )\n'
        '          if ( &( zrot_owner.action_list[ zrot_k ] ) == a->signature )\n'
        '          {\n'
        '            zrot_pre_owner = zrot_owner.name_str;\n'
        '            zrot_pre_ordinal = static_cast<unsigned>( zrot_k + 1 );\n'
        '            break;\n'
        '          }\n'
        '      }\n'
        '      sim->print_log( "' + MARK +
        '{}|{}|{}|{}|{}|{}|{}|{}|{}",\n'
        '        sim->current_time().total_millis(), zrot_pre_owner,\n'
        '        zrot_pre_ordinal, a->name_str, zrot_cd_queue, zrot_icd_up,\n'
        '        zrot_moving, zrot_usable_move, zrot_cost_ok );\n'
        '    }\n'
        + prefix
    )
    text = text.replace(prefix, patch, 1)
    if (text.count("zrot_native_ready = a->action_ready();") != 1 or
        text.count(MARK) != 1):
        raise GuardPatchError("DUPLICATE_NATIVE_READY_EVALUATION_OR_MARKER")
    return text.encode("utf-8")


def run(root: Path, profile: Path, profile_blob: str | None) -> dict:
    root = root.resolve(strict=True)
    revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if revision != PINNED_COMMIT:
        raise GuardPatchError("SIMC_GIT_REVISION_CHANGED")
    contract = verify_source(root)
    data = profile.read_bytes()
    if not profile_blob or git_blob(data) != profile_blob:
        raise GuardPatchError("OFFICIAL_PROFILE_BLOB_MISMATCH")
    ir = parse_profile(data, require_source=False)
    talents = talent_inventory(ir)
    buffs = buff_inventory(ir)
    actions = source_inventory(ir)
    environments = environment_inventory(ir)
    target_action = root / ACTION_CPP
    target_player = root / PLAYER_CPP
    action_patch = patched_action(target_action.read_bytes(), talents,
                                  buffs, actions, environments)
    player_patch = patched_player(target_player.read_bytes())
    # All source identity and patch assertions precede first source write.
    target_action.write_bytes(action_patch)
    target_player.write_bytes(player_patch)
    return {
        "schema": SCHEMA,
        "official_simc_commit": revision,
        "official_profile_git_blob": git_blob(data),
        "original_action_cpp_blob": ACTION_CPP_BLOB,
        "original_player_cpp_blob": PLAYER_CPP_BLOB,
        "modified_action_cpp_sha256": sha(action_patch),
        "modified_player_cpp_sha256": sha(player_patch),
        "source_proof": contract,
        "readiness_calls_once_per_selected_action_row": True,
        "original_if_evaluated_once": True,
        "native_ready_boolean_never_source_fact": True,
        "source_base_ready_entry_markers_not_guaranteed_for_overrides": True,
        "native_behavior_nonperturbation": "NOT_YET_TESTED",
        "WCL_API_calls": 0,
        "MAIN_promotion": False,
    }


def selftest() -> dict:
    from simc_native_if_expression_instrument_v1 import OLD
    from simc_native_if_movement_event_pre_instrument_v1 import inventory
    from simc_native_select_trace_instrument_v1 import START, END
    synth = parse_profile(
        b"actions=foo,if=talent.alpha&buff.bar.up&gcd<1.5&movement.distance>1&cooldown.x.ready\n"
        b"actions+=/bar,if=raid_event.movement.in>1&raid_event.movement.distance>5\n",
        require_source=False,
    )
    original_action = (
        BEFORE + "  if ( !ready() ) return false;\n" +
        OLD + "\n  return true;\n}\n" + AFTER +
        "  return true;\n}\n" + READY_SITE +
        "  if ( !cooldown->is_ready() ) return false;\n"
        "  return true;\n}\n"
        "\nvoid action_t::init()\n{}\n"
    ).encode()
    a = patched_action(
        original_action, talent_inventory(synth),
        buff_inventory(synth), source_inventory(synth),
        inventory(synth), strict=False).decode()
    assert a.count("if_expr->success()") == 1
    assert a.count(BASE_ACTION_MARK) == 1
    assert a.count(BASE_READY_MARK) == 1
    original_player = (
        START + "\n{\n"
        "  // Mark this action list as visited with the APL internal id\n"
        "    if ( a->action_ready() )\n"
        "          return real_a;\n"
        "        return a;\n"
        "  return nullptr;\n}\n" + END + "\n{}\n"
    ).encode()
    p = patched_player(original_player, strict=False).decode()
    assert p.count(MARK) == 1
    assert p.count("zrot_native_ready = a->action_ready()") == 1
    assert p.index(MARK) < p.index("zrot_native_ready = a->action_ready()")
    assert "a->cost_affordable()" in p and "a->usable_moving()" in p
    assert p.count("ZROT_NATIVE_SELECT_V1|ATTEMPT") == 1
    for invalid in (
        original_player.replace(b"if ( a->action_ready() )",
                                b"if ( a->ready() )"),
        original_player + b"ZROT_NATIVE_READY_GUARDS_PRE_V1|",
    ):
        try:
            patched_player(invalid, strict=False)
        except (GuardPatchError, PinError):
            pass
        else:
            raise AssertionError("UNSAFE_READY_SOURCE_PATCH_ACCEPTED")
    return {
        "status": "PASS_OFFLINE_SYNTHETIC",
        "checks": 12,
        "real_native_compile": "NOT_RUN",
        "WCL_API_calls": 0,
        "full_action_ready_proof": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root", type=Path)
    p.add_argument("--official-profile", type=Path)
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--receipt", type=Path)
    a = p.parse_args()
    if not a.simc_root and not a.official_profile:
        receipt = selftest()
    elif a.simc_root and a.official_profile:
        receipt = run(a.simc_root, a.official_profile,
                      a.expected_profile_git_blob)
    else:
        p.error("simc root and official profile must be provided together")
    raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) +
           "\n").encode()
    if a.receipt:
        a.receipt.parent.mkdir(parents=True, exist_ok=True)
        with a.receipt.open("xb") as f:
            f.write(raw)
    else:
        print(raw.decode(), end="")


if __name__ == "__main__":
    main()
