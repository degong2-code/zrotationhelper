#!/usr/bin/env python3
"""Source-faithful SimC -> conditional General Rotation HYPOTHESIS IR.

Consumes two SHA-pinned, independently verified products:
1) full original pinned profile structural+typed-AST model (121 rows)
2) actual native SimulationCraft effective APL crosscheck (121/121 equal)

Builds a hierarchical conditional reference for precombat, the default list,
call/run flow, ST / >=2 target branch routes, all priority rows, and operand
provenance. DOES NOT replace native foreground decision parity, readiness,
or a WoW player training model. No WCL lane inputs are permitted.

Default invocation: isolated synthetic structural contract test.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib,json
from pathlib import Path

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
IR_SHA="03f84ec50e8e1968b49a0dfe4d021def7681201a04a62971affbabc9b130f60d"
NATIVE_SHA="ac8959be2db6d7549b7ea1fad84f64b3a9be8f5eb3d13cc5445d3d123ea42356"

class ModelError(ValueError):pass

def _sha(raw):return hashlib.sha256(raw).hexdigest()

def read_exact(path,expected):
    raw=path.read_bytes()
    if not 100<len(raw)<1_500_000 or _sha(raw)!=expected:
        raise ModelError("PINNED_SOURCE_RECEIPT_NOT_VERIFIED")
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ModelError("DUPLICATE_JSON_KEY")
            out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=unique)

def target_guard_pairs(ast):
    """Only direct numeric conjunctions; no inferred OR or target transforms."""
    if not isinstance(ast,list):return []
    if ast[:2]==["binary","&"]:
        return target_guard_pairs(ast[2])+target_guard_pairs(ast[3])
    if len(ast)==4 and ast[:1]==["binary"]:
        op=ast[1]
        l,r=ast[2],ast[3]
        if (op in ("=","<","<=",">",">=")
            and l==["symbol","active_enemies"]
            and isinstance(r,list) and len(r)==2
            and r[0]=="number" and type(r[1]) in (int,float)):
            return [{"symbol":"active_enemies","comparator":op,"count":r[1]}]
    return []

def symbols_of(ast):
    if not isinstance(ast,list):return set()
    if ast[0]=="symbol":return {ast[1]}
    if ast[0]=="number":return set()
    if ast[0] in ("unary","function"):return symbols_of(ast[2])
    if ast[0]=="binary":return symbols_of(ast[2])|symbols_of(ast[3])
    raise ModelError("INVALID_SOURCE_AST")

def expression_breakpoints(lists):
    pairs=[]
    for name,rows in lists.items():
        for row in rows:
            for field,data in row["expression_fields"].items():
                clauses=target_guard_pairs(data["ast"])
                for clause in clauses:
                    pairs.append({"list":name,"index":row["index"],
                                  "source_line":row["source_line"],
                                  "source_attribute":field,**clause})
    return pairs

def model(source,native):
    if (source.get("schema")!="ZrotSourceFaithfulSimcAplSemanticIRV2"
        or source.get("scope_policy_id")!=POLICY
        or source.get("source_git_blob_sha1")!="3225992ed5b754ad5d61e8b785d9d859f1eed1be"
        or source.get("source_action_line_count")!=121
        or native.get("schema")!="ZrotNativeEffectiveAplCrosscheckV1"
        or native.get("scope_policy_id")!=POLICY
        or native.get("source_sha256")!=source.get("source_sha256")
        or native.get("real_native_capture") is not True
        or native.get("native_effective_ast_compilation")!="PASS"
        or native.get("source_to_native_effective",{}).get("source_to_effective_structure_identical") is not True
        or native["source_to_native_effective"].get("semantic_rows_matching")!=121
        or source.get("semantic_runtime_equivalence_to_native_SimC")!="NOT_YET_TESTED"
        or native.get("source_to_native_action_selection_parity")!="NOT_RUN"):
        raise ModelError("SOURCE_NATIVE_EQUALITY_OR_RESEARCH_AUTHORITY_MISSING")
    lists=source["action_lists"]
    control=[]
    for row in lists["default"]:
        if row["behavior"] in ("CALL","RUN"):
            attrs={e["key"]:e["value"] for e in row["attributes"]}
            if attrs["name"] not in lists:raise ModelError("UNRESOLVED_SOURCE_LIST")
            control.append({
              "caller_list":"default","source_priority_index":row["index"],
              "source_line":row["source_line"],"control":row["behavior"],
              "target_list":attrs["name"],
              "if_expression":row["expression_fields"].get("if",{}).get("source"),
              "if_ast":row["expression_fields"].get("if",{}).get("ast"),
              "target_count_clauses":target_guard_pairs(
                  row["expression_fields"].get("if",{}).get("ast")),
              "other_symbolic_guards":sorted(x for x in (
                  symbols_of(row["expression_fields"]["if"]["ast"])
                  if "if" in row["expression_fields"] else set())
                  if x!="active_enemies"),
              "no_action_semantics":"CALLER_FALLTHROUGH" if row["behavior"]=="CALL"
                                    else "RUN_DESTINATION_YIELD_NO_CALLER_FALLTHROUGH"})
    priority={}
    for list_name,rows in lists.items():
        priority[list_name]=[{
            "priority_index":row["index"],
            "action_token":row["action"],
            "action_behavior":row["behavior"],
            "source_line":row["source_line"],
            "source_sha256":row["source_sha256"],
            "raw_modifiers":row["attributes"],
            "parsed_expressions":row["expression_fields"],
            "eligibility_guard":"MUST_EVALUATE_NATIVE_SEMANTICS",
            "cooldown_resource_charge_readiness":"UNKNOWN",
            "action_ready_to_recommend":False} for row in rows]
    breakers=expression_breakpoints(lists)
    source_selected_branches=[x for x in control if x["control"]=="RUN"]
    target_equal1=[x["target_list"] for x in source_selected_branches
                   if any(c["comparator"]=="=" and c["count"]==1 for c in x["target_count_clauses"])]
    target_2more=[x["target_list"] for x in source_selected_branches
                  if any(c["comparator"]==">" and c["count"]==1 for c in x["target_count_clauses"])]
    variable_rows=[(name,row["index"],row["source_line"]) for name,rows in lists.items()
                   for row in rows if row["behavior"]=="VARIABLE"]
    control_lines=sum(len(x) for x in source["graph_edges"].values())
    if len(control)!=control_lines:
        raise ModelError("SOURCE_LIST_GRAPH_DIFFERENCE")
    if sum(len(rows) for rows in priority.values())!=121:
        raise ModelError("SOURCE_MODEL_LOSSY")
    return {
       "schema":"ZrotGeneralRotationSimcSourceHypothesisModelV1",
       "scope_policy_id":POLICY,
       "status":"NATIVE_EFFECTIVE_APL_EXACT_SOURCE_STRUCTURE_BEHAVIOR_NOT_YET_PROVEN",
       "source_profile_sha256":source["source_sha256"],
       "source_git_blob_sha1":source["source_git_blob_sha1"],
       "native_executed_effective_apl_sha256":native["native_effective_apl_sha256"],
       "native_executable_sha256":native["native_simc_binary_sha256"],
       "native_source_semantic_row_match":"121/121",
       "all_source_action_lists":{
            name:{"row_count":len(rows),"context":"PRECOMBAT_DIRECTIVES_NOT_COMBAT_OPENER"
                    if name=="precombat" else
                    "PRIORITY_SCAN_HYPOTHESIS",
                  "ordered_rows":priority[name]}
            for name,rows in priority.items()},
       "default_action_flow":control,
       "precombat":{
           "source_directive_count":len(lists["precombat"]),
           "variable_definition_count":sum(1 for n,i,l in variable_rows if n=="precombat"),
           "non_variable_directive_count":sum(1 for r in lists["precombat"] if r["behavior"]!="VARIABLE"),
           "variable_overwrites_preserved":source["duplicate_variable_definition_sites"],
           "actual_opening_cast_sequence":"NOT_DERIVED_FROM_PRECOMBAT_LINES"},
       "hero_and_target_count_route_hypotheses":source_selected_branches,
       "source_routing_target_count_equals_one":target_equal1,
       "source_routing_target_count_greater_than_one":target_2more,
       "two_target_vs_AoE_separate_source_list":"NOT_PRESENT_FOR_THIS_PINNED_FURY_PROFILE",
       "source_count_comparisons_in_conditions":breakers,
       "source_symbolic_dependencies":source["source_symbol_dependencies"],
       "raw_action_rows_retained":121,
       "run_list_control_flow_native_parity":"NOT_YET_PROVEN_PER_DECISION",
       "precombat_variable_runtime_parity":"NOT_YET_PROVEN",
       "ability_ready_state_semantics":"NOT_PROVEN",
       "source_action_priority_vs_actual_foreground_native_decision":"NOT_REPLAYED",
       "opener_sequence_native_decision_parity":"NOT_REPLAYED",
       "wcl_comparison_eligible":False,
       "target_dummy_feedback_eligible":False,
       "MAIN_promotion":False,
    }

def selftest():
    assert target_guard_pairs(["binary","&",
        ["symbol","talent.x"],
        ["binary",">",["symbol","active_enemies"],["number",1.0]]])==[
          {"symbol":"active_enemies","comparator":">","count":1.0}]
    assert target_guard_pairs(["binary","|",
        ["binary","=",["symbol","active_enemies"],["number",1.0]],
        ["symbol","x"]])==[]
    assert target_guard_pairs(["binary","+",["symbol","active_enemies"],["number",1]])==[]
    assert symbols_of(["binary","&",["symbol","rage"],
        ["binary","=",["symbol","active_enemies"],["number",1]]])=={
        "rage","active_enemies"}
    assert target_guard_pairs(["binary","=",
        ["symbol","active_enemies"],["number",1]])[0]["count"]==1
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":5,
            "native_source_loaded":False,"WCL_API_calls":0,
            "gameplay_priority_proven":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-ir",type=Path)
    p.add_argument("--native-structural-receipt",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not a.source_ir and not a.native_structural_receipt:
        d=selftest()
    elif a.source_ir and a.native_structural_receipt:
        d=model(read_exact(a.source_ir,IR_SHA),
                read_exact(a.native_structural_receipt,NATIVE_SHA))
    else:p.error("both pinned receipts or neither required")
    b=(json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(b)
        print("SIMC_GENERAL_ROTATION_SOURCE_HYPOTHESIS_SHA256="+_sha(b))
    else:print(b.decode(),end="")

if __name__=="__main__":main()
