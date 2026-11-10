#!/usr/bin/env python3
"""Generic, source-only SimC General Rotation CALL/RUN guard scenario frontier.

Reuses the existing typed SimC APL parser and source hypothesis IR. Applies
explicitly SYNTHETIC numeric source facts to the original "if" AST for ordered
root-list CALL/RUN rows. It never executes a call, selects a spell, guesses
readiness, advances opener time, or treats source facts as WCL observations.

No class/spec/spell semantics in Generic. A standalone source scenario is
useful for checking ST, 2T, AoE and talent/build branching *before* Native
same-root PRE, opponent readiness or independent WCL blind validation.

PyCharm/no arguments: offline synthetic regression, no files or API calls.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import subprocess

from simc_apl_semantic_ir_v2 import canonical, evaluate_ast, truth, git_blob
from general_rotation_source_hypothesis_ir_v1 import compile_profile

SCHEMA="ZrotGenericSimCSourceGuardScenarioFrontierV1"
MATRIX="ZrotGenericSimCSourceGuardScenarioMatrixV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
REV="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
IDENT=re.compile(r"[a-z0-9][a-z0-9_]{0,63}\Z")
HEX40=re.compile(r"[a-f0-9]{40}\Z")
ALLOWED={"CALL","RUN"}

class SourceGuardFrontierError(ValueError):pass

def require(value,why):
    if not value:raise SourceGuardFrontierError(why)

def _facts(facts,target):
    require(isinstance(facts,dict) and len(facts)<=100 and
            type(target) is int and 1<=target<=40 and
            type(facts.get("active_enemies")) in (int,float) and
            facts["active_enemies"]==target and
            all(isinstance(k,str) and len(k)<=128 and
                type(v) in (int,float,bool) and math.isfinite(float(v))
                for k,v in facts.items()),
            "UNTRUSTED_OR_NONFINITE_EXPLICIT_SOURCE_SCENARIO")
    return facts

def control_guard_frontier(model:dict,facts:dict,target:int)->dict:
    """Source-guard assessment ONLY; source-order and READY remain separate."""
    require(isinstance(model,dict) and model.get("schema")==
            "ZrotGeneralRotationSourceHypothesisIRV1" and
            model.get("policy")==POLICY and
            type(model.get("source_only_priority_graph")) is dict,
            "PINNED_TYPED_APL_SOURCE_MODEL_REQUIRED")
    _facts(facts,target)
    graph=model["source_only_priority_graph"]
    lists=graph.get("lists")
    require(type(lists) is dict and "default" in lists and
            type(graph.get("list_order")) is list,
            "SOURCE_DEFAULT_LIST_ORDER_REQUIRED")
    rows=lists["default"]
    output=[]
    classes=Counter()
    for rank,row in enumerate(rows):
        identity=row.get("identity")
        require(type(identity) is dict and identity.get("source_index")==rank
                and identity.get("source_list")=="default"
                and row.get("source_priority_ordinal")==rank
                and row.get("expected_ready")=="UNKNOWN",
                "SOURCE_ROW_OR_NATIVE_READY_IDENTITY_TAMPERED")
        if row["behavior"] not in ALLOWED:
            continue
        dest=row["control_destination"]
        require(type(dest) is str and dest in lists,
                "UNBOUND_OR_CROSS_SOURCE_CONTROL_DESTINATION")
        condition=row["conditions"].get("if")
        if condition is None:
            status="TRUE"
            missing=[]
            original_if=None
        else:
            require(type(condition) is dict and
                    type(condition.get("symbols")) is list and
                    type(condition.get("source_ast")) is list and
                    type(condition.get("raw_expression")) is str,
                    "UNTRUSTED_OR_MISSING_SOURCE_TYPED_IF")
            v=truth(evaluate_ast(condition["source_ast"],facts))
            status="TRUE" if v is True else "FALSE" if v is False else "UNKNOWN"
            missing=sorted(set(condition["symbols"])-set(facts))
            original_if=condition["raw_expression"]
        classes[status]+=1
        output.append({
            "source_root_list":"default",
            "source_rank_one_based":rank+1,
            "source_row_sha256":identity["source_line_sha256"],
            "source_line":identity["source_line"],
            "source_control":row["behavior"],
            "source_destination":dest,
            "source_original_if":original_if,
            "source_if_under_explicit_synthetic_facts":status,
            "possibly_unobserved_source_symbols_upper_bound":(
                missing if status=="UNKNOWN" else []),
            "source_if_false_excludes_only_this_source_control_row":
                status=="FALSE",
            "source_if_true_does_NOT_prove_control_is_ready":
                status=="TRUE",
            "control_native_ready":"UNKNOWN",
            "earlier_noncontrol_action_consumption":"UNKNOWN",
            "destination_ACTUALLY_ENTERED":"UNKNOWN",
            "source_control_semantics":(
                "CHILD_CALL_AND_RESUME_ONLY_IF_NO_ACTION"
                if row["behavior"]=="CALL" else
                "RUN_QUEUED_LIST_TRANSFER_NOT_SYNCHRONOUS_CALL"),
        })
    require(sum(classes.values())==len(output),
            "SOURCE_GUARD_ROW_COUNT_DRIFT")
    return {
        "source_spec_key":model["spec_key"],
        "source_profile_blob_sha1":model["source_git_blob"],
        "source_target_count_assumed":target,
        "source_only_entry_list":"default",
        "source_precombat_action_list_rows":
            len(lists.get("precombat",[])),
        "default_source_rows":len(rows),
        "source_control_row_count":len(output),
        "source_if_guard_class_counts":dict(sorted(classes.items())),
        "source_control_guard_frontier":output,
        "opener_first_actual_cast":"UNKNOWN",
        "opener_to_normal_priority_transition":"UNKNOWN",
        "source_list_ACTIVE_runtime_sequence":"UNKNOWN",
        "any_physical_READY_independently_proven":False,
        "safe_dummy_training_error":"UNKNOWN",
        "no_SOURCE_true_implies_native_ready":True,
        "no_flattened_RUN_or_CALL":True,
    }

def run(root:Path,manifest_path:Path,scenario_path:Path)->dict:
    root=root.resolve(strict=True)
    source_commit=subprocess.run(
        ["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    require(source_commit==REV,"PINNED_SOURCE_REVISION_CHANGED")
    manifest=json.loads(manifest_path.read_bytes())
    matrix=json.loads(scenario_path.read_bytes())
    require(manifest.get("schema")=="ZrotGeneralRotationSimcPinnedSourceManifestV1"
            and manifest.get("official_simc_commit")==REV and
            matrix.get("schema")==MATRIX and
            matrix.get("source_revision")==REV and
            matrix.get("policy_id")==POLICY and
            matrix.get("semantic_provenance")==
                "EXPLICIT_SYNTHETIC_SOURCE_FACTS_NOT_NATIVE_PRE_NOT_WCL_OBSERVATION"
            and type(manifest.get("profiles")) is list and
            type(matrix.get("scenarios")) is list,
            "UNPINNED_OR_CROSS_DATA_SOURCE_MATRIX")
    profiles={}
    for p in manifest["profiles"]:
        require(type(p) is dict and
                type(p.get("key")) is str and IDENT.fullmatch(p["key"]) and
                type(p.get("class_key")) is str and IDENT.fullmatch(p["class_key"])
                and type(p.get("git_blob")) is str and
                HEX40.fullmatch(p["git_blob"]) and
                type(p.get("profile")) is str and
                p["profile"].startswith("profiles/") and
                ".." not in p["profile"].split("/") and
                p["key"] not in profiles,
                "DUPLICATE_OR_UNTRUSTED_SOURCE_PROFILE")
        f=(root/p["profile"]).resolve(strict=True)
        require(f.is_relative_to(root),"SOURCE_PROFILE_PATH_ESCAPE")
        raw=f.read_bytes()
        require(git_blob(raw)==p["git_blob"],
                "ORIGINAL_SOURCE_PROFILE_GIT_BLOB_MISMATCH")
        profiles[p["key"]]=compile_profile(raw,p)
    require(len(profiles)>=2 and len(set(x["class_key"] for x in
            manifest["profiles"]))>=2,
            "GENERIC_CROSS_CLASS_SOURCE_COVERAGE_REQUIRED")
    output=[]
    encountered=set()
    for scenario in matrix["scenarios"]:
        require(type(scenario) is dict and
                set(scenario)=={"spec_key","scenario_id","target_count","source_facts"}
                and type(scenario["scenario_id"]) is str and
                IDENT.fullmatch(scenario["scenario_id"])
                and scenario["spec_key"] in profiles
                and (scenario["spec_key"],scenario["scenario_id"])
                    not in encountered,
                "CROSS_PROFILE_OR_DUPLICATE_SOURCE_SCENARIO")
        encountered.add((scenario["spec_key"],scenario["scenario_id"]))
        facts=_facts(scenario["source_facts"],scenario["target_count"])
        examined=control_guard_frontier(
            profiles[scenario["spec_key"]],facts,scenario["target_count"])
        examined["scenario_id"]=scenario["scenario_id"]
        examined["scenario_source_facts_sha256"]=sha256(canonical(facts)).hexdigest()
        examined["source_input_kind"]="SYNTHETIC_NOT_NATIVE_PRE"
        output.append(examined)
    require(output and len({x["source_spec_key"] for x in output})==len(profiles),
            "NOT_EVERY_PINNED_PROFILE_TESTED")
    return {
        "schema":SCHEMA,
        "policy_id":POLICY,
        "source_commit":REV,
        "source_classes":sorted({x["class_key"] for x in manifest["profiles"]}),
        "source_profiles":len(profiles),
        "source_APL_rows":sum(x["coverage"]["source_action_rows"]
                               for x in profiles.values()),
        "target_count_build_scenarios":len(output),
        "scenarios":output,
        "evidence_level":"PINNED_SOURCE_AST_WITH_EXPLICIT_SYNTHETIC_FACTS",
        "source_Guard_TRUE_does_NOT_imply_ACTION_READY":True,
        "source_ALL_CONTROL_ROWS_not_ALL_ACTION_READY":True,
        "original_Native_source_selection_replayed":False,
        "WCL_blind_candidate_discovery_used":False,
        "opener_exit_proven":False,
        "general_rotation_priority_optimality_proven":False,
        "actual_dummy_wrong_cast_proven":False,
        "MAIN_promoted":False
    }

def selftest()->dict:
    sample=(b"actions.precombat=snapshot_stats\n"
            b"actions=call_action_list,name=solo,if=active_enemies=1&talent.branch\n"
            b"actions+=/run_action_list,name=multi,if=active_enemies>1\n"
            b"actions.solo=spell_one\n"
            b"actions.multi=spell_many\n")
    model=compile_profile(sample,{"key":"fictitious_spec",
                                  "class_key":"fictional",
                                  "git_blob":git_blob(sample)})
    cases=[
        ({"active_enemies":1,"talent.branch":1},1,["TRUE","FALSE"]),
        ({"active_enemies":2,"talent.branch":0},2,["FALSE","TRUE"]),
        ({"active_enemies":1},1,["UNKNOWN","FALSE"]),
    ]
    for facts,n,want in cases:
        proof=control_guard_frontier(model,facts,n)
        got=[x["source_if_under_explicit_synthetic_facts"]
             for x in proof["source_control_guard_frontier"]]
        require(got==want and
                all(x["control_native_ready"]=="UNKNOWN" and
                    x["destination_ACTUALLY_ENTERED"]=="UNKNOWN"
                    for x in proof["source_control_guard_frontier"])
                and proof["opener_to_normal_priority_transition"]=="UNKNOWN",
                "SYNTHETIC_GUARD_NOT_CONSERVATIVELY_TRI_STATED")
    rejected=0
    for facts,n in [
        ({"active_enemies":float("nan")},1),
        ({"active_enemies":2},1),
        ({"active_enemies":1,"talent.branch":float("inf")},1),
        ({"active_enemies":True},1),
    ]:
        try:control_guard_frontier(model,facts,n)
        except SourceGuardFrontierError:rejected+=1
        else:raise AssertionError("UNSAFE_SYNTHETIC_CONTEXT_ACCEPTED")
    return {
        "status":"PASS_OFFLINE_GENERIC_SYNTHETIC",
        "cases":len(cases),
        "invalid_inputs_rejected":rejected,
        "runtime_call_or_run_activated":False,
        "physical_ready_proven":False,
        "opener_end_proven":False,
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root",type=Path)
    ap.add_argument("--manifest",type=Path)
    ap.add_argument("--scenarios",type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    if not any((a.source_root,a.manifest,a.scenarios)):
        result=selftest()
    else:
        if not all((a.source_root,a.manifest,a.scenarios)):
            ap.error("all three source root/manifest/scenarios must be supplied")
        result=run(a.source_root,a.manifest,a.scenarios)
    body=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(body)
        print(json.dumps({"written":str(a.out),
                          "sha256":sha256(body).hexdigest(),
                          "bytes":len(body)}))
    else:
        print(body.decode(),end="")

if __name__=="__main__":
    main()
