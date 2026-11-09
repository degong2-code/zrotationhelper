#!/usr/bin/env python3
"""Generic pinned SimC action-sequence emission -> actual action_t APL row.

Instrument the ORIGINAL player_t::sequence_add(...) exactly where SimC
appends JSON2 action_sequence data. A passive marker observes a->signature,
a->action_list, and the exact JSON2 destination ordinal before the append.

No new calls to readiness, resource/procs, RNG, scheduling, or action methods.
This is a source-row identity witness for SIMULATED action-sequence records,
not a ready/optimality/causality oracle. An action without an APL signature
(auto attacks, triggered effects etc.) remains UNMAPPED.

Safe default for PyCharm: source-only synthetic test.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from simc_apl_semantic_ir_v2 import git_blob
from simc_native_select_trace_instrument_v1 import (
    SIMC_COMMIT,PLAYER_CPP_BLOB,RELATIVE)

SCHEMA="ZrotOriginalSimCJson2SequenceExactAPLRowProducerV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
MARK="ZROT_GR_JSON2_ACTION_SOURCE_ROW_V1|"
START="void player_t::sequence_add( const action_t* a, const player_t* t )"
END="\nvoid player_t::precombat_init()"
INSERT="      if ( a->is_precombat )"
LOG=r"""      // Generic passive APL row identity for precisely this JSON2 append.
      // a and the recorded ordinal are the SAME values sequence_add uses.
      if ( sim->log && !is_pet() && !is_enemy() )
      {
        unsigned zrot_row = 0;
        const char* zrot_owner = "-";
        if ( a->action_list && a->signature )
        {
          const auto& zrot_apl = *a->action_list;
          for ( std::size_t zrot_i = 0; zrot_i < zrot_apl.action_list.size(); ++zrot_i )
          {
            if ( &( zrot_apl.action_list[ zrot_i ] ) == a->signature )
            {
              zrot_owner = zrot_apl.name_str.c_str();
              zrot_row = static_cast<unsigned>( zrot_i + 1 );
              break;
            }
          }
        }
        sim->print_log(
          "ZROT_GR_JSON2_ACTION_SOURCE_ROW_V1|{}|{}|{}|{}|{}|{}|{}",
          sim->current_time().total_millis(),
          a->is_precombat ? "P" : "C",
          a->is_precombat ? collected_data.action_sequence_precombat.size()
                          : collected_data.action_sequence.size(),
          a->name_str, zrot_owner, zrot_row,
          static_cast<const void*>( a ) );
      }
