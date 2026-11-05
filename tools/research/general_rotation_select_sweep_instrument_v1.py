#!/usr/bin/env python3
"""Original-source generic select_action invocation-boundary trace.

Each invocation gets an RAII sweep ID, parent ID and execution-mode context.
Existing original action_ready call remains exactly once; its return is a
POST comparator, never independent readiness proof. No additional RNG or
game-mechanic method calls. Prior producer bytes, original source and version
are verified before modifying a temporary source checkout.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_call_scope_instrument_v1 import SCHEMA as CALL_SCOPE_SCHEMA, TRACE_MARK, SKIP_MARK
from general_rotation_apl_eligibility_instrument_v1 import SCHEMA as INIT_SCHEMA
from general_rotation_source_route_audit_v1 import _bounded_body, _source_code_mask, git_blob
from general_rotation_select_pre_passive_producer_v1 import REVISION, PLAYER

SCHEMA="ZrotGenericOriginalSelectionSweepSourceProducerV1"
SWEEP_MARK="ZROT_GENERIC_SELECT_SWEEP_V1|"
RESULT_MARK="ZROT_GENERIC_READY_RESULT_V1|"
WAIT_MARK="ZROT_GENERIC_SELECT_WAIT_V1|"
SIGNATURE="action_t* player_t::select_action( const action_priority_list_t& list,"
LOOP="  for ( action_t* a : a_list )"
WAIT_SOURCE="    if ( a->option.wait_on_ready == 1 )\n      break;"

class SweepInstrumentError(ValueError): pass

def _sha(raw:bytes)->str: return sha256(raw).hexdigest()

def _method(src:str)->tuple[str,int]:
    mask=_source_code_mask(src)
    return _bounded_body(src,mask,SIGNATURE,(0,len(src)))

def patch_source(pristine:bytes,previous:bytes)->bytes:
    original=pristine.decode("utf8")
    source=previous.decode("utf8")
    official,_=_method(original)
    body,start=_method(source)
    if (official.count(LOOP)!=1 or official.count(WAIT_SOURCE)!=1 or
        body.count(LOOP)!=1 or body.count(WAIT_SOURCE)!=1 or
        body.count("return a->action_ready();")!=1 or
        body.count(TRACE_MARK)!=1 or body.count(SKIP_MARK)!=1 or
        any(marker in body for marker in (SWEEP_MARK,RESULT_MARK,WAIT_MARK))):
        raise SweepInstrumentError("PINNED_SOURCE_SWEEP_AND_PRIOR_SCOPE_REQUIRED")
    # Outer make_scope(selection=false) changes active parent, not the
    # action_ready root. Scoped method tracing stays inside a ready call.
    sweep=r"""  auto zrot_select_sweep = zrot_generic_call_scope_v1::make_scope(
    sim->log && !is_pet() && !is_enemy(),
    false,
    [&](const char* zrot_event, std::uint64_t zrot_id,
        std::uint64_t zrot_parent, std::uint64_t zrot_root) {
      sim->print_log(
        "ZROT_GENERIC_SELECT_SWEEP_V1|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}",
        sim->current_time().total_millis(),zrot_event,
        zrot_id,zrot_parent,zrot_root,list.name_str,
        static_cast<int>(et),list.random,
        current.skill - current.skill_debuff,a_list.size());
    } );
