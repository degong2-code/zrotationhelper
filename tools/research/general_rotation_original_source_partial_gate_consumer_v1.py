#!/usr/bin/env python3
"""Verified ORIGINAL SimC source PRE -> generic open-world gate evidence.

Consumes one CI-produced, byte-pinned passive source-PRE probe receipt,
a separately pinned original reporter source receipt and a pristine vs
instrumented cast-sequence parity report. Recomputes numeric predicates
INDEPENDENTLY from original raw source fields, never from a post-choice
ready bit or source-claimed Boolean. Never accepts a positive READY route
closure; partial base-method predicates are not global readiness gates.

This reusable consumer is separate from the producer/SpecAdapter. The
caller must authenticate the GitHub Actions run and the expected bytes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import git_blob,parse_profile
from general_rotation_decision_proof_engine_v1 import (
    Identity,Fact,GateContract,decide_candidate,UNKNOWN
)

SCHEMA="ZrotGenericOriginalSourcePREPartialGateConsumerV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
AUDIT_SCHEMA="ZrotSourcePinnedOriginalDirectionCastPREProbeV1"
PARITY_SCHEMA="ZrotFocusedOriginalSourcePRESequenceNonperturbationV1"
PROVENANCE="SIMC_ORIGINAL_METHOD_PRE"
GATES=("MOVEMENT_DIRECTIONALITY_BASE_CLEAR",
       "CAST_BASE_WHILE_CASTING_BRANCH_BYPASS")
UNRESOLVED=("MOVEMENT","CAST_GCD","NECESSARY_ELIGIBILITY",
            "SPEC_OVERRIDE_TOTAL","BASE_VIRTUAL_COMPLETE")

class SourceEvidenceError(ValueError):
    pass


def raw_json(raw:bytes,expected_sha:str)->dict:
    if (not isinstance(expected_sha,str) or len(expected_sha)!=64 or
        sha256(raw).hexdigest()!=expected_sha):
        raise SourceEvidenceError("SOURCE_EVIDENCE_SHA256_MISMATCH")
    try:
        result=json.loads(raw)
    except (ValueError,TypeError) as e:
        raise SourceEvidenceError("INVALID_EVIDENCE_JSON") from e
    if not isinstance(result,dict):
        raise SourceEvidenceError("EVIDENCE_OBJECT_REQUIRED")
    return result


def recompute(source_profile:bytes,profile_blob:str, *,
              raw_audit:bytes,expected_audit_sha256:str,
              raw_patch:bytes,expected_patch_sha256:str,
              raw_parity:bytes,expected_parity_sha256:str,
              expected_key:tuple[int,str,int,str]) -> dict:
    if (git_blob(source_profile)!=profile_blob or
        len(expected_key)!=4 or type(expected_key[0]) is not int or
        expected_key[0]<0 or
        type(expected_key[2]) is not int or expected_key[2]<1):
        raise SourceEvidenceError("OFFICIAL_PROFILE_OR_FOCUS_NOT_PINNED")
    ir=parse_profile(source_profile,require_source=True,
                     expected_git_blob=profile_blob)
    t,name,ord1,action=expected_key
    lists=ir["action_lists"]
    if (name not in lists or ord1>len(lists[name])):
        raise SourceEvidenceError("FOCUSED_APL_ROW_MISSING")
    source_row=lists[name][ord1-1]
    if source_row["behavior"]!="ACTION" or source_row["action"]!=action:
        raise SourceEvidenceError("FOCUSED_APL_ROW_NOT_PHYSICAL_ACTION")
    audit=raw_json(raw_audit,expected_audit_sha256)
    patch=raw_json(raw_patch,expected_patch_sha256)
    parity=raw_json(raw_parity,expected_parity_sha256)
    if (audit.get("schema")!=AUDIT_SCHEMA or
        audit.get("policy_id")!=POLICY or
        audit.get("scope")!="SIMC_ORIGINAL_METHOD_PRE" or
        audit.get("WCL_API_calls")!=0 or
        audit.get("full_positive_READY_proven")!=0 or
        audit.get("dummy_error_permitted") is not False or
        type(audit.get("original_pre_attempts_with_fields")) is not int or
        audit["original_pre_attempts_with_fields"]<1):
        raise SourceEvidenceError("SOURCE_PRE_AUDIT_CONTRACT_DRIFT")
    if (patch.get("schema")!=AUDIT_SCHEMA or
        patch.get("policy_id")!=POLICY or
        patch.get("new_virtual_or_target_calls")!=0 or
        patch.get("original_ready_method_call_count_unchanged") is not True or
        patch.get("original_NATIVE_and_pristine_behavior_parity")!="NOT_YET_TESTED" or
        not isinstance(patch.get("modified_player_sha256"),str)):
        raise SourceEvidenceError("SOURCE_PRE_PATCH_PROVENANCE_INVALID")
    if (parity.get("schema")!=PARITY_SCHEMA or
        parity.get("original_profile_and_APL_identical") is not True or
        parity.get("precombat_cast_sequence_equal") is not True or
        parity.get("combat_cast_sequence_equal") is not True or
        parity.get("original_combat_count")!=parity.get("instrumented_combat_count") or
        type(parity.get("original_combat_count")) is not int or
        parity["original_combat_count"]<1):
        raise SourceEvidenceError("ORIGINAL_VS_INSTRUMENTED_CAST_SEQUENCE_CONFLICT")
    p=audit.get("one_exact_source_key",{})
    if not isinstance(p,dict) or p.get("source_key")!=list(expected_key):
        raise SourceEvidenceError("SOURCE_PRE_FOCUS_IDENTITY_MISMATCH")
    raw=p.get("observed_direct_source_fields")
    upstream=p.get("independent_base_subpredicates")
    if (not isinstance(raw,dict) or not isinstance(upstream,dict) or
        (raw.get("time_ms"),raw.get("list"),raw.get("ordinal"),
         raw.get("native_name"))!=expected_key or
        raw.get("actor_is_moving") not in (0,1) or
        raw.get("action_direction") not in range(5) or
        raw.get("actor_direction") not in range(5) or
        raw.get("usable_while_casting") not in (0,1) or
        any(raw.get(k) not in (0,1) for k in
            ("actor_executing","actor_channeling")) or
        type(raw.get("gcd_ready_ms")) is not int):
        raise SourceEvidenceError("RAW_SOURCE_PRE_FIELDS_INVALID")
    # Independent source-formula re-evaluation:
    # pinned action_t::has_movement_directionality() checks enum NONE/OMNI,
    # actor movement NONE or exact direction equality. It is virtual, hence
    # this is only the BASE expression, not full method-dispatch closure.
    a,m=raw["action_direction"],raw["actor_direction"]
    independent_direction=(a in (0,1) or m==0 or a==m)
    # action_t::ready() checks execute_time/gcd() only in the conditional
    # branch when usable_while_casting is enabled; false bypasses that
    # branch but does not prove an action can globally cast.
    independent_cast_bypass=raw["usable_while_casting"]==0
    if (upstream.get("base_directionality_numeric") is not independent_direction or
        upstream.get("base_usable_while_casting_branch_bypassed") is not independent_cast_bypass or
        upstream.get("physical_skill_READY")!="UNKNOWN" or
        upstream.get("MOVEMENT_full_route")!="UNKNOWN" or
        upstream.get("CAST_GCD_full_route")!="UNKNOWN" or
        upstream.get("readiness_virtual_dispatch_closed") is not False or
        upstream.get("dummy_error_permitted") is not False or
        upstream.get("original_method_PRE_time_ms")!=t):
        raise SourceEvidenceError("INDEPENDENT_SOURCE_FORMULA_VS_PRODUCER_CONFLICT")
    ident=Identity(scope=name+"::"+action,
                   source_sha256=source_row["source_sha256"],
                   t_ms=t,ordinal=ord1-1,occurrence=0)
    contract=GateContract(
        source="PINNED_ORIGINAL_SOURCE_PRE_BASE_SUBCONDITIONS",
        source_sha256=source_row["source_sha256"],
        required=GATES+UNRESOLVED,closed=False)
    proven=[]
    for gate,value in (
        (GATES[0],independent_direction),
        (GATES[1],independent_cast_bypass)):
        if value is True:
            proven.append(Fact(
                ident,gate,True,"INDEPENDENT_SOURCE_REPLAY",
                PROVENANCE,t,
                "sha256:source_audit:"+expected_audit_sha256))
        # False *base* expressions are not a necessary negative unless
        # source virtual dispatch has independently been closed.
    verdict=decide_candidate(ident,contract,proven,is_physical_action=True)
    if verdict["decision"]!=UNKNOWN or verdict["dummy_error_permitted"]:
        raise SourceEvidenceError("PARTIAL_PRE_EVIDENCE_PROMOTED_TO_FULL_READY")
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "official_profile_git_blob_sha1":profile_blob,
        "source_list":name,"source_index":ord1-1,
        "source_action":action,
        "source_row_sha256":source_row["source_sha256"],
        "decision_at_simc_ms":t,"source_occurrence":0,
        "original_probe_audit_sha256":expected_audit_sha256,
        "original_probe_patch_sha256":expected_patch_sha256,
        "pristine_instrumented_sequence_sha256":expected_parity_sha256,
        "original_combat_casts_preserved":parity["original_combat_count"],
        "raw_source_values_recomputed":raw,
        "actual_original_source_PRE_independent_subgates":[
            {"gate":f.gate,"value":f.value,"basis":f.basis,
             "captured":f.captured,"at_ms":f.event_t_ms,
             "receipt":f.receipt} for f in proven],
        "partial_gates_positive_count":len(proven),
        "partial_gates_not_proven":[g for g in GATES
                                     if g not in verdict["independent_true"]],
        "full_movement_cast_or_spec_route": "UNKNOWN",
        "remaining_full_gates":list(UNRESOLVED),
        "selected_candidate_status":verdict["decision"],
        "Native_selected_return_as_independent_READY":False,
        "external_unverified_adapter_JSON_used":False,
        "WCL_strict_PRE_observed":False,
        "WCL_API_calls":0,
        "dummy_trainer_error_permitted":False,
        "complete_general_rotation_opener":False,
        "MAIN_promoted":False,
    }


def selftest()->dict:
    source=b"actions=alpha\n"
    profile_blob=git_blob(source)
    key=(20,"default",1,"alpha")
    audit={
        "schema":AUDIT_SCHEMA,"policy_id":POLICY,
        "scope":"SIMC_ORIGINAL_METHOD_PRE",
        "original_pre_attempts_with_fields":1,
        "WCL_API_calls":0,"full_positive_READY_proven":0,
        "dummy_error_permitted":False,
        "one_exact_source_key":{
            "source_key":list(key),
            "observed_direct_source_fields":{
                "time_ms":20,"list":"default","ordinal":1,"native_name":"alpha",
                "action_direction":0,"actor_direction":0,
                "usable_while_casting":0,
                "actor_executing":0,"actor_channeling":0,
                "gcd_ready_ms":18,"actor_is_moving":0},
            "independent_base_subpredicates":{
                "base_directionality_numeric":True,
                "base_usable_while_casting_branch_bypassed":True,
                "original_method_PRE_time_ms":20,
                "physical_skill_READY":"UNKNOWN",
                "MOVEMENT_full_route":"UNKNOWN",
                "CAST_GCD_full_route":"UNKNOWN",
                "readiness_virtual_dispatch_closed":False,
                "dummy_error_permitted":False,
            }
        }
    }
    patch={"schema":AUDIT_SCHEMA,"policy_id":POLICY,
           "new_virtual_or_target_calls":0,
           "original_ready_method_call_count_unchanged":True,
           "original_NATIVE_and_pristine_behavior_parity":"NOT_YET_TESTED",
           "modified_player_sha256":"f"*64}
    parity={"schema":PARITY_SCHEMA,
            "original_profile_and_APL_identical":True,
            "precombat_cast_sequence_equal":True,
            "combat_cast_sequence_equal":True,
            "original_combat_count":1,"instrumented_combat_count":1}
    enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+"\n").encode()
    def call(a=audit,pt=patch,p=parity,expected=None):
        rb,rp,rr=enc(a),enc(pt),enc(p)
        return recompute(source,profile_blob,
            raw_audit=rb,expected_audit_sha256=(
                expected if expected is not None else sha256(rb).hexdigest()),
            raw_patch=rp,expected_patch_sha256=sha256(rp).hexdigest(),
            raw_parity=rr,expected_parity_sha256=sha256(rr).hexdigest(),
            expected_key=key)
    result=call()
    assert result["partial_gates_positive_count"]==2
    assert result["selected_candidate_status"]==UNKNOWN
    assert result["remaining_full_gates"]==list(UNRESOLVED)
    assert result["dummy_trainer_error_permitted"] is False
    from copy import deepcopy
    attempts=[]
    false_result=deepcopy(audit)
    false_result["one_exact_source_key"]["observed_direct_source_fields"][
        "usable_while_casting"]=1
    false_result["one_exact_source_key"]["independent_base_subpredicates"][
        "base_usable_while_casting_branch_bypassed"]=False
    reduced=call(a=false_result)
    assert reduced["partial_gates_positive_count"]==1
    assert reduced["selected_candidate_status"]==UNKNOWN
    for changed in (
        lambda a:a["one_exact_source_key"].update(source_key=[19,"default",1,"alpha"]),
        lambda a:a["one_exact_source_key"]["observed_direct_source_fields"].update(
            actor_direction=6),
        lambda a:a["one_exact_source_key"]["independent_base_subpredicates"].update(
            base_directionality_numeric=False),
        lambda a:a.update(full_positive_READY_proven=1),
    ):
        forged=deepcopy(audit)
        changed(forged)
        try:call(a=forged)
        except SourceEvidenceError:attempts.append(True)
        else:raise AssertionError("FORGED_OR_CONTRADICTORY_SOURCE_PRE_ACCEPTED")
    try:call(expected="0"*64)
    except SourceEvidenceError:attempts.append(True)
    else:raise AssertionError("ALTERED_RECEIPT_SHA256_ACCEPTED")
    assert len(attempts)==5
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":12,"source_original_native_CXX_executed":False,
            "full_positive_READY":0,"WCL_API_calls":0}


def main()->None:
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--official-profile",type=Path)
    a.add_argument("--expected-profile-git-blob")
    a.add_argument("--audit-json",type=Path)
    a.add_argument("--audit-sha256")
    a.add_argument("--patch-json",type=Path)
    a.add_argument("--patch-sha256")
    a.add_argument("--parity-json",type=Path)
    a.add_argument("--parity-sha256")
    a.add_argument("--focus-time-ms",type=int)
    a.add_argument("--focus-list")
    a.add_argument("--focus-ordinal",type=int)
    a.add_argument("--focus-action")
    a.add_argument("--out",type=Path)
    args=a.parse_args()
    fields=(args.official_profile,args.expected_profile_git_blob,
            args.audit_json,args.audit_sha256,args.patch_json,
            args.patch_sha256,args.parity_json,args.parity_sha256,
            args.focus_time_ms,args.focus_list,args.focus_ordinal,
            args.focus_action,args.out)
    if all(x is None for x in fields):
        result=selftest()
        print(json.dumps(result,sort_keys=True))
        return
    if any(x is None for x in fields):
        a.error("all source/pin/audit/patch/parity/focus/output fields required")
    result=recompute(args.official_profile.read_bytes(),
        args.expected_profile_git_blob,
        raw_audit=args.audit_json.read_bytes(),
        expected_audit_sha256=args.audit_sha256,
        raw_patch=args.patch_json.read_bytes(),
        expected_patch_sha256=args.patch_sha256,
        raw_parity=args.parity_json.read_bytes(),
        expected_parity_sha256=args.parity_sha256,
        expected_key=(args.focus_time_ms,args.focus_list,
                      args.focus_ordinal,args.focus_action))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("xb") as f:
        f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    print("ORIGINAL_SOURCE_PARTIAL_GATE_CONSUMER_SHA256="+
          sha256(args.out.read_bytes()).hexdigest())


if __name__=="__main__":
    main()
