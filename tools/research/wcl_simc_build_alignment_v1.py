#!/usr/bin/env python3
"""Pinned public SimC talent export ↔ observed WCL talentTree comparator.

Implements Blizzard's 6-bit LSB-first talent-export stream; requires separately
supplied per-spec complete node ordering and entry metadata. Unknown nodes,
version drift, or unparsable encodings FAIL CLOSED. Even structurally matching
selections do not prove identical full combat build/gear or APL applicability.
Offline mode performs only synthetic tests; no implicit network or WCL API.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

from wcl_dual_cohort_state_observability_v1 import read_cohort
from wcl_simc_postlock_real_audit_v1 import _zip
from wcl_simc_postlock_real_audit_v1 import _canonical as canonical, _sha as sha

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
ALPHABET="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
EXPECTED_PROFILE_BLOB="3225992ed5b754ad5d61e8b785d9d859f1eed1be"
EXPECTED_SPEC=72
EXPECTED_VERSION=2

class BuildSourceError(ValueError):
    pass


class Bits:
    """Read exact Blizzard ExportUtil 6-bit characters, LSB-first."""
    def __init__(self,raw:str):
        if (not isinstance(raw,str) or not 26<=len(raw)<=512 or
            any(c not in ALPHABET for c in raw)):
            raise BuildSourceError("UNRECOGNIZED_TALENT_STRING")
        self.values=[ALPHABET.index(c) for c in raw]
        self.pos=0
    def get(self,n:int)->int:
        if type(n) is not int or not 1<=n<=16:
            raise BuildSourceError("INVALID_BIT_WIDTH")
        if self.pos+n>len(self.values)*6:
            raise BuildSourceError("TRUNCATED_TALENT_STRING")
        result=0
        for i in range(n):
            off=self.pos+i
            result|=((self.values[off//6]>>(off%6))&1)<<i
        self.pos+=n
        return result
    def padding_valid(self):
        return (len(self.values)*6-self.pos<6 and
            all(((self.values[i//6]>>(i%6))&1)==0
                for i in range(self.pos,len(self.values)*6)))


def parse_profile(raw:bytes)->dict:
    git_blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
    if git_blob!=EXPECTED_PROFILE_BLOB:
        raise BuildSourceError("UNPINNED_OFFICIAL_SIMC_PROFILE")
    text=raw.decode("utf-8")
    if not re.search(r"(?m)^spec=fury$",text):
        raise BuildSourceError("PINNED_PROFILE_SPEC_MISMATCH")
    rows=re.findall(r"(?m)^talents=([A-Za-z0-9+/]+)\s*$",text)
    if len(rows)!=1:raise BuildSourceError("AMBIGUOUS_PROFILE_TALENT_EXPORT")
    return {"export":rows[0],"profile_blob_sha1":git_blob,
            "source_simc_spec":"fury",
            "source_profile_talent_export_sha256":sha(rows[0].encode()),
            "profile_has_omnium_talent_directives":
                bool(re.search(r"(?m)^omnium_talents=",text))}


def tree_contract(data:object,spec_id:int)->dict:
    if not isinstance(data,list) or len(data)<1:
        raise BuildSourceError("MISSING_TREE_DATA")
    chosen=[x for x in data if isinstance(x,dict) and x.get("specId")==spec_id]
    if len(chosen)!=1:raise BuildSourceError("SPEC_TREE_NOT_UNIQUE")
    t=chosen[0]
    order=t.get("fullNodeOrder")
    if not isinstance(order,list) or len(order)<50 or len(order)!=len(set(order)):
        raise BuildSourceError("UNTRUSTED_NODE_ORDER")
    if any(type(x) is not int or x<=0 for x in order):
        raise BuildSourceError("UNTRUSTED_NODE_IDS")
    if order!=sorted(order):
        raise BuildSourceError("UNSORTED_NODE_ORDER")
    nodes={}
    for field in ("classNodes","specNodes","heroNodes","subTreeNodes"):
        group=t.get(field)
        if not isinstance(group,list):raise BuildSourceError("TREE_GROUP_MISSING_"+field)
        for node in group:
            if not isinstance(node,dict) or type(node.get("id")) is not int:
                raise BuildSourceError("MALFORMED_TREE_NODE")
            ident=node["id"]
            if ident in nodes and nodes[ident]!=node:
                raise BuildSourceError("INCONSISTENT_NODE_ACROSS_GROUPS")
            nodes[ident]=node
    if len(nodes)<30:raise BuildSourceError("TREE_METADATA_INCOMPLETE")
    return {"spec_id":spec_id,"node_order":order,"nodes":nodes,
            "public_tree_input_sha256":sha(canonical(data)),
            "subtree_node_count":sum(1 for n in nodes.values()
                                    if n.get("type")=="subtree")}


def decode(export:str,tree:dict)->dict:
    bits=Bits(export)
    if bits.get(8)!=EXPECTED_VERSION:
        raise BuildSourceError("TALENT_EXPORT_VERSION_NOT_SUPPORTED")
    spec=bits.get(16)
    if spec!=tree["spec_id"]:raise BuildSourceError("TALENT_SPEC_ID_MISMATCH")
    tree_hash=bytes(bits.get(8) for _ in range(16))
    entries=[]
    missing=[]
    for nid in tree["node_order"]:
        selected=bits.get(1)
        if selected==0:continue
        node=tree["nodes"].get(nid)
        if not isinstance(node,dict):
            missing.append(nid)
            # Do not try parsing remaining bits without the missing node's type.
            raise BuildSourceError("SELECTED_NODE_METADATA_MISSING")
        choices=node.get("entries")
        if not isinstance(choices,list) or not choices:
            raise BuildSourceError("SELECTED_NODE_ENTRIES_MISSING")
        choices=sorted(choices,key=lambda e:e.get("index",0))
        purchased=bits.get(1)==1
        if purchased:
            partial=bits.get(1)==1
            max_rank=node.get("maxRanks")
            if type(max_rank) is not int:
                max_rank=choices[0].get("maxRanks",1)
            if type(max_rank) is not int or max_rank<1:
                raise BuildSourceError("UNVERIFIED_NODE_MAX_RANK")
            rank=bits.get(6) if partial else max_rank
            if not 1<=rank<=max_rank:
                raise BuildSourceError("TALENT_RANK_OUT_OF_RANGE")
            is_choice=bits.get(1)==1
            idx=bits.get(2) if is_choice else 0
        else:
            rank=1;idx=0
        if idx>=len(choices):raise BuildSourceError("TALENT_CHOICE_ENTRY_MISSING")
        entry_id=choices[idx].get("id")
        if type(entry_id) is not int or entry_id<1:
            raise BuildSourceError("INVALID_ENTRY_ID")
        entries.append((nid,entry_id,rank))
    if not bits.padding_valid():
        raise BuildSourceError("EXTRA_TALENT_BITS_OR_NONZERO_PADDING")
    return {"spec_id":spec,
            "loadout_version":EXPECTED_VERSION,
            "loadout_tree_hash_zero":tree_hash==bytes(16),
            "loadout_tree_hash_sha256":sha(tree_hash),
            "selected":sorted(entries),
            "source_export_sha256":sha(export.encode()),
            "decoded_node_count":len(entries)}


def observed_tree(events:list,actor:int)->dict:
    sample=[]
    casts=[e for e in events if e.get("sourceID")==actor and
           e.get("type") in ("cast","begincast")]
    if not casts:raise BuildSourceError("NO_ACTOR_CASTS")
    first_cast=min(x["timestamp"] for x in casts)
    for e in events:
        if e.get("type")!="combatantinfo" or e.get("sourceID")!=actor:
            continue
        if e.get("timestamp")>=first_cast:
            continue
        spec=e.get("specID")
        raw=e.get("talentTree")
        if spec!=EXPECTED_SPEC or not isinstance(raw,list):
            raise BuildSourceError("WCL_COMBATANT_SPEC_OR_TREE_MISSING")
        normalized=[]
        for item in raw:
            if not isinstance(item,dict):raise BuildSourceError("MALFORMED_WCL_TALENT_ENTRY")
            node,entry,rank=(item.get(k) for k in ("nodeID","id","rank"))
            if any(type(x) is not int or x<0 for x in (node,entry,rank)):
                raise BuildSourceError("INVALID_WCL_TALENT_NODE_OR_RANK")
            if rank>0: normalized.append((node,entry,rank))
        # WCL may carry multi-entry side-system selections (e.g. a node
        # with several different entry/rank tuples). Preserve all of them;
        # the spec-tree index must classify, never silently pick one.
        if len(normalized)!=len(set(normalized)):
            raise BuildSourceError("EXACT_DUPLICATE_WCL_TALENT_TUPLE")
        sample.append((e["timestamp"],tuple(sorted(normalized))))
    if not sample:raise BuildSourceError("NO_STRICT_PRE_BUILD_SNAPSHOT")
    if len(set(x[1] for x in sample))!=1:
        raise BuildSourceError("CHANGED_COMBATANT_TREE_WITHIN_OPENER")
    return {"spec_id":EXPECTED_SPEC,"selected":list(sample[0][1]),
            "raw_numeric_tree_selected_node_count":len(sample[0][1]),
            "raw_numeric_selection_sha256":sha(canonical(sample[0][1])),
            "snapshot_timestamp":sample[0][0],
            "first_cast_timestamp":first_cast,
            "strict_pre":True}


def compare_one(decoded:dict, observed:dict,tree:dict)->dict:
    sim=set(tuple(x) for x in decoded["selected"])
    wcl=set(tuple(x) for x in observed["selected"])
    known=set(tree["node_order"])
    external=sorted({x[0] for x in wcl if x[0] not in known})
    normal_wcl={x for x in wcl if x[0] in known}
    normal_counts=Counter(x[0] for x in normal_wcl)
    duplicates=sorted(n for n,count in normal_counts.items() if count>1)
    if external:
        verdict="UNKNOWN_EXTERNAL_WCL_TALENT_NODES"
    elif duplicates:
        verdict="UNKNOWN_WCL_MULTIENTRY_SPEC_TREE_NODE"
    else:
        verdict=("NUMERIC_SELECTION_MATCH" if sim==normal_wcl
                 else "NUMERIC_SELECTION_DIFFERENCE")
    sim_by_node={x[0]:x[1:] for x in sim}
    wcl_by_node={x[0]:x[1:] for x in normal_wcl}
    missing=sorted(sim_by_node.keys()-wcl_by_node.keys())
    extra=sorted(wcl_by_node.keys()-sim_by_node.keys())
    different=sorted(n for n in sim_by_node.keys() & wcl_by_node.keys()
                     if sim_by_node[n]!=wcl_by_node[n])
    return {"status":verdict,
            "WCL_selected_talent_entry_count":len(wcl),
            "WCL_selected_node_count":len({x[0] for x in wcl}),
            "WCL_selected_spec_tree_entry_count":len(normal_wcl),
            "WCL_node_ids_outside_public_spec_tree":external,
            "WCL_multientry_spec_tree_nodes":duplicates,
            "external_side_system_semantics":"UNKNOWN",
            "SimC_decoded_selected_node_count":len(sim),
            "shared_identical_selected_nodes":len(sim&normal_wcl),
            "simc_only_nodes_count":len(missing),
            "wcl_only_nodes_count":len(extra),
            "choice_or_rank_mismatched_node_count":len(different),
            "different_numeric_node_ids":sorted(set(missing+extra+different)),
            "matches_entire_SimC_combat_configuration":False,
            "SimC_APL_ready_to_apply_to_WCL":False,
            "mechanic_readiness":"UNKNOWN",
            "priority_rule_validated":False}


def run(wcl_discovery:Path,wcl_holdout:Path,profile:Path,talent_metadata:Path)->dict:
    raw=profile.read_bytes()
    src=parse_profile(raw)
    tdata=json.loads(talent_metadata.read_bytes())
    tree=tree_contract(tdata,EXPECTED_SPEC)
    decoded=decode(src["export"],tree)
    out={}
    for kind,path in (("discovery",wcl_discovery),("holdout",wcl_holdout)):
        gate,view,events,_=read_cohort(_zip(path),role=kind)
        observed=observed_tree(events,gate["actor_id"])
        out[kind]=compare_one(decoded,observed,tree)
        out[kind]["raw_talent_tree_sha256"]=observed["raw_numeric_selection_sha256"]
        out[kind]["combatant_build_strict_pre"]=True
    return {"schema":"ZrotPostLockWclSimcTalentSelectionAlignmentV1",
            "scope_policy_id":POLICY,
            "status":"POSTLOCK_STRUCTURAL_TALENT_COMPARISON_ONLY",
            "profile_git_blob_sha1":src["profile_blob_sha1"],
            "profile_export_sha256":src["source_profile_talent_export_sha256"],
            "metadata_sha256":tree["public_tree_input_sha256"],
            "talent_export_version":decoded["loadout_version"],
            "talent_export_spec_id":decoded["spec_id"],
            "export_tree_hash_zero":decoded["loadout_tree_hash_zero"],
            "external_tree_hash_authoritatively_verified":False,
            "external_tree_patch_equivalence_to_WCL":"UNKNOWN",
            "profile_extra_omnium_talent_configuration":src["profile_has_omnium_talent_directives"],
            "simc_encoded_talent_count":decoded["decoded_node_count"],
            **out,
            "same_WCL_build_between_cohorts":
                out["discovery"]["raw_talent_tree_sha256"]==
                out["holdout"]["raw_talent_tree_sha256"],
            "full_build_equivalence_to_current_SimC":"UNKNOWN",
            "priority_or_optimality_inferred":False,
            "dummy_trainer_error_rule_ready":False,
            "MAIN_promotion":False}


def selftest()->dict:
    def pack(values):
        bits=[]
        for width,value in values:
            bits.extend((value>>i)&1 for i in range(width))
        while len(bits)%6:bits.append(0)
        return "".join(ALPHABET[sum(bits[i+j]<<j for j in range(6))]
                       for i in range(0,len(bits),6))
    tree={"spec_id":72,"node_order":[1,2,3],
          "nodes":{1:{"id":1,"entries":[{"id":101,"maxRanks":1}],"maxRanks":1},
                   2:{"id":2,"entries":[{"id":202,"maxRanks":2}],"maxRanks":2},
                   3:{"id":3,"entries":[{"id":303,"index":0},{"id":304,"index":1}],
                      "maxRanks":1,"type":"choice"}}}
    values=[(8,2),(16,72)]+[(8,0)]*16+[
        (1,1),(1,1),(1,0),(1,0),
        (1,1),(1,1),(1,1),(6,1),(1,0),
        (1,1),(1,1),(1,0),(1,1),(2,1)]
    raw=pack(values)
    # Test miniature self-test stream separately from production size limits.
    if len(raw)<26:raise AssertionError("BROKEN_TEST_STREAM")
    d=decode(raw,tree)
    assert d["selected"]==[(1,101,1),(2,202,1),(3,304,1)]
    assert d["spec_id"]==72
    assert d["loadout_tree_hash_zero"] is True
    m=compare_one(d,{"selected":d["selected"]},tree)
    assert m["status"]=="NUMERIC_SELECTION_MATCH"
    bad=compare_one(d,{"selected":[(1,101,1)]},tree)
    assert bad["status"]=="NUMERIC_SELECTION_DIFFERENCE"
    assert bad["SimC_APL_ready_to_apply_to_WCL"] is False
    off_tree=compare_one(d,{"selected":d["selected"]+[
        (110412,137002,1),(110412,137003,2),(110412,137004,1)]},tree)
    assert off_tree["status"]=="UNKNOWN_EXTERNAL_WCL_TALENT_NODES"
    assert off_tree["WCL_node_ids_outside_public_spec_tree"]==[110412]
    assert off_tree["external_side_system_semantics"]=="UNKNOWN"
    try:decode(pack([(8,3),(16,72)]+[(8,0)]*16+values[18:]),tree)
    except BuildSourceError as e:assert "VERSION" in str(e)
    else:raise AssertionError("ACCEPTED_WRONG_VERSION")
    try:decode(pack([(8,2),(16,73)]+[(8,0)]*16+values[18:]),tree)
    except BuildSourceError as e:assert "SPEC_ID" in str(e)
    else:raise AssertionError("ACCEPTED_WRONG_SPEC")
    return {"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":10,"external_WCL_or_SimC_source_loaded":False,
            "full_build_equivalence_proven":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--discovery-zip",type=Path)
    p.add_argument("--holdout-zip",type=Path)
    p.add_argument("--profile",type=Path)
    p.add_argument("--tree-data",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    inputs=(a.discovery_zip,a.holdout_zip,a.profile,a.tree_data)
    if all(x is None for x in inputs):result=selftest()
    elif all(x is not None for x in inputs):
        result=run(*inputs)
    else:p.error("provide all four inputs or none (offline test)")
    blob=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("WCL_SIMC_TALENT_ALIGNMENT_RECEIPT_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
