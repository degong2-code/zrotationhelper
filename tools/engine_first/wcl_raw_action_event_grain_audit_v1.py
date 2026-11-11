#!/usr/bin/env python3
"""Blind WCL successor: restore event grain from immutable raw checkpoints.

Never count begin+completion as separate player decisions. Even a completed
cast event does not certify manual input, readiness, or optimality. Preserve
existing numeric candidate lock; cast-only counts are a post-lock sensitivity
check on the same cohorts, not a new holdout or a replacement lock.
No args: safe synthetic tests. No network or SimC dependencies.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import zipfile

POLICY='ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1'
SCHEMA='ZrotWclRawActionEventGrainAuditV1'


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canon(x):
    return (json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def sha(x):
    return sha256(x).hexdigest()


def num(x):
    if type(x) is int:
        return x
    if isinstance(x, str) and x.strip().lstrip('-').isdigit():
        return int(x)
    return None


def ability(e):
    for obj, keys in ((e, ('abilityGameID','abilityID','guid')), (e.get('ability'), ('gameID','guid','id'))):
        if isinstance(obj, dict):
            for k in keys:
                n=num(obj.get(k))
                if n is not None:
                    return n
    return None


def event_key(page_sha, ordinal, event):
    return 'raw_'+sha(canon([page_sha,ordinal,event]))[:40]


def verify_digest(obj, key):
    copy=dict(obj); expected=copy.pop(key, None)
    require(sha(canon(copy))==expected,'DERIVED_DIGEST_MISMATCH:'+key)


def audit(z, role):
    def load(name):
        return json.loads(z.read(name))
    transport=load(f'results/{role}-numeric.json')
    matrix=load(f'results/{role}-matrix.json')
    verify_digest(transport,'numeric_transport_sha256')
    verify_digest(matrix,'matrix_sha256')
    require(transport['source_cohort_role']==matrix['source_role']==role.upper() and
            matrix['source_numeric_transport_sha256']==transport['numeric_transport_sha256'] and
            matrix['raw_page_identity_sha256']==transport['raw_receipt_sha256'], 'ROLE_OR_MATRIX_PROVENANCE_MISMATCH')
    actor=transport['actor_id']; start=transport['fight_start_abs_ms']
    root=f"{role}/raw/{transport['report_code']}/fight_{transport['fight_id']}/"
    ck=load(root+'checkpoint.json'); identity=ck['identity']
    require(ck['complete'] is True and identity['report_code']==transport['report_code'] and
            identity['fight_id']==transport['fight_id'] and identity['start']==start and
            identity['evidence_window']=='FIGHT_START_BOUNDED', 'CHECKPOINT_IDENTITY_MISMATCH')
    require([p['sha256'] for p in ck['pages']]==transport['raw_source_page_sha256'], 'RAW_PAGE_LEDGER_MISMATCH')
    raw={}; actions={}; total=0
    for i,p in enumerate(ck['pages']):
        require(p['file']==f'page_{i:05d}.json','UNEXPECTED_PAGE_NAME')
        b=z.read(root+p['file']); page=json.loads(b)
        require(sha(b)==p['sha256'] and page['schema']=='FreshWCLPageV1' and page['start']==p['start'] and page['next']==p['next'] and len(page['events'])==p['event_count'], 'RAW_PAGE_CHANGED')
        for n,e in enumerate(page['events']):
            eid=event_key(p['sha256'],n,e); t=e['timestamp']-start
            require(eid not in raw and type(t) is int and 0<=t<=identity['end']-start,'RAW_EVENT_ID_OR_TIME_INVALID')
            raw[eid]=e; total+=1
            kind=str(e.get('type','')).casefold(); spell=ability(e)
            if kind in ('cast','begincast') and num(e.get('sourceID'))==actor and spell is not None and spell>0:
                actions[eid]={'event_id':eid,'event_type':kind,'spell_id':spell,'t_ms':t,
                              'target_id':num(e.get('targetID')),'melee_flag':e.get('melee') is True,
                              'manual_player_input':'UNKNOWN'}
    require(total==transport['raw_event_count'],'RAW_EVENT_COUNT_MISMATCH')
    prior={x['event_id']:x for x in transport['cast_events']}
    require(len(prior)==len(transport['cast_events'])==len(actions)==transport['actor_numeric_cast_count'] and set(prior)==set(actions),'RAW_ACTION_EVENT_MEMBERSHIP_MISMATCH')
    for eid,a in actions.items():
        require((a['spell_id'],a['t_ms'])==(prior[eid]['spell_id'],prior[eid]['t_ms']),'RAW_ACTION_ID_OR_CLOCK_MISMATCH')
    rows={r['raw_cast_event_id']:r for r in matrix['per_numeric_cast']}
    require(len(rows)==len(actions)==matrix['cast_rows'] and set(rows)==set(actions),'MATRIX_EVENT_MEMBERSHIP_MISMATCH')
    transitions={x['source_event_id']:x for x in transport['transitions']}
    known=unknown=0
    for eid,row in rows.items():
        a=actions[eid]; require((row['t_ms'],row['numeric_spell_id'])==(a['t_ms'],a['spell_id']),'MATRIX_ACTION_ID_MISMATCH')
        for signal,f in row['strict_pre_signals'].items():
            if f['status']=='KNOWN':
                source=transitions.get(f['source_event_id']); ev=raw.get(f['source_event_id'])
                require(source is not None and ev is not None and num(ev.get('targetID'))==actor and
                        source['signal']==signal and source['value']==f['value'] and
                        f['event_t_ms']==source['t_ms']==ev['timestamp']-start<a['t_ms'] and
                        f['raw_receipt_sha256']==transport['raw_receipt_sha256'], 'STRICT_PRE_SOURCE_EVENT_NOT_EARLIER')
                known+=1
            else:
                require(f['status']=='UNKNOWN' and f['value'] is None,'UNKNOWN_STATE_FILLED')
                unknown+=1
    require(known==matrix['signal_status_summary'].get('KNOWN',0) and unknown==matrix['signal_status_summary'].get('UNKNOWN',0),'STRICT_PRE_COUNTS_MISMATCH')
    by_type=Counter(a['event_type'] for a in actions.values()); spell_counts={kind:Counter(a['spell_id'] for a in actions.values() if a['event_type']==kind) for kind in ('cast','begincast')}
    completed=[a for a in actions.values() if a['event_type']=='cast']; ticks=Counter(a['t_ms'] for a in completed)
    return {'role':role.upper(),'report_code':identity['report_code'],'fight_id':identity['fight_id'],'actor_id':actor,'raw_events':total,
            'action_event_count':len(actions),'cast_event_count':by_type['cast'],'begincast_event_count':by_type['begincast'],
            'cast_only_counts':dict(sorted((str(k),v) for k,v in spell_counts['cast'].items())),
            'begincast_counts':dict(sorted((str(k),v) for k,v in spell_counts['begincast'].items())),
            'raw_melee_cast_flags':sum(a['melee_flag'] for a in completed),
            'multiple_completion_events_same_timestamp':sum(n>1 for n in ticks.values()),
            'completed_event_distinct_timestamps':len(ticks),'known_strict_pre':known,'unknown_strict_pre':unknown,
            'numeric_transport_sha256':transport['numeric_transport_sha256'],'matrix_sha256':matrix['matrix_sha256'],
            'all_known_PRE_source_ids_and_times_verified':True,'event_type_sidecar':sorted(actions.values(),key=lambda a:(a['t_ms'],a['event_id'])),
            'manual_decisions':'UNKNOWN','target_count':'UNKNOWN','physical_readiness':'UNKNOWN'}


def comparison(discovery,holdout,lock,metrics,lock_sha):
    require(discovery['report_code']!=holdout['report_code'] and metrics['unchanged_discovery_lock_sha256']==lock_sha and
            not lock['semantic_names_attached'] and lock['prelocked_min_observations']==2 and not lock['threshold_retuned_after_discovery'], 'LOCK_OR_COHORT_IDENTITY_MISMATCH')
    original={str(r['action_spell_id']):r['observed_event_count'] for r in lock['candidates']}
    d=Counter(discovery['cast_only_counts'])+Counter(discovery['begincast_counts']); h=Counter(holdout['cast_only_counts'])+Counter(holdout['begincast_counts'])
    require({k:v for k,v in d.items() if v>=2}==original,'ORIGINAL_EVENT_LOCK_CHANGED')
    expected={str(x['action_spell_id']):x['holdout_observed_casts'] for x in metrics['candidate_observations']}
    require(expected=={k:h[k] for k in original},'ORIGINAL_HOLDOUT_EVENT_COUNTS_CHANGED')
    cast_only={k for k,v in discovery['cast_only_counts'].items() if v>=2}
    return {'original_lock_sha256':lock_sha,'original_locked_ids':sorted(map(int,original)),
            'cast_only_same_threshold_ids':sorted(map(int,cast_only)), 'candidate_set_unchanged_in_sensitivity_check':cast_only==set(original),
            'original_candidate_rows':[{'numeric_spell_id':int(k),'discovery_all_action_events':original[k], 'holdout_all_action_events':expected[k],
                'discovery_cast_events':discovery['cast_only_counts'].get(k,0),'holdout_cast_events':holdout['cast_only_counts'].get(k,0)} for k in sorted(original,key=int)],
            'cast_only_reobserved_original_candidates':sum(holdout['cast_only_counts'].get(k,0)>=1 for k in original),
            'metric':'POSTLOCK_CAST_EVENT_TYPE_SENSITIVITY_NOT_NEW_DISCOVERY_LOCK_OR_HOLDOUT',
            'new_lock_created':False,'threshold_retuned':False,'manual_player_input_proven':False,'priority_proven':False,'MAIN_promoted':False}


def selftest():
    require(ability({'abilityGameID':123})==123 and ability({'ability':{'gameID':'124'}})==124 and num(True) is None,'NUMERIC_ID_TEST')
    require(event_key('a'*64,0,{'type':'cast'})!=event_key('a'*64,0,{'type':'begincast'}),'GRAIN_ID_TEST')
    x={'v':1}; x['digest']=sha(canon(x)); verify_digest(x,'digest')
    try:verify_digest({**x,'v':2},'digest')
    except ValueError:pass
    else:raise AssertionError('TAMPER_ACCEPTED')
    return {'status':'PASS_SYNTHETIC_STATIC','negative_digest_control':'REJECT','network_calls':0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--discovery-zip',type=Path);p.add_argument('--holdout-zip',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    require(all(vars(a).values()),'BOTH_IMMUTABLE_ARTIFACTS_AND_OUTPUT_REQUIRED')
    with zipfile.ZipFile(a.discovery_zip) as dz, zipfile.ZipFile(a.holdout_zip) as hz:
        d=audit(dz,'discovery'); h=audit(hz,'holdout'); raw=dz.read('results/discovery-lock.json')
        result={'schema':SCHEMA,'policy_id':POLICY,'discovery_zip_sha256':sha(a.discovery_zip.read_bytes()),'holdout_zip_sha256':sha(a.holdout_zip.read_bytes()),'discovery':d,'holdout':h,
                'comparison':comparison(d,h,json.loads(raw),json.loads(hz.read('holdout/derived/holdout_observed_metrics.json')),sha(raw)), 'new_WCL_API_calls':0,'new_SimC_calls':0}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('xb') as f:f.write(canon(result))
    print(json.dumps({k:result['comparison'][k] for k in ('candidate_set_unchanged_in_sensitivity_check','cast_only_reobserved_original_candidates','original_candidate_rows')},sort_keys=True))
    print('GRAIN_AUDIT_SHA256='+sha(a.out.read_bytes()))

if __name__=='__main__':main()
