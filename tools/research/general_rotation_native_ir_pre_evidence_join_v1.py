#!/usr/bin/env python3
"""Generic SimC source PRE -> General Rotation IR evidence join.

A portable original-method source marker fixture is replayed without a new
Native C++ build. The generic SimC APL parser, independent IF evaluator,
priority frontier, and generic open-world proof bridge are reused unchanged.

This joins a real observed IF decision with its exact source IR row:
source Git blob, list, ordinal, row SHA256, original occurrence and timestamp.
IF_FALSE / IF_TRUE mean only original source guard outcomes; neither implies
full skill READY nor correct player priority. An optional SpecAdapter supplies
class-owned, independently source-grounded guard semantics.

SimC original-method PRE is NOT WCL strict PRE. Native observed IF/ready is
only a comparator after independent source-operand replay. No fake WCL state
or dummy mistakes are emitted. Safe no-args mode is synthetic.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import gzip
from hashlib import sha256
import importlib
import json
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import parse_profile,git_blob,canonical
from general_rotation_source_hypothesis_ir_v1 import compile_profile
from simc_native_if_pre_operand_replay_v1 import analyze_trace as source_if_ledger
from simc_native_if_false_priority_frontier_v1 import (
    source_if_samples,analyze_trace as priority_frontier
)
from simc_native_decision_proof_bridge_v1 import NativeProofBridge

SCHEMA="ZrotGeneralRotationNativeSourcePreIrEvidenceJoinV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
FIXTURE_SCHEMA="ZrotGenericSourceMarkedPortableNativePreFixtureV1"
SHA_PATTERN=re.compile(r"^[0-9a-f]{64}$")
ADAPTER_PATTERN=re.compile(
    r"^simc_native_[a-z0-9_]+_adapter_v[0-9]+:[A-Z][A-Za-z0-9_]+$"
)
class NativeIREvidenceError(ValueError):pass

def digest(b:bytes)->str:return sha256(b).hexdigest()

def exact_ir_sample(model:dict,sample:dict,case:str,occurrence:int)->dict:
    k=sample["key"]
    if len(k)!=4 or not isinstance(k[0],int) or not isinstance(k[2],int):
        raise NativeIREvidenceError("ACTUAL_SAMPLE_POINTER_MALFORMED")
    graph=model["source_only_priority_graph"]["lists"]
    if k[1] not in graph or not 1<=k[2]<=len(graph[k[1]]):
        raise NativeIREvidenceError("SOURCE_LIST_OR_ROW_MISSING")
    row=graph[k[1]][k[2]-1]
    if row["identity"]["source_line_sha256"]!=sample["source_sha256"]:
        raise NativeIREvidenceError("SOURCE_ROW_HASH_MISMATCH")
    cond=row["conditions"].get("if")
    if (cond is None or cond["raw_expression"]!=sample["source_if"] or
        cond["symbols"]!=sample["symbols"]):
        raise NativeIREvidenceError("TYPED_IR_CONDITION_OR_SYMBOLS_MISMATCH")
    value=sample["independent_IF_bool"]
    if value not in (None,0,1):
        raise NativeIREvidenceError("NON_TRISTATE_INDEPENDENT_IF")
    if value is not None and value!=sample["Native_IF_bool_POST_comparator"]:
        raise NativeIREvidenceError("INDEPENDENT_SOURCE_IF_VS_NATIVE_CONFLICT")
    return {
        "case":case,
        "source_spec":model["spec_key"],
        "source_list":k[1],
        "source_index":k[2]-1,
        "source_row_sha256":sample["source_sha256"],
        "source_action":row["action"],
        "source_action_kind":row["kind"],
        "at_simc_ms":k[0],
        "native_source_name_FOR_IDENTITY_ONLY":k[3],
        "same_source_key_occurrence":occurrence,
        "if_result":("PROVEN_TRUE" if value==1 else
                     "PROVEN_FALSE" if value==0 else "UNKNOWN"),
        "source_if":sample["source_if"],
        "source_symbols":sample["symbols"],
        "Native_IF_comparator_not_evidence":True,
        "source_only_not_real_WoW_state":True,
        "full_skill_READY":"UNKNOWN",
        "WCL_priority_optimality":"UNKNOWN",
        "dummy_practice_error":"UNKNOWN",
    }

def summarize(model:dict,case:str,samples:list[dict])->dict:
    by_key=defaultdict(int)
    by_row=defaultdict(Counter)
    out=[]
    for row in samples:
        key=tuple(row["key"])
        occurrence=by_key[key]
        by_key[key]+=1
        item=exact_ir_sample(model,row,case,occurrence)
        result=item["if_result"]
        index=(item["source_list"],item["source_index"],item["source_row_sha256"])
        by_row[index][result]+=1
        out.append(item)
    counts=Counter(r["if_result"] for r in out)
    row_evidence=[
        {"source_list":key[0],"source_index":key[1],
         "source_row_sha256":key[2],
         "observed_source_IF":dict(sorted(counts.items())),
         "full_skill_READY":"UNKNOWN"}
        for key,counts in sorted(by_row.items())
    ]
    return {
        "actual_source_IF_evaluations":len(samples),
        "independent_AST_IF_outcomes":dict(sorted(counts.items())),
        "observed_source_rows_with_if":len(row_evidence),
        "per_source_row":row_evidence,
        "bounded_exact_occurrence_examples":out[:18],
        "all_non_decidable_conditions_UNKNOWN":True,
    }

def read_case(root:Path,meta:dict)->tuple[str,dict]:
    path=Path(meta["path"])
    if path.is_absolute() or len(path.parts)!=1 or path.suffix!=".gz":
        raise NativeIREvidenceError("UNSAFE_PORTABLE_FIXTURE_PATH")
    stored=(root/path).read_bytes()
    sm=meta["source_meta"]
    if (len(stored)!=sm["compressed_bytes"] or
        digest(stored)!=sm["portable_gzip_sha256"]):
        raise NativeIREvidenceError("COMPRESSED_SOURCE_FIXTURE_FINGERPRINT_CHANGED")
    if sm["source_marker_bytes"]>32_000_000 or len(stored)>16_000_000:
        raise NativeIREvidenceError("PORTABLE_FIXTURE_UNBOUNDED")
    raw=gzip.decompress(stored)
    if len(raw)!=sm["source_marker_bytes"] or digest(raw)!=sm["filtered_source_markers_sha256"]:
        raise NativeIREvidenceError("DECOMPRESSED_SOURCE_MARKER_BYTES_CHANGED")
    if (raw.count(b"\n")!=sm["source_marker_lines"] or
        any(b"ZROT_" not in line for line in raw.splitlines())):
        raise NativeIREvidenceError("SOURCE_MARKER_LINE_COUNT_OR_CONTENT_CHANGED")
    return raw.decode("utf-8"),meta["equivalence"]["marker_counts"]

def load_adapter_factory(source:str|None):
    if source is None:return None
    if not ADAPTER_PATTERN.fullmatch(source):
        raise NativeIREvidenceError("SPEC_ADAPTER_NOT_A_SOURCE_PINNED_MODULE_CLASS")
    module_name,cls_name=source.split(":",1)
    try:cls=getattr(importlib.import_module(module_name),cls_name)
    except (ImportError,AttributeError) as e:
        raise NativeIREvidenceError("SPEC_ADAPTER_IMPORT_NOT_AVAILABLE") from e
    if not callable(cls):
        raise NativeIREvidenceError("SPEC_ADAPTER_IS_NOT_A_FACTORY")
    return cls

def run(profile:Path,meta:dict,fixture_dir:Path,expect_manifest:str,
        adapter_factory=None)->dict:
    if (not SHA_PATTERN.fullmatch(expect_manifest) or
        not SHA_PATTERN.fullmatch(meta.get("git_blob",""))):
        raise NativeIREvidenceError("SOURCE_PROFILE_AND_MANIFEST_PIN_REQUIRED")
    raw_profile=profile.read_bytes()
    if git_blob(raw_profile)!=meta["git_blob"]:
        raise NativeIREvidenceError("OFFICIAL_PROFILE_GIT_BLOB_CHANGED")
    model=compile_profile(raw_profile,meta)
    ir=parse_profile(raw_profile,require_source=True,
                     expected_git_blob=meta["git_blob"])
    root=fixture_dir.resolve(strict=True)
    man=(root/"manifest.json").read_bytes()
    if digest(man)!=expect_manifest:
        raise NativeIREvidenceError("PORTABLE_SOURCE_MANIFEST_SHA256_MISMATCH")
    manifest=json.loads(man)
    if (manifest["schema"]!=FIXTURE_SCHEMA or
        manifest["profile_git_blob"]!=meta["git_blob"] or
        manifest["source_action_line_count"]!=model["coverage"]["source_action_rows"] or
        not manifest["all_original_vs_compact_generic_replay_exact"] or
        not manifest["source_markers_only"]):
        raise NativeIREvidenceError("PORTABLE_SOURCE_MANIFEST_CONTRACT_DRIFT")
    if not manifest["cases"]:
        raise NativeIREvidenceError("PORTABLE_SOURCE_NO_CASES")
    combined=Counter()
    totals=Counter()
    front_totals=Counter()
    generic_totals=Counter()
    results={}
    for name,case in sorted(manifest["cases"].items()):
        trace,source_marker_counts=read_case(root,case)
        prev=source_if_ledger(trace,ir)
        samples=source_if_samples(trace,ir,prev)
        if (prev["counts"]["all_native_action_ready_attempts"]!=source_marker_counts["native_attempt"]
            or len(samples)!=source_marker_counts["source_if_fact"]):
            raise NativeIREvidenceError("SAMPLE_OR_NATIVE_SOURCE_ATTEMPT_COUNTS_CHANGED")
        adapter=adapter_factory() if adapter_factory else None
        proof=NativeProofBridge()
        frontier=priority_frontier(trace,ir,samples,spec_adapter=adapter,
                                   proof_bridge=proof)
        counts=frontier["counts"]
        if (counts["Native_action_ready_attempts"]!=source_marker_counts["native_attempt"]
            or counts["real_source_IF_samples"]!=len(samples)):
            raise NativeIREvidenceError("FRONTIER_SOURCE_PRE_COUNTS_DRIFT")
        combined.update(frontier["independent_candidate_exclusion_reasons"])
        totals.update({
            "Native_action_ready_attempts":counts["Native_action_ready_attempts"],
            "source_IF_evaluations":len(samples),
        })
        front_totals.update(frontier["foreground_prefix_screening"])
        generic_totals.update(frontier["generic_open_world_proof"]["counts"])
        evidence=summarize(model,name,samples)
        results[name]={
            **evidence,
            "fixture_marker_counts":source_marker_counts,
            "actual_original_IF_evaluation_ledger_SHA256":digest(canonical(
                prev["all_native_if_pre_fact_ledger"])),
            "native_source_frontier_counts":counts,
            "native_source_foreground_partial_prefix":frontier["foreground_prefix_screening"],
            "native_source_proof_counters":frontier["generic_open_world_proof"]["counts"],
            "original_source_method_guard_and_selection_trace_replayed":True,
            "source_priority_order_optimality":"UNKNOWN",
        }
        totals.update(evidence["independent_AST_IF_outcomes"])
    if totals["Native_action_ready_attempts"]<=0 or totals["source_IF_evaluations"]<=0:
        raise NativeIREvidenceError("SOURCE_EVIDENCE_COHORT_EMPTY")
    if (generic_totals["attempts"]!=totals["Native_action_ready_attempts"] or
        generic_totals.get("proof_READY",0)!=0):
        raise NativeIREvidenceError("UNEXPECTED_ACTUAL_GENERIC_FULL_READY_PROOF")
    return {
        "schema":SCHEMA,"policy":POLICY,
        "source_spec":model["spec_key"],"source_class":model["class_key"],
        "official_profile_git_blob":model["source_git_blob"],
        "portable_manifest_sha256":expect_manifest,
        "source_IR_source_action_rows":model["coverage"]["source_action_rows"],
        "source_only_not_real_WoW_state":True,
        "cases":results,
        "totals":dict(sorted(totals.items())),
        "source_frontier_partial_prefix":dict(sorted(front_totals.items())),
        "source_generic_proof_counts":dict(sorted(generic_totals.items())),
        "independent_exclusion_reasons":dict(sorted(combined.items())),
        "Native_comparator_not_independent_IF_input":True,
        "real_opening_cast_sequence_verified":False,
        "complete_positive_ability_READY_proven":False,
        "WCL_independent_blind_holdout_proven":False,
        "real_target_dummy_error_proven":False,
        "WCL_API_calls":0,"MAIN_promoted":False,
    }

def selftest()->dict:
    from simc_apl_semantic_ir_v2 import git_blob
    raw=(b"actions=first,if=active_enemies>=2\n"
         b"actions+=/second,if=rage>=20\n")
    model=compile_profile(raw,{"key":"alpha","class_key":"class_alpha","git_blob":git_blob(raw)})
    sha=model["source_only_priority_graph"]["lists"]["default"][0]["identity"]["source_line_sha256"]
    base={"key":(100,"default",1,"first"),"source_sha256":sha,
          "source_if":"active_enemies>=2","symbols":["active_enemies"],
          "Native_IF_bool_POST_comparator":0}
    neg=exact_ir_sample(model,dict(base,independent_IF_bool=0),"single",0)
    assert neg["if_result"]=="PROVEN_FALSE"
    yes=exact_ir_sample(model,dict(base,independent_IF_bool=1,
                    Native_IF_bool_POST_comparator=1),"single",1)
    assert yes["if_result"]=="PROVEN_TRUE"
    unk=exact_ir_sample(model,dict(base,independent_IF_bool=None),"single",2)
    assert unk["if_result"]=="UNKNOWN"
    summary=summarize(model,"single",[
        dict(base,independent_IF_bool=0),
        dict(base,independent_IF_bool=0),
        dict(base,independent_IF_bool=None)])
    assert summary["independent_AST_IF_outcomes"]["PROVEN_FALSE"]==2
    assert summary["bounded_exact_occurrence_examples"][1]["same_source_key_occurrence"]==1
    bad=[
        dict(base,source_sha256="a"*64,independent_IF_bool=0),
        dict(base,source_if="rage<100",independent_IF_bool=0),
        dict(base,key=(100,"default",4,"first"),independent_IF_bool=0),
        dict(base,independent_IF_bool=1),
    ]
    for item in bad:
        try:exact_ir_sample(model,item,"single",0)
        except NativeIREvidenceError:pass
        else:raise AssertionError("UNPINNED_PRE_IF_TO_IR_JOIN_ACCEPTED")
    try:load_adapter_factory("os:system")
    except NativeIREvidenceError:pass
    else:raise AssertionError("UNRESTRICTED_DYNAMIC_ADAPTER_ACCEPTED")
    assert load_adapter_factory(None) is None
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":13,"same_timestamp_duplicate_occurrence_kept":True,
        "actual_Native_marker_fixture_NOT_RUN":True,
        "original_SimC_CXX_NOT_BUILT":True,
        "WCL_API_calls":0
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--profile-key")
    p.add_argument("--class-key")
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--fixture-dir",type=Path)
    p.add_argument("--expected-manifest-sha256")
    p.add_argument("--spec-adapter")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    fields=(a.official_profile,a.profile_key,a.class_key,a.expected_profile_git_blob,
            a.fixture_dir,a.expected_manifest_sha256)
    if not any(fields):
        result=selftest()
    elif all(fields):
        factory=load_adapter_factory(a.spec_adapter)
        result=run(a.official_profile,{"key":a.profile_key,"class_key":a.class_key,
                   "git_blob":a.expected_profile_git_blob},a.fixture_dir,
                   a.expected_manifest_sha256,adapter_factory=factory)
    else:p.error("all source / case / pin options required")
    raw=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as h:h.write(raw)
        print("ACTUAL_NATIVE_TO_GENERAL_ROTATION_IR_PRE_SHA256="+digest(raw))
    else:print(raw.decode("utf-8"),end="")

if __name__=="__main__":main()
