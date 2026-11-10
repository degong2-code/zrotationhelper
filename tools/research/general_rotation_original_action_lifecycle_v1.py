#!/usr/bin/env python3
"""Source-neutral, source-pinned original SimC create/init action lifecycle probe.

Captures unchanged original action_t object state at four lifecycle phases:
POST_CREATE before action_list_skip, POST_BIND after original source signature
binding, PRE_INIT before original action->init(), and POST_INIT after that
original call. No extra create/init/ready/IF/RNG calls, no action mutations.
Source descriptor and object identity are native pointer facts; not-found spell
classification is from the existing s_data pointer, NOT a new spell query.
No arguments: static/synthetic fail-closed tests, safe in PyCharm.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from general_rotation_original_runtime_membership_v1 import (
    REV, POLICY, PLAYER, SCHEMA as PARENT_SCHEMA, MARK as PARENT_MARK,
    digest,
)
SCHEMA="ZrotOriginalSimCActionCreateInitLifecycleProbeV1"
MARK="ZROT_ORIGINAL_ACTION_LIFECYCLE_V1|"
CREATE_START="void player_t::create_actions()\n{"
CREATE_END="\nnamespace\n{\n// Only \"real\" off gcd actions should trigger"
INIT_START="void player_t::init_actions()\n{"
INIT_END="\nvoid player_t::init_background_actions()"
CREATE_ANCHOR="      bool skip = false;"
POST_BIND_ANCHOR="    }\n  }\n\n  if ( sim->collect_action_sequence"
INIT_ANCHOR="      action->init();"
REQUIRED_PARENT="ZROT_ORIGINAL_SELECT_CANDIDATE_STAGE_V1|"

class LifecycleError(ValueError):pass
def need(value,reason):
    if not value:raise LifecycleError(reason)

def _emit(phase, actor_expr, act_expr, sig_expr):
    # All expression parameters are original existing pointers/state.
    # 10 trace fields: phase, actor, native action, source descriptor,
    # background, sequence, native not_found, native nil, spell-data ok,
    # signature_bound.
    return (
        '      if ( sim->log && !is_pet() && !is_enemy() )\n'
        f'        sim->print_log("{MARK}{{}}|{{}}|{{}}|{{}}|{{}}|{{}}|{{}}|{{}}|{{}}|{{}}",\n'
        f'          "{phase}",static_cast<const void*>({actor_expr}),\n'
        f'          static_cast<const void*>({act_expr}),static_cast<const void*>({sig_expr}),\n'
        f'          {act_expr}->background ? 1 : 0,{act_expr}->sequence ? 1 : 0,\n'
        f'          {act_expr}->s_data==spell_data_t::not_found() ? 1 : 0,\n'
        f'          {act_expr}->s_data==spell_data_t::nil() ? 1 : 0,\n'
        f'          {act_expr}->data().ok() ? 1 : 0,\n'
        f'          {act_expr}->signature ? 1 : 0);\n'
    )

def patch(raw:bytes)->bytes:
    before=raw.decode("utf-8")
    need(before.count(PARENT_MARK)==1 and before.count(REQUIRED_PARENT)==1 and
         MARK not in before and
         before.count(CREATE_START)==before.count(INIT_START)==1 and
         before.count(CREATE_END)==before.count(INIT_END)==1,
         "PINNED_ORIGINAL_RUNTIME_MEMBERSHIP_PARENT_REQUIRED")
    c1=before.index(CREATE_START);c2=before.index(CREATE_END,c1)
    i1=before.index(INIT_START);i2=before.index(INIT_END,i1)
    need(c1<c2<i1<i2,"ORIGINAL_PLAYER_ACTION_CREATE_INIT_FUNCTION_ORDER_DRIFT")
    create=before[c1:c2]
    init=before[i1:i2]
    need(create.count(CREATE_ANCHOR)==1 and
         create.count(POST_BIND_ANCHOR)==1 and
         create.count("a = create_action( action_name, action_options );")==1 and
         create.count("a->signature     = &( action_priority );")==1 and
         init.count(INIT_ANCHOR)==1,
         "PINNED_CREATE_SKIP_BIND_OR_INIT_CALLSITE_CHANGED")
    postcreate=_emit("POST_CREATE","this","a","&(action_priority)")
    afterbind=_emit("POST_BIND","this","a","&(action_priority)")
    # POST_CREATE: after existing create_action's null guard, before original
    # skip-list checks and signature binding. Scope has valid a.
    create=create.replace(CREATE_ANCHOR,postcreate+CREATE_ANCHOR,1)
    # POST_BIND: outside existing skip/else, inside original source row loop;
    # source descriptor pointer is owned by original apl->action_list.
    create=create.replace(POST_BIND_ANCHOR,
                          "    }\n"+afterbind+"  }\n\n  if ( sim->collect_action_sequence",1)
    preinit=_emit("PRE_INIT","this","action","action->signature")
    postinit=_emit("POST_INIT","this","action","action->signature")
    init=init.replace(INIT_ANCHOR,preinit+INIT_ANCHOR+"\n"+postinit,1)
    changed=before[:c1]+create+before[c2:i1]+init+before[i2:]
    need(changed.count(MARK)==4 and
         changed.count("a = create_action( action_name, action_options );")==
         before.count("a = create_action( action_name, action_options );") and
         changed.count("action->init();")==before.count("action->init();") and
         changed.count("a->action_ready()")==before.count("a->action_ready()") and
         changed.count("sequence_add( action, action->target );")==
         before.count("sequence_add( action, action->target );") and
         changed.count("action->queue_execute( execute_type::FOREGROUND );")==
         before.count("action->queue_execute( execute_type::FOREGROUND );"),
         "ORIGINAL_PLAYER_ACTION_BEHAVIOR_MUTATED")
    return changed.encode("utf-8")

def install(root:Path,prior:dict)->dict:
    root=root.resolve(strict=True)
    git=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       capture_output=True,text=True,check=True).stdout.strip()
    need(git==REV,"ORIGINAL_SIMC_REVISION_DRIFT")
    path=root/PLAYER;original=path.read_bytes()
    need(prior.get("schema")==PARENT_SCHEMA and
         prior.get("source_revision")==REV and
         prior.get("patched_sha256")==digest(original) and
         prior.get("original_action_ready_calls_added")==0 and
         prior.get("native_IF_RNG_queue_calls_added")==0,
         "PINNED_PARENT_RECEIPT_NOT_SAME_ORIGINAL_PLAYER_BYTES")
    updated=patch(original)
    path.write_bytes(updated)
    return {"schema":SCHEMA,"policy_id":POLICY,"source_revision":REV,
            "source_file":PLAYER,"parent_sha256":digest(original),
            "patched_sha256":digest(updated),
            "native_lifecycle_marker":MARK,
            "phases":["POST_CREATE","POST_BIND","PRE_INIT","POST_INIT"],
            "zero_additional_original_create_init_calls":True,
            "added_native_ready_or_RNG_or_queue_or_IF_calls":0,
            "no_source_semantics_in_generic":True,
            "native_not_found_spell_data_is_observed_not_requeried":True,
            "physical_READY_proven":0,"WCL_calls":0,
            "MAIN_promoted":False}

def selftest():
    create=CREATE_START+"""
 for ( auto apl : apls )
 {
    for ( auto& action_priority : apl->action_list )
    {
      a = create_action( action_name, action_options );
      a->signature     = &( action_priority );
      bool skip = false;
      if ( skip ) {}
      else {}
    }
  }

  if ( sim->collect_action_sequence
""" # restore canonical exact anchor sequence in fixture below
    create=CREATE_START+"""
    for ( auto& action_priority : apl->action_list )
    {
      a = create_action( action_name, action_options );
      a->signature     = &( action_priority );
      bool skip = false;
    }
  }

  if ( sim->collect_action_sequence
"""
    init=INIT_START+"\n  try\n  {\n      action->init();\n  }\n"
    raw=(create+CREATE_END+"\n"+init+INIT_END+"\n"+
         "// "+PARENT_MARK+"\n// "+REQUIRED_PARENT+"\n").encode()
    updated=patch(raw).decode()
    need(updated.count(MARK)==4 and
         updated.index('POST_CREATE')<updated.index(CREATE_ANCHOR) and
         updated.index('PRE_INIT')<updated.index(INIT_ANCHOR)<
         updated.index('POST_INIT') and
         updated.count('action->init();')==1 and
         updated.count('a = create_action( action_name, action_options );')==1,
         "LIFECYCLE_PROBE_IS_NOT_PASSIVE")
    negative=0
    for v in (raw.decode().replace(CREATE_START,"INVALID"),
              raw.decode().replace(CREATE_ANCHOR,""),
              raw.decode().replace(POST_BIND_ANCHOR,""),
              raw.decode().replace(INIT_ANCHOR,""),
              raw.decode().replace(PARENT_MARK,"OTHER"),
              updated):
        try:patch(v.encode())
        except LifecycleError:negative+=1
        else:raise AssertionError("UNPINNED_OR_ALREADY_PATCHED_SOURCE_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls":negative,
            "additional_original_create_init_ready_calls":0,
            "WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--prior-receipt",type=Path)
    p.add_argument("--out-receipt",type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(vars(a).values()),"EXPLICIT_PINNED_SOURCE_AND_RECEIPT_REQUIRED")
    receipt=install(a.source_root,json.loads(a.prior_receipt.read_bytes()))
    a.out_receipt.parent.mkdir(parents=True,exist_ok=True)
    with a.out_receipt.open("xb") as f:
        f.write(json.dumps(receipt,sort_keys=True,separators=(",",":")).encode())
    print("ORIGINAL_ACTION_LIFECYCLE_PATCH_SHA256="+sha256(a.out_receipt.read_bytes()).hexdigest())

if __name__=="__main__":main()
