#!/usr/bin/env python3
"""Generic original SimC create/init lifecycle -> same-root foreground audit.

Consume original source-pinned Native log, earlier certified membership JSON,
and the original APL profile. Only original same-actor, same-object,
same-source-signature, strictly ordered creation/initialization observations
can explain an excluded source row. Unobserved lifecycle or ambiguous flags
remain UNKNOWN. Constructor not-found classification cites the pinned original
action_t::action_t() guard, not an inferred ability/talent meaning.
No-args: synthetic fail-closed tests, safe without CLI parameters in PyCharm.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from general_rotation_original_attempt_frontier_v1 import (
    parse_markers, POLICY,REV,pointer,numeric
)
from general_rotation_original_runtime_membership_replay_v1 import (
    load_inventory,SCHEMA as MEMBERSHIP_SCHEMA,SOURCE_SCHEMA
)

SCHEMA="ZrotOriginalSimCActionLifecycleSourceBoundReplayV1"
MARK="ZROT_ORIGINAL_ACTION_LIFECYCLE_V1|"
PHASES=("POST_CREATE","POST_BIND","PRE_INIT","POST_INIT")

class LifecycleReplayError(ValueError):pass
def need(value,reason):
    if not value:raise LifecycleReplayError(reason)

def ptr(raw,allow_null=False):
    if allow_null and raw in ("(nil)","0x0","0x0000000000000000"):
        return "NULL"
    return pointer(raw)

def parse_lifecycle(log:str):
    out=[]
    for n,line in enumerate(log.splitlines()):
        if MARK not in line:continue
        need(line.count(MARK)==1,"DUPLICATE_LIFECYCLE_PREFIX")
        cells=line.split(MARK,1)[1].strip().split("|")
        need(len(cells)==10 and cells[0] in PHASES and
             all(c in ("0","1") for c in cells[4:]) ,
             "BAD_LIFECYCLE_SCHEMA_OR_BOOLEAN")
        phase,actor,action,src,bg,seq,notfound,nil,spellok,bound=cells
        source=ptr(src,allow_null=True)
        need(not (notfound=="1" and nil=="1") and
             not (notfound=="1" and spellok=="1") and
             (phase!="POST_CREATE" or source!="NULL") and
             (phase not in ("PRE_INIT","POST_INIT") or
              source=="NULL" or bound=="1"),
             "IMPOSSIBLE_LIFECYCLE_FLAGS_OR_SIGNATURE")
        out.append({"line":n,"phase":phase,"actor":ptr(actor),
                    "action_ptr":ptr(action),"source_ptr":source,
                    "background":bg=="1","sequence":seq=="1",
                    "not_found_spell_data":notfound=="1",
                    "nil_spell_data":nil=="1",
                    "spell_data_ok":spellok=="1",
                    "signature_bound":bound=="1"})
    need(out and len(out)<=50000,"EMPTY_OR_UNBOUNDED_NATIVE_LIFECYCLE")
    return out

def cause_for(phases,runtime):
    a=phases["POST_CREATE"];b=phases["POST_BIND"]
    c=phases["PRE_INIT"];d=phases["POST_INIT"]
    # Causal *sufficient* native constructor guard only when source-pinned
    # s_data pointer is not_found and background was already set on return
    # from create_action() before source skip and init.
    if a["not_found_spell_data"] and a["background"]:
        return "SOURCE_PINNED_CONSTRUCTOR_NOT_FOUND_SPELL_GUARD_OBSERVED"
    if not a["background"] and b["background"] and not b["signature_bound"]:
        return "SOURCE_ACTION_SKIP_OR_BIND_PHASE_BACKGROUND"
    if a["background"]:
        return "ALREADY_BACKGROUND_AT_POST_CREATE_CAUSE_UNKNOWN"
    if b["background"] and not a["background"]:
        return "BACKGROUND_CHANGED_AFTER_CREATE_BEFORE_SOURCE_BIND"
    if c["background"] and not b["background"]:
        return "BACKGROUND_CHANGED_BETWEEN_BIND_AND_INIT"
    if d["background"] and not c["background"]:
        return "BACKGROUND_CHANGED_DURING_ACTION_INIT_CAUSE_UNKNOWN"
    if runtime["background"]=="1" and not d["background"]:
        return "BACKGROUND_CHANGED_AFTER_ACTION_INIT_CAUSE_UNKNOWN"
    if runtime["background"]=="1":
        return "BACKGROUND_AT_FOREGROUND_SNAPSHOT_WITHOUT_OBSERVED_TRANSITION"
    return "NOT_BACKGROUND_AT_ORIGINAL_FOREGROUND_SNAPSHOT"

def audit(log:str,source:dict,membership:dict):
    need(source.get("schema")==SOURCE_SCHEMA and
         membership.get("schema")==MEMBERSHIP_SCHEMA and
         membership.get("policy_id")==POLICY and
         membership.get("source_revision")==REV and
         membership.get("selected_root_original_foreground_membership")=="PRESENT" and
         membership.get("General_Rotation_priority_promoted")==0 and
         membership.get("current_Retail_gameplay_ready")=="UNKNOWN",
         "SOURCE_OR_UPSTREAM_MEMBERSHIP_PROVENANCE_INVALID")
    begin,returned,_,_,_=parse_markers(log)
    chosen=membership["selected_root"]
    token=chosen["dispatch_token"]
    need(token in begin and token in returned,"ORIGINAL_FOREGROUND_ROOT_DISPATCH_MISSING")
    start=begin[token];stop=returned[token]
    need(start[0]<stop[0] and start[2]==stop[2] and
         start[1]==stop[1]==chosen["t_ms"],
         "SOURCE_ROOT_ACTOR_OR_TIME_MISMATCH")
    rows=source["action_lists"].get(chosen["source_list"])
    need(rows and chosen["source_rank"]<=len(rows) and
         rows[chosen["source_rank"]-1]["action"]==chosen["source_action"],
         "SOURCE_LIST_RANK_OR_ACTION_DRIFT")
    original_inventory=[x for x in load_inventory(log)
                        if start[0]<x["line"]<stop[0] and
                        x["actor"]==start[2] and
                        x["list"]==chosen["source_list"] and
                        x["t_ms"]==chosen["t_ms"]]
    n=len(rows)
    need(len(original_inventory)>=n,
         "MISSING_ORIGINAL_SOURCE_RUNTIME_FOREGROUND_INVENTORY")
    snap=original_inventory[-n:]
    need([x["rank"] for x in snap]==list(range(1,n+1)),
         "SOURCE_RUNTIME_INVENTORY_NOT_COMPLETE_ORDERED")
    prior=membership["same_root_upper_source_rows"]
    need(len(prior)==chosen["source_rank"]-1,
         "MISSING_SELECTED_ROOT_UPPER_SOURCE_EVIDENCE")
    all_events=parse_lifecycle(log)
    records=[]
    for rank,p in enumerate(prior,1):
        row=snap[rank-1]
        src=rows[rank-1]
        need(p["rank"]==rank and p["source_action"]==src["action"] and
             p["source_sha256"]==src["source_sha256"] and
             p["native_foreground_membership"]==row["foreground"] and
             p["native_background_flag"]==row["background"] and
             p["native_sequence_flag"]==row["sequence"],
             "PREVIOUS_MEMBERSHIP_NOT_SAME_ORIGINAL_ROW")
        item={"rank":rank,"source_action":src["action"],
              "source_sha256":src["source_sha256"],
              "runtime_membership_class":p["runtime_membership_class"],
              "observed_object_count":row["bound_count"],
              "same_root_visited":p["same_root_stage_visit"],
              "original_ready_return":p["original_action_ready_result"],
              "native_object_lifecycle":"UNKNOWN",
              "native_background_origin":"UNKNOWN",
              "native_spell_data_not_found_at_create":"UNKNOWN",
              "no_gameplay_ready_inferred":True}
        if not row["bound_count"]:
            need(not row["foreground"],"UNBOUND_SOURCE_ROW_MARKED_FOREGROUND")
            records.append(item);continue
        obj=[x for x in all_events if
             x["actor"]==start[2] and x["action_ptr"]==row["ptr"] and
             x["line"]<snap[0]["line"]]
        by_phase={p:[x for x in obj if x["phase"]==p] for p in PHASES}
        need(all(len(v)==1 for v in by_phase.values()),
             "MISSING_DUPLICATE_OR_CROSS_ACTOR_NATIVE_ACTION_LIFECYCLE")
        phase={k:v[0] for k,v in by_phase.items()}
        order=[phase[k]["line"] for k in PHASES]
        need(order==sorted(order) and len(set(order))==4,
             "FUTURE_OR_UNORDERED_NATIVE_ACTION_LIFECYCLE")
        create=phase["POST_CREATE"];bind=phase["POST_BIND"]
        before=phase["PRE_INIT"];after=phase["POST_INIT"]
        need(create["source_ptr"]==bind["source_ptr"] and
             bind["source_ptr"]==before["source_ptr"]==after["source_ptr"] and
             bind["signature_bound"] and before["signature_bound"] and
             after["signature_bound"],
             "SAME_OBJECT_ORIGINAL_SOURCE_SIGNATURE_DRIFT")
        need(after["background"] or not row["background"] or
             row["foreground"] is False,
             "NATIVE_BACKGROUND_CONTRADICTION")
        item["native_object_lifecycle"]="EXACT_SOURCE_SIGNATURE_FOUR_PHASES"
        item["native_spell_data_not_found_at_create"]=create["not_found_spell_data"]
        item["native_background_origin"]=cause_for(phase,row)
        item["native_flags_by_phase"]={
            name:{"background":x["background"],"sequence":x["sequence"],
                  "not_found":x["not_found_spell_data"],
                  "spell_data_ok":x["spell_data_ok"]}
            for name,x in phase.items()
        }
        item["instance_original_PTR_cohort_verified"]=True
        # It is valid for init_finished or class extensions to change flags
        # after POST_INIT. Do not call that a physical readiness verdict.
        records.append(item)
    absent=[x for x in records if x["same_root_visited"]=="UNOBSERVED"]
    return {
        "schema":SCHEMA,"policy_id":POLICY,"source_revision":REV,
        "source_spec":membership["source_spec"],"targets":membership["targets"],
        "selected_root":chosen,
        "original_source_to_runtime_membership_preserved":True,
        "same_actor_source_and_action_ptr_four_phase_join":True,
        "source_upper_rows_with_original_lifecycle":records,
        "unvisited_source_causal_guard_candidates":[{
             "rank":x["rank"],"action":x["source_action"],
             "native_background_origin":x["native_background_origin"],
             "native_spell_data_not_found_at_create":x["native_spell_data_not_found_at_create"]}
             for x in absent],
        "background_origin_counts":dict(Counter(x["native_background_origin"] for x in records)),
        "physical_skill_READY_independently_proven":0,
        "current_Retail_priority":"UNKNOWN",
        "WCL_independent_blind_postlock":"NOT_RUN",
        "dummy_wrong_cast":"UNKNOWN","opener_end":"UNKNOWN",
        "MAIN_promoted":False
    }

def selftest():
    from general_rotation_original_attempt_frontier_v1 import BEGIN,SELECT,PRE,EXTRA,RESULT
    from general_rotation_original_runtime_membership_replay_v1 import MARK as INV
    src=lambda name:{"action":name,"source_sha256":"sha-"+name}
    source={"schema":SOURCE_SCHEMA,"action_lists":{"sub":[src("alpha"),src("beta")]}}
    chosen={"t_ms":100,"call_id":10,"dispatch_token":1,
            "source_list":"sub","source_rank":2,"source_action":"beta",
            "native_action_ready_return":True}
    membership={"schema":MEMBERSHIP_SCHEMA,"policy_id":POLICY,"source_revision":REV,
        "selected_root":chosen,"selected_root_original_foreground_membership":"PRESENT",
        "General_Rotation_priority_promoted":0,
        "current_Retail_gameplay_ready":"UNKNOWN",
        "source_spec":"fictional","targets":1,
        "same_root_upper_source_rows":[{
          "rank":1,"source_action":"alpha","source_sha256":"sha-alpha",
          "native_foreground_membership":False,"native_background_flag":"1",
          "native_sequence_flag":"0","runtime_membership_class":"ABSENT_BACKGROUND_FLAG",
          "same_root_stage_visit":"UNOBSERVED",
          "original_action_ready_result":"NOT_CALLED"}]}
    def phase(name,bg,nf):
        return MARK+f"{name}|0x1|0xaa|0xabc|{int(bg)}|0|{int(nf)}|0|{0 if nf else 1}|{int(name!='POST_CREATE')}"
    ev=[phase("POST_CREATE",1,1),phase("POST_BIND",1,1),
        phase("PRE_INIT",1,1),phase("POST_INIT",1,1),
        BEGIN+"100|1|0x1",
        INV+"100|0x1|sub|1|0xaa|1|0|1|0",
        INV+"100|0x1|sub|2|0xbb|1|1|0|0",
        PRE+"100|10|sub|2|0xbb|0|0",
        EXTRA+"100|10|0xbb|"+"a"*64+"|1|1",
        RESULT+"100|10|0xbb|1",
        SELECT+"100|1|0x1|0xbb"]
    raw="\n".join(ev)
    result=audit(raw,source,membership)
    need(result["unvisited_source_causal_guard_candidates"]==[{
        "rank":1,"action":"alpha",
        "native_background_origin":"SOURCE_PINNED_CONSTRUCTOR_NOT_FOUND_SPELL_GUARD_OBSERVED",
        "native_spell_data_not_found_at_create":True}]
        and result["physical_skill_READY_independently_proven"]==0,
        "ORIGINAL_NOT_FOUND_GUARD_NOT_LINKED")
    invalid=[
        raw.replace("|0xaa|0xabc|","|0xab|0xabc|"),
        raw.replace("POST_BIND|","MALFORMED|"),
        raw.replace("POST_CREATE|","POST_INIT|"),
        raw.replace("POST_CREATE|0x1|0xaa|0xabc|1|0|1|0|0|0",
                    "POST_CREATE|0x1|0xaa|0xabc|1|0|1|0|1|0"),
        raw.replace("0xabc","0xabd",1),
        raw.replace("POST_INIT|0x1|0xaa","POST_INIT|0x2|0xaa"),
        raw.replace(INV+"100|0x1|sub|1|0xaa|1|0|1|0",
                    INV+"100|0x1|sub|1|0xbb|1|0|1|0")
    ]
    rejected=0
    for bad in invalid:
        try:audit(bad,source,membership)
        except (LifecycleReplayError,ValueError):rejected+=1
        else:raise AssertionError("ACCEPTED_FOREIGN_OR_MISSING_NATIVE_CREATION")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls":rejected,
            "native_constructor_not_found_guard_synthetic":True,
            "physical_READY_proven":0,"WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--profile",type=Path)
    p.add_argument("--prior-membership",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(vars(a).values()),"PINNED_LIFECYCLE_INPUTS_REQUIRED")
    from simc_apl_semantic_ir_v2 import parse_profile, canonical,git_blob
    prior_raw=a.prior_membership.read_bytes()
    prior=json.loads(prior_raw);raw=a.profile.read_bytes()
    need(git_blob(raw)==prior.get("source_profile_git_blob"),
         "SOURCE_PROFILE_NOT_PINNED_TO_PRIOR_NATIVE_SNAPSHOT")
    result=audit(a.native_log.read_text("utf-8"),parse_profile(raw,require_source=False),prior)
    result["prior_membership_sha256"]=sha256(prior_raw).hexdigest()
    result["source_profile_git_blob"]=prior["source_profile_git_blob"]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canonical(result))
    print("ORIGINAL_ACTION_LIFECYCLE_REPLAY_SHA256="+sha256(a.out.read_bytes()).hexdigest())
    print("ORIGINAL_ACTION_LIFECYCLE_REPLAY_COUNTS="+json.dumps({
        "targets":result["targets"],
        "background_origin_counts":result["background_origin_counts"],
        "unvisited":result["unvisited_source_causal_guard_candidates"]},sort_keys=True))

if __name__=="__main__":main()
