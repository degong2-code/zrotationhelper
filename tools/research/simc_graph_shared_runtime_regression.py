#!/usr/bin/env python3
"""Cross-specialization graph-to-existing-APL-runtime boundary regression.

No spell-class constants, gameplay authority, or native parity claims.
Compiled graph must be byte-for-byte structurally equivalent to the source
model's own compilation; missing decision state must remain UNKNOWN.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "02_SOURCE" / "runtime"))
from raid_dps.core.behavioral_evaluator import StrictPreStateProvider, StateTransition

from simc_apl_source_engine import ingest_actions
from simc_apl_conditional_ir import compile_structural_ir
from simc_apl_decision_graph import compile_decision_graph
from simc_apl_priority_trace import trace_priority, CANDIDATE, BLOCK


def make_state(*rows):
    return StrictPreStateProvider().build(
        action_timestamp_ms=1000,
        transitions=tuple(StateTransition(t, k, v) for t, k, v in rows),
        required_keys=("targets", "stacks"),
    )


def check():
    n = 0
    for spec, action_a, action_b, fallback in (
            ("enhancement", "synthetic_alpha", "synthetic_beta", "synthetic_fallback"),
            ("unholy", "synthetic_gamma", "synthetic_delta", "synthetic_escape"),
            ("fury", "synthetic_lambda", "synthetic_sigma", "synthetic_zeta")):
        source = (
            f"spec={spec}\n"
            "actions=call_action_list,name=burst,if=active_enemies>=2\n"
            f"actions+=/{fallback}\n"
            f"actions.burst={action_a},if=buff.test.stack>=2\n"
            f"actions.burst+=/{action_b}\n"
        ).encode()
        model = ingest_actions(source, expected_spec=spec)
        graph = compile_decision_graph(compile_structural_ir(model))
        kw = {
            "model": model, "spec_slug": spec,
            "operand_to_feature": {"active_enemies":"targets",
                                   "buff.test.stack":"stacks"},
            "expected_apl_sha256": hashlib.sha256(source).hexdigest(),
        }
        def compare(state, ready, expected_status, expected_token=None, reason=None):
            nonlocal n
            ordinary = trace_priority(**kw, strict_pre_state=state,
                                      action_readiness=ready)
            bridged = trace_priority(**kw, strict_pre_state=state,
                                     action_readiness=ready, decision_graph=graph)
            assert (ordinary.status, ordinary.candidate_action_token, ordinary.reason) == (
                bridged.status, bridged.candidate_action_token, bridged.reason)
            assert bridged.status == expected_status, bridged
            assert bridged.candidate_action_token == expected_token, bridged
            if reason is not None:
                assert bridged.reason == reason, bridged
            assert bridged.provenance["decision_graph_contract"] == "EXACT_SOURCE_RECOMPILATION"
            assert bridged.provenance["native_decision_equivalence"] == "NOT_VALIDATED"
            assert bridged.provenance["gameplay_promotion"] is False
            assert all(x in graph["nodes"]
                       for x in bridged.provenance["graph_visited_node_ids"])
            n += 1
        ready_all = {action_a:"READY", action_b:"READY", fallback:"READY"}
        compare(make_state((900,"targets",2),(900,"stacks",2)),
                ready_all, CANDIDATE, action_a)
        compare(make_state((900,"targets",1),(900,"stacks",2)),
                ready_all, CANDIDATE, fallback)
        compare(make_state((900,"targets",2),(900,"stacks",0)),
                ready_all, CANDIDATE, action_b)
        compare(make_state((900,"targets",2)),
                ready_all, BLOCK, reason="GUARD_UNKNOWN")
        compare(make_state((900,"targets",2),(900,"stacks",3)),
                {action_a:"UNKNOWN",action_b:"READY",fallback:"READY"},
                BLOCK, reason="ACTION_READINESS_UNKNOWN")
        compare(make_state((900,"targets",2),(900,"stacks",0),
                           (1000,"stacks",9),(1001,"targets",0)),
                ready_all, CANDIDATE, action_b)
        compare(make_state((900,"targets",2),(900,"stacks",2)),
                {action_a:"NOT_READY",action_b:"READY",fallback:"READY"},
                CANDIDATE, action_b)
        modified=deepcopy(graph)
        modified["nodes"]["default:1"]["next_in_list"]="burst:1"
        try:
            trace_priority(**kw, strict_pre_state=make_state((900,"targets",2)),
                           action_readiness=ready_all, decision_graph=modified)
        except ValueError as e:
            assert str(e) == "DECISION_GRAPH_CANONICAL_MISMATCH"
        else:
            raise AssertionError("TAMPERED_GRAPH_ACCEPTED")
        n += 1
        changed=deepcopy(graph)
        changed["source_apl_sha256"]="0"*64
        try:
            trace_priority(**kw, strict_pre_state=make_state((900,"targets",2)),
                           action_readiness=ready_all, decision_graph=changed)
        except ValueError as e:
            assert str(e) == "DECISION_GRAPH_CANONICAL_MISMATCH"
        else:
            raise AssertionError("WRONG_SOURCE_PIN_ACCEPTED")
        n += 1
    # call exhaustion returns to next parent; run exhaustion forbids it.
    run_source = (b"spec=synthetic\nactions=run_action_list,name=child\n"
                  b"actions+=/fallback\nactions.child=alpha\n")
    model=ingest_actions(run_source, expected_spec="synthetic")
    graph=compile_decision_graph(compile_structural_ir(model))
    blocked=trace_priority(model, strict_pre_state=make_state(),
                           spec_slug="synthetic", operand_to_feature={},
                           action_readiness={"alpha":"NOT_READY","fallback":"READY"},
                           expected_apl_sha256=hashlib.sha256(run_source).hexdigest(),
                           decision_graph=graph)
    assert blocked.status == BLOCK and blocked.reason == "RUN_LIST_YIELD_NO_FALLTHROUGH"
    n += 1
    print(f"SIMC_GENERIC_GRAPH_TO_SHARED_RUNTIME_BOUNDARY=PASS CHECKS={n} "
          "VALIDATION=SYNTHETIC_STATE_ONLY")


if __name__ == "__main__":
    check()
