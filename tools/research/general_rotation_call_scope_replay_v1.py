#!/usr/bin/env python3
"""Generic strict causal CALL-SCOPE replayer for Original SimC action readiness.

Uses source-side globally unique invocation IDs (not timestamps) and balanced
RAII parent/child frames to correlate the exact SELECT action_ready call with
its instrumented C++ virtual override and base method entries.

Original method PRE entry/typed FIELD records carry the current scope ID.
Same-ms duplicate actions cannot merge. The full C++ method graph remains
unclosed: only instrumented paths are observed; method negative witnesses
remain METHOD_RETURN_FALSE, never full chosen-action READY/priority.

For privacy, the receipt has aggregate counts and capped source-row-hash
examples only. Actor names and raw simulated character logs are not exported.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import json
from pathlib import Path
import re

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_method_pre_passive_producer_v1 import (
    _validate_plan, MARK as METHOD_MARK
)
from general_rotation_select_pre_passive_producer_v1 import (
    MARK as SELECT_MARK, READS as SELECT_READS
)
from general_rotation_call_scope_instrument_v1 import (
    TRACE_MARK, SKIP_MARK, SCHEMA as SOURCE_TRACE_SCHEMA
)
from general_rotation_source_false_guard_engine_v1 import (
    verify_rules, assess_method_entry, FALSE as METHOD_FALSE
)
from simc_apl_semantic_ir_v2 import parse_profile, git_blob

SCHEMA="ZrotGenericOriginalReadyCallScopeStrictReplayV1"


class ScopeReplayError(ValueError):
    pass


def _exact_source_identity(apl:dict, owner:str,ordinal:int,native:str):
    rows=apl.get(owner)
    if rows is None or ordinal<1 or ordinal>len(rows):
        raise ScopeReplayError("UNMAPPED_SOURCE_APL_OWNER_OR_ORDINAL")
    row=rows[ordinal-1]
    if not native:
        raise ScopeReplayError("EMPTY_NATIVE_ACTION_NAME")
    return row


def replay(log:str,profile:bytes,manifest:dict,trace_receipt:dict,
           false_guards:dict|None=None)->dict:
    if (trace_receipt.get("schema")!=SOURCE_TRACE_SCHEMA or
        trace_receipt.get("trace_marker")!=TRACE_MARK or
        trace_receipt.get("original_action_ready_call_count")!=1 or
        trace_receipt.get("new_action_ready_calls")!=0 or
        trace_receipt.get("method_PRE_marker_call_id_appended") is not True or
        trace_receipt.get("source_select_skip_marker")!=SKIP_MARK):
        raise ScopeReplayError("SOURCE_SCOPE_PRODUCER_RECEIPT_REQUIRED")
    sites={x["method_key"]:x for x in _validate_plan(manifest)}
    if len(sites)!=trace_receipt.get("source_method_count"):
        raise ScopeReplayError("METHOD_SITE_COUNT_NOT_PINNED")
    certified=verify_rules(false_guards,manifest) if false_guards is not None else {}
    parsed=parse_profile(profile,require_source=False)
    apl=parsed["action_lists"]
    open_by_id={}
    seen_ids=set()
    finished_ids=set()
    root_stacks=defaultdict(list)
    by_method=Counter()
    by_method_edges=Counter()
    false_by_rule=Counter()
    method_pre_belongs_to_scope=0
    unlinked_legacy_method_pre=0
    selection_skips=Counter()
    bounded_source_skips=[]
    selection_pre_records=0
    selection_pre_complete=0
    selected_attempts=0
    method_scopes=0
    max_depth=0
    examples=[]
    pending_select=defaultdict(list)
    ready_selections=defaultdict(deque)

    def _register_method_outcome(frame):
        nonlocal method_pre_belongs_to_scope
        if not frame["entry_seen"]:
            raise ScopeReplayError("METHOD_SCOPE_MISSING_MATCHED_ORIGINAL_PRE")
        if set(frame["raw_fields"])!={
            x["operand_name"] for x in sites[frame["method"]]["fields"]}:
            raise ScopeReplayError("METHOD_SCOPE_RAW_FIELDS_INCOMPLETE")
        method_pre_belongs_to_scope+=1
        witness=assess_method_entry({
            "source_method_key":frame["method"],
            "source_method_body_sha256":
                sites[frame["method"]]["source_method_body_sha256"],
            "capture_phase":"SIMC_ORIGINAL_METHOD_PRE",
            "raw_fields":frame["raw_fields"]
        },certified)
        if witness["method_return_verdict"]==METHOD_FALSE:
            false_by_rule[witness["source_guard_rule_id"]]+=1
            if len(examples)<3:
                examples.append({
                    "method_call_id":frame["id"],"selected_root_call_id":frame["root"],
                    "parent_method_call_id":frame["parent"],
                    "source_row_sha256":frame["source_row_sha256"],
                    "source_guard":witness["source_guard_rule_id"],
                    "method_return_verdict":METHOD_FALSE,
                    "chosen_action_READY":"UNKNOWN",
                })

    for rawline in log.splitlines():
        if SKIP_MARK in rawline:
            if rawline.count(SKIP_MARK)!=1:
                raise ScopeReplayError("AMBIGUOUS_SOURCE_BACKGROUND_EXCLUSION")
            parts=rawline.split(SKIP_MARK,1)[1].strip().split("|")
            if len(parts)!=5:
                raise ScopeReplayError("SOURCE_SELECT_SKIP_SHAPE_DRIFT")
            clock,owner,ord_s,native,reason=parts
            if (not clock.isdigit() or not ord_s.isdigit() or
                reason!="BACKGROUND"):
                raise ScopeReplayError("UNDECLARED_APL_LOOP_SKIP_CAUSE")
            row=_exact_source_identity(apl,owner,int(ord_s),native)
            action=row["action"]
            selection_skips[(action,reason)]+=1
            if len(bounded_source_skips)<3:
                bounded_source_skips.append({
                    "at_simc_ms":int(clock),
                    "source_row_sha256":row["source_sha256"],
                    "source_action":action,
                    "source_loop_skip_reason":reason,
                    "action_READY_called":False,
                    "whole_action_NOT_READY_proven":False
                })
            continue
        if SELECT_MARK in rawline:
            if rawline.count(SELECT_MARK)!=1:
                raise ScopeReplayError("AMBIGUOUS_SELECT_PRE_MARKER")
            fields=rawline.split(SELECT_MARK,1)[1].strip().split("|")
            if len(fields)!=7:
                raise ScopeReplayError("SELECT_PRE_FIELDS_CHANGED")
            clock,owner,ordinal,native,fieldid,kind,value=fields
            if not clock.isdigit() or not ordinal.isdigit():
                raise ScopeReplayError("INVALID_SELECT_PRE_TIME")
            _exact_source_identity(apl,owner,int(ordinal),native)
            if not re.fullmatch(r"[a-f0-9]{64}",fieldid):
                raise ScopeReplayError("SELECT_PRE_UNPINNED_FIELD_ID")
            key=(int(clock),owner,int(ordinal),native)
            pending_select[key].append((fieldid,kind,value))
            if len(pending_select[key])==len(SELECT_READS):
                chunk=pending_select.pop(key)
                if len({x[0] for x in chunk})!=len(SELECT_READS):
                    raise ScopeReplayError("DUPLICATE_SELECT_PRE_FIELD")
                ready_selections[key].append(chunk)
                selection_pre_complete+=1
            elif len(pending_select[key])>len(SELECT_READS):
                raise ScopeReplayError("OVERFULL_SELECT_PRE_GROUP")
            selection_pre_records+=1
            continue

        if TRACE_MARK in rawline:
            if rawline.count(TRACE_MARK)!=1:
                raise ScopeReplayError("AMBIGUOUS_SOURCE_SCOPE_MARKER")
            p=rawline.split(TRACE_MARK,1)[1].strip().split("|")
            if len(p)!=10:
                raise ScopeReplayError("CALL_SCOPE_EVENT_FIELD_COUNT_CHANGED")
            clock,event,kind,id_s,parent_s,root_s,method,owner,ordinal_s,native=p
            if (not clock.isdigit() or event not in ("BEGIN","END")
                or kind not in ("SELECT","METHOD") or not id_s.isdigit()
                or not parent_s.isdigit() or not root_s.isdigit()
                or not ordinal_s.isdigit()):
                raise ScopeReplayError("INVALID_CALL_SCOPE_EVENT")
            callid=int(id_s); parent=int(parent_s); root=int(root_s)
            ordinal=int(ordinal_s)
            if not callid or not root or ordinal<1:
                raise ScopeReplayError("EMPTY_CALL_ID_ROOT_OR_SOURCE_ORDINAL")
            source_row=_exact_source_identity(apl,owner,ordinal,native)
            if event=="BEGIN":
                if callid in seen_ids or callid in open_by_id:
                    raise ScopeReplayError("CALL_ID_REUSED")
                seen_ids.add(callid)
                if kind=="SELECT":
                    if callid!=root or method!="select_call":
                        raise ScopeReplayError("INVALID_SELECT_CALL_ROOT")
                    if parent:
                        # A nested select call requires an explicitly observed
                        # parent frame. Do not infer nesting by same millisecond.
                        prior=open_by_id.get(parent)
                        if prior is None or parent!=root_stacks[prior["root"]][-1]:
                            raise ScopeReplayError("UNSCOPED_NESTED_SELECT_CALL")
                    key=(int(clock),owner,ordinal,native)
                    queue=ready_selections.get(key)
                    if not queue:
                        raise ScopeReplayError("SELECT_ROOT_WITHOUT_TYPED_PRE")
                    queue.popleft()
                    selected_attempts+=1
                    root_stacks[root].append(callid)
                else:
                    if method not in sites or callid==root:
                        raise ScopeReplayError("UNDECLARED_METHOD_SOURCE_SITE")
                    upstream=open_by_id.get(parent)
                    if (upstream is None or upstream["root"]!=root
                        or not root_stacks[root]
                        or root_stacks[root][-1]!=parent):
                        raise ScopeReplayError("METHOD_PARENT_NOT_CURRENT_CAUSAL_FRAME")
                    by_method_edges[(upstream["method"],method)]+=1
                    by_method[method]+=1
                    method_scopes+=1
                    root_stacks[root].append(callid)
                max_depth=max(max_depth,len(root_stacks[root]))
                open_by_id[callid]={
                    "id":callid,"parent":parent,"root":root,
                    "time":int(clock),"kind":kind,"method":method,
                    "owner":owner,"ordinal":ordinal,"native":native,
                    "source_row_sha256":source_row["source_sha256"],
                    "entry_seen":False,"raw_fields":{},
                }
            else:
                frame=open_by_id.get(callid)
                if (frame is None or frame["root"]!=root or
                    frame["parent"]!=parent or frame["kind"]!=kind or
                    frame["method"]!=method or frame["owner"]!=owner or
                    frame["ordinal"]!=ordinal or frame["native"]!=native or
                    int(clock)!=frame["time"] or
                    not root_stacks[root] or root_stacks[root][-1]!=callid):
                    raise ScopeReplayError("RETURN_SCOPE_OR_PARENT_STACK_MISMATCH")
                if kind=="METHOD":
                    _register_method_outcome(frame)
                root_stacks[root].pop()
                if not root_stacks[root]:
                    del root_stacks[root]
                del open_by_id[callid]
                finished_ids.add(callid)
            continue

        if METHOD_MARK in rawline:
            if rawline.count(METHOD_MARK)!=1:
                raise ScopeReplayError("AMBIGUOUS_METHOD_PRE_CALL_SCOPE")
            parts=rawline.split(METHOD_MARK,1)[1].strip().split("|")
            if len(parts)!=10:
                raise ScopeReplayError("EXPLICIT_METHOD_CALL_ID_REQUIRED")
            clock,owner,ord_s,native,method,event,fid,kind,raw_value,call_s=parts
            if not call_s.isdigit() or not clock.isdigit() or not ord_s.isdigit():
                raise ScopeReplayError("NONINTEGER_METHOD_CALL_REFERENCE")
            callid=int(call_s)
            if callid==0:
                unlinked_legacy_method_pre+=1
                continue
            frame=open_by_id.get(callid)
            if (frame is None or frame["kind"]!="METHOD"
                or frame["method"]!=method or frame["owner"]!=owner
                or frame["ordinal"]!=int(ord_s)
                or frame["native"]!=native or frame["time"]!=int(clock)):
                raise ScopeReplayError("METHOD_PRE_NOT_IN_EXACT_SOURCE_CALL_FRAME")
            if event=="ENTRY":
                if frame["entry_seen"] or (fid,kind,raw_value)!=("-","-","-"):
                    raise ScopeReplayError("DUPLICATE_OR_FAKE_METHOD_PRE_ENTRY")
                frame["entry_seen"]=True
            elif event=="FIELD":
                if not frame["entry_seen"]:
                    raise ScopeReplayError("METHOD_FIELD_BEFORE_SAME_CALL_PRE_ENTRY")
                matches=[f for f in sites[method]["fields"] if f["field_id"]==fid]
                if len(matches)!=1 or matches[0]["value_kind"]!=kind:
                    raise ScopeReplayError("METHOD_FIELD_SOURCE_DECLARATION_MISMATCH")
                name=matches[0]["operand_name"]
                if name in frame["raw_fields"]:
                    raise ScopeReplayError("SAME_METHOD_CALL_DUPLICATE_FIELD")
                if kind=="bool":
                    if raw_value not in ("0","1"):
                        raise ScopeReplayError("RAW_BOOL_METHOD_PRE_INVALID")
                    value=raw_value=="1"
                elif kind=="int":
                    if not re.fullmatch(r"-?[0-9]+",raw_value):
                        raise ScopeReplayError("RAW_INT_METHOD_PRE_INVALID")
                    value=int(raw_value)
                else:
                    raise ScopeReplayError("UNSUPPORTED_RAW_METHOD_PRE_KIND")
                frame["raw_fields"][name]=value
            else:
                raise ScopeReplayError("UNKNOWN_METHOD_PRE_EVENT")
            continue

    if (open_by_id or root_stacks or pending_select or
        any(q for q in ready_selections.values()) or
        not selected_attempts or not method_scopes or
        method_pre_belongs_to_scope!=method_scopes):
        raise ScopeReplayError("UNBALANCED_OR_INCOMPLETE_REAL_CALL_TRACE")
    return {
        "schema":SCHEMA,
        "source_profile_git_blob_sha1":git_blob(profile),
        "select_PRE_records":selection_pre_records,
        "source_loop_skips_before_action_READY":sum(selection_skips.values()),
        "source_loop_skips_by_action":{
            f"{act}.{reason}":n for (act,reason),n in sorted(selection_skips.items())
        },
        "bounded_original_source_loop_skip_examples":bounded_source_skips,
        "source_BACKGROUND_exclusion_not_a_READY_failure":True,
        "selected_action_ready_original_calls":selected_attempts,
        "dynamic_method_calls_scope_linked":method_scopes,
        "exact_method_PRE_entries_linked":method_pre_belongs_to_scope,
        "uncorrelated_method_PRE_entries_or_fields":unlinked_legacy_method_pre,
        "complete_original_select_PRE_groups":selection_pre_complete,
        "root_and_parent_id_source":"EXPLICIT_GLOBAL_UNIQUE_CXX_RAII_STACK",
        "source_call_chain_time_collision_resolved":True,
        "max_observed_trace_stack_depth":max_depth,
        "observed_method_calls_by_site":dict(sorted(by_method.items())),
        "observed_parent_child_edges":{
            f"{src}>{dst}":n for (src,dst),n in sorted(by_method_edges.items())},
        "certified_false_method_returns":sum(false_by_rule.values()),
        "certified_false_method_returns_by_rule":dict(sorted(false_by_rule.items())),
        "bounded_false_method_examples":examples,
        "all_native_instrumented_methods_observed":False,
        "source_virtual_dispatch_exhaustive":False,
        "positive_FULL_action_READY_proven":0,
        "source_APL_priority_complete":False,
        "trainer_error_verdict_permitted":False,
        "WCL_API_calls":0,
        "raw_character_native_log_exported":False,
    }


def selftest()->dict:
    # Use minimal synthetic source: single APL row and two nested methods,
    # including explicit IDs so same timestamp cannot misattribute a field.
    from hashlib import sha256
    from general_rotation_original_pre_capture_engine_v1 import digest
    from general_rotation_call_scope_instrument_v1 import SCHEMA as TRACE_SCHEMA
    profile=b'warrior="Synthetic"\nspec=fury\nactions=/rampage\n'
    original=sha256(b"body").hexdigest()
    fields=[]
    for name in ("gcd_ready_ms","usable_while_casting"):
        fields.append({
            "source_node":"base_ready","source_path":"action.cpp",
            "source_git_blob_sha1":"e"*40,"source_method_body_sha256":original,
            "field_id":sha256(name.encode()).hexdigest(),"operand_name":name,
            "value_kind":"int" if name=="gcd_ready_ms" else "bool",
        })
    fields.append({
        "source_node":"base_action","source_path":"action.cpp",
        "source_git_blob_sha1":"e"*40,"source_method_body_sha256":"f"*64,
        "field_id":"c"*64,"operand_name":"repeat_cast_allowed",
        "value_kind":"bool",
    })
    tmpl={"schema":"ZrotGeneralRotationOriginalPRECaptureContractV1",
          "fields":fields}
    tmpl["template_sha256"]=digest(tmpl)
    sites=[
        {"method_key":"base_action","signature":"bool action_t::action_ready()",
         "class_anchor":None,"source_path":"action.cpp",
         "source_git_blob_sha1":"e"*40,"source_method_body_sha256":"f"*64,
         "fields":[]},
        {"method_key":"base_ready","signature":"bool action_t::ready()",
         "class_anchor":None,"source_path":"action.cpp",
         "source_git_blob_sha1":"e"*40,"source_method_body_sha256":original,
         "fields":fields[:2]},
    ]
    man={"schema":"ZrotGenericPassiveSelectTemplateManifestV1",
         "pinned_source_commit":"b522cded8c26b97dac03fdf56e57a03ec7e8faa6",
         "templates":[tmpl],"method_entry_sites":sites}
    receipt={
        "schema":TRACE_SCHEMA, "trace_marker":TRACE_MARK,
        "original_action_ready_call_count":1,"new_action_ready_calls":0,
        "method_PRE_marker_call_id_appended":True,
        "source_select_skip_marker":SKIP_MARK,
        "source_method_count":2
    }
    def trace(ev,kind,call,parent,root,method):
        return (TRACE_MARK+f"20|{ev}|{kind}|{call}|{parent}|{root}|"+
                f"{method}|default|1|rampage")
    def pre(method,ev,call,field="-",kind="-",value="-"):
        return (METHOD_MARK+f"20|default|1|rampage|{method}|{ev}|"+
                f"{field}|{kind}|{value}|{call}")
    select_records=[
        (SELECT_MARK+f"20|default|1|rampage|{sha256(name.encode()).hexdigest()}|"+
         ("int|1000" if name=="gcd_ready_ms" else "bool|1"))
        for name in sorted(SELECT_READS)
    ]
    events=[SKIP_MARK+"19|default|1|rampage|BACKGROUND"]+select_records+[
        trace("BEGIN","SELECT",10,0,10,"select_call"),
        trace("BEGIN","METHOD",11,10,10,"base_action"),
        pre("base_action","ENTRY",11),
        trace("BEGIN","METHOD",12,11,10,"base_ready"),
        pre("base_ready","ENTRY",12),
        pre("base_ready","FIELD",12,sha256(b"gcd_ready_ms").hexdigest(),"int","1000"),
        pre("base_ready","FIELD",12,sha256(b"usable_while_casting").hexdigest(),"bool","1"),
        trace("END","METHOD",12,11,10,"base_ready"),
        trace("END","METHOD",11,10,10,"base_action"),
        trace("END","SELECT",10,0,10,"select_call"),
    ]
    out=replay("\n".join(events),profile,man,receipt)
    assert out["selected_action_ready_original_calls"]==1
    assert out["source_loop_skips_by_action"]["rampage.BACKGROUND"]==1
    assert out["source_BACKGROUND_exclusion_not_a_READY_failure"] is True
    assert out["dynamic_method_calls_scope_linked"]==2
    assert out["max_observed_trace_stack_depth"]==3
    assert out["positive_FULL_action_READY_proven"]==0
    broken=[
        events[:5]+[events[4]]+events[5:], # duplicate method BEGIN id
        [x.replace("|12|11|10|base_ready","|12|10|10|base_ready")
         if "BEGIN|METHOD|12|" in x else x for x in events],
        [x.replace("|12", "|99") if x.startswith(METHOD_MARK)
         and "|base_ready|FIELD|" in x else x for x in events],
        events[:-1],
        [x.replace("|default|1|","|default|9|",1) if x.startswith(METHOD_MARK)
         else x for x in events],
    ]
    for records in broken:
        try:replay("\n".join(records),profile,man,receipt)
        except ScopeReplayError:pass
        else:raise AssertionError("UNSCOPED_OR_FORGED_METHOD_CALL_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":10,"synthetic_explicit_parent_edges_verified":True,
        "actual_native_RAII_call_evidence_tested":False,
        "positive_READY_certified":0,"WCL_API_calls":0,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--profile",type=Path)
    p.add_argument("--source-templates",type=Path)
    p.add_argument("--trace-receipt",type=Path)
    p.add_argument("--certified-false-guards",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    req=(a.native_log,a.profile,a.source_templates,a.trace_receipt)
    if all(x is None for x in req) and a.certified_false_guards is None:
        result=selftest()
    elif all(x is not None for x in req):
        result=replay(
            a.native_log.read_text(encoding="utf-8"),a.profile.read_bytes(),
            json.loads(a.source_templates.read_bytes()),
            json.loads(a.trace_receipt.read_bytes()),
            json.loads(a.certified_false_guards.read_bytes())
            if a.certified_false_guards else None)
    else:p.error("all four trace/source inputs required together")
    data=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(data)
    else:print(data.decode(),end="")


if __name__=="__main__":
    main()
