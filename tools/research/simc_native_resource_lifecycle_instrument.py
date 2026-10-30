#!/usr/bin/env python3
"""Pinned official SimC native resource init/max lifecycle instrumentation.

Only attaches reporter-only marks AFTER player_t::init_resources() and
player_t::recalculate_resource_max() have completed their actual writes.
DO NOT instrument all 'resources.current[...] = ...': pool_resource::ready()
temporarily edits and restores resource to test eligibility, which is NOT a
persistent state transition. Source-specific pin and exact anchors guard
this small opt-in research executable, not a gameplay policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from simc_apl_pointer_instrument import UPSTREAM_SHA

FILE="engine/player/player.cpp"
MARKER="ZROT_NATIVE_RESOURCE_LIFECYCLE_V1"
_INIT_ANCHOR='''    else
      resources.current[ resource ] = max_resource;
  }

  // Only collect pet resource timelines if they get reported separately'''
_RECALC_ANCHOR='''  sim->print_debug( "Recalculated maximum {} for {}: old={:.2f}/{:.2f}, new={:.2f}/{:.2f}",'''
_INIT_TRACE='''    // zRotationHelper source-locked resource initialization observation.
    // INIT is a native EVENT-TIME value, not a prior-to-decision event.
    // Do not claim direct-write or class-specific resource completeness.
    if ( sim->log && !is_pet() && !is_enemy() &&
         resource != RESOURCE_NONE && resources.max[ resource ] > 0.0 )
    {
      sim->print_log( "ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|{}|{}|{}|{}|{:.17g}|{:.17g}|INIT",
                      sim->current_time().total_millis(), actor_index, actor_spawn_index,
                      util::resource_type_string( resource ),
                      resources.current[ resource ], resources.max[ resource ] );
    }
'''
_RECALC_TRACE='''  // Source-locked actual resource-max/current recalc function completion.
  // Any transient eligibility-only direct resource writes remain unobserved.
  if ( sim->log && !is_pet() && !is_enemy() &&
       resource_type != RESOURCE_NONE && resources.max[ resource_type ] > 0.0 )
  {
    sim->print_log( "ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|{}|{}|{}|{}|{:.17g}|{:.17g}|RECALC",
                    sim->current_time().total_millis(), actor_index, actor_spawn_index,
                    util::resource_type_string( resource_type ),
                    resources.current[ resource_type ], resources.max[ resource_type ] );
  }

'''


def patch_source(source:str)->str:
    if source.count(_INIT_ANCHOR)!=1 or source.count(_RECALC_ANCHOR)!=1:
        raise ValueError("LIFECYCLE_NATIVE_SOURCE_ANCHOR_MISMATCH")
    if MARKER in source:
        raise ValueError("LIFECYCLE_NATIVE_SOURCE_ALREADY_INSTRUMENTED")
    return (source.replace(_INIT_ANCHOR,
             _INIT_ANCHOR.replace('  }\n\n  // Only',_INIT_TRACE+'  }\n\n  // Only'))
            .replace(_RECALC_ANCHOR,_RECALC_TRACE+_RECALC_ANCHOR))


def audit_direct_write_site_scope(source:str)->dict:
    """Bounded inventory of player.cpp direct writes, NOT repository-wide proof."""
    sites=[]
    for m in re.finditer(
        r"resources\.(?:current|max|initial)\s*\[[^\]]+\]\s*(?:[+\-*/]?=|\+\+|--)",
        source):
        line=source.count("\n",0,m.start())+1
        window=source[max(0,m.start()-150):m.start()+180]
        sites.append({"line":line,
                      "assignment":source[m.start():].splitlines()[0].strip(),
                      "likely_pool_resource_trial":
                          ("player->resources.current[ resource ]" in window)})
    return {
        "scope":"PINNED_ENGINE_PLAYER_CPP_ONLY_NOT_ALL_CLASS_MODULES",
        "total_direct_assignment_sites":len(sites),
        "sites":sites,
        "completeness":"UNKNOWN_REPOSITORY_WIDE",
    }


def apply_tree(root:Path):
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       capture_output=True,text=True,check=True).stdout.strip()
    if rev!=UPSTREAM_SHA:raise ValueError("LIFECYCLE_UPSTREAM_COMMIT_MISMATCH")
    path=root/FILE
    before=path.read_bytes()
    after=patch_source(before.decode("utf-8")).encode("utf-8")
    path.write_bytes(after)
    return {
        "schema":"ZrotPinnedSimcResourceInitMaxSourceInstrumentationV1",
        "upstream_sha":UPSTREAM_SHA,
        "source_file":FILE,
        "pre_patch_sha256":hashlib.sha256(before).hexdigest(),
        "post_patch_sha256":hashlib.sha256(after).hexdigest(),
        "native_hook_sites":["player_t::init_resources",
                             "player_t::recalculate_resource_max"],
        "direct_write_inventory":audit_direct_write_site_scope(before.decode("utf-8")),
        "actor_scope":"NONPET_NONENEMY_ONLY",
        "claimed_full_resource_completeness":False,
        "temporary_pool_resource_writes_are_real_transitions":False,
        "actionable":False,
    }


def selftest():
    source=_INIT_ANCHOR+"\nvoid unrelated(){}\n"+_RECALC_ANCHOR+"\n"
    actual=patch_source(source)
    assert actual.count(MARKER)==2
    assert actual.count("INIT")>=1 and "RECALC" in actual
    assert actual.index("ZROT_NATIVE_RESOURCE_LIFECYCLE_V1")<actual.index(
        "Only collect pet resource timelines")
    assert "current_time().total_millis()" in actual
    assert audit_direct_write_site_scope(
        "player->resources.current[ resource ] -= extra;\n"
        "player->resources.current[ resource ] = current;\n")[
            "total_direct_assignment_sites"]==2
    for invalid in [actual,source.replace(_INIT_ANCHOR,""),
                    source.replace(_RECALC_ANCHOR,"")]:
        try:patch_source(invalid)
        except ValueError:pass
        else:raise AssertionError("UNPINNED_RESOURCE_HOOK_ACCEPTED")
    print("SIMC_NATIVE_RESOURCE_INIT_MAX_SOURCE_AUDIT_SELF_TEST=PASS")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream-root",type=Path)
    p.add_argument("--self-test",action="store_true")
    o=p.parse_args()
    if o.self_test or o.upstream_root is None:
        selftest();return
    print(json.dumps(apply_tree(o.upstream_root),indent=2,sort_keys=True))


if __name__=="__main__":
    main()
