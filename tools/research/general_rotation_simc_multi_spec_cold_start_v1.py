#!/usr/bin/env python3
"""Generic SimC-first cross-specialization APL cold-start source extractor.

A declarative, pinned input manifest chooses *source files*, not logic.
The same typed SimC APL parser processes every class/spec; nothing here
contains Warrior/Mage skill names, priorities, target thresholds or buffs.
No Native simulation or WCL comparison is needed to establish source
coverage; exact runtime READY, actual opener and optimality remain UNKNOWN.

Use the real official pinned profiles for a cheap multi-spec E2E source
parsing check, and generate a reproducible source and IR receipt. New class
discovery requires only a new manifest entry, never an engine code branch.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from simc_apl_semantic_ir_v2 import (
    parse_profile,git_blob,canonical
)
SCHEMA="ZrotGeneralRotationSimcMultiSpecColdStartV1"
MANIFEST_SCHEMA="ZrotGeneralRotationSimcPinnedSourceManifestV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
PIN=r"[a-f0-9]{40}"
KEY=r"[a-z0-9_]+"
class MultiSpecColdStartError(ValueError):pass

def load_manifest(path:Path)->dict:
    obj=json.loads(path.read_bytes())
    if obj.get("schema")!=MANIFEST_SCHEMA or not re.fullmatch(PIN,obj.get("official_simc_commit","")):
        raise MultiSpecColdStartError("PINNED_MULTI_SPEC_MANIFEST_INVALID")
    specs=obj.get("profiles",[])
    if not isinstance(specs,list) or len(specs)<2:
        raise MultiSpecColdStartError("MULTI_SPEC_MANIFEST_REQUIRES_TWO_UNRELATED_SPECS")
    keys=set();distinct_classes=set();seen_paths=set()
    for spec in specs:
        if not isinstance(spec,dict) or set(spec)!={"key","class_key","profile","git_blob"}:
            raise MultiSpecColdStartError("PINNED_PROFILE_METADATA_SHAPE_INVALID")
        if not all(re.fullmatch(KEY,spec[k]) for k in ("key","class_key")):
            raise MultiSpecColdStartError("PROFILE_SPEC_AND_CLASS_IDENTIFIER_INVALID")
        if (spec["key"] in keys or spec["profile"] in seen_paths or
            not re.fullmatch(PIN,spec["git_blob"])):
            raise MultiSpecColdStartError("DUPLICATED_PROFILE_OR_UNPINNED_BLOB")
        rel=Path(spec["profile"])
        if (rel.is_absolute() or len(rel.parts)<3 or
            rel.parts[:2] != ("profiles","MID2") or
            ".." in rel.parts or rel.suffix!=".simc"):
            raise MultiSpecColdStartError("UNSAFE_PROFILE_SOURCE_PATH")
        seen_paths.add(spec["profile"]);keys.add(spec["key"])
        distinct_classes.add(spec["class_key"])
    if len(distinct_classes)<2:
        raise MultiSpecColdStartError("CROSS_SPEC_VALIDATION_REQUIRES_TWO_CLASSES")
    return obj

def run(source_root:Path,manifest_path:Path)->dict:
    root=source_root.resolve(strict=True)
    manifest=load_manifest(manifest_path)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       capture_output=True,text=True,check=True).stdout.strip()
    if rev!=manifest["official_simc_commit"]:
        raise MultiSpecColdStartError("OFFICIAL_SOURCE_REVISION_DRIFT")
    results=[]
    raw_rows=0
    for spec in manifest["profiles"]:
        rel=Path(spec["profile"])
        path=(root/rel).resolve(strict=True)
        if not path.is_relative_to(root):
            raise MultiSpecColdStartError("PROFILE_REALPATH_ESCAPES_SOURCE_ROOT")
        raw=path.read_bytes()
        if git_blob(raw)!=spec["git_blob"]:
            raise MultiSpecColdStartError("SOURCE_PROFILE_GIT_BLOB_MISMATCH")
        # Existing generic parser: fail-closed on unsupported grammar.
        ir=parse_profile(raw,require_source=True,
                         expected_git_blob=spec["git_blob"])
        if ir["source_action_line_count"]<1 or not ir["action_lists"]:
            raise MultiSpecColdStartError("PINNED_PROFILE_NO_SOURCE_PRIORITY_ROWS")
        results.append({
            "key":spec["key"],"class_key":spec["class_key"],
            "profile":spec["profile"],
            "official_profile_git_blob":spec["git_blob"],
            "profile_raw_sha256":sha256(raw).hexdigest(),
            "semantic_source_IR_sha256":sha256(canonical(ir)).hexdigest(),
            "source_action_rows":ir["source_action_line_count"],
            "action_list_count":len(ir["action_lists"]),
            "action_list_counts":ir["action_list_counts"],
            "expression_attribute_counts":ir["expression_attribute_counts"],
            "source_symbol_count":len(ir["source_symbol_dependencies"]),
            "source_graph_edge_count":sum(len(v) for v in ir["graph_edges"].values()),
            "APL_source_parsed":True,
            "source_IF_READY_independently_replayed":False,
            "native_opener_verified":False,
        })
        raw_rows+=ir["source_action_line_count"]
    return {
        "schema":SCHEMA,"policy":POLICY,
        "source_pin":rev,"profiles":results,
        "distinct_class_count":len({x["class_key"] for x in results}),
        "total_action_rows":raw_rows,
        "SimC_first_apl_semantic_parsing_completed":True,
        "all_profile_source_blobs_verified":True,
        "Native_action_ready_independently_proven":False,
        "WCL_independent_blind_holdout_completed":False,
        "General_Rotation_opener_verified":False,
        "source_symbols_are_hypotheses_not_observed_WoW_state":True,
        "WCL_API_calls":0,"MAIN_promoted":False,
    }

def selftest():
    from tempfile import TemporaryDirectory
    cases=[
        ("alpha","warrior","profiles/MID2/a.simc"),
        ("beta","mage","profiles/MID2/b.simc")
    ]
    manifest={"schema":MANIFEST_SCHEMA,"official_simc_commit":"a"*40,
              "profiles":[{"key":k,"class_key":c,"profile":p,"git_blob":"b"*40}
                          for k,c,p in cases]}
    with TemporaryDirectory() as td:
        p=Path(td)/"manifest.json"
        p.write_bytes(canonical(manifest))
        assert len(load_manifest(p)["profiles"])==2
        for mutate in (
            lambda m:m["profiles"][1].update(class_key="warrior"),
            lambda m:m["profiles"][0].update(profile="../evil.simc"),
            lambda m:m["profiles"][0].update(git_blob="unknown"),
            lambda m:m.update(official_simc_commit="UNPINNED"),
            lambda m:m["profiles"].pop(),
            lambda m:m["profiles"][0].update(key="beta"),
        ):
            candidate=json.loads(canonical(manifest))
            mutate(candidate)
            p.write_bytes(canonical(candidate))
            try:load_manifest(p)
            except MultiSpecColdStartError:pass
            else:raise AssertionError("INVALID_GENERIC_COLD_START_MANIFEST_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":8,"unrelated_class_examples":2,
            "Native_CXX_not_run":True,"WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.source_root and args.manifest:result=run(args.source_root,args.manifest)
    elif not args.source_root and not args.manifest:result=selftest()
    else:p.error("--source-root and --manifest must be supplied together")
    raw=canonical(result)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("xb") as f:f.write(raw)
        print("SIMC_MULTI_SPEC_COLD_START_RECEIPT_SHA256="+sha256(raw).hexdigest())
    else:print(raw.decode(),end="")

if __name__=="__main__":main()
