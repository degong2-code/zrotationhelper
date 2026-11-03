#!/usr/bin/env python3
"""Bounded independent AST replay using verified Native SimC pre-IF operands.

Two numeric input facts are passively sampled before the one original native
if_expr evaluation: player primary resource (Rage for pinned Fury source) and
sim.active_enemies. This module evaluates ONLY IF expressions whose every
symbol is within {rage, active_enemies}. It never uses Native IF outcome as
input. Other symbols, variables, proc, cooldown and talent remain UNKNOWN.

Require source/effective APL row equality, pinned official input profile,
native actual capture identity, exact passive IF event/ready attempt matching,
and original-vs-instrumented JSON2 sequence nonperturbation by workflow.
No WCL and no user gameplay interpretation. No-arg synthetic self-test.
"""
from __future__ import annotations
import argparse
from collections import Counter,deque,defaultdict
import hashlib,json,math,re
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile,evaluate_ast,ast_symbols,truth
from simc_native_select_trace_audit_v1 import audit_dir,MARK
from simc_native_if_condition_coverage_v1 import parse_if
from simc_native_if_pre_operand_instrument_v1 import MARK as FACT_MARK

PINNED_FURY_BLOB="3225992ed5b754ad5d61e8b785d9d859f1eed1be"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SCHEMA="ZrotNativeIndependentPreIfRestrictedOperandReplayV1"
KNOWN={"rage","active_enemies"}
class OperandReplayError(ValueError):pass

def sha(x):return hashlib.sha256(x).hexdigest()

def parse_fact(line):
    i=line.find(FACT_MARK)
    if i<0:return None
    x=line[i:].strip().split("|")
    if (len(x)!=9 or not re.fullmatch(r"[0-9]+",x[1]) or
        not re.fullmatch(r"[0-9]+",x[3]) or
        not re.fullmatch(r"-?[0-9]+",x[6]) or
        not re.fullmatch(r"[0-9]+",x[8]) or x[5] not in ("0","1")):
        raise OperandReplayError("NATIVE_PRE_FACT_RECORD_MALFORMED")
    try:value=float(x[7])
    except (ValueError,OverflowError):raise OperandReplayError("RESOURCE_PRE_NOT_FINITE")
    if not math.isfinite(value) or abs(value)>1e9:
        raise OperandReplayError("RESOURCE_PRE_VALUE_OUT_OF_BOUNDS")
    if int(x[8])>10000:raise OperandReplayError("ACTIVE_ENEMIES_OUT_OF_BOUNDS")
    return {"time_ms":int(x[1]),"list":x[2],"ordinal":int(x[3]),
        "native_name":x[4],"native_if_bool":int(x[5]),
        "primary_resource_id":int(x[6]),"primary_resource_value":value,
        "active_enemies":int(x[8])}

def exact_key(d):
    return (d["time_ms"],d["list"],d["ordinal"],d["native_name"])

def get_native_attempt(line):
    i=line.find(MARK)
    if i<0:return None
    parts=line[i:].strip().split("|")
    if parts[1]!="ATTEMPT":return None
    if len(parts)!=8 or not parts[2].isdigit() or not parts[5].isdigit() or parts[7] not in ("0","1"):
        raise OperandReplayError("NATIVE_ATTEMPT_SCHEMA_CHANGED")
    return {"time_ms":int(parts[2]),"list":parts[4],"ordinal":int(parts[5]),
            "visited_list":parts[3],"native_name":parts[6],
            "ready":int(parts[7])}

def evaluate_sample(fact,row):
    if not fact or "if" not in row["expression_fields"]:
        return "UNKNOWN_IF_NOT_SAMPLED",None
    expr=row["expression_fields"]["if"]
    symbols=set(expr["symbols"])
    missing=symbols-KNOWN
    facts={"rage":fact["primary_resource_value"],
           "active_enemies":fact["active_enemies"]}
    # Three-valued soundness: if an unknown AND operand is irrelevant
    # because the known side is false, or an unknown OR operand is
    # irrelevant because the known side is true, the result is provable.
    # UNKNOWN is still required when unknown operands can change truth.
    independently=evaluate_ast(expr["ast"],facts)
    check=truth(independently)
    if check is None:
        return ("UNKNOWN_UNSAMPLED_SYMBOLS" if missing
                else "UNKNOWN_NUMERIC_RESULT"),None
    actual=1 if check else 0
    if actual!=fact["native_if_bool"]:
        raise OperandReplayError(
            "INDEPENDENT_AST_VS_NATIVE_IF_TRUTH_CONFLICT:"
            +row["list"]+":"+str(row["index"]))
    return ("MATCH_AST_DETERMINATE_WITH_MISSING_SYMBOLS" if missing
            else "MATCH_AST_FROM_PRE_OPERANDS"),{
         "independent_result_bool":actual,
         "unobserved_but_logically_irrelevant_symbols":sorted(missing),
         "native_if_bool_for_comparison_only":fact["native_if_bool"],
         "source_condition":expr["source"],
         "source_expression_symbols":sorted(symbols),
         "resource_at_pre_evaluation":fact["primary_resource_value"],
         "active_enemies_at_pre_evaluation":fact["active_enemies"]}

