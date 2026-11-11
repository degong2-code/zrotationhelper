#!/usr/bin/env python3
"""Postlock numerical build comparison against a pinned SimC profile/DBC.
No assumption that allocated hero ranks are runtime enabled or tier IDs
activate set effects. A mismatched encoded tree is not an exact build match.
No flags: safe synthetic checks; no network.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
from general_rotation_original_talent_hash_dbc_v1 import decode,parse_dbc,gitblob,_profile_values
from wcl_raw_action_event_grain_audit_v1 import canon,sha,require
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SCHEMA="ZrotPostlockNumericBuildProfileCompareV1"
REV="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
DBC_BLOB="6eec16fcea3e9eb82948cf5810a599401606b3ee"
SLOTS={"head","neck","shoulders","back","chest","wrists","hands","waist","legs","feet","finger1","finger2","trinket1","trinket2","main_hand","off_hand","shirt","tabard"}

def compare(snapshot,decoded,profile_items):
    require(snapshot["observed_numeric_specID"]==decoded["spec_id"],"NUMERIC_SPEC_MISMATCH")
    w=Counter()
    for row in snapshot["observed_talent_entries"]:
        key=(row["nodeID"],row["entryID"])
        require(key not in w,"DUPLICATE_NUMERIC_TALENT_ENTRY")
        w[key]=row["rank"]
    d={(r["node"],r["entry"]):r for r in decoded["rows"]}
    p={(r["node"],r["entry"]):r["rank"] for r in decoded["selected"]}
    require(len(p)==len(decoded["selected"]) and len(d)==len(decoded["rows"]),"DUPLICATE_PINNED_TRAIT_ENTRY")
    # Zero-rank rows do not establish positive allocation. Unmatched raw
    # numeric entries may represent source-version mismatch, never invented.
    wp={k:v for k,v in w.items() if v>0}
    union=sorted(set(p)|set(wp))
    rows=[]
    for k in union:
        trait=d.get(k); sr=p.get(k,0); wr=wp.get(k,0)
        status=("UNKNOWN_WCL_ENTRY_NOT_IN_PINNED_DBC" if trait is None else
                "SAME_POSITIVE_ENCODED_RANK" if sr==wr else
                "DIFFERENT_POSITIVE_ENCODED_RANK")
        rows.append({"node_id":k[0],"entry_id":k[1],"source_rank":sr,"WCL_rank":wr,
                     "pinned_tree":None if trait is None else trait["tree"],
                     "pinned_spell_id":None if trait is None else trait["spell"],
                     "status":status,"runtime_enabled":"UNKNOWN"})
    counts=Counter(x["status"] for x in rows)
    g=Counter(x for x in snapshot["observed_gear_item_ids"] if x>0)
    sg=Counter(profile_items)
    return {"numeric_spec_id":decoded["spec_id"],"encoded_source_positive_entries":len(p),
            "WCL_positive_entries":len(wp),"WCL_zero_rank_entries":sum(v==0 for v in w.values()),
            "comparison_status_counts":dict(sorted(counts.items())),
            "encoded_positive_rank_vectors_equal":p==wp,
            "same_pinned_positive_rank_entries":counts["SAME_POSITIVE_ENCODED_RANK"],
            "differences":[x for x in rows if x["status"]!="SAME_POSITIVE_ENCODED_RANK"],
            "all_numeric_entry_comparisons":rows,
            "source_profile_item_count":sum(sg.values()),"WCL_item_count":sum(g.values()),
            "same_item_id_multiset_count":sum((g&sg).values()),"item_ID_multisets_equal":g==sg,
            "observed_WCL_set_item_counts":snapshot["observed_gear_setID_item_counts"],
            "runtime_hero_subtree_and_talent_enabled":"UNKNOWN",
            "full_build_equivalence":"UNKNOWN" if p==wp and g==sg else "NOT_IDENTICAL_OBSERVED_RANK_OR_ITEM_VECTOR",
            "item_level_enchant_effect_and_tier_activation":"UNKNOWN","current_patch_mechanic_parity":"UNKNOWN"}

def produce(root,adapter,certs,lock_bytes,contract_bytes,metrics_bytes):
    from wcl_disjoint_holdout_v1 import validate_contract,validate_frozen_lock
    c=validate_contract(json.loads(contract_bytes));lock=validate_frozen_lock(lock_bytes,c)
    metrics=json.loads(metrics_bytes)
    require(metrics["unchanged_discovery_lock_sha256"]==sha(lock_bytes) and
            metrics["predeclared_contract_sha256"]==sha(contract_bytes) and
            metrics["different_report_from_discovery"] is True,"POSTLOCK_METRIC_IDENTITY")
    require(subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],capture_output=True,text=True,check=True).stdout.strip()==REV,
            "PINNED_SIMC_REVISION_MISMATCH")
    p=(root/adapter["source_profile_path"]).read_bytes()
    dbc=(root/adapter["source_trait_data_path"]).read_bytes()
    require(adapter["source_revision"]==REV and gitblob(p)==adapter["profile_git_blob"] and gitblob(dbc)==DBC_BLOB,"SOURCE_PROFILE_OR_DBC_BLOB_MISMATCH")
    decoded=decode(_profile_values(p)["talents"][0],parse_dbc(dbc.decode()),adapter["class_id"],adapter["spec_id"])
    gear=[]
    for line in p.decode().splitlines():
        key,sep,tail=line.partition("=")
        if sep and key in SLOTS:
            match=re.search(r"(?:^|,)id=(\d+)(?:,|$)",tail)
            if match:gear.append(int(match[1]))
    require(len(gear)>0,"PROFILE_GEAR_IDS_MISSING")
    out=[]
    for role,cert in zip(("DISCOVERY","HOLDOUT"),certs,strict=True):
        require(cert["schema"]=="ZrotWclActorCombatantinfoPreEvidenceV1" and cert["combatantinfo_pre_status"]=="OBSERVED_STRICT_PRE" and
                cert["actor_numeric_build_snapshot"]["strictly_before_first_actor_action"] is True,"NO_STRICT_PRE_BUILD_CERTIFICATE")
        ident=c["frozen_discovery"] if role=="DISCOVERY" else {"report_code":metrics["holdout_source_report"],"fight_id":metrics["holdout_source_fight"],"actor_id":metrics["holdout_actor_id"]}
        require(cert["actor_fight_fingerprint_sha256"]==sha(canon([ident["report_code"],ident["fight_id"],ident["actor_id"]])),"BUILD_CERTIFICATE_COHORT_MISMATCH")
        out.append({"role":role,"build_certificate_sha256":sha(canon(cert)),**compare(cert["actor_numeric_build_snapshot"],decoded,gear)})
    return {"schema":SCHEMA,"policy_id":POLICY,"source_revision":REV,"profile_git_blob":adapter["profile_git_blob"],"trait_dbc_git_blob":DBC_BLOB,
            "original_numeric_lock_sha256":sha(lock_bytes),"original_holdout_metrics_sha256":sha(metrics_bytes),
            "postlock_only":True,"cases":out,"new_priority_rules_promoted":0,"manual_player_input":"UNKNOWN","MAIN_promoted":False}

def selftest():
    decoded={"spec_id":1,"rows":[{"node":2,"entry":3,"tree":1,"spell":4}],"selected":[{"node":2,"entry":3,"rank":1}]}
    snapshot={"observed_numeric_specID":1,"observed_talent_entries":[{"nodeID":2,"entryID":3,"rank":1}],"observed_gear_item_ids":[9],"observed_gear_setID_item_counts":{}}
    a=compare(snapshot,decoded,[9])
    require(a["encoded_positive_rank_vectors_equal"] and a["full_build_equivalence"]=="UNKNOWN","MATCH_OVERPROMOTION")
    snapshot["observed_talent_entries"][0]["rank"]=2
    require(compare(snapshot,decoded,[9])["full_build_equivalence"]=="NOT_IDENTICAL_OBSERVED_RANK_OR_ITEM_VECTOR","RANK_DIFFERENCE_LOST")
    return {"status":"PASS_SYNTHETIC_STATIC","checks":2}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("source-root","adapter","discovery-cert","holdout-cert","lock","contract","metrics","out"):p.add_argument("--"+k,type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):print(json.dumps(selftest(),sort_keys=True));return
    require(all(vars(a).values()),"ALL_PINNED_POSTLOCK_INPUTS_REQUIRED")
    out=produce(a.source_root,json.loads(a.adapter.read_bytes()),[json.loads(x.read_bytes()) for x in (a.discovery_cert,a.holdout_cert)],a.lock.read_bytes(),a.contract.read_bytes(),a.metrics.read_bytes())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canon(out))
    print("POSTLOCK_BUILD_COMPARE_SHA256="+sha(a.out.read_bytes()))
    print("POSTLOCK_BUILD_COMPARE_SUMMARY",json.dumps([{k:v for k,v in x.items() if k not in ("differences","all_numeric_entry_comparisons")} for x in out["cases"]],sort_keys=True))
if __name__=="__main__":main()
