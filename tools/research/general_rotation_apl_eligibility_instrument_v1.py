#!/usr/bin/env python3
"""Original-source generic SimC APL actor action-init / foreground inventory.

Fourth passive C++ producer stage. Consumes byte-pinned outputs of SELECT-PRE,
METHOD-PRE, strict CALL-SCOPE producers, not the original action_priority
source directly. Audits official C++ player_t::init_actions and init_finished
against pristine git-show source before adding side-effect-free inventory logs.

This is *initialization and list membership evidence*, not a proof of WHY
an action was omitted, its readiness, or source priority optimality.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from general_rotation_call_scope_instrument_v1 import (
    SCHEMA as PREVIOUS_SCHEMA
)
from general_rotation_source_route_audit_v1 import (
    _source_code_mask, _bounded_body, git_blob
)
from general_rotation_select_pre_passive_producer_v1 import REVISION, PLAYER
from general_rotation_original_pre_capture_engine_v1 import canonical

SCHEMA="ZrotGenericOriginalActionInitializationEligibilityProducerV1"
MARK="ZROT_GENERIC_APL_ELIGIBILITY_V1|"
STAGES=(
    ("INIT_ACTIONS_END","void player_t::init_actions()"),
    ("INIT_FINISHED_END","void player_t::init_finished()"),
)


class EligibilityInstrumentError(ValueError):
    pass


def _sha(data:bytes)->str:
    return sha256(data).hexdigest()


def _block(stage:str)->str:
    if not re.fullmatch(r"[A-Z_]+",stage):
        raise EligibilityInstrumentError("UNSAFE_ELIGIBILITY_STAGE_NAME")
    return r"""
  // Source-true *post-stage* action registry inventory, not a readiness call.
  if ( sim->log && !is_pet() && !is_enemy() )
  {
    std::size_t zrot_registered = 0;
    std::size_t zrot_mapped = 0;
    std::size_t zrot_unmapped = 0;
    for ( action_t* zrot_action : action_list )
    {
      ++zrot_registered;
      if ( !zrot_action || !zrot_action->action_list || !zrot_action->signature )
      {
        ++zrot_unmapped;
        continue;
      }
      const auto* zrot_owner = zrot_action->action_list;
      std::size_t zrot_ordinal = 0;
      for ( std::size_t zrot_i = 0; zrot_i < zrot_owner->action_list.size(); ++zrot_i )
      {
        if ( &( zrot_owner->action_list[zrot_i] ) == zrot_action->signature )
        {
          zrot_ordinal = zrot_i + 1;
          break;
        }
      }
      if ( zrot_ordinal == 0 )
      {
        ++zrot_unmapped;
        continue;
      }
      ++zrot_mapped;
      bool zrot_in_foreground = false;
      for ( action_t* zrot_candidate : zrot_owner->foreground_action_list )
      {
        if ( zrot_candidate == zrot_action )
        {
          zrot_in_foreground = true;
          break;
        }
      }
      sim->print_log(
        "ZROT_GENERIC_APL_ELIGIBILITY_V1|ROW|""" + stage + r"""|{}|{}|{}|{}|{}|{}|{}|{}",
        zrot_owner->name_str, static_cast<unsigned>( zrot_ordinal ),
        zrot_action->name_str, zrot_action->background ? 1 : 0,
        zrot_in_foreground ? 1 : 0,
        active_action_list == zrot_owner ? 1 : 0,
        main_hand_weapon.type == WEAPON_NONE ? 1 : 0,
        off_hand_weapon.type == WEAPON_NONE ? 1 : 0 );
    }
    sim->print_log(
      "ZROT_GENERIC_APL_ELIGIBILITY_V1|END|""" + stage + r"""|{}|{}|{}",
      static_cast<unsigned>( zrot_registered ),
      static_cast<unsigned>( zrot_mapped ),
      static_cast<unsigned>( zrot_unmapped ) );
  }
"""


def _method_body(source:str,signature:str)->tuple[str,int]:
    code=_source_code_mask(source)
    if code.count(signature)!=1:
        raise EligibilityInstrumentError("ORIGINAL_INIT_METHOD_SIGNATURE_AMBIGUOUS")
    return _bounded_body(source,code,signature,(0,len(code)))


def instrument(original_source:bytes,already_instrumented:bytes)->tuple[bytes,dict]:
    pristine=original_source.decode("utf8")
    modified=already_instrumented.decode("utf8")
    if MARK in modified or MARK in pristine:
        raise EligibilityInstrumentError("ELIGIBILITY_SOURCE_ALREADY_INSTRUMENTED")
    injections=[]
    source_methods=[]
    for stage,signature in STAGES:
        official_body,_=_method_body(pristine,signature)
        existing_body,opening=_method_body(modified,signature)
        # Prior producers must not have touched the init stages. A changed
        # body invalidates our source-truth claim, even if names still match.
        if existing_body!=official_body:
            raise EligibilityInstrumentError("PINNED_INIT_BODY_CHANGED:"+stage)
        marker=_block(stage)
        if marker.count(MARK)!=2:
            raise EligibilityInstrumentError("INVALID_SOURCE_INIT_MARKER_EMITTER")
        closing=opening+len(existing_body)-1
        injections.append((closing,marker))
        source_methods.append({
            "stage":stage,"signature":signature,
            "original_source_method_body_sha256":_sha(official_body.encode()),
            "original_init_body_unchanged":True
        })
    if len({x for x,_ in injections})!=len(injections):
        raise EligibilityInstrumentError("DUPLICATE_INIT_METHOD_BODY_END")
    for position,body in sorted(injections,reverse=True):
        modified=modified[:position]+body+modified[position:]
    if (modified.count(MARK)!=2*len(STAGES)
        or modified.count("action_ready(")!=pristine.count("action_ready(")+
            (already_instrumented.decode("utf8").count("action_ready(")-
             pristine.count("action_ready("))):
        raise EligibilityInstrumentError("ELIGIBILITY_INJECTION_CHANGED_READY_CALLS")
    return modified.encode(),{"source_method_pins":source_methods}


def generate(root:Path, previous_receipt_path:Path)->dict:
    r=root.resolve(strict=True)
    commit=subprocess.run(["git","-C",str(r),"rev-parse","HEAD"],text=True,
                          capture_output=True,check=True).stdout.strip()
    if commit!=REVISION:
        raise EligibilityInstrumentError("SIMC_ORIGINAL_SOURCE_REVISION_MISMATCH")
    previous=json.loads(previous_receipt_path.read_bytes())
    if (previous.get("schema")!=PREVIOUS_SCHEMA or
        previous.get("source_revision")!=REVISION or
        previous.get("original_action_ready_call_count")!=1 or
        previous.get("new_action_ready_calls")!=0):
        raise EligibilityInstrumentError("STRICT_PREVIOUS_CALL_SCOPE_RECEIPT_REQUIRED")
    matches=[s for s in previous["source_files"] if s["path"]==PLAYER]
    if len(matches)!=1:
        raise EligibilityInstrumentError("PREVIOUS_SCOPE_PLAYER_SOURCE_NOT_UNIQUE")
    source_file=r/PLAYER
    current=source_file.read_bytes()
    if _sha(current)!=matches[0]["after_sha256"]:
        raise EligibilityInstrumentError("PREVIOUS_SCOPE_SOURCE_BYTES_DRIFT")
    original=subprocess.run(["git","-C",str(r),"show",f"{REVISION}:{PLAYER}"],
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
    official_blob=git_blob(original)
    expected_blob=subprocess.run(
        ["git","-C",str(r),"rev-parse",f"{REVISION}:{PLAYER}"],
        text=True,capture_output=True,check=True).stdout.strip()
    if official_blob!=expected_blob:
        raise EligibilityInstrumentError("OFFICIAL_INIT_SOURCE_GIT_BLOB_DRIFT")
    transformed,pins=instrument(original,current)
    source_file.write_bytes(transformed)
    return {
        "schema":SCHEMA,
        "source_revision":REVISION,
        "source_path":PLAYER,
        "official_source_git_blob_sha1":official_blob,
        "prior_scope_producer_sha256":_sha(previous_receipt_path.read_bytes()),
        "source_before_sha256":_sha(current),
        "source_after_sha256":_sha(transformed),
        "stage_inventory_marker":MARK,
        **pins,
        "source_stage_count":2,
        "source_action_ready_call_count_delta":0,
        "added_original_ready_rng_target_sync_calls":0,
        "actual_native_compiled":False,
        "source_APL_activation_full_exhaustiveness":False,
        "positive_FULL_action_READY_proven":0,
        "WCL_API_calls":0
    }


def selftest()->dict:
    before=r"""#include "one.hpp"
void player_t::init_actions()
{
  action_t* x = nullptr;
}
void player_t::init_finished()
{
  action_t* y = nullptr;
}
"""
    patched,out=instrument(before.encode(),before.encode())
    assert len(out["source_method_pins"])==2
    assert patched.decode().count(MARK)==4
    assert patched.decode().count("main_hand_weapon.type == WEAPON_NONE")==2
    assert patched.decode().count("off_hand_weapon.type == WEAPON_NONE")==2
    assert patched.decode().count("action_ready(")==0
    assert all(row["original_init_body_unchanged"] for row in out["source_method_pins"])
    for malformed in (before.replace("x = nullptr","x = 1"),before.replace(
        "void player_t::init_finished()","void player_t::wrong_init_finished()")):
        try:instrument(before.encode(),malformed.encode())
        except EligibilityInstrumentError:pass
        else:raise AssertionError("SOURCE_INIT_METHOD_DRIFT_ACCEPTED")
    try:instrument(before.encode(),patched)
    except EligibilityInstrumentError:pass
    else:raise AssertionError("DUPLICATE_INIT_SOURCE_PATCH_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":10,"stage_count":2,
        "source_truth_verified_in_actual_simc":False,
        "actual_native_compiled":False,
        "positive_READY_certified":0,"WCL_API_calls":0
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--previous-call-scope-receipt",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root is None and a.previous_call_scope_receipt is None:
        result=selftest()
    elif a.simc_root is not None and a.previous_call_scope_receipt is not None:
        result=generate(a.simc_root,a.previous_call_scope_receipt)
    else:p.error("simc root and previous call-scope receipt must be paired")
    raw=canonical(result)
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as out:out.write(raw)
    else:print(raw.decode(),end="")


if __name__=="__main__":
    main()
