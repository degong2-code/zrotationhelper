#!/usr/bin/env python3
"""Pin-source native sim_t::reset clock-epoch boundary stamping.

A current_iteration is NOT necessarily a complete elapsed-time epoch. This
separate SimC reporter emits a source-stamped reset boundary at the exact
sim_t::reset() call using the SAME sim_t monotonic counter as resource and
select_action events. Its timestamp is not a PRE state observation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from simc_apl_pointer_instrument import UPSTREAM_SHA
FILE="engine/sim/sim.cpp"
ANCHOR='''void sim_t::reset()
{
  print_debug( "Resetting Simulator" );'''
REPLACEMENT='''void sim_t::reset()
{
  // Source-generated clock epoch boundary. Counter is shared with all
  // ZROT_NATIVE_EVENT_V2 stamps. Never infer this from log text positions.
  if ( log )
  {
    print_log( "ZROT_NATIVE_RESET_BOUNDARY_V1|{}|{}|{}|{}",
               thread_index, current_iteration, zrot_native_event_sequence++,
               current_time().total_millis() );
  }
  print_debug( "Resetting Simulator" );'''

def patch_source(source:str)->str:
    if source.count(ANCHOR)!=1 or "ZROT_NATIVE_RESET_BOUNDARY_V1" in source:
        raise ValueError("NATIVE_RESET_SOURCE_ANCHOR_INVALID")
    return source.replace(ANCHOR,REPLACEMENT)

def patch_tree(root:Path)->dict:
    revision=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,text=True,capture_output=True).stdout.strip()
    if revision!=UPSTREAM_SHA:raise ValueError("NATIVE_RESET_UPSTREAM_SHA_MISMATCH")
    # The common source counter is created by the preceding event reporter.
    header=(root/"engine/sim/sim.hpp").read_text("utf-8")
    if header.count("unsigned long long zrot_native_event_sequence = 0;")!=1:
        raise ValueError("NATIVE_RESET_COMMON_SEQUENCE_NOT_INSTRUMENTED")
    path=root/FILE
    old=path.read_bytes()
    new=patch_source(old.decode()).encode()
    path.write_bytes(new)
    return {
        "schema":"ZrotNativeSimResetBoundaryInstrumentationV1",
        "upstream_commit_sha":UPSTREAM_SHA,
        "source_file":FILE,
        "before_sha256":hashlib.sha256(old).hexdigest(),
        "after_sha256":hashlib.sha256(new).hexdigest(),
        "marker":"ZROT_NATIVE_RESET_BOUNDARY_V1",
        "boundary_origin":"sim_t::reset_before_event_manager_reset",
        "counter_identity":"SHARED_SIM_T_OWNED_MONOTONIC_SOURCE_COUNTER",
        "gameplay_rule_promotion":False,
    }

def selftest():
    text="prefix\n"+ANCHOR+"\nsuffix"
    patched=patch_source(text)
    assert patched.count("ZROT_NATIVE_RESET_BOUNDARY_V1")==1
    assert patched.index("zrot_native_event_sequence++")<patched.index(
        'print_debug( "Resetting Simulator" );')
    for test in [patched,text.replace(ANCHOR,""),text+ANCHOR]:
        try:patch_source(test)
        except ValueError:pass
        else:raise AssertionError("UNPINNED_RESET_SOURCE_ACCEPTED")
    print("SIMC_NATIVE_RESET_BOUNDARY_SOURCE_SELF_TEST=PASS")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream-root",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test or not args.upstream_root:
        selftest();return
    print(json.dumps(patch_tree(args.upstream_root),sort_keys=True,indent=2))

if __name__=="__main__":
    main()
