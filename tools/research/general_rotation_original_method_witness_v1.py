#!/usr/bin/env python3
"""Generic exact-action original-method witness: no spec or spell semantics.

The source adapter provides an exact method marker, source-bound rule,
field names and original PRE field-index mappings. The bridge pairs:

  source row PRE -> original action_t* -> ORIGINAL override entry ->
  original a->action_ready() attempt (POST comparator only).

The bridge evaluates bounded declarative necessary gates. Every absence,
ambiguous witness, wrong object, timestamp or field discrepancy is UNKNOWN
(or an explicit transport error), never assumed eligible. A trusted Fact is
emitted only on an authenticated original-source route *after* source bytes,
fresh run and pristine/instrumented parity are independently validated
by the calling CI verifier. External adapter JSON is never such authority.

NOT_READY is only a scoped necessary-negative; positive READY requires
full dynamic route closure and is intentionally never produced here.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, replace
from hashlib import sha256
import json
import re
from typing import Any, Iterable

from general_rotation_decision_proof_engine_v1 import (
    Fact, GateContract, Identity, decide_candidate, NOT_READY, UNKNOWN
)
from general_rotation_condition_ir_v1 import (
    SourceBoundRequirement, ObservedField, numeric_condition,
    validate_expression
)
from general_rotation_original_pre_field_transport_v1 import (
    FieldRequest, parse_marker, parse_attempt
)

SCHEMA="ZrotGenericExactActionMethodWitnessV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
POINTER_MARK="ZROT_GR_EXACT_ACTION_POINTER_PRE_V1|"
ADDRESS=re.compile(r"^0x[0-9a-fA-F]+$")
REQUIRED_OPEN=("BASE_VIRTUAL_COMPLETE","CAST_GCD","MOVEMENT","SPEC_OVERRIDE_TOTAL")


class MethodWitnessError(ValueError): pass


def require(ok:bool,why:str)->None:
    if not ok: raise MethodWitnessError(why)


@dataclass(frozen=True)
class MethodMarker:
    """SpecAdapter-owned method-event schema, not a global spell registry."""
    prefix:str
    method_key:str
    fields:tuple[str,...]
    raw_kind:str="bool01"

    def __post_init__(self):
        require(
            isinstance(self.prefix,str) and self.prefix.startswith("ZROT_")
            and self.prefix.endswith("|") and "|" not in self.prefix[:-1]
            and isinstance(self.method_key,str) and self.method_key
            and len(self.fields)>0 and len(set(self.fields))==len(self.fields)
            and len(self.fields)<=12 and self.raw_kind in ("bool01","stack_nonnegative"),
            "INVALID_SOURCE_METHOD_WITNESS_DECLARATION"
        )


def extend_player_pointer(already_generic:bytes)->bytes:
    """Passive same-action pointer marker before the single original call.

    This is common to EVERY specialization. A SpecAdapter must not
    duplicate this C++ producer or ask for another action_ready().
    """
    from general_rotation_original_pre_field_transport_v1 import (
        MARK as GENERIC_PRE_MARK,ORIGINAL_CALL)
    src=already_generic.decode("utf-8")
    require(GENERIC_PRE_MARK in src and POINTER_MARK not in src and
            src.count(ORIGINAL_CALL)==1 and
            src.index(GENERIC_PRE_MARK)<src.index(ORIGINAL_CALL),
            "GENERIC_PRE_FIELD_MARKER_REQUIRED")
    code=(
        "    // Same-process action_t* for exact source PRE guard matching.\n"
        "    if ( sim->log && !is_pet() && !is_enemy() )\n"
        '      sim->print_log( "'+POINTER_MARK+'{}|{}|{}",\n'
        "        sim->current_time().total_millis(), a->name_str,\n"
        "        static_cast<const void*>( a ) );\n"
    )
    out=src.replace(ORIGINAL_CALL,code+ORIGINAL_CALL,1)
    require(out.count("a->action_ready()")==src.count("a->action_ready()") and
            out.count(ORIGINAL_CALL)==1 and out.count(POINTER_MARK)==1 and
            out.index(GENERIC_PRE_MARK)<out.index(POINTER_MARK)<
                out.index(ORIGINAL_CALL),
            "SOURCE_READY_CALL_OR_POINTER_ORDER_CHANGED")
    return out.encode("utf-8")


def parse_pointer(line:str)->dict|None:
    pos=line.find(POINTER_MARK)
    if pos<0:return None
    p=line[pos:].strip().split("|")
    require(len(p)==4,"SOURCE_POINTER_FORMAT_INVALID")
    try:t=int(p[1])
    except ValueError as e:raise MethodWitnessError("SOURCE_POINTER_TIME_INVALID") from e
    require(t>=0 and p[2] and ADDRESS.fullmatch(p[3]) is not None,
            "SOURCE_POINTER_ADDRESS_INVALID")
    return {"time_ms":t,"action_name":p[2],"pointer":p[3].lower()}


def parse_method(line:str, declarations:tuple[MethodMarker,...])->dict|None:
    # Several source-method override guards may share one producer prefix.
    prefixes={d.prefix for d in declarations if d.prefix in line}
    require(len(prefixes)<=1,"MULTIPLE_OR_AMBIGUOUS_METHOD_MARKERS")
    if not prefixes:return None
    prefix=next(iter(prefixes))
    p=line[line.find(prefix):].strip().split("|")
    require(len(p)>=6,"METHOD_MARKER_FIELD_COUNT_DRIFT")
    matching=[d for d in declarations
              if d.prefix==prefix and d.method_key==p[2]]
    require(len(matching)==1,"UNKNOWN_OR_DUPLICATE_METHOD_IDENTITY")
    d=matching[0]
    require(len(p)==5+len(d.fields),"METHOD_MARKER_FIELD_COUNT_DRIFT")
    try:
        t=int(p[1])
        values=[int(x) for x in p[5:]]
    except ValueError as e:raise MethodWitnessError("METHOD_RAW_PRE_NOT_INTEGER") from e
    require(t>=0 and p[2]==d.method_key and p[3] and
            ADDRESS.fullmatch(p[4]) is not None,
            "METHOD_NAME_OR_POINTER_INVALID")
    if d.raw_kind=="bool01":
        require(all(x in (0,1) for x in values),
                "METHOD_BOOLEAN_NOT_EXPLICIT")
        normalized=[bool(x) for x in values]
    else:
        require(all(x>=0 for x in values),"METHOD_STACK_NEGATIVE")
        normalized=[bool(x) for x in values]
    return {"time_ms":t,"method_key":d.method_key,
            "action_name":p[3],"pointer":p[4].lower(),
            "field_values":dict(zip(d.fields,normalized)),
            "raw_values":dict(zip(d.fields,values))}


def pair_original_attempts(trace:str,*,fields:tuple[FieldRequest,...],
                           method_markers:tuple[MethodMarker,...])->dict:
    require(0<len(fields)<=12 and len(method_markers)>0,
            "METHOD_WITNESS_NEEDS_BOUNDED_SOURCE_FIELDS")
    require(len(set((d.prefix,d.method_key) for d in method_markers))
            ==len(method_markers),"METHOD_WITNESS_METHOD_KEY_NOT_UNIQUE")
    pending=None;rows=[];unattributed=0;calls=0
    for line in trace.splitlines():
        raw=parse_marker(line,fields)
        if raw is not None:
            require(pending is None,"UNPAIRED_PRE_OR_NESTED_ATTEMPT")
            pending={"raw":raw,"pointer":None,"guards":[]}
            continue
        ptr=parse_pointer(line)
        if ptr is not None:
            require(pending is not None and pending["pointer"] is None and
                    ptr["time_ms"]==pending["raw"]["time_ms"] and
                    ptr["action_name"]==pending["raw"]["native_action_name"],
                    "ACTION_POINTER_NOT_BOUND_TO_EXACT_PRE")
            pending["pointer"]=ptr["pointer"]
            continue
        guard=parse_method(line,method_markers)
        if guard is not None:
            if pending is None:unattributed+=1
            else:pending["guards"].append(guard)
            continue
        attempt=parse_attempt(line)
        if attempt is None:continue
        calls+=1
        require(pending is not None and pending["pointer"] is not None and
                all(attempt[k]==pending["raw"][k] for k in
                    ("time_ms","source_list","ordinal_1based",
                     "native_action_name")),
                "ORIGINAL_NATIVE_ATTEMPT_AND_PRE_DISAGREE")
        witnesses={}
        for d in method_markers:
            matched=[
                g for g in pending["guards"]
                if g["method_key"]==d.method_key and
                   g["time_ms"]==pending["raw"]["time_ms"] and
                   g["action_name"]==pending["raw"]["native_action_name"] and
                   g["pointer"]==pending["pointer"]
            ]
            require(len(matched)<=1,"DUPLICATE_EXACT_ACTION_METHOD_GUARD")
            if matched:witnesses[d.method_key]=matched[0]
        rows.append({"raw":pending["raw"],"pointer":pending["pointer"],
                     "witnesses":witnesses,
                     "nonmatching_method_events":len(pending["guards"])-len(witnesses),
                     "native_return_is_POST_comparator_only":True})
        pending=None
    require(calls>0 and pending is None and len(rows)==calls,
            "TRUNCATED_OR_EMPTY_ORIGINAL_ATTEMPT_TRACE")
    return {"rows":rows,"original_native_attempts":calls,
            "unattributed_method_events":unattributed}


def evaluate_bound_cases(*,rows:list[dict],fields:tuple[FieldRequest,...],
                         source_rules:list[tuple[SourceBoundRequirement,Identity,str]],
                         receipt_sha256:dict[str,str],source_verified:bool=False)->dict:
    """Accept source_verified=True ONLY after a pinned original CI replay.

    The public function is not an authentication authority: code owners must
    check original C++/profile bytes, same-process action pointer and parity
    externally. Default False forbids any independent Fact or NOT_READY.
    """
    require(all(len(v)==64 and all(c in "0123456789abcdef" for c in v)
                for v in receipt_sha256.values())
            and set(receipt_sha256)=={"raw_log","patch","parity"},
            "SOURCE_EVIDENCE_THREE_RECEIPT_DIGESTS_REQUIRED")
    keys=[f.key for f in fields]
    require(len(keys)==len(set(keys)),"PRE_RAW_FIELD_KEYS_DUPLICATED")
    out=[];counts=Counter()
    for rule,base,method_key in source_rules:
        owner,action=base.scope.split("::",1)
        scoped=[r for r in rows if
                r["raw"]["source_list"]==owner and
                r["raw"]["ordinal_1based"]==base.ordinal+1 and
                r["raw"]["native_action_name"]==action]
        examples=[];statuses=Counter();occurrences=Counter()
        req=validate_expression(rule.expression)["required_fields"]
        require(set(req)<=set(keys),"SOURCE_RULE_MISSING_CAPTURED_FIELDS")
        for row in scoped:
            raw=row["raw"];t=raw["time_ms"]
            occurrence=occurrences[t];occurrences[t]+=1
            method=row["witnesses"].get(method_key)
            if method is None:
                statuses["UNKNOWN_NO_ORIGINAL_OVERRIDE_ENTRY"]+=1
                continue
            captured=dict(zip(keys,raw["values"]))
            # Original method has to re-read or evaluate the same underlying
            # source fields and exactly agree with the prior PRE snapshot.
            require(set(req)<=set(method["field_values"]),
                    "ORIGINAL_METHOD_DOES_NOT_WITNESS_NEEDED_SOURCE_FIELDS")
            local={}
            for k in req:
                value=captured[k]
                if value==-1:
                    raise MethodWitnessError("CAPTURE_MISSING_BUT_OVERRIDE_HAS_VALUE")
                require(value in (0,1) and method["field_values"][k]==bool(value),
                        "SAME_ACTION_PRE_VS_ORIGINAL_OVERRIDE_VALUE_CONFLICT")
                local[k]=ObservedField(k,bool(value),t,
                    "SIMC_ORIGINAL_METHOD_PRE",
                    "source-original-"+receipt_sha256["raw_log"])
            numeric=numeric_condition(rule.expression,local)
            require(numeric["tri_value"] in ("TRUE","FALSE"),
                    "NECESSARY_GUARD_NOT_DETERMINISTIC")
            predicate=numeric["tri_value"]=="TRUE"
            ident=replace(base,t_ms=t,occurrence=occurrence)
            proof=None
            decision=UNKNOWN
            if source_verified:
                proof=Fact(
                    identity=ident,gate=rule.gate,value=predicate,
                    basis="INDEPENDENT_SOURCE_REPLAY",
                    captured="SIMC_ORIGINAL_METHOD_PRE",
                    event_t_ms=t,
                    receipt="|".join(k+":"+v for k,v in sorted(receipt_sha256.items())))
                contract=GateContract(
                    "ACTUAL_ORIGINAL_METHOD_ENTRY_SCOPED_NECESSARY_ONLY",
                    (rule.gate,)+REQUIRED_OPEN,ident.source_sha256,
                    closed=False)
                report=decide_candidate(
                    ident,contract,(proof,),is_physical_action=True)
                decision=report["decision"]
                require(decision==(UNKNOWN if predicate else NOT_READY)
                        and report["dummy_error_permitted"] is False,
                        "OPEN_WORLD_NEGATIVE_SCOPE_PROOF_DRIFT")
            statuses[decision]+=1
            if len(examples)<3:
                examples.append({"t_ms":t,"occurrence":occurrence,
                    "source_method":method_key,
                    "fields":{k:method["raw_values"][k] for k in req},
                    "necessary_condition":numeric["tri_value"],
                    "candidate":decision,
                    "source_method_pointer_equal":True,
                    "full_READY":False})
        counts["scoped_NOT_READY"]+=statuses[NOT_READY]
        counts["UNKNOWN"]+=statuses[UNKNOWN]+statuses[
            "UNKNOWN_NO_ORIGINAL_OVERRIDE_ENTRY"]
        counts["method_witnesses"]+=sum(statuses.values())-statuses[
            "UNKNOWN_NO_ORIGINAL_OVERRIDE_ENTRY"]
        out.append({"source_action":action,"source_row_sha256":base.source_sha256,
                    "source_rule_id":rule.stable_rule_id,"method_key":method_key,
                    "source_rows_attempted":len(scoped),
                    "matched_method_count":sum(statuses.values())-statuses[
                        "UNKNOWN_NO_ORIGINAL_OVERRIDE_ENTRY"],
                    "status_distribution":dict(sorted(statuses.items())),
                    "examples":examples,"full_positive_READY":0})
    return {"schema":SCHEMA,"policy_id":POLICY,
            "source_authenticated_for_this_call":source_verified,
            "counts":dict(counts),"candidate_proofs":out,
            "full_positive_READY":0,"WCL_STRICT_PRE_used":False,
            "dummy_practice_error_permitted":False}


def selftest()->dict:
    from general_rotation_condition_ir_v1 import SourceBoundRequirement
    from general_rotation_original_pre_field_transport_v1 import FieldRequest,MARK
    def rule(name,expr,row):
        return SourceBoundRequirement(name,"a"*40,row,"engine/class_modules/synthetic.cpp",
            "b"*40,"c"*64,"necessary_eligibility",expr)
    eq=lambda key,value:{"op":"compare","field":key,"cmp":"eq","value":value}
    fields=(
        FieldRequest("equipment.main_hand.equipped","actor_weapon_slot_equipped","main_hand"),
        FieldRequest("equipment.off_hand.equipped","actor_weapon_slot_equipped","off_hand"),
        FieldRequest("buff.example.active","actor_named_buff_active","example"),
    )
    m1=MethodMarker("ZROT_DEMO|","cast_override_v2",("buff.example.active",))
    m2=MethodMarker("ZROT_DEMO|","opaque_weapon",
                     ("equipment.main_hand.equipped","equipment.off_hand.equipped"))
    def row(time,source,ordinal,action,ptr,method,values,gate):
        a=MARK+f"{time}|{source}|{ordinal}|{action}|"+ "|".join(str(x) for x in values)
        b=POINTER_MARK+f"{time}|{action}|{ptr}"
        c=method.prefix+f"{time}|{method.method_key}|{action}|{ptr}|"+ "|".join(str(x) for x in gate)
        d=f"ZROT_NATIVE_SELECT_V1|ATTEMPT|{time}|{source}|{source}|{ordinal}|{action}|0"
        return "\n".join((a,b,c,d))
    from general_rotation_original_pre_field_transport_v1 import (
        MARK as SOURCE_MARK,ORIGINAL_CALL)
    mock=("PRE\n"+SOURCE_MARK+"{}|{}|{}|{}|{}|{}|{}\n"+
          ORIGINAL_CALL+"\nPOST").encode()
    placed=extend_player_pointer(mock).decode()
    assert placed.index(SOURCE_MARK)<placed.index(POINTER_MARK)<placed.index(ORIGINAL_CALL)
    assert placed.count("a->action_ready()")==1
    raw="\n".join((
        row(10,"spells",1,"opaque_cast","0x100",m1,(1,0,0),(0,)),
        row(10,"weapon",1,"opaque_weapon","0x200",m2,(1,0,0),(1,0))))
    parsed=pair_original_attempts(raw,fields=fields,method_markers=(m1,m2))
    assert parsed["original_native_attempts"]==2
    assert parsed["rows"][0]["witnesses"].get("cast_override_v2") is not None
    cast_rule=rule("buff.required",eq("buff.example.active",True),"d"*64)
    weapon_rule=rule("two.equipped",{"op":"all","children":[
        eq("equipment.main_hand.equipped",True),
        eq("equipment.off_hand.equipped",True)]},"e"*64)
    source_rules=[
        (cast_rule,Identity("spells::opaque_cast","d"*64,10,0,0),"cast_override_v2"),
        (weapon_rule,Identity("weapon::opaque_weapon","e"*64,10,0,0),"opaque_weapon"),
    ]
    hashes={"raw_log":"1"*64,"patch":"2"*64,"parity":"3"*64}
    default=evaluate_bound_cases(rows=parsed["rows"],fields=fields,
        source_rules=source_rules,receipt_sha256=hashes)
    assert default["counts"]["scoped_NOT_READY"]==0
    assert default["counts"]["UNKNOWN"]==2
    authenticated=evaluate_bound_cases(rows=parsed["rows"],fields=fields,
        source_rules=source_rules,receipt_sha256=hashes,source_verified=True)
    assert authenticated["counts"]["scoped_NOT_READY"]==2
    assert authenticated["counts"]["method_witnesses"]==2
    assert authenticated["full_positive_READY"]==0
    # Same time, different pointers: one can never steal the other guard.
    damaged=raw.replace("ZROT_DEMO|10|opaque_weapon|opaque_weapon|0x200",
                         "ZROT_DEMO|10|opaque_weapon|opaque_weapon|0x100")
    unlinked=pair_original_attempts(damaged,fields=fields,method_markers=(m1,m2))
    checked=evaluate_bound_cases(rows=unlinked["rows"],fields=fields,
        source_rules=source_rules,receipt_sha256=hashes,source_verified=True)
    assert checked["counts"]["scoped_NOT_READY"]==1
    assert checked["counts"]["UNKNOWN"]==1
    # Mismatching actual raw source state and method guard must fail closed.
    wrong=raw.replace("ZROT_DEMO|10|opaque_weapon|opaque_weapon|0x200|1|0",
                      "ZROT_DEMO|10|opaque_weapon|opaque_weapon|0x200|1|1")
    try:
        bad=pair_original_attempts(wrong,fields=fields,method_markers=(m1,m2))
        evaluate_bound_cases(rows=bad["rows"],fields=fields,
            source_rules=source_rules,receipt_sha256=hashes,source_verified=True)
    except MethodWitnessError:pass
    else:raise AssertionError("INCONSISTENT_ORIGINAL_METHOD_FIELD_ACCEPTED")
    # Unobserved source row stays UNKNOWN.
    absent=evaluate_bound_cases(rows=[],fields=fields,
        source_rules=source_rules,receipt_sha256=hashes,source_verified=True)
    assert absent["counts"]["scoped_NOT_READY"]==0
    # Invalid method identity is rejected even when the envelope is shared.
    unrecognized=raw.replace("ZROT_DEMO|10|opaque_cast|",
                             "ZROT_DEMO|10|foreign_method|")
    try:pair_original_attempts(
        unrecognized,fields=fields,method_markers=(m1,m2))
    except MethodWitnessError:pass
    else:raise AssertionError("UNDECLARED_SOURCE_METHOD_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":25,"different_source_method_adapters":2,
            "same_timestamp_cross_action_guard_theft":False,
            "unverified_external_json_can_certify_NOT_READY":False,
            "real_native_CXX_executed":False,"full_positive_READY":0,
            "WCL_API_calls":0}


if __name__=="__main__":
    print(json.dumps(selftest(),sort_keys=True))
