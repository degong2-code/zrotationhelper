#!/usr/bin/env python3
"""Reusable post-lock WCL actor combatantinfo provenance; no gameplay advice.

Consumes an existing verified raw checkpoint/page ledger plus its actor identity
gate. Strict PRE is established only when the actor's sole combatantinfo
timestamp is earlier than the actor's first observed cast or begin-cast.
Observed numeric gear/talent/set entries are *not* spell, set-bonus, patch,
SimC profile or READY certification. No WCL API/SimC network calls.

No flags: offline synthetic tests. --raw-root and --actor-gate: offline reuse.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import tempfile

from fresh_wcl_engine_v1 import canonical, sha, replay, checked_pages, write_atomic

SCHEMA = "ZrotWclActorCombatantinfoPreEvidenceV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class CombatantEvidenceError(ValueError):
    pass


def require(ok: bool, code: str) -> None:
    if not ok:
        raise CombatantEvidenceError(code)


def _positive(x: object) -> bool:
    return type(x) is int and x > 0


def _raw_entries(folder: Path, checkpoint: dict) -> list[dict]:
    result = []
    for page in checked_pages(folder, checkpoint):
        obj = json.loads((folder / page["file"]).read_bytes())
        result.extend(obj["events"])
    return result


def _numeric_build(event: dict) -> dict:
    require(_positive(event.get("specID")), "COMBATANT_SPEC_ID_MISSING")
    gear = event.get("gear")
    tree = event.get("talentTree")
    require(type(gear) is list and type(tree) is list,
            "COMBATANT_GEAR_OR_TREE_UNOBSERVED")
    # WCL represents an unequipped slot with id=0. It is an observed slot,
    # not an equipped item and not evidence of any activated set bonus.
    require(all(type(g) is dict and type(g.get("id")) is int and
                g["id"] >= 0 and
                (g.get("setID") is None or _positive(g["setID"])) and
                (g["id"] != 0 or g.get("setID") is None) for g in gear),
            "COMBATANT_GEAR_INCOMPLETE")
    require(all(type(t) is dict and _positive(t.get("nodeID")) and
                _positive(t.get("id")) and
                type(t.get("rank")) is int and t["rank"] >= 0 for t in tree),
            "COMBATANT_TALENT_TREE_INCOMPLETE")
    # Preserve multiple entries for a single node. A selected talentTree entry
    # need not correspond to an active hero-tree branch or current SimC option.
    selected = [{"nodeID": t["nodeID"], "entryID": t["id"], "rank": t["rank"]}
                for t in tree]
    sets = Counter(str(g["setID"]) for g in gear if g.get("setID") is not None)
    return {
        "observed_numeric_specID": event["specID"],
        "observed_gear_slot_count": len(gear),
        "observed_gear_item_count": sum(g["id"] > 0 for g in gear),
        "observed_gear_empty_slot_count": sum(g["id"] == 0 for g in gear),
        "observed_gear_item_ids": [g["id"] for g in gear],
        "observed_gear_setID_item_counts": dict(sorted(sets.items())),
        "observed_gear_numeric_sha256": sha(canonical(gear)),
        "observed_talent_entry_count": len(selected),
        "observed_talent_unique_node_count": len(set(t["nodeID"] for t in selected)),
        "observed_talent_entries": selected,
        "observed_talent_entry_sha256": sha(canonical(selected)),
    }


def produce(folder: Path, gate: dict) -> dict:
    require(type(gate) is dict and
            gate.get("schema") == "ZrotWclActorIdentityGateV1" and
            gate.get("status") == "ACTOR_FIGHT_SPEC_CLASS_MATCH" and
            gate.get("talent_build") == "UNKNOWN" and
            gate.get("spec_build_equivalence_to_SimC") == "UNKNOWN" and
            gate.get("rank_source_verified") is False and
            _positive(gate.get("actor_id")) and
            type(gate.get("source_metadata_sha256")) is str and
            HEX64.fullmatch(gate["source_metadata_sha256"]),
            "ORIGINAL_ACTOR_IDENTITY_GATE_INVALID")
    raw = replay(folder)  # Existing checkpoint ledger/hash/time validation.
    checkpoint = json.loads((folder / "checkpoint.json").read_bytes())
    ident = raw["identity"]
    for gate_field, raw_field in (
        ("report_code", "report_code"), ("fight_id", "fight_id"),
        ("report_revision", "revision"), ("fight_start_ms", "start"),
        ("fight_end_ms", "full_fight_end")
    ):
        require(gate.get(gate_field) == ident.get(raw_field),
                "ORIGINAL_ACTOR_FIGHT_IDENTITY_MISMATCH")
    require(ident.get("evidence_window") == "FIGHT_START_BOUNDED" and
            checkpoint.get("complete") is True,
            "BOUNDED_COMPLETE_SNAPSHOT_REQUIRED")
    events = _raw_entries(folder, checkpoint)
    actor = gate["actor_id"]
    actions = [e["timestamp"] for e in events
               if e.get("sourceID") == actor and
               e.get("type") in ("begincast", "cast")]
    require(bool(actions), "NO_ACTOR_ACTIONS_IN_RAW_WINDOW")
    first = min(actions)
    ci_rows = [e for e in events if e.get("type") == "combatantinfo"
               and e.get("sourceID") == actor]
    # Multiple conflicting/same-timestamp records do not become known state.
    eligible = (len(ci_rows) == 1 and
                type(ci_rows[0].get("timestamp")) in (int, float) and
                ci_rows[0]["timestamp"] < first)
    result = {
        "schema": SCHEMA, "policy_id": POLICY,
        "source": "OFFICIAL_WCL_EXISTING_CHECKPOINT_AND_ACTOR_GATE",
        "actor_fight_fingerprint_sha256": sha(canonical([
            gate["report_code"], gate["fight_id"], actor])),
        "original_actor_gate_sha256": sha(canonical(gate)),
        "original_metadata_sha256_from_prior_gate_only":
            gate["source_metadata_sha256"],
        "original_source_page_sha256": [p["sha256"] for p in
                                        checkpoint["pages"]],
        "combatantinfo_actor_row_count": len(ci_rows),
        "actor_first_action_ms": first - ident["start"],
        "combatantinfo_pre_status":
            "OBSERVED_STRICT_PRE" if eligible else
            "UNKNOWN_NO_UNIQUE_PRE_COMBATANTINFO",
        "actor_numeric_build_snapshot": None,
        "current_Retail_patch_or_client_build": "UNKNOWN",
        "report_absolute_UTC_epoch": "UNKNOWN",
        "source_SimC_profile_build_equivalence": "UNKNOWN",
        "source_spell_aura_semantic_identity": "UNKNOWN",
        "equipped_set_bonus_activated": "UNKNOWN",
        "competing_action_READY": "UNKNOWN",
        "general_rotation_rule_certified": False,
        "dummy_wrong_cast_certified": False,
        "new_WCL_API_calls": 0,
    }
    if eligible:
        e = ci_rows[0]
        require(e["timestamp"] >= ident["start"],
                "COMBATANTINFO_BEFORE_FIGHT_START")
        result["actor_numeric_build_snapshot"] = {
            "combatantinfo_at_ms": e["timestamp"] - ident["start"],
            "strictly_before_first_actor_action": True,
            "combatantinfo_event_sha256": sha(canonical(e)),
            **_numeric_build(e),
        }
    return result


def selftest() -> dict:
    import copy
    passed = 0
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        def make(events):
            page = {"schema": "FreshWCLPageV1", "start": 100,
                    "next": None, "events": events}
            (folder / "page_00000.json").write_bytes(canonical(page))
            ident = {"report_code": "ProofABC", "fight_id": 1,
                     "revision": 1, "start": 100, "end": 500,
                     "full_fight_end": 900, "requested_window_ms": 400,
                     "evidence_window": "FIGHT_START_BOUNDED"}
            cp = {"schema": "FreshWCLCheckpointV1", "complete": True,
                  "identity": ident, "cursor": None,
                  "pages": [{"file": "page_00000.json",
                             "start": 100, "next": None,
                             "event_count": len(events),
                             "sha256": sha(canonical(page))}]}
            (folder / "checkpoint.json").write_bytes(canonical(cp))
        gate = {"schema": "ZrotWclActorIdentityGateV1",
                "status": "ACTOR_FIGHT_SPEC_CLASS_MATCH",
                "actor_id": 42, "report_code": "ProofABC", "fight_id": 1,
                "report_revision": 1, "fight_start_ms": 100,
                "fight_end_ms": 900, "source_metadata_sha256": "a"*64,
                "talent_build": "UNKNOWN",
                "spec_build_equivalence_to_SimC": "UNKNOWN",
                "rank_source_verified": False}
        ci = {"type": "combatantinfo", "timestamp": 101,
              "sourceID": 42, "specID": 72,
              "gear": [{"id": 201, "setID": 7},
                       {"id": 202, "setID": 7}],
              "talentTree": [{"nodeID": 7, "id": 70, "rank": 1},
                             {"nodeID": 7, "id": 71, "rank": 1}]}
        cast = {"type": "cast", "timestamp": 200,
                "sourceID": 42, "abilityGameID": 123}
        make([ci, cast])
        report = produce(folder, gate)
        assert report["combatantinfo_pre_status"] == "OBSERVED_STRICT_PRE"
        assert report["actor_numeric_build_snapshot"]["observed_gear_setID_item_counts"] == {"7":2}
        assert report["actor_numeric_build_snapshot"]["observed_talent_unique_node_count"] == 1
        assert report["general_rotation_rule_certified"] is False
        passed += 1
        make([{**ci, "gear": ci["gear"] + [{"id": 0}]}, cast])
        empty = produce(folder, gate)["actor_numeric_build_snapshot"]
        assert empty["observed_gear_slot_count"] == 3
        assert empty["observed_gear_item_count"] == 2
        assert empty["observed_gear_empty_slot_count"] == 1
        passed += 1
        make([{**ci, "timestamp": 200}, cast])
        assert produce(folder, gate)["actor_numeric_build_snapshot"] is None
        passed += 1
        make([ci, {**ci, "timestamp": 102}, cast])
        assert produce(folder, gate)["combatantinfo_pre_status"].startswith("UNKNOWN")
        passed += 1
        make([{**ci, "sourceID": 43}, cast])
        assert produce(folder, gate)["actor_numeric_build_snapshot"] is None
        passed += 1
        make([ci, cast])
        altered = copy.deepcopy(gate)
        altered["fight_id"] = 9
        try: produce(folder, altered)
        except CombatantEvidenceError: passed += 1
        else: raise AssertionError("CROSS_FIGHT_GATE_ACCEPTED")
        (folder / "page_00000.json").write_bytes(b"{}")
        try: produce(folder, gate)
        except Exception: passed += 1
        else: raise AssertionError("TAMPERED_PAGE_ACCEPTED")
    return {"status": "PASS_OFFLINE_SYNTHETIC", "checks": passed,
            "independent_gameplay_PRIORITY_proven": False,
            "WCL_API_called": False}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--raw-root", type=Path)
    p.add_argument("--actor-gate", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    if not any((args.raw_root, args.actor_gate, args.out)):
        print(json.dumps(selftest(), sort_keys=True))
        return
    if not all((args.raw_root, args.actor_gate, args.out)):
        p.error("--raw-root, --actor-gate and --out are required together")
    gate = json.loads(args.actor_gate.read_bytes())
    result = produce(args.raw_root, gate)
    write_atomic(args.out, canonical(result))
    print(json.dumps({"status": result["combatantinfo_pre_status"],
                      "numeric_build_observed":
                          result["actor_numeric_build_snapshot"] is not None,
                      "gameplay_priority": "NOT_CERTIFIED",
                      "output_sha256": sha(args.out.read_bytes())},
                     sort_keys=True))


if __name__ == "__main__":
    main()
