#!/usr/bin/env python3
"""Spec-neutral SimC source APL target-count / build-branch projection.

Consumes the EXISTING SHA-pinned semantic APL and ordered IF/ELSE program.
Only active_enemies, declared synthetic talent assumptions and source-derived
precombat variables are numerically evaluated. Everything else is UNKNOWN.
CALL/RUN never become an imagined spell selection; non-IF attributes remain.

This is a source hypothesis for 1/2/3+ targets, not Native READY parity,
a verified opener termination, WCL validation or target-dummy advice.
No CLI args: offline synthetic checks; no credentials/network/SimC builds.
"""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
import re
import subprocess

from simc_apl_semantic_ir_v2 import (
    canonical, evaluate_ast, git_blob, parse_profile, truth, variable_effect
)
from general_rotation_simc_e2e_research_engine_v1 import compile_spec
from general_rotation_simc_multi_spec_cold_start_v1 import load_manifest

SCHEMA = "ZrotGenericSimCSourceTargetCountProjectionV1"
SCENARIOS_SCHEMA = "ZrotGenericSimCSourceProjectionScenarioManifestV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
FACT = re.compile(r"^talent\\.[a-z0-9_]+$")
CASE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")


class ProjectionError(ValueError):
    pass


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise ProjectionError(reason)


def verify_scenarios(manifest: dict, scenario_manifest: dict) -> list[dict]:
    need(type(scenario_manifest) is dict and
         scenario_manifest.get("schema") == SCENARIOS_SCHEMA and
         isinstance(scenario_manifest.get("cases"), list) and
         1 <= len(scenario_manifest["cases"]) <= 48,
         "SOURCE_SCENARIO_MANIFEST_MISSING")
    specs = {p["key"] for p in manifest["profiles"]}
    seen = set()
    out = []
    for entry in scenario_manifest["cases"]:
        need(type(entry) is dict and set(entry) ==
             {"spec_key", "name", "assumed_talent_facts"} and
             entry["spec_key"] in specs and type(entry["name"]) is str and
             CASE.fullmatch(entry["name"]) and
             (entry["spec_key"], entry["name"]) not in seen and
             type(entry["assumed_talent_facts"]) is dict and
             len(entry["assumed_talent_facts"]) <= 12 and
             all(type(k) is str and FACT.fullmatch(k) and
                 type(v) is int and v in (0, 1)
                 for k, v in entry["assumed_talent_facts"].items()),
             "UNTRUSTED_SOURCE_BUILD_SCENARIO")
        seen.add((entry["spec_key"], entry["name"]))
        out.append(entry)
    need({x["spec_key"] for x in out} == specs,
         "ALL_PINNED_SOURCE_SPECS_REQUIRE_CONTEXT")
    return out


def source_precombat_variables(parsed: dict, initial_facts: dict) -> tuple[dict, list[dict]]:
    """Only source precombat variable expressions: no Native event imputation."""
    facts = dict(initial_facts)
    computed = []
    for row in parsed["action_lists"].get("precombat", []):
        if row["behavior"] != "VARIABLE":
            continue
        name = next((e["value"] for e in row["attributes"]
                     if e["key"] == "name"), None)
        need(type(name) is str, "VARIABLE_SOURCE_NAME_UNVERIFIED")
        ast = row["expression_fields"].get("if")
        guard = truth(evaluate_ast(ast["ast"], facts)) if ast else True
        effect = (variable_effect(row, facts) if guard is True else None)
        value = effect["value"] if effect and effect["status"] == "EVALUATED" else None
        key = "variable." + name
        if value is None:
            facts.pop(key, None)
        else:
            facts[key] = value
        computed.append({
            "name": name, "source_line": row["source_line"],
            "source_row_sha256": row["source_sha256"],
            "source_IF": "TRUE" if guard is True else
                         "FALSE" if guard is False else "UNKNOWN",
            "source_expression_result": value,
            "source_result_status": "SYNTHETICALLY_EVALUABLE" if value is not None
                                     else "UNKNOWN_OR_CONDITION_FALSE",
            "Native_variable_side_effect_parity": "NOT_VERIFIED",
        })
    return facts, computed


