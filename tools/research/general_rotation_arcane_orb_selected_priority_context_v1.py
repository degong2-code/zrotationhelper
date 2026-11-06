#!/usr/bin/env python3
"""Source-order priority context for real selected Arcane Orb native returns.

Connect the existing original C++ source-selected leaf tree to an already
verified original action_t::ready/action_ready branch-stage receipt, without
running Native SimC again or relying on unobserved 'readiness'.

Previous Native FALSE is an observation of that source's outcome, NOT a
proof that the entire skill class was physically unavailable. For the
earlier Arcane Orb variant, give the source-observed branch result only.
Do not import SimC/Hekili's semantic hypothesis into WCL blind discovery.

No CLI arguments: safe zero-network source-identity synthetic contract.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from general_rotation_full_root_state_join_v1 import SCHEMA as SELECTED
from general_rotation_time_scoped_priority_ir_v1 import SCHEMA as TEMPORAL
from general_rotation_arcane_orb_native_ready_stage_replay_v1 import SCHEMA as GATES
from general_rotation_source_eligibility_decision_ir_v1 import POLICY

SCHEMA="ZrotArcaneOrbOriginalNativeSelectedPriorityContextV1"
SOURCE_PINS={
 "st":{
 "temporal":"1b8e60e3e32fe987df7d1322fda571520c20dccda586edc093a273e6e6803032",
 "chosen":"f736766ae310f3665fbcd492ab05ff4704d453ab03720d2e2e5d9166de39494d",
 "gates":"79bb76801c49d6280d97f34e16e94fdf6312b101f17e629f27b2b933999b8863"},
 "2t":{
 "temporal":"e3691f55a9a1fcea2b4abd6cbfb89fb778fb622e714df064875affd53692a5c6",
 "chosen":"ed908c85fab7d6a7dd834c9769528a9b7f97bbf6fe122505de98cdec5acfd14e",
 "gates":"af62e1f62e280dfaa4ada5f618a824d0c5f67bba5e939a73aa23150766d3823a"},
}
class ArcanePriorityContextError(ValueError):
    pass


def need(ok:bool,label:str)->None:
    if not ok:raise ArcanePriorityContextError(label)


def compose(temporal:dict,chosen:dict,gates:dict)->dict:
    need(temporal.get("schema")==TEMPORAL and
         chosen.get("schema")==SELECTED and
         gates.get("schema")==GATES and
         temporal.get("product_policy_id")==POLICY and
         chosen.get("product_policy_id")==POLICY and
         gates.get("product_policy_id")==POLICY and
         temporal.get("source_profile_git_blob_sha1")==
         chosen.get("source_profile_git_blob_sha1") and
         temporal.get("independent_FULL_READY_proven")==0 and
         chosen.get("complete_independent_full_READY_proven")==0 and
         chosen.get("gameplay_feedback_permitted") is False and
         gates.get("independent_full_action_READY_gate_closure") is False,
         "UNTRUSTED_OR_ORIGINAL_CPP_SOURCE_COHORT_CHANGED")
    sweep_by_id={}
    for sw in temporal["observed_time_scoped_selection_frontiers"]:
        ident=sw["sweep_call_id"]
        need(ident not in sweep_by_id,"DUPLICATED_CPP_SELECT_SWEEP")
        sweep_by_id[ident]=sw
    native_gates={}
    for row in gates["original_arcane_orb_ready_roots"]:
        rid=row["original_ready_root_id"]
        need(rid not in native_gates and
             row["original_CXX_action_ready_return_stage"] is not None,
             "DUPLICATED_CPP_READY_OR_UNTRACED_ROOT")
        native_gates[rid]=row
    selected_orbs=[r for r in chosen["source_selected_rows"]
                   if r.get("action")=="arcane_orb"]
    need(selected_orbs,"NO_SOURCE_SELECTED_ARCANE_ORB")
    tally=Counter()
    records=[]
    seen=set()
    for winner in selected_orbs:
        rid=winner["selected_CPP_ready_root_id"]
        leaf=winner["original_CPP_source_select_path"][-1]
        sw=sweep_by_id.get(leaf)
        need(sw is not None and sw["source_list"]==winner["source_list"] and
             sw["at_simc_ms"]==winner["at_simc_ms"] and
             rid not in seen and
             winner["original_native_source_return_observed"] is True and
             winner["independent_full_READY_proven"] is False,
             "SELECTED_ORIGINAL_CPP_LEAF_NOT_SINGLE_SOURCE")
        seen.add(rid)
        trace=native_gates.get(rid)
        need(trace is not None and trace["at_simc_ms"]==winner["at_simc_ms"] and
             trace["source_row_sha256"]==winner["source_row_sha256"] and
             trace["source_list"]==winner["source_list"] and
             trace["source_ordinal"]==winner["source_ordinal"] and
             trace["source_CXX_POST_selection_boolean"] is True and
             trace["original_CXX_action_ready_return_stage"]=="ACTION_READY_TRUE",
             "SELECTED_ARCANE_ORB_MUST_EQUAL_ORIGINAL_CPP_READY_TRUE")
        events=sw["observed_candidate_event_stream"]
        indices=[i for i,item in enumerate(events)
                 if item.get("original_action_ready_root_id")==rid and
                 item.get("source_row_sha256")==winner["source_row_sha256"]]
        need(len(indices)==1,"SELECTED_CPP_READY_ROOT_NOT_UNIQUE_IN_LEAF_SWEEP")
        idx=indices[0]
        need(events[idx].get("stage")=="ACTION_READY_CALLED" and
             events[idx].get("simc_NATIVE_return_post_comparator") is True,
             "SELECTED_NATIVE_TRUE_SOURCE_ROW_MISSING")
        before=[]
        for item in events[:idx]:
            kind=item.get("stage")
            seen_boolean=item.get("simc_NATIVE_return_post_comparator")
            if kind=="ACTION_READY_CALLED":
                need(type(seen_boolean) is bool and
                     seen_boolean is False and
                     type(item.get("ordinal_one_based")) is int and
                     item["ordinal_one_based"]<winner["source_ordinal"],
                     "EARLIER_SOURCE_NATIVE_TRUE_OR_NONCAUSAL_ORDER")
                pri={
                    "earlier_source_action":item["source_action"],
                    "earlier_source_ordinal":item["ordinal_one_based"],
                    "earlier_CPP_ready_root_id":
                        item["original_action_ready_root_id"],
                    "earlier_native_POST":False,
                    "earlier_full_skill_unavailable_independently_proven":False,
                    "earlier_source_branch_actual":None,
                    "unobserved_ready_reason":"UNKNOWN_ORIGINAL_NATIVE_FALSE_ONLY",
                }
                if item.get("source_action")=="arcane_orb":
                    earlier=native_gates.get(item["original_action_ready_root_id"])
                    need(earlier is not None and earlier["at_simc_ms"]==
                            winner["at_simc_ms"] and
                         earlier["source_row_sha256"]==item["source_row_sha256"] and
                         earlier["source_CXX_POST_selection_boolean"] is False,
                         "EARLIER_ARCANE_ORB_ORIGINAL_CPP_BRANCH_NOT_PROVEN")
                    pri["earlier_source_branch_actual"]=earlier[
                        "original_CXX_action_ready_return_stage"]
                    pri["unobserved_ready_reason"]=(
                        "ORIGINAL_CPP_BRANCH_OBSERVED_NOT_INDEPENDENT_READINESS")
                    tally["earlier_arcane_orb_original_CPP_branch_observed"]+=1
                    if pri["earlier_source_branch_actual"]=="ACTION_APL_IF_FALSE":
                        tally["earlier_arcane_orb_original_APL_IF_FALSE"]+=1
                before.append(pri)
                tally["earlier_physical_candidates_native_false"]+=1
            else:
                # Preserve unknown for non-READY source skips, rather than
                # silently removing them or calling them "unavailable".
                before.append({
                    "earlier_source_action":item.get("source_action"),
                    "earlier_source_ordinal":item.get("ordinal_one_based"),
                    "earlier_CPP_ready_root_id":None,
                    "earlier_native_POST":"NOT_CALLED",
                    "earlier_full_skill_unavailable_independently_proven":False,
                    "earlier_source_branch_actual":None,
                    "unobserved_ready_reason":"SOURCE_SKIP_NOT_AN_INDEPENDENT_GATE",
                })
                tally["earlier_source_non_READY_skips"]+=1
        tally["original_source_selected_arcane_orb"]+=1
        tally["prior_source_candidate_rows_in_same_leaf_list"]+=len(before)
        records.append({
            "selected_action":"arcane_orb",
            "selected_source_list":winner["source_list"],
            "selected_source_row_ordinal":winner["source_ordinal"],
            "simc_ms":winner["at_simc_ms"],
            "selected_root_CPP_ready_id":rid,
            "selected_root_CPP_returned_action_stage":
                trace["original_CXX_action_ready_return_stage"],
            "selected_original_CPP_mana_current":
                trace["original_CPP_before_call_raw_PRE"]["mana_current"],
            "selected_original_CPP_mana_max":
                trace["original_CPP_before_call_raw_PRE"]["mana_max"],
            "original_ready_selected_causal_order_proven":True,
            "source_earlier_candidates":before,
            "independent_prior_physical_NOT_READY_proven":False,
            "complete_all_possible_source_row_priority_proven":False,
            "user_dummy_mistake_verdict":"UNKNOWN",
        })
    need(tally["original_source_selected_arcane_orb"]==
         gates["counts"].get("original_native_return_true"),
         "EXACT_CPP_ARCANE_ORB_SELECTED_VS_NATIVE_TRUE_COUNT_MISMATCH")
    return {
        "schema":SCHEMA,"product_policy_id":POLICY,
        "source_profile_git_blob_sha1":chosen["source_profile_git_blob_sha1"],
        "target_count_scenario":chosen["target_count"],
        "counts":dict(sorted(tally.items())),
        "selected_actions":records,
        "source_order_is_observed_not_optimality":True,
        "native_POST_false_not_independent_full_NOT_READY":True,
        "no_WCL_blind_candidate_semantics_import":True,
        "independent_full_skill_READY_proven":0,
        "dummy_feedback_permitted":False,
        "WCL_API_calls":0,
    }


def _read_verified(folder:Path,case:str)->tuple[dict,dict,dict]:
    need(case in SOURCE_PINS,"NONAPPROVED_SOURCE_CASE")
    source=SOURCE_PINS[case]
    expected={
        "temporal":f"zrot-source-temporal-frontier-arcane-{case}.json",
        "chosen":f"zrot-all-original-source-chosen-state-arcane-{case}.json",
        "gates":f"zrot-original-arcane-ready-stage-{case}.json",
    }
    result={}
    for key,name in expected.items():
        raw=(folder/name).read_bytes()
        need(sha256(raw).hexdigest()==source[key],
             "ACTUAL_GITHUB_NATIVE_RECEIPT_CONTENT_SHA256_DRIFT:"+key)
        result[key]=json.loads(raw)
    return result["temporal"],result["chosen"],result["gates"]


def selftest()->dict:
    for case in SOURCE_PINS:
        need(set(SOURCE_PINS[case])=={"temporal","chosen","gates"} and
             all(len(h)==64 and all(c in "0123456789abcdef" for c in h)
                 for h in SOURCE_PINS[case].values()),
             "SOURCE_PIN_CONTRACT_INVALID")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":6,"current_SIMC_recompiled":False,
            "independent_FULL_READY_proven":0,"WCL_API_calls":0}


def main()->None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--original-native-artifact-directory",type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    if a.original_native_artifact_directory is None:
        data=selftest()
    else:
        pairs={}
        combined=Counter()
        for case in ("st","2t"):
            values=_read_verified(a.original_native_artifact_directory,case)
            result=compose(*values)
            pairs[case]=result
            combined.update(result["counts"])
        need(combined["original_source_selected_arcane_orb"]==4 and
             combined["earlier_arcane_orb_original_APL_IF_FALSE"]==2 and
             combined["earlier_physical_candidates_native_false"]==10,
             "PINNED_FIRST_PHYSICAL_ORB_SOURCE_PRIORITY_CONTEXT_COUNT_DRIFT")
        data={
            "schema":SCHEMA,
            "product_policy_id":POLICY,
            "cases":pairs,"totals":dict(sorted(combined.items())),
            "original_simc_CPP_rebuilt_this_step":False,
            "strict_WCL_PRE_or_holdout_performed":False,
            "full_competitor_READY_proven":0,
            "dummy_mistake_feedback_permitted":False,
        }
    encoded=(json.dumps(data,sort_keys=True,separators=(",",":"),
                        allow_nan=False)+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(encoded)
    else:
        import sys
        sys.stdout.buffer.write(encoded)

if __name__=="__main__":
    main()
