#!/usr/bin/env python3
"""Independent WCL aura transition provenance -> source SimC IF guard.

Only latest target-actor aura transition timestamp STRICTLY EARLIER than
action time can contribute. Multiple conflicting same-timestamp transitions,
missing initial aura, or disagreement with the original raw replay are UNKNOWN.
No assumption that a recorded application remains active without a known
remove; positive values mean event-sourced state, not verified spell duration.

Generic interpreter imports the source SimC APL AST. The specialization
adapter maps source numeric buff and power IDs. Rage /10 is observational.
Neither an observed guard nor its absence proves a spell READY, a missed
priority, or a target dummy mistake. Safe no-arg run is fully offline.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
from itertools import groupby
import hashlib
import json
from pathlib import Path

from wcl_dual_cohort_state_observability_v1 import read_cohort
from wcl_simc_postlock_real_audit_v1 import _zip,_canonical as canonical,_sha as sha
from wcl_actor_resource_owner_strict_pre_v1 import reconstruct
from wcl_actor_rage_predicate_evidence_v1 import validate_adapter
from simc_ordered_if_else_general_rotation_ir_v1 import eval_ast

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SCHEMA="ZrotAuraProvenanceSimcPredicateFixtureV1"

class AuraPreError(ValueError):pass

TYPES={"applybuff":True,"refreshbuff":True,"applybuffstack":True,
       "removebuff":False,"removebuffstack":None}


def _transition(event):
    kind=event.get("type")
    if kind not in TYPES:return None
    if kind=="removebuffstack":
        number=event.get("stack",event.get("stacks"))
        active=(number>0) if type(number) is int and number>=0 else None
    else:active=TYPES[kind]
    return active


def replay_aura(events,actor,spell_ids,casts):
    """Use a fresh transition reducer, not the persisted original aura map."""
    ids=set(spell_ids)
    if (type(actor) is not int or actor<=0 or len(ids)!=len(spell_ids)
            or any(type(x) is not int or x<=0 for x in ids)):
        raise AuraPreError("BAD_AURA_REPLAY_INPUT")
    sorted_events=sorted(enumerate(events),key=lambda p:(p[1]["timestamp"],p[0]))
    state={}
    replay=[]
    counts=Counter()
    index=0
    for ts,iterator in groupby(sorted_events,key=lambda p:p[1]["timestamp"]):
        batch=[event for _,event in iterator]
        for event in batch:
            if event.get("sourceID")!=actor or event.get("type") not in ("cast","begincast"):
                continue
            if index>=len(casts):
                raise AuraPreError("EXTRA_SOURCE_CAST")
            expected=casts[index]
            if expected["timestamp"]!=ts or expected["ability_id"]!=event.get("abilityGameID"):
                raise AuraPreError("SOURCE_CAST_ORDER_MISMATCH")
            this={}
            for sid in sorted(ids):
                prior=state.get(sid)
                old=expected.get("aura_pre",{}).get(str(sid))
                previous=old.get("active") if isinstance(old,dict) else None
                computed=prior["active"] if prior is not None else None
                matched=(previous==computed) if previous is not None or computed is not None else True
                # Divergence must DOWNGRADE to unknown, not fix up original view.
                authoritative=computed if matched else None
                provenance=("NO_PRIOR_TRANSITION" if prior is None
                    else "PRE_REPLAY_MISMATCH_QUARANTINED" if not matched
                    else "AMBIGUOUS_TRANSITION" if computed is None
                    else "MATCHING_TARGET_AURA_TRANSITION")
                if prior is not None and prior["timestamp"]>=ts:
                    raise AuraPreError("SAME_TIMESTAMP_AURA_LEAK")
                if not matched:counts["mismatched_spell_casts"]+=1
                if authoritative is None:counts["unknown_spell_casts"]+=1
                this[str(sid)]={
                  "active":authoritative,
                  "independent_raw_state":computed,
                  "original_blind_replay_state":previous,
                  "original_replay_matches":matched,
                  "proof_status":provenance,
                  "source_timestamp":prior["timestamp"] if prior else None,
                  "last_transition_type":prior["event_type"] if prior else None,
                  "events_at_last_transition":prior["batch_count"] if prior else 0,
                  "spell_duration_or_expiry_verified":False
                }
            replay.append({"timestamp":ts,"ability_id":expected["ability_id"],
                           "spells":this})
            index+=1
        pending=defaultdict(list)
        for event in batch:
            if event.get("targetID")!=actor or event.get("type") not in TYPES:
                continue
            sid=event.get("abilityGameID")
            if type(sid) is not int or sid not in ids:continue
            pending[sid].append((_transition(event),event.get("type")))
            counts["tracked_aura_transition_events"]+=1
        for sid,rows in pending.items():
            vals={v for v,_ in rows}
            if len(vals)!=1 or None in vals:
                active=None
                counts["ambiguous_aura_timestamp_groups"]+=1
            else:
                active=next(iter(vals))
            state[sid]={"active":active,"timestamp":ts,"event_type":rows[-1][1],
                        "batch_count":len(rows)}
    if len(replay)!=len(casts):
        raise AuraPreError("MISSING_SOURCE_CAST")
    return replay,dict(sorted(counts.items()))


def validate_fixture(path,adapter,ir_bytes):
    obj=json.loads(path.read_bytes())
    if (obj.get("schema")!=SCHEMA or obj.get("scope_policy_id")!=POLICY
        or obj.get("source_simc_ir_receipt_sha256")!=sha(ir_bytes)
        or obj.get("source_adapter_sha256")!=sha(canonical(adapter))
        or not isinstance(obj.get("apl_row"),dict)
        or obj["apl_row"].get("list")!="slayer"
        or obj["apl_row"].get("index")!=2):
        raise AuraPreError("UNPINNED_SOURCE_APL_OR_ADAPTER")
    return obj


def check_condition(ir,fixture):
    if ir.get("schema")!="ZrotSimcSlayerConditionalPriorityResearchIRV1" or ir.get("scope_policy_id")!=POLICY:
        raise AuraPreError("SOURCE_IR_SCHEMA")
    pos=fixture["apl_row"]["index"]
    row=ir["source_list_rows"][fixture["apl_row"]["list"]][pos]
    if (row.get("if_source")!="buff.recklessness.up&rage>=100"
        or row.get("action")!="rampage"
        or sorted(row["symbolic_dependencies"])!=["buff.recklessness.up","rage"]):
        raise AuraPreError("SOURCE_APL_ROW_DRIFT")
    return row


def evaluate_sample(events,gate,view,adapter,row):
    actor=gate["actor_id"]
    ordered=view["decisions"]
    numeric={k:val for k,val in adapter["action_buff_numeric_ids"].items()}
    raw_aura,diagnostics=replay_aura(events,actor,list(numeric.values()),ordered)
    resources=reconstruct(events,actor,ordered)["candidate_pre_snapshots"]
    cast_results=[]
    for actual,auras,pre in zip(ordered,raw_aura,resources):
        t=actual["timestamp"]
        if t!=pre["timestamp"] or t!=auras["timestamp"]:
            raise AuraPreError("CAST_PRE_ALIGNMENT_DIVERGED")
        facts={}
        captured={}
        for name,sid in numeric.items():
            record=auras["spells"][str(sid)]
            captured[name]=record
            if type(record["active"]) is bool:
                if type(record["source_timestamp"]) not in (int,float) or record["source_timestamp"]>=t:
                    raise AuraPreError("INVALID_AURA_PRE_PROVENANCE")
                facts[name]={"value":record["active"],"timestamp":record["source_timestamp"],
                             "provenance":"STRICT_PRE_OBSERVATION"}
        power=pre["resource_pre"].get(str(adapter["wcl_actor_power_type"]))
        normalized=None
        if power:
            ts=power["source_timestamp"]
            if type(ts) not in (int,float) or ts>=t:
                raise AuraPreError("RESOURCE_PRE_TIMESTAMP_LEAK")
            normalized=power["raw_amount"]/adapter["wcl_raw_units_per_game_resource"]
            facts["rage"]={"value":normalized,"timestamp":ts,
                           "provenance":"STRICT_PRE_OBSERVATION"}
        result=eval_ast(row["if_ast"],facts,t)
        if type(result) not in (bool,type(None)):
            raise AuraPreError("APL_GUARD_NOT_TRI_BOOLEAN")
        cast_results.append({"timestamp":t,"actual_numeric_spell_id":actual["ability_id"],
            "source_apl_priority_index":row["index"],
            "source_apl_action":row["action"],
            "source_apl_if":row["if_source"],
            "guard_value":result,
            "rage_normalized_provisionally":normalized,
            "rage_scale_qualifier":"CROSSFIELD_EMPIRICAL_NOT_PATCH_VERIFIED",
            "aura_pre_provenance":captured,
            "full_buff_remains_verified":False,
            "active_target_count":"UNKNOWN",
            "competing_action_readiness":"UNKNOWN",
            "expected_spell":"UNKNOWN",
            "dummy_mistake_verdict":"UNKNOWN"})
    values=Counter("UNKNOWN" if e["guard_value"] is None else str(e["guard_value"]).upper()
                   for e in cast_results)
    return {"actor_casts":len(cast_results),
            "aura_reconstruction":diagnostics,
            "source_apl_guard_counts":{k:values[k] for k in ("TRUE","FALSE","UNKNOWN")},
            "source_apl_guard_extracted_and_executed":True,
            "actual_action_priority_verified":False,
            "cast_records":cast_results}


def execute(fixture_path,adapter_path,source_ir_path,discovery,holdout):
    adapter_raw=adapter_path.read_bytes()
    adapter=validate_adapter(json.loads(adapter_raw))
    ir_bytes=source_ir_path.read_bytes()
    fixture=validate_fixture(fixture_path,adapter,ir_bytes)
    ir=json.loads(ir_bytes)
    selected_row=check_condition(ir,fixture)
    result={}
    for name,path in (("discovery",discovery),("holdout",holdout)):
        gate,view,events,pages=read_cohort(_zip(path),role=name)
        sample=evaluate_sample(events,gate,view,adapter,selected_row)
        sample["report_code"]=gate["report_code"]
        sample["verified_raw_pages"]=pages
        result[name]=sample
    if result["discovery"]["report_code"]==result["holdout"]["report_code"]:
        raise AuraPreError("NOT_REPORT_DISJOINT")
    return {"schema":"ZrotWclAuraStrictPreSimcGuardAuditV1",
       "scope_policy_id":POLICY,
       "status":"ACTUAL_SOURCE_APL_GUARD_OBSERVATIONS_WITH_AURA_PROVENANCE",
       "fixture_sha256":sha(fixture_path.read_bytes()),
       "adapter_sha256":sha(adapter_raw),
       "source_ir_sha256":sha(ir_bytes),
       "source_apl_row_sha256":selected_row["source_sha256"],
       "discovery":result["discovery"],"holdout":result["holdout"],
       "cast_rows_total":sum(result[k]["actor_casts"] for k in ("discovery","holdout")),
       "same_timestamp_state_leakage":False,
       "source_buff_duration_truth":"UNVERIFIED",
       "resource_scaling_patch_truth":"UNVERIFIED",
       "action_ready_and_priority_truth":"UNKNOWN",
       "trainer_error_flags":0,
       "MAIN_promotion":False}


def selftest():
    spell=1719
    events=[
      {"timestamp":100,"type":"applybuff","targetID":7,"abilityGameID":spell},
      {"timestamp":110,"type":"cast","sourceID":7,"abilityGameID":200},
      {"timestamp":110,"type":"removebuff","targetID":7,"abilityGameID":spell},
      {"timestamp":115,"type":"cast","sourceID":7,"abilityGameID":201},
      {"timestamp":120,"type":"applybuff","targetID":7,"abilityGameID":spell},
      {"timestamp":120,"type":"removebuff","targetID":7,"abilityGameID":spell},
      {"timestamp":125,"type":"cast","sourceID":7,"abilityGameID":202},
    ]
    views=[
      {"timestamp":110,"ability_id":200,"aura_pre":{"1719":{"active":True}}},
      {"timestamp":115,"ability_id":201,"aura_pre":{"1719":{"active":False}}},
      {"timestamp":125,"ability_id":202,"aura_pre":{"1719":{"active":False}}}]
    rows,diag=replay_aura(events,7,[spell],views)
    assert rows[0]["spells"]["1719"]["active"] is True
    assert rows[1]["spells"]["1719"]["active"] is False
    assert rows[2]["spells"]["1719"]["active"] is None
    assert rows[0]["spells"]["1719"]["source_timestamp"]==100
    assert diag["ambiguous_aura_timestamp_groups"]==1
    assert diag["mismatched_spell_casts"]==1
    assert rows[1]["spells"]["1719"]["source_timestamp"]==110
    assert rows[0]["spells"]["1719"]["spell_duration_or_expiry_verified"] is False
    assert rows[0]["spells"]["1719"]["proof_status"]=="MATCHING_TARGET_AURA_TRANSITION"
    return {"status":"PASS_OFFLINE_SYNTHETIC",
       "checks":9,"live_API_calls":0,"priority_rules_validated":0,
       "wrong_cast_flags":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixture",type=Path)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--source-ir",type=Path)
    p.add_argument("--discovery-zip",type=Path)
    p.add_argument("--holdout-zip",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    paths=(a.fixture,a.adapter,a.source_ir,a.discovery_zip,a.holdout_zip)
    if all(path is None for path in paths):result=selftest()
    elif all(path is not None for path in paths):result=execute(*paths)
    else:p.error("all five evidence inputs required, otherwise safe offline selftest")
    raw=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
        print("WCL_SIMC_AURA_PRE_GUARD_RECEIPT_SHA256="+sha(raw))
    else:print(raw.decode(),end="")

if __name__=="__main__":main()
