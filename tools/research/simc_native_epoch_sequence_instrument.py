#!/usr/bin/env python3
"""Source-pinned native event epoch + monotonic emission-order stamp (V2).

Run this AFTER existing V1 resource gain/loss, init/recalc, select-entry
reporters. Adds sim_t-owned strictly increasing source sequence and stamps
all four native source paths plus selection BEGIN/END in an adjacent
ZROT_NATIVE_EVENT_V2 marker. Preserves every previous V1 marker for existing
independent validators. Runtime order, not output line order, is the sequencer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from simc_apl_pointer_instrument import UPSTREAM_SHA

_PLAYER="engine/player/player.cpp"
_SIM="engine/sim/sim.hpp"
_FIELD_ANCHOR="  int current_iteration, iterations;"
_FIELD_EXTRA="  unsigned long long zrot_native_event_sequence = 0;"
_MARK="ZROT_NATIVE_EVENT_V2|"
_FORMAT=(
  'sim->print_log( "ZROT_NATIVE_EVENT_V2|{}|{}|{}|{}|{}|{}|{}|{}|{:.17g}|{:.17g}",'
)


def patch_sources(sources:dict[str,str])->dict[str,str]:
    if set(sources)!={_SIM,_PLAYER}:
        raise ValueError("EPOCH_SOURCE_FILE_SET_INVALID")
    h,p=sources[_SIM],sources[_PLAYER]
    if h.count(_FIELD_ANCHOR)!=1 or _FIELD_EXTRA in h:
        raise ValueError("EPOCH_SIM_HEADER_SOURCE_ANCHOR_INVALID")
    h=h.replace(_FIELD_ANCHOR,_FIELD_ANCHOR+"\n"+_FIELD_EXTRA)
    if _MARK in p:
        raise ValueError("EPOCH_PLAYER_ALREADY_INSTRUMENTED")
    # All six V1 print calls exist in player.cpp, source-pinned by previous
    # unique exact-match reporter patches. The captured call is kept intact.
    kinds=(
        ("GAIN", r'sim->print_log\( "ZROT_NATIVE_RESOURCE_V1\|[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*"GAIN" \);'),
        ("LOSS", r'sim->print_log\( "ZROT_NATIVE_RESOURCE_V1\|[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*"LOSS" \);'),
        ("INIT", r'sim->print_log\( "ZROT_NATIVE_RESOURCE_LIFECYCLE_V1\|[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*"INIT" \);'),
        ("RECALC", r'sim->print_log\( "ZROT_NATIVE_RESOURCE_LIFECYCLE_V1\|[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*"RECALC" \);'),
        ("SELECT_BEGIN", r'sim->print_log\( "ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1\|[^\n]*\n[^\n]*\);'),
        ("SELECT_END", r'sim->print_log\( "ZROT_NATIVE_SELECT_RESOURCE_END_V1\|[^\n]*\n[^\n]*\n[^\n]*\);'),
    )
    # Format: kind|thread|iteration|seq|time_ms|actor|spawn|resource|current|max.
    for kind,pattern in kinds:
        matches=list(re.finditer(pattern,p))
        if len(matches)!=1:
            raise ValueError("EPOCH_V1_"+kind+"_PRINT_ANCHOR_COUNT_"+str(len(matches)))
        m=matches[0]
        indentation=p[p.rfind("\n",0,m.start())+1:m.start()]
        if not indentation.isspace():
            raise ValueError("EPOCH_V1_INDENTATION_INVALID_"+kind)
        if kind in ("GAIN","LOSS"):
            resource="util::resource_type_string( resource_type )"
            current="resources.current[ resource_type ]"
            maximum="resources.max[ resource_type ]"
        elif kind=="INIT":
            resource="util::resource_type_string( resource )"
            current="resources.current[ resource ]"
            maximum="resources.max[ resource ]"
        elif kind=="RECALC":
            resource="util::resource_type_string( resource_type )"
            current="resources.current[ resource_type ]"
            maximum="resources.max[ resource_type ]"
        else:
            resource='"none"'
            current="0.0"
            maximum="0.0"
        marker=(
            indentation+_FORMAT+"\n"+
            indentation+"                \""+kind+"\", sim->thread_index, sim->current_iteration,\n"+
            indentation+"                sim->zrot_native_event_sequence++, sim->current_time().total_millis(),\n"+
            indentation+"                actor_index, actor_spawn_index, "+resource+",\n"+
            indentation+"                "+current+", "+maximum+" );\n"+
            indentation
        )
        p=p[:m.start()]+marker+p[m.start():]
    if p.count("ZROT_NATIVE_EVENT_V2|")!=6:
        raise ValueError("EPOCH_SOURCE_SIX_SITE_ASSERTION_FAILED")
    return {_SIM:h,_PLAYER:p}


def apply(root:Path)->dict:
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    if rev!=UPSTREAM_SHA:
        raise ValueError("EPOCH_UPSTREAM_SHA_MISMATCH")
    before={name:(root/name).read_text("utf-8") for name in (_SIM,_PLAYER)}
    after=patch_sources(before)
    hashes={}
    for name in (_SIM,_PLAYER):
        pre=before[name].encode()
        post=after[name].encode()
        (root/name).write_bytes(post)
        hashes[name]={"before_sha256":hashlib.sha256(pre).hexdigest(),
                      "after_sha256":hashlib.sha256(post).hexdigest()}
    return {
        "schema":"ZrotSimcNativeSourceEpochMonotonicStampV1",
        "upstream_commit_sha":UPSTREAM_SHA,
        "patched_file_receipts":hashes,
        "native_source_marker":"ZROT_NATIVE_EVENT_V2",
        "producer_sites":["GAIN","LOSS","INIT","RECALC","SELECT_BEGIN","SELECT_END"],
        "epoch_key":"SOURCE_LOG_SHA_THREAD_INDEX_CURRENT_ITERATION",
        "runtime_order":"sim_t_owned_monotonic_counter_at_emission",
        "v1_markers_retained":True,
        "does_not_prove_full_resource_completeness":True,
        "gameplay_rule_promotion":False,
    }


def selftest():
    fake={
        _SIM:"struct sim_t {\n"+_FIELD_ANCHOR+"\n};",
        _PLAYER:(
           '    sim->print_log( "ZROT_NATIVE_RESOURCE_V1|{}",\n'
           '                    alpha,\n'
           '                    beta,\n'
           '                    gamma, "GAIN" );\n'
           '    sim->print_log( "ZROT_NATIVE_RESOURCE_V1|{}",\n'
           '                    alpha,\n'
           '                    beta,\n'
           '                    gamma, "LOSS" );\n'
           '    sim->print_log( "ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|{}",\n'
           '                    alpha,\n'
           '                    beta,\n'
           '                    gamma, "INIT" );\n'
           '    sim->print_log( "ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|{}",\n'
           '                    alpha,\n'
           '                    beta,\n'
           '                    gamma, "RECALC" );\n'
           '    sim->print_log( "ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|{}",\n'
           '                    alpha );\n'
           '    sim->print_log( "ZROT_NATIVE_SELECT_RESOURCE_END_V1|{}",\n'
           '                    alpha, beta );\n'
        )
    }
    patched=patch_sources(fake)
    assert patched[_PLAYER].count(_MARK)==6
    assert patched[_PLAYER].count("sim->zrot_native_event_sequence++")==6
    assert _FIELD_EXTRA in patched[_SIM]
    assert patched[_PLAYER].count('ZROT_NATIVE_RESOURCE_V1|')==2
    assert patched[_PLAYER].count('ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|')==2
    for changed in [patched,{**fake,_PLAYER:fake[_PLAYER].replace('"GAIN"','"GONE"')},
                    {**fake,_SIM:fake[_SIM].replace(_FIELD_ANCHOR,"")}]:
        try:patch_sources(changed)
        except ValueError:pass
        else:raise AssertionError("EPOCH_SOURCE_INVALID_ACCEPTED")
    print("SIMC_NATIVE_MONOTONIC_EPOCH_SOURCE_STAMP_SELF_TEST=PASS")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream-root",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test or not args.upstream_root:
        selftest();return
    print(json.dumps(apply(args.upstream_root),indent=2,sort_keys=True))


if __name__=="__main__":
    main()
