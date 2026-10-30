#!/usr/bin/env python3
"""Pinned public native SimC effective-APL action-instance ID probe.

The selected spell queries are sourced from names actually present in the
same actor's native JSON2 action_sequence AND the export of that very run's
effective APL. No per-spec ability knowledge. Do not interpret the sample as
a foreground decision, or same-time snapshot as Strict PRE. Raw data stays
inside a temporary CI directory; upload only hashes/counts/diagnostics.
"""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/"tools"/"research"))
from simc_spell_query_public_probe import IMAGE, PUBLIC_FIXTURES, run_docker
from simc_apl_source_engine import ingest_actions
from simc_apl_conditional_ir import compile_structural_ir
from simc_apl_observability_contract import compile_requirements
from simc_apl_semantic_resolver import compile_semantic_route_plan
from simc_spell_query_catalog import make_query_plan, build_catalog, sha
from simc_native_json_sequence import extract_json_sequence
from simc_native_action_id_reconcile import reconcile_native_action_ids

N_QUERIES=5
SEED=1247695


def observed_source_query_plan(route,sequence,max_queries):
    """Native-output-guided query sample; not an inferred rotation priority."""
    valid={x["action_token"] for x in route["readiness"]}
    tokens=sorted({e["action_token"]
                   for e in sequence["precombat_sequence"]+sequence["combat_sequence"]
                   if e["record_kind"]=="SAMPLE_ACTION"
                   and type(e["numeric_action_id"]) is int
                   and e["numeric_action_id"]>0
                   and e["action_token"] in valid
                   and re.fullmatch(r"[a-z][a-z0-9_]{1,95}",e["action_token"])})
    selected=tokens[:max_queries]
    if not selected:
        raise ValueError("NO_POSITIVE_NATIVE_ACTION_IDS_FOR_SOURCE_APL_TOKENS")
    request=make_query_plan(route,max_queries=max_queries)
    request["selected_query_tokens"]=selected
    request["skipped_or_deferred_action_count"]=len(route["readiness"])-len(selected)
    request["selection_policy"]="NATIVE_SAMPLED_ACTION_TOKEN_INTERSECTION_WITH_EXACT_EFFECTIVE_APL"
    request["native_sequence_sha256"]=sequence["source_native_json2_sha256"]
    return request


