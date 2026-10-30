#!/usr/bin/env python3
"""Independent Native IF-guard source envelope to bare-resource eval audit.

Direct IF attribution needs an actual action.cpp guard BEGIN/END, one nested
bare REF evaluation from the same source epoch, and exact pointer-matched
action attempt / effective APL row. IF result is NOT readiness, optimality,
nor strict-pre state transition.
"""
from __future__ import annotations
import argparse
from collections import defaultdict,Counter
import json
from pathlib import Path
import re
from simc_native_epoch_sequence_audit import parse_epoch_native_log,independent_epoch_audit,sha
from simc_native_bare_resource_eval_audit import REGEX as BARE_RE
from simc_native_apl_eval_scope_audit import (
    REGEX as SCOPE_RE, audit as audit_attempt_scopes
)

GUARD="ZROT_NATIVE_APL_IF_GUARD_V1|"
RE=re.compile(
 r"ZROT_NATIVE_APL_IF_GUARD_V1\|(BEGIN|END)\|(\d+)\|(-?\d+)\|(\d+)\|"
 r"(-?\d+)\|(\d+)\|(-?\d+)\|([a-z][a-z0-9_]*)\|(\d+)\|(\d+)\|(-?\d+)\s*$"
)


def _epoch(row):
    return (row["thread"],row["iteration"],row["reset_seq"],row["actor"],row["spawn"])


def _match_windows(rows,identity_fields):
    intervals=defaultdict(list)
    per_epoch=defaultdict(list)
    for row in rows:
        per_epoch[_epoch(row)].append(row)
    for key,items in per_epoch.items():
        stack=[]
        for item in sorted(items,key=lambda r:r["sequence"]):
            if item["kind"]=="BEGIN":
                stack.append(item)
            else:
                if not stack:raise ValueError("IF_GUARD_ORPHAN_END")
                begin=stack.pop()
                if any(begin[field]!=item[field] for field in identity_fields):
                    raise ValueError("IF_GUARD_BEGIN_END_IDENTITY_MISMATCH")
                if item["sequence"]<=begin["sequence"] or item["time_ms"]<begin["time_ms"]:
                    raise ValueError("IF_GUARD_BEGIN_END_TIME_ORDER_INVALID")
                intervals[key].append((begin,item))
        if stack:raise ValueError("IF_GUARD_UNCLOSED_BEGIN")
    return intervals


