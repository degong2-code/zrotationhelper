#!/usr/bin/env python3
"""Research-only pinned public SimC binary spell_query end-to-end exercise.

Requires Docker on CI runner. Creates and hash-checks ephemeral XML only,
uploads no raw profile, DBC XML, logs or WCL credentials. No class logic:
profile names/specs are fixtures; query names come from each profile's APL.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"/"research"))
from simc_apl_source_engine import ingest_actions
from simc_apl_conditional_ir import compile_structural_ir
from simc_apl_observability_contract import compile_requirements
from simc_apl_semantic_resolver import compile_semantic_route_plan
from simc_spell_query_catalog import build_catalog,make_query_plan,sha,link_catalog_candidates_to_route
from simc_spell_query_scope_filter import parse_pinned_profile_scope,assess_candidate_scope

IMAGE="simulationcraftorg/simc@sha256:a6cfbc243456825d2dbecd607fe025948680219f4b4348603ed77a081b5f5895"
PUBLIC_FIXTURES=(("enhancement","MID2_Shaman_Enhancement"),
                 ("fury","MID2_Warrior_Fury"),
                 ("unholy","MID2_Death_Knight_Unholy"))


def run_docker(*args,capture=True):
    result=subprocess.run(
        ["docker","run","--rm",*args],check=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE,timeout=75)
    return result.stdout


def run():
    subprocess.run(["docker","pull",IMAGE],check=True,
                   stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=180)
    binary_sha=run_docker("--entrypoint","sha256sum",IMAGE,"/app/SimulationCraft/simc").decode().split()[0]
    if not re.fullmatch(r"[a-f0-9]{64}",binary_sha):
        raise ValueError("SIMC_PINNED_BINARY_SHA_INVALID")
    summaries=[]
    with TemporaryDirectory(prefix="zrot_public_dbc_",dir=os.environ.get("RUNNER_TEMP")) as td:
        root=Path(td)
        for spec,profile_stem in PUBLIC_FIXTURES:
            profile=run_docker("--entrypoint","cat",IMAGE,
                               f"/app/SimulationCraft/profiles/MID2/{profile_stem}.simc")
            profile_sha=sha(profile)
            scope=parse_pinned_profile_scope(profile,expected_spec=spec,
                                             expected_profile_sha256=profile_sha)
            model=ingest_actions(profile,expected_spec=spec,
                                 profile_sha256=profile_sha,
                                 simc_executable_sha256=binary_sha,
                                 profile_spec=spec,profile_dependencies_verified=True)
            route=compile_semantic_route_plan(
                compile_requirements(compile_structural_ir(model)))
            request=make_query_plan(route,max_queries=5)
            if request["source_simc_executable_sha256"]!=binary_sha:
                raise ValueError("SIMC_BINARY_IDENTITY_CHANGED")
            blobs={}
            hashes={}
            for i,token in enumerate(request["selected_query_tokens"]):
                filename=f"{spec}_{i}.xml"
                output=root/filename
                # No interpolated shell command or user-provided URL.
                run_docker("-v",str(root)+":/capture",IMAGE,
                           "display_build=0",f"spell_query=spell.name={token}",
                           f"spell_query_xml_output_file=/capture/{filename}",
                           capture=False)
                raw=output.read_bytes()
                if not raw:
                    raise ValueError("SIMC_SPELL_QUERY_EMPTY_OUTPUT")
                blobs[token]=raw
                hashes[token]=sha(raw)
            catalog=build_catalog(request,binary_sha256=binary_sha,
                                  image_digest=IMAGE.split("@",1)[1],
                                  query_blobs=blobs,query_sha256=hashes)
            joined=link_catalog_candidates_to_route(route,catalog)
            scoped=assess_candidate_scope(route,catalog,scope)
            if scoped["total_candidates_preserved"]!=scoped["total_name_candidates"]:
                raise AssertionError("CANDIDATE_SCOPE_EVIDENCE_LOSS")
            if scoped["all_readiness"]!="UNKNOWN" or not scoped["all_action_spell_ids_uncertified"]:
                raise AssertionError("SCOPE_FALSIFIED_GAMEPLAY_AUTHORITY")
            if catalog["source_query_token_count"]!=5:
                raise AssertionError("PUBLIC_SAMPLE_QUERY_COUNT_NOT_MET")
            statuses=Counter(r["resolution_status"] for r in catalog["spell_query_results"])
            summaries.append({
                "spec":spec,"source_profile_sha256":profile_sha,
                "source_apl_sha256":model["apl_sha256"],
                "source_row_count":model["apl_row_count"],
                "actor_class_token":scope["actor_class_token"],
                "talent_directive_count":scope["talent_directive_count"],
                "talent_directives_sha256":scope["talent_directives_sha256"],
                "scope_positive_candidate_count":scoped["total_explicit_scope_support_candidates"],
                "scope_class_nonmatch_candidate_count":scoped["total_class_nonmatch_candidates"],
                "scope_status_counts":scoped["scope_status_counts"],
                "scope_candidate_retained_count":scoped["total_candidates_preserved"],
                "scope_query_details":[{
                    "query_token":r["action_token"],
                    "original_name_candidate_count":len(r["original_candidate_ids"]),
                    "explicitly_scope_supported_count":len(r["explicitly_supported_candidate_ids"]),
                    "class_nonmatch_count":len(r["class_nonmatch_candidate_ids"]),
                    "all_candidate_ids_retained":r["every_candidate_retained_for_review"],
                } for r in scoped["action_candidate_scope_assessments"]
                  if r["action_token"] in request["selected_query_tokens"]],
                "selected_action_tokens":request["selected_query_tokens"],
                "query_result_summary":dict(sorted(statuses.items())),
                "source_action_requirements_count":joined["route_action_count"],
                "unqueried_action_requirements":joined["route_action_count"]-joined["queried_action_count"],
                "all_action_readiness":joined["all_readiness"],
                "candidate_spell_count":sum(r["exact_name_candidate_count"]
                                           for r in catalog["spell_query_results"]),
                "xml_receipts":[{"token":r["query_token"],
                                  "xml_sha256":r["raw_xml_sha256"],
                                  "xml_bytes":r["raw_xml_bytes"],
                                  "raw_spell_count":r["xml_spell_count"],
                                  "exact_name_candidates":r["exact_name_candidate_count"]}
                                 for r in catalog["spell_query_results"]],
                "status":"PINNED_NATIVE_DBC_XML_EXTRACTED_CANDIDATES_ONLY",
                "ability_runtime_mapping":"NOT_VERIFIED",
                "readiness":"UNKNOWN",
                "strict_pre":"NOT_RUN",
            })
    report={
        "schema":"ZrotSimcPublicPinnedMechanicsCatalogProbeV1",
        "image_digest":IMAGE.split("@",1)[1],
        "simc_executable_sha256":binary_sha,
        "fixture_count":len(PUBLIC_FIXTURES),
        "total_query_count":sum(len(x["selected_action_tokens"]) for x in summaries),
        "fixture_summaries":summaries,
        "source_kind":"PINNED_PUBLIC_SIMC_BINARY_SPELL_QUERY",
        "blizzard_live_mechanics_authority":"NOT_VERIFIED",
        "action_identity_resolution":"CANDIDATE_NAMES_ONLY",
        "native_foreground_parity":"NOT_RUN",
        "wcl_validation":"NOT_RUN",
        "gameplay_rule_promotion":False,
        "private_raw_artifacts_uploaded":False,
    }
    assert report["total_query_count"]==15
    summary_path=os.environ.get("ZROT_PUBLIC_CATALOG_SUMMARY")
    rendered=json.dumps(report,sort_keys=True,indent=2)+"\n"
    print("PINNED_SIMC_PUBLIC_DBC_SPELL_QUERY_NATIVE=PASS QUERIES=15 SPECS=3")
    print(rendered)
    if summary_path:
        Path(summary_path).write_text(rendered,encoding="utf-8")


if __name__=="__main__":
    run()
