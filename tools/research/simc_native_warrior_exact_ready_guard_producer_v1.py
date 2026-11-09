#!/usr/bin/env python3
"""Warrior source adapter for reusable original method-witness engine.

Only source-pinned rampage_parent_t::ready() is changed. Its original
necessary two-*slot* weapon condition is evaluated once as two pure
weapon enum reads and reused in the same original negative branch.
This is NOT a one-two-handed-weapon requirement and NOT a general Fury
policy. The generic source PRE / action pointer producer is reused;
no additional a->action_ready() or virtual readiness methods are called.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from simc_apl_semantic_ir_v2 import git_blob
from simc_native_select_trace_instrument_v1 import SIMC_COMMIT,PLAYER_CPP_BLOB
from general_rotation_equipment_source_fixture_v1 import (
    WARRIOR_BLOB,PROFILE_BLOB,START,END)
from general_rotation_original_pre_field_transport_v1 import MARK as PRE_MARK
from general_rotation_original_method_witness_v1 import (
    POINTER_MARK,extend_player_pointer)

SCHEMA="ZrotWarriorExactReadyWeaponGuardProducerV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
PLAYER_PATH="engine/player/player.cpp"
WARRIOR_PATH="engine/class_modules/sc_warrior.cpp"
PROFILE_PATH="profiles/MID2/MID2_Warrior_Fury.simc"
METHOD_MARK="ZROT_GR_WARRIOR_EXACT_READY_METHOD_PRE_V1|"
DELEGATE="return warrior_attack_t::ready();"
WEAPON_CHECK_MAIN="p()->main_hand_weapon.type == WEAPON_NONE"
WEAPON_CHECK_OFF="p()->off_hand_weapon.type == WEAPON_NONE"
ORIGINAL=(
    "  bool ready() override\n"
    "  {\n"
    "    if ( p()->main_hand_weapon.type == WEAPON_NONE || p()->off_hand_weapon.type == WEAPON_NONE )\n"
    "    {\n"
    "      return false;\n"
    "    }\n"
    "    return warrior_attack_t::ready();\n"
    "  }"
)

class WarriorGuardProducerError(ValueError):pass

def require(x:bool,why:str)->None:
    if not x:raise WarriorGuardProducerError(why)

def sha(raw:bytes)->str:return sha256(raw).hexdigest()

def verify_pristine(root:Path)->dict:
    root=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    require(rev==SIMC_COMMIT,"ORIGINAL_SIMC_COMMIT_NOT_PINNED")
    blobs={PLAYER_PATH:PLAYER_CPP_BLOB,WARRIOR_PATH:WARRIOR_BLOB,
           PROFILE_PATH:PROFILE_BLOB}
    for p,expected in blobs.items():
        orig=subprocess.run(
            ["git","-C",str(root),"show","HEAD:"+p],
            check=True,capture_output=True).stdout
        require(git_blob(orig)==expected,"SOURCE_GIT_BLOB_DRIFT:"+p)
    return {"official_source_sha":rev,"original_git_blobs":blobs}

def original_guard_replacement()->str:
    return (
        "  bool ready() override\n"
        "  {\n"
        "    // Source PRE: same original, pure weapon-slot enum reads.\n"
        "    const int zrot_gr_main = "+WEAPON_CHECK_MAIN+" ? 0 : 1;\n"
        "    const int zrot_gr_off = "+WEAPON_CHECK_OFF+" ? 0 : 1;\n"
        "    if ( p()->sim->log )\n"
        '      p()->sim->print_log( "'+METHOD_MARK+
        '{}|{}|{}|{}|{}|{}",\n'
        '        p()->sim->current_time().total_millis(), "rampage",\n'
        "        name_str, static_cast<const void*>( this ), zrot_gr_main, zrot_gr_off );\n"
        "    if ( zrot_gr_main == 0 || zrot_gr_off == 0 )\n"
        "    {\n"
        "      return false;\n"
        "    }\n"
        "    "+DELEGATE+"\n"
        "  }"
    )

def extend_warrior(original:bytes,*,check_pin:bool=True)->bytes:
    if check_pin:
        require(git_blob(original)==WARRIOR_BLOB,
                "ORIGINAL_WARRIOR_CPP_BLOB_MISMATCH")
    s=original.decode("utf-8")
    require(METHOD_MARK not in s and s.count(START)==1,
            "WARRIOR_READY_METHOD_ALREADY_PATCHED_OR_NOT_UNIQUE")
    start=s.index(START);end=s.index(END,start)
    body=s[start:end]
    require(body.count(ORIGINAL)==1,"ORIGINAL_RAMPAGE_OVERRIDE_BODY_NOT_EXACT")
    before_count=s.count(DELEGATE)
    new=s[:start]+body.replace(ORIGINAL,original_guard_replacement(),1)+s[end:]
    require(new.count(DELEGATE)==before_count and
            new.count(METHOD_MARK)==1 and
            new.count("zrot_gr_main == 0 || zrot_gr_off == 0")==1 and
            new.count("p()->main_hand_weapon.type == WEAPON_NONE")==
            s.count("p()->main_hand_weapon.type == WEAPON_NONE") and
            new.count("p()->off_hand_weapon.type == WEAPON_NONE")==
            s.count("p()->off_hand_weapon.type == WEAPON_NONE"),
            "ORIGINAL_NECESSARY_GUARD_OR_DELEGATION_CHANGED")
    return new.encode("utf-8")

def patch(root:Path)->dict:
    root=root.resolve(strict=True)
    pins=verify_pristine(root)
    pfile=root/PLAYER_PATH
    wfile=root/WARRIOR_PATH
    p0=pfile.read_bytes();w0=wfile.read_bytes()
    require(git_blob(w0)==WARRIOR_BLOB,
            "ORIGINAL_WARRIOR_SOURCE_NOT_PRISTINE")
    require(PRE_MARK.encode() in p0 and POINTER_MARK.encode() not in p0,
            "GENERIC_SOURCE_PRE_PRODUCER_MISSING_OR_DUPLICATED")
    p1=extend_player_pointer(p0)
    w1=extend_warrior(w0)
    pfile.write_bytes(p1)
    wfile.write_bytes(w1)
    return {"schema":SCHEMA,"policy_id":POLICY,
            "source_revision":pins["official_source_sha"],
            "source_pins":pins["original_git_blobs"],
            "source_player_before_sha256":sha(p0),
            "source_player_after_sha256":sha(p1),
            "source_warrior_before_sha256":sha(w0),
            "source_warrior_after_sha256":sha(w1),
            "original_action_ready_call_count_unchanged":True,
            "original_weapon_slot_condition_preserved":True,
            "original_warrior_delegate_call_count_unchanged":True,
            "added_virtual_ready_calls":0,
            "semantic_requirement":"both_mainhand_and_offhand_slot_occupied",
            "source_ready_method":"rampage_parent_t::ready",
            "runtime_ready":"UNKNOWN",
            "same_seed_combat_parity":"NOT_YET_TESTED",
            "WCL_API_calls":0}

def selftest()->dict:
    fake=(START+"\n"+ORIGINAL+"\n"+END).encode()
    patched=extend_warrior(fake,check_pin=False).decode()
    require(patched.count(METHOD_MARK)==1 and
            patched.count(DELEGATE)==1 and
            patched.count("p()->main_hand_weapon.type == WEAPON_NONE")==1 and
            patched.count("p()->off_hand_weapon.type == WEAPON_NONE")==1,
            "SYNTHETIC_WARRIOR_SOURCE_PATCH_CHANGED_ORIGINAL_GUARD")
    try:extend_warrior(patched.encode(),check_pin=False)
    except WarriorGuardProducerError:pass
    else:raise AssertionError("DOUBLE_ORIGINAL_METHOD_PATCH_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":7,"spec_semantics_isolated_to_adapter":True,
            "generic_pointer_marker_reused":True,
            "original_native_CPP_executed":False,
            "independent_full_READY":0,"WCL_API_calls":0}

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source-root",type=Path)
    cli.add_argument("--out",type=Path)
    a=cli.parse_args()
    if a.source_root is None and a.out is None:
        print(json.dumps(selftest(),sort_keys=True));return
    if a.source_root is None or a.out is None:
        cli.error("source-root and out required")
    result=patch(a.source_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:
        f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    print("WARRIOR_EXACT_READY_SOURCE_GUARD_PATCH_SHA256="+sha(a.out.read_bytes()))

if __name__=="__main__":main()
