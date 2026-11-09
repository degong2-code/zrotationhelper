#!/usr/bin/env python3
"""Spec-neutral conditional eligibility IR for General Rotation.

The generic interpreter knows only typed state fields, EQ/NE/IN/GE/etc.,
AND/OR/NOT, time-scoped observations, and source-bound rule identity.
It knows NO class names, action/spell names, weapon slots, weapon categories,
WoW hard-coded mechanics, or encounter-specific scheduling.

SpecAdapters declare actual requirements after *independent source review*.
An expression is NOT an assertion that the source rule exists or a complete
READY proof. Caller-supplied observations and receipts are untrusted. This
interpreter outputs a numeric *hypothesis* and an open GateContract/UNKNOWN;
a separately validated raw producer/route must promote individual facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any

from general_rotation_decision_proof_engine_v1 import (
    Identity, GateContract, decide_candidate, UNKNOWN
)

SCHEMA="ZrotGeneralRotationSourceBoundConditionalEligibilityIRV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
KEY=re.compile(r"^[a-z][a-z0-9_.]{0,127}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")
HEX40=re.compile(r"^[0-9a-f]{40}$")
COMPARE=frozenset(("eq","ne","in","not_in","gte","lte","gt","lt"))
CAPTURES=frozenset(("SIMC_ORIGINAL_METHOD_PRE","WCL_STRICT_PRE",
                    "SYNTHETIC_TEST_ONLY"))
MAX_NODES=96
MAX_DEPTH=12
MAX_FIELDS=128


class ConditionalIRError(ValueError):
    pass


def fail(ok:bool,code:str)->None:
    if not ok:raise ConditionalIRError(code)


def scalar(value:Any)->bool:
    return type(value) in (bool,int,str,float) and (
        type(value) is not float or -1e100 < value < 1e100)


def valid_key(value:Any)->bool:
    return isinstance(value,str) and KEY.fullmatch(value) is not None


def canonical(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class SourceBoundRequirement:
    """Source identity is a row + method guard, NEVER a hardcoded skill name."""
    semantic_key:str
    source_profile_git_blob:str
    source_row_sha256:str
    source_method_path:str
    source_method_git_blob:str
    source_guard_sha256:str
    gate:str
    expression:dict

    def __post_init__(self):
        fail(valid_key(self.semantic_key) and valid_key(self.gate),
             "SOURCE_RULE_SEMANTIC_ID_OR_GATE_INVALID")
        fail(bool(HEX40.fullmatch(self.source_profile_git_blob)) and
             bool(HEX64.fullmatch(self.source_row_sha256)) and
             bool(HEX40.fullmatch(self.source_method_git_blob)) and
             bool(HEX64.fullmatch(self.source_guard_sha256)) and
             isinstance(self.source_method_path,str) and
             self.source_method_path.startswith("engine/") and
             ".." not in self.source_method_path,
             "SOURCE_RULE_REQUIRES_PINNED_METHOD_AND_ROW")
        validate_expression(self.expression)

    @property
    def stable_rule_id(self)->str:
        return sha256(canonical({
            "semantic_key":self.semantic_key,
            "source_profile_git_blob":self.source_profile_git_blob,
            "source_row_sha256":self.source_row_sha256,
            "source_method_path":self.source_method_path,
            "source_method_git_blob":self.source_method_git_blob,
            "source_guard_sha256":self.source_guard_sha256,
            "gate":self.gate,"expression":self.expression,
        })).hexdigest()


@dataclass(frozen=True)
class ObservedField:
    """Raw state supplied by a producer, NOT self-authenticating evidence."""
    key:str
    value:bool|int|float|str
    event_t_ms:int
    captured:str
    receipt:str

    def __post_init__(self):
        fail(valid_key(self.key) and scalar(self.value) and
             type(self.event_t_ms) is int and self.event_t_ms>=0 and
             self.captured in CAPTURES and
             isinstance(self.receipt,str) and bool(self.receipt),
             "STATE_FIELD_VALUE_OR_PROVENANCE_INVALID")


def validate_expression(node:Any)->dict:
    """Validate a bounded portable AST without eval or specialization branches."""
    visited=0
    fields=set()
    def visit(x:Any,depth:int)->None:
        nonlocal visited
        visited+=1
        fail(visited<=MAX_NODES and depth<=MAX_DEPTH,
             "CONDITION_AST_BUDGET_EXCEEDED")
        fail(isinstance(x,dict) and isinstance(x.get("op"),str),
             "CONDITION_NODE_NOT_OBJECT")
        op=x["op"]
        if op in ("all","any"):
            fail(set(x)=={"op","children"} and
                 isinstance(x["children"],list) and
                 1<=len(x["children"])<=MAX_FIELDS,
                 "CONDITION_JUNCTION_CHILDREN_INVALID")
            for child in x["children"]:visit(child,depth+1)
        elif op=="not":
            fail(set(x)=={"op","child"},"CONDITION_NOT_FIELDS_INVALID")
            visit(x["child"],depth+1)
        elif op=="compare":
            fail(set(x)=={"op","field","cmp","value"} and
                 valid_key(x["field"]) and x["cmp"] in COMPARE,
                 "CONDITION_COMPARE_FIELDS_INVALID")
            value=x["value"]
            if x["cmp"] in ("in","not_in"):
                fail(isinstance(value,list) and 1<=len(value)<=32 and
                     all(scalar(v) for v in value) and
                     all(type(v) is type(value[0]) for v in value),
                     "CONDITION_MEMBERSHIP_TYPES_INVALID")
            else:
                fail(scalar(value),"CONDITION_LITERAL_INVALID")
            if x["cmp"] in ("gt","gte","lt","lte"):
                fail(type(value) in (int,float),
                     "NUMERIC_COMPARISON_REQUIRES_NUMBER")
            fields.add(x["field"])
        else:
            raise ConditionalIRError("UNSUPPORTED_CONDITION_OPCODE")
    visit(node,0)
    fail(len(fields)<=MAX_FIELDS,"CONDITION_FIELDS_EXCEEDED")
    return {"node_count":visited,"required_fields":sorted(fields)}


def compare(observed:Any,cmp:str,target:Any)->bool|None:
    if cmp in ("eq","ne"):
        if type(observed) is not type(target):return None
        eq=observed==target
        return eq if cmp=="eq" else not eq
    if cmp in ("in","not_in"):
        if not all(type(observed) is type(v) for v in target):return None
        inside=observed in target
        return inside if cmp=="in" else not inside
    if (type(observed) not in (int,float) or
        type(target) not in (int,float)):return None
    if cmp=="gt":return observed>target
    if cmp=="gte":return observed>=target
    if cmp=="lt":return observed<target
    if cmp=="lte":return observed<=target
    raise ConditionalIRError("IMPOSSIBLE_COMPARE_OPCODE")


def numeric_condition(expr:dict,observations:dict[str,ObservedField])->dict:
    """Strong-Kleene tri-state: AND false dominates unknown; OR true dominates."""
    syntax=validate_expression(expr)
    missing=set()
    type_unknown=set()
    used=set()
    def walk(x:dict)->bool|None:
        op=x["op"]
        if op=="compare":
            key=x["field"]
            item=observations.get(key)
            if item is None:
                missing.add(key)
                return None
            used.add(key)
            v=compare(item.value,x["cmp"],x["value"])
            if v is None:type_unknown.add(key)
            return v
        if op=="not":
            v=walk(x["child"])
            return None if v is None else not v
        values=[walk(v) for v in x["children"]]
        if op=="all":
            return False if False in values else (
                True if all(v is True for v in values) else None)
        return True if True in values else (
            False if all(v is False for v in values) else None)
    value=walk(expr)
    return {"tri_value":"UNKNOWN" if value is None else
            "TRUE" if value else "FALSE",
            "numeric_bool":value,
            "missing_field_keys":sorted(missing),
            "incompatible_type_keys":sorted(type_unknown),
            "observed_field_keys":sorted(used),
            "expression_nodes":syntax["node_count"]}


def inspect_requirement(binding:SourceBoundRequirement, *,
                        source_profile_git_blob:str,
                        identity:Identity,
                        observations:list[ObservedField],
                        origin:str)->dict:
    """Compare a declared rule to PRE values; NEVER mint independent READY facts.

    In particular, a fake source receipt, user JSON, observed WCL cast or
    class-specific rule string cannot cause a real NOT_READY/READY decision.
    """
    fail(isinstance(binding,SourceBoundRequirement) and
         isinstance(identity,Identity) and
         binding.source_profile_git_blob==source_profile_git_blob and
         identity.source_sha256==binding.source_row_sha256,
         "SOURCE_RULE_APL_ROW_PROFILE_SCOPE_CONFLICT")
    fail(origin in ("SIMC_ORIGINAL_METHOD_PRE","WCL_STRICT_PRE",
                    "SYNTHETIC_TEST_ONLY"),"CONDITION_PRE_PHASE_INVALID")
    fail(isinstance(observations,list) and len(observations)<=MAX_FIELDS,
         "PRE_OBSERVATION_VOLUME_INVALID")
    by_key={}
    for f in observations:
        fail(isinstance(f,ObservedField) and f.captured==origin,
             "CROSS_PROVENANCE_OR_INVALID_SOURCE_FACT")
        if origin=="SIMC_ORIGINAL_METHOD_PRE":
            fail(f.event_t_ms==identity.t_ms,
                 "SIMC_ORIGINAL_METHOD_PRE_NOT_EXACT_TIMESTAMP")
        elif origin=="WCL_STRICT_PRE":
            fail(f.event_t_ms<identity.t_ms,
                 "WCL_SAME_TIMESTAMP_OR_FUTURE_LEAKAGE")
        else:
            fail(f.event_t_ms==identity.t_ms,
                 "SYNTHETIC_STATE_TIME_MISMATCH")
        fail(f.key not in by_key,
             "DUPLICATED_OR_CONTRADICTORY_FIELD_PROVENANCE")
        by_key[f.key]=f
    result=numeric_condition(binding.expression,by_key)
    # This generic layer is agnostic to how the original producer was
    # authenticated. Deliberately do not construct a trusted Fact from an
    # arbitrary declaration or user-submitted PRE value.
    contract=GateContract(
        source="SOURCE_DECLARATION_NOT_PRODUCER_AUTHENTICATION",
        source_sha256=identity.source_sha256,
        required=(binding.gate,"BASE_VIRTUAL_COMPLETE"),
        closed=False)
    proof=decide_candidate(identity,contract,(),is_physical_action=True)
    fail(proof["decision"]==UNKNOWN and
         proof["dummy_error_permitted"] is False,
         "UNVERIFIED_PREDICATE_ACCIDENTALLY_PROMOTED")
    return {"schema":SCHEMA,"policy_id":POLICY,
            "semantic_requirement":binding.semantic_key,
            "source_row_sha256":identity.source_sha256,
            "source_profile_git_blob":source_profile_git_blob,
            "source_method_git_blob":binding.source_method_git_blob,
            "source_guard_sha256":binding.source_guard_sha256,
            "source_rule_id":binding.stable_rule_id,
            "at_ms":identity.t_ms,
            "source_occurrence":identity.occurrence,
            "source_phase":origin,
            "hypothesis":result,
            "producer_source_guard_independently_authenticated_here":False,
            "state_values_independently_authenticated_here":False,
            "numeric_hypothesis_not_used_to_eliminate_candidates":True,
            "open_world_candidate_proof":proof["decision"],
            "full_action_READY":"UNKNOWN",
            "dummy_error_permitted":False,
            "WCL_actual_combat_cast_not_a_mechanic_truth":True,
            "MAIN_promoted":False}


def selftest()->dict:
    from copy import deepcopy
    h="a"*64;blob="b"*40
    ident=Identity("demo::opaque-source-action",h,100,3,0)
    p=lambda field,cmp,value:{"op":"compare","field":field,
                               "cmp":cmp,"value":value}
    both_weapons={"op":"all","children":[
        p("equipment.main_hand.weapon_type","ne","NONE"),
        p("equipment.off_hand.weapon_type","ne","NONE")]}
    daggers={"op":"all","children":[
        p("equipment.main_hand.equipped","eq",True),
        p("equipment.off_hand.equipped","eq",True),
        p("equipment.main_hand.weapon_subclass","eq","DAGGER"),
        p("equipment.off_hand.weapon_subclass","eq","DAGGER")]}
    # The opaque action names are deliberately different: identical
    # engine, different source rule and field requirements.
    b1=SourceBoundRequirement("equipment.both_weapon_slots",blob,h,
        "engine/class_modules/a.cpp","c"*40,"d"*64,
        "necessary_eligibility",both_weapons)
    b2=SourceBoundRequirement("equipment.two_daggers",blob,h,
        "engine/class_modules/b.cpp","e"*40,"f"*64,
        "necessary_eligibility",daggers)
    def o(key,value,ts=100,cap="SYNTHETIC_TEST_ONLY"):
        return ObservedField(key,value,ts,cap,"synthetic-declaration-only")
    a=[o("equipment.main_hand.weapon_type","SWORD"),
       o("equipment.off_hand.weapon_type","DAGGER")]
    first=inspect_requirement(b1,source_profile_git_blob=blob,
        identity=ident,observations=a,origin="SYNTHETIC_TEST_ONLY")
    assert first["hypothesis"]["tri_value"]=="TRUE"
    assert first["open_world_candidate_proof"]==UNKNOWN
    second=inspect_requirement(b1,source_profile_git_blob=blob,
        identity=ident,observations=a[:1],origin="SYNTHETIC_TEST_ONLY")
    assert second["hypothesis"]["tri_value"]=="UNKNOWN"
    assert second["hypothesis"]["missing_field_keys"]==[
        "equipment.off_hand.weapon_type"]
    third=inspect_requirement(b1,source_profile_git_blob=blob,
        identity=ident,observations=[a[0],o("equipment.off_hand.weapon_type","NONE")],
        origin="SYNTHETIC_TEST_ONLY")
    assert third["hypothesis"]["tri_value"]=="FALSE"
    assert third["open_world_candidate_proof"]==UNKNOWN
    both_daggers=[o("equipment.main_hand.equipped",True),
                  o("equipment.off_hand.equipped",True),
                  o("equipment.main_hand.weapon_subclass","DAGGER"),
                  o("equipment.off_hand.weapon_subclass","DAGGER")]
    dagger_ok=inspect_requirement(b2,source_profile_git_blob=blob,
        identity=Identity("another-spec::unrelated-ability",h,100,3,0),
        observations=both_daggers,origin="SYNTHETIC_TEST_ONLY")
    assert dagger_ok["hypothesis"]["tri_value"]=="TRUE"
    assert dagger_ok["open_world_candidate_proof"]==UNKNOWN
    offhand_missing=inspect_requirement(b2,source_profile_git_blob=blob,
        identity=ident,observations=both_daggers[:2]+both_daggers[2:3],
        origin="SYNTHETIC_TEST_ONLY")
    assert offhand_missing["hypothesis"]["tri_value"]=="UNKNOWN"
    daggers_wrong=inspect_requirement(b2,source_profile_git_blob=blob,
        identity=ident,observations=both_daggers[:3]+[
            o("equipment.off_hand.weapon_subclass","SWORD")],
        origin="SYNTHETIC_TEST_ONLY")
    assert daggers_wrong["hypothesis"]["tri_value"]=="FALSE"
    assert daggers_wrong["open_world_candidate_proof"]==UNKNOWN
    # General conditional branches and compare arithmetic need no new
    # per-spec code.
    branch={"op":"any","children":[
        {"op":"all","children":[p("talent.path_a","eq",True),
                               p("resource.points","gte",5)]},
        {"op":"all","children":[p("talent.path_a","eq",False),
                               p("resource.points","gte",8)]}]}
    assert numeric_condition(branch,{"talent.path_a":o("talent.path_a",True),
        "resource.points":o("resource.points",7)})["tri_value"]=="TRUE"
    assert numeric_condition(branch,{"talent.path_a":o("talent.path_a",True),
        "resource.points":o("resource.points",2)})["tri_value"]=="FALSE"
    assert numeric_condition(branch,{"resource.points":o("resource.points",7)
                                     })["tri_value"]=="UNKNOWN"
    # Negative truth can be derived despite irrelevant missing data, but
    # still cannot be promoted from untrusted source declarations.
    assert numeric_condition(both_weapons,
        {"equipment.off_hand.weapon_type":o(
            "equipment.off_hand.weapon_type","NONE")})["tri_value"]=="FALSE"
    bad=[]
    for change in (
        lambda x:x.update(op="exec"),
        lambda x:x.update(children=[]),
        lambda x:x.update(children=[{"op":"compare","field":"bad",
                                    "cmp":"gt","value":"foo"}]),
    ):
        candidate=deepcopy(both_weapons)
        change(candidate)
        try:validate_expression(candidate)
        except ConditionalIRError:bad.append(True)
        else:raise AssertionError("FORGED_CONDITIONAL_IR_ACCEPTED")
    for samples,phase in (
        ([o("equipment.main_hand.weapon_type","SWORD",100,
            "WCL_STRICT_PRE")],"WCL_STRICT_PRE"),
        ([o("equipment.main_hand.weapon_type","SWORD",101,
            "SIMC_ORIGINAL_METHOD_PRE")],"SIMC_ORIGINAL_METHOD_PRE"),
        ([o("equipment.main_hand.weapon_type","SWORD")]*2,
         "SYNTHETIC_TEST_ONLY"),
    ):
        try:inspect_requirement(b1,source_profile_git_blob=blob,
                 identity=ident,observations=samples,origin=phase)
        except ConditionalIRError:bad.append(True)
        else:raise AssertionError("TEMPORAL_OR_DUPLICATE_FACT_ACCEPTED")
    assert len(bad)==6
    # Same-timestamp WCL forbidden; t-1 WCL allowed for *numeric*
    # hypotheses, never independent priority/READY without raw auth.
    wcl=inspect_requirement(b1,source_profile_git_blob=blob,
        identity=ident,origin="WCL_STRICT_PRE",
        observations=[o("equipment.main_hand.weapon_type","SWORD",99,
                        "WCL_STRICT_PRE"),
                      o("equipment.off_hand.weapon_type","DAGGER",95,
                        "WCL_STRICT_PRE")])
    assert wcl["hypothesis"]["tri_value"]=="TRUE"
    assert wcl["open_world_candidate_proof"]==UNKNOWN
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":20,"different_opaque_ability_names":True,
            "weapon_slot_subclass_conditions_declarative":True,
            "unverified_evidence_never_skips_or_selects_spells":True,
            "full_positive_READY":0,"WCL_API_calls":0}


if __name__=="__main__":
    print(json.dumps(selftest(),sort_keys=True))
