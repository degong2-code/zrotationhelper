#!/usr/bin/env python3
"""Offline synthetic behavior tests for exact-pinned public research modules.

No WCL calls or gameplay entrypoint. Only pure identity, coverage and strict
PRE aura-index modules may be imported from the public research checkout.
The archived 124-file package is NOT available in public GitHub Actions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "02_SOURCE/runtime"
PINS = {
    "raid_dps/core/coverage.py": "30daad468f43ab012f4d85cb457ba838899bef5ddaf32acb4d14645043ba8147",
    "raid_dps/core/identity.py": "d2328bef5f7db3fa973cbb99b2125f13d796a5249be3c007219c38509965f8b6",
    "raid_dps/core/prestate.py": "889fdd114f5a07d31612c0fc2a548ac0dfab1dc1d5738e8741f573194efd7d50",
}


def _candidate_prestate(original):
    """Patch only the discovered zero-stack fallback in an isolated module."""
    name = "raid_dps.core.prestate_zero_stack_candidate"
    original_text = (RUNTIME / "raid_dps/core/prestate.py").read_text(encoding="utf-8")
    old = """        stack = (
            as_int(
                event.get("stack")
            )
            or as_int(
                event.get("stacks")
            )
        )

        # WCL payloads can omit the post-event stack count."""
    new = """        stack = as_int(event.get("stack"))
        if stack is None:
            stack = as_int(event.get("stacks"))

        # WCL payloads can omit the post-event stack count."""
    if original_text.count(old) != 1:
        raise AssertionError("CANDIDATE_PATCH_CONTEXT_CHANGED")
    patched = original_text.replace(old, new, 1)
    candidate = types.ModuleType(name)
    candidate.__file__ = "<temporary in-memory candidate only>"
    candidate.__package__ = "raid_dps.core"
    exec(compile(patched, name, "exec"), candidate.__dict__)
    if candidate.aura_transition({
        "type": "removebuffstack", "abilityGameID": 101, "stack": 0
    }) != (False, 0):
        raise AssertionError("CANDIDATE_ZERO_STACK_NOT_FIXED")
    return candidate


def reproduce_defect(original) -> dict:
    events=[
        {"timestamp":100,"type":"applybuff","abilityGameID":101,"stack":3},
        {"timestamp":110,"type":"removebuffstack","abilityGameID":101,"stack":0},
    ]
    index=original.AuraIdIndex(events)
    old_state=index.state_pre(101,111)
    if old_state!=(True,1):
        raise AssertionError("ORIGINAL_DEFECT_NOT_REPRODUCED")
    if index.state_pre(101,110)!=(True,3):
        raise AssertionError("ORIGINAL_STRICT_PRE_ALREADY_DIFFERENT")
    return {
      "schema":"ZrotPrestateZeroStackOriginalDefectReproductionV1",
      "result":"KNOWN_LEGACY_DEFECT_REPRODUCED",
      "original_module_sha256":PINS["raid_dps/core/prestate.py"],
      "event":{"type":"removebuffstack","stack":0,"timestamp":110},
      "original_next_timestamp_state":list(old_state),
      "expected_next_timestamp_state":[False,0],
      "same_timestamp_prior_state":[True,3],
      "original_code_modified":False,
      "FROZEN_modified":False,
      "MAIN_promoted":False,
    }