def _if_result(ast, facts) -> str:
    if ast is None:
        return "TRUE"
    value = truth(evaluate_ast(ast, facts))
    return "TRUE" if value is True else "FALSE" if value is False else "UNKNOWN"


def project_profile(raw: bytes, metadata: dict, case: dict,
                    counts: list[int]) -> dict:
    need(type(raw) is bytes and git_blob(raw) == metadata["git_blob"],
         "PROFILE_GIT_BLOB_NOT_PINNED")
    need(type(counts) is list and 1 <= len(counts) <= 40 and
         counts == sorted(set(counts)) and
         all(type(n) is int and 1 <= n <= 40 for n in counts) and
         {1, 2, 3}.issubset(counts),
         "TARGET_COUNTS_NOT_BOUNDED_AND_COMPLETE")
    need(case["spec_key"] == metadata["key"],
         "SOURCE_SCENARIO_SPEC_MISMATCH")
    parsed = parse_profile(raw, require_source=True,
                           expected_git_blob=metadata["git_blob"])
    source = compile_spec(raw, metadata, None)
    program = source["conditioned_opener_and_priority"][
        "all_ordered_source_IF_ELSE_lists"]
    need(source["source_APL_row_count"] == parsed["source_action_line_count"] and
         set(program) == set(parsed["action_lists"]),
         "EXISTING_SOURCE_PROGRAM_MISMATCH")
    symbols = set(parsed["source_symbol_dependencies"])
    assumptions = case["assumed_talent_facts"]
    need(set(assumptions).issubset(symbols),
         "SCENARIO_ASSUMES_TALENT_ABSENT_FROM_SOURCE")
    contexts = []
    previous = None
    for target_count in counts:
        facts, variables = source_precombat_variables(
            parsed, {"active_enemies": target_count, **assumptions})
        statuses = {}
        controls = []
        target_symbols = []
        for list_name, rows in program.items():
            original = parsed["action_lists"][list_name]
            need(len(rows) == len(original),
                 "SOURCE_ACTION_ROW_COUNT_DRIFT")
            bucket = {"TRUE": [], "FALSE": [], "UNKNOWN": []}
            for i, row in enumerate(rows):
                witness = original[i]
                ident = row["identity"]
                need(row["priority_rank_in_list"] == i + 1 and
                     ident["source_line_sha256"] == witness["source_sha256"] and
                     ident["source_line"] == witness["source_line"] and
                     row["action"] == witness["action"],
                     "SOURCE_ROW_WITNESS_DRIFT")
                guard = _if_result(row["condition_AST"], facts)
                bucket[guard].append(i + 1)
                if row["behavior"] in ("CALL", "RUN", "SWAP_UNSUPPORTED"):
                    controls.append({
                        "source_list": list_name, "rank": i + 1,
                        "action": row["action"],
                        "destination": row["source_control_destination"],
                        "source_IF": row["when_source_if"],
                        "guard_at_count_under_assumptions": guard,
                        "actual_control_transition": "UNKNOWN_NOT_NATIVE_EXECUTION",
                    })
                if any("active_enemies" in keys or
                       any(s.startswith("variable.") for s in keys)
                       for keys in row["condition_operands"].values()):
                    target_symbols.append({
                        "source_list": list_name, "rank": i + 1,
                        "source_line_sha256": ident["source_line_sha256"],
                        "source_if": row["when_source_if"],
                        "source_if_status": guard,
                        "source_symbol_dependencies": sorted(
                            set().union(*[set(s) for s in
                                            row["condition_operands"].values()])),
                    })
            statuses[list_name] = {
                "true_SOURCE_IF_priority_ranks": bucket["TRUE"],
                "false_SOURCE_IF_priority_ranks": bucket["FALSE"],
                "unknown_SOURCE_IF_priority_ranks": bucket["UNKNOWN"],
                "row_count": len(rows),
            }
        transitions = []
        if previous is not None:
            for list_name, cur in statuses.items():
                old = previous["statuses"][list_name]
                for status_key in ("TRUE", "FALSE", "UNKNOWN"):
                    key = {"TRUE": "true", "FALSE": "false",
                           "UNKNOWN": "unknown"}[status_key] + "_SOURCE_IF_priority_ranks"
                    for rank in set(old[key]).symmetric_difference(cur[key]):
                        transitions.append({
                            "source_list": list_name, "rank": rank,
                            "from_count": previous["count"],
                            "to_count": target_count,
                            "source_if_classification_changed": True,
                        })
        contexts.append({
            "target_count_hypothesis": target_count,
            "source_precombat_variable_expressions_not_native_executions": variables,
            "source_if_by_ordered_list": statuses,
            "source_control_candidates_not_actual_routing": controls,
            "source_target_or_variable_dependent_rows": target_symbols,
            "changed_source_if_classes_since_previous_sample": transitions,
            "full_native_spell_READY": "UNKNOWN",
            "actual_WoW_dummy_expected_spell": "UNKNOWN",
        })
        previous = {"count": target_count, "statuses": statuses}
    return {
        "schema": SCHEMA, "policy_id": POLICY,
        "spec_key": metadata["key"], "class_key": metadata["class_key"],
        "source_profile_git_blob_sha1": metadata["git_blob"],
        "source_profile_sha256": sha256(raw).hexdigest(),
        "scenario_name": case["name"],
        "source_only_assumed_talents_NOT_REAL_PLAYER_BUILD": assumptions,
        "ordered_source_IF_ELSE_program_REUSED": program,
        "source_APL_action_rows": parsed["source_action_line_count"],
        "source_target_count_contexts": contexts,
        "source_precombat_action_order_not_executed_opener":
            [{"action": r["action"], "source_line": r["source_line"],
              "source_row_sha256": r["source_sha256"]}
             for r in parsed["action_lists"].get("precombat", [])],
        "opener_end_condition": "UNKNOWN",
        "full_alternative_action_READY_proven": 0,
        "independent_WCL_priority_validated": False,
        "general_rotation_optimality": "UNKNOWN",
        "user_target_dummy_wrong_cast_verdict": "UNKNOWN",
        "source_control_RUN_CALL_preserved_not_flattened": True,
        "non_IF_action_attributes_not_silently_evaluated": True,
        "MAIN_promoted": False,
    }


