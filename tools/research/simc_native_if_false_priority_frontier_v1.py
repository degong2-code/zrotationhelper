#!/usr/bin/env python3
"""Native source-ordered General Rotation candidate frontier from independent PRE IF.

Join every real IF expression's independently computed source operand AST to
the exact corresponding attempt, using original chronological occurrence,
source list, effective APL row/ordinal, action name and SHA256. Then join the
observed base action_ready first-exit IF_FALSE, preserving subclass UNKNOWN.

The SELECT stack gives observed ordering and native-selected root provenance,
NEVER an independent ready bit. A predecessor can be independently excluded
by a proven false IF (or pinned exact cooldown queue clock with actual base
ready method entry and source first-exit). The selected candidate is *never*
labelled independently ready; positive action choice remains UNKNOWN.

All future simulated movement events are SimC source research conditions, NOT
a real-time WoW target dummy future-event signal. No WCL data or boss plans.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile
from simc_native_if_pre_operand_replay_v1 import (
    PINNED_FURY_BLOB, verify_folder, parse_fact, exact_key, get_native_attempt
)
from simc_native_if_source_clock_successor_v1 import pre_facts
from simc_native_if_talent_pre_instrument_v1 import talent_inventory
from simc_native_if_talent_pre_replay_v1 import group_actual_pre_talents, independent_if
from simc_native_if_buff_pre_instrument_v1 import buff_inventory
from simc_native_if_buff_pre_replay_v1 import group_actual_pre_buffs
from simc_native_if_action_gcd_cd_pre_instrument_v1 import source_inventory
from simc_native_if_action_gcd_cd_pre_replay_v1 import group_action_expr_pre
from simc_native_if_movement_event_pre_instrument_v1 import inventory
from simc_native_if_movement_event_pre_replay_v1 import group_environment_facts
from simc_native_ready_guard_witness_replay_v1 import read_guard, read_method_entry
from simc_native_ready_guard_witness_instrument_v1 import (
    BASE_ACTION_MARK, BASE_READY_MARK
)
from simc_native_cooldown_queue_clock_replay_v1 import read_clock
from simc_native_cooldown_tolerance_replay_v1 import (
    read_tolerance, independent_raw_tolerance_queue
)
from simc_native_postguard_source_replay_v1 import parse_exit
from simc_native_foreground_structural_replay_v1 import unpack_marker

SCHEMA="ZrotNativeIndependentIfFalseSourcePriorityFrontierV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"


class PriorityFrontierError(ValueError):
    pass


def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def source_if_samples(trace:str,ir:dict,prior:dict)->list[dict]:
    """Recompute without using either the native IF truth or ready Boolean."""
    rows=prior["all_native_if_pre_fact_ledger"]
    talents=talent_inventory(ir)
    buffs=buff_inventory(ir)
    scoped=source_inventory(ir)
    environment=inventory(ir)
    grouped=[
        group_actual_pre_talents(trace,talents),
        group_actual_pre_buffs(trace,buffs),
        group_action_expr_pre(trace,scoped),
        group_environment_facts(trace,environment),
    ]
    if not all(len(arr)==len(rows) for arr in grouped):
        raise PriorityFrontierError("ACTUAL_PRE_IF_LEDGER_GROUP_COUNT_CHANGED")
    computed=[]
    for index,row in enumerate(rows):
        k=(row["at_ms"],row["source_list"],row["source_index"]+1,row["native_name"])
        if any(arr[index]["key"]!=k for arr in grouped):
            raise PriorityFrontierError("CHRONOLOGICAL_SOURCE_PRE_IF_POINTER_MISMATCH")
        if k[1] not in ir["action_lists"] or not 1<=k[2]<=len(ir["action_lists"][k[1]]):
            raise PriorityFrontierError("ACTUAL_PRE_IF_OFFICIAL_APL_SOURCE_NOT_FOUND")
        source=ir["action_lists"][k[1]][k[2]-1]
        expr=source["expression_fields"].get("if")
        if (expr is None or source["source_sha256"]!=row["source_line_sha256"]
            or row["source_if"]!=expr["source"]
            or row["source_if_symbols"]!=expr["symbols"]):
            raise PriorityFrontierError("OFFICIAL_IF_SOURCE_SHA_AND_EXPRESSION_CHANGED")
        talent,buff,action,env=(g[index] for g in grouped)
        facts={
            **pre_facts(row),
            **talent["values"], **buff["values"],
            **{name:value for name,value in action["captured"].items()
               if value is not None},
            **env["facts"],
        }
        verdict=independent_if(expr,facts)
        if verdict is not None and verdict not in (0,1):
            raise PriorityFrontierError("AST_NONBOOLEAN_RESULT_NOT_TRI_STATE")
        # Compare Native result ONLY after independently computing AST.
        if verdict is not None and verdict!=row["native_if_result_verification_only"]:
            raise PriorityFrontierError("INDEPENDENT_IF_AST_VS_NATIVE_COMPARATOR_CONFLICT")
        computed.append({
            "key":k,
            "source_sha256":source["source_sha256"],
            "source_if":expr["source"],
            "symbols":expr["symbols"],
            "independent_IF_bool":verdict,
            "Native_IF_bool_POST_comparator":row["native_if_result_verification_only"],
            "movement_simc_event_not_real_WoW_future":True,
        })
    return computed


def one_attempt(pending:dict, attempt:dict, ir:dict)->dict:
    pre=pending["pre"]
    k=exact_key(attempt)
    if k!=exact_key(pre):
        raise PriorityFrontierError("NATIVE_ATTEMPT_PRE_SOURCE_IDENTITY_MISMATCH")
    if k[1] not in ir["action_lists"] or not 1<=k[2]<=len(ir["action_lists"][k[1]]):
        raise PriorityFrontierError("SELECTED_SOURCE_EFFECTIVE_APL_ROW_MISSING")
    row=ir["action_lists"][k[1]][k[2]-1]
    fact=pending["if"]
    if fact is not None and (fact["key"]!=k or
                             fact["source_sha256"]!=row["source_sha256"]):
        raise PriorityFrontierError("IF_FACT_ATTEMPT_SOURCE_SHA_NOT_EQUAL")
    exits=[e for e in pending["exits"]
           if (e["time_ms"],e["name"])==(k[0],k[3])]
    path=exits[0]["reason"] if len(exits)==1 else None
    has_native_base_path=len(exits)==1
    status="UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED"
    reason=None
    if path=="IF_FALSE":
        if fact is None:
            raise PriorityFrontierError("SOURCE_IF_FALSE_WITHOUT_PRE_IF_FACT")
        if fact["independent_IF_bool"]==1:
            raise PriorityFrontierError("NATIVE_IF_FALSE_BUT_INDEPENDENT_AST_TRUE")
        if fact["independent_IF_bool"]==0 and attempt["ready"]==0:
            status="EXCLUDED_BY_INDEPENDENT_IF_FALSE_AND_BASE_EXIT"
            reason="actual_IF_source_false"
        else:
            status="UNKNOWN_IF_SOURCE_FALSE_BUT_AST_OR_OVERRIDE_UNPROVEN"
    elif path=="BASE_READY_FALSE" and (pending["base_action_entries"]==1
                                     and pending["base_ready_entries"]==1
                                     and pending["clock"] is not None
                                     and pending["tolerance"] is not None):
        calc=independent_raw_tolerance_queue(pending["clock"],
                                              pending["tolerance"])
        if calc["numeric_cooldown_ready"]==0 and attempt["ready"]==0:
            status="EXCLUDED_BY_INDEPENDENT_COOLDOWN_FALSE_AND_BASE_EXIT"
            reason=calc["source_numeric_reason"]
    if status.startswith("EXCLUDED_") and row["action"] in (
            "variable","call_action_list","run_action_list"):
        # The command may mutate state or control source lists, and is
        # NOT a straightforward competing physical ability.
        status="UNKNOWN_APL_CONTROL_COMMAND_NOT_SPELL_EXCLUSION"
        reason=None
    return {
        "source_key":k,
        "source_index":k[2]-1,
        "source_sha256":row["source_sha256"],
        "source_action":row["action"],
        "source_behavior":row["behavior"],
        "native_action_name":attempt["native_name"],
        "status":status,
        "source_exclusion_reason":reason,
        "independent_IF_bool":fact["independent_IF_bool"] if fact else None,
        "source_base_exit_observed":path,
        "native_ready_POST_comparator":attempt["ready"],
        "method_base_path_source_observed":has_native_base_path,
        "selected_ability_ready_independently_proven":False,
    }


def analyze_trace(trace:str,ir:dict,samples:list[dict],spec_adapter=None,proof_bridge=None)->dict:
    stack=[]
    root=None
    current=None
    sample_cursor=0
    counts=Counter()
    excluded=Counter()
    exits=Counter()
    prefix_totals=Counter()
    root_examples=[]
    if_false_examples=[]
    for line in trace.splitlines():
        guard=read_guard(line)
        if guard is not None:
            if current is not None:
                raise PriorityFrontierError("OVERLAPPING_NATIVE_SOURCE_PRE_GUARDS")
            current={"pre":guard,"if":None,"exits":[],
                     "clock":None,"tolerance":None,
                     "base_action_entries":0,"base_ready_entries":0}
            continue
        if spec_adapter is not None:
            spec_adapter.consume(line,current)
        if proof_bridge is not None:
            proof_bridge.consume(line,current)
        clock=read_clock(line)
        if clock is not None:
            if current is None or current["clock"] is not None or (
                exact_key(clock)!=exact_key(current["pre"])):
                raise PriorityFrontierError("NATIVE_PRE_CLOCK_POINTER_NOT_SAME_ATTEMPT")
            current["clock"]=clock
            continue
        tolerance=read_tolerance(line)
        if tolerance is not None:
            if current is None or current["tolerance"] is not None or (
                exact_key(tolerance)!=exact_key(current["pre"])):
                raise PriorityFrontierError("NATIVE_PRE_TOLERANCE_POINTER_NOT_SAME_ATTEMPT")
            current["tolerance"]=tolerance
            continue
        for token,slot in (
            (BASE_ACTION_MARK,"base_action_entries"),
            (BASE_READY_MARK,"base_ready_entries")
        ):
            entered=read_method_entry(line,token)
            if entered is not None:
                if current is not None and entered==(
                    current["pre"]["time_ms"],current["pre"]["native_name"]):
                    current[slot]+=1
                break
        else:
            original_fact=parse_fact(line)
            if original_fact is not None:
                if sample_cursor>=len(samples):
                    raise PriorityFrontierError("EXCESS_OR_DUPLICATE_REAL_PRE_IF_EVENT")
                sample=samples[sample_cursor]
                sample_cursor+=1
                if sample["key"]!=exact_key(original_fact):
                    raise PriorityFrontierError("IF_EVENT_CHRONOLOGY_OR_SOURCE_POINTER_DRIFT")
                if current is None or exact_key(current["pre"])!=sample["key"] or current["if"] is not None:
                    raise PriorityFrontierError("NATIVE_IF_NOT_ONE_ACTUAL_ATTEMPT")
                current["if"]=sample
                counts["real_source_IF_samples"]+=1
                counts["independent_IF_"+(
                    "UNKNOWN" if sample["independent_IF_bool"] is None
                    else "TRUE" if sample["independent_IF_bool"] else "FALSE")]+=1
                continue
            e=parse_exit(line)
            if e is not None and current is not None:
                current["exits"].append(e)
            marker=unpack_marker(line)
            if marker is None:continue
            typ=marker["type"]
            if typ=="ENTER":
                if not stack:
                    root={"mode":marker["mode"],"time_ms":marker["t"],
                          "source_list":marker["list"],"attempts":[]}
                stack.append(marker["list"])
                continue
            if not stack or stack[-1]!=marker["list"]:
                raise PriorityFrontierError("SELECT_ACTION_STACK_SOURCE_REPLAY_INVALID")
            if typ=="ATTEMPT":
                attempt=get_native_attempt(line)
                if attempt is None or current is None:
                    raise PriorityFrontierError("SELECT_ATTEMPT_WITHOUT_PRE_GUARD")
                if current["if"] is not None and (
                    current["if"]["Native_IF_bool_POST_comparator"] not in (0,1)):
                    raise PriorityFrontierError("NATIVE_IF_COMPARATOR_MISSING")
                one=one_attempt(current,attempt,ir)
                if spec_adapter is not None:
                    one=spec_adapter.improve_negative(current,attempt,one)
                if proof_bridge is not None:
                    one["generic_proof"]=proof_bridge.evaluate_attempt(
                        current,one,spec_adapter=spec_adapter)
                counts["Native_action_ready_attempts"]+=1
                counts["status_"+one["status"]]+=1
                if one["source_base_exit_observed"] is not None:
                    exits[one["source_base_exit_observed"]]+=1
                if one["source_base_exit_observed"]=="IF_FALSE":
                    counts["Native_source_IF_FALSE_exit_joined"]+=1
                    if (one["status"]=="EXCLUDED_BY_INDEPENDENT_IF_FALSE_AND_BASE_EXIT"):
                        counts["IF_FALSE_exits_independently_proved"]+=1
                        if len(if_false_examples)<16:
                            if_false_examples.append({
                                "source_key":one["source_key"],
                                "source_sha256":one["source_sha256"],
                                "source_action":one["source_action"],
                                "source_if":current["if"]["source_if"],
                                "Native_source_EXIT_comparator":"IF_FALSE",
                                "independent_IF":0,
                            })
                    else:counts["IF_FALSE_exits_UNKNOWN"]+=1
                if one["status"].startswith("EXCLUDED_"):
                    excluded[one["source_exclusion_reason"]]+=1
                if root is None:
                    raise PriorityFrontierError("NATIVE_ROOT_ATTEMPT_WITHOUT_SELECT_ENTER")
                root["attempts"].append(one)
                current=None
                continue
            if typ not in ("RETURN","NO_ACTION"):
                raise PriorityFrontierError("NATIVE_SELECT_MARKER_UNEXPECTED")
            stack.pop()
            if stack:
                continue
            if root is None:
                raise PriorityFrontierError("ROOT_NO_RETURN_STATE")
            counts["Native_root_select_scans"]+=1
            if root["mode"]=="FOREGROUND":
                counts["Native_foreground_roots"]+=1
                root_status="RETURNED_ACTION" if typ=="RETURN" else "NO_ACTION"
                if typ=="RETURN":
                    counts["Native_foreground_root_returned"]+=1
                if proof_bridge is not None:
                    proof_bridge.evaluate_root(
                        root["attempts"],returned=typ=="RETURN",
                        observed_name=(marker["native_name"] if typ=="RETURN" else None))
                prior=root["attempts"][:-1] if typ=="RETURN" else root["attempts"]
                proved=sum(item["status"].startswith("EXCLUDED_") for item in prior)
                unknown=len(prior)-proved
                counts["foreground_prior_candidates_independently_eliminated"]+=proved
                counts["foreground_prior_candidates_UNKNOWN"]+=unknown
                if typ=="RETURN":
                    prefix_totals["native_returned_foreground_roots"]+=1
                    if unknown==0:
                        prefix_totals["all_prior_attempts_source_excluded_but_winner_NOT_ready_proven"]+=1
                    else:
                        prefix_totals["native_winner_has_unknown_prior_candidates"]+=1
                if len(root_examples)<20:
                    root_examples.append({
                        "at_ms":root["time_ms"],"root_source_list":root["source_list"],
                        "source_selection_observed_only":root_status,
                        "Native_returned_name_provenance_only":
                            marker["native_name"] if typ=="RETURN" else None,
                        "prior_independent_exclusions":proved,
                        "prior_readiness_UNKNOWN":unknown,
                        "prior_exclusion_examples":[
                            {"action":r["source_action"],"source_list":r["source_key"][1],
                             "source_index":r["source_index"],
                             "source_sha256":r["source_sha256"],"status":r["status"]}
                            for r in prior if r["status"].startswith("EXCLUDED_")
                        ][:8],
                        "independent_winner_ready":False,
                    })
            root=None
    if current is not None or stack or root is not None:
        raise PriorityFrontierError("SOURCE_SELECTION_OR_PRE_ATTEMPT_UNPAIRED_EOF")
    if sample_cursor!=len(samples):
        raise PriorityFrontierError("SOURCE_PRE_IF_EVENT_NOT_FULLY_CONSUMED")
    if (counts["real_source_IF_samples"]!=len(samples) or
        counts["Native_source_IF_FALSE_exit_joined"]!=
            counts["IF_FALSE_exits_independently_proved"]+
            counts["IF_FALSE_exits_UNKNOWN"]):
        raise PriorityFrontierError("SOURCE_IF_FALSE_JOIN_ACCOUNTING_INVALID")
    return {
        "counts":dict(sorted(counts.items())),
        "Native_source_base_first_exits":dict(sorted(exits.items())),
        "independent_source_negative_reasons":dict(sorted(excluded.items())),
        "foreground_prefix_screening":dict(sorted(prefix_totals.items())),
        "bounded_IF_FALSE_join_examples":if_false_examples,
        "bounded_foreground_source_frontier_examples":root_examples,
        "Native_IF_truth_used_only_after_independent_AST":True,
        "Native_ready_bit_used_as_independent_ready_input":False,
        "selected_winner_independent_positive_ready":False,
        "full_General_Rotation_priority_proven":False,
        "SpecAdapter_name":type(spec_adapter).__name__ if spec_adapter else None,
        "SpecAdapter_source_witness":spec_adapter.summary() if spec_adapter else {},
        "generic_open_world_proof":proof_bridge.summary() if proof_bridge else None,
        "positive_ready_preflight":(
            proof_bridge.summary()["positive_ready_preflight"] if proof_bridge else None),
    }


def run(profile:Path,stationary_st:Path,stationary_two:Path,
        moving_st:Path,moving_two:Path,adapter_factory=None,
        proof_bridge_factory=None)->dict:
    ir=parse_profile(profile.read_bytes(),require_source=True,
                     expected_git_blob=PINNED_FURY_BLOB)
    cases={}
    total=Counter()
    all_exits=Counter()
    all_prefix=Counter()
    all_adapter=Counter()
    all_proof=Counter()
    for name,folder,targets,actual_if,attempts in (
        ("stationary_st",stationary_st,1,255,1542),
        ("stationary_two_target",stationary_two,2,222,1030),
        ("moving_st",moving_st,1,253,1650),
        ("moving_two_target",moving_two,2,223,1186)
    ):
        folder=folder.resolve(strict=True)
        base=verify_folder(folder,targets,ir)
        raw=(folder/"simc_native_log.txt").read_bytes()
        trace=raw.decode("utf-8")
        samples=source_if_samples(trace,ir,base)
        adapter=adapter_factory() if adapter_factory is not None else None
        bridge=proof_bridge_factory() if proof_bridge_factory is not None else None
        result=analyze_trace(trace,ir,samples,spec_adapter=adapter,
                             proof_bridge=bridge)
        counts=result["counts"]
        all_adapter.update(result["SpecAdapter_source_witness"])
        if bridge is not None:
            all_proof.update(result["generic_open_world_proof"]["counts"])
        if (len(samples)!=actual_if or
            counts["real_source_IF_samples"]!=actual_if or
            counts["Native_action_ready_attempts"]!=attempts or
            base["counts"]["all_native_action_ready_attempts"]!=attempts):
            raise PriorityFrontierError("PINNED_ACTUAL_NATIVE_SCENARIO_COUNTS_DRIFT")
        for key,value in counts.items():
            total[key]+=value
        all_exits.update(result["Native_source_base_first_exits"])
        all_prefix.update(result["foreground_prefix_screening"])
        cases[name]={
            **result,
            "official_source_log_sha256":sha(raw),
            "official_native_binary_sha256":base["native_binary_sha256"],
            "effective_apl_sha256":base["native_apl_sha256"],
        }
    if (total["Native_action_ready_attempts"]!=5408 or
        total["real_source_IF_samples"]!=953 or
        len({x["official_native_binary_sha256"] for x in cases.values()})!=1):
        raise PriorityFrontierError("CROSS_SCENARIO_SOURCE_COHORT_NOT_IDENTICAL")
    return {
        "schema":(SCHEMA if adapter_factory is None else
                  "ZrotNativeSpecAdapterSourcePriorityFrontierV1"),
        "product_policy_id":POLICY,
        "status":"NATIVE_PRE_IF_SOURCE_FALSE_JOIN_PLUS_BOUNDED_PRIORITY_FRONTIER",
        "four_scenarios":cases,
        "totals":dict(sorted(total.items())),
        "total_actual_native_base_exit_reasons":dict(sorted(all_exits.items())),
        "foreground_frontier":dict(sorted(all_prefix.items())),
        "SpecAdapter_source_witness":dict(sorted(all_adapter.items())),
        "generic_open_world_proof_counts":dict(sorted(all_proof.items())),
        "Native_false_or_ready_bit_not_independent_AST_input":True,
        "independent_IF_only_at_observed_visited_source_rows":True,
        "native_selected_action_not_independently_ready":True,
        "native_choice_not_optimality_proof":True,
        "simc_movement_forecast_not_actual_WoW_prediction":True,
        "WCL_API_calls":0,"MAIN_promoted":False,
        "full_General_Rotation_or_trainer_complete":False,
    }


def selftest():
    ir=parse_profile(
        b"actions=alpha,if=rage>50\n"
        b"actions+=/beta\n",require_source=False)
    r=ir["action_lists"]["default"][0]
    k=(10,"default",1,"alpha")
    sample={"key":k,"source_sha256":r["source_sha256"],
            "source_if":"rage>50","symbols":["rage"],
            "independent_IF_bool":0,"Native_IF_bool_POST_comparator":0}
    trace="\n".join([
        "ZROT_NATIVE_SELECT_V1|ENTER|10|default|FOREGROUND",
        "ZROT_NATIVE_READY_GUARDS_PRE_V1|10|default|1|alpha|1|1|0|-1|1",
        "ZROT_NATIVE_CD_QUEUE_CLOCK_PRE_V1|10|default|1|alpha|0|1|1|-10",
        "ZROT_NATIVE_CD_TOLERANCE_PRE_V1|10|default|1|alpha|-1|10",
        "ZROT_NATIVE_BASE_ACTION_READY_ENTER_V1|10|alpha",
        "ZROT_NATIVE_BASE_READY_ENTER_V1|10|alpha",
        "ZROT_NATIVE_IF_FACT_V1|10|default|1|alpha|0|3|20|1",
        "ZROT_NATIVE_BASE_POST_EXIT_V1|10|alpha|IF_FALSE",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|1|alpha|0",
        "ZROT_NATIVE_READY_GUARDS_PRE_V1|10|default|2|beta|1|1|0|-1|1",
        "ZROT_NATIVE_CD_QUEUE_CLOCK_PRE_V1|10|default|2|beta|0|1|1|-10",
        "ZROT_NATIVE_CD_TOLERANCE_PRE_V1|10|default|2|beta|-1|10",
        "ZROT_NATIVE_BASE_ACTION_READY_ENTER_V1|10|beta",
        "ZROT_NATIVE_BASE_READY_ENTER_V1|10|beta",
        "ZROT_NATIVE_BASE_POST_EXIT_V1|10|beta|FULL_BASE_TRUE",
        "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|2|beta|1",
        "ZROT_NATIVE_SELECT_V1|RETURN|10|default|beta|DIRECT",
    ])
    got=analyze_trace(trace,ir,[sample])
    c=got["counts"]
    assert c["Native_action_ready_attempts"]==2
    assert c["IF_FALSE_exits_independently_proved"]==1
    assert c["Native_foreground_root_returned"]==1
    assert c["foreground_prior_candidates_independently_eliminated"]==1
    assert got["foreground_prefix_screening"][
        "all_prior_attempts_source_excluded_but_winner_NOT_ready_proven"]==1
    assert got["bounded_foreground_source_frontier_examples"][0]["independent_winner_ready"] is False
    for bad in (
        trace.replace("IF_FALSE","TARGET_FALSE"),
        trace.replace("ZROT_NATIVE_IF_FACT_V1|10|default|1|alpha",
                      "ZROT_NATIVE_IF_FACT_V1|10|default|2|alpha"),
        trace.replace("ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|2|beta|1",
                      "ZROT_NATIVE_SELECT_V1|ATTEMPT|10|default|default|3|beta|1"),
    ):
        if bad==trace:raise AssertionError("NO_MALFORMED_SAMPLE")
        if "TARGET_FALSE" in bad:
            # Former IF event remains valid, but no observed IF_FALSE exit:
            # no independent exclusion is allowed from unvisited guard path.
            result=analyze_trace(bad,ir,[sample])
            assert result["counts"].get("IF_FALSE_exits_independently_proved",0)==0
            continue
        try:analyze_trace(bad,ir,[sample])
        except PriorityFrontierError:pass
        else:raise AssertionError("SOURCE_IDENTITY_DRIFT_ACCEPTED")
    # An identical source/time row can recur; FIFO chronological occurrence
    # must distinguish the two and refuse swapped independent facts.
    assert len({sample["key"],k})==1
    unknown={**sample,"independent_IF_bool":None}
    w=analyze_trace(trace,ir,[unknown])
    assert w["counts"]["IF_FALSE_exits_UNKNOWN"]==1
    assert w["counts"]["foreground_prior_candidates_UNKNOWN"]==1
    return {
        "status":"PASS_OFFLINE_SYNTHETIC","checks":13,
        "Native_not_run":True,"WCL_API_calls":0,
        "full_action_priority_proven":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--native-st-dir",type=Path)
    p.add_argument("--native-2t-dir",type=Path)
    p.add_argument("--native-moving-st-dir",type=Path)
    p.add_argument("--native-moving-2t-dir",type=Path)
    p.add_argument("--spec-adapter",choices=["warrior"])
    p.add_argument("--proof-engine",choices=["open-world"])
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    args=(a.official_profile,a.native_st_dir,a.native_2t_dir,
          a.native_moving_st_dir,a.native_moving_2t_dir)
    if not any(args):
        result=selftest()
    elif all(args):
        factory=None
        if a.spec_adapter=="warrior":
            from simc_native_warrior_priority_frontier_adapter_v1 import WarriorPriorityAdapter
            factory=WarriorPriorityAdapter
        proof_factory=None
        if a.proof_engine=="open-world":
            from simc_native_decision_proof_bridge_v1 import NativeProofBridge
            proof_factory=NativeProofBridge
        result=run(*args,adapter_factory=factory,
                   proof_bridge_factory=proof_factory)
    else:p.error("all pinned actual Native input paths required")
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
        print("INDEPENDENT_SOURCE_IF_FALSE_PRIORITY_FRONTIER_SHA256="+sha(raw))
    else:print(raw.decode(),end="")


if __name__=="__main__":main()