def analyze_trace(text,ir,*,capture_examples=12):
    lists=ir["action_lists"]
    pending_if=defaultdict(deque)
    pending_fact=defaultdict(deque)
    outstanding=defaultdict(deque)
    counts=Counter()
    matched_examples=[]
    compact_fact_ledger=[]
    resource_kinds=set()
    rows_with_match=Counter()
    for line in text.splitlines():
        original_if=parse_if(line)
        if original_if:
            record={"time_ms":original_if["t"],"list":original_if["list"],
                    "ordinal":original_if["ordinal"],
                    "native_name":original_if["native_name"],
                    "native_if_bool":original_if["result"]}
            pending_if[exact_key(record)].append(record)
            counts["original_native_if_reports"]+=1
            continue
        fact=parse_fact(line)
        if fact:
            k=exact_key(fact)
            if not pending_if[k]:
                raise OperandReplayError("PRE_OPERAND_FACT_WITHOUT_ORIGINAL_NATIVE_IF")
            earlier=pending_if[k].popleft()
            if earlier["native_if_bool"]!=fact["native_if_bool"]:
                raise OperandReplayError("PASSIVE_SOURCE_FACT_IF_RESULT_MISMATCH")
            pending_fact[k].append(fact)
            resource_kinds.add(fact["primary_resource_id"])
            counts["passive_pre_facts_paired"]+=1
            continue
        attempt=get_native_attempt(line)
        if not attempt:continue
        counts["all_native_action_ready_attempts"]+=1
        name=attempt["list"]
        index=attempt["ordinal"]-1
        if name not in lists or not 0<=index<len(lists[name]):
            raise OperandReplayError("NATIVE_ATTEMPT_POINTER_ROW_MISSING")
        row=lists[name][index]
        k=exact_key(attempt)
        fact=pending_fact[k].popleft() if pending_fact[k] else None
        if fact and fact["native_if_bool"]==0 and attempt["ready"]==1:
            raise OperandReplayError("NATIVE_IF_FALSE_BUT_ACTION_READY_TRUE")
        if fact:
            counts["facts_attached_to_actual_ready_attempts"]+=1
            state,detail=evaluate_sample(fact,row)
            counts[state]+=1
            compact_fact_ledger.append({
               "at_ms":fact["time_ms"],"source_list":name,
               "source_index":index,"source_line_sha256":row["source_sha256"],
               "native_action":row["action"],"native_name":attempt["native_name"],
               "native_if_result_verification_only":fact["native_if_bool"],
               "native_ready_verification_only":attempt["ready"],
               "pre_primary_resource_id":fact["primary_resource_id"],
               "pre_primary_resource_value":fact["primary_resource_value"],
               "pre_active_enemies":fact["active_enemies"],
               "source_if":row["expression_fields"].get("if",{}).get("source"),
               "source_if_symbols":row["expression_fields"].get("if",{}).get("symbols"),
               "derived_AST_status":state,
               "independently_derived_bool":detail["independent_result_bool"] if detail else None
            })
            if detail:
                rows_with_match[name+":"+str(index)]+=1
                if len(matched_examples)<capture_examples:
                    matched_examples.append({
                       "source_list":name,"source_index":index,
                       "source_line":row["source_line"],
                       "action":row["action"],"at_ms":fact["time_ms"],
                       "source_line_sha256":row["source_sha256"],
                       **detail})
        else:
            counts["native_attempt_without_if_evaluation"]+=1
    leftover=sum(len(q) for q in pending_if.values())+sum(len(q) for q in pending_fact.values())
    if leftover:
        raise OperandReplayError("UNMATCHED_PRE_OPERAND_OR_IF_RECORDS:"+str(leftover))
    if len(resource_kinds)!=1:raise OperandReplayError("NATIVE_PRIMARY_RESOURCE_KIND_CHANGED")
    if counts["passive_pre_facts_paired"]!=counts["facts_attached_to_actual_ready_attempts"]:
        raise OperandReplayError("PRE_EVAL_SOURCE_FACT_MATCH_INCOMPLETE")
    if counts["original_native_if_reports"]!=counts["passive_pre_facts_paired"]:
        raise OperandReplayError("NATIVE_IF_REPORT_COUNT_DRIFT")
    return {
        "counts":dict(sorted(counts.items())),
        "unique_primary_resource_ids":sorted(resource_kinds),
        "source_rows_with_independent_AST_matches":dict(sorted(rows_with_match.items())),
        "independent_matched_examples":matched_examples,
        "all_native_if_pre_fact_ledger":compact_fact_ledger,
        "all_other_unobserved_operands":"UNKNOWN",
        "native_IF_truth_as_python_operand":False,
        "native_spell_ready_used_as_AST_operand":False,
        "pristine_action_nonperturbation_required":True,
        "actual_Fury_primary_resource_source":"warrior_t::primary_resource RETURNS RESOURCE_RAGE",
        "source_active_enemies_semantics":"sim->active_enemies direct reference"}