def run():
    binary=run_docker("--entrypoint","sha256sum",IMAGE,"/app/SimulationCraft/simc")
    binary_sha=binary.decode().split()[0]
    if not re.fullmatch(r"[a-f0-9]{64}",binary_sha):
        raise ValueError("INVALID_NATIVE_BINARY_SHA")
    fixtures=[]
    with TemporaryDirectory(prefix="zrot_native_id_",dir=os.environ.get("RUNNER_TEMP")) as td:
        root=Path(td)
        for spec,stem in PUBLIC_FIXTURES:
            path=root/spec
            path.mkdir()
            profile=run_docker("--entrypoint","cat",IMAGE,
                               f"/app/SimulationCraft/profiles/MID2/{stem}.simc")
            profile_sha=sha(profile)
            # The simulator consumes its own pinned built-in public profile.
            run_docker("-v",str(path)+":/capture",IMAGE,
                       f"profiles/MID2/{stem}.simc",
                       "iterations=1","threads=1","calculate_scale_factors=0",
                       "max_time=60","vary_combat_length=0",f"seed={SEED}",
                       "log=1","log_spell_id=1","report_details=1",
                       "save_actions=/capture/simc_effective_actions.simc",
                       "json2=/capture/simc_native_sequence.json,full_states=1",
                       "output=/capture/simc_native_log.txt",capture=False)
            filenames=("simc_effective_actions.simc","simc_native_log.txt",
                       "simc_native_sequence.json")
            blobs={f:(path/f).read_bytes() for f in filenames}
            if not all(blobs.values()):
                raise ValueError("NATIVE_ID_CAPTURE_FILE_EMPTY")
            receipt={
                "schema":"ZrotSimcNativeReferenceCaptureV1",
                "status":"SIMC_NATIVE_CAPTURED_UNPARSED",
                "simc_spec":spec,"profile_sha256":profile_sha,
                "simc_executable_sha256":binary_sha,
                "effective_apl_sha256":sha(blobs["simc_effective_actions.simc"]),
                "native_log_sha256":sha(blobs["simc_native_log.txt"]),
                "native_json2_sha256":sha(blobs["simc_native_sequence.json"]),
                "outputs":[{"file":f,"sha256":sha(blobs[f]),"bytes":len(blobs[f])}
                           for f in filenames],
            }
            (path/"simc_reference_receipt.json").write_text(json.dumps(receipt))
            sequence=extract_json_sequence(path)
            # Crucial: construct source route from this run's EFFECTIVE APL,
            # not from the Docker profile's different original raw bytes.
            model=ingest_actions(blobs["simc_effective_actions.simc"],
                                 expected_spec=spec,
                                 profile_sha256=profile_sha,
                                 simc_executable_sha256=binary_sha,
                                 profile_spec=spec,
                                 profile_dependencies_verified=True)
            route=compile_semantic_route_plan(
                compile_requirements(compile_structural_ir(model)))
            if route["source_apl_sha256"]!=sequence["source_apl_sha256"]:
                raise ValueError("EFFECTIVE_APL_NATIVE_SEQUENCE_MISMATCH")
            request=observed_source_query_plan(route,sequence,N_QUERIES)
            raw_queries={}
            hashes={}
            for i,token in enumerate(request["selected_query_tokens"]):
                file_name=f"query_{i}.xml"
                run_docker("-v",str(path)+":/capture",IMAGE,
                           "display_build=0",f"spell_query=spell.name={token}",
                           f"spell_query_xml_output_file=/capture/{file_name}",
                           capture=False)
                raw_queries[token]=(path/file_name).read_bytes()
                hashes[token]=sha(raw_queries[token])
            catalog=build_catalog(request,binary_sha256=binary_sha,
                                  image_digest=IMAGE.split("@",1)[1],
                                  query_blobs=raw_queries,query_sha256=hashes)
            evidence=reconcile_native_action_ids(route,catalog,sequence)
            if evidence["sampled_valid_source_action_events"]<1:
                raise ValueError("NATIVE_ID_NO_VALID_SOURCE_SAMPLE")
            if evidence["source_action_identity_certified"] is not False or evidence["all_readiness"]!="UNKNOWN":
                raise ValueError("NATIVE_ID_ACCIDENTAL_GAMEPLAY_CERTIFICATION")
            if evidence["queried_action_count"]!=len(request["selected_query_tokens"]):
                raise ValueError("NATIVE_ID_QUERY_COVERAGE_ERROR")
            fixtures.append({
                "spec":spec,
                "source_profile_sha256":profile_sha,
                "source_effective_apl_sha256":route["source_apl_sha256"],
                "source_native_json2_sha256":sequence["source_native_json2_sha256"],
                "native_precombat_sequence_count":sequence["precombat_count"],
                "native_combat_sequence_count":sequence["combat_count"],
                "source_effective_apl_action_tokens":len(route["readiness"]),
                "native_source_matched_samples":evidence["sampled_valid_source_action_events"],
                "native_unmapped_event_tokens":evidence["sampled_unmapped_native_event_tokens"],
                "sampled_query_tokens":request["selected_query_tokens"],
                "queried_action_count":evidence["queried_action_count"],
                "reconciliation_status_counts":evidence["reconciliation_status_counts"],
                "query_evidence":[{
                    "action_token":r["action_token"],
                    "native_action_ids_and_counts":r["native_action_object_ids_and_counts"],
                    "dbc_candidate_ids":r["source_dbc_spell_id_candidates"],
                    "result":r["status"],
                } for r in evidence["action_id_evidence"]
                  if r["action_token"] in request["selected_query_tokens"]],
                "identity_certified":False,
                "readiness":"UNKNOWN",
                "same_time_pre_state_certified":False,
            })
    report={
        "schema":"ZrotPinnedPublicSimcNativeActionObjectIdEvidenceV1",
        "image_digest":IMAGE.split("@",1)[1],
        "simc_executable_sha256":binary_sha,
        "seed":SEED,
        "fixture_count":len(fixtures),
        "query_count":sum(r["queried_action_count"] for r in fixtures),
        "fixtures":fixtures,
        "data_scope":"NATIVE_ACTION_SEQUENCE_OBJECT_ID_VS_DBC_NAME_CANDIDATES",
        "foreground_selection_certification":"NOT_RUN",
        "native_decision_parity":"NOT_VALIDATED",
        "strict_pre":"NOT_RUN",
        "wcl_blind_discovery":"NOT_RUN",
        "gameplay_rule_promotion":False,
        "raw_native_files_uploaded":False,
    }
    output=json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    print("PINNED_NATIVE_SIMC_ACTION_INSTANCE_ID_CATALOG_COMPARISON=PASS "
          f"SPECS={len(fixtures)} QUERIES={report['query_count']}")
    print(output)
    dest=os.environ.get("ZROT_PUBLIC_NATIVE_ID_SUMMARY")
    if dest:
        Path(dest).write_text(output,encoding="utf-8")


if __name__=="__main__":
    run()