def run_fixture(*, candidate_patch:bool=False, original_defect_repro:bool=False) -> dict:
    for relative, expected_sha in PINS.items():
        data = (RUNTIME / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_sha:
            raise AssertionError("RESEARCH_SOURCE_NOT_HISTORICAL_SHA:" + relative)
    sys.path.insert(0, str(RUNTIME))
    try:
        from raid_dps.core import coverage as cov
        from raid_dps.core import identity as ident
        from raid_dps.core import prestate as pre
    finally:
        sys.path.remove(str(RUNTIME))

    if original_defect_repro:
        return reproduce_defect(pre)
    if not candidate_patch:
        raise AssertionError("ORIGINAL_PRESTATE_HAS_KNOWN_ZERO_STACK_DEFECT_USE_--original-defect-repro_OR_--candidate-patch")
    pre = _candidate_prestate(pre)

    passed = []
    def check(label: str, ok: bool) -> None:
        if not ok:
            raise AssertionError("OFFLINE_RESEARCH_FIXTURE_FAILURE:" + label)
        passed.append(label)

    # Runtime identity must NOT resolve a localized name-only event.
    check("id_abilityGameID", ident.event_ability_id({"abilityGameID": 901}) == 901)
    check("id_abilityID_fallback", ident.event_ability_id({"abilityID": "902"}) == 902)
    check("id_nested_gameID", ident.event_ability_id({"ability": {"gameID": 903}}) == 903)
    check("id_display_name_is_not_identity", ident.event_ability_id({"name": "Localized Spell"}) is None)
    check("id_stable_locale_independent", ident.stable_ability_identity({"ability": {"id": 904}}) == "ability:904")
    check("id_missing_unresolvable", ident.stable_ability_identity({"name": "x"}) is None)

    events = [
        {"timestamp": 100, "type": "applybuff", "abilityGameID": 101, "stack": 1},
        {"timestamp": 110, "type": "applybuffstack", "abilityGameID": 101, "stack": 3},
        {"timestamp": 120, "type": "removebuff", "abilityGameID": 101},
        {"timestamp": 115, "type": "applybuff", "abilityGameID": 102, "stack": 2},
        {"timestamp": 125, "type": "removebuff", "abilityGameID": 102},
        {"timestamp": 130, "type": "applybuff", "abilityGameID": 103},
        {"timestamp": 135, "type": "removebuffstack", "abilityGameID": 103, "stack": 0},
        {"timestamp": 140, "type": "applybuff", "name": "Only localized name"},
        {"timestamp": 170, "type": "applybuff", "abilityGameID": 101, "stack": 5},
    ]
    index = pre.AuraIdIndex(events)

    check("strict_pre_at_first_apply", index.state_pre(101, 100) == (False, 0))
    check("strict_pre_between_apply_and_stack", index.state_pre(101, 109.99) == (True, 1))
    check("strict_pre_excludes_same_timestamp_stack", index.state_pre(101, 110) == (True, 1))
    check("strict_pre_stack_after_event", index.state_pre(101, 110.001) == (True, 3))
    check("strict_pre_excludes_same_timestamp_removal", index.state_pre(101, 120) == (True, 3))
    check("strict_pre_removal_after_event", index.state_pre(101, 120.001) == (False, 0))
    check("strict_pre_no_future_170_at_160", index.state_pre(101, 160) == (False, 0))
    check("strict_pre_future_apply_visible_only_after", index.state_pre(101, 170.001) == (True, 5))
    check("strict_pre_unknown_ability", index.state_pre(999, 120) == (False, 0))
    check("strict_pre_same_timestamp_other_id_excluded", index.state_pre(102, 115) == (False, 0))
    check("strict_pre_other_id_after_apply", index.stack_pre(102, 116) == 2)
    check("strict_pre_other_id_same_timestamp_remove_excluded", index.state_pre(102, 125) == (True, 2))
    check("strict_pre_other_id_remove_visible_after", index.state_pre(102, 126) == (False, 0))
    check("strict_pre_any_equivalent_id", index.any_active_pre([101, 102], 116) is True)
    check("strict_pre_latest_equivalent_ids", index.latest_state_pre([101, 102], 116) == (True, 2))
    check("strict_pre_latest_equivalent_ids_at_125", index.latest_state_pre([101, 102], 125) == (False, 0))
    check("strict_pre_default_stack_on_apply", index.state_pre(103, 130.01) == (True, 1))
    check("strict_pre_stack_zero_after_removed", index.state_pre(103, 135.01) == (False, 0))
    check("strict_pre_localized_name_no_ability_id", 9999 not in index.by_id)

    # Coverage is observational availability, NOT evidence strength.
    check("coverage_trackable_95", cov.classify_coverage(95, 100) == cov.TRACKABLE)
    check("coverage_partial_20", cov.classify_coverage(20, 100) == cov.PARTIAL)
    check("coverage_partial_94", cov.classify_coverage(94, 100) == cov.PARTIAL)
    check("coverage_masked_under_20", cov.classify_coverage(19, 100) == cov.MASKED)
    check("coverage_semantic_mask_overrides_100", cov.classify_coverage(100, 100, semantic_mask=True) == cov.MASKED)
    check("coverage_empty_total_unknown_masked", cov.classify_coverage(0, 0) == cov.MASKED)
    row = cov.coverage_record(field="resource", covered=100, total=100, semantic_mask=True, semantic_route="SYNTHETIC_ONLY")
    check("coverage_record_masked", row["status"] == cov.MASKED and row["coverage_pct"] == 100.0)
    check("coverage_record_no_strength_claim", not any(key in row for key in ("causal", "mandatory", "optimal")))

    return {
        "schema": "ZrotResearchStrictPreAndCoverageSyntheticReceiptV1",
        "mode":"BRANCH_ONLY_IN_MEMORY_ZERO_STACK_CANDIDATE",
        "original_bug_reproduced_separately":True,
        "original_research_source_modified":False,
        "candidate_only_in_memory":True,
        "result": "PASS",
        "research_module_original_sha_exact_n": len(PINS),
        "behavioral_assertion_count": len(passed),
        "assertions": passed,
        "strict_PRE_bisect_left_timestamp_less_than_t": "PASS",
        "same_timestamp_future_state_leakage": False,
        "state_readiness_missing_assumed_available": False,
        "coverage_label_treated_as_evidence_strength": False,
        "original_private_124_source_executed": False,
        "product_MAIN_entrypoint_executed": False,
        "WCL_SimC_Blizzard_live_calls": False,
        "current_product_authority": "UNKNOWN",
        "FROZEN_mutated": False,
        "seq578": "FAILED_QUARANTINED_PRESERVED",
        "seq637": "UNKNOWN",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true", help="execute offline synthetic fixture")
    parser.add_argument("--original-defect-repro", action="store_true")
    parser.add_argument("--candidate-patch", action="store_true")
    args = parser.parse_args()
    if args.original_defect_repro and args.candidate_patch:
        parser.error("choose exactly one mode")
    print(json.dumps(run_fixture(candidate_patch=args.candidate_patch, original_defect_repro=args.original_defect_repro), sort_keys=True, indent=2))
