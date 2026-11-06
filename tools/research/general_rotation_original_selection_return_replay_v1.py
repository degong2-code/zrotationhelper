#!/usr/bin/env python3
"""Exact original select_action return witness, not independent action READY.

Root and nested SimC source list invocation identity is explicit in C++ RAII
markers. Return action source row is pinned by the original action-list
signature pointer. A Native READY true result is never inferred to be a
final choice without an observed C++ return. Prior exclusions are *native
source process observations*, not independently reconstructed mechanics.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import re

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_original_selection_return_producer_v1 import (
    SCHEMA as PRODUCER_SCHEMA, MARK as RETURN_MARK, RETURN_SITES
)
from general_rotation_root_resource_pre_producer_v1 import SCHEMA as MANA_SCHEMA
from general_rotation_select_pre_passive_producer_v1 import REVISION
from general_rotation_select_sweep_instrument_v1 import SWEEP_MARK
from general_rotation_time_scoped_priority_ir_v1 import SCHEMA as TEMPORAL_SCHEMA
from general_rotation_source_eligibility_decision_ir_v1 import POLICY
from simc_apl_semantic_ir_v2 import parse_profile, git_blob

SCHEMA="ZrotOriginalSourceReturnedActionFrontierV1"
NATIVE="ACTION_READY_CALLED"
SKIP="BACKGROUND_SKIP_BEFORE_READY"
WAIT="WAIT_ON_READY_BREAK"
HEXPAT=re.compile("[0-9a-f]{64}\\Z")


class SourceChoiceError(ValueError):
    pass


def replay(log:str,profile:bytes,temporal:dict,producer:dict,
           prior_mana_producer:dict)->dict:
    if (producer.get("schema")!=PRODUCER_SCHEMA or
        producer.get("source_revision")!=REVISION or
        producer.get("source_return_marker")!=RETURN_MARK or
        producer.get("source_return_kinds")!=sorted(RETURN_SITES) or
        producer.get("original_action_ready_call_count")!=1 or
        producer.get("additional_action_ready_RNG_resource_calls")!=0 or
        producer.get("original_return_paths_preserved") is not True or
        producer.get("prior_mana_source_receipt_sha256") !=
            sha256(canonical(prior_mana_producer)).hexdigest() or
        producer.get("source_before_sha256")!=prior_mana_producer.get("source_after_sha256") or
        prior_mana_producer.get("schema")!=MANA_SCHEMA):
        raise SourceChoiceError("SOURCE_PINNED_RETURN_PRODUCER_CHAIN_REQUIRED")
    if (temporal.get("schema")!=TEMPORAL_SCHEMA or
        temporal.get("product_policy_id")!=POLICY or
        temporal.get("source_profile_git_blob_sha1")!=git_blob(profile) or
        temporal.get("independent_FULL_READY_proven")!=0 or
        temporal.get("source_order_complete") is not False):
        raise SourceChoiceError("SOURCE_TIME_FRONTIER_CONTRACT_MISMATCH")
    rows=parse_profile(profile,require_source=False)["action_lists"]
    expected={}
    for sw in temporal["observed_time_scoped_selection_frontiers"]:
        sid=sw.get("sweep_call_id")
        if (type(sid)!=int or sid<=0 or sid in expected or
            sw.get("source_list") not in rows):
            raise SourceChoiceError("UNMAPPED_SOURCE_SWEEP")
        expected[sid]=sw
    if len(expected)!=temporal.get("source_sweep_count"):
        raise SourceChoiceError("SOURCE_SWEEP_COUNT_CHANGED")
    open_stack=[]
    active=set()
    completed={}
    returned={}
    nested_by_parent={}
    counts=Counter()
    chosen_rows=Counter()
    examples=[]
    for line in log.splitlines():
        if SWEEP_MARK in line:
            if line.count(SWEEP_MARK)!=1:
                raise SourceChoiceError("AMBIGUOUS_SWEEP_ID")
            p=line.split(SWEEP_MARK,1)[1].strip().split("|")
            if len(p)!=10:
                raise SourceChoiceError("BAD_SWEEP_LOG_RECORD")
            clock,direction,sid_s,parent_s,root_s,owner,mode,rnd,skill,span=p
            if not (clock.isdigit() and sid_s.isdigit() and parent_s.isdigit()
                    and root_s=="0"):
                raise SourceChoiceError("INVALID_SOURCE_CALL_ID")
            sid=int(sid_s);parent=int(parent_s);sw=expected.get(sid)
            if (sw is None or owner!=sw["source_list"] or
                parent!=sw["parent_sweep_call_id"] or
                (direction=="BEGIN" and int(clock)!=sw["at_simc_ms"])):
                raise SourceChoiceError("CALL_ID_SOURCE_SWEEP_IDENTITY_MISMATCH")
            if direction=="BEGIN":
                if (sid in active or sid in completed or
                    (parent!=open_stack[-1] if open_stack else parent!=0)):
                    raise SourceChoiceError("NONCAUSAL_NESTED_SOURCE_SWEEP")
                open_stack.append(sid)
                active.add(sid)
            elif direction=="END":
                if (not open_stack or open_stack[-1]!=sid or
                    sid not in returned or int(clock)<sw["at_simc_ms"]):
                    raise SourceChoiceError("SWEEP_WITHOUT_MATCHED_RETURN")
                open_stack.pop();active.remove(sid)
                completed[sid]=returned[sid]
                if parent:
                    nested_by_parent.setdefault(parent,[]).append(completed[sid])
            else:
                raise SourceChoiceError("UNDECLARED_SWEEP_DIRECTION")
            continue
        if RETURN_MARK not in line:
            continue
        if line.count(RETURN_MARK)!=1:
            raise SourceChoiceError("AMBIGUOUS_RETURN_SOURCE_MARKER")
        p=line.split(RETURN_MARK,1)[1].strip().split("|")
        if len(p)!=7:
            raise SourceChoiceError("INVALID_NATIVE_CHOICE_RETURN_SHAPE")
        at_s,sid_s,kind,owner,origin,ord_s,native=p
        if (not at_s.isdigit() or not sid_s.isdigit() or
            not ord_s.isdigit() or kind not in RETURN_SITES):
            raise SourceChoiceError("FORGED_NATIVE_SOURCE_RETURN")
        sid=int(sid_s);ordinal=int(ord_s)
        sw=expected.get(sid)
        if (sw is None or not open_stack or open_stack[-1]!=sid or
            sid in returned or owner!=sw["source_list"] or
            int(at_s)<sw["at_simc_ms"]):
            raise SourceChoiceError("RETURN_OUTSIDE_EXACT_NATIVE_SWEEP")
        events=sw["observed_candidate_event_stream"]
        is_null=kind.startswith("NULL_")
        if is_null:
            if (ordinal!=0 or origin!="-" or native!="-"):
                raise SourceChoiceError("NULL_RETURN_HAS_FAKE_SOURCE_ROW")
            row=None
            counts[kind]+=1
        else:
            if origin not in rows or ordinal<1 or ordinal>len(rows[origin]) or not native:
                raise SourceChoiceError("RETURN_POINTER_NOT_SOURCE_MAPPED")
            row=rows[origin][ordinal-1]
            if (not isinstance(row.get("source_sha256"),str) or
                not HEXPAT.fullmatch(row["source_sha256"])):
                raise SourceChoiceError("RETURN_SOURCE_ROW_HASH_MISSING")
            if kind=="DIRECT":
                if origin!=owner:
                    raise SourceChoiceError("DIRECT_RETURN_OUTSIDE_CURRENT_LIST")
                if not events or events[-1].get("stage")!=NATIVE or not events[-1].get(
                        "simc_NATIVE_return_post_comparator") is True:
                    raise SourceChoiceError("DIRECT_RETURN_WITHOUT_LAST_TRUE_READY")
                source=events[-1]
                if (source.get("ordinal_one_based")!=ordinal or
                    source.get("source_row_sha256")!=row["source_sha256"] or
                    source.get("source_action")!=row["action"] or
                    row["action"] in ("call_action_list","variable")):
                    raise SourceChoiceError("DIRECT_RETURN_SOURCE_ACTION_MISMATCH")
            elif kind=="CHILD_PROPAGATED":
                if (not events or events[-1].get("source_action")!="call_action_list" or
                    events[-1].get("stage")!=NATIVE or
                    events[-1].get("simc_NATIVE_return_post_comparator") is not True):
                    raise SourceChoiceError("CHILD_RETURN_WITHOUT_CALL_ACTION_LIST")
                children=nested_by_parent.get(sid,[])
                if (not children or children[-1]["row"] is None or
                    children[-1]["origin"]!=origin or
                    children[-1]["ordinal"]!=ordinal):
                    raise SourceChoiceError("PROPAGATED_ACTION_NOT_FROM_CHILD_RETURN")
            counts[kind]+=1
            chosen_rows[row["action"]]+=1
        seen=events
        prior_native_false=sum(e["stage"]==NATIVE and
            e.get("simc_NATIVE_return_post_comparator") is False for e in seen)
        prior_background=sum(e["stage"]==SKIP for e in seen)
        prior_control=sum(e["stage"]==NATIVE and
            e.get("simc_NATIVE_return_post_comparator") is True and
            e["source_action"] in ("call_action_list","variable") for e in seen)
        event={
            "sweep_call_id":sid,"parent_sweep_call_id":sw["parent_sweep_call_id"],
            "at_simc_ms":sw["at_simc_ms"],"source_list":owner,
            "return_kind":kind,"origin":origin,"ordinal":ordinal,
            "row":row,"action":None if row is None else row["action"],
            "prior_native_false_observed":prior_native_false,
            "prior_background_skips_observed":prior_background,
            "prior_true_control_actions_observed":prior_control,
            "source_order_deterministic":sw["source_order_sampling_deterministic"],
        }
        returned[sid]=event
        if not sw["parent_sweep_call_id"]:
            counts["root_sweep_returned"]+=1
            if row is not None:
                counts["root_sweep_returned_action_source_row"]+=1
                if len(examples)<16:
                    examples.append({
                        "sweep_call_id":sid,
                        "at_simc_ms":sw["at_simc_ms"],
                        "return_kind":kind,
                        "source_list":origin,
                        "source_ordinal":ordinal,
                        "source_row_sha256":row["source_sha256"],
                        "source_action":row["action"],
                        "prior_native_false_observed":prior_native_false,
                        "prior_background_skips_observed":prior_background,
                        "full_READY":"UNKNOWN",
                    })
    if (open_stack or active or len(completed)!=len(expected) or
        len(returned)!=len(expected)):
        raise SourceChoiceError("INCOMPLETE_NATIVE_RETURN_SWEEP_COHORT")
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "source_profile_git_blob_sha1":git_blob(profile),
        "source_sweeps_exact_cxx_return":len(expected),
        "counts":dict(sorted(counts.items())),
        "bounded_root_return_examples":examples,
        "source_action_return_counts":dict(sorted(chosen_rows.items())),
        "return_is_observed_original_simc_selection_not_independent_READY":True,
        "prior_native_false_not_independently_proven_NOT_READY":True,
        "complete_source_order_proven":False,
        "independent_FULL_READY_proven":0,
        "practice_error_feedback_permitted":False,
        "WCL_API_calls":0,
    }


def selftest()->dict:
    source=(b'warrior="Synthetic"\nspec=fury\n'
            b'actions=/foo\n'
            b'actions+=/call_action_list,name=child\n'
            b'actions.child=/bar\n')
    rows=parse_profile(source,require_source=False)["action_lists"]
    def attempt(row,ordinal,yes):
        return {"stage":NATIVE,"source_action":row["action"],
                "source_row_sha256":row["source_sha256"],
                "ordinal_one_based":ordinal,
                "simc_NATIVE_return_post_comparator":yes}
    a=rows["default"];b=rows["child"]
    sweeps=[
        {"sweep_call_id":11,"parent_sweep_call_id":0,"source_list":"default",
         "at_simc_ms":20,"source_order_sampling_deterministic":True,
         "observed_candidate_event_stream":[attempt(a[0],1,False),attempt(a[1],2,True)]},
        {"sweep_call_id":12,"parent_sweep_call_id":11,"source_list":"child",
         "at_simc_ms":20,"source_order_sampling_deterministic":True,
         "observed_candidate_event_stream":[attempt(b[0],1,True)]}
    ]
    temporal={"schema":TEMPORAL_SCHEMA,"product_policy_id":POLICY,
              "source_profile_git_blob_sha1":git_blob(source),
              "source_order_complete":False,"independent_FULL_READY_proven":0,
              "source_sweep_count":len(sweeps),
              "observed_time_scoped_selection_frontiers":sweeps}
    mana={"schema":MANA_SCHEMA,"source_after_sha256":"0"*64}
    producer={"schema":PRODUCER_SCHEMA,"source_revision":REVISION,
              "source_return_marker":RETURN_MARK,
              "source_return_kinds":sorted(RETURN_SITES),
              "original_action_ready_call_count":1,
              "additional_action_ready_RNG_resource_calls":0,
              "original_return_paths_preserved":True,
              "prior_mana_source_receipt_sha256":sha256(canonical(mana)).hexdigest(),
              "source_before_sha256":"0"*64}
    def sweep(event,sid,parent,owner):
        return (SWEEP_MARK+f"20|{event}|{sid}|{parent}|0|{owner}|0|0|1|2")
    direct=RETURN_MARK+"20|12|DIRECT|child|child|1|bar"
    child=RETURN_MARK+"20|11|CHILD_PROPAGATED|default|child|1|bar"
    events=[
        sweep("BEGIN",11,0,"default"),
        sweep("BEGIN",12,11,"child"),direct,
        sweep("END",12,11,"child"),child,
        sweep("END",11,0,"default")]
    def check(x):return replay("\n".join(x),source,temporal,producer,mana)
    result=check(events)
    assert result["counts"]["root_sweep_returned_action_source_row"]==1
    assert result["counts"]["DIRECT"]==1
    assert result["counts"]["CHILD_PROPAGATED"]==1
    assert result["independent_FULL_READY_proven"]==0
    for invalid in (
        events[:3]+events[4:],
        events[:4]+[child.replace("|child|1|","|child|2|")]+events[5:],
        events[:4]+[direct]+events[4:],
        [events[0],events[2],events[1]]+events[3:],
        events[:4]+[child.replace("|11|","|99|")]+events[5:],
    ):
        try:check(invalid)
        except SourceChoiceError:pass
        else:raise AssertionError("UNPINNED_NATIVE_RETURN_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":9,"Native_CXX_executed":False,
        "independent_FULL_READY_proven":0,"WCL_API_calls":0
    }


if __name__=="__main__":
    print(canonical(selftest()).decode(),end="")
