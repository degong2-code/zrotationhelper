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


def _selector_status(tree:dict, talent_nid:int|None, selections:list)->dict:
    """Only explicit active hero-tree chooser entries can prove activation."""
    if talent_nid is None:
        return {"active":None,"status":"UNKNOWN_NO_TALENT_NODE_MAPPING"}
    node=tree["nodes"].get(talent_nid)
    subtree=node.get("subTreeId") if isinstance(node,dict) else None
    if type(subtree) is not int or subtree<=0:
        return {"active":None,"status":"UNKNOWN_NO_SUBTREE_MEMBERSHIP"}
    matches=[]
    for parent_nid,parent in tree["nodes"].items():
        if parent.get("type")!="subtree":continue
        for entry in parent.get("entries",[]):
            if entry.get("traitSubTreeId")==subtree:
                matches.append((parent_nid,entry.get("id")))
    if len(matches)!=1:
        return {"active":None,"status":"UNKNOWN_HERO_SELECTOR_NOT_UNIQUE",
                "subtree_id":subtree,"selector_matches":len(matches)}
    parent_nid,expected_entry=matches[0]
    observed=[entry for nid,entry,rank in selections
              if nid==parent_nid and rank>0]
    if len(observed)!=1:
        return {"active":None,"status":"UNKNOWN_HERO_SELECTOR_SELECTION_MISSING_OR_MULTIPLE",
                "subtree_id":subtree,"selector_node_id":parent_nid,
                "selection_count":len(observed)}
    return {"active":observed[0]==expected_entry,
            "status":"EXPLICIT_PARENT_HERO_SELECTOR_EVIDENCE",
            "subtree_id":subtree,"selector_node_id":parent_nid,
            "actual_selector_entry_id":observed[0],
            "required_selector_entry_id":expected_entry}


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
        sim_active=_selector_status(tree,nid,sim["selected"])
        wcl_active=_selector_status(tree,nid,actual["selected"])
        # A tree-root can appear selected in the export while its entire
        # hero subtree is inactive. The chooser, not raw root presence,
        # determines applicability. Still require root selection for TRUE.
        def talent_guard(selected,selector):
            if selected is False or selector["active"] is False:
                return "FALSE"
            if selected is True and selector["active"] is True:
                return "TRUE"
            return "UNKNOWN"
        profile_guard=talent_guard(sim_selected,sim_active)
        wcl_guard=talent_guard(wcl_selected,wcl_active)
        if profile_guard=="FALSE" and wcl_guard=="FALSE":
            conditional_state="BOTH_INACTIVE_HERO_BRANCH"
        elif profile_guard=="TRUE" and wcl_guard=="TRUE":
            conditional_state="HERO_GUARD_AGREES_TARGET_COUNT_UNKNOWN"
        else:
            conditional_state="UNKNOWN_OR_DIFFERENT_HERO_GUARD"
        out.append({**row,"resolved_node_id":nid,
                    "simc_profile_hero_talent_guard":profile_guard,
                    "wcl_pre_hero_talent_guard":wcl_guard,
                    "conditional_branch_state":conditional_state,
                    "target_count_operand":"active_enemies",
                    "target_count_at_wcl_decision":"UNKNOWN",
                    "branch_action_priority_verified":False,
                    "simc_profile_raw_node_selected":sim_selected,
                    "wcl_strict_pre_raw_node_selected":wcl_selected,
                    "raw_node_selection_comparison":source_state,
                    "simc_hero_selector_state":sim_active,
                    "wcl_hero_selector_state":wcl_active,
                    "hero_talent_enabled_same_in_both":(
                        sim_active["active"]==wcl_active["active"]
                        if isinstance(sim_active["active"],bool) and
                           isinstance(wcl_active["active"],bool) else None),
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
    selector={"nodes":{
      5:{"name":"Lightning Strikes","subTreeId":500},
      9:{"name":"Slayer's Dominance","subTreeId":501},
      99:{"type":"subtree","name":"Hero Choice",
          "entries":[{"id":1900,"traitSubTreeId":500},
                     {"id":1901,"traitSubTreeId":501}]}}}
    sel_yes=_selector_status(selector,5,[(99,1900,1)])
    sel_no=_selector_status(selector,5,[(99,1901,1)])
    assert sel_yes["active"] is True and sel_no["active"] is False
    assert sel_yes["status"]=="EXPLICIT_PARENT_HERO_SELECTOR_EVIDENCE"
    # Same raw root selection can have opposite effective hero-trait state.
    assert sel_no["active"] is False
    assert _selector_status(selector,5,[])["active"] is None
    assert _selector_status(tree,5,[])["active"] is None
    try:source_branches(b"actions+=/rampage,if=rage>=80\n")
    except APLBranchError:pass
    else:raise AssertionError("NON_BRANCH_APL_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":12,
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