def audit(raw:bytes,expected_sha:str,source_model:dict)->dict:
    original=audit_attempt_scopes(raw,expected_sha,source_model)
    projected=parse_epoch_native_log(raw,expected_sha)
    if independent_epoch_audit(raw,projected)["status"]!="PASS_EPOCH_NATIVE_SOURCE_BYTES_INDEPENDENT_RECALC":
        raise ValueError("IF_GUARD_EPOCH_RAW_INDEPENDENCE_REQUIRED")
    if source_model["apl_sha256"]!=original["effective_apl_sha256"]:
        raise ValueError("IF_GUARD_EFFECTIVE_APL_MISMATCH")
    seen={(r["thread"],r["sequence"]) for r in projected["events"]+
          projected["reset_boundaries"]}
    rows=[]
    scope_rows=[]
    evals=[]
    for lineno,line in enumerate(raw.splitlines(),1):
        for marker,regex,dest in (
            (GUARD,RE,rows),
            ("ZROT_NATIVE_APL_EVAL_SCOPE_V1|",SCOPE_RE,scope_rows),
            ("ZROT_NATIVE_APL_RESOURCE_EVAL_V1|",BARE_RE,evals),
        ):
            if marker.encode() not in line:continue
            s=line.decode("utf-8")
            if s.count(marker)!=1:raise ValueError("IF_GUARD_DUPLICATED_SOURCE_MARKER")
            m=regex.search(s)
            if not m:raise ValueError("IF_GUARD_UNPARSEABLE_SOURCE_MARKER")
            groups=m.groups()
            if marker==GUARD:
                kind,th,it,seq,t,actor,spawn,apl,ordinal,action,result=groups
                entry=dict(kind=kind,thread=int(th),iteration=int(it),
                    sequence=int(seq),time_ms=int(t),actor=int(actor),
                    spawn=int(spawn),apl_list=apl,ordinal=int(ordinal),
                    action_id=int(action),result=int(result),line=lineno)
                if (kind=="BEGIN" and entry["result"]!=-1) or (
                    kind=="END" and entry["result"] not in (0,1)):
                    raise ValueError("IF_GUARD_INVALID_BOOLEAN_RESULT")
            elif marker=="ZROT_NATIVE_APL_EVAL_SCOPE_V1|":
                kind,th,it,seq,t,actor,spawn,mode,apl,ordinal,action,context=groups
                entry=dict(kind=kind,thread=int(th),iteration=int(it),
                    sequence=int(seq),time_ms=int(t),actor=int(actor),
                    spawn=int(spawn),apl_list=apl,ordinal=int(ordinal),
                    action_id=int(action),mode=mode,context=context,line=lineno)
            else:
                th,it,seq,t,actor,spawn,res,value=groups
                entry=dict(thread=int(th),iteration=int(it),sequence=int(seq),
                    time_ms=int(t),actor=int(actor),spawn=int(spawn),
                    resource=res,value=float(value),line=lineno)
            dest.append(entry)
    if len(evals)!=original["bare_eval_total"]:
        raise ValueError("IF_GUARD_BARE_EVAL_DENOMINATOR_MISMATCH")
    for row in rows+scope_rows+evals:
        key=(row["thread"],row["sequence"])
        if key in seen:raise ValueError("IF_GUARD_SOURCE_SEQUENCE_COLLISION")
        seen.add(key)
        resets=[r["sequence"] for r in projected["reset_boundaries"] if
                r["thread"]==row["thread"] and
                r["iteration"]==row["iteration"] and
                r["sequence"]<row["sequence"]]
        row["reset_seq"]=max(resets) if resets else None
    if any(row["reset_seq"] is None for row in rows):
        raise ValueError("IF_GUARD_MISSING_SOURCE_RESET")
    guard_windows=_match_windows(rows,("apl_list","ordinal","action_id"))
    scope_windows=_match_windows(scope_rows,("apl_list","ordinal","action_id","mode","context"))
    canonical={(r["list"],r["list_rank"]):r for r in source_model["rows"]}
    guard_count=sum(row["kind"]=="BEGIN" for row in rows)
    true_count=sum(row["kind"]=="END" and row["result"]==1 for row in rows)
    false_count=sum(row["kind"]=="END" and row["result"]==0 for row in rows)
    outputs=Counter()
    owners=Counter()
    examples=[]
    for ev in evals:
        key=_epoch(ev)
        guards=[(begin,end) for begin,end in guard_windows.get(key,())
                if begin["sequence"]<ev["sequence"]<end["sequence"]]
        scopes=[(begin,end) for begin,end in scope_windows.get(key,())
                if begin["sequence"]<ev["sequence"]<end["sequence"]]
        inside=max(scopes,key=lambda x:x[0]["sequence"]) if scopes else None
        direct=max(guards,key=lambda x:x[0]["sequence"]) if guards else None
        chosen=None;source=None;mode=None
        if ev["reset_seq"] is None:
            status="UNKNOWN_NO_SOURCE_RESET"
        elif direct is None:
            if inside is not None and inside[0]["context"]=="VARIABLE_ACTION_ATTEMPT":
                status="OBSERVED_VARIABLE_ATTEMPT_NOT_DIRECT_IF"
            elif inside is not None:
                status="UNKNOWN_BARE_EVAL_OUTSIDE_DIRECT_IF"
            else:
                status="UNKNOWN_NO_SCOPE_OR_IF"
        else:
            begin,end=direct
            if inside is None:
                status="UNKNOWN_DIRECT_IF_OUTSIDE_ACTION_ATTEMPT"
            elif (begin["apl_list"],begin["ordinal"],begin["action_id"])!=(
                  inside[0]["apl_list"],inside[0]["ordinal"],inside[0]["action_id"]):
                status="UNKNOWN_IF_OWNER_SCOPE_MISMATCH"
            elif not (inside[0]["sequence"]<begin["sequence"] and
                      end["sequence"]<inside[1]["sequence"]):
                status="UNKNOWN_IF_SCOPE_NOT_NESTED"
            elif ev["time_ms"]!=begin["time_ms"] or end["time_ms"]!=ev["time_ms"]:
                status="UNKNOWN_IF_GUARD_CLOCK_MISMATCH"
            elif begin["ordinal"]<=0:
                status="UNKNOWN_NO_NATIVE_SIGNATURE_POINTER_MATCH"
            else:
                source=canonical.get((begin["apl_list"],begin["ordinal"]))
                if source is None or source.get("guard") is None:
                    status="UNKNOWN_NO_SOURCE_GUARD_ROW"
                else:
                    status="MATCH_NATIVE_DIRECT_IF_GUARD_BARE_EVALUATION"
                    chosen=begin
                    mode=inside[0]["mode"]
                    owners[(begin["apl_list"],begin["ordinal"],source["command_token"],
                        mode,ev["resource"],end["result"])]+=1
        outputs[status]+=1
        if len(examples)<25:
            examples.append({"source_seq":ev["sequence"],"resource":ev["resource"],
                "status":status,"apl_list":chosen["apl_list"] if chosen else None,
                "ordinal":chosen["ordinal"] if chosen else None,
                "mode":mode,"action_token":source["command_token"] if chosen else None,
                "source_line":source["source_line"] if chosen else None})
    return {"schema":"ZrotNativeDirectIfBareEvalAuditV1",
        "source_log_sha256":expected_sha,
        "effective_apl_sha256":source_model["apl_sha256"],
        "source_epoch_independent_audit":"PASS",
        "bare_eval_total":len(evals),
        "action_scope_count":original["scope_begin_count"],
        "guard_begin_count":guard_count,"guard_end_count":true_count+false_count,
        "guard_success_true_count":true_count,"guard_success_false_count":false_count,
        "outcomes":dict(sorted(outputs.items())),
        "confirmed_owner_counts":[
          {"list":k[0],"ordinal":k[1],"action":k[2],"mode":k[3],
           "resource":k[4],"guard_success":bool(k[5]),"count":v}
           for k,v in sorted(owners.items())],
        "examples_max_25":examples,
        "guard_result_is_not_action_ready":True,
        "eval_as_state_transition":False,"readiness_certified":0,
        "gameplay_rule_promotion":False}


