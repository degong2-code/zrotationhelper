#!/usr/bin/env python3
"""Source APL -> producer/semantic/readiness observability reconciliation.

This report is intentionally *not* a binding, replay or a game recommendation.
It consumes real pinned source APL requirement and semantic-route contracts.
Native source trace currently exposes partial resource current/max only;
source grammar similarity is NOT mechanic identity and cannot certify that any
SimC operand equals that trace feature, nor that an action is ready.

No specialization, ability, boss, target or priority semantics hardcoded.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import hashlib
import re
from pathlib import Path
from typing import Mapping, Any

from simc_apl_observability_contract import _SCHEMA as OBS_SCHEMA
from simc_apl_semantic_resolver import _SCHEMA as ROUTE_SCHEMA, compile_semantic_route_plan
from simc_apl_readiness_provider import MANDATORY

_SCHEMA="ZrotNativeResourceAplObservabilityGapAuditV1"
_RESOURCE_FAMILY="RESOURCE_QUERY"
_REMAINING="NO_VERIFIED_NATIVE_FEATURE_PRODUCER_FOR_GRAMMAR"
_RESOURCE="NATIVE_PARTIAL_CURRENT_MAX_PRODUCER_EXISTS_SEMANTIC_UNBOUND"
_SOURCE_LABEL="PINNED_SIMC_RESOURCE_LABEL_CANDIDATE_NOT_EXPRESSION_PROOF"
_START="const char* util::resource_type_string( resource_e resource_type )"
_END="const char* util::resource_type_abbrev( resource_e resource_type )"
_PIN="710c2408bfd3ae4df71b8cd55cdf01f63fd6c926"


def source_resource_labels(raw:bytes,*,source_sha256:str,upstream_sha:str)->dict:
    """Only resource label inventory from official pinned util.cpp source.

    The source of a lexical resource label alone is NOT proof that player_t or
    any class expression resolves a similarly named APL operand to that
    resource, nor that a Native observer covers the operand semantics.
    """
    if upstream_sha!=_PIN or not isinstance(raw,bytes) or not 0<len(raw)<300000:
        raise ValueError("RESOURCE_LABEL_UNPINNED_SOURCE_OR_SIZE")
    if hashlib.sha256(raw).hexdigest()!=source_sha256:
        raise ValueError("RESOURCE_LABEL_SOURCE_SHA_MISMATCH")
    try:source=raw.decode("utf-8")
    except UnicodeDecodeError as e:raise ValueError("RESOURCE_LABEL_NOT_UTF8") from e
    if source.count(_START)!=1 or source.count(_END)!=1:
        raise ValueError("RESOURCE_LABEL_SOURCE_FUNCTION_ANCHOR")
    chunk=source.split(_START,1)[1].split(_END,1)[0]
    cases=re.findall(
        r'case\s+RESOURCE_([A-Z_]+):\s*return\s+"([a-z_]+)";',chunk)
    if len(cases)<5 or len(cases)!=len(set(cases)):
        raise ValueError("RESOURCE_LABEL_SOURCE_CASES_UNSAFE")
    labels={}
    for enum,label in cases:
        if enum=="NONE":continue
        if enum in labels or not label or label in labels.values():
            raise ValueError("RESOURCE_LABEL_DUPLICATE_ENUM_OR_TOKEN")
        labels[enum]=label
    if "resource_type_string>( name )" not in source:
        raise ValueError("RESOURCE_LABEL_PARSE_TYPE_LINK_UNVERIFIED")
    return {"upstream_sha":upstream_sha,"source_sha256":source_sha256,
            "resource_label_names":sorted(labels.values()),
            "resource_enum_to_label":dict(sorted(labels.items())),
            "source_label_only_no_expression_equivalence":True}



def audit_requirements(requirements:Mapping[str,Any],routes:Mapping[str,Any],
                       *,source_resource_inventory:dict|None=None)->dict:
    """Fail closed on forged route/requirements or strengthened claim status."""
    if not isinstance(requirements,dict) or requirements.get("schema")!=OBS_SCHEMA:
        raise ValueError("GAP_AUDIT_REQUIRES_SOURCE_OBSERVABILITY_CONTRACT")
    if not isinstance(routes,dict) or routes.get("schema")!=ROUTE_SCHEMA:
        raise ValueError("GAP_AUDIT_REQUIRES_SEMANTIC_ROUTE_PLAN")
    expected=compile_semantic_route_plan(requirements)
    if routes!=expected:
        raise ValueError("GAP_AUDIT_ROUTE_NOT_CANONICAL_SOURCE_RECOMPILATION")
    if requirements.get("actual_strict_pre_observation")!="NOT_RUN" or (
        requirements.get("gameplay_rule_promotion") is not False or
        routes.get("gameplay_rule_promotion") is not False or
        routes.get("semantic_authority")!="NOT_ESTABLISHED"):
        raise ValueError("GAP_AUDIT_UNVERIFIED_INPUT_CLAIM")
    if requirements.get("no_implicit_operand_identity_mapping") is not True or (
        requirements.get("no_implicit_readiness_or_ability_id") is not True):
        raise ValueError("GAP_AUDIT_UNVERIFIED_IDENTITY_POLICY")
    original_req={r["operand"]:r for r in requirements["required_state_operands"]}
    if len(original_req)!=requirements["operand_requirement_count"]:
        raise ValueError("GAP_AUDIT_OPERAND_COUNT_IDENTITY")
    labels=set()
    if source_resource_inventory is not None:
        if source_resource_inventory.get("upstream_sha")!=_PIN or not (
            source_resource_inventory.get("source_label_only_no_expression_equivalence") is True):
            raise ValueError("GAP_AUDIT_RESOURCE_LABEL_PROVENANCE_REQUIRED")
        labels=set(source_resource_inventory.get("resource_label_names",[]))
        if not labels or len(labels)!=len(source_resource_inventory["resource_label_names"]):
            raise ValueError("GAP_AUDIT_INVALID_PINNED_RESOURCE_LABELS")
    rows=[]
    cats=Counter()
    grammar=Counter()
    for operand in routes["operands"]:
        name=operand["operand"]
        req=original_req.get(name)
        if req is None or req.get("semantic_binding")!="UNBOUND" or (
            req.get("strict_pre_observation")!="UNKNOWN" or
            operand.get("identity")!="UNKNOWN" or
            operand.get("observation_feature") is not None):
            raise ValueError("GAP_AUDIT_OPERAND_PREMATURE_CERTIFICATION")
        if req["source_references"]!=operand["source_references"]:
            raise ValueError("GAP_AUDIT_LOST_APL_SOURCE_REFERENCES")
        if not req["source_references"]:
            raise ValueError("GAP_AUDIT_SOURCE_REFERENCES_REQUIRED")
        family=operand["grammar_family"]
        candidate=family==_RESOURCE_FAMILY
        bare_label=(family=="UNKNOWN_NAMESPACE" and "." not in name and name in labels)
        gate=_RESOURCE if candidate else (_SOURCE_LABEL if bare_label else _REMAINING)
        cats[gate]+=1
        grammar[family]+=1
        rows.append({
            "operand":name,"grammar_family":family,
            "source_references":req["source_references"],
            "producer_path_status":gate,
            "native_resource_family_candidate_only":candidate,
            "upstream_resource_label_collision_candidate":bare_label,
            "resource_label_provenance":"PINNED_UTIL_SOURCE_LABEL_ONLY" if bare_label else "NO_LABEL_SOURCE_MATCH",
            "native_operand_feature_binding":None,
            "verified_resource_type":None,
            "verified_derived_expression_semantics":False,
            "source_epoch_strict_pre_at_decision":"NOT_EVALUATED",
            "decision_observation":"UNKNOWN",
            "mechanic_identity":"UNKNOWN",
            "could_be_used_for_priority_trace":False,
        })
    if len(rows)!=routes["operand_count"] or (
        sum(cats.values())!=requirements["operand_requirement_count"]):
        raise ValueError("GAP_AUDIT_SOURCE_OPERAND_LOSS")
    if dict(sorted(grammar.items()))!=routes["grammar_family_counts"]:
        # The grammar classifier, not the researcher, owns these categories.
        # Route compiler omits zero-count keys and UNKNOWN from the summary
        # only if no matching operands exist.
        raise ValueError("GAP_AUDIT_GRAMMAR_DISTRIBUTION_DRIFT")
    actions=[]
    for ready in requirements["required_action_readiness"]:
        if ready.get("status")!="UNKNOWN" or (
            ready.get("ability_identity")!="UNKNOWN" or
            ready.get("requirements_policy")!="NOT_SUPPLIED" or
            tuple(ready.get("required_dimensions",()))!=tuple(MANDATORY)):
            raise ValueError("GAP_AUDIT_READINESS_PREMATURE_CERTIFICATION")
        if not ready.get("source_references"):
            raise ValueError("GAP_AUDIT_READINESS_SOURCE_REFERENCES_REQUIRED")
        actions.append({
            "action_token":ready["action_token"],
            "source_references":ready["source_references"],
            "unverified_dimensions":list(MANDATORY),
            "native_readiness_policy":"NOT_PRESENT",
            "source_action_identity":"UNKNOWN",
            "ready":"UNKNOWN",
            "cannot_be_skipped_as_unavailable":True,
        })
    if len(actions)!=routes["action_token_count"] or (
        len(actions)!=requirements["readiness_requirement_count"]):
        raise ValueError("GAP_AUDIT_LOST_ACTION_REQUIREMENTS")
    return {
        "schema":_SCHEMA,
        "spec":requirements["spec"],
        "source_apl_sha256":requirements["source_apl_sha256"],
        "source_profile_sha256":requirements["source_profile_sha256"],
        "source_simc_executable_sha256":requirements["source_simc_executable_sha256"],
        "source_row_count":requirements["source_row_count"],
        "source_operands":rows,
        "required_action_readiness":actions,
        "source_operand_count":len(rows),
        "native_resource_grammar_candidates_not_bindings":cats[_RESOURCE],
        "pinned_resource_label_collision_candidates_not_bindings":cats[_SOURCE_LABEL],
        "resource_label_registry_source_sha256":(
            source_resource_inventory["source_sha256"]
            if source_resource_inventory is not None else None),
        "other_operand_producer_semantics_unverified":cats[_REMAINING],
        "all_action_tokens_unverified":len(actions),
        "all_readiness_dimensions_unverified":len(actions)*len(MANDATORY),
        "native_observation_producer_scope":
            "SOURCE_VERIFIED_PARTIAL_CURRENT_MAX_ONLY_NO_APL_OPERAND_BINDING",
        "native_resource_value_present_for_any_specific_operand":False,
        "native_resource_type_identity_independently_verified":False,
        "native_epoch_state_input":"NOT_CONNECTED_TO_THIS_SOURCE_APL",
        "strict_pre_replay":"NOT_RUN",
        "simc_foreground_priority_parity":"NOT_VALIDATED",
        "wcl_blind_candidate_discovery":"NOT_RUN",
        "missing_readiness_is_not_not_ready":True,
        "gameplay_rule_promotion":False,
    }


def selftest():
    from simc_apl_source_engine import ingest_actions
    from simc_apl_conditional_ir import compile_structural_ir
    from simc_apl_observability_contract import compile_requirements
    import copy
    for spec,name in (("enhancement","alpha"),("unholy","gamma"),
                      ("heldout_spec","omega")):
        src=(f"spec={spec}\nactions={name},if=resource.mana>20&buff.foo.up\n"
             "actions+=/other,if=cooldown.alpha.ready|rage>40\n"
             "actions+=/third\n").encode()
        req=compile_requirements(compile_structural_ir(
            ingest_actions(src,expected_spec=spec)))
        route=compile_semantic_route_plan(req)
        out=audit_requirements(req,route)
        assert out["source_operand_count"]==4
        assert out["native_resource_grammar_candidates_not_bindings"]==1
        assert out["other_operand_producer_semantics_unverified"]==3
        assert out["all_action_tokens_unverified"]==3
        assert out["all_readiness_dimensions_unverified"]==3*len(MANDATORY)
        assert not out["native_resource_value_present_for_any_specific_operand"]
        assert all(x["decision_observation"]=="UNKNOWN" for x in out["source_operands"])
        assert all(x["ready"]=="UNKNOWN" for x in out["required_action_readiness"])
        assert not out["gameplay_rule_promotion"]
        util_source=(f"{_START}\n"
                     "case RESOURCE_NONE: return \"none\";\n"
                     "case RESOURCE_MANA: return \"mana\";\n"
                     "case RESOURCE_RAGE: return \"rage\";\n"
                     "case RESOURCE_FURY: return \"fury\";\n"
                     "case RESOURCE_RUNIC_POWER: return \"runic_power\";\n"
                     "case RESOURCE_ENERGY: return \"energy\";\n"
                     f"{_END}\n"
                     "return parse_enum<resource_e, RESOURCE_NONE, RESOURCE_MAX,"
                     " resource_type_string>( name );\n").encode()
        inventory=source_resource_labels(util_source,
            source_sha256=hashlib.sha256(util_source).hexdigest(),upstream_sha=_PIN)
        named=audit_requirements(req,route,source_resource_inventory=inventory)
        assert named["pinned_resource_label_collision_candidates_not_bindings"]==1
        assert named["native_resource_grammar_candidates_not_bindings"]==1
        assert named["other_operand_producer_semantics_unverified"]==2
        collision=[x for x in named["source_operands"] if x["operand"]=="rage"][0]
        assert collision["upstream_resource_label_collision_candidate"] is True
        assert collision["native_operand_feature_binding"] is None
        assert collision["decision_observation"]=="UNKNOWN"
        for badsha in ("0"*64,):
            try:source_resource_labels(util_source,source_sha256=badsha,upstream_sha=_PIN)
            except ValueError as e:assert str(e)=="RESOURCE_LABEL_SOURCE_SHA_MISMATCH"
            else:raise AssertionError("FORGED_RESOURCE_SOURCE_ACCEPTED")
        bad=copy.deepcopy(route)
        bad["operands"][0]["observation_feature"]="native.resource.current.mana"
        try:audit_requirements(req,bad)
        except ValueError as exc:
            assert str(exc)=="GAP_AUDIT_ROUTE_NOT_CANONICAL_SOURCE_RECOMPILATION"
        else:raise AssertionError("UNVERIFIED_NATIVE_BINDING_ACCEPTED")
        bad=copy.deepcopy(req)
        bad["required_action_readiness"][0]["status"]="READY"
        try:audit_requirements(bad,route)
        except ValueError as exc:assert str(exc)=="SOURCE_READINESS_CANNOT_BE_CERTIFIED"
        else:raise AssertionError("FABRICATED_READINESS_ACCEPTED")
        bad=copy.deepcopy(req)
        bad["required_state_operands"][0]["semantic_binding"]="NATIVE_APPROVED"
        try:audit_requirements(bad,route)
        except ValueError:pass
        else:raise AssertionError("FABRICATED_NATIVE_SEMANTIC_BINDING_ACCEPTED")
    print("SIMC_NATIVE_APL_OBSERVABILITY_GAP_SELF_TEST=PASS SPECS=3 SYNTHETIC_ONLY")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--requirements",type=Path)
    p.add_argument("--semantic-route",type=Path)
    p.add_argument("--pinned-util-source",type=Path)
    p.add_argument("--pinned-util-source-sha256")
    p.add_argument("--output",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test or args.requirements is None:
        selftest();return
    if not args.semantic_route:p.error("--semantic-route required")
    req=json.loads(args.requirements.read_text(encoding="utf-8"))
    route=json.loads(args.semantic_route.read_text(encoding="utf-8"))
    inventory=None
    if args.pinned_util_source:
        if not args.pinned_util_source_sha256:
            p.error("--pinned-util-source-sha256 required")
        inventory=source_resource_labels(args.pinned_util_source.read_bytes(),
            source_sha256=args.pinned_util_source_sha256,upstream_sha=_PIN)
    result=audit_requirements(req,route,source_resource_inventory=inventory)
    out=json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(out,encoding="utf-8")
        print("WROTE_SIMC_NATIVE_APL_OBSERVABILITY_GAP_AUDIT")
    else:print(out)


if __name__=="__main__":
    main()
