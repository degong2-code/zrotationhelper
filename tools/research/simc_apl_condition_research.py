#!/usr/bin/env python3
"""Research-only SimC APL condition evaluation with strict-PRE explicit bindings.

This is a limited numeric operator interpreter, NOT a SimulationCraft engine.
It does not infer spell mechanics, action readiness, profile/build compatibility,
action-list control flow, target selection, or optimality. No rule promotion.
SimC syntax reference: simulationcraft/simc Wiki,
"Action List Conditional Expressions".
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import math
import re

from simc_apl_syntax_inventory import parse as parse_apl

# Deliberately not a Python eval / exec. Unrecognized syntax is UNSUPPORTED.
_TOKEN = re.compile(
    r'\s*(?:'
    r'(\d+(?:\.\d*)?|\.\d+)'
    r'|([a-zA-Z_][a-zA-Z0-9_.]*)'
    r'|(%%|<=|>=|!=|<\?|>\?|[()&|^!<>=+\-*%@])'
    r')'
)
_BP = {'|': 10, '^': 20, '&': 30,
       '=': 40, '!=': 40, '<': 40, '<=': 40, '>': 40, '>=': 40,
       '<?': 50, '>?': 50, '+': 60, '-': 60,
       '*': 70, '%': 70, '%%': 70}


class UnsupportedExpression(ValueError):
    pass


@dataclass(frozen=True)
class ConditionOutcome:
    status: str  # TRUE, FALSE, UNKNOWN, UNSUPPORTED
    value: float | None
    missing_operands: tuple[str, ...] = ()
    reason: str | None = None


def _tokenize(src: str):
    found = []
    i = 0
    while i < len(src):
        if src[i:].strip() == '':
            break
        m = _TOKEN.match(src, i)
        if m is None:
            raise UnsupportedExpression('UNSUPPORTED_TOKEN')
        value = next(v for v in m.groups() if v is not None)
        if value in ('floor', 'ceil') and src[m.end():].lstrip().startswith('('):
            found.append(('FUNC', value))
        elif m.group(1) is not None:
            found.append(('NUM', value))
        elif m.group(2) is not None:
            found.append(('VAR', value))
        else:
            found.append(('OP', value))
        i = m.end()
    found.append(('EOF', ''))
    return found


class _Parser:
    def __init__(self, expr: str):
        self.tokens = _tokenize(expr)
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def take(self):
        t = self.peek()
        self.pos += 1
        return t

    def require(self, val):
        if self.take() != ('OP', val):
            raise UnsupportedExpression('EXPECTED_' + val)

    def expression(self, minimum=0, depth=0):
        if depth > 100:
            raise UnsupportedExpression('EXPRESSION_NESTING_LIMIT')
        typ, tok = self.take()
        if typ == 'NUM':
            lhs = ('number', float(tok))
        elif typ == 'VAR':
            lhs = ('variable', tok)
        elif typ == 'FUNC':
            self.require('(')
            arg = self.expression(0, depth + 1)
            self.require(')')
            lhs = ('function', tok, arg)
        elif typ == 'OP' and tok == '(':
            lhs = self.expression(0, depth + 1)
            self.require(')')
        elif typ == 'OP' and tok in ('!', '+', '-', '@'):
            lhs = ('unary', tok, self.expression(80, depth + 1))
        else:
            raise UnsupportedExpression('EXPECTED_OPERAND')
        while True:
            typ, op = self.peek()
            if typ != 'OP' or op not in _BP or _BP[op] < minimum:
                break
            self.take()
            rhs = self.expression(_BP[op] + 1, depth + 1)
            lhs = ('binary', op, lhs, rhs)
        return lhs

    def parse(self):
        tree = self.expression()
        if self.peek()[0] != 'EOF':
            raise UnsupportedExpression('TRAILING_OR_UNSUPPORTED_EXPRESSION')
        return tree


def _finite_number(value):
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        try:
            x = float(value)
        except (OverflowError, ValueError):
            return None
        return x if math.isfinite(x) else None
    return None


def _merge(a, b):
    return frozenset(a | b)


def _compute(tree, bound):
    tag = tree[0]
    if tag == 'number':
        return tree[1], frozenset(), None
    if tag == 'variable':
        key = tree[1]
        if key not in bound:
            return None, frozenset((key,)), 'MISSING_OR_UNOBSERVABLE_OPERAND'
        v = _finite_number(bound[key])
        if v is None:
            return None, frozenset((key,)), 'NON_NUMERIC_OR_NONFINITE_OPERAND'
        return v, frozenset(), None
    if tag in ('unary', 'function'):
        op, node = tree[1:]
        x, missing, issue = _compute(node, bound)
        if x is None:
            return None, missing, issue
        if tag == 'unary':
            v = {'!': lambda: float(x == 0), '+': lambda: x,
                 '-': lambda: -x, '@': lambda: abs(x)}[op]()
        else:
            v = float(math.floor(x)) if op == 'floor' else float(math.ceil(x))
        return (v, frozenset(), None) if math.isfinite(v) else (
            None, frozenset(), 'NONFINITE_OPERATION')
    op, a, b = tree[1:]
    x, mx, rx = _compute(a, bound)
    y, my, ry = _compute(b, bound)
    missing = _merge(mx, my)
    if op in ('&', '|'):
        # Three-valued logic: FALSE & UNKNOWN = FALSE, TRUE | UNKNOWN = TRUE.
        if op == '&' and ((x is not None and x == 0) or
                          (y is not None and y == 0)):
            return 0.0, frozenset(), None
        if op == '|' and ((x is not None and x != 0) or (y is not None and y != 0)):
            return 1.0, frozenset(), None
        if x is None or y is None:
            return None, missing, rx or ry
        return float((x != 0 and y != 0) if op == '&' else
                     (x != 0 or y != 0)), frozenset(), None
    if x is None or y is None:
        return None, missing, rx or ry
    try:
        if op == '+': v = x + y
        elif op == '-': v = x - y
        elif op == '*': v = x * y
        elif op == '%': v = x / y  # SimC '%' is DIVISION, NOT modulo.
        elif op == '%%': v = math.fmod(x, y)  # SimC '%%' is modulo.
        elif op == '<?': v = max(x, y)  # SimC '<?' means MAX.
        elif op == '>?': v = min(x, y)  # SimC '>?' means MIN.
        elif op == '=': v = float(x == y)
        elif op == '!=': v = float(x != y)
        elif op == '<': v = float(x < y)
        elif op == '<=': v = float(x <= y)
        elif op == '>': v = float(x > y)
        elif op == '>=': v = float(x >= y)
        elif op == '^': v = float((x != 0) != (y != 0))
        else: raise UnsupportedExpression('UNIMPLEMENTED_OPERATOR')
    except (ZeroDivisionError, ValueError, OverflowError):
        return None, frozenset(), 'ARITHMETIC_UNDEFINED'
    if not math.isfinite(v):
        return None, frozenset(), 'NONFINITE_OPERATION'
    return float(v), frozenset(), None


def evaluate(expression: str, *, bound_values, decision_timestamp_ms: int,
             state_timestamp_max_ms: int | None) -> ConditionOutcome:
    """A condition outcome, not an action recommendation.

    bound_values must be explicitly mapped, strictly-pre observed numeric
    values keyed by exact SimC expression operand. Missing is NEVER zero.
    """
    if state_timestamp_max_ms is not None and (
        state_timestamp_max_ms >= decision_timestamp_ms
    ):
        raise ValueError('STRICT_PRE_VIOLATION')
    try:
        tree = _Parser(expression).parse()
        value, missing, reason = _compute(tree, bound_values)
    except (UnsupportedExpression, RecursionError) as e:
        return ConditionOutcome('UNSUPPORTED', None, (), type(e).__name__)
    if value is None:
        return ConditionOutcome('UNKNOWN', None, tuple(sorted(missing)), reason)
    return ConditionOutcome('TRUE' if value != 0 else 'FALSE', value)


def bind_strict_pre(state, *, operand_to_feature):
    """Explicit semantic identity mapping. Never infer readiness or names.

    An OBSERVED PRE feature with a valid past provenance may bind a numeric
    operand. UNKNOWN/UNOBSERVABLE/non-numeric is left absent.
    """
    state.validate()
    bound = {}
    for operand, feature_key in operand_to_feature.items():
        observation = state.features.get(feature_key)
        if observation is None:
            continue
        status = getattr(observation.status, 'value', observation.status)
        if status != 'OBSERVED':
            continue
        ts = observation.source_timestamp_ms
        if ts is not None and ts >= state.decision_timestamp_ms:
            raise ValueError('STRICT_PRE_FEATURE_VIOLATION')
        num = _finite_number(observation.value)
        if num is not None:
            bound[operand] = num
    return bound


def inspect_guards(profile_text: str, state, *, operand_to_feature):
    """Every APL row inspected; NO action-list evaluation/priority/selection."""
    state.validate()
    _, lists = parse_apl(profile_text)
    bound = bind_strict_pre(state, operand_to_feature=operand_to_feature)
    results = []
    for name, rows in lists.items():
        for r in rows:
            guard = r['condition']
            result = (
                evaluate(guard, bound_values=bound,
                         decision_timestamp_ms=state.decision_timestamp_ms,
                         state_timestamp_max_ms=state.state_timestamp_max_ms)
                if guard is not None
                else ConditionOutcome('TRUE', 1.0)
            )
            results.append({
                'list': name, 'rank': r['rank'], 'line': r['line'],
                'command': r['command'], 'guard': guard,
                'guard_status': result.status,
                'missing_operands': result.missing_operands,
                'guard_reason': result.reason,
                'readiness': 'UNKNOWN',
                'hypothesis_only': True,
                'recommended_action': None,
                'wcl_replay': 'NOT_RUN',
            })
    return results


def selftest():
    import sys
    from pathlib import Path
    runtime_root = Path(__file__).resolve().parents[2] / '02_SOURCE' / 'runtime'
    sys.path.insert(0, str(runtime_root))
    from raid_dps.core.behavioral_evaluator import (
        ObservationStatus, StateTransition, StrictPreStateProvider
    )
    s = StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=(
            StateTransition(900, 'stacks', 5),
            StateTransition(950, 'enemy_count', 2),
            StateTransition(1000, 'stacks', 0),
            StateTransition(1001, 'enemy_count', 1),
        ),
        required_keys=('stacks', 'enemy_count', 'unseen'),
        unobservable_keys=('hidden',),
    )
    assert s.state_timestamp_max_ms == 950
    b = bind_strict_pre(s, operand_to_feature={
        'buff.storm.stack': 'stacks', 'active_enemies': 'enemy_count',
        'talent.unseen.enabled': 'unseen', 'buff.hidden.up': 'hidden',
    })
    assert b == {'buff.storm.stack': 5.0, 'active_enemies': 2.0}
    def check(expr, expected):
        actual = evaluate(expr, bound_values=b,
                          decision_timestamp_ms=1000,
                          state_timestamp_max_ms=950)
        assert actual.status == expected, (expr, actual)
        return actual
    check('buff.storm.stack>=5&active_enemies>1', 'TRUE')
    check('buff.storm.stack<5|active_enemies=1', 'FALSE')
    check('0|1&0', 'FALSE')   # logical & precedes |
    check('1|0&0', 'TRUE')
    check('!0&1', 'TRUE')
    check('2=2', 'TRUE')
    check('5%2=2.5', 'TRUE')    # SimC division
    check('9%%2.5=1.5', 'TRUE')
    check('3<?4=4', 'TRUE')    # max
    check('3>?4=3', 'TRUE')    # min
    check('floor(2.9)=2&ceil(2.1)=3', 'TRUE')
    check('@-3=3', 'TRUE')
    check('0&talent.unseen.enabled', 'FALSE')
    check('1|talent.unseen.enabled', 'TRUE')
    check('1&talent.unseen.enabled', 'UNKNOWN')
    u = check('buff.hidden.up', 'UNKNOWN')
    assert u.missing_operands == ('buff.hidden.up',)
    check('1%0', 'UNKNOWN')
    check('buff.storm.stack==5', 'UNSUPPORTED')
    check('target.foo~bar', 'UNSUPPORTED')
    check('buff.storm.stack?1:0', 'UNSUPPORTED')
    check('buff.storm.stack<5&!', 'UNSUPPORTED')
    try:
        evaluate('1', bound_values=b, decision_timestamp_ms=1000,
                 state_timestamp_max_ms=1000)
    except ValueError as exc:
        assert str(exc) == 'STRICT_PRE_VIOLATION'
    else:
        raise AssertionError('SAME_TIMESTAMP_ACCEPTED')
    profile = (
        'spec=enhancement\n'
        'actions=stormstrike,if=buff.storm.stack>=5&active_enemies=2\n'
        'actions+=/lava_lash,if=buff.hidden.up\n'
        'actions+=/call_action_list,name=secondary,if=active_enemies>1\n'
        'actions.secondary=lightning_bolt,if=talent.unseen.enabled\n'
    )
    rows = inspect_guards(profile, s, operand_to_feature={
        'buff.storm.stack': 'stacks', 'active_enemies': 'enemy_count',
        'buff.hidden.up': 'hidden', 'talent.unseen.enabled': 'unseen',
    })
    assert [r['guard_status'] for r in rows] == [
        'TRUE', 'UNKNOWN', 'TRUE', 'UNKNOWN']
    assert all(r['recommended_action'] is None and r['readiness'] == 'UNKNOWN'
               and r['wcl_replay'] == 'NOT_RUN' for r in rows)
    print('SIMC_APL_CONDITION_STRICT_PRE_SELF_TEST=PASS')


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--self-test', action='store_true')
    options = a.parse_args()
    if options.self_test:
        selftest()
        return 0
    print('RESEARCH_ONLY: use inspect_guards() with explicit Strict PRE bindings')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
