#!/usr/bin/env python3
"""Official WCL encounter ranking -> verified actor -> bounded numeric blind E2E.

No arguments: offline synthetic regression. Live requires explicit --live and
encounter ID, official OAuth, a page cap, and a current report/fight identity.
Do not treat rankings, cast counts, or SimC samples as causal rotation rules.
The WCL rankings JSON shape is not frozen; unexpected shapes fail closed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile

from fresh_wcl_engine_v1 import (
    canonical, sha, credentials, oauth_token, official_graphql, collect, replay,
)
from wcl_actor_scoped_cohort_v1 import META_QUERY, identity_gate, prepare, write_once

RANK_QUERY = """query ZrotOfficialRanker($enc:Int!, $difficulty:Int!,
                                        $class:String!, $spec:String!){
  worldData {
    encounter(id:$enc) {
      id name zone { id name frozen }
      characterRankings(difficulty:$difficulty, page:1,
                        className:$class, specName:$spec)
    }
  }
}"""
CODE_RE = re.compile(r"^[A-Za-z0-9]{6,40}$")


class RankSourceError(ValueError):
    """Malformed or unverified public ranking source."""


def _positive(x):
    return type(x) is int and x > 0


def ranked_rows(data, *, encounter, class_name, spec_name, difficulty, min_rank=1,
                max_rank=50):
    """Untrusted source shape: only strict report+fight+name rows may advance."""
    if not _positive(encounter) or not _positive(difficulty):
        raise RankSourceError("INVALID_ENCOUNTER_OR_DIFFICULTY")
    w = data.get("worldData", {}) if isinstance(data, dict) else {}
    e = w.get("encounter") if isinstance(w, dict) else None
    if not isinstance(e, dict) or e.get("id") != encounter:
        raise RankSourceError("ENCOUNTER_ID_UNVERIFIED")
    zone = e.get("zone")
    if not isinstance(zone, dict) or not _positive(zone.get("id")):
        raise RankSourceError("ZONE_ID_UNVERIFIED")
    if zone.get("frozen") is not False:
        raise RankSourceError("ZONE_FROZEN_OR_UNKNOWN")
    body = e.get("characterRankings")
    if not isinstance(body, dict):
        raise RankSourceError("UNRECOGNIZED_RANKING_JSON_SHAPE")
    rows = body.get("rankings")
    if not isinstance(rows, list) or len(rows) > 100:
        raise RankSourceError("RANKING_ROWS_MISSING_OR_EXCESSIVE")
    candidates = []
    for ordinal, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        rank = item.get("rank")
        if type(rank) is float and rank.is_integer():
            rank = int(rank)  # provider JSON may emit integral Float
        if rank is None:
            # V2 rankings JSON may omit a numeric rank: page-1 ordinal is
            # only collection order, NEVER a proven official numeric rank.
            position = ordinal
            rank_authority = "PAGE1_ORDER_ONLY_OFFICIAL_RANK_UNKNOWN"
        elif type(rank) is int and rank > 0:
            position = rank
            rank_authority = "EXPLICIT_NUMERIC_RANK"
        else:
            continue
        if not min_rank <= position <= max_rank:
            continue
        report = item.get("report")
        if isinstance(report, dict):
            code = report.get("code")
            fight = report.get("fightID", item.get("fightID"))
        else:
            code = item.get("reportID") or (report if isinstance(report, str) else None)
            fight = item.get("fightID")
        actor = item.get("name")
        if isinstance(actor, dict):
            actor = actor.get("name")
        if not isinstance(actor, str) or not actor.strip():
            continue
        if not isinstance(code, str) or not CODE_RE.fullmatch(code):
            continue
        if type(fight) is float and fight.is_integer():
            fight = int(fight)
        if not _positive(fight):
            continue
        # Ranking JSON may expose numeric spec ids, not human labels.
        # Bind names only when actually strings; full spec gate runs later.
        if isinstance(item.get("spec"), str) and item["spec"].casefold() != spec_name.casefold():
            continue
        if item.get("class") is not None and isinstance(item["class"], str) and item["class"].casefold() != class_name.casefold():
            continue
        candidates.append({
            "rank": rank, "ranking_page_position": ordinal,
            "rank_authority": rank_authority, "code": code, "fight": fight,
            "ranked_actor_name": actor, "encounter": encounter,
            "zone": zone["id"], "difficulty": difficulty,
            "expected_spec": spec_name, "expected_class": class_name,
        })
    candidates.sort(key=lambda x: (x["ranking_page_position"], x["code"], x["fight"]))
    if not candidates:
        # No secret, report code, or player name in diagnostic: only keys
        # and JSON types. This is a response-contract inspection, not a retry.
        shapes = []
        for row in rows[:2]:
            if isinstance(row, dict):
                shape = {k: type(v).__name__ for k, v in sorted(row.items())
                         if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,40}", k)}
                if isinstance(row.get("report"), dict):
                    shape["report_fields"] = {k: type(v).__name__
                        for k, v in sorted(row["report"].items())
                        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,40}", k)}
                shapes.append(shape)
        details = {"row_count": len(rows), "sample_shapes": shapes}
        raise RankSourceError("NO_RANKING_WITH_REPORT_FIGHT_AND_NAME__SHAPE=" +
                              json.dumps(details, separators=(",", ":"), sort_keys=True))
    return candidates


def select_verified(query, rankings_data, *, encounter, class_name, spec_name,
                    difficulty, max_rank=50, max_age_days=45, max_candidates=3,
                    now=None, min_page_position=1, max_page_position=100,
                    excluded_report_codes=()):
    """Verify the ranking's report/fight/actor through official report metadata."""
    candidates = ranked_rows(rankings_data, encounter=encounter,
                             class_name=class_name, spec_name=spec_name,
                             difficulty=difficulty, max_rank=max_rank)
    if (type(min_page_position) is not int or type(max_page_position) is not int
            or not 1 <= min_page_position <= max_page_position <= 100
            or type(max_candidates) is not int or not 1 <= max_candidates <= 30
            or not isinstance(excluded_report_codes, (tuple, list))
            or any(not isinstance(x, str) or not CODE_RE.fullmatch(x)
                   for x in excluded_report_codes)):
        raise RankSourceError("INVALID_PREDECLARED_RANKING_FILTER")
    candidates = [c for c in candidates
                  if min_page_position <= c["ranking_page_position"] <= max_page_position
                  and c["code"] not in excluded_report_codes]
    if not candidates:
        raise RankSourceError("NO_ELIGIBLE_RANKING_ROWS_AFTER_PREDECLARED_FILTER")
    now = now or datetime.now(timezone.utc)
    errors = []
    for c in candidates[:max_candidates]:
        try:
            meta = query(META_QUERY, {"code": c["code"], "fight": c["fight"]})
            report = (meta.get("reportData") or {}).get("report") or {}
            fights = report.get("fights") or []
            fight = next((x for x in fights if isinstance(x, dict) and
                          x.get("id") == c["fight"]), None)
            actors = ((report.get("masterData") or {}).get("actors") or [])
            if not isinstance(fight, dict) or fight.get("encounterID") != encounter:
                raise RankSourceError("RANKED_ENCOUNTER_NOT_MATCHED")
            if fight.get("difficulty") != difficulty:
                raise RankSourceError("RANKED_DIFFICULTY_NOT_MATCHED")
            names = [a for a in actors if isinstance(a, dict) and
                     isinstance(a.get("name"), str) and
                     a["name"].casefold() == c["ranked_actor_name"].casefold()]
            if len(names) != 1 or not _positive(names[0].get("id")):
                raise RankSourceError("RANKING_ACTOR_NOT_UNIQUE")
            actor_id = names[0]["id"]
            gate = identity_gate(meta, c["code"], c["fight"], actor_id,
                                 spec_name, class_name)
            report_start = report.get("startTime")
            if type(report_start) not in (int, float):
                raise RankSourceError("REPORT_UNIX_START_MISSING")
            # Report.startTime UNIX milliseconds; fight.startTime offset ms.
            start_unix = (report_start + gate["fight_start_ms"]) / 1000
            age_days = (now.timestamp() - start_unix) / 86400
            if not 0 <= age_days <= max_age_days:
                raise RankSourceError("FIGHT_OUTSIDE_FRESHNESS_WINDOW")
            public_receipt = {
                "schema": "ZrotOfficialRankerSelectionV1",
                "status": "PUBLIC_RANK_MATCHED_TO_VERIFIED_FIGHT_ACTOR",
                "explicit_official_rank": c["rank"],
                "ranking_page_position": c["ranking_page_position"],
                "rank_authority": c["rank_authority"],
                "report_code": c["code"],
                "fight_id": c["fight"],
                "actor_id": actor_id,
                "zone_id": c["zone"], "encounter_id": encounter,
                "difficulty": difficulty,
                "report_revision": gate["report_revision"],
                "source_rank_query_sha256": sha(canonical(rankings_data)),
                "report_actor_metadata_sha256": gate["source_metadata_sha256"],
                "source_age_days": round(age_days, 3),
                "spec_class_identity": "VERIFIED_AGAINST_REPORT",
                "talent_build": "UNKNOWN",
                "readiness": "UNKNOWN",
                "rank_in_current_top_table": True,
                "exact_rank_verified": c["rank_authority"] == "EXPLICIT_NUMERIC_RANK",
                "rankings_not_frozen": True,
                "holdout": "NOT_USED_FOR_DISCOVERY",
                "actual_gameplay_priority": "NOT_VALIDATED",
            }
            return c, meta, gate, public_receipt
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(type(exc).__name__ + ":" + str(exc).split(":")[0][:100])
    raise RankSourceError("NO_VERIFIED_CURRENT_RANKED_ACTOR__" + "|".join(errors[:3]))


