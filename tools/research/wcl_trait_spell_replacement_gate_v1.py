#!/usr/bin/env python3
"""WCL actor PRE talent+buff evidence for source-backed replacement family gates.

Uses independent WCL raw identity and pre-action aura observation, pinned public
spec-tree metadata for numeric trait node/entry identity, and frozen SimC source
mechanic hints. Does NOT assume patch equality or full player build equivalence.

A confirmed source-model replacement gate means the base action is replaced in
the model, NOT that the replacement button is off CD or should be pressed.
False/unknown state cannot authorize rotation error classification.
No-argument invocation is safe synthetic tests, no network/API/credentials.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from wcl_simc_build_alignment_v1 import observed_tree,tree_contract
from wcl_dual_cohort_state_observability_v1 import read_cohort
from wcl_simc_postlock_real_audit_v1 import _zip,_canonical as canonical,_sha as sha

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
METADATA_SHA="53bb1b612f140b666d66b75314db501bb1fa31923b66ad3f3cb02edbc5f3a07c"
SOURCE_RECEIPT_SHA="e622c7df37d9b792f403b00abe54228fa9a8f1dfac8133610a8517143afd80ab"
LOCK="c5e2bedeb7f4f0152e8ba86a30b1b13ecc5aa1374af4c0b01237a16151a1c98e"

class ReplacementGateError(ValueError): pass


def unique_trait(tree, name):
    matched=[]
    for nid,node in tree["nodes"].items():
        node_names=str(node.get("name","")).split(" / ")
        if name.casefold() in [t.strip().casefold() for t in node_names]:
            matched.append(nid)
    if len(matched)!=1:raise ReplacementGateError("NAMED_SPEC_TALENT_NODE_NOT_UNIQUE")
    ident=matched[0];node=tree["nodes"][ident]
    entries={e.get("id") for e in node.get("entries",[]) if type(e.get("id")) is int}
    if not entries:raise ReplacementGateError("TALENT_NODE_HAS_NO_ENTRIES")
    return ident,entries


def threeval_and(a,b):
    if a is False or b is False:return False
    if a is True and b is True:return True
    return None


def source_buff_pre(dec,idnum):
    row=dec.get("aura_pre",{}).get(str(idnum))
    if not isinstance(row,dict) or type(row.get("active")) is not bool:return None
    return row["active"]


def actor_trait_selected(events,actor,tree,trait_token):
    observed=observed_tree(events,actor)
    nid,entry_ids=unique_trait(tree,trait_token)
    entries=[(n,e,r) for n,e,r in observed["selected"] if n==nid]
    if not entries:return {"selected":False,"source":"STRICT_PRE_COMBATANTINFO",
                          "node_id":nid,"selection_count":0}
    if len(entries)!=1 or entries[0][1] not in entry_ids or entries[0][2]<1:
        raise ReplacementGateError("UNRECONCILED_TRAIT_ENTRY_IN_WCL")
    return {"selected":True,"source":"STRICT_PRE_COMBATANTINFO",
            "node_id":nid,"selection_count":1,
            "source_entry_id":entries[0][1],"source_rank":entries[0][2]}


def cohort(gate,view,events,tree,trait_token,buff_id):
    actor=gate["actor_id"]
    talent=actor_trait_selected(events,actor,tree,trait_token)
    counts=Counter()
    result=[]
    for i,row in enumerate(view["decisions"]):
        enabled=threeval_and(talent["selected"],source_buff_pre(row,buff_id))
        symbolic=("SOURCE_MODEL_PARENT_ACTION_REPLACED" if enabled is True
                  else "SOURCE_MODEL_PARENT_ACTION_UNREPLACED" if enabled is False
                  else "UNKNOWN_REPLACEMENT_GATE")
        counts["TRUE" if enabled is True else "FALSE" if enabled is False else "UNKNOWN"]+=1
        actual=row["ability_id"]
        casts_replacement=actual in (335096,335097)
        actual_expected_side=("CONSISTENT_WITH_REPLACEMENT_SOURCE_MODEL"
            if casts_replacement and enabled is True else
            "CAST_REPLACEMENT_WHILE_SOURCE_GATE_FALSE" if casts_replacement and enabled is False else
            "UNKNOWN_OR_UNMAPPED_ACTIONABILITY")
        if casts_replacement and enabled is False:
            counts["replacement_cast_with_negative_gate"]+=1
        result.append({
           "cast_index":i,"timestamp":row["timestamp"],
           "actual_numeric_spell_id":actual,
           "replacement_talent_precombat":talent["selected"],
           "recklessness_buff_strict_pre":source_buff_pre(row,buff_id),
           "source_model_replacement_gate":
               "TRUE" if enabled is True else "FALSE" if enabled is False else "UNKNOWN",
           "base_action_family_availability_by_replacement_alone":symbolic,
           "recorded_replacement_cast_consistency":actual_expected_side,
           "base_bloodthirst_actual_cd_ready":"UNKNOWN",
           "base_raging_blow_actual_cd_ready":"UNKNOWN",
           "replacement_bloodbath_actual_cd_ready":"UNKNOWN",
           "replacement_crushing_blow_actual_cd_ready":"UNKNOWN",
           "full_mechanic_build_equivalence":"UNKNOWN",
           "which_action_should_be_pressed":"UNKNOWN",
           "priority_or_mistake": "UNKNOWN"})
    return {"strict_pre_actor_spec":gate.get("observed_spec"),
            "trait_model_name":trait_token,
            "trait_numeric_precombat_evidence":talent,
            "casts_evaluated":len(result),
            "cast_replacement_gate_counts":{
              key:counts.get(key,0) for key in ("TRUE","FALSE","UNKNOWN")},
            "recorded_replacement_cast_with_false_gate":counts["replacement_cast_with_negative_gate"],
            "recorded_cast_details":result,
            "any_gameplay_recommendation":False}


def run(tree_file,source_receipt,discovery,holdout,trait_token,buff_id):
    raw=tree_file.read_bytes()
    if sha(raw)!=METADATA_SHA:raise ReplacementGateError("UNPINNED_PUBLIC_TALENT_TREE_SHA")
    tree=tree_contract(json.loads(raw),72)
    sr=source_receipt.read_bytes()
    if sha(sr)!=SOURCE_RECEIPT_SHA:raise ReplacementGateError("UNPINNED_CAST_FAMILY_EVIDENCE")
    original=json.loads(sr)
    if (original.get("schema")!="ZrotSourceBackedActionFamilyWclCastEvidenceV1"
        or original.get("original_numeric_lock_sha256")!=LOCK
        or original.get("combined_actor_casts")!=105):
        raise ReplacementGateError("WRONG_REPLAY_SOURCE_CONTRACT")
    result={}
    for role,path in (("discovery",discovery),("holdout",holdout)):
        gate,view,events,pages=read_cohort(_zip(path),role=role)
        if original[role]["source_report_code"]!=gate["report_code"]:
            raise ReplacementGateError("REPORT_IDENTITY_MISMATCH")
        obj=cohort(gate,view,events,tree,trait_token,buff_id)
        obj["raw_checkpoint_pages_verified"]=pages
        result[role]=obj
    return {"schema":"ZrotWclSpecTraitEffectiveActionGateV1",
       "scope_policy_id":POLICY,
       "status":"OBSERVED_REPLACEMENT_GATE_NOT_COOLDOWN_READY",
       "public_tree_sha256":METADATA_SHA,
       "source_cast_family_receipt_sha256":SOURCE_RECEIPT_SHA,
       "source_patch_equivalence_to_player":"UNKNOWN",
       "action_replacement_source_simc_semantics":"RECKLESS_ABANDON_AND_RECKLESSNESS",
       "source_spell_ids_for_replacement":{"Bloodbath":335096,"CrushingBlow":335097},
       "discovery":result["discovery"],"holdout":result["holdout"],
       "total_casts":sum(result[k]["casts_evaluated"] for k in result),
       "actual_competing_spell_cooldown_readiness":"UNKNOWN",
       "dummy_wrong_action_flags":0,"MAIN_promotion":False}


def selftest():
    tree={"nodes":{
       10:{"id":10,"name":"Reckless Abandon","entries":[{"id":101}]},
       11:{"id":11,"name":"Other","entries":[{"id":102}]}
    }}
    assert unique_trait(tree,"Reckless Abandon")== (10,{101})
    assert threeval_and(True,True) is True
    assert threeval_and(False,None) is False
    assert threeval_and(None,True) is None
    ev=[{"timestamp":0,"type":"combatantinfo","sourceID":7,"specID":72,
         "talentTree":[{"nodeID":10,"id":101,"rank":1}]},
        {"timestamp":100,"sourceID":7,"type":"cast","abilityGameID":335097}]
    talent=actor_trait_selected(ev,7,tree,"Reckless Abandon")
    assert talent["selected"] is True
    view={"decisions":[{"timestamp":100,"ability_id":335097,
                        "aura_pre":{"1719":{"active":True}}}]}
    gate={"actor_id":7,"observed_spec":"Fury"}
    out=cohort(gate,view,ev,tree,"Reckless Abandon",1719)
    assert out["cast_replacement_gate_counts"]["TRUE"]==1
    assert out["recorded_cast_details"][0]["base_action_family_availability_by_replacement_alone"]=="SOURCE_MODEL_PARENT_ACTION_REPLACED"
    assert out["recorded_cast_details"][0]["which_action_should_be_pressed"]=="UNKNOWN"
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":9,
            "actual_WCL_or_SimC_source_loaded":False,
            "priority_claims_validated":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tree-data",type=Path)
    p.add_argument("--source-family-receipt",type=Path)
    p.add_argument("--discovery-zip",type=Path)
    p.add_argument("--holdout-zip",type=Path)
    p.add_argument("--trait-name",default="Reckless Abandon")
    p.add_argument("--buff-id",type=int,default=1719)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    args=(a.tree_data,a.source_family_receipt,a.discovery_zip,a.holdout_zip)
    if all(x is None for x in args):obj=selftest()
    elif all(x is not None for x in args):
        obj=run(*args,a.trait_name,a.buff_id)
    else:p.error("all four evidence paths required or none")
    b=canonical(obj)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(b)
        print("WCL_TRAIT_REPLACEMENT_GATE_EVIDENCE_SHA256="+sha(b))
    else:print(b.decode(),end="")

if __name__=="__main__":main()