def verify_folder(folder,targets,source_ir):
    folder=folder.resolve(strict=True)
    audit=audit_dir(folder,targets)
    effective=parse_profile((folder/"simc_effective_actions.simc").read_bytes(),
                            require_source=False)
    if (set(effective["action_lists"])!=set(source_ir["action_lists"]) or
        effective["action_list_counts"]!=source_ir["action_list_counts"]):
        raise OperandReplayError("NATIVE_EFFECTIVE_LIST_MISMATCH")
    for name in source_ir["action_lists"]:
        for src,native in zip(source_ir["action_lists"][name],effective["action_lists"][name]):
            for field in ("action","attributes","expression_fields"):
                if src[field]!=native[field]:
                    raise OperandReplayError("OFFICIAL_PROFILE_NATIVE_EFFECTIVE_DIFFERENCE")
    log=(folder/"simc_native_log.txt").read_bytes()
    summary=analyze_trace(log.decode("utf-8"),effective)
    if summary["counts"]["all_native_action_ready_attempts"]!=audit["source_action_ready_attempts"]["total"]:
        raise OperandReplayError("ACTUAL_READY_COUNT_DRIFT")
    summary["controlled_targets"]=targets
    summary["native_apl_sha256"]=audit["native_effective_apl_sha256"]
    summary["native_binary_sha256"]=audit["native_binary_sha256"]
    summary["actual_native_log_sha256"]=sha(log)
    return summary

def run(profile,st_dir,two_dir):
    original=profile.read_bytes()
    source=parse_profile(original,require_source=True,expected_git_blob=PINNED_FURY_BLOB)
    st=verify_folder(st_dir,1,source)
    two=verify_folder(two_dir,2,source)
    if (st["native_apl_sha256"]!=two["native_apl_sha256"] or
        st["native_binary_sha256"]!=two["native_binary_sha256"] or
        st["unique_primary_resource_ids"]!=two["unique_primary_resource_ids"]):
        raise OperandReplayError("ST_2T_NATIVE_IDENTITY_OR_RESOURCE_KIND_MISMATCH")
    count=sum(x["counts"].get("MATCH_AST_FROM_PRE_OPERANDS",0) for x in (st,two))
    partial=sum(x["counts"].get("MATCH_AST_DETERMINATE_WITH_MISSING_SYMBOLS",0)
                for x in (st,two))
    return {"schema":SCHEMA,"scope_policy_id":POLICY,
            "status":"INDEPENDENT_NUMERIC_AST_SUBSET_ONLY_NATIVE_OPERAND_PARITY",
            "source_pinned_profile_blob_sha1":PINNED_FURY_BLOB,
            "source_profile_sha256":sha(original),
            "restricted_accepted_symbol_set":sorted(KNOWN),
            "source_only_pre_operand_numeric_ast_matches":count,
            "source_partial_operand_three_valued_ast_matches":partial,
            "total_independent_conclusive_AST_matches":count+partial,
            "compact_actual_native_pre_IF_fact_rows":sum(
                len(x["all_native_if_pre_fact_ledger"]) for x in (st,two)),
            "native_pre_operand_readout_used":True,
            "native_if_truth_used_as_AST_input":False,
            "remaining_native_if_expression_semantics":"UNKNOWN",
            "native_variable_side_effect_parity":"NOT_PROVEN",
            "native_all_ability_readiness_parity":"NOT_PROVEN",
            "full_General_Rotation_model_complete":False,
            "WCL_comparison_eligible":False,"MAIN_promotion":False,
            "st":st,"two_target":two}


