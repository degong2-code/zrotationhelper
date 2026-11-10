#!/usr/bin/env python3
"""Source-neutral, passive original SimC candidate-iteration stage instrumentor.

The source-pinned original select_action() loop is not reimplemented. A single
marker before its context/background/wait/action_ready branches captures each
actual candidate's source row, iteration owner and skip/attempt mode. This
instrumentor adds ZERO action_ready/IF/RNG/queue/execute calls. No arguments
runs synthetic/static negative controls, safe in PyCharm.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

SCHEMA = 'ZrotOriginalSimCNativeCandidateStagePatchV1'
REV = 'b522cded8c26b97dac03fdf56e57a03ec7e8faa6'
POLICY = 'ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1'
PARENT_SCHEMA = 'ZrotOriginalSimCSelectedExtraPREOneNativeCallPatchV1'
PLAYER = 'engine/player/player.cpp'
START = 'action_t* player_t::select_action( const action_priority_list_t& list,'
END = '\nplayer_t* player_t::actor_by_name_str'
STAGE = 'ZROT_ORIGINAL_SELECT_CANDIDATE_STAGE_V1|'
ANCHOR = '    if ( context && a == context )\n    {\n      return nullptr;\n    }'
BG = '    if ( a->background )\n      continue;'
WAIT = '    if ( a->option.wait_on_ready == 1 )\n      break;'

class StageError(ValueError):pass

def need(v,code):
    if not v:raise StageError(code)

def digest(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()

def patch(source:bytes)->bytes:
    original=source.decode('utf-8')
    need(original.count(START)==original.count(END)==1 and
         original.count(STAGE)==0 and
         'ZROT_ORIGINAL_SELECT_EXTRA_PRE_FIELDS_V1|' in original and
         'ZROT_ORIGINAL_SELECT_NATIVE_READY_RESULT_V1|' in original,
         'PINNED_EXTRA_PRE_NATIVE_RESULT_PARENT_MISSING')
    i=original.index(START);j=original.index(END,i)
    segment=original[i:j]
    need(all(segment.count(x)==1 for x in (ANCHOR,BG,WAIT)) and
         segment.count('zrot_if_ready=a->action_ready();')==1,
         'ORIGINAL_ACTION_SELECTION_ANCHORS_DRIFT')
    # This marker is read-only. Observe the actual a pointer AFTER native
    # list.random selection, BEFORE context/background/wait early exits.
    note=r'''    if ( sim->log && !is_pet() && !is_enemy() )
    {
      unsigned zrot_stage_rank = 0;
      const char* zrot_stage_owner = "-";
      if ( a && a->action_list && a->signature )
      {
        const auto& zrot_stage_apl = *a->action_list;
        for ( std::size_t zrot_i=0; zrot_i<zrot_stage_apl.action_list.size(); ++zrot_i )
        {
          if ( &(zrot_stage_apl.action_list[zrot_i]) == a->signature )
          {
            zrot_stage_rank=static_cast<unsigned>(zrot_i+1);
            zrot_stage_owner=zrot_stage_apl.name_str.c_str();
            break;
          }
        }
      }
      const char* zrot_stage_kind = (context && a == context) ? "CONTEXT_RETURN" :
        (a->background ? "BACKGROUND_SKIP" :
        (a->option.wait_on_ready == 1 ? "WAIT_BREAK" : "ATTEMPT"));
      sim->print_log("ZROT_ORIGINAL_SELECT_CANDIDATE_STAGE_V1|{}|{}|{}|{}|{}|{}",
        sim->current_time().total_millis(),list.name_str.c_str(),
        zrot_stage_owner,zrot_stage_rank,static_cast<const void*>(a),
        zrot_stage_kind);
    }
'''
    updated=original[:i]+segment.replace(ANCHOR,note+ANCHOR,1)+original[j:]
    need(updated.count(STAGE)==1 and
         updated.count('zrot_if_ready=a->action_ready();')==original.count('zrot_if_ready=a->action_ready();') and
         updated.count('sequence_add( action, action->target );')==original.count('sequence_add( action, action->target );') and
         updated.count('action->queue_execute( execute_type::FOREGROUND );')==original.count('action->queue_execute( execute_type::FOREGROUND );'),
         'ORIGINAL_SOURCE_CONTROL_FLOW_MUTATED')
    return updated.encode('utf-8')

def install(root:Path, prior:dict)->dict:
    root=root.resolve(strict=True)
    rev=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
    need(rev==REV,'ORIGINAL_SIMC_REVISION_MISMATCH')
    path=root/PLAYER;src=path.read_bytes()
    need(prior.get('schema')==PARENT_SCHEMA and
         prior.get('source_revision')==REV and
         prior.get('updated_original_player_cpp_sha256')==digest(src) and
         prior.get('original_action_ready_cxx_call_added')==0 and
         prior.get('original_action_ready_call_count_preserved') is True,
         'EXTRA_PRE_PARENT_RECEIPT_OR_SOURCE_DRIFT')
    edited=patch(src)
    path.write_bytes(edited)
    return {'schema':SCHEMA,'policy_id':POLICY,'source_revision':REV,
            'source_file':PLAYER,'parent_player_sha256':digest(src),
            'patched_player_sha256':digest(edited),'native_candidate_marker':STAGE,
            'additional_action_ready_calls':0,'additional_IF_RNG_or_queue_calls':0,
            'runtime_candidate_stage_is_not_physical_READY':True,
            'WCL_API_calls':0,'MAIN_promoted':False}

def selftest()->dict:
    old=(START+'\n{\n for ( action_t* a : a_list )\n {\n'+ANCHOR+'\n'+BG+'\n'+WAIT+
         '\n      zrot_if_ready=a->action_ready();\n }\n}\n'+END+'\n'
         '// ZROT_ORIGINAL_SELECT_EXTRA_PRE_FIELDS_V1|\n'
         '// ZROT_ORIGINAL_SELECT_NATIVE_READY_RESULT_V1|\n')
    out=patch(old.encode()).decode()
    need(out.index(STAGE)<out.index(ANCHOR)<out.index(BG)<out.index(WAIT),
         'CANDIDATE_STAGE_AFTER_DECISION')
    need(out.count('zrot_if_ready=a->action_ready();')==1 and
         '"BACKGROUND_SKIP"' in out and '"WAIT_BREAK"' in out and
         '"CONTEXT_RETURN"' in out and '"ATTEMPT"' in out,
         'MISSING_STAGE_OR_DOUBLE_READY')
    negative=0
    variants=(old.replace(ANCHOR,''),old.replace(BG,''),old.replace(WAIT,''),
              old.replace('ZROT_ORIGINAL_SELECT_EXTRA_PRE_FIELDS_V1|','NO_EXTRA'),
              old.replace('ZROT_ORIGINAL_SELECT_NATIVE_READY_RESULT_V1|','NO_RETURN'),
              out)
    for broken in variants:
        try:patch(broken.encode())
        except StageError:negative+=1
        else:raise AssertionError('ACCEPTED_UNBOUND_OR_REPEAT_NATIVE_STAGE_INSTRUMENTATION')
    return {'schema':SCHEMA,'status':'PASS_SYNTHETIC_STATIC',
            'negative_controls':negative,'added_original_ready_calls':0,
            'added_native_RNG_calls':0,'WCL_API_calls':0}

def main():
    arg=argparse.ArgumentParser(description=__doc__)
    arg.add_argument('--source-root',type=Path)
    arg.add_argument('--prior-receipt',type=Path)
    arg.add_argument('--out-receipt',type=Path)
    a=arg.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(vars(a).values()),'EXPLICIT_PINNED_NATIVE_INPUTS_REQUIRED')
    prior=json.loads(a.prior_receipt.read_bytes())
    receipt=install(a.source_root,prior)
    a.out_receipt.parent.mkdir(parents=True,exist_ok=True)
    with a.out_receipt.open('xb') as f:f.write(json.dumps(receipt,sort_keys=True,separators=(',',':')).encode('utf-8'))
    print('ORIGINAL_NATIVE_CANDIDATE_STAGE_PATCH_SHA256='+digest(a.out_receipt.read_bytes()))

if __name__=='__main__':main()
