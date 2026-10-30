#!/usr/bin/env python3
"""Opt-in pinned SimC sequence-add callsite instrumentation, research-only.

Trace the ORIGINAL method invocation category on an action sequence record,
rather than classify foreground by names, event timestamps or GCD length.
A foreground execute_action call may still arise from strict/queued options,
and specialized scheduled execution is not automatically optimal APL choice.
No action readiness, timestamps or simulation selection semantics are changed.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
from simc_apl_pointer_instrument import UPSTREAM_SHA, instrument_checked_tree

ORIGINS = (
    "PRECOMBAT_DIRECT",
    "FOREGROUND_EXECUTE_ACTION",
    "QUEUED_SPECIALIZED_EXECUTE",
    "VARIABLE_SIDE_EFFECT",
    "UNKNOWN_CALLSITE",
)
FILES = (
    "engine/player/player_collected_data.hpp",
    "engine/player/player.hpp",
    "engine/player/player.cpp",
    "engine/action/action.cpp",
    "engine/action/variable.cpp",
    "engine/report/json/report_json.cpp",
)


def replace_exact(source:str,old:str,new:str,count:int=1)->str:
    present=source.count(old)
    if present!=count:
        raise ValueError(f"SIMC_ORIGIN_ANCHOR_COUNT_EXPECT_{count}_ACTUAL_{present}")
    return source.replace(old,new)


def patch_callsite_sources(sources:dict[str,str])->dict[str,str]:
    if set(sources)!=set(FILES):
        raise ValueError("SIMC_ORIGIN_SOURCE_FILE_SET_MISMATCH")
    out=dict(sources)
    name="engine/player/player_collected_data.hpp"
    out[name]=replace_exact(out[name],
        "    bool queue_failed;\n",
        '    bool queue_failed;\n    std::string zrot_sequence_origin_callsite;\n')
    name="engine/player/player.hpp"
    out[name]=replace_exact(out[name],
        "  void sequence_add( const action_t* a, const player_t* target );",
        '  void sequence_add( const action_t* a, const player_t* target,\n'
        '                     const char* zrot_origin = "UNKNOWN_CALLSITE" );')
    name="engine/player/player.cpp"
    out[name]=replace_exact(out[name],
        "void player_t::sequence_add( const action_t* a, const player_t* t )",
        "void player_t::sequence_add( const action_t* a, const player_t* t, const char* zrot_origin )")
    out[name]=replace_exact(out[name],
        "        a->sequence_add_fn( data.action_reporting, data.target_reporting );",
        "        data.zrot_sequence_origin_callsite = zrot_origin;\n"
        "        a->sequence_add_fn( data.action_reporting, data.target_reporting );",
        count=2)
    # The two precombat sites are structurally distinct from combat execute.
    out[name]=replace_exact(out[name],
        "              sequence_add( action, action->target );",
        '              sequence_add( action, action->target, "PRECOMBAT_DIRECT" );')
    out[name]=replace_exact(out[name],
        "            sequence_add( action, action->target );",
        '            sequence_add( action, action->target, "PRECOMBAT_DIRECT" );')
    out[name]=replace_exact(out[name],
        "        sequence_add( action, action->target );",
        '        sequence_add( action, action->target, "FOREGROUND_EXECUTE_ACTION" );',
        count=1)
    name="engine/action/action.cpp"
    out[name]=replace_exact(out[name],
        "      action->player->sequence_add( action, action->target );",
        '      action->player->sequence_add( action, action->target, "QUEUED_SPECIALIZED_EXECUTE" );')
    name="engine/action/variable.cpp"
    out[name]=replace_exact(out[name],
        "    player->sequence_add( this, nullptr );",
        '    player->sequence_add( this, nullptr, "VARIABLE_SIDE_EFFECT" );')
    name="engine/report/json/report_json.cpp"
    out[name]=replace_exact(out[name],
        '      json[ "queue_failed" ] = entry.queue_failed;',
        '      json[ "queue_failed" ] = entry.queue_failed;\n'
        '      json[ "zrot_sequence_origin_callsite" ] = entry.zrot_sequence_origin_callsite;')
    return out


def extend_pinned_instrumented_tree(root:Path)->dict:
    result=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                          text=True,capture_output=True,check=True)
    if result.stdout.strip()!=UPSTREAM_SHA:
        raise ValueError("SIMC_ORIGIN_UPSTREAM_SHA_MISMATCH")
    # Caller must first apply the existing pointer serializer instrument.
    src={file:(root/file).read_text(encoding="utf-8") for file in FILES}
    if src["engine/report/json/report_json.cpp"].count("zrot_apl_object_ordinal")!=1:
        raise ValueError("SIMC_ORIGIN_POINTER_INSTRUMENT_REQUIRED")
    patched=patch_callsite_sources(src)
    receipts={}
    for file in FILES:
        raw=src[file].encode("utf-8")
        new=patched[file].encode("utf-8")
        (root/file).write_bytes(new)
        receipts[file]={
            "before_sha256":hashlib.sha256(raw).hexdigest(),
            "after_sha256":hashlib.sha256(new).hexdigest(),
        }
    return {
        "schema":"ZrotPinnedSimcActionSequenceCallsiteInstrumentationV1",
        "source_upstream_sha256":UPSTREAM_SHA,
        "patched_file_receipts":receipts,
        "callsite_labels":list(ORIGINS),
        "asserted_provenance_not_inferred_from_timestamps":True,
        "native_action_selection_unchanged":True,
        "simulation_binary":"MUST_COMPILE_AND_VERIFY",
        "strict_pre":"NOT_RUN",
        "gameplay_promotion":False,
    }


def selftest():
    files={
        "engine/player/player_collected_data.hpp":"    bool queue_failed;\n",
        "engine/player/player.hpp":"  void sequence_add( const action_t* a, const player_t* target );\n",
        "engine/player/player.cpp":(
            "void player_t::sequence_add( const action_t* a, const player_t* t )\n"
            "        a->sequence_add_fn( data.action_reporting, data.target_reporting );\n"
            "        a->sequence_add_fn( data.action_reporting, data.target_reporting );\n"
            "            sequence_add( action, action->target );\n"
            "            sequence_add( action, action->target );\n"
            "        sequence_add( action, action->target );\n"
        ),
        "engine/action/action.cpp":"      action->player->sequence_add( action, action->target );\n",
        "engine/action/variable.cpp":"    player->sequence_add( this, nullptr );\n",
        "engine/report/json/report_json.cpp":
            '      json[ "queue_failed" ] = entry.queue_failed;\n'
            '      json[ "zrot_apl_object_ordinal" ] = 1;\n',
    }
    updated=patch_callsite_sources(files)
    assert updated["engine/player/player.cpp"].count('"PRECOMBAT_DIRECT"')==2
    assert updated["engine/player/player.cpp"].count('"FOREGROUND_EXECUTE_ACTION"')==1
    assert updated["engine/player/player.cpp"].count("data.zrot_sequence_origin_callsite") == 2
    assert all(updated[f]!=files[f] for f in FILES)
    try:patch_callsite_sources(updated)
    except ValueError as e:assert str(e).startswith("SIMC_ORIGIN_ANCHOR_COUNT")
    else:raise AssertionError("DOUBLE_ORIGIN_INSTRUMENT_ACCEPTED")
    print("SIMC_NATIVE_SEQUENCE_CALLSITE_INSTRUMENT_SELF_TEST=PASS")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream-root",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test or not a.upstream_root:
        selftest()
        return
    import json
    print(json.dumps(extend_pinned_instrumented_tree(a.upstream_root),
                     sort_keys=True,indent=2))


if __name__=="__main__":
    main()
