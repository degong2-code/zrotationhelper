#!/usr/bin/env python3
"""Extract source-proven General Rotation opener *candidates* from fixed Native SimC.

The goal is a standing-target-dummy baseline, NOT a raid timeline. No movement
or raid_event expression is silently evaluated, omitted, or filled with zero.
Rows such as time<=0.5|movement.distance>5 retain their core-opener clause.
Native source selection is OBSERVED, not an independent readiness oracle or
a claim of optimality. Never use selected Native actions as WCL-blind input.

No arguments: synthetic; full inputs: verified pinned Fury ST/2T receipts.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile, git_blob

SCHEMA = "ZrotGeneralRotationDummyContextOpenerCandidateV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
FURY_PROFILE_BLOB = "3225992ed5b754ad5d61e8b785d9d859f1eed1be"
NATIVE_SELECTED_SHA256 = "d75b1b1fd614b03e73ff3ab269b4735da237f1707740a011b96f4f508509a816"
NATIVE_PRE_IF_SHA256 = "7d33ae0746d3d595e3012acb8590e78e476d3e4bf5d3b5e94f244329ea215027"
NATIVE_ACTION_SCOPED_SHA256 = "f0c410f6e86bfe98e0d7921d65e66a8cdb1b1a3b009dfa8dd7dd0d15597a67bb"
EXPECTED_RECEIPT_COUNTS = {
    "st": {"IF": 255, "selected": 100, "ready_attempts": 1542},
    "two_target": {"IF": 222, "selected": 90, "ready_attempts": 1030},
}
ENVIRONMENT_PREFIXES = ("movement.", "raid_event.movement.")
NATIVE_SELECTED_SCHEMA = "ZrotNativeSimcSelectedRowTwoTargetAuditV1"
NATIVE_PRE_IF_SCHEMA = "ZrotNativeIndependentPreIfRestrictedOperandReplayV1"
NATIVE_SCOPED_SCHEMA = "ZrotNativeActionGcdCooldownPreAstReplayV1"


class ContextEvidenceError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def is_external_symbol(symbol: str) -> bool:
    return symbol.startswith(ENVIRONMENT_PREFIXES)


def context_class(symbols: list[str]) -> str:
    if not symbols:
        return "NO_IF_CONDITION_OR_CONSTANT"
    external = [x for x in symbols if is_external_symbol(x)]
    if not external:
        return "CORE_CONDITION_ONLY"
    if len(external) == len(symbols):
        return "ENVIRONMENT_CONDITION_ONLY"
    return "MIXED_CORE_AND_ENVIRONMENT_CONDITION"


def row_annotation(row: dict) -> dict:
    expr = row["expression_fields"].get("if")
    symbols = expr["symbols"] if expr else []
    return {
        "source_condition": expr["source"] if expr else None,
        "source_symbols": symbols,
        "environment_symbols": sorted(x for x in symbols
                                       if is_external_symbol(x)),
        "context_class": context_class(symbols),
        "source_action_class": row["behavior"],
        "source_row_sha256": row["source_sha256"],
    }


def resolve_selected(row: dict, ir: dict):
    pointer = row["selected_row_pointer_proof"]
    if not isinstance(pointer, dict):
        raise ContextEvidenceError("SELECTED_ROW_WITHOUT_SOURCE_POINTER")
    name = pointer.get("list")
    index = pointer.get("source_index")
    items = ir["action_lists"].get(name)
    if items is None or type(index) is not int or not 0 <= index < len(items):
        raise ContextEvidenceError("NATIVE_SELECTED_ROW_NOT_IN_PINNED_APL")
    source = items[index]
    expected = {
        "list": source["list"],
        "source_index": source["index"],
        "source_action": source["action"],
        "source_text": source["source_text"],
        "source_file_line": source["source_line"],
        "source_sha256": source["source_sha256"],
    }
    if pointer != expected:
        raise ContextEvidenceError("NATIVE_SELECTED_SOURCE_POINTER_MISMATCH")
    if not row.get("native_action_ready_observed"):
        raise ContextEvidenceError("SOURCE_SELECTED_WITHOUT_NATIVE_READY_OBSERVATION")
    at = row.get("root_time_ms")
    if type(at) is not int or at < -3600000 or at > 86400000:
        raise ContextEvidenceError("INVALID_NATIVE_SELECTION_TIMESTAMP")
    if not isinstance(row.get("root_native_action"), str) or not row["root_native_action"]:
        raise ContextEvidenceError("NATIVE_SELECTION_ACTION_EMPTY")
    return source


def audit_if_rows(rows: list, ir: dict):
    counts = Counter()
    distinct_source = {}
    for row in rows:
        name, index = row["source_list"], row["source_index"]
        items = ir["action_lists"].get(name)
        if items is None or type(index) is not int or not 0 <= index < len(items):
            raise ContextEvidenceError("NATIVE_IF_SOURCE_INDEX_NOT_IN_APL")
        source = items[index]
        expr = source["expression_fields"].get("if")
        if (expr is None or
            row["source_line_sha256"] != source["source_sha256"] or
            row["source_if"] != expr["source"] or
            row["source_if_symbols"] != expr["symbols"]):
            raise ContextEvidenceError("NATIVE_IF_SOURCE_ROW_OR_SYMBOL_MISMATCH")
        bucket = context_class(expr["symbols"])
        counts[bucket] += 1
        distinct_source[(name, index)] = bucket
    return {
        "actual_native_IF_evaluations": len(rows),
        "context_dependency_evaluation_counts": dict(sorted(counts.items())),
        "distinct_source_IF_rows": len(distinct_source),
        "distinct_source_IF_rows_by_context": dict(sorted(Counter(
            distinct_source.values()).items())),
    }


def opener_candidates(selected, ir, *, window_ms: int):
    counts = Counter()
    seq = []
    prev_ts = None
    for r in selected:
        source = resolve_selected(r, ir)
        at = r["root_time_ms"]
        if prev_ts is not None and at < prev_ts:
            raise ContextEvidenceError("SELECTED_NATIVE_SOURCE_CLOCK_NOT_MONOTONIC")
        prev_ts = at
        info = row_annotation(source)
        counts[info["context_class"]] += 1
        if at > window_ms:
            continue
        if source["behavior"] in ("CALL", "RUN", "VARIABLE", "SWAP_UNSUPPORTED"):
            role = "APL_CONTROL_NOT_PLAYER_CAST"
        elif source["action"] == "auto_attack":
            role = "AUTO_ATTACK_SETUP_NOT_ROTATIONAL_BUTTON"
        elif source["action"] in ("potion", "use_item"):
            role = "CONSUMABLE_OR_EQUIPMENT_OPTION"
        else:
            role = "NATIVE_SELECTED_ACTION_CANDIDATE_NOT_VALIDATED_CAST"
        seq.append({
            "timestamp_ms": at,
            "native_selected_action": r["root_native_action"],
            "source_apl_action": source["action"],
            "role": role,
            "source_list": source["list"],
            "source_index": source["index"],
            **info,
        })
    return {
        "selected_native_actions_total": len(selected),
        "source_context_counts_selected_all": dict(sorted(counts.items())),
        "candidate_window_ms": window_ms,
        "native_selected_in_opener_window": len(seq),
        "native_selection_events_in_time_order": seq,
        "rotational_candidate_sequence_only": [
            x["native_selected_action"] for x in seq if
            x["role"] == "NATIVE_SELECTED_ACTION_CANDIDATE_NOT_VALIDATED_CAST"
        ],
    }


def audit(ir, native_selected, native_pre_if, native_scoped,
          *, window_ms: int = 12000):
    if not 0 < window_ms <= 30000:
        raise ContextEvidenceError("INVALID_OPENER_CANDIDATE_WINDOW")
    if native_selected.get("schema") != NATIVE_SELECTED_SCHEMA:
        raise ContextEvidenceError("SELECTED_SOURCE_RECEIPT_SCHEMA_MISMATCH")
    if native_pre_if.get("schema") != NATIVE_PRE_IF_SCHEMA:
        raise ContextEvidenceError("PRE_IF_RECEIPT_SCHEMA_MISMATCH")
    if native_scoped.get("schema") != NATIVE_SCOPED_SCHEMA:
        raise ContextEvidenceError("ACTION_SCOPED_RECEIPT_SCHEMA_MISMATCH")
    if (native_scoped.get("independently_replayed_IF_matches") != 317 or
        native_scoped.get("remaining_IF_UNKNOWN") != 160):
        raise ContextEvidenceError("CURRENT_317_IF_BASELINE_NOT_MATCHED")
    scenarios = {}
    overall = Counter()
    readiness_total = 0
    for label, expected in EXPECTED_RECEIPT_COUNTS.items():
        sel = native_selected[label]
        rows = native_pre_if[label]["all_native_if_pre_fact_ledger"]
        if len(rows) != expected["IF"]:
            raise ContextEvidenceError("PINNED_NATIVE_IF_COHORT_DRIFT")
        selected = sel["selected_foreground_root_examples"]
        native_attempts = sel["source_action_ready_attempts"]
        if (len(selected) != expected["selected"] or
            native_attempts["total"] != expected["ready_attempts"] or
            native_attempts["ready"] + native_attempts["not_ready"] !=
                native_attempts["total"]):
            raise ContextEvidenceError("PINNED_NATIVE_SELECT_COHORT_DRIFT")
        if native_scoped[label]["native_IF_count"] != expected["IF"]:
            raise ContextEvidenceError("SOURCE_SCOPED_IF_COUNTS_DRIFT")
        facts = audit_if_rows(rows, ir)
        opener = opener_candidates(selected, ir, window_ms=window_ms)
        for k, v in facts["context_dependency_evaluation_counts"].items():
            overall[k] += v
        readiness_total += native_attempts["total"]
        scenarios[label] = {
            "target_count": 1 if label == "st" else 2,
            "source_identified_actual_IFs": facts,
            "observed_native_selected_opener_candidates": opener,
            "native_ready_attempts_observed_not_independently_reproduced":
                native_attempts["total"],
            "native_ready_observed_true": native_attempts["ready"],
            "native_ready_observed_false": native_attempts["not_ready"],
            "independently_reproduced_ready_attempts": 0,
            "independent_ready_attempt_status": "NOT_YET_EVALUATED",
            "observed_source_only_not_cast_or_optimality_claim": True,
        }
    if sum(overall.values()) != 477 or readiness_total != 2572:
        raise ContextEvidenceError("SOURCE_COHORT_TOTAL_MISMATCH")
    return {
        "schema": SCHEMA,
        "scope_policy_id": POLICY,
        "profile_git_blob_sha1": ir["source_git_blob_sha1"],
        "policy_context": "STANDING_TARGET_DUMMY_GENERAL_ROTATION_RESEARCH",
        "native_source_evidence": "SIMC_ONLY_NO_WCL_SEMANTIC_LEAK",
        "simc_native_observations_not_mandatory_rotation": True,
        "no_environment_variable_false_or_zero_imputation": True,
        "no_environment_only_row_automatically_deleted": True,
        "mixed_OR_condition_core_branch_preserved": True,
        "dummy_environment_and_simulation_event_is_separated": True,
        "source_context_count_of_native_IFs": dict(sorted(overall.items())),
        "source_identified_native_IF_count": 477,
        "native_selected_source_root_rows_total": 190,
        "native_ready_attempts_observed": readiness_total,
        "independent_native_ready_attempts": 0,
        "native_ready_observation_used_as_independent_provider": False,
        "independent_native_selected_action_parity": "NOT_ESTABLISHED",
        "dummy_errored_cast_verdict_eligible": False,
        "general_rotation_opener_verified": False,
        "MAIN_or_FROZEN_promoted": False,
        "WCL_API_calls": 0,
        "st": scenarios["st"],
        "two_target": scenarios["two_target"],
    }


def selftest():
    raw = (
        b"actions=auto_attack\n"
        b"actions+=/charge,if=time<=0.5|movement.distance>5\n"
        b"actions+=/heroic_leap,if=raid_event.movement.distance>25&raid_event.movement.in>45\n"
        b"actions+=/run_action_list,name=single,if=active_enemies=1\n"
        b"actions.single=spell_a,if=rage>=10\n"
    )
    ir = parse_profile(raw, require_source=False)
    lists = ir["action_lists"]
    opener_row = lists["default"][1]
    context_row = lists["default"][2]
    assert context_class(opener_row["expression_fields"]["if"]["symbols"]) == (
        "MIXED_CORE_AND_ENVIRONMENT_CONDITION")
    assert context_class(context_row["expression_fields"]["if"]["symbols"]) == (
        "ENVIRONMENT_CONDITION_ONLY")
    assert row_annotation(opener_row)["source_condition"] == (
        "time<=0.5|movement.distance>5")
    def selected(row, ts):
        return {
            "root_time_ms": ts, "root_native_action": row["action"],
            "native_action_ready_observed": True,
            "selected_row_pointer_proof": {
                "list": row["list"], "source_index": row["index"],
                "source_action": row["action"],
                "source_text": row["source_text"],
                "source_file_line": row["source_line"],
                "source_sha256": row["source_sha256"],
            },
        }
    got = opener_candidates(
        [selected(lists["default"][0], 0),
         selected(opener_row, 0), selected(lists["default"][3], 0)],
        ir, window_ms=5000)
    assert got["native_selected_in_opener_window"] == 3
    assert got["rotational_candidate_sequence_only"] == ["charge"]
    assert got["native_selection_events_in_time_order"][2]["role"] == (
        "APL_CONTROL_NOT_PLAYER_CAST")
    assert got["native_selection_events_in_time_order"][1]["environment_symbols"] == [
        "movement.distance"]
    assert got["native_selection_events_in_time_order"][1]["source_condition"] == (
        "time<=0.5|movement.distance>5")
    a = selected(opener_row, 0)
    a["selected_row_pointer_proof"]["source_sha256"] = "f"*64
    try:
        resolve_selected(a, ir)
    except ContextEvidenceError:
        pass
    else:
        raise AssertionError("SPOOFED_APL_SOURCE_POINTER_ACCEPTED")
    pre_if = [{
        "source_list": "default", "source_index": 1,
        "source_line_sha256": opener_row["source_sha256"],
        "source_if": opener_row["expression_fields"]["if"]["source"],
        "source_if_symbols": opener_row["expression_fields"]["if"]["symbols"],
    }]
    assert audit_if_rows(pre_if, ir)["actual_native_IF_evaluations"] == 1
    pre_if[0]["source_if_symbols"] = []
    try:
        audit_if_rows(pre_if, ir)
    except ContextEvidenceError:
        pass
    else:
        raise AssertionError("ALTERED_IF_SOURCE_SYMBOLS_ACCEPTED")
    assert is_external_symbol("raid_event.movement.in")
    assert not is_external_symbol("buff.enrage.up")
    return {
        "status": "PASS_OFFLINE_SYNTHETIC", "checks": 12,
        "native_simc_not_run": True, "WCL_API_calls": 0,
        "movement_false_imputation": False,
        "full_action_ready_parity": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile", type=Path)
    p.add_argument("--native-selected-receipt", type=Path)
    p.add_argument("--native-if-pre-receipt", type=Path)
    p.add_argument("--native-action-scoped-receipt", type=Path)
    p.add_argument("--opener-window-ms", type=int, default=12000)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    fields = (a.official_profile, a.native_selected_receipt,
              a.native_if_pre_receipt, a.native_action_scoped_receipt)
    if not any(fields):
        value = selftest()
    elif all(fields):
        inputs = [x.read_bytes() for x in fields]
        for actual, expected in zip(
            inputs[1:],
            (NATIVE_SELECTED_SHA256, NATIVE_PRE_IF_SHA256,
             NATIVE_ACTION_SCOPED_SHA256),
        ):
            if sha(actual) != expected:
                raise ContextEvidenceError("IMMUTABLE_RECEIPT_SHA256_MISMATCH")
        ir = parse_profile(inputs[0], require_source=True,
                           expected_git_blob=FURY_PROFILE_BLOB)
        value = audit(ir, *(json.loads(blob) for blob in inputs[1:]),
                      window_ms=a.opener_window_ms)
        value["receipt_input_sha256"] = {
            "native_selected": sha(inputs[1]),
            "native_if_pre": sha(inputs[2]),
            "native_action_scoped": sha(inputs[3]),
        }
    else:
        p.error("four fixed proof inputs required, or none for synthetic")
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")) + "\n").encode("utf-8")
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("xb") as f:
            f.write(raw)
        print("GENERAL_ROTATION_DUMMY_CONTEXT_OPENER_SHA256=" + sha(raw))
    else:
        print(raw.decode(), end="")


if __name__ == "__main__":
    main()
