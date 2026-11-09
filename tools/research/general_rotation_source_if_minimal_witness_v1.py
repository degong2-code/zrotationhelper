#!/usr/bin/env python3
"""Generic sufficient-source-fact explanations for a SimC APL IF decision.

Given a source-pinned SimC expression and a distinct causal PRE fact dictionary,
find an *inclusion-minimal* set of facts sufficient to reach the same Boolean
with the existing UNKNOWN-aware SimC interpreter. This is NOT a SAT solver,
not a claim of globally unique minimum, and not a priority-optimality proof.

This is a GENERAL ENGINE, with no ability/spec/encounter-specific vocabulary.
Default no-argument mode runs deterministic synthetic checks.
"""
from __future__ import annotations

import argparse
import json
import math

from simc_apl_semantic_ir_v2 import Expression, ast_symbols, evaluate_ast, truth

SCHEMA="ZrotGeneralRotationMinimalSourceIFWitnessV1"

class MinimalIFWitnessError(ValueError):
    pass

def require(ok:bool,message:str)->None:
    if not ok:raise MinimalIFWitnessError(message)

def sufficient_source_witness(expression:str, facts:dict,
                              *, expected:bool)->dict:
    require(isinstance(expression,str) and bool(expression) and
            isinstance(facts,dict) and type(expected) is bool,
            "SOURCE_EXPRESSION_FACTS_BOOLEAN_CONTRACT_REQUIRED")
    ast=Expression(expression).parse()
    symbols=sorted(ast_symbols(ast))
    require(all(s in facts and type(facts[s]) in (int,float,bool)
                for s in symbols),
            "EXACT_SOURCE_PRE_FACT_COVERAGE_REQUIRED")
    full=truth(evaluate_ast(ast,facts))
    require(full is expected,
            "SOURCE_AST_REPLAY_NOT_EQUAL_TO_CLAIMED_TRUTH")
    sufficient={s:facts[s] for s in symbols}
    # Greedy removal: each discarded factor remains unknown, never 0.
    # The final set is irreducible under this source AST interpreter.
    for symbol in sorted(symbols):
        candidate={key:value for key,value in sufficient.items()
                   if key!=symbol}
        if truth(evaluate_ast(ast,candidate)) is expected:
            sufficient=candidate
    require(truth(evaluate_ast(ast,sufficient)) is expected,
            "REMOVED_FACTS_LOST_SUFFICIENT_SOURCE_IF_TRUTH")
    for symbol in sufficient:
        smaller={k:v for k,v in sufficient.items() if k!=symbol}
        require(truth(evaluate_ast(ast,smaller)) is not expected,
                "FINAL_SOURCE_FACT_WITNESS_NOT_INCLUSION_MINIMAL")
    return {
        "schema":SCHEMA,
        "source_expression":expression,
        "source_all_operand_names":symbols,
        "source_initial_exact_facts":{
            key:facts[key] for key in symbols
        },
        "sufficient_fact_witness":{
            k:sufficient[k] for k in sorted(sufficient)
        },
        "sufficient_source_bool_value":expected,
        "witness_method":"DELETION_BASED_INCLUSION_MINIMAL_UNDER_TYPED_TRI_STATE_AST",
        "witness_unique_globally":False,
        "source_boolean_true_is_not_full_action_READY":True,
        "gameplay_priority_optimality_proven":False,
    }

