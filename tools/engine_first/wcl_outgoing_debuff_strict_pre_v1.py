#!/usr/bin/env python3
"""Source-neutral, actor+target+spell scoped outgoing debuff Strict PRE.

Consumes exact archived WCL checkpoint pages and the verified event grain
audit. Never interprets spell names or assumes an unobserved debuff absent.
Pre-lock candidates are not re-learned. A WCL cast event is not manual input.
No args: safe synthetic regression. No WCL or SimC network calls.
"""
from __future__ import annotations
import argparse
from bisect import bisect_left
from collections import Counter,defaultdict
import json
from pathlib import Path
import zipfile
from wcl_raw_action_event_grain_audit_v1 import (
    audit, ability, canon, event_key, num, require, sha
)

SCHEMA="ZrotWclOutgoingDebuffStrictPreV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
KINDS={"applydebuff","refreshdebuff","removedebuff","applydebuffstack","removedebuffstack"}

def read_transitions(events, actor, start, fight):
    rows=[]; excluded=Counter()
    for eid,e in events:
        kind=e.get("type")
        if kind not in KINDS:continue
        if num(e.get("sourceID"))!=actor:
            excluded["OTHER_SOURCE"]+=1;continue
        target=num(e.get("targetID")); spell=ability(e)
        if target is None or target<=0 or spell is None or spell<=0:
            excluded["INVALID_TARGET_OR_SPELL"]+=1;continue
        require(e.get("fight")==fight,"FOREIGN_FIGHT_DEBUFF")
        t=e["timestamp"]-start
        require(type(t) is int and t>=0,"INVALID_DEBUFF_TIME")
        stack=e.get("stack",e.get("stacks"))
        if type(stack) is not int or stack<0:stack=None
        if kind=="removedebuff":active=False;stack=0
        elif kind=="removedebuffstack":active=stack>0 if stack is not None else None
        elif kind=="applydebuffstack" and stack==0:active=None
        else:active=True
        rows.append({"event_id":eid,"source_id":actor,"target_id":target,"spell_id":spell,
                     "t_ms":t,"kind":kind,"active":active,"explicit_stack":stack})
    require(len({r["event_id"] for r in rows})==len(rows),"DUPLICATE_DEBUFF_EVENT_ID")
    return rows,dict(sorted(excluded.items()))

def batch_state(batch):
    active={x["active"] for x in batch}
    stacks={x["explicit_stack"] for x in batch if x["explicit_stack"] is not None}
    a=next(iter(active)) if len(active)==1 and None not in active else None
    stack=next(iter(stacks)) if len(stacks)==1 and a is not None else None
    if a is False and stack not in (None,0):a=None;stack=None
    return {"status":"KNOWN_ACTIVE" if a is True else "KNOWN_INACTIVE" if a is False else "UNKNOWN_CONFLICT_OR_UNOBSERVED_STACK",
            "active":a,"explicit_stack":stack,"transition_t_ms":batch[0]["t_ms"],
            "source_event_ids":sorted(x["event_id"] for x in batch),
            "transition_types":sorted({x["kind"] for x in batch}),
            "remaining_ms":"UNKNOWN" if a is not False else 0}

def matrix(actions,transitions,actor):
    by_key=defaultdict(lambda:defaultdict(list))
    for r in transitions:
        require(r["source_id"]==actor,"FOREIGN_SOURCE_TRANSITION")
        by_key[(r["source_id"],r["target_id"],r["spell_id"])][r["t_ms"]].append(r)
    groups={k:(sorted(v),v) for k,v in by_key.items()}
    ids_by_target=defaultdict(list)
    for k in sorted(groups):ids_by_target[k[1]].append(k)
    out=[];counts=Counter()
    for a in sorted(actions,key=lambda x:(x["t_ms"],x["event_id"])):
        t=a["t_ms"]; target=a["target_id"]; facts={}
        # Observed ID vocabulary describes coverage only. Future transitions
        # cannot supply active/inactive, stack, expiry, or a target inference.
        for k in ids_by_target.get(target,[]):
            times,batches=groups[k]
            i=bisect_left(times,t)-1
            if i<0:
                f={"status":"UNKNOWN_NO_STRICT_PRIOR_TRANSITION","active":None,
                   "explicit_stack":None,"transition_t_ms":None,"source_event_ids":[],
                   "remaining_ms":"UNKNOWN"}
            else:
                f=batch_state(batches[times[i]])
                require(f["transition_t_ms"]<t,"SAME_TIME_OR_FUTURE_LEAK")
                f["observed_transition_age_ms"]=t-f["transition_t_ms"]
            counts[(a["event_type"],f["status"])]+=1
            facts[str(k[2])]=f
        out.append({"raw_action_event_id":a["event_id"],"event_type":a["event_type"],
                    "spell_id":a["spell_id"],"t_ms":t,"source_id":actor,"target_id":target,
                    "target_scope_status":"OBSERVED_NUMERIC_TARGET" if type(target) is int and target>0 else "UNKNOWN_TARGET",
                    "per_target_debuff":facts,"unlisted_debuff_state":"UNKNOWN",
                    "manual_player_input":"UNKNOWN","physical_READY":"UNKNOWN"})
    return out,{"|".join(k):v for k,v in sorted(counts.items())}

