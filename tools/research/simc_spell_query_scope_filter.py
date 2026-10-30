#!/usr/bin/env python3
"""Conservative, source-pinned class/spec/build-scope evidence for SimC DBC candidates.

Automatically read the *same exact* pinned profile bytes used to extract APL.
Compare SimC DBC <class>/<spec> labels with its actor/spec. Rank explicit
support and contradictions while retaining ALL original candidate IDs.
A positive scope label is neither a learned-talent proof nor an APL action ID.
No class-specific spell, talent, encounter, or action priority table.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from simc_apl_source_engine import _ACTOR, _profile_fields, sha
from simc_spell_query_catalog import (
    _SCHEMA as CATALOG_SCHEMA, link_catalog_candidates_to_route,
)
from simc_apl_semantic_resolver import _SCHEMA as ROUTE_SCHEMA

_SHA = re.compile(r"^[0-9a-f]{64}$")
_SCOPE_SCHEMA = "ZrotSimcPinnedProfileActorScopeV1"
_RESULT_SCHEMA = "ZrotSimcGenericDacCandidateScopeAssessmentV1"
_TALENT_KEYS = frozenset(("talents", "class_talents", "spec_talents",
                          "hero_talents", "talent", "talent_loadout",
                          "talent_export"))
# Stable lexical normalization used for class/spec label comparison only.
def _key(value):
    return re.sub(r"[^a-z0-9]+", "", value.lower()) if isinstance(value, str) else ""


def parse_pinned_profile_scope(profile_bytes: bytes, *,
                               expected_spec: str, expected_profile_sha256: str):
    if not isinstance(expected_profile_sha256, str) or not _SHA.fullmatch(expected_profile_sha256):
        raise ValueError("PROFILE_SCOPE_SHA_REQUIRED")
    if sha(profile_bytes) != expected_profile_sha256:
        raise ValueError("PROFILE_SCOPE_RAW_SHA_MISMATCH")
    try:
        contents = profile_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError("PROFILE_SCOPE_NOT_UTF8") from e
    fields = _profile_fields(contents)
    if fields["actor_count"] != 1:
        raise ValueError("PROFILE_SCOPE_SINGLE_ACTOR_REQUIRED")
    spec = fields["spec"]
    if not isinstance(spec, str) or spec != expected_spec:
        raise ValueError("PROFILE_SCOPE_SPEC_MISMATCH")
    actor = None
    talent_lines = []
    for line in contents.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if _ACTOR.match(line):
            actor = line.split("=", 1)[0].strip().lower()
        if "=" in line and line.split("=", 1)[0].strip().lower() in _TALENT_KEYS:
            talent_lines.append(line)
    if not actor or not _key(actor):
        raise ValueError("PROFILE_SCOPE_ACTOR_UNAVAILABLE")
    # Only a scope fingerprint. Parsing actual talent eligibility requires
    # the matching native SimC build and talent definition; not done here.
    fingerprint = sha("\n".join(talent_lines).encode()) if talent_lines else None
    return {
        "schema": _SCOPE_SCHEMA, "spec":spec,
        "profile_sha256":expected_profile_sha256,
        "actor_class_token":actor, "actor_class_label_key":_key(actor),
        "spec_label_key":_key(spec),
        "talent_directive_count":len(talent_lines),
        "talent_directives_sha256":fingerprint,
        "talent_selection_and_replacement_eligibility":"UNKNOWN_NOT_PARSED",
        "source_scope_provenance":"EXACT_PINNED_PROFILE_BYTES",
        "gameplay_rule_promotion":False,
    }


def _labels(candidate, kind):
    sub=candidate.get("dbc_subrecords")
    if not isinstance(sub,dict):
        raise ValueError("DBC_CANDIDATE_SCOPE_FIELDS_MISSING")
    rows=sub.get(kind)
    if not isinstance(rows,list):
        raise ValueError("DBC_SCOPE_LABELS_NOT_LIST")
    names=[]
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("DBC_SCOPE_LABEL_INVALID")
        name=row.get("name")
        if isinstance(name,str) and name.strip():
            names.append(name.strip())
    return sorted(set(names))


def _comparison(candidate,scope):
    class_names=_labels(candidate,"class")
    spec_names=_labels(candidate,"spec")
    class_key=scope["actor_class_label_key"]
    spec_key=scope["spec_label_key"]
    # Spec labels may be "Enhancement" or "Enhancement Shaman".
    # Only exact spellings in either order can positively support a match.
    spec_permitted={spec_key, spec_key+class_key, class_key+spec_key}
    class_match=any(_key(x)==class_key for x in class_names)
    spec_match=any(_key(x) in spec_permitted for x in spec_names)
    class_relation=("EXPLICIT_MATCH" if class_match else
                    "EXPLICIT_NONMATCH" if class_names else "UNSTATED")
    spec_relation=("EXPLICIT_MATCH" if spec_match else
                   "LABEL_NOT_EXACTLY_MATCHED" if spec_names else "UNSTATED")
    # Do not equate nonmatch with impossible: pet/racial/shared/synthetic
    # actions and SimC internal action implementations may differ from DBC.
    supports=class_match or spec_match
    conflict=class_relation=="EXPLICIT_NONMATCH"
    return {
        "spell_id":candidate["spell_id"],
        "original_name":candidate["spell_name"],
        "dbc_class_names":class_names,
        "dbc_spec_names":spec_names,
        "class_relation":class_relation,
        "spec_relation":spec_relation,
        "explicit_scope_support":supports,
        "explicit_class_nonmatch":conflict,
        "selection_status":("SUPPORT_WITH_CLASS_CONFLICT_REVIEW" if supports and conflict else
                            "EXPLICIT_SCOPE_SUPPORT_CANDIDATE" if supports else
                            "EXPLICIT_CLASS_NONMATCH_REVIEW" if conflict else
                            "NO_POSITIVE_SCOPE_EVIDENCE_RETAINED"),
        "apl_action_identity":"UNKNOWN",
        "build_talent_eligibility":"UNKNOWN",
        "readiness":"UNKNOWN",
    }


def assess_candidate_scope(route:dict,catalog:dict,scope:dict):
    if route.get("schema")!=ROUTE_SCHEMA or catalog.get("schema")!=CATALOG_SCHEMA:
        raise ValueError("SCOPE_ASSESSMENT_SCHEMA_INVALID")
    if scope.get("schema")!=_SCOPE_SCHEMA or scope.get("gameplay_rule_promotion") is not False:
        raise ValueError("SCOPE_PROFILE_CONTRACT_INVALID")
    for source,plan,actual in (
        ("profile",scope.get("profile_sha256"),catalog.get("source_profile_sha256")),
        ("spec",scope.get("spec"),catalog.get("spec")),
        ("route_profile",route.get("source_profile_sha256"),scope.get("profile_sha256")),
        ("route_apl",route.get("source_apl_sha256"),catalog.get("source_apl_sha256"))
    ):
        if not plan or plan!=actual:
            raise ValueError("SCOPE_SOURCE_IDENTITY_MISMATCH_"+source)
    if scope.get("source_scope_provenance")!="EXACT_PINNED_PROFILE_BYTES":
        raise ValueError("SCOPE_SOURCE_PROVENANCE_REQUIRED")
    if not scope.get("actor_class_label_key") or not scope.get("spec_label_key"):
        raise ValueError("SCOPE_CLASS_OR_SPEC_REQUIRED")
    join=link_catalog_candidates_to_route(route,catalog)
    by_token={r["query_token"]:r for r in catalog["spell_query_results"]}
    out=[]
    totals=Counter()
    for ref in join["action_candidates"]:
        token=ref["action_token"]
        record=by_token.get(token)
        evaluated=[_comparison(c,scope) for c in record["candidate_spells"]] if record else []
        original_ids=ref["spell_id_candidates"]
        if sorted(c["spell_id"] for c in evaluated)!=sorted(original_ids):
            raise ValueError("SCOPE_EVIDENCE_CANDIDATE_LOSS")
        positive=[c["spell_id"] for c in evaluated if c["explicit_scope_support"]]
        contradictions=[c["spell_id"] for c in evaluated if c["explicit_class_nonmatch"]]
        counts=Counter(c["selection_status"] for c in evaluated)
        totals.update(counts)
        out.append({
            "action_token":token,
            "original_candidate_ids":original_ids,
            "explicitly_supported_candidate_ids":positive,
            "class_nonmatch_candidate_ids":contradictions,
            "every_candidate_retained_for_review":True,
            "candidate_assessments":evaluated,
            "scope_status_counts":dict(sorted(counts.items())),
            "final_action_spell_id":"UNKNOWN",
        })
    assert len(out)==join["route_action_count"]
    return {
        "schema":_RESULT_SCHEMA,
        "spec":scope["spec"], "source_apl_sha256":route["source_apl_sha256"],
        "source_profile_sha256":scope["profile_sha256"],
        "simc_executable_sha256":catalog["simc_executable_sha256"],
        "actor_class_token":scope["actor_class_token"],
        "talent_directives_sha256":scope["talent_directives_sha256"],
        "talent_directive_count":scope["talent_directive_count"],
        "profile_scope_authority":"PINNED_SIMC_PROFILE_METADATA_ONLY",
        "candidate_scope_authority":"DBC_LABEL_COMPARISON_NOT_GAMEPLAY_VALIDATION",
        "total_source_actions":join["route_action_count"],
        "queried_action_count":join["queried_action_count"],
        "total_name_candidates":sum(len(x["original_candidate_ids"]) for x in out),
        "total_explicit_scope_support_candidates":sum(
            len(x["explicitly_supported_candidate_ids"]) for x in out),
        "total_class_nonmatch_candidates":sum(
            len(x["class_nonmatch_candidate_ids"]) for x in out),
        "total_candidates_preserved":sum(
            len(x["candidate_assessments"]) for x in out),
        "scope_status_counts":dict(sorted(totals.items())),
        "action_candidate_scope_assessments":out,
        "all_action_spell_ids_uncertified":True,
        "all_readiness":"UNKNOWN",
        "native_foreground_equivalence":"NOT_RUN",
        "blizzard_patch_live_authority":"NOT_VERIFIED",
        "gameplay_rule_promotion":False,
    }


def selftest():
    from simc_apl_source_engine import ingest_actions
    from simc_apl_conditional_ir import compile_structural_ir
    from simc_apl_observability_contract import compile_requirements
    from simc_apl_semantic_resolver import compile_semantic_route_plan
    from simc_spell_query_catalog import build_catalog,make_query_plan
    for cls,spec,action in (
        ("shaman","enhancement","alpha_strike"),
        ("warrior","fury","omega_strike"),
        ("deathknight","unholy","gamma_strike"),
    ):
        raw=(f'{cls}="Fixture"\nspec={spec}\n'
             "talents=123456\n"
             f"actions={action}\n"
             "actions+=/fallback\n").encode()
        pin=sha(raw)
        scope=parse_pinned_profile_scope(raw,expected_spec=spec,
                                         expected_profile_sha256=pin)
        assert scope["talent_directive_count"]==1
        assert scope["talent_directives_sha256"]
        model=ingest_actions(raw,expected_spec=spec,
                             profile_sha256=pin,profile_spec=spec,
                             simc_executable_sha256="a"*64,
                             profile_dependencies_verified=True)
        route=compile_semantic_route_plan(
            compile_requirements(compile_structural_ir(model)))
        request=make_query_plan(route,max_queries=1)
        assert request["selected_query_tokens"]==[action]
        name=action.replace("_"," ").title()
        xml=(f'<spell_query>'
             f'<spell id="101" name="{name}"><class name="{cls.title()}" /><spec name="{spec.title()}" /></spell>'
             f'<spell id="202" name="{name}"><class name="Another Class" /></spell>'
             f'<spell id="303" name="{name}" />'
             f'</spell_query>').encode()
        catalog=build_catalog(request,binary_sha256="a"*64,
                              image_digest="sha256:"+"b"*64,
                              query_blobs={action:xml},query_sha256={action:sha(xml)})
        out=assess_candidate_scope(route,catalog,scope)
        assert out["total_name_candidates"]==3
        assert out["total_candidates_preserved"]==3
        assert out["total_explicit_scope_support_candidates"]==1
        assert out["total_class_nonmatch_candidates"]==1
        entry=next(r for r in out["action_candidate_scope_assessments"]
                   if r["action_token"]==action)
        assert entry["original_candidate_ids"]==[101,202,303]
        assert entry["explicitly_supported_candidate_ids"]==[101]
        assert entry["final_action_spell_id"]=="UNKNOWN"
        assert out["all_readiness"]=="UNKNOWN"
        assert out["gameplay_rule_promotion"] is False
        altered=dict(scope,profile_sha256="0"*64)
        try:assess_candidate_scope(route,catalog,altered)
        except ValueError as e:assert str(e)=="SCOPE_SOURCE_IDENTITY_MISMATCH_profile"
        else:raise AssertionError("BAD_PROFILE_PIN_ACCEPTED")
        try:parse_pinned_profile_scope(raw+b" ",expected_spec=spec,
                                       expected_profile_sha256=pin)
        except ValueError as e:assert str(e)=="PROFILE_SCOPE_RAW_SHA_MISMATCH"
        else:raise AssertionError("TAMPERED_PROFILE_ACCEPTED")
        try:parse_pinned_profile_scope(raw.replace(f"spec={spec}".encode(),b"spec=other"),
                                       expected_spec=spec,
                                       expected_profile_sha256=sha(raw.replace(f"spec={spec}".encode(),b"spec=other")))
        except ValueError as e:assert str(e)=="PROFILE_SCOPE_SPEC_MISMATCH"
        else:raise AssertionError("CROSS_SPEC_PROFILE_ACCEPTED")
        assert not scope["gameplay_rule_promotion"]
    print("SIMC_PINNED_PROFILE_SCOPE_FILTER_SELF_TEST=PASS SPECS=3 SYNTHETIC_ONLY")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--profile",type=Path)
    p.add_argument("--profile-sha256")
    p.add_argument("--spec")
    args=p.parse_args()
    if args.self_test or not args.profile:
        selftest()
        return
    if not args.profile_sha256 or not args.spec:
        p.error("--profile-sha256 and --spec required with --profile")
    print(json.dumps(parse_pinned_profile_scope(
        args.profile.read_bytes(),expected_spec=args.spec,
        expected_profile_sha256=args.profile_sha256),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
