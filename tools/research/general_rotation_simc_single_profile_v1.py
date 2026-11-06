#!/usr/bin/env python3
"""Direct class-neutral SimC .simc -> source conditional priority IR.

Single local profile, no manifest, credentials, SimC build or game client.
Uses the SAME generic source-to-conditional-opener engine as multi-class E2E.
Header class/spec is detected, not a hardcoded branch for Mage/Warrior.

Without an externally verified source pin, "local" does not mean an
official/current patch profile; all actual READY and opener execution UNKNOWN.
No arguments -> self-test for safe PyCharm launches.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import git_blob,canonical
from general_rotation_simc_e2e_research_engine_v1 import (
    SCHEMA as E2E_SCHEMA, POLICY,compile_spec
)

SCHEMA="ZrotGenericSimCSingleInputSourceConditionalModelV1"
IDENT=re.compile(r"[a-z][a-z0-9_]*\Z")
PIN=re.compile(r"[a-f0-9]{40}\Z")
class DirectProfileError(ValueError):pass

def compile_single(raw:bytes,*,expected_git_blob:str|None=None)->dict:
    try:decoded=raw.decode("utf8")
    except UnicodeDecodeError as e:raise DirectProfileError("NON_UTF8_PROFILE") from e
    lines=[x.strip() for x in decoded.splitlines()
           if x.strip() and not x.lstrip().startswith("#")]
    if not lines:raise DirectProfileError("EMPTY_PROFILE")
    actor_key,sep,actor_name=lines[0].partition("=")
    if (not sep or not IDENT.fullmatch(actor_key) or
        not actor_name or actor_key in ("actions","spec","source")):
        raise DirectProfileError("PROFILE_CLASS_HEADER_INVALID")
    specs=[x.partition("=")[2] for x in lines if x.startswith("spec=")]
    if len(specs)!=1 or not IDENT.fullmatch(specs[0]):
        raise DirectProfileError("ONE_SPECIALIZATION_HEADER_REQUIRED")
    blob=git_blob(raw)
    if expected_git_blob is not None and (
        not PIN.fullmatch(expected_git_blob) or expected_git_blob!=blob):
        raise DirectProfileError("EXPECTED_SOURCE_GIT_BLOB_MISMATCH")
    meta={"key":actor_key+"_"+specs[0],
          "class_key":actor_key,
          "git_blob":blob}
    result=compile_spec(raw,meta,None)
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "source_git_blob_sha1":blob,
        "source_profile_sha256":sha256(raw).hexdigest(),
        "source_origin":(
            "USER_PINNED_CONTENT_NOT_OFFICIAL_REVISION_VERIFIED"
            if expected_git_blob is not None else
            "LOCAL_FILE_SHA_COMPUTED_NOT_OFFICIAL_REVISION_VERIFIED"),
        "spec_key":meta["key"],
        "profile_to_conditioned_priority_graph_compiled":True,
        "source_model":result,
        "native_opener_selected_source_trace":"NOT_SUPPLIED",
        "physical_ready_and_optimality":"UNKNOWN",
        "real_dummy_error_feedback":"UNKNOWN",
        "WCL_blind_holdout":"NOT_RUN",
        "WCL_API_calls":0,
    }

def selftest()->dict:
    raw=(b"warrior=\"sample\"\nspec=fury\n"
         b"actions.precombat=snapshot_stats\n"
         b"actions=call_action_list,name=aoe,if=active_enemies>=2\n"
         b"actions+=/slam,if=rage>=30\n"
         b"actions.aoe=whirlwind\n")
    out=compile_single(raw)
    assert out["spec_key"]=="warrior_fury"
    assert out["source_model"]["source_APL_row_count"]==4
    assert out["source_model"]["opener_first_actual_player_cast"]=="UNKNOWN"
    for invalid in (b"spec=fury\nactions=slam\n",
                    raw.replace(b"spec=fury",b"spec=fury\nspec=arms"),
                    raw.replace(b"actions=slam",b"actions=invalid")):
        try:compile_single(invalid,expected_git_blob="a"*40)
        except DirectProfileError:pass
        else:raise AssertionError("UNPINNED_SOURCE_PROFILE_ACCEPTED")
    try:compile_single(raw,expected_git_blob="b"*40)
    except DirectProfileError:pass
    else:raise AssertionError("PINNED_SOURCE_BLOB_MUTATION_ACCEPTED")
    return {
      "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
      "checks":6,"native_simc_builds":0,
      "WCL_API_calls":0,"independent_FULL_READY_proven":0,
    }

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path,help="Existing .simc file (any spec)")
    p.add_argument("--expected-git-blob",help="Optional exact Git blob SHA1 input pin")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.profile is not None:
        if a.profile.suffix!=".simc":p.error("profile extension must be .simc")
        value=compile_single(a.profile.read_bytes(),
                             expected_git_blob=a.expected_git_blob)
    else:
        if a.expected_git_blob is not None:p.error("--profile is required for source pin")
        value=selftest()
    encoded=canonical(value)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(encoded)
        print("SIMC_SINGLE_PROFILE_IR_OUTPUT="+str(a.out))
        print("SIMC_SINGLE_PROFILE_IR_SHA256="+sha256(encoded).hexdigest())
    else:
        import sys
        sys.stdout.buffer.write(encoded)

if __name__=="__main__":
    main()
