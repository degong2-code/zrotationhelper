#!/usr/bin/env python3
"""Fail-closed, offline continuity gate for zRotationHelper product intent.

Checks a user-approved scope lock, the active documentation entrypoints,
the latest real branch handoff, a full-snapshot handoff template, and 5
synthetic successor transitions. NEVER calls legacy MAIN, WCL or SimC.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
LOCK_PATH=ROOT/"docs/PRODUCT_SCOPE_LOCK_V1.json"
TEMPLATE=ROOT/"handoff/HANDOFF_TEMPLATE_V1.json"
ACTIVE=ROOT/"_UPLOAD_TO_CHATGPT/branches/BR-ENGINE-FIRST-FRESH-WCL-VSLICE/LATEST_HANDOFF.json"
EXPECTED_POLICY_ID="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
EXPECTED_BLOB_SHA1="14b9f5174a9d1652a56dcca03af1f2302b78c22d"
EXPECTED_POLICY_SHA256="157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295"
EXPECTED_RESEARCH_ORDER=[
 "SIMC_APL_PROFILE_BASELINE_AND_OPENER_HYPOTHESIS",
 "WCL_HIGH_RANKER_STRICT_PRE_INDEPENDENT_BLIND_CANDIDATE_DISCOVERY_AND_LOCK",
 "POST_LOCK_SIMC_HYPOTHESIS_REPLAY_AGAINST_WCL_RANKER_STATES",
 "BLIZZARD_MECHANIC_RECONCILIATION_AND_IMPORTANT_AMBIGUITY_VALIDATION",
 "VALIDATED_GENERAL_ROTATION_OPENER_AND_PRIORITY_IR",
 "TARGET_DUMMY_OWN_ACTION_FEEDBACK",
]
EXPECTED_EXCLUDED={
 "ENCOUNTER_SPECIFIC_ROTATION_PLAN",
 "RAID_EXECUTION_ASSISTANT",
 "NSRT_EXPORT",
 "RAID_TIMELINE_OR_BOSS_GUIDE_EXPORT",
 "PRODUCTION_READY_GAMEPLAY_CLAIM_WITHOUT_VALIDATION",
}

class ScopeDrift(ValueError):
    pass

def encoded(x:dict)->bytes:
    return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")

def git_blob_sha1(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def digest(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def load(path:Path)->dict:
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict):raise ScopeDrift("NON_OBJECT_JSON")
    return x

def assert_lock(p:dict)->None:
    def need(cond:bool,reason:str)->None:
        if not cond:raise ScopeDrift(reason)
    need(p.get("schema")=="ZrotProductScopeLockV1","POLICY_SCHEMA")
    need(p.get("policy_id")==EXPECTED_POLICY_ID,"POLICY_ID")
    need(p.get("authority")=="USER_EXPLICIT_FINAL_PRODUCT_GOAL_CHANGE","POLICY_AUTHORITY")
    goal=p.get("final_product_goal",{})
    need(goal.get("research_product")=="GENERAL_ROTATION_OPENER_AND_CONDITIONAL_PRIORITY","GOAL_GENERAL_ROTATION")
    need(goal.get("opener")=="EXPLICIT_REQUIRED","GOAL_OPENER")
    need(set(goal.get("combat_contexts",[]))=={"SINGLE_TARGET","TWO_TARGET","CLEAVE","AOE","TARGET_COUNT_BREAKPOINTS"},"GOAL_TARGET_CONTEXTS")
    need(goal.get("training_product")=="LIGHTWEIGHT_TARGET_DUMMY_ROTATION_MISTAKE_FEEDBACK","GOAL_DUMMY")
    need(goal.get("training_mode_preference")=="OBSERVABILITY_FIRST_LIVE_IF_FEASIBLE_ELSE_POST_SESSION_COMBAT_LOG_ANALYSIS","GOAL_TRAINING_FALLBACK")
    need("ACTUAL_ACTION" in goal.get("training_result",""),"GOAL_FEEDBACK_CONTENT")
    need(p.get("research_execution_order")==EXPECTED_RESEARCH_ORDER,"RESEARCH_ORDER")
    g=p.get("research_guards",{})
    for name in ("SimC_first_hypothesis_bootstrap","WCL_blind_lock_before_SimC_semantic_answer_injection","SimC_counterfactual_optional_for_important_ambiguity","avoid_false_causal_priority_claims","cross_spec_generic_semantics_not_hardcoded"):
        need(g.get(name) is True,"GUARD_"+name)
    need(g.get("Strict_PRE_timestamp_rule")=="event_timestamp < decision_timestamp","STRICT_PRE")
    need(g.get("unobserved_readiness")=="UNKNOWN","UNKNOWN_READINESS")
    need(set(p.get("out_of_scope",[]))==EXPECTED_EXCLUDED,"EXCLUDED_OLD_SCOPE")
    support=p.get("permitted_support",{})
    for key in ("new_fresh_WCL_log_collection_is_engine_E2E_test","past_data_not_prerequisite","raid_reports_as_general_rotation_empirical_fixtures"):
        need(support.get(key) is True,"ENGINE_FIRST_"+key)
    limits=p.get("interface_limits",{})
    need(limits.get("actual_live_dummy_feedback_feasibility")=="UNVERIFIED_DEPENDS_ON_SUPPORTED_RETAIL_ADDON_API","ADDON_LIVE_UNPROVEN")
    need(limits.get("offline_combatlog_feedback_allowed") is True,"ADDON_POST_SESSION")
    need(limits.get("no_unobserved_state_as_known") is True,"ADDON_UNKNOWN")
    need(limits.get("no_restricted_or_secret_combat_value_bypass") is True,"ADDON_RESTRICTIONS")
    hand=p.get("handoff_rules",{})
    for name in ("required_on_every_handoff","carry_full_policy_object","carry_policy_sha256","carry_explicit_next_product_goal","carry_explicit_out_of_scope","carry_next_generation_integer","at_least_five_hop_simulation_required","no_silent_scope_override","explicit_user_new_policy_required_to_supersede"):
        need(hand.get(name) is True,"HANDOFF_RULE_"+name)
    need(p.get("promotion_policy")=="BRANCH_CAN_RECORD_USER_POLICY_AND_PROPOSE_MERGE; MAIN_ALONE_PROMOTES_SHARED_POINTERS","MAIN_PROMOTION_BOUNDARY")
    need(set(p.get("invariants",[]))=={"SEQ578_FAILED_QUARANTINED","SEQ637_UNKNOWN","FROZEN_EVIDENCE_NOT_REWRITTEN"},"FROZEN_INVARIANTS")

def pinned_lock()->tuple[dict,str,str]:
    b=LOCK_PATH.read_bytes()
    if git_blob_sha1(b)!=EXPECTED_BLOB_SHA1:
        raise ScopeDrift("POLICY_CONTENT_BYTES_CHANGED_WITHOUT_EXPLICIT_USER_VERSION_BUMP")
    if digest(b)!=EXPECTED_POLICY_SHA256:
        raise ScopeDrift("POLICY_SHA256_CHANGED_WITHOUT_EXPLICIT_USER_VERSION_BUMP")
    p=json.loads(b)
    assert_lock(p)
    return p,git_blob_sha1(b),digest(b)

def validate_entrypoints()->dict:
    markers={
      "README.md":["CURRENT USER-APPROVED PRODUCT GOAL","SimC APL/profile","target dummy","NSRT","docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md"],
      "AGENTS.md":["General Rotation + Dummy Trainer","OUT OF SCOPE","PRODUCT_SCOPE_LOCK_V1.json","validate_scope_continuity_v1.py"],
      "docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md":["ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1","General Rotation opener","target-dummy","NSRT","HANDOFF_CONTINUITY_PROTOCOL_V1.md"],
      "docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md":["PRODUCT_SCOPE_LOCK_V1.json","HANDOFF_CONTINUITY_PROTOCOL_V1.md","오프닝"],
      "docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md":["EVERY","policy_snapshot","five sequential","explicit user","MAIN"],
      "handoff/NEW_CHAT_BOOT_PROMPT.md":["SimC APL/profile","WCL","OPENER","OUT OF SCOPE","scope_continuity.policy_snapshot"],
    }
    for name,tokens in markers.items():
        t=(ROOT/name).read_text(encoding="utf-8")
        for token in tokens:
            if token not in t:raise ScopeDrift("ENTRYPOINT_MISSING_REQUIRED_MARKER:"+name+":"+token)
    return {"checked":len(markers),"read_first_policy":"PASS"}

def validate_handoff(h:dict,p:dict,blob:str,*,template:bool=False)->int:
    sc=h.get("scope_continuity")
    if not isinstance(sc,dict):raise ScopeDrift("NO_SCOPE_CONTINUITY")
    if sc.get("policy_id")!=EXPECTED_POLICY_ID:raise ScopeDrift("HANDOFF_POLICY_ID")
    if sc.get("policy_git_blob_sha1")!=blob:raise ScopeDrift("HANDOFF_POLICY_BLOB")
    if sc.get("policy_sha256")!=EXPECTED_POLICY_SHA256:raise ScopeDrift("HANDOFF_POLICY_SHA256")
    if sc.get("policy_snapshot")!=p:raise ScopeDrift("HANDOFF_POLICY_SNAPSHOT_DRIFT")
    if sc.get("scope_override") is not False or sc.get("new_user_scope_override_evidence") is not None:
        raise ScopeDrift("SILENT_USER_SCOPE_OVERRIDE")
    g=sc.get("generation")
    if isinstance(g,bool) or not isinstance(g,int) or g<0:raise ScopeDrift("HANDOFF_GENERATION")
    if g==0:
        if sc.get("parent_handoff_sha256") is not None:raise ScopeDrift("GEN_ZERO_UNEXPECTED_PARENT")
    else:
        hsh=sc.get("parent_handoff_sha256")
        if not isinstance(hsh,str) or len(hsh)!=64 or any(c not in "0123456789abcdef" for c in hsh):
            raise ScopeDrift("HANDOFF_MISSING_PARENT_FINGERPRINT")
    if sc.get("carried_forward_at") is None:raise ScopeDrift("MISSING_CARRY_TIMESTAMP")
    nxt=h.get("product_exact_next") or h.get("next_owner_exact_next")
    if not isinstance(nxt,str) or "General Rotation" not in nxt:
        raise ScopeDrift("PRODUCT_EXACT_NEXT_NOT_GENERAL_ROTATION")
    target=nxt.casefold()
    if "nsrt" in target or "encounter rotation plan" in target or "raid execution" in target or "raid timeline" in target:
        raise ScopeDrift("REINTRODUCED_OLD_PRODUCT_SCOPE")
    order=h.get("read_first",[])
    if not isinstance(order,list) or order[0]!="docs/PRODUCT_SCOPE_LOCK_V1.json":
        raise ScopeDrift("READ_FIRST_NOT_CURRENT_SCOPE")
    if h.get("shared_authoritative_state_mutated") is not False:
        raise ScopeDrift("IMPLICIT_SHARED_MAIN_PROMOTION")
    if h.get("project_wide_FROZEN_changed") is not False:
        raise ScopeDrift("IMPLICIT_FROZEN_CHANGE")
    return g

def next_handoff(parent:dict,raw_parent:bytes,p:dict,blob:str)->dict:
    generation=validate_handoff(parent,p,blob)
    new=deepcopy(parent)
    cont=new["scope_continuity"]
    cont["generation"]=generation+1
    cont["parent_handoff_sha256"]=digest(raw_parent)
    cont["carried_forward_at"]="2026-11-02"
    new["chat_exact_next"]="REPLACE_WITH_ACTUAL_NEXT_STEP_WHEN_THIS_IS_A_REAL_HANDOFF"
    # The product objective, policy, scope exclusions and verification state are NOT regenerated from a stale roadmap.
    return new

def verify_five_hops(parent:dict,p:dict,blob:str)->dict:
    current=deepcopy(parent)
    base=validate_handoff(current,p,blob)
    history=[]
    for i in range(1,6):
        previous_bytes=encoded(current)
        successor=next_handoff(current,previous_bytes,p,blob)
        generation=validate_handoff(successor,p,blob)
        if generation!=base+i:raise ScopeDrift("FIVE_HOP_GENERATION_DRIFT")
        if successor["scope_continuity"]["parent_handoff_sha256"]!=digest(previous_bytes):
            raise ScopeDrift("FIVE_HOP_PARENT_CHAIN_DRIFT")
        if successor["scope_continuity"]["policy_snapshot"]!=p:
            raise ScopeDrift("FIVE_HOP_SCOPE_DRIFT")
        history.append({"simulated_hop":i,"generation":generation,"scope":"PASS","parent_link":"PASS"})
        current=successor
    return {"result":"PASS","simulated_successor_hops":history,"actual_handoffs_created":0}

def negative_tests(p:dict,blob:str,current:dict)->int:
    cases=[]
    def mutant(callback):
        x=deepcopy(current)
        callback(x)
        cases.append(x)
    mutant(lambda x:x.pop("scope_continuity",None))
    mutant(lambda x:x["scope_continuity"].pop("policy_snapshot",None))
    mutant(lambda x:x["scope_continuity"]["policy_snapshot"]["final_product_goal"].update({"opener":"OPTIONAL"}))
    mutant(lambda x:x["scope_continuity"].update({"policy_id":"LEGACY_RAID_FIRST"}))
    mutant(lambda x:x["scope_continuity"].update({"policy_git_blob_sha1":"0"*40}))
    mutant(lambda x:x["scope_continuity"].update({"policy_sha256":"0"*64}))
    mutant(lambda x:x["scope_continuity"].update({"scope_override":True}))
    mutant(lambda x:x["scope_continuity"].update({"generation":-1}))
    mutant(lambda x:x.update({"product_exact_next":"Make NSRT raid execution guide"}))
    mutant(lambda x:x.update({"product_exact_next":"General Rotation then encounter rotation plan"}))
    mutant(lambda x:x.update({"shared_authoritative_state_mutated":True}))
    mutant(lambda x:x.update({"project_wide_FROZEN_changed":True}))
    mutant(lambda x:x.update({"read_first":["old_raid_handoff.json"]}))
    failures=0
    for x in cases:
        try:validate_handoff(x,p,blob)
        except ScopeDrift:failures+=1
        else:raise ScopeDrift("NEGATIVE_DRIFT_CASE_WAS_ACCEPTED")
    altered=deepcopy(p)
    altered["out_of_scope"].remove("NSRT_EXPORT")
    try:assert_lock(altered)
    except ScopeDrift:failures+=1
    else:raise ScopeDrift("UNAUTHORIZED_POLICY_MUTATION_WAS_ACCEPTED")
    return failures

def run(args)->dict:
    p,blob,sha256=pinned_lock()
    docs=validate_entrypoints()
    template=load(TEMPLATE)
    gen_template=validate_handoff(template,p,blob,template=True)
    active=load(Path(args.handoff) if args.handoff else ACTIVE)
    gen=validate_handoff(active,p,blob)
    out={"schema":"ZrotFiveHandoffScopeContinuityReceiptV1",
      "result":"PASS_SCOPE_CONTINUITY",
      "policy_id":EXPECTED_POLICY_ID,"policy_git_blob_sha1":blob,"policy_sha256":sha256,
      "active_real_generation":gen,"template_generation":gen_template,
      "documentation_entrypoints":docs,
      "product_scope":"GENERAL_ROTATION_OPENER_PRIORITY_AND_TARGET_DUMMY_FEEDBACK",
      "old_raid_NSRT_encounter_output_required":False,
      "real_WCL_SimC_WoW_client_calls":"NOT_RUN",
      "MAIN_pointer_modified":False,"FROZEN_modified":False}
    if args.self_test:
        out["negative_cases_passed"]=negative_tests(p,blob,active)
        out["five_hop_simulation"]=verify_five_hops(active,p,blob)
    if args.next_handoff:
        if not args.handoff:raise ScopeDrift("NEXT_HANDOFF_NEEDS_EXPLICIT_SOURCE_PATH")
        to=Path(args.next_handoff)
        if to.exists():raise ScopeDrift("DO_NOT_OVERWRITE_EXISTING_HANDOFF")
        child=next_handoff(active,Path(args.handoff).read_bytes(),p,blob)
        if to.parent:
            to.parent.mkdir(parents=True,exist_ok=True)
        to.write_bytes(encoded(child))
        out["new_handoff"]=str(to)
        out["new_handoff_generation"]=child["scope_continuity"]["generation"]
    return out

def main()->int:
    parser=argparse.ArgumentParser(description="Offline product-scope continuity gate; no live API")
    parser.add_argument("--validate",action="store_true")
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--handoff",type=str)
    parser.add_argument("--next-handoff",type=str)
    args=parser.parse_args()
    try:
        out=run(args)
        print(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except (ScopeDrift,ValueError,OSError,KeyError) as ex:
        print(json.dumps({"result":"FAIL_CLOSED","reason":str(ex)},ensure_ascii=False))
        return 2

if __name__=="__main__":
    sys.exit(main())
