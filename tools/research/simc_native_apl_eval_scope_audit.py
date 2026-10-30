#!/usr/bin/env python3
"""Independently reparse Native action-attempt scope with bare reference evals.

Source reset+sequence and pointer-equal APL (list,ordinal) identity are required.
An action *attempt context* does NOT prove the reference occurred inside its
if guard, or confer readiness, PRE state or gameplay rule authority.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import json
import re
from pathlib import Path
from simc_native_epoch_sequence_audit import parse_epoch_native_log, independent_epoch_audit, sha
from simc_native_bare_resource_eval_audit import audit as audit_bare, REGEX as EVAL_REGEX

MARK="ZROT_NATIVE_APL_EVAL_SCOPE_V1|"
REGEX=re.compile(
    r"ZROT_NATIVE_APL_EVAL_SCOPE_V1\|(BEGIN|END)\|(\d+)\|(-?\d+)\|(\d+)\|"
    r"(-?\d+)\|(\d+)\|(-?\d+)\|(FOREGROUND|OFF_GCD|CAST_WHILE_CASTING)\|"
    r"([a-z][a-z0-9_]*)\|(\d+)\|(\d+)\|"
    r"(IF_ACTION_ATTEMPT|VARIABLE_ACTION_ATTEMPT)\s*$"
)
SCHEMA="ZrotNativeAplAttemptScopeSourceAuditV1"


def _epoch(row):
    return (row["thread"],row["iteration"],row["reset_seq"],
            row["actor"],row["spawn"])


def audit(raw:bytes,expected_sha256:str,model:dict)->dict:
    if not isinstance(model,dict) or model.get("schema")!="ZrotGenericSimcAplSourceHypothesisV1":
        raise ValueError("APL_SCOPE_CANONICAL_EFFECTIVE_SOURCE_MODEL_REQUIRED")
    if model.get("actionable_general_rotation") is not False or not isinstance(model.get("rows"),list):
        raise ValueError("APL_SCOPE_SOURCE_HYPOTHESIS_ONLY")
    original=audit_bare(raw,expected_sha256)
    projected=parse_epoch_native_log(raw,expected_sha256)
    independent=independent_epoch_audit(raw,projected)
    if independent["status"]!="PASS_EPOCH_NATIVE_SOURCE_BYTES_INDEPENDENT_RECALC":
        raise ValueError("APL_SCOPE_INDEPENDENT_EPOCH_AUDIT_MISSING")
    seen={(e["thread"],e["sequence"]) for e in
          projected["events"]+projected["reset_boundaries"]}
    entries=[]
    evals=[]
    for index,line in enumerate(raw.splitlines(),1):
        if MARK.encode() in line:
            text=line.decode("utf-8")
            if text.count(MARK)!=1:raise ValueError("APL_SCOPE_MARKER_DUPLICATED")
            m=REGEX.search(text)
            if not m:raise ValueError("APL_SCOPE_MARKER_FORMAT")
            kind,th,it,seq,t,actor,spawn,mode,apl,rank,action,context=m.groups()
            row=dict(kind=kind,thread=int(th),iteration=int(it),sequence=int(seq),
                     time_ms=int(t),actor=int(actor),spawn=int(spawn),mode=mode,
                     apl_list=apl,ordinal=int(rank),action_id=int(action),
                     context=context,line=index)
            if row["thread"]<0 or row["sequence"]<0:
                raise ValueError("APL_SCOPE_INVALID_SEQUENCE")
            entries.append(row)
        if b"ZROT_NATIVE_APL_RESOURCE_EVAL_V1|" in line:
            m=EVAL_REGEX.search(line.decode("utf-8"))
            if not m:raise ValueError("APL_SCOPE_BARE_EVAL_SOURCE_FORMAT")
            th,it,seq,t,actor,spawn,resource,value=m.groups()
            evals.append(dict(thread=int(th),iteration=int(it),sequence=int(seq),
                              time_ms=int(t),actor=int(actor),spawn=int(spawn),
                              resource=resource,value=float(value),line=index))
    if len(evals)!=original["native_evaluation_count"]:
        raise ValueError("APL_SCOPE_EVAL_SOURCE_COUNT_MISMATCH")
    # Independently validate native source monotonic counter uniqueness across
    # legacy V2, resets, expression evals and new scope markers.
    for row in entries+evals:
        key=(row["thread"],row["sequence"])
        if key in seen:raise ValueError("APL_SCOPE_SHARED_SEQUENCE_COLLISION")
        seen.add(key)
        resets=[r["sequence"] for r in projected["reset_boundaries"]
                if r["thread"]==row["thread"] and r["iteration"]==row["iteration"]
                and r["sequence"]<row["sequence"]]
        row["reset_seq"]=max(resets) if resets else None
    source_rows={}
    for row in model["rows"]:
        key=(row.get("list"),row.get("list_rank"))
        if not isinstance(key[0],str) or not isinstance(key[1],int):
            raise ValueError("APL_SCOPE_MALFORMED_SOURCE_ROW")
        if key in source_rows:raise ValueError("APL_SCOPE_DUPLICATE_SOURCE_ROW")
        source_rows[key]=row

    by_epoch=defaultdict(list)
    for row in entries:
        by_epoch[_epoch(row)].append(row)
    intervals=defaultdict(list)
    for key,rows in by_epoch.items():
        stack=[]
        for row in sorted(rows,key=lambda r:r["sequence"]):
            if row["kind"]=="BEGIN":
                stack.append(row)
            else:
                if not stack:raise ValueError("APL_SCOPE_ORPHAN_END")
                begin=stack.pop()
                attrs=("mode","apl_list","ordinal","action_id","context")
                if any(begin[attr]!=row[attr] for attr in attrs):
                    raise ValueError("APL_SCOPE_BEGIN_END_POINTER_IDENTITY_DRIFT")
                if begin["sequence"]>=row["sequence"] or begin["time_ms"]>row["time_ms"]:
                    raise ValueError("APL_SCOPE_BEGIN_END_CLOCK_CONTRADICTION")
                intervals[key].append((begin,row))
        if stack:raise ValueError("APL_SCOPE_UNCLOSED_BEGIN")
    counts=Counter()
    modes=Counter()
    owners=Counter()
    examples=[]
    for row in evals:
        matches=[(b,e) for b,e in intervals.get(_epoch(row),[])
                 if b["sequence"]<row["sequence"]<e["sequence"]]
        chosen=None
        src=None
        if row["reset_seq"] is None:
            status="UNKNOWN_NO_SOURCE_RESET_EPOCH"
        elif not matches:
            status="UNKNOWN_NO_NATIVE_ACTION_ATTEMPT_CONTEXT"
        else:
            # Pick the innermost nested call_action_list scope.
            chosen,end=max(matches,key=lambda x:x[0]["sequence"])
            if not (chosen["time_ms"]<=row["time_ms"]<=end["time_ms"]):
                status="UNKNOWN_SOURCE_SCOPE_CLOCK_CONFLICT"
            elif chosen["ordinal"]<=0:
                status="UNKNOWN_NO_SIGNATURE_POINTER_MATCH"
            else:
                src=source_rows.get((chosen["apl_list"],chosen["ordinal"]))
                if src is None:
                    status="UNKNOWN_EFFECTIVE_APL_ROW_NOT_RECONCILED"
                elif (chosen["context"]=="VARIABLE_ACTION_ATTEMPT") != (
                        src.get("command_token")=="variable"):
                    status="UNKNOWN_SOURCE_COMMAND_CONTEXT_DRIFT"
                    src=None
                else:
                    status="MATCH_NATIVE_APL_ACTION_ATTEMPT_POINTER_CONTEXT"
                    modes[chosen["mode"]]+=1
                    owners[(chosen["apl_list"],chosen["ordinal"],
                            src["command_token"],chosen["mode"],row["resource"])]+=1
        counts[status]+=1
        if len(examples)<30:
            examples.append({
                "status":status,"resource":row["resource"],"evaluated_value":row["value"],
                "evaluation_source_seq":row["sequence"],
                "evaluation_time_ms":row["time_ms"],
                "mode":chosen["mode"] if chosen else None,
                "apl_list":chosen["apl_list"] if chosen else None,
                "apl_ordinal":chosen["ordinal"] if chosen else None,
                "source_action":src.get("command_token") if src else None,
                "effective_apl_source_line":src.get("source_line") if src else None,
                "scope_context":chosen["context"] if chosen else None,
            })
    return {"schema":SCHEMA,
            "source_log_sha256":expected_sha256,
            "effective_apl_sha256":model["apl_sha256"],
            "epoch_independent_raw_validation":independent["status"],
            "bare_eval_total":len(evals),
            "scope_begin_count":sum(r["kind"]=="BEGIN" for r in entries),
            "scope_end_count":sum(r["kind"]=="END" for r in entries),
            "outcome_counts":dict(sorted(counts.items())),
            "matched_mode_counts":dict(sorted(modes.items())),
            "owner_context_counts":[{
                "apl_list":k[0],"ordinal":k[1],"action_token":k[2],
                "execution_mode":k[3],"resource":k[4],"count":v
            } for k,v in sorted(owners.items())],
            "examples_max_30":examples,
            "source_owner_kind":"NATIVE_POINTER_MATCHED_ACTION_ATTEMPT_CONTEXT_ONLY",
            "guard_expression_owner_certified":False,
            "runtime_eval_used_as_strict_pre":False,
            "readiness_certified":0,"gameplay_rule_promotion":False}


def selftest():
    def reset(seq):return f"ZROT_NATIVE_RESET_BOUNDARY_V1|0|0|{seq}|0\n".encode()
    def event(kind,seq,t):
        res="rage" if kind=="INIT" else "none"
        v=f"ZROT_NATIVE_EVENT_V2|{kind}|0|0|{seq}|{t}|0|1|{res}|{10 if res=='rage' else 0}|{100 if res=='rage' else 0}\n"
        if kind=="INIT":legacy=f"ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|{t}|0|1|rage|10|100|INIT\n"
        elif kind=="SELECT_BEGIN":legacy=f"ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|{t}|0|1\n"
        else:legacy=f"ZROT_NATIVE_SELECT_RESOURCE_END_V1|{t}|0|1|100\n"
        return (v+legacy).encode()
    def scope(kind,seq,t,mode="FOREGROUND",ordinal=1,context="IF_ACTION_ATTEMPT"):
        return (f"ZROT_NATIVE_APL_EVAL_SCOPE_V1|{kind}|0|0|{seq}|{t}|0|1|"
                f"{mode}|default|{ordinal}|100|{context}\n").encode()
    def ev(seq,t):return f"ZROT_NATIVE_APL_RESOURCE_EVAL_V1|0|0|{seq}|{t}|0|1|rage|10\n".encode()
    model={"schema":"ZrotGenericSimcAplSourceHypothesisV1","apl_sha256":"a"*64,
           "actionable_general_rotation":False,
           "rows":[{"list":"default","list_rank":1,"command_token":"rampage","source_line":17,
                    "guard":"rage>=100","role":"ACTION_TOKEN"},
                   {"list":"default","list_rank":2,"command_token":"variable","source_line":18,
                    "guard":None,"role":"DIRECTIVE"}]}
    base=reset(0)+event("INIT",1,0)+event("SELECT_BEGIN",2,10)
    raw=(base+scope("BEGIN",3,10)+ev(4,10)+scope("END",5,10)+
         event("SELECT_END",6,10)+scope("BEGIN",7,11,"OFF_GCD",2,"VARIABLE_ACTION_ATTEMPT")+
         ev(8,11)+scope("END",9,11,"OFF_GCD",2,"VARIABLE_ACTION_ATTEMPT"))
    result=audit(raw,sha(raw),model)
    assert result["bare_eval_total"]==2
    assert result["outcome_counts"]=={"MATCH_NATIVE_APL_ACTION_ATTEMPT_POINTER_CONTEXT":2}
    assert result["matched_mode_counts"]=={"FOREGROUND":1,"OFF_GCD":1}
    assert result["readiness_certified"]==0
    # No guessed owner from same timestamp; action with no pointer is UNKNOWN.
    missing=base+scope("BEGIN",3,10,ordinal=0)+ev(4,10)+scope("END",5,10,ordinal=0)+event("SELECT_END",6,10)
    assert audit(missing,sha(missing),model)["outcome_counts"]=={
        "UNKNOWN_NO_SIGNATURE_POINTER_MATCH":1}
    for bad in (
        raw.replace(b"|END|0|0|5|10|0|1|FOREGROUND|default|1|100|",b"|END|0|0|5|10|0|1|FOREGROUND|default|2|100|"),
        raw.replace(b"|BEGIN|0|0|3|10|0|1",b"|BEGIN|0|0|4|10|0|1"),
        raw.replace(b"|END|0|0|5|10|0|1|",b"|END|0|0|5|10|0|1|unknown|"),
    ):
        try:audit(bad,sha(bad),model)
        except ValueError:pass
        else:raise AssertionError("SCOPE_TAMPERING_ACCEPTED")
    print("SIMC_NATIVE_APL_EVAL_SCOPE_SOURCE_AUDIT_SELF_TEST=PASS SYNTHETIC_ONLY")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--native-log",type=Path)
    p.add_argument("--log-sha256")
    p.add_argument("--effective-model",type=Path)
    a=p.parse_args()
    if a.self_test or not a.native_log:
        selftest();return
    if not a.log_sha256 or not a.effective_model:
        p.error("--log-sha256 and --effective-model required")
    print(json.dumps(audit(a.native_log.read_bytes(),a.log_sha256,
                          json.loads(a.effective_model.read_text("utf-8"))),
                     ensure_ascii=False,sort_keys=True,indent=2))


if __name__=="__main__":
    main()
