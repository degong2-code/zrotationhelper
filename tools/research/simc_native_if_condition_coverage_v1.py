#!/usr/bin/env python3
"""Native SimC IF condition evaluation coverage at genuine action_ready() site.

Consumes a passive C++ hook that wraps exactly one original native
if_expr->success() and retains signed pointer ownership per APL row.
A False action_ready result with no IF evaluation does NOT imply IF false.
Unmatched/ambiguous IF hooks are UNKNOWN, never backfilled from action_ready.
The report is native-conditional observational evidence only. It cannot
declare independent expression arithmetic or cooldown parity.

Default invocation self-tests synthetic traces. No WCL or game addon input.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter,defaultdict
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile
from simc_native_select_trace_audit_v1 import audit_dir,MARK
from simc_native_foreground_structural_replay_v1 import (
    unpack_marker, root_foreground_groups, StructuralError
)

IF_MARK="ZROT_NATIVE_IF_V1|"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SCHEMA="ZrotNativeIfConditionEvaluationCoverageV1"

class IfAuditError(ValueError):pass

def sha(v):return hashlib.sha256(v).hexdigest()

def parse_if(line):
    p=line.find(IF_MARK)
    if p<0:return None
    parts=line[p:].strip().split("|")
    if (len(parts)!=6 or
        not re.fullmatch(r"[0-9]+",parts[1]) or
        not re.fullmatch(r"[0-9]+",parts[3]) or
        parts[5] not in ("0","1")):
        raise IfAuditError("NATIVE_IF_EVAL_MARKER_MALFORMED")
    return {"type":"NATIVE_IF","t":int(parts[1]),
       "list":parts[2],"ordinal":int(parts[3]),
       "native_name":parts[4],"result":int(parts[5])}


def audit_if_coverage(log,source,*,sample_limit=15):
    lists=source["action_lists"]
    native_stack=[]
    root=None
    all_roots=[]
    out_of_root=0
    records=0
    for line in log.splitlines():
        e=parse_if(line)
        if e is not None:
            records+=1
            if root is not None:root.append(e)
            else:out_of_root+=1
            continue
        m=unpack_marker(line)
        if m is None:continue
        if m["type"]=="ENTER":
            if not native_stack:
                root=[] if m["mode"]=="FOREGROUND" else None
            native_stack.append(m["list"])
        elif not native_stack or m["list"]!=native_stack[-1]:
            raise IfAuditError("INCOMPATIBLE_NATIVE_SELECTION_STACK")
        if root is not None:root.append(m)
        if m["type"] in ("RETURN","NO_ACTION"):
            native_stack.pop()
            if not native_stack and root is not None:
                all_roots.append(root)
                root=None
    if native_stack or not all_roots:raise IfAuditError("NATIVE_IF_ROOT_SEQUENCE_INVALID")
    summary=Counter()
    samples=[]
    expressions=Counter()
    missing_source=Counter()
    matches=0
    for root_index,events in enumerate(all_roots):
        fifo=defaultdict(list)
        for e in events:
            if e["type"]=="NATIVE_IF":
                if (e["list"] not in lists or not 1<=e["ordinal"]<=len(lists[e["list"]])):
                    missing_source["source_pointer_unknown"]+=1
                    continue
                row=lists[e["list"]][e["ordinal"]-1]
                expression=row["expression_fields"].get("if")
                if expression is None:
                    missing_source["no_if_expr_on_pointer_row"]+=1
                    continue
                expression_text=expression["source"]
                expressions[expression_text]+=1
                fifo[(e["t"],e["list"],e["ordinal"],e["native_name"])].append(e)
                summary["native_if_eval_total"]+=1
                summary["native_if_true" if e["result"] else "native_if_false"]+=1
            elif e["type"]=="ATTEMPT":
                key=(e["t"],e["owner"],e["ordinal"],e["native_name"])
                candidates=fifo.pop(key,[])
                if len(candidates)==1:
                    verdict="OBSERVED_TRUE" if candidates[0]["result"] else "OBSERVED_FALSE"
                    summary["matched_if_evaluated_attempts"]+=1
                    if candidates[0]["result"]==0 and e["ready"]==1:
                        raise IfAuditError("NATIVE_IF_FALSE_BUT_ACTION_READY_TRUE")
                    if candidates[0]["result"]==1 and e["ready"]==0:
                        summary["if_true_but_action_ready_false"]+=1
                    if candidates[0]["result"]==0:
                        summary["if_false_and_action_ready_false"]+=1
                elif len(candidates)>1:
                    verdict="UNKNOWN_MULTIPLE_IF_EVALS"
                    summary["ambiguous_if_matches"]+=1
                else:
                    verdict="UNKNOWN_IF_NOT_OBSERVED"
                    summary["unobserved_if_at_attempt"]+=1
                summary["total_native_action_ready_attempts"]+=1
                if len(samples)<sample_limit:
                    sample={
                        "root_index":root_index,
                        "timestamp_ms":e["t"],
                        "source_list":e["owner"],
                        "source_index":e["ordinal"]-1 if e["ordinal"] else None,
                        "native_name":e["native_name"],
                        "native_action_ready_bit":e["ready"],
                        "native_if_evaluation":verdict,
                        "independent_ast_evaluation":"UNKNOWN_OPERAND_VALUES",
                        "reason_when_if_not_observed":"UNKNOWN_COOLDOWN_TARGET_OR_OTHER_GATE"
                    }
                    samples.append(sample)
        for unused in fifo.values():
            summary["if_evals_without_one_to_one_attempt"]+=len(unused)
    return {
        "schema":SCHEMA,"scope_policy_id":POLICY,
        "status":"NATIVE_IF_REACHED_RESULT_OBSERVED_NOT_INDEPENDENT_EXPRESSION_PARITY",
        "native_root_foreground_scans":len(all_roots),
        "native_if_all_events_including_non_foreground":records,
        "native_if_outside_foreground":out_of_root,
        "native_if_verified_source_expressions":len(expressions),
        "source_if_expression_eval_counts":dict(sorted(expressions.items())),
        "source_reconciliation_unknowns":dict(missing_source),
        "counts":dict(summary),"representative_attempts":samples,
        "absence_of_if_event_means_condition_false":False,
        "native_if_outcome_distinct_from_full_ready":True,
        "source_expression_ast_independent_state_values":"UNKNOWN",
        "native_spell_ready_parity":"NOT_PROVEN",
        "player_rotation_error_verdict":"UNKNOWN",
        "WCL_eligible":False,"MAIN_promotion":False}


def verify_native_folder(folder,targets,official):
    folder=folder.resolve(strict=True)
    proof=audit_dir(folder,targets)
    effective=(folder/"simc_effective_actions.simc").read_bytes()
    effective_ir=parse_profile(effective,require_source=False)
    if set(official["action_lists"])!=set(effective_ir["action_lists"]):
        raise IfAuditError("SOURCE_NATIVE_APL_LISTS_DIFFER")
    for name in official["action_lists"]:
        a,b=official["action_lists"][name],effective_ir["action_lists"][name]
        if len(a)!=len(b):raise IfAuditError("SOURCE_NATIVE_APL_ROWS_DIFFER")
        for x,y in zip(a,b):
            if (x["action"]!=y["action"] or x["attributes"]!=y["attributes"] or
                x["expression_fields"]!=y["expression_fields"]):
                raise IfAuditError("SOURCE_NATIVE_APL_EXPRESSION_CHANGED")
    log=(folder/"simc_native_log.txt").read_bytes()
    result=audit_if_coverage(log.decode("utf-8"),effective_ir)
    if result["native_root_foreground_scans"]!=proof["source_selection_calls"]["root_foreground_scans"]:
        raise IfAuditError("NATIVE_FOREGROUND_ROOTS_DIVERGED")
    if result["counts"].get("total_native_action_ready_attempts",0)!=proof["source_action_ready_attempts"]["total"]:
        raise IfAuditError("NATIVE_READY_COUNTS_DIVERGED")
    result["native_target_count_controlled"]=targets
    result["native_log_sha256"]=sha(log)
    result["native_effective_apl_sha256"]=sha(effective)
    result["native_binary_sha256"]=proof["native_binary_sha256"]
    return result


def run(profile,st,tw):
    raw=profile.read_bytes()
    official=parse_profile(raw)
    one=verify_native_folder(st,1,official)
    two=verify_native_folder(tw,2,official)
    if (one["native_binary_sha256"]!=two["native_binary_sha256"] or
        one["native_effective_apl_sha256"]!=two["native_effective_apl_sha256"]):
        raise IfAuditError("NATIVE_BUILD_MISMATCH_ST_TWO_TARGET")
    return {"schema":"ZrotNativeIfConditionFuryTwoTargetV1",
       "scope_policy_id":POLICY,
       "status":"REAL_NATIVE_IF_OUTCOME_COVERAGE_NO_INDEPENDENT_OPERAND_PARITY",
       "source_sha256":sha(raw),
       "st":one,"two_target":two,
       "if_value_source":"PINNED_NATIVE_ACTION_CPP_SINGLE_EVALUATION",
       "source_scans":one["native_root_foreground_scans"]+two["native_root_foreground_scans"],
       "native_if_result_positive_claims":"SOURCE_NATIVE_ONLY",
       "independent_if_semantic_parity":"NOT_PROVEN",
       "generic_gameplay_priority_model":"NOT_COMPLETE",
       "MAIN_promotion":False}


def selftest():
    source=parse_profile(b"actions=foo,if=foo.bar>0\n"
         b"actions+=/bar,if=foo.bar=0\n",require_source=False)
    events=[
       "ZROT_NATIVE_SELECT_V1|ENTER|1|default|FOREGROUND",
       "ZROT_NATIVE_IF_V1|1|default|1|foo|0",
       "ZROT_NATIVE_SELECT_V1|ATTEMPT|1|default|default|1|foo|0",
       "ZROT_NATIVE_IF_V1|1|default|2|bar|1",
       "ZROT_NATIVE_SELECT_V1|ATTEMPT|1|default|default|2|bar|1",
       "ZROT_NATIVE_SELECT_V1|RETURN|1|default|bar|DIRECT"
    ]
    result=audit_if_coverage("\n".join(events),source)
    assert result["counts"]["total_native_action_ready_attempts"]==2
    assert result["counts"]["matched_if_evaluated_attempts"]==2
    assert result["counts"]["native_if_false"]==1
    assert result["counts"]["native_if_true"]==1
    assert result["source_expression_ast_independent_state_values"]=="UNKNOWN"
    broken=events.copy()
    broken[2]=broken[2].replace("|foo|0","|foo|1")
    try:audit_if_coverage("\n".join(broken),source)
    except IfAuditError:pass
    else:raise AssertionError("ACCEPTED_IF_FALSE_READY_TRUE")
    incomplete=[events[0],events[2],events[3],events[4],events[5]]
    unknown=audit_if_coverage("\n".join(incomplete),source)
    assert unknown["counts"]["unobserved_if_at_attempt"]==1
    assert unknown["absence_of_if_event_means_condition_false"] is False
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":8,
       "real_native_executed":False,"independent_operand_parity_proven":False,"WCL_API_calls":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path)
    p.add_argument("--native-st-dir",type=Path)
    p.add_argument("--native-2t-dir",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    all_inputs=(args.profile,args.native_st_dir,args.native_2t_dir)
    if all(v is None for v in all_inputs):
        data=selftest()
    elif all(v is not None for v in all_inputs):
        data=run(*all_inputs)
    else:p.error("provide all three source pins or none")
    blob=(json.dumps(data,sort_keys=True,separators=(",",":"))+"\n").encode()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("xb") as f:f.write(blob)
        print("NATIVE_IF_CONDITION_COVERAGE_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
