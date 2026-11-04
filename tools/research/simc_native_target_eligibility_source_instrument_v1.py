#!/usr/bin/env python3
"""One-call, source-pinned Native base target_ready predicate evidence.

Instrument only the real action_t::target_ready original invocation and
the original player_t::select_action source PRE pointer scope. Each sleeping,
invulnerability and player-distance check executes AT MOST once in exactly
the original short-circuit order. The target readiness and source method
exit are for post-computation comparison, not independent inputs.
Custom target_ready, dynamic target_if/cycle/target_number remain UNKNOWN.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path
from simc_apl_semantic_ir_v2 import git_blob, parse_profile
from simc_native_if_expression_instrument_v1 import PINNED_COMMIT, ACTION_CPP_BLOB
from simc_native_ready_guard_witness_instrument_v1 import ACTION_CPP, PLAYER_CPP, PLAYER_CPP_BLOB
from simc_native_postguard_source_instrument_v1 import (
    run as base_run, verify_postguard_source, extend_action as patch_base_action,
    extend_player as patch_base_player
)
from simc_native_resource_cost_pre_instrument_v1 import patch as source_pre_patch

SCHEMA="ZrotNativeBaseTargetEligibilityOneCallSourcePreV1"
MARK="ZROT_NATIVE_BASE_TARGET_DECISION_V1|"
CFG="ZROT_NATIVE_TARGET_CONFIG_PRE_V1|"
SOURCE='''bool action_t::target_ready( player_t* candidate_target )
{
  // Ensure target is valid to execute on
  if ( candidate_target->is_sleeping() )
    return false;

  if ( candidate_target->debuffs.invulnerable &&
       candidate_target->debuffs.invulnerable->check() && harmful )
    return false;

  if ( sim->distance_targeting_enabled && range > 0 &&
       player->get_player_distance( *candidate_target ) > range + candidate_target->combat_reach )
    return false;

  return true;
}
'''
class TargetPatchError(ValueError): pass

def sha(raw:bytes):return hashlib.sha256(raw).hexdigest()

def patch_target(action:bytes)->bytes:
    text=action.decode()
    if text.count(SOURCE)!=1 or MARK in text:
        raise TargetPatchError("OFFICIAL_BASE_TARGET_READY_UNIQUE_SOURCE_CHANGED")
    # Original predicate call count is invariant; the first failure exits as
    # in upstream. Never compute additional target distances or invuln checks.
    replace='''bool action_t::target_ready( player_t* candidate_target )
{
  const int zrot_target_sleep = candidate_target->is_sleeping() ? 1 : 0;
  if ( zrot_target_sleep )
  {
    if ( sim->log && player && !player->is_pet() && !player->is_enemy() )
      sim->print_log( "'''+MARK+'''{}|{}|SLEEP|1|-1|-1|-1|{:.17g}|{:.17g}|-1",
        sim->current_time().total_millis(), name_str, range,
        candidate_target->combat_reach );
    return false;
  }

  const int zrot_target_invul =
    candidate_target->debuffs.invulnerable &&
    candidate_target->debuffs.invulnerable->check() && harmful ? 1 : 0;
  if ( zrot_target_invul )
  {
    if ( sim->log && player && !player->is_pet() && !player->is_enemy() )
      sim->print_log( "'''+MARK+'''{}|{}|INVULNERABLE|0|1|-1|-1|{:.17g}|{:.17g}|-1",
        sim->current_time().total_millis(), name_str, range,
        candidate_target->combat_reach );
    return false;
  }

  const int zrot_target_dist_enabled =
    sim->distance_targeting_enabled && range > 0 ? 1 : 0;
  double zrot_target_distance = -1.0;
  if ( zrot_target_dist_enabled )
  {
    zrot_target_distance = player->get_player_distance( *candidate_target );
    if ( zrot_target_distance > range + candidate_target->combat_reach )
    {
      if ( sim->log && player && !player->is_pet() && !player->is_enemy() )
        sim->print_log( "'''+MARK+'''{}|{}|RANGE|0|0|1|1|{:.17g}|{:.17g}|{:.17g}",
          sim->current_time().total_millis(), name_str, range,
          candidate_target->combat_reach, zrot_target_distance );
      return false;
    }
  }
  if ( sim->log && player && !player->is_pet() && !player->is_enemy() )
    sim->print_log( "'''+MARK+'''{}|{}|PASS|0|0|1|{}|{:.17g}|{:.17g}|{:.17g}",
      sim->current_time().total_millis(), name_str,
      zrot_target_dist_enabled, range, candidate_target->combat_reach,
      zrot_target_distance );
  return true;
}
'''
    out=text.replace(SOURCE,replace,1)
    if (out.count(MARK)!=4 or out.count("candidate_target->is_sleeping()")!=1 or
        out.count("candidate_target->debuffs.invulnerable->check()")!=1 or
        out.count("player->get_player_distance( *candidate_target )")!=1):
        raise TargetPatchError("ORIGINAL_BASE_TARGET_PREDICATE_CALL_COUNT_CHANGED")
    return out.encode()

def patch_player(base:bytes)->bytes:
    text=base.decode()
    end="""        zrot_last_same, zrot_last_foreground_execute_positive,
        a->player->executing == a ? 1 : 0 );"""
    if text.count(end)!=1 or CFG in text:
        raise TargetPatchError("SELECT_ACTION_PRE_TARGET_SCOPE_CHANGED")
    pre='''
      // Passive config: never call select_target()/target_ready() twice.
      sim->print_log( "'''+CFG+'''{}|{}|{}|{}|{}|{}|{}|{}|{}",
        sim->current_time().total_millis(), zrot_pre_owner,
        zrot_pre_ordinal, a->name_str,
        a->target_if_mode == TARGET_IF_NONE ? 1 : 0,
        a->option.cycle_targets ? 1 : 0,
        a->option.cycle_players ? 1 : 0,
        a->option.target_number,
        a->target ? 1 : 0 );'''
    out=text.replace(end,end+pre,1)
    if out.count(CFG)!=1 or out.index(CFG)>out.index("bool zrot_native_ready = a->action_ready();"):
        raise TargetPatchError("SOURCE_PRE_TARGET_CONFIG_NOT_BEFORE_NATIVE_CALL")
    return out.encode()

def verify_source(root:Path):
    prior=verify_postguard_source(root)
    source=(root/ACTION_CPP).read_bytes()
    if git_blob(source)!=ACTION_CPP_BLOB or source.decode().count(SOURCE)!=1:
        raise TargetPatchError("OFFICIAL_TARGET_PREDICATE_SOURCE_BLOB_CHANGED")
    return prior

def run(root:Path,profile:Path,expected_blob:str|None):
    root=root.resolve(strict=True)
    revision=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    if revision!=PINNED_COMMIT:raise TargetPatchError("SIMC_PINNED_SOURCE_REVISION_CHANGED")
    contract=verify_source(root)
    raw=profile.read_bytes()
    if not expected_blob or git_blob(raw)!=expected_blob:
        raise TargetPatchError("OFFICIAL_PROFILE_BLOB_CHANGED")
    a=root/ACTION_CPP;p=root/PLAYER_CPP
    if git_blob(p.read_bytes())!=PLAYER_CPP_BLOB:
        raise TargetPatchError("OFFICIAL_PLAYER_SELECT_SOURCE_CHANGED")
    ir=parse_profile(raw,require_source=False)
    base_a,base_p=source_pre_patch(a.read_bytes(),p.read_bytes(),ir)
    transformed_a=patch_target(patch_base_action(base_a))
    transformed_p=patch_player(patch_base_player(base_p))
    a.write_bytes(transformed_a);p.write_bytes(transformed_p)
    return {"schema":SCHEMA,"pinned_simc_commit":revision,
        "profile_git_blob":git_blob(raw),"source_contract":contract,
        "source_patched_action_sha256":sha(transformed_a),
        "source_patched_player_sha256":sha(transformed_p),
        "original_target_is_sleeping_checks":1,
        "original_invulnerability_checks":1,"original_get_player_distance_calls":1,
        "extra_select_target_or_action_ready_calls":0,
        "native_nonperturbation":"NOT_YET_TESTED",
        "source_target_method_return_for_comparison_only":True,
        "WCL_API_calls":0,"MAIN_promoted":False}

def selftest():
    action=patch_target(("BEFORE\n"+SOURCE+"AFTER\n").encode()).decode()
    assert action.count(MARK)==4
    assert action.count("candidate_target->is_sleeping()")==1
    assert action.count("debuffs.invulnerable->check()")==1
    assert action.count("player->get_player_distance( *candidate_target )")==1
    assert action.count("return false;")==3
    assert "zrot_target_distance > range + candidate_target->combat_reach" in action
    target_scope=("        zrot_last_same, zrot_last_foreground_execute_positive,\n"
                  "        a->player->executing == a ? 1 : 0 );\n"
                  "    bool zrot_native_ready = a->action_ready();")
    changed=patch_player(target_scope.encode()).decode()
    assert changed.count(CFG)==1
    assert changed.index(CFG)<changed.index("bool zrot_native_ready")
    assert changed.count("a->action_ready()")==1
    for fn,value in ((patch_target,action.encode()),(patch_player,changed.encode())):
        try:fn(value)
        except TargetPatchError:pass
        else:raise AssertionError("DOUBLE_TARGET_PATCH_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":11,
            "actual_Native_CXX_not_executed":True,"WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root and a.official_profile:
        r=run(a.simc_root,a.official_profile,a.expected_profile_git_blob)
    elif not a.simc_root and not a.official_profile:
        r=selftest()
    else:p.error("requires both source root and official profile")
    raw=(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as f:f.write(raw)
    else:print(raw.decode(),end="")
if __name__=="__main__":main()
