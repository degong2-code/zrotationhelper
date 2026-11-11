#!/usr/bin/env python3
"""Generic postlock WCL raw-aura -> pinned SimC source-IF sensitivity diagnostic.

This consumes a previously locked WCL numeric cohort, the existing verified
raw actor Aura Temporal Strict PRE matrix, original event-grain proof and an
external spec adapter. NEVER inject SimC symbols into blind discovery.
A source IF can be FALSE/TRUE as a hypothetical evaluation even if the
observed WCL cast was a proc, trigger, background action, different APL list,
or different build. It cannot prove READY, priority, or a dummy user mistake.

No-args = PyCharm-safe synthetic tests, no WCL API and no SimC compilation.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path
import re
import zipfile

from wcl_raw_action_event_grain_audit_v1 import audit,canon,require,sha
from simc_apl_semantic_ir_v2 import parse_profile,git_blob,evaluate_ast,truth
from general_rotation_original_talent_hash_dbc_v1 import parse_dbc
from wcl_disjoint_holdout_v1 import validate_contract,validate_frozen_lock

SCHEMA="ZrotGenericPostlockWclAuraSourceIfSensitivityV1"
ADAPTER_SCHEMA="ZrotPostlockSourceAuraPredicateAdapterV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")
SYM=re.compile(r"^buff\.[a-z][a-z0-9_]*\.(?:stack|up)$")
ACT=re.compile(r"^[a-z][a-z0-9_]*$")

def validated_adapter(a,profile,cpp,dbc,lock_raw):
    require(a.get("schema")==ADAPTER_SCHEMA and a.get("policy_id")==POLICY and
            HEX40.fullmatch(a.get("source_profile_git_blob","")) and
            HEX40.fullmatch(a.get("source_class_cpp_git_blob","")) and
            HEX64.fullmatch(a.get("protected_prior_numeric_lock_sha256","")) and
            sha(lock_raw)==a["protected_prior_numeric_lock_sha256"] and
            git_blob(profile)==a["source_profile_git_blob"] and
            git_blob(cpp)==a["source_class_cpp_git_blob"] and
            a.get("allow_source_apl_prior_to_lock") is False and
            a.get("allow_wcl_holdout_relocking") is False and
            a.get("allow_unknown_stack_as_zero") is False and
            a.get("allow_t_same_timestamp_as_pre") is False and
            a.get("allow_promote_gameplay_rule") is False and
            a.get("manual_input_proven") is False and
            a.get("ready_and_competing_spells_proven") is False,
            "UNPINNED_POSTLOCK_SOURCE_SEMANTIC_AUTHORITY")
    symbols=a.get("buff_symbols")
    mappings=a.get("observed_numeric_source_action_candidates")
    excluded=a.get("excluded_numeric_action_families")
    need_ids=set()
    require(type(symbols) is dict and symbols and type(mappings) is dict and mappings
            and type(excluded) is dict and not (set(excluded)&set(mappings)),
            "INVALID_BUFF_OR_ACTION_MAPPING")
    for k,id_ in symbols.items():
        require(SYM.fullmatch(k) is not None and type(id_) is int and id_>0,
                "INVALID_BUFF_SYMBOL_ID")
        need_ids.add(id_)
    for k,v in mappings.items():
        require(k.isdigit() and int(k)>0 and ACT.fullmatch(v) is not None,
                "INVALID_POSTLOCK_ACTION_BINDING")
        need_ids.add(int(k))
    for k in excluded:
        require(k.isdigit() and int(k)>0,"INVALID_EXCLUDED_NUMERIC_ID")
    source=cpp.decode("utf-8")
    checks=a.get("source_spell_concordance_checks")
    require(type(checks) is list and checks,"POSTLOCK_SOURCE_CPP_PROOFS_MISSING")
    for row in checks:
        require(type(row.get("numeric_id")) is int and
                row["numeric_id"] in need_ids|{int(k) for k in excluded} and
                type(row.get("source_cpp_exact")) is str and
                row["source_cpp_exact"] in source,
                "PINNED_CLASS_CPP_SOURCE_SPELL_MAPPING_MISSING")
    traits=parse_dbc(dbc.decode("utf-8"))
    for row in a.get("source_talent_DBC_checks",[]):
        require(any(t["spell"]==row["numeric_id"] and
                    t["node"]==row["trait_node"] and
                    t["entry"]==row["trait_entry"]
                    for t in traits),"PINNED_TALENT_DBC_SOURCE_SPELL_MAPPING_MISSING")
    ir=parse_profile(profile,require_source=True,
                     expected_git_blob=a["source_profile_git_blob"])
    found={row["action"] for rows in ir["action_lists"].values() for row in rows}
    require(set(mappings.values())<=found and
            all(x in ir["source_symbol_dependencies"] for x in symbols),
            "SOURCE_APL_ACTION_OR_BUFF_SYMBOL_MISSING")
    return ir

def load_aura(raw,transport,role):
    aura=json.loads(raw)
    expected=aura.get("temporal_matrix_sha256")
    copy=dict(aura);copy.pop("temporal_matrix_sha256",None)
    require(expected==sha(canon(copy)) and
            aura["schema"]=="ZrotWclActorAuraTemporalStrictPreV1" and
            aura["policy_id"]==POLICY and
            aura["source_numeric_transport_sha256"]==transport["numeric_transport_sha256"] and
            aura["source_raw_receipt_sha256"]==transport["raw_receipt_sha256"] and
            aura["source_raw_page_sha256"]==transport["raw_source_page_sha256"] and
            aura["actual_cast_rows"]==transport["actor_numeric_cast_count"],
            "RAW_AURA_TEMPORAL_MATRIX_IDENTITY_OR_DIGEST_MISMATCH")
    return aura

def facts_at(cast,aura_row,symbols):
    t=cast["t_ms"]
    available={}
    details={}
    for symbol,id_ in symbols.items():
        key=str(id_)
        raw=aura_row["per_numeric_aura_spell"].get(key)
        field="stack" if symbol.endswith(".stack") else "up"
        if raw is None:
            details[symbol]={"value":None,"status":"UNKNOWN_NO_EARLIER_RAW_AURA_TRANSITION"}
            continue
        ts=raw["last_transition_t_ms"]
        require(type(ts) is int and ts<t and
                raw["source_checkpoint_raw_receipt_sha256"] is not None,
                "SOURCE_AURA_FACT_SAME_TIMESTAMP_OR_FUTURE")
        val=raw.get("explicit_stack") if field=="stack" else (
            1 if raw["active"] is True else 0 if raw["active"] is False else None)
        # A conflicting/ambiguous same-time batch never becomes exact.
        if field=="stack" and raw.get("explicit_stack_status")!="EXACT_RAW_STACK_OBSERVED":
            val=None
        if raw["active"] is None:val=None
        if val is None:
            details[symbol]={"value":None,"status":"UNKNOWN_RAW_STACK_OR_AMBIGUOUS_BATCH",
                             "source_transition_ms":ts,"source_event_ids":raw["source_event_ids"]}
            continue
        require(type(val) is int and val>=0,"INVALID_SOURCE_AURA_NUMERIC_VALUE")
        available[symbol]={"value":val,"timestamp":ts,
                           "provenance":"STRICT_PRE_OBSERVATION"}
        details[symbol]={"value":val,"status":"OBSERVED_EARLIER_RAW_AURA",
                         "source_transition_ms":ts,
                         "source_event_ids":raw["source_event_ids"]}
    return available,details

def _guard_outcome(expr,facts,t):
    if expr is None:return "NO_EXPLICIT_SOURCE_IF"
    v=truth(evaluate_ast(expr["ast"],facts,action_timestamp=t,strict_pre=True))
    return "SOURCE_IF_TRUE" if v is True else "SOURCE_IF_FALSE" if v is False else "SOURCE_IF_UNKNOWN"

def render_case(z,role,aura,ir,adapter,lock):
    original=audit(z,role)
    transport=json.loads(z.read(f"results/{role}-numeric.json"))
    load_aura(canon(aura),transport,role)
    old=transport["cast_events"]
    rows=aura["per_numeric_cast"]
    require(len(rows)==len(old) and
            len(original["event_type_sidecar"])==len(old) and
            original["numeric_transport_sha256"]==transport["numeric_transport_sha256"],
            "ORIGINAL_ACTION_EVENT_GRAIN_UNBOUND")
    sidecar={r["event_id"]:r for r in original["event_type_sidecar"]}
    mapping=adapter["observed_numeric_source_action_candidates"]
    focus_source_rows={
        a:[row for list_name in ("single_sb","single_totemic","aoe")
           for row in ir["action_lists"].get(list_name,[]) if row["action"]==a]
        for a in mapping.values()
    }
    observations=[];stats=Counter();state_status=Counter();by_numeric=defaultdict(Counter)
    original_locked={int(x["action_spell_id"]) for x in lock["candidates"]}
    require(set(map(int,mapping))<=original_locked and
            set(map(int,adapter["excluded_numeric_action_families"]))<=original_locked,
            "POSTLOCK_INPUT_ACTION_NOT_IN_FROZEN_NUMERIC_LOCK")
    for row,raw in zip(rows,old):
        eid=raw["event_id"]; e=sidecar.get(eid)
        require(e is not None and row["numeric_raw_cast_event_id"]==eid and
                row["at_ms"]==raw["t_ms"]==e["t_ms"] and
                row["spell_id"]==raw["spell_id"]==e["spell_id"],
                "POSTLOCK_RAW_AURA_EVENT_OR_CAST_TIME_DRIFT")
        numeric_id=raw["spell_id"]
        if str(numeric_id) not in mapping:
            continue
        t=raw["t_ms"]
        facts,details=facts_at(raw,row,adapter["buff_symbols"])
        source_action=mapping[str(numeric_id)]
        ifs=[]
        for s in focus_source_rows[source_action]:
            expr=s["expression_fields"].get("if")
            verdict=_guard_outcome(expr,facts,t)
            stats[(e["event_type"],verdict)]+=1
            ifs.append({"list":s["list"],"rank":s["index"]+1,
                        "source_sha256":s["source_sha256"],
                        "source_if":expr["source"] if expr else None,
                        "unobserved_symbols":sorted(set(expr["symbols"])-set(facts)) if expr else [],
                        "source_IF_at_WCL_numeric_PRE":verdict,
                        "source_gameplay_READY":"UNKNOWN"})
        mw=details.get("buff.maelstrom_weapon.stack",{"value":None,"status":"UNKNOWN"})
        stamp={"event_id":eid,"event_type":e["event_type"],"t_ms":t,
               "spell_id":numeric_id,"source_action_candidate":source_action,
               "numeric_target_id":e["target_id"],
               "strict_pre_source_observation_facts":details,
               "maelstrom_weapon_exact_raw_stack":mw["value"],
               "maelstrom_predicate_candidates":{
                   "stack_at_least_5":"UNKNOWN" if mw["value"] is None else bool(mw["value"]>=5),
                   "stack_at_least_8":"UNKNOWN" if mw["value"] is None else bool(mw["value"]>=8),
                   "stack_at_least_10":"UNKNOWN" if mw["value"] is None else bool(mw["value"]>=10),
                   "stack_equal_10":"UNKNOWN" if mw["value"] is None else bool(mw["value"]==10)},
               "source_APL_row_hypotheses":ifs,
               "actual_simc_action_list":"UNKNOWN_TARGET_COUNT_AND_BUILD",
               "manual_player_input":"UNKNOWN",
               "same_time_other_casts_are_not_ordered":True,
               "current_WoW_apl_mechanic_parity":"UNKNOWN",
               "competing_action_READY":"UNKNOWN",
               "source_IF_unequal_to_gameplay_priority":True,
               "dummy_wrong_cast":"UNKNOWN"}
        observations.append(stamp)
        by_numeric[str(numeric_id)]["TOTAL_"+e["event_type"]]+=1
        if mw["value"] is not None:by_numeric[str(numeric_id)]["EXACT_STACK_PRE_"+e["event_type"]]+=1
        else:by_numeric[str(numeric_id)]["UNKNOWN_STACK_PRE_"+e["event_type"]]+=1
        for label,val in stamp["maelstrom_predicate_candidates"].items():
            state_status[(e["event_type"],label,str(val))]+=1
    require(bool(observations),"LOCKED_ACTIONS_NOT_OBSERVED")
    return {"role":role.upper(),"report_code":transport["report_code"],
            "fight_id":transport["fight_id"],"actor_id":transport["actor_id"],
            "source_raw_numeric_transport_sha256":transport["numeric_transport_sha256"],
            "source_aura_temporal_matrix_sha256":aura["temporal_matrix_sha256"],
            "postlock_cast_evidence_count":len(observations),
            "observed_source_IF_verdict_counts":{"|".join(k):v for k,v in sorted(stats.items())},
            "strict_PRE_stack_predicate_counts":{"|".join(k):v for k,v in sorted(state_status.items())},
            "per_numeric_action_coverage":{k:dict(v) for k,v in sorted(by_numeric.items())},
            "per_observed_action_event":observations,
            "wcl_actor_owned_class_resource_is_maelstrom_weapon_stack":False,
            "cross_report_same_player_identity":"UNKNOWN",
            "full_build_equivalence_to_source":"UNKNOWN_OR_MISMATCH",
            "complete_READY_proven":0,"new_general_rotation_rule_promoted":0}

def selftest():
    cast={"t_ms":110}
    raw={"per_numeric_aura_spell":{"77":{"last_transition_t_ms":100,
          "explicit_stack":8,"explicit_stack_status":"EXACT_RAW_STACK_OBSERVED",
          "active":True,"source_checkpoint_raw_receipt_sha256":"a"*64,
          "source_event_ids":["x"]}}}
    f,d=facts_at(cast,raw,{"buff.foo.stack":77,"buff.foo.up":77,"buff.bar.up":88})
    from simc_apl_semantic_ir_v2 import Expression
    expr=Expression("buff.foo.stack>=8&buff.foo.up").parse()
    require(truth(evaluate_ast(expr,f,action_timestamp=110,strict_pre=True)) is True and
            d["buff.bar.up"]["value"] is None,"SYNTHETIC_SOURCE_IF_STRICT_PRE_NOT_TRUE")
    require(truth(evaluate_ast(expr,f,action_timestamp=100,strict_pre=True)) is None,
            "SAME_TIMESTAMP_ACCEPTED")
    x=json.loads(json.dumps(raw));x["per_numeric_aura_spell"]["77"]["explicit_stack_status"]="UNKNOWN"
    facts,det=facts_at(cast,x,{"buff.foo.stack":77})
    require("buff.foo.stack" not in facts and det["buff.foo.stack"]["value"] is None,
            "UNKNOWN_STACK_COERCED")
    return {"status":"PASS_SYNTHETIC_STATIC","checks":3,
            "strict_PRE_same_timestamp_rejected":True,
            "unknown_stack_not_zero":True,"manual_input":"UNKNOWN",
            "new_WCL_API_calls":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("discovery-zip","holdout-zip","discovery-aura","holdout-aura",
              "profile","cpp","dbc","adapter","lock","contract","metrics","out"):
        p.add_argument("--"+k,type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    require(all(vars(a).values()),"ALL_ORIGINAL_POSTLOCK_SOURCE_INPUTS_REQUIRED")
    adapter=json.loads(a.adapter.read_bytes())
    lock_raw=a.lock.read_bytes()
    contract_raw=a.contract.read_bytes()
    metrics_raw=a.metrics.read_bytes()
    contract=validate_contract(json.loads(contract_raw))
    lock=validate_frozen_lock(lock_raw,contract)
    metrics=json.loads(metrics_raw)
    require(metrics["unchanged_discovery_lock_sha256"]==sha(lock_raw) and
            metrics["predeclared_contract_sha256"]==sha(contract_raw) and
            metrics["new_discovery_candidates_added"]==0 and
            metrics["candidate_set_frozen_before_holdout"] is True,
            "HOLDOUT_RELOCK_OR_METRIC_DRIFT")
    ir=validated_adapter(adapter,a.profile.read_bytes(),a.cpp.read_bytes(),
                         a.dbc.read_bytes(),lock_raw)
    results=[]
    for role,path,source in (("discovery",a.discovery_zip,a.discovery_aura),
                             ("holdout",a.holdout_zip,a.holdout_aura)):
        with zipfile.ZipFile(path) as z:
            aura=json.loads(source.read_bytes())
            results.append(render_case(z,role,aura,ir,adapter,lock))
    require(results[0]["report_code"]!=results[1]["report_code"],"SAME_REPORT_REUSE")
    output={"schema":SCHEMA,"policy_id":POLICY,"source_revision":adapter["source_revision"],
            "protected_blind_lock_sha256":sha(lock_raw),
            "source_profile_git_blob":adapter["source_profile_git_blob"],
            "source_class_cpp_git_blob":adapter["source_class_cpp_git_blob"],
            "postlock_only":True,"source_apl_scenario_lists":["single_sb","single_totemic","aoe"],
            "actual_target_count_for_list_assignment":"UNKNOWN",
            "source_IF_false_is_not_player_error":True,
            "source_IF_true_is_not_action_READY":True,
            "observed_action_automatic_proc_manual":"UNKNOWN",
            "cases":results,"new_general_rotation_rules_promoted":0,
            "new_WCL_API_calls":0,"new_SimC_native_builds":0,
            "MAIN_promoted":False}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canon(output))
    print("WCL_POSTLOCK_AURA_SOURCE_IF_SHA256="+sha(a.out.read_bytes()))
    for case in results:
        print("WCL_POSTLOCK_SOURCE_IF_SUMMARY="+json.dumps({
            "role":case["role"],"postlock_action_events":case["postlock_cast_evidence_count"],
            "per_numeric":case["per_numeric_action_coverage"],
            "IF_counts":case["observed_source_IF_verdict_counts"]},sort_keys=True))

if __name__=="__main__":
    main()
