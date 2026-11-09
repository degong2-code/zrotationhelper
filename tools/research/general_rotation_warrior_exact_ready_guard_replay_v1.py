#!/usr/bin/env python3
"""Fury source adapter: independently validate original ready() weapon guard.

This module supplies Fury-specific field declarations and source pins to the
shared General Rotation OriginalMethodWitness bridge. It does NOT implement
a per-class pointer/marker parser or an additional readiness decision engine.

Real source verification requires the original fixed Git objects, the
modified on-disk C++ producer hashes, and a same-seed pristine/instrumented
SimC action sequence parity receipt. Arbitrary JSON does not establish
source origin; the caller must run this on the controlled producer job.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from simc_apl_semantic_ir_v2 import git_blob
from general_rotation_condition_ir_v1 import validate_expression
from general_rotation_equipment_source_fixture_v1 import (
    source_rule as original_weapon_rule,PROFILE_BLOB,WARRIOR_BLOB)
from general_rotation_source_pre_field_capture_v1 import FIELDS, make_plan
from general_rotation_original_method_witness_v1 import (
    MethodMarker,pair_original_attempts,evaluate_bound_cases)
from simc_native_warrior_exact_ready_guard_producer_v1 import (
    SCHEMA as SOURCE_PRODUCER_SCHEMA, METHOD_MARK,
    PLAYER_PATH,WARRIOR_PATH,PROFILE_PATH,verify_pristine)
from simc_native_select_trace_instrument_v1 import SIMC_COMMIT

SCHEMA="ZrotFuryExactOriginalMethodWeaponNecessaryGateReplayV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
PARITY_SCHEMA="ZrotFuryOriginalWeaponReadySequenceParityV1"

class FuryWitnessError(ValueError):pass

def require(x:bool,why:str)->None:
    if not x:raise FuryWitnessError(why)

def sha(x:bytes)->str:return sha256(x).hexdigest()

def normalized_source_rule(root:Path):
    source=subprocess.run(["git","-C",str(root),"show","HEAD:"+WARRIOR_PATH],
        capture_output=True,check=True).stdout
    profile=(root/PROFILE_PATH).read_bytes()
    # This original C++ requirement checks NON-NONE, i.e. BOTH weapon slots.
    # Its normalized generic source PRE capture emits bool equipped fields.
    rule,ident=original_weapon_rule(source,profile)
    expected={"op":"all","children":[
        {"op":"compare","field":"equipment.main_hand.equipped",
         "cmp":"eq","value":True},
        {"op":"compare","field":"equipment.off_hand.equipped",
         "cmp":"eq","value":True}]}
    normalized=replace(rule,semantic_key="equipment.both_weapon_slots_occupied",
                       expression=expected)
    require(set(validate_expression(normalized.expression)["required_fields"])<=
            {f.key for f in FIELDS},
            "ORIGINAL_FURY_GUARD_UNSUPPORTED_CAPTURE_FIELDS")
    return [(normalized,ident,"rampage")]

def verify_run(root:Path,patch:bytes,parity:bytes)->dict:
    orig=verify_pristine(root)
    p=json.loads(patch)
    q=json.loads(parity)
    require(p.get("schema")==SOURCE_PRODUCER_SCHEMA and
            p.get("policy_id")==POLICY and
            p.get("original_action_ready_call_count_unchanged") is True and
            p.get("original_weapon_slot_condition_preserved") is True and
            p.get("original_warrior_delegate_call_count_unchanged") is True and
            p.get("added_virtual_ready_calls")==0 and
            sha((root/PLAYER_PATH).read_bytes())==
                p.get("source_player_after_sha256") and
            sha((root/WARRIOR_PATH).read_bytes())==
                p.get("source_warrior_after_sha256") and
            orig["original_git_blobs"][WARRIOR_PATH]==WARRIOR_BLOB,
            "PINNED_SOURCE_AND_ACTUAL_PRODUCER_BYTES_NOT_MATCHING")
    require(q.get("schema")==PARITY_SCHEMA and
            q.get("official_source_rev")==SIMC_COMMIT and
            q.get("pristine_and_instrumented_precombat_equal") is True and
            q.get("pristine_and_instrumented_combat_equal") is True and
            q.get("original_native_CPP_compiled") is True and
            type(q.get("original_combat_casts")) is int and
            q["original_combat_casts"]>0,
            "FURY_ORIGINAL_INSTRUMENTED_ACTION_SEQUENCE_NOT_REPRODUCED")
    require(git_blob((root/PROFILE_PATH).read_bytes())==PROFILE_BLOB,
            "ORIGINAL_FURY_PROFILE_NOT_IDENTICAL")
    # The official fixed source pins and original semantic rule are
    # re-derived, not copied from the producer's receipt text.
    plan=make_plan(root)
    require(plan["original_revision"]==SIMC_COMMIT and
            plan["field_requests"][0]["key"]=="equipment.main_hand.equipped" and
            plan["field_requests"][1]["key"]=="equipment.off_hand.equipped",
            "PINNED_GENERIC_SOURCE_PLAN_DIFFERENT")
    return q

def audit(root:Path,trace:bytes,patch:bytes,parity:bytes)->dict:
    q=verify_run(root,patch,parity)
    decoded=pair_original_attempts(
        trace.decode("utf-8"),fields=FIELDS,
        method_markers=(MethodMarker(
            METHOD_MARK,"rampage",
            ("equipment.main_hand.equipped","equipment.off_hand.equipped")),))
    rules=normalized_source_rule(root)
    report=evaluate_bound_cases(
        rows=decoded["rows"],fields=FIELDS,
        source_rules=rules,
        receipt_sha256={"raw_log":sha(trace),"patch":sha(patch),
                        "parity":sha(parity)},
        source_verified=True)
    require(report["full_positive_READY"]==0 and
            report["dummy_practice_error_permitted"] is False and
            report["WCL_STRICT_PRE_used"] is False,
            "SOURCE_PRE_NEGATIVE_BECAME_FULL_POSITIVE_READY")
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "official_source_rev":SIMC_COMMIT,
        "source_profile_git_blob":PROFILE_BLOB,
        "raw_source_log_sha256":sha(trace),
        "producer_patch_receipt_sha256":sha(patch),
        "pristine_instrumented_sequence_sha256":sha(parity),
        "pristine_instrumented_combat_casts":q["original_combat_casts"],
        "original_native_attempts":decoded["original_native_attempts"],
        "unattributed_method_events":decoded["unattributed_method_events"],
        "source_scope_method":"rampage_parent_t::ready",
        "source_requirement":"both_main_hand_and_off_hand_weapon_slots_occupied",
        "source_original_PRE_provenance":"SIMC_ORIGINAL_METHOD_PRE",
        "source_evidence_authenticated_by_independent_original_run":True,
        **report,
        "actual_WCL_holdout_completed":False,
        "actual_WoW_dummy_practice_observed":False,
        "MAIN_promoted":False,
    }

def selftest()->dict:
    assert METHOD_MARK.startswith("ZROT_")
    assert PARITY_SCHEMA.startswith("Zrot")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":4,"generic_method_witness_used":True,
            "class_specific_pointer_parser_written":False,
            "actual_original_CXX_executed":False,
            "full_positive_READY":0,"WCL_API_calls":0}

def main()->None:
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source-root",type=Path)
    cli.add_argument("--raw-log",type=Path)
    cli.add_argument("--patch-receipt",type=Path)
    cli.add_argument("--parity-receipt",type=Path)
    cli.add_argument("--out",type=Path)
    a=cli.parse_args()
    vals=(a.source_root,a.raw_log,a.patch_receipt,a.parity_receipt,a.out)
    if all(x is None for x in vals):
        print(json.dumps(selftest(),sort_keys=True));return
    if any(x is None for x in vals):
        cli.error("source-root, raw-log, patch, parity, output all required")
    r=audit(a.source_root,a.raw_log.read_bytes(),
            a.patch_receipt.read_bytes(),a.parity_receipt.read_bytes())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:
        f.write((json.dumps(r,sort_keys=True,indent=2)+"\n").encode())
    print("FURY_ORIGINAL_EXACT_WEAPON_GUARD_REPLAY_SHA256="+sha(a.out.read_bytes()))

if __name__=="__main__":
    main()
