#!/usr/bin/env python3
"""SimC-first opener + conditional-priority hypothesis vertical slice.

Consumes a real exported APL/profile action-list file and a separate explicit
Strict PRE timeline. Reuses current generic SimC parsing, structural IR,
symbolic graph, and bounded priority traversal. Does NOT derive an opener
from precombat directives or assume observed cooldown/readiness. Output is
NOT a validated rotation, game recommendation, or a WCL blind candidate.

PyCharm without Script Parameters runs a safe offline self-test.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "02_SOURCE" / "runtime") not in sys.path:
    sys.path.insert(0, str(ROOT / "02_SOURCE" / "runtime"))

from raid_dps.core.behavioral_evaluator import StateTransition, StrictPreStateProvider
from simc_apl_source_engine import ingest_actions
from simc_apl_conditional_ir import compile_structural_ir
from simc_apl_decision_graph import compile_decision_graph
from simc_apl_priority_trace import trace_priority

SCHEMA = "ZrotSimcFirstGeneralOpenerPriorityHypothesisV1"
INPUT_SCHEMA = "ZrotSimcOpenerPriorityReplayInputV1"
PHASES = {"OPENER", "POST_OPENER"}
READINESS = {"READY", "NOT_READY", "UNKNOWN", "UNOBSERVABLE"}
MAX_DECISIONS = 256
MAX_TRANSITIONS = 20000

class BaselineError(ValueError):
    pass


def _int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BaselineError("INVALID_INT_" + label)
    return value


def _validate_fixture(fixture: dict, spec: str) -> list[dict]:
    if not isinstance(fixture, dict) or fixture.get("schema") != INPUT_SCHEMA:
        raise BaselineError("REPLAY_FIXTURE_SCHEMA")
    if fixture.get("spec") != spec:
        raise BaselineError("REPLAY_SPEC_MISMATCH")
    if fixture.get("mode") != "EXPLICIT_STRICT_PRE_SYNTHETIC_OR_ATTESTED":
        raise BaselineError("REPLAY_FIXTURE_PROVENANCE_REQUIRED")
    binding = fixture.get("operand_to_feature")
    if not isinstance(binding, dict) or not binding or not all(
        isinstance(k, str) and k and isinstance(v, str) and v
        for k, v in binding.items()
    ):
        raise BaselineError("OPERAND_BINDINGS_REQUIRED")
    entries = fixture.get("decisions")
    if not isinstance(entries, list) or not entries or len(entries) > MAX_DECISIONS:
        raise BaselineError("BOUNDED_DECISIONS_REQUIRED")
    last = None
    for i, step in enumerate(entries):
        if not isinstance(step, dict):
            raise BaselineError("DECISION_OBJECT_REQUIRED")
        ts = _int(step.get("timestamp_ms"), "TIMESTAMP")
        if ts < 0 or (last is not None and ts <= last):
            raise BaselineError("DECISION_TIMESTAMPS_NOT_STRICTLY_INCREASING")
        last = ts
        if step.get("phase") not in PHASES:
            raise BaselineError("EXPLICIT_OPENER_PHASE_REQUIRED")
        if step.get("phase") == "OPENER" and any(
            x["phase"] == "POST_OPENER" for x in entries[:i]
        ):
            raise BaselineError("OPENER_RESUMED_AFTER_END")
        rows = step.get("transitions")
        if not isinstance(rows, list) or len(rows) > MAX_TRANSITIONS:
            raise BaselineError("BOUNDED_TRANSITIONS_REQUIRED")
        for r in rows:
            if not isinstance(r, dict) or not isinstance(r.get("key"), str) or not r["key"]:
                raise BaselineError("INVALID_TRANSITION_IDENTITY")
            _int(r.get("timestamp_ms"), "TRANSITION_TIMESTAMP")
            if "value" not in r:
                raise BaselineError("TRANSITION_VALUE_REQUIRED")
        readiness = step.get("action_readiness")
        if not isinstance(readiness, dict) or any(
            not isinstance(k, str) or not k or v not in READINESS
            for k, v in readiness.items()
        ):
            raise BaselineError("EXPLICIT_READINESS_MAP_REQUIRED")
        unobs = step.get("unobservable_keys", [])
        if not isinstance(unobs, list) or any(
            not isinstance(x, str) or not x for x in unobs
        ):
            raise BaselineError("INVALID_UNOBSERVABLE_KEYS")
    return entries


def build_baseline(actions_bytes: bytes, *, spec: str, fixture: dict) -> dict:
    """Compile source and replay explicit decision samples without gameplay promotion."""
    if not isinstance(actions_bytes, bytes) or not actions_bytes:
        raise BaselineError("NONEMPTY_APL_BYTES_REQUIRED")
    model = ingest_actions(actions_bytes, expected_spec=spec)
    ir = compile_structural_ir(model)
    graph = compile_decision_graph(ir)
    entries = _validate_fixture(fixture, spec)
    binding = fixture["operand_to_feature"]
    required_keys = set(binding.values())
    precombat = []
    for row in ir["lists"].get("precombat", []):
        precombat.append({
            "source_line": row["source_line"],
            "order": row["priority_in_list"],
            "command": row["command"],
            "guard": row["guard"],
            "operation": row["operation"],
            "unverified_obligations": row["unverified_semantic_obligations"],
            "precombat_executed": False,
        })
    results = []
    for step in entries:
        transitions = [
            StateTransition(
                timestamp_ms=r["timestamp_ms"], key=r["key"], value=r["value"],
                sequence=_int(r.get("sequence", 0), "SEQUENCE"),
                valid=r.get("valid", True) is True,
            )
            for r in step["transitions"]
        ]
        state = StrictPreStateProvider().build(
            action_timestamp_ms=step["timestamp_ms"],
            transitions=transitions,
            required_keys=required_keys,
            unobservable_keys=step.get("unobservable_keys", []),
        )
        traced = trace_priority(
            model,
            strict_pre_state=state,
            spec_slug=spec,
            operand_to_feature=binding,
            action_readiness=step["action_readiness"],
            expected_apl_sha256=model["apl_sha256"],
            expected_profile_sha256=model.get("profile_sha256"),
            decision_graph=graph,
        )
        results.append({
            "timestamp_ms": step["timestamp_ms"],
            "phase": step["phase"],
            "phase_source": "EXPLICIT_INPUT_LABEL_NOT_AUTOMATICALLY_INFERRED",
            "context_target_count": step.get("target_count_label", "UNSPECIFIED"),
            "status": traced.status,
            "hypothesis_action_token": traced.candidate_action_token,
            "source_list": traced.list_name,
            "source_line": traced.source_line,
            "reason": traced.reason,
            "traversed_rows": list(traced.trace),
            "strict_pre_max_timestamp_ms": state.state_timestamp_max_ms,
            "same_timestamp_events_excluded": state.excluded_same_timestamp_n,
            "future_events_excluded": state.excluded_future_n,
            "action_readiness_source": "EXPLICIT_INPUT_ONLY_NOT_AUTOMATICALLY_VERIFIED",
            "actionable": False,
            "WCL_blind_candidate_lock": "NOT_ACCESSED",
            "WCL_validation": "NOT_RUN",
        })
    return {
        "schema": SCHEMA,
        "scope_id": "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
        "source_spec": spec,
        "source_kind": model["source_kind"],
        "source_apl_sha256": model["apl_sha256"],
        "source_profile_sha256": model.get("profile_sha256"),
        "source_current_patch_verified": model["current_patch_verified"],
        "source_semantic_unresolved": model["unresolved_requirements"],
        "precombat_apl_directives_not_combat_opener": precombat,
        "precombat_is_distinct": ir["precombat_is_distinct"],
        "simc_structural_apl_row_count": ir["total_rows"],
        "simc_structural_priority_entry_list": ir["priority_entry_list"],
        "simc_conditional_required_operands": ir["required_state_operands"],
        "simc_unverified_semantic_obligations": ir["semantic_gap_count_by_row"],
        "decision_graph_node_count": len(graph["nodes"]),
        "explicit_opener_sample_count": sum(
            x["phase"] == "OPENER" for x in results
        ),
        "post_opener_sample_count": sum(
            x["phase"] == "POST_OPENER" for x in results
        ),
        "decision_samples": results,
        "opener_sequence_proven_complete": False,
        "validated_general_rotation_IR": False,
        "WCL_blind_lane_consumed": False,
        "WCL_high_ranker_replay": "NOT_RUN",
        "Blizzard_spell_identity_truth": "UNVERIFIED",
        "training_mistake_feedback_eligible": False,
        "production_authority": "NONE",
    }


def inspect_source_only(actions_bytes: bytes, *, spec: str) -> dict:
    """Real-profile source inspection, with no simulated readiness or opener casts."""
    if not isinstance(actions_bytes, bytes) or not actions_bytes:
        raise BaselineError("NONEMPTY_APL_BYTES_REQUIRED")
    model=ingest_actions(actions_bytes, expected_spec=spec)
    ir=compile_structural_ir(model)
    graph=compile_decision_graph(ir)
    precombat=ir["lists"].get("precombat", [])
    return {
        "schema":"ZrotSimcSourceOnlyGeneralRotationOpenerInventoryV1",
        "scope_id":"ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
        "spec":spec,
        "source_apl_sha256":model["apl_sha256"],
        "row_count":ir["total_rows"],
        "precombat_directives":[
            {"command":r["command"],"source_line":r["source_line"],
             "guard":r["guard"],"operation":r["operation"]}
            for r in precombat
        ],
        "source_list_names":sorted(ir["lists"]),
        "source_list_rows":{
            name:[{"rank":r["priority_in_list"],"command":r["command"],
                   "guard":r["guard"],"source_line":r["source_line"],
                   "obligations":r["unverified_semantic_obligations"]}
                  for r in rows]
            for name,rows in ir["lists"].items()
        },
        "target_count_guard_candidates":[
            {"list":name,"source_line":r["source_line"],"guard":r["guard"]}
            for name,rows in ir["lists"].items()
            for r in rows if isinstance(r["guard"],str)
            and "active_enemies" in r["guard"]
        ],
        "required_state_operands":ir["required_state_operands"],
        "unresolved_semantic_gap_counts":ir["semantic_gap_count_by_row"],
        "decision_graph_node_count":len(graph["nodes"]),
        "source_is_actual_executed_simc_APL":False,
        "precombat_is_combat_opener":False,
        "combat_opener_sequence_inferred":False,
        "decision_readiness_observed":False,
        "WCL_ranking_validated":False,
        "general_rotation_proven":False,
        "intended_next":"REPLAY_AT_EXPLICIT_STRICT_PRE_STATE_THEN_INDEPENDENT_WCL_RANKER_COMPARISON",
    }


def self_test() -> dict:
    sample = (
        b"spec=fury\n"
        b"actions.precombat=flask\n"
        b"actions.precombat+=/food\n"
        b"actions=call_action_list,name=multi,if=active_enemies>=3\n"
        b"actions+=/call_action_list,name=single,if=active_enemies=1\n"
        b"actions+=/filler\n"
        b"actions.multi=whirlwind\n"
        b"actions.multi+=/rampage\n"
        b"actions.single=rampage,if=rage>=80\n"
        b"actions.single+=/bloodthirst\n"
    )
    def case(ts, phase, targets=None, rage=None, readiness=None,
             extra=(), unobservable=()):
        transitions = []
        if targets is not None:
            transitions.append({"timestamp_ms":ts-30,"key":"target_feature","value":targets})
        if rage is not None:
            transitions.append({"timestamp_ms":ts-30,"key":"rage_feature","value":rage})
        transitions.extend(extra)
        return {
            "timestamp_ms":ts,"phase":phase,
            "transitions":transitions,
            "action_readiness":readiness or {},
            "unobservable_keys":list(unobservable),
            "target_count_label":targets if targets is not None else "UNKNOWN",
        }
    fixture = {
        "schema":INPUT_SCHEMA,"spec":"fury",
        "mode":"EXPLICIT_STRICT_PRE_SYNTHETIC_OR_ATTESTED",
        "operand_to_feature":{
            "active_enemies":"target_feature","rage":"rage_feature"
        },
        "decisions":[
            case(1000,"OPENER",targets=1,rage=90,
                 readiness={"rampage":"READY"}),
            case(1100,"OPENER",targets=1,rage=40,
                 readiness={"bloodthirst":"READY"}),
            case(1200,"POST_OPENER",targets=3,rage=10,
                 readiness={"whirlwind":"READY"}),
            case(1300,"POST_OPENER",targets=1,rage=90,
                 readiness={"rampage":"UNKNOWN"}),
            case(1400,"POST_OPENER",targets=None,rage=90,
                 readiness={"rampage":"READY"}),
            case(1500,"POST_OPENER",targets=3,rage=0,
                 readiness={"whirlwind":"READY"},
                 extra=[
                     {"timestamp_ms":1500,"key":"target_feature","value":1},
                     {"timestamp_ms":1600,"key":"target_feature","value":1}
                 ]),
        ],
    }
    only=inspect_source_only(sample,spec="fury")
    assert only["precombat_is_combat_opener"] is False
    assert len(only["precombat_directives"])==2
    assert len(only["target_count_guard_candidates"])>=2
    assert only["combat_opener_sequence_inferred"] is False
    r = build_baseline(sample, spec="fury", fixture=fixture)
    checks = []
    def check(name, value):
        if not value: raise AssertionError("BASELINE_FIXTURE_"+name)
        checks.append(name)
    rows = r["decision_samples"]
    check("phase_opener_count",r["explicit_opener_sample_count"]==2)
    check("phase_post_count",r["post_opener_sample_count"]==4)
    check("precombat_not_opener",len(r["precombat_apl_directives_not_combat_opener"])==2)
    check("precombat_never_executed",all(not x["precombat_executed"] for x in r["precombat_apl_directives_not_combat_opener"]))
    check("single_high_rage",rows[0]["hypothesis_action_token"]=="rampage")
    check("single_low_rage",rows[1]["hypothesis_action_token"]=="bloodthirst")
    check("three_targets",rows[2]["hypothesis_action_token"]=="whirlwind")
    check("unknown_readiness_blocks",rows[3]["hypothesis_action_token"] is None)
    check("unknown_readiness_reason","READINESS" in rows[3]["reason"])
    check("missing_targets_blocks",rows[4]["hypothesis_action_token"] is None)
    check("same_timestamp_no_leak",rows[5]["hypothesis_action_token"]=="whirlwind")
    check("same_timestamp_excluded",rows[5]["same_timestamp_events_excluded"]==1)
    check("future_excluded",rows[5]["future_events_excluded"]==1)
    check("source_sha",r["source_apl_sha256"]==hashlib.sha256(sample).hexdigest())
    check("no_wcl_blind_contamination",r["WCL_blind_lane_consumed"] is False)
    check("no_gameplay_promotion",r["validated_general_rotation_IR"] is False)
    check("no_opener_sequence_inference",r["opener_sequence_proven_complete"] is False)
    check("general_spec_no_hardcode",build_baseline(
        sample.replace(b"spec=fury",b"spec=arcane"),
        spec="arcane",
        fixture={**fixture,"spec":"arcane"}
    )["source_spec"]=="arcane")
    for label, mutant in [
        ("guard_spec", {**fixture,"spec":"other"}),
        ("missing_provenance", {**fixture,"mode":"UNVERIFIED"}),
        ("missing_readiness", {**fixture,"decisions":[{k:v for k,v in fixture["decisions"][0].items() if k!="action_readiness"}]}),
        ("bad_time", {**fixture,"decisions":[
            fixture["decisions"][0],{**fixture["decisions"][1],"timestamp_ms":1000}
        ]}),
        ("no_opener_after_end", {**fixture,"decisions":[
            fixture["decisions"][2],fixture["decisions"][0]
        ]}),
    ]:
        try: build_baseline(sample,spec="fury",fixture=mutant)
        except (BaselineError, ValueError): checks.append(label+"_rejected")
        else: raise AssertionError("NEGATIVE_CASE_ACCEPTED_"+label)
    return {
        "result":"PASS",
        "synthetic_assertion_count":len(checks),
        "checks":checks,
        "production_WCL_SimC_Blizzard_live":"NOT_RUN",
        "actual_gameplay_opener": "NOT_PROVEN",
        "actual_training_feedback":"NOT_PROVEN",
        "MAIN_FROZEN_modified":False,
    }


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--actions-file",type=Path)
    ap.add_argument("--spec")
    ap.add_argument("--fixture",type=Path)
    ap.add_argument("--source-only",action="store_true",help="inspect a pinned real APL without fabricating combat decisions")
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.self_test or (args.actions_file is None and args.fixture is None and args.spec is None):
        print(json.dumps(self_test(),indent=2,ensure_ascii=False))
        return 0
    if args.source_only:
        if args.actions_file is None or not args.spec or args.fixture is not None:
            ap.error("--source-only requires --actions-file and --spec, without --fixture")
        result=inspect_source_only(args.actions_file.read_bytes(),spec=args.spec)
    else:
        if args.actions_file is None or args.fixture is None or not args.spec:
            ap.error("--actions-file, --spec and --fixture must be supplied together")
        result=build_baseline(
            args.actions_file.read_bytes(),
            spec=args.spec,
            fixture=json.loads(args.fixture.read_text(encoding="utf-8")),
        )
    raw=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(raw,encoding="utf-8")
        print("WROTE_SIMC_OPENER_PRIORITY_HYPOTHESIS")
    else:
        print(raw,end="")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
