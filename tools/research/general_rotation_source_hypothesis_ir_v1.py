#!/usr/bin/env python3
"""Generic source-only General Rotation hypothesis IR from pinned SimC APL.

Source-ordered conditional candidate rows and control graph are hypotheses,
NOT verified casts, opener execution, physical spell readiness or optimality.
Every source row remains traceable to its profile Git blob and row SHA256.
No specialization, boss or WCL semantic conclusions are hard-coded.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from simc_apl_semantic_ir_v2 import parse_profile,git_blob,canonical
from general_rotation_simc_multi_spec_cold_start_v1 import load_manifest
from general_rotation_decision_proof_engine_v1 import CONTROL_COMMANDS

SCHEMA="ZrotGeneralRotationSourceHypothesisIRV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
COMPARE=frozenset(("=","!=","<","<=",">",">="))
TARGETS=frozenset(("active_enemies","desired_targets","target_count","enemy_count","enemies","targets"))
RESOURCES=frozenset(("rage","energy","focus","mana","runic_power","insanity","chi","fury","pain","holy_power","maelstrom","soul_shard","combo_points","arcane_charges","essence"))

class HypothesisIRError(ValueError): pass

def source_contexts(symbol:str)->list[str]:
    """Non-authoritative symbol categories, not mechanic interpretations."""
    x=symbol.lower()
    h=x.split(".")[0]
    labels=set()
    if h in TARGETS or x.startswith(("spell_targets.","active_enemies.")):
        labels.add("target_count")
    if h in RESOURCES or h=="resource":labels.add("resource")
    if h in ("buff","debuff","dot"):labels.add("buff_or_debuff")
    if h in ("cooldown","charges","full_recharge_time"):labels.add("cooldown")
    if h in ("talent","hero_talent","set_bonus","equipped"):labels.add("build")
    if h in ("movement","moving","movement_distance","distance","distance_to_move"):
        labels.add("movement")
    if h in ("gcd","casting","channeling","cast_time"):labels.add("casting")
    if "fight_remains" in x or "time_to_die" in x:labels.add("fight_remains")
    if ("target.health" in x or h=="health" or h=="health_pct"):
        labels.add("target_health")
    if "pool" in x:labels.add("pooling")
    return sorted(labels) if labels else ["unknown"]

def is_target_symbol(symbol:str)->bool:
    return symbol in TARGETS or symbol.startswith(("spell_targets.","active_enemies."))

def count_literal_comparisons(node,field:str)->list[dict]:
    """Literal target-count source comparisons, NOT gameplay breakpoints."""
    found=[]
    def walk(n):
        if not isinstance(n,list) or not n:return
        if n[0]=="binary" and len(n)==4:
            if n[1] in COMPARE:
                left,right=n[2],n[3]
                for sym,num,direction in (
                    (left,right,"symbol_left"),(right,left,"symbol_right")
                ):
                    if (isinstance(sym,list) and len(sym)==2 and
                        sym[0]=="symbol" and is_target_symbol(sym[1]) and
                        isinstance(num,list) and len(num)==2 and num[0]=="number"):
                        found.append({
                            "condition_field":field,"symbol":sym[1],
                            "operator":n[1],"literal":num[1],
                            "direction":direction,
                            "real_target_switch_threshold":"UNKNOWN"})
            walk(n[2]);walk(n[3])
        elif n[0] in ("unary","function") and len(n)==3:walk(n[2])
    walk(node)
    return found

def compile_profile(raw:bytes,metadata:dict)->dict:
    if not isinstance(raw,bytes) or not isinstance(metadata,dict):
        raise HypothesisIRError("RAW_SOURCE_AND_PINNED_METADATA_REQUIRED")
    if git_blob(raw)!=metadata.get("git_blob"):
        raise HypothesisIRError("OFFICIAL_PROFILE_SOURCE_BLOB_MISMATCH")
    parsed=parse_profile(raw,require_source=True,
                         expected_git_blob=metadata["git_blob"])
    lists={}
    tag_counts=Counter()
    control_counts=Counter()
    all_rows=0
    for name,rows in parsed["action_lists"].items():
        compiled=[]
        for index,row in enumerate(rows):
            if row["index"]!=index or row["list"]!=name:
                raise HypothesisIRError("SOURCE_ROW_ORDER_IDENTITY_DRIFT")
            action=row["action"]
            control=(action in CONTROL_COMMANDS or
                     row["behavior"] in ("CALL","RUN","SWAP_UNSUPPORTED","VARIABLE"))
            if control:control_counts[row["behavior"]]+=1
            conditions={}
            targets=[]
            symbols=set()
            for field,expr in row["expression_fields"].items():
                conditions[field]={
                    "raw_expression":expr["source"],
                    "source_ast":expr["ast"],
                    "symbols":expr["symbols"],
                    "independent_state_result":"UNKNOWN",
                }
                symbols.update(expr["symbols"])
                targets.extend(count_literal_comparisons(expr["ast"],field))
            contexts=sorted({tag for symbol in symbols
                             for tag in source_contexts(symbol)})
            if action=="pool_resource":contexts=sorted(set(contexts+["pooling"]))
            tag_counts.update(contexts)
            dest=None
            if row["behavior"] in ("CALL","RUN","SWAP_UNSUPPORTED"):
                values=[a["value"] for a in row["attributes"] if a["key"]=="name"]
                if len(values)!=1 or values[0] not in parsed["action_lists"]:
                    raise HypothesisIRError("CONTROL_EDGE_TARGET_NOT_PINNED")
                dest=values[0]
            compiled.append({
                "identity":{
                    "source_list":name,"source_index":index,
                    "source_line":row["source_line"],
                    "source_line_sha256":row["source_sha256"],
                },
                "source_text":row["source_text"],
                "action":action,"behavior":row["behavior"],
                "kind":"APL_CONTROL" if control else "EXECUTABLE_SOURCE_CANDIDATE",
                "source_priority_ordinal":index,
                "conditions":conditions,
                "control_destination":dest,
                "context_hints_not_mechanic_truth":contexts,
                "literal_target_count_comparisons_not_verified_breakpoints":targets,
                "expected_ready":"UNKNOWN",
                "simultaneously_ready_source_priority":"UNKNOWN",
                "real_WoW_dummy_expected_cast":"UNKNOWN",
            })
        lists[name]=compiled
        all_rows+=len(compiled)
    if all_rows!=parsed["source_action_line_count"] or "default" not in lists:
        raise HypothesisIRError("SOURCE_ROW_RECONCILIATION_FAILED")
    return {
        "schema":SCHEMA,"policy":POLICY,
        "spec_key":metadata["key"],"class_key":metadata["class_key"],
        "source_git_blob":metadata["git_blob"],
        "profile_sha256":sha256(raw).hexdigest(),
        "source_only_priority_graph":{
            "list_order":list(lists),"lists":lists,"edges":parsed["graph_edges"],
            "source_variable_sites":parsed["variable_definitions"]
        },
        "opener_hypothesis":{
            "has_precombat_list":"precombat" in lists,
            "precombat_source_rows":len(lists.get("precombat",[])),
            "default_list_candidate_rows":len(lists["default"]),
            "first_actual_cast":"UNKNOWN",
            "runtime_opener_sequence":"UNKNOWN",
            "opener_end_condition":"UNKNOWN",
            "precombat_source_order_is_NOT_cast_order":True
        },
        "coverage":{
            "source_action_rows":all_rows,
            "action_lists":len(lists),
            "source_controls":dict(sorted(control_counts.items())),
            "condition_context_hints":dict(sorted(tag_counts.items())),
            "source_symbol_count":len(parsed["source_symbol_dependencies"]),
            "literal_target_count_comparisons":sum(
                len(row["literal_target_count_comparisons_not_verified_breakpoints"])
                for rows in lists.values() for row in rows)
        },
        "evidence_status":{
            "source_APL_hypothesis_extraction":True,
            "native_opener_sequence_proven":False,
            "complete_positive_READY_proven":False,
            "WCL_blind_candidate_locked":False,
            "independent_WCL_holdout_proven":False,
            "validated_general_rotation_priority":False,
            "target_dummy_error_safe":False,
            "MAIN_promoted":False
        }
    }

def run(root:Path,manifest_path:Path)->dict:
    manifest=load_manifest(manifest_path)
    root=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       capture_output=True,text=True,check=True).stdout.strip()
    if rev!=manifest["official_simc_commit"]:
        raise HypothesisIRError("PINNED_OFFICIAL_SOURCE_COMMIT_CHANGED")
    models=[]
    for metadata in manifest["profiles"]:
        target=(root/metadata["profile"]).resolve(strict=True)
        if not target.is_relative_to(root):
            raise HypothesisIRError("SOURCE_PROFILE_PATH_ESCAPED_ROOT")
        models.append(compile_profile(target.read_bytes(),metadata))
    if len({m["class_key"] for m in models})<2:
        raise HypothesisIRError("UNRELATED_CLASSES_REQUIRED_FOR_GENERIC_E2E")
    return {
        "schema":"ZrotMultiSpecGeneralRotationSourceHypothesisIRV1",
        "policy":POLICY,"pinned_simc_commit":rev,"models":models,
        "class_count":len({m["class_key"] for m in models}),
        "source_action_rows_total":sum(m["coverage"]["source_action_rows"]
                                       for m in models),
        "source_only_hypotheses":True,
        "native_positive_ready_NOT_proven":True,
        "WCL_API_calls":0,"MAIN_promoted":False
    }

def selftest():
    raw=(
        b"actions.precombat=mark\n"
        b"actions=variable,name=20swindow,op=set,value=1\n"
        b"actions+=/call_action_list,name=cleave,if=active_enemies>=2\n"
        b"actions+=/filler,if=rage>=50&movement.distance<5\n"
        b"actions.cleave=alpha,if=spell_targets.alpha>3\n"
        b"actions.cleave+=/beta\n"
    )
    model=compile_profile(raw,{"key":"alpha","class_key":"other",
                                "git_blob":git_blob(raw)})
    assert model["coverage"]["source_action_rows"]==6
    assert model["coverage"]["action_lists"]==3
    assert model["opener_hypothesis"]["precombat_source_rows"]==1
    assert model["opener_hypothesis"]["first_actual_cast"]=="UNKNOWN"
    lists=model["source_only_priority_graph"]["lists"]
    assert lists["default"][1]["kind"]=="APL_CONTROL"
    assert lists["default"][1]["control_destination"]=="cleave"
    assert lists["default"][2]["kind"]=="EXECUTABLE_SOURCE_CANDIDATE"
    assert "movement" in lists["default"][2]["context_hints_not_mechanic_truth"]
    assert lists["default"][1]["literal_target_count_comparisons_not_verified_breakpoints"][0]["literal"]==2
    assert lists["cleave"][0]["literal_target_count_comparisons_not_verified_breakpoints"][0]["literal"]==3
    assert lists["default"][2]["expected_ready"]=="UNKNOWN"
    assert model["evidence_status"]["validated_general_rotation_priority"] is False
    assert count_literal_comparisons(["binary",">=",["symbol","variable.aoe_count"],["number",2.0]],"if")==[]
    try:compile_profile(raw,{"key":"alpha","class_key":"other","git_blob":"a"*40})
    except HypothesisIRError:pass
    else:raise AssertionError("UNPINNED_PROFILE_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":15,"Native_CXX_not_run":True,"WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.source_root and a.manifest:r=run(a.source_root,a.manifest)
    elif not a.source_root and not a.manifest:r=selftest()
    else:p.error("both source and manifest must be supplied")
    raw=canonical(r)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
        print("GENERIC_ROTATION_SOURCE_IR_SHA256="+sha256(raw).hexdigest())
    else:print(raw.decode(),end="")

if __name__=="__main__":main()
