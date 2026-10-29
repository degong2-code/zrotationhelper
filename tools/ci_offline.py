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
    '02_SOURCE/runtime/raid_dps/core/coverage.py',
    '02_SOURCE/runtime/raid_dps/core/general_rotation_evaluator.py',
    '02_SOURCE/runtime/raid_dps/core/behavioral_evaluator.py',
    '02_SOURCE/validation/generalization/CROSS_SPEC_SYNTHETIC_PROBE_v1.py',
    '02_SOURCE/validation/generalization/GENERAL_ROTATION_EVALUATOR_INTERFACE_CONTRACT.json',
)


SPEC_PATHS = (
    '02_SOURCE/runtime/raid_dps/specs/__init__.py',
    '02_SOURCE/runtime/raid_dps/specs/protocol.py',
    '02_SOURCE/runtime/raid_dps/specs/enhancement_shaman/__init__.py',
    '02_SOURCE/runtime/raid_dps/specs/enhancement_shaman/adapter.py',
    '02_SOURCE/runtime/raid_dps/specs/fury_warrior/__init__.py',
    '02_SOURCE/runtime/raid_dps/specs/fury_warrior/adapter.py',
    '02_SOURCE/runtime/raid_dps/specs/unholy_dk/__init__.py',
    '02_SOURCE/runtime/raid_dps/specs/unholy_dk/adapter.py',
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


def check_source_manifest_safety() -> None:
    """Fail closed if bootstrap scope changes silently or references leave the repo."""
    assert len(SRC_PATHS) == 9, 'bootstrap source scope changed; review required'
    assert len(SRC_PATHS) == len(set(SRC_PATHS)), 'duplicate manifest path'
    root = ROOT.resolve()
    for relative in SRC_PATHS:
        path = Path(relative)
        assert not path.is_absolute() and '..' not in path.parts
        resolved = (ROOT / path).resolve(strict=True)
        assert resolved.is_relative_to(root)
        assert resolved.is_file()


def check_spec_adapter_structure() -> None:
    """Structural smoke only; frozen primitive authority and WCL are not checked."""
    from importlib import import_module
    from raid_dps.specs.protocol import SpecAdapter, validate_adapter
    assert len(SPEC_PATHS) == 8
    assert len(set(SPEC_PATHS)) == 8
    root = ROOT.resolve()
    for relative in SPEC_PATHS:
        p = Path(relative)
        assert not p.is_absolute() and '..' not in p.parts
        source = (ROOT / p).resolve(strict=True)
        assert source.is_relative_to(root)
        assert source.is_file()
        compile(source.read_bytes(), relative, 'exec', dont_inherit=True)
    sys.path.insert(0, str(PY_ROOT))
    slugs = ('enhancement_shaman', 'fury_warrior', 'unholy_dk')
    seen = set()
    for slug in slugs:
        adapter = import_module('raid_dps.specs.' + slug).ADAPTER
        assert isinstance(adapter, SpecAdapter)
        assert adapter.spec_slug not in seen
        seen.add(adapter.spec_slug)
        primitives_from_candidate = {feature.primitive for feature in adapter.state_features()}
        assert primitives_from_candidate
        # This is only a structural self-consistency test. An authoritative
        # primitive allowlist is not part of the public bootstrap snapshot.
        assert not validate_adapter(adapter, allowed_primitives=primitives_from_candidate)
        families = {family.key: family for family in adapter.action_families()}
        for override in adapter.action_overrides():
            family = families[override.family_key]
            assert set(override.when_active_action_ids).issubset(set(family.upgraded_action_ids))
            assert set(override.when_inactive_action_ids).issubset(set(family.base_action_ids))
        frozen_refs = adapter.frozen_evidence_ids()
        assert len(frozen_refs) == len(set(frozen_refs))



def check_cross_spec_runtime_bridge() -> None:
    """Adapter -> strict PRE -> generic recommendation -> behavioral outcome.

    Synthetic interface test only. READY is assigned by the fixture, not
    inferred from combat logs or the game.
    """
    from raid_dps.core import behavioral_evaluator as be
    from raid_dps.core import general_rotation_evaluator as gr
    from raid_dps.specs.enhancement_shaman import ADAPTER as enhancement
    from raid_dps.specs.fury_warrior import ADAPTER as fury
    for adapter in (enhancement, fury):
        family = next(
            f for f in adapter.action_families()
            if f.base_action_ids and f.upgraded_action_ids
        )
        feature = next(
            f for f in adapter.state_features()
            if f.key in ('maelstrom_weapon_stacks', 'rage')
        )
        state = be.StrictPreStateProvider().build(
            action_timestamp_ms=1000,
            transitions=(
                be.StateTransition(900, feature.key, 5),
                be.StateTransition(1000, feature.key, 0),
                be.StateTransition(1100, feature.key, 0),
            ),
            required_keys=(feature.key,),
        )
        assert state.excluded_same_timestamp_n == 1
        assert state.excluded_future_n == 1
        assert state.features[feature.key].value == 5
        observed = {
            key: obs.value for key, obs in state.features.items()
            if obs.status is be.ObservationStatus.OBSERVED
        }
        decision = gr.GeneralRotationEvaluator().evaluate(
            gr.DecisionState(
                1000, state.state_timestamp_max_ms, observed,
                spec_key=adapter.spec_slug,
            ),
            (
                gr.RotationRule(
                    'synthetic_bridge', 10, family.key,
                    (gr.RuleCondition(feature.key, 'ge', 5),),
                    confidence='SYNTHETIC_ONLY',
                    evidence=('synthetic_bridge',),
                ),
            ),
        )
        assert decision.recommendation is not None
        assert decision.recommendation.recommended_action == family.key
        rule = be.BehavioralRule(
            'synthetic_bridge', family.key,
            (be.RuleCondition(feature.key, 'ge', 5),),
            spec_slug=adapter.spec_slug,
        )
        actual = int(family.upgraded_action_ids[0])
        outcomes = []
        for readiness, expected, excluded in (
            (be.ReadinessStatus.READY, be.EvaluationStatus.ACTION_MATCH, False),
            (be.ReadinessStatus.UNKNOWN, be.EvaluationStatus.READINESS_UNKNOWN, True),
        ):
            fixture = be.FixtureObservation(
                adapter.spec_slug + ':' + readiness.value, 'SYNTHETIC',
                adapter.spec_slug, None, 1000, actual, state,
                {family.key: readiness},
            )
            result = be.BehavioralEvaluator().evaluate(
                rule=rule, fixture=fixture, adapter=adapter,
            )
            assert expected in result.statuses
            assert result.excluded_from_mismatch_denominator is excluded
            outcomes.append(result)
        masked = be.StrictPreStateProvider().build(
            action_timestamp_ms=1000,
            transitions=(be.StateTransition(900, feature.key, 5),),
            required_keys=(feature.key,),
            unobservable_keys=(feature.key,),
        )
        masked_fixture = be.FixtureObservation(
            adapter.spec_slug + ':masked', 'SYNTHETIC', adapter.spec_slug,
            None, 1000, actual, masked,
            {family.key: be.ReadinessStatus.READY},
        )
        unavailable = be.BehavioralEvaluator().evaluate(
            rule=rule, fixture=masked_fixture, adapter=adapter,
        )
        assert be.EvaluationStatus.STATE_UNOBSERVABLE in unavailable.statuses
        assert unavailable.excluded_from_mismatch_denominator
        outcomes.append(unavailable)
        summary = be.summarize(
            outcomes, fixture_kinds=('SYNTHETIC',) * len(outcomes),
        )
        assert summary['mismatch_denominator_n'] == 1
        assert summary['empirical_validation'] == 'NOT_RUN'
        assert summary['authority_promotion'] is False



def check_native_aura_strict_pre_coverage_boundary() -> None:
    """WCL-shaped aura events -> strict-PRE decisions; O4 full pipeline NOT_RUN."""
    from raid_dps.core import coverage, prestate
    from raid_dps.core import general_rotation_evaluator as gr
    from raid_dps.specs.enhancement_shaman import ADAPTER
    features = {feature.key: feature for feature in ADAPTER.state_features()}
    stack_ids = features['maelstrom_weapon_stacks'].identity_ids
    assert 344179 in stack_ids
    aura = prestate.AuraIdIndex((
        {'timestamp':900, 'abilityGameID':344179, 'type':'applybuffstack', 'stack':5},
        {'timestamp':1000, 'abilityGameID':344179, 'type':'removebuff'},
        {'timestamp':1005, 'abilityGameID':344179, 'type':'applybuffstack', 'stack':9},
    ))
    assert aura.latest_state_pre(stack_ids, 900) == (False, 0)
    assert aura.latest_state_pre(stack_ids, 1000) == (True, 5)
    assert aura.latest_state_pre(stack_ids, 1001) == (False, 0)
    rules = (
        gr.RotationRule('synthetic_stacks_branch', 10, 'SYNTHETIC_A',
                        (gr.RuleCondition('mw_stacks', 'ge', 5),)),
        gr.RotationRule('synthetic_fallback', 100, 'SYNTHETIC_B'),
    )
    for timestamp, last_source, expected in (
        (1000, 900, 'synthetic_stacks_branch'),
        (1001, 1000, 'synthetic_fallback'),
    ):
        _, stacks = aura.latest_state_pre(stack_ids, timestamp)
        recommendation = gr.GeneralRotationEvaluator().evaluate(
            gr.DecisionState(timestamp, last_source, {'mw_stacks':stacks},
                             spec_key=ADAPTER.spec_slug),
            rules,
        ).recommendation
        assert recommendation is not None and recommendation.rule_id == expected
    assert coverage.classify_coverage(19,20) == coverage.TRACKABLE
    assert coverage.classify_coverage(4,20) == coverage.PARTIAL
    assert coverage.classify_coverage(20,20,semantic_mask=True) == coverage.MASKED
    assert coverage.coverage_record(field='target_hp_pct_pre',covered=20,total=20,
                                    semantic_mask=True,semantic_route='UNOBSERVABLE')['status'] == coverage.MASKED



def check_simc_apl_syntax_inventory() -> None:
    """Only parse syntax, never evaluate SimC expressions or promote rules."""
    p = ROOT / 'tools/research/simc_apl_syntax_inventory.py'
    compile(p.read_bytes(), str(p), 'exec', dont_inherit=True)
    proc = subprocess.run(
        [sys.executable, '-I', '-B', str(p), '--self-test'],
        cwd=str(ROOT), capture_output=True, text=True, timeout=10,
    )
    assert proc.returncode == 0, 'SimC syntax inventory self-test failed'
    assert 'SIMC_APL_SYNTAX_SELF_TEST=PASS' in proc.stdout



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
        ('spec_adapter_structure_only', check_spec_adapter_structure),
        ('cross_spec_runtime_bridge_synthetic', check_cross_spec_runtime_bridge),
        ('source_manifest_safety', check_source_manifest_safety),
        ('native_aura_strict_pre_coverage_boundary', check_native_aura_strict_pre_coverage_boundary),
        ('simc_apl_syntax_inventory_research_only', check_simc_apl_syntax_inventory),
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
    for relative in SRC_PATHS + SPEC_PATHS + ('tools/research/simc_apl_syntax_inventory.py',):
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
        'validation_scope':'OFFLINE_SYNTHETIC_SPEC_STRUCTURE_AND_SIMC_APL_SYNTAX_ONLY',
        'simc_apl_expression_semantics':'NOT_RUN',
        'spec_adapter_authority_contract':'NOT_RUN',
        'cross_spec_empirical_validation':'NOT_RUN',
        'full_o4_pipeline':'NOT_RUN',
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
