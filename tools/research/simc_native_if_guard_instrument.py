#!/usr/bin/env python3
"""Pinned SimC original if_expr->success() source callsite reporter.

Two canonical action.cpp source sites only: action_t::action_ready and
call_action_list_t::action_ready. Logs exact original IF expression evaluation,
not a general READY or APL optimality claim. Runtime eval is NOT Strict PRE.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from simc_apl_pointer_instrument import UPSTREAM_SHA

FILE="engine/action/action.cpp"
HEADER="engine/sim/sim.hpp"
HEADER_COUNTER="  unsigned long long zrot_native_event_sequence = 0;"
NAMESPACE="namespace\n{  // anonymous namespace\n"
OLD="  if ( if_expr && !if_expr->success() )"
NEW="  if ( if_expr && !zrot_native_eval_if_guard( this ) )"
FUNCTION= r"""
// zRotationHelper: exact original IF expression delegate, source-research only.
// No new readiness check, no class/boss rules, and no time-based row guess.
bool zrot_native_eval_if_guard( action_t* action )
{
  auto* owner = action->player;
  if ( !owner->sim->log || owner->is_pet() || owner->is_enemy() )
    return action->if_expr->success();

  std::string apl_list = "unknown";
  unsigned ordinal = 0;
  if ( action->action_list && action->signature )
  {
    const auto& original_list = *action->action_list;
    for ( std::size_t idx = 0; idx < original_list.action_list.size(); ++idx )
    {
      if ( &( original_list.action_list[ idx ] ) == action->signature )
      {
        apl_list = original_list.name_str;
        ordinal = static_cast<unsigned>( idx + 1 );
        break;
      }
    }
  }

  owner->sim->print_log(
    "ZROT_NATIVE_APL_IF_GUARD_V1|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}",
    "BEGIN", owner->sim->thread_index, owner->sim->current_iteration,
    owner->sim->zrot_native_event_sequence++, owner->sim->current_time().total_millis(),
    owner->actor_index, owner->actor_spawn_index, apl_list,
    ordinal, action->id, -1 );

  // The original expression is evaluated EXACTLY ONCE. Its subexpression
  // hooks preserve actual nested evaluation order with the same source clock.
  const bool original_success = action->if_expr->success();

  owner->sim->print_log(
    "ZROT_NATIVE_APL_IF_GUARD_V1|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}",
    "END", owner->sim->thread_index, owner->sim->current_iteration,
    owner->sim->zrot_native_event_sequence++, owner->sim->current_time().total_millis(),
    owner->actor_index, owner->actor_spawn_index, apl_list,
    ordinal, action->id, static_cast<int>( original_success ) );
  return original_success;
}
"""


def patch(source: str, header: str) -> str:
    if header.count(HEADER_COUNTER)!=1:
        raise ValueError("IF_GUARD_COMMON_SOURCE_COUNTER_MISSING")
    if source.count(NAMESPACE)!=1 or source.count(OLD)!=2:
        raise ValueError("IF_GUARD_TWO_ORIGINAL_CALLSITES_REQUIRED")
    if "ZROT_NATIVE_APL_IF_GUARD_V1" in source or "zrot_native_eval_if_guard" in source:
        raise ValueError("IF_GUARD_SOURCE_ALREADY_PATCHED")
    new=source.replace(NAMESPACE,NAMESPACE+FUNCTION+"\n",1).replace(OLD,NEW)
    if new.count(NEW)!=2 or new.count("action->if_expr->success()")!=2:
        raise ValueError("IF_GUARD_ORIGINAL_DELEGATE_COUNT_INVALID")
    if new.count("const bool original_success = action->if_expr->success();")!=1:
        raise ValueError("IF_GUARD_DOUBLE_EVALUATION_RISK")
    if new.count("zrot_native_event_sequence++")!=2:
        raise ValueError("IF_GUARD_SOURCE_SEQUENCE_ANCHOR_INVALID")
    return new


def apply(root:Path)->dict:
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                      text=True,capture_output=True,check=True).stdout.strip()
    if rev!=UPSTREAM_SHA:
        raise ValueError("IF_GUARD_PINNED_UPSTREAM_MISMATCH")
    src=root/FILE
    raw=src.read_bytes()
    new=patch(raw.decode("utf-8"),(root/HEADER).read_text("utf-8")).encode("utf-8")
    src.write_bytes(new)
    return {"schema":"ZrotPinnedSimcDirectIfGuardReporterV1",
            "upstream_commit_sha":UPSTREAM_SHA,
            "source_file":FILE,
            "original_sha256":hashlib.sha256(raw).hexdigest(),
            "patched_sha256":hashlib.sha256(new).hexdigest(),
            "original_if_success_delegation_exactly_once":True,
            "guard_source_sites":["action_t::action_ready","call_action_list_t::action_ready"],
            "native_pointer_row_origin":True,
            "actual_guard_readiness_certified":False,
            "gameplay_rule_promotion":False}


def selftest():
    base=NAMESPACE+"void placeholder() {\n"+OLD+"\n}\n"+OLD+"\n"
    patched=patch(base,HEADER_COUNTER)
    assert patched.count("ZROT_NATIVE_APL_IF_GUARD_V1|")==2
    assert patched.count(NEW)==2
    assert "original_success = action->if_expr->success()" in patched
    assert patched.index("zrot_native_eval_if_guard( action_t*")<patched.index("void placeholder")
    for bad,h in [(patched,HEADER_COUNTER),(base.replace(OLD,"",1),HEADER_COUNTER),
                  (base+OLD,HEADER_COUNTER),(base,""),(base.replace(NAMESPACE,""),HEADER_COUNTER)]:
        try:patch(bad,h)
        except ValueError:pass
        else:raise AssertionError("IF_GUARD_UNPINNED_PATCH_ALLOWED")
    print("SIMC_NATIVE_IF_GUARD_SOURCE_SELF_TEST=PASS SYNTHETIC_ONLY")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--upstream-root",type=Path)
    args=parser.parse_args()
    if args.self_test or args.upstream_root is None:
        selftest()
    else:
        print(json.dumps(apply(args.upstream_root),sort_keys=True,indent=2))


if __name__=="__main__":
    main()
