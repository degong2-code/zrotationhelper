#!/usr/bin/env python3
"""Pinned Mage SpecAdapter guard witness at the original ready() execution.

Only two source-verified Mage override methods are instrumented here:
arcane_blast_t::ready and prismatic_bolt_t::ready. The original buff_t::check()
is executed exactly once at its original logical site, captured in a local
integer, and used by the original short-circuit branch. All other original
ready/action_ready invocations and method order are left unchanged.

The generic player_t select-action path is already patched by the reusable
General Rotation PRE field transport; this patch adds an action *pointer*
marker immediately before the single original action_ready() call. The
method-entry marker logs the exact same 'this' pointer, enabling strict
attempt-to-dispatch pairing (including repeated attempts at one timestamp).

These are original SimC method-PRE observations, not WCL strict-before PRE.
Source-marker transport, original behavior parity and method route must be
validated independently before any necessary-negative GateContract fact.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from simc_apl_semantic_ir_v2 import git_blob
from simc_native_select_trace_instrument_v1 import SIMC_COMMIT, PLAYER_CPP_BLOB
from general_rotation_mage_source_fixture_v1 import (
    CPP_BLOB as MAGE_BLOB, PROFILE_BLOB as MAGE_PROFILE_BLOB)
from general_rotation_original_pre_field_transport_v1 import (
    MARK as GENERIC_PRE_MARK, ORIGINAL_CALL as ORIGINAL_READY_CALL)
from general_rotation_original_method_witness_v1 import (
    POINTER_MARK,extend_player_pointer,MethodWitnessError)

SCHEMA="ZrotMageOriginalReadyMethodGuardWitnessProducerV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
PLAYER_PATH="engine/player/player.cpp"
MAGE_PATH="engine/class_modules/sc_mage.cpp"
PROFILE_PATH="profiles/MID2/MID2_Mage_Arcane.simc"
METHOD_MARK="ZROT_GR_MAGE_EXACT_READY_METHOD_PRE_V1|"
BUFF_CHECK="p()->buffs.prismatic_bolt->check()"
DELEGATE="return arcane_mage_spell_t::ready();"

ORIGINAL_METHODS=(
    ("arcane_blast",
     """  bool ready() override
  {
    // Arcane Blast is upgraded into Prismatic Bolt while the buff is up.
    if ( p()->buffs.prismatic_bolt->check() )
      return false;

    return arcane_mage_spell_t::ready();
  }""",
     "zrot_gr_guard_stack > 0"),
    ("prismatic_bolt",
     """  bool ready() override
  {
    if ( !p()->buffs.prismatic_bolt->check() )
      return false;

    return arcane_mage_spell_t::ready();
  }""",
     "zrot_gr_guard_stack <= 0"),
)


class GuardProducerError(ValueError):
    pass


def require(ok:bool,code:str)->None:
    if not ok:raise GuardProducerError(code)


def digest(x:bytes)->str:
    return sha256(x).hexdigest()


def verify_pristine_root(root:Path)->dict:
    root=root.resolve(strict=True)
    revision=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        capture_output=True,text=True,check=True).stdout.strip()
    require(revision==SIMC_COMMIT,"ORIGINAL_SIMC_REVISION_MISMATCH")
    pins={PLAYER_PATH:PLAYER_CPP_BLOB,MAGE_PATH:MAGE_BLOB,
          PROFILE_PATH:MAGE_PROFILE_BLOB}
    for p,blob in pins.items():
        original=subprocess.run(["git","-C",str(root),"show","HEAD:"+p],
            check=True,capture_output=True).stdout
        require(git_blob(original)==blob,"SOURCE_GIT_BLOB_DRIFT:"+p)
    return {"original_commit":revision,"source_git_blobs":pins}


def mage_guard_body(action:str,condition:str)->str:
    return (
       "  bool ready() override\n"
       "  {\n"
       "    // Source-guard original invocation witness, not a second check().\n"
       "    const int zrot_gr_guard_stack = "+BUFF_CHECK+";\n"
       "    if ( p()->sim->log )\n"
       '      p()->sim->print_log( "'+METHOD_MARK+
            '{}|{}|{}|{}|{}",\n'
       "        p()->sim->current_time().total_millis(), \""+action+"\",\n"
       "        name_str, static_cast<const void*>( this ), zrot_gr_guard_stack );\n"
       "    if ( "+condition+" )\n"
       "      return false;\n"
       "\n"
       "    "+DELEGATE+"\n"
       "  }"
    )


def extend_mage(pristine:bytes,*,require_pin:bool=True)->bytes:
    if require_pin:
        require(git_blob(pristine)==MAGE_BLOB,
                "NOT_PINNED_ORIGINAL_MAGE_SOURCE")
    code=pristine.decode("utf-8")
    require(METHOD_MARK not in code,"MAGE_GUARD_ALREADY_INSTRUMENTED")
    check_count=code.count(BUFF_CHECK)
    delegate_count=code.count(DELEGATE)
    for action,source,condition in ORIGINAL_METHODS:
        require(code.count(source)==1,
                "ORIGINAL_READY_GUARD_BODY_NOT_UNIQUE:"+action)
        code=code.replace(source,mage_guard_body(action,condition),1)
    require(code.count(BUFF_CHECK)==check_count and
            code.count(DELEGATE)==delegate_count and
            code.count(METHOD_MARK)==len(ORIGINAL_METHODS),
            "MAGE_ORIGINAL_BUFF_AND_DELEGATE_CALL_COUNTS_DRIFT")
    return code.encode("utf-8")


def patch_original_tree(root:Path)->dict:
    root=root.resolve(strict=True)
    revision=verify_pristine_root(root)
    player=root/PLAYER_PATH
    mage=root/MAGE_PATH
    pbefore=player.read_bytes()
    mbefore=mage.read_bytes()
    require(git_blob(mbefore)==MAGE_BLOB,
            "MAGE_CPP_ALREADY_MODIFIED")
    pafter=extend_player_pointer(pbefore)
    mafter=extend_mage(mbefore)
    # Commit both changes only after both have been checked in memory.
    player.write_bytes(pafter)
    mage.write_bytes(mafter)
    return {"schema":SCHEMA,"policy_id":POLICY,
            "official_source":revision,
            "player_before_sha256":digest(pbefore),
            "player_after_sha256":digest(pafter),
            "mage_before_sha256":digest(mbefore),
            "mage_after_sha256":digest(mafter),
            "original_buff_check_count_preserved":True,
            "original_delegate_call_count_preserved":True,
            "original_action_ready_call_count_preserved":True,
            "new_independent_ready_method_calls":0,
            "instrumented_method_names":[x[0] for x in ORIGINAL_METHODS],
            "object_identity_correlator":"same-process C++ action_t*",
            "original_and_instrumented_behavior_parity":"NOT_YET_TESTED",
            "WCL_API_calls":0,"full_positive_READY":0}


def selftest()->dict:
    mock="\n".join(x[1] for x in ORIGINAL_METHODS).encode()
    modified=extend_mage(mock,require_pin=False).decode()
    require(modified.count(METHOD_MARK)==2 and
            modified.count(BUFF_CHECK)==2 and
            modified.count(DELEGATE)==2 and
            "if ( zrot_gr_guard_stack <= 0 )" in modified and
            "if ( zrot_gr_guard_stack > 0 )" in modified,
            "MAGE_BOTH_SOURCE_GUARDS_NOT_PRESERVED")
    sample=("HEAD\n"+GENERIC_PRE_MARK+"{}|{}|{}|{}|{}|{}|{}\n"+
            ORIGINAL_READY_CALL+"\nTAIL").encode()
    pointed=extend_player_pointer(sample).decode()
    require(pointed.count(POINTER_MARK)==1 and
            pointed.index(GENERIC_PRE_MARK)<pointed.index(POINTER_MARK)<
            pointed.index(ORIGINAL_READY_CALL) and
            pointed.count("a->action_ready()")==1,
            "EXACT_POINTER_SOURCE_INSERTION_FAILED")
    for fn,x in ((extend_player_pointer,pointed.encode()),
                 (lambda y:extend_mage(y,require_pin=False),modified.encode())):
        try:fn(x)
        except (GuardProducerError,MethodWitnessError):pass
        else:raise AssertionError("DUPLICATE_SOURCE_GUARD_PRODUCER_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":12,
            "exact_same_action_pointer_for_method_pairing":True,
            "existing_original_ready_and_buff_check_counts_preserved":True,
            "Native_CPP_compiled":False,"WCL_API_calls":0,
            "independent_full_READY":0}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root is None:
        print(json.dumps(selftest(),sort_keys=True))
        return
    require(a.receipt is not None,
            "ORIGINAL_SOURCE_PATCH_RECEIPT_REQUIRED")
    output=patch_original_tree(a.simc_root)
    a.receipt.parent.mkdir(parents=True,exist_ok=True)
    with a.receipt.open("xb") as f:
        f.write((json.dumps(output,sort_keys=True,indent=2)+"\n").encode())
    print("PINNED_MAGE_ORIGINAL_READY_SOURCE_PATCH_SHA256="+
          digest(a.receipt.read_bytes()))


if __name__=="__main__":
    main()
