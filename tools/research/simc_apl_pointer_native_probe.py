#!/usr/bin/env python3
"""Build-independent runner for an already compiled, opt-in instrumented SimC.

Uses only public profiles in a PINNED upstream source checkout. Keeps all raw
JSON2, log, profile, effective APL inside the CI runner's temporary folder.
A separate proof-receipt pins every raw output and instrumented executable.
No WCL, Blizzard API, private profile, native patch distribution or promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from simc_apl_pointer_instrument import UPSTREAM_SHA
from simc_apl_pointer_provenance_audit import audit_captured_native

FIXTURES=(
    ("enhancement","profiles/MID2/MID2_Shaman_Enhancement.simc"),
    ("fury","profiles/MID2/MID2_Warrior_Fury.simc"),
    ("unholy","profiles/MID2/MID2_Death_Knight_Unholy.simc"),
)


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def run(source_root:Path,binary:Path,output_path:Path|None=None):
    rev=subprocess.run(["git","-C",str(source_root),"rev-parse","HEAD"],
                       check=True,capture_output=True,text=True).stdout.strip()
    if rev != UPSTREAM_SHA:
        raise ValueError("LIVE_POINTER_UPSTREAM_COMMIT_MISMATCH")
    binary_bytes=binary.read_bytes()
    if not binary_bytes:
        raise ValueError("LIVE_POINTER_BINARY_EMPTY")
    binary_digest=sha(binary_bytes)
    summaries=[]
    with tempfile.TemporaryDirectory(prefix="zrot_pinned_apl_pointer_") as td:
        root=Path(td)
        for spec,relative in FIXTURES:
            profile=source_root/relative
            if not profile.is_file():
                raise ValueError("LIVE_POINTER_PROFILE_MISSING")
            profile_sha=sha(profile.read_bytes())
            dest=root/spec
            dest.mkdir()
            names=("simc_effective_actions.simc","simc_native_log.txt",
                   "simc_native_sequence.json")
            command=[
                str(binary.resolve()),str(profile.resolve()),
                "iterations=1","threads=1","calculate_scale_factors=0",
                "max_time=55","vary_combat_length=0","seed=1247695",
                "log=1","log_spell_id=1","report_details=1",
                f"save_actions={dest/names[0]}",
                f"output={dest/names[1]}",
                f"json2={dest/names[2]},full_states=1",
            ]
            completed=subprocess.run(command,cwd=source_root,
                                     capture_output=True,text=True,timeout=120)
            if completed.returncode!=0:
                raise ValueError("LIVE_POINTER_SIMC_RUN_FAILED_"+spec+
                                 " EXIT="+str(completed.returncode)+
                                 " STDERR="+completed.stderr[-300:])
            blobs={n:(dest/n).read_bytes() for n in names}
            if not all(blobs.values()):
                raise ValueError("LIVE_POINTER_SIMC_OUTPUT_EMPTY")
            receipt={
                "schema":"ZrotSimcNativeReferenceCaptureV1",
                "status":"SIMC_NATIVE_CAPTURED_UNPARSED",
                "simc_spec":spec,
                "profile_sha256":profile_sha,
                "simc_executable_sha256":binary_digest,
                "instrumented_binary_sha256":binary_digest,
                "instrumented_upstream_sha256":UPSTREAM_SHA,
                "effective_apl_sha256":sha(blobs[names[0]]),
                "native_log_sha256":sha(blobs[names[1]]),
                "native_json2_sha256":sha(blobs[names[2]]),
                "outputs":[{"file":name,"sha256":sha(blobs[name]),
                            "bytes":len(blobs[name])} for name in names],
            }
            (dest/"simc_reference_receipt.json").write_text(
                json.dumps(receipt,sort_keys=True))
            evidence=audit_captured_native(dest,require_callsite_proof=True,
                                           require_selection_proof=True)
            status=evidence["pointer_status_counts"]
            verified=status.get("POINTER_ROW_AND_EXACT_EFFECTIVE_APL_SIGNATURE_MATCH",0)
            drift=status.get("POINTER_ROW_MATCH_SIGNATURE_DRIFT_NEEDS_REVIEW",0)
            if verified < 1:
                raise ValueError("LIVE_POINTER_NO_EXACT_APL_ROW_EVIDENCE_"+spec)
            if evidence["sequence_callsite_status_counts"].get("UNKNOWN_CALLSITE",0)>0:
                raise ValueError("LIVE_POINTER_UNCLASSIFIED_SEQUENCE_CALLSITE_"+spec)
            if (evidence["foreground_selection_path_counts"].get(
                "UNKNOWN_FOREGROUND_BRANCH",0)>0 or
                evidence["foreground_selection_path_counts"].get(
                    "MISSING_SELECTION_PROVENANCE",0)>0):
                raise ValueError("LIVE_POINTER_UNCLASSIFIED_FOREGROUND_SELECT_"+spec)
            selected=evidence["source_bound_native_select_action_rows"]
            if (selected>evidence["sequence_callsite_status_counts"].get(
                "FOREGROUND_EXECUTE_ACTION",0)):
                raise ValueError("LIVE_POINTER_SELECT_ACTION_EXCEEDS_FOREGROUND")
            if evidence["gameplay_rule_promotion"] is not False:
                raise ValueError("LIVE_POINTER_UNSAFE_GAMEPLAY_PROMOTION")
            summaries.append({
                "spec":spec,
                "profile_sha256":profile_sha,
                "effective_apl_sha256":receipt["effective_apl_sha256"],
                "native_json2_sha256":receipt["native_json2_sha256"],
                "source_row_count":evidence["apl_source_rows"],
                "sequence_row_count":evidence["native_sequence_rows"],
                "exact_pointer_origin_rows":verified,
                "pointer_signature_drift_rows":drift,
                "pointer_status_counts":status,
                "sequence_callsite_status_counts":evidence["sequence_callsite_status_counts"],
                "foreground_selection_path_counts":evidence["foreground_selection_path_counts"],
                "source_bound_native_select_action_rows":selected,
                "all_native_rows_matched":False
                    if verified!=evidence["native_sequence_rows"] else True,
                "native_foreground_decision_proof":"SOURCE_BRANCH_OBSERVED_NOT_STRICT_PRE_PARITY",
            })
    summary={
        "schema":"ZrotSimcPinnedPublicPointerSourceProbeV1",
        "upstream_commit_sha":UPSTREAM_SHA,
        "instrumented_binary_sha256":binary_digest,
        "source_kind":"NEWLY_COMPILED_PINNED_UPSTREAM_PLUS_REPORTER_ONLY_INSTRUMENT",
        "public_profile_count":len(summaries),
        "profiles":summaries,
        "decision_necessary_conditions_not_fully_verified":True,
        "foreground_branch_evidence":"DIRECT_EXECUTE_ACTION_BRANCH_NOT_APPROVED_RULE",
        "strict_pre":"NOT_RUN",
        "native_foreground_equivalence":"NOT_VALIDATED",
        "blizzard_current_mechanics":"NOT_VERIFIED",
        "wcl_independent_discovery":"NOT_RUN",
        "gameplay_rule_promotion":False,
        "uploaded_raw_native_profiles_or_logs":False,
    }
    content=json.dumps(summary,sort_keys=True,indent=2)+"\n"
    if output_path:
        output_path.parent.mkdir(parents=True,exist_ok=True)
        output_path.write_text(content,encoding="utf-8")
    print("PINNED_SIMC_NATIVE_APL_POINTER_EVIDENCE=PASS PROFILES="+str(len(summaries)))
    print(content)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream-root",type=Path,required=True)
    p.add_argument("--binary",type=Path,required=True)
    p.add_argument("--summary",type=Path)
    args=p.parse_args()
    run(args.upstream_root,args.binary,args.summary)


if __name__=="__main__":
    main()
