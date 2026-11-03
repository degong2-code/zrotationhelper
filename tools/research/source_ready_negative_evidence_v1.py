#!/usr/bin/env python3
"""Generic evidence-gated foreground action availability from source ready() rules.

This executor accepts spec adapter + SHA-pinned SimC implementation and the
prior immutable WCL-derived 105-cast strict-PRE talent/buff receipt.

A source-model ready() hard blocker is a useful *conditional exclusion*,
NOT direct proof that the game client shared the same build/patch and NOT
proof that another action is ready. It never reconstructs cooldown from
intercast gaps or assumes reset procs/charges/GCD. All cases remain UNKNOWN
for full cooldown readiness, alternative optimality and player mistakes.

Safe no-argument entry point runs local synthetic regression; no network.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SIMC_BLOB="38ee3dd0d5943eb9227ec55aefb21e7d47244f96"
PRELOCK_RECEIPT_SHA="2f2a14d9dd9b4d9f5fc70819e5e2285e8767639203bc03a27efa3af69ec3caa5"
BLIND_LOCK="c5e2bedeb7f4f0152e8ba86a30b1b13ecc5aa1374af4c0b01237a16151a1c98e"

class EvidenceError(ValueError):pass


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def git_blob(blob):
    return hashlib.sha1(b"blob "+str(len(blob)).encode()+b"\0"+blob).hexdigest()


def unique_json(raw):
    def unique(pairs):
        obj={}
        for name,value in pairs:
            if name in obj:raise EvidenceError("DUPLICATE_JSON_FIELD")
            obj[name]=value
        return obj
    return json.loads(raw,object_pairs_hook=unique)


def parse_adapter(raw):
    a=unique_json(raw)
    if (a.get("schema")!="ZrotSourceForegroundReadyGateAdapterV1"
        or a.get("scope_policy_id")!=POLICY
        or a.get("spec_id")!=72
        or a.get("source",{}).get("git_blob_sha1")!=SIMC_BLOB
        or a.get("frozen_discovery_lock_sha256")!=BLIND_LOCK
        or a.get("allow_full_READY") is not False
        or a.get("allow_automatic_player_error") is not False
        or a.get("allow_use_cast_gap_as_cooldown") is not False
        or a.get("source_model_patch_equivalence_to_WCL")!="UNKNOWN"):
        raise EvidenceError("UNTRUSTED_ADAPTER_SOURCE_OR_AUTHORITY")
    pairs=a.get("cooldown_families")
    if not isinstance(pairs,list) or len(pairs)!=2:
        raise EvidenceError("COOLDOWN_FAMILIES_NOT_COMPLETE")
    names=set()
    for pair in pairs:
        if pair.get("shared_cooldown_key") not in ("bloodthirst","raging_blow"):
            raise EvidenceError("UNEXPECTED_COOLDOWN_FAMILY")
        for side in ("base","replacement"):
            row=pair.get(side)
            if not isinstance(row,dict):raise EvidenceError("MISSING_ACTION_VARIANT")
            if row.get("block_when")!=("GATE_TRUE" if side=="base" else "GATE_FALSE"):
                raise EvidenceError("WRONG_MODEL_GATE")
            name=row.get("action")
            if not isinstance(name,str) or name in names:
                raise EvidenceError("NON_UNIQUE_ACTION_ALIAS")
            names.add(name)
    if names!={"bloodthirst","bloodbath","raging_blow","crushing_blow"}:
        raise EvidenceError("ACTION_VARIANTS_NOT_LOCKED")
    return a


def extract_struct(source,struct):
    if not re.fullmatch(r"[a-z][a-z0-9_]*_t",struct):
        raise EvidenceError("INVALID_SOURCE_STRUCT_NAME")
    matches=list(re.finditer(r"(?m)^struct "+re.escape(struct)+r"\s*:\s*public\s+warrior_attack_t\b",source))
    if len(matches)!=1:
        raise EvidenceError("SOURCE_CLASS_STRUCT_NOT_UNIQUE_"+struct)
    begin=matches[0].start()
    finish=source.find("\n};",begin)
    if finish<0:
        raise EvidenceError("SOURCE_CLASS_UNTERMINATED_"+struct)
    code=source[begin:finish+3]
    ready=code.find("bool ready() override")
    if ready<0:raise EvidenceError("SOURCE_READY_OVERRIDE_NOT_FOUND_"+struct)
    ready_src=code[ready:]
    if "return warrior_attack_t::ready();" not in ready_src:
        raise EvidenceError("SOURCE_READY_PARENT_DELEGATION_MISSING_"+struct)
    return ready_src


def verify_source_mechanics(source_blob,adapter):
    if git_blob(source_blob)!=SIMC_BLOB:
        raise EvidenceError("SIMC_SOURCE_GIT_BLOB_CHANGED")
    source=source_blob.decode("utf-8")
    anchored={}
    for family in adapter["cooldown_families"]:
        for variant in ("base","replacement"):
            row=family[variant]
            section=extract_struct(source,row["source_struct"])
            if variant=="base":
                # Bloodthirst is excluded as a player foreground action, but
                # its background path is explicitly exempt in SimC.
                source_pattern=(r"if\s*\(\s*p\(\)->talents\.fury\.reckless_abandon->ok\(\)"
                    r"\s*&&\s*p\(\)->buff\.recklessness->check\(\)")
                if not re.search(source_pattern,section):
                    raise EvidenceError("SOURCE_BASE_REPLACEMENT_READY_GUARD_MISSING")
                has_background="&& !background" in section
                if has_background!=row["foreground_exception"]:
                    raise EvidenceError("SOURCE_BACKGROUND_EXEMPTION_CHANGED")
            else:
                for clause in (
                    r"if\s*\(\s*!p\(\)->talents\.fury\.reckless_abandon->ok\(\)\s*\)\s*return false;",
                    r"if\s*\(\s*!p\(\)->buff\.recklessness->check\(\)\s*\)\s*return false;"
                ):
                    if not re.search(clause,section):
                        raise EvidenceError("SOURCE_REPLACEMENT_NEGATIVE_GUARD_MISSING")
            # The ready code contains other restrictions, which this audit
            # intentionally does not assert resolved by simply passing gate.
            anchored[row["action"]]={
                "ready_override_confirmed":True,
                "action_group":family["shared_cooldown_key"],
                "excludes_only_foreground":row["foreground_exception"],
                "source_code_ready_override_sha256":sha(section.encode()),
                "all_other_ready_checks_verified":False}
    if len(anchored)!=4:raise EvidenceError("SOURCE_MODEL_MISSING_ACTIONS")
    return anchored


def gate_states(gate,adapter):
    """Only negative source-model availability is conclusive here."""
    if gate not in ("TRUE","FALSE","UNKNOWN"):
        raise EvidenceError("UNRECOGNIZED_SOURCE_PRE_GATE")
    selected={}
    for pair in adapter["cooldown_families"]:
        for side in ("base","replacement"):
            variant=pair[side]
            name=variant["action"]
            if gate=="UNKNOWN":
                status="UNKNOWN_GATE"
            elif (gate=="TRUE")==(side=="base"):
                status="SOURCE_MODEL_BLOCKED_FOREGROUND"
            else:
                status="SOURCE_MODEL_GATE_PASSED_OTHER_READY_FACTORS_UNKNOWN"
            selected[name]={
                "source_ready_guard_status":status,
                "shared_cooldown_group":pair["shared_cooldown_key"],
                "cooldown_ready":"UNKNOWN",
                "charges_available":"UNKNOWN",
                "gcd_ready":"UNKNOWN",
                "real_player_action_ready":"UNKNOWN",
                "applies_only_to_simc_source_model":True
            }
    return selected


def evaluate(adapter,source_details,receipt):
    if (receipt.get("schema")!="ZrotWclSpecTraitEffectiveActionGateV1"
        or receipt.get("scope_policy_id")!=POLICY
        or receipt.get("status")!="OBSERVED_REPLACEMENT_GATE_NOT_COOLDOWN_READY"
        or receipt.get("source_patch_equivalence_to_player")!="UNKNOWN"
        or receipt.get("source_cast_family_receipt_sha256")!=
          "e622c7df37d9b792f403b00abe54228fa9a8f1dfac8133610a8517143afd80ab"
        or receipt.get("actual_competing_spell_cooldown_readiness")!="UNKNOWN"
        or receipt.get("total_casts")!=105):
        raise EvidenceError("UNTRUSTED_POSTLOCK_REPLACEMENT_RECEIPT")
    by_role={}
    for role,expected_count in (("discovery",54),("holdout",51)):
        x=receipt[role]
        if (x.get("casts_evaluated")!=expected_count
            or len(x.get("recorded_cast_details",[]))!=expected_count
            or x.get("trait_numeric_precombat_evidence",{}).get("source")!="STRICT_PRE_COMBATANTINFO"):
            raise EvidenceError("WCL_COHORT_CAST_IDENTITY_DRIFT")
        stats={name:Counter() for name in source_details}
        decisions=[]
        for d in x["recorded_cast_details"]:
            gate=d.get("source_model_replacement_gate")
            s=gate_states(gate,adapter)
            for name,entry in s.items():
                stats[name][entry["source_ready_guard_status"]]+=1
            if d.get("which_action_should_be_pressed")!="UNKNOWN":
                raise EvidenceError("WCL_RECEIPT_ALREADY_PROMOTED_PRIORITY")
            decisions.append({
                "timestamp":d["timestamp"],
                "actual_numeric_spell_id":d["actual_numeric_spell_id"],
                "strict_pre_replacement_gate":gate,
                "candidate_foreground_actions":s,
                "source_model_nonreadiness_proven_actions":sorted(
                    name for name,v in s.items()
                    if v["source_ready_guard_status"]=="SOURCE_MODEL_BLOCKED_FOREGROUND"),
                "actual_game_ready_action":"UNKNOWN",
                "competing_actions_cd_charge_states":"UNKNOWN",
                "expected_priority_action":"UNKNOWN",
                "trainer_wrong_cast":"UNKNOWN"
            })
        by_role[role]={
            "observed_casts":expected_count,
            "source_trait":x["trait_numeric_precombat_evidence"],
            "source_model_action_guard_status_counts":{
                name:{key:count for key,count in sorted(counter.items())}
                for name,counter in sorted(stats.items())},
            "source_model_foreground_exclusions":sum(
                len(r["source_model_nonreadiness_proven_actions"]) for r in decisions),
            "actual_ready_positive_claims":0,
            "confirmed_player_wrong_casts":0,
            "actions":decisions
        }
    return {
       "schema":"ZrotSourceReadyNegativeProofAndWclStrictPreV1",
       "scope_policy_id":POLICY,
       "status":"SOURCE_FOREGROUND_BLOCKERS_OBSERVED_NOT_COMPLETE_GAME_READINESS",
       "source_simc_git_blob_sha1":SIMC_BLOB,
       "source_ready_override_evidence":source_details,
       "source_pre_talent_buff_receipt_sha256":PRELOCK_RECEIPT_SHA,
       "total_actor_casts":105,
       "source_model_false_ready_action_contexts":sum(
           r["source_model_foreground_exclusions"] for r in by_role.values()),
       "game_cd_charge_state_verified":False,
       "simc_patch_and_player_full_build_equivalence":"UNKNOWN",
       "actual_target_count":"UNKNOWN",
       "true_spell_ready_claims":0,
       "confirmed_dummy_mistakes":0,
       "MAIN_promotion":False,
       **by_role
    }


def selftest():
    adapter={"schema":"ZrotSourceForegroundReadyGateAdapterV1",
      "scope_policy_id":POLICY,"spec_id":72,
      "source":{"git_blob_sha1":SIMC_BLOB},
      "frozen_discovery_lock_sha256":BLIND_LOCK,
      "allow_full_READY":False,"allow_automatic_player_error":False,
      "allow_use_cast_gap_as_cooldown":False,
      "source_model_patch_equivalence_to_WCL":"UNKNOWN",
      "cooldown_families":[
        {"shared_cooldown_key":"bloodthirst",
         "base":{"action":"bloodthirst","source_struct":"bloodthirst_t","block_when":"GATE_TRUE","foreground_exception":True},
         "replacement":{"action":"bloodbath","source_struct":"bloodbath_t","block_when":"GATE_FALSE","foreground_exception":False}},
        {"shared_cooldown_key":"raging_blow",
         "base":{"action":"raging_blow","source_struct":"raging_blow_t","block_when":"GATE_TRUE","foreground_exception":False},
         "replacement":{"action":"crushing_blow","source_struct":"crushing_blow_t","block_when":"GATE_FALSE","foreground_exception":False}}]}
    adapter=parse_adapter(json.dumps(adapter).encode())
    tru=gate_states("TRUE",adapter)
    assert {x for x in tru if tru[x]["source_ready_guard_status"]=="SOURCE_MODEL_BLOCKED_FOREGROUND"}=={"bloodthirst","raging_blow"}
    assert all(tru[x]["cooldown_ready"]=="UNKNOWN" for x in tru)
    fls=gate_states("FALSE",adapter)
    assert {x for x in fls if fls[x]["source_ready_guard_status"]=="SOURCE_MODEL_BLOCKED_FOREGROUND"}=={"bloodbath","crushing_blow"}
    assert all(r["real_player_action_ready"]=="UNKNOWN" for r in fls.values())
    unk=gate_states("UNKNOWN",adapter)
    assert all(r["source_ready_guard_status"]=="UNKNOWN_GATE" for r in unk.values())
    assert all(r["charges_available"]=="UNKNOWN" for r in unk.values())
    for invalid in ("READY",True,None,2):
        try:gate_states(invalid,adapter)
        except EvidenceError:pass
        else:raise AssertionError("ACCEPTED_UNPROVEN_GAME_READINESS")
    try:parse_adapter(json.dumps({**adapter,"allow_full_READY":True}).encode())
    except EvidenceError:pass
    else:raise AssertionError("ACCEPTED_PRIORITY_PROMOTION")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":11,
            "actual_WCL_or_SimC_loaded":False,
            "false_player_priority_errors":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--simc-cpp",type=Path)
    p.add_argument("--replacement-receipt",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any((a.adapter,a.simc_cpp,a.replacement_receipt)):
        result=selftest()
    elif all((a.adapter,a.simc_cpp,a.replacement_receipt)):
        ad=parse_adapter(a.adapter.read_bytes())
        source=verify_source_mechanics(a.simc_cpp.read_bytes(),ad)
        evidence=a.replacement_receipt.read_bytes()
        if sha(evidence)!=PRELOCK_RECEIPT_SHA:
            raise EvidenceError("POSTLOCK_WCL_SOURCE_RECEIPT_BYTES_CHANGED")
        result=evaluate(ad,source,unique_json(evidence))
    else:p.error("all three pinned source inputs required, or none for self-test")
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
        print("SIMC_WCL_FOREGROUND_READY_GATE_SHA256="+sha(raw))
    else:print(raw.decode(),end="")

if __name__=="__main__":main()
