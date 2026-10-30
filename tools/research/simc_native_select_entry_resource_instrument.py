#!/usr/bin/env python3
"""Source-pinned, read-only resource diagnostic AT actual select_action ENTRY.

Logs a BEGIN/resource/END group directly around the foreground select_action
invocation. The resource values are diagnostic evidence from the Native
execution, not state transitions. Never backdate them to strictly-before
decision time, infer readiness or alter SimC APL state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from simc_apl_pointer_instrument import UPSTREAM_SHA

FILE="engine/player/player.cpp"
_ANCHOR='''    action = select_action( *active_action_list, execute_type::FOREGROUND );
    zrot_foreground_selection_path = "SELECT_ACTION_FOREGROUND";'''
_REPLACEMENT='''    // zRotationHelper diagnostic snapshot at actual select_action entry.
    // The values are an audit reference, NEVER a time-<t state transition.
    if ( sim->log && !is_pet() && !is_enemy() )
    {
      sim->print_log( "ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|{}|{}|{}",
                      sim->current_time().total_millis(), actor_index, actor_spawn_index );
      for ( resource_e diagnostic_resource = RESOURCE_HEALTH;
            diagnostic_resource < RESOURCE_MAX; ++diagnostic_resource )
      {
        if ( resources.max[ diagnostic_resource ] > 0.0 )
        {
          sim->print_log( "ZROT_NATIVE_SELECT_RESOURCE_VALUE_V1|{}|{}|{}|{}|{:.17g}|{:.17g}",
                          sim->current_time().total_millis(), actor_index, actor_spawn_index,
                          util::resource_type_string( diagnostic_resource ),
                          resources.current[ diagnostic_resource ],
                          resources.max[ diagnostic_resource ] );
        }
      }
    }
    action = select_action( *active_action_list, execute_type::FOREGROUND );
    if ( sim->log && !is_pet() && !is_enemy() )
    {
      sim->print_log( "ZROT_NATIVE_SELECT_RESOURCE_END_V1|{}|{}|{}|{}",
                      sim->current_time().total_millis(), actor_index, actor_spawn_index,
                      action ? action->id : 0 );
    }
    zrot_foreground_selection_path = "SELECT_ACTION_FOREGROUND";'''


def patch_source(source:str)->str:
    if source.count(_ANCHOR)!=1:
        raise ValueError("SELECT_DIAG_UPSTREAM_ANCHOR_COUNT")
    if "ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1" in source:
        raise ValueError("SELECT_DIAG_SOURCE_ALREADY_INSTRUMENTED")
    return source.replace(_ANCHOR,_REPLACEMENT)


def apply_tree(root:Path)->dict:
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       check=True,capture_output=True,text=True).stdout.strip()
    if rev!=UPSTREAM_SHA:raise ValueError("SELECT_DIAG_UPSTREAM_SHA_MISMATCH")
    path=root/FILE
    before=path.read_bytes()
    after=patch_source(before.decode("utf-8")).encode("utf-8")
    path.write_bytes(after)
    return {
        "schema":"ZrotPinnedSimcSelectEntryResourceDiagnosticSourceV1",
        "upstream_sha":UPSTREAM_SHA,
        "source_file":FILE,
        "before_sha256":hashlib.sha256(before).hexdigest(),
        "after_sha256":hashlib.sha256(after).hexdigest(),
        "captured_at":"IMMEDIATELY_BEFORE_NATIVE_SELECT_ACTION",
        "trace_group":"BEGIN_RESOURCE_VALUES_END",
        "source_selection_code_modified":False,
        "diagnostic_snapshot_is_pre_transition":False,
        "native_action_readiness":"UNKNOWN",
        "gameplay_rule_promotion":False,
    }


def selftest():
    raw="prefix\n"+_ANCHOR+"\nsuffix"
    patched=patch_source(raw)
    assert patched.count("ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1")==1
    assert patched.count("ZROT_NATIVE_SELECT_RESOURCE_VALUE_V1")==1
    assert patched.count("ZROT_NATIVE_SELECT_RESOURCE_END_V1")==1
    assert patched.index("BEGIN_V1")<patched.index("action = select_action(")
    assert patched.index("action = select_action(")<patched.index("END_V1")
    for bad in [patched,raw.replace(_ANCHOR,""),raw+_ANCHOR]:
        try:patch_source(bad)
        except ValueError:pass
        else:raise AssertionError("BAD_SELECT_ENTRY_SOURCE_ACCEPTED")
    print("SIMC_NATIVE_SELECT_ENTRY_RESOURCE_DIAGNOSTIC_SOURCE_SELF_TEST=PASS")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upstream-root",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test or args.upstream_root is None:
        selftest();return
    print(json.dumps(apply_tree(args.upstream_root),sort_keys=True,indent=2))


if __name__=="__main__":
    main()
