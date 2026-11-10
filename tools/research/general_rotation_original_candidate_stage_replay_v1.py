#!/usr/bin/env python3
"""Generic same-root SimC candidate-stage / original-APl row coverage audit.

Source IR and prior independently produced native attempt frontier are inputs.
Original C++ VISIT/skip/break markers are joined by strict log line ordering,
action pointer, selected root dispatch and source rank; a rank not visited is
NOT physical NOT_READY. An IF_FALSE is source predicate evidence, not a causal
post-hoc explanation of an earlier failed action_ready() call.
No arguments run synthetic fail-closed tests, not a Native production proof.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from general_rotation_original_attempt_frontier_v1 import (
    parse_markers,FrontierError,need,numeric,pointer,BEGIN,SELECT,SCHEMA as FRONTIER_SCHEMA,
    POLICY,REV
)

SCHEMA='ZrotOriginalSimCNativeCandidateStageSameRootReplayV1'
MARK='ZROT_ORIGINAL_SELECT_CANDIDATE_STAGE_V1|'
STAGES=('ATTEMPT','BACKGROUND_SKIP','WAIT_BREAK','CONTEXT_RETURN')

class StageReplayError(ValueError):pass

def require(ok,code):
    if not ok:raise StageReplayError(code)

def load_stages(log:str):
    stages=[]
    for line_n,line in enumerate(log.splitlines()):
        if MARK not in line:continue
        require(line.count(MARK)==1,'MULTIPLE_NATIVE_CANDIDATE_STAGE_PREFIX')
        p=line.split(MARK,1)[1].strip().split('|')
        require(len(p)==6 and p[5] in STAGES and p[2] and p[1] and
                (p[2]=='-' or p[2].replace('_','').isalnum()),
                'NATIVE_CANDIDATE_STAGE_INVALID_ARITY_OR_KIND')
        t,active,owner,raw_rank,raw_ptr,kind=p
        rank=numeric(raw_rank)
        require((rank==0)==(owner=='-'),'NATIVE_CANDIDATE_POINTER_ROW_UNRESOLVED')
        stages.append({'line':line_n,'t_ms':numeric(t),
                       'active_list':active,'source_list':owner,
                       'source_rank':rank,'ptr':pointer(raw_ptr),'stage':kind})
    require(bool(stages) and len(stages)<=100000,'EMPTY_OR_UNBOUNDED_NATIVE_CANDIDATE_TRACE')
    return stages

def replay(log:str,source:dict,frontier:dict):
    require(frontier.get('schema')==FRONTIER_SCHEMA and
            frontier.get('policy_id')==POLICY and
            frontier.get('source_revision')==REV and
            frontier.get('physical_ability_ready_independent_of_Native_result')=='UNKNOWN' and
            frontier.get('WoW_current_Retail_priority')=='UNKNOWN' and
            source.get('schema')=='ZrotSourceFaithfulSimcAplSemanticIRV2',
            'UNPINNED_FRONTIER_OR_SOURCE_IR')
    begin,root_returns,pre,extra,returns=parse_markers(log)
    stages=load_stages(log)
    chosen=frontier['selected_root']
    dispatch=chosen['dispatch_token']
    require(dispatch in begin and dispatch in root_returns,
            'SAME_NATIVE_FOREGROUND_DISPATCH_MISSING')
    start=begin[dispatch];end=root_returns[dispatch]
    require(start[0]<end[0] and start[2]==end[2] and
            start[1]<=chosen['t_ms']==end[1],
            'NATIVE_ROOT_TIME_ACTOR_IDENTITY_CONFLICT')
    events=[x for x in stages if start[0]<x['line']<end[0]]
    attempts=sorted([x for x in pre.values() if start[0]<x['line']<end[0]],
                    key=lambda x:x['line'])
    require(events and attempts and len(events)<=400 and len(attempts)<=400,
            'MISSING_OR_UNBOUNDED_SAME_ROOT_CANDIDATES')
    previous=frontier['all_same_foreground_original_attempts_before_selected']
    require(len(previous)==len(attempts) and
            [x['call_id'] for x in previous]==[x['call_id'] for x in attempts],
            'FOREIGN_PRIOR_NATIVE_ATTEMPT_COHORT')
    # Bind every original attempt to the last and ONLY preceding candidate stage
    # without relying on timestamp uniqueness or selected-name inference.
    matched={};unresolved=[]
    for index,event in enumerate(events):
        after=events[index+1]['line'] if index+1<len(events) else end[0]
        covered=[a for a in attempts if event['line']<a['line']<after]
        require(len(covered)==(1 if event['stage']=='ATTEMPT' else 0),
                'VISIT_STAGE_AND_ORIGINAL_READY_CALL_NOT_ONE_TO_ONE')
        if covered:
            a=covered[0]
            require(a['t_ms']==event['t_ms'] and a['ptr']==event['ptr'] and
                    a['list']==event['source_list'] and a['rank']==event['source_rank'] and
                    event['active_list']==event['source_list'] and
                    a['call_id'] not in matched,
                    'STAGE_NOT_THE_EXACT_SOURCE_PRE_ACTION')
            matched[a['call_id']]=event
        else:unresolved.append(event)
    require(set(matched)=={x['call_id'] for x in attempts},
            'MISSING_NATIVE_ATTEMPT_STAGE_MATCH')
    for x,y in zip(attempts,previous):
        require((returns[x['call_id']][3] and y['original_action_ready_return']=='TRUE') or
                (not returns[x['call_id']][3] and y['original_action_ready_return']=='FALSE'),
                'PREVIOUS_NATIVE_RESULT_MISMATCH')
    selected_id=chosen['call_id'];sel_event=matched.get(selected_id)
    require(sel_event and selected_id==attempts[-1]['call_id'] and
            chosen['native_action_ready_return'] is True and
            returns[selected_id][3] and
            sel_event['source_list']==chosen['source_list'] and
            sel_event['source_rank']==chosen['source_rank'] and
            sel_event['ptr']==end[3],
            'SELECTED_ORIGINAL_ACTION_NOT_LAST_ATTEMPTED_READY')
    lists=source['action_lists']
    chosen_list=chosen['source_list'];rank=chosen['source_rank']
    require(chosen_list in lists and 1<=rank<=len(lists[chosen_list]) and
            lists[chosen_list][rank-1]['action']==chosen['source_action'],
            'SOURCE_LIST_OR_SELECTED_ROW_DRIFT')
    prior_map={p['call_id']:p for p in previous}
    rows=[]
    for n in range(1,rank):
        source_row=lists[chosen_list][n-1]
        visited=[x for x in events if x['source_list']==chosen_list and x['source_rank']==n]
        status='UNOBSERVED_IN_SAME_RUNTIME_SCAN'
        original_ready='NOT_CALLED';independent_if='UNKNOWN';decision_call_id=None
        if len(visited)==1:
            x=visited[0]
            if x['stage']=='ATTEMPT':
                candidate=[call for call,ev in matched.items() if ev is x]
                require(len(candidate)==1,'SOURCE_ROW_ATTEMPT_NOT_JOINED')
                decision_call_id=candidate[0]
                record=prior_map[decision_call_id]
                require(record['list']==chosen_list and record['rank']==n,
                        'UPSTREAM_SOURCE_ROW_NOT_SAME_CANDIDATE')
                original_ready=record['original_action_ready_return']
                independent_if=record['IF_independent_STRICT_CALL_PRE']
                status='OBSERVED_NATIVE_ATTEMPT_'+original_ready
            else:status='OBSERVED_'+x['stage']
        elif len(visited)>1:
            status='MULTIPLE_NATIVE_ITERATIONS_UNKNOWN'
        rows.append({'rank':n,'source_action':source_row['action'],
                     'source_behavior':source_row['behavior'],
                     'source_sha256':source_row['source_sha256'],
                     'native_visit_state':status,'original_action_ready_result':original_ready,
                     'independent_IF_at_ATTEMPT_PRE':independent_if,
                     'original_call_id':decision_call_id,
                     'physical_mechanic_ready':'UNKNOWN'})
    counts=dict(Counter(x['native_visit_state'] for x in rows))
    unknown=[x['rank'] for x in rows if x['native_visit_state']=='UNOBSERVED_IN_SAME_RUNTIME_SCAN']
    return {'schema':SCHEMA,'policy_id':POLICY,'source_revision':REV,
            'source_spec':frontier['source_spec'],'targets':frontier['targets'],
            'same_foreground_dispatch_token':dispatch,
            'selected_root':chosen,'native_candidate_stage_count':len(events),
            'same_root_action_ready_attempts':len(attempts),
            'every_attempt_has_exact_stage_pre_return':True,
            'source_rank_coverage':rows,'source_rank_visit_counts':counts,
            'source_higher_ranks_without_native_visit':unknown,
            'unknown_source_rank_is_not_NOT_READY':True,
            'native_post_not_independent_physical_ready':True,
            'full_CALL_RUN_return_stack':'UNKNOWN',
            'WCL_blind_holdout':'NOT_RUN',
            'current_Retail_priority':'UNKNOWN',
            'opener_end':'UNKNOWN','dummy_wrong_cast':'UNKNOWN',
            'MAIN_promoted':False}

def selftest():
    from general_rotation_original_attempt_frontier_v1 import (
        PRE,EXTRA,RESULT,SCHEMA as FS, POLICY,REV
    )
    def row(act,behavior='ACTION'):
        return {'action':act,'behavior':behavior,'source_sha256':'sha-'+act}
    source={'schema':'ZrotSourceFaithfulSimcAplSemanticIRV2',
            'action_lists':{'default':[row('variable','VARIABLE'),row('call_action_list','CALL')],
                            'child':[row('a'),row('b'),row('c'),row('d')]}}
    original=[{'call_id':n,'t_ms':100,'list':li,'rank':rank,
               'original_action_ready_return':'TRUE' if res else 'FALSE',
               'IF_independent_STRICT_CALL_PRE':'UNKNOWN'}
              for n,li,rank,res in ((7,'default',1,1),(8,'default',2,1),
                                     (9,'child',2,0),(10,'child',4,1))]
    frontier={'schema':FS,'policy_id':POLICY,'source_revision':REV,
              'physical_ability_ready_independent_of_Native_result':'UNKNOWN',
              'WoW_current_Retail_priority':'UNKNOWN','targets':1,'source_spec':'fictional',
              'all_same_foreground_original_attempts_before_selected':original,
              'selected_root':{'t_ms':100,'call_id':10,'dispatch_token':1,
                   'native_action_ready_return':True,'source_action':'d',
                   'source_list':'child','source_rank':4}}
    events=[BEGIN+'100|1|0x01']
    def visit(owner,rank,ptr,stage,call=None,yes=False):
        events.append(MARK+f'100|{owner}|{owner}|{rank}|{ptr}|{stage}')
        if call is not None:
            events.extend((PRE+f'100|{call}|{owner}|{rank}|{ptr}|0|0',
                           EXTRA+f'100|{call}|{ptr}|'+'a'*64+'|1|1',
                           RESULT+f'100|{call}|{ptr}|{1 if yes else 0}'))
    visit('default',1,'0x11','ATTEMPT',7,True)
    visit('default',2,'0x22','ATTEMPT',8,True)
    visit('child',1,'0x31','BACKGROUND_SKIP')
    visit('child',2,'0x32','ATTEMPT',9,False)
    visit('child',4,'0x34','ATTEMPT',10,True)
    events.append(SELECT+'100|1|0x01|0x34')
    raw='\n'.join(events)
    result=replay(raw,source,frontier)
    evidence=result['source_rank_coverage']
    require([x['native_visit_state'] for x in evidence]==[
       'OBSERVED_BACKGROUND_SKIP','OBSERVED_NATIVE_ATTEMPT_FALSE',
       'UNOBSERVED_IN_SAME_RUNTIME_SCAN'],
       'EXPECTED_BACKGROUND_FALSE_UNOBSERVED_NOT_CLASSIFIED')
    negative=0
    variants=[raw.replace(MARK+'100|child|child|2|0x32|ATTEMPT',''),
              raw.replace(MARK+'100|child|child|2|0x32|ATTEMPT',MARK+'100|child|child|2|0x32|BACKGROUND_SKIP'),
              raw.replace(MARK+'100|child|child|2|0x32|ATTEMPT',MARK+'100|child|child|2|0xab|ATTEMPT'),
              raw.replace(MARK+'100|child|child|2|0x32|ATTEMPT',MARK+'101|child|child|2|0x32|ATTEMPT'),
              raw.replace(MARK+'100|child|child|4|0x34|ATTEMPT',''),
              raw.replace(MARK+'100|child|child|4|0x34|ATTEMPT',MARK+'100|child|child|4|0x34|WAIT_BREAK'),
              raw.replace(SELECT+'100|1|0x01|0x34',SELECT+'100|1|0x01|0x32')]
    for bad in variants:
        try:replay(bad,source,frontier)
        except (FrontierError,StageReplayError):negative+=1
        else:raise AssertionError('ACCEPTED_FOREIGN_STAGE_OR_MISSING_ORIGINAL_READY')
    return {'schema':SCHEMA,'status':'PASS_SYNTHETIC_STATIC',
            'negative_controls':negative,'higher_source_ranks':3,
            'unobserved_rank_NOT_READY_proven':0,'WCL_API_calls':0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native-log',type=Path)
    p.add_argument('--profile',type=Path)
    p.add_argument('--prior-frontier',type=Path)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    if all(v is None for v in vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    require(all(v is not None for v in vars(a).values()),'EXPLICIT_NATIVE_STAGE_INPUTS_REQUIRED')
    from simc_apl_semantic_ir_v2 import parse_profile,canonical,git_blob
    prior=json.loads(a.prior_frontier.read_bytes());raw=a.profile.read_bytes()
    require(git_blob(raw)==prior['source_profile_git_blob'],'PROFILE_GIT_BLOB_DRIFT')
    out=replay(a.native_log.read_text('utf-8'),parse_profile(raw,require_source=False),prior)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('xb') as f:f.write(canonical(out))
    print('ORIGINAL_NATIVE_CANDIDATE_STAGE_REPLAY_SHA256='+sha256(a.out.read_bytes()).hexdigest())
    print('ORIGINAL_NATIVE_CANDIDATE_STAGE_COUNTS='+json.dumps({
        'targets':out['targets'],'stage_count':out['native_candidate_stage_count'],
        'attempts':out['same_root_action_ready_attempts'],
        'source_rank_visit_counts':out['source_rank_visit_counts'],
        'source_higher_ranks_without_native_visit':out['source_higher_ranks_without_native_visit']},sort_keys=True))

if __name__=='__main__':main()
