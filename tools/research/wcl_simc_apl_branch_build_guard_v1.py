#!/usr/bin/env python3
"""Post-lock SimC APL talent-branch applicability to real WCL builds.

Only compares talent selections; no action readiness or active enemy count
is invented. Uses pinned public SimC profile and pinned public spec-tree data,
plus existing independent WCL raw snapshots. Spec names remain source inputs,
not generic engine hardcoding. Default: offline synthetic tests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from wcl_simc_build_alignment_v1 import parse_profile,tree_contract,decode,observed_tree
from wcl_simc_multientry_omnium_audit_v1 import METADATA_SHA
from wcl_dual_cohort_state_observability_v1 import read_cohort
from wcl_simc_postlock_real_audit_v1 import _zip,_canonical as canonical,_sha as sha

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
class APLBranchError(ValueError):pass


def _normalize(s:str)->str:
    return re.sub(r"[^a-z0-9]","",s.casefold())


def source_branches(profile_raw:bytes):
    text=profile_raw.decode("utf-8")
    rows=[]
    for line in text.splitlines():
        m=re.fullmatch(r"actions\+=/run_action_list,name=([a-z_]+),if=talent\.([a-z_]+)&active_enemies(=|>|<|>=|<=)([0-9]+)",line)
        if m:
            rows.append({"action_list":m[1],"talent_token":m[2],
                         "enemy_comparator":m[3],"enemy_threshold":int(m[4]),
                         "source_apl_row_sha256":sha(line.encode())})
    if not rows:raise APLBranchError("NO_EXPLICIT_TALENT_GUARDED_APL_BRANCHES")
    return rows


def unique_node_for_token(tree,token):
    expected=_normalize(token)
    matches=[]
    for node_id,node in tree["nodes"].items():
        names=str(node.get("name","")).split(" / ")
        if expected in {_normalize(x) for x in names}:
            matches.append(node_id)
    return matches[0] if len(matches)==1 else None


def evaluate(profile_raw:bytes,tree:dict,branches:list,actual:dict):
    sim=decode(parse_profile(profile_raw)["export"],tree)
    sim_nodes={row[0] for row in sim["selected"]}
    wcl_nodes={row[0] for row in actual["selected"]}
    out=[]
    for row in branches:
        nid=unique_node_for_token(tree,row["talent_token"])
        if nid is None:
            source_state="UNKNOWN_METADATA_NODE_MAPPING"
            sim_selected=None;wcl_selected=None
        else:
            sim_selected=nid in sim_nodes
            wcl_selected=nid in wcl_nodes
            if sim_selected and not wcl_selected:
                source_state="PROFILE_SELECTED_WCL_NOT_SELECTED"
            elif sim_selected and wcl_selected:
                source_state="BOTH_SELECTED"
            elif not sim_selected and wcl_selected:
                source_state="WCL_SELECTED_PROFILE_NOT_SELECTED"
            else:source_state="NEITHER_SELECTED"
        out.append({**row,"resolved_node_id":nid,
                    "simc_profile_talent_selected":sim_selected,
                    "wcl_strict_pre_talent_selected":wcl_selected,
                    "structural_talent_applicability":source_state,
                    "active_enemies_at_wcl_decision":"UNKNOWN",
                    "simc_foreground_action_replay":"NOT_RUN",
                    "profile_action_list_priority_transfer":"BLOCKED",
                    "validated_rotation_rule":False})
    return out


def study(profile:Path,tree_data:Path,discovery:Path,holdout:Path):
    profile_raw=profile.read_bytes()
    parse_profile(profile_raw)
    metadata=tree_data.read_bytes()
    if sha(metadata)!=METADATA_SHA:raise APLBranchError("UNPINNED_PUBLIC_TALENT_METADATA")
    tree=tree_contract(json.loads(metadata),72)
    branches=source_branches(profile_raw)
    result={}
    for kind,path in (("discovery",discovery),("holdout",holdout)):
        gate,view,events,_=read_cohort(_zip(path),role=kind)
        observed=observed_tree(events,gate["actor_id"])
        result[kind]={"spec_id":observed["spec_id"],
                      "strict_pre_combatant_talent_evidence":True,
                      "branch_statuses":evaluate(profile_raw,tree,branches,observed)}
    return {"schema":"ZrotPostlockSimcTalentBranchApplicabilityV1",
            "scope_policy_id":POLICY,
            "status":"BUILD_GUARD_STRUCTURAL_COMPARISON_ONLY",
            "profile_sha256":sha(profile_raw),
            "source_branch_count":len(branches),
            "metadata_sha256":sha(metadata),
            **result,
            "inferred_WCL_target_count":None,
            "complete_SimC_build_equivalence":"UNKNOWN",
            "WCL_cooldown_resource_action_readiness":"UNKNOWN",
            "SimC_action_selection_replayed":False,
            "pairwise_priority_verified":False,
            "trainer_model_eligible":False,
            "MAIN_promotion":False}


def selftest():
    profile=b"actions+=/run_action_list,name=thane,if=talent.lightning_strikes&active_enemies=1\n"
    rows=source_branches(profile)
    assert rows[0]["talent_token"]=="lightning_strikes"
    assert rows[0]["enemy_threshold"]==1
    tree={"nodes":{5:{"name":"Lightning Strikes"},
                   7:{"name":"Slayer's Dominance"},8:{"name":"Improved Berserking / Warpaint"}}}
    assert unique_node_for_token(tree,"lightning_strikes")==5
    assert unique_node_for_token(tree,"slayers_dominance")==7
    assert unique_node_for_token(tree,"warpaint")==8
    assert unique_node_for_token(tree,"unmapped_ability") is None
    try:source_branches(b"actions+=/rampage,if=rage>=80\n")
    except APLBranchError:pass
    else:raise AssertionError("NON_BRANCH_APL_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":7,
            "actual_SimC_or_WCL_sources_read":False,
            "priority_validated":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path)
    p.add_argument("--tree-data",type=Path)
    p.add_argument("--discovery-zip",type=Path)
    p.add_argument("--holdout-zip",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    inputs=(a.profile,a.tree_data,a.discovery_zip,a.holdout_zip)
    if all(x is None for x in inputs):obj=selftest()
    elif all(x is not None for x in inputs):obj=study(*inputs)
    else:p.error("all source inputs required")
    blob=canonical(obj)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("SIMC_WCL_APL_BRANCH_GUARD_RECEIPT_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__": main()
