#!/usr/bin/env python3
"""Spec-neutral source-certified, *negative-only* Original METHOD-PRE guard evaluator.

External SpecAdapter supplies a typed guard declaration. The generic compiler
checks pinned official C++ method source AND an exact early-return-false branch.
At replay, raw observed Original METHOD-PRE booleans may prove that ONE
specific method invocation returns false; no positive return, complete
action READY, source-selection call pairing or priority is inferred.

Only one narrow source grammar is supported: a Boolean OR of audited
source-owned read operands, immediately followed by return false, with or
without enclosing braces. Unknown or nonmatching C++ fails closed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from general_rotation_original_pre_capture_engine_v1 import canonical, digest
from general_rotation_source_route_audit_v1 import (
    _bounded_body, _class_scope, _source_code_mask, git_blob,
    SourceRouteAuditError
)
from general_rotation_method_pre_passive_producer_v1 import (
    _validate_plan, MethodPREError
)

SCHEMA="ZrotGenericOriginalPRECertifiedNegativeGuardRulesV1"
PRE="SIMC_ORIGINAL_METHOD_PRE"
FALSE="METHOD_RETURN_FALSE_PROVEN"
UNKNOWN="UNKNOWN"


class FalseGuardError(ValueError):
    pass


def _atom(field:dict)->str:
    kind=field.get("original_pre_read_kind")
    operand=field.get("source_operand_literal")
    if field.get("value_kind")!="bool" or not isinstance(operand,str):
        raise FalseGuardError("BOOL_SOURCE_GUARD_OPERAND_REQUIRED")
    if kind=="bool_weapon_none":
        return operand+" == WEAPON_NONE"
    if kind=="bool_const_buff_check":
        return operand
    if kind=="bool_nonnull":
        return operand+" != nullptr"
    raise FalseGuardError("UNSUPPORTED_SOURCE_GUARD_OPERAND_RECIPE")


def compile_rules(source_root:Path, manifest:dict)->dict:
    """Prove source code has exactly the declared false-return branch."""
    try:
        sites=_validate_plan(manifest)
    except MethodPREError as e:
        raise FalseGuardError("INVALID_EXTERNAL_SOURCE_METHOD_PLAN") from e
    by_key={s["method_key"]:s for s in sites}
    rules=manifest.get("method_false_guard_rules")
    if (not isinstance(rules,list) or not rules or
        not isinstance(source_root,Path)):
        raise FalseGuardError("DECLARATIVE_FALSE_RETURN_RULES_REQUIRED")
    root=source_root.resolve(strict=True)
    checked=[]
    seen=set()
    for rule in rules:
        if not isinstance(rule,dict) or set(rule)!={
            "rule_id","method_key","raw_bool_fields","source_if_form"
        }:
            raise FalseGuardError("EXACT_RULE_DECLARATION_REQUIRED")
        rule_id=rule["rule_id"]
        key=rule["method_key"]
        fields=rule["raw_bool_fields"]
        form=rule["source_if_form"]
        if (not isinstance(rule_id,str) or
            not re.fullmatch(r"[a-z][a-z0-9_]*",rule_id) or
            rule_id in seen or key not in by_key or
            not isinstance(fields,list) or not fields or
            len(fields)!=len(set(fields)) or
            form not in ("DIRECT_FALSE","BRACED_FALSE")):
            raise FalseGuardError("INVALID_FALSE_BRANCH_RULE_OR_ID")
        seen.add(rule_id)
        site=by_key[key]
        raw_by_name={x["operand_name"]:x for x in site["fields"]}
        if any(name not in raw_by_name for name in fields):
            raise FalseGuardError("RULE_FIELD_NOT_IN_SOURCE_METHOD")
        expressions=[_atom(raw_by_name[name]) for name in fields]
        # Only OR is authorized for this first negative-only contract.
        # The exact token ordering and operators must match pinned C++.
        raw_expression=" || ".join(expressions)
        expression=re.sub(r"\s+","",raw_expression)
        if_source="if("+expression+")"
        suffix="{returnfalse;}" if form=="BRACED_FALSE" else "returnfalse;"
        witness=if_source+suffix
        file=(root/site["source_path"]).resolve(strict=True)
        if not file.is_relative_to(root) or not file.is_file():
            raise FalseGuardError("RULE_SOURCE_OUTSIDE_PINNED_TREE")
        data=file.read_bytes()
        if git_blob(data)!=site["source_git_blob_sha1"]:
            raise FalseGuardError("RULE_ORIGINAL_SOURCE_GIT_BLOB_DRIFT")
        original=data.decode("utf-8")
        mask=_source_code_mask(original)
        try:
            scope=_class_scope(original,mask,site["class_anchor"])
            body,_=_bounded_body(original,mask,site["signature"],scope)
        except SourceRouteAuditError as exc:
            raise FalseGuardError("RULE_SOURCE_METHOD_SCOPE_DRIFT") from exc
        if sha256(body.encode()).hexdigest()!=site["source_method_body_sha256"]:
            raise FalseGuardError("RULE_SOURCE_METHOD_BODY_DRIFT")
        clean=re.sub(r"\s+","",_source_code_mask(body))
        if clean.count(witness)!=1:
            raise FalseGuardError("SOURCE_FALSE_RETURN_BRANCH_NOT_CERTIFIED")
        checked.append({
            "rule_id":rule_id,"source_method_key":key,
            "field_names":fields,"logic":"ANY_TRUE",
            "source_if_form":form,
            "source_guard_false_witness_sha256":sha256(witness.encode()).hexdigest(),
            "source_git_blob_sha1":site["source_git_blob_sha1"],
            "source_method_body_sha256":site["source_method_body_sha256"],
            "source_phase":PRE,
            "independent_positive_method_ready_proven":False,
            "independent_action_ready_proven":False,
        })
    receipt={
        "schema":SCHEMA,
        "source_revision":manifest["pinned_source_commit"],
        "source_route_verification":"EXACT_PINNED_IF_RETURN_FALSE_ONLY",
        "source_rules":sorted(checked,key=lambda x:x["rule_id"]),
        "rule_count":len(checked),
        "source_virtual_dispatch_closed":False,
        "full_action_ready_certified":0,
        "WCL_API_calls":0,
    }
    receipt["ruleset_sha256"]=digest(receipt)
    return receipt


def verify_rules(receipt:dict,manifest:dict)->dict:
    if (not isinstance(receipt,dict) or receipt.get("schema")!=SCHEMA
        or not isinstance(manifest,dict)
        or receipt.get("source_revision")!=manifest.get("pinned_source_commit")
        or receipt.get("source_virtual_dispatch_closed") is not False
        or receipt.get("full_action_ready_certified")!=0):
        raise FalseGuardError("ORIGINAL_SOURCE_GUARD_RECEIPT_REQUIRED")
    raw=dict(receipt)
    supplied_hash=raw.pop("ruleset_sha256",None)
    if supplied_hash!=digest(raw):
        raise FalseGuardError("SOURCE_GUARD_RULESET_SHA_CHANGED")
    sites={s["method_key"]:s for s in _validate_plan(manifest)}
    rules=receipt.get("source_rules")
    defs=manifest.get("method_false_guard_rules")
    if (not isinstance(rules,list) or not isinstance(defs,list)
        or len(rules)!=len(defs) or receipt.get("rule_count")!=len(rules)
        or len({r["rule_id"] for r in rules})!=len(rules)):
        raise FalseGuardError("SOURCE_GUARD_RULESET_NOT_COMPLETE")
    defs_by_name={r["rule_id"]:r for r in defs}
    if len(defs_by_name)!=len(defs):
        raise FalseGuardError("DUPLICATE_SOURCE_RULE_DECLARATION")
    for rule in rules:
        defined=defs_by_name.get(rule["rule_id"])
        site=sites.get(rule["source_method_key"])
        if (not defined or not site or
            rule["source_method_key"]!=defined["method_key"] or
            rule["field_names"]!=defined["raw_bool_fields"] or
            rule["source_if_form"]!=defined["source_if_form"] or
            rule["source_method_body_sha256"]!=site["source_method_body_sha256"] or
            rule["source_git_blob_sha1"]!=site["source_git_blob_sha1"] or
            rule["source_phase"]!=PRE or rule["logic"]!="ANY_TRUE"):
            raise FalseGuardError("SOURCE_GUARD_RULE_IDENTITY_DRIFT")
    return {x["source_method_key"]:x for x in rules}


def assess_method_entry(entry:dict, by_method:dict)->dict:
    """One method invocation's guarded false or UNKNOWN, never action READY."""
    method=entry.get("source_method_key")
    r=by_method.get(method)
    if r is None:
        return {"source_method_key":method,
                "method_return_verdict":UNKNOWN,
                "reason":"NO_CERTIFIED_NEGATIVE_RULE_FOR_METHOD"}
    if (entry.get("capture_phase")!=PRE or
        entry.get("source_method_body_sha256")!=r["source_method_body_sha256"]
        or not isinstance(entry.get("raw_fields"),dict)):
        raise FalseGuardError("ORIGINAL_METHOD_PRE_IDENTITY_REQUIRED")
    raw=entry["raw_fields"]
    values=[raw.get(name) for name in r["field_names"]]
    if any(type(v) is not bool for v in values):
        raise FalseGuardError("CERTIFIED_GUARD_BOOLEAN_FACT_MISSING")
    return {
        "source_method_key":method,
        "source_guard_rule_id":r["rule_id"],
        "source_guard_false_witness_sha256":r["source_guard_false_witness_sha256"],
        "method_return_verdict":FALSE if any(values) else UNKNOWN,
        "reason":"SOURCE_EARLY_RETURN_FALSE_TRIGGERED" if any(values) else
                 "OTHER_GUARDS_AND_DELEGATES_UNRESOLVED",
        "actual_action_READY":"UNKNOWN",
        "source_order_complete":False,
    }


