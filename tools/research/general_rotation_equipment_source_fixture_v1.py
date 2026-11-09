#!/usr/bin/env python3
"""Warrior example adapter / source-pinned equipment rule fixture.

Specialization-specific source semantics live HERE, not inside the
general_rotation_condition_ir_v1 generic interpreter. The exact original
warrior Rampage parent ready() guard is pinned to official SimC C++.
This static mapping does not establish the runtime weapon state, virtual
dispatch, or complete READY. No synthetic Rogue/dual-dagger example is
advertised as a real retail specialization spell mechanic.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from general_rotation_condition_ir_v1 import (
    SourceBoundRequirement,inspect_requirement,ConditionalIRError
)
from general_rotation_decision_proof_engine_v1 import Identity
from simc_apl_semantic_ir_v2 import parse_profile,git_blob

SCHEMA="ZrotWarriorSourcePinnedEquipmentSpecAdapterFixtureV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
WARRIOR_BLOB="38ee3dd0d5943eb9227ec55aefb21e7d47244f96"
PROFILE_BLOB="3225992ed5b754ad5d61e8b785d9d859f1eed1be"
SOURCE_ROW_SHA="217c49dcce32cbc0d975679ed09e0a79c71f05e2615e6566f46bffc9b1ffece2"
METHOD="engine/class_modules/sc_warrior.cpp"
START="struct rampage_parent_t : public warrior_attack_t"
END="// Ravager"
READY="bool ready() override"
GUARD=("if ( p()->main_hand_weapon.type == WEAPON_NONE || "
       "p()->off_hand_weapon.type == WEAPON_NONE )")
DELEGATE="return warrior_attack_t::ready();"
LIST="slayer"
ORDINAL=7
ACTION="rampage"


class WarriorEquipmentSourceError(ValueError):
    pass


def atom(key:str,cmp:str,value:str)->dict:
    return {"op":"compare","field":key,"cmp":cmp,"value":value}


def source_rule(source:bytes,profile:bytes)->tuple[SourceBoundRequirement,Identity]:
    if git_blob(source)!=WARRIOR_BLOB or git_blob(profile)!=PROFILE_BLOB:
        raise WarriorEquipmentSourceError("PINNED_WARRIOR_SOURCE_PROFILE_CHANGED")
    text=source.decode("utf-8")
    if text.count(START)!=1:
        raise WarriorEquipmentSourceError("EXPECTED_RAMPAGE_PARENT_SOURCE_NOT_UNIQUE")
    body=text.split(START,1)[1].split(END,1)[0]
    if (body.count(READY)!=1 or body.count(GUARD)!=1 or
        body.count(DELEGATE)!=1 or
        not body.index(READY)<body.index(GUARD)<body.index(DELEGATE)):
        raise WarriorEquipmentSourceError("PINNED_RAMPAGE_READY_GUARD_CHANGED")
    ir=parse_profile(profile,require_source=True,expected_git_blob=PROFILE_BLOB)
    if LIST not in ir["action_lists"] or ORDINAL>len(ir["action_lists"][LIST]):
        raise WarriorEquipmentSourceError("PINNED_SOURCE_ACTION_ROW_MISSING")
    row=ir["action_lists"][LIST][ORDINAL-1]
    if (row["behavior"]!="ACTION" or row["action"]!=ACTION or
        row["source_sha256"]!=SOURCE_ROW_SHA):
        raise WarriorEquipmentSourceError("SOURCE_ROW_SOURCE_METHOD_BINDING_DRIFT")
    # Positive requirement is logically equivalent to the original
    # disqualifying OR: !none(main_hand) AND !none(off_hand).
    # This is TWO distinct weapon slots, NOT a single two-handed weapon.
    expression={"op":"all","children":[
        atom("equipment.main_hand.weapon_type","ne","NONE"),
        atom("equipment.off_hand.weapon_type","ne","NONE"),
    ]}
    requirement=SourceBoundRequirement(
        semantic_key="equipment.mainhand_offhand_present",
        source_profile_git_blob=PROFILE_BLOB,
        source_row_sha256=SOURCE_ROW_SHA,
        source_method_path=METHOD,
        source_method_git_blob=WARRIOR_BLOB,
        source_guard_sha256=sha256(GUARD.encode()).hexdigest(),
        gate="necessary_eligibility",
        expression=expression)
    identity=Identity(
        scope=LIST+"::"+ACTION,source_sha256=SOURCE_ROW_SHA,
        t_ms=20031,ordinal=ORDINAL-1,occurrence=0)
    return requirement,identity


def audit(source:bytes,profile:bytes)->dict:
    rule,identity=source_rule(source,profile)
    # At original SimC 20031ms we have no source-equipment PRE marker.
    # The original selected spell is not evidence of a main-hand/off-hand.
    result=inspect_requirement(
        rule,source_profile_git_blob=PROFILE_BLOB,
        identity=identity,observations=[],
        origin="SIMC_ORIGINAL_METHOD_PRE")
    if (result["hypothesis"]["tri_value"]!="UNKNOWN" or
        result["hypothesis"]["missing_field_keys"]!=[
            "equipment.main_hand.weapon_type",
            "equipment.off_hand.weapon_type"] or
        result["open_world_candidate_proof"]!="UNKNOWN" or
        result["dummy_error_permitted"]):
        raise WarriorEquipmentSourceError("UNKNOWN_EQUIPMENT_PRE_WAS_LAUNDERED")
    return {
        "schema":SCHEMA,
        "policy_id":POLICY,
        "source_profile_git_blob":PROFILE_BLOB,
        "official_warrior_cpp_blob":WARRIOR_BLOB,
        "original_cpp_source_guard_sha256":rule.source_guard_sha256,
        "original_source_row_sha256":SOURCE_ROW_SHA,
        "source_bound_rule_id":rule.stable_rule_id,
        "source_guard_verified_against_original_cpp":True,
        "weapon_requirement_equivalence":"MAIN_HAND_PRESENT_AND_OFF_HAND_PRESENT",
        "single_two_handed_weapon_requirement_proven":False,
        "original_source_equipment_field_observations":0,
        "original_runtime_equipment_eligibility":"UNKNOWN",
        "original_virtual_dispatch_or_full_ready":"UNKNOWN",
        "tested_generic_rule":result,
        "can_expand_to_two_daggers_without_engine_change":True,
        "actual_WCL_or_dummy_practice_verdict":False,
        "MAIN_promoted":False,
    }


def selftest()->dict:
    # This synthetic fixture verifies that SOURCE pins are validated:
    # a fake C++ body/profile must be rejected; it cannot be silently
    # interpreted as trusted source mechanics.
    try:
        source_rule(
            (START+"\n"+READY+"\n"+GUARD+"\n"+DELEGATE).encode(),
            b"actions=/rampage\n")
    except WarriorEquipmentSourceError:pass
    else:raise AssertionError("UNPINNED_SOURCE_ACCEPTED")
    # Proven actual missing equipment state must remain UNKNOWN.
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":3,"actual_official_CPP_files_read":False,
        "full_positive_READY":0,"WCL_API_calls":0,
    }


def main()->None:
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--official-warrior-source",type=Path)
    cli.add_argument("--official-profile",type=Path)
    cli.add_argument("--out",type=Path)
    a=cli.parse_args()
    if all(x is None for x in (
            a.official_warrior_source,a.official_profile,a.out)):
        print(json.dumps(selftest(),sort_keys=True))
        return
    if not (a.official_warrior_source and a.official_profile and a.out):
        cli.error("source + profile + out needed for pinned source audit")
    result=audit(a.official_warrior_source.read_bytes(),
                 a.official_profile.read_bytes())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:
        f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    print("SOURCE_PINNED_EQUIPMENT_SPEC_ADAPTER_RECEIPT_SHA256="+
          sha256(a.out.read_bytes()).hexdigest())


if __name__=="__main__":
    main()
