#!/usr/bin/env python3
"""Arcane Mage SpecAdapter fixture: opposite buff gates, same generic IR.

Pinned official C++ and APL, with no witnessed real Mage PRE. Real READY
and WCL/target-dummy decisions remain UNKNOWN. No Mage branching in core.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
from general_rotation_condition_ir_v1 import (
    SourceBoundRequirement,ObservedField,inspect_requirement)
from general_rotation_decision_proof_engine_v1 import Identity
from simc_apl_semantic_ir_v2 import git_blob,parse_profile

SCHEMA="ZrotMageSourcePinnedOppositeBuffGuardAdapterFixtureV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
CPP_BLOB="306d835f2db5f7418da221ce155d32e81c53f45c"
PROFILE_BLOB="8d06eda4f69374dd1ed2e2d1eb8076b82cbbaf7f"
SPECS=(
    ("arcane_blast",72,
     "struct arcane_blast_t final : public arcane_mage_spell_t",
     "// The aoe part of Prismatic Bolt",
     "if ( p()->buffs.prismatic_bolt->check() )",False),
    ("prismatic_bolt",69,
     "struct prismatic_bolt_t final : public arcane_mage_spell_t",
     "  void execute() override",
     "if ( !p()->buffs.prismatic_bolt->check() )",True),
)

class MageSourceError(ValueError):pass

def rules(cpp_raw:bytes,profile:bytes):
    if git_blob(cpp_raw)!=CPP_BLOB or git_blob(profile)!=PROFILE_BLOB:
        raise MageSourceError("ORIGINAL_MAGE_SOURCE_PROFILE_PIN_MISMATCH")
    cpp=cpp_raw.decode("utf-8")
    ir=parse_profile(profile,require_source=True,
                     expected_git_blob=PROFILE_BLOB)
    source_rows=ir["action_lists"].get("spellslinger",[])
    if len(source_rows)<2:
        raise MageSourceError("MAGE_SOURCE_APL_LIST_MISSING")
    output=[]
    for action,line,start,end,guard,expected in SPECS:
        if cpp.count(start)!=1:
            raise MageSourceError("MAGE_SOURCE_STRUCT_NOT_UNIQUE")
        body=cpp.split(start,1)[1].split(end,1)[0]
        if (body.count("bool ready() override")!=1 or
            body.count(guard)!=1 or
            body.count("return arcane_mage_spell_t::ready();")!=1 or
            body.count("return false;")<1 or
            not body.index("bool ready() override") <
            body.index(guard) <
            body.index("return arcane_mage_spell_t::ready();")):
            raise MageSourceError("MAGE_READY_GUARD_CHANGED")
        matched=[r for r in source_rows if
                 r["source_line"]==line and r["action"]==action and
                 r["behavior"]=="ACTION"]
        if len(matched)!=1:
            raise MageSourceError("MAGE_SOURCE_APL_ROW_PIN_DRIFT")
        row=matched[0]
        rule=SourceBoundRequirement(
            semantic_key="buff.prismatic_bolt." + ("present" if expected else "absent"),
            source_profile_git_blob=PROFILE_BLOB,
            source_row_sha256=row["source_sha256"],
            source_method_path="engine/class_modules/sc_mage.cpp",
            source_method_git_blob=CPP_BLOB,
            source_guard_sha256=sha256(guard.encode()).hexdigest(),
            gate="necessary_eligibility",
            expression={"op":"compare","field":"buff.prismatic_bolt.active",
                        "cmp":"eq","value":expected})
        ident=Identity("spellslinger::"+action,row["source_sha256"],
                       20031,row["index"],0)
        output.append((rule,ident))
    return output

def audit(cpp_raw:bytes,profile:bytes)->dict:
    pairs=rules(cpp_raw,profile)
    if len(pairs)!=2 or pairs[0][0].stable_rule_id==pairs[1][0].stable_rule_id:
        raise MageSourceError("DUPLICATE_MAGE_SOURCE_RULES")
    for rule,ident in pairs:
        missing=inspect_requirement(
            rule,source_profile_git_blob=PROFILE_BLOB,identity=ident,
            observations=[],origin="SIMC_ORIGINAL_METHOD_PRE")
        if (missing["hypothesis"]["tri_value"]!="UNKNOWN" or
            missing["hypothesis"]["missing_field_keys"]!=[
                "buff.prismatic_bolt.active"] or
            missing["open_world_candidate_proof"]!="UNKNOWN"):
            raise MageSourceError("MISSING_MAGE_BUFF_WAS_PROMOTED")
    examples=[]
    for active in (False,True):
        outcome=[]
        for rule,ident in pairs:
            candidate=inspect_requirement(
                rule,source_profile_git_blob=PROFILE_BLOB,identity=ident,
                observations=[ObservedField("buff.prismatic_bolt.active",
                    active,ident.t_ms,"SYNTHETIC_TEST_ONLY","synthetic-not-real")],
                origin="SYNTHETIC_TEST_ONLY")
            if candidate["open_world_candidate_proof"]!="UNKNOWN":
                raise MageSourceError("SYNTHETIC_MAGE_STATE_PROMOTED")
            outcome.append(candidate["hypothesis"]["tri_value"])
        if outcome!=(["FALSE","TRUE"] if active else ["TRUE","FALSE"]):
            raise MageSourceError("OPPOSITE_MAGE_SOURCE_RULE_NOT_GENERALIZED")
        examples.append({"synthetic_buff_active":active,
            "arcane_blast_condition":outcome[0],
            "prismatic_bolt_condition":outcome[1],
            "both_full_READY":"UNKNOWN"})
    return {"schema":SCHEMA,"policy_id":POLICY,
        "official_mage_cpp_git_blob":CPP_BLOB,
        "official_mage_profile_git_blob":PROFILE_BLOB,
        "two_source_guard_rules_verified":True,
        "both_physically_distinct_spells_same_generic_condition_IR":True,
        "source_bound_rule_ids":[r.stable_rule_id for r,_ in pairs],
        "real_original_mage_buff_PRE_count":0,
        "full_arcane_ready":"UNKNOWN",
        "synthetic_opposite_buff_examples":examples,
        "WCL_holdout_completed":False,"MAIN_promoted":False}

def selftest():
    try:rules(b"fiction",b"actions=arcane_blast")
    except MageSourceError:pass
    else:raise AssertionError("FORGED_SOURCE_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":2,"real_CPP_source_executed":False,
            "full_positive_READY":0,"WCL_API_calls":0}

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--official-mage-source",type=Path)
    cli.add_argument("--official-profile",type=Path)
    cli.add_argument("--out",type=Path)
    a=cli.parse_args()
    if all(x is None for x in (a.official_mage_source,a.official_profile,a.out)):
        print(json.dumps(selftest(),sort_keys=True));return
    if not(a.official_mage_source and a.official_profile and a.out):
        cli.error("source, profile, and output must be supplied together")
    result=audit(a.official_mage_source.read_bytes(),
                 a.official_profile.read_bytes())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:
        f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    print("MAGE_SOURCE_BOUND_RULE_RECEIPT_SHA256="+
          sha256(a.out.read_bytes()).hexdigest())

if __name__=="__main__":
    main()
