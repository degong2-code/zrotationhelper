#!/usr/bin/env python3
"""SimC source-derived generic semantic routing, never inferred game truth.

The registry describes lexical namespaces only. It does not grant spell IDs,
talent ranks, buff identities, readiness, source/target scope, or PRE state.
An evidence pack is merely an explicitly supplied *candidate* binding, even
when it cites Blizzard/SimC data; independent authority verification is separate.
No specialization, ability or boss-specific rules.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any, Mapping

from simc_apl_observability_contract import _SCHEMA as REQUIREMENTS_SCHEMA

_SCHEMA = "ZrotSimcGenericSemanticRoutePlanV1"
_BINDING_SCHEMA = "ZrotSimcSemanticEvidencePackV1"
_HEX = re.compile(r"^[a-f0-9]{64}$")
# Grammar families, not proofs that the operand is available or even valid.
# Any unknown namespace remains UNKNOWN rather than inferred from its spelling.
_NAMESPACE_ROUTES = {
    "buff": "AURA_QUERY", "debuff": "AURA_QUERY", "dot": "AURA_QUERY",
    "active_dot": "AURA_QUERY",
    "cooldown": "COOLDOWN_QUERY", "charges": "COOLDOWN_QUERY",
    "full_recharge_time": "COOLDOWN_QUERY",
    "action": "ACTION_STATE_QUERY", "prev": "ACTION_STATE_QUERY",
    "prev_gcd": "ACTION_STATE_QUERY",
    "talent": "BUILD_QUERY", "hero_tree": "BUILD_QUERY",
    "set_bonus": "BUILD_QUERY", "equipped": "EQUIPMENT_QUERY",
    "trinket": "EQUIPMENT_QUERY", "item": "EQUIPMENT_QUERY",
    "resource": "RESOURCE_QUERY",
    "variable": "VARIABLE_LIFETIME_QUERY",
    "target": "TARGET_QUERY", "spell_targets": "TARGET_QUERY",
    "active_enemies": "TARGET_QUERY", "active_enemies_within": "TARGET_QUERY",
    "raid_event": "ENCOUNTER_TIMING_QUERY",
    "fight_remains": "ENCOUNTER_TIMING_QUERY",
    "time": "TIMING_QUERY", "gcd": "TIMING_QUERY",
    "pet": "PET_QUERY",
}
_COMMON_PROOF_REQUIREMENTS = (
    "PINNED_SPEC_BUILD_CONTEXT", "SEMANTIC_IDENTITY_SOURCE",
    "OBSERVATION_PRODUCER_AND_SCOPE", "STRICT_PRE_TRANSITION_TIMESTAMP",
)


def compile_semantic_route_plan(requirements: Mapping[str, Any]) -> dict:
    if not isinstance(requirements, dict) or requirements.get("schema") != REQUIREMENTS_SCHEMA:
        raise ValueError("SEMANTIC_OBSERVABILITY_CONTRACT_REQUIRED")
    sha=requirements.get("source_apl_sha256")
    spec=requirements.get("spec")
    if not isinstance(sha,str) or not _HEX.fullmatch(sha):
        raise ValueError("SEMANTIC_APL_PIN_REQUIRED")
    if not isinstance(spec,str) or not spec:
        raise ValueError("SEMANTIC_SPEC_REQUIRED")
    if requirements.get("gameplay_rule_promotion") is not False:
        raise ValueError("SEMANTIC_UNVERIFIED_SOURCE_REQUIRED")
    operands=requirements.get("required_state_operands")
    actions=requirements.get("required_action_readiness")
    if not isinstance(operands,list) or not isinstance(actions,list):
        raise ValueError("SEMANTIC_REQUIREMENTS_MISSING")
    result=[]
    route_counts=Counter()
    seen=set()
    for row in operands:
        if not isinstance(row,dict):
            raise ValueError("INVALID_SEMANTIC_OPERAND")
        name=row.get("operand")
        if not isinstance(name,str) or not name or name in seen:
            raise ValueError("DUPLICATE_OR_EMPTY_SEMANTIC_OPERAND")
        seen.add(name)
        if row.get("semantic_binding")!="UNBOUND":
            raise ValueError("SOURCE_PREBOUND_SEMANTICS_FORBIDDEN")
        if row.get("strict_pre_observation")!="UNKNOWN":
            raise ValueError("SOURCE_PREOBSERVED_SEMANTICS_FORBIDDEN")
        parts=name.split(".")
        namespace=parts[0] if len(parts)>1 else name
        if row.get("namespace") != (parts[0] if len(parts)>1 else "unqualified"):
            raise ValueError("NAMESPACE_SOURCE_MISMATCH")
        family=_NAMESPACE_ROUTES.get(namespace,"UNKNOWN_NAMESPACE")
        route_counts[family]+=1
        result.append({
            "operand":name,
            "grammar_namespace":namespace,
            "grammar_family":family,
            "source_references":row.get("source_references"),
            "source_subject_token":parts[1] if len(parts)>2 else None,
            "query_suffix_tokens":parts[2:] if len(parts)>2 else [],
            "identity": "UNKNOWN",
            "observation_feature":None,
            "evidence_requirements":list(_COMMON_PROOF_REQUIREMENTS),
            "route_status":"GRAMMAR_ONLY_NOT_SEMANTICALLY_BOUND"
                           if family!="UNKNOWN_NAMESPACE" else "UNKNOWN_NAMESPACE",
        })
    if len(result)!=requirements.get("operand_requirement_count"):
        raise ValueError("OPERAND_SOURCE_COUNT_MISMATCH")
    readiness=[]
    seen_action=set()
    for item in actions:
        token=item.get("action_token") if isinstance(item,dict) else None
        if not isinstance(token,str) or not token or token in seen_action:
            raise ValueError("INVALID_READINESS_ACTION_TOKEN")
        seen_action.add(token)
        if item.get("status")!="UNKNOWN" or item.get("ability_identity")!="UNKNOWN":
            raise ValueError("SOURCE_READINESS_CANNOT_BE_CERTIFIED")
        readiness.append({
            "action_token":token, "source_references":item.get("source_references"),
            "required_dimensions":item.get("required_dimensions"),
            "ability_identity":"UNKNOWN",
            "policy_status":"NEEDS_SOURCE_ACCOUNTABLE_MECHANICS_POLICY",
            "ready":"UNKNOWN",
        })
    if len(readiness)!=requirements.get("readiness_requirement_count"):
        raise ValueError("READINESS_SOURCE_COUNT_MISMATCH")
    return {
        "schema":_SCHEMA, "spec":spec,
        "source_apl_sha256":sha,
        "source_profile_sha256":requirements.get("source_profile_sha256"),
        "source_simc_executable_sha256":requirements.get("source_simc_executable_sha256"),
        "source_row_count":requirements["source_row_count"],
        "operands":result,
        "readiness":readiness,
        "operand_count":len(result), "action_token_count":len(readiness),
        "grammar_family_counts":dict(sorted(route_counts.items())),
        "unknown_grammar_operand_count":route_counts["UNKNOWN_NAMESPACE"],
        "unsupported_expression_count":requirements["unsupported_expression_count"],
        "unsupported_expression_fields":requirements["unsupported_expression_fields"],
        "control_semantics_requirements":requirements["control_semantics_requirements"],
        "semantic_authority":"NOT_ESTABLISHED",
        "strict_pre_reconstruction":"NOT_RUN",
        "native_simc_decision_parity":"NOT_VALIDATED",
        "blind_wcl_independent_discovery":"NOT_RUN",
        "gameplay_rule_promotion":False,
    }


def apply_caller_evidence_pack(plan: Mapping[str,Any], pack: Mapping[str,Any]) -> dict:
    """Prepare explicit candidate feature mappings; NEVER certify authority.

    This accepts labels and proofs supplied by a caller; it cannot prove that
    referenced Blizzard/SimC records are genuine or mechanically sufficient.
    """
    if plan.get("schema")!=_SCHEMA:
        raise ValueError("SEMANTIC_ROUTE_PLAN_REQUIRED")
    if not isinstance(pack,dict) or pack.get("schema")!=_BINDING_SCHEMA:
        raise ValueError("SEMANTIC_EVIDENCE_PACK_SCHEMA")
    for key in ("spec","source_apl_sha256","source_profile_sha256"):
        if pack.get(key)!=plan.get(key):
            raise ValueError("SEMANTIC_EVIDENCE_IDENTITY_MISMATCH_"+key)
    build=pack.get("build_key")
    if not isinstance(build,str) or not build.strip():
        raise ValueError("SEMANTIC_EVIDENCE_BUILD_REQUIRED")
    if pack.get("hypothesis_only") is not True or pack.get("gameplay_rule_promotion") is not False:
        raise ValueError("SEMANTIC_EVIDENCE_PREMATURE_AUTHORITY")
    bindings=pack.get("bindings")
    if not isinstance(bindings,list):
        raise ValueError("SEMANTIC_EVIDENCE_BINDINGS_REQUIRED")
    declared={row["operand"] for row in plan["operands"]}
    seen=set()
    feature_owners={}
    result=[]
    for item in bindings:
        if not isinstance(item,dict):
            raise ValueError("INVALID_SEMANTIC_BINDING")
        operand=item.get("operand")
        feature=item.get("feature_key")
        source=item.get("source_kind")
        evidence=item.get("evidence_ref")
        digest=item.get("source_sha256")
        identity=item.get("mechanic_identity")
        if operand not in declared or operand in seen:
            raise ValueError("DUPLICATE_OR_UNKNOWN_SEMANTIC_BINDING")
        if not all(isinstance(x,str) and x.strip()
                   for x in (feature,source,evidence,identity)):
            raise ValueError("SEMANTIC_BINDING_EVIDENCE_INCOMPLETE")
        if source not in ("BLIZZARD_OFFICIAL","SIMC_PINNED_SOURCE"):
            raise ValueError("UNSUPPORTED_SEMANTIC_EVIDENCE_KIND")
        if not isinstance(digest,str) or not _HEX.fullmatch(digest):
            raise ValueError("SEMANTIC_EVIDENCE_SHA256_REQUIRED")
        if feature in feature_owners and feature_owners[feature] != operand:
            raise ValueError("AMBIGUOUS_FEATURE_ALIAS")
        seen.add(operand)
        feature_owners[feature]=operand
        result.append({
            "operand":operand,"feature_key":feature,
            "source_kind":source,"source_sha256":digest,
            "evidence_ref":evidence,"mechanic_identity":identity,
            "status":"CALLER_ATTESTED_NOT_INDEPENDENTLY_VERIFIED",
        })
    return {
        "schema":"ZrotSimcGenericCandidateBindingsV1",
        "spec":plan["spec"],"source_apl_sha256":plan["source_apl_sha256"],
        "source_profile_sha256":plan["source_profile_sha256"],
        "build_key":build,
        "candidate_bindings":result,
        "remaining_unbound_operands":len(declared)-len(seen),
        "all_readiness":"UNKNOWN",
        "evidence_source_validity":"NOT_INDEPENDENTLY_VERIFIED",
        "actual_strict_pre_observation":"NOT_RUN",
        "gameplay_rule_promotion":False,
    }


def selftest():
    from simc_apl_source_engine import ingest_actions
    from simc_apl_conditional_ir import compile_structural_ir
    from simc_apl_observability_contract import compile_requirements
    for spec,token in (("synthetic","alpha"),("unholy","omega"),("imaginary","beta")):
        src=(f"spec={spec}\n"
             f"actions={token},if=buff.test.stack>=2&cooldown.foo.remains=0\n"
             "actions+=/other,if=variable.gate&unknown_prefix.strange\n"
             "actions+=/third,if=active_enemies>=2\n").encode()
        ir=compile_structural_ir(ingest_actions(src,expected_spec=spec))
        req=compile_requirements(ir)
        plan=compile_semantic_route_plan(req)
        assert plan["operand_count"]==5,plan
        assert plan["action_token_count"]==3
        assert plan["unknown_grammar_operand_count"]==1
        assert plan["grammar_family_counts"]["AURA_QUERY"]==1
        assert plan["grammar_family_counts"]["COOLDOWN_QUERY"]==1
        assert plan["grammar_family_counts"]["VARIABLE_LIFETIME_QUERY"]==1
        assert all(item["identity"]=="UNKNOWN" and item["observation_feature"] is None
                   for item in plan["operands"])
        assert all(item["ready"]=="UNKNOWN" for item in plan["readiness"])
        assert plan["gameplay_rule_promotion"] is False
        pack={
            "schema":_BINDING_SCHEMA,"spec":spec,
            "source_apl_sha256":plan["source_apl_sha256"],
            "source_profile_sha256":plan["source_profile_sha256"],
            "build_key":"synthetic-build-A","hypothesis_only":True,
            "gameplay_rule_promotion":False,
            "bindings":[{
                "operand":"buff.test.stack","feature_key":"buff_stack",
                "source_kind":"SIMC_PINNED_SOURCE","evidence_ref":"fixture:source:1",
                "source_sha256":"a"*64,"mechanic_identity":"fixture:buff:1",
            }],
        }
        candidate=apply_caller_evidence_pack(plan,pack)
        assert candidate["remaining_unbound_operands"]==4
        assert candidate["candidate_bindings"][0]["status"]=="CALLER_ATTESTED_NOT_INDEPENDENTLY_VERIFIED"
        assert candidate["all_readiness"]=="UNKNOWN"
        import copy
        for field,value,reason in [
            ("spec","wrong","SEMANTIC_EVIDENCE_IDENTITY_MISMATCH_spec"),
            ("source_apl_sha256","0"*64,"SEMANTIC_EVIDENCE_IDENTITY_MISMATCH_source_apl_sha256"),
            ("build_key","","SEMANTIC_EVIDENCE_BUILD_REQUIRED"),
            ("hypothesis_only",False,"SEMANTIC_EVIDENCE_PREMATURE_AUTHORITY"),
        ]:
            bad=copy.deepcopy(pack)
            bad[field]=value
            try:
                apply_caller_evidence_pack(plan,bad)
            except ValueError as exc:
                assert str(exc)==reason,(field,str(exc))
            else:
                raise AssertionError("INVALID_SOURCE_BINDING_ACCEPTED")
        duplicate=copy.deepcopy(pack)
        duplicate["bindings"].append({**duplicate["bindings"][0],
                                      "operand":"cooldown.foo.remains"})
        try:
            apply_caller_evidence_pack(plan,duplicate)
        except ValueError as exc:
            assert str(exc)=="AMBIGUOUS_FEATURE_ALIAS"
        else:
            raise AssertionError("AMBIGUOUS_ALIAS_ACCEPTED")
        unknown=copy.deepcopy(pack)
        unknown["bindings"][0]["operand"]="not_declared"
        try:
            apply_caller_evidence_pack(plan,unknown)
        except ValueError as exc:
            assert str(exc)=="DUPLICATE_OR_UNKNOWN_SEMANTIC_BINDING"
        else:
            raise AssertionError("UNDECLARED_BINDING_ACCEPTED")
    print("SIMC_GENERIC_SEMANTIC_ROUTE_SELF_TEST=PASS SPECS=3 CLAIM=SYNTAX_ONLY")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements",type=Path)
    parser.add_argument("--evidence-pack",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test or args.requirements is None:
        selftest()
        return
    requirements=json.loads(args.requirements.read_text(encoding="utf-8"))
    route=compile_semantic_route_plan(requirements)
    if args.evidence_pack:
        route["caller_evidence_candidates"]=apply_caller_evidence_pack(
            route,json.loads(args.evidence_pack.read_text(encoding="utf-8")))
    content=json.dumps(route,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(content,encoding="utf-8")
        print("WROTE_SIMC_GENERIC_SEMANTIC_ROUTE_PLAN")
    else:
        print(content)


if __name__=="__main__":
    main()
