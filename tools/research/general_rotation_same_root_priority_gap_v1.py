#!/usr/bin/env python3
"""Evidence-bounded same-root SimC decision gap from pinned, immutable CI ZIPs.

The output identifies missing strict PRE/availability questions. It NEVER infers
physical READY, an optimal skill priority, WCL consensus or a dummy mistake.
Without arguments, perform a safe static self-test (PyCharm-friendly).
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import zipfile

SCHEMA = 'ZrotGenericSameRootPriorityGapV1'
POLICY = 'ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1'
REV = 'b522cded8c26b97dac03fdf56e57a03ec7e8faa6'
NAMES = ('selected-root-exact-pre-source-if','original-native-attempt-frontier',
         'original-native-candidate-stage','original-apl-runtime-membership',
         'original-action-lifecycle')

class ProofError(ValueError):
    pass

def need(ok, label):
    if not ok:
        raise ProofError(label)

def digest(data):
    return sha256(data).hexdigest()

def archive(path, expected):
    raw = Path(path).read_bytes()
    need(digest(raw) == expected, 'IMMUTABLE_ARTIFACT_ZIP_SHA256_MISMATCH')
    return zipfile.ZipFile(path)

def extract(z, name, expected):
    raw = z.read(name)
    need(digest(raw) == expected, 'ORIGINAL_EVIDENCE_BYTE_SHA256_MISMATCH:'+name)
    return json.loads(raw)

def classify(row, member, life, prior, trait_excluded):
    need(row['physical_mechanic_ready'] == member['independent_physical_ready'] == 'UNKNOWN',
         'PHYSICAL_READY_NOT_INDEPENDENTLY_OBSERVED')
    need(life['no_gameplay_ready_inferred'] is True and
         life['instance_original_PTR_cohort_verified'] is True,
         'LIFECYCLE_COHORT_OR_READY_OVERCLAIM')
    state = row['native_visit_state']
    if trait_excluded:
        need(state == 'UNOBSERVED_IN_SAME_RUNTIME_SCAN' and
             member['runtime_membership_class'] == 'ABSENT_BACKGROUND_FLAG' and
             member['native_foreground_membership'] is False and
             life['native_spell_data_not_found_at_create'] is True and
             life['native_flags_by_phase']['POST_CREATE']['background'] is True and
             row['original_action_ready_result'] == 'NOT_CALLED',
             'TALENT_EXCLUSION_NOT_BACKED_BY_SAME_INSTANCE_NATIVE')
        return 'SOURCE_PROFILE_TALENT_EXCLUDED_NATIVE_NOT_FOUND'
    if state == 'UNOBSERVED_IN_SAME_RUNTIME_SCAN':
        need(row['original_action_ready_result'] == 'NOT_CALLED',
             'UNOBSERVED_CANDIDATE_READY_INVENTED')
        return 'UNOBSERVED_CANDIDATE_UNKNOWN'
    need(state.startswith('OBSERVED_NATIVE_ATTEMPT_') and prior is not None,
         'MISSING_PRIOR_CALL_FOR_NATIVE_ATTEMPT')
    need(row['original_action_ready_result'] == prior['original_action_ready_return'],
         'NATIVE_ORIGINAL_RESULT_MISMATCH')
    if row['source_behavior'] == 'CALL' and row['original_action_ready_result'] == 'TRUE':
        return 'OBSERVED_SOURCE_CONTROL_CALL_NOT_PRIORITY_WINNER'
    need(row['original_action_ready_result'] == 'FALSE',
         'HIGHER_NONCONTROL_ACTION_WAS_SELECTED')
    if row['independent_IF_at_ATTEMPT_PRE'] == 'FALSE':
        return 'SOURCE_IF_FALSE_AT_INDEPENDENT_PRE'
    if row['independent_IF_at_ATTEMPT_PRE'] == 'TRUE':
        return 'SOURCE_IF_TRUE_NATIVE_COMPOSITE_FALSE_MECHANIC_READY_UNKNOWN'
    if row['independent_IF_at_ATTEMPT_PRE'] == 'NO_EXPLICIT_IF':
        return 'NO_SOURCE_IF_NATIVE_COMPOSITE_FALSE_MECHANIC_READY_UNKNOWN'
    need(row['independent_IF_at_ATTEMPT_PRE'] == 'UNKNOWN',
         'UNEXPECTED_SOURCE_IF_PROOF_STATE')
    return 'SOURCE_IF_PRE_UNKNOWN_AND_MECHANIC_READY_UNKNOWN'

def inspect_case(native, talent, plan, case):
    prefix = case['artifact_prefix'].rstrip('/') + '/'
    original, frontier, stage, member, life = [
        extract(native, prefix + name + '.json', case['original_sha256'][name])
        for name in NAMES]
    selected = frontier['selected_root']
    want = case['selected_root']
    for key in ('t_ms','source_list','source_rank','source_action'):
        need(selected[key] == want[key], 'SELECTED_ROOT_PIN_MISMATCH:'+key)
    need(frontier['source_spec'] == stage['source_spec'] == member['source_spec'] ==
         life['source_spec'] == original['source_spec'] == plan['spec_key'] and
         frontier['targets'] == stage['targets'] == member['targets'] ==
         life['targets'] == original['targets'] == case['targets'],
         'SAME_SPEC_TARGET_COHORT_DRIFT')
    need(frontier['source_revision'] == stage['source_revision'] ==
         member['source_revision'] == life['source_revision'] == REV and
         original['original_SimC_source_revision'] == REV and
         frontier['source_profile_git_blob'] == original['original_profile_blob'] ==
         talent['source_profile_git_blob'] == plan['profile_git_blob'],
         'SOURCE_REVISION_OR_PROFILE_BLOB_DRIFT')
    need(stage['selected_root'] == member['selected_root'] == life['selected_root'] == selected and
         selected['native_action_ready_return'] is True and
         frontier['complete_CALL_RUN_return_stack'] == stage['full_CALL_RUN_return_stack'] == 'UNKNOWN',
         'EXACT_ROOT_OR_ROUTE_OVERCLAIM')
    for x in (stage, member, life):
        need(x['MAIN_promoted'] is False and x['dummy_wrong_cast'] == 'UNKNOWN',
             'UNAUTHORIZED_PRODUCT_PROMOTION')
    need(frontier['physical_ability_ready_independent_of_Native_result'] ==
         frontier['WoW_current_Retail_priority'] == 'UNKNOWN' and
         original['full_physical_READY_proven'] == 0 and
         life['physical_skill_READY_independently_proven'] == 0,
         'SELECTED_ACTION_PHYSICAL_READY_OVERCLAIM')
    samples = [x for x in original['selected_source_IF_samples']
               if x['original_selected_call_id'] == selected['call_id'] and
               x['original_dispatch_token'] == selected['dispatch_token'] and
               x['source_list'] == selected['source_list'] and
               x['source_rank'] == selected['source_rank'] and
               x['source_action'] == selected['source_action'] and
               x['t_ms'] == selected['t_ms']]
    need(len(samples) == 1 and samples[0]['original_physical_READY'] == 'UNKNOWN',
         'SOURCE_PRE_NOT_SAME_NATIVE_SELECTED_CALL')
    entry = frontier['original_foreground_CALL_entry']
    attempts = frontier['all_same_foreground_original_attempts_before_selected']
    matches = [x for x in attempts if x['list'] == entry['source_list'] and
               x['rank'] == entry['source_rank'] and
               x['behavior'] == 'CALL' and
               x['original_action_ready_return'] == 'TRUE' and
               x['t_ms'] == selected['t_ms']]
    need(len(matches) == 1 and entry['original_action_ready_return'] is True,
         'FOREGROUND_SOURCE_CALL_ENTRY_NOT_PROVEN')
    by_call = {x['call_id']:x for x in attempts}
    need(len(by_call) == len(attempts), 'DUPLICATED_ORIGINAL_CALL_IDS')
    rows, members, lives = (stage['source_rank_coverage'],
                            member['same_root_upper_source_rows'],
                            life['source_upper_rows_with_original_lifecycle'])
    need(len(rows) == len(members) == len(lives) == selected['source_rank'] - 1,
         'UPPER_SOURCE_ROW_COVERAGE_INCOMPLETE')
    exclusions = {x['source_rank']:x for x in case.get('source_talent_exclusions',[])}
    need(len(exclusions) == len(case.get('source_talent_exclusions',[])),
         'DUPLICATE_TALENT_EXCLUSION_RANK')
    assessment=[]
    for idx,(row,mem,life_row) in enumerate(zip(rows,members,lives),1):
        need(row['rank'] == mem['rank'] == life_row['rank'] == idx and
             row['source_action'] == mem['source_action'] == life_row['source_action'] and
             row['source_sha256'] == mem['source_sha256'] == life_row['source_sha256'] and
             row['original_action_ready_result'] == mem['original_action_ready_result'],
             'SAME_ORIGINAL_ROW_SIGNATURE_OR_ORDER_DRIFT')
        call_id = row['original_call_id']
        prior = by_call.get(call_id) if call_id is not None else None
        if prior is not None:
            need(prior['list'] == selected['source_list'] and prior['rank'] == idx and
                 prior['action'] == row['source_action'] and
                 prior['IF_independent_STRICT_CALL_PRE'] == row['independent_IF_at_ATTEMPT_PRE'],
                 'CROSS_CALL_OR_IF_PRE_LEAKAGE')
        exclusion=exclusions.get(idx)
        if exclusion:
            need(exclusion['source_action'] == row['source_action'],
                 'TRAIT_CASE_ACTION_MISMATCH')
            t=[x for x in talent['cases'] if x['trait_name'] == exclusion['trait_name'] and
               x['trait_node'] == exclusion['trait_node'] and
               x['trait_spell'] == exclusion['trait_spell']]
            need(len(t) == 1 and t[0]['source_profile_status'] ==
                 'PROFILE_NOT_SELECTED_NOT_GRANTED' and
                 t[0]['native_dependency_join'] == 'SAME_PROFILE_SPELL_INPUT_AND_NATIVE_NOT_FOUND',
                 'TRAIT_NOT_INDEPENDENTLY_EXCLUDED')
        why=classify(row,mem,life_row,prior,bool(exclusion))
        assessment.append({'rank':idx,'source_action':row['source_action'],
            'behavior':row['source_behavior'],'source_row_sha256':row['source_sha256'],
            'evidence_class':why,'native_visit_state':row['native_visit_state'],
            'native_composite_ready_return':row['original_action_ready_result'],
            'independent_source_IF_PRE':row['independent_IF_at_ATTEMPT_PRE'],
            'missing_IF_PRE_symbols': sorted(set(prior['source_IF_missing_PRE'])) if prior else [],
            'independent_physical_READY':'UNKNOWN'})
    focus=[]
    for rank in case['focus_ranks']:
        need(1 <= rank < selected['source_rank'], 'FOCUS_OUTSIDE_PRECEDING_ROWS')
        row=assessment[rank-1]
        need(row['behavior'] == 'ACTION' and
             row['evidence_class'] == 'SOURCE_IF_PRE_UNKNOWN_AND_MECHANIC_READY_UNKNOWN',
             'FOCUS_ALREADY_RESOLVED_OR_NOT_DIRECT_ACTION')
        focus.append({'rank':rank,'action':row['source_action'],
                      'exact_missing_IF_PRE_symbols':row['missing_IF_PRE_symbols'],
                      'readiness_independent_observation':'UNKNOWN',
                      'required_followup':'SAME_ORIGINAL_CALL_PRE_IF_AND_PHYSICAL_READY_OR_UNKNOWN'})
    return {'case_id':case['case_id'],'targets':case['targets'],
            'selected_root':selected,
            'selected_same_call_original_PRE_fields':samples[0]['original_PRE_fields'],
            'verified_foreground_source_CALL_entry':entry,
            'preceding_source_control_CALLS':[{'list':x['list'],'rank':x['rank'],
                   'destination':x.get('destination'),'original_native_result':x['original_action_ready_return']}
                  for x in attempts if x['behavior'] == 'CALL' and
                  x['original_action_ready_return'] == 'TRUE'],
            'full_CALL_RUN_return_stack':'UNKNOWN',
            'higher_source_rows':assessment,
            'higher_source_evidence_counts':dict(Counter(x['evidence_class'] for x in assessment)),
            'focused_missing_PRE_and_READY':focus,
            'independent_all_competitor_physical_READY':'UNKNOWN',
            'source_profile_proof_not_current_Retail':True,
            'user_general_rotation_priority_promoted':0}

def analyze(native_zip, talent_zip, cfg):
    need(cfg['schema'] == 'ZrotSameRootPriorityGapAdapterV1' and
         cfg['policy_id'] == POLICY and cfg['source_revision'] == REV and
         len(cfg['cases']) == 2 and len({x['targets'] for x in cfg['cases']}) == 2,
         'FIXTURE_SCOPE_OR_POLICY_INVALID')
    with archive(native_zip,cfg['native_zip_sha256']) as n, archive(talent_zip,cfg['talent_zip_sha256']) as t:
        talent=extract(t,cfg['talent_json_name'],cfg['talent_json_sha256'])
        need(talent['policy_id'] == POLICY and talent['source_revision'] == REV and
             talent['spec_key'] == cfg['spec_key'] and
             talent['source_profile_git_blob'] == cfg['profile_git_blob'] and
             talent['General_Rotation_priority_promoted'] == 0 and
             talent['WCL_independent_blind'] == 'NOT_RUN',
             'TRAIT_ARTIFACT_POLICY_OR_REV_DRIFT')
        cases=[inspect_case(n,talent,cfg,x) for x in cfg['cases']]
    return {'schema':SCHEMA,'policy_id':POLICY,'source_revision':REV,
            'spec_key':cfg['spec_key'],'source_profile_git_blob':cfg['profile_git_blob'],
            'native_zip_sha256':cfg['native_zip_sha256'],
            'talent_zip_sha256':cfg['talent_zip_sha256'],
            'research_level':'PINNED_ORIGINAL_SIMC_DECISION_PRE_PARTIAL',
            'cases':cases,'general_priority_and_opener':'UNKNOWN',
            'current_Retail_mechanics':'UNKNOWN',
            'WCL_independent_blind_candidate_lock':'NOT_RUN_FOR_THESE_ROOTS',
            'current_user_dummy_wrong_cast':'UNKNOWN',
            'new_general_rotation_priority_promotions':0,'MAIN_promoted':False}

def selftest():
    row={'physical_mechanic_ready':'UNKNOWN','native_visit_state':'OBSERVED_NATIVE_ATTEMPT_FALSE',
         'original_action_ready_result':'FALSE','source_behavior':'ACTION',
         'independent_IF_at_ATTEMPT_PRE':'UNKNOWN'}
    mem={'independent_physical_ready':'UNKNOWN'}
    life={'no_gameplay_ready_inferred':True,'instance_original_PTR_cohort_verified':True}
    prior={'original_action_ready_return':'FALSE'}
    need(classify(row,mem,life,prior,False)=='SOURCE_IF_PRE_UNKNOWN_AND_MECHANIC_READY_UNKNOWN',
         'POSITIVE_BOUNDED_CLASSIFICATION_FAILED')
    n=0
    for bad in ({**row,'physical_mechanic_ready':'TRUE'},
                {**row,'native_visit_state':'UNOBSERVED_IN_SAME_RUNTIME_SCAN'},
                {**row,'original_action_ready_result':'TRUE'},
                {**row,'independent_IF_at_ATTEMPT_PRE':'MADE_UP'}):
        try:classify(bad,mem,life,prior,False)
        except ProofError:n+=1
        else:raise AssertionError('ACCEPTED_INVALID_PRIORITY_PROMOTION')
    return {'schema':SCHEMA,'status':'PASS_SYNTHETIC_STATIC',
            'negative_controls_rejected':n,'new_original_native_runs':0,
            'physical_READY_promotions':0,'WCL_API_calls':0}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--native-zip',type=Path)
    ap.add_argument('--talent-zip',type=Path)
    ap.add_argument('--adapter',type=Path)
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    if not any(vars(args).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(vars(args).values()), 'ALL_PINNED_ORIGINAL_INPUTS_REQUIRED')
    cfg=json.loads(args.adapter.read_bytes())
    out=analyze(args.native_zip,args.talent_zip,cfg)
    data=(json.dumps(out,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('xb') as f:f.write(data)
    print('FOCUSED_ORIGINAL_PRIORITY_GAP_SHA256='+digest(data))
    print('FOCUSED_ORIGINAL_PRIORITY_GAP_SUMMARY='+json.dumps([
        {'case':x['case_id'],'higher_rows':len(x['higher_source_rows']),
         'focused_missing':x['focused_missing_PRE_and_READY'],
         'evidence_counts':x['higher_source_evidence_counts']} for x in out['cases']],sort_keys=True))

if __name__=='__main__':main()
