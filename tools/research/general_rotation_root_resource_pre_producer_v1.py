#!/usr/bin/env python3
"""Generic original SimC root PRE raw mana numerator/denominator collector.

A source-pinned successor to the root active-enemies producer. Reads original
player_t::resources, not the Native if_expr return, and never calls an
additional action_ready(), spell, resource-mutating or RNG function.
No numeric mana.pct fact is asserted here: separate replay verifies source
order, denominator and original Native IF parity before such an assertion.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_root_actor_pre_producer_v1 import (
    SCHEMA as ROOT_SCHEMA, MARK as ACTOR_MARK, ORIGINAL_CALL, _method
)
from general_rotation_select_pre_passive_producer_v1 import REVISION, PLAYER
from general_rotation_source_route_audit_v1 import git_blob

SCHEMA = "ZrotOriginalRootRawResourcePreProducerV1"
MARK = "ZROT_GENERIC_ROOT_MANA_PRE_V1|"

class RootResourcePREError(ValueError):
    pass

def digest(b:bytes)->str:
    return sha256(b).hexdigest()

# Capture the *two independent raw quantities*. No derived percentage is
# injected into the C++ APL or calculated by the producer. 17 significant
# digits are necessary to round-trip IEEE-754 doubles for threshold checks.
PRE = r"""      if ( sim->log && !is_pet() && !is_enemy() &&
           zrot_generic_call_scope_v1::current_root() != 0 )
      {
        sim->print_log(
          "ZROT_GENERIC_ROOT_MANA_PRE_V1|{}|{}|{:.17g}|{:.17g}",
          sim->current_time().total_millis(),
          zrot_generic_call_scope_v1::current_root(),
          static_cast<double>( resources.current[ RESOURCE_MANA ] ),
          static_cast<double>( resources.max[ RESOURCE_MANA ] ) );
      }
