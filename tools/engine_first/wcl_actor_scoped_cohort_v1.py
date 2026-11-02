#!/usr/bin/env python3
"""WCL actor-scoped numeric evidence, separated from SimC semantics.

No-argument mode is offline synthetic self-test. --live is explicit, requires
a public report/fight/actor and lawful OAuth credentials, and stores raw event
pages locally only. It never proves rank, build, cooldown readiness or priority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tempfile

from fresh_wcl_engine_v1 import (
    EngineError, canonical, sha, collect, credentials, oauth_token,
    official_graphql, replay,
)
from wcl_blind_numeric_candidate_lock_v1 import lock_candidates, BlindInputError

META_QUERY = """query ZrotActorGate($code:String!, $fight:Int!){
  reportData { report(code:$code) { code revision
    fights(fightIDs:[$fight],translate:false) {
      id startTime endTime inProgress encounterID difficulty
      friendlyPlayers friendlySpecs
    }
    masterData(translate:false) {
      actors { id type subType }
    }
  } }
}"""
SCHEMA = "ZrotWclActorIdentityGateV1"
HEX = re.compile(r"^[0-9a-f]{64}$")


class ActorGateError(ValueError):
    """No identity or actor-scoped scientific conclusion on malformed input."""


def _int(value, label):
    if type(value) is not int or value <= 0:
        raise ActorGateError(label)
    return value


def _name(value):
    return re.sub(r"[^a-z0-9]+", "", value.casefold()) if isinstance(value, str) else ""


def _report(data):
    report = data.get("reportData", {}).get("report") if isinstance(data, dict) else None
    if not isinstance(report, dict):
        raise ActorGateError("MISSING_REPORT_DATA")
    return report


def identity_gate(data: dict, code: str, fight_id: int, actor_id: int,
                  expected_spec: str, expected_class: str) -> dict:
    """Verify actor->fight->spec without importing the SimC hypothesis lane."""
    fight_id = _int(fight_id, "INVALID_FIGHT_ID")
    actor_id = _int(actor_id, "INVALID_ACTOR_ID")
    if not re.fullmatch(r"[A-Za-z0-9]{6,40}", code):
        raise ActorGateError("INVALID_REPORT_CODE")
    if not _name(expected_spec) or not _name(expected_class):
        raise ActorGateError("EXPECTED_SPEC_AND_CLASS_REQUIRED")
    report = _report(data)
    if report.get("code") != code or type(report.get("revision")) is not int:
        raise ActorGateError("REPORT_CODE_OR_REVISION_UNVERIFIED")
    fights = report.get("fights")
    if not isinstance(fights, list):
        raise ActorGateError("FIGHTS_NOT_OBSERVED")
    matches = [f for f in fights if isinstance(f, dict) and f.get("id") == fight_id]
    if len(matches) != 1:
        raise ActorGateError("FIGHT_NOT_UNIQUE")
    fight = matches[0]
    if fight.get("inProgress") is True:
        raise ActorGateError("INCOMPLETE_FIGHT")
    start, end = fight.get("startTime"), fight.get("endTime")
    if (type(start) not in (int, float) or type(end) not in (int, float)
            or start >= end):
        raise ActorGateError("INVALID_FIGHT_TIME")
    ids, specs = fight.get("friendlyPlayers"), fight.get("friendlySpecs")
    if (not isinstance(ids, list) or not isinstance(specs, list)
            or len(ids) != len(specs) or len(ids) != len(set(
                x for x in ids if type(x) is int))
            or any(type(x) is not int for x in ids)):
        raise ActorGateError("FRIENDLY_ACTOR_SPEC_ARRAY_UNVERIFIED")
    if ids.count(actor_id) != 1:
        raise ActorGateError("ACTOR_NOT_IN_FIGHT")
    observed_spec = specs[ids.index(actor_id)]
    if _name(observed_spec) != _name(expected_spec):
        raise ActorGateError("ACTOR_SPEC_MISMATCH")
    master = report.get("masterData")
    actors = master.get("actors") if isinstance(master, dict) else None
    if not isinstance(actors, list):
        raise ActorGateError("MASTER_ACTOR_LIST_MISSING")
    observed = [a for a in actors if isinstance(a, dict) and a.get("id") == actor_id]
    if len(observed) != 1:
        raise ActorGateError("MASTER_ACTOR_NOT_UNIQUE")
    actor = observed[0]
    if _name(actor.get("type")) != "player":
        raise ActorGateError("ACTOR_NOT_PLAYER")
    if _name(actor.get("subType")) != _name(expected_class):
        raise ActorGateError("ACTOR_CLASS_MISMATCH")
    return {
        "schema": SCHEMA,
        "status": "ACTOR_FIGHT_SPEC_CLASS_MATCH",
        "report_code": code,
        "report_revision": report["revision"],
        "fight_id": fight_id,
        "actor_id": actor_id,
        "fight_start_ms": start,
        "fight_end_ms": end,
        "observed_spec": observed_spec,
        "observed_class": actor["subType"],
        "rank_source_verified": False,
        "talent_build": "UNKNOWN",
        "spec_build_equivalence_to_SimC": "UNKNOWN",
        "source_metadata_sha256": sha(canonical(data)),
        "proof_is_player_rotation": False,
    }


def scope_replay(raw: dict, gate: dict) -> dict:
    """Lock numeric cast rows to one verified actor; preserve raw replay hash."""
    if gate.get("schema") != SCHEMA or gate.get("status") != "ACTOR_FIGHT_SPEC_CLASS_MATCH":
        raise ActorGateError("IDENTITY_GATE_REQUIRED")
    if raw.get("schema") != "FreshWCLReplayV1" or raw.get("blind_numeric_only") is not True:
        raise ActorGateError("RAW_NUMERIC_REPLAY_REQUIRED")
    fingerprint = raw.get("replay_sha256")
    if not isinstance(fingerprint, str) or not HEX.fullmatch(fingerprint):
        raise ActorGateError("INVALID_SOURCE_REPLAY_SHA")
    if sha(canonical({k: v for k, v in raw.items() if k != "replay_sha256"})) != fingerprint:
        raise ActorGateError("SOURCE_REPLAY_TAMPERED")
    identity = raw.get("identity")
    if not isinstance(identity, dict) or any(
        identity.get(key) != gate[gkey] for key, gkey in
        (("report_code", "report_code"), ("fight_id", "fight_id"),
         ("revision", "report_revision"), ("start", "fight_start_ms"),
         ("end", "fight_end_ms"))
    ):
        raise ActorGateError("SOURCE_REPLAY_FIGHT_IDENTITY_MISMATCH")
    if raw.get("cooldown_or_resource_readiness") != "UNKNOWN" or raw.get("candidate_lock") != "NOT_IMPLEMENTED":
        raise ActorGateError("PRELOCK_READINESS_OR_SEMANTIC_MUTATION")
    rows = raw.get("decisions")
    if not isinstance(rows, list) or raw.get("decision_count") != len(rows):
        raise ActorGateError("RAW_DECISION_COUNT_MISMATCH")
    actor = gate["actor_id"]
    selected = [r for r in rows if r.get("source_actor_id") == actor]
    if not selected:
        raise ActorGateError("NO_ACTOR_CAST_ROWS")
    for row in selected:
        if row.get("readiness") != "UNKNOWN" or type(row.get("ability_id")) is not int:
            raise ActorGateError("NON_NUMERIC_OR_INFERRED_ACTOR_CAST")
        if not isinstance(row.get("aura_pre"), dict) or any(
            not str(k).isdigit() for k in row["aura_pre"]):
            raise ActorGateError("SEMANTIC_AURA_LEAKAGE")
    # Do not include observed spec/class/spell names in the blind artifact.
    view = {
        "schema": "FreshWCLReplayV1",
        "identity": dict(identity, actor_id=actor,
                         source_replay_sha256=fingerprint),
        "source_page_sha256": raw.get("source_page_sha256"),
        "event_count": raw.get("event_count"),
        "decision_count": len(selected),
        "decisions": selected,
        "blind_numeric_only": True,
        "numeric_actor_scope_only": True,
        "other_actor_decisions_removed": len(rows) - len(selected),
        "cooldown_or_resource_readiness": "UNKNOWN",
        "candidate_lock": "NOT_IMPLEMENTED",
        "gameplay_priority_claim": "NONE",
    }
    view["replay_sha256"] = sha(canonical(view))
    return view


def prepare(meta: dict, raw: dict, *, code: str, fight: int, actor: int,
            spec: str, player_class: str, min_observations: int) -> tuple[dict, dict, dict, dict]:
    gate = identity_gate(meta, code, fight, actor, spec, player_class)
    view = scope_replay(raw, gate)
    lock = lock_candidates([view], min_observations=min_observations,
                           source_kind="ATTESTED_RAW_WCL_REPLAY")
    if lock["gameplay_rule_eligible"] or lock["holdout_validated"]:
        raise ActorGateError("INVALID_SCIENTIFIC_PROMOTION")
    receipt = {
        "schema": "ZrotWclActorScopedDiscoveryReceiptV1",
        "status": "NUMERIC_DISCOVERY_ONLY",
        "scope_policy_id": "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
        "actor_gate_sha256": sha(canonical(gate)),
        "blind_actor_view_sha256": sha(canonical(view)),
        "blind_lock_sha256": sha(canonical(lock)),
        "predeclared_min_observations_cli_value": min_observations,
        "threshold_predeclaration_independently_audited": False,
        "high_ranker_provenance": "NOT_VERIFIED",
        "talent_build": "UNKNOWN",
        "readiness": "UNKNOWN",
        "independent_holdout": "NOT_RUN",
        "post_lock_simc_replay": "NOT_RUN",
        "current_season_gameplay_priority": "NOT_VALIDATED",
        "blizzard_mechanic_reconciliation": "NOT_RUN",
        "actual_WCL_execution": "USER_SUPPLIED_OR_LIVE_SOURCE_REQUIRES_AUDIT",
        "same_timestamp_state": "EXCLUDED_BY_SOURCE_STRICT_PRE",
    }
    return gate, view, lock, receipt


def write_once(path: Path, obj: dict):
    """Never silently overwrite scientific discovery or evidence receipts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(canonical(obj))