"""
    body=body.replace(LOOP,sweep+LOOP,1)
    wait=r"""    if ( a->option.wait_on_ready == 1 )
    {
      if ( sim->log && !is_pet() && !is_enemy() )
        sim->print_log( "ZROT_GENERIC_SELECT_WAIT_V1|{}|{}|{}|{}",
          sim->current_time().total_millis(),
          zrot_generic_call_scope_v1::active_id(),list.name_str,a->name_str );
      break;
    }"""
    body=body.replace(WAIT_SOURCE,wait,1)
    skip_old='"ZROT_GENERIC_SELECT_SKIP_V1|{}|{}|{}|{}|BACKGROUND",'
    skip_new='"ZROT_GENERIC_SELECT_SKIP_V1|{}|{}|{}|{}|BACKGROUND|{}",'
    tail_old="static_cast<unsigned>( zrot_skip_index + 1 ),a->name_str );"
    tail_new=("static_cast<unsigned>( zrot_skip_index + 1 ),a->name_str,\n"
              "              zrot_generic_call_scope_v1::active_id() );")
    if body.count(skip_old)!=1 or body.count(tail_old)!=1:
        raise SweepInstrumentError("PRIOR_SOURCE_BACKGROUND_SKIP_MARKER_DRIFT")
    body=body.replace(skip_old,skip_new,1).replace(tail_old,tail_new,1)
    original_call="      return a->action_ready();"
    logged=r"""      const bool zrot_native_comparator = a->action_ready();
      if ( sim->log && !is_pet() && !is_enemy() &&
           zrot_generic_call_scope_v1::current_root() != 0 )
        sim->print_log( "ZROT_GENERIC_READY_RESULT_V1|{}|{}|{}",
          sim->current_time().total_millis(),
          zrot_generic_call_scope_v1::current_root(),
          zrot_native_comparator ? 1 : 0 );
      return zrot_native_comparator;"""
    if body.count(original_call)!=1:
        raise SweepInstrumentError("ORIGINAL_ACTION_READY_RETURN_SHAPE_DRIFT")
    body=body.replace(original_call,logged,1)
    if (body.count("a->action_ready()")!=1 or
        any(body.count(x)!=1 for x in (SWEEP_MARK,RESULT_MARK,WAIT_MARK,SKIP_MARK))):
        raise SweepInstrumentError("ORIGINAL_CALL_COUNT_OR_TRACE_MARKER_DRIFT")
    return (source[:start]+body+source[start+len(_method(source)[0]):]).encode()

def generate(root:Path,call_receipt_path:Path,init_receipt_path:Path)->dict:
    r=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(r),"rev-parse","HEAD"],text=True,
        capture_output=True,check=True).stdout.strip()
    if rev!=REVISION:raise SweepInstrumentError("ORIGINAL_SOURCE_REVISION_DRIFT")
    call=json.loads(call_receipt_path.read_bytes())
    init=json.loads(init_receipt_path.read_bytes())
    if (call.get("schema")!=CALL_SCOPE_SCHEMA or
        call.get("source_revision")!=REVISION or
        init.get("schema")!=INIT_SCHEMA or init.get("source_revision")!=REVISION or
        init.get("source_path")!=PLAYER or
        init.get("source_action_ready_call_count_delta")!=0 or
        call.get("original_action_ready_call_count")!=1 or
        call.get("new_action_ready_calls")!=0):
        raise SweepInstrumentError("EXACT_PRIOR_PRODUCER_RECEIPTS_REQUIRED")
    file=r/PLAYER
    previous=file.read_bytes()
    if _sha(previous)!=init["source_after_sha256"]:
        raise SweepInstrumentError("PRIOR_SOURCE_BYTES_DRIFT")
    pristine=subprocess.run(["git","-C",str(r),"show",f"{REVISION}:{PLAYER}"],
        capture_output=True,check=True).stdout
    blob=subprocess.run(["git","-C",str(r),"rev-parse",f"{REVISION}:{PLAYER}"],
        text=True,capture_output=True,check=True).stdout.strip()
    if git_blob(pristine)!=blob:
        raise SweepInstrumentError("OFFICIAL_SOURCE_GIT_BLOB_DRIFT")
    modified=patch_source(pristine,previous)
    file.write_bytes(modified)
    return {"schema":SCHEMA,"source_revision":REVISION,"source_path":PLAYER,
        "official_source_git_blob_sha1":blob,
        "source_before_sha256":_sha(previous),"source_after_sha256":_sha(modified),
        "source_sweep_marker":SWEEP_MARK,
        "source_result_comparator_marker":RESULT_MARK,
        "source_wait_skip_marker":WAIT_MARK,
        "source_background_skip_marker":SKIP_MARK,
        "source_original_action_ready_call_count":1,
        "additional_action_ready_calls":0,"additional_rng_calls":0,
        "source_temporal_frontier_complete":False,
        "positive_FULL_READY_certified":0,"actual_native_compiled":False,
        "WCL_API_calls":0}

def selftest()->dict:
    # Exercise the source acceptance gate with minimum official-like text.
    official=(SIGNATURE+'\n                                    execute_type et,\n'+
        '                                    const action_t* context )\n{\n'+
        '  for ( action_t* a : a_list )\n'+
        '  {\n'+WAIT_SOURCE+'\n'+
        '    if ( a->action_ready() ) { return a; }\n  }\n}\n')
    previous=official.replace(
        '    if ( a->action_ready() ) { return a; }',
        '    if ( ([&]() -> bool {\n      return a->action_ready();\n'
        '    })() ) { return a; }')
    # Missing previously pinned source skip/call marker must be rejected.
    for invalid in (previous,previous.replace("a->action_ready()","true")):
        try:patch_source(official.encode(),invalid.encode())
        except SweepInstrumentError:pass
        else:raise AssertionError("UNPINNED_READY_SWEEP_SOURCE_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":2,"actual_compiled":False,
        "positive_READY_certified":0,"WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--call-scope-receipt",type=Path)
    p.add_argument("--init-inventory-receipt",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    req=(a.simc_root,a.call_scope_receipt,a.init_inventory_receipt)
    if all(x is None for x in req):result=selftest()
    elif all(x is not None for x in req):result=generate(*req)
    else:p.error("all three source inputs required together")
    payload=canonical(result)
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as f:f.write(payload)
    else:print(payload.decode(),end="")

if __name__=="__main__":main()
