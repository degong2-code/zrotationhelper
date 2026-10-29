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




def check_simc_apl_condition_strict_pre() -> None:
    """SimC-specific operators, missing states, strict PRE; no advice."""
    p = ROOT / 'tools/research/simc_apl_condition_research.py'
    compile(p.read_bytes(), str(p), 'exec', dont_inherit=True)
    proc = subprocess.run(
        [sys.executable, '-B', str(p), '--self-test'],
        cwd=str(ROOT), capture_output=True, text=True, timeout=20,
        env={k:v for k,v in os.environ.items() if k not in
             {'WCL_CLIENT_ID','WCL_CLIENT_SECRET','GH_TOKEN','GITHUB_TOKEN'}},
    )
    assert proc.returncode == 0, 'SimC condition Strict-PRE self-test failed'
    assert 'SIMC_APL_CONDITION_STRICT_PRE_SELF_TEST=PASS' in proc.stdout




def check_simc_wcl_post_lock_guard_replay() -> None:
    """Numeric blind candidate lock + SimC guard replay, research-only."""
    p = ROOT / 'tools/research/post_lock_simc_wcl_guard_replay.py'
    compile(p.read_bytes(), str(p), 'exec', dont_inherit=True)
    proc = subprocess.run(
        [sys.executable, '-B', str(p)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=20,
        env={k:v for k,v in os.environ.items() if k not in
             {'WCL_CLIENT_ID','WCL_CLIENT_SECRET','GH_TOKEN','GITHUB_TOKEN'}},
    )
    assert proc.returncode == 0, 'post-lock SimC/WCL guard replay self-test failed'
    assert 'POST_LOCK_SIMC_WCL_GUARD_REPLAY_SELF_TEST=PASS' in proc.stdout




def check_simc_generic_source_hypothesis() -> None:
    """Generic SimC effective APL capture/ingest contract; executable live NOT_RUN."""
    p = ROOT / 'tools/research/simc_apl_source_engine.py'
    compile(p.read_bytes(), str(p), 'exec', dont_inherit=True)
    proc = subprocess.run(
        [sys.executable, '-B', str(p), '--self-test'],
        cwd=str(ROOT), capture_output=True, text=True, timeout=20,
        env={k:v for k,v in os.environ.items() if k not in
             {'WCL_CLIENT_ID','WCL_CLIENT_SECRET','GH_TOKEN','GITHUB_TOKEN'}},
    )
    assert proc.returncode == 0, 'generic source acquisition self-test failed'
    assert 'SIMC_GENERIC_SOURCE_HYPOTHESIS_SELF_TEST=PASS' in proc.stdout




def check_simc_apl_ordered_priority() -> None:
    """Research-only APL order, nested list and variable evaluation."""
    p = ROOT / 'tools/research/simc_apl_priority_trace.py'
    compile(p.read_bytes(), str(p), 'exec', dont_inherit=True)
    proc = subprocess.run(
        [sys.executable, '-B', str(p)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=20,
        env={k:v for k,v in os.environ.items() if k not in
             {'WCL_CLIENT_ID','WCL_CLIENT_SECRET','GH_TOKEN','GITHUB_TOKEN'}},
    )
    assert proc.returncode == 0, 'SimC APL priority traversal failed'
    assert 'SIMC_APL_ORDERED_PRIORITY_TRAVERSAL_SELF_TEST=PASS' in proc.stdout




def check_simc_source_to_priority_file_cli() -> None:
    """Offline end-to-end: exported APL file -> model -> Strict PRE -> JSON."""
    import tempfile
    source_engine = ROOT / 'tools/research/simc_apl_source_engine.py'
    priority_engine = ROOT / 'tools/research/simc_apl_priority_trace.py'
    env = {k:v for k,v in os.environ.items() if k not in
           {'WCL_CLIENT_ID','WCL_CLIENT_SECRET','GH_TOKEN','GITHUB_TOKEN'}}
    with tempfile.TemporaryDirectory(prefix='zrot_apl_cli_') as td:
        workspace=Path(td)
        source=workspace/'input.simc'
        model=workspace/'model.json'
        snapshot=workspace/'state.json'
        source.write_text(
            'spec=enhancement\n'
            'actions=variable,name=gate,op=set,value=4\n'
            'actions+=/stormstrike,if=active_enemies>=2&'
            'buff.foo.stack>=variable.gate\n'
            'actions+=/lava_lash\n', encoding='utf-8')
        ingest=subprocess.run(
            [sys.executable,'-B',str(source_engine),'--spec','enhancement',
             '--actions-file',str(source),'--out',str(model)],
            cwd=str(ROOT),capture_output=True,text=True,timeout=15,env=env)
        assert ingest.returncode == 0, 'source ingestion CLI failed'
        data=json.loads(model.read_text(encoding='utf-8'))
        assert data['apl_row_count'] == 3
        assert data['actionable_general_rotation'] is False
        sample={
            'spec_slug':'enhancement','decision_timestamp_ms':1000,
            'transitions':[
                {'timestamp_ms':900,'key':'targets','value':2},
                {'timestamp_ms':950,'key':'stacks','value':5},
                {'timestamp_ms':970,'key':'storm_ready','value':'READY'},
                {'timestamp_ms':1000,'key':'stacks','value':0},
                {'timestamp_ms':1020,'key':'targets','value':0},
            ],
            'operand_to_feature':{
                'active_enemies':'targets','buff.foo.stack':'stacks',
            },
            'readiness_feature_keys':{'stormstrike':'storm_ready'},
        }
        def run_state(s):
            snapshot.write_text(json.dumps(s),encoding='utf-8')
            output=subprocess.run(
                [sys.executable,'-B',str(priority_engine),
                 '--model',str(model),'--snapshot',str(snapshot)],
                cwd=str(ROOT),capture_output=True,text=True,timeout=15,env=env)
            assert output.returncode == 0, 'priority CLI failed'
            return json.loads(output.stdout)
        matched=run_state(sample)
        assert matched['status']=='HYPOTHESIS_CANDIDATE'
        assert matched['candidate_action_token']=='stormstrike'
        assert matched['actionable'] is False
        assert matched['provenance']['strict_pre_timestamp_ms']==970
        unavailable=run_state({
            **sample, 'transitions':[
                {**r,'timestamp_ms':1000} if r['key']=='storm_ready'
                else r for r in sample['transitions']
            ]})
        assert unavailable['status']=='BLOCKED'
        assert unavailable['reason']=='ACTION_READINESS_UNKNOWN'
        assert unavailable['candidate_action_token'] is None


def check_simc_wcl_batch_reconciliation() -> None:
    """Bounded SimC action-hypothesis replay against synthetic WCL-shaped casts."""
    p = ROOT / 'tools/research/simc_wcl_reconciliation_engine.py'
    compile(p.read_bytes(), str(p), 'exec', dont_inherit=True)
    proc = subprocess.run(
        [sys.executable, '-B', str(p)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=20,
        env={k:v for k,v in os.environ.items() if k not in
             {'WCL_CLIENT_ID','WCL_CLIENT_SECRET','GH_TOKEN','GITHUB_TOKEN'}},
    )
    assert proc.returncode == 0, 'SimC/WCL batch reconciliation regression failed'
    assert 'SIMC_WCL_BATCH_RECONCILIATION_SELF_TEST=PASS' in proc.stdout




def check_simc_conditional_priority_ir() -> None:
    """All APL lists and condition branches are retained, never auto-promoted."""
    p=ROOT / 'tools/research/simc_apl_conditional_ir.py'
    compile(p.read_bytes(),str(p),'exec',dont_inherit=True)
    proc=subprocess.run([sys.executable,'-B',str(p),'--self-test'],
                        cwd=str(ROOT),capture_output=True,text=True,timeout=20)
    assert proc.returncode==0, 'SimC conditional priority IR self-test failed'
    assert 'SIMC_GENERIC_CONDITIONAL_PRIORITY_IR_SELF_TEST=PASS' in proc.stdout



def check_simc_pre_readiness_provider() -> None:
    """Missing charge/cooldown/resource/GCD/target state stays UNKNOWN."""
    p=ROOT / 'tools/research/simc_apl_readiness_provider.py'
    compile(p.read_bytes(),str(p),'exec',dont_inherit=True)
    proc=subprocess.run([sys.executable,'-B',str(p)],
        cwd=str(ROOT),capture_output=True,text=True,timeout=20)
    assert proc.returncode==0, 'generic PRE readiness provider failed'
    assert 'SIMC_GENERIC_PRE_READINESS_SELF_TEST=PASS' in proc.stdout




def check_simc_native_reference_capture_contract() -> None:
    """Native reference acquisition tested with a fake runner, not actual SimC."""
    p=ROOT/'tools/research/simc_native_reference_capture.py'
    compile(p.read_bytes(),str(p),'exec',dont_inherit=True)
    r=subprocess.run([sys.executable,'-B',str(p),'--self-test'],
                     cwd=str(ROOT),capture_output=True,text=True,timeout=20)
    assert r.returncode==0,'SimC reference capture contract failed'
    assert 'SIMC_NATIVE_REFERENCE_CAPTURE_CONTRACT_SELF_TEST=PASS' in r.stdout




def check_simc_readiness_to_priority_cli() -> None:
    """End-to-end synthetic action readiness predicates -> source APL choice."""
    import tempfile
    provider=ROOT/'tools/research/simc_apl_source_engine.py'
    trace=ROOT/'tools/research/simc_apl_priority_trace.py'
    with tempfile.TemporaryDirectory(prefix="zrot_pre_ready_cli_") as td:
        folder=Path(td)
        apl=folder/'apl.simc'
        model=folder/'model.json'
        snap=folder/'state.json'
        apl.write_text(
            "spec=synthetic\n"
            "actions=alpha,if=active_enemies>=2\n"
            "actions+=/beta\n", encoding='utf-8')
        env={k:v for k,v in os.environ.items() if k not in
             {'WCL_CLIENT_ID','WCL_CLIENT_SECRET','GH_TOKEN','GITHUB_TOKEN'}}
        r=subprocess.run([sys.executable,'-B',str(provider),
                          '--spec','synthetic','--actions-file',str(apl),
                          '--out',str(model)],
                         cwd=str(ROOT),capture_output=True,text=True,timeout=15,env=env)
        assert r.returncode==0,'synthetic source ingestion failed'
        ingested=json.loads(model.read_text(encoding='utf-8'))
        source_sha=ingested['apl_sha256']
        columns={
          'ability_learned':('learned','eq',1),
          'cooldown_or_charge':('cooldown_ms','le',0),
          'resource':('resource','ge',40),
          'gcd':('gcd_available','eq',1),
          'cast_state':('casting','eq',0),
          'movement':('moving','eq',0),
          'range':('in_range','eq',1),
          'target':('target_valid','eq',1),
        }
        contract={
          'schema':'ZrotGenericReadinessRequirementsV1',
          'spec_slug':'synthetic','build_key':'build_synthetic',
          'apl_sha256':source_sha,'hypothesis_only':True,
          'actions':{'alpha':{
            'evidence_ref':'synthetic_fixture',
            'dimensions':{name:{'mode':'ALL','predicates':[
              {'feature':field,'op':op,'value':value}]}
              for name,(field,op,value) in columns.items()}
          }},
        }
        values={
          'enemies':2,'learned':1,'cooldown_ms':0,'resource':50,
          'gcd_available':1,'casting':0,'moving':0,'in_range':1,
          'target_valid':1,
        }
        def check_run(current):
            payload={
              'spec_slug':'synthetic','build_key':'build_synthetic',
              'decision_timestamp_ms':1000,
              'transitions':[
                  {'timestamp_ms':900,'key':key,'value':val}
                  for key,val in current.items()],
              'operand_to_feature':{'active_enemies':'enemies'},
              'readiness_feature_keys':{},
              'readiness_contract':contract,
            }
            snap.write_text(json.dumps(payload),encoding='utf-8')
            p=subprocess.run([sys.executable,'-B',str(trace),
                              '--model',str(model),'--snapshot',str(snap)],
                             cwd=str(ROOT),capture_output=True,text=True,
                             timeout=15,env=env)
            assert p.returncode==0, 'readiness to priority CLI failed'
            return json.loads(p.stdout)
        good=check_run(values)
        assert good['status']=='HYPOTHESIS_CANDIDATE'
        assert good['candidate_action_token']=='alpha'
        assert not good['actionable']
        assert good['readiness_provenance']=='SOURCE_DECLARED_REQUIREMENT_MODEL_UNVERIFIED'
        without_target=check_run({k:v for k,v in values.items() if k!='target_valid'})
        assert without_target['status']=='BLOCKED'
        assert without_target['reason']=='ACTION_READINESS_UNKNOWN'
        failed=check_run({**values,'cooldown_ms':500})
        assert failed['status']=='BLOCKED'
        assert failed['reason']=='ACTION_READINESS_UNKNOWN'
        # Alpha known NOT_READY, next beta is unknown; no false fallback.
        assert failed['candidate_action_token'] is None




def check_simc_precombat_variable_replay() -> None:
    """Source-derived precombat variables require ordered attestation and PRE."""
    p=ROOT/'tools/research/simc_apl_precombat_replay.py'
    compile(p.read_bytes(),str(p),'exec',dont_inherit=True)
    proc=subprocess.run([sys.executable,'-B',str(p),'--self-test'],
        cwd=str(ROOT),capture_output=True,text=True,timeout=20)
    assert proc.returncode==0, 'SimC precombat variable replay failed'
    assert 'SIMC_PRECOMBAT_VARIABLE_REPLAY_SELF_TEST=PASS' in proc.stdout



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
        ('simc_apl_condition_strict_pre_research_only', check_simc_apl_condition_strict_pre),
        ('simc_wcl_post_lock_guard_replay_research_only', check_simc_wcl_post_lock_guard_replay),
        ('simc_generic_source_hypothesis', check_simc_generic_source_hypothesis),
        ('simc_apl_ordered_priority_research_only', check_simc_apl_ordered_priority),
        ('simc_source_to_priority_file_cli', check_simc_source_to_priority_file_cli),
        ('simc_conditional_priority_structural_ir', check_simc_conditional_priority_ir),
        ('simc_pre_readiness_provider', check_simc_pre_readiness_provider),
        ('simc_readiness_to_priority_cli', check_simc_readiness_to_priority_cli),
        ('simc_native_reference_capture_contract', check_simc_native_reference_capture_contract),
        ('simc_precombat_variable_replay', check_simc_precombat_variable_replay),
        ('simc_wcl_batch_reconciliation_research_only', check_simc_wcl_batch_reconciliation),
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
    for relative in SRC_PATHS + SPEC_PATHS + ('tools/research/simc_apl_syntax_inventory.py', 'tools/research/simc_apl_condition_research.py', 'tools/research/post_lock_simc_wcl_guard_replay.py', 'tools/research/simc_apl_source_engine.py', 'tools/research/simc_apl_priority_trace.py', 'tools/research/simc_wcl_reconciliation_engine.py', 'tools/research/simc_apl_conditional_ir.py', 'tools/research/simc_apl_readiness_provider.py', 'tools/research/simc_native_reference_capture.py', 'tools/research/simc_apl_variable_runtime.py', 'tools/research/simc_apl_precombat_replay.py'):
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
        'simc_apl_expression_semantics':'LIMITED_RESEARCH_ONLY',
        'simc_apl_wcl_replay':'SYNTHETIC_GUARD_ONLY_NOT_FULL_APL',
        'simc_live_apl_export':'NOT_RUN',
        'simc_generic_source_engine':'SOURCE_CAPTURE_CAPABILITY_ONLY',
        'simc_apl_priority_research':'BOUNDED_ORDER_TRACE_ONLY',
        'simc_structural_if_else_ir':'SOURCE_CONDITIONAL_STRUCTURE_ONLY',
        'simc_readiness_derivation':'SOURCE_DECLARED_CONSTRAINTS_NOT_EMPIRICAL',
        'simc_native_reference_capture':'SYNTHETIC_CONTRACT_ONLY_ACTUAL_NOT_RUN',
        'simc_wcl_batch_reconciliation':'SYNTHETIC_ACTION_FAMILY_CANDIDATES_ONLY',
        'blind_wcl_independence_validation':'NOT_RUN',
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