def selftest():
    def reset(seq):return f"ZROT_NATIVE_RESET_BOUNDARY_V1|0|0|{seq}|0\n".encode()
    def ev(kind,seq,t):
        res="rage" if kind=="INIT" else "none"
        cur=10 if kind=="INIT" else 0
        v=(f"ZROT_NATIVE_EVENT_V2|{kind}|0|0|{seq}|{t}|0|1|{res}|"
           f"{cur}|{100 if kind=='INIT' else 0}\n")
        if kind=="INIT":legacy=f"ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|{t}|0|1|rage|10|100|INIT\n"
        elif kind=="SELECT_BEGIN":legacy=f"ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|{t}|0|1\n"
        else:legacy=f"ZROT_NATIVE_SELECT_RESOURCE_END_V1|{t}|0|1|100\n"
        return (v+legacy).encode()
    def scope(kind,seq):return (
        f"ZROT_NATIVE_APL_EVAL_SCOPE_V1|{kind}|0|0|{seq}|10|0|1|"
        f"FOREGROUND|default|1|100|IF_ACTION_ATTEMPT\n").encode()
    def guard(kind,seq,result):return (
        f"ZROT_NATIVE_APL_IF_GUARD_V1|{kind}|0|0|{seq}|10|0|1|default|1|100|{result}\n").encode()
    def bare(seq):return f"ZROT_NATIVE_APL_RESOURCE_EVAL_V1|0|0|{seq}|10|0|1|rage|10\n".encode()
    model={"schema":"ZrotGenericSimcAplSourceHypothesisV1",
           "apl_sha256":"a"*64,"actionable_general_rotation":False,
           "rows":[{"list":"default","list_rank":1,"command_token":"rampage",
                    "source_line":14,"guard":"rage>=100","role":"ACTION_TOKEN"}]}
    raw=(reset(0)+ev("INIT",1,0)+ev("SELECT_BEGIN",2,10)+
         scope("BEGIN",3)+guard("BEGIN",4,-1)+bare(5)+
         guard("END",6,1)+scope("END",7)+ev("SELECT_END",8,10))
    got=audit(raw,sha(raw),model)
    assert got["outcomes"]=={"MATCH_NATIVE_DIRECT_IF_GUARD_BARE_EVALUATION":1}
    assert got["confirmed_owner_counts"][0]["guard_success"] is True
    assert got["readiness_certified"]==0
    for bad in (
      raw.replace(b"|END|0|0|6|10|0|1|default|1|100|1",
                  b"|END|0|0|6|10|0|1|default|2|100|1"),
      raw.replace(b"|END|0|0|6|10|0|1|default|1|100|1",
                  b"|END|0|0|6|10|0|1|default|1|100|2"),
      raw.replace(b"|BEGIN|0|0|4|10|0|1",b"|BEGIN|0|0|5|10|0|1"),
    ):
        try:audit(bad,sha(bad),model)
        except ValueError:pass
        else:raise AssertionError("IF_GUARD_TAMPERING_ACCEPTED")
    print("SIMC_NATIVE_DIRECT_IF_GUARD_AUDIT_SELF_TEST=PASS SYNTHETIC_ONLY")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--log",type=Path)
    parser.add_argument("--model",type=Path)
    parser.add_argument("--sha256")
    args=parser.parse_args()
    if args.self_test or not args.log:
        selftest();return
    if not args.model or not args.sha256:
        parser.error("--model and --sha256 required")
    print(json.dumps(audit(args.log.read_bytes(),args.sha256,
                           json.loads(args.model.read_text("utf-8"))),
                     sort_keys=True,indent=2))


if __name__=="__main__":
    main()
