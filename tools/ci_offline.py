#!/usr/bin/env python3
"""Offline-only zRotationHelper bootstrap CI. No product launcher or external IO."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PY_ROOT = ROOT / '02_SOURCE' / 'runtime'
ARTIFACTS = ROOT / 'ci_artifacts'
SRC_PATHS = (
    '02_SOURCE/runtime/raid_dps/__init__.py',
    '02_SOURCE/runtime/raid_dps/core/__init__.py',
    '02_SOURCE/runtime/raid_dps/core/identity.py',
    '02_SOURCE/runtime/raid_dps/core/prestate.py',
    '02_SOURCE/runtime/raid_dps/core/general_rotation_evaluator.py',
    '02_SOURCE/runtime/raid_dps/core/behavioral_evaluator.py',
    '02_SOURCE/validation/generalization/CROSS_SPEC_SYNTHETIC_PROBE_v1.py',
    '02_SOURCE/validation/generalization/GENERAL_ROTATION_EVALUATOR_INTERFACE_CONTRACT.json',
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_syntax() -> None:
    for relative in SRC_PATHS:
        if relative.endswith('.py'):
            source = (ROOT / relative).read_bytes()
            compile(source, relative, 'exec', dont_inherit=True)


def check_contract() -> None:
    obj = json.loads((ROOT / SRC_PATHS[-1]).read_text(encoding='utf-8'))
    assert obj['schema'] == 'ZraidGeneralRotationEvaluatorInterfaceContract'
    assert obj['module']['path'] == '02_SOURCE/runtime/raid_dps/core/general_rotation_evaluator.py'
    assert obj['strict_pre_contract'] == 'state_timestamp_max_ms < decision_timestamp_ms'
    assert obj['priority_contract'] == 'lower_integer_is_higher_priority'
    assert obj['integration_boundary'].startswith('state reconstruction')


def check_rotation() -> None:
    sys.path.insert(0, str(PY_ROOT))
    from raid_dps.core import general_rotation_evaluator as gr
    result = gr.synthetic_regression()
    assert result['ok'] is True
    assert len(result['checks']) == 7
    assert all(result['checks'].values())
    try:
        gr.GeneralRotationEvaluator().evaluate(
            gr.DecisionState(1000,1000,{}),
            (gr.RotationRule('safe',1,'a'),),
        )
    except gr.EvaluationContractError:
        pass
    else:
        raise AssertionError('same-timestamp decision input was accepted')


def check_behavioral_strict_pre() -> None:
    sys.path.insert(0, str(PY_ROOT))
    from raid_dps.core import behavioral_evaluator as b
    state = b.StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=[
            b.StateTransition(900, 'resource', 5),
            b.StateTransition(1000, 'resource', 100),
            b.StateTransition(1010, 'resource', 200),
            b.StateTransition(850, 'ignored', 1, valid=False),
        ],
        required_keys=('resource', 'absent'),
        unobservable_keys=('hidden',),
    )
    assert state.features['resource'].value == 5
    assert state.features['resource'].source_timestamp_ms == 900
    assert state.excluded_same_timestamp_n == 1
    assert state.excluded_future_n == 1
    assert state.invalid_transition_n == 1
    assert state.features['absent'].status == b.ObservationStatus.UNKNOWN
    assert state.features['hidden'].status == b.ObservationStatus.UNOBSERVABLE
    assert state.state_timestamp_max_ms == 900


def check_behavioral_readiness() -> None:
    sys.path.insert(0, str(PY_ROOT))
    from raid_dps.core import behavioral_evaluator as b
    from types import SimpleNamespace
    class SyntheticAdapter:
        spec_slug = 'synthetic'
        def action_families(self):
            return (
                SimpleNamespace(key='spender', base_action_ids=(100,), upgraded_action_ids=(101,)),
                SimpleNamespace(key='builder', base_action_ids=(200,), upgraded_action_ids=()),
            )
    state = b.StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=(b.StateTransition(900, 'resource', 5),),
        required_keys=('resource',),
    )
    rule = b.BehavioralRule('synthetic_rule', 'spender', (b.RuleCondition('resource','ge',5),))
    def fixture(readiness):
        return b.FixtureObservation('synthetic_fixture','SYNTHETIC','synthetic',None,1000,101,state,readiness)
    unknown = b.BehavioralEvaluator().evaluate(rule=rule,fixture=fixture({}),adapter=SyntheticAdapter())
    assert b.EvaluationStatus.READINESS_UNKNOWN in unknown.statuses
    assert unknown.excluded_from_mismatch_denominator
    known = b.BehavioralEvaluator().evaluate(rule=rule,fixture=fixture({'spender':b.ReadinessStatus.READY}),adapter=SyntheticAdapter())
    assert b.EvaluationStatus.ACTION_MATCH in known.statuses
    assert not known.excluded_from_mismatch_denominator
    summary = b.summarize((unknown,known),fixture_kinds=('SYNTHETIC',))
    assert summary['mismatch_denominator_n'] == 1
    assert summary['unknown_or_unobservable_counted_as_mismatch'] is False
    assert summary['empirical_validation'] == 'NOT_RUN'


def check_identity_import() -> None:
    sys.path.insert(0, str(PY_ROOT))
    from raid_dps.core import identity, prestate
    assert identity.event_ability_id({'abilityGameID': 101}) == 101
    assert identity.stable_ability_identity({'abilityGameID': 101}) == 'ability:101'
    assert hasattr(prestate, 'AuraIdIndex')


def check_cross_spec_self_test() -> None:
    p = ROOT / '02_SOURCE/validation/generalization/CROSS_SPEC_SYNTHETIC_PROBE_v1.py'
    proc = subprocess.run(
        [sys.executable, '-I', '-B', str(p), '--self-test'],
        cwd=str(ROOT), capture_output=True, text=True, timeout=25,
        env={k:v for k,v in os.environ.items() if k not in {'WCL_CLIENT_ID','WCL_CLIENT_SECRET','GH_TOKEN','GITHUB_TOKEN'}},
    )
    assert proc.returncode == 0
    assert 'SELF_TEST=PASS' in proc.stdout
    assert 'SELF_TEST_CASE_N=6' in proc.stdout


def check_ci_pipeline_canary() -> None:
    """One-time, isolated CI failure-path probe; no product logic is modified."""
    # Deliberate wrong expected count, corrected in the next commit after log inspection.
    assert len(SRC_PATHS) == 9, 'deliberate CI diagnostic canary'


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    results = []
    checks = (
        ('source_syntax', check_syntax),
        ('contract_shape', check_contract),
        ('rotation_7_case_synthetic', check_rotation),
        ('behavioral_strict_pre', check_behavioral_strict_pre),
        ('behavioral_readiness_unknown', check_behavioral_readiness),
        ('identity_import', check_identity_import),
        ('cross_spec_6_case_synthetic', check_cross_spec_self_test),
        ('ci_pipeline_canary', check_ci_pipeline_canary),
    )
    for name, fn in checks:
        try:
            fn()
            status = 'PASS'
        except Exception as exc:
            status = 'FAIL'
        # Do not include exception text or source excerpts in public receipts.
        results.append({'name':name,'status':status})
        print(name + ': ' + status, flush=True)
    rows = []
    for relative in SRC_PATHS:
        p = ROOT / relative
        if p.is_file():
            rows.append((relative,sha256(p.read_bytes())))
    (ARTIFACTS / 'source_sha256.txt').write_text(
        ''.join(f'{digest}  {relative}\n' for relative,digest in rows), encoding='utf-8'
    )
    ok = all(row['status'] == 'PASS' for row in results)
    receipt = {
        'schema':'zrotationhelper.bootstrap.offline-ci-receipt.v1',
        'status':'PASS' if ok else 'FAIL',
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'github_repository':os.environ.get('GITHUB_REPOSITORY','NOT_GITHUB'),
        'git_commit_sha':os.environ.get('GITHUB_SHA','NOT_GITHUB'),
        'github_run_id':os.environ.get('GITHUB_RUN_ID','NOT_GITHUB'),
        'python_version':sys.version.split()[0],
        'platform':platform.platform(),
        'source_sha256_file_sha':sha256((ARTIFACTS/'source_sha256.txt').read_bytes()),
        'checks':results,
        'validation_scope':'OFFLINE_SYNTHETIC_ONLY',
        'wcl_live':'NOT_RUN','simc_live':'NOT_RUN','windows_actual':'NOT_RUN',
        'seq637':'UNKNOWN','authority_promotion':'NONE',
    }
    (ARTIFACTS/'ci_receipt.json').write_text(
        json.dumps(receipt,sort_keys=True,indent=2)+'\n', encoding='utf-8'
    )
    print('OFFLINE_BOOTSTRAP=' + receipt['status'])
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
