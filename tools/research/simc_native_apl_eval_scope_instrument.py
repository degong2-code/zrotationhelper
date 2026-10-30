#!/usr/bin/env python3
"""Pinned, research-only SimC per-attempt APL pointer scope instrumentation.

Appends a source-sequenced BEGIN/END envelope to each relevant action attempt
in player_t::select_action, covering FOREGROUND/OFF_GCD/CAST_WHILE_CASTING and
variable_t::execute. This DOES NOT prove an eval belongs to the APL if guard.
Original readiness, call list recursion, priority and actions are unchanged.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from simc_apl_pointer_instrument import UPSTREAM_SHA

FILE="engine/player/player.cpp"
HEADER="engine/sim/sim.hpp"
COMMON_COUNTER="  unsigned long long zrot_native_event_sequence = 0;"
ANCHOR="    if ( a->action_ready() )"
SELECT_FUNCTION="action_t* player_t::select_action( const action_priority_list_t& list,"
MARK="ZROT_NATIVE_APL_EVAL_SCOPE_V1|"
STRUCT= r"""  // zRotationHelper read-only scope of the actual attempted APL action object.
  // Source-row identity comes only from native pointer equality, NOT token/name.
  struct zrot_apl_attempt_scope_t
  {
    player_t* p;
    action_t* a;
    execute_type mode;
    bool recorded = false;
    std::string owner_list = "unknown";
    unsigned owner_ordinal = 0;
    const char* context = "IF_ACTION_ATTEMPT";

    zrot_apl_attempt_scope_t( player_t* player, action_t* action, execute_type execute )
      : p( player ), a( action ), mode( execute )
    {
      if ( !p->sim->log || p->is_pet() || p->is_enemy() ||
           !( a->if_expr || a->type == ACTION_VARIABLE ) )
        return;
      context = a->type == ACTION_VARIABLE ? "VARIABLE_ACTION_ATTEMPT" : "IF_ACTION_ATTEMPT";
      if ( a->action_list && a->signature )
      {
        const auto& apl = *a->action_list;
        for ( std::size_t idx = 0; idx < apl.action_list.size(); ++idx )
        {
          if ( &( apl.action_list[ idx ] ) == a->signature )
          {
            owner_list = apl.name_str;
            owner_ordinal = static_cast<unsigned>( idx + 1 );
            break;
          }
        }
      }
      recorded = true;
      emit( "BEGIN" );
    }

    void emit( const char* kind ) const
    {
      const char* mode_str = mode == execute_type::OFF_GCD ? "OFF_GCD" :
                             mode == execute_type::CAST_WHILE_CASTING ? "CAST_WHILE_CASTING" :
                             "FOREGROUND";
      p->sim->print_log(
        "ZROT_NATIVE_APL_EVAL_SCOPE_V1|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}",
        kind, p->sim->thread_index, p->sim->current_iteration,
        p->sim->zrot_native_event_sequence++, p->sim->current_time().total_millis(),
        p->actor_index, p->actor_spawn_index, mode_str, owner_list,
        owner_ordinal, a->id, context );
    }

    ~zrot_apl_attempt_scope_t()
    {
      if ( recorded )
        emit( "END" );
    }
  };
"""


def patch(source:str,header:str)->str:
    if header.count(COMMON_COUNTER)!=1:
        raise ValueError("APL_SCOPE_SHARED_NATIVE_SOURCE_COUNTER_MISSING")
    if source.count(SELECT_FUNCTION)!=1 or source.count(ANCHOR)!=1:
        raise ValueError("APL_SCOPE_PINNED_SELECT_ANCHOR_INVALID")
    if MARK in source:
        raise ValueError("APL_SCOPE_ALREADY_INSTRUMENTED")
    start=source.index(SELECT_FUNCTION)
    body=source.index("{",start)
    if source.index(ANCHOR)<=body or source.index(ANCHOR)-body>3500:
        raise ValueError("APL_SCOPE_ACTION_READY_OUTSIDE_SELECT_BODY")
    # One scope lifetime spans action_ready and variable execute, including
    # recursive call_action_list frames, with destructor on continue/return.
    new=source[:body+1]+"\n"+STRUCT+source[body+1:]
    new=new.replace(ANCHOR,"    zrot_apl_attempt_scope_t zrot_apl_scope( this, a, et );\n"+ANCHOR)
    if (new.count(MARK)!=1 or
        new.count("zrot_apl_attempt_scope_t zrot_apl_scope( this, a, et );")!=1 or
        new.count("p->sim->zrot_native_event_sequence++")!=1 or
        new.count("owner_ordinal = static_cast<unsigned>( idx + 1 )")!=1 or
        new.count("a->execute();")<1):
        raise ValueError("APL_SCOPE_DELEGATION_OR_ROW_PROVENANCE_NOT_PRESERVED")
    return new


def apply(root:Path)->dict:
    ref=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       text=True,check=True,capture_output=True).stdout.strip()
    if ref!=UPSTREAM_SHA:
        raise ValueError("APL_SCOPE_PINNED_SIMC_UPSTREAM_MISMATCH")
    f=root/FILE
    before=f.read_bytes()
    after=patch(before.decode("utf-8-sig"),(root/HEADER).read_text("utf-8")).encode("utf-8-sig")
    f.write_bytes(after)
    return {"schema":"ZrotNativeSourceAplAttemptScopeV1",
            "simc_upstream_sha":UPSTREAM_SHA,
            "source_file":FILE,
            "old_sha256":hashlib.sha256(before).hexdigest(),
            "new_sha256":hashlib.sha256(after).hexdigest(),
            "marker":"ZROT_NATIVE_APL_EVAL_SCOPE_V1",
            "owner_provenance":"NATIVE_SIGNATURE_POINTER_EQUALITY",
            "guard_expression_direct_owner":"NOT_ASSERTED",
            "same_epoch_source_sequence":True,
            "offgcd_action_attempt_scope":True,
            "variable_action_execute_inside_scope":True,
            "readiness":"UNKNOWN",
            "gameplay_rule_promotion":False}


def selftest():
    fake=(SELECT_FUNCTION+" x, execute_type et )\n{\n"
          "  for ( action_t* a : a_list )\n  {\n"
          +ANCHOR+"\n    {\n       a->execute();\n    }\n  }\n}\n")
    fake=fake.replace(" ) x,", " x,") # no semantic impact, fixture only
    source=patch(fake,COMMON_COUNTER)
    assert source.count(MARK)==1
    assert source.index("zrot_apl_attempt_scope_t zrot_apl_scope") < source.index(ANCHOR)
    assert "a->signature" in source and "apl.action_list[ idx ]" in source
    assert "VARIABLE_ACTION_ATTEMPT" in source and "OFF_GCD" in source
    assert source.index("a->execute();")>source.index(ANCHOR)
    for bad,h in [(source,COMMON_COUNTER),(fake.replace(ANCHOR,""),COMMON_COUNTER),
                  (fake+ANCHOR,COMMON_COUNTER),(fake,"")]:
        try:patch(bad,h)
        except ValueError:pass
        else:raise AssertionError("APL_SCOPE_BAD_SOURCE_ACCEPTED")
    print("SIMC_NATIVE_APL_EVAL_SCOPE_SOURCE_SELF_TEST=PASS SYNTHETIC_ONLY")


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
