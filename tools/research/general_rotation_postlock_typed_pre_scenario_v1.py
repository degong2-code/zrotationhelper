#!/usr/bin/env python3
"""Generic WCL typed Strict PRE -> source IF *sensitivity* research bridge.

Takes a frozen numeric-only WCL cohort, matching provenance-pinned raw actor
transport, the independently rebuilt joint aura+numeric-power Strict PRE,
the original SimC source hypothesis IR and a *post-lock* source-row candidate
binding. The externally supplied operand mapping makes assumptions explicit:
a WCL aura spell-ID name link and numeric power scale are not mechanic truth.

Replays each source IF AST under declared numeric-unit scenarios. This is
useful for locating invariant/sensitive/missing operands, but it NEVER proves
the exact APL row selected by a player, GCD/charges/cooldown READY, mandatory
priority or target-dummy errors. Historical distinct report is not recast as
a freshly locked holdout. No args runs synthetic two-class regressions.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import canonical,evaluate_ast,truth,git_blob
from general_rotation_wcl_postlock_source_ir_bridge_v1 import (
    NUMERIC_SCHEMA,POLICY,EVIDENCE_SCHEMA,SOURCE_SCHEMA,
    load as load_json
)
from general_rotation_postlock_numeric_spell_adapter_v1 import (
    SCHEMA as BINDING_COMPILE_SCHEMA
)
from wcl_raw_actor_numeric_transport_v1 import (
    _check_transport,SCHEMA as RAW_TRANSPORT_SCHEMA,ORIGIN
)

SCHEMA="ZrotGenericPostlockWclTypedPreIfSensitivityV1"
MAP_SCHEMA="ZrotGenericPostlockWclExploratoryOperandMapV1"
JOIN_SCHEMA="ZrotWclNumericAuraResourceStrictPreJoinV1"
HEX=re.compile(r"^[0-9a-f]{64}$")
SYM=re.compile(r"^[a-z][a-z0-9_.]*$")

class TypedIfError(ValueError):pass

def need(ok,reason):
    if not ok:raise TypedIfError(reason)

def sha(data:bytes):return sha256(data).hexdigest()

def _join_checks(numeric,transport,joint):
    need(type(numeric)==dict and numeric.get("schema")==NUMERIC_SCHEMA and
         numeric.get("source_APL_injected_in_numeric_phase") is False and
         numeric.get("candidate_set_changed_after_lock") is False and
         numeric.get("ready_or_priority_proven") is False and
         numeric.get("raw_discovery_and_holdout_independent_audit")=="NOT_RUN" and
         numeric.get("source_kind")==ORIGIN and
         type(numeric.get("lock_sha256")) is str and
         HEX.fullmatch(numeric["lock_sha256"]),
         "FROZEN_WCL_NUMERIC_BLIND_PHASE_REQUIRED")
    _check_transport(transport)
    need(numeric.get("holdout_raw_receipt_sha256")==
         transport["raw_receipt_sha256"] and
         numeric.get("holdout_scope")==
            transport["report_code"]+"/"+str(transport["fight_id"]) and
         numeric.get("holdout_actor")==str(transport["actor_id"]) and
         type(numeric.get("numeric_casts"))==list and
         len(numeric["numeric_casts"])==
            transport["actor_numeric_cast_count"] and
         0<len(numeric["numeric_casts"])<=50000,
         "WCL_FROZEN_HOLDOUT_SCOPE_ACTOR_OR_CASTS_DIFFERENT")
    need(type(joint)==dict and joint.get("schema")==JOIN_SCHEMA and
         joint.get("policy_id")==POLICY and
         joint.get("source_numeric_transport_sha256")==
            transport["numeric_transport_sha256"] and
         type(joint.get("joined_numeric_pre_sha256")) is str and
         joint["joined_numeric_pre_sha256"]==
             sha(canonical({k:v for k,v in joint.items()
                            if k!="joined_numeric_pre_sha256"})) and
         joint.get("complete_and_competing_READY_proven")==0 and
         joint.get("General_Rotation_priority_promoted") is False and
         joint.get("dummy_training_error_proven") is False,
         "RAW_TYPED_PRE_MATRIX_DIGEST_PROVENANCE_OR_CLAIM_INVALID")
    numeric_rows=numeric["numeric_casts"];raw=transport["cast_events"]
    join_rows=joint.get("per_numeric_cast")
    need(type(join_rows)==list and
         len(numeric_rows)==len(raw)==len(join_rows)==
            joint.get("actor_cast_rows"),
         "NUMERIC_CASTS_JOINT_PRE_COUNTS_NOT_EQUAL")
    expected={x["event_id"]:(x["at_ms"],x["spell_id"])
              for x in numeric_rows}
    raw_lookup={x["event_id"]:(x["t_ms"],x["spell_id"])
                for x in raw}
    joined={x["numeric_raw_cast_event_id"]:(x["at_ms"],x["spell_id"])
            for x in join_rows}
    need(len(expected)==len(raw_lookup)==len(joined)==len(raw) and
         expected==raw_lookup==joined,
         "WCL_NUMERIC_RAW_EVENT_ID_TIME_SPELL_MISMATCH")
    for row in join_rows:
        t=row["at_ms"]
        need(row["complete_spell_READY"]=="UNKNOWN" and
             row["other_ready_actions"]=="UNKNOWN" and
             row["dummy_wrong_cast"]=="UNKNOWN" and
             row["source_APL_candidate_row"]==
                "UNKNOWN_UNTIL_POSTLOCK_ADAPTER",
             "RAW_SOURCE_PRE_WAS_GAMEPLAY_UPGRADED")
        for fact in row["raw_aura_strict_pre"].values():
            need(fact.get("status") in ("KNOWN","UNKNOWN"),
                 "WCL_AURA_PRE_UNDECLARED")
            if fact["status"]=="KNOWN":
                need(type(fact["event_t_ms"]) is int and
                     fact["event_t_ms"]<t and
                     fact["raw_receipt_sha256"]==transport["raw_receipt_sha256"] and
                     type(fact["value"]) is bool,
                     "RAW_AURA_PRE_TIME_OR_VALUE_INVALID")
        for power, fact in row["raw_numeric_power_owned_strict_pre"].items():
            need(type(fact["raw_power_type"]) is int and
                 str(fact["raw_power_type"])==power and
                 type(fact["strict_prior_at_ms"]) is int and
                 fact["strict_prior_at_ms"]<t and
                 fact["source_checkpoint_raw_receipt_sha256"]==
                     transport["raw_receipt_sha256"] and
                 fact["game_resource_units_conversion"]=="UNKNOWN" and
                 fact["game_resource_kind_semantics"]=="UNKNOWN" and
                 fact["owner_proof"] in (
                    "ACTOR_OWNED_SOURCE","ACTOR_OWNED_TARGET") and
                 type(fact["raw_amount"]) in (int,float) and
                 type(fact["raw_maximum"]) in (int,float) and
                 math.isfinite(float(fact["raw_amount"])) and
                 math.isfinite(float(fact["raw_maximum"])) and
                 0<=fact["raw_amount"]<=fact["raw_maximum"],
                 "RAW_RESOURCE_PRE_INCOMPLETE_OWNER_OR_TIME")
    return {x["numeric_raw_cast_event_id"]:x for x in join_rows}

def _source_checks(numeric,source_case,compiled):
    need(type(source_case)==dict and
         source_case.get("schema")==EVIDENCE_SCHEMA and
         source_case.get("policy_id")==POLICY and
         source_case.get("WCL_independent_candidate_lock")=="NOT_RUN" and
         source_case.get("WCL_independent_holdout")=="NOT_RUN" and
         source_case.get("source_full_READY_proven")==0 and
         source_case.get("source_order_priority_proven")==0 and
         source_case.get("dummy_wrong_skill")=="UNKNOWN",
         "SOURCE_IR_ALREADY_PROMOTED")
    ir=source_case.get("source_hypothesis_IR",{})
    need(ir.get("schema")==SOURCE_SCHEMA and
         ir.get("evidence_status",{}).get(
           "validated_general_rotation_priority") is False,
         "NOT_SOURCE_ONLY_APL_HYPOTHESIS")
    need(type(compiled)==dict and
         compiled.get("schema")==BINDING_COMPILE_SCHEMA and
         compiled.get("policy_id")==POLICY and
         compiled.get("frozen_numeric_phase_sha256")==sha(canonical(numeric)) and
         compiled.get("frozen_numeric_lock_sha256")==numeric["lock_sha256"] and
         compiled.get("source_case_sha256")==sha(canonical(source_case)) and
         compiled.get("source_git_blob")==ir["source_git_blob"] and
         compiled.get("source_spec")==source_case["source_spec"] and
         compiled.get("source_target_count")==source_case["target_count"] and
         compiled.get("external_adapter_status")=="CANDIDATE_POSTLOCK_ONLY" and
         compiled.get("source_spell_ID_mapping_current_Retail_independently_audited") is False and
         compiled.get("allow_whole_spell_READY_from_mapping") is False and
         compiled.get("allow_selected_APL_row_from_cast") is False and
         compiled.get("allow_dummy_wrong_cast_from_mapping") is False,
         "POSTLOCK_SOURCE_CANDIDATE_COMPILE_IDENTITY_OR_CLAIM_MISMATCH")
    binding=compiled["binding"]
    need(binding.get("binding_stage")=="POST_LOCK_ONLY" and
         binding.get("bound_numeric_lock_sha256")==numeric["lock_sha256"] and
         binding.get("source_profile_git_blob")==ir["source_git_blob"] and
         binding.get("action_identity_and_mechanic_independently_audited") is False and
         binding.get("build_equivalence_independently_verified") is False and
         binding.get("WCL_target_count_at_cast_verified") is False,
         "SOURCE_BINDING_WRONGLY_CERTIFIED")
    lists=ir["source_only_priority_graph"]["lists"]
    indexes={};seen=set()
    for m in binding["numeric_to_source_rows"]:
        spell=m["spell_id"];name=m["source_list"];i=m["source_index"]
        need(type(spell)==int and
             spell in numeric["numeric_locked_spell_ids"] and
             name in lists and
             type(i)==int and 0<=i<len(lists[name]) and
             (spell,name,i) not in seen and
             m["source_row_sha256"]==
               lists[name][i]["identity"]["source_line_sha256"] and
             m["symbol_to_raw_signal"]=={},
             "SOURCE_APL_ROW_NOT_EXACT_OR_PRESEMANTICS_ALREADY_INJECTED")
        seen.add((spell,name,i))
        indexes.setdefault(spell,[]).append(lists[name][i])
    need(len(seen)==compiled["output_bindings"],
         "SOURCE_CANDIDATE_MAPPING_ROW_COUNT_DRIFT")
    return indexes


def _temporal_checks(transport,temporal):
    """Require original numeric-cast event IDs and raw receipt to match."""
    from wcl_raw_actor_aura_temporal_pre_v1 import SCHEMA as AURA_TEMPORAL_SCHEMA
    need(type(temporal)==dict and
         temporal.get("schema")==AURA_TEMPORAL_SCHEMA and
         temporal.get("policy_id")==POLICY and
         temporal.get("source_numeric_transport_sha256")==
             transport["numeric_transport_sha256"] and
         temporal.get("source_raw_receipt_sha256")==
             transport["raw_receipt_sha256"] and
         temporal.get("source_raw_page_sha256")==
             transport["raw_source_page_sha256"] and
         temporal.get("aura_remains_known")==0 and
         temporal.get("full_GCD_cooldown_charge_READY_proven")==0 and
         temporal.get("mandatory_general_rotation_rule_promoted") is False and
         temporal.get("raw_last_aura_event_age_never_promoted_to_remaining_duration") is True and
         temporal.get("temporal_matrix_sha256")==
             sha(canonical({k:v for k,v in temporal.items()
                            if k!="temporal_matrix_sha256"})),
         "TEMPORAL_AURA_RAW_SOURCE_OR_GAMEPLAY_AUTHORITY_INVALID")
    rows=temporal.get("per_numeric_cast")
    casts=transport["cast_events"]
    need(type(rows)==list and len(rows)==len(casts)==
         temporal.get("actual_cast_rows"),
         "TEMPORAL_AURA_CAST_COUNT_DIFFERS_FROM_RAW")
    keyed={}
    for row in rows:
        ident=row["numeric_raw_cast_event_id"]
        need(ident not in keyed and
             row["aura_remaining_duration_for_any_spell"]=="UNKNOWN" and
             row["complete_action_READY"]=="UNKNOWN",
             "TEMPORAL_AURA_CAST_ROW_DUPLICATE_OR_PROMOTED")
        keyed[ident]=row
    need(set(keyed)=={c["event_id"] for c in casts},
         "TEMPORAL_CAST_ID_NOT_SAME_AS_FROZEN_RAW")
    for cast in casts:
        row=keyed[cast["event_id"]]
        t=cast["t_ms"]
        need(row["at_ms"]==t and row["spell_id"]==cast["spell_id"],
             "TEMPORAL_CAST_TIMESTAMP_OR_ID_DIFFERENT")
        for sid,aura in row["per_numeric_aura_spell"].items():
            need(sid.isdecimal() and
                 aura["aura_remaining_duration_ms"]=="UNKNOWN" and
                 type(aura["last_transition_t_ms"])==int and
                 aura["last_transition_t_ms"]<t and
                 aura["source_checkpoint_raw_receipt_sha256"]==
                    transport["raw_receipt_sha256"] and
                 aura["explicit_stack_status"] in (
                    "EXACT_RAW_STACK_OBSERVED","UNKNOWN_NOT_EXPLICITLY_OBSERVED") and
                 (aura["explicit_stack"] is None or
                  type(aura["explicit_stack"])==int and
                  aura["explicit_stack"]>=0) and
                 (aura["explicit_stack"] is None)==(
                  aura["explicit_stack_status"]==
                    "UNKNOWN_NOT_EXPLICITLY_OBSERVED"),
                 "WCL_TEMPORAL_AURA_STACK_FACT_NOT_STRICT_PRIOR")
    return keyed

def _map_checks(mapping,numeric,source_case,compiled):
    need(type(mapping)==dict and mapping.get("schema")==MAP_SCHEMA and
         mapping.get("policy_id")==POLICY and
         mapping.get("use_stage")=="AFTER_FROZEN_NUMERIC_CANDIDATE_LOCK_ONLY" and
         mapping.get("assert_current_game_mechanic_truth") is False and
         mapping.get("assert_WCL_actor_build_equivalence") is False and
         mapping.get("assert_WCL_target_count_match") is False and
         mapping.get("assert_full_READY_or_player_error") is False and
         mapping.get("frozen_numeric_lock_sha256")==numeric["lock_sha256"] and
         mapping.get("source_profile_git_blob")==
             source_case["source_hypothesis_IR"]["source_git_blob"] and
         type(mapping.get("operand_bindings"))==list and
         0<len(mapping["operand_bindings"])<=80,
         "SOURCE_OPERAND_ASSUMPTIONS_NOT_EXPLICIT_POSTLOCK")
    indexes={};scale_operands={}
    for entry in mapping["operand_bindings"]:
        need(type(entry)==dict and
             type(entry.get("source_symbol"))==str and
             SYM.fullmatch(entry["source_symbol"]) and
             entry["source_symbol"] not in indexes and
             entry.get("confidence")==
                "EXPLORATORY_UNVERIFIED_MECHANIC_AND_BUILD",
             "SOURCE_OPERAND_SEMANTIC_TRUTH_MUST_NOT_BE_ASSUMED")
        symbol=entry["source_symbol"]
        kind=entry.get("raw_kind")
        if kind=="WCL_RAW_AURA_BOOL":
            need(type(entry.get("raw_signal"))==str and
                 re.fullmatch(r"raw_aura_[0-9]+_active",
                              entry["raw_signal"]) and
                 set(entry)=={
                   "source_symbol","raw_kind","raw_signal","confidence"},
                 "AURA_OPERAND_UNPINNED_NUMERIC_SIGNAL")
        elif kind=="WCL_RAW_ACTOR_NUMERIC_POWER":
            factors=entry.get("raw_units_per_source_unit_scenarios")
            need(type(entry.get("raw_power_type"))==int and
                 0<=entry["raw_power_type"]<=255 and
                 type(factors)==list and 1<=len(factors)<=4 and
                 all(type(x) in (int,float) and
                     math.isfinite(float(x)) and 0<x<=100000
                     for x in factors) and
                 len(set(factors))==len(factors) and
                 set(entry)=={
                   "source_symbol","raw_kind","raw_power_type",
                   "raw_units_per_source_unit_scenarios","confidence"},
                 "NUMERIC_RESOURCE_SCALING_MUST_BE_SCENARIO_ONLY")
            scale_operands[symbol]=factors
        elif kind=="WCL_RAW_AURA_EXPLICIT_STACK":
            need(symbol.startswith("buff.") and symbol.endswith(".stack") and
                 type(entry.get("raw_numeric_aura_spell_id"))==int and
                 entry["raw_numeric_aura_spell_id"]>0 and
                 set(entry)=={"source_symbol","raw_kind",
                             "raw_numeric_aura_spell_id","confidence"},
                 "STACK_SOURCE_SYMBOL_MUST_BE_EXPLICIT_EXPLORATORY_ID_NOT_REMAINS")
        else:raise TypedIfError("UNSUPPORTED_RAW_SOURCE_OPERAND_KIND")
        indexes[symbol]=entry
    scenarios=[dict(zip(scale_operands,values))
               for values in product(*scale_operands.values())] if scale_operands else [{}]
    need(0<len(scenarios)<=16,"NUMERIC_POWER_SCENARIOS_UNBOUNDED")
    return indexes,scenarios

def _facts(row, mapping, scenario, required_symbols, temporal_row):
    values={};evidence={};unknown=[]
    t=row["at_ms"]
    for symbol in required_symbols:
        contract=mapping.get(symbol)
        if contract is None:
            unknown.append(symbol)
            continue
        if contract["raw_kind"]=="WCL_RAW_AURA_BOOL":
            raw_signal=contract["raw_signal"]
            prior=row["raw_aura_strict_pre"].get(raw_signal)
            if prior is None or prior["status"]!="KNOWN":
                unknown.append(symbol);continue
            timestamp=prior["event_t_ms"];val=float(prior["value"])
            raw_rec={"kind":"WCL_RAW_AURA_BOOL",
                     "raw_signal":raw_signal,"raw_value":prior["value"],
                     "raw_source_event_id":prior["source_event_id"],
                     "strict_pre_ms":timestamp,
                     "scenario_assumption_only":True}
        elif contract["raw_kind"]=="WCL_RAW_AURA_EXPLICIT_STACK":
            need(temporal_row is not None,
                 "EXPLICIT_AURA_STACK_SOURCE_REQUIRES_PROVEN_TEMPORAL_PRE")
            sid=str(contract["raw_numeric_aura_spell_id"])
            prior=temporal_row["per_numeric_aura_spell"].get(sid)
            if (prior is None or
                prior["explicit_stack_status"]!="EXACT_RAW_STACK_OBSERVED"):
                unknown.append(symbol);continue
            timestamp=prior["last_transition_t_ms"]
            val=float(prior["explicit_stack"])
            raw_rec={"kind":"WCL_RAW_AURA_EXPLICIT_STACK",
                     "raw_numeric_aura_spell_id":
                         contract["raw_numeric_aura_spell_id"],
                     "raw_explicit_numeric_stack":prior["explicit_stack"],
                     "raw_source_event_ids":prior["source_event_ids"],
                     "strict_pre_ms":timestamp,
                     "scenario_assumption_only":True,
                     "game_buff_identity_verified":False}
        else:
            raw_kind=str(contract["raw_power_type"])
            prior=row["raw_numeric_power_owned_strict_pre"].get(raw_kind)
            if prior is None:
                unknown.append(symbol);continue
            timestamp=prior["strict_prior_at_ms"]
            factor=scenario[symbol]
            val=float(prior["raw_amount"])/factor
            raw_rec={"kind":"WCL_RAW_ACTOR_NUMERIC_POWER",
                     "raw_power_type":contract["raw_power_type"],
                     "raw_amount":prior["raw_amount"],
                     "assumed_raw_units_per_source_unit":factor,
                     "raw_owner_proof":prior["owner_proof"],
                     "strict_pre_ms":timestamp,
                     "scenario_assumption_only":True}
        need(timestamp<t and math.isfinite(val),
             "WCL_OBSERVED_PRE_NOT_STRICT_EARLIER")
        values[symbol]={"value":val,"timestamp":timestamp,
                        "provenance":"STRICT_PRE_OBSERVATION"}
        evidence[symbol]=raw_rec
    return values,evidence,unknown

def evaluate(numeric,transport,joint,source_case,compiled,mapping,*,temporal=None):
    """Evaluate all plausible original source-row IFs, with zero auto-promotion."""
    cast_pre=_join_checks(numeric,transport,joint)
    temporal_casts=(_temporal_checks(transport,temporal)
                    if temporal is not None else {})
    rows=_source_checks(numeric,source_case,compiled)
    operand_map,scenarios=_map_checks(mapping,numeric,source_case,compiled)
    need(temporal is not None or
         all(x["raw_kind"]!="WCL_RAW_AURA_EXPLICIT_STACK"
             for x in operand_map.values()),
         "SOURCE_STACK_OPERAND_REQUIRES_EXPLICIT_RAW_TEMPORAL_MATRIX")
    stats=Counter();raw_fact_stats=Counter()
    required_source_symbols=Counter()
    unmapped_source_symbols=Counter()
    raw_status_unknown=Counter()
    source_rows=[];per_cast=[]
    for cast in numeric["numeric_casts"]:
        idnum=cast["event_id"]
        pre=cast_pre[idnum]
        linked=rows.get(cast["spell_id"],[])
        matches=[]
        for node in linked:
            if_cond=node["conditions"].get("if")
            required=sorted(set(if_cond["symbols"])) if if_cond else []
            for symbol in required:
                required_source_symbols[symbol]+=1
                if symbol not in operand_map:
                    unmapped_source_symbols[symbol]+=1
            statuses=[];scenario_examples=[]
            for scenario in scenarios:
                facts,evidence,missing=_facts(
                    pre,operand_map,scenario,required,
                    temporal_casts.get(idnum))
                for symbol in evidence:raw_fact_stats[symbol]+=1
                for symbol in missing:raw_status_unknown[symbol]+=1
                if if_cond is None:
                    status="NO_EXPLICIT_IF"
                else:
                    value=truth(evaluate_ast(
                        if_cond["source_ast"],facts,
                        action_timestamp=cast["at_ms"],strict_pre=True))
                    status=("TRUE" if value is True else
                            "FALSE" if value is False else "UNKNOWN")
                statuses.append(status)
                scenario_examples.append({
                  "assumed_numeric_unit_divisors":scenario,
                  "hypothetical_source_if":status,
                  "WCL_raw_facts_with_unverified_source_semantics":evidence,
                  "declared_operand_without_RAW_PRE":missing
                })
            possibilities=sorted(set(statuses))
            if if_cond is None:result="NO_EXPLICIT_IF_NOT_READY_PROOF"
            elif len(possibilities)>1:
                result="SCALE_SENSITIVE_OR_SCENARIO_UNKNOWN"
            else:result=possibilities[0]+"_UNDER_UNVERIFIED_SEMANTIC_LINK"
            stats[result]+=1
            matches.append({
               "source_identity":node["identity"],
               "source_action_token":node["action"],
               "source_conditional_symbols":
                  if_cond["symbols"] if if_cond else [],
               "raw_scenario_condition_result":result,
               "raw_scenario_possible_states":possibilities,
               "scenario_diagnostics":scenario_examples,
               "certified_current_game_source_IF":"UNKNOWN",
               "source_row_was_selected":"UNKNOWN",
               "action_physical_READY":"UNKNOWN",
               "competing_priority":"UNKNOWN"
            })
        if len(linked)>1:stats["MULTIPLE_SOURCE_APL_ROWS_CAST"]+=1
        elif len(linked)==1:stats["SINGLE_SOURCE_APL_ROW_CAST"]+=1
        else:stats["NO_SOURCE_APL_ROW_CAST"]+=1
        if linked:stats["WCL_CAST_WITH_POSTLOCK_TOKEN_CANDIDATE"]+=1
        per_cast.append({
          "raw_WCL_event_id":idnum,"at_ms":cast["at_ms"],
          "spell_id":cast["spell_id"],
          "potential_source_rows":matches,
          "source_row_choice":"UNKNOWN" if matches else
             "UNKNOWN_NO_SOURCE_TOKEN_MATCH",
          "raw_owned_power_and_aura_join_sha256":
             joint["joined_numeric_pre_sha256"],
          "WCL_actual_target_count":"UNKNOWN",
          "WCL_build_vs_SimC_profile":"UNKNOWN",
          "source_action_mandatory_priority":"UNKNOWN",
          "dummy_wrong_cast":"UNKNOWN"
        })
        source_rows.extend(matches)
    need(len(per_cast)==len(numeric["numeric_casts"]),
         "RAW_WCL_CAST_OR_SOURCE_SET_DROPPED")
    return {
      "schema":SCHEMA,"policy_id":POLICY,
      "input_original_WCL_numeric_lock_sha256":numeric["lock_sha256"],
      "source_IR_git_blob":
        source_case["source_hypothesis_IR"]["source_git_blob"],
      "bound_WCL_numeric_phase_sha256":sha(canonical(numeric)),
      "raw_actor_transport_sha256":transport["numeric_transport_sha256"],
      "joint_owned_power_aura_pre_sha256":joint["joined_numeric_pre_sha256"],
      "optional_raw_aura_temporal_matrix_sha256":(
          temporal["temporal_matrix_sha256"] if temporal is not None else None),
      "raw_numeric_aura_stack_cast_channel_replayed":temporal is not None,
      "source_candidate_binding_sha256":sha(canonical(compiled)),
      "postlock_exploratory_operand_map_sha256":sha(canonical(mapping)),
      "WCL_raw_evidence_origin":numeric["source_kind"],
      "numeric_observed_casts":len(per_cast),
      "raw_WCL_candidate_casts_with_source_token":
          stats["WCL_CAST_WITH_POSTLOCK_TOKEN_CANDIDATE"],
      "individual_source_IF_candidate_row_probes":len(source_rows),
      "source_conditional_scenario_counts":dict(sorted(stats.items())),
      "source_operand_scenario_usage_counts":dict(sorted(raw_fact_stats.items())),
      "required_source_IF_operand_occurrence_counts":
          dict(sorted(required_source_symbols.items())),
      "unmapped_source_IF_operand_occurrence_counts":
          dict(sorted(unmapped_source_symbols.items())),
      "unobserved_source_IF_operand_scenario_counts":
          dict(sorted(raw_status_unknown.items())),
      "explored_unit_conversion_scenarios":scenarios,
      "source_operand_semantics_independently_certified":False,
      "WCL_actor_build_and_target_source_equivalent":False,
      "certified_source_IF_guard_true_count":0,
      "real_competing_spell_READY_proven":0,
      "mandatory_General_Rotation_priorities_promoted":0,
      "dummy_wrong_cast_verdicts":0,
      "observed_numeric_WCL_ID_does_not_identify_source_APL_row":True,
      "per_numeric_cast":per_cast,
      "new_WCL_API_calls":0,
      "new_SimC_CXX_builds":0,
      "MAIN_promoted":False
    }

def selftest():
    from general_rotation_source_hypothesis_ir_v1 import compile_profile
    from wcl_raw_actor_numeric_transport_v1 import (
       SCHEMA as RAW_SCHEMA,ORIGIN as RAW_ORIGIN
    )
    from general_rotation_postlock_numeric_spell_adapter_v1 import (
       compile_binding,ADAPTER_SCHEMA
    )
    import copy
    positive=0;negative=0
    def must_fail(fn):
        nonlocal negative
        try:fn()
        except (TypedIfError,KeyError,ValueError):negative+=1
        else:raise AssertionError("RESEARCH_SEMANTIC_LEAK_OR_BAD_WITNESS_ACCEPTED")
    for cls,spec in [("warrior","fury"),("mage","arcane")]:
        p=(cls+'="Synthetic"\nspec='+spec+'\n'
           'actions=alpha,if=buff.ready.up&energy>=100\n'
           'actions+=/alpha,if=energy<100\n'
           'actions+=/alpha,if=energy>=100&variable.missing\n'
           'actions+=/alpha,if=buff.proc.stack>=2\n').encode()
        model=compile_profile(
            p,{"key":spec,"class_key":cls,"git_blob":git_blob(p)})
        case={"schema":EVIDENCE_SCHEMA,"policy_id":POLICY,
           "class_key":cls,"source_spec":spec,"target_count":1,
           "source_hypothesis_IR":model,"source_full_READY_proven":0,
           "source_order_priority_proven":0,
           "WCL_independent_candidate_lock":"NOT_RUN",
           "WCL_independent_holdout":"NOT_RUN",
           "dummy_wrong_skill":"UNKNOWN",
           "native_selected_used_as_positive_ready_input":False}
        adapter={
           "schema":ADAPTER_SCHEMA,"scope_policy_id":POLICY,
           "specialization":{"class":cls.title(),"spec":spec.title(),"spec_id":999},
           "source_simc":{"repo":"simulationcraft/simc",
             "revision":"b522cded8c26b97dac03fdf56e57a03ec7e8faa6",
             "path":"engine/class_modules/sc_synthetic.cpp",
             "git_blob_sha1":"a"*40},
           "candidates":[{
              "spell_id":1201,"canonical_action":"alpha","family":"SYNTH",
              "manuality":"DIRECT_SPELL_CANDIDATE","readiness":"UNKNOWN"}],
           "allow_infer_exact_cd_from_gap":False,
           "allow_infer_availability_of_alternative":False,
           "allow_infer_priority_or_player_error":False,
           "protected_blind_lock_sha256":"b"*64}
        numeric={
           "schema":NUMERIC_SCHEMA,"lock_sha256":"b"*64,
           "source_kind":RAW_ORIGIN,
           "numeric_locked_spell_ids":[1201],
           "numeric_casts":[{"event_id":"cast-1","at_ms":1000,
                            "spell_id":1201}],
           "holdout_scope":"synthetic-report/1",
           "holdout_actor":"42",
           "holdout_raw_receipt_sha256":"c"*64,
           "source_APL_injected_in_numeric_phase":False,
           "candidate_set_changed_after_lock":False,
           "raw_discovery_and_holdout_independent_audit":"NOT_RUN",
           "ready_or_priority_proven":False}
        transport={
          "schema":RAW_SCHEMA,"policy_id":POLICY,"origin":RAW_ORIGIN,
          "source_cohort_role":"HOLDOUT",
          "prior_disjoint_report_holdout_recomputed":True,
          "report_code":"synthetic-report","fight_id":1,"actor_id":42,
          "raw_receipt_sha256":"c"*64,
          "actor_numeric_cast_count":1,
          "cast_events":[{"event_id":"cast-1","t_ms":1000,"spell_id":1201,
                          "source_kind":"WCL_NORMALIZED_RAW_EVENT"}],
          "target_count_at_cast":"UNKNOWN",
          "build_equivalent_to_SimC":"UNKNOWN",
          "independent_rank_or_holdout_proven":False,
          "source_gameplay_rule":"UNKNOWN"
        }
        transport["numeric_transport_sha256"]=sha(canonical(transport))
        joint={
          "schema":JOIN_SCHEMA,"policy_id":POLICY,
          "source_numeric_transport_sha256":
              transport["numeric_transport_sha256"],
          "actor_cast_rows":1,
          "complete_and_competing_READY_proven":0,
          "General_Rotation_priority_promoted":False,
          "dummy_training_error_proven":False,
          "per_numeric_cast":[{
            "numeric_raw_cast_event_id":"cast-1",
            "at_ms":1000,"spell_id":1201,
            "raw_aura_strict_pre":{
               "raw_aura_123_active":{
                  "status":"KNOWN","event_t_ms":900,
                  "raw_receipt_sha256":"c"*64,
                  "value":True,"source_event_id":"aura-1"}},
            "raw_numeric_power_owned_strict_pre":{
               "1":{"raw_power_type":1,
                    "strict_prior_at_ms":800,
                    "source_checkpoint_raw_receipt_sha256":"c"*64,
                    "game_resource_units_conversion":"UNKNOWN",
                    "game_resource_kind_semantics":"UNKNOWN",
                    "owner_proof":"ACTOR_OWNED_SOURCE",
                    "raw_amount":500,"raw_maximum":1000}},
            "complete_spell_READY":"UNKNOWN",
            "other_ready_actions":"UNKNOWN",
            "dummy_wrong_cast":"UNKNOWN",
            "source_APL_candidate_row":"UNKNOWN_UNTIL_POSTLOCK_ADAPTER"}]}
        joint["joined_numeric_pre_sha256"]=sha(canonical(joint))
        compiled=compile_binding(numeric,case,adapter,canonical(adapter))
        temporal={
          "schema":"ZrotWclActorAuraTemporalStrictPreV1",
          "policy_id":POLICY,
          "source_numeric_transport_sha256":
             transport["numeric_transport_sha256"],
          "source_raw_receipt_sha256":transport["raw_receipt_sha256"],
          "source_raw_page_sha256":"d"*64,
          "actual_cast_rows":1,
          "aura_remains_known":0,
          "full_GCD_cooldown_charge_READY_proven":0,
          "mandatory_general_rotation_rule_promoted":False,
          "raw_last_aura_event_age_never_promoted_to_remaining_duration":True,
          "per_numeric_cast":[{
            "numeric_raw_cast_event_id":"cast-1","at_ms":1000,
            "spell_id":1201,"aura_remaining_duration_for_any_spell":"UNKNOWN",
            "complete_action_READY":"UNKNOWN",
            "per_numeric_aura_spell":{"777":{
              "aura_remaining_duration_ms":"UNKNOWN",
              "last_transition_t_ms":700,
              "source_checkpoint_raw_receipt_sha256":"c"*64,
              "explicit_stack":3,
              "explicit_stack_status":"EXACT_RAW_STACK_OBSERVED",
              "source_event_ids":["synthetic-stack-event"]}}
          }]
        }
        transport["raw_source_page_sha256"]="d"*64
        transport["numeric_transport_sha256"]=sha(canonical({
          k:v for k,v in transport.items() if k!="numeric_transport_sha256"}))
        joint["source_numeric_transport_sha256"]=transport["numeric_transport_sha256"]
        joint["joined_numeric_pre_sha256"]=sha(canonical({
          k:v for k,v in joint.items() if k!="joined_numeric_pre_sha256"}))
        temporal["source_numeric_transport_sha256"]=transport["numeric_transport_sha256"]
        temporal["temporal_matrix_sha256"]=sha(canonical(temporal))
        mapping={
          "schema":MAP_SCHEMA,"policy_id":POLICY,
          "use_stage":"AFTER_FROZEN_NUMERIC_CANDIDATE_LOCK_ONLY",
          "frozen_numeric_lock_sha256":"b"*64,
          "source_profile_git_blob":model["source_git_blob"],
          "assert_current_game_mechanic_truth":False,
          "assert_WCL_actor_build_equivalence":False,
          "assert_WCL_target_count_match":False,
          "assert_full_READY_or_player_error":False,
          "operand_bindings":[{
             "source_symbol":"buff.ready.up","raw_kind":"WCL_RAW_AURA_BOOL",
             "raw_signal":"raw_aura_123_active",
             "confidence":"EXPLORATORY_UNVERIFIED_MECHANIC_AND_BUILD"},
             {"source_symbol":"energy",
              "raw_kind":"WCL_RAW_ACTOR_NUMERIC_POWER",
              "raw_power_type":1,
              "raw_units_per_source_unit_scenarios":[1,10],
              "confidence":"EXPLORATORY_UNVERIFIED_MECHANIC_AND_BUILD"},
             {"source_symbol":"buff.proc.stack",
              "raw_kind":"WCL_RAW_AURA_EXPLICIT_STACK",
              "raw_numeric_aura_spell_id":777,
              "confidence":"EXPLORATORY_UNVERIFIED_MECHANIC_AND_BUILD"}]
        }
        res=evaluate(numeric,transport,joint,case,compiled,mapping,
                     temporal=temporal)
        need(res["numeric_observed_casts"]==1 and
             res["required_source_IF_operand_occurrence_counts"]==
                {"buff.ready.up":1,"energy":3,
                 "variable.missing":1,"buff.proc.stack":1} and
             res["source_operand_scenario_usage_counts"]==
                {"buff.ready.up":2,"energy":6,"buff.proc.stack":2} and
             res["unmapped_source_IF_operand_occurrence_counts"]==
                {"variable.missing":1} and
             res["unobserved_source_IF_operand_scenario_counts"]==
                {"variable.missing":2} and
             res["raw_WCL_candidate_casts_with_source_token"]==1 and
             res["individual_source_IF_candidate_row_probes"]==4 and
             res["source_conditional_scenario_counts"][
                 "TRUE_UNDER_UNVERIFIED_SEMANTIC_LINK"]==1 and
             res["source_conditional_scenario_counts"][
                 "SCALE_SENSITIVE_OR_SCENARIO_UNKNOWN"]==3 and
             res["certified_source_IF_guard_true_count"]==0 and
             res["real_competing_spell_READY_proven"]==0 and
             res["dummy_wrong_cast_verdicts"]==0,
             "CROSS_CLASS_NUMERIC_SCENARIO_SOURCE_IF_REGRESSION")
        positive+=1
        missing=copy.deepcopy(temporal)
        missing["per_numeric_cast"][0]["per_numeric_aura_spell"]["777"][
            "explicit_stack"]=None
        missing["per_numeric_cast"][0]["per_numeric_aura_spell"]["777"][
            "explicit_stack_status"]="UNKNOWN_NOT_EXPLICITLY_OBSERVED"
        missing["temporal_matrix_sha256"]=sha(canonical({
            k:v for k,v in missing.items() if k!="temporal_matrix_sha256"}))
        unknown=evaluate(numeric,transport,joint,case,compiled,mapping,
                         temporal=missing)
        need(unknown["source_conditional_scenario_counts"][
              "UNKNOWN_UNDER_UNVERIFIED_SEMANTIC_LINK"]>=1 and
             unknown["certified_source_IF_guard_true_count"]==0,
             "UNKNOWN_MISSING_RAW_STACK_WAS_FILLED_FROM_APPLICATION")
        bad=copy.deepcopy(temporal)
        bad["per_numeric_cast"][0]["per_numeric_aura_spell"]["777"][
            "last_transition_t_ms"]=1000
        bad["temporal_matrix_sha256"]=sha(canonical({
            k:v for k,v in bad.items() if k!="temporal_matrix_sha256"}))
        must_fail(lambda:evaluate(numeric,transport,joint,case,compiled,
                                  mapping,temporal=bad))
        must_fail(lambda:evaluate(numeric,transport,joint,case,compiled,mapping))
        bad=copy.deepcopy(mapping)
        bad["operand_bindings"][-1]["source_symbol"]="buff.proc.remains"
        must_fail(lambda:evaluate(numeric,transport,joint,case,compiled,
                                  bad,temporal=temporal))
        bad=copy.deepcopy(joint)
        bad["per_numeric_cast"][0]["raw_numeric_power_owned_strict_pre"][
            "1"]["strict_prior_at_ms"]=1000
        bad["joined_numeric_pre_sha256"]=sha(canonical({
           k:v for k,v in bad.items() if k!="joined_numeric_pre_sha256"}))
        must_fail(lambda:evaluate(numeric,transport,bad,case,compiled,mapping))
        bad=copy.deepcopy(joint)
        bad["per_numeric_cast"][0]["raw_aura_strict_pre"][
             "raw_aura_123_active"]["event_t_ms"]=1000
        bad["joined_numeric_pre_sha256"]=sha(canonical({
           k:v for k,v in bad.items() if k!="joined_numeric_pre_sha256"}))
        must_fail(lambda:evaluate(numeric,transport,bad,case,compiled,mapping))
        bad=copy.deepcopy(mapping)
        bad["assert_current_game_mechanic_truth"]=True
        must_fail(lambda:evaluate(numeric,transport,joint,case,compiled,bad))
        bad=copy.deepcopy(mapping)
        bad["operand_bindings"][1]["raw_units_per_source_unit_scenarios"]=[0]
        must_fail(lambda:evaluate(numeric,transport,joint,case,compiled,bad))
        bad=copy.deepcopy(numeric);bad["source_APL_injected_in_numeric_phase"]=True
        must_fail(lambda:evaluate(bad,transport,joint,case,compiled,mapping))
        bad=copy.deepcopy(compiled);bad["allow_whole_spell_READY_from_mapping"]=True
        must_fail(lambda:evaluate(numeric,transport,joint,case,bad,mapping))
        bad=copy.deepcopy(joint)
        bad["per_numeric_cast"][0]["spell_id"]=999
        bad["joined_numeric_pre_sha256"]=sha(canonical({
           k:v for k,v in bad.items() if k!="joined_numeric_pre_sha256"}))
        must_fail(lambda:evaluate(numeric,transport,bad,case,compiled,mapping))
        bad=copy.deepcopy(mapping);bad["operand_bindings"][0]["confidence"]="CERTIFIED"
        must_fail(lambda:evaluate(numeric,transport,joint,case,compiled,bad))
    return {
       "schema":SCHEMA,"status":"PASS_TWO_CLASS_TYPED_SCENARIO",
       "synthetic_class_count":2,"positive":positive,"negative":negative,
       "same_timestamp_state_leak_rejected":True,
       "uncertain_power_divisor_sensitivity_visible":True,
       "multiple_APL_row_conditions_preserved":True,
       "missing_unmapped_source_operand_remains_UNKNOWN":True,
       "explicit_raw_aura_stack_source_if_exploratory_only":True,
       "unknown_stack_and_same_time_temporal_controls":True,
       "source_semantics_current_game_certified":False,
       "player_competitor_READY_proven":0,
       "player_dummy_errors_proven":0,
       "live_WCL_API_calls":0
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for arg in ("numeric-phase","raw-transport","joined-pre","source-case",
                "compiled-binding","operand-map","out"):
        ap.add_argument("--"+arg,type=Path)
    ap.add_argument("--temporal-pre",type=Path)
    opts=ap.parse_args()
    required=("numeric_phase","raw_transport","joined_pre","source_case",
              "compiled_binding","operand_map","out")
    if all(getattr(opts,k) is None for k in required) and opts.temporal_pre is None:
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(getattr(opts,k) is not None for k in required),
         "ALL_PROVENANCE_PINNED_SEPARATE_INPUTS_REQUIRED")
    numeric,_=load_json(opts.numeric_phase)
    transport,_=load_json(opts.raw_transport)
    joint,_=load_json(opts.joined_pre)
    source,_=load_json(opts.source_case)
    compiled,_=load_json(opts.compiled_binding)
    mapping,_=load_json(opts.operand_map)
    temporal=load_json(opts.temporal_pre)[0] if opts.temporal_pre else None
    out=evaluate(numeric,transport,joint,source,compiled,mapping,
                 temporal=temporal)
    need(not opts.out.exists(),"NO_OVERWRITE_EVIDENCE_RESULT")
    opts.out.parent.mkdir(parents=True,exist_ok=True)
    opts.out.write_bytes(canonical(out))
    print("GENERIC_WCL_TYPED_POSTLOCK_IF_SCENARIO_SHA256="+
          sha(opts.out.read_bytes()))
    print("GENERIC_WCL_TYPED_POSTLOCK_IF_SCENARIO_COUNTS="+json.dumps(
          out["source_conditional_scenario_counts"],sort_keys=True))
    print("CERTIFIED_GENERAL_ROTATION_PRIORITY_PROVEN=0")

if __name__=="__main__":
    main()
