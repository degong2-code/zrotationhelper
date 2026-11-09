#!/usr/bin/env python3
"""Generic source-list competing-candidate proof frontier for pinned SimC.

Consumes an *existing independently audited* source-competitor evidence ledger,
a SHA-pinned original SimC APL profile and declarative SpecAdapter. Recomputes
source IF FALSE/TRUE using the existing tri-state APL AST; imports a previously
source-certified local necessary negative gate only from an exact pinned receipt.
A native POST false return alone is always UNKNOWN. One negative necessary
gate means only the *specific APL occurrence* is excluded, not global spell
availability. No spell/class semantics or target threshold in generic logic.

The source-list path is incomplete as a global priority path when parent
CALL/RUN/movement/other candidates are unproven. Selected SimC return never
proves full READY or user dummy errors. Default runs synthetic checks.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import parse_profile, git_blob, evaluate_ast, truth, canonical
from general_rotation_source_if_minimal_witness_v1 import sufficient_partial_source_witness
from general_rotation_decision_proof_engine_v1 import (
    Identity, Fact, GateContract, decide_candidate, evaluate_priority,
    NOT_READY, UNKNOWN,
)

SCHEMA="ZrotGenericOriginalSimCSourceCompetitorExclusionFrontierV1"
ADAPTER="ZrotOriginalSimCSourceCompetitorPinnedAdapterV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
HEX64=re.compile(r"^[0-9a-f]{64}$")
HEX40=re.compile(r"^[0-9a-f]{40}$")
ROW_IF_FALSE="INDEPENDENT_SOURCE_ROW_IF_FALSE"
CLASS_FALSE="INDEPENDENT_SOURCE_LOCAL_READY_GUARD_FALSE"
NATIVE_ONLY="ORIGINAL_NATIVE_APL_IF_FALSE_INDEPENDENT_PRE_UNKNOWN"
GATE_IF="original_source_IF"
GATE_SPEC="original_source_necessary_guard"
LABELS=(ROW_IF_FALSE,CLASS_FALSE,NATIVE_ONLY)


class CompetitorEvidenceError(ValueError):
    pass


def require(ok:bool, code:str):
    if not ok:raise CompetitorEvidenceError(code)


def _finite_facts(facts:dict)->bool:
    return type(facts) is dict and all(
        type(k) is str and type(v) in (int,float,bool) and
        math.isfinite(float(v)) for k,v in facts.items()
    )


def _read_original_apl(profile:bytes,pin:dict)->dict:
    require(type(profile) is bytes and
            pin.get("source_profile_git_blob")==git_blob(profile) and
            HEX40.fullmatch(pin["source_profile_git_blob"]) is not None,
            "ORIGINAL_SOURCE_APL_PROFILE_BLOB_DRIFT")
    parsed=parse_profile(profile,require_source=True,
                         expected_git_blob=pin["source_profile_git_blob"])
    return parsed


def _fact(ident:Identity,gate:str,value:bool,t_ms:int,receipt:str)->Fact:
    # The external receipt must be authenticated upstream (exact SHA), and
    # its independent original PRE assertions rechecked before this call.
    return Fact(ident,gate,value,"INDEPENDENT_SOURCE_REPLAY",
                "SIMC_ORIGINAL_METHOD_PRE",t_ms,receipt)


def compile_frontier(ledger:dict,parsed:dict,pin:dict,
                     *,receipt_sha256:str)->dict:
    require(type(pin) is dict and pin.get("schema")==ADAPTER and
            pin.get("policy_id")==POLICY and
            type(pin.get("source_spec_key")) is str and
            type(pin.get("source_list")) is str and
            type(pin.get("source_revision")) is str and
            HEX40.fullmatch(pin["source_revision"]) is not None and
            type(pin.get("target_count")) is int and pin["target_count"]>=1 and
            type(pin.get("local_gate_rules")) is list and
            type(pin.get("expected_case_count")) is int and
            pin["expected_case_count"]>=1 and
            HEX64.fullmatch(receipt_sha256) is not None,
            "PINNED_COMPETITOR_SOURCE_ADAPTER_INVALID")
    rules={}
    for rule in pin["local_gate_rules"]:
        require(type(rule) is dict and
                set(rule)=={"action","original_numeric_field","false_value"} and
                type(rule["action"]) is str and
                type(rule["original_numeric_field"]) is str and
                type(rule["false_value"]) in (int,float,bool) and
                math.isfinite(float(rule["false_value"])) and
                rule["action"] not in rules,
                "DUPLICATE_OR_UNBOUND_LOCAL_SOURCE_RULE")
        rules[rule["action"]]=rule
    require(ledger.get("schema")==pin.get("original_ledger_schema") and
            ledger.get("product_policy_id")==POLICY and
            ledger.get("source_candidate_order_and_return_proven") is True and
            ledger.get("source_local_failure_not_skill_globally_unavailable") is True and
            ledger.get("general_rotation_priority_optimality_proven") is False and
            ledger.get("dummy_training_feedback_permitted") is False and
            ledger.get("WCL_API_calls")==0 and
            ledger.get("counts",{}).get("original_cpp_selected_2T_orb_rows")==
                pin["expected_case_count"],
            "ORIGINAL_SOURCE_LEDGER_PROOF_SCOPE_INVALID")
    source_list=parsed["action_lists"].get(pin["source_list"])
    require(type(source_list) is list and len(source_list)>0,
            "ORIGINAL_SOURCE_LIST_UNAVAILABLE")
    rows=ledger.get("two_target_winner_decisions")
    require(type(rows) is list and len(rows)==pin["expected_case_count"],
            "ORIGINAL_COMPETITOR_CASE_COUNT_CHANGED")
    seen_occurrences=set()
    counts=Counter()
    result=[]
    for case in rows:
        at=case.get("original_cpp_at_simc_ms")
        chosen_ord=case.get("chosen_source_row_ordinal")
        target=case.get("target_count_scenario")
        chosen_id=case.get("chosen_CPP_ready_root_id")
        require(type(at) is int and at>=0 and target==pin["target_count"] and
                type(chosen_ord) is int and 1<=chosen_ord<=len(source_list) and
                type(chosen_id) is int and chosen_id>0 and
                (at,chosen_id) not in seen_occurrences and
                case.get("WoW_dummy_error_verdict")=="UNKNOWN" and
                case.get("chosen_full_physical_READY_independently_proven") is False and
                case.get("earlier_all_possible_action_alternatives_exhaustively_proven") is False,
                "ORIGINAL_SELECTED_CASE_NOT_SAME_SOURCE_SCOPE")
        seen_occurrences.add((at,chosen_id))
        prior=case.get("earlier_source_rows")
        require(type(prior) is list and len(prior)==chosen_ord-1,
                "ORIGINAL_SOURCE_PREVIOUS_ROWS_NOT_CONTIGUOUS")
        used_roots={chosen_id}
        decisions=[]
        output=[]
        for pos,e in enumerate(prior,1):
            original=source_list[pos-1]
            root=e.get("original_cpp_ready_root_id")
            label=e.get("decision_evidence_class")
            action=e.get("source_action")
            require(type(root) is int and root>0 and root not in used_roots and
                    e.get("original_source_ordinal")==pos and
                    action==original["action"] and
                    original["behavior"]=="ACTION" and
                    label in LABELS and
                    e.get("native_CPP_source_POST_observed") is False and
                    e.get("independent_entire_spell_NOT_READY_proven") is False and
                    e.get("dummy_user_mistake_verdict")=="UNKNOWN" and
                    type(e.get("source_row_exclusion_condition_proven")) is bool,
                    "ORIGINAL_PHYSICAL_COMPETITOR_ROW_OR_PRE_CHANGED")
            used_roots.add(root)
            source_identity=Identity(
                scope=f"{pin['source_spec_key']}:{target}:{pin['source_list']}",
                source_sha256=original["source_sha256"],
                t_ms=at,ordinal=pos-1,occurrence=root
            )
            contract=GateContract(
                "PINNED_ORIGINAL_SIMC_SOURCE_LOCAL",
                (GATE_IF,GATE_SPEC),original["source_sha256"],closed=False
            )
            facts=[]
            reason="ORIGINAL_NATIVE_POST_ONLY"
            minimal=None
            witness=e.get("source_independent_local_pre_witness")
            condition=original["expression_fields"].get("if")
            if label==ROW_IF_FALSE:
                require(type(witness) is dict and _finite_facts(witness) and
                        condition is not None and
                        truth(evaluate_ast(condition["ast"],witness)) is False and
                        e["source_row_exclusion_condition_proven"] is True,
                        "ORIGINAL_APL_IF_FALSE_NOT_INDEPENDENTLY_REPLAYED")
                # Calculate a *minimal* witness rather than trusting a label.
                proof=sufficient_partial_source_witness(
                    condition["source"],witness,expected=False)
                minimal=proof["minimal_sufficient_PRE_facts"]
                facts=[_fact(source_identity,GATE_IF,False,at,receipt_sha256)]
                reason="INDEPENDENT_APL_IF_FALSE"
            elif label==CLASS_FALSE:
                require(type(witness) is dict and
                        action in rules and
                        witness.get("source_readiness_class")==action and
                        type(witness.get(rules[action]["original_numeric_field"]))
                            in (int,float,bool) and
                        math.isfinite(float(witness[
                            rules[action]["original_numeric_field"]])) and
                        witness[rules[action]["original_numeric_field"]]==
                            rules[action]["false_value"] and
                        e["source_row_exclusion_condition_proven"] is True,
                        "ORIGINAL_SOURCE_LOCAL_NECESSARY_FALSE_NOT_CERTIFIED")
                minimal={
                    rules[action]["original_numeric_field"]:
                        witness[rules[action]["original_numeric_field"]]
                }
                facts=[_fact(source_identity,GATE_SPEC,False,at,receipt_sha256)]
                reason="INDEPENDENT_LOCAL_NECESSARY_FALSE"
            else:
                require(label==NATIVE_ONLY and witness is None and
                        e["source_row_exclusion_condition_proven"] is False,
                        "NATIVE_ONLY_COMPETITOR_PROMOTED_TO_SOURCE_FALSE")
            proof=decide_candidate(source_identity,contract,facts,True)
            required=NOT_READY if label!=NATIVE_ONLY else UNKNOWN
            require(proof["decision"]==required and
                    proof["positive_route_closed"] is False and
                    proof["dummy_error_permitted"] is False,
                    "ORIGINAL_NOT_READY_FRONTIER_WAS_PROMOTED")
            counts[reason]+=1
            decisions.append(proof)
            output.append({
                "source_list":pin["source_list"],
                "source_rank_one_based":pos,
                "original_source_row_sha256":original["source_sha256"],
                "source_action":action,
                "original_CPP_root_id":root,
                "native_ready_false_POST_only":True,
                "source_local_exclusion":proof["decision"],
                "recomputed_source_negative_reason":reason,
                "source_original_PRE_minimal_witness":minimal,
                "source_IF_expression":(
                    condition["source"] if condition is not None else None),
                "global_physical_ability_NOT_READY":"UNKNOWN",
                "dummy_expected_action":"UNKNOWN",
                "proof":proof,
            })
        chosen=source_list[chosen_ord-1]
        require(chosen["behavior"]=="ACTION" and
                chosen["action"]==case.get("chosen_source_action") and
                case.get("chosen_independently_replayed_source_APL_IF") is True,
                "CHOSEN_ORIGINAL_SOURCE_ACTION_CHANGED")
        chosen_condition=chosen["expression_fields"].get("if")
        chosen_facts=case.get("chosen_minimal_sufficient_source_facts")
        require(chosen_condition is not None and
                _finite_facts(chosen_facts) and
                truth(evaluate_ast(chosen_condition["ast"],chosen_facts)) is True,
                "CHOSEN_SOURCE_IF_TRUE_NOT_REPRODUCIBLE")
        chosen_witness=sufficient_partial_source_witness(
            chosen_condition["source"],chosen_facts,expected=True)
        chosen_ident=Identity(
            scope=f"{pin['source_spec_key']}:{target}:{pin['source_list']}",
            source_sha256=chosen["source_sha256"],t_ms=at,
            ordinal=chosen_ord-1,occurrence=chosen_id
        )
        chosen_gate=GateContract(
            "PINNED_ORIGINAL_SIMC_SOURCE_LOCAL",
            (GATE_IF,GATE_SPEC),chosen["source_sha256"],closed=False
        )
        chosen_proof=decide_candidate(
            chosen_ident,chosen_gate,
            [_fact(chosen_ident,GATE_IF,True,at,receipt_sha256)],True
        )
        require(chosen_proof["decision"]==UNKNOWN,
                "NATIVE_CHOSEN_RESULT_PROMOTED_TO_POSITIVE_READY")
        decisions.append(chosen_proof)
        frontier=evaluate_priority(
            decisions,len(decisions)-1,
            source_order_complete=False,
            native_selected_name=chosen["action"]
        )
        require(frontier["decision"]==UNKNOWN and
                frontier["earlier_NOT_READY"]+frontier["earlier_UNKNOWN"]==
                    chosen_ord-1 and
                frontier["earlier_READY"]==0 and
                frontier["returned_READINESS"]==UNKNOWN,
                "INCOMPLETE_PRIORITY_TREATED_AS_PROVEN")
        result.append({
            "original_simc_ms":at,
            "source_spec_key":pin["source_spec_key"],
            "source_target_count":target,
            "source_list":pin["source_list"],
            "native_selected_rank_one_based":chosen_ord,
            "native_selected_original_CPP_root_id":chosen_id,
            "native_selected_action":chosen["action"],
            "native_selected_row_sha256":chosen["source_sha256"],
            "selected_original_source_IF_true_minimal_witness":
                chosen_witness["minimal_sufficient_PRE_facts"],
            "selected_physical_READY":"UNKNOWN",
            "prior_APL_rows_contiguous_from_first":True,
            "parent_CALL_RUN_or_other_action_lists_proven":False,
            "prior_competitors":output,
            "source_list_local_evidence_frontier":frontier,
            "current_Retail_general_rotation_priority":"UNKNOWN",
            "actual_player_cast_expected":"UNKNOWN",
        })
    original_counts=ledger.get("counts",{})
    require(sum(x for x in counts.values())==
            original_counts.get("prior_original_source_rows") and
            counts["INDEPENDENT_APL_IF_FALSE"]==
            original_counts.get("earlier_independent_source_IF_false") and
            counts["INDEPENDENT_LOCAL_NECESSARY_FALSE"]==
            original_counts.get("earlier_independent_local_READY_false") and
            counts["ORIGINAL_NATIVE_POST_ONLY"]==
            original_counts.get("earlier_original_cpp_if_false_not_independently_replayed"),
            "ORIGINAL_LEDGER_REASON_COUNTS_DO_NOT_REPLAY")
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "source_profile_git_blob_sha1":parsed["source_git_blob_sha1"],
        "original_source_ledger_member_sha256":receipt_sha256,
        "source_spec":pin["source_spec_key"],
        "target_count":pin["target_count"],
        "source_list":pin["source_list"],
        "verified_native_source_cases":len(result),
        "earlier_competing_local_APL_rows":sum(counts.values()),
        "source_local_independent_EXCLUDED_occurrences":
            counts["INDEPENDENT_APL_IF_FALSE"]+
            counts["INDEPENDENT_LOCAL_NECESSARY_FALSE"],
        "source_IF_FALSE_counts":counts["INDEPENDENT_APL_IF_FALSE"],
        "source_necessary_ready_FALSE_counts":counts[
            "INDEPENDENT_LOCAL_NECESSARY_FALSE"],
        "original_native_POST_ONLY_UNKNOWN_counts":counts[
            "ORIGINAL_NATIVE_POST_ONLY"],
        "source_only_case_frontiers":result,
        "source_row_local_NOT_READY_not_global_ability_unavailability":True,
        "source_original_single_list_not_entire_APL_control_graph":True,
        "all_selected_action_full_READY":"UNKNOWN",
        "all_competing_entire_physical_READY":"UNKNOWN",
        "general_rotation_source_order_choice_proven":False,
        "real_WoW_dummy_mistake":"UNKNOWN",
        "WCL_blind_candidate_lock":"NOT_RUN",
        "WCL_API_calls":0,"new_SimC_CXX_builds":0,
        "MAIN_promoted":False,
    }


def verify_and_run(ledger_file:Path,profile_file:Path,adapter_file:Path)->dict:
    a=json.loads(adapter_file.read_bytes())
    require(a.get("schema")==ADAPTER and a.get("policy_id")==POLICY and
            type(a.get("original_ledger_sha256")) is str and
            HEX64.fullmatch(a["original_ledger_sha256"]) is not None,
            "ADAPTER_WITHOUT_EXACT_ORIGINAL_LEDGER_MEMBER_PIN")
    raw=ledger_file.read_bytes()
    digest=sha256(raw).hexdigest()
    require(digest==a["original_ledger_sha256"],
            "ORIGINAL_NATIVE_SOURCE_RECEIPT_BYTES_CHANGED")
    parsed=_read_original_apl(profile_file.read_bytes(),a)
    ledger=json.loads(raw)
    return compile_frontier(ledger,parsed,a,receipt_sha256=digest)


def selftest()->dict:
    # Two arbitrary class/specialization fixtures: no spell semantics in core.
    from simc_apl_semantic_ir_v2 import Expression, ast_symbols
    cases=0
    tamper=0
    for spec,action in (("newclass_a","alpha"),("otherclass_b","gamma")):
        def parsed_row(token,expr,index):
            return {"action":token,"behavior":"ACTION",
                    "source_sha256":sha256(f"{spec}:{index}:{token}:{expr}".encode()).hexdigest(),
                    "expression_fields":(
                        {"if":{"source":expr,
                               "ast":Expression(expr).parse(),
                               "symbols":sorted(ast_symbols(Expression(expr).parse()))}}
                        if expr else {})}
        rows=[parsed_row(action,"a&b",0),
              parsed_row(action+"_two","u&v",1),
              parsed_row("selected", "v|w",2)]
        pin={"schema":ADAPTER,"policy_id":POLICY,
             "source_spec_key":spec,"source_revision":"a"*40,
             "source_profile_git_blob":"b"*40,
             "source_list":"primary","target_count":3,
             "expected_case_count":1,
             "original_ledger_schema":"dummy-verified-original",
             "local_gate_rules":[
                 {"action":action+"_two",
                  "original_numeric_field":"observed_local_gate",
                  "false_value":0}]}
        ledger={"schema":"dummy-verified-original",
                "product_policy_id":POLICY,
                "source_candidate_order_and_return_proven":True,
                "source_local_failure_not_skill_globally_unavailable":True,
                "general_rotation_priority_optimality_proven":False,
                "dummy_training_feedback_permitted":False,
                "WCL_API_calls":0,
                "counts":{
                  "original_cpp_selected_2T_orb_rows":1,
                  "prior_original_source_rows":2,
                  "earlier_independent_source_IF_false":1,
                  "earlier_independent_local_READY_false":1,
                  "earlier_original_cpp_if_false_not_independently_replayed":0
                },
                "two_target_winner_decisions":[{
                  "original_cpp_at_simc_ms":100,
                  "target_count_scenario":3,
                  "chosen_source_row_ordinal":3,
                  "chosen_CPP_ready_root_id":40,
                  "chosen_source_action":"selected",
                  "chosen_independently_replayed_source_APL_IF":True,
                  "chosen_minimal_sufficient_source_facts":{"v":1},
                  "chosen_full_physical_READY_independently_proven":False,
                  "earlier_all_possible_action_alternatives_exhaustively_proven":False,
                  "WoW_dummy_error_verdict":"UNKNOWN",
                  "earlier_source_rows":[
                    {"original_source_ordinal":1,"source_action":action,
                     "original_cpp_ready_root_id":35,
                     "decision_evidence_class":ROW_IF_FALSE,
                     "native_CPP_source_POST_observed":False,
                     "independent_entire_spell_NOT_READY_proven":False,
                     "dummy_user_mistake_verdict":"UNKNOWN",
                     "source_row_exclusion_condition_proven":True,
                     "source_independent_local_pre_witness":{"a":0}},
                    {"original_source_ordinal":2,
                     "source_action":action+"_two",
                     "original_cpp_ready_root_id":38,
                     "decision_evidence_class":CLASS_FALSE,
                     "native_CPP_source_POST_observed":False,
                     "independent_entire_spell_NOT_READY_proven":False,
                     "dummy_user_mistake_verdict":"UNKNOWN",
                     "source_row_exclusion_condition_proven":True,
                     "source_independent_local_pre_witness":{
                         "observed_local_gate":0,
                         "source_readiness_class":action+"_two"}}
                  ]}]}
        model={"source_git_blob_sha1":"b"*40,
               "action_lists":{"primary":rows}}
        r=compile_frontier(ledger,model,pin,receipt_sha256="c"*64)
        assert r["source_local_independent_EXCLUDED_occurrences"]==2
        assert r["all_selected_action_full_READY"]=="UNKNOWN"
        assert r["source_only_case_frontiers"][0][
            "source_list_local_evidence_frontier"]["decision"]=="UNKNOWN"
        cases+=1
        import copy
        for edit in (
            lambda x:x["two_target_winner_decisions"][0][
                "earlier_source_rows"][0].update(
                    source_independent_local_pre_witness={"a":1}),
            lambda x:x["two_target_winner_decisions"][0][
                "earlier_source_rows"][1].update(
                    source_independent_local_pre_witness={
                        "observed_local_gate":1,
                        "source_readiness_class":action+"_two"}),
            lambda x:x["two_target_winner_decisions"][0][
                "earlier_source_rows"][0].update(
                    original_cpp_ready_root_id=40),
            lambda x:x["two_target_winner_decisions"][0][
                "chosen_minimal_sufficient_source_facts"].update(v=0),
            lambda x:x["two_target_winner_decisions"][0][
                "earlier_source_rows"][0].update(
                    source_row_exclusion_condition_proven=False),
        ):
            altered=copy.deepcopy(ledger)
            edit(altered)
            try:compile_frontier(altered,model,pin,receipt_sha256="c"*64)
            except (CompetitorEvidenceError,ValueError):tamper+=1
            else:raise AssertionError("FORGED_COMPETING_SOURCE_REASON_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC",
            "arbitrary_specialization_fixtures":cases,
            "forge_cases_rejected":tamper,
            "source_FULL_READY_proven":0,"WCL_API_calls":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-ledger",type=Path)
    p.add_argument("--source-profile",type=Path)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any((a.original_ledger,a.source_profile,a.adapter)):
        result=selftest()
    else:
        if not all((a.original_ledger,a.source_profile,a.adapter)):
            p.error("All three input paths are required together")
        result=verify_and_run(a.original_ledger,a.source_profile,a.adapter)
    body=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(body)
        print(json.dumps({"written":str(a.out),"sha256":sha256(body).hexdigest()}))
    else:
        print(body.decode(),end="")


if __name__=="__main__":
    main()