def run_live(*, encounter, class_name, spec_name, difficulty, max_pages,
             max_rank, max_age_days, out_dir, min_observations=2,
             opener_window_ms=15000):
    """One bounded live run. Never overwrites a lock or silently grows cohort."""
    client, secret = credentials(None)
    token = oauth_token(client, secret)
    def query(q, v):
        return official_graphql(token, q, v)
    rank = query(RANK_QUERY, {"enc": encounter, "class": class_name,
                              "spec": spec_name, "difficulty": difficulty})
    candidate, meta, gate, selection = select_verified(
        query, rank, encounter=encounter, class_name=class_name,
        spec_name=spec_name, difficulty=difficulty,
        max_rank=max_rank, max_age_days=max_age_days)
    # No actor- or ranking-source name in stored numeric blind evidence.
    if any((out_dir / "derived" / name).exists() for name in
           ("selection.json", "identity.json", "blind_replay.json",
            "blind_lock.json", "receipt.json")):
        raise RankSourceError("EXISTING_SCIENTIFIC_ARTIFACT_NO_OVERWRITE")
    info = collect(query, candidate["code"], candidate["fight"],
                   out_dir / "raw", max_pages=max_pages,
                   window_ms=opener_window_ms)
    if info["status"] != "COMPLETE_WINDOW":
        return {"status": "PARTIAL_API_COLLECTION_CHECKPOINT_ONLY",
                "pages": info["pages"],
                "requested_window_ms": opener_window_ms,
                "identity_gate": "PASS",
                "rank_provenance": "REPORT_MATCH_VERIFIED",
                "WCL_live": "EXECUTED",
                "blind_lock": "NOT_RUN",
                "checkpoint": info["checkpoint"],
                "api_points": "NOT_MEASURED",
                "gameplay_priority": "NOT_VALIDATED"}
    raw = replay(out_dir / "raw" / candidate["code"] / f"fight_{candidate['fight']}")
    identity, view, lock, receipt = prepare(
        meta, raw, code=candidate["code"], fight=candidate["fight"],
        actor=gate["actor_id"], spec=spec_name, player_class=class_name,
        min_observations=min_observations)
    if identity["source_metadata_sha256"] != gate["source_metadata_sha256"]:
        raise RankSourceError("IDENTITY_CHANGED_BETWEEN_GATES")
    receipt["actual_WCL_execution"] = "OFFICIAL_CLIENT_OAUTH_AND_EVENT_QUERY"
    receipt["ranking_selection_sha256"] = sha(canonical(selection))
    receipt["rank_provenance"] = "OFFICIAL_ENCOUNTER_TABLE_AND_REPORT_ACTOR_MATCH"
    receipt["talent_build"] = "UNKNOWN"
    receipt["window_provenance"] = {
        "scope": "FIGHT_START_BOUNDED",
        "requested_window_ms": opener_window_ms,
        "completed_window": True,
        "complete_fight": False,
    }
    out = out_dir / "derived"
    for filename, data in (("selection.json", selection),
                           ("identity.json", identity),
                           ("blind_replay.json", view),
                           ("blind_lock.json", lock),
                           ("receipt.json", receipt)):
        write_once(out / filename, data)
    return {"status": "LIVE_WCL_ACTOR_SCOPED_NUMERIC_DISCOVERY_ONLY",
            "ranking_page_position": selection["ranking_page_position"],
            "explicit_official_rank": selection["explicit_official_rank"],
            "fight_age_days": selection["source_age_days"],
            "pages": info["pages"], "events": info["events"],
            "opener_window_ms": opener_window_ms,
            "window_completed": True,
            "full_fight_completed": False,
            "candidate_count": lock["candidate_n"],
            "blind_lock_sha256": sha(canonical(lock)),
            "readiness": "UNKNOWN",
            "holdout": "NOT_RUN",
            "post_lock_SimC": "NOT_RUN",
            "gameplay_priority": "NOT_VALIDATED",
            "api_points": "NOT_MEASURED"}


