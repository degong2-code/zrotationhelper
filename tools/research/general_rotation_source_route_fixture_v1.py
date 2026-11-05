#!/usr/bin/env python3
"""Specialization-specific *fixtures*, separate from the generic route engine.

Pinned official SimC source sites from Fury and Arcane are examples of the
source declarative adapter surface. Static sites do not close virtual routes,
and this module never certifies READY or WCL/dummy-practice decisions.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from general_rotation_source_route_audit_v1 import (
    MethodSite, RoutePlan, audit, SourceRouteAuditError
)
from simc_native_decision_proof_bridge_v1 import GATES

SCHEMA = "ZrotGeneralRotationTwoSpecSourceRouteFixtureAuditV1"
UPSTREAM = "b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
ACTION = "engine/action/action.cpp"
WARRIOR = "engine/class_modules/sc_warrior.cpp"
MAGE = "engine/class_modules/sc_mage.cpp"
ACTION_BLOB = "399ecd9453b3f30bfc2ebf2b3ffd8f56cce8f8d4"
WARRIOR_BLOB = "38ee3dd0d5943eb9227ec55aefb21e7d47244f96"
MAGE_BLOB = "306d835f2db5f7418da221ce155d32e81c53f45c"


def base_ready() -> MethodSite:
    return MethodSite(
        "base_ready", ACTION, ACTION_BLOB, "bool action_t::ready()", None,
        ("if ( !cooldown->is_ready() )",
         "if ( internal_cooldown->down() )",
         "if ( player->is_moving() && !usable_moving() )",
         "if ( !cost_affordable() )",
         "if ( usable_while_casting )",
         "player->gcd_ready > sim->current_time()"),
        (), ("COOLDOWN", "RESOURCE", "MOVEMENT", "CAST_GCD"), True
    )


def base_action(next_nodes: tuple[str, ...]) -> MethodSite:
    return MethodSite(
        "base_action", ACTION, ACTION_BLOB, "bool action_t::action_ready()", None,
        ("if ( !ready() )",
         "if ( !select_target() )",
         "if ( !has_movement_directionality() )",
         "if ( line_cooldown->down() )",
         "if ( sync_action && !sync_action->action_ready() )",
         "if ( option.moving != -1 && option.moving != ( player->is_moving() ? 1 : 0 ) )",
         "if ( if_expr && !if_expr->success() )",
         "if ( !cooldown_allow_casting_success &&"),
        next_nodes, ("BASE_TARGET", "SYNC_LINE", "APL_IF", "MOVEMENT", "CAST_GCD"), True
    )


def base_directionality() -> MethodSite:
    return MethodSite(
        "base_directionality", ACTION, ACTION_BLOB,
        "bool action_t::has_movement_directionality() const", None,
        ("if ( movement_directionality == movement_direction_type::NONE || movement_directionality == movement_direction_type::OMNI )",
         "movement_direction_type m = player->movement_direction();"),
        (), ("MOVEMENT",), True
    )


def warrior_route() -> RoutePlan:
    return RoutePlan(
        "warrior_fury_rampage_static_sites", "warrior_action", GATES, (
            MethodSite(
                "warrior_action", WARRIOR, WARRIOR_BLOB,
                "bool action_ready() override",
                "struct warrior_action_t : public parse_action_effects_t<Base>",
                ("if ( !this->replacement_action || this->cooldown->duration == 0_ms )",
                 "return this->replacement_action->action_ready();"),
                ("base_action",), ("SPEC_OVERRIDE_TOTAL",), True),
            base_action(("rampage_ready", "base_directionality")),
            MethodSite(
                "rampage_ready", WARRIOR, WARRIOR_BLOB, "bool ready() override",
                "struct rampage_parent_t : public warrior_attack_t",
                ("if ( p()->main_hand_weapon.type == WEAPON_NONE || p()->off_hand_weapon.type == WEAPON_NONE )",
                 "return warrior_attack_t::ready();"),
                ("warrior_ready",),
                ("SPEC_OVERRIDE_TOTAL", "NECESSARY_ELIGIBILITY"), True),
            MethodSite(
                "warrior_ready", WARRIOR, WARRIOR_BLOB, "bool ready() override",
                "struct warrior_action_t : public parse_action_effects_t<Base>",
                ("if ( this->replacement_action )",
                 "if ( !ab::ready() )",
                 "if ( p()->current.distance_to_move > ab::range && ab::range != -1 )",
                 "if ( ( p()->channeling || p()->buff.bladestorm->check() ) && !usable_while_channeling )"),
                ("base_ready",),
                ("SPEC_OVERRIDE_TOTAL", "NECESSARY_ELIGIBILITY", "MOVEMENT"), True),
            base_ready(),
            base_directionality(),
        )
    )


def mage_route() -> RoutePlan:
    return RoutePlan(
        "mage_arcane_blast_static_sites", "base_action", GATES, (
            base_action(("arcane_blast_ready", "base_directionality")),
            MethodSite(
                "arcane_blast_ready", MAGE, MAGE_BLOB,
                "bool ready() override",
                "struct arcane_blast_t final : public arcane_mage_spell_t",
                ("if ( p()->buffs.prismatic_bolt->check() )",
                 "return arcane_mage_spell_t::ready();"),
                ("base_ready",),
                ("SPEC_OVERRIDE_TOTAL", "NECESSARY_ELIGIBILITY"), True),
            base_ready(),
            base_directionality(),
        )
    )


def audit_both(source_root: Path, native_join: Path | None = None) -> dict:
    evidence = {
        "warrior_fury": audit(warrior_route(), source_root),
        "mage_arcane": audit(mage_route(), source_root),
    }
    if any(
        x["source_positive_READY_closure_eligible"] or
        x["independent_guard_PRE_truth_proven"] or
        x["action_READY"] != "UNKNOWN" for x in evidence.values()
    ):
        raise SourceRouteAuditError("STATIC_ROUTE_CLAIMED_READY")
    native_example = None
    if native_join is not None:
        ledger = json.loads(native_join.read_bytes())
        if (ledger.get("schema") != "ZrotGeneralRotationNativeSourcePreIrEvidenceJoinV1"
                or ledger.get("source_spec") != "warrior_fury"
                or ledger.get("complete_positive_ability_READY_proven") is not False
                or ledger["source_positive_ready_preflight"]["candidate_count"] != 79):
            raise SourceRouteAuditError("ACTUAL_NATIVE_COHORT_NOT_PINNED")
        rows = ledger["source_positive_ready_preflight"]["bounded_cross_case_shortlist"]
        selected = next((r for r in rows if r.get("at_simc_ms") == 20031 and
                         r.get("source_action") == "rampage" and
                         r.get("case") == "moving_st"), None)
        if (selected is None or selected.get("source_row_sha256") !=
                "217c49dcce32cbc0d975679ed09e0a79c71f05e2615e6566f46bffc9b1ffece2"
                or selected.get("earlier_independent_NOT_READY") != 6
                or selected.get("physical_skill_READY") != "UNKNOWN"):
            raise SourceRouteAuditError("NATIVE_SOURCE_ROW_IDENTITY_CHANGED")
        native_example = {
            "source_spec":ledger["source_spec"], "at_simc_ms":selected["at_simc_ms"],
            "actual_source_action_comparator_only":selected["source_action"],
            "missing_or_unverified":selected["unproved_gates"],
            "method_site_audit":"DECLARED_STATIC_SITES_ONLY",
            "virtual_dispatch_complete_for_selected_action":False,
            "positive_READY":"UNKNOWN"
        }
    return {
        "schema": SCHEMA,
        "policy": "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
        "pinned_source_commit": UPSTREAM,
        "spec_fixture_count":len(evidence),
        "audits":evidence,"actual_native_gap_example":native_example,
        "one_generic_engine_two_source_fixtures":True,
        "dynamic_dispatch_and_guard_exhaustiveness_reviewed":False,
        "positive_READY_certified":0,
        "real_Arcane_Native_E2E":False,
        "WCL_API_calls":0, "MAIN_promoted":False
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path,required=True)
    p.add_argument("--native-join",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    result=audit_both(a.source_root,a.native_join)
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as h:h.write(raw)
        print("ROUTE_AUDIT_SHA256="+sha256(raw).hexdigest())
    else:
        print(raw.decode(),end="")


if __name__=="__main__":
    main()
