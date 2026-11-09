#!/usr/bin/env python3
"""Source-neutral WCL aura event age/stack Strict PRE research transport.

Reuses the original verified actor transport and raw checkpoint/page ledger;
does not change the previous FROZEN Boolean actor transport or WCL blind lock.
Only real target-actor raw buff apply/refresh/remove/stack events enter this
producer. Known event time < cast time is mandatory. Same-time changes do NOT
affect a cast at that timestamp. Contradictory same-timestamp transitions
remain UNKNOWN, including stack. A raw event age is NOT the aura's remaining
duration. No WCL raw event establishes source action READY, GCD, cooldown,
game unit semantics, actual APL row or a dummy training mistake.

No CLI args: offline synthetic. Explicit raw actor root + numeric transport:
replay previously captured official raw pages, no API.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from hashlib import sha256
from itertools import groupby
import argparse
import json
import math
from pathlib import Path

from fresh_wcl_engine_v1 import checked_pages,canonical,sha,_ability,_aura_transition
from wcl_raw_actor_numeric_transport_v1 import (
    actor_snapshot,_check_transport,_as_relative_ms,_raw_event_id,
    read_json,RAW_SOURCE,POLICY
)

SCHEMA="ZrotWclActorAuraTemporalStrictPreV1"
AURA_TYPES=frozenset((
    "applybuff","refreshbuff","applybuffstack","removebuff","removebuffstack"))
AGE_KINDS=frozenset(("applybuff","refreshbuff"))

class TemporalError(ValueError):pass
def need(ok,tag):
    if not ok:raise TemporalError(tag)

def _stack_field(e:dict)->int|None:
    """Only a literal WCL stack number is evidence of an exact stack."""
    v=e.get("stack",e.get("stacks"))
    return v if type(v)==int and 0<=v<=100000 else None

def _events_to_rows(events:list,actor:int,start_ms:int,
                    raw_page_sha:str,raw_receipt_sha:str):
    """Original page+ordinal provenance; raw record gets no class labels."""
    result=[]
    for p_sha,page_events in events:
        for index,event in enumerate(page_events):
            need(type(event)==dict,"NON_OBJECT_WCL_SOURCE_EVENT")
            t=_as_relative_ms(event.get("timestamp"),start_ms)
            typ=str(event.get("type","")).casefold()
            if typ not in AURA_TYPES or event.get("targetID")!=actor:
                continue
            spell=_ability(event)
            if type(spell)!=int or spell<=0:continue
            transition=_aura_transition(event)
            need(transition is not None,"RAW_AURA_TRANSITION_REDUCER_DRIFT")
            active=transition["active"]
            need(type(active) is bool or active is None,
                 "NON_TRISTATE_RAW_AURA")
            stacks=_stack_field(event)
            if typ=="removebuff":stacks=0
            if typ=="applybuffstack" and stacks==0:
                # Some raw sources omit exact stack count; never convert an
                # explicit zero-stack apply into a positive stack witness.
                active=None
            result.append({
                "source_event_id":_raw_event_id(p_sha,index,event),
                "spell_id":spell,"t_ms":t,
                "event_type":typ,"active":active,
                "explicit_stack":stacks,
                "raw_receipt_sha256":raw_receipt_sha,
                "source_kind":RAW_SOURCE
            })
    result.sort(key=lambda x:(x["t_ms"],x["spell_id"],x["source_event_id"]))
    return result

def _reduce_timestamp_batch(batch:list)->dict:
    """No event-array-order interpretation at a shared WCL timestamp."""
    actives={e["active"] for e in batch}
    stacks={e["explicit_stack"] for e in batch if e["explicit_stack"] is not None}
    active=(next(iter(actives)) if len(actives)==1 and None not in actives
            else None)
    stack=(next(iter(stacks)) if len(stacks)==1 else None)
    if active is False and stack is not None and stack!=0:
        active=None;stack=None
    if active is None:stack=None
    types=sorted({e["event_type"] for e in batch})
    # Unknown stack is distinct from explicit 0 and must stay unknown.
    return {
       "status":"KNOWN_ACTIVE" if active is True else
                "KNOWN_INACTIVE" if active is False else
                "UNKNOWN_AMBIGUOUS_TIMESTAMP_TRANSITIONS",
       "active":active,"explicit_stack":stack,
       "raw_event_types":types,
       "source_event_ids":sorted(e["source_event_id"] for e in batch),
       "last_transition_t_ms":batch[0]["t_ms"],
       "last_application_or_refresh_t_ms":(
          batch[0]["t_ms"] if active is True and
          len(batch)==1 and batch[0]["event_type"] in AGE_KINDS else None),
       "last_observed_aura_event_age_is_not_remains":True,
       "aura_remaining_duration_ms":"UNKNOWN",
       "game_spell_and_source_buff_semantics":"UNKNOWN"
    }

def matrix_from_numeric_casts(transport:dict,rows:list)->dict:
    """Batched raw aura transitions, one source-neutral snapshot per cast."""
    _check_transport(transport)
    need(type(rows)==list and len(rows)<=100000,
         "BOUNDED_NUMERIC_AURA_ROWS_REQUIRED")
    ids=set();event_count=Counter();prior_count=Counter()
    for e in rows:
        need(type(e)==dict and
             type(e.get("source_event_id"))==str and
             e["source_event_id"] not in ids and
             type(e.get("spell_id"))==int and e["spell_id"]>0 and
             type(e.get("t_ms"))==int and e["t_ms"]>=0 and
             e.get("event_type") in AURA_TYPES and
             (e.get("active") is None or type(e["active"]) is bool) and
             (e.get("explicit_stack") is None or
              type(e["explicit_stack"])==int and
              0<=e["explicit_stack"]<=100000) and
             e.get("raw_receipt_sha256")==transport["raw_receipt_sha256"] and
             e.get("source_kind")==RAW_SOURCE,
             "RAW_AURA_EVENT_WRONG_ACTOR_SCHEMA_OR_PROVENANCE")
        ids.add(e["source_event_id"])
        event_count[e["event_type"]]+=1
    all_raw_aura_spell_ids={e["spell_id"] for e in rows}
    groups=[]
    for (_,spell),iterator in groupby(
        sorted(rows,key=lambda x:(x["t_ms"],x["spell_id"],
                                  x["source_event_id"])),
        key=lambda x:(x["t_ms"],x["spell_id"])):
        batch=list(iterator)
        groups.append((batch[0]["t_ms"],spell,_reduce_timestamp_batch(batch)))
    # Important: collect *all* spell groups of one timestamp before any
    # cast at that timestamp. Its effects apply to strictly later casts.
    groups.sort(key=lambda x:(x[0],x[1]))
    state={};cursor=0;output=[]
    for cast in transport["cast_events"]:
        t=cast["t_ms"]
        while cursor<len(groups) and groups[cursor][0]<t:
            event_t,spell,one=groups[cursor]
            state[spell]=one
            cursor+=1
        snapshot={}
        for spell,one in state.items():
            event_t=one["last_transition_t_ms"]
            need(type(event_t)==int and event_t<t,
                 "AURA_STATE_NOT_STRICT_PRIOR_TO_CAST")
            snap={
               **one,
               "last_observed_aura_event_age_ms":t-event_t,
               "explicit_stack_status":(
                 "EXACT_RAW_STACK_OBSERVED" if
                 one["explicit_stack"] is not None else
                 "UNKNOWN_NOT_EXPLICITLY_OBSERVED"),
               "aura_remaining_duration_ms":"UNKNOWN",
               "source_checkpoint_raw_receipt_sha256":
                  transport["raw_receipt_sha256"]
            }
            if one["last_application_or_refresh_t_ms"] is not None:
                snap["last_explicit_application_or_refresh_age_ms"]=(
                    t-one["last_application_or_refresh_t_ms"])
            else:
                snap["last_explicit_application_or_refresh_age_ms"]="UNKNOWN"
            if snap["explicit_stack_status"]=="EXACT_RAW_STACK_OBSERVED":
                prior_count["EXACT_RAW_STACK_PRE"]+=1
            else:prior_count["UNKNOWN_STACK_PRE"]+=1
            if snap["active"] is None:
                prior_count["UNKNOWN_AURA_ACTIVE_PRE"]+=1
            else:
                prior_count["KNOWN_AURA_ACTIVE_PRE"]+=1
            snapshot[str(spell)]=snap
        # The lack of any earlier raw event does NOT imply buff absence.
        # Account for every spell-ID ever seen in this bounded raw source,
        # including those with no preceding transition at the decision.
        prior_count["UNKNOWN_NO_PRIOR_AURA_EVENT"]+=(
            len(all_raw_aura_spell_ids)-len(snapshot))
        output.append({
           "numeric_raw_cast_event_id":cast["event_id"],
           "at_ms":t,"spell_id":cast["spell_id"],
           "per_numeric_aura_spell":dict(sorted(snapshot.items())),
           "aura_remaining_duration_for_any_spell":"UNKNOWN",
           "source_buff_semantics":"UNKNOWN",
           "complete_action_READY":"UNKNOWN",
           "dummy_wrong_cast":"UNKNOWN"
        })
    result={
      "schema":SCHEMA,"policy_id":POLICY,
      "source_numeric_transport_sha256":transport["numeric_transport_sha256"],
      "source_raw_receipt_sha256":transport["raw_receipt_sha256"],
      "source_raw_page_sha256":transport["raw_source_page_sha256"],
      "actual_cast_rows":len(output),
      "actor_raw_buff_event_type_counts":dict(sorted(event_count.items())),
      "target_actor_raw_buff_event_rows":len(rows),
      "distinct_raw_numeric_aura_spell_ids":len(all_raw_aura_spell_ids),
      "all_raw_aura_ID_x_cast_state_slots":
          len(all_raw_aura_spell_ids)*len(output),
      "strict_prior_raw_aura_observability":dict(sorted(prior_count.items())),
      "per_numeric_cast":output,
      "raw_stack_value_not_source_SimC_buff_stack_without_mechanic_binding":True,
      "raw_last_aura_event_age_never_promoted_to_remaining_duration":True,
      "aura_remains_known":0,
      "source_APl_condition_checked":False,
      "full_GCD_cooldown_charge_READY_proven":0,
      "mandatory_general_rotation_rule_promoted":False,
      "dummy_wrong_cast_proven":0,
      "new_WCL_API_calls":0,
      "MAIN_promoted":False
    }
    need(prior_count["KNOWN_AURA_ACTIVE_PRE"]+
         prior_count["UNKNOWN_AURA_ACTIVE_PRE"]+
         prior_count["UNKNOWN_NO_PRIOR_AURA_EVENT"]==
            result["all_raw_aura_ID_x_cast_state_slots"],
         "OPEN_WORLD_AURA_NO_PRIOR_STATE_COVERAGE_LOST")
    result["temporal_matrix_sha256"]=sha(canonical(result))
    return result

def from_verified_raw_actor_root(root:Path,transport:dict)->dict:
    """Independently regenerate original provenance before converting types."""
    _check_transport(transport)
    role=transport["source_cohort_role"]
    derived=root/"derived"
    named=(("selection.json","identity.json","blind_replay.json","receipt.json")
           if role=="DISCOVERY" else
           ("source_selection.json","identity_gate.json",
            "blind_holdout_replay.json","holdout_observed_metrics.json"))
    selection,gate,view,receipt=[read_json(derived/n) for n in named]
    need(selection.get("report_code")==transport["report_code"] and
         selection.get("fight_id")==transport["fight_id"] and
         gate.get("actor_id")==transport["actor_id"],
         "RAW_TEMPORAL_SOURCE_ACTOR_IDENTITY_DRIFT")
    folder=root/"raw"/selection["report_code"]/(
        "fight_"+str(selection["fight_id"]))
    replayed=actor_snapshot(folder,gate,view,receipt,source_role=role)
    need(replayed==transport,"ORIGINAL_RAW_ACTOR_TRANSPORT_NOT_REPRODUCIBLE")
    chk=read_json(folder/"checkpoint.json")
    page_rows=[]
    for meta in checked_pages(folder,chk):
        page=read_json(folder/meta["file"])
        need(sha(canonical(page))==meta["sha256"],
             "AURA_TEMPORAL_RAW_PAGE_SHA_DRIFT")
        page_rows.append((meta["sha256"],page["events"]))
    rows=_events_to_rows(
        page_rows,transport["actor_id"],transport["fight_start_abs_ms"],
        transport["raw_source_page_sha256"],transport["raw_receipt_sha256"])
    matrix=matrix_from_numeric_casts(transport,rows)
    need(matrix["actual_cast_rows"]==transport["actor_numeric_cast_count"],
         "AURA_PRE_ALL_CAST_ROWS_NOT_REPLAYED")
    return matrix

def selftest():
    from wcl_raw_actor_numeric_transport_v1 import SCHEMA as RAW_SCHEMA,ORIGIN
    def event(t,typ,sid,*,stacks=None,target=42):
        x={"timestamp":1000+t,"type":typ,"sourceID":24,
           "targetID":target,"abilityGameID":sid}
        if stacks is not None:x["stacks"]=stacks
        return x
    events=[
      event(100,"applybuff",81),event(200,"removebuff",81),
      event(350,"applybuffstack",81,stacks=3),
      event(500,"removebuff",81),event(500,"applybuffstack",81,stacks=2),
      event(600,"refreshbuff",81)
    ]
    casts=[{"event_id":f"c{i}","t_ms":t,"spell_id":900,
            "source_kind":RAW_SOURCE}
           for i,t in enumerate((50,200,300,400,550,650))]
    transport={
      "schema":RAW_SCHEMA,"policy_id":POLICY,"origin":ORIGIN,
      "source_cohort_role":"DISCOVERY",
      "prior_disjoint_report_holdout_recomputed":False,
      "report_code":"synthetic","fight_id":1,"actor_id":42,
      "raw_receipt_sha256":"c"*64,"raw_source_page_sha256":"d"*64,
      "actor_numeric_cast_count":len(casts),"cast_events":casts,
      "target_count_at_cast":"UNKNOWN","build_equivalent_to_SimC":"UNKNOWN",
      "independent_rank_or_holdout_proven":False,"source_gameplay_rule":"UNKNOWN"
    }
    transport["numeric_transport_sha256"]=sha(canonical(transport))
    rows=_events_to_rows([("e"*64,events)],42,1000,"d"*64,"c"*64)
    out=matrix_from_numeric_casts(transport,rows)
    one=[r["per_numeric_aura_spell"].get("81") for r in out["per_numeric_cast"]]
    need(out["strict_prior_raw_aura_observability"][
           "UNKNOWN_NO_PRIOR_AURA_EVENT"]==1 and
         out["all_raw_aura_ID_x_cast_state_slots"]==6 and
         one[0] is None and
         one[1]["active"] is True and one[1]["explicit_stack"] is None and
         one[2]["active"] is False and one[2]["explicit_stack"]==0 and
         one[3]["active"] is True and one[3]["explicit_stack"]==3 and
         one[4]["active"] is None and one[4]["explicit_stack"] is None and
         one[5]["active"] is True and
         one[5]["last_explicit_application_or_refresh_age_ms"]==50 and
         all(r["aura_remaining_duration_for_any_spell"]=="UNKNOWN"
             for r in out["per_numeric_cast"]),
         "AURA_TEMPORAL_STRICT_PRE_TRISTATE_OR_STACK_BROKEN")
    negatives=0
    def fail(x):
        nonlocal negatives
        try:x()
        except (TemporalError,ValueError):negatives+=1
        else:raise AssertionError("BAD_AURA_OR_EVENT_LEAK_ACCEPTED")
    b=json.loads(json.dumps(transport));b["cast_events"][1]["t_ms"]=150
    b["numeric_transport_sha256"]=sha(canonical({
        k:v for k,v in b.items() if k!="numeric_transport_sha256"}))
    # Any future-event row must still remain absent from its earlier cast.
    b_out=matrix_from_numeric_casts(b,rows)
    need(b_out["per_numeric_cast"][1]["per_numeric_aura_spell"]["81"][
         "last_transition_t_ms"]==100,
         "FUTURE_AURA_TRANSITION_LEAKED_INTO_PRE")
    b=json.loads(json.dumps(transport));b["numeric_transport_sha256"]="0"*64
    fail(lambda:matrix_from_numeric_casts(b,rows))
    tamper=json.loads(json.dumps(rows));tamper[0]["raw_receipt_sha256"]="0"*64
    fail(lambda:matrix_from_numeric_casts(transport,tamper))
    tamper=json.loads(json.dumps(rows));tamper[0]["explicit_stack"]=-1
    fail(lambda:matrix_from_numeric_casts(transport,tamper))
    need(negatives==3,"MISSING_REQUIRED_NEGATIVE_CONTROLS")
    return {
      "schema":SCHEMA,"status":"PASS_SOURCE_NEUTRAL_AURA_TEMPORAL_SYNTHETIC",
      "positive_raw_aura_events":len(rows),
      "casts":len(casts),"negative_controls":negatives,
      "same_timestamp_changes_not_PRE":True,
      "same_timestamp_contradictory_events_UNKNOWN":True,
      "explicit_numeric_stacks_not_guess_from_apply":True,
      "last_apply_or_refresh_age_not_remains":True,
      "no_prior_raw_event_not_interpreted_as_buff_absent":True,
      "source_APl_source_IF_proven":0,"full_READY_proven":0,
      "dummy_wrong_cast_proven":0,"new_WCL_API_calls":0
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor-root",type=Path)
    parser.add_argument("--raw-transport",type=Path)
    parser.add_argument("--out",type=Path)
    a=parser.parse_args()
    if all(v is None for v in vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(v is not None for v in vars(a).values()),
         "RAW_ACTOR_ROOT_TRANSPORT_AND_OUTPUT_REQUIRED")
    need(not a.out.exists(),"NO_OVERWRITE_SOURCE_EVIDENCE")
    transport=read_json(a.raw_transport)
    result=from_verified_raw_actor_root(a.actor_root,transport)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_bytes(canonical(result))
    print("WCL_RAW_AURA_TEMPORAL_STRICT_PRE_SHA256="+sha(a.out.read_bytes()))
    print("WCL_RAW_AURA_TEMPORAL_STATUS="+json.dumps({
      "actor_cast_rows":result["actual_cast_rows"],
      "raw_aura_event_types":result["actor_raw_buff_event_type_counts"],
      "explicit_stack_PRE":result["strict_prior_raw_aura_observability"].get(
         "EXACT_RAW_STACK_PRE",0),
      "unknown_stack_PRE":result["strict_prior_raw_aura_observability"].get(
         "UNKNOWN_STACK_PRE",0),
      "remaining_duration_verified":result["aura_remains_known"]
    },sort_keys=True))

if __name__=="__main__":main()
