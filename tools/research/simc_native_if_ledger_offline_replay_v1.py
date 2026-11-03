#!/usr/bin/env python3
"""Offline deterministic regression from frozen native PRE-IF operand ledger.

The Native simulation is run ONCE with official source and passive instrument.
Its 477 row-identified PRE operand facts are preserved in a derived receipt.
This validator checks that receipt against the exact pinned SimC APL and
recomputes every decidable source IF from numeric facts WITHOUT running native
SimC or calling WCL. Native IF truth is used only after evaluation.

It is a cheap independent-*execution* regression using the SAME Python AST
algorithm, not a second independent expression oracle. It cannot prove
unsampled buffs, charges, proc, variables, or complete Native parity.
"""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
from simc_apl_semantic_ir_v2 import parse_profile
from simc_native_if_pre_operand_replay_v1 import evaluate_sample,OperandReplayError

PINNED_PROFILE_BLOB="3225992ed5b754ad5d61e8b785d9d859f1eed1be"
PINNED_NATIVE_FACT_RECEIPT_SHA256="ebf8a902bff1c1167306217535ac5fc10466bc3a1d4512adc175a2449e7fbd13"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SCHEMA="ZrotIndependentSimcOperandLedgerOfflineRecheckV1"
class RegressionError(ValueError):pass

def sha(x):return hashlib.sha256(x).hexdigest()

def reevaluate(official,receipt):
    if (official.get("schema")!="ZrotSourceFaithfulSimcAplSemanticIRV2"
        or official.get("source_git_blob_sha1")!=PINNED_PROFILE_BLOB
        or official.get("scope_policy_id")!=POLICY
        or receipt.get("schema")!="ZrotNativeIndependentPreIfRestrictedOperandReplayV1"
        or receipt.get("scope_policy_id")!=POLICY
        or receipt.get("status")!="INDEPENDENT_NUMERIC_AST_SUBSET_ONLY_NATIVE_OPERAND_PARITY"
        or receipt.get("source_pinned_profile_blob_sha1")!=PINNED_PROFILE_BLOB
        or receipt.get("WCL_comparison_eligible") is not False
        or receipt.get("native_if_truth_used_as_AST_input") is not False):
        raise RegressionError("SOURCE_OR_RECEIPT_AUTHORITY_CHANGED")
    total=Counter()
    scenario_results={}
    for label,expected in (("st",255),("two_target",222)):
        cohort=receipt[label]
        ledger=cohort["all_native_if_pre_fact_ledger"]
        if (len(ledger)!=expected or
            cohort["counts"]["facts_attached_to_actual_ready_attempts"]!=expected):
            raise RegressionError("NATIVE_FACT_LEDGER_COUNT_DRIFT")
        summary=Counter()
        independent_examples=[]
        for d in ledger:
            list_name=d["source_list"]
            rows=official["action_lists"].get(list_name)
            index=d["source_index"]
            if rows is None or type(index)!=int or not 0<=index<len(rows):
                raise RegressionError("NATIVE_FACT_SOURCE_ROW_NOT_IN_APL")
            row=rows[index]
            expr=row["expression_fields"].get("if",{})
            if (d["source_line_sha256"]!=row["source_sha256"]
                or d["native_action"]!=row["action"]
                or d["source_if"]!=expr.get("source")
                or d["source_if_symbols"]!=expr.get("symbols")
                or d["pre_primary_resource_id"] not in cohort["unique_primary_resource_ids"]
                or d["native_if_result_verification_only"] not in (0,1)):
                raise RegressionError("NATIVE_SOURCE_FACT_RECONCILIATION_MISMATCH")
            fact={"primary_resource_value":d["pre_primary_resource_value"],
                  "active_enemies":d["pre_active_enemies"],
                  "native_if_bool":d["native_if_result_verification_only"]}
            status,value=evaluate_sample(fact,row)
            if status!=d["derived_AST_status"]:
                raise RegressionError("AST_REGRESSION_STATUS_CHANGED")
            number=value["independent_result_bool"] if value else None
            if number!=d["independently_derived_bool"]:
                raise RegressionError("AST_REGRESSION_CALCULATED_BOOLEAN_CHANGED")
            if value and len(independent_examples)<5:
                independent_examples.append({
                    "list":list_name,"source_index":index,
                    "source_if":expr.get("source"),
                    "pre_rage":fact["primary_resource_value"],
                    "pre_active_enemies":fact["active_enemies"],
                    "independent_bool":number,
                    "source_native_bool_comparison_only":fact["native_if_bool"],
                    "subset_verdict":status})
            summary[status]+=1
        if sum(summary.values())!=expected:
            raise RegressionError("AST_COVERAGE_COUNT_DRIFT")
        for key,value in summary.items():
            if value!=cohort["counts"].get(key,0):
                raise RegressionError("NATIVE_OBSERVED_AST_COUNT_CHANGED:"+key)
        scenario_results[label]={
            "facts_reverified":expected,
            "ast_verdict_counts":dict(sorted(summary.items())),
            "independent_replayed_boolean_count":sum(v for k,v in summary.items() if k.startswith("MATCH_")),
            "replayed_examples":independent_examples,
            "native_binary_was_executed_in_this_validation":False}
        total.update(summary)
    if total["MATCH_AST_FROM_PRE_OPERANDS"]!=3 or total["MATCH_AST_DETERMINATE_WITH_MISSING_SYMBOLS"]!=63:
        raise RegressionError("REFERENCE_NUMERIC_COVERAGE_CHANGED")
    return {"schema":SCHEMA,"scope_policy_id":POLICY,
        "status":"REPRODUCED_NATIVE_BOUNDED_PRE_FACT_AST_FROM_IMMUTABLE_RECEIPT",
        "pinned_native_pre_fact_receipt_sha256":PINNED_NATIVE_FACT_RECEIPT_SHA256,
        "total_native_IF_pre_facts_replayed":477,
        "fully_known_numeric_AST_matches":total["MATCH_AST_FROM_PRE_OPERANDS"],
        "decisive_partial_three_valued_AST_matches":total["MATCH_AST_DETERMINATE_WITH_MISSING_SYMBOLS"],
        "known_native_IF_checks_correctly_recomputed":66,
        "IF_checks_with_unverified_other_operands":411,
        "native_If_outcome_used_as_AST_input":False,
        "native_simc_executed_in_recheck":False,
        "independent_second_language_or_implementation_oracle":False,
        "General_Rotation_priority_model_complete":False,
        "WCL_comparison_eligible":False,"MAIN_promotion":False,
        **scenario_results}