"""

class SequenceAPLSourceError(ValueError):pass

def check(ok:bool,reason:str):
    if not ok:raise SequenceAPLSourceError(reason)

def sha(raw:bytes)->str:
    return sha256(raw).hexdigest()

def patch(original:bytes,*,enforce_pin:bool=True)->bytes:
    if enforce_pin:
        check(git_blob(original)==PLAYER_CPP_BLOB,
              "OFFICIAL_PLAYER_CPP_GIT_BLOB_CHANGED")
    s=original.decode("utf-8")
    check(MARK not in s and s.count(START)==1 and s.count(END)==1,
          "ORIGINAL_SEQUENCE_METHOD_ALREADY_PATCHED_OR_MISSING")
    a=s.index(START)
    b=s.index(END,a)
    body=s[a:b]
    check(body.count(INSERT)==1 and
          body.count("collected_data.action_sequence.emplace_back( a, t, sim->current_time(), this )")==1 and
          body.count("collected_data.action_sequence_precombat.emplace_back( a, t, sim->current_time(), this )")==1 and
          body.count("a->sequence_add_fn( data.action_reporting, data.target_reporting );")==2 and
          body.count("if ( !sim->collect_action_sequence )")==1,
          "PINNED_ORIGINAL_JSON2_COLLECTION_LOCATION_DRIFT")
    new=s[:a]+body.replace(INSERT,LOG+INSERT,1)+s[b:]
    check(new.count(MARK)==1 and
          new.count("a->action_ready()")==s.count("a->action_ready()") and
          new.count("a->ready()")==s.count("a->ready()") and
          new.count("a->sequence_add_fn( data.action_reporting, data.target_reporting );")==s.count("a->sequence_add_fn( data.action_reporting, data.target_reporting );") and
          new.count("collected_data.action_sequence.emplace_back( a, t, sim->current_time(), this )")==s.count("collected_data.action_sequence.emplace_back( a, t, sim->current_time(), this )") and
          new.count("collected_data.action_sequence_precombat.emplace_back( a, t, sim->current_time(), this )")==s.count("collected_data.action_sequence_precombat.emplace_back( a, t, sim->current_time(), this )"),
          "JSON2_ORIGINAL_APPEND_OR_READY_COUNT_CHANGED")
    return new.encode("utf-8")

def install(root:Path)->dict:
    root=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    check(rev==SIMC_COMMIT,"OFFICIAL_SIMC_REVISION_CHANGED")
    location=root/RELATIVE
    original=location.read_bytes()
    altered=patch(original)
    location.write_bytes(altered)
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "original_simc_revision":rev,
        "original_player_cpp_git_blob_sha1":PLAYER_CPP_BLOB,
        "original_player_cpp_sha256":sha(original),
        "patched_player_cpp_sha256":sha(altered),
        "marker":MARK,
        "hook":"player_t::sequence_add",
        "evidence_point":"BEFORE_SAME_JSON2_EMPLACE_BACK",
        "ready_or_RNG_calls_added":0,
        "original_JSON2_appends_unchanged":True,
        "precombat_and_combat_ordinals_separate":True,
        "pointer_to_original_action_t_captured":True,
        "actual_CXX_compiled":False,
        "valid_same_run_source_row_proof":"PENDING_REPLAY_AND_PARITY",
        "complete_READY_proven":0,
        "WCL_API_calls":0,
    }

def selftest()->dict:
    method=(START+"\n{\n"
            "  if ( !sim->collect_action_sequence )\n    return;\n"
            "    if ( collected_data.action_sequence.size() <= sim->expected_max_time() * 2.0 + 3.0 )\n"
            "    {\n"
            "      if ( a->is_precombat )\n"
            "      {\n"
            "        auto& data = collected_data.action_sequence_precombat.emplace_back( a, t, sim->current_time(), this );\n"
            "        a->sequence_add_fn( data.action_reporting, data.target_reporting );\n"
            "      }\n      else\n      {\n"
            "        auto& data = collected_data.action_sequence.emplace_back( a, t, sim->current_time(), this );\n"
            "        a->sequence_add_fn( data.action_reporting, data.target_reporting );\n"
            "      }\n    }\n}\n")
    raw=("// mock test only\n"+method+END+"\n").encode()
    changed=patch(raw,enforce_pin=False).decode()
    assert changed.count(MARK)==1
    assert changed.index(MARK)<changed.index(INSERT,changed.index(START))
    assert changed.count("a->action_ready()")==0
    assert changed.count("action_sequence.emplace_back(")==raw.decode().count("action_sequence.emplace_back(")
    for invalid in (changed.encode(),raw.replace(b"a->signature",b"a->other_signature")):
        if invalid==raw:continue
        try:patch(invalid,enforce_pin=False)
        except SequenceAPLSourceError:pass
        else:raise AssertionError("SOURCE_PATCH_FAIL_CLOSED_REQUIRED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":13,"pinned_original_cpp_compiled":False,
        "specific_spells_hardcoded":0,"original_ready_calls_added":0,
        "WCL_API_calls":0,
    }

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source-root",type=Path)
    cli.add_argument("--out",type=Path)
    a=cli.parse_args()
    if a.source_root is None and a.out is None:
        print(json.dumps(selftest(),sort_keys=True))
        return
    if a.source_root is None or a.out is None:
        cli.error("--source-root and --out required")
    result=install(a.source_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:
        f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    print("ORIGINAL_SIMC_JSON2_APL_ROW_SOURCE_PATCH_SHA256="+
          sha(a.out.read_bytes()))

if __name__=="__main__":
    main()
