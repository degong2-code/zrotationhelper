#!/usr/bin/env python3
"""Passive, pinned original SimC select_action *return* witness.

Unlike a positive action_ready() result, a returned source action is an
observed native choice. Direct and child-APL propagation are distinct.
This producer never calls readiness, changes selection or claims optimality.
It does not make full READY independently observable.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_root_resource_pre_producer_v1 import SCHEMA as MANA_SCHEMA, MARK as MANA_MARK
from general_rotation_select_sweep_instrument_v1 import _method, SWEEP_MARK, RESULT_MARK
from general_rotation_select_pre_passive_producer_v1 import REVISION, PLAYER
from general_rotation_source_route_audit_v1 import git_blob

SCHEMA="ZrotOriginalNativeSourceSelectedReturnProducerV1"
MARK="ZROT_GENERIC_SOURCE_RETURN_V1|"
RETURN_SITES={
    "DIRECT":"        return a;",
    "CHILD_PROPAGATED":"          return real_a;",
    "NULL_CONTEXT":"      return nullptr;",
    "NULL_EXHAUSTED":"  return nullptr;",
}

class SourceReturnError(ValueError):
    pass

def digest(x:bytes)->str:
    return sha256(x).hexdigest()

def _log_action(kind:str, pointer:str)->str:
    if kind not in ("DIRECT","CHILD_PROPAGATED") or pointer not in ("a","real_a"):
        raise SourceReturnError("UNDECLARED_RETURN_POINTER")
    # Access only existing in-memory identity fields; do not call any
    # readiness, resource, target, RNG or action execution methods.
    return """        if ( sim->log && !is_pet() && !is_enemy() )
        {
          unsigned zrot_return_ordinal = 0;
          if ( POINTER->action_list && POINTER->signature )
          {
            const auto& zrot_return_owner = *POINTER->action_list;
            for ( std::size_t zrot_ri = 0;
                  zrot_ri < zrot_return_owner.action_list.size(); ++zrot_ri )
            {
              if ( &( zrot_return_owner.action_list[ zrot_ri ] ) == POINTER->signature )
              {
                zrot_return_ordinal = static_cast<unsigned>( zrot_ri + 1 );
                break;
              }
            }
          }
          if ( zrot_return_ordinal != 0 )
            sim->print_log(
              "ZROT_GENERIC_SOURCE_RETURN_V1|{}|{}|KIND|{}|{}|{}|{}",
              sim->current_time().total_millis(),
              zrot_generic_call_scope_v1::active_id(),
              list.name_str, POINTER->action_list->name_str,
              zrot_return_ordinal, POINTER->name_str );
        }
""".replace("POINTER",pointer).replace("KIND",kind)

def _log_null(kind:str)->str:
    if kind not in ("NULL_CONTEXT","NULL_EXHAUSTED"):
        raise SourceReturnError("UNDECLARED_NULL_SOURCE_RETURN")
    return """        if ( sim->log && !is_pet() && !is_enemy() )
          sim->print_log(
            "ZROT_GENERIC_SOURCE_RETURN_V1|{}|{}|KIND|{}|-|0|-",
            sim->current_time().total_millis(),
            zrot_generic_call_scope_v1::active_id(),list.name_str );
