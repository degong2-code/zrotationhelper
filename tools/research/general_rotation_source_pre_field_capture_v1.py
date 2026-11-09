#!/usr/bin/env python3
"""Spec-neutral source-PRE field capture for General Rotation research.

Two generic C++ accessors: weapon slot equipped, and named actor buff
current-stack. Source-pinned SpecAdapters select which field is needed
for a physical APL row. No action/class name is present in the C++ producer.

Patch the original pinned SimC player_t::select_action() BEFORE its only
action_ready() invocation, preserving exactly one original readiness call.
Independent verifier compares pristine/instrumented performed-action JSON.
Raw PRE observations are NOT trusted independent READY or NOT_READY facts:
validate binding, provenance, and producer parity separately. Same-time
SimC method PRE must never be substituted for WCL STRICT PRE (<t).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass,replace
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from collections import Counter

from simc_apl_semantic_ir_v2 import git_blob,parse_profile
from simc_native_select_trace_instrument_v1 import (
    instrument as patch_native_source,
    SIMC_COMMIT,PLAYER_CPP_BLOB,RELATIVE as PLAYER_CPP)
from general_rotation_equipment_source_fixture_v1 import (
    source_rule as source_warrior_rule, WARRIOR_BLOB, PROFILE_BLOB as FURY_BLOB)
from general_rotation_mage_source_fixture_v1 import (
    rules as source_mage_rules, CPP_BLOB as MAGE_BLOB,
    PROFILE_BLOB as MAGE_PROFILE_BLOB)
from general_rotation_condition_ir_v1 import (
    ObservedField,inspect_requirement,validate_expression)
from general_rotation_original_pre_field_transport_v1 import (
    FieldCaptureError,require,FieldRequest,field_requests,
    cpp_code,extend_pristine_player,parse_marker,parse_attempt)

SCHEMA="ZrotGenericSimcOriginalPREFieldCapturePlanV1"
AUDIT_SCHEMA="ZrotGenericSimcOriginalPREFieldCaptureReplayV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
MARK="ZROT_GR_FIELD_CAPTURE_PRE_V1|"
ATTEMPT="ZROT_NATIVE_SELECT_V1|ATTEMPT|"
ORIGINAL_CALL="    bool zrot_native_ready = a->action_ready();"
BUFF_CPP_BLOB="6e9b1d8bcf6facea53d0f6e7ac573dfcf52e0a96"
BUFF_HPP_BLOB="6dfc0d2bd56134d3390cdb8757bb4febc8f97e9c"
PLAYER_HPP_BLOB="f2648bec55750fce281e52185966d0424961a5c6"
FIELD_KEY=re.compile(r"^[a-z][a-z0-9_.]{1,127}$")
BUFF_NAME=re.compile(r"^[a-z][a-z0-9_]{0,63}$")
HEX40=re.compile(r"^[0-9a-f]{40}$")
READERS=frozenset(("actor_weapon_slot_equipped","actor_named_buff_active"))
SLOTS=frozenset(("main_hand","off_hand"))



def canonical(value)->bytes:
    return (json.dumps(value,sort_keys=True,ensure_ascii=False,
                       separators=(",",":"),allow_nan=False)+"\n").encode()


def sha(raw:bytes)->str:
    return sha256(raw).hexdigest()



FIELDS=(
    FieldRequest("equipment.main_hand.equipped",
                 "actor_weapon_slot_equipped","main_hand"),
    FieldRequest("equipment.off_hand.equipped",
                 "actor_weapon_slot_equipped","off_hand"),
    FieldRequest("buff.prismatic_bolt.active",
                 "actor_named_buff_active","prismatic_bolt"),
)


def verify_generic_cpp_source(source_root:Path)->dict:
    git=subprocess.run(
        ["git","-C",str(source_root),"rev-parse","HEAD"],
        capture_output=True,text=True,check=True).stdout.strip()
    require(git==SIMC_COMMIT,"ORIGINAL_SIMC_REVISION_NOT_PINNED")
    checks={
        "engine/player/player.cpp":PLAYER_CPP_BLOB,
        "engine/player/player.hpp":PLAYER_HPP_BLOB,
        "engine/buff/buff.cpp":BUFF_CPP_BLOB,
        "engine/buff/buff.hpp":BUFF_HPP_BLOB,
        "engine/class_modules/sc_warrior.cpp":WARRIOR_BLOB,
        "engine/class_modules/sc_mage.cpp":MAGE_BLOB,
    }
    originals={}
    for path,pin in checks.items():
        raw=subprocess.run(
            ["git","-C",str(source_root),"show","HEAD:"+path],
            capture_output=True,check=True).stdout
        require(git_blob(raw)==pin,
                "OFFICIAL_ORIGINAL_SOURCE_BLOB_DRIFT:"+path)
        originals[path]=raw
    player=originals["engine/player/player.hpp"]
    for needle in (b"weapon_t main_hand_weapon;",
                   b"weapon_t off_hand_weapon;"):
        require(needle in player,"PUBLIC_ACTOR_WEAPON_FIELD_CHANGED")
    buff_cpp=originals["engine/buff/buff.cpp"]
    buff_hpp=originals["engine/buff/buff.hpp"]
    for needle in (b"buff_t* buff_t::find( player_t* p",
                   b"return find( p->buff_list, name, source );"):
        require(needle in buff_cpp,"ACTOR_BUFF_LOOKUP_SOURCE_CHANGED")
    for needle in (b"int check() const",b"return current_stack;"):
        require(needle in buff_hpp,"BUFF_STACK_ACCESSOR_NOT_PURE")
    return {"simc_revision":git,"source_git_blobs":checks}



def original_rules(source_root:Path)->dict:
    warrior=(source_root/"engine/class_modules/sc_warrior.cpp").read_bytes()
    mage=(source_root/"engine/class_modules/sc_mage.cpp").read_bytes()
    fury=(source_root/"profiles/MID2/MID2_Warrior_Fury.simc").read_bytes()
    arcane=(source_root/"profiles/MID2/MID2_Mage_Arcane.simc").read_bytes()
    old_w,identity=source_warrior_rule(warrior,fury)
    # Preserve the same pinned C++ guard but normalize its two original
    # WEAPON_NONE comparisons into *slot equipped* Boolean PRE fields.
    def is_present(name:str)->dict:
        return {"op":"compare","field":name,"cmp":"eq","value":True}
    warrior_rule=replace(
        old_w,semantic_key="equipment.mainhand_offhand_slots_present",
        expression={"op":"all","children":[
            is_present("equipment.main_hand.equipped"),
            is_present("equipment.off_hand.equipped")]})
    mage_pairs=source_mage_rules(mage,arcane)
    pairs={"warrior_fury":{"profile_blob":FURY_BLOB,"profile":fury,
                           "rules":[(warrior_rule,identity)]},
           "mage_arcane":{"profile_blob":MAGE_PROFILE_BLOB,"profile":arcane,
                          "rules":mage_pairs}}
    requests={x.key for x in FIELDS}
    for cfg in pairs.values():
        for rule,_ in cfg["rules"]:
            used=set(validate_expression(rule.expression)["required_fields"])
            require(used<=requests,"RULE_FIELD_WITHOUT_PRODUCER")
    return pairs


def make_plan(source_root:Path)->dict:
    source_root=source_root.resolve(strict=True)
    checks=verify_generic_cpp_source(source_root)
    pairs=original_rules(source_root)
    rules=[]
    for spec,cfg in sorted(pairs.items()):
        for rule,identity in cfg["rules"]:
            rules.append({
                "spec_fixture":spec,"semantic_key":rule.semantic_key,
                "rule_id":rule.stable_rule_id,
                "source_profile_git_blob":cfg["profile_blob"],
                "source_row_sha256":identity.source_sha256,
                "source_list":identity.scope.split("::",1)[0],
                "source_ordinal_1based":identity.ordinal+1,
                "source_action":identity.scope.split("::",1)[1],
                "source_method_path":rule.source_method_path,
                "source_method_git_blob":rule.source_method_git_blob,
                "source_guard_sha256":rule.source_guard_sha256,
                "required_field_keys":validate_expression(
                    rule.expression)["required_fields"],
                "source_dispatch_verified":False,
            })
    result={"schema":SCHEMA,"policy_id":POLICY,
            "original_revision":SIMC_COMMIT,
            "source_pins":checks["source_git_blobs"],
            "field_requests":[{"key":f.key,"reader":f.reader,
                               "argument":f.argument} for f in FIELDS],
            "source_rule_bindings":rules,
            "action_identity_resolution":"source_signature_pointer",
            "capture_phase":"SIMC_ORIGINAL_METHOD_PRE",
            "CXX_source_guard_provenance_verified":True,
            "original_original_and_patched_cast_parity":"NOT_YET_PROVEN",
            "source_dispatch_exhaustive":False,
            "independent_READY_or_NOT_READY":False,
            "WCL_API_calls":0}
    result["plan_sha256"]=sha(canonical(result))
    return result


def validate_plan(plan:dict,expected:dict)->tuple[FieldRequest,...]:
    require(isinstance(plan,dict) and plan==expected,
            "CAPTURE_PLAN_NOT_INDEPENDENTLY_REGENERATED_FROM_PINNED_SOURCE")
    fields=field_requests(plan["field_requests"])
    require(plan["plan_sha256"]==sha(canonical({
        k:v for k,v in plan.items() if k!="plan_sha256"
    })),"CAPTURE_PLAN_SHA256_CHANGED")
    return fields



def patch_source(source_root:Path,expected_plan:dict)->dict:
    source_root=source_root.resolve(strict=True)
    plan=make_plan(source_root)
    fields=validate_plan(expected_plan,plan)
    target=source_root/PLAYER_CPP
    original=target.read_bytes()
    require(git_blob(original)==PLAYER_CPP_BLOB,
            "SOURCE_PLAYER_CPP_NO_LONGER_PRISTINE")
    revised=extend_pristine_player(original,fields)
    target.write_bytes(revised)
    return {"schema":SCHEMA,"policy_id":POLICY,
            "plan_sha256":plan["plan_sha256"],
            "producer_marker":MARK,"original_player_cpp_git_blob":PLAYER_CPP_BLOB,
            "modified_player_cpp_sha256":sha(revised),
            "fields_emitted":len(fields),
            "original_select_action_ready_call_count_unchanged":True,
            "new_virtual_ready_calls":0,
            "target_selection_parity":"NOT_YET_PROVEN",
            "full_READY_proven":0,"WCL_API_calls":0}



def replay_original_pre(trace:str,*,plan:dict,source_root:Path,
                        spec:str)->dict:
    actual=make_plan(source_root)
    fields=validate_plan(plan,actual)
    cfg=original_rules(source_root).get(spec)
    require(cfg is not None,"UNDECLARED_SPEC_SOURCE_PROFILE")
    ir=parse_profile(cfg["profile"],require_source=True,
                     expected_git_blob=cfg["profile_blob"])
    samples=[]
    pending=None
    native_attempts=0
    for line in trace.splitlines():
        row=parse_marker(line,fields)
        if row is not None:
            require(pending is None,"DUPLICATED_OR_UNCLOSED_SOURCE_PRE_MARKER")
            pending=row
            continue
        check=parse_attempt(line)
        if check is None:continue
        native_attempts+=1
        require(pending is not None and all(
            pending[k]==check[k] for k in
            ("time_ms","source_list","ordinal_1based","native_action_name")),
            "ORIGINAL_SOURCE_PRE_NOT_PAIRED_WITH_ONE_NATIVE_ATTEMPT")
        samples.append(pending)
        pending=None
    require(pending is None and samples,
            "UNPAIRED_OR_MISSING_ACTUAL_SOURCE_PRE")
    results=[]
    for rule,identity in cfg["rules"]:
        wanted_list,wanted_action=identity.scope.split("::",1)
        ordinal=identity.ordinal+1
        matching=[r for r in samples if
                  r["source_list"]==wanted_list and
                  r["ordinal_1based"]==ordinal and
                  r["native_action_name"]==wanted_action]
        # Not all APL rows must be visited in one deterministic simulation.
        if not matching:
            results.append({"semantic_key":rule.semantic_key,
                "source_row_sha256":identity.source_sha256,
                "matched_original_PRE_attempts":0,
                "source_original_PRE":"NOT_OBSERVED",
                "runtime_condition_status":"UNKNOWN",
                "full_READY":"UNKNOWN"})
            continue
        first=matching[0]
        rlist=ir["action_lists"].get(wanted_list,[])
        require(len(rlist)>=ordinal and
                rlist[ordinal-1]["source_sha256"]==identity.source_sha256,
                "SOURCE_CAPTURE_ORIGINAL_APL_ROW_IDENTITY_CHANGED")
        values=dict(zip((f.key for f in fields),first["values"]))
        observed=[]
        unknown=[]
        for key in validate_expression(rule.expression)["required_fields"]:
            raw=values[key]
            if raw == -1:
                unknown.append(key)
                continue
            observed.append(ObservedField(key, bool(raw), first["time_ms"],
                             "SIMC_ORIGINAL_METHOD_PRE",
                             "actual-original-pre-capture-plan:"+plan["plan_sha256"]))
        original_identity=replace(identity,t_ms=first["time_ms"])
        inspected=inspect_requirement(rule,
            source_profile_git_blob=cfg["profile_blob"],
            identity=original_identity,
            observations=observed,origin="SIMC_ORIGINAL_METHOD_PRE")
        require(inspected["open_world_candidate_proof"]=="UNKNOWN" and
                inspected["dummy_error_permitted"] is False,
                "RUNTIME_SOURCE_HYPOTHESIS_PROMOTED_TO_FULL_READY")
        results.append({"semantic_key":rule.semantic_key,
            "source_row_sha256":identity.source_sha256,
            "matched_original_PRE_attempts":len(matching),
            "first_original_PRE_at_ms":first["time_ms"],
            "first_raw_source_marker":first,
            "unknown_field_keys":unknown,
            "numeric_condition":inspected["hypothesis"]["tri_value"],
            "gate_rule_id":rule.stable_rule_id,
            "full_READY":inspected["full_action_READY"]})
    require(native_attempts==len(samples),
            "RAW_PRE_NATIVE_ATTEMPT_COUNT_CHANGED")
    return {"schema":AUDIT_SCHEMA,"policy_id":POLICY,"spec_fixture":spec,
            "plan_sha256":plan["plan_sha256"],
            "official_simc_revision":SIMC_COMMIT,
            "profile_git_blob":cfg["profile_blob"],
            "original_method_PRE_markers_paired":len(samples),
            "original_native_attempt_count":native_attempts,
            "source_bound_condition_results":results,
            "source_original_PRE_field_transport_verified":True,
            "source_field_values_self_authenticating":False,
            "source_dynamic_dispatch_exhaustive":False,
            "independent_FULL_READY":0,
            "WCL_STRICT_PRE_not_substituted":True,
            "dummy_trainer_error_permitted":False,
            "WCL_API_calls":0}


def selftest()->dict:
    import tempfile
    from simc_native_select_trace_instrument_v1 import START,END
    h=(START+"\n{\n"
       "  // Mark this action list as visited with the APL internal id\n"
       "    if ( a->action_ready() )\n"
       "          return real_a;\n"
       "        return a;\n"
       "  return nullptr;\n}\n"+END+"\n{}\n").encode()
    patched=extend_pristine_player(h,FIELDS).decode()
    require(patched.count(MARK)==1 and
            patched.count("a->action_ready()")==1 and
            patched.index(MARK)<patched.index(ORIGINAL_CALL),
            "GENERIC_CAPTURE_PATCH_TEST_FAILED")
    # The generic C++ producer emits a raw typed *field value*, not a
    # semantic field name or ability-specific source expression. The
    # field-key-to-expression mapping is carried in the pinned plan.
    for fragment in ("main_hand_weapon.type == WEAPON_NONE",
                     "off_hand_weapon.type == WEAPON_NONE",
                     'buff_t::find( a->player, "prismatic_bolt" )'):
        require(fragment in patched,"GENERIC_CAPTURE_FIELD_READER_MISSING")
    sample=(MARK+"20|default|1|alpha|1|0|-1")
    parsed=parse_marker(sample,FIELDS)
    require(parsed["values"]==[1,0,-1],"UNKNOWN_ACTOR_BUFF_NOT_PRESERVED")
    require(parse_attempt(
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|20|default|default|1|alpha|0") ==
        {"time_ms":20,"source_list":"default","ordinal_1based":1,
         "native_action_name":"alpha"},
         "SOURCE_ATTEMPT_BINDING_CHANGED")
    for bad in (
        MARK+"20|default|1|alpha|1|0|2",
        MARK+"20|default|1|alpha|1|0",
    ):
        try:parse_marker(bad,FIELDS)
        except FieldCaptureError:pass
        else:raise AssertionError("FORGED_OR_TRUNCATED_PRE_MARKER_ACCEPTED")
    for bad in ({"key":"x","reader":"python_exec","argument":"os.system"},
                {"key":"buff.foo.active","reader":"actor_named_buff_active",
                 "argument":"foo; action_ready()"},
                {"key":"equipment.mh.equipped",
                 "reader":"actor_weapon_slot_equipped","argument":"left"}):
        try:field_requests([bad])
        except (FieldCaptureError,TypeError):pass
        else:raise AssertionError("UNSAFE_GENERIC_SOURCE_READ_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":13,"same_generic_cpp_capturer_for_two_specs":True,
            "no_hardcoded_class_or_action_in_cpp_producer":True,
            "real_cpp_build":"NOT_RUN","WCL_API_calls":0,
            "full_positive_READY":0}


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root",type=Path)
    parser.add_argument("--plan-out",type=Path)
    parser.add_argument("--patch",action="store_true")
    parser.add_argument("--patch-receipt",type=Path)
    parser.add_argument("--audit-log",type=Path)
    parser.add_argument("--spec",choices=("warrior_fury","mage_arcane"))
    parser.add_argument("--audit-out",type=Path)
    a=parser.parse_args()
    if not (a.source_root or a.plan_out or a.patch or
            a.patch_receipt or a.audit_log or a.spec or a.audit_out):
        print(json.dumps(selftest(),sort_keys=True));return
    if a.source_root is None:
        parser.error("source-root required")
    plan=make_plan(a.source_root)
    if a.plan_out:
        a.plan_out.parent.mkdir(parents=True,exist_ok=True)
        with a.plan_out.open("xb") as p:p.write(canonical(plan))
    if a.patch:
        if not a.patch_receipt or a.audit_log or a.spec or a.audit_out:
            parser.error("patch requires receipt; cannot mix audit")
        receipt=patch_source(a.source_root,plan)
        a.patch_receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.patch_receipt.open("xb") as p:p.write(canonical(receipt))
        print("SIMC_GENERIC_SOURCE_PRE_FIELDS_PATCH_SHA256="+
              sha(a.patch_receipt.read_bytes()))
        return
    if a.audit_log or a.spec or a.audit_out:
        if not (a.audit_log and a.spec and a.audit_out):
            parser.error("audit-log/spec/audit-out required together")
        report=replay_original_pre(
            a.audit_log.read_text(),plan=plan,source_root=a.source_root,
            spec=a.spec)
        a.audit_out.parent.mkdir(parents=True,exist_ok=True)
        with a.audit_out.open("xb") as p:p.write(canonical(report))
        print("SIMC_GENERIC_SOURCE_PRE_FIELD_AUDIT_SHA256="+
              sha(a.audit_out.read_bytes()))
        return
    if a.patch_receipt:
        parser.error("patch receipt without patch")
    print("SIMC_GENERIC_CAPTURE_PLAN_SHA256="+sha(canonical(plan)))


if __name__=="__main__":
    main()