def selftest():
    model=parse_profile(
       b"actions=foo,if=rage>100\n"
       b"actions+=/bar,if=active_enemies=2\n"
       b"actions+=/baz,if=buff.recklessness.up&rage>=100\n",
       require_source=False)
    row=model["action_lists"]["default"]
    base={"time_ms":1,"list":"default","ordinal":1,"native_name":"foo",
          "native_if_bool":1,"primary_resource_id":3,
          "primary_resource_value":101.0,"active_enemies":1}
    state,d=evaluate_sample(base,row[0])
    assert state=="MATCH_AST_FROM_PRE_OPERANDS"
    assert d["independent_result_bool"]==1
    assert evaluate_sample({**base,"ordinal":2,"native_name":"bar",
                            "native_if_bool":1,"active_enemies":2},row[1])[0]==state
    assert evaluate_sample({**base,"ordinal":3,"native_name":"baz"},row[2])[0]=="UNKNOWN_UNSAMPLED_SYMBOLS"
    # Known false conjunct must yield an independent false result even when
    # the other symbol was not sampled. Known true OR must similarly win.
    orrow=parse_profile(b"actions=foo,if=talent.unknown|active_enemies=2\n",
                       require_source=False)["action_lists"]["default"][0]
    androw=parse_profile(b"actions=foo,if=talent.unknown&active_enemies=1\n",
                        require_source=False)["action_lists"]["default"][0]
    decisively_false={**base,"active_enemies":2,"native_if_bool":0}
    decisive_status,decisive=evaluate_sample(decisively_false,androw)
    assert decisive_status=="MATCH_AST_DETERMINATE_WITH_MISSING_SYMBOLS"
    assert decisive["independent_result_bool"]==0
    decisively_true={**base,"active_enemies":2,"native_if_bool":1}
    true_status,true_payload=evaluate_sample(decisively_true,orrow)
    assert true_status=="MATCH_AST_DETERMINATE_WITH_MISSING_SYMBOLS"
    assert true_payload["independent_result_bool"]==1
    assert true_payload["unobserved_but_logically_irrelevant_symbols"]==["talent.unknown"]
    try:evaluate_sample({**base,"native_if_bool":0},row[0])
    except OperandReplayError:pass
    else:raise AssertionError("MISMATCH_NATIVE_IF_ACCEPTED")
    assert parse_fact("ZROT_NATIVE_IF_FACT_V1|1|default|1|foo|1|3|101|2")["primary_resource_value"]==101
    try:parse_fact("ZROT_NATIVE_IF_FACT_V1|1|default|1|foo|1|3|nan|2")
    except OperandReplayError:pass
    else:raise AssertionError("NON_FINITE_PRE_OPERAND_ACCEPTED")
    trace="\n".join([
      "ZROT_NATIVE_IF_V1|1|default|1|foo|1",
      "ZROT_NATIVE_IF_FACT_V1|1|default|1|foo|1|3|101|2",
      "ZROT_NATIVE_SELECT_V1|ATTEMPT|1|default|default|1|foo|1",
      "ZROT_NATIVE_IF_V1|1|default|3|baz|0",
      "ZROT_NATIVE_IF_FACT_V1|1|default|3|baz|0|3|101|2",
      "ZROT_NATIVE_SELECT_V1|ATTEMPT|1|default|default|3|baz|0",
      "ZROT_NATIVE_SELECT_V1|ATTEMPT|1|default|default|2|bar|0"])
    analysis=analyze_trace(trace,model)
    assert analysis["counts"]["MATCH_AST_FROM_PRE_OPERANDS"]==1
    assert analysis["counts"]["UNKNOWN_UNSAMPLED_SYMBOLS"]==1
    assert len(analysis["all_native_if_pre_fact_ledger"])==2
    assert analysis["all_native_if_pre_fact_ledger"][0]["independently_derived_bool"]==1
    assert analysis["counts"]["native_attempt_without_if_evaluation"]==1
    assert analysis["native_IF_truth_as_python_operand"] is False
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":15,
            "actual_native_executed":False,"WCL_API_calls":0,
            "independent_numeric_subset_test":True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path)
    p.add_argument("--native-st-dir",type=Path)
    p.add_argument("--native-2t-dir",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    paths=(a.profile,a.native_st_dir,a.native_2t_dir)
    if all(x is None for x in paths):data=selftest()
    elif all(x is not None for x in paths):data=run(*paths)
    else:p.error("all source-identity inputs required or none")
    blob=(json.dumps(data,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("NATIVE_IF_INDEPENDENT_AST_SUBSET_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
