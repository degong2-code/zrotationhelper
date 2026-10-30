#!/usr/bin/env python3
"""Pin-guarded native SimC resource gain/loss change-point trace instrumentation.

Appends a precise, machine-readable marker to the normal SimC log at the
native player_t::resource_gain/resource_loss MUTATION sites. Separate research
binary only, reporter-only; no changes to the state transition or APL logic.
This is intentionally PARTIAL resource producer coverage: base/initial/max
mutations and some direct resource writes are not traced, and target/range/
buff/cooldown mechanics remain UNKNOWN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from simc_apl_pointer_instrument import UPSTREAM_SHA

FILE="engine/player/player.cpp"
MARKER="ZROT_NATIVE_RESOURCE_V1"
_GAIN='''  if ( sim->log )
  {
    sim->print_log( "{} gains {:.2f} ({:.2f}) {} from {} ({:.2f}/{:.2f})",'''
_LOSS='''  if ( sim->debug )
    sim->print_debug( "Player {} loses {:.2f} ({:.2f}) {}. pct={:.2f}% ({:.2f}/{:.2f})",'''
_TRACE='''
  // zRotationHelper evidence-only resource trace, not a ready state.
  // Timestamp is the actual native event clock, not t-1 of an action.
  // This cannot prove initial/max or direct-write resource completeness.
  if ( sim->log && actual_amount > 0.0 && !is_pet() && !is_enemy() )
  {
    sim->print_log( "ZROT_NATIVE_RESOURCE_V1|{}|{}|{}|{}|{:.17g}|{:.17g}|{}",
                    sim->current_time().total_millis(), actor_index, actor_spawn_index,
                    util::resource_type_string( resource_type ),
                    resources.current[ resource_type ], actual_amount, "DIRECTION" );
  }
'''


def patch_player_source(source:str)->str:
    if source.count(_GAIN)!=1 or source.count(_LOSS)!=1:
        raise ValueError("RESOURCE_CHANGE_UPSTREAM_ANCHOR_MISMATCH")
    if MARKER in source:
        raise ValueError("RESOURCE_CHANGE_ALREADY_INSTRUMENTED")
    gain=_TRACE.replace("DIRECTION","GAIN")
    loss=_TRACE.replace("DIRECTION","LOSS")
    return source.replace(_GAIN,gain+"\n"+_GAIN).replace(_LOSS,loss+"\n"+_LOSS)


def apply_checked_tree(root:Path)->dict:
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],capture_output=True,
                       text=True,check=True).stdout.strip()
    if rev!=UPSTREAM_SHA:
        raise ValueError("RESOURCE_CHANGE_UPSTREAM_SHA_MISMATCH")
    path=root/FILE
    before=path.read_bytes()
    after=patch_player_source(before.decode("utf-8")).encode()
    path.write_bytes(after)
    return {
        "schema":"ZrotSimcNativeResourceMutationInstrumentationV1",
        "upstream_commit_sha":UPSTREAM_SHA,
        "source_path":FILE,
        "before_sha256":hashlib.sha256(before).hexdigest(),
        "after_sha256":hashlib.sha256(after).hexdigest(),
        "source_hooks":["player_t::resource_gain","player_t::resource_loss"],
        "timestamp_semantics":"NATIVE_EVENT_TIME_NOT_DECISION_PRE",
        "resource_state_completeness":"PARTIAL_NO_INITIAL_MAX_OR_DIRECT_WRITES",
        "retained_original_log":True,
        "gameplay_rule_promotion":False,
    }


def selftest():
    fixture=_GAIN+"\n...\n"+_LOSS+"\n"
    output=patch_player_source(fixture)
    assert output.count("ZROT_NATIVE_RESOURCE_V1")==2
    assert '"GAIN"' in output and '"LOSS"' in output
    assert "total_millis()" in output
    assert "{:.17g}" in output
    assert "actual_amount > 0.0" in output
    for invalid in [fixture.replace(_GAIN,""),fixture.replace(_LOSS,""),output]:
        try:patch_player_source(invalid)
        except ValueError:pass
        else:raise AssertionError("INVALID_PATCH_SOURCE_ACCEPTED")
    print("SIMC_NATIVE_RESOURCE_CHANGE_SOURCE_PATCH_SELF_TEST=PASS")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream-root",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test or args.upstream_root is None:
        selftest();return
    print(json.dumps(apply_checked_tree(args.upstream_root),indent=2,sort_keys=True))


if __name__=="__main__":
    main()