def run(source_root: Path, manifest_path: Path, cases_path: Path,
        counts: list[int]) -> dict:
    root = source_root.resolve(strict=True)
    manifest = load_manifest(manifest_path)
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    need(head == manifest["official_simc_commit"],
         "UNPINNED_SIMC_SOURCE_REVISION")
    cases = verify_scenarios(
        manifest, json.loads(cases_path.read_bytes()))
    specs = {row["key"]: row for row in manifest["profiles"]}
    results = []
    for case in cases:
        spec = specs[case["spec_key"]]
        file = (root / spec["profile"]).resolve(strict=True)
        need(file.is_relative_to(root), "PROFILE_PATH_ESCAPES_PINNED_SIMC_ROOT")
        results.append(project_profile(file.read_bytes(), spec, case, counts))
    return {
        "schema": SCHEMA, "policy_id": POLICY,
        "official_simc_commit": head,
        "source_profiles": len(specs),
        "source_scenarios": len(results),
        "target_counts": counts,
        "all_scenarios": results,
        "no_WCL_prelock_semantic_ingestion": True,
        "real_WCL_API_calls": 0, "new_native_CXX_builds": 0,
        "current_Retail_rotation_complete": False,
        "source_only_target_breakpoint_not_fight_ready_proof": True,
        "MAIN_promoted": False,
    }