def selftest():
    from fresh_wcl_engine_v1 import collect
    code = "ABCDEF123456"
    fight, actor = 11, 7
    metadata = {"reportData": {"report": {
        "code": code, "revision": 4,
        "fights": [{"id": fight, "startTime": 100, "endTime": 500,
                    "inProgress": False, "friendlyPlayers": [7, 8],
                    "friendlySpecs": ["Fury", "Arms"]}],
        "masterData": {"actors": [
            {"id": 7, "type": "Player", "subType": "Warrior"},
            {"id": 8, "type": "Player", "subType": "Warrior"},
        ]},
    }}}
    events = [
        {"timestamp": 110, "type": "applybuff", "targetID": 7,
         "abilityGameID": 444, "stack": 2},
        {"timestamp": 120, "type": "cast", "sourceID": 7, "abilityGameID": 101},
        {"timestamp": 120, "type": "removebuff", "targetID": 7, "abilityGameID": 444},
        {"timestamp": 130, "type": "cast", "sourceID": 8, "abilityGameID": 999},
        {"timestamp": 140, "type": "cast", "sourceID": 7, "abilityGameID": 101},
        {"timestamp": 160, "type": "cast", "sourceID": 8, "abilityGameID": 999},
    ]
    def query(q, v):
        if "FreshReport" in q:
            return {"reportData": {"report": {
                "code": code, "revision": 4,
                "fights": [{"id": fight, "startTime": 100, "endTime": 500,
                            "inProgress": False}]}}}
        return {"reportData": {"report": {"events": {
            "data": events, "nextPageTimestamp": None}}}}
    tests = 0
    with tempfile.TemporaryDirectory() as d:
        collect(query, code, fight, Path(d))
        raw = replay(Path(d) / code / f"fight_{fight}")
        gate, view, lock, receipt = prepare(
            metadata, raw, code=code, fight=fight, actor=actor,
            spec="fury", player_class="warrior", min_observations=2)
        assert view["decision_count"] == 2
        assert view["other_actor_decisions_removed"] == 2
        assert all(r["source_actor_id"] == actor for r in view["decisions"])
        assert [r["ability_id"] for r in view["decisions"]] == [101, 101]
        assert view["decisions"][0]["aura_pre"]["444"]["active"] is True
        assert view["decisions"][1]["aura_pre"]["444"]["active"] is False
        assert len(lock["candidates"]) == 1 and lock["candidates"][0]["action_spell_id"] == 101
        assert "Fury" not in json.dumps(view) and "Warrior" not in json.dumps(view)
        assert gate["talent_build"] == "UNKNOWN"
        assert not gate["rank_source_verified"] and not lock["gameplay_rule_eligible"]
        assert receipt["independent_holdout"] == "NOT_RUN"
        tests += 11
        import copy
        for mutation, expected in (
            (lambda m: m["reportData"]["report"]["fights"][0]["friendlySpecs"].__setitem__(0, "Arms"), "ACTOR_SPEC_MISMATCH"),
            (lambda m: m["reportData"]["report"]["fights"][0]["friendlyPlayers"].append(7), "FRIENDLY_ACTOR_SPEC_ARRAY"),
            (lambda m: m["reportData"]["report"]["masterData"]["actors"][0].update(type="Pet"), "ACTOR_NOT_PLAYER"),
            (lambda m: m["reportData"]["report"]["masterData"]["actors"][0].update(subType="Mage"), "ACTOR_CLASS_MISMATCH"),
            (lambda m: m["reportData"]["report"]["fights"][0].update(inProgress=True), "INCOMPLETE_FIGHT"),
        ):
            bad = copy.deepcopy(metadata)
            mutation(bad)
            try: identity_gate(bad, code, fight, actor, "Fury", "Warrior")
            except ActorGateError as ex: assert expected in str(ex), (expected, ex)
            else: raise AssertionError("ACTOR_IDENTITY_NEGATIVE_ACCEPTED")
            tests += 1
        damaged = copy.deepcopy(raw)
        damaged["decisions"][0]["ability_id"] = 505
        try: scope_replay(damaged, gate)
        except ActorGateError as ex: assert "SOURCE_REPLAY_TAMPERED" in str(ex)
        else: raise AssertionError("TAMPERED_REPLAY_ACCEPTED")
        tests += 1
        try: scope_replay(raw, {**gate, "fight_id": 42})
        except ActorGateError as ex: assert "SOURCE_REPLAY_FIGHT_IDENTITY" in str(ex)
        else: raise AssertionError("DIFFERENT_FIGHT_ACCEPTED")
        tests += 1
        output = Path(d) / "receipt.json"
        write_once(output, receipt)
        try: write_once(output, receipt)
        except FileExistsError: pass
        else: raise AssertionError("RECEIPT_OVERWRITE_ALLOWED")
        tests += 1
    return {"status": "PASS_OFFLINE_SYNTHETIC",
            "assertion_groups": tests,
            "actual_WCL_requests": 0,
            "real_ranker_verified": False,
            "live_readiness": "UNKNOWN",
            "real_gameplay_rule": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--report-code")
    ap.add_argument("--fight", type=int)
    ap.add_argument("--actor", type=int)
    ap.add_argument("--spec")
    ap.add_argument("--player-class")
    ap.add_argument("--metadata", type=Path)
    ap.add_argument("--raw-replay", type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--env", type=Path)
    ap.add_argument("--max-pages", type=int, default=8)
    ap.add_argument("--min-observations", type=int, default=2)
    a = ap.parse_args()
    if a.self_test or (not a.live and a.metadata is None and a.raw_replay is None):
        print(json.dumps(selftest(), sort_keys=True))
        return
    if (not all([a.report_code, a.fight, a.actor, a.spec,
                 a.player_class, a.out_dir])
            or a.metadata is not None and a.live
            or a.raw_replay is not None and a.live):
        ap.error("explicit identity/output inputs required; live and offline modes are exclusive")
    if a.live:
        if not re.fullmatch(r"[A-Za-z0-9]{6,40}", a.report_code) or not 1 <= a.max_pages <= 1000 or not 1 <= a.min_observations <= 1000:
            ap.error("invalid report, page limit or predeclared observation threshold")
        # No network or credential access without an explicit --live.
        client_id, client_secret = credentials(a.env)
        token = oauth_token(client_id, client_secret)
        def query(q, v):
            return official_graphql(token, q, v)
        meta = query(META_QUERY, {"code": a.report_code, "fight": a.fight})
        gate = identity_gate(meta, a.report_code, a.fight, a.actor,
                             a.spec, a.player_class)
        result = collect(query, a.report_code, a.fight,
                         a.out_dir / "raw", max_pages=a.max_pages)
        if result["status"] != "COMPLETE":
            print(json.dumps({"status": "PARTIAL_CHECKPOINT_ONLY",
                              "checkpoint": result["checkpoint"],
                              "api_points": "NOT_MEASURED",
                              "gameplay_claim": False}))
            return
        raw = replay(a.out_dir / "raw" / a.report_code / f"fight_{a.fight}")
        if raw["identity"]["revision"] != gate["report_revision"]:
            raise ActorGateError("REPORT_REVISION_CHANGED_DURING_COLLECTION")
    else:
        if a.metadata is None or a.raw_replay is None:
            ap.error("--metadata and --raw-replay are both required in offline mode")
        meta = json.loads(a.metadata.read_text(encoding="utf-8"))
        raw = json.loads(a.raw_replay.read_text(encoding="utf-8"))
    gate, view, lock, receipt = prepare(
        meta, raw, code=a.report_code, fight=a.fight, actor=a.actor,
        spec=a.spec, player_class=a.player_class,
        min_observations=a.min_observations)
    derived = a.out_dir / "derived"
    for file, data in (("actor_identity_gate.json", gate),
                       ("blind_actor_replay.json", view),
                       ("blind_numeric_lock.json", lock),
                       ("discovery_receipt.json", receipt)):
        if (derived / file).exists():
            raise ActorGateError("EXISTING_DERIVED_ARTIFACT__DO_NOT_OVERWRITE")
    for file, data in (("actor_identity_gate.json", gate),
                       ("blind_actor_replay.json", view),
                       ("blind_numeric_lock.json", lock),
                       ("discovery_receipt.json", receipt)):
        write_once(derived / file, data)
    print(json.dumps({"status": "ACTOR_SCOPED_NUMERIC_DISCOVERY_ONLY",
                      "source_replay_sha256": view["identity"]["source_replay_sha256"],
                      "actor_view_sha256": receipt["blind_actor_view_sha256"],
                      "numeric_lock_sha256": receipt["blind_lock_sha256"],
                      "high_ranker": "UNVERIFIED",
                      "priority": "NOT_VALIDATED"}, sort_keys=True))


if __name__ == "__main__":
    main()
