#!/usr/bin/env python3
"""Source-neutral pinned SimC profile/talent IF replay on five same-root gaps.

A static profile fact is NOT an independently observed Native action_ready,
nor a WoW-current talent, physical READY, WCL result or user error.
Unknown DoT, tier bonuses and hero starter grants remain UNKNOWN.
No-argument execution performs safe synthetic tests (PyCharm friendly).
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile, evaluate_ast, truth, git_blob
from general_rotation_original_talent_hash_dbc_v1 import (
    SCHEMA as TALENT_SCHEMA, POLICY, TalentDecodeError
)

SCHEMA = "ZrotOriginalProfileSameRootStaticIfGuardV1"
CFG_SCHEMA = "ZrotOriginalProfileStaticIfGuardAdapterV1"
GAP_SCHEMA = "ZrotGenericSameRootPriorityGapV1"

class StaticGuardError(ValueError):
    pass

def need(ok, message):
    if not ok:
        raise StaticGuardError(message)

def canonical(data):
    return (json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")

def static_talent_fact(case):
    """Only an encoded/purchased rank is a known TRUE; free-grant is unresolved."""
    need(case["current_Retail_user_talent_selected"] == "UNKNOWN" and
         case["current_Retail_physical_ability_READY"] == "UNKNOWN",
         "GAMEPLAY_READY_OR_LIVE_TALENT_OVERCLAIM")
    rank = case["source_profile_allocated_rank"]
    grant = case["source_dbc_free_grant_to_spec"]
    status = case["source_profile_status"]
    if status == "PROFILE_SELECTED_RANK":
        need(isinstance(rank, int) and rank > 0 and
             case["source_profile_hash_node_selected"] is True,
             "SOURCE_TALENT_SELECTED_RANK_CONTRADICTION")
        return 1.0, "SOURCE_PROFILE_ENCODED_SELECTED_RANK"
    if status == "PROFILE_NOT_SELECTED_NOT_GRANTED":
        need(rank == 0 and not grant and
             case["source_profile_hash_node_selected"] is False,
             "SOURCE_TALENT_UNSELECTED_CONTRADICTION")
        return 0.0, "SOURCE_PROFILE_NOT_SELECTED_AND_NOT_GRANTED"
    need(status == "PROFILE_UNSELECTED_BUT_FREE_GRANTED" and
         rank == 0 and grant is True,
         "UNKNOWN_TALENT_STATUS_OR_INCONSISTENT_GRANT")
    # The pinned decoder does not independently witness actual hero-subtree
    # activation and runtime player_talent_t. A DBC starter flag alone
    # must never become an observed true ability/condition.
    return None, "FREE_GRANT_WITHOUT_INDEPENDENT_RUNTIME_HERO_SUBTREE_PROOF"

def replay(profile_bytes, talent, prior_gap, config, prior_raw):
    need(config.get("schema") == CFG_SCHEMA and
         config.get("policy_id") == POLICY and
         config.get("source_revision") == "b522cded8c26b97dac03fdf56e57a03ec7e8faa6" and
         prior_gap.get("schema") == GAP_SCHEMA and
         prior_gap.get("policy_id") == POLICY and
         talent.get("schema") == TALENT_SCHEMA and
         talent.get("policy_id") == POLICY,
         "SOURCE_PROFILE_GAP_POLICY_OR_SCHEMA_DRIFT")
    need(sha256(prior_raw).hexdigest() == config["prior_gap_sha256"],
         "PREVIOUS_INDEPENDENT_GAP_BYTES_CHANGED")
    need(prior_gap.get("source_revision") == talent.get("source_revision") ==
         config["source_revision"] and
         prior_gap["spec_key"] == talent["spec_key"] == config["spec_key"] and
         prior_gap["source_profile_git_blob"] ==
         talent["source_profile_git_blob"] == config["source_profile_git_blob"] ==
         git_blob(profile_bytes),
         "GAP_PROFILE_SOURCE_REVISION_IDENTITY_DRIFT")
    need(talent["original_source_parse_and_DBC_proven"] is True and
         talent["native_action_talent_value_read_independently"] == "NOT_RUN" and
         talent["General_Rotation_priority_promoted"] == 0 and
         talent["WCL_independent_blind"] == "NOT_RUN" and
         prior_gap["new_general_rotation_priority_promotions"] == 0 and
         prior_gap["WCL_independent_blind_candidate_lock"] == "NOT_RUN_FOR_THESE_ROOTS",
         "UNSUPPORTED_LIVE_OR_WCL_MECHANIC_CLAIM")
    need(len(prior_gap["cases"]) == 2 and
         len(config["talent_symbols"]) >= 1 and
         len(set(config["talent_symbols"])) == len(config["talent_symbols"]),
         "UNBOUNDED_OR_DUPLICATE_STATIC_TALENT_INPUTS")
    talent_map = {}
    for symbol, identity in config["talent_symbols"].items():
        need(symbol.startswith("talent.") and symbol.endswith(".enabled") and
             len(symbol) < 128 and isinstance(identity, dict),
             "NOT_A_TALENT_APL_SOURCE_SYMBOL")
        matches = [c for c in talent["cases"] if
                   c["trait_name"] == identity["trait_name"] and
                   c["trait_node"] == identity["trait_node"] and
                   c["trait_entry"] == identity["trait_entry"] and
                   c["trait_spell"] == identity["trait_spell"]]
        need(len(matches) == 1, "SOURCE_PROFILE_TALENT_IDENTITY_NOT_EXACT")
        value, status = static_talent_fact(matches[0])
        talent_map[symbol] = {"value": value, "provenance": status,
                              "rank": matches[0]["source_profile_allocated_rank"]}
    source = parse_profile(profile_bytes, require_source=True,
                           expected_git_blob=config["source_profile_git_blob"])
    result=[]
    total_focus=0
    for case in prior_gap["cases"]:
        selected=case["selected_root"]
        need(selected["source_action"] and isinstance(selected["t_ms"], int) and
             0 <= selected["t_ms"] < 3600000 and
             case["full_CALL_RUN_return_stack"] == "UNKNOWN" and
             case["user_general_rotation_priority_promoted"] == 0,
             "GAP_ROOT_OR_PRIORITY_PROVENANCE_DRIFT")
        li=selected["source_list"]
        rows=source["action_lists"].get(li)
        need(rows and 0 < selected["source_rank"] <= len(rows) and
             rows[selected["source_rank"]-1]["action"] == selected["source_action"],
             "ORIGINAL_SELECTED_APL_ROOT_MISMATCH")
        cases=[]
        for focus in case["focused_missing_PRE_and_READY"]:
            rank=focus["rank"]
            need(type(rank) is int and 0 < rank < selected["source_rank"] and
                 0 <= rank-1 < len(case["higher_source_rows"]),
                 "FOCUS_OUTSIDE_EXACT_UPSTREAM_APL")
            evidence=case["higher_source_rows"][rank-1]
            row=rows[rank-1]
            need(row["action"] == focus["action"] == evidence["source_action"] and
                 row["source_sha256"] == evidence["source_row_sha256"] and
                 evidence["evidence_class"] == "SOURCE_IF_PRE_UNKNOWN_AND_MECHANIC_READY_UNKNOWN" and
                 focus["readiness_independent_observation"] == "UNKNOWN" and
                 row["behavior"] == "ACTION",
                 "SOURCE_FOCUS_NOT_EXACT_OR_READY_OVERCLAIM")
            expr = row["expression_fields"].get("if")
            need(expr is not None, "NO_IF_ATTRIBUTE_FOR_SOURCE_PRE_FOCUS")
            # 'time' is solely the native selected-root simulation clock.
            # It is NOT an inferred post-action transition or gameplay state.
            facts={"time": selected["t_ms"]/1000.0}
            for symbol in expr["symbols"]:
                if symbol in talent_map and talent_map[symbol]["value"] is not None:
                    facts[symbol] = talent_map[symbol]["value"]
            result_value=evaluate_ast(expr["ast"], facts)
            b=truth(result_value)
            verdict="SOURCE_PROFILE_STATIC_FALSE" if b is False else (
                "SOURCE_PROFILE_STATIC_TRUE_PHYSICAL_READY_UNKNOWN"
                if b is True else "SOURCE_PROFILE_IF_STILL_UNKNOWN")
            # Preserve the recorded independent Native PRE UNKNOWN; re-evaluation
            # is an additional static source-profile hypothesis, not a
            # direct observation of the original IF or any physical readiness.
            unresolved=sorted(set(expr["symbols"])-set(facts))
            cases.append({"rank":rank,"action":row["action"],
                 "source_if":expr["source"],
                 "source_if_ast_symbols":expr["symbols"],
                 "static_facts_used":{k: facts[k] for k in sorted(facts)
                                      if k in expr["symbols"]},
                 "unresolved_facts":unresolved,
                 "talent_facts":{k:talent_map[k] for k in expr["symbols"]
                                 if k in talent_map},
                 "profile_static_IF":verdict,
                 "original_independent_same_call_PRE":"UNKNOWN",
                 "independent_physical_READY":"UNKNOWN",
                 "current_Retail_gameplay_priority":"UNKNOWN"})
            total_focus+=1
        result.append({"case_id":case["case_id"],
                       "selected_source_list":li,
                       "selected_source_rank":selected["source_rank"],
                       "selected_action":selected["source_action"],
                       "native_same_root_t_ms":selected["t_ms"],
                       "same_root_foreground_CALL":case["verified_foreground_source_CALL_entry"],
                       "complete_CALL_RUN_return_stack":"UNKNOWN",
                       "focused_source_static_projection":cases})
    need(total_focus == config["expected_focus_rows"],
         "FOCUSED_SOURCE_DECISIONS_CHANGED_UNEXPECTEDLY")
    return {"schema":SCHEMA,"policy_id":POLICY,
            "source_revision":config["source_revision"],
            "spec_key":config["spec_key"],
            "source_profile_git_blob":config["source_profile_git_blob"],
            "previous_gap_sha256":config["prior_gap_sha256"],
            "talent_source_cases":talent_map,
            "cases":result,
            "product_general_rotation_rules_promoted":0,
            "current_Retail_mechanics":"UNKNOWN",
            "opener_end":"UNKNOWN",
            "independent_physical_ready":"UNKNOWN",
            "WCL_blind_candidate_lock":"NOT_RUN_FOR_THIS_SOURCE_PROJECTION",
            "actual_target_dummy_mistake":"UNKNOWN",
            "MAIN_promoted":False}

def selftest():
    proto={"current_Retail_user_talent_selected":"UNKNOWN",
           "current_Retail_physical_ability_READY":"UNKNOWN",
           "source_profile_allocated_rank":0,
           "source_dbc_free_grant_to_spec":False,
           "source_profile_hash_node_selected":False,
           "source_profile_status":"PROFILE_NOT_SELECTED_NOT_GRANTED"}
    v,p=static_talent_fact(proto)
    need(v==0 and p=="SOURCE_PROFILE_NOT_SELECTED_AND_NOT_GRANTED",
         "PROFILE_UNSELECTED_EVALUATION_WRONG")
    s={**proto,"source_profile_status":"PROFILE_SELECTED_RANK",
       "source_profile_allocated_rank":1,
       "source_profile_hash_node_selected":True}
    need(static_talent_fact(s)[0]==1,"PROFILE_SELECTED_EVALUATION_WRONG")
    grant={**proto,"source_profile_status":"PROFILE_UNSELECTED_BUT_FREE_GRANTED",
           "source_dbc_free_grant_to_spec":True}
    need(static_talent_fact(grant)[0] is None,
         "HERO_FREE_GRANT_MUST_NOT_BECOME_LIVE_READY")
    from simc_apl_semantic_ir_v2 import Expression
    need(truth(evaluate_ast(Expression("talent.alpha.enabled&dot.beta.remains=0").parse(),
              {"talent.alpha.enabled":0.0})) is False,
         "STATIC_FALSE_WITH_UNKNOWN_DOT_MUST_SHORT_CIRCUIT")
    need(evaluate_ast(Expression("talent.alpha.enabled|set_bonus.sample").parse(),
              {"talent.alpha.enabled":0.0}) is None,
         "UNKNOWN_TIER_SET_MUST_REMAIN_UNKNOWN")
    n=0
    for broken in ({**proto,"source_profile_status":"PROFILE_SELECTED_RANK"},
                   {**grant,"current_Retail_physical_ability_READY":"TRUE"},
                   {**proto,"source_profile_status":"PROFILE_UNSELECTED_BUT_FREE_GRANTED"},
                   {**s,"source_profile_hash_node_selected":False}):
        try:static_talent_fact(broken)
        except StaticGuardError:n+=1
        else:raise AssertionError("UNVERIFIED_SOURCE_TALENT_WAS_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls":n,
            "free_grants_counted_as_READY":0,
            "new_original_Native_builds":0,"WCL_API_calls":0,
            "priority_promotions":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-profile",type=Path)
    p.add_argument("--talent-result",type=Path)
    p.add_argument("--prior-gap",type=Path)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(v is not None for v in vars(a).values()),
         "ALL_EXACT_PINNED_SOURCE_INPUTS_REQUIRED")
    prev=a.prior_gap.read_bytes()
    result=replay(a.source_profile.read_bytes(),
           json.loads(a.talent_result.read_bytes()),
           json.loads(prev),json.loads(a.adapter.read_bytes()),prev)
    data=canonical(result)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(data)
    print("ORIGINAL_PROFILE_STATIC_IF_GUARDS_SHA256="+sha256(data).hexdigest())
    print("SOURCE_ONLY_GUARD_CASES="+json.dumps(
        [{"case":x["case_id"],
          "guards":[{"rank":g["rank"],"result":g["profile_static_IF"],
                     "unknown":g["unresolved_facts"]}
                    for g in x["focused_source_static_projection"]]}
         for x in result["cases"]],sort_keys=True))

if __name__=="__main__":
    main()
