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
import gzip
import json
from pathlib import Path
import subprocess
import tempfile

from simc_apl_pointer_instrument import UPSTREAM_SHA
from simc_apl_pointer_provenance_audit import audit_captured_native
from simc_apl_source_engine import ingest_actions
from simc_native_resource_change_probe import (
    native_resource_pre_gate, native_log_to_ndjson, audit_native_projection_independently
)
from simc_native_resource_lifecycle_probe import (
    project_lifecycle_log, independent_lifecycle_audit, lifecycle_pre_gate
)
from simc_native_select_resource_diagnostic_audit import compare_diagnostics
from simc_native_epoch_sequence_audit import (
    parse_epoch_native_log, independent_epoch_audit, compare_epoch_bound_resources
)
from simc_native_bare_resource_eval_audit import audit as audit_native_bare_resource_eval
from simc_native_apl_eval_scope_audit import audit as audit_apl_attempt_scopes
from simc_native_if_guard_audit import audit as audit_native_direct_if
from decimal import Decimal

FIXTURES=(
    ("enhancement","profiles/MID2/MID2_Shaman_Enhancement.simc"),
    ("fury","profiles/MID2/MID2_Warrior_Fury.simc"),
    ("unholy","profiles/MID2/MID2_Death_Knight_Unholy.simc"),
    ("havoc","profiles/MID2/MID2_Demon_Hunter_Havoc.simc"),
)


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def run(source_root:Path,binary:Path,output_path:Path|None=None,
        specs:tuple[str,...]|None=None, marker_output_dir:Path|None=None):
    rev=subprocess.run(["git","-C",str(source_root),"rev-parse","HEAD"],
                       check=True,capture_output=True,text=True).stdout.strip()
    if rev != UPSTREAM_SHA:
        raise ValueError("LIVE_POINTER_UPSTREAM_COMMIT_MISMATCH")
    binary_bytes=binary.read_bytes()
    if not binary_bytes:
        raise ValueError("LIVE_POINTER_BINARY_EMPTY")
    binary_digest=sha(binary_bytes)
    if specs is None:
        active_fixtures=FIXTURES
    else:
        allowed={name:path for name,path in FIXTURES}
        if (not specs or len(specs)!=len(set(specs))
                or any(name not in allowed for name in specs)):
            raise ValueError("NATIVE_PUBLIC_FIXTURE_SELECTION_INVALID")
        active_fixtures=tuple((name,allowed[name]) for name in specs)
    summaries=[]
    if marker_output_dir is not None:
        marker_output_dir.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="zrot_pinned_apl_pointer_") as td:
        root=Path(td)
        for spec,relative in active_fixtures:
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
            # Genuine, log-source-pinned resource gain/loss mutations; do not
            # derive pseudo-transitions by differencing action snapshots.
            effective_model=ingest_actions(
                blobs[names[0]], expected_spec=spec,
                profile_sha256=profile_sha, simc_executable_sha256=binary_digest,
                profile_spec=spec, profile_dependencies_verified=True)
            if effective_model["apl_sha256"]!=receipt["effective_apl_sha256"]:
                raise ValueError("NATIVE_RESOURCE_EFFECTIVE_APL_SHA_MISMATCH")
            raw_resource=native_log_to_ndjson(
                blobs[names[1]], expected_log_sha256=receipt["native_log_sha256"])
            native_resource_review=audit_native_projection_independently(
                blobs[names[1]],raw_resource)
            source_selected=[r for r in evidence["sequence_provenance"]
                             if r["foreground_apl_select_action_confirmed"]
                             and r["native_action_timestamp_s"] is not None]
            if not source_selected:
                raise ValueError("NATIVE_RESOURCE_NO_SELECT_ACTION_REFERENCE")
            decision_time_ms=min(
                int(Decimal(str(x["native_action_timestamp_s"]))*1000)
                for x in source_selected)
            last_decision_time_ms=max(
                int(Decimal(str(x["native_action_timestamp_s"]))*1000)
                for x in source_selected)
            if decision_time_ms<0 or last_decision_time_ms<decision_time_ms:
                raise ValueError("NATIVE_RESOURCE_INVALID_SELECTION_TIME_RANGE")
            boundary=native_resource_pre_gate(
                effective_model,blobs[names[1]],
                expected_log_sha256=receipt["native_log_sha256"],
                decision_timestamp_ms=decision_time_ms)
            late_boundary=native_resource_pre_gate(
                effective_model,blobs[names[1]],
                expected_log_sha256=receipt["native_log_sha256"],
                decision_timestamp_ms=last_decision_time_ms)
            if (boundary["readiness"]!="UNKNOWN" or
                late_boundary["readiness"]!="UNKNOWN" or
                boundary["gameplay_rule_promotion"] is not False or
                late_boundary["gameplay_rule_promotion"] is not False):
                raise ValueError("NATIVE_RESOURCE_UNVERIFIED_READINESS")
            if raw_resource["source_event_count"]>0 and (
                late_boundary.get("accepted_strictly_earlier_raw_events",0)<=0):
                raise ValueError("NATIVE_RESOURCE_NO_EARLIER_EVENT_AT_LAST_SELECTION")
            lifecycle=project_lifecycle_log(
                blobs[names[1]],receipt["native_log_sha256"])
            lifecycle_verified=independent_lifecycle_audit(
                blobs[names[1]],lifecycle)
            if lifecycle["lifecycle_row_count"]<1:
                raise ValueError("NATIVE_LIFECYCLE_NO_INIT_OR_RECALC_MARKERS_"+spec)
            selected_actor_identity=raw_resource["actor_identity_tuple"]
            if selected_actor_identity is None:
                raise ValueError("NATIVE_LIFECYCLE_NO_CONFIRMED_ACTOR_SCOPE_"+spec)
            lifecycle_first=lifecycle_pre_gate(
                effective_model,lifecycle,actor_identity=selected_actor_identity,
                decision_timestamp_ms=decision_time_ms)
            lifecycle_last=lifecycle_pre_gate(
                effective_model,lifecycle,actor_identity=selected_actor_identity,
                decision_timestamp_ms=last_decision_time_ms)
            if (lifecycle_last["readiness"]!="UNKNOWN" or
                lifecycle_last["trace_status"]!="BLOCKED"):
                raise ValueError("NATIVE_LIFECYCLE_UNVERIFIED_READINESS_OR_TRACE_"+spec)
            if lifecycle_last["source_rows"]<1:
                raise ValueError("NATIVE_LIFECYCLE_NOT_SAME_ACTOR_SPAWN_"+spec)
            diagnostic=compare_diagnostics(
                blobs[names[1]],expected_log_sha256=receipt["native_log_sha256"],
                resource_projection=raw_resource,lifecycle_projection=lifecycle)
            if (diagnostic["source_selection_diagnostic_audit"]["status"] !=
                    "PASS_EXACT_DIAGNOSTIC_NATIVE_RAW_RECALC"):
                raise ValueError("NATIVE_SELECT_RESOURCE_DIAG_SOURCE_AUDIT_FAILED")
            if diagnostic["native_selection_entry_count"]<1 or (
                    diagnostic["selection_entry_status_counts"].get(
                    "positive_return_action_entries",0)<1):
                raise ValueError("NATIVE_SELECT_RESOURCE_NO_REAL_SELECT_ENTRIES_"+spec)
            if (diagnostic["native_entry_snapshot_used_as_reconstructed_pre"] is not False
                    or diagnostic["gameplay_rule_promotion"] is not False):
                raise ValueError("NATIVE_SELECT_RESOURCE_SNAPSHOT_PRE_LEAK")
            epoch=parse_epoch_native_log(
                blobs[names[1]],receipt["native_log_sha256"])
            epoch_audit=independent_epoch_audit(blobs[names[1]],epoch)
            if epoch["reset_boundary_count"]<1:
                raise ValueError("NATIVE_EPOCH_NO_RUNTIME_RESET_BOUNDARY_"+spec)
            if epoch_audit["status"]!="PASS_EPOCH_NATIVE_SOURCE_BYTES_INDEPENDENT_RECALC":
                raise ValueError("NATIVE_EPOCH_SOURCE_AUDIT_FAILED")
            epoch_comparison=compare_epoch_bound_resources(
                blobs[names[1]],epoch)
            if epoch_comparison["readiness"]!="UNKNOWN" or (
                    epoch_comparison["gameplay_rule_promotion"] is not False or
                    epoch_comparison["diagnostic_snapshot_used_as_strict_pre"] is not False):
                raise ValueError("NATIVE_EPOCH_UNCERTIFIED_GAMEPLAY_CLAIM")
            if epoch_comparison["native_select_entry_count"]!=diagnostic[
                    "native_selection_entry_count"]:
                raise ValueError("NATIVE_EPOCH_SELECT_DIAGNOSTIC_COUNT_MISMATCH")
            bare_eval=audit_native_bare_resource_eval(
                blobs[names[1]], receipt["native_log_sha256"])
            if (bare_eval["source_log_sha256"]!=receipt["native_log_sha256"]
                    or bare_eval["evaluations_inside_selection"]>
                    bare_eval["native_evaluation_count"]
                    or bare_eval["gameplay_rule_promotion"] is not False
                    or bare_eval["eval_used_as_strict_pre"] is not False
                    or bare_eval["certified_operand_values"]!=0):
                raise ValueError("NATIVE_BARE_RESOURCE_EVAL_PRE_CERTIFICATION_LEAK")
            attempt_scopes=audit_apl_attempt_scopes(
                blobs[names[1]],receipt["native_log_sha256"],effective_model)
            if (attempt_scopes["bare_eval_total"]!=bare_eval["native_evaluation_count"]
                    or attempt_scopes["scope_begin_count"]<1
                    or attempt_scopes["scope_begin_count"]!=attempt_scopes["scope_end_count"]
                    or attempt_scopes["runtime_eval_used_as_strict_pre"] is not False
                    or attempt_scopes["guard_expression_owner_certified"] is not False
                    or attempt_scopes["gameplay_rule_promotion"] is not False
                    or attempt_scopes["readiness_certified"]!=0):
                raise ValueError("NATIVE_EVAL_ATTEMPT_SCOPE_SOURCE_OR_CLAIM_FAILURE")
            direct_if=audit_native_direct_if(
                blobs[names[1]],receipt["native_log_sha256"],effective_model)
            if (direct_if["bare_eval_total"]!=bare_eval["native_evaluation_count"]
                or direct_if["guard_begin_count"]!=direct_if["guard_end_count"]
                or direct_if["gameplay_rule_promotion"] is not False
                or direct_if["readiness_certified"]!=0
                or direct_if["eval_as_state_transition"] is not False):
                raise ValueError("NATIVE_DIRECT_IF_SOURCE_AUDIT_FAILED")
            marker_subset_receipt=None
            if marker_output_dir is not None:
                # Keep public-source Native proof markers only, not full log,
                # unneeded profile/character metadata or game credentials.
                marker_bytes=b"\n".join(x for x in blobs[names[1]].splitlines()
                    if b"ZROT_NATIVE_" in x)+b"\n"
                independent_subset=audit_native_direct_if(
                    marker_bytes,sha(marker_bytes),effective_model)
                exact_fields=("bare_eval_total","guard_begin_count",
                              "guard_end_count","outcomes","confirmed_owner_counts",
                              "action_scope_count")
                if any(independent_subset[k]!=direct_if[k] for k in exact_fields):
                    raise ValueError("NATIVE_DIRECT_IF_MARKER_SUBSET_REPLAY_DRIFT")
                compressed=gzip.compress(marker_bytes,mtime=0)
                marker_file=marker_output_dir/(spec+".zrot_native_markers.txt.gz")
                marker_file.write_bytes(compressed)
                marker_subset_receipt={
                    "marker_only_source_sha256":sha(marker_bytes),
                    "marker_only_bytes":len(marker_bytes),
                    "compressed_source_sha256":sha(compressed),
                    "compressed_bytes":len(compressed),
                    "compressed_artifact_file":marker_file.name,
                    "independent_replay_result":"PASS_SAME_DIRECT_IF_SOURCE_OUTCOMES",
                }
            summaries.append({
                "spec":spec,
                "native_epoch_log_source_sha256":epoch["source_log_sha256"],
                "native_epoch_source_marker_count":epoch["event_count"],
                "native_epoch_reset_boundary_count":epoch["reset_boundary_count"],
                "native_epoch_reset_thread_iteration_pairs":sorted({
                    (x["thread"],x["iteration"]) for x in epoch["reset_boundaries"]}),
                "native_epoch_iterations":epoch["source_iterations"],
                "native_epoch_event_kinds":epoch["event_kind_counts"],
                "native_epoch_independent_audit":epoch_audit["status"],
                "native_epoch_comparison_counts":epoch_comparison["comparison_counts"],
                "native_epoch_possible_gaps":epoch_comparison["potential_mismatch_examples"],
                "native_epoch_selected_entry_count":epoch_comparison["native_select_entry_count"],
                "native_epoch_snapshot_promoted_as_pre":False,
                "native_bare_resource_eval_count":bare_eval["native_evaluation_count"],
                "native_bare_resource_eval_within_selection":bare_eval["evaluations_inside_selection"],
                "native_bare_resource_eval_resources":bare_eval["evaluated_resource_counts"],
                "native_bare_resource_eval_outcomes":bare_eval["counts"],
                "native_bare_resource_eval_examples":bare_eval["examples_max_25"],
                "native_bare_resource_eval_source_row_identity":"UNKNOWN",
                "native_bare_resource_eval_strict_pre_certified":False,
                "native_apl_attempt_scope_begin_count":attempt_scopes["scope_begin_count"],
                "native_apl_attempt_scope_owner_counts":attempt_scopes["outcome_counts"],
                "native_apl_attempt_scope_mode_counts":attempt_scopes["matched_mode_counts"],
                "native_apl_attempt_scope_owner_contexts":attempt_scopes["owner_context_counts"],
                "native_apl_attempt_scope_examples":attempt_scopes["examples_max_30"],
                "native_apl_guard_eval_owner_certified":False,
                "native_direct_if_guard_begin_count":direct_if["guard_begin_count"],
                "native_direct_if_guard_true_count":direct_if["guard_success_true_count"],
                "native_direct_if_guard_false_count":direct_if["guard_success_false_count"],
                "native_direct_if_eval_outcomes":direct_if["outcomes"],
                "native_direct_if_eval_owner_counts":direct_if["confirmed_owner_counts"],
                "native_direct_if_examples":direct_if["examples_max_25"],
                "native_direct_if_state_readiness_certified":False,
                "native_marker_only_independent_receipt":marker_subset_receipt,
                "select_resource_diagnostic_log_sha256":diagnostic["source_log_sha256"],
                "select_resource_diagnostic_audit":diagnostic[
                    "source_selection_diagnostic_audit"]["status"],
                "select_resource_native_entry_count":diagnostic[
                    "native_selection_entry_count"],
                "select_resource_selection_status":diagnostic[
                    "selection_entry_status_counts"],
                "select_resource_comparison_counts":diagnostic["comparison_counts"],
                "select_resource_possible_missing_transition_examples":
                    diagnostic["conflict_examples_at_most_25"],
                "select_resource_snapshot_used_as_pre":False,
                "select_resource_incomplete_source_coverage":True,
                "native_lifecycle_log_source_sha256":lifecycle["source_log_sha256"],
                "native_lifecycle_rows":lifecycle["lifecycle_row_count"],
                "native_lifecycle_events_by_path":lifecycle["events_by_path"],
                "native_lifecycle_actor_spawn_identities":lifecycle["actor_spawn_identities"],
                "native_lifecycle_independent_audit":lifecycle_verified["status"],
                "native_lifecycle_current_actor_source_rows":lifecycle_last["source_rows"],
                "native_lifecycle_rows_before_first_select":lifecycle_first["strictly_before_selected_action"],
                "native_lifecycle_rows_before_final_select":lifecycle_last["strictly_before_selected_action"],
                "native_lifecycle_last_same_timestamp_excluded":lifecycle_last.get(
                    "strict_pre_excluded_same_timestamp",0),
                "native_lifecycle_readiness":lifecycle_last["readiness"],
                "native_lifecycle_semantics":"PARTIAL_INIT_MAX_RECALC_FUNCTIONS_ONLY",
                "resource_log_source_sha256":receipt["native_log_sha256"],
                "native_resource_event_count":raw_resource["source_event_count"],
                "native_resource_negative_precombat_excluded":raw_resource[
                    "excluded_negative_timestamp_events"],
                "resource_actor_identity_tuple":raw_resource["actor_identity_tuple"],
                "resource_log_independent_audit":native_resource_review["status"],
                "resource_event_first_select_action_decision_ms":decision_time_ms,
                "resource_events_strictly_before_first_selected_action":
                    boundary.get("accepted_strictly_earlier_raw_events",0),
                "resource_strict_pre_status":boundary.get("state_status"),
                "resource_trace_status":boundary.get("trace_status","BLOCKED_UNKNOWN"),
                "resource_readiness":boundary["readiness"],
                "resource_event_last_select_action_decision_ms":last_decision_time_ms,
                "resource_events_strictly_before_last_selected_action":
                    late_boundary.get("accepted_strictly_earlier_raw_events",0),
                "resource_last_strict_pre_status":late_boundary.get("state_status"),
                "resource_last_trace_status":late_boundary.get("trace_status","BLOCKED_UNKNOWN"),
                "resource_last_candidate_action":late_boundary.get("trace_candidate_action_token"),
                "resource_semantic_coverage":"PARTIAL_GAIN_LOSS_ONLY_NOT_CERTIFIED",
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
        "retained_public_marker_only_proof":marker_output_dir is not None,
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
    p.add_argument("--specs",help="Comma-separated subset of pinned public fixture slugs")
    p.add_argument("--marker-output-dir",type=Path)
    args=p.parse_args()
    requested=tuple(args.specs.split(",")) if args.specs else None
    run(args.upstream_root,args.binary,args.summary,
        specs=requested,marker_output_dir=args.marker_output_dir)


if __name__=="__main__":
    main()
