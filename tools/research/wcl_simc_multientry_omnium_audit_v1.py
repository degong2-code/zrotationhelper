#!/usr/bin/env python3
"""Post-lock structural audit of WCL multi-entry trait nodes and SimC Omnium.

Never guess that WCL TraitNodeEntry ids are SimC talent IDs or spell IDs.
A valid source is strict-PRE combatantinfo, immutable raw WCL evidence, and a
pinned public SimC profile plus bounded externally-identified talent metadata.
No argument: offline synthetic self-test, no network/API and no gameplay rules.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re

from wcl_simc_build_alignment_v1 import (
    BuildSourceError,EXPECTED_PROFILE_BLOB,EXPECTED_SPEC,
    parse_profile,tree_contract,decode,observed_tree,
)
from wcl_dual_cohort_state_observability_v1 import read_cohort
from wcl_simc_postlock_real_audit_v1 import _zip, _canonical as canonical, _sha as sha

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
METADATA_SHA="53bb1b612f140b666d66b75314db501bb1fa31923b66ad3f3cb02edbc5f3a07c"

class StructuralEvidenceError(ValueError): pass


def omnium_profile_values(raw:bytes):
    text=raw.decode("utf-8")
    lines=re.findall(r"(?m)^omnium_talents=(\S+)$",text)
    if len(lines)!=1: raise StructuralEvidenceError("OMNIUM_DIRECTIVE_MISSING_OR_AMBIGUOUS")
    tokens=lines[0].split("/")
    rows=[]
    for token in tokens:
        match=re.fullmatch(r"([0-9]+):([1-9][0-9]?)",token)
        if match is None:raise StructuralEvidenceError("OMNIUM_TALENT_TOKEN_UNRECOGNIZED")
        tid,rank=int(match[1]),int(match[2])
        if tid<1:raise StructuralEvidenceError("INVALID_OMNIUM_ID")
        rows.append((tid,rank))
    if len(rows)!=len(set(t for t,_ in rows)):
        raise StructuralEvidenceError("OMNIUM_DUPLICATE_TALENT")
    return rows


def metadata_index(tree):
    order=tree["node_order"]
    by_entry,by_spell,by_definition=defaultdict(list),defaultdict(list),defaultdict(list)
    for nid,node in sorted(tree["nodes"].items()):
        group=[k for k in ("classNodes","specNodes","heroNodes","subTreeNodes")
               if k in node.get("_group_members",[])]
        for ent in node.get("entries",[]):
            for key,table in (("id",by_entry),("spellId",by_spell),("definitionId",by_definition)):
                v=ent.get(key)
                if type(v) is int and v>0:
                    table[v].append({"node_id":nid,"entry_id":ent.get("id"),
                                     "entry_name":ent.get("name"),
                                     "node_type":node.get("type"),
                                     "metadata_field":key})
    return by_entry,by_spell,by_definition


def resolve_multientry(observed:dict, tree:dict):
    grouped=defaultdict(list)
    for nid,eid,rank in observed["selected"]:
        grouped[nid].append((eid,rank))
    multi=[]
    by_entry,by_spell,by_definition=metadata_index(tree)
    for nid,entries in sorted(grouped.items()):
        if len(entries)<2:continue
        node=tree["nodes"].get(nid)
        if node is None:
            multi.append({"node_id":nid,"status":"UNKNOWN_NODE_ABSENT_FROM_TREE",
                          "wcl_entries":[{"id":a,"rank":b} for a,b in sorted(entries)]})
            continue
        official={e.get("id") for e in node.get("entries",[]) if isinstance(e,dict)}
        can_map=all(eid in official for eid,_ in entries)
        multi.append({
            "node_id":nid,"node_type":node.get("type"),
            "node_name":node.get("name"),
            "node_is_in_full_spec_order":nid in tree["node_order"],
            "metadata_entry_ids_count":len(official),
            "all_raw_wcl_entry_ids_are_metadata_entries":can_map,
            "wcl_entries":[
                {"id":eid,"rank":rank,
                 "metadata_entry_name":next((e.get("name") for e in node.get("entries",[])
                                             if e.get("id")==eid),None),
                 "metadata_spell_id":next((e.get("spellId") for e in node.get("entries",[])
                                            if e.get("id")==eid),None)}
                for eid,rank in sorted(entries)],
            "single_choice_export_compatible":False if len(entries)>1 else None,
            "mechanic_mapping":"UNKNOWN",
        })
    return multi


def match_omnium_ids(omnium,tree):
    by_entry,by_spell,by_definition=metadata_index(tree)
    rows=[]
    for ident,rank in omnium:
        matches={}
        for field,table in (("entry_id",by_entry),("spell_id",by_spell),
                             ("definition_id",by_definition)):
            hits=table.get(ident,[])
            if hits:matches[field]=hits
        rows.append({"profile_talent_id":ident,"profile_rank":rank,
                     "matching_metadata_id_fields":matches,
                     "direct_wcl_entry_equivalence":"NOT_ASSERTED",
                     "omnium_selected_in_actual_WCL":"UNKNOWN"})
    return rows


def _node_descriptions(values,tree):
    result=[]
    for node_id in values:
        node=tree["nodes"].get(node_id)
        result.append({"node_id":node_id,
                      "metadata_name":node.get("name") if node else None,
                      "metadata_node_type":node.get("type") if node else None,
                      "source_patch_equivalence":"UNKNOWN"})
    return result


def inspect(profile,tree_data,discovery,holdout):
    raw=profile.read_bytes()
    sim=parse_profile(raw)
    meta=tree_data.read_bytes()
    if sha(meta)!=METADATA_SHA:
        raise StructuralEvidenceError("TALENT_METADATA_SNAPSHOT_CHANGED__REVALIDATE_PATCH")
    tree=tree_contract(json.loads(meta),EXPECTED_SPEC)
    decoded=decode(sim["export"],tree)
    omnium=omnium_profile_values(raw)
    sim_map={node:(entry,rank) for node,entry,rank in decoded["selected"]}
    result={}
    for role,path in (("discovery",discovery),("holdout",holdout)):
        gate,view,events,_=read_cohort(_zip(path),role=role)
        observed=observed_tree(events,gate["actor_id"])
        entries=defaultdict(list)
        for node,entry,rank in observed["selected"]:
            entries[node].append((entry,rank))
        normal={node:vals[0] for node,vals in entries.items() if len(vals)==1}
        matched=[node for node in sim_map if node in normal and sim_map[node]==normal[node]]
        diff=[node for node in sim_map if node in normal and sim_map[node]!=normal[node]]
        sim_only=[node for node in sim_map if node not in entries]
        wcl_only=[node for node in entries if node not in sim_map]
        multi=resolve_multientry(observed,tree)
        result[role]={
          "strict_pre_combatantinfo":True,
          "numeric_spec_id":observed["spec_id"],
          "simc_export_normal_node_identical_count":len(matched),
          "simc_export_normal_node_rank_or_choice_different_count":len(diff),
          "simc_export_missing_in_wcl_count":len(sim_only),
          "wcl_missing_in_simc_export_count":len(wcl_only),
          "normal_node_differences":_node_descriptions(diff,tree),
          "simc_only_nodes":_node_descriptions(sim_only,tree),
          "wcl_only_nodes":_node_descriptions(wcl_only,tree),
          "multientry_nodes":multi,
          "full_omnium_comparison":"UNVERIFIED",
          "full_build_equal_to_simc":False if (diff or sim_only or wcl_only) else None,
          "readiness":"UNKNOWN",
        }
    return {
      "schema":"ZrotWclSimcPostlockMultientryOmniumEvidenceV1",
      "scope_policy_id":POLICY,
      "status":"STRUCTURAL_NODE_AND_ID_NAMESPACE_AUDIT_NOT_GAMEPLAY",
      "simc_profile_git_blob_sha1":sim["profile_blob_sha1"],
      "public_talent_metadata_sha256":sha(meta),
      "talent_export_spec_id":decoded["spec_id"],
      "talent_export_selected_node_count":len(decoded["selected"]),
      "simc_omnium_talent_ids":match_omnium_ids(omnium,tree),
      "discovery":result["discovery"],
      "holdout":result["holdout"],
      "wcl_multi_node_equal_across_reports":
          result["discovery"]["multientry_nodes"]==
          result["holdout"]["multientry_nodes"],
      "omnium_direct_WCL_mapping_proven":False,
      "full_player_simc_build_equivalence":"UNKNOWN",
      "priority_or_optimality_proven":False,
      "trainer_mistake_classification":"UNKNOWN",
      "MAIN_promotion":False,
    }


def selftest():
    tree={"node_order":[100],"nodes":{100:{"id":100,"type":"tiered","name":"Fixture",
          "entries":[{"id":13,"name":"A"},{"id":14,"name":"B"}]}}}
    obs={"selected":[(100,13,1),(100,14,2)]}
    rows=resolve_multientry(obs,tree)
    assert len(rows)==1 and rows[0]["all_raw_wcl_entry_ids_are_metadata_entries"]
    assert rows[0]["node_type"]=="tiered"
    assert rows[0]["single_choice_export_compatible"] is False
    rows=resolve_multientry({"selected":[(100,13,1),(100,15,2)]},tree)
    assert rows[0]["all_raw_wcl_entry_ids_are_metadata_entries"] is False
    omnium=omnium_profile_values(b"spec=fury\nomnium_talents=136822:1/136823:2\n")
    assert omnium==[(136822,1),(136823,2)]
    assert all(row["direct_wcl_entry_equivalence"]=="NOT_ASSERTED"
               for row in match_omnium_ids(omnium,tree))
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":6,
            "actual_WCL_read":False,"actual_SimC_read":False,
            "validated_gameplay_priority":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path)
    p.add_argument("--tree-data",type=Path)
    p.add_argument("--discovery-zip",type=Path)
    p.add_argument("--holdout-zip",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    args=(a.profile,a.tree_data,a.discovery_zip,a.holdout_zip)
    if all(x is None for x in args):d=selftest()
    elif all(x is not None for x in args):d=inspect(*args)
    else:p.error("all four source inputs required")
    blob=canonical(d)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("WCL_SIMC_OMNIUM_STRUCTURAL_RECEIPT_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
