#!/usr/bin/env python3
"""Research-only SimC APL syntax inventory, extracted from the historical
GenericSimcAplHypothesisCompilerV1 parser (source SHA256:
48ef1f8620e44bb06f2d637ee9ed382e25acc3673e509148d88ad57d3b935c2d).

NO semantic expression evaluation, WCL binding, readiness, or gameplay advice.
This standalone parser deliberately has NO Seq568 evidence dependency.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re

LINE = re.compile(r'^actions(?:\.([a-zA-Z0-9_]+))?(\+?=)(/?)(.*)$')


def split_args(value: str) -> list[str]:
    depth = 0
    out = []
    left = 0
    for idx, c in enumerate(value):
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth < 0:
                raise ValueError('UNBALANCED_APL_PAREN')
        elif c == ',' and depth == 0:
            out.append(value[left:idx])
            left = idx + 1
    if depth != 0:
        raise ValueError('UNBALANCED_APL_PAREN')
    out.append(value[left:])
    return out


def parse(txt: str):
    """Parse historical source syntax; preserve guards as OPAQUE strings."""
    meta = {}
    lists = collections.OrderedDict()
    list_base = set()
    for ln, text in enumerate(txt.splitlines(), 1):
        s = text.strip()
        if not s or s.startswith('#'):
            continue
        if s.startswith('actions'):
            m = LINE.fullmatch(s)
            if not m:
                raise ValueError('UNRECOGNIZED_APL_LINE_' + str(ln))
            group, op, slash, value = m.groups()
            group = group or 'default'
            if op == '=' and group in list_base:
                raise ValueError('DUPLICATE_LIST_BASE_' + group)
            if op == '=':
                list_base.add(group)
            if not value:
                raise ValueError('EMPTY_APL_LINE_' + str(ln))
            tokens = split_args(value)
            cmd = tokens[0]
            # Official SimC util::string_split defaults to skip_empty_entries.
            # Preserve the source line and record ignored empty option slots.
            empty_option_slots = sum(token == '' for token in tokens[1:])
            if empty_option_slots:
                tokens = [cmd] + [token for token in tokens[1:] if token]
            if not re.fullmatch(r'[a-zA-Z0-9_]+', cmd):
                raise ValueError('INVALID_APL_COMMAND_' + str(ln))
            params = []
            for v in tokens[1:]:
                if '=' not in v:
                    raise ValueError('INVALID_APL_PARAMETER_' + str(ln))
                k, z = v.split('=', 1)
                if not re.fullmatch(r'[a-zA-Z0-9_]+', k) or not z:
                    raise ValueError('INVALID_APL_PARAMETER_' + str(ln))
                params.append([k, z])
            cond = [v for k, v in params if k == 'if']
            if len(cond) > 1:
                raise ValueError('DUPLICATE_IF_' + str(ln))
            target = [v for k, v in params
                      if k == 'name' and cmd in ('call_action_list', 'run_action_list')]
            if cmd in ('call_action_list', 'run_action_list') and len(target) != 1:
                raise ValueError('CALL_TARGET_MISSING_' + str(ln))
            kind = ('CONTROL_DIRECTIVE' if cmd in
                    ('variable', 'snapshot_stats', 'auto_attack',
                     'call_action_list', 'run_action_list') else 'ACTION_CANDIDATE')
            row = {
                'line': ln, 'list': group,
                'rank': len(lists.setdefault(group, [])) + 1,
                'command': cmd, 'params': params,
                'condition': cond[0] if cond else None,
                'kind': kind, 'call_target': target[0] if target else None,
                'source_literal': s, 'ignored_empty_option_slots': empty_option_slots,
                'promotion': 'HYPOTHESIS_ONLY',
                'readiness': 'UNKNOWN', 'playable': False,
            }
            lists[group].append(row)
        elif '=' in s:
            k, v = s.split('=', 1)
            if k in ('spec', 'level', 'talents', 'source', 'race', 'role',
                     'position', 'shaman', 'warrior', 'mage', 'death_knight',
                     'paladin', 'hunter', 'druid', 'priest', 'rogue', 'warlock',
                     'evoker', 'monk', 'demon_hunter', 'deathknight',
                     'demonhunter'):
                meta[k] = v
    if 'default' not in lists or not lists['default']:
        raise ValueError('MAIN_APL_MISSING')
    if set(lists) != list_base:
        raise ValueError('APPEND_BEFORE_BASE')
    for rows in lists.values():
        for row in rows:
            if row['call_target'] and row['call_target'] not in lists:
                raise ValueError('UNRESOLVED_APL_CALL_' + row['call_target'])
    edges = {k: [r['call_target'] for r in v if r['call_target']]
             for k, v in lists.items()}

    def walk(k, stack, done):
        if k in stack:
            raise ValueError('CYCLIC_APL_CALL_' + k)
        if k in done:
            return
        stack.add(k)
        for target in edges[k]:
            walk(target, stack, done)
        stack.remove(k)
        done.add(k)
    done = set()
    for key in edges:
        walk(key, set(), done)
    return meta, lists


def inventory(profile_text: str):
    meta, groups = parse(profile_text)
    rows = [r for group in groups.values() for r in group]
    return {
        'schema': 'ZrotSimcAplSyntaxInventoryResearchV1',
        'profile_sha256': hashlib.sha256(profile_text.encode('utf-8')).hexdigest(),
        'profile_spec': meta.get('spec', 'UNKNOWN'),
        'lists': {key: len(group) for key, group in groups.items()},
        'action_rows': len(rows),
        'opaque_condition_rows': sum(r['condition'] is not None for r in rows),
        'list_call_rows': sum(r['call_target'] is not None for r in rows),
        'priority': 'SOURCE_ORDER_ONLY',
        'expression_semantics': 'OPAQUE_NOT_EVALUATED',
        'exact_build_binding_to_wcl': 'UNVERIFIED',
        'readiness': 'UNKNOWN',
        'recommendations': 0,
        'can_compile_to_canonical_rotation_rule': False,
        'status': 'RESEARCH_ONLY_NOT_AUTHORITY',
    }


def selftest():
    example = (
        'spec=enhancement\n'
        'actions=call_action_list,name=st,if=active_enemies=1\n'
        'actions+=/call_action_list,name=aoe,if=active_enemies>1\n'
        'actions.st=stormstrike,if=buff.foo.stack>=5\n'
        'actions.st+=/lava_lash\n'
        'actions.aoe=crash_lightning,if=talent.abc.enabled&buff.foo.up\n'
    )
    x = inventory(example)
    assert x['action_rows'] == 5 and len(x['lists']) == 3
    assert x['opaque_condition_rows'] == 4 and x['list_call_rows'] == 2
    assert x['recommendations'] == 0 and x['readiness'] == 'UNKNOWN'
    assert x['expression_semantics'] == 'OPAQUE_NOT_EVALUATED'
    assert parse('actions=alpha,,if=x=1')[1]['default'][0]['ignored_empty_option_slots'] == 1
    assert parse('actions=alpha,,if=x=1')[1]['default'][0]['params'] == [['if','x=1']]
    assert split_args('spell,if=(a|b)&c,use_off_gcd=1') == [
        'spell', 'if=(a|b)&c', 'use_off_gcd=1']
    cases = (
        'actions=call_action_list,name=missing',
        'actions=spell,if=(a|b',
        'actions=spell\nactions=other',
        'actions=call_action_list,name=default',
        'actions+=/spell',
    )
    for case in cases:
        try:
            parse(case)
        except ValueError:
            pass
        else:
            raise AssertionError('INVALID_APL_ACCEPTED')
    print('SIMC_APL_SYNTAX_SELF_TEST=PASS')


def main() -> int:
    arg = argparse.ArgumentParser()
    arg.add_argument('--self-test', action='store_true')
    arg.add_argument('--profile', type=Path)
    opts = arg.parse_args()
    if opts.self_test or opts.profile is None:
        selftest()
        return 0
    print(json.dumps(inventory(opts.profile.read_text(encoding='utf-8-sig')),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
