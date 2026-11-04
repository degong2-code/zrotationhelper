#!/usr/bin/env python3
"""Portable, source-marker-only Native PRE replay fixture producer.

Original pinned official SimC Native logs may be large. Preserve *every*
ZROT_ source-record line, in original order, without dedupe, interpolation
or timestamp reordering, then gzip deterministically (mtime=0). Compare
two existing independent generic replayers on original vs compacted
records BEFORE asserting this is a usable replay fixture.

This does NOT preserve damage/ability output for pristine sequence parity,
nor demonstrate independent positive action READY or other specializations.
It is a source-marked, scoped input to Python replayers, not a fabricated
WoW/WCL log. No WCL calls, boss timeline or encounter plan.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import gzip
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import git_blob,parse_profile,canonical
from simc_native_ready_guard_witness_replay_v1 import replay_log,read_guard
from simc_native_postguard_source_replay_v1 import replay_trace
from simc_native_if_pre_operand_replay_v1 import get_native_attempt
from simc_native_if_pre_operand_replay_v1 import parse_fact

SCHEMA="ZrotGenericSourceMarkedPortableNativePreFixtureV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
REQUIRED_MARKER=b"ZROT_"

class NativeCompactFixtureError(ValueError):pass

def digest(raw:bytes)->str:
    return sha256(raw).hexdigest()

def compact(raw:bytes)->tuple[bytes,dict]:
    if not raw:
        raise NativeCompactFixtureError("NATIVE_SOURCE_LOG_EMPTY")
    # Keep original bytes, line separators, chronological occurrence
    # order and duplicate source records. No lossy schema translation.
    retained=b"".join(line for line in raw.splitlines(keepends=True)
                      if REQUIRED_MARKER in line)
    if not retained or not retained.endswith(b"\n"):
        raise NativeCompactFixtureError("NATIVE_SOURCE_MARKER_TRACE_NOT_COMPLETE")
    if b"ZROT_" not in retained:
        raise NativeCompactFixtureError("SOURCE_MARKER_OMITTED")
    archive=gzip.compress(retained,compresslevel=9,mtime=0)
    if gzip.decompress(archive)!=retained:
        raise NativeCompactFixtureError("DETERMINISTIC_GZIP_ROUNDTRIP_CHANGED")
    return archive,{
        "raw_log_sha256":digest(raw),
        "filtered_source_markers_sha256":digest(retained),
        "portable_gzip_sha256":digest(archive),
        "raw_log_bytes":len(raw),
        "source_marker_bytes":len(retained),
        "compressed_bytes":len(archive),
        "raw_log_lines":len(raw.splitlines()),
        "source_marker_lines":len(retained.splitlines()),
    }

def audit_equivalence(raw:bytes,zip_bytes:bytes,ir:dict)->dict:
    reduced=gzip.decompress(zip_bytes)
    original=raw.decode("utf-8")
    filtered=reduced.decode("utf-8")
    def marker_counts(log:str):
        return {
            "ready_pre_scoped":sum(read_guard(l) is not None for l in log.splitlines()),
            "native_attempt":sum(get_native_attempt(l) is not None for l in log.splitlines()),
            "source_if_fact":sum(parse_fact(l) is not None for l in log.splitlines()),
        }
    a=marker_counts(original)
    b=marker_counts(filtered)
    if a!=b or not a["native_attempt"] or not a["ready_pre_scoped"]:
        raise NativeCompactFixtureError("SOURCE_MARKER_COUNTS_NOT_IDENTICAL")
    # Both replays consume source markers only. Matching complete JSON
    # structures checks that no hidden non-marker line changed their
    # observation. No Native choice/ready bit becomes an independent
    # input or a production validation claim.
    first_raw=replay_log(original,ir)
    first_zip=replay_log(filtered,ir)
    if first_raw!=first_zip:
        raise NativeCompactFixtureError("GENERIC_BASE_GUARD_REPLAY_DIFFERS_AFTER_COMPACTION")
    post_raw=replay_trace(original,ir)
    post_zip=replay_trace(filtered,ir)
    if post_raw!=post_zip:
        raise NativeCompactFixtureError("GENERIC_POSTGUARD_REPLAY_DIFFERS_AFTER_COMPACTION")
    return {
        "marker_counts":a,
        "base_guard_replay_exact_equal":True,
        "postguard_replay_exact_equal":True,
        "ready_verdicts_from_Native_NOT_independent":True,
        "source_marker_occurrence_order_preserved":True,
        "independent_full_priority_not_claimed":True,
    }

def run(profile:Path,expected_blob:str,cases:list[str],out_dir:Path)->dict:
    raw_profile=profile.read_bytes()
    if git_blob(raw_profile)!=expected_blob:
        raise NativeCompactFixtureError("OFFICIAL_SIMC_PROFILE_BLOB_CHANGED")
    ir=parse_profile(raw_profile,require_source=True,expected_git_blob=expected_blob)
    if not cases:raise NativeCompactFixtureError("NO_ACTUAL_SOURCE_LOG_CASES")
    destinations=[]
    for record in cases:
        label,sep,path=record.partition("=")
        if (not sep or not label or not label.replace("_","").isalnum() or
            not path or any(label==p[0] for p in destinations)):
            raise NativeCompactFixtureError("INVALID_OR_DUPLICATE_SOURCE_CASE")
        destinations.append((label,Path(path)))
    # Validate ALL cases, including replay parity, before creating
    # any user-visible output file.
    validated=[]
    for label,path in destinations:
        raw=path.resolve(strict=True).read_bytes()
        data,meta=compact(raw)
        proof=audit_equivalence(raw,data,ir)
        validated.append((label,data,meta,proof))
    out_dir.mkdir(parents=True,exist_ok=False)
    manifest={
        "schema":SCHEMA,"product_scope":POLICY,
        "profile_git_blob":expected_blob,
        "source_action_line_count":ir["source_action_line_count"],
        "cases":{},
        "all_original_vs_compact_generic_replay_exact":True,
        "source_markers_only":True,
        "Native_pristine_action_output_not_included":True,
        "full_ready_or_selection_NOT_proven":True,
        "WCL_API_calls":0,"MAIN_promoted":False
    }
    for label,data,meta,proof in validated:
        fn=f"{label}.source-pre.jsonl.gz"
        with (out_dir/fn).open("xb") as file:file.write(data)
        manifest["cases"][label]={
            "path":fn,"source_meta":meta,"equivalence":proof,
        }
    binary=canonical(manifest)
    with (out_dir/"manifest.json").open("xb") as file:file.write(binary)
    return {"schema":SCHEMA,"status":"ACTUAL_NATIVE_MARKER_TRACE_COMPACTED",
        "case_count":len(validated),
        "manifest_sha256":digest(binary),
        "case_counts":{k:v["equivalence"]["marker_counts"]
                       for k,v in manifest["cases"].items()},
        "all_original_vs_compact_generic_replay_exact":True,
        "Native_full_cast_sequence_NOT_available_in_compact":True,
        "WCL_API_calls":0}

def selftest():
    sample=(
        b"HEADER untracked\n"
        b"source ZROT_NATIVE_READY_GUARDS_PRE_V1|10|default|1|foo|1|1|0|-1|1\n"
        b"unrelated high-volume text\n"
        b"ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|foo|0\n"
        b"ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|foo|0\n"
    )
    gz,meta=compact(sample)
    decoded=gzip.decompress(gz)
    assert meta["source_marker_lines"]==3
    assert decoded.count(b"ZROT_NATIVE_SELECT_V1|ATTEMPT")==2
    assert meta["raw_log_bytes"]>meta["source_marker_bytes"]
    assert gz==compact(sample)[0]
    assert all(b"ZROT_" in line for line in decoded.splitlines())
    try:compact(b"missing source markers\n")
    except NativeCompactFixtureError:pass
    else:raise AssertionError("SOURCELESS_LOG_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":7,"actual_Native_source_log_not_used_in_selftest":True,
        "WCL_API_calls":0
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--native-case",action="append",default=[],
                   help="LABEL=/absolute/path/simc_native_log.txt; repeat")
    p.add_argument("--out-dir",type=Path)
    args=p.parse_args()
    if (args.official_profile and args.expected_profile_git_blob and
        args.native_case and args.out_dir):
        result=run(args.official_profile,args.expected_profile_git_blob,
                   args.native_case,args.out_dir)
    elif not any((args.official_profile,args.expected_profile_git_blob,
                  args.native_case,args.out_dir)):
        result=selftest()
    else:p.error("all four Native source options required together")
    print(canonical(result).decode(),end="")

if __name__=="__main__":main()
