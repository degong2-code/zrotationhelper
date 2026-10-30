#!/usr/bin/env python3
"""Pinned SimC C++ source proof for *bare* resource APL expression semantics.

This only proves the generic source path:
player_t::create_expression -> create_resource_expression ->
util::parse_resource_type -> make_ref_expr(resources.current[r]).
It explicitly does not certify *live* Native PRE values, resource completeness,
class-module alternative value semantics, ability readiness or game optimality.

The branch-selected class override source is audited conservatively: the bare
token must not be intercepted before the explicit player_t fallback. A static
source check is narrower than Native execution instrumentation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from simc_apl_native_observability_gap import source_resource_labels, _PIN

_SCHEMA="ZrotPinnedSimcBareResourceExpressionSourceProofV1"
_BASE="std::unique_ptr<expr_t> player_t::create_expression( util::string_view expression_str )"
_RESOURCE="player_t::create_resource_expression( util::string_view expression_str )"
_FALLBACK="return player_t::create_expression( name_str );"


def _hash(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def _pinned_file(raw:bytes,expected_sha:str,filename:str)->str:
    if not isinstance(raw,bytes) or not 0<len(raw)<950000 or _hash(raw)!=expected_sha:
        raise ValueError("SIMC_EXPRESSION_SOURCE_SHA_OR_SIZE_"+filename)
    try:return raw.decode("utf-8")
    except UnicodeDecodeError as e:raise ValueError("SIMC_EXPRESSION_SOURCE_UTF8_"+filename) from e


def _function(source:str,signature:str)->str:
    if source.count(signature)!=1:
        raise ValueError("SIMC_EXPRESSION_MISSING_OR_REPEATED_SOURCE_ANCHOR")
    begin=source.index(signature)
    opening=source.find("{",begin)
    if opening<0 or opening-begin>250:
        raise ValueError("SIMC_EXPRESSION_FUNCTION_BODY_MISSING")
    depth=0
    for i in range(opening,len(source)):
        if source[i]=="{":depth+=1
        elif source[i]=="}":
            depth-=1
            if depth==0:return source[begin:i+1]
    raise ValueError("SIMC_EXPRESSION_UNTERMINATED_FUNCTION")


def prove_bare_resource(gap_report:dict,inventory:dict,*,player_cpp:bytes,
                        player_sha256:str,class_cpp:bytes|None=None,
                        class_sha256:str|None=None,
                        class_expression_function:str|None=None)->dict:
    if gap_report.get("schema")!="ZrotNativeResourceAplObservabilityGapAuditV1" or (
        gap_report.get("gameplay_rule_promotion") is not False):
        raise ValueError("SIMC_EXPRESSION_GAP_CONTRACT_REQUIRED")
    if inventory.get("upstream_sha")!=_PIN or (
        inventory.get("source_label_only_no_expression_equivalence") is not True) or (
        inventory.get("source_sha256")!=gap_report.get("resource_label_registry_source_sha256")):
        raise ValueError("SIMC_EXPRESSION_PINNED_UTIL_SOURCE_MISMATCH")
    labels=inventory["resource_enum_to_label"]
    if not isinstance(labels,dict) or not labels:
        raise ValueError("SIMC_EXPRESSION_PINNED_ENUM_MAPPING_REQUIRED")
    if (class_cpp is None)!=(class_sha256 is None) or (
        (class_cpp is None)!=(class_expression_function is None)):
        raise ValueError("SIMC_EXPRESSION_CLASS_OVERRIDE_PROOF_INCOMPLETE")
    player=_pinned_file(player_cpp,player_sha256,"player.cpp")
    base=_function(player,_BASE)
    resource=_function(player,_RESOURCE)
    tests=[
        ("if ( auto q = create_resource_expression( expression_str ) )",base),
        ("return q;",base),
        ("resource_e r = util::parse_resource_type( splits[ 0 ] );",resource),
        ("if ( r == RESOURCE_NONE )",resource),
        ("if ( splits.size() == 1 )",resource),
        ("return make_ref_expr( expression_str, resources.current[ r ] );",resource),
    ]
    for anchor,body in tests:
        if body.count(anchor)!=1:
            raise ValueError("SIMC_EXPRESSION_SOURCE_SEMANTICS_ANCHOR_"+anchor)
    if not (resource.index("if ( r == RESOURCE_NONE )") <
            resource.index("if ( splits.size() == 1 )") <
            resource.index("return make_ref_expr( expression_str, resources.current[ r ] );")):
        raise ValueError("SIMC_EXPRESSION_RESOURCE_CONTROL_FLOW_DRIFT")
    class_src=None
    class_path="NO_CLASS_OVERRIDE_DECLARED"
    if class_cpp is not None:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*::create_expression",class_expression_function or ""):
            raise ValueError("SIMC_EXPRESSION_CLASS_FUNCTION_INVALID")
        src=_pinned_file(class_cpp,class_sha256,"class.cpp")
        signature=re.compile(
            r"std::unique_ptr<expr_t>\s+"+re.escape(class_expression_function)+
            r"\(\s*(?:std::string_view|util::string_view)\s+name_str\s*\)")
        hits=list(signature.finditer(src))
        if len(hits)!=1:
            raise ValueError("SIMC_EXPRESSION_CLASS_EXACT_OVERRIDE_NOT_FOUND")
        class_src=_function(src,hits[0].group(0))
        if class_src.count(_FALLBACK)!=1 or not class_src.rstrip().endswith(_FALLBACK+"\n}"):
            raise ValueError("SIMC_EXPRESSION_CLASS_FALLBACK_NOT_LAST")
        class_path="SOURCE_CHECKED_CLASS_OVERRIDE_BARE_TOKEN_FALLBACK"
    rows=[]
    seen=set()
    for op in gap_report["source_operands"]:
        name=op["operand"]
        if not op.get("upstream_resource_label_collision_candidate"):
            continue
        if (op["native_operand_feature_binding"] is not None or
            op["decision_observation"]!="UNKNOWN" or
            op["could_be_used_for_priority_trace"] is not False):
            raise ValueError("SIMC_EXPRESSION_PREMATURE_READY_OR_BINDING")
        candidates=[enum for enum,label in labels.items() if label==name]
        if len(candidates)!=1 or name in seen or "." in name:
            raise ValueError("SIMC_EXPRESSION_NONUNIQUE_BARE_RESOURCE")
        seen.add(name)
        override_status="NO_CLASS_OVERRIDE_IN_FIXTURE_SOURCE_PATH"
        if class_src is not None:
            # Bare exact value interception (or prefix interception) would
            # prevent making the base expression claim.
            if re.search(r'(?:name_str\s*==|str_compare_ci\(\s*name_str\s*,)\s*"'+
                         re.escape(name)+r'"',class_src):
                raise ValueError("SIMC_EXPRESSION_CLASS_BARE_TOKEN_INTERCEPT")
            if re.search(r'str_prefix_ci\(\s*name_str\s*,\s*"'+re.escape(name),class_src):
                raise ValueError("SIMC_EXPRESSION_CLASS_PREFIX_INTERCEPT")
            if re.search(r'str_compare_ci\(\s*splits\[\s*0\s*\]\s*,\s*"'+
                         re.escape(name)+r'"\s*\)\s*&&\s*splits\.size\(\)\s*>\s*1',
                         class_src):
                override_status="CLASS_DOTTED_ONLY_SPECIAL_CASE_BARE_FALLS_THROUGH"
            elif re.search(r'str_compare_ci\(\s*splits\[\s*0\s*\]\s*,\s*"'+
                           re.escape(name)+r'"',class_src):
                raise ValueError("SIMC_EXPRESSION_CLASS_AMBIGUOUS_BARE_ROUTE")
            else:
                override_status=class_path
        rows.append({
            "operand":name,
            "source_references":op["source_references"],
            "source_resource_enum":"RESOURCE_"+candidates[0],
            "pinned_source_expression":"make_ref_expr(resources.current[resource_e])",
            "source_semantics":"BARE_RESOURCE_CURRENT_REFERENCE_IN_PINNED_SIMC",
            "source_semantics_proof":"SOURCE_GUARD_EXACT_PLAYER_CPP_AND_UTIL_RESOURCE_LABEL",
            "class_override_fallthrough":override_status,
            "player_source_sha256":player_sha256,
            "class_source_sha256":class_sha256,
            "upstream_util_source_sha256":inventory["source_sha256"],
            "native_producer_semantic_value_link":"NOT_VALIDATED_PER_DECISION",
            "native_epoch_strict_pre_state":"UNKNOWN",
            "full_state_write_coverage":"UNKNOWN",
            "ability_readiness":"UNKNOWN",
            "general_rotation_promotion":False,
        })
    if len(rows)!=gap_report.get("pinned_resource_label_collision_candidates_not_bindings"):
        raise ValueError("SIMC_EXPRESSION_SOURCE_CANDIDATE_LOSS")
    return {
        "schema":_SCHEMA,
        "spec":gap_report["spec"],
        "source_apl_sha256":gap_report["source_apl_sha256"],
        "source_profile_sha256":gap_report["source_profile_sha256"],
        "source_upstream_revision":_PIN,
        "source_resolution_proof_count":len(rows),
        "proven_bare_expression_semantics":rows,
        "source_semantics_verified":True,
        "actual_native_strict_pre_operand_values_verified":False,
        "action_readiness_verified":0,
        "action_readiness_unknown":gap_report["all_action_tokens_unverified"],
        "native_decision_parity":"NOT_VALIDATED",
        "blind_wcl_candidate_lock":"NOT_RUN",
        "gameplay_rule_promotion":False,
    }


def selftest():
    from copy import deepcopy
    # Minimal source-shaped synthetic snippets (never official evidence).
    util=(b"const char* util::resource_type_string( resource_e resource_type ) {\n"+
          b'case RESOURCE_NONE: return "none";\n'+
          b'case RESOURCE_RAGE: return "rage";\n'+
          b'case RESOURCE_RUNE: return "rune";\n'+
          b'case RESOURCE_FURY: return "fury";\n'+
          b'case RESOURCE_MANA: return "mana";\n'+
          b'case RESOURCE_RUNIC_POWER: return "runic_power";\n'+
          b'}\nconst char* util::resource_type_abbrev( resource_e resource_type ) {}\n'+
          b'resource_e util::parse_resource_type( util::string_view name ) { return '+
          b'parse_enum<resource_e, RESOURCE_NONE, RESOURCE_MAX, resource_type_string>( name ); }')
    inventory=source_resource_labels(util,source_sha256=_hash(util),upstream_sha=_PIN)
    player=(b"std::unique_ptr<expr_t> player_t::create_expression( util::string_view expression_str ) {\n"+
            b"if ( auto q = create_resource_expression( expression_str ) )\nreturn q;\n}\n"+
            b"player_t::create_resource_expression( util::string_view expression_str ) {\n"+
            b"resource_e r = util::parse_resource_type( splits[ 0 ] );\n"+
            b"if ( r == RESOURCE_NONE ) return nullptr;\n"+
            b"if ( splits.size() == 1 )\nreturn make_ref_expr( expression_str, resources.current[ r ] );\n}\n")
    cls=(b"std::unique_ptr<expr_t> death_knight_t::create_expression( std::string_view name_str ) {\n"+
         b'if ( util::str_compare_ci( splits[ 0 ], "rune" ) && splits.size() > 1 ) {\n'+
         b'return make_fn_expr("x", some_func);\n}\n'+_FALLBACK.encode()+b"\n}\n")
    for name in ("rune","rage","fury","runic_power"):
        fake={"schema":"ZrotNativeResourceAplObservabilityGapAuditV1","spec":"test",
              "source_apl_sha256":"a"*64,"source_profile_sha256":None,
              "resource_label_registry_source_sha256":_hash(util),
              "all_action_tokens_unverified":5,
              "pinned_resource_label_collision_candidates_not_bindings":1,
              "source_operands":[{
                  "operand":name,"source_references":["synthetic:row"],
                  "upstream_resource_label_collision_candidate":True,
                  "native_operand_feature_binding":None,
                  "decision_observation":"UNKNOWN",
                  "could_be_used_for_priority_trace":False,
              }],"gameplay_rule_promotion":False}
        result=prove_bare_resource(fake,inventory,player_cpp=player,
                                  player_sha256=_hash(player),class_cpp=cls,
                                  class_sha256=_hash(cls),
                                  class_expression_function="death_knight_t::create_expression")
        assert result["source_resolution_proof_count"]==1
        assert result["action_readiness_unknown"]==5
        assert not result["actual_native_strict_pre_operand_values_verified"]
        assert not result["gameplay_rule_promotion"]
        bad=cls.replace(b"splits.size() > 1",b"splits.size() >= 1")
        if name=="rune":
            try:prove_bare_resource(fake,inventory,player_cpp=player,
                          player_sha256=_hash(player),class_cpp=bad,
                          class_sha256=_hash(bad),
                          class_expression_function="death_knight_t::create_expression")
            except ValueError as e:
                assert str(e)=="SIMC_EXPRESSION_CLASS_AMBIGUOUS_BARE_ROUTE"
            else:raise AssertionError("CLASS_OVERRIDDEN_RUNE_ACCEPTED")
        stale=deepcopy(inventory)
        stale["source_sha256"]="0"*64
        try:prove_bare_resource(fake,stale,player_cpp=player,player_sha256=_hash(player))
        except ValueError as e:assert str(e)=="SIMC_EXPRESSION_PINNED_UTIL_SOURCE_MISMATCH"
        else:raise AssertionError("FAKE_UTIL_SHA_ACCEPTED")
    print("SIMC_PINNED_BARE_RESOURCE_EXPRESSION_SOURCE_PROOF_SELF_TEST=PASS LABELS=4 SYNTHETIC_ONLY")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--gap-report",type=Path)
    p.add_argument("--pinned-util-source",type=Path)
    p.add_argument("--pinned-util-sha256")
    p.add_argument("--pinned-player-source",type=Path)
    p.add_argument("--pinned-player-sha256")
    p.add_argument("--pinned-class-source",type=Path)
    p.add_argument("--pinned-class-sha256")
    p.add_argument("--class-expression-function")
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.self_test or args.gap_report is None:
        selftest();return
    for k in ("pinned_util_source","pinned_util_sha256",
              "pinned_player_source","pinned_player_sha256"):
        if getattr(args,k) is None:p.error("--"+k.replace("_","-")+" is required")
    gap=json.loads(args.gap_report.read_text("utf-8"))
    inventory=source_resource_labels(
        args.pinned_util_source.read_bytes(),
        source_sha256=args.pinned_util_sha256,upstream_sha=_PIN)
    out=prove_bare_resource(gap,inventory,
        player_cpp=args.pinned_player_source.read_bytes(),
        player_sha256=args.pinned_player_sha256,
        class_cpp=args.pinned_class_source.read_bytes() if args.pinned_class_source else None,
        class_sha256=args.pinned_class_sha256,
        class_expression_function=args.class_expression_function)
    rendered=json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(rendered,encoding="utf-8")
        print("WROTE_PINNED_SIMC_RESOURCE_EXPRESSION_PROOF")
    else:print(rendered)


if __name__=="__main__":
    main()
