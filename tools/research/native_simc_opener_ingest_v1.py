#!/usr/bin/env python3
"""Provenance-bounded parser of NATIVE SimulationCraft performed-action logs.

SimC source contract (pinned upstream):
  engine/action/action.cpp action_t::execute(): "{} performs {} ({})"
  engine/sim/sim_ostream.cpp: "{:.3f} " prefix from simulation time.

Never interpret an APL line or an action log as a ready-for-player spell,
optimal priority, a fully proven opener, or a combat-log readiness state.
No user-specific character identity is inferred.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

PERFORMS=re.compile(
    r"^\s*(?P<time>-?\d+(?:\.\d+)?)\s+(?P<actor>\S+)\s+"
    r"performs\s+(?P<action>.+?)\s+\((?P<primary_resource>[^()]*)\)\s*$"
)

class NativeLogError(ValueError): pass

def extract(log_data:bytes,*,actor_filter:str,source_commit:str,
            profile_blob_sha1:str,seed:int,window_seconds:float=15.0)->dict:
    if not log_data or len(log_data)>64*1024*1024:
        raise NativeLogError("BOUNDED_NONEMPTY_NATIVE_LOG_REQUIRED")
    if not actor_filter or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}",actor_filter):
        raise NativeLogError("PINNED_ACTOR_NAME_REQUIRED")
    if not re.fullmatch(r"[0-9a-f]{40}",source_commit):
        raise NativeLogError("UPSTREAM_COMMIT_REQUIRED")
    if not re.fullmatch(r"[0-9a-f]{40}",profile_blob_sha1):
        raise NativeLogError("PROFILE_GIT_BLOB_REQUIRED")
    if isinstance(seed,bool) or not isinstance(seed,int) or seed<=0:
        raise NativeLogError("FIXED_POSITIVE_SEED_REQUIRED")
    if not 0<window_seconds<=120:
        raise NativeLogError("INVALID_OBSERVATION_WINDOW")
    raw_lines=log_data.decode("utf-8",errors="replace").splitlines()
    performed=[]
    all_actors=set()
    first_actor_events=0
    prior=None
    for line_n,line in enumerate(raw_lines,1):
        m=PERFORMS.match(line)
        if m is None:
            continue
        all_actors.add(m["actor"])
        if m["actor"]!=actor_filter:
            continue
        first_actor_events+=1
        t=float(m["time"])
        if prior is not None and t<prior:
            raise NativeLogError("ACTOR_ACTION_TIME_BACKWARDS")
        prior=t
        performed.append({
            "source_line":line_n,
            "simulation_time_s":t,
            "actor":m["actor"],
            "action_as_logged":m["action"],
            "primary_resource_display":m["primary_resource"],
            "evidence_type":"SIMC_NATIVE_ACTION_EXECUTED",
            "cooldown_or_spell_ready_at_WCL_time":"UNKNOWN",
            "player_action_optimality":"NOT_ESTABLISHED"
        })
    precombat=[v for v in performed if v["simulation_time_s"]<0]
    opening=[v for v in performed if 0<=v["simulation_time_s"]<window_seconds]
    post=[v for v in performed if v["simulation_time_s"]>=window_seconds]
    return {
      "schema":"ZrotNativeSimcObservedActionWindowV1",
      "scope_policy_id":"ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
      "native_log_sha256":hashlib.sha256(log_data).hexdigest(),
      "native_source_commit":source_commit,
      "profile_git_blob_sha1":profile_blob_sha1,
      "actor_filter":actor_filter,
      "seed":seed,
      "observed_performs_event_count":len(performed),
      "recorded_other_actors_count":len(all_actors-{actor_filter}),
      "precombat_action_count":len(precombat),
      "observed_opening_window_seconds":window_seconds,
      "opening_window_actions":opening,
      "post_window_performed_action_count":len(post),
      "observed_log_actor_found":first_actor_events>0,
      "combat_opener_automatically_proven":False,
      "opening_window_is_observation_not_optimized_sequence":True,
      "precombat_not_conflated_with_opening_window":True,
      "numeric_spell_id_verified":False,
      "cooldown_readiness_reconstructed":False,
      "actual_WCL_ranker_comparison":"NOT_RUN",
      "actual_Blizzard_mechanic_check":"NOT_RUN",
      "player_facing_general_rotation_rule_ready":False,
      "training_dummy_error_evaluation_eligible":False,
    }

def self_test()->dict:
    line=(
      b"-0.500 Fury_Alpha performs pre_spell (100)\n"
      b"0.000 Fury_Alpha performs recklessness (100)\n"
      b"0.000 Fury_Alpha schedules execute for bladestorm\n"
      b"0.000 Fury_Alpha performs rampage (80)\n"
      b"0.000 Some_Pet performs bite (0)\n"
      b"1.500 Fury_Alpha performs raging_blow (55)\n"
      b"14.999 Fury_Alpha performs bloodthirst (80)\n"
      b"15.000 Fury_Alpha performs execute (20)\n"
      b"16.000 Fury_Alpha consumes 5 rage for execute (15)\n"
    )
    keys=dict(actor_filter="Fury_Alpha",source_commit="a"*40,
              profile_blob_sha1="b"*40,seed=31459)
    r=extract(line,**keys)
    count=0
    def check(v):
        nonlocal count
        assert v
        count+=1
    check(r["observed_performs_event_count"]==6)
    check(r["precombat_action_count"]==1)
    check(len(r["opening_window_actions"])==4)
    check([x["action_as_logged"] for x in r["opening_window_actions"]]
          ==["recklessness","rampage","raging_blow","bloodthirst"])
    check(r["post_window_performed_action_count"]==1)
    check(r["recorded_other_actors_count"]==1)
    check(r["opening_window_actions"][0]["simulation_time_s"]==0)
    check(r["opening_window_actions"][0]["primary_resource_display"]=="100")
    check(r["numeric_spell_id_verified"] is False)
    check(r["cooldown_readiness_reconstructed"] is False)
    check(r["combat_opener_automatically_proven"] is False)
    check(r["actual_WCL_ranker_comparison"]=="NOT_RUN")
    check(r["player_facing_general_rotation_rule_ready"] is False)
    check(r["training_dummy_error_evaluation_eligible"] is False)
    check(r["native_log_sha256"]==hashlib.sha256(line).hexdigest())
    cases=[
       (dict(actor_filter=""),"PINNED_ACTOR"),
       (dict(source_commit="deadbeef"),"UPSTREAM_COMMIT"),
       (dict(profile_blob_sha1="xyz"),"PROFILE_GIT_BLOB"),
       (dict(seed=0),"FIXED_POSITIVE_SEED"),
       (dict(window_seconds=0),"INVALID_OBSERVATION_WINDOW"),
    ]
    for update,label in cases:
        kw={**keys,**update}
        if "window_seconds" in kw:
            win=kw.pop("window_seconds")
        else:win=15.
        try:extract(line,**kw,window_seconds=win)
        except NativeLogError as e:check(label in str(e))
        else:raise AssertionError("NEGATIVE_REJECT_FAILED_"+label)
    unordered=b"2.000 Fury_Alpha performs alpha (20)\n1.000 Fury_Alpha performs beta (20)\n"
    try:extract(unordered,**keys)
    except NativeLogError as e:check("BACKWARDS" in str(e))
    else:raise AssertionError("BACKWARD_LOG_ACCEPTED")
    return {"result":"PASS","case_count":count,
            "native_SimC_executable_ran":"NO_SYNTHETIC_ONLY",
            "real_WCL_SimC_Blizzard_live":"NOT_RUN",
            "no_unobserved_readiness_inferred":True}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--log-file",type=Path)
    ap.add_argument("--actor")
    ap.add_argument("--source-commit")
    ap.add_argument("--profile-git-blob")
    ap.add_argument("--seed",type=int,default=31459)
    ap.add_argument("--window-seconds",type=float,default=15.0)
    ap.add_argument("--out",type=Path)
    x=ap.parse_args()
    if x.self_test or not x.log_file and not x.actor and not x.source_commit and not x.profile_git_blob:
        result=self_test()
    else:
        if not all((x.log_file,x.actor,x.source_commit,x.profile_git_blob)):
            ap.error("--log-file, --actor, --source-commit and --profile-git-blob required together")
        result=extract(x.log_file.read_bytes(),actor_filter=x.actor,
                       source_commit=x.source_commit,profile_blob_sha1=x.profile_git_blob,
                       seed=x.seed,window_seconds=x.window_seconds)
    output=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if x.out:
        x.out.parent.mkdir(parents=True,exist_ok=True)
        x.out.write_text(output,encoding="utf-8")
        print("WROTE_NATIVE_SIMC_OBSERVATION_WITH_NONPROMOTION_GATES")
    else:print(output,end="")

if __name__=="__main__":
    main()