""".replace("KIND",kind)

def patch(pristine:bytes, previous:bytes)->bytes:
    raw=pristine.decode("utf8")
    updated=previous.decode("utf8")
    official,_=_method(raw)
    body,start=_method(updated)
    if (MANA_MARK not in body or SWEEP_MARK not in body or
        RESULT_MARK not in body or MARK in body or
        body.count("a->action_ready()")!=1 or
        official.count("a->action_ready()")!=1):
        raise SourceReturnError("PINNED_ORIGINAL_SOURCE_SELECT_METHOD_REQUIRED")
    for kind, original in RETURN_SITES.items():
        # Inspect complete original source lines: two independent null
        # statements differ only by indentation and one contains the
        # other's text as a suffix.
        if official.splitlines().count(original)!=1 or body.splitlines().count(original)!=1:
            raise SourceReturnError("ORIGINAL_RETURN_SOURCE_ANCHOR_DRIFT:"+kind)
        insertion=(_log_action(kind,"a" if kind=="DIRECT" else "real_a")
                   if kind in ("DIRECT","CHILD_PROPAGATED") else _log_null(kind))
        literal="\n"+original+"\n"
        if body.count(literal)!=1:
            raise SourceReturnError("SOURCE_RETURN_ANCHOR_NOT_LINE_EXACT:"+kind)
        body=body.replace(literal,"\n"+insertion+original+"\n",1)
    if (body.count(MARK)!=4 or body.count("a->action_ready()")!=1 or
        any(body.splitlines().count(site)!=1 for site in RETURN_SITES.values())):
        raise SourceReturnError("RETURN_PATCH_CHANGED_SELECT_SEMANTICS")
    return (updated[:start]+body+updated[start+len(_method(updated)[0]):]).encode("utf8")

def generate(root:Path, prior_receipt_path:Path)->dict:
    root=root.resolve(strict=True)
    revision=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                            capture_output=True,text=True,check=True).stdout.strip()
    if revision!=REVISION:
        raise SourceReturnError("OFFICIAL_SIMC_REVISION_DRIFT")
    receipt_bytes=prior_receipt_path.read_bytes()
    prior=json.loads(receipt_bytes)
    if (prior.get("schema")!=MANA_SCHEMA or
        prior.get("source_revision")!=REVISION or
        prior.get("root_PRE_marker")!=MANA_MARK or
        prior.get("source_path")!=PLAYER or
        prior.get("original_ready_calls_added")!=0):
        raise SourceReturnError("SOURCE_MANA_PRE_PROVENANCE_REQUIRED")
    file=root/PLAYER
    before=file.read_bytes()
    if digest(before)!=prior["source_after_sha256"]:
        raise SourceReturnError("PREVIOUS_SOURCE_BYTES_CHANGED")
    original=subprocess.run(["git","-C",str(root),"show",f"{REVISION}:{PLAYER}"],
                            capture_output=True,check=True).stdout
    if git_blob(original)!=prior["original_git_blob_sha1"]:
        raise SourceReturnError("OFFICIAL_SOURCE_BLOB_DRIFT")
    after=patch(original,before)
    file.write_bytes(after)
    return {
        "schema":SCHEMA,"source_revision":REVISION,"source_path":PLAYER,
        "original_source_blob_sha1":git_blob(original),
        "source_before_sha256":digest(before),
        "source_after_sha256":digest(after),
        "prior_mana_source_receipt_sha256":digest(receipt_bytes),
        "source_return_marker":MARK,
        "source_return_kinds":sorted(RETURN_SITES),
        "original_action_ready_call_count":1,
        "additional_action_ready_RNG_resource_calls":0,
        "original_return_paths_preserved":True,
        "complete_source_return_proven":False,
        "native_CXX_compiled":False,
        "independent_FULL_READY_proven":0,
        "WCL_API_calls":0
    }

def selftest()->dict:
    from general_rotation_select_sweep_instrument_v1 import SIGNATURE
    original=(SIGNATURE+"\n execute_type et, const action_t* context )\n{\n"
              "if ( a->action_ready() ) {}\n"
              +"\n".join(RETURN_SITES.values())+"\n}\n").encode()
    previous=(SIGNATURE+"\n execute_type et, const action_t* context )\n{\n"
              " // ZROT_GENERIC_ROOT_MANA_PRE_V1|\n"
              " // ZROT_GENERIC_SELECT_SWEEP_V1|\n"
              " // ZROT_GENERIC_READY_RESULT_V1|\n"
              "if ( a->action_ready() ) {}\n"
              +"\n".join(RETURN_SITES.values())+"\n}\n").encode()
    rewritten=patch(original,previous).decode()
    assert rewritten.count(MARK)==4
    assert rewritten.count("a->action_ready()")==1
    assert "DIRECT|{}|{}|{}|{}" in rewritten
    assert "CHILD_PROPAGATED|{}|{}|{}|{}" in rewritten
    for bad in (rewritten.encode(),previous.replace(b"return real_a;",b"return nullptr;"),
                previous.replace(b"ZROT_GENERIC_ROOT_MANA_PRE_V1|",b"REMOVED")):
        try:patch(original,bad)
        except SourceReturnError:pass
        else:raise AssertionError("UNPINNED_OR_DUPLICATE_RETURN_PATH_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":7,"native_CXX_executed":False,
            "independent_FULL_READY_proven":0,"WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--prior-mana-pre-receipt",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root is None and a.prior_mana_pre_receipt is None:
        value=selftest()
    elif a.simc_root is not None and a.prior_mana_pre_receipt is not None:
        value=generate(a.simc_root,a.prior_mana_pre_receipt)
    else:p.error("both original C++ source and pinned prior mana PRE receipt required")
    raw=canonical(value)
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as file:file.write(raw)
    else:print(raw.decode(),end="")

if __name__=="__main__":main()
