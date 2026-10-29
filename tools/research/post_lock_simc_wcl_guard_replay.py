#!/usr/bin/env python3
"""Research-only post-lock SimC guard/WCL strict-PRE alignment.

This probes whether SimC APL guards for an observed numeric action are true
in a WCL-shaped PRE state. It DOES NOT execute a complete APL, establish
recommended actions, certify independent candidate discovery, or validate
gameplay rules. Never use results as mismatch/optimality evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from simc_apl_condition_research import inspect_guards
from simc_apl_syntax_inventory import parse as parse_apl

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ReplayFixture:
    spec_slug: str
    build_key: str
    apl_spec: str
    observed_action_id: int
    strict_pre_state: Any
    profile_sha256: str


def _pin(raw: bytes, expected_sha256: str, name: str):
    if not isinstance(expected_sha256, str) or not SHA256_RE.fullmatch(expected_sha256):
        raise ValueError("INVALID_" + name + "_SHA256_PIN")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(name + "_SHA256_MISMATCH")


def _locked_numeric_actions(lock_bytes: bytes, lock_sha256: str):
    """Read lock artifact BYTES, not post-lock derived candidate lists.

    This enforces structural/numeric-only boundaries. The artifact's actual
    independent provenance still requires MAIN review; this cannot prove it.
    """
    _pin(lock_bytes, lock_sha256, "BLIND_LOCK")
    obj = json.loads(lock_bytes)
    if not isinstance(obj, dict):
        raise ValueError("BLIND_LOCK_OBJECT_REQUIRED")
    if obj.get("schema") != "ZrotWave3NumericCandidateLock":
        raise ValueError("BLIND_LOCK_SCHEMA_UNKNOWN")
    if obj.get("status") != "LOCKED_NUMERIC_ONLY":
        raise ValueError("BLIND_CANDIDATE_NOT_LOCKED")
    if obj.get("threshold_retuned_after_discovery") is not False:
        raise ValueError("THRESHOLD_LOCK_UNVERIFIED")
    if obj.get("semantic_names_attached") is not False:
        raise ValueError("SIMC_SEMANTIC_CONTAMINATION")
    if obj.get("gameplay_rule_claim") is not False:
        raise ValueError("BLIND_LOCK_GAMEPLAY_CLAIM")
    rows=obj.get("candidates")
    if not isinstance(rows, list) or not rows:
        raise ValueError("BLIND_LOCK_CANDIDATES_REQUIRED")
    if obj.get("candidate_n") != len(rows):
        raise ValueError("BLIND_LOCK_CANDIDATE_COUNT")
    found=set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("BLIND_LOCK_CANDIDATE_SHAPE")
        action=row.get("action_spell_id")
        if type(action) is not int or action <= 0:
            raise ValueError("BLIND_LOCK_ACTION_NOT_NUMERIC")
        if row.get("semantic_name", None) is not None:
            raise ValueError("CANDIDATE_SEMANTIC_NAME_PRE_LOCK")
        if row.get("gameplay_rule_claim", False) is not False:
            raise ValueError("CANDIDATE_GAMEPLAY_CLAIM")
        if row.get("priority_claim", False) is not False:
            raise ValueError("CANDIDATE_PRIORITY_CLAIM")
        if row.get("causality_claim", False) is not False:
            raise ValueError("CANDIDATE_CAUSAL_CLAIM")
        found.add(action)
    return found


def replay_post_lock(*, profile_text: str, fixture: ReplayFixture,
                     blind_lock_bytes: bytes, blind_lock_sha256: str,
                     apl_line_to_numeric_action: Mapping[int, int],
                     operand_to_pre_feature: Mapping[str, str]):
    """Compare only guard observability/consistency for one observed cast.

    The explicit name->numeric mapping is supplied *after* lock. Matching the
    cast to a TRUE guard is not a predicted-action MATCH, and a FALSE guard
    is not an observed-action CONFLICT (other rows may permit the cast).
    """
    if not fixture.spec_slug or not fixture.build_key or not fixture.apl_spec:
        raise ValueError("EXACT_SPEC_BUILD_AND_PROFILE_SPEC_REQUIRED")
    _pin(profile_text.encode("utf-8"), fixture.profile_sha256, "PROFILE")
    fixture.strict_pre_state.validate()
    if type(fixture.observed_action_id) is not int or fixture.observed_action_id <= 0:
        raise ValueError("OBSERVED_ACTION_NUMERIC_REQUIRED")
    locked_actions = _locked_numeric_actions(blind_lock_bytes, blind_lock_sha256)
    meta, groups = parse_apl(profile_text)
    if meta.get("spec") != fixture.apl_spec:
        raise ValueError("PROFILE_SPEC_MISMATCH")
    if not apl_line_to_numeric_action:
        return _result(fixture, blind_lock_sha256, "UNMAPPED_APL_ACTION",
                       [], [], "NO_POST_LOCK_NUMERIC_MAP")
    rows = {r["line"]: r for group in groups.values() for r in group}
    for line, action in apl_line_to_numeric_action.items():
        if type(line) is not int or line not in rows:
            raise ValueError("INVALID_APL_LINE_MAPPING")
        if rows[line]["kind"] != "ACTION_CANDIDATE":
            raise ValueError("CONTROL_DIRECTIVE_IS_NOT_ACTION")
        if type(action) is not int or action <= 0:
            raise ValueError("NUMERIC_ACTION_MAP_REQUIRED")
    # A lock whose candidate identity does not cover the observed cast
    # cannot be used as evidence about this cast.
    if fixture.observed_action_id not in locked_actions:
        return _result(fixture, blind_lock_sha256, "NO_LOCKED_CANDIDATE",
                       [], [], "CAST_NOT_IN_BLIND_LOCK")
    guards = inspect_guards(profile_text, fixture.strict_pre_state,
                            operand_to_feature=operand_to_pre_feature)
    matches = [g for g in guards
               if apl_line_to_numeric_action.get(g["line"]) == fixture.observed_action_id]
    if not matches:
        return _result(fixture, blind_lock_sha256, "UNMAPPED_APL_ACTION",
                       [], [], "NO_APL_ROW_FOR_OBSERVED_NUMERIC_CAST")
    statuses = {g["guard_status"] for g in matches}
    # TRUE first: another row can permit the same action when a FALSE row
    # exists. Unknown/unsupported cannot be collapsed into false.
    if "TRUE" in statuses:
        label="GUARD_TRUE_FOR_OBSERVED_ACTION"
    elif "UNKNOWN" in statuses or "UNSUPPORTED" in statuses:
        label="GUARD_UNRESOLVED"
    else:
        label="GUARD_FALSE_DISCREPANCY_CANDIDATE"
    return _result(
        fixture, blind_lock_sha256, label,
        [{"apl_line":g["line"], "guard_status":g["guard_status"],
          "unresolved_operands":list(g["missing_operands"])}
         for g in matches],
        sorted(locked_actions), "NOT_ACTION_PRIORITY_OR_CAUSALITY")


def _result(fixture, lock_sha, label, rows, action_ids, reason):
    return {
        "schema":"ZrotPostLockSimcWclGuardReplayResearchV1",
        "fixture_spec_slug":fixture.spec_slug,
        "fixture_build_key":fixture.build_key,
        "fixture_decision_timestamp_ms":fixture.strict_pre_state.decision_timestamp_ms,
        "profile_sha256":fixture.profile_sha256,
        "blind_lock_sha256":lock_sha,
        "blind_independence_verification":"NOT_RUN",
        "category":label,
        "guard_rows":rows,
        "locked_action_id_count":len(action_ids),
        "reason":reason,
        "recommended_action":None,
        "readiness":"UNKNOWN",
        "full_apl_execution":"NOT_RUN",
        "real_wcl_validation":"NOT_RUN",
        "gameplay_rule_promotion":False,
        "authority_promotion":False,
    }


def selftest():
    from pathlib import Path
    import sys
    root=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(root / "02_SOURCE" / "runtime"))
    from raid_dps.core.behavioral_evaluator import (
        StrictPreStateProvider, StateTransition,
    )
    profile=(
        "spec=enhancement\n"
        "actions=stormstrike,if=buff.test.stack>=5&active_enemies=2\n"
        "actions+=/stormstrike,if=active_enemies=1\n"
        "actions+=/lava_lash,if=buff.unknown.up\n"
    )
    lock={
        "schema":"ZrotWave3NumericCandidateLock",
        "status":"LOCKED_NUMERIC_ONLY",
        "candidate_n":2,
        "candidates":[
            {"action_spell_id":101,"semantic_name":None,"gameplay_rule_claim":False},
            {"action_spell_id":202,"semantic_name":None,"gameplay_rule_claim":False},
        ],
        "threshold_retuned_after_discovery":False,
        "semantic_names_attached":False,
        "gameplay_rule_claim":False,
    }
    raw=json.dumps(lock,sort_keys=True).encode()
    lock_sha=hashlib.sha256(raw).hexdigest()
    def fx(*,actual=101,transitions=None,profile_hash=None):
        state=StrictPreStateProvider().build(
            action_timestamp_ms=1000,
            transitions=transitions if transitions is not None else (
                StateTransition(900,"stacks",5),
                StateTransition(950,"enemies",2),
                StateTransition(1000,"stacks",0),
                StateTransition(1050,"enemies",1),
            ),
            required_keys=("stacks","enemies","missing"),
        )
        return ReplayFixture("enhancement_shaman","build_fixture",
                             "enhancement",actual,state,
                             profile_hash or hashlib.sha256(profile.encode()).hexdigest())
    kwargs={"profile_text":profile,"blind_lock_bytes":raw,
            "blind_lock_sha256":lock_sha,
            "apl_line_to_numeric_action":{2:101,3:101,4:202},
            "operand_to_pre_feature":{"buff.test.stack":"stacks",
                                      "active_enemies":"enemies",
                                      "buff.unknown.up":"missing"}}
    def replay(fixture,**changes):
        return replay_post_lock(fixture=fixture,**(kwargs|changes))
    a=replay(fx())
    assert a["category"]=="GUARD_TRUE_FOR_OBSERVED_ACTION" and a["guard_rows"][0]["guard_status"]=="TRUE"
    assert a["recommended_action"] is None and not a["gameplay_rule_promotion"]
    b=replay(fx(transitions=(
        StateTransition(900,"stacks",2),StateTransition(950,"enemies",3))))
    assert b["category"]=="GUARD_FALSE_DISCREPANCY_CANDIDATE"
    c=replay(fx(actual=202))
    assert c["category"]=="GUARD_UNRESOLVED"
    d=replay(fx(actual=303))
    assert d["category"]=="NO_LOCKED_CANDIDATE"
    e=replay(fx(),apl_line_to_numeric_action={4:202})
    assert e["category"]=="UNMAPPED_APL_ACTION"
    f=replay(fx(transitions=(
        StateTransition(900,"stacks",2),StateTransition(950,"enemies",1))))
    assert f["category"]=="GUARD_TRUE_FOR_OBSERVED_ACTION"
    assert len(f["guard_rows"])==2
    for changes,expected in (
        ({"blind_lock_sha256":"0"*64},"BLIND_LOCK_SHA256_MISMATCH"),
        ({"apl_line_to_numeric_action":{2:101,3:101,4:True}},"NUMERIC_ACTION_MAP_REQUIRED"),
        ({"apl_line_to_numeric_action":{99:101}},"INVALID_APL_LINE_MAPPING"),
    ):
        try:replay(fx(),**changes)
        except ValueError as exc:
            assert str(exc)==expected,(expected,str(exc))
        else:raise AssertionError("INVALID_INPUT_ACCEPTED")
    bad=dict(lock,semantic_names_attached=True)
    altered=json.dumps(bad,sort_keys=True).encode()
    try:replay(fx(),blind_lock_bytes=altered,
               blind_lock_sha256=hashlib.sha256(altered).hexdigest())
    except ValueError as exc:assert str(exc)=="SIMC_SEMANTIC_CONTAMINATION"
    else:raise AssertionError("SEMANTIC_LOCK_ACCEPTED")
    try:replay(fx(profile_hash="0"*64))
    except ValueError as exc:assert str(exc)=="PROFILE_SHA256_MISMATCH"
    else:raise AssertionError("UNPINNED_PROFILE_ACCEPTED")
    try:replay(fx(),profile_text=profile.replace("enhancement","fury"))
    except ValueError as exc:assert str(exc)=="PROFILE_SHA256_MISMATCH"
    else:raise AssertionError("CROSS_SPEC_PROFILE_ACCEPTED")
    print("POST_LOCK_SIMC_WCL_GUARD_REPLAY_SELF_TEST=PASS")


if __name__=="__main__":
    selftest()
