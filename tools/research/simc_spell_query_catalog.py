#!/usr/bin/env python3
"""Pinned SimC spell_query XML -> generic DBC metadata candidate catalog.

Reads actual official-SimC-binary spell_query XML outputs, never spell IDs
entered by class-specific code. Bounded XML parsing and SHA receipts make
source bytes auditable. Exact normalized name is only a *candidate* match:
an APL action token need not correspond 1:1 to a DBC spell, and database
fields are not current Blizzard authority, runtime readiness, or Strict PRE.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from simc_apl_semantic_resolver import _SCHEMA as ROUTE_SCHEMA

_SCHEMA="ZrotSimcPinnedSpellQueryCatalogV1"
_REQUEST_SCHEMA="ZrotSimcPinnedSpellQueryRequestV1"
_SHA=re.compile(r"^[0-9a-f]{64}$")
_TOKEN=re.compile(r"^[a-z][a-z0-9_]{1,95}$")
MAX_XML=2_000_000
MAX_QUERIES=48
MAX_SPELLS_PER_QUERY=1000
# These tags are a *data extraction* allowlist, not a mechanics model.
SPELL_ATTRIBUTES=("id","name","cooldown","gcd","duration","stacks_max",
                  "stacks_initial","replaces_id","replaces_name","charge_cooldown",
                  "charges","max_range","min_range","cast_time")
CHILD_TAGS=("class","spec","resource","effects")


def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def _tokenize(name:str)->str:
    # Conservative exact-name candidate only; not guaranteed to match SimC's
    # full Unicode tokenize_fn semantics. A mismatch stays unlinked.
    return re.sub(r"[^a-z0-9]+","_",name.lower()).strip("_")


def make_query_plan(route:dict,*,max_queries:int=8)->dict:
    """Choose action names from the IR, without ability lists or spec rules."""
    if route.get("schema")!=ROUTE_SCHEMA or route.get("gameplay_rule_promotion") is not False:
        raise ValueError("CATALOG_ROUTE_NOT_UNVERIFIED")
    if not isinstance(max_queries,int) or isinstance(max_queries,bool) or not 1<=max_queries<=MAX_QUERIES:
        raise ValueError("CATALOG_QUERY_LIMIT_INVALID")
    spec=route.get("spec")
    apl_sha=route.get("source_apl_sha256")
    if not isinstance(spec,str) or not spec or not isinstance(apl_sha,str) or not _SHA.fullmatch(apl_sha):
        raise ValueError("CATALOG_SOURCE_IDENTITY_INVALID")
    raw=route.get("readiness")
    if not isinstance(raw,list):
        raise ValueError("CATALOG_ACTION_TOKENS_MISSING")
    action_tokens=sorted({r["action_token"] for r in raw
                          if isinstance(r,dict) and isinstance(r.get("action_token"),str)
                          and _TOKEN.fullmatch(r["action_token"])})
    selected=action_tokens[:max_queries]
    if not selected:
        raise ValueError("NO_QUERYABLE_ACTION_TOKENS")
    return {
        "schema":_REQUEST_SCHEMA, "spec":spec,
        "source_apl_sha256":apl_sha,
        "source_profile_sha256":route.get("source_profile_sha256"),
        "source_simc_executable_sha256":route.get("source_simc_executable_sha256"),
        "selected_query_tokens":selected,
        "skipped_or_deferred_action_count":len(raw)-len(selected),
        "selection_policy":"LEXICOGRAPHIC_BOUNDED_SOURCE_ACTION_TOKENS",
        "query_format":"spell_query=spell.name=TOKEN",
        "candidate_only":True,
        "current_blizzard_authority":"NOT_VERIFIED",
    }


def _parse_spell_xml(data:bytes,token:str)->dict:
    if not data or len(data)>MAX_XML:
        raise ValueError("SPELL_QUERY_XML_SIZE_INVALID")
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("SPELL_QUERY_XML_DTD_FORBIDDEN")
    try:
        root=ET.fromstring(data)
    except ET.ParseError as e:
        raise ValueError("SPELL_QUERY_XML_INVALID") from e
    if root.tag!="spell_query":
        raise ValueError("SPELL_QUERY_XML_ROOT_INVALID")
    all_spells=list(root)
    if len(all_spells)>MAX_SPELLS_PER_QUERY or any(e.tag!="spell" for e in all_spells):
        raise ValueError("SPELL_QUERY_XML_CONTENT_UNSUPPORTED")
    candidates=[]
    identifiers=set()
    for el in all_spells:
        id_text=el.get("id")
        name=el.get("name")
        if not isinstance(id_text,str) or not id_text.isdecimal() or int(id_text)<=0 or not name:
            raise ValueError("SPELL_QUERY_ID_OR_NAME_INVALID")
        id_value=int(id_text)
        if id_value in identifiers:
            raise ValueError("DUPLICATE_SPELL_QUERY_ID")
        identifiers.add(id_value)
        if _tokenize(name)!=token:
            continue
        fields={k:el.attrib[k] for k in SPELL_ATTRIBUTES if k in el.attrib}
        # Preserve all available identity/scope evidence, without inventing
        # default cooldown / range / resource / talent applicability.
        child_records={}
        for label in CHILD_TAGS:
            items=[]
            for child in el.findall(label):
                if label=="effects":
                    items=[{"effect_records_count":len(list(child)),
                            "declared_count":child.attrib.get("count")}]
                    break
                items.append(dict(sorted(child.attrib.items())))
            child_records[label]=items
        candidates.append({
            "spell_id":id_value,"spell_name":name,
            "dbc_fields":fields,"dbc_subrecords":child_records,
            "name_match":"EXACT_CONSERVATIVE_NORMALIZATION_ONLY",
            "apl_action_identity":"UNVERIFIED",
        })
    return {
        "query_token":token,"xml_spell_count":len(all_spells),
        "exact_name_candidate_count":len(candidates),
        "candidate_spells":sorted(candidates,key=lambda p:p["spell_id"]),
        "resolution_status":("NO_EXACT_NAME_CANDIDATE" if not candidates else
                             "AMBIGUOUS_EXACT_NAME_CANDIDATES" if len(candidates)>1 else
                             "ONE_EXACT_NAME_CANDIDATE_UNVERIFIED"),
    }


def build_catalog(request:dict,*,binary_sha256:str,image_digest:str,
                  query_blobs:dict[str,bytes],query_sha256:dict[str,str])->dict:
    if request.get("schema")!=_REQUEST_SCHEMA or request.get("candidate_only") is not True:
        raise ValueError("CATALOG_QUERY_REQUEST_REQUIRED")
    if not isinstance(binary_sha256,str) or not _SHA.fullmatch(binary_sha256):
        raise ValueError("CATALOG_BINARY_SHA_REQUIRED")
    pinned=request.get("source_simc_executable_sha256")
    if pinned is not None and binary_sha256!=pinned:
        raise ValueError("CATALOG_BINARY_SOURCE_PIN_MISMATCH")
    if not isinstance(image_digest,str) or not image_digest.startswith("sha256:") or not _SHA.fullmatch(image_digest[7:]):
        raise ValueError("CATALOG_IMAGE_DIGEST_INVALID")
    tokens=request.get("selected_query_tokens")
    if (not isinstance(tokens,list) or not 1<=len(tokens)<=MAX_QUERIES
            or len(set(tokens))!=len(tokens)
            or any(not isinstance(t,str) or not _TOKEN.fullmatch(t) for t in tokens)):
        raise ValueError("CATALOG_REQUEST_TOKENS_INVALID")
    if set(query_blobs)!=set(tokens) or set(query_sha256)!=set(tokens):
        raise ValueError("CATALOG_OUTPUT_TOKEN_SET_MISMATCH")
    rows=[]
    counts=Counter()
    for token in tokens:
        raw=query_blobs[token]
        expected=query_sha256[token]
        if not isinstance(expected,str) or not _SHA.fullmatch(expected) or sha(raw)!=expected:
            raise ValueError("CATALOG_RAW_QUERY_SHA_MISMATCH")
        row=_parse_spell_xml(raw,token)
        row["raw_xml_sha256"]=sha(raw)
        row["raw_xml_bytes"]=len(raw)
        rows.append(row)
        counts[row["resolution_status"]]+=1
    return {
        "schema":_SCHEMA,
        "source_kind":"PINNED_SIMC_BINARY_DBC_SPELL_QUERY_XML",
        "spec":request["spec"],
        "source_apl_sha256":request["source_apl_sha256"],
        "source_profile_sha256":request.get("source_profile_sha256"),
        "simc_executable_sha256":binary_sha256,
        "simc_image_digest":image_digest,
        "source_query_token_count":len(tokens),
        "query_resolution_counts":dict(sorted(counts.items())),
        "spell_query_results":rows,
        "source_dbc_mechanics_are_blizzard_live_truth":False,
        "apl_action_spell_mapping_certified":False,
        "native_rotation_foreground_equivalence":"NOT_VALIDATED",
        "readiness":"UNKNOWN",
        "strict_pre_state":"NOT_RUN",
        "wcl_empirical_validation":"NOT_RUN",
        "gameplay_rule_promotion":False,
    }



def link_catalog_candidates_to_route(route:dict,catalog:dict)->dict:
    """Join query evidence to action tokens by exact identity, not spell truth.

    A unique DBC record is still NOT independently proven to be the APL
    action used by the actor. Every readiness status stays UNKNOWN.
    """
    if route.get("schema")!=ROUTE_SCHEMA or catalog.get("schema")!=_SCHEMA:
        raise ValueError("CATALOG_ROUTE_JOIN_SCHEMA")
    for key,cat_key in (("spec","spec"),("source_apl_sha256","source_apl_sha256"),
                        ("source_profile_sha256","source_profile_sha256")):
        if route.get(key)!=catalog.get(cat_key):
            raise ValueError("CATALOG_ROUTE_SOURCE_MISMATCH_"+key)
    route_binary=route.get("source_simc_executable_sha256")
    if route_binary is not None and route_binary!=catalog.get("simc_executable_sha256"):
        raise ValueError("CATALOG_ROUTE_BINARY_MISMATCH")
    if route.get("gameplay_rule_promotion") is not False or catalog.get("gameplay_rule_promotion") is not False:
        raise ValueError("CATALOG_ROUTE_PROMOTION_FORBIDDEN")
    allowed={x["action_token"] for x in route["readiness"]}
    query_rows=catalog.get("spell_query_results")
    if not isinstance(query_rows,list) or len(query_rows)!=catalog.get("source_query_token_count"):
        raise ValueError("CATALOG_QUERY_ROW_COUNT_MISMATCH")
    by_token={}
    for item in query_rows:
        token=item.get("query_token") if isinstance(item,dict) else None
        if token not in allowed or token in by_token:
            raise ValueError("CATALOG_QUERY_TOKEN_NOT_IN_SOURCE_APL")
        if item.get("exact_name_candidate_count")!=len(item.get("candidate_spells",[])):
            raise ValueError("CATALOG_CANDIDATE_COUNT_MISMATCH")
        by_token[token]=item
    results=[]
    for token in sorted(allowed):
        record=by_token.get(token)
        candidates=(record["candidate_spells"] if record else [])
        results.append({
            "action_token":token,
            "spell_id_candidates":[x["spell_id"] for x in candidates],
            "query_status":record["resolution_status"] if record else "NOT_QUERYED",
            "source_xml_sha256":record["raw_xml_sha256"] if record else None,
            "identity_status":"UNVERIFIED_APL_ACTION_MAPPING",
            "runtime_readiness":"UNKNOWN",
            "mechanic_effect_coverage":"DBC_RECORD_ONLY_NOT_RUNTIME",
        })
    return {
        "schema":"ZrotSimcGenericCatalogActionCandidateJoinV1",
        "spec":catalog["spec"],"source_apl_sha256":catalog["source_apl_sha256"],
        "source_simc_executable_sha256":catalog["simc_executable_sha256"],
        "route_action_count":len(allowed),"queried_action_count":len(by_token),
        "action_candidates":results,
        "source_profile_and_apl_identity_pinned":route_binary is not None,
        "apl_action_identity_certified":False,
        "all_readiness":"UNKNOWN",
        "gameplay_rule_promotion":False,
    }


def selftest():
    from simc_apl_source_engine import ingest_actions
    from simc_apl_conditional_ir import compile_structural_ir
    from simc_apl_observability_contract import compile_requirements
    from simc_apl_semantic_resolver import compile_semantic_route_plan
    for spec,action in (("imaginary","alpha_strike"),("fury","omega_strike"),("unholy","gamma_strike")):
        src=(f"spec={spec}\n"
             f"actions={action},if=active_enemies>=2\n"
             "actions+=/other_action\n").encode()
        route=compile_semantic_route_plan(
            compile_requirements(compile_structural_ir(ingest_actions(src,expected_spec=spec))))
        req=make_query_plan(route,max_queries=1)
        assert req["selected_query_tokens"]==[action]
        raw=(f'<spell_query><spell id="101" name="{action.replace("_"," ").title()}" cooldown="8" gcd="1.5">'
             '<class id="1" name="Synthetic" /><resource type="1" cost="30" />'
             '<effects count="1"><effect id="33" /></effects></spell></spell_query>').encode()
        result=build_catalog(req,binary_sha256="a"*64,image_digest="sha256:"+"b"*64,
                             query_blobs={action:raw},query_sha256={action:sha(raw)})
        record=result["spell_query_results"][0]
        assert record["exact_name_candidate_count"]==1
        assert record["candidate_spells"][0]["spell_id"]==101
        assert record["candidate_spells"][0]["dbc_fields"]["cooldown"]=="8"
        assert record["candidate_spells"][0]["dbc_subrecords"]["resource"][0]["cost"]=="30"
        assert not result["apl_action_spell_mapping_certified"] and result["readiness"]=="UNKNOWN"
        joined=link_catalog_candidates_to_route(route,result)
        assert joined["queried_action_count"]==1
        assert joined["route_action_count"]==2
        assert joined["action_candidates"][0]["identity_status"]=="UNVERIFIED_APL_ACTION_MAPPING"
        assert joined["all_readiness"]=="UNKNOWN"
        assert sum(x["query_status"]=="NOT_QUERYED" for x in joined["action_candidates"])==1
        assert not joined["gameplay_rule_promotion"]
        try:link_catalog_candidates_to_route({**route,"spec":"wrong"},result)
        except ValueError as e:assert str(e)=="CATALOG_ROUTE_SOURCE_MISMATCH_spec"
        else:raise AssertionError("CROSS_SPEC_IDENTITY_ACCEPTED")

        assert not result["gameplay_rule_promotion"]
        dup=(b'<spell_query><spell id="101" name="Alpha Strike" />'
             b'<spell id="202" name="Alpha Strike" /></spell_query>')
        if action=="alpha_strike":
            amb=build_catalog(req,binary_sha256="a"*64,image_digest="sha256:"+"b"*64,
                              query_blobs={action:dup},query_sha256={action:sha(dup)})
            assert amb["spell_query_results"][0]["resolution_status"]=="AMBIGUOUS_EXACT_NAME_CANDIDATES"
        bad=raw+b" "
        for passed,expect in (({action:sha(bad)},"CATALOG_RAW_QUERY_SHA_MISMATCH"),):
            try:build_catalog(req,binary_sha256="a"*64,image_digest="sha256:"+"b"*64,
                              query_blobs={action:raw},query_sha256=passed)
            except ValueError as e:assert str(e)==expect,str(e)
            else:raise AssertionError("MISMATCHED_CATALOG_SHA_ACCEPTED")
        try:build_catalog({**req,"source_simc_executable_sha256":"c"*64},
                           binary_sha256="a"*64,image_digest="sha256:"+"b"*64,
                           query_blobs={action:raw},query_sha256={action:sha(raw)})
        except ValueError as e:assert str(e)=="CATALOG_BINARY_SOURCE_PIN_MISMATCH"
        else:raise AssertionError("WRONG_EXECUTABLE_ACCEPTED")
        try:_parse_spell_xml(b'<!DOCTYPE foo [<!ENTITY z "x">]><spell_query />',action)
        except ValueError as e:assert str(e)=="SPELL_QUERY_XML_DTD_FORBIDDEN"
        else:raise AssertionError("DTD_ACCEPTED")
    print("SIMC_PINNED_DBC_XML_CATALOG_SELF_TEST=PASS SPECS=3 SYNTHETIC_ONLY")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--semantic-route",type=Path)
    p.add_argument("--max-queries",type=int,default=8)
    p.add_argument("--request-out",type=Path)
    p.add_argument("--self-test",action="store_true")
    opts=p.parse_args()
    if opts.self_test or opts.semantic_route is None:
        selftest()
        return
    route=json.loads(opts.semantic_route.read_text("utf-8"))
    request=make_query_plan(route,max_queries=opts.max_queries)
    rendered=json.dumps(request,sort_keys=True,indent=2)+"\n"
    if opts.request_out:
        opts.request_out.parent.mkdir(parents=True,exist_ok=True)
        opts.request_out.write_text(rendered,encoding="utf-8")
        print("WROTE_PINNED_SIMC_SPELL_QUERY_REQUEST")
    else:
        print(rendered)


if __name__=="__main__":
    main()
