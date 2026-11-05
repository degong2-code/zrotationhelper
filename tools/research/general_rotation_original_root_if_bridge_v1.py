#!/usr/bin/env python3
"""Source-pinned native IF comparator for already proven original root PRE.

The independent AST consumes ONLY original C++ active_enemies PRE facts.
The native if_expr->success() result is a POST comparator, never an AST
operand or full action_ready witness.  Identical SimC timestamps are joined
only through the actual C++ RAII root/method call IDs, not a time heuristic.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_source_route_audit_v1 import _bounded_body, _source_code_mask, git_blob
from general_rotation_select_pre_passive_producer_v1 import REVISION
from general_rotation_root_actor_pre_producer_v1 import SCHEMA as ROOT_SCHEMA, MARK as ROOT_MARK
from general_rotation_root_actor_pre_replay_v1 import replay as replay_original_root
from general_rotation_call_scope_instrument_v1 import TRACE_MARK
from general_rotation_select_sweep_instrument_v1 import RESULT_MARK
from general_rotation_time_scoped_priority_ir_v1 import SCHEMA as TIME_SCHEMA
from general_rotation_source_eligibility_decision_ir_v1 import POLICY
from simc_apl_semantic_ir_v2 import parse_profile, evaluate_ast, truth

SCHEMA = "ZrotOriginalRootNativeIFComparatorProducerV1"
REPLAY_SCHEMA = "ZrotOriginalRootPREIndependentIFVsNativeComparatorV1"
MARK = "ZROT_GENERIC_ROOT_NATIVE_IF_V1|"
PATH = "engine/action/action.cpp"
METHOD = "bool action_t::action_ready()"
OLD = "  if ( if_expr && !if_expr->success() )\n    return false;"
NEW = r"""  // Passive comparator: evaluate the ORIGINAL expression exactly once.
  if ( if_expr )
  {
    const bool zrot_original_if_result = if_expr->success();
    if ( sim->log && player && !player->is_pet() && !player->is_enemy() &&
         zrot_generic_call_scope_v1::current_root() != 0 )
      sim->print_log( "ZROT_GENERIC_ROOT_NATIVE_IF_V1|{}|{}|{}|{}",
        sim->current_time().total_millis(),
        zrot_generic_call_scope_v1::current_root(),
        zrot_generic_call_scope_v1::active_id(),
        zrot_original_if_result ? 1 : 0 );
    if ( !zrot_original_if_result )
      return false;
  }"""


class RootIFBridgeError(ValueError):
    pass


def digest(blob: bytes) -> str:
    return sha256(blob).hexdigest()


def method_region(source: str) -> tuple[str, int]:
    return _bounded_body(source, _source_code_mask(source), METHOD,
                         (0, len(source)))


def patch(pristine: bytes, previous: bytes) -> bytes:
    official = pristine.decode("utf8")
    current = previous.decode("utf8")
    original, _ = method_region(official)
    body, start = method_region(current)
    if (original.count(OLD) != 1 or original.count("if_expr->success()") != 1 or
        body.count(OLD) != 1 or body.count("if_expr->success()") != 1 or
        '#include "zrot_generic_call_scope_v1.hpp"' not in current or
        "ZROT_GENERIC_CALL_SCOPE_V1|" not in body or
        "ZROT_GENERIC_METHOD_PRE_V1|" not in body or
        MARK in current):
        raise RootIFBridgeError("PINNED_ORIGINAL_SINGLE_IF_METHOD_TRACE_REQUIRED")
    replaced = body.replace(OLD, NEW, 1)
    if (replaced.count("if_expr->success()") != 1 or
        replaced.count(MARK) != 1 or
        replaced.count("a->action_ready()") != body.count("a->action_ready()")):
        raise RootIFBridgeError("NATIVE_IF_ADDED_DECISION_CALL")
    return (current[:start] + replaced + current[start + len(body):]).encode("utf8")


def generate(root: Path, root_pre_receipt: Path) -> dict:
    root = root.resolve(strict=True)
    revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
        capture_output=True, text=True).stdout.strip()
    if revision != REVISION:
        raise RootIFBridgeError("OFFICIAL_SOURCE_REVISION_CHANGED")
    ancestor = root_pre_receipt.read_bytes()
    prior = json.loads(ancestor)
    if (prior.get("schema") != ROOT_SCHEMA or
        prior.get("source_revision") != REVISION or
        prior.get("added_ready_calls") != 0 or
        prior.get("operand_source_cpp") != "sim->active_enemies"):
        raise RootIFBridgeError("EXACT_ROOT_PRE_PROVENANCE_REQUIRED")
    path = root / PATH
    previous = path.read_bytes()
    original = subprocess.run(
        ["git", "-C", str(root), "show", f"{REVISION}:{PATH}"],
        check=True, capture_output=True).stdout
    blob = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{REVISION}:{PATH}"],
        check=True, capture_output=True, text=True).stdout.strip()
    if git_blob(original) != blob:
        raise RootIFBridgeError("ORIGINAL_GIT_BLOB_MISMATCH")
    changed = patch(original, previous)
    path.write_bytes(changed)
    return {
        "schema": SCHEMA, "source_revision": REVISION,
        "official_action_source_path": PATH, "official_action_blob_sha1": blob,
        "source_before_sha256": digest(previous),
        "source_after_sha256": digest(changed),
        "root_PRE_producer_receipt_sha256": digest(ancestor),
        "native_if_marker": MARK,
        "original_native_if_expression_evaluations_per_callsite": 1,
        "new_IF_ready_rng_target_calls": 0,
        "capture_phase": "NATIVE_IF_RESULT_AFTER_ORIGINAL_EVALUATION",
        "independent_source_PRE_ast_input": False,
        "native_compilation_and_ab_parity": "NOT_RUN",
        "full_READY_proven": 0, "WCL_API_calls": 0
    }


def _temporal_roots(profile: bytes, temporal: dict) -> dict:
    if (temporal.get("schema") != TIME_SCHEMA or
        temporal.get("product_policy_id") != POLICY or
        temporal.get("source_profile_git_blob_sha1") != git_blob(profile) or
        temporal.get("independent_FULL_READY_proven") != 0 or
        temporal.get("source_order_complete") is not False):
        raise RootIFBridgeError("SOURCE_TIME_IR_NOT_PINNED")
    lists = parse_profile(profile, require_source=False)["action_lists"]
    roots = {}
    for sweep in temporal["observed_time_scoped_selection_frontiers"]:
        owner = sweep["source_list"]
        for event in sweep["observed_candidate_event_stream"]:
            if event.get("stage") != "ACTION_READY_CALLED":
                continue
            rid = event["original_action_ready_root_id"]
            ordinal = event["ordinal_one_based"]
            row = lists[owner][ordinal - 1]
            if (rid in roots or event["source_row_sha256"] != row["source_sha256"]
                or event["source_action"] != row["action"]):
                raise RootIFBridgeError("DUPLICATED_OR_WRONG_ORIGINAL_SOURCE_ROOT")
            roots[rid] = (sweep["at_simc_ms"], owner, ordinal, row)
    if len(roots) != temporal["original_ready_calls"]:
        raise RootIFBridgeError("ORIGINAL_SOURCE_ROOT_COUNT_DRIFT")
    return roots


def corroborate(log: str, profile: bytes, temporal: dict,
                root_producer: dict, native_if_producer: dict) -> dict:
    if (native_if_producer.get("schema") != SCHEMA or
        native_if_producer.get("source_revision") != REVISION or
        native_if_producer.get("native_if_marker") != MARK or
        native_if_producer.get("new_IF_ready_rng_target_calls") != 0 or
        native_if_producer.get("full_READY_proven") != 0):
        raise RootIFBridgeError("SOURCE_NATIVE_IF_PRODUCER_REQUIRED")
    # Mandatory independent source-root causal replay first.
    base = replay_original_root(log, profile, temporal, root_producer)
    roots = _temporal_roots(profile, temporal)
    active = set()
    pre = {}
    returned = set()
    base_frames = {}
    native = {}
    counts = Counter()
    for raw in log.splitlines():
        if TRACE_MARK in raw:
            if raw.count(TRACE_MARK) != 1:
                raise RootIFBridgeError("AMBIGUOUS_CALL_SCOPE_MARKER")
            parts = raw.split(TRACE_MARK, 1)[1].strip().split("|")
            if len(parts) != 10:
                raise RootIFBridgeError("MALFORMED_CXX_CALL_SCOPE")
            clock, direction, kind, call, parent, root, method, owner, ord_s, name = parts
            if (not clock.isdigit() or not call.isdigit() or
                not root.isdigit() or not ord_s.isdigit()):
                raise RootIFBridgeError("CXX_CALL_SCOPE_ID_INVALID")
            rid, cid = int(root), int(call)
            if kind == "SELECT":
                if (rid not in roots or cid != rid or
                    int(clock) != roots[rid][0]):
                    raise RootIFBridgeError("NONCAUSAL_SOURCE_ROOT")
                if direction == "BEGIN":
                    if rid in active:
                        raise RootIFBridgeError("DUPLICATE_ROOT_BEGIN")
                    active.add(rid)
                elif direction == "END":
                    if rid not in active:
                        raise RootIFBridgeError("ROOT_END_WITHOUT_BEGIN")
                    active.remove(rid)
                else:
                    raise RootIFBridgeError("UNKNOWN_SCOPE_DIRECTION")
            elif kind == "METHOD" and method == "base_action":
                if direction == "BEGIN":
                    if (cid in base_frames or rid not in active or
                        (owner, int(ord_s), name) !=
                        (roots[rid][1], roots[rid][2], roots[rid][3]["action"])):
                        raise RootIFBridgeError("NATIVE_IF_METHOD_NOT_SOURCE_ROW")
                    base_frames[cid] = rid
                elif direction == "END":
                    if base_frames.pop(cid, None) != rid:
                        raise RootIFBridgeError("UNBALANCED_BASE_ACTION_FRAME")
            continue
        if ROOT_MARK in raw:
            parts = raw.split(ROOT_MARK, 1)[1].strip().split("|")
            if (len(parts) != 4 or not parts[0].isdigit() or
                not parts[1].isdigit() or parts[2] != "active_enemies" or
                not re.fullmatch(r"[0-9]+", parts[3])):
                raise RootIFBridgeError("INVALID_SOURCE_ROOT_ACTOR_PRE")
            rid = int(parts[1])
            if rid in pre or rid not in active or rid in returned:
                raise RootIFBridgeError("NONCAUSAL_SOURCE_ROOT_FACT")
            pre[rid] = int(parts[3])
            continue
        if RESULT_MARK in raw:
            parts = raw.split(RESULT_MARK, 1)[1].strip().split("|")
            if len(parts) != 3 or not parts[1].isdigit():
                raise RootIFBridgeError("UNMAPPED_NATIVE_READY_COMPARATOR")
            returned.add(int(parts[1]))
            continue
        if MARK in raw:
            if raw.count(MARK) != 1:
                raise RootIFBridgeError("AMBIGUOUS_NATIVE_IF_MARKER")
            parts = raw.split(MARK, 1)[1].strip().split("|")
            if (len(parts) != 4 or not all(p.isdigit() for p in parts[:3])
                or parts[3] not in ("0", "1")):
                raise RootIFBridgeError("INVALID_NATIVE_IF_RECORD")
            at, rid, mid = map(int, parts[:3])
            if (rid not in roots or at != roots[rid][0] or rid not in active
                or rid not in pre or rid in returned):
                raise RootIFBridgeError("NATIVE_IF_OUTSIDE_ORIGINAL_PRE_CALL")
            # Unmapped virtual/base method call is explicitly UNKNOWN.
            if base_frames.get(mid) != rid:
                counts["unlinked_original_method_if_unknown"] += 1
                continue
            native.setdefault(rid, []).append(parts[3] == "1")
    if active or base_frames or len(pre) != len(roots) or len(returned) != len(roots):
        raise RootIFBridgeError("INCOMPLETE_NATIVE_SOURCE_ROOT_REPLAY")
    counts["original_root_pre_linked"] = len(roots)
    examples = []
    conflicts = []
    for rid, (at, owner, ordinal, row) in roots.items():
        expr = row["expression_fields"].get("if")
        if expr is None:
            counts["root_without_apl_if"] += 1
            continue
        independently = truth(evaluate_ast(expr["ast"], {"active_enemies": pre[rid]}))
        comparators = native.get(rid, [])
        if not comparators:
            counts["native_if_not_source_observed_unknown"] += 1
            continue
        if len(comparators) != 1:
            counts["multiple_native_if_within_root_unknown"] += 1
            continue
        counts["one_source_linked_original_native_if"] += 1
        if independently is None:
            counts["other_unobserved_if_symbols_unknown"] += 1
            continue
        match = bool(independently) == comparators[0]
        counts["independent_ast_vs_original_native_if_" +
               ("match" if match else "conflict")] += 1
        sample = {"root_id": rid, "at_simc_ms": at,
                  "source_row_sha256": row["source_sha256"],
                  "source_list": owner, "ordinal_one_based": ordinal,
                  "ast_from_direct_original_PRE": bool(independently),
                  "original_native_if_return_comparator": comparators[0],
                  "full_action_ready": "UNKNOWN"}
        if len(examples) < 12:
            examples.append(sample)
        if not match:
            conflicts.append(sample)
    counts["original_if_ast_determinate_before_native_comparison"] = (
        base["counts"].get("if_recomputed_from_original_actor_PRE", 0))
    if (counts["independent_ast_vs_original_native_if_match"] +
        counts["independent_ast_vs_original_native_if_conflict"] >
        counts["original_if_ast_determinate_before_native_comparison"]):
        raise RootIFBridgeError("IF_COMPARATOR_EXCEEDS_PRE_EVIDENCE")
    return {
        "schema": REPLAY_SCHEMA, "product_policy_id": POLICY,
        "source_profile_git_blob_sha1": git_blob(profile),
        "exact_original_action_ready_roots": len(roots),
        "status_counts": dict(sorted(counts.items())),
        "independent_ast_vs_original_native_if_conflicts": conflicts[:12],
        "first_bounded_comparisons": examples,
        "native_if_comparison_truth_is_post_only": True,
        "independent_full_action_ready_proven": 0,
        "source_order_complete": False,
        "WCL_latest_transition_strict_PRE_claim": False,
        "WCL_blind_semantics_injected": False,
        "dummy_feedback_permitted": False, "WCL_API_calls": 0
    }


def selftest() -> dict:
    # Exact original control semantics and a source-pinned prior instrument.
    official = (METHOD + "\n{\n" + OLD + "\n}\n").encode()
    previous = (METHOD + '\n{\n  // ZROT_GENERIC_CALL_SCOPE_V1|\n'
                '  // ZROT_GENERIC_METHOD_PRE_V1|\n' + OLD +
                '\n}\n#include "zrot_generic_call_scope_v1.hpp"\n').encode()
    changed = patch(official, previous).decode()
    assert changed.count("if_expr->success()") == 1
    assert changed.count(MARK) == 1
    assert changed.count("a->action_ready()") == 0
    for bad in (previous.replace(b"if_expr->success()", b"if_expr->evaluate()"),
                changed.encode()):
        try:
            patch(official, bad)
        except RootIFBridgeError:
            pass
        else:
            raise AssertionError("UNVERIFIED_NATIVE_IF_PATCH_ACCEPTED")
    p = b'warrior="Synthetic"\nspec=fury\nactions=/foo,if=active_enemies>=2\n'
    row = parse_profile(p, require_source=False)["action_lists"]["default"][0]
    temporal = {
        "schema": TIME_SCHEMA, "product_policy_id": POLICY,
        "source_profile_git_blob_sha1": git_blob(p),
        "source_order_complete": False, "independent_FULL_READY_proven": 0,
        "original_ready_calls": 1,
        "observed_time_scoped_selection_frontiers": [{
            "source_list": "default", "at_simc_ms": 100,
            "observed_candidate_event_stream": [{
                "stage": "ACTION_READY_CALLED",
                "original_action_ready_root_id": 7,
                "ordinal_one_based": 1,
                "source_row_sha256": row["source_sha256"],
                "source_action": "foo",
                "simc_NATIVE_return_post_comparator": True}]}]}
    root_receipt = {
        "schema": ROOT_SCHEMA, "operand_symbol": "active_enemies",
        "operand_source_cpp": "sim->active_enemies",
        "root_PRE_marker": ROOT_MARK,
        "original_action_ready_call_count": 1, "added_ready_calls": 0,
        "direct_before_call_snapshot_same_simc_tick": True,
        "WCL_latest_transition_before_t_claim": False}
    bridge_receipt = {
        "schema": SCHEMA, "source_revision": REVISION,
        "native_if_marker": MARK, "new_IF_ready_rng_target_calls": 0,
        "full_READY_proven": 0}
    begin = TRACE_MARK + "100|BEGIN|SELECT|7|0|7|select_call|default|1|foo"
    pre = ROOT_MARK + "100|7|active_enemies|2"
    method_begin = TRACE_MARK + "100|BEGIN|METHOD|8|7|7|base_action|default|1|foo"
    observed = MARK + "100|7|8|1"
    method_end = TRACE_MARK + "100|END|METHOD|8|7|7|base_action|default|1|foo"
    comparator = RESULT_MARK + "100|7|1"
    end = TRACE_MARK + "100|END|SELECT|7|0|7|select_call|default|1|foo"
    events = [begin, pre, method_begin, observed, method_end, comparator, end]
    def check(records):
        return corroborate("\n".join(records), p, temporal,
                           root_receipt, bridge_receipt)
    matched = check(events)
    assert matched["status_counts"]["independent_ast_vs_original_native_if_match"] == 1
    assert matched["independent_full_action_ready_proven"] == 0
    no_if = check([x for x in events if x != observed])
    assert no_if["status_counts"]["native_if_not_source_observed_unknown"] == 1
    conflict = check([x.replace(MARK+"100|7|8|1", MARK+"100|7|8|0")
                      if x == observed else x for x in events])
    assert conflict["status_counts"]["independent_ast_vs_original_native_if_conflict"] == 1
    for bad in (
        [begin, pre, method_begin, method_end, comparator, observed, end],
        [begin, pre, method_begin,
         observed.replace("|7|8|", "|17|8|"),
         method_end, comparator, end],
        [begin, pre, method_begin,
         observed.replace("|7|8|", "|7|9|"),
         method_end, comparator, end],
    ):
        try:
            check(bad)
        except RootIFBridgeError:
            pass
        else:
            raise AssertionError("UNSCOPED_NATIVE_IF_COMPARATOR_ACCEPTED")
    return {"schema": SCHEMA, "status": "PASS_OFFLINE_SYNTHETIC",
            "checks": 11, "Native_CXX_executed": False,
            "independent_AST_native_IF_match_synthetic": 1,
            "full_READY_proven": 0, "WCL_API_calls": 0}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root", type=Path)
    p.add_argument("--root-pre-receipt", type=Path)
    p.add_argument("--receipt", type=Path)
    args = p.parse_args()
    if args.simc_root is None and args.root_pre_receipt is None:
        result = selftest()
    elif args.simc_root is not None and args.root_pre_receipt is not None:
        result = generate(args.simc_root, args.root_pre_receipt)
    else:
        p.error("source root and verified source root PRE receipt required together")
    data = canonical(result)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        with args.receipt.open("xb") as output:
            output.write(data)
    else:
        print(data.decode(), end="")


if __name__ == "__main__":
    main()