def selftest()->dict:
    # The source compiler has its own actual-official-checkout CI route.
    # Test the independent evaluator without inventing executable inputs.
    known={
        "source_method_key":"example_method",
        "source_method_body_sha256":"a"*64,
        "field_names":["weapon_a_missing","weapon_b_missing"],
        "rule_id":"no_weapons",
        "source_guard_false_witness_sha256":"b"*64
    }
    entry={
        "source_method_key":"example_method",
        "source_method_body_sha256":"a"*64,
        "capture_phase":PRE,
        "raw_fields":{"weapon_a_missing":True,"weapon_b_missing":False}
    }
    bad=assess_method_entry(entry,{"example_method":known})
    assert bad["method_return_verdict"]==FALSE
    assert bad["actual_action_READY"]=="UNKNOWN"
    for pair in ((False,True),(True,True)):
        e=dict(entry,raw_fields=dict(zip(known["field_names"],pair)))
        assert assess_method_entry(e,{"example_method":known})[
            "method_return_verdict"]==FALSE
    negative_free=dict(entry,raw_fields={
        "weapon_a_missing":False,"weapon_b_missing":False})
    assert assess_method_entry(negative_free,{"example_method":known})[
        "method_return_verdict"]==UNKNOWN
    assert assess_method_entry(entry,{})["method_return_verdict"]==UNKNOWN
    for wrong in (
        dict(entry,source_method_body_sha256="f"*64),
        dict(entry,capture_phase="SIMC_SELECT_ACTION_PRE"),
        dict(entry,raw_fields={"weapon_a_missing":1,"weapon_b_missing":False}),
        dict(entry,raw_fields={"weapon_a_missing":True}),
    ):
        try:assess_method_entry(wrong,{"example_method":known})
        except FalseGuardError:pass
        else:raise AssertionError("UNTRUSTED_OR_NONPRE_METHOD_FACT_ACCEPTED")
    return {
        "schema":SCHEMA, "status":"PASS_OFFLINE_SYNTHETIC",
        "synthetic_negative_guard_checks":9,
        "actual_original_source_compiled":False,
        "positive_action_READY_certified":0,"WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--source-templates",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.simc_root is None and a.source_templates is None:
        result=selftest()
    elif a.simc_root is not None and a.source_templates is not None:
        manifest=json.loads(a.source_templates.read_bytes())
        result=compile_rules(a.simc_root,manifest)
    else:p.error("--simc-root and --source-templates required together")
    data=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(data)
    else:
        print(data.decode(),end="")


if __name__=="__main__":
    main()