def produce(z,role):
    grain=audit(z,role)
    t=json.loads(z.read(f"results/{role}-numeric.json"))
    root=f"{role}/raw/{t['report_code']}/fight_{t['fight_id']}/"
    ck=json.loads(z.read(root+"checkpoint.json"))
    events=[]
    for p in ck["pages"]:
        raw=z.read(root+p["file"])
        require(sha(raw)==p["sha256"],"RAW_PAGE_TAMPERED")
        events.extend((event_key(p["sha256"],i,e),e) for i,e in enumerate(json.loads(raw)["events"]))
    rows,excluded=read_transitions(events,t["actor_id"],t["fight_start_abs_ms"],t["fight_id"])
    result,counts=matrix(grain["event_type_sidecar"],rows,t["actor_id"])
    return {"schema":SCHEMA,"policy_id":POLICY,"role":role.upper(),"report_code":t["report_code"],
            "fight_id":t["fight_id"],"actor_id":t["actor_id"],
            "source_raw_receipt_sha256":t["raw_receipt_sha256"],
            "source_raw_page_sha256":t["raw_source_page_sha256"],
            "source_numeric_transport_sha256":t["numeric_transport_sha256"],
            "action_events":len(result),"cast_events":grain["cast_event_count"],
            "begincast_events":grain["begincast_event_count"],
            "own_debuff_transitions":len(rows),"distinct_spell_ids":len({r["spell_id"] for r in rows}),
            "source_target_spell_keys":len({(r["source_id"],r["target_id"],r["spell_id"]) for r in rows}),
            "excluded":excluded,"strict_PRE_summary_by_event_type":counts,
            "transitions":sorted(rows,key=lambda r:(r["t_ms"],r["event_id"])),"per_action_event":result,
            "strict_timestamp_lt":True,"same_timestamp_not_used":True,"missing_debuff_not_inferred_absent":True,
            "active_remaining_time":"UNKNOWN_WITHOUT_EXPIRY","observed_target_count_is_not_active_enemy_count":True,
            "manual_player_input":"UNKNOWN","complete_READY":"UNKNOWN",
            "new_WCL_API_calls":0,"new_priority_rules_promoted":0,"MAIN_promoted":False}

def selftest():
    raw=[
      ("x",{"type":"applydebuff","sourceID":8,"targetID":20,"abilityGameID":77,"timestamp":10,"fight":1}),
      ("y",{"type":"applydebuff","sourceID":9,"targetID":20,"abilityGameID":77,"timestamp":11,"fight":1}),
      ("z",{"type":"applydebuff","sourceID":8,"targetID":21,"abilityGameID":77,"timestamp":12,"fight":1}),
      ("r",{"type":"removedebuff","sourceID":8,"targetID":20,"abilityGameID":77,"timestamp":20,"fight":1}),
      ("c",{"type":"applydebuff","sourceID":8,"targetID":20,"abilityGameID":77,"timestamp":30,"fight":1}),
      ("d",{"type":"removedebuff","sourceID":8,"targetID":20,"abilityGameID":77,"timestamp":30,"fight":1}),
    ]
    rows,excluded=read_transitions(raw,8,0,1)
    actions=[{"event_id":str(i),"event_type":"cast","spell_id":99,"target_id":target,"t_ms":t}
             for i,(target,t) in enumerate([(20,10),(20,20),(20,21),(21,21),(20,31),(22,31)])]
    output,_=matrix(actions,rows,8)
    f={r["raw_action_event_id"]:r["per_target_debuff"].get("77") for r in output}
    require(excluded["OTHER_SOURCE"]==1 and f["0"]["active"] is None and
            f["1"]["active"] is True and f["1"]["transition_t_ms"]==10 and
            f["2"]["active"] is False and f["3"]["active"] is True and
            f["4"]["active"] is None and f["5"] is None and
            f["1"]["remaining_ms"]=="UNKNOWN","SCOPE_OR_TIME_REGRESSION")
    return {"status":"PASS_SYNTHETIC_STATIC","checks":7,"new_WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip",type=Path);p.add_argument("--role",choices=("discovery","holdout"));p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    require(all(vars(a).values()),"ZIP_ROLE_OUTPUT_REQUIRED")
    with zipfile.ZipFile(a.zip) as z:result=produce(z,a.role)
    result["source_zip_sha256"]=sha(a.zip.read_bytes())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canon(result))
    print("DEBUFF_STRICT_PRE_SHA256="+sha(a.out.read_bytes()))
    print("DEBUFF_STRICT_PRE_SUMMARY",json.dumps({k:result[k] for k in ("role","action_events","own_debuff_transitions","distinct_spell_ids","source_target_spell_keys","strict_PRE_summary_by_event_type","excluded")},sort_keys=True))

if __name__=="__main__":main()
