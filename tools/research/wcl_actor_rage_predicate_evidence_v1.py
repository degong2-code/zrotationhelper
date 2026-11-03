#!/usr/bin/env python3
"""WCL strict PRE Rage predicate evidence for source-derived SimC IF conditions.

Compares two original, report-disjoint WCL snapshots (SHA / actor / cast
replay independently checked by read_cohort). Uses a separate specialization
adapter so WCL type / ability semantics are never hardcoded into the engine.

Empirical resource scaling and raw aura transitions yield *observations*
only. They do not establish target count, ability cost under talents, GCD,
charges, cooldown, competing-action readiness, or a dummy mistake.
Default invocation: safe synthetic self-test; no credentials or WCL API.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import groupby
import json
from pathlib import Path
import sys

from wcl_actor_resource_owner_strict_pre_v1 import reconstruct,resource_owner,parse_resources
from wcl_dual_cohort_state_observability_v1 import read_cohort
from wcl_simc_postlock_real_audit_v1 import _zip, _canonical as canonical, _sha as sha

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
ADAPTER="ZrotSpecPowerPredicateAdapterV1"

class PredicateEvidenceError(ValueError): pass


def validate_adapter(a:dict)->dict:
    if (a.get("schema")!=ADAPTER or a.get("scope_policy_id")!=POLICY
        or not isinstance(a.get("specialization"),dict)
        or type(a.get("specialization",{}).get("spec_id")) is not int
        or type(a.get("wcl_actor_power_type")) is not int
        or a.get("wcl_raw_units_per_game_resource")!=10
        or a.get("factor_authority")!="OBSERVATIONAL_ONLY_EXTERNAL_COMBAT_LOG_GUIDE_NOT_PATCH_PINNED_BLIZZARD_TRUTH"
        or a.get("allowed_conclusion")!="RAW_STRICT_PRE_OBSERVED_PREDICATES_ONLY"
        or a.get("actor_resource_name")!="rage"
        or not isinstance(a.get("action_buff_numeric_ids"),dict)
        or set(a["action_buff_numeric_ids"])!={"buff.recklessness.up","buff.enrage.up"}
        or not isinstance(a.get("forbidden_claims"),list)
        or len(a["forbidden_claims"])<7):
        raise PredicateEvidenceError("SEMANTIC_ADAPTER_UNTRUSTED")
    return a


def empirical_scale_evidence(events:list,actor:int,power_type:int,factor:int)->dict:
    """Require strict-earlier actor-owned raw snapshot to evaluate delta.

    RESOURCECHANGE gain can be integer-truncated relative to high precision
    underlying gains; floor(positive raw_delta / 10) is only an observed
    cross-field compatibility test, not a power-cost formula.
    """
    ordered=sorted(enumerate(events),key=lambda x:(x[1]["timestamp"],x[0]))
    prior=None
    types=Counter()
    evidence=[]
    unexplained=[]
    for time,batch in groupby(ordered,key=lambda x:x[1]["timestamp"]):
        batch=[v for _,v in batch]
        for event in batch:
            if (event.get("type")!="resourcechange" or
                event.get("sourceID")!=actor or
                resource_owner(event,actor)!="ACTOR_OWNED_SOURCE" or
                event.get("resourceChangeType")!=power_type):
                continue
            res=parse_resources(event)
            item=res.get(power_type)
            gain=event.get("resourceChange")
            if item is None or type(gain) not in (int,float) or gain<=0:
                unexplained.append({"timestamp":time,"reason":"INVALID_GAIN_OR_RESOURCE_FIELD"})
                continue
            if prior is None or prior["timestamp"]>=time:
                unexplained.append({"timestamp":time,"reason":"NO_STRICT_EARLIER_ACTOR_POWER_SNAPSHOT"})
                continue
            delta=item["raw_amount"]-prior["raw_amount"]
            if delta<=0:
                unexplained.append({"timestamp":time,"reason":"GAIN_BUT_NET_RAW_RESOURCE_NONINCREASE",
                                    "reported_gain":gain,"raw_net_delta":delta,
                                    "ability_numeric_id":event.get("abilityGameID")})
                continue
            works=(int(delta/factor)==gain)
            types[str(event.get("abilityGameID"))]+=1
            evidence.append({"timestamp":time,"ability_numeric_id":event.get("abilityGameID"),
                "observed_raw_increase":delta,"reported_resource_change":gain,
                "floor_delta_div_candidate_factor_matches":works,
                "source_pre_timestamp":prior["timestamp"]})
        # Do not import snapshots from the same timestamp into PRE comparison.
        for event in batch:
            if resource_owner(event,actor) not in ("ACTOR_OWNED_SOURCE","ACTOR_OWNED_TARGET"):
                continue
            item=parse_resources(event).get(power_type)
            if item:
                prior={"timestamp":time,"raw_amount":item["raw_amount"]}
    return {"candidate_raw_units_per_game_resource":factor,
        "eligible_positive_raw_gain_events":len(evidence),
        "crossfield_compatible_positive_gain_events":sum(x["floor_delta_div_candidate_factor_matches"] for x in evidence),
        "observed_gain_numeric_spell_ids":dict(sorted(types.items())),
        "noncalibratable_resourcechange_events":unexplained,
        "crossfield_test_uses_strict_earlier_actor_owned_snapshot":True,
        "hypothesis_was_prelocked_on_independent_holdout":False,
        "spell_cost_mechanic_proven":False}


def observed_aura(decision:dict,idnum:int):
    state=decision.get("aura_pre",{}).get(str(idnum))
    if isinstance(state,dict) and type(state.get("active")) is bool:
        return state["active"]
    return None


def combine_and(a,b):
    if a is False or b is False:return False
    if a is True and b is True:return True
    return None


def cohort(events:list,gate:dict,view:dict,adapter:dict)->dict:
    actor=gate["actor_id"]
    if gate.get("observed_spec")!=adapter["specialization"]["spec"] or gate.get("observed_class")!=adapter["specialization"]["class"]:
        raise PredicateEvidenceError("ACTOR_SPEC_CLASS_MISMATCH")
    state=reconstruct(events,actor,view["decisions"])
    factor=adapter["wcl_raw_units_per_game_resource"]
    ptype=str(adapter["wcl_actor_power_type"])
    calibrated=empirical_scale_evidence(events,actor,int(ptype),factor)
    observations=[]
    for rec,dec in zip(state["candidate_pre_snapshots"],view["decisions"]):
        if rec["timestamp"]!=dec["timestamp"] or rec["ability_id"]!=dec["ability_id"]:
            raise PredicateEvidenceError("STRICT_PRE_CAST_REPLAY_DIVERGENCE")
        resource=rec["resource_pre"].get(ptype)
        amount=resource["raw_amount"] if resource else None
        if amount is not None and (type(amount) not in (int,float) or amount<0):
            raise PredicateEvidenceError("BAD_RESOURCE_PRE")
        threshold=adapter["speculative_resource_coverage_threshold"]
        rage_ge_100=(amount>=factor*threshold) if amount is not None else None
        reck=observed_aura(dec,adapter["action_buff_numeric_ids"]["buff.recklessness.up"])
        enrage=observed_aura(dec,adapter["action_buff_numeric_ids"]["buff.enrage.up"])
        conjunct=combine_and(reck,rage_ge_100)
        observations.append({"timestamp":rec["timestamp"],
          "actual_numeric_spell_id":rec["ability_id"],
          "WCL_actor_owned_raw_rage":amount,
          "provisional_normalized_rage":(amount/factor if amount is not None else None),
          "resource_source_timestamp":resource["source_timestamp"] if resource else None,
          "observed_rage_ge_100":rage_ge_100,
          "observed_buff_recklessness_up":reck,
          "observed_buff_enrage_up":enrage,
          "observed_recklessness_and_rage_ge_100":conjunct,
          "condition_proof_level":"PROVISIONAL_OBSERVATION_ONLY",
          "actual_spell_available":"UNKNOWN",
          "higher_priority_actions_available":"UNKNOWN",
          "expected_action":"UNKNOWN","dummy_mistake_verdict":"UNKNOWN"})
    def totals(name):
        c=Counter(("UNKNOWN" if item[name] is None else str(item[name]).upper()) for item in observations)
        return {k:c.get(k,0) for k in ("TRUE","FALSE","UNKNOWN")}
    return {
      "report_code":gate["report_code"],
      "fight_id":gate["fight_id"],
      "actor_id":actor,
      "raw_event_count":len(events),
      "actor_cast_count":len(observations),
      "max_actor_raw_resource":max((x.get("WCL_actor_owned_raw_rage") or 0) for x in observations),
      "resource_scale_empirical":calibrated,
      "observed_rage_ge_100_counts":totals("observed_rage_ge_100"),
      "observed_recklessness_buff_counts":totals("observed_buff_recklessness_up"),
      "observed_enrage_buff_counts":totals("observed_buff_enrage_up"),
      "observed_recklessness_and_rage_ge_100_counts":totals("observed_recklessness_and_rage_ge_100"),
      "spell_cost_verified":False,
      "alternative_spell_readiness_verified":False,
      "conditional_model_training_allowed":False,
      "records":observations}


def run(adapter_path:Path,discovery_path:Path,holdout_path:Path):
    adapter_raw=adapter_path.read_bytes()
    adapter=validate_adapter(json.loads(adapter_raw))
    result={}
    for name,path in (("discovery",discovery_path),("holdout",holdout_path)):
        gate,view,events,pages=read_cohort(_zip(path),role=name)
        c=cohort(events,gate,view,adapter)
        c["verified_source_pages"]=pages
        result[name]=c
    if result["discovery"]["report_code"]==result["holdout"]["report_code"]:
        raise PredicateEvidenceError("NONDISJOINT_WCL_REPORT")
    return {"schema":"ZrotWclActorRageStrictPrePredicateEvidenceV1",
      "scope_policy_id":POLICY,
      "status":"EXPLORATORY_RAGE_SCALE_AND_AURA_OBSERVATION_NOT_READINESS",
      "specialization_adapter_sha256":sha(adapter_raw),
      "candidate_raw_resource_factor":adapter["wcl_raw_units_per_game_resource"],
      "power_type_raw_numeric_id":adapter["wcl_actor_power_type"],
      "power_type_external_semantics":adapter["actor_resource_name"],
      "factor_patch_authority":"NOT_MECHANIC_TRUTH_VERIFIED",
      "discovery":result["discovery"],"holdout":result["holdout"],
      "actual_SimC_APL_conditions_observable_in_part":True,
      "full_if_else_action_priority_eligible":False,
      "actual_active_enemy_count":"UNKNOWN",
      "spell_cost_modifiers_and_cooldowns":"UNKNOWN",
      "dummy_mistake_flags":0,
      "MAIN_promotion":False}


def selftest():
    adapter={"schema":ADAPTER,"scope_policy_id":POLICY,
      "specialization":{"class":"Warrior","spec":"Fury","spec_id":72},
      "wcl_actor_power_type":1,
      "wcl_raw_units_per_game_resource":10,
      "factor_authority":"OBSERVATIONAL_ONLY_EXTERNAL_COMBAT_LOG_GUIDE_NOT_PATCH_PINNED_BLIZZARD_TRUTH",
      "allowed_conclusion":"RAW_STRICT_PRE_OBSERVED_PREDICATES_ONLY",
      "actor_resource_name":"rage",
      "action_buff_numeric_ids":{"buff.recklessness.up":1719,"buff.enrage.up":184362},
      "forbidden_claims":["COST","GCD","COOLDOWN","TARGETS","ALTERNATIVE","PRIORITY","MISTAKE"],
      "speculative_resource_coverage_threshold":100}
    validate_adapter(adapter)
    events=[
      {"timestamp":1,"type":"cast","sourceID":7,"resourceActor":1,
       "classResources":[{"amount":200,"max":1300,"type":1}]},
      {"timestamp":2,"type":"resourcechange","sourceID":7,"resourceActor":1,
       "abilityGameID":1719,"resourceChange":50,"resourceChangeType":1,
       "classResources":[{"amount":700,"max":1300,"type":1}]},
      {"timestamp":3,"type":"resourcechange","sourceID":7,"resourceActor":1,
       "abilityGameID":50622,"resourceChange":7,"resourceChangeType":1,
       "classResources":[{"amount":775,"max":1300,"type":1}]},
      {"timestamp":4,"type":"damage","sourceID":7,"targetID":8,"resourceActor":2,
       "classResources":[{"amount":100,"max":100,"type":3}]}
    ]
    c=empirical_scale_evidence(events,7,1,10)
    assert c["eligible_positive_raw_gain_events"]==2
    assert c["crossfield_compatible_positive_gain_events"]==2
    assert c["hypothesis_was_prelocked_on_independent_holdout"] is False
    assert combine_and(True,True) is True
    assert combine_and(None,False) is False
    assert combine_and(None,True) is None
    assert observed_aura({"aura_pre":{"1719":{"active":True}}},1719) is True
    assert observed_aura({"aura_pre":{}},1719) is None
    assert c["spell_cost_mechanic_proven"] is False
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":10,
            "actual_WCL_API_calls":0,"manual_rotation_rule_proven":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--discovery-zip",type=Path)
    p.add_argument("--holdout-zip",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    inputs=(a.adapter,a.discovery_zip,a.holdout_zip)
    if all(x is None for x in inputs):out=selftest()
    elif all(x is not None for x in inputs):out=run(*inputs)
    else:p.error("provide all three inputs or none for safe synthetic test")
    b=canonical(out)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(b)
        print("WCL_RAGE_PREDICATE_EXPLORATORY_RECEIPT_SHA256="+sha(b))
    else:print(b.decode(),end="")

if __name__=="__main__":main()
