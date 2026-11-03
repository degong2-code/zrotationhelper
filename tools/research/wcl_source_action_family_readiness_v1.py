#!/usr/bin/env python3
"""SimC-backed action family, cast evidence and cooldown observability engine.

Generic engine; specific spell IDs and effect relationships are supplied by
a separately pinned specialization adapter. Original WCL raw evidence is
independently replayed and original blind numeric candidate set preserved.

Observing a cast at timestamp t proves that WCL recorded the action at t.
It does NOT establish which alternative was ready strictly BEFORE t, even
when the same action was just cast. Intercast gaps are observations, not
cooldown duration estimates. Manual/auto and proc evidence stay qualified.
No-argument invocation runs safe offline synthetic regression.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from itertools import groupby
import hashlib,json
from pathlib import Path
from wcl_dual_cohort_state_observability_v1 import read_cohort
from wcl_simc_postlock_real_audit_v1 import _zip,_canonical as canonical,_sha as sha

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SOURCE_BLOB="38ee3dd0d5943eb9227ec55aefb21e7d47244f96"
BLIND_LOCK="c5e2bedeb7f4f0152e8ba86a30b1b13ecc5aa1374af4c0b01237a16151a1c98e"

class FamilyError(ValueError):pass

def git_blob_sha(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def source_checks(simc_bytes, adapter):
    if git_blob_sha(simc_bytes)!=SOURCE_BLOB:
        raise FamilyError("PINNED_SIMC_MECHANICS_BLOB_CHANGED")
    text=simc_bytes.decode("utf-8")
    checks={
      "explicit_bloodbath_id":'spec.bloodbath                = find_spell(335096);',
      "explicit_crushing_blow_id":'spec.crushing_blow            = find_spell(335097);',
      "bloodbath_uses_bloodthirst_cooldown":'cooldown = p->cooldown.bloodthirst;',
      "crushing_blow_uses_raging_blow_cooldown":'cooldown = p -> cooldown.raging_blow;',
      "crushing_blow_reckless_abandon_talent_gate":'if ( !p()->talents.fury.reckless_abandon->ok() )',
      "bloodbath_recklessness_gate":'if ( !p()->buff.recklessness->check() )',
      "raging_blow_proc_cooldown_reset":'cooldown->reset( true );',
      "raging_blow_hasted":'cooldown->hasted = true;',
      "rampage_cost_affected_by_recklessness_and_talent":
        'if ( p()->talents.fury.rampaging_berserker_2->ok() && p()->buff.recklessness->check() )'
    }
    missed=[name for name,value in checks.items() if value not in text]
    if missed:raise FamilyError("PINNED_SIMC_MECHANIC_SNIPPET_MISSING:"+",".join(missed))
    return {"source_git_blob_verified":True,"checks":checks,
            "base_cooldown_values_extracted":False,
            "actual_player_talent_and_proc_states_in_source":False}


def validate_adapter(blob):
    adapter=json.loads(blob)
    if (adapter.get("schema")!="ZrotSpecActionFamilyMechanicsAdapterV1"
        or adapter.get("scope_policy_id")!=POLICY
        or adapter.get("source_simc",{}).get("git_blob_sha1")!=SOURCE_BLOB
        or adapter.get("protected_blind_lock_sha256")!=BLIND_LOCK
        or adapter.get("allow_infer_exact_cd_from_gap") is not False
        or adapter.get("allow_infer_availability_of_alternative") is not False
        or adapter.get("allow_infer_priority_or_player_error") is not False
        or not isinstance(adapter.get("candidates"),list)
        or len(adapter["candidates"])!=4):
        raise FamilyError("UNTRUSTED_ACTION_FAMILY_CONTRACT")
    mapping={}
    for row in adapter["candidates"]:
        ident=row.get("spell_id")
        if type(ident) is not int or ident in mapping or ident<1:
            raise FamilyError("INVALID_CANDIDATE_NUMERIC_ID")
        if (row.get("readiness")!="UNKNOWN"
            or not isinstance(row.get("family"),str)
            or row.get("manuality") not in ("DIRECT_SPELL_CANDIDATE","UNVERIFIED_AUTO_HYPOTHESIS")):
            raise FamilyError("UNVERIFIED_ACTION_AUTHORITY_ESCALATION")
        if "replaces" in row and (row.get("activated_when")!=
            ["talent.reckless_abandon","buff.recklessness.up"]):
            raise FamilyError("REPLACEMENT_GATE_UNPINNED")
        mapping[ident]=row
    if set(mapping)!={1,184367,335096,335097}:
        raise FamilyError("FROZEN_CANDIDATE_MAPPING_CHANGED")
    return adapter,mapping


def replay_one(gate,view,events,mapping):
    actor=gate["actor_id"]
    casts=[e for e in sorted(enumerate(events),key=lambda v:(v[1]["timestamp"],v[0]))
           if e[1].get("sourceID")==actor and e[1].get("type") in ("cast","begincast")]
    if len(casts)!=len(view["decisions"]):
        raise FamilyError("STRICT_PRE_CAST_COUNT_DIVERGENCE")
    prior_family={}
    records=[]
    direct=Counter()
    gaps=defaultdict(list)
    for index,((raw_index,ev),old) in enumerate(zip(casts,view["decisions"])):
        ts=ev["timestamp"]
        sid=ev.get("abilityGameID")
        if ts!=old["timestamp"] or sid!=old["ability_id"]:
            raise FamilyError("STRICT_PRE_CAST_IDENTITY_DIVERGED")
        rec=mapping.get(sid)
        family=rec["family"] if rec else "UNMAPPED_CAST_ID"
        if rec:direct[sid]+=1
        prev=prior_family.get(family)
        gap=ts-prev if prev is not None else None
        if gap is not None:
            if gap<0:raise FamilyError("FUTURE_CAST_LEAK")
            gaps[family].append(gap)
        # WCL isFake/isMelee flags may be unavailable in raw GraphQL. Do not
        # infer manual buttons from missing or false flags.
        is_fake=ev.get("isFake")
        is_melee=ev.get("isMelee")
        if is_melee is True or is_fake is True:
            actionability="OBSERVED_CAST_FLAGGED_NOT_ORDINARY_MANUAL"
        elif rec and rec["manuality"]=="DIRECT_SPELL_CANDIDATE":
            actionability="DIRECT_SPELL_ID_CAST_MANUAL_INPUT_UNPROVEN"
        else:actionability="MANUAL_ACTIONABILITY_UNKNOWN"
        # A cast at t is an action observation at t, NOT strict-pre evidence
        # of spell availability or alternative availability.
        records.append({
          "decision_index":index,"timestamp":ts,"actual_spell_id":sid,
          "action_family":family,"source_canonical_action":rec["canonical_action"] if rec else None,
          "source_replacement_parent":rec.get("replaces") if rec else None,
          "original_blind_candidate":rec is not None,
          "event_type":ev["type"],"raw_is_melee":is_melee,
          "raw_is_fake":is_fake,
          "actionability":actionability,
          "replacement_activation":"UNKNOWN_TALENT_AND_ABILITY_STATE" if rec and "replaces" in rec else "NOT_A_REPLACEMENT_OR_UNMAPPED",
          "observed_this_cast_at_t":True,
          "previous_same_family_cast_timestamp":prev,
          "elapsed_since_previous_same_family_cast_ms":gap,
          "exact_cooldown_from_interval":"NOT_INFERRED",
          "charge_count_before_action":"UNKNOWN",
          "cooldown_remaining_before_action":"UNKNOWN",
          "reset_proc_before_action":"UNKNOWN",
          "other_families_ready_before_action":"UNKNOWN",
          "action_ready_strict_pre":"UNKNOWN",
          "manual_input_proven":False,
          "rotation_priority_proven":False,
          "dummy_mistake_verdict":"UNKNOWN"})
        # State update after collecting current record; same-timestamp
        # intervals remain zero observation, not verified readiness.
        prior_family[family]=ts
    out={
      "actor_cast_count":len(records),
      "source_report_code":gate["report_code"],
      "source_fight_id":gate["fight_id"],
      "numeric_blind_candidate_casts":{str(k):direct[k] for k in sorted(mapping)},
      "recognized_candidate_cast_total":sum(direct.values()),
      "other_cast_total":len(records)-sum(direct.values()),
      "action_family_cast_totals":dict(sorted(Counter(r["action_family"] for r in records).items())),
      "observed_intercast_gaps_ms_only":{
         key:{"pairs":len(v),"min_elapsed":min(v),"max_elapsed":max(v)}
         for key,v in sorted(gaps.items())},
      "mechanic_cooldowns_or_charges_proven":False,
      "manual_keypress_proven":False,
      "competing_action_readiness_proven":False,
      "wrong_priority_flags":0,
      "cast_records":records}
    return out


def run(adapter_path,source_path,discovery,holdout):
    adapter_raw=adapter_path.read_bytes()
    adapter,mapping=validate_adapter(adapter_raw)
    source=source_checks(source_path.read_bytes(),adapter)
    cohorts={}
    for name,path in (("discovery",discovery),("holdout",holdout)):
        gate,view,events,pages=read_cohort(_zip(path),role=name)
        data=replay_one(gate,view,events,mapping)
        data["validated_raw_pages"]=pages
        data["validated_raw_event_count"]=len(events)
        cohorts[name]=data
    if cohorts["discovery"]["source_report_code"]==cohorts["holdout"]["source_report_code"]:
        raise FamilyError("REPORTS_NOT_DISJOINT")
    return {"schema":"ZrotSourceBackedActionFamilyWclCastEvidenceV1",
      "scope_policy_id":POLICY,
      "status":"SOURCE_IDENTIFIED_ACTION_FAMILIES_CAST_PROOFS_ONLY",
      "source_simc_mechanics_git_blob_sha1":SOURCE_BLOB,
      "source_simc_checklist":source,
      "adapter_git_blob_sha1":git_blob_sha(adapter_raw),
      "original_numeric_lock_sha256":BLIND_LOCK,
      "numeric_candidate_set_untouched":True,
      "discovery":cohorts["discovery"],"holdout":cohorts["holdout"],
      "combined_actor_casts":sum(c["actor_cast_count"] for c in cohorts.values()),
      "cooldown_or_charge_state_at_uncast_alternatives":"UNKNOWN",
      "effective_action_replacement_eligibility":"UNKNOWN",
      "autoattack_manual_cast":"UNVERIFIED",
      "priority_claims_proven":0,
      "dummy_errors_confirmed":0,
      "MAIN_promotion":False}


def selftest():
    sample={"schema":"ZrotSpecActionFamilyMechanicsAdapterV1","scope_policy_id":POLICY,
      "source_simc":{"git_blob_sha1":SOURCE_BLOB},
      "protected_blind_lock_sha256":BLIND_LOCK,
      "allow_infer_exact_cd_from_gap":False,
      "allow_infer_availability_of_alternative":False,
      "allow_infer_priority_or_player_error":False,
      "candidates":[
        {"spell_id":1,"family":"AUTO_ATTACK_UNSCORABLE","canonical_action":"auto_attack","readiness":"UNKNOWN","manuality":"UNVERIFIED_AUTO_HYPOTHESIS"},
        {"spell_id":184367,"family":"RAMPAGE","canonical_action":"rampage","readiness":"UNKNOWN","manuality":"DIRECT_SPELL_CANDIDATE"},
        {"spell_id":335096,"family":"BLOODTHIRST_FAMILY","canonical_action":"bloodbath","readiness":"UNKNOWN","manuality":"DIRECT_SPELL_CANDIDATE","replaces":"bloodthirst","activated_when":["talent.reckless_abandon","buff.recklessness.up"]},
        {"spell_id":335097,"family":"RAGING_BLOW_FAMILY","canonical_action":"crushing_blow","readiness":"UNKNOWN","manuality":"DIRECT_SPELL_CANDIDATE","replaces":"raging_blow","activated_when":["talent.reckless_abandon","buff.recklessness.up"]}
      ]}
    a,mapping=validate_adapter(json.dumps(sample))
    fake_gate={"actor_id":7,"report_code":"test","fight_id":1}
    ev=[
      {"timestamp":100,"type":"cast","sourceID":7,"abilityGameID":335097},
      {"timestamp":100,"type":"cast","sourceID":7,"abilityGameID":1,"isMelee":True},
      {"timestamp":110,"type":"cast","sourceID":7,"abilityGameID":335097},
      {"timestamp":120,"type":"cast","sourceID":7,"abilityGameID":184367}]
    view={"decisions":[{"timestamp":x["timestamp"],"ability_id":x["abilityGameID"]} for x in ev]}
    out=replay_one(fake_gate,view,ev,mapping)
    assert out["actor_cast_count"]==4
    assert out["numeric_blind_candidate_casts"]=={"1":1,"184367":1,"335096":0,"335097":2}
    assert out["observed_intercast_gaps_ms_only"]["RAGING_BLOW_FAMILY"]["min_elapsed"]==10
    assert out["cast_records"][1]["actionability"]=="OBSERVED_CAST_FLAGGED_NOT_ORDINARY_MANUAL"
    assert out["cast_records"][2]["action_ready_strict_pre"]=="UNKNOWN"
    assert out["wrong_priority_flags"]==0
    assert out["cast_records"][0]["replacement_activation"]=="UNKNOWN_TALENT_AND_ABILITY_STATE"
    try:validate_adapter(json.dumps({**sample,"allow_infer_exact_cd_from_gap":True}))
    except FamilyError:pass
    else:raise AssertionError("ACCEPTED_UNVERIFIED_CD_DURATION")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":8,"actual_WCL_or_SimC_loaded":False,
            "priority_claims_proven":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--simc-source",type=Path)
    p.add_argument("--discovery-zip",type=Path)
    p.add_argument("--holdout-zip",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    all_inputs=(a.adapter,a.simc_source,a.discovery_zip,a.holdout_zip)
    if all(x is None for x in all_inputs):obj=selftest()
    elif all(x is not None for x in all_inputs):obj=run(*all_inputs)
    else:p.error("all four source inputs required or none for safe synthetic test")
    blob=canonical(obj)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("WCL_SIMC_ACTION_FAMILY_CAST_RECEIPT_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