def selftest():
    f=b"actions=foo,if=rage>100\n"
    a=parse_profile(f,require_source=False)
    a["source_git_blob_sha1"]=PINNED_PROFILE_BLOB
    fact={
        "source_list":"default","source_index":0,
        "source_line_sha256":a["action_lists"]["default"][0]["source_sha256"],
        "native_action":"foo","source_if":"rage>100",
        "source_if_symbols":["rage"],"pre_primary_resource_id":3,
        "native_if_result_verification_only":1,
        "pre_primary_resource_value":101.0,"pre_active_enemies":1,
        "derived_AST_status":"MATCH_AST_FROM_PRE_OPERANDS",
        "independently_derived_bool":1}
    report={"schema":"ZrotNativeIndependentPreIfRestrictedOperandReplayV1",
        "scope_policy_id":POLICY,
        "status":"INDEPENDENT_NUMERIC_AST_SUBSET_ONLY_NATIVE_OPERAND_PARITY",
        "source_pinned_profile_blob_sha1":PINNED_PROFILE_BLOB,
        "WCL_comparison_eligible":False,"native_if_truth_used_as_AST_input":False}
    for label,n in (("st",255),("two_target",222)):
        report[label]={
            "all_native_if_pre_fact_ledger":[dict(fact) for _ in range(n)],
            "counts":{"facts_attached_to_actual_ready_attempts":n,
                      "MATCH_AST_FROM_PRE_OPERANDS":n},
            "unique_primary_resource_ids":[3]}
    try:reevaluate(a,report)
    except RegressionError as e:
        assert "REFERENCE_NUMERIC_COVERAGE_CHANGED" in str(e)
    else:raise AssertionError("ACCEPTED_WRONG_NATIVE_REFERENCE_COHORT_COUNTS")
    bad=json.loads(json.dumps(report))
    bad["st"]["all_native_if_pre_fact_ledger"][0]["native_if_result_verification_only"]=0
    try:reevaluate(a,bad)
    except OperandReplayError:pass
    else:raise AssertionError("NATIVE_BOOLEAN_MISMATCH_NOT_DETECTED")
    bad=json.loads(json.dumps(report))
    bad["st"]["all_native_if_pre_fact_ledger"][0]["source_line_sha256"]="wrong"
    try:reevaluate(a,bad)
    except RegressionError:pass
    else:raise AssertionError("SOURCE_LINE_IDENTITY_NOT_ENFORCED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":3,
      "native_simc_run":False,"WCL_API_calls":0,
      "independent_second_implementation_oracle":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--native-pre-fact-receipt",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if not args.official_profile and not args.native_pre_fact_receipt:
        result=selftest()
    elif args.official_profile and args.native_pre_fact_receipt:
        raw=args.native_pre_fact_receipt.read_bytes()
        if sha(raw)!=PINNED_NATIVE_FACT_RECEIPT_SHA256:
            raise RegressionError("PINNED_NATIVE_PRE_FACT_BYTES_DIFFER")
        profile=parse_profile(args.official_profile.read_bytes(),require_source=True,
                              expected_git_blob=PINNED_PROFILE_BLOB)
        result=reevaluate(profile,json.loads(raw))
    else:p.error("both pinned inputs required, or neither for self-test")
    blob=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("xb") as f:f.write(blob)
        print("NATIVE_PRE_FACT_OFFLINE_RECHECK_SHA256="+sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
