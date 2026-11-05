#!/usr/bin/env python3
"""Generic source-pinned original SimC action_t::init eligibility guard capture.

Fifth, research-only producer stage after verified generic APL INIT inventory.
Rewrites only the three existing short-circuited verify_actor_*() reads by
wrapping their actual returned Boolean in a passive logger. The guarded
original calls still execute once, in precisely the same order and under
the same C++ short-circuit structure. No added ready/resource/RNG calls.

A raw negative init guard proves source-forced background at init only.
It does not prove any later action READY or the unique reason for exclusion.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from general_rotation_apl_eligibility_instrument_v1 import SCHEMA as INIT_SCHEMA
from general_rotation_source_route_audit_v1 import (
    _bounded_body, _source_code_mask, git_blob
)
from general_rotation_select_pre_passive_producer_v1 import REVISION
from general_rotation_original_pre_capture_engine_v1 import canonical

SCHEMA="ZrotGenericOriginalActionInitGuardReturnProbeV1"
MARK="ZROT_GENERIC_APL_INIT_GUARD_V1|"
SOURCE_PATH="engine/action/action.cpp"
SOURCE_METHOD="void action_t::init()"
ORIGINAL_GUARD="if ( !verify_actor_level() || !verify_actor_spec() || !verify_actor_weapon() )"
GUARDS=("level","spec","weapon")


class InitGuardError(ValueError):
    pass


def sha(data:bytes)->str:
    return sha256(data).hexdigest()


def _body(src:str)->str:
    code=_source_code_mask(src)
    if code.count(SOURCE_METHOD)!=1:
        raise InitGuardError("ACTION_INIT_SOURCE_METHOD_MISSING_OR_AMBIGUOUS")
    body,_=_bounded_body(src,code,SOURCE_METHOD,(0,len(code)))
    return body


def patch_source(pristine:bytes,patched:bytes)->bytes:
    orig=pristine.decode("utf8")
    current=patched.decode("utf8")
    original_body=_body(orig)
    active_body=_body(current)
    if original_body!=active_body or active_body.count(ORIGINAL_GUARD)!=1:
        raise InitGuardError("EXACT_OFFICIAL_INITIALIZATION_GUARD_BODY_REQUIRED")
    if MARK in current:
        raise InitGuardError("SOURCE_ALREADY_GUARD_INSTRUMENTED")
    prefix=r"""const auto* zrot_guard_owner = this->action_list;
    std::size_t zrot_guard_ordinal = 0;
    if ( sim->log && player && !player->is_pet() && !player->is_enemy() &&
         zrot_guard_owner && this->signature )
    {
      for ( std::size_t zrot_i = 0; zrot_i < zrot_guard_owner->action_list.size(); ++zrot_i )
      {
        if ( &( zrot_guard_owner->action_list[zrot_i] ) == this->signature )
        {
          zrot_guard_ordinal = zrot_i + 1;
          break;
        }
      }
    }
    auto zrot_original_guard_result = [&](const char* zrot_guard, bool zrot_value) -> bool
    {
      if ( zrot_guard_ordinal != 0 )
      {
        sim->print_log( "ZROT_GENERIC_APL_INIT_GUARD_V1|{}|{}|{}|{}|{}",
          zrot_guard_owner->name_str, static_cast<unsigned>(zrot_guard_ordinal),
          this->name_str, zrot_guard, zrot_value ? 1 : 0 );
      }
      return zrot_value;
    };
    """
    rewritten=(
        'if ( !zrot_original_guard_result("level", verify_actor_level()) || '
        '!zrot_original_guard_result("spec", verify_actor_spec()) || '
        '!zrot_original_guard_result("weapon", verify_actor_weapon()) )'
    )
    if (rewritten.count("verify_actor_level()")!=1 or
        rewritten.count("verify_actor_spec()")!=1 or
        rewritten.count("verify_actor_weapon()")!=1):
        raise InitGuardError("ORIGINAL_GUARD_INVOCATION_COUNT_CHANGED")
    changed=active_body.replace(ORIGINAL_GUARD,prefix+rewritten,1)
    for guard in ("verify_actor_level()","verify_actor_spec()",
                  "verify_actor_weapon()"):
        if changed.count(guard)!=original_body.count(guard):
            raise InitGuardError("ADDED_SOURCE_GUARD_CALL_OR_SHORT_CIRCUIT")
    if changed.count(MARK)!=1 or changed.count("zrot_original_guard_result(")!=3:
        raise InitGuardError("GUARD_WRAPPER_OR_LOG_SITE_DRIFT")
    start=current.index(active_body)
    output=current[:start]+changed+current[start+len(active_body):]
    return output.encode("utf8")


def generate(root:Path, previous_inventory_receipt:Path,
             previous_call_scope_receipt:Path)->dict:
    r=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(r),"rev-parse","HEAD"],
                       text=True,capture_output=True,check=True).stdout.strip()
    if rev!=REVISION:
        raise InitGuardError("OFFICIAL_SIMC_SOURCE_COMMIT_MISMATCH")
    inventory=json.loads(previous_inventory_receipt.read_bytes())
    scope=json.loads(previous_call_scope_receipt.read_bytes())
    if (inventory.get("schema")!=INIT_SCHEMA or
        inventory.get("source_revision")!=REVISION or
        scope.get("source_revision")!=REVISION):
        raise InitGuardError("PINNED_PRIOR_SOURCE_PRODUCER_RECEIPTS_REQUIRED")
    match=[x for x in scope.get("source_files",[])
           if x.get("path")==SOURCE_PATH]
    if len(match)!=1:
        raise InitGuardError("PREVIOUS_ACTION_CPP_SCOPE_SOURCE_NOT_UNIQUE")
    file=r/SOURCE_PATH
    actual=file.read_bytes()
    if sha(actual)!=match[0]["after_sha256"]:
        raise InitGuardError("EXACT_PRIOR_ACTION_CPP_BYTES_REQUIRED")
    official=subprocess.run(["git","-C",str(r),"show",
        f"{REVISION}:{SOURCE_PATH}"],capture_output=True,check=True).stdout
    declared=subprocess.run(["git","-C",str(r),"rev-parse",
        f"{REVISION}:{SOURCE_PATH}"],capture_output=True,text=True,check=True).stdout.strip()
    if git_blob(official)!=declared:
        raise InitGuardError("ORIGINAL_ACTION_SOURCE_BLOB_DRIFT")
    before_body=_body(official.decode("utf8"))
    rewritten=patch_source(official,actual)
    file.write_bytes(rewritten)
    return {
        "schema":SCHEMA,"source_revision":REVISION,
        "source_path":SOURCE_PATH,
        "official_source_git_blob_sha1":git_blob(official),
        "official_init_method_body_sha256":sha(before_body.encode()),
        "prior_scope_action_source_sha256":sha(actual),
        "modified_action_source_sha256":sha(rewritten),
        "source_guard_marker":MARK,
        "original_guard_calls":["verify_actor_level",
                                "verify_actor_spec","verify_actor_weapon"],
        "original_guard_short_circuit_order_preserved":True,
        "source_guard_call_count_delta":0,
        "additional_ready_virtual_rng_calls":0,
        "actual_native_verified":False,
        "positive_action_READY_proven":0,
        "WCL_API_calls":0
    }


def selftest()->dict:
    base=(
        'void action_t::init()\n{\n'
        '  if ( initialized ) return;\n'
        '  if ( !verify_actor_level() || !verify_actor_spec() || !verify_actor_weapon() )\n'
        '  {\n    background = true;\n  }\n'
        '}\n'
    )
    value=patch_source(base.encode(),base.encode()).decode()
    for g in ("verify_actor_level()","verify_actor_spec()","verify_actor_weapon()"):
        assert value.count(g)==1
    assert value.count(MARK)==1
    assert value.count("zrot_original_guard_result(")==3
    assert "background = true;" in value
    for wrong in (
        base.replace("verify_actor_spec()","verify_other_spec()"),
        base.replace("background = true;","background = false;"),
        value,
    ):
        try:patch_source(base.encode(),wrong.encode())
        except InitGuardError:pass
        else:raise AssertionError("MUTATED_OR_DUPLICATE_INIT_GUARD_SOURCE_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":9,"original_guard_short_circuit_preserved":True,
        "actual_native_compiled":False,
        "positive_READY_certified":0,"WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--init-inventory-receipt",type=Path)
    p.add_argument("--prior-call-scope-receipt",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    args=(a.simc_root,a.init_inventory_receipt,a.prior_call_scope_receipt)
    if all(x is None for x in args):
        result=selftest()
    elif all(x is not None for x in args):
        result=generate(*args)
    else:p.error("source root and both previous receipts required")
    raw=canonical(result)
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as f:f.write(raw)
    else:print(raw.decode(),end="")


if __name__=="__main__":
    main()
