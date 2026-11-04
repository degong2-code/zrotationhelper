#!/usr/bin/env python3
"""Warrior-only semantic adapter: trace original virtual readiness routing.

SimC upstream pinned official warrior_action_t<Base> template:
ready() has replacement, qualified base, distance/range, and
channel/bladestorm checks. action_ready() may delegate to replacement
action or invoke the base action_ready(). Instrument exactly original
method calls; do not add buff->check, replacement ready, base ready or
action_ready invocations. Record first exiting source path and raw numeric
range state. No generic engine specialization semantics added.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from simc_apl_semantic_ir_v2 import git_blob,parse_profile
from simc_native_if_expression_instrument_v1 import PINNED_COMMIT,ACTION_CPP_BLOB
from simc_native_ready_guard_witness_instrument_v1 import PLAYER_CPP_BLOB,ACTION_CPP,PLAYER_CPP
from simc_native_target_eligibility_source_instrument_v1 import (
    verify_source as verify_target_source,
    patch_target,patch_player as extend_target_player
)
from simc_native_resource_cost_pre_instrument_v1 import patch as prior_patch
from simc_native_postguard_source_instrument_v1 import extend_action as patch_post_action,extend_player as patch_post_player

SCHEMA="ZrotWarriorOriginalCallReadyAndReplacementSourceV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
WARRIOR="engine/class_modules/sc_warrior.cpp"
WARRIOR_GIT_BLOB="38ee3dd0d5943eb9227ec55aefb21e7d47244f96"
READY_MARK="ZROT_WARRIOR_READY_PATH_PRE_V1|"
ACTION_MARK="ZROT_WARRIOR_ACTION_READY_PATH_PRE_V1|"
READY_START="  bool ready() override\n  {\n    if ( this->replacement_action )"
END="\n  void update_ready( timespan_t cd ) override"
REGION_START="struct warrior_action_t : public parse_action_effects_t<Base>"
REGION_END="struct warrior_attack_t : public warrior_action_t<melee_attack_t>"
class WarriorSourceError(ValueError):pass

def sha(blob:bytes):return hashlib.sha256(blob).hexdigest()

def patch_warrior(source:bytes)->bytes:
    s=source.decode()
    if s.count(REGION_START)!=1 or s.count(REGION_END)!=1 or READY_MARK in s or ACTION_MARK in s:
        raise WarriorSourceError("PINNED_WARRIOR_TEMPLATE_OR_ALREADY_PATCHED")
    start=s.index(REGION_START);end=s.index(REGION_END,start)
    chunk=s[start:end]
    if chunk.count(READY_START)!=1 or chunk.count(END)!=1:
        raise WarriorSourceError("TEMPLATE_READY_AND_ACTION_READY_UNIQUE_SOURCE_MISSING")
    beg=chunk.index(READY_START);last=chunk.index(END,beg)
    original=chunk[beg:last]
    for fragment in (
        "return this->replacement_action->ready();",
        "if ( !ab::ready() )",
        "if ( p()->current.distance_to_move > ab::range && ab::range != -1 )",
        "if ( ( p()->channeling || p()->buff.bladestorm->check() ) && !usable_while_channeling )",
        "if ( !this->replacement_action || this->cooldown->duration == 0_ms )",
        "return this->replacement_action->action_ready();",
        "return ab::action_ready();",
    ):
        if fragment not in original:raise WarriorSourceError("WARRIOR_METHOD_SOURCE_GUARD_CHANGED:"+fragment)
    marker_gate="if ( ab::sim->log && ab::player && !ab::player->is_pet() && !ab::player->is_enemy() )"
    def ready_log(stage:str,indent:str,channel:str,result:str)->str:
        return (
            indent+marker_gate+"\n"
            +indent+'  ab::sim->print_log( "'+READY_MARK+'{}|{}|'+stage+'|{:.17g}|{:.17g}|{}|{}|{}",\n'
            +indent+"    ab::sim->current_time().total_millis(), ab::name_str,\n"
            +indent+"    p()->current.distance_to_move, ab::range, "+channel+",\n"
            +indent+"    usable_while_channeling ? 1 : 0, "+result+" );\n"
        )
    def action_log(stage:str,indent:str)->str:
        return (
            indent+marker_gate+"\n"
            +indent+'  ab::sim->print_log( "'+ACTION_MARK+'{}|{}|'+stage+'|{}",\n'
            +indent+"    ab::sim->current_time().total_millis(), ab::name_str,\n"
            +indent+"    zrot_original_native_action_result ? 1 : 0 );\n"
        )
    new_ready=(
        "  bool ready() override\n  {\n"
        "    if ( this->replacement_action )\n"
        "    {\n"
        "      const bool zrot_use_replacement = this->always_replace ||\n"
        "        ( this->replacement_action_buff && this->replacement_action_buff->check() );\n"
        "      if ( zrot_use_replacement )\n"
        "      {\n"
        "        const bool zrot_original_native_ready_result = this->replacement_action->ready();\n"
        +ready_log("REPLACEMENT_DELEGATED","        ","-1","zrot_original_native_ready_result ? 1 : 0")
        +"        return zrot_original_native_ready_result;\n"
        "      }\n"
        "    }\n"
        "    if ( !ab::ready() )\n"
        "    {\n"
        +ready_log("QUALIFIED_BASE_READY_FALSE","      ","-1","0")
        +"      return false;\n"
        "    }\n"
        "    if ( p()->current.distance_to_move > ab::range && ab::range != -1 )\n"
        "    {\n"
        +ready_log("DISTANCE_TOO_FAR","      ","-1","0")
        +"      return false;\n"
        "    }\n"
        "    const bool zrot_original_channel_or_bladestorm =\n"
        "      p()->channeling || p()->buff.bladestorm->check();\n"
        "    if ( zrot_original_channel_or_bladestorm && !usable_while_channeling )\n"
        "    {\n"
        +ready_log("CHANNELING_NOT_USABLE","      ","zrot_original_channel_or_bladestorm ? 1 : 0","0")
        +"      return false;\n"
        "    }\n"
        +ready_log("QUALIFIED_BASE_AND_WARRIOR_READY_TRUE","    ","zrot_original_channel_or_bladestorm ? 1 : 0","1")
        +"    return true;\n"
        "  }\n\n"
    )
    new_action=(
        "  bool action_ready() override\n"
        "  {\n"
        "    if ( !this->replacement_action || this->cooldown->duration == 0_ms )\n"
        "    {\n"
        "      const bool zrot_original_native_action_result = ab::action_ready();\n"
        +action_log("NO_REPLACEMENT_OR_ZERO_DURATION","      ")
        +"      return zrot_original_native_action_result;\n"
        "    }\n"
        "    const bool zrot_use_replacement = this->always_replace ||\n"
        "      ( this->replacement_action_buff && this->replacement_action_buff->check() );\n"
        "    if ( zrot_use_replacement )\n"
        "    {\n"
        "      const bool zrot_original_native_action_result = this->replacement_action->action_ready();\n"
        +action_log("REPLACEMENT_DELEGATED","      ")
        +"      return zrot_original_native_action_result;\n"
        "    }\n"
        "    const bool zrot_original_native_action_result = ab::action_ready();\n"
        +action_log("REPLACEMENT_INACTIVE_QUALIFIED_BASE","    ")
        +"    return zrot_original_native_action_result;\n"
        "  }\n"
    )
    replacement=new_ready+new_action
    if original.count("this->replacement_action->ready()")!=1 or original.count("ab::ready()")!=1 or original.count("this->replacement_action->action_ready()")!=1 or original.count("ab::action_ready()")!=2:
        raise WarriorSourceError("ORIGINAL_CALL_COUNTER_DRIFT")
    if (replacement.count("this->replacement_action->ready()")!=1 or replacement.count("ab::ready()")!=1 or replacement.count("this->replacement_action->action_ready()")!=1 or replacement.count("ab::action_ready()")!=2 or replacement.count("buff.bladestorm->check()")!=1 or replacement.count("replacement_action_buff->check()")!=2):
        raise WarriorSourceError("INSTRUMENTED_CALL_COUNTER_DRIFT")
    final=s[:start]+chunk[:beg]+replacement+chunk[last:]+s[end:]
    if final.count(READY_MARK)!=4 or final.count(ACTION_MARK)!=3:
        raise WarriorSourceError("WARRIOR_SOURCE_PATH_RECEIPT_COUNT_INVALID")
    return final.encode()

def run(root:Path,profile:Path,expected_blob:str|None)->dict:
    root=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    if rev!=PINNED_COMMIT:raise WarriorSourceError("OFFICIAL_PINNED_SIMC_COMMIT_CHANGED")
    verify_target_source(root)
    warrior=root/WARRIOR
    raw_w=warrior.read_bytes()
    if git_blob(raw_w)!=WARRIOR_GIT_BLOB:
        raise WarriorSourceError("OFFICIAL_WARRIOR_CPP_GIT_BLOB_CHANGED")
    raw=profile.read_bytes()
    if not expected_blob or git_blob(raw)!=expected_blob:
        raise WarriorSourceError("PINNED_APL_PROFILE_BLOB_CHANGED")
    a=root/ACTION_CPP;p=root/PLAYER_CPP
    if git_blob(a.read_bytes())!=ACTION_CPP_BLOB or git_blob(p.read_bytes())!=PLAYER_CPP_BLOB:
        raise WarriorSourceError("ORIGINAL_ACTION_PLAYER_CPP_CHANGED")
    ir=parse_profile(raw,require_source=False)
    a0,p0=prior_patch(a.read_bytes(),p.read_bytes(),ir)
    a1=patch_target(patch_post_action(a0))
    p1=extend_target_player(patch_post_player(p0))
    w1=patch_warrior(raw_w)
    a.write_bytes(a1);p.write_bytes(p1);warrior.write_bytes(w1)
    return {
        "schema":SCHEMA,"product_policy":POLICY,
        "official_simc_commit":rev,"official_warrior_blob":WARRIOR_GIT_BLOB,
        "official_APL_profile_blob":git_blob(raw),
        "produced_action_sha256":sha(a1),"produced_player_sha256":sha(p1),
        "produced_warrior_sha256":sha(w1),
        "native_original_ready_calls_preserved":True,
        "native_original_action_ready_calls_preserved":True,
        "native_original_replacement_buff_checks_preserved":True,
        "actual_Native_nonperturbation":"NOT_YET_TESTED",
        "scope":"Warrior-only semantic adapter, generic engine unchanged",
        "full_independent_virtual_ready":False,"WCL_API_calls":0,
        "MAIN_promoted":False,
    }

def selftest():
    original=(
        REGION_START+"\n"
        +READY_START+"\n"
        "    {\n"
        "      if ( this->always_replace || ( this->replacement_action_buff && this->replacement_action_buff->check() ) )\n"
        "        return this->replacement_action->ready();\n"
        "    }\n"
        "    if ( !ab::ready() )\n"
        "      return false;\n"
        "    if ( p()->current.distance_to_move > ab::range && ab::range != -1 )\n"
        "      return false;\n"
        "    if ( ( p()->channeling || p()->buff.bladestorm->check() ) && !usable_while_channeling )\n"
        "      return false;\n"
        "    return true;\n"
        "  }\n"
        "  bool action_ready() override\n"
        "  {\n"
        "    if ( !this->replacement_action || this->cooldown->duration == 0_ms )\n"
        "      return ab::action_ready();\n"
        "    if ( this->always_replace || ( this->replacement_action_buff && this->replacement_action_buff->check() ) )\n"
        "      return this->replacement_action->action_ready();\n"
        "    return ab::action_ready();\n"
        "  }\n"
        +END+"\n{};\n"
        +REGION_END+"\n"
    ).encode()
    out=patch_warrior(original).decode()
    assert out.count(READY_MARK)==4 and out.count(ACTION_MARK)==3
    assert out.count("zrot_use_replacement")>=2
    assert out.count("ab::ready()")==1
    assert out.count("ab::action_ready()")==2
    assert out.count("buff.bladestorm->check()")==1
    assert out.count("this->replacement_action->ready()")==1
    assert out.count("this->replacement_action->action_ready()")==1
    for case in (out.encode(),original.replace(b"if ( !ab::ready() )",b"if ( ab::ready() )")):
        try:patch_warrior(case)
        except WarriorSourceError:pass
        else:raise AssertionError("WARRIOR_SOURCE_DUPLICATE_OR_DRIFT_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":12,
        "actual_SimC_CXX":"NOT_RUN","WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root and a.official_profile:
        r=run(a.simc_root,a.official_profile,a.expected_profile_git_blob)
    elif not a.simc_root and not a.official_profile:r=selftest()
    else:p.error("requires both --simc-root and --official-profile")
    raw=(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as f:f.write(raw)
    else:print(raw.decode(),end="")
if __name__=="__main__":main()
