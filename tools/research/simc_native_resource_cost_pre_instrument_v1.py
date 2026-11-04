#!/usr/bin/env python3
"""Source-bounded numeric resource affordability PRE evidence for SimC.

Observe only existing virtual method executions: action_t::cost_affordable()
captures the SAME cost() that the original method passes to the player;
player_t::resource_available() captures current resource and is_infinite
inside its own base method. No second cost() or resource_available() calls
are added. Subclass override paths lacking BOTH base method markers remain
UNKNOWN. The previous source guard recorder still calls cost_affordable()
once before original action_ready(), and the original ready runs once.
Source provenance, temporal ordering, original-vs-instrumented action
sequence and strict no false positive gate apply.

This does NOT prove ability ready, class-specific resource calculations or
action priority, and never introduces raid encounter plans or NSRT.
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
from simc_native_cooldown_tolerance_pre_instrument_v1 import (
    verify_tolerance_source,
    extend_player as extend_tolerance,
)
from simc_native_cooldown_queue_clock_instrument_v1 import (
    patch_originals as base_patch_originals,
)
from simc_native_if_talent_pre_instrument_v1 import talent_inventory
from simc_native_if_buff_pre_instrument_v1 import buff_inventory
from simc_native_if_action_gcd_cd_pre_instrument_v1 import source_inventory
from simc_native_if_movement_event_pre_instrument_v1 import inventory

SCHEMA = "ZrotNativeActualBaseResourceCostPreSourceV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
ACTION_MARK = "ZROT_NATIVE_BASE_COST_PRE_V1|"
PLAYER_MARK = "ZROT_NATIVE_BASE_RESOURCE_PRE_V1|"

ACTION_SOURCE = (
    "bool action_t::cost_affordable()\n"
    "{\n"
    "  auto resource = current_resource();\n"
    "  return resource == RESOURCE_NONE || player->resource_available( resource, cost() );\n"
    "}\n"
)
PLAYER_SOURCE = (
    "bool player_t::resource_available( resource_e resource_type, double cost ) const\n"
    "{\n"
    "  if ( resource_type == RESOURCE_NONE || cost <= 0 || resources.is_infinite( resource_type ) )"
)
class ResourcePreError(ValueError):
    pass


def sha(blob:bytes)->str:
    return hashlib.sha256(blob).hexdigest()


def verify_resource_source(root:Path)->dict:
    prior=verify_tolerance_source(root)
    action=(root/ACTION_CPP).read_bytes()
    player=(root/PLAYER_CPP).read_bytes()
    if git_blob(action)!=ACTION_CPP_BLOB or git_blob(player)!=PLAYER_CPP_BLOB:
        raise ResourcePreError("ORIGINAL_RESOURCE_SOURCE_BLOB_NOT_PINNED")
    a=action.decode()
    p=player.decode()
    if a.count(ACTION_SOURCE)!=1 or p.count(PLAYER_SOURCE)!=1:
        raise ResourcePreError("OFFICIAL_RESOURCE_METHOD_BODY_DRIFT")
    for snippet in (
        "bool available = resources.current[ resource_type ] >= cost;",
        "if ( resource_type == RESOURCE_NONE || cost <= 0 || resources.is_infinite( resource_type ) )",
    ):
        if p.count(snippet)!=1:
            raise ResourcePreError("BASE_RESOURCE_COMPARISON_DRIFT")
    return {
        "prior_source":prior,
        "official_action_cpp_git_blob_sha1":ACTION_CPP_BLOB,
        "official_player_cpp_git_blob_sha1":PLAYER_CPP_BLOB,
        "base_cost_source":"current_resource(); NONE || player.resource_available(resource,cost())",
        "base_resource_available_source":
            "RESOURCE_NONE || cost<=0 || resource_is_infinite || resource_current>=cost",
        "cost_method_executed_once_inside_original_base_cost_method":True,
        "player_base_resource_method_may_be_overridden":True,
        "action_base_cost_method_may_be_overridden":True,
    }


def extend_action(text:str)->str:
    if text.count(ACTION_SOURCE)!=1 or ACTION_MARK in text:
        raise ResourcePreError("BASE_COST_METHOD_SOURCE_CHANGED_OR_ALREADY_PATCHED")
    replacement=(
        "bool action_t::cost_affordable()\n"
        "{\n"
        "  auto resource = current_resource();\n"
        "  if ( resource == RESOURCE_NONE )\n"
        "  {\n"
        "    if ( sim->log && player && !player->is_pet() && !player->is_enemy() )\n"
        '      sim->print_log( "'+ACTION_MARK+'{}|{}|{}|{:.17g}",\n'
        "        sim->current_time().total_millis(), name_str,\n"
        "        static_cast<int>( resource ), 0.0 );\n"
        "    return true;\n"
        "  }\n"
        "  const double zrot_original_cost_once = cost();\n"
        "  if ( sim->log && player && !player->is_pet() && !player->is_enemy() )\n"
        '    sim->print_log( "'+ACTION_MARK+'{}|{}|{}|{:.17g}",\n'
        "      sim->current_time().total_millis(), name_str,\n"
        "      static_cast<int>( resource ), zrot_original_cost_once );\n"
        "  return player->resource_available( resource, zrot_original_cost_once );\n"
        "}\n"
    )
    out=text.replace(ACTION_SOURCE,replacement,1)
    if (out.count("zrot_original_cost_once = cost();")!=1 or
        out.count("player->resource_available( resource, zrot_original_cost_once );")!=1 or
        out.count(ACTION_MARK)!=2):
        raise ResourcePreError("ORIGINAL_BASE_COST_CALL_MULTIPLICITY_CHANGED")
    return out


def extend_player(text:str)->str:
    if text.count(PLAYER_SOURCE)!=1 or PLAYER_MARK in text:
        raise ResourcePreError("BASE_RESOURCE_METHOD_SOURCE_CHANGED_OR_ALREADY_PATCHED")
    snippet=(
        "bool player_t::resource_available( resource_e resource_type, double cost ) const\n"
        "{\n"
        "  // Source facts read by base method on its ORIGINAL invocation.\n"
        "  if ( sim->log && !is_pet() && !is_enemy() )\n"
        "  {\n"
        "    const double zrot_resource_current = resource_type == RESOURCE_NONE ?\n"
        "      0.0 : resources.current[ resource_type ];\n"
        "    const int zrot_resource_infinite = resource_type == RESOURCE_NONE ?\n"
        "      0 : ( resources.is_infinite( resource_type ) ? 1 : 0 );\n"
        '    sim->print_log( "'+PLAYER_MARK+'{}|{}|{:.17g}|{:.17g}|{}",\n'
        "      sim->current_time().total_millis(), static_cast<int>( resource_type ),\n"
        "      cost, zrot_resource_current, zrot_resource_infinite );\n"
        "  }\n"
        "  if ( resource_type == RESOURCE_NONE || cost <= 0 || resources.is_infinite( resource_type ) )"
    )
    out=text.replace(PLAYER_SOURCE,snippet,1)
    if out.count(PLAYER_MARK)!=1 or out.count("bool player_t::resource_available(")!=1:
        raise ResourcePreError("BASE_RESOURCE_METHOD_COUNT_CHANGED")
    return out


def patch(original_action:bytes,original_player:bytes,ir:dict):
    a,p=base_patch_originals(
        original_action,original_player,
        talent_inventory(ir),buff_inventory(ir),
        source_inventory(ir),inventory(ir))
    p=extend_tolerance(p)
    return extend_action(a.decode()).encode(),extend_player(p.decode()).encode()


def run(root:Path,profile:Path,expected_blob:str|None)->dict:
    root=root.resolve(strict=True)
    revision=subprocess.run(
        ["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    if revision!=PINNED_COMMIT:
        raise ResourcePreError("PINNED_UPSTREAM_COMMIT_CHANGED")
    semantic=verify_resource_source(root)
    raw=profile.read_bytes()
    if not expected_blob or git_blob(raw)!=expected_blob:
        raise ResourcePreError("OFFICIAL_PROFILE_IDENTITY_CHANGED")
    ir=parse_profile(raw,require_source=False)
    a=root/ACTION_CPP;p=root/PLAYER_CPP
    a2,p2=patch(a.read_bytes(),p.read_bytes(),ir)
    # All contract and syntactic source checks before first write.
    a.write_bytes(a2)
    p.write_bytes(p2)
    return {
        "schema":SCHEMA,
        "policy_id":POLICY,
        "official_source_commit":revision,
        "official_profile_git_blob_sha1":git_blob(raw),
        "source_contract":semantic,
        "modified_action_cpp_sha256":sha(a2),
        "modified_player_cpp_sha256":sha(p2),
        "extra_cost_calls_from_instrumentation":0,
        "extra_resource_available_calls_from_instrumentation":0,
        "original_action_ready_calls":1,
        "subclass_overrides_stay_UNKNOWN_if_unentered":True,
        "native_nonperturbation":"NOT_YET_PROVEN",
        "full_action_ready_reproduced":False,
        "WCL_API_calls":0,
        "MAIN_promoted":False,
    }


def selftest():
    from simc_native_if_pre_operand_replay_v1 import PINNED_FURY_BLOB
    a=extend_action("HEAD\n"+ACTION_SOURCE+"\nTAIL")
    assert a.count(ACTION_MARK)==2
    assert a.count("zrot_original_cost_once = cost();")==1
    assert a.count("return player->resource_available( resource, zrot_original_cost_once );")==1
    assert "resource == RESOURCE_NONE" in a
    p=extend_player("HEAD\n"+PLAYER_SOURCE+"\nTAIL")
    assert p.count(PLAYER_MARK)==1
    assert p.count("resources.current[ resource_type ]")>=1
    assert p.count("resources.is_infinite( resource_type )")>=2
    for fn,s in [(extend_action,a),(extend_player,p)]:
        try:fn(s)
        except ResourcePreError:pass
        else:raise AssertionError("DOUBLE_INSTRUMENTATION_ACCEPTED")
    assert PINNED_FURY_BLOB
    return {
        "status":"PASS_OFFLINE_SYNTHETIC","checks":9,
        "CXX_actual_compile":"NOT_RUN","WCL_API_calls":0,
        "full_readiness":False,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simc-root",type=Path)
    parser.add_argument("--official-profile",type=Path)
    parser.add_argument("--expected-profile-git-blob")
    parser.add_argument("--receipt",type=Path)
    args=parser.parse_args()
    if args.simc_root and args.official_profile:
        data=run(args.simc_root,args.official_profile,args.expected_profile_git_blob)
    elif not args.simc_root and not args.official_profile:
        data=selftest()
    else:
        parser.error("both root and official profile required")
    raw=(json.dumps(data,sort_keys=True,separators=(",",":"))+"\n").encode()
    if args.receipt:
        args.receipt.parent.mkdir(parents=True,exist_ok=True)
        with args.receipt.open("xb") as f:f.write(raw)
    else:print(raw.decode(),end="")


if __name__=="__main__":
    main()
