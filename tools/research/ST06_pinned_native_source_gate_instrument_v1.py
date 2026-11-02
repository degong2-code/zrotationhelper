#!/usr/bin/env python3
"""ST-06 pinned SimC class-specific source-obligation instrumentation.

Fixture-only source hooks, NOT generic engine semantics and NOT readiness
certification. They emit actual native evaluations for the two pinned
specializations while leaving original ready/cost results intact. Hook values
are EVALUATION-TIME observations, NEVER backdated STRICT PRE transitions.
The original SimC checkout must be exactly the pinned upstream commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from simc_apl_pointer_instrument import UPSTREAM_SHA

FILES = {
    "fury": "engine/class_modules/sc_warrior.cpp",
    "havoc": "engine/class_modules/sc_demon_hunter.cpp",
}
SOURCE_BLOBS = {
    "fury": "275a56a140f6800030b61df6958ee50b48c32821",
    "havoc": "d7ee195c60e83f48cca16400a51bd3f68c94b710",
}
SIM_HEADER = "engine/sim/sim.hpp"
COUNTER = "  unsigned long long zrot_native_event_sequence = 0;"
MARK = "ZROT_NATIVE_SOURCE_OBLIGATION_V1|"
FMT = (
    "ZROT_NATIVE_SOURCE_OBLIGATION_V1|{}|{}|{}|{}|{}|{}|{}|{}"
    "|{:.17g}|{:.17g}|{:.17g}|{:.17g}"
)


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _emit(actor: str, kind: str, a: str, b: str, c: str, d: str) -> str:
    # Native record is a function evaluation, NOT a state change.
    return (
        "    if ( " + actor + "->sim->log && !" + actor + "->is_pet() && !" +
        actor + "->is_enemy() )\n"
        "      " + actor + "->sim->print_log(\n"
        '        "' + FMT + '",\n'
        '        "' + kind + '", ' + actor + "->sim->thread_index, " + actor +
        "->sim->current_iteration,\n"
        "        " + actor + "->sim->zrot_native_event_sequence++, " +
        actor + "->sim->current_time().total_millis(),\n"
        "        " + actor + "->actor_index, " + actor + "->actor_spawn_index, id,\n"
        "        " + a + ", " + b + ", " + c + ", " + d + " );\n"
    )


def _segment(source: str, class_name: str) -> tuple[str, str, str]:
    tag = "struct " + class_name + " :"
    if source.count(tag) != 1:
        raise ValueError("CLASS_SOURCE_UNIQUE_ANCHOR_REQUIRED_" + class_name)
    begin = source.index(tag)
    end = source.find("\n};", begin)
    if end < 0:
        raise ValueError("SOURCE_CLASS_END_MISSING")
    return source[:begin], source[begin:end + 3], source[end + 3:]


def _replace_once(body: str, needle: str, replacement: str, label: str) -> str:
    if body.count(needle) != 1:
        raise ValueError("SOURCE_HOOK_UNIQUE_ANCHOR_REQUIRED_" + label)
    return body.replace(needle, replacement, 1)


def patch_fury(source: str) -> str:
    prefix, body, suffix = _segment(source, "rampage_parent_t")
    ready = (
        "  bool ready() override\n"
        "  {\n"
        "    if ( p()->main_hand_weapon.type == WEAPON_NONE || p()->off_hand_weapon.type == WEAPON_NONE )"
    )
    ready_new = (
        "  bool ready() override\n"
        "  {\n"
        "    const int zrot_main_present = p()->main_hand_weapon.type != WEAPON_NONE;\n"
        "    const int zrot_off_present = p()->off_hand_weapon.type != WEAPON_NONE;\n"
        + _emit("p()", "MAIN_AND_OFF_HAND_WEAPON",
                "static_cast<double>( zrot_main_present )",
                "static_cast<double>( zrot_off_present )", "-1.0", "-1.0") +
        "    if ( p()->main_hand_weapon.type == WEAPON_NONE || p()->off_hand_weapon.type == WEAPON_NONE )"
    )
    body = _replace_once(body, ready, ready_new, "FURY_WEAPONS")
    cost_return = "    return c;\n  }\n\n  void execute() override"
    cost_trace = _emit(
        "p()", "DYNAMIC_RESOURCE_COST",
        "c", "p()->resources.current[ RESOURCE_RAGE ]",
        "static_cast<double>( p()->talents.fury.rampaging_berserker_2->ok() )",
        "static_cast<double>( p()->buff.recklessness->check() )",
    )
    body = _replace_once(
        body, cost_return,
        cost_trace + cost_return,
        "FURY_DYNAMIC_COST")
    if body.count(MARK) != 2:
        raise ValueError("FURY_TWO_SOURCE_OBLIGATION_SITES_REQUIRED")
    return prefix + body + suffix


def patch_havoc(source: str) -> str:
    prefix, body, suffix = _segment(source, "felblade_t")
    ready = (
        "  bool ready() override\n"
        "  {\n"
        "    // Felblade has a 1s cooldown triggered by Vengeful Retreat\n"
        "    if ( dh()->cooldown.felblade_vengeful_retreat_movement_shared->down() )"
    )
    # Original cooldown predicate executed exactly once; no test-only re-eval.
    ready_new = (
        "  bool ready() override\n"
        "  {\n"
        "    // Felblade has a 1s cooldown triggered by Vengeful Retreat\n"
        "    const bool zrot_shared_down =\n"
        "      dh()->cooldown.felblade_vengeful_retreat_movement_shared->down();\n"
        + _emit("dh()", "SHARED_MOVEMENT_COOLDOWN",
                "static_cast<double>( zrot_shared_down )", "-1.0", "-1.0", "-1.0") +
        "    if ( zrot_shared_down )"
    )
    body = _replace_once(body, ready, ready_new, "HAVOC_SHARED_MOVEMENT_COOLDOWN")
    if body.count(MARK) != 1 or "movement_directionality = movement_direction_type::TOWARDS;" not in body:
        raise ValueError("HAVOC_SOURCE_ANCHOR_COVERAGE_INVALID")
    return prefix + body + suffix


def apply(root: Path) -> dict:
    revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True, capture_output=True, check=True).stdout.strip()
    if revision != UPSTREAM_SHA:
        raise ValueError("UPSTREAM_PIN_MISMATCH")
    header = (root / SIM_HEADER).read_text(encoding="utf-8")
    if header.count(COUNTER) != 1:
        raise ValueError("NATIVE_MONOTONIC_SOURCE_COUNTER_REQUIRED")
    receipt = {"schema": "ZrotST06PinnedSimcObligationHookSourceV1",
               "upstream_sha": revision, "scope": "SOURCE_FIXTURE_ONLY",
               "original_gameplay_delegation_preserved": True,
               "native_eval_is_strict_pre": False,
               "source_specific_readiness_certified": False,
               "current_retail_verified": False, "promotion": False,
               "files": {}}
    for spec, path in FILES.items():
        source_file = root / path
        old = source_file.read_bytes()
        if blob_sha(old) != SOURCE_BLOBS[spec]:
            raise ValueError("PINNED_NATIVE_SOURCE_BLOB_MISMATCH_" + spec)
        original = old.decode("utf-8")
        patched = (patch_fury(original) if spec == "fury" else patch_havoc(original))
        source_file.write_bytes(patched.encode("utf-8"))
        receipt["files"][spec] = {
            "path": path,
            "source_blob_sha1": blob_sha(old),
            "source_sha256": hashlib.sha256(old).hexdigest(),
            "patched_sha256": hashlib.sha256(patched.encode()).hexdigest(),
            "native_marker_count_in_source": patched.count(MARK),
        }
    return receipt


def selftest() -> dict:
    # Regression only for exact source code anchors. This does NOT compile C++.
    warrior = (
        "struct rampage_parent_t : public warrior_attack_t\n{\n"
        "  double cost() const override\n  {\n    double c = warrior_attack_t::cost();\n"
        "    return c;\n  }\n\n  void execute() override\n  {\n  }\n"
        "  bool ready() override\n  {\n"
        "    if ( p()->main_hand_weapon.type == WEAPON_NONE || p()->off_hand_weapon.type == WEAPON_NONE )\n"
        "      return false;\n    return warrior_attack_t::ready();\n  }\n};\n"
    )
    havoc = (
        "struct felblade_t : public inertia_trigger_t<demon_hunter_attack_t>\n{\n"
        "    movement_directionality = movement_direction_type::TOWARDS;\n"
        "  bool ready() override\n  {\n"
        "    // Felblade has a 1s cooldown triggered by Vengeful Retreat\n"
        "    if ( dh()->cooldown.felblade_vengeful_retreat_movement_shared->down() )\n"
        "      return false;\n    return base_t::ready();\n  }\n};\n"
    )
    fury = patch_fury(warrior)
    dh = patch_havoc(havoc)
    assert fury.count(MARK) == 2
    assert dh.count(MARK) == 1
    assert fury.count("return warrior_attack_t::ready()") == 1
    assert dh.count("felblade_vengeful_retreat_movement_shared->down()") == 1
    assert dh.count("return base_t::ready()") == 1
    for spec, bad in (("fury", fury), ("havoc", dh),
                      ("fury", warrior.replace("return c;", "return 0;")),
                      ("havoc", havoc.replace("movement_directionality = movement_direction_type::TOWARDS;", ""))):
        fn = patch_fury if spec == "fury" else patch_havoc
        try:
            fn(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("UNPINNED_REINSTRUMENTATION_ACCEPTED_" + spec)
    return {"schema": "ZrotST06SourcePatchSyntheticSelftestV1",
            "status": "PASS", "counts": {"fury": 2, "havoc": 1},
            "native_build": "NOT_RUN_IN_SELFTEST",
            "source_specific_ready_certified": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-root", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.upstream_root and not args.self_test:
        report = apply(args.upstream_root)
    else:
        report = selftest()
    print(json.dumps(report, sort_keys=True, indent=2))
