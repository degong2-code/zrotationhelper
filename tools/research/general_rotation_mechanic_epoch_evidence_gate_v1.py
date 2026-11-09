#!/usr/bin/env python3
"""Generic post-lock General Rotation mechanic provenance/epoch gate.

Real WCL source IF scenario results are hypotheses. A Blizzard patch note
can attest a *described mechanic change*, but not current WCL spell IDs,
the actor's build, original SimC implementation, PRE readiness or priority.
Use an external versioned registry to separate those distinct claims and
rank the source-IF missing evidence by observed candidate-row impact.

This gate never alters the frozen numeric WCL discovery or SOURCE IF results.
No arguments: two unrelated spec synthetic tests; all other inputs are
offline pinned original evidence, without network/credentials.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from simc_apl_semantic_ir_v2 import canonical
from general_rotation_postlock_typed_pre_scenario_v1 import (
    SCHEMA as SCENARIO_SCHEMA,POLICY,sha
)

SCHEMA="ZrotPostlockGeneralRotationMechanicEpochEvidenceGateV1"
REGISTRY_SCHEMA="ZrotPostlockMechanicEvidenceRegistryV1"
SYM=re.compile(r"^[a-z][a-z0-9_.]*$")
SHA40=re.compile(r"^[a-f0-9]{40}$")
SHA64=re.compile(r"^[a-f0-9]{64}$")
KNOWN_PROVIDERS={
 "BLIZZARD_OFFICIAL":{"worldofwarcraft.blizzard.com"},
 "UNVERSIONED_PUBLIC_SPELL_DB":{"www.wowhead.com"}
}
CLASSIFICATIONS={
 "MECHANIC_REFERENCE_ONLY",
 "PUBLIC_SPELL_ID_NAME_CANDIDATE_ONLY",
 "NO_REGISTERED_EXTERNAL_SEMANTIC_EVIDENCE"
}
TRUST_BOUNDS=(
 "current_Retail_spell_ID_source_identity",
 "WCL_actor_talent_gear_build_equivalence",
 "original_SimC_source_mechanic_implementation_verified",
 "mechanic_effective_and_WCL_report_epoch",
 "original_source_IF_semantic_operand_verified",
 "simultaneous_competitor_cooldown_and_resource_READY"
)

class MechanicGateError(ValueError):pass
def need(ok,code):
    if not ok:raise MechanicGateError(code)

def _utc(value:str):
    need(type(value)==str and value.endswith("Z"),
         "MECHANIC_SOURCE_UTC_TIME_REQUIRED")
    try:result=datetime.fromisoformat(value[:-1]+"+00:00")
    except ValueError as exc:
        raise MechanicGateError("INVALID_UTC_MECHANIC_TIME") from exc
    need(result.tzinfo is not None and result.utcoffset().total_seconds()==0,
         "TIME_WITHOUT_UTC_OFFSET_NOT_ACCEPTED")
    return result

def check_registry(r:dict):
    need(type(r)==dict and r.get("schema")==REGISTRY_SCHEMA and
         r.get("policy_id")==POLICY and
         r.get("purpose","").endswith("strictly AFTER WCL numeric candidate lock") and
         type(r.get("source_spec"))==str and
         re.fullmatch(r"[a-z][a-z0-9_]+",r["source_spec"]) and
         r.get("source_repo")=="simulationcraft/simc" and
         type(r.get("source_commit"))==str and
         SHA40.fullmatch(r["source_commit"]) and
         r.get("source_commit_evidence_url")==
             "https://github.com/simulationcraft/simc/commit/"+r["source_commit"] and
         r.get("source_commit_timestamp_role")==
             "CODE_REVISION_TIME_NOT_GAMEPLAY_MECHANIC_IMPLEMENTATION_PROOF" and
         r.get("WCL_actor_fight_UTC_epoch")=="UNKNOWN" and
         r.get("original_WCL_report_actor_build_complete")=="UNKNOWN" and
         type(r.get("original_blind_numeric_lock_sha256"))==str and
         SHA64.fullmatch(r["original_blind_numeric_lock_sha256"]) and
         r.get("actual_WCL_target_count_at_action")=="UNKNOWN" and
         r.get("requested_promotion") is False and
         r.get("assumption_policy")==
             "NO_EXTERNAL_PUBLIC_NOTE_ALONE_CAN_CERTIFY_GAME_SPELL_ID_OR_GAMEPLAY_READY",
         "MECHANIC_RESEARCH_SCOPE_LOCK_OR_BOUNDS_INVALID")
    commit_time=_utc(r["source_commit_timestamp_utc"])
    refs=r.get("references")
    need(type(refs)==list and 0<len(refs)<=30,
         "BOUNDED_MECHANIC_EXTERNAL_REFERENCES_REQUIRED")
    ids={};publication_times={}
    for ref in refs:
        need(type(ref)==dict and
             type(ref.get("reference_id"))==str and
             re.fullmatch(r"[a-z][a-z0-9_]+",ref["reference_id"]) and
             ref["reference_id"] not in ids and
             ref.get("provider") in KNOWN_PROVIDERS and
             ref.get("retrieved_utc_date") and
             ref.get("information_scope") and
             ref.get("policy") and
             type(ref.get("url"))==str,
             "UNRECONCILED_MECHANIC_REFERENCE")
        uri=urlparse(ref["url"])
        need(uri.scheme=="https" and uri.netloc in
             KNOWN_PROVIDERS[ref["provider"]] and
             not uri.username and not uri.password and
             not uri.fragment,"OFFICIAL_OR_PUBLIC_SOURCE_ORIGIN_INVALID")
        publication=ref["publication_and_mechanic_effective_time"]
        publication_times[ref["reference_id"]]=(
            None if publication=="UNKNOWN" else _utc(publication))
        # An externally described mechanic is not itself current game truth.
        expected_policy=(
           "MECHANIC_TEXT_SCOPE_ONLY_NO_SPELL_ID_OR_APL_SEMANTIC_CERTIFICATION"
           if ref["provider"]=="BLIZZARD_OFFICIAL" else
           "SPELL_ID_NAME_CANDIDATE_ONLY_NOT_PLAYER_BUILD_OR_EXACT_DURATION")
        need(ref["policy"]==expected_policy,
             "REFERENCE_PROOF_SCOPE_NOT_CONSERVATIVE")
        ids[ref["reference_id"]]=ref
    rows=r.get("source_symbol_bindings")
    need(type(rows)==list and 0<len(rows)<=120,
         "SOURCE_OPERAND_REGISTRY_REQUIRED")
    bindings={}
    for item in rows:
        s=item.get("symbol")
        refs_for=item.get("candidate_sources")
        need(type(s)==str and SYM.fullmatch(s) and
             s not in bindings and
             type(refs_for)==list and len(refs_for)<=12 and
             len(set(refs_for))==len(refs_for) and
             all(x in ids for x in refs_for) and
             item.get("source_semantics") in ("UNKNOWN","UNVERIFIED") and
             item.get("source_spell_ID_identity") in (
                "UNKNOWN","CANDIDATE_EXTERNAL_NAME") and
             item.get("source_implementation_patch_parity")=="UNKNOWN" and
             type(item.get("required_next_proof"))==str and
             bool(item["required_next_proof"]) and
             type(item.get("signal_kind"))==str,
             "MECHANIC_SYMBOL_SEMANTICS_INVALID")
        # Explicit grouping above is intentionally rechecked separately:
        # we never allow a numeric ID from Blizzard prose-only references.
        raw_id=item.get("raw_numeric_id")
        need(raw_id is None or type(raw_id)==int and raw_id>0,
             "MECHANIC_EXTERNAL_RAW_ID_INVALID")
        if raw_id is not None:
            need(item["source_spell_ID_identity"]==
                     "CANDIDATE_EXTERNAL_NAME" and
                 bool(refs_for) and all(ids[x]["provider"]==
                     "UNVERSIONED_PUBLIC_SPELL_DB" for x in refs_for),
                 "BLIZZARD_PATCH_NOTE_CANNOT_ATTEST_WCL_NUMERIC_ID")
        if item["source_spell_ID_identity"]=="CANDIDATE_EXTERNAL_NAME":
            need(raw_id is not None,
                 "UNMAPPED_NUMERIC_ID_MUST_NOT_BE_NAME_ID_CANDIDATE")
        bindings[s]=item
    gates=r.get("claim_gates")
    need(type(gates)==dict and gates and
         all(x=="UNKNOWN" for x in gates.values()),
         "UNCERTIFIED_GAME_MECHANIC_CLAIM_WAS_UPGRADED")
    return bindings,ids,publication_times,commit_time

def _study_check(study:dict):
    need(type(study)==dict and
         study.get("schema")==SCENARIO_SCHEMA and
         study.get("policy_id")==POLICY and
         study.get("source_operand_semantics_independently_certified") is False and
         study.get("WCL_actor_build_and_target_source_equivalent") is False and
         study.get("certified_source_IF_guard_true_count")==0 and
         study.get("real_competing_spell_READY_proven")==0 and
         study.get("mandatory_General_Rotation_priorities_promoted")==0 and
         study.get("dummy_wrong_cast_verdicts")==0 and
         study.get("observed_numeric_WCL_ID_does_not_identify_source_APL_row") is True and
         type(study.get("required_source_IF_operand_occurrence_counts"))==dict and
         type(study.get("unmapped_source_IF_operand_occurrence_counts"))==dict and
         type(study.get("unobserved_source_IF_operand_scenario_counts"))==dict and
         type(study.get("numeric_observed_casts"))==int and
         study["numeric_observed_casts"]>0 and
         type(study.get("input_original_WCL_numeric_lock_sha256"))==str and
         SHA64.fullmatch(study["input_original_WCL_numeric_lock_sha256"]),
         "SOURCE_IF_STUDY_GUARD_OR_OBSERVABILITY_CHANGED")
    for name in ("required_source_IF_operand_occurrence_counts",
                 "unmapped_source_IF_operand_occurrence_counts",
                 "unobserved_source_IF_operand_scenario_counts"):
        for symbol,count in study[name].items():
            need(type(symbol)==str and SYM.fullmatch(symbol) and
                 type(count)==int and 0<=count<=100000,
                 "UNTRUSTED_SOURCE_IF_OPERAND_OCCURRENCE_COUNT")
    required=study["required_source_IF_operand_occurrence_counts"]
    for k,v in study["unmapped_source_IF_operand_occurrence_counts"].items():
        need(k in required and v<=required[k],
             "UNMAPPED_OPERAND_COUNT_EXCEEDS_SOURCE_AST")
    return required

def compile_frontier(study:dict, registry:dict,*,context:str)->dict:
    bindings,refs,epochs,simc_time=check_registry(registry)
    required=_study_check(study)
    spec=registry["source_spec"]
    need(type(context)==str and
         context in (spec+"-st",spec+"-2t",spec+"-aoe",
                     spec+"-cleave"),
         "STUDY_SOURCE_SPEC_AND_TARGET_CONTEXT_MISMATCH")
    need(study["input_original_WCL_numeric_lock_sha256"]==
         registry["original_blind_numeric_lock_sha256"],
         "ORIGINAL_NUMERIC_DISCOVERY_LOCK_WRONG")
    rows=[]
    for symbol,n in required.items():
        item=bindings.get(symbol)
        candidate_refs=(item or {}).get("candidate_sources",[])
        candidate=[refs[r] for r in candidate_refs]
        providers={ref["provider"] for ref in candidate}
        stage=("MECHANIC_REFERENCE_ONLY" if
              "BLIZZARD_OFFICIAL" in providers else
              "PUBLIC_SPELL_ID_NAME_CANDIDATE_ONLY" if candidate_refs
              else "NO_REGISTERED_EXTERNAL_SEMANTIC_EVIDENCE")
        epoch_status="UNKNOWN_EFFECTIVE_HOTFIX_AND_WCL_REPORT_TIME"
        # Even a dated patch note and later SimC commit do not certify
        # that source C++ actually implemented the change.
        if candidate and all(epochs[x] is not None for x in candidate_refs):
            if any(simc_time<epochs[x] for x in candidate_refs):
                epoch_status="SOURCE_COMMIT_BEFORE_SOME_DOCUMENTED_CHANGE_REVIEW"
            else:
                epoch_status="COMMIT_AFTER_REPORTED_CHANGE_NOT_MECHANIC_PROOF"
        row={
          "source_symbol":symbol,
          "source_candidate_row_occurrences":n,
          "source_candidate_rows_missing_raw_mapping":
              study["unmapped_source_IF_operand_occurrence_counts"].get(symbol,0),
          "source_operand_missing_PRE_scenarios":
              study["unobserved_source_IF_operand_scenario_counts"].get(symbol,0),
          "strongest_external_reference_stage":stage,
          "candidate_external_reference_ids":candidate_refs,
          "candidate_raw_numeric_ID_only":(item or {}).get("raw_numeric_id"),
          "mechanic_and_WCL_epoch_comparison":epoch_status,
          "named_mechanic_or_ID_source_provenance_only":bool(candidate_refs),
          "current_client_spell_ID_to_source_APL_certified":False,
          "actual_actor_build_talent_gear_compatible":"UNKNOWN",
          "source_implementation_confirmed_against_Blizzard_mechanic":False,
          "full_spell_READY_and_alternatives":"UNKNOWN",
          "dummy_wrong_cast":"UNKNOWN",
          "research_next_evidence":(item or {}).get("required_next_proof",
             "Locate a pinned source semantic candidate / authoritative mechanic contract before making an IF claim.")
        }
        rows.append(row)
    # Stable importance is candidate APL row occurrence, NOT causal
    # magnitude, observed mistakes, source priority or optimization score.
    rows.sort(key=lambda x:(-x["source_candidate_rows_missing_raw_mapping"],
                            -x["source_candidate_row_occurrences"],
                            x["source_symbol"]))
    return {
      "schema":SCHEMA,
      "policy_id":POLICY,
      "source_context":context,
      "source_commit":registry["source_commit"],
      "source_commit_timestamp_utc":registry["source_commit_timestamp_utc"],
      "WCL_actor_report_UTC_epoch":"UNKNOWN",
      "original_numeric_WCL_blind_lock_sha256":
         registry["original_blind_numeric_lock_sha256"],
      "input_source_IF_study_sha256":sha(canonical(study)),
      "input_public_mechanic_registry_sha256":sha(canonical(registry)),
      "source_candidate_WCL_casts":study["raw_WCL_candidate_casts_with_source_token"],
      "candidate_source_IF_rows":study["individual_source_IF_candidate_row_probes"],
      "mechanic_symbol_frontier":rows,
      "raw_unmapped_source_operand_total":sum(
         x["source_candidate_rows_missing_raw_mapping"] for x in rows),
      "mechanic_coverage_stage_count":dict(sorted(Counter(
         x["strongest_external_reference_stage"] for x in rows).items())),
      "source_time_after_public_bulletin_does_not_certify_game_mechanic":True,
      "patch_and_build_evidence_completed":False,
      "Blizzard_official_reference_does_not_certify_numeric_spell_ID":True,
      "current_Retail_source_IF_trues_certified":0,
      "full_competing_action_READY_proven":0,
      "General_Rotation_rules_promoted":0,
      "dummy_wrong_cast_verdicts":0,
      "new_WCL_API_calls":0,
      "SimC_CXX_builds":0,
      "MAIN_promoted":False
    }

def selftest():
    from copy import deepcopy
    positive=0;negative=0
    def must_fail(fn):
        nonlocal negative
        try:fn()
        except (MechanicGateError,ValueError):negative+=1
        else:raise AssertionError("FALSE_MECHANIC_PROOF_PROMOTED")
    sample={
      "schema":SCENARIO_SCHEMA,"policy_id":POLICY,
      "source_operand_semantics_independently_certified":False,
      "WCL_actor_build_and_target_source_equivalent":False,
      "certified_source_IF_guard_true_count":0,
      "real_competing_spell_READY_proven":0,
      "mandatory_General_Rotation_priorities_promoted":0,
      "dummy_wrong_cast_verdicts":0,
      "observed_numeric_WCL_ID_does_not_identify_source_APL_row":True,
      "required_source_IF_operand_occurrence_counts":{
          "buff.proc.stack":6,"gcd":8},
      "unmapped_source_IF_operand_occurrence_counts":{
          "buff.proc.stack":6,"gcd":8},
      "unobserved_source_IF_operand_scenario_counts":{
          "buff.proc.stack":12,"gcd":16},
      "numeric_observed_casts":2,
      "raw_WCL_candidate_casts_with_source_token":2,
      "individual_source_IF_candidate_row_probes":14,
      "input_original_WCL_numeric_lock_sha256":"a"*64
    }
    for spec in ("warrior_fury","mage_arcane"):
        registry={
         "schema":REGISTRY_SCHEMA,"policy_id":POLICY,
         "purpose":"mechanic proof strictly AFTER WCL numeric candidate lock",
         "source_spec":spec,"source_repo":"simulationcraft/simc",
         "source_commit":"b"*40,
         "source_commit_timestamp_utc":"2026-11-01T09:25:22Z",
         "source_commit_evidence_url":
            "https://github.com/simulationcraft/simc/commit/"+"b"*40,
         "source_commit_timestamp_role":
            "CODE_REVISION_TIME_NOT_GAMEPLAY_MECHANIC_IMPLEMENTATION_PROOF",
         "WCL_actor_fight_UTC_epoch":"UNKNOWN",
         "original_WCL_report_actor_build_complete":"UNKNOWN",
         "original_blind_numeric_lock_sha256":"a"*64,
         "actual_WCL_target_count_at_action":"UNKNOWN",
         "requested_promotion":False,
         "assumption_policy":
            "NO_EXTERNAL_PUBLIC_NOTE_ALONE_CAN_CERTIFY_GAME_SPELL_ID_OR_GAMEPLAY_READY",
         "references":[{
            "reference_id":"official","provider":"BLIZZARD_OFFICIAL",
            "url":"https://worldofwarcraft.blizzard.com/en-us/news/test",
            "retrieved_utc_date":"2026-11-09",
            "publication_and_mechanic_effective_time":"UNKNOWN",
            "information_scope":"MECHANIC change but no numeric id",
            "policy":"MECHANIC_TEXT_SCOPE_ONLY_NO_SPELL_ID_OR_APL_SEMANTIC_CERTIFICATION"
         }],
         "source_symbol_bindings":[{
           "symbol":"buff.proc.stack","candidate_sources":["official"],
           "raw_numeric_id":None,"signal_kind":"STACK",
           "source_semantics":"UNVERIFIED","source_spell_ID_identity":"UNKNOWN",
           "source_implementation_patch_parity":"UNKNOWN",
           "required_next_proof":"pin exact spell ID"}],
         "claim_gates":{"spell_ID":"UNKNOWN","actor_build":"UNKNOWN"}
        }
        r=compile_frontier(sample,registry,context=spec+"-st")
        need(len(r["mechanic_symbol_frontier"])==2 and
             r["raw_unmapped_source_operand_total"]==14 and
             r["mechanic_symbol_frontier"][0]["source_symbol"]=="gcd" and
             r["current_Retail_source_IF_trues_certified"]==0 and
             r["dummy_wrong_cast_verdicts"]==0,
             "GENERIC_MECHANIC_FRONTIER_SYNTHETIC_INVALID")
        positive+=1
        v=deepcopy(sample);v["certified_source_IF_guard_true_count"]=1
        must_fail(lambda:compile_frontier(v,registry,context=spec+"-st"))
        v=deepcopy(registry);v["requested_promotion"]=True
        must_fail(lambda:compile_frontier(sample,v,context=spec+"-st"))
        v=deepcopy(registry);v["source_symbol_bindings"][0]["raw_numeric_id"]=123
        must_fail(lambda:compile_frontier(sample,v,context=spec+"-st"))
        v=deepcopy(registry);v["claim_gates"]["spell_ID"]="PASS"
        must_fail(lambda:compile_frontier(sample,v,context=spec+"-st"))
        v=deepcopy(registry);v["references"][0]["url"]="https://evil.example/spell"
        must_fail(lambda:compile_frontier(sample,v,context=spec+"-st"))
        v=deepcopy(registry);v["references"][0]["policy"]="CERTIFIED_GAMEPLAY"
        must_fail(lambda:compile_frontier(sample,v,context=spec+"-st"))
        v=deepcopy(registry);v["original_blind_numeric_lock_sha256"]="0"*64
        must_fail(lambda:compile_frontier(sample,v,context=spec+"-st"))
        must_fail(lambda:compile_frontier(sample,registry,context="other-st"))
    return {
      "schema":SCHEMA,"status":"PASS_GENERIC_SOURCE_MECHANIC_EPOCH_GATE",
      "two_different_specializations_synthetic":positive,
      "negative_claim_controls":negative,
      "Blizzard_prose_does_not_assign_spell_ID":True,
      "SimC_commit_after_bulletin_not_semantic_proof":True,
      "original_blind_numeric_lock_untouched":True,
      "current_Retail_source_IF_certified":0,
      "actual_WCL_API_calls":0
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study",type=Path)
    p.add_argument("--registry",type=Path)
    p.add_argument("--context")
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if all(x is None for x in vars(args).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(x is not None for x in vars(args).values()),
         "SOURCE_IF_STUDY_REGISTRY_CONTEXT_OUT_REQUIRED")
    need(not args.out.exists(),"NO_OVERWRITE_MECHANIC_FRONTIER_EVIDENCE")
    study=json.loads(args.study.read_bytes())
    registry=json.loads(args.registry.read_bytes())
    result=compile_frontier(study,registry,context=args.context)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes(canonical(result))
    print("GENERIC_POSTLOCK_MECHANIC_EPOCH_FRONTIER_SHA256="+
          sha(args.out.read_bytes()))
    print("MISSING_SOURCE_MECHANIC_EVIDENCE_FRONTIER="+json.dumps(
          [(x["source_symbol"],
            x["source_candidate_rows_missing_raw_mapping"])
           for x in result["mechanic_symbol_frontier"]],sort_keys=True))
    print("CERTIFIED_CURRENT_RETAIL_SOURCE_IF_OR_PRIORITY_PROVEN=0")
if __name__=="__main__":main()