def selftest() -> dict:
    raw = ("actions.precombat=variable,name=aoe_count,value=2+(3*talent.flag)\\n"
           "actions=run_action_list,name=st,if=active_enemies=1\\n"
           "actions+=/run_action_list,name=aoe,if=active_enemies>=variable.aoe_count\\n"
           "actions.st=alpha,if=active_enemies=1&talent.flag\\n"
           "actions.aoe=beta,if=active_enemies>=variable.aoe_count\\n").encode()
    metadata = {"key": "dummy_alpha", "class_key": "alpha", "git_blob": git_blob(raw)}
    def case(name, facts):
        return {"spec_key": "dummy_alpha", "name": name,
                "assumed_talent_facts": facts}
    off = project_profile(raw, metadata, case("off", {"talent.flag": 0}),
                          [1,2,3,4,5,6])
    on = project_profile(raw, metadata, case("on", {"talent.flag": 1}),
                         [1,2,3,4,5,6])
    unknown = project_profile(raw, metadata, case("unknown", {}), [1,2,3])
    need(off["source_APL_action_rows"] == 5 and
         off["source_target_count_contexts"][1]["source_control_candidates_not_actual_routing"][1][
             "guard_at_count_under_assumptions"] == "TRUE" and
         on["source_target_count_contexts"][1]["source_control_candidates_not_actual_routing"][1][
             "guard_at_count_under_assumptions"] == "FALSE" and
         on["source_target_count_contexts"][4]["source_control_candidates_not_actual_routing"][1][
             "guard_at_count_under_assumptions"] == "TRUE" and
         unknown["source_target_count_contexts"][1]["source_control_candidates_not_actual_routing"][1][
             "guard_at_count_under_assumptions"] == "UNKNOWN" and
         all(r["full_alternative_action_READY_proven"] == 0
             for r in (off, on, unknown)), "TARGET_PROJECTION_SYNTHETIC_INVALID")
    # Unobserved talent assumptions, truncated invalid counts, and source drift fail.
    negative = 0
    for action in (
        lambda: project_profile(raw, metadata, case("bad", {"buff.enrage.up":1}), [1,2,3]),
        lambda: project_profile(raw, metadata, case("bad", {}), [1,2,2,3]),
        lambda: project_profile(raw, {**metadata, "git_blob":"a"*40},
                                case("bad", {}), [1,2,3]),
        lambda: project_profile(raw, metadata, case("bad", {"talent.missing":1}), [1,2,3]),
    ):
        try: action()
        except (ProjectionError, KeyError): negative += 1
        else: raise AssertionError("INVALID_SOURCE_TARGET_CONTEXT_ACCEPTED")
    return {
        "status": "PASS_OFFLINE_SYNTHETIC",
        "real_SimC_profile_loaded": False,
        "positive_source_target_scenarios": 3,
        "negative_fail_closed_checks": negative,
        "WCL_API_calls": 0, "actual_native_READY_proven": 0,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root", type=Path)
    p.add_argument("--manifest", type=Path)
    p.add_argument("--scenarios", type=Path)
    p.add_argument("--target-counts", default="1,2,3,4,5,6,7,8,10")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    if not any((args.source_root, args.manifest, args.scenarios)):
        result = selftest()
    else:
        if not all((args.source_root, args.manifest, args.scenarios)):
            p.error("--source-root --manifest --scenarios are all required")
        try:
            counts = [int(x) for x in args.target_counts.split(",")]
        except ValueError as exc:
            raise ProjectionError("INVALID_TARGET_COUNT_LIST") from exc
        result = run(args.source_root, args.manifest, args.scenarios, counts)
    data = canonical(result)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(data)
        print(json.dumps({"sha256": sha256(data).hexdigest(),
                          "bytes": len(data),
                          "status": result.get("status","SOURCE_ONLY_PROJECTION")}))
    else:
        print(data.decode(), end="")


if __name__ == "__main__":
    main()
