#!/usr/bin/env python3
"""Pin-guarded, reporter-only native foreground selection-branch provenance.

Runs AFTER the existing pointer and sequence callsite instrumentation. Records
the actual branch taken inside player_t::execute_action() for sampled actions:
SELECT_ACTION_FOREGROUND, STRICT_SEQUENCE, SPELL_QUEUED_ACTION. This proves
native dispatch *path*, not eligibility/readiness or priority equivalence.
Every string comes from the actual C++ execution path, never name/time.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from simc_apl_pointer_instrument import UPSTREAM_SHA
from simc_apl_selection_callsite_instrument import replace_exact

FILES=(
    "engine/player/player.cpp",
    "engine/player/player.hpp",
    "engine/player/player_collected_data.hpp",
    "engine/report/json/report_json.cpp",
)
VALID_PATHS=(
    "SELECT_ACTION_FOREGROUND",
    "STRICT_SEQUENCE",
    "SPELL_QUEUED_ACTION",
    "NOT_APPLICABLE",
    "UNKNOWN_FOREGROUND_BRANCH",
)


def patch_selection_sources(sources:dict[str,str])->dict[str,str]:
    if set(sources)!=set(FILES):
        raise ValueError("FOREGROUND_SELECTION_SOURCE_FILES_REQUIRED")
    out=dict(sources)
    name="engine/player/player_collected_data.hpp"
    out[name]=replace_exact(out[name],
        "    std::string zrot_sequence_origin_callsite;\n",
        "    std::string zrot_sequence_origin_callsite;\n"
        "    std::string zrot_foreground_selection_path;\n")
    name="engine/player/player.hpp"
    out[name]=replace_exact(out[name],
        '                     const char* zrot_origin = "UNKNOWN_CALLSITE" );',
        '                     const char* zrot_origin = "UNKNOWN_CALLSITE",\n'
        '                     const char* zrot_selection_path = "NOT_APPLICABLE" );')
    name="engine/player/player.cpp"
    out[name]=replace_exact(out[name],
        "void player_t::sequence_add( const action_t* a, const player_t* t, const char* zrot_origin )",
        "void player_t::sequence_add( const action_t* a, const player_t* t,\n"
        "                             const char* zrot_origin, const char* zrot_selection_path )")
    out[name]=replace_exact(out[name],
        "        data.zrot_sequence_origin_callsite = zrot_origin;\n",
        "        data.zrot_sequence_origin_callsite = zrot_origin;\n"
        "        data.zrot_foreground_selection_path = zrot_selection_path;\n",
        count=2)
    out[name]=replace_exact(out[name],
        "action_t* player_t::execute_action()\n{\n  assert( !readying );\n\n  action_t* action = nullptr;",
        "action_t* player_t::execute_action()\n{\n  assert( !readying );\n\n"
        "  action_t* action = nullptr;\n"
        '  const char* zrot_foreground_selection_path = "UNKNOWN_FOREGROUND_BRANCH";')
    out[name]=replace_exact(out[name],
        "    action = strict_sequence;\n",
        '    action = strict_sequence;\n'
        '    zrot_foreground_selection_path = "STRICT_SEQUENCE";\n')
    out[name]=replace_exact(out[name],
        "    if ( spell_queued_action->ready() )\n      action = spell_queued_action;",
        "    if ( spell_queued_action->ready() )\n"
        "    {\n"
        "      action = spell_queued_action;\n"
        '      zrot_foreground_selection_path = "SPELL_QUEUED_ACTION";\n'
        "    }")
    out[name]=replace_exact(out[name],
        "    action = select_action( *active_action_list, execute_type::FOREGROUND );\n",
        "    action = select_action( *active_action_list, execute_type::FOREGROUND );\n"
        '    zrot_foreground_selection_path = "SELECT_ACTION_FOREGROUND";\n')
    out[name]=replace_exact(out[name],
        '        sequence_add( action, action->target, "FOREGROUND_EXECUTE_ACTION" );',
        '        sequence_add( action, action->target, "FOREGROUND_EXECUTE_ACTION",\n'
        "                      zrot_foreground_selection_path );")
    name="engine/report/json/report_json.cpp"
    out[name]=replace_exact(out[name],
        '      json[ "zrot_sequence_origin_callsite" ] = entry.zrot_sequence_origin_callsite;',
        '      json[ "zrot_sequence_origin_callsite" ] = entry.zrot_sequence_origin_callsite;\n'
        '      json[ "zrot_foreground_selection_path" ] = entry.zrot_foreground_selection_path;')
    return out


def instrument_tree(root:Path):
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       capture_output=True,check=True,text=True).stdout.strip()
    if rev!=UPSTREAM_SHA:raise ValueError("FOREGROUND_SELECTION_UPSTREAM_SHA_MISMATCH")
    originals={f:(root/f).read_text("utf-8") for f in FILES}
    for marker,file in [
        ("zrot_apl_object_ordinal","engine/report/json/report_json.cpp"),
        ("zrot_sequence_origin_callsite","engine/player/player_collected_data.hpp"),
    ]:
        if marker not in originals[file]:
            raise ValueError("FOREGROUND_SELECTION_PRIOR_INSTRUMENTATION_REQUIRED")
    patches=patch_selection_sources(originals)
    receipts={}
    for f in FILES:
        before=originals[f].encode();after=patches[f].encode()
        (root/f).write_bytes(after)
        receipts[f]={"before_sha256":hashlib.sha256(before).hexdigest(),
                     "after_sha256":hashlib.sha256(after).hexdigest()}
    return {
        "schema":"ZrotPinnedSimcForegroundSelectionPathInstrumentationV1",
        "upstream_source_sha":UPSTREAM_SHA,
        "files":receipts,
        "valid_selection_paths":list(VALID_PATHS),
        "provenance_capture":"DIRECT_PLAYER_EXECUTE_ACTION_BRANCH",
        "native_priority_or_readiness_equivalence":"NOT_VALIDATED",
        "gameplay_rule_promotion":False,
    }


def selftest():
    player_source="""action_t* player_t::execute_action()
{
  assert( !readying );

  action_t* action = nullptr;

  if ( strict_sequence )
  {
    action = strict_sequence;
  }
  else if ( enable_spell_queue && spell_queued_action )
  {
    if ( spell_queued_action->ready() )
      action = spell_queued_action;
  }
  else
  {
    action = select_action( *active_action_list, execute_type::FOREGROUND );
  }
        sequence_add( action, action->target, "FOREGROUND_EXECUTE_ACTION" );

void player_t::sequence_add( const action_t* a, const player_t* t, const char* zrot_origin )
        data.zrot_sequence_origin_callsite = zrot_origin;
        data.zrot_sequence_origin_callsite = zrot_origin;
"""
    files={
        "engine/player/player.cpp":player_source,
        "engine/player/player.hpp":'                     const char* zrot_origin = "UNKNOWN_CALLSITE" );',
        "engine/player/player_collected_data.hpp":
            '    std::string zrot_sequence_origin_callsite;\n',
        "engine/report/json/report_json.cpp":
            '      json[ "zrot_sequence_origin_callsite" ] = entry.zrot_sequence_origin_callsite;',
    }
    fixed=patch_selection_sources(files)
    assert fixed["engine/player/player.cpp"].count('"SELECT_ACTION_FOREGROUND"')==1
    assert fixed["engine/player/player.cpp"].count('"SPELL_QUEUED_ACTION"')==1
    assert fixed["engine/player/player.cpp"].count('"STRICT_SEQUENCE"')==1
    assert fixed["engine/player/player.cpp"].count("data.zrot_foreground_selection_path") == 2
    assert "zrot_foreground_selection_path" in fixed["engine/report/json/report_json.cpp"]
    try:patch_selection_sources(fixed)
    except ValueError as e:assert str(e).startswith("SIMC_ORIGIN_ANCHOR_COUNT")
    else:raise AssertionError("DOUBLE_INSTRUMENTATION_ACCEPTED")
    changed=dict(files,**{"engine/player/player.cpp":
             player_source.replace("    action = strict_sequence;","    action = something_else;")})
    try:patch_selection_sources(changed)
    except ValueError as e:assert str(e).startswith("SIMC_ORIGIN_ANCHOR_COUNT")
    else:raise AssertionError("UNPINNED_BRANCH_ACCEPTED")
    print("SIMC_FOREGROUND_NATIVE_BRANCH_INSTRUMENT_SELF_TEST=PASS")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream-root",type=Path)
    p.add_argument("--self-test",action="store_true")
    o=p.parse_args()
    if o.self_test or not o.upstream_root:
        selftest()
    else:
        print(json.dumps(instrument_tree(o.upstream_root),indent=2,sort_keys=True))


if __name__=="__main__":
    main()
