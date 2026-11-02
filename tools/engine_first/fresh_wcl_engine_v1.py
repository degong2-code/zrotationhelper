#!/usr/bin/env python3
"""zRotationHelper — fresh-data ingestion / snapshot / strict-PRE replay MVP.

Default is an offline self-test; LIVE OAuth collection requires explicit `collect`.
No legacy MAIN/Inbox imports. Built-in standard library only.
A deliberately incomplete engine slice: no SimC, ranking or gameplay priority claim.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Callable
from urllib import request, error
import base64

TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
GRAPHQL_URL = "https://www.warcraftlogs.com/api/v2/client"
REPORT_RE = re.compile(r"^[A-Za-z0-9]{6,40}$")
META_QUERY = """query FreshReport($code:String!, $fight:Int!){
  reportData { report(code:$code) { code revision
    fights(fightIDs:[$fight],translate:false) {
      id startTime endTime encounterID difficulty inProgress
    }
  } }
}"""
EVENTS_QUERY = """query FreshEvents($code:String!, $fight:Int!, $start:Float!, $end:Float!){
  reportData { report(code:$code) {
    events(fightIDs:[$fight],startTime:$start,endTime:$end,limit:10000,
           translate:false,useAbilityIDs:true,useActorIDs:true,includeResources:true) {
      data nextPageTimestamp
    }
  } }
}"""

class EngineError(Exception):
    """Fail-closed collection or replay contract error."""


def canonical(obj:Any)->bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)+"\n").encode("utf-8")


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def write_atomic(path:Path, data:bytes)->None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Temporary file and replace in the same directory; never write credentials.
    fd,tmp=tempfile.mkstemp(prefix=".fresh_",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def parse_dotenv(path:Path)->dict[str,str]:
    data={}
    if not path.is_file():return data
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line=line.strip()
        if not line or line.startswith("#") or "=" not in line:continue
        k,v=line.split("=",1)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",k.strip()):continue
        v=v.strip()
        if len(v)>1 and v[0] in "\"'" and v[-1]==v[0]:v=v[1:-1]
        data[k.strip()]=v
    return data


def credentials(env_path:Path|None)->tuple[str,str]:
    # No recursive filesystem probing; explicit --env, local .env, repo parent .env.
    paths=[env_path] if env_path else [Path.cwd()/".env",Path(__file__).resolve().parent/".env",Path(__file__).resolve().parent.parent/".env"]
    loaded={}
    for p in paths:
        if p is not None and p.is_file():
            loaded=parse_dotenv(p)
            break
    merged={**loaded,**os.environ}
    key=merged.get("WCL_CLIENT_ID") or merged.get("WCL_ID")
    secret=merged.get("WCL_CLIENT_SECRET") or merged.get("WCL_SECRET")
    if not key or not secret:raise EngineError("WCL_CREDENTIALS_MISSING__NO_NETWORK_CALL")
    return key,secret


def oauth_token(client_id:str,client_secret:str)->str:
    basic=base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req=request.Request(TOKEN_URL,data=b"grant_type=client_credentials",method="POST",headers={
        "Authorization":"Basic "+basic,"Content-Type":"application/x-www-form-urlencoded"})
    try:
        with request.urlopen(req,timeout=25) as res:obj=json.load(res)
        token=obj.get("access_token")
        if not isinstance(token,str) or not token:raise EngineError("OAUTH_NO_ACCESS_TOKEN")
        return token
    except (error.URLError,ValueError,KeyError) as exc:
        raise EngineError("OAUTH_REQUEST_FAILED__CREDENTIALS_REDACTED") from exc


def official_graphql(token:str,query:str,variables:dict)->dict:
    payload=canonical({"query":query,"variables":variables})
    req=request.Request(GRAPHQL_URL,data=payload,method="POST",headers={
        "Authorization":"Bearer "+token,"Content-Type":"application/json"})
    try:
        with request.urlopen(req,timeout=60) as res:obj=json.load(res)
    except (error.URLError,ValueError,KeyError) as exc:
        raise EngineError("WCL_GRAPHQL_REQUEST_FAILED__TOKEN_REDACTED") from exc
    if not isinstance(obj,dict) or obj.get("errors") or not isinstance(obj.get("data"),dict):
        raise EngineError("WCL_GRAPHQL_ERRORS_OR_MISSING_DATA__NO_PARTIAL_COMMIT")
    return obj["data"]


def _report(data:dict)->dict:
    r=(data.get("reportData") or {}).get("report")
    if not isinstance(r,dict):raise EngineError("WCL_REPORT_UNAVAILABLE_OR_SCHEMA_MISMATCH")
    return r


def validate_report(code:str,fight:int,report:dict)->dict:
    if report.get("code")!=code:raise EngineError("WCL_REPORT_CODE_MISMATCH")
    fights=report.get("fights")
    if not isinstance(fights,list):raise EngineError("WCL_FIGHTS_MISSING")
    found=[f for f in fights if isinstance(f,dict) and f.get("id")==fight]
    if len(found)!=1:raise EngineError("FIGHT_ID_NOT_UNIQUE_OR_MISSING")
    f=found[0]
    start,end=f.get("startTime"),f.get("endTime")
    if (not isinstance(start,(int,float)) or isinstance(start,bool) or
        not isinstance(end,(int,float)) or isinstance(end,bool) or start>=end):
        raise EngineError("FIGHT_TIME_INVALID")
    if f.get("inProgress") is True:raise EngineError("FIGHT_STILL_IN_PROGRESS")
    rev=report.get("revision")
    if not isinstance(rev,int) or isinstance(rev,bool):raise EngineError("REPORT_REVISION_MISSING")
    return {"report_code":code,"fight_id":fight,"revision":rev,"start":start,"end":end,
            "encounter_id":f.get("encounterID"),"difficulty":f.get("difficulty")}


def checked_pages(folder:Path,state:dict)->list[dict]:
    seen=set()
    pages=state.get("pages")
    if not isinstance(pages,list):raise EngineError("INVALID_PAGE_LEDGER")
    for i,page in enumerate(pages):
        if page.get("file")!=f"page_{i:05d}.json":raise EngineError("LEDGER_PAGE_NAME_MISMATCH")
        p=folder/page["file"]
        if not p.is_file() or p.is_symlink():raise EngineError("PAGE_MISSING_OR_SYMLINK")
        b=p.read_bytes()
        if sha(b)!=page.get("sha256"):raise EngineError("PAGE_TAMPERED")
        obj=json.loads(b)
        if obj.get("schema")!="FreshWCLPageV1" or obj.get("start")!=page.get("start"):
            raise EngineError("PAGE_PAYLOAD_MISMATCH")
        if obj.get("next")!=page.get("next") or len(obj.get("events",[]))!=page.get("event_count"):
            raise EngineError("PAGE_LEDGER_PAYLOAD_DIVERGED")
        if page["file"] in seen:raise EngineError("DUPLICATE_LEDGER_PAGE")
        seen.add(page["file"])
    physical={p.name for p in folder.glob("page_*.json")}
    if physical!=seen:raise EngineError("UNCOMMITTED_OR_MISSING_PAGE__REVIEW_REQUIRED")
    return pages



def recover_orphan_page(folder:Path,state:dict)->bool:
    """Adopt one fully committed page after crash before checkpoint replace.

    Do not silently truncate/ignore unknown or damaged files; fail closed.
    """
    if state["complete"]:return False
    expected=folder/f"page_{len(state['pages']):05d}.json"
    if not expected.is_file() or expected.is_symlink():return False
    b=expected.read_bytes()
    try:obj=json.loads(b)
    except (ValueError,UnicodeError) as exc:raise EngineError("ORPHAN_PAGE_UNREADABLE") from exc
    cursor=state["cursor"]
    nxt=obj.get("next")
    evs=obj.get("events")
    end=state["identity"]["end"]
    if (obj.get("schema")!="FreshWCLPageV1" or obj.get("start")!=cursor or
        not isinstance(evs,list) or
        (nxt is not None and (not isinstance(nxt,(int,float)) or nxt<=cursor or nxt>end))):
        raise EngineError("ORPHAN_PAGE_INVALID__DO_NOT_REQUERY")
    if nxt is not None and not evs:raise EngineError("ORPHAN_EMPTY_NONTERMINAL_PAGE")
    if any(not isinstance(e,dict) or not isinstance(e.get("timestamp"),(int,float)) or
           not cursor<=e["timestamp"]<=end for e in evs):
        raise EngineError("ORPHAN_EVENT_OUTSIDE_WINDOW")
    name=expected.name
    state["pages"].append({"file":name,"sha256":sha(b),"start":cursor,
                           "next":nxt,"event_count":len(evs)})
    state["cursor"]=nxt
    state["complete"]=nxt is None
    write_atomic(folder/"checkpoint.json",canonical(state))
    return True


def collect(query:Callable[[str,dict],dict],code:str,fight:int,out:Path,max_pages:int=100,*,window_ms:int|None=None)->dict:
    if not REPORT_RE.fullmatch(code) or not isinstance(fight,int) or fight<=0:
        raise EngineError("REPORT_OR_FIGHT_ID_INVALID")
    if not 1<=max_pages<=1000:raise EngineError("MAX_PAGES_OUT_OF_RANGE")
    folder=out/code/f"fight_{fight}"
    info=validate_report(code,fight,_report(query(META_QUERY,{"code":code,"fight":fight})))
    if window_ms is not None:
        if type(window_ms) is not int or not 1000<=window_ms<=60000:
            raise EngineError("INVALID_BOUNDED_OPENER_WINDOW")
        full_end=info["end"]
        info={**info,"full_fight_end":full_end,
              "end":min(full_end,info["start"]+window_ms),
              "requested_window_ms":window_ms,
              "evidence_window":"FIGHT_START_BOUNDED"}
    state_path=folder/"checkpoint.json"
    if state_path.is_file():
        state=json.loads(state_path.read_bytes())
        if state.get("schema")!="FreshWCLCheckpointV1" or state.get("identity")!=info:
            raise EngineError("SNAPSHOT_IDENTITY_OR_REVISION_CHANGED__START_NEW_SNAPSHOT")
    else:
        if folder.exists() and list(folder.iterdir()):raise EngineError("UNTRACKED_DIRECTORY_CONTENT")
        state={"schema":"FreshWCLCheckpointV1","identity":info,"cursor":info["start"],
               "pages":[],"complete":False}
    # Verify committed prefix, then recover a single crash-safe orphan page.
    # If there is more than one orphan or any mismatch, stop without network calls.
    committed={p.get("file") for p in state.get("pages",[])}
    physical={p.name for p in folder.glob("page_*.json")}
    orphan=physical-committed
    if orphan:
        expected_name=f"page_{len(state['pages']):05d}.json"
        if orphan!={expected_name}:
            raise EngineError("UNEXPECTED_UNCOMMITTED_PAGE_SET")
        recover_orphan_page(folder,state)
    checked_pages(folder,state)
    for _ in range(max_pages):
        if state["complete"]:break
        cursor=state["cursor"]
        data=query(EVENTS_QUERY,{"code":code,"fight":fight,"start":cursor,"end":info["end"]})
        paginator=_report(data).get("events")
        if not isinstance(paginator,dict) or not isinstance(paginator.get("data"),list):
            raise EngineError("WCL_EVENTS_SCHEMA_MISSING")
        evs=paginator["data"]
        nxt=paginator.get("nextPageTimestamp")
        if nxt is not None and (not isinstance(nxt,(int,float)) or isinstance(nxt,bool) or nxt<=cursor or nxt>info["end"]):
            raise EngineError("NON_MONOTONIC_OR_OUT_OF_RANGE_PAGE_CURSOR")
        if nxt is not None and not evs:raise EngineError("EMPTY_PAGE_WITH_NEXT_CURSOR")
        for e in evs:
            if not isinstance(e,dict) or not isinstance(e.get("timestamp"),(int,float)) or isinstance(e.get("timestamp"),bool):
                raise EngineError("EVENT_IDENTITY_OR_TIMESTAMP_UNOBSERVED")
            if e["timestamp"]<cursor or e["timestamp"]>info["end"]:
                raise EngineError("EVENT_OUTSIDE_REQUEST_WINDOW")
        name=f"page_{len(state['pages']):05d}.json"
        obj={"schema":"FreshWCLPageV1","start":cursor,"next":nxt,"events":evs}
        write_atomic(folder/name,canonical(obj))
        state["pages"].append({"file":name,"sha256":sha(canonical(obj)),"start":cursor,
                               "next":nxt,"event_count":len(evs)})
        state["cursor"]=nxt
        state["complete"]=nxt is None
        write_atomic(state_path,canonical(state))
    return {"status":("COMPLETE_WINDOW" if window_ms is not None else "COMPLETE")
            if state["complete"] else "PARTIAL", "pages":len(state["pages"]),
            "events":sum(x["event_count"] for x in state["pages"]), "identity":info,
            "checkpoint":str(state_path),"live_api_invoked":"INJECTED_TRANSPORT"}


def _num(value:Any)->int|None:
    if isinstance(value,bool):return None
    if isinstance(value,int):return value
    if isinstance(value,str) and value.strip().lstrip("-").isdigit():return int(value)
    return None


def _ability(event:dict)->int|None:
    for key in ("abilityGameID","abilityID","guid"):
        n=_num(event.get(key))
        if n is not None:return n
    a=event.get("ability")
    if isinstance(a,dict):
        for key in ("gameID","guid","id"):
            n=_num(a.get(key))
            if n is not None:return n
    return None


def _aura_transition(e:dict)->dict|None:
    typ=str(e.get("type","")).casefold()
    stacks=_num(e.get("stack"))
    if stacks is None:stacks=_num(e.get("stacks"))
    if typ in ("applybuff","refreshbuff","applybuffstack"):
        return {"active":True,"stacks":stacks if stacks is not None and stacks>0 else None}
    if typ=="removebuff":return {"active":False,"stacks":0}
    if typ=="removebuffstack":
        # Explicit zero is an observed remove; missing stacks remain UNKNOWN.
        return ({"active":stacks>0,"stacks":max(stacks,0)} if stacks is not None else
                {"active":None,"stacks":None})
    return None


def replay(folder:Path)->dict:
    checkpoint=folder/"checkpoint.json"
    if not checkpoint.is_file():raise EngineError("CHECKPOINT_NOT_FOUND")
    state=json.loads(checkpoint.read_bytes())
    if not state.get("complete"):raise EngineError("INCOMPLETE_SNAPSHOT__NO_REPLAY")
    pages=checked_pages(folder,state)
    events=[]
    for p in pages:events.extend(json.loads((folder/p["file"]).read_bytes())["events"])
    for i,e in enumerate(events):
        if not isinstance(e,dict) or not isinstance(e.get("timestamp"),(int,float)):
            raise EngineError("EVENT_NOT_REPLAYABLE")
        if e["timestamp"]<state["identity"]["start"] or e["timestamp"]>state["identity"]["end"]:
            raise EngineError("EVENT_TIMESTAMP_OUTSIDE_FIGHT")
    # Event order within identical timestamp is irrelevant to PRE: strict < t.
    sorted_events=sorted(enumerate(events),key=lambda item:(item[1]["timestamp"],item[0]))
    aura_index={}
    for pos,e in sorted_events:
        transition=_aura_transition(e)
        if transition is None:continue
        aid=_ability(e);target=_num(e.get("targetID"))
        if aid is None or target is None:continue
        aura_index.setdefault((target,aid),[]).append((e["timestamp"],pos,transition))
    actors={key[0] for key in aura_index}
    decisions=[]
    for pos,e in sorted_events:
        typ=str(e.get("type","")).casefold()
        if typ not in ("cast","begincast"):continue
        timestamp=e["timestamp"]
        actor=_num(e.get("sourceID"));ability=_ability(e)
        known={}
        if actor is not None:
            for (target,aid),transitions in aura_index.items():
                if target!=actor:continue
                # Same-timestamp transitions (including those earlier in page order)
                # are never permitted as a decision feature.
                ts=[row[0] for row in transitions]
                index=bisect_left(ts,timestamp)-1
                if index<0:continue  # no observed PRE transition -> UNKNOWN
                known[str(aid)]=transitions[index][2]
        decisions.append({"timestamp":timestamp,"source_actor_id":actor,"ability_id":ability,
                          "aura_pre":known,"readiness":"UNKNOWN"})
    proof={"schema":"FreshWCLReplayV1","identity":state["identity"],
           "source_page_sha256":[p["sha256"] for p in pages],
           "event_count":len(events),"decision_count":len(decisions),
           "decisions":decisions,"blind_numeric_only":True,
           "cooldown_or_resource_readiness":"UNKNOWN",
           "candidate_lock":"NOT_IMPLEMENTED","gameplay_priority_claim":"NONE"}
    proof["replay_sha256"]=sha(canonical(proof))
    return proof


def self_test()->dict:
    checks=[]
    def check(name:str,condition:bool):
        if not condition:raise AssertionError(name)
        checks.append(name)
    code="ABCDEF123456";fight=42
    base={"code":code,"revision":3,"fights":[{"id":fight,"startTime":100,"endTime":300,
          "encounterID":999,"difficulty":4,"inProgress":False}]}
    events1=[
        {"timestamp":100,"type":"applybuff","abilityGameID":101,"targetID":7,"stack":3},
        {"timestamp":110,"type":"cast","sourceID":7,"abilityGameID":201},
        {"timestamp":110,"type":"removebuffstack","abilityGameID":101,"targetID":7,"stack":0},
        {"timestamp":120,"type":"cast","sourceID":7,"abilityGameID":202},
    ]
    events2=[
        {"timestamp":130,"type":"applybuff","abilityGameID":102,"targetID":7,"stack":2},
        {"timestamp":130,"type":"cast","sourceID":7,"abilityGameID":203},
        {"timestamp":140,"type":"cast","sourceID":7,"abilityGameID":204},
        {"timestamp":150,"type":"cast","sourceID":8,"abilityGameID":205},
    ]
    calls=[]
    def transport(q,v):
        if "FreshReport" in q:return {"reportData":{"report":base}}
        calls.append(v["start"])
        if v["start"]==100:p={"data":events1,"nextPageTimestamp":130}
        elif v["start"]==130:p={"data":events2,"nextPageTimestamp":None}
        else:raise AssertionError("unexpected request")
        return {"reportData":{"report":{"events":p}}}
    with tempfile.TemporaryDirectory(prefix="zrot_engine_first_") as temp:
        root=Path(temp)
        x=collect(transport,code,fight,root,max_pages=1)
        check("cold_start_partial",x["status"]=="PARTIAL" and x["pages"]==1)
        folder=root/code/f"fight_{fight}"
        try:replay(folder)
        except EngineError as exc:check("incomplete_replay_refused","INCOMPLETE_SNAPSHOT" in str(exc))
        else:raise AssertionError("partial replay allowed")
        y=collect(transport,code,fight,root,max_pages=3)
        check("resume_only_missing_page",y["status"]=="COMPLETE" and calls==[100,130])
        z=collect(transport,code,fight,root,max_pages=1)
        check("completed_repeat_no_api_page",z["pages"]==2 and calls==[100,130])
        proof=replay(folder)
        check("eight_events_five_casts",proof["event_count"]==8 and proof["decision_count"]==5)
        d=proof["decisions"]
        check("same_timestamp_remove_not_leaked",d[0]["aura_pre"]["101"]=={"active":True,"stacks":3})
        check("zero_stack_remove_after_timestamp",d[1]["aura_pre"]["101"]=={"active":False,"stacks":0})
        check("same_timestamp_apply_not_leaked", "102" not in d[2]["aura_pre"])
        check("next_cast_sees_apply",d[3]["aura_pre"]["102"]=={"active":True,"stacks":2})
        check("unseen_actor_unknown_aura",d[4]["aura_pre"]=={} and d[4]["readiness"]=="UNKNOWN")
        check("replay_deterministic",replay(folder)["replay_sha256"]==proof["replay_sha256"])
        check("no_semantic_priority",proof["candidate_lock"]=="NOT_IMPLEMENTED" and proof["blind_numeric_only"])
        # Simulate process crash: page file durable, checkpoint still at old cursor.
        with tempfile.TemporaryDirectory(prefix="zrot_orphan_") as other:
            orphan_root=Path(other)
            first=collect(transport,code,fight,orphan_root,max_pages=1)
            f=orphan_root/code/f"fight_{fight}"
            b=canonical({"schema":"FreshWCLPageV1","start":130,"next":None,"events":events2})
            write_atomic(f/"page_00001.json",b)
            before=list(calls)
            resumed=collect(transport,code,fight,orphan_root,max_pages=2)
            check("orphan_page_recovered_without_api_reread",resumed["status"]=="COMPLETE" and calls==before)
            check("orphan_replay_matches_clean_run",replay(f)["replay_sha256"]==proof["replay_sha256"])
        # Previous checkpoint replay is always immutable/independent of new cursor.

        rev=base["revision"];base["revision"]=rev+1
        try:collect(transport,code,fight,root)
        except EngineError as exc:check("revision_change_refused","REVISION_CHANGED" in str(exc))
        else:raise AssertionError("revision mismatch accepted")
        base["revision"]=rev
        page=folder/"page_00000.json"
        original=page.read_bytes();page.write_bytes(original+b"tamper")
        try:replay(folder)
        except EngineError as exc:check("tampered_page_rejected","PAGE_TAMPERED" in str(exc))
        else:raise AssertionError("tamper accepted")
        page.write_bytes(original)
        def bad_next(q,v):
            if "FreshReport" in q:return {"reportData":{"report":base}}
            return {"reportData":{"report":{"events":{"data":events1,"nextPageTimestamp":v["start"]}}}}
        try:collect(bad_next,code,43,root) # missing fight -> fail before events
        except EngineError as exc:check("missing_fight_rejected","FIGHT_ID" in str(exc))
        else:raise AssertionError("invalid fight accepted")
        with tempfile.TemporaryDirectory(prefix="zrot_cursor_") as other:
            try:collect(bad_next,code,fight,Path(other))
            except EngineError as exc:check("nonmonotonic_cursor_rejected","NON_MONOTONIC" in str(exc))
            else:raise AssertionError("bad cursor accepted")
        check("zero_stack_distinguished_from_unknown", _aura_transition({"type":"removebuffstack","stack":0})=={"active":False,"stacks":0} and _aura_transition({"type":"removebuffstack"})=={"active":None,"stacks":None})
        check("name_only_not_identity", _ability({"name":"폭풍의 일격"}) is None)
        keynames=("WCL_CLIENT_ID","WCL_CLIENT_SECRET","WCL_ID","WCL_SECRET")
        original_env={k:os.environ.get(k) for k in keynames}
        try:
            for k in keynames:os.environ.pop(k,None)
            try:credentials(root/"not-there.env")
            except EngineError as exc:check("missing_credentials_fail_closed","CREDENTIALS_MISSING" in str(exc))
            else:raise AssertionError("missing credentials accepted")
        finally:
            for k,v in original_env.items():
                if v is not None:os.environ[k]=v
    return {"schema":"FreshWCLEngineV1SelfTest","result":"PASS","check_count":len(checks),
            "checks":checks,"real_api_requests":0,"product_MAIN_modified":False,"FROZEN_modified":False,
            "full_rotation_engine_complete":False}


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    subs=p.add_subparsers(dest="command")
    subs.add_parser("self-test",help="offline cold-start/resume/replay fixture (default)")
    coll=subs.add_parser("collect",help="EXPLICIT live WCL public API collection")
    coll.add_argument("--report",required=True)
    coll.add_argument("--fight",type=int,required=True)
    coll.add_argument("--out",type=Path,default=Path(__file__).resolve().parent/"snapshots")
    coll.add_argument("--env",type=Path)
    coll.add_argument("--max-pages",type=int,default=15)
    rep=subs.add_parser("replay",help="verify and replay existing local checkpoint")
    rep.add_argument("--folder",type=Path,required=True)
    args=p.parse_args()
    try:
        if args.command in (None,"self-test"):
            result=self_test()
        elif args.command=="collect":
            if not REPORT_RE.fullmatch(args.report) or args.fight<=0:raise EngineError("INVALID_REPORT_OR_FIGHT")
            key,secret=credentials(args.env)
            token=oauth_token(key,secret)
            result=collect(lambda q,v:official_graphql(token,q,v),args.report,args.fight,args.out,args.max_pages)
            result["live_api_invoked"]="YES__ONLY_EXPLICIT_COLLECT"
        elif args.command=="replay":result=replay(args.folder)
        else:raise EngineError("UNSUPPORTED_MODE")
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except (EngineError,ValueError,KeyError,OSError,AssertionError,TypeError) as exc:
        print(json.dumps({"status":"FAIL_CLOSED","code":str(exc).split(":")[0],"secrets_printed":False},ensure_ascii=False))
        return 2

if __name__=="__main__":raise SystemExit(main())
