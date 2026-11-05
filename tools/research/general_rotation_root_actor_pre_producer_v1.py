#!/usr/bin/env python3
"""Source-pinned generic original SimC READY-root PRE actor operand capture.

Adds one read-only actor state snapshot *inside* the existing unique RAII
original select_call scope, immediately before the original a->action_ready()
call. Causal source order (BEGIN -> PRE -> original call -> RESULT -> END)
is checked by a separate replay. This is a direct SimC before-call snapshot
at the same sim clock tick, NOT a WCL latest-transition-before-t fact.
Never synthesize an earlier timestamp. The state is the official direct
sim->active_enemies field, no additional action_ready or RNG call.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_source_route_audit_v1 import _bounded_body, _source_code_mask, git_blob
from general_rotation_select_pre_passive_producer_v1 import REVISION,PLAYER
from general_rotation_select_sweep_instrument_v1 import (
    SCHEMA as SWEEP_SCHEMA, RESULT_MARK, SWEEP_MARK, SIGNATURE
)

SCHEMA="ZrotGenericOriginalRootActorPRECaptureSourceProducerV1"
MARK="ZROT_GENERIC_ROOT_ACTOR_PRE_V1|"
ORIGINAL_CALL="      const bool zrot_native_comparator = a->action_ready();"

class OriginalRootPREError(ValueError):
    pass


def _sha(b:bytes)->str:
    return sha256(b).hexdigest()


def _method(src:str)->tuple[str,int]:
    mask=_source_code_mask(src)
    return _bounded_body(src,mask,SIGNATURE,(0,len(src)))


def patch_source(pristine:bytes,previous:bytes)->bytes:
    source=previous.decode("utf8")
    official=pristine.decode("utf8")
    original,_=_method(official)
    body,start=_method(source)
    if (original.count("a->action_ready()")!=1 or
        body.count(ORIGINAL_CALL)!=1 or body.count(RESULT_MARK)!=1 or
        body.count(SWEEP_MARK)!=1 or MARK in source or
        body.count("zrot_generic_call_scope_v1::current_root()")<1):
        raise OriginalRootPREError("EXACT_PINNED_ORIGINAL_CALL_SWEEP_SOURCE_REQUIRED")
    # This instrumentation creates no new action_ready call. The existing
    # root scope has been established before this source position.
    extra=r"""      if ( sim->log && !is_pet() && !is_enemy() &&
           zrot_generic_call_scope_v1::current_root() != 0 )
      {
        sim->print_log(
          "ZROT_GENERIC_ROOT_ACTOR_PRE_V1|{}|{}|active_enemies|{}",
          sim->current_time().total_millis(),
          zrot_generic_call_scope_v1::current_root(),
          static_cast<int>( sim->active_enemies ) );
      }
"""
    changed=body.replace(ORIGINAL_CALL,extra+ORIGINAL_CALL,1)
    if (changed.count(ORIGINAL_CALL)!=1 or
        changed.count(MARK)!=1 or
        changed.count("a->action_ready()")!=body.count("a->action_ready()") or
        changed.count("sim->active_enemies")!=body.count("sim->active_enemies")+1 or
        changed.count(RESULT_MARK)!=1):
        raise OriginalRootPREError("CHANGED_READY_ROOT_OR_DUPLICATE_RAW_PRE")
    return (source[:start]+changed+source[start+len(body):]).encode()


def generate(root:Path,prior_sweep_receipt:Path)->dict:
    base=root.resolve(strict=True)
    commit=subprocess.run(["git","-C",str(base),"rev-parse","HEAD"],
        capture_output=True,text=True,check=True).stdout.strip()
    if commit!=REVISION:
        raise OriginalRootPREError("OFFICIAL_SIMC_COMMIT_CHANGED")
    upstream=json.loads(prior_sweep_receipt.read_bytes())
    if (upstream.get("schema")!=SWEEP_SCHEMA or
        upstream.get("source_revision")!=REVISION or
        upstream.get("source_original_action_ready_call_count")!=1 or
        upstream.get("additional_action_ready_calls")!=0):
        raise OriginalRootPREError("PRIOR_VERIFIED_SWEEP_RECEIPT_REQUIRED")
    path=base/PLAYER
    previous=path.read_bytes()
    if _sha(previous)!=upstream.get("source_after_sha256"):
        raise OriginalRootPREError("EXACT_PREVIOUS_SWEEP_CPP_BYTES_REQUIRED")
    pristine=subprocess.run(["git","-C",str(base),"show",f"{REVISION}:{PLAYER}"],
        capture_output=True,check=True).stdout
    blob=subprocess.run(["git","-C",str(base),"rev-parse",f"{REVISION}:{PLAYER}"],
        capture_output=True,text=True,check=True).stdout.strip()
    if git_blob(pristine)!=blob:
        raise OriginalRootPREError("OFFICIAL_PLAYER_CPP_GIT_BLOB_CHANGED")
    modified=patch_source(pristine,previous)
    path.write_bytes(modified)
    return {
        "schema":SCHEMA,
        "source_revision":REVISION,
        "official_source_path":PLAYER,
        "official_source_blob_sha1":blob,
        "source_before_sha256":_sha(previous),
        "source_after_sha256":_sha(modified),
        "previous_sweep_receipt_sha256":_sha(prior_sweep_receipt.read_bytes()),
        "original_action_ready_call_count":1,
        "added_ready_calls":0,
        "added_RNG_calls":0,
        "operand_symbol":"active_enemies",
        "operand_source_cpp":"sim->active_enemies",
        "operand_value_kind":"int",
        "source_causal_order":"ROOT_BEGIN_THEN_ACTOR_PRE_THEN_ORIGINAL_READY_THEN_RESULT_THEN_ROOT_END",
        "WCL_latest_transition_before_t_claim":False,
        "direct_before_call_snapshot_same_simc_tick":True,
        "root_PRE_marker":MARK,
        "actual_native_compiled":False,
        "full_READY_proven":0,
        "WCL_API_calls":0
    }


def selftest():
    official=(SIGNATURE+'\n execute_type et,const action_t* context )\n'
              '{\n  if ( a->action_ready() ) {}\n}\n')
    prior=(SIGNATURE+'\n execute_type et,const action_t* context )\n'
           '{\n  // ZROT_GENERIC_SELECT_SWEEP_V1|\n'
           '  // ZROT_GENERIC_READY_RESULT_V1|\n'
           '  auto root=zrot_generic_call_scope_v1::current_root();\n'
           '      const bool zrot_native_comparator = a->action_ready();\n}\n')
    actual=patch_source(official.encode(),prior.encode())
    assert actual.decode().count(MARK)==1
    assert actual.decode().count("a->action_ready()")==1
    assert actual.decode().count("sim->active_enemies")==1
    for broken in (prior.replace(ORIGINAL_CALL,"return true;"),actual.decode(),
                   prior.replace("ZROT_GENERIC_READY_RESULT_V1|","not_ready_result")):
        try:patch_source(official.encode(),broken.encode())
        except OriginalRootPREError:pass
        else:raise AssertionError("UNVERIFIED_OR_DUPLICATE_SOURCE_PATCH_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":6,"live_cpp_verified":False,
        "source_READY_call_count_delta":0,"WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--prior-sweep-receipt",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root is None and a.prior_sweep_receipt is None:
        result=selftest()
    elif a.simc_root is not None and a.prior_sweep_receipt is not None:
        result=generate(a.simc_root,a.prior_sweep_receipt)
    else:p.error("source root and prior sweep producer receipt required together")
    data=canonical(result)
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as f:f.write(data)
    else:print(data.decode(),end="")

if __name__=="__main__":main()
