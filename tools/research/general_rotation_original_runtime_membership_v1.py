#!/usr/bin/env python3
"""Generic, source-pinned original SimC APL-to-initialized-foreground inventory.

Read-only instrumentation in original player_t::select_action() at APL entry.
For each source row, bind the exact original action_t.signature pointer and
inspect membership in list.foreground_action_list plus native flags. A row not
visited is NEVER promoted to physical NOT_READY; the original source rank and
runtime inclusion state are separate evidence dimensions.

No args runs synthetic/static tests. CLI validates a pinned patch receipt.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from general_rotation_original_candidate_stage_v1 import (
    REV, POLICY, PLAYER, START, END, STAGE, need, StageError, digest
)

SCHEMA="ZrotOriginalNativeSourceRowForegroundMembershipPatchV1"
PARENT_SCHEMA="ZrotOriginalSimCNativeCandidateStagePatchV1"
MARK="ZROT_ORIGINAL_APL_FOREGROUND_MEMBERSHIP_V1|"
ANCHOR="  for ( action_t* a : a_list )\n  {"

def patch(raw:bytes)->bytes:
    text=raw.decode("utf-8")
    need(text.count(START)==text.count(END)==1 and
         text.count(MARK)==0 and text.count(STAGE)==1 and
         "ZROT_ORIGINAL_SELECT_NATIVE_READY_RESULT_V1|" in text,
         "PINNED_CANDIDATE_STAGE_PARENT_MISSING")
    a=text.index(START);b=text.index(END,a)
    method=text[a:b]
    need(method.count(ANCHOR)==1 and
         method.count("zrot_if_ready=a->action_ready();")==1,
         "ORIGINAL_FOREGROUND_LOOP_ANCHOR_DRIFT")
    # Iterate existing source priority descriptors; the signature ptr comes
    # from original player_t::create_actions(). This is a passive READ ONLY
    # inventory at list-entry, before original candidate iteration begins.
    capture=r'''  if ( sim->log && !is_pet() && !is_enemy() &&
       et == execute_type::FOREGROUND )
  {
    for ( std::size_t zrot_idx=0; zrot_idx<list.action_list.size(); ++zrot_idx )
    {
      const auto* zrot_src_sig=&list.action_list[zrot_idx];
      const action_t* zrot_bound=nullptr;
      unsigned zrot_bound_count=0;
      for ( const auto* zrot_obj : action_list )
      {
        if ( zrot_obj && zrot_obj->signature==zrot_src_sig )
        {
          zrot_bound=zrot_obj;
          ++zrot_bound_count;
        }
      }
      int zrot_in_foreground=0;
      if ( zrot_bound )
      {
        for ( const auto* zrot_fg : list.foreground_action_list )
        {
          if ( zrot_fg==zrot_bound )
          {
            zrot_in_foreground=1;
            break;
          }
        }
      }
      sim->print_log("ZROT_ORIGINAL_APL_FOREGROUND_MEMBERSHIP_V1|{}|{}|{}|{}|{}|{}|{}|{}|{}",
        sim->current_time().total_millis(),
        static_cast<const void*>(this),list.name_str.c_str(),
        zrot_idx+1,static_cast<const void*>(zrot_bound),zrot_bound_count,
        zrot_in_foreground,zrot_bound ? ( zrot_bound->background ? 1 : 0 ) : -1,
        zrot_bound ? ( zrot_bound->sequence ? 1 : 0 ) : -1);
    }
  }
'''
    patched=text[:a]+method.replace(ANCHOR,capture+ANCHOR,1)+text[b:]
    need(patched.count(MARK)==1 and
         patched.count(STAGE)==text.count(STAGE) and
         patched.count("zrot_if_ready=a->action_ready();")==text.count("zrot_if_ready=a->action_ready();") and
         patched.count("action->queue_execute( execute_type::FOREGROUND );")==text.count("action->queue_execute( execute_type::FOREGROUND );") and
         patched.count("sequence_add( action, action->target );")==text.count("sequence_add( action, action->target );"),
         "NONPASSIVE_ORIGINAL_FOREGROUND_MUTATION")
    return patched.encode("utf-8")

def install(root:Path,prior:dict)->dict:
    root=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       check=True,capture_output=True,text=True).stdout.strip()
    need(rev==REV,"ORIGINAL_SOURCE_REVISION_DRIFT")
    path=root/PLAYER
    before=path.read_bytes()
    need(prior.get("schema")==PARENT_SCHEMA and prior.get("source_revision")==REV and
         prior.get("patched_player_sha256")==digest(before) and
         prior.get("additional_action_ready_calls")==0 and
         prior.get("additional_IF_RNG_or_queue_calls")==0,
         "ORIGINAL_CANDIDATE_STAGE_PARENT_RECEIPT_DRIFT")
    after=patch(before)
    path.write_bytes(after)
    return {"schema":SCHEMA,"policy_id":POLICY,"source_revision":REV,
            "original_player_path":PLAYER,
            "parent_sha256":digest(before),"patched_sha256":digest(after),
            "native_source_membership_marker":MARK,
            "only_original_signature_pointer_used":True,
            "original_action_ready_calls_added":0,
            "native_IF_RNG_queue_calls_added":0,
            "inspection_side_effects":"TRACE_OUTPUT_ONLY",
            "physical_READY_proven":0,"WCL_API_calls":0,
            "MAIN_promoted":False}

def selftest():
    base=(START+'\n{\n'+ANCHOR+'\n      zrot_if_ready=a->action_ready();\n}\n'+
          END+'\n// '+STAGE+'\n// ZROT_ORIGINAL_SELECT_NATIVE_READY_RESULT_V1|\n')
    edited=patch(base.encode()).decode()
    need(edited.index(MARK)<edited.index(ANCHOR) and
         edited.count("zrot_if_ready=a->action_ready();")==1 and
         "zrot_obj->signature==zrot_src_sig" in edited and
         "zrot_fg==zrot_bound" in edited,
         "SOURCE_SIGNATURE_INVENTORY_NOT_BEFORE_ORIGINAL_READY")
    failures=0
    for bad in (
        base.replace(ANCHOR,""),
        base.replace(STAGE,"NOT_THE_STAGE"),
        base.replace("ZROT_ORIGINAL_SELECT_NATIVE_READY_RESULT_V1|","NO_RESULT"),
        edited,
        base.replace("zrot_if_ready=a->action_ready();",""),
        base.replace(START,"INVALID_START")
    ):
        try:patch(bad.encode())
        except StageError:failures+=1
        else:raise AssertionError("ACCEPTED_UNPINNED_SOURCE_OR_DUPLICATE_INVENTORY")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls_rejected":failures,
            "added_original_ready_calls":0,"added_IF_RNG_queue_calls":0,
            "WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--prior-receipt",type=Path)
    p.add_argument("--out-receipt",type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(vars(a).values()),"EXPLICIT_PINNED_NATIVE_PATCH_INPUTS_REQUIRED")
    prior=json.loads(a.prior_receipt.read_bytes())
    receipt=install(a.source_root,prior)
    a.out_receipt.parent.mkdir(parents=True,exist_ok=True)
    with a.out_receipt.open("xb") as f:
        f.write(json.dumps(receipt,sort_keys=True,separators=(",",":")).encode("utf-8"))
    print("ORIGINAL_NATIVE_SOURCE_MEMBERSHIP_PATCH_SHA256="+
          sha256(a.out_receipt.read_bytes()).hexdigest())

if __name__=="__main__":main()