def sufficient_partial_source_witness(expression:str, facts:dict,
                                      *, expected:bool)->dict:
    """Inclusion-minimal sufficient IF facts even with some source symbols missing.

    A TRUE/FALSE claim must follow from the original partial PRE facts using
    three-valued AST evaluation, with all missing symbols remaining UNKNOWN.
    The witness is sufficient for THIS occurrence only, never general READY.
    """
    require(isinstance(expression,str) and bool(expression) and
            type(facts) is dict and type(expected) is bool,
            "PARTIAL_SOURCE_IF_INPUT_REQUIRED")
    ast=Expression(expression).parse()
    names=sorted(ast_symbols(ast))
    known={s:facts[s] for s in names if s in facts}
    require(all(type(v) in (int,float,bool) and math.isfinite(float(v))
                for v in known.values()),
            "NON_FINITE_OR_NON_NUMERIC_PARTIAL_PRE_FACT")
    result=truth(evaluate_ast(ast,known))
    require(result is expected,
            "PARTIAL_PRE_DOES_NOT_SUFFICE_FOR_ASSERTED_IF")
    minimal=dict(known)
    for symbol in sorted(known):
        without={k:v for k,v in minimal.items() if k!=symbol}
        if truth(evaluate_ast(ast,without)) is expected:
            minimal=without
    require(truth(evaluate_ast(ast,minimal)) is expected,
            "PARTIAL_MINIMAL_WITNESS_NOT_SUFFICIENT")
    for symbol in minimal:
        smaller={k:v for k,v in minimal.items() if k!=symbol}
        require(truth(evaluate_ast(ast,smaller)) is not expected,
                "PARTIAL_MINIMAL_WITNESS_REDUCIBLE")
    return {
        "schema":"ZrotGeneralRotationPartialSourceIFWitnessV1",
        "source_expression":expression,
        "source_all_operand_names":names,
        "observed_source_operand_names":sorted(known),
        "unobserved_source_operand_names":
            sorted(set(names)-set(known)),
        "minimal_sufficient_PRE_facts":
            {k:minimal[k] for k in sorted(minimal)},
        "not_needed_for_this_occurrence":
            sorted(set(names)-set(minimal)),
        "source_IF_result":expected,
        "witness_inclusion_minimal_not_global_unique":True,
        "missing_symbols_are_not_assumed_zero":True,
        "source_IF_is_not_full_READY_or_priority":True,
    }


def selftest()->dict:
    examples=(
      ("a&b",{"a":0,"b":1},False,{"a":0}),
      ("a|(b&c)",{"a":1,"b":0,"c":0},True,{"a":1}),
      ("x<(3+(n>=v))",{"x":3,"n":2,"v":2},True,
       {"n":2,"v":2,"x":3}),
      ("a&x>=2",{"a":0,"x":2},False,{"a":0}),
    )
    for expr,facts,expected,witness in examples:
        got=sufficient_source_witness(expr,facts,expected=expected)
        assert got["sufficient_fact_witness"]==witness,(expr,got)
    # A TRUE OR arm does not require unobserved alternatives.
    partial=sufficient_partial_source_witness(
        "a|(b&c)",{"a":1},expected=True)
    assert partial["minimal_sufficient_PRE_facts"]=={"a":1}
    assert partial["unobserved_source_operand_names"]==["b","c"]
    partial_false=sufficient_partial_source_witness(
        "a&b",{"a":0},expected=False)
    assert partial_false["minimal_sufficient_PRE_facts"]=={"a":0}
    for expr,facts,expected in (
        ("a&b",{"a":1},True),
        ("a|b",{"a":0},False),
        ("a|b",{"a":0,"b":0},True),
        ("a|b",{"a":1,"b":float("nan")},True),
    ):
        try:sufficient_partial_source_witness(expr,facts,expected=expected)
        except MinimalIFWitnessError:pass
        else:raise AssertionError("UNSOUND_PARTIAL_SOURCE_IF_WITNESS")
    for expr,facts,val in (
        ("a&b",{"a":1},True),
        ("a|b",{"a":0,"b":0},True),
        ("a",{"a":1},False)):
        try:sufficient_source_witness(expr,facts,expected=val)
        except MinimalIFWitnessError:pass
        else:raise AssertionError("UNPROVEN_SOURCE_IF_FACT_SET_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":13,"independent_full_READY_proven":0,
            "WCL_API_calls":0}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.parse_args()
    print(json.dumps(selftest(),sort_keys=True,ensure_ascii=False))
