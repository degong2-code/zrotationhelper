#!/usr/bin/env python3
"""Audit exact original SimC foreground root attempt ordering, not WoW priority.

Consumes earlier original-source selected-root replay from the SAME Native log.
Before each original action_ready() call, PRE and extra fields are logged;
a separate return marker records that one original call's result AFTER it ran.
Never infer readiness from selected/cast rows, native IF POST, or omission.
No-argument PyCharm run is an offline synthetic contract test.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
REV="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
SCHEMA="ZrotOriginalNativeSameForegroundRootAttemptFrontierV1"
PLAN_SCHEMA="ZrotOriginalNativeSelectedPriorityFrontierPlanV1"
PRIOR_SCHEMA="ZrotOriginalSimCSelectedSameCallExtraPRESourceIFReplayV1"
PRE="ZROT_ORIGINAL_SELECT_IF_PRE_V1|"
EXTRA="ZROT_ORIGINAL_SELECT_EXTRA_PRE_FIELDS_V1|"
RESULT="ZROT_ORIGINAL_SELECT_NATIVE_READY_RESULT_V1|"
BEGIN="ZROT_GR_FOREGROUND_APL_BEGIN_V1|"
SELECT="ZROT_GR_FOREGROUND_APL_RETURN_V1|"
PTR=re.compile(r"^0x[0-9a-fA-F]+$")

class FrontierError(ValueError):pass

def need(flag,code):
    if not flag:raise FrontierError(code)

def marker(line,prefix,n):
    if prefix not in line:return None
    need(line.count(prefix)==1,"DUPLICATE_TRACE_MARKER")
    parts=line.split(prefix,1)[1].strip().split("|")
    need(len(parts)==n,"ORIGINAL_TRACE_MARKER_ARITY_DRIFT:"+prefix)
    return parts

def numeric(v):
    need(v.isdecimal(),"INVALID_ORIGINAL_NATIVE_NUMERIC_TOKEN")
    return int(v)

def pointer(s):
    need(PTR.fullmatch(s) is not None,"INVALID_ORIGINAL_NATIVE_POINTER")
    return s.lower()

def parse_markers(log):
    """Do not join same-timestamp events: use exact call id, ptr and line order."""
    begin={};select={};pre={};extra={};returned={}
    for line_n,line in enumerate(log.splitlines()):
        if (p:=marker(line,BEGIN,3)) is not None:
            t,dispatch,actor=p; d=numeric(dispatch)
            need(d>0 and d not in begin,"ROOT_DISPATCH_DUPLICATE")
            begin[d]=(line_n,numeric(t),pointer(actor))
        if (p:=marker(line,SELECT,4)) is not None:
            t,dispatch,actor,chosen=p;d=numeric(dispatch)
            need(d>0 and d not in select,"ROOT_RETURN_DUPLICATE")
            select[d]=(line_n,numeric(t),pointer(actor),pointer(chosen))
        if (p:=marker(line,PRE,7)) is not None:
            t,c,owner,rank,ptr,resource,stack=p; id_=numeric(c)
            need(id_>0 and id_ not in pre,"PRE_ID_DUPLICATE")
            pre[id_]={"line":line_n,"t_ms":numeric(t),"call_id":id_,
                      "list":owner,"rank":numeric(rank),"ptr":pointer(ptr)}
        if EXTRA in line:
            p=line.split(EXTRA,1)[1].strip().split("|")
            need(len(p)>=4,"EXTRA_FIELD_HEADER_MALFORMED")
            t,c,ptr,plan_sha=p[:4];id_=numeric(c)
            need(id_>0 and id_ not in extra and re.fullmatch(r"[0-9a-f]{64}",plan_sha),
                 "EXTRA_ID_OR_PLAN_HASH_INVALID")
            need((len(p)-4)%2==0,"EXTRA_FIELD_PAIR_MALFORMED")
            fields=[]
            for i in range(4,len(p),2):
                need(p[i] in ("0","1"),"EXTRA_PRESENCE_BIT_INVALID")
                fields.append((p[i],p[i+1]))
            extra[id_]=(line_n,numeric(t),pointer(ptr),plan_sha,fields)
        if (p:=marker(line,RESULT,4)) is not None:
            t,c,ptr,v=p;id_=numeric(c)
            need(id_>0 and id_ not in returned and v in ("0","1"),
                 "NATIVE_RESULT_DUPLICATE_OR_NOT_BOOLEAN")
            returned[id_]=(line_n,numeric(t),pointer(ptr),v=="1")
    need(bool(begin) and bool(pre) and bool(extra) and bool(returned),
         "MISSING_REAL_NATIVE_FOREGROUND_FRONTIER")
    need(set(pre)==set(extra)==set(returned),"MISSING_OR_DUPLICATE_READY_ATTEMPT_RESULT")
    for id_,row in pre.items():
        a=extra[id_];b=returned[id_]
        need(row["line"]<a[0]<b[0] and row["t_ms"]==a[1]==b[1] and
             row["ptr"]==a[2]==b[2],"PRE_RESULT_NOT_SAME_NATIVE_CALL")
    return begin,select,pre,extra,returned

def witness(log,profile_ir,prior,plan,targets,*,plan_sha,prior_sha):
    need(plan.get("schema")==PLAN_SCHEMA and plan.get("policy_id")==POLICY
         and plan.get("source_revision")==REV and isinstance(plan.get("cases"),list),
         "FRONTIER_PLAN_INVALID")
    need(prior.get("schema")==PRIOR_SCHEMA and prior.get("policy_id")==POLICY
         and prior.get("original_SimC_source_revision")==REV
         and prior.get("targets")==targets
         and prior.get("original_profile_blob")==plan.get("profile_git_blob")
         and prior.get("source_spec")==plan.get("spec_key")
         and prior.get("full_physical_READY_proven")==0
         and prior.get("competitor_ready_proven")==0,
         "SOURCE_REPLAY_NOT_SAME_PINNED_COHORT")
    cases=[c for c in plan["cases"] if c.get("targets")==targets]
    need(len(cases)==1,"ONE_EXACT_TARGET_FRONTIER_CASE_REQUIRED")
    wanted=cases[0]
    need(all(type(wanted.get(k)) is int for k in ("t_ms","source_rank","entry_rank"))
         and all(type(wanted.get(k)) is str and wanted[k] for k in
                 ("source_list","source_action","entry_list")),
         "INVALID_FOCUS_ROOT")
    source_lists=profile_ir["action_lists"]
    need(wanted["source_list"] in source_lists and
         wanted["entry_list"] in source_lists and
         1<=wanted["source_rank"]<=len(source_lists[wanted["source_list"]]) and
         1<=wanted["entry_rank"]<=len(source_lists[wanted["entry_list"]]),
         "FOCUS_ROW_OUTSIDE_EXACT_SOURCE")
    row=source_lists[wanted["source_list"]][wanted["source_rank"]-1]
    need(row["action"]==wanted["source_action"],"FOCUS_ACTION_SOURCE_DRIFT")
    entry=source_lists[wanted["entry_list"]][wanted["entry_rank"]-1]
    entry_attrs={x["key"]:x["value"] for x in entry["attributes"]}
    need(entry["behavior"]=="CALL" and
         entry_attrs.get("name")==wanted["source_list"],
         "FOCUS_PARENT_IS_NOT_THE_DECLARED_CALL")
    matches=[r for r in prior["selected_source_IF_samples"] if
             r["t_ms"]==wanted["t_ms"] and
             r["source_list"]==wanted["source_list"] and
             r["source_rank"]==wanted["source_rank"] and
             r["source_action"]==wanted["source_action"]]
    need(len(matches)==1,"EXACT_SELECTED_SOURCE_ROOT_ABSENT_OR_AMBIGUOUS")
    selected=matches[0]
    need(selected["source_row_sha256"]==row["source_sha256"] and
         selected["original_physical_READY"]=="UNKNOWN" and
         selected["competitor_priority"]=="UNKNOWN",
         "UNAUTHORIZED_PRIOR_READY_PROMOTION")
    begin,returned_root,pre,extra,ret=parse_markers(log)
    token=selected["original_dispatch_token"]
    need(token in begin and token in returned_root,"FOREGROUND_DISPATCH_ROOT_ABSENT")
    opening=begin[token];closing=returned_root[token]
    need(opening[0]<closing[0] and opening[2]==closing[2] and
         opening[1]<=closing[1] and closing[1]==selected["t_ms"],
         "SOURCE_ROOT_OUT_OF_ORDER_OR_TIME_MISMATCH")
    attempts=sorted((r for r in pre.values() if opening[0]<r["line"]<closing[0]),
                    key=lambda r:r["line"])
    need(attempts and len(attempts)<=300,"UNBOUNDED_OR_EMPTY_SOURCE_ATTEMPT_FRONTIER")
    need(all(opening[0]<ret[a["call_id"]][0]<closing[0] for a in attempts),
         "CROSS_ROOT_NATIVE_READY_RESULT")
    need(len({a["call_id"] for a in attempts})==len(attempts),"DUPLICATE_ROOT_PRE_CALL")
    selected_attempt=[a for a in attempts if a["call_id"]==selected["original_selected_call_id"]]
    need(len(selected_attempt)==1,"SELECTED_ROOT_CALL_ID_NOT_IN_SAME_FOREGROUND_ROOT")
    chosen=selected_attempt[0]
    need(chosen["ptr"]==closing[3] and ret[chosen["call_id"]][3] and
         chosen["list"]==wanted["source_list"] and chosen["rank"]==wanted["source_rank"],
         "NATIVE_SELECTED_SOURCE_NOT_THE_TRUE_READY_ATTEMPT")
    need(attempts[-1]["call_id"]==chosen["call_id"],
         "POST_SELECTED_ATTEMPT_IN_SAME_FOREGROUND_ROOT")
    entry_matches=[a for a in attempts if a["list"]==wanted["entry_list"] and
                   a["rank"]==wanted["entry_rank"] and a["line"]<chosen["line"]]
    need(len(entry_matches)==1 and ret[entry_matches[0]["call_id"]][3],
         "SOURCE_CALL_ENTRY_NOT_ORIGINAL_TRUE_READY")
    entry_attempt=entry_matches[0]
    fact_adapter=plan.get("fields_adapter")
    need(isinstance(fact_adapter,dict) and
         fact_adapter.get("sha256")==plan_sha and
         type(fact_adapter.get("fields")) is list,
         "PRE_FIELD_ADAPTER_PIN_INVALID")
    fields=fact_adapter["fields"]
    out=[]
    from simc_apl_semantic_ir_v2 import evaluate_ast,truth
    for a in attempts:
        list_name=a["list"];rank=a["rank"]
        native_result=ret[a["call_id"]][3]
        snap=extra[a["call_id"]]
        need(snap[3]==plan_sha and len(snap[4])==len(fields),
             "PRE_EXACT_ADAPTER_FIELDS_NOT_IDENTICAL")
        facts={f["symbol"]:float(value) for f,(present,value) in zip(fields,snap[4])
               if present=="1"}
        if list_name in source_lists and 1<=rank<=len(source_lists[list_name]):
            src=source_lists[list_name][rank-1]
            expr=src["expression_fields"].get("if")
            known=truth(evaluate_ast(expr["ast"],facts)) if expr else None
            verdict="NO_EXPLICIT_IF" if expr is None else (
                "UNKNOWN" if known is None else "TRUE" if known else "FALSE")
            need(not(native_result and verdict=="FALSE"),
                 "NATIVE_SELECTED_SOURCE_WITH_INDEPENDENT_FALSE_IF")
            attrs={x["key"]:x["value"] for x in src["attributes"]}
            source_info={"list":list_name,"rank":rank,
                         "action":src["action"],"behavior":src["behavior"],
                         "source_sha256":src["source_sha256"],
                         "destination":attrs.get("name") if src["behavior"] in ("CALL","RUN") else None,
                         "IF_independent_STRICT_CALL_PRE":verdict,
                         "source_IF_missing_PRE":sorted(set(expr["symbols"])-set(facts)) if expr else []}
        else:
            source_info={"list":list_name,"rank":rank,"action":"UNKNOWN",
                         "behavior":"UNKNOWN","source_sha256":"UNKNOWN",
                         "IF_independent_STRICT_CALL_PRE":"UNKNOWN","source_IF_missing_PRE":[]}
        out.append({"call_id":a["call_id"],"t_ms":a["t_ms"],
                    **source_info,
                    "original_action_ready_return":"TRUE" if native_result else "FALSE",
                    "original_PRE_capture_line_before_return":True})
    # READY true on CALL enters a child list; it is NOT a priority winner.
    prev=[r for r in out if r["call_id"]!=chosen["call_id"]]
    bad=[r for r in prev if r["original_action_ready_return"]=="TRUE"
         and r["behavior"] not in ("CALL","RUN")]
    need(not bad,"NON_CONTROL_NATIVE_TRUE_BEFORE_RETURNED_ACTION")
    selected_prior=[r for r in prev if r["list"]==wanted["source_list"]]
    known_ranks={r["rank"] for r in selected_prior if r["rank"]<wanted["source_rank"]}
    missing_ranks=sorted(set(range(1,wanted["source_rank"]))-known_ranks)
    return {"schema":SCHEMA,"policy_id":POLICY,"source_revision":REV,
            "source_spec":plan["spec_key"],"targets":targets,
            "cohort_source_replay_sha256":prior_sha,
            "source_profile_git_blob":plan["profile_git_blob"],
            "source_adapter_sha256":plan_sha,
            "selected_root":{"t_ms":chosen["t_ms"],"call_id":chosen["call_id"],
                             "dispatch_token":token,"source_list":chosen["list"],
                             "source_rank":chosen["rank"],"source_action":row["action"],
                             "native_action_ready_return":True},
            "original_foreground_CALL_entry":{"source_list":entry_attempt["list"],
                "source_rank":entry_attempt["rank"],
                "original_action_ready_return":True},
            "all_same_foreground_original_attempts_before_selected":out,
            "preceding_attempt_count":len(prev),
            "preceding_noncontrol_NATIVE_TRUE":0,
            "higher_source_ranks_not_attempted":missing_ranks,
            "all_higher_source_ranks_observed":not missing_ranks,
            "complete_CALL_RUN_return_stack":"UNKNOWN",
            "physical_ability_ready_independent_of_Native_result":"UNKNOWN",
            "WoW_current_Retail_priority":"UNKNOWN",
            "WCL_blind_holdout":"NOT_RUN","opener_end":"UNKNOWN",
            "dummy_wrong_cast":"UNKNOWN","MAIN_promoted":False}

def selftest():
    # Parse and negative-control same-root identity with no project dependencies.
    pre=PRE+"100|7|list|1|0xaa|10|0"
    extra=EXTRA+"100|7|0xaa|"+"a"*64+"|1|1"
    result=RESULT+"100|7|0xaa|0"
    log="\n".join((BEGIN+"100|1|0x1",pre,extra,result,
                   SELECT+"100|1|0x1|0xaa"))
    b,s,p,x,r=parse_markers(log)
    need(len(b)==len(s)==len(p)==len(x)==len(r)==1 and not r[7][3],
         "SYNTHETIC_MARKER_PARSE_FAILED")
    negative=0
    bad_inputs=[log.replace("|7|0xaa|0","|7|0xbb|0"),
                log.replace("|7|0xaa|0","|7|0xaa|1")+"\n"+result,
                log.replace(EXTRA,"NOT_EXTRA"),
                log.replace(PRE,"NOT_PRE"),
                log.replace(result,""),
                log.replace("|7|0xaa|"+"a"*64,"|8|0xaa|"+"a"*64)]
    for broken in bad_inputs:
        try:parse_markers(broken)
        except FrontierError:negative+=1
        else:raise AssertionError("ACCEPTED_FOREIGN_OR_MISSING_NATIVE_PRE_RESULT")
    # Exercise complete same-root CALL -> child selection without any SimC run.
    from types import ModuleType
    import sys
    old_module=sys.modules.get("simc_apl_semantic_ir_v2")
    fake=ModuleType("simc_apl_semantic_ir_v2")
    fake.evaluate_ast=lambda expr,facts: None
    fake.truth=lambda value: None if value is None else bool(value)
    sys.modules["simc_apl_semantic_ir_v2"]=fake
    try:
        def row(name,rank,action,behavior="ACTION",attrs=()):
            return {"action":action,"behavior":behavior,"source_sha256":f"sha-{name}-{rank}",
                    "attributes":[{"key":k,"value":v} for k,v in attrs],"expression_fields":{}}
        ir={"action_lists":{"default":[row("default",1,"call_action_list","CALL",(("name","sub"),))],
                            "sub":[row("sub",1,"alpha"),row("sub",2,"beta")]}}
        prior={"schema":PRIOR_SCHEMA,"policy_id":POLICY,"original_SimC_source_revision":REV,
               "targets":1,"original_profile_blob":"a"*40,"source_spec":"fictional",
               "full_physical_READY_proven":0,"competitor_ready_proven":0,
               "selected_source_IF_samples":[{"t_ms":100,"source_list":"sub","source_rank":2,
                  "source_action":"beta","source_row_sha256":"sha-sub-2",
                  "original_physical_READY":"UNKNOWN","competitor_priority":"UNKNOWN",
                  "original_dispatch_token":1,"original_selected_call_id":30}]}
        plan={"schema":PLAN_SCHEMA,"policy_id":POLICY,"source_revision":REV,
              "profile_git_blob":"a"*40,"spec_key":"fictional",
              "cases":[{"targets":1,"t_ms":100,"source_list":"sub","source_rank":2,
                        "source_action":"beta","entry_list":"default","entry_rank":1}],
              "fields_adapter":{"sha256":"a"*64,"fields":[{"symbol":"active_enemies"}]}}
        events=[BEGIN+"100|1|0x01"]
        for callid,owner,rank,ptr,success in ((10,"default",1,"0x11",1),
                                               (20,"sub",1,"0x21",0),
                                               (30,"sub",2,"0x31",1)):
            events.extend((PRE+f"100|{callid}|{owner}|{rank}|{ptr}|0|0",
                           EXTRA+f"100|{callid}|{ptr}|"+"a"*64+"|1|1",
                           RESULT+f"100|{callid}|{ptr}|{success}"))
        events.append(SELECT+"100|1|0x01|0x31")
        proof=witness("\n".join(events),ir,prior,plan,1,plan_sha="a"*64,prior_sha="b"*64)
        need(proof["preceding_attempt_count"]==2 and
             proof["all_higher_source_ranks_observed"] and
             proof["selected_root"]["call_id"]==30 and
             proof["original_foreground_CALL_entry"]["original_action_ready_return"],
             "SYNTHETIC_NESTED_FRONTIER_NOT_BOUND_TO_READY")
        for bad_events in (
            [e.replace("|20|0x21|0","|20|0x21|1") for e in events],
            [e.replace("|30|0x31|1","|30|0x31|0") for e in events],
            [e.replace("|1|0x01|0x31","|1|0x01|0x21") for e in events],
        ):
            try:witness("\n".join(bad_events),ir,prior,plan,1,plan_sha="a"*64,prior_sha="b"*64)
            except FrontierError:negative+=1
            else:raise AssertionError("ACCEPTED_WRONG_NATIVE_WINNER_OR_PRIOR_READY")
    finally:
        if old_module is None:sys.modules.pop("simc_apl_semantic_ir_v2",None)
        else:sys.modules["simc_apl_semantic_ir_v2"]=old_module
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negatives_rejected":negative,"native_calls_added":0,
            "physical_READY_proven":0,"WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--profile",type=Path)
    p.add_argument("--prior",type=Path)
    p.add_argument("--plan",type=Path)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--targets",type=int)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if all(v is None for v in vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(v is not None for v in vars(a).values()),
         "EXPLICIT_NATIVE_PROVENANCE_INPUTS_REQUIRED")
    from simc_apl_semantic_ir_v2 import parse_profile,git_blob,canonical
    raw=a.profile.read_bytes();ir=parse_profile(raw,require_source=False)
    plan=json.loads(a.plan.read_bytes());prior_raw=a.prior.read_bytes()
    prior=json.loads(prior_raw);adapter=json.loads(a.adapter.read_bytes())
    need(git_blob(raw)==plan.get("profile_git_blob") and
         adapter.get("source_revision")==REV,"PROFILE_OR_ADAPTER_PIN_DRIFT")
    plan["fields_adapter"]={"fields":adapter["fields"],
                           "sha256":sha256(canonical(adapter)).hexdigest()}
    result=witness(a.native_log.read_text("utf-8"),ir,prior,plan,a.targets,
                   plan_sha=plan["fields_adapter"]["sha256"],
                   prior_sha=sha256(prior_raw).hexdigest())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canonical(result))
    print("ORIGINAL_NATIVE_READY_ATTEMPT_FRONTIER_SHA256="+
          sha256(a.out.read_bytes()).hexdigest())
    print("ORIGINAL_NATIVE_READY_ATTEMPT_FRONTIER_COUNTS="+
          json.dumps({"targets":a.targets,"root":result["selected_root"],
                     "preceding_attempts":result["preceding_attempt_count"],
                     "missing_higher_ranks":result["higher_source_ranks_not_attempted"]},
                     sort_keys=True))

if __name__=="__main__":main()