def selftest():
    from fresh_wcl_engine_v1 import collect, replay
    code = "ABCDEF123456"; enc = 3420; fight = 9
    ranking = {"worldData": {"encounter": {
        "id": enc, "name": "Fixture Encounter",
        "zone": {"id": 53, "name": "Fixture Zone", "frozen": False},
        "characterRankings": {"rankings": [
            {"rank": 3, "name": "FuryTester", "report": {"code": code, "fightID": fight}, "spec": "Fury"}]}}}}
    meta = {"reportData": {"report": {
        "code": code, "revision": 2, "startTime": 1791000000000,
        "fights": [{"id": fight, "startTime": 1000, "endTime": 75000,
                    "difficulty": 4, "encounterID": enc, "inProgress": False,
                    "friendlyPlayers": [7, 8], "friendlySpecs": ["Fury", "Arms"]}],
        "masterData": {"actors": [
            {"id": 7, "name": "FuryTester", "type": "Player", "subType": "Warrior"},
            {"id": 8, "name": "Other", "type": "Player", "subType": "Warrior"}]}}}}
    queries = []
    def query(q, variables):
        queries.append((q, variables))
        return meta
    mock_now = datetime.fromtimestamp(1791000000 + 86400, tz=timezone.utc)
    cand, md, gate, proof = select_verified(
        query, ranking, encounter=enc, class_name="Warrior",
        spec_name="Fury", difficulty=4, now=mock_now)
    assert cand["rank"] == 3 and gate["actor_id"] == 7
    assert proof["exact_rank_verified"] is True
    assert proof["talent_build"] == "UNKNOWN" and proof["rank_in_current_top_table"]
    assert len(queries) == 1
    # Frozen holdout filter must exclude discovery report before any metadata API.
    before=len(queries)
    try:
        select_verified(query, ranking, encounter=enc, class_name="Warrior",
                        spec_name="Fury", difficulty=4, now=mock_now,
                        min_page_position=2, max_page_position=15)
    except RankSourceError as exc:
        assert "NO_ELIGIBLE_RANKING" in str(exc)
    else: raise AssertionError("HOLDOUT_PAGE_POSITION_BYPASS")
    assert len(queries)==before
    try:
        select_verified(query, ranking, encounter=enc, class_name="Warrior",
                        spec_name="Fury", difficulty=4, now=mock_now,
                        excluded_report_codes=(code,))
    except RankSourceError as exc:
        assert "NO_ELIGIBLE_RANKING" in str(exc)
    else: raise AssertionError("DISCOVERY_REPORT_REUSED_AS_HOLDOUT")
    assert len(queries)==before
    import copy
    tested = 4
    for mutation in ("zone-frozen", "wrong-encounter", "bad-rank", "no-report"):
        bad = copy.deepcopy(ranking)
        e = bad["worldData"]["encounter"]
        if mutation == "zone-frozen":
            e["zone"]["frozen"] = True
        if mutation == "wrong-encounter":
            e["id"] = 999
        if mutation == "bad-rank":
            e["characterRankings"]["rankings"][0]["rank"] = 200
        if mutation == "no-report":
            e["characterRankings"]["rankings"][0].pop("report")
        try: ranked_rows(bad, encounter=enc, class_name="Warrior",
                         spec_name="Fury", difficulty=4)
        except RankSourceError: pass
        else: raise AssertionError("INVALID_RANKING_ACCEPTED:" + mutation)
        tested += 1
    for mutation in ("ambiguous-name", "wrong-spec", "wrong-difficulty", "stale"):
        bad = copy.deepcopy(meta)
        report = bad["reportData"]["report"]
        if mutation == "ambiguous-name":
            report["masterData"]["actors"][1]["name"] = "FuryTester"
        if mutation == "wrong-spec":
            report["fights"][0]["friendlySpecs"][0] = "Arms"
        if mutation == "wrong-difficulty":
            report["fights"][0]["difficulty"] = 5
        if mutation == "stale":
            report["startTime"] = 1700000000000
        try:
            select_verified(lambda *_: bad, ranking, encounter=enc,
                            class_name="Warrior", spec_name="Fury",
                            difficulty=4, now=mock_now)
        except RankSourceError: pass
        else: raise AssertionError("INVALID_RANKED_ACTOR_ACCEPTED:" + mutation)
        tested += 1
    # Numeric specialization IDs must not reject all otherwise valid rows.
    variant = copy.deepcopy(ranking)
    variant["worldData"]["encounter"]["characterRankings"]["rankings"][0]["spec"] = 72
    variant["worldData"]["encounter"]["characterRankings"]["rankings"][0]["fightID"] = 9.0
    numeric = ranked_rows(variant, encounter=enc, class_name="Warrior",
                          spec_name="Fury", difficulty=4)
    assert len(numeric) == 1 and numeric[0]["fight"] == 9
    tested += 1
    no_rank = copy.deepcopy(ranking)
    no_rank["worldData"]["encounter"]["characterRankings"]["rankings"][0].pop("rank")
    no_rank_rows = ranked_rows(no_rank, encounter=enc, class_name="Warrior",
                               spec_name="Fury", difficulty=4)
    assert len(no_rank_rows) == 1 and no_rank_rows[0]["rank"] is None
    assert no_rank_rows[0]["ranking_page_position"] == 1
    assert no_rank_rows[0]["rank_authority"] == "PAGE1_ORDER_ONLY_OFFICIAL_RANK_UNKNOWN"
    tested += 1
    # Exercise bounded-window collection and actor/lock E2E with no network.
    from fresh_wcl_engine_v1 import collect, replay
    from wcl_actor_scoped_cohort_v1 import prepare
    with tempfile.TemporaryDirectory() as d:
        calls = []
        def mock(q, variables):
            if "FreshReport" in q:
                return {"reportData": {"report": {
                    "code": code, "revision": 2,
                    "fights": [{"id": fight, "startTime": 1000, "endTime": 75000,
                                "difficulty": 4, "encounterID": enc,
                                "inProgress": False}]}}}
            calls.append((variables["start"], variables["end"]))
            return {"reportData": {"report": {"events": {
                "data": [{"timestamp": 1100, "type": "cast",
                          "sourceID": 7, "abilityGameID": 101},
                         {"timestamp": 1200, "type": "cast",
                          "sourceID": 7, "abilityGameID": 101},
                         {"timestamp": 1300, "type": "cast",
                          "sourceID": 8, "abilityGameID": 999}],
                "nextPageTimestamp": None}}}}
        result = collect(mock, code, fight, Path(d), max_pages=2,
                         window_ms=15000)
        assert result["status"] == "COMPLETE_WINDOW"
        assert calls == [(1000, 16000)]
        raw = replay(Path(d) / code / f"fight_{fight}")
        assert raw["identity"]["end"] == 16000
        assert raw["identity"]["full_fight_end"] == 75000
        actor_meta = meta
        gate2, view, lock, receipt = prepare(actor_meta, raw, code=code,
             fight=fight, actor=7, spec="Fury", player_class="Warrior",
             min_observations=2)
        assert view["decision_count"] == 2 and lock["candidate_n"] == 1
        assert lock["candidates"][0]["action_spell_id"] == 101
        assert receipt["high_ranker_provenance"] == "NOT_VERIFIED"
        assert receipt["readiness"] == "UNKNOWN"
        tested += 7
    return {"status": "PASS_OFFLINE_SYNTHETIC",
            "negative_cases": 8, "assertion_groups": tested,
            "live_wcl_api_calls": 0, "actual_ranker_collected": False,
            "freshness_and_identity_fail_closed": True,
            "SimC_semantic_blind_injection": False,
            "actual_priority_proven": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--encounter-id", type=int)
    ap.add_argument("--class-name", default="Warrior")
    ap.add_argument("--spec-name", default="Fury")
    ap.add_argument("--difficulty", type=int, default=4)
    ap.add_argument("--max-pages", type=int, default=2)
    ap.add_argument("--opener-window-ms", type=int, default=15000)
    ap.add_argument("--max-rank", type=int, default=50)
    ap.add_argument("--max-age-days", type=int, default=45)
    ap.add_argument("--out-dir", type=Path)
    args = ap.parse_args()
    if args.self_test or not args.live:
        print(json.dumps(selftest(), sort_keys=True))
        return
    if (not _positive(args.encounter_id) or not _positive(args.difficulty)
            or not 1 <= args.max_pages <= 5 or not 1 <= args.max_rank <= 100
            or not 1 <= args.max_age_days <= 60
            or not 1000 <= args.opener_window_ms <= 60000
            or not args.out_dir or not args.class_name or not args.spec_name):
        ap.error("live requires bounded encounter, difficulty, ranking and output arguments")
    try:
        result = run_live(
            encounter=args.encounter_id, class_name=args.class_name,
            spec_name=args.spec_name, difficulty=args.difficulty,
            max_pages=args.max_pages, max_rank=args.max_rank,
            max_age_days=args.max_age_days, out_dir=args.out_dir,
            opener_window_ms=args.opener_window_ms)
    except Exception as exc:
        # Never print transport responses, credentials, names or report bodies.
        print(json.dumps({"status": "BLOCKED_OR_FAILED", "category":
                          type(exc).__name__,
                          "cause": str(exc) if isinstance(exc, RankSourceError) else
                          "EXTERNAL_API_OR_ENGINE_NEEDS_FOCUSED_DIAGNOSIS",
                          "gameplay_priority": "NOT_VALIDATED"}))
        raise SystemExit(2)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
