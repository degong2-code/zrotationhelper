#!/usr/bin/env python3
"""Pin-guarded, generic SimulationCraft JSON2 APL-object provenance instrumentation.

Never touch class modules, APL algorithms, or native action selection. The
upstream player::create_actions() assigns action_t::signature to the actual
action_priority_t object and action_t::action_list to its owning list. We
serialize a row ordinal only when pointer IDENTITY is found in that list.
This is not based on spell names or timestamps. The modified build has its
OWN executable hash, distinct from the older official Docker image.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess

UPSTREAM_SHA = "710c2408bfd3ae4df71b8cd55cdf01f63fd6c926"
RELATIVE_PATH = Path("engine/report/json/report_json.cpp")
_ANCHOR_INCLUDE = '#include "simulationcraft.hpp"'
_ANCHOR = '      json[ "queue_failed" ] = entry.queue_failed;'
_INSERT = """      // zRotationHelper provenance instrumentation, researcher build only.
      // action_list/signature are assigned together in player_t::create_actions.
      // Pointer address equality against the owning priority list gives the
      // specific APL object, including duplicate token rows and same-time casts.
      // An absent match is UNKNOWN, not a guessed APL line.
      if ( entry.action->action_list && entry.action->signature )
      {
        const auto& origin_apl = *entry.action->action_list;
        for ( std::size_t origin_idx = 0; origin_idx < origin_apl.action_list.size(); ++origin_idx )
        {
          if ( &( origin_apl.action_list[ origin_idx ] ) == entry.action->signature )
          {
            json[ "zrot_apl_object_list" ] = origin_apl.name_str;
            json[ "zrot_apl_object_ordinal" ] = static_cast<unsigned>( origin_idx + 1 );
            json[ "zrot_apl_object_signature" ] = entry.action->signature_str;
            json[ "zrot_origin_proof" ] = "OWNING_LIST_SIGNATURE_POINTER_EQUALITY";
            break;
          }
        }
      }
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_report_json(source: str) -> str:
    if source.count(_ANCHOR_INCLUDE) != 1:
        raise ValueError("UPSTREAM_REPORT_INCLUDE_ANCHOR_NOT_UNIQUE")
    if source.count(_ANCHOR) != 1:
        raise ValueError("UPSTREAM_REPORT_JSON_ANCHOR_NOT_UNIQUE")
    if '"zrot_apl_object_ordinal"' in source or "zrot_origin_proof" in source:
        raise ValueError("UPSTREAM_ALREADY_INSTRUMENTED")
    return (source.replace(_ANCHOR_INCLUDE, _ANCHOR_INCLUDE + '\n#include "player/action_priority_list.hpp"')
                  .replace(_ANCHOR, _ANCHOR + '\n' + _INSERT.rstrip('\n')))


def instrument_checked_tree(root: Path) -> dict:
    r=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                     capture_output=True,text=True,check=True)
    if r.stdout.strip() != UPSTREAM_SHA:
        raise ValueError("UPSTREAM_COMMIT_PIN_MISMATCH")
    path=root/RELATIVE_PATH
    raw=path.read_bytes()
    text=raw.decode("utf-8")
    patched=patch_report_json(text).encode("utf-8")
    if patched==raw:
        raise ValueError("NO_INSTRUMENTATION_CHANGE")
    path.write_bytes(patched)
    return {
        "schema":"ZrotPinnedSimcAplObjectPointerInstrumentationV1",
        "upstream_commit_sha":UPSTREAM_SHA,
        "instrumented_source_path":str(RELATIVE_PATH),
        "original_source_sha256":sha256(raw),
        "patched_source_sha256":sha256(patched),
        "pointer_relation":"ACTION_SIGNATURE_EQUALS_OWNING_PRIORITY_LIST_ENTRY_ADDRESS",
        "report_only_no_selection_code_changed":True,
        "executable_sha256":"PENDING_BUILD",
        "native_apl_decision_equivalence":"NOT_VALIDATED",
        "strict_pre":"NOT_RUN",
        "gameplay_rule_promotion":False,
    }


def selftest():
    src = ('#include "simulationcraft.hpp"\n'
           'void emit(){\n'
           '      json[ "queue_failed" ] = entry.queue_failed;\n'
           '}\n')
    result=patch_report_json(src)
    assert result.count('zrot_apl_object_ordinal')==1
    assert 'entry.action->signature' in result
    assert '&( origin_apl.action_list[ origin_idx ] ) == entry.action->signature' in result
    assert result.count('#include "player/action_priority_list.hpp"')==1
    for changed,err in [
        (src.replace(_ANCHOR,""),"UPSTREAM_REPORT_JSON_ANCHOR_NOT_UNIQUE"),
        (src+_ANCHOR,"UPSTREAM_REPORT_JSON_ANCHOR_NOT_UNIQUE"),
        (src.replace(_ANCHOR_INCLUDE,""),"UPSTREAM_REPORT_INCLUDE_ANCHOR_NOT_UNIQUE"),
        (result,"UPSTREAM_ALREADY_INSTRUMENTED"),
    ]:
        try: patch_report_json(changed)
        except ValueError as e: assert str(e)==err,(str(e),err)
        else: raise AssertionError("UNEXPECTED_UPSTREAM_SOURCE_ACCEPTED")
    print("SIMC_APL_POINTER_PROVENANCE_INSTRUMENTATION_SELF_TEST=PASS")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream-root",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test or not args.upstream_root:
        selftest()
        return
    import json
    print(json.dumps(instrument_checked_tree(args.upstream_root),
                     sort_keys=True,indent=2))


if __name__=="__main__":
    main()