"""

def patch(pristine:bytes, previous:bytes)->bytes:
    official=pristine.decode("utf8")
    current=previous.decode("utf8")
    origin,_=_method(official)
    body,start=_method(current)
    if (origin.count("a->action_ready()")!=1 or
        body.count(ORIGINAL_CALL)!=1 or
        body.count(ACTOR_MARK)!=1 or
        body.count("zrot_generic_call_scope_v1::current_root()")<1 or
        body.count("a->action_ready()")!=1 or
        MARK in current):
        raise RootResourcePREError("EXACT_ROOT_PRE_SOURCE_RECEIPT_REQUIRED")
    new_body=body.replace(ORIGINAL_CALL,PRE+ORIGINAL_CALL,1)
    if (new_body.count(ORIGINAL_CALL)!=1 or
        new_body.count(MARK)!=1 or
        new_body.count(ACTOR_MARK)!=1 or
        new_body.count("a->action_ready()")!=1 or
        new_body.index(ACTOR_MARK)>new_body.index(MARK) or
        new_body.index(MARK)>new_body.index(ORIGINAL_CALL)):
        raise RootResourcePREError("ROOT_RESOURCE_CAPTURE_CHANGED_SOURCE_ORDER")
    return (current[:start]+new_body+current[start+len(body):]).encode("utf8")

def generate(root:Path,root_receipt_path:Path)->dict:
    root=root.resolve(strict=True)
    revision=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                            capture_output=True,text=True,check=True).stdout.strip()
    if revision!=REVISION:
        raise RootResourcePREError("SOURCE_REVISION_NOT_PINNED")
    receipt_bytes=root_receipt_path.read_bytes()
    prior=json.loads(receipt_bytes)
    if (prior.get("schema")!=ROOT_SCHEMA or
        prior.get("source_revision")!=REVISION or
        prior.get("operand_source_cpp")!="sim->active_enemies" or
        prior.get("added_ready_calls")!=0 or
        prior.get("direct_before_call_snapshot_same_simc_tick") is not True):
        raise RootResourcePREError("PREVIOUS_SOURCE_PROVENANCE_UNTRUSTED")
    filename=root/PLAYER
    before=filename.read_bytes()
    if digest(before)!=prior.get("source_after_sha256"):
        raise RootResourcePREError("SOURCE_ROOT_PRE_BYTES_CHANGED")
    original=subprocess.run(["git","-C",str(root),"show",f"{REVISION}:{PLAYER}"],
                            capture_output=True,check=True).stdout
    blob=subprocess.run(["git","-C",str(root),"rev-parse",f"{REVISION}:{PLAYER}"],
                        capture_output=True,check=True,text=True).stdout.strip()
    if (blob!=git_blob(original) or
        blob!=prior.get("official_source_blob_sha1") or
        b"resources.current[ RESOURCE_MANA ]" not in original or
        b"resources.max[ RESOURCE_MANA ]" not in original):
        raise RootResourcePREError("OFFICIAL_MANA_RESOURCE_SOURCE_UNPINNED")
    after=patch(original,before)
    filename.write_bytes(after)
    return {
        "schema":SCHEMA,"source_revision":REVISION,
        "source_path":PLAYER,"original_git_blob_sha1":blob,
        "source_before_sha256":digest(before),
        "source_after_sha256":digest(after),
        "previous_root_actor_pre_receipt_sha256":digest(receipt_bytes),
        "original_ready_calls_added":0,
        "new_rng_or_resource_mutation_calls":0,
        "source_mana_fields":["mana_current","mana_max"],
        "source_read_expressions":[
            "resources.current[ RESOURCE_MANA ]",
            "resources.max[ RESOURCE_MANA ]"
        ],
        "raw_value_format":"IEEE754_DOUBLE_17_SIGNIFICANT_DIGITS",
        "root_PRE_marker":MARK,
        "native_CPP_A_B":"NOT_RUN",
        "percentage_interpretation":"NOT_ASSESSED_IN_PRODUCER",
        "source_priority_complete":False,
        "full_READY_proven":0,"WCL_API_calls":0
    }

def selftest()->dict:
    official=(
        "action_t* player_t::select_action("+
        "const action_priority_list_t* list,\\n execute_type et,const action_t* context )\\n"+
        "{\\n if ( a->action_ready() ) {}\\n}\\n"
    ).replace("\\n","\n").encode()
    prior=(
        "action_t* player_t::select_action("+
        "const action_priority_list_t* list,\\n execute_type et,const action_t* context )\\n"+
        "{\\n // ZROT_GENERIC_ROOT_ACTOR_PRE_V1|\\n"+
        " auto root=zrot_generic_call_scope_v1::current_root();\\n"+
        "      const bool zrot_native_comparator = a->action_ready();\\n}\\n"
    ).replace("\\n","\n").encode()
    out=patch(official,prior).decode()
    assert out.count(MARK)==1
    assert out.count("a->action_ready()")==1
    assert out.index(ACTOR_MARK)<out.index(MARK)<out.index(ORIGINAL_CALL)
    assert out.count("resources.current[ RESOURCE_MANA ]")==1
    assert out.count("resources.max[ RESOURCE_MANA ]")==1
    assert "{:.17g}" in out
    for bad in (prior.replace(ORIGINAL_CALL.encode(),b"return true;"),
                out.encode(),
                prior.replace(ACTOR_MARK.encode(),b"BROKEN_ACTOR_PRE|")):
        try:patch(official,bad)
        except RootResourcePREError:pass
        else:raise AssertionError("INVALID_OR_DUPLICATE_ROOT_RESOURCE_CAPTURE_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":9,"native_CXX_executed":False,
            "full_READY_proven":0,"WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--root-actor-pre-receipt",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root is None and a.root_actor_pre_receipt is None:
        out=selftest()
    elif a.simc_root is not None and a.root_actor_pre_receipt is not None:
        out=generate(a.simc_root,a.root_actor_pre_receipt)
    else:
        p.error("root and original actor PRE source receipt required together")
    raw=canonical(out)
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as f:f.write(raw)
    else:print(raw.decode(),end="")

if __name__=="__main__":main()
