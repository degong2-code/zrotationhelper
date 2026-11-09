#!/usr/bin/env python3
"""Readable report of pinned original SimC opener samples and complete APL.

No-argument PyCharm mode uses purely synthetic data. This module renders the
generic source-to-native model; it does not generate recommendations, reparse
APL, infer an opener end, or claim observed casts prove optimal priority.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

from general_rotation_simc_native_cast_delivery_v1 import (
    SCHEMA as INPUT_SCHEMA,POLICY)

SCHEMA="ZrotGeneralRotationSourceWithObservedSimCCastsReportV1"
HASH=re.compile(r"^[a-f0-9]{64}$")


class ReadableReportError(ValueError):pass


def require(x,reason):
    if not x:raise ReadableReportError(reason)


def cell(x):
    if x is None:return "—"
    v=str(x).replace("\n"," ").replace("\r"," ").replace("|","\\|")
    return chr(96)+v.replace(chr(96),"'")+chr(96)


def title(x):
    return str(x).replace("\n"," ").replace("\r"," ").replace("#","").replace("|","\\|")


def render(doc:dict,*,sha256_of_input:str)->str:
    require(HASH.fullmatch(sha256_of_input) is not None and
            doc.get("schema")==INPUT_SCHEMA and
            doc.get("policy_id")==POLICY and
            doc.get("full_ready_proven")==0 and
            doc.get("opener_true_end_and_competing_READY")=="UNKNOWN" and
            doc.get("post_opener_conditioned_source_program_complete") is True and
            doc.get("WCL_independent_holdout")=="NOT_RUN" and
            doc.get("target_dummy_error_verdict")=="UNKNOWN" and
            doc.get("MAIN_promoted") is False,
            "UNVERIFIED_OR_PROMOTED_INPUT")
    specs=defaultdict(list);seen=set()
    cases=doc.get("research_cases")
    require(isinstance(cases,list) and len(cases)>=4 and
            len(cases)==doc["target_count_cases"],
            "NOT_ALL_TARGET_CASES_PRESENT")
    for c in cases:
        identity=(c["source_spec_key"],c["case"])
        require(identity not in seen and
                type(c["target_count"]) is int and c["target_count"]>0 and
                type(c["simc_JSON2_observed_combat_action_count"]) is int and
                c["simc_JSON2_observed_combat_action_count"]>0 and
                c["first_real_player_cast"]=="UNKNOWN" and
                c["opener_end_transition"]=="UNKNOWN" and
                c["dummy_error_verdict"]=="UNKNOWN",
                "UNSAFE_ACTUAL_CASE_TO_HUMAN_REPORT")
        seen.add(identity);specs[c["source_spec_key"]].append(c)
    require(len(specs)==doc["source_model_count"],"SPEC_COVERAGE_MISMATCH")
    lines=[
        "# SimC-first General Rotation research report",
        "",
        "Product scope: "+cell(POLICY),
        "Input SHA256: "+cell(sha256_of_input),
        "",
        "**Research only, NOT a verified player rotation.** Each opener row below is an",
        "original SimC JSON2 action sample; it does not independently establish",
        "the exact APL decision row or whether other skills were available.",
        "The first 10 seconds are an observation window, not a proven opener ending.",
        "No independent WCL holdout, no full READY, no target-dummy error verdict.",
        "",
    ]
    total_rows=0
    for spec in sorted(specs):
        source=sorted(specs[spec],key=lambda c:c["target_count"])
        lines.extend(["## "+title(spec),""])
        lines.append("Official pinned profile Git blob: "+cell(
            source[0]["source_profile_git_blob_sha1"]))
        lines.append("")
        for c in source:
            lines.extend([
                "### Original SimC actions: "+str(c["target_count"])+" target(s), "+title(c["case"]),
                "",
                "Native source-root returns (includes list controls; NOT casts): **"+
                str(c["original_simc_root_source_returns_not_casts"])+"**.",
                "JSON2 observed sample actions during full fight: **"+
                str(c["simc_JSON2_observed_combat_action_count"])+"**.",
                "Sampled first "+str(c["opener_window_ms_for_observation_only"]/1000)+" s:",
                "",
                "| Time | Observed SimC action | Numeric ID | Possible APL rows (name-only) |",
                "|---:|---|---:|---:|",
            ])
            for a in c["observed_first_window_actions"]:
                require(a["exact_source_row_used"]=="UNKNOWN" and
                        a["same_timestamp_SimC_snapshot_is_strict_PRE"] is False and
                        a["source_or_competitor_readiness"]=="UNKNOWN" and
                        a["user_mistake_proven"] is False,
                        "OBSERVED_ACTION_FALSELY_CERTIFIED")
                lines.append(
                    "| "+f"{a['at_simc_ms']/1000:.3f}"+"s | "+cell(a["action_token"])+
                    " | "+str(a["numeric_spell_id"])+" | "+
                    str(len(a["potential_APL_source_rows_by_action_name_ONLY"]))+" |")
            lines.extend([
                "",
                "Remaining observed JSON2 actions after sample window: **"+
                str(len(c["observed_after_window_actions"]))+"**. "
                "Not independently certified as post-opener.",
                "",
            ])
        lines.extend([
            "### Complete ordered source IF/ELSE priority model",
            "",
            "Each list is in its own local APL rank order. RUN/CALL controls",
            "are not player spellcasts; source-IF may be conditional on talents,",
            "resources, procs, cooldowns or target count.",
            "",
        ])
        program=source[0]["source_APL_priority_model"]
        for c in source[1:]:
            require(program==c["source_APL_priority_model"],
                    "DIFFERENT_APL_PROGRAMS_ACROSS_TARGET_CASES")
        names=sorted(program,key=lambda n:(n!="precombat",n!="default",n))
        for name in names:
            rows=program[name]
            lines.extend(["#### Source list: "+title(name)+" ("+str(len(rows))+" rows)","",
                          "| Priority | Kind | Action | Source IF | Control / fallback |",
                          "|---:|---|---|---|---|"])
            for ix,row in enumerate(rows,1):
                require(row["rank_in_source_list"]==ix and
                        row["independent_native_READINESS"]=="UNKNOWN" and
                        row["expected_player_skill"]=="UNKNOWN",
                        "APL_ORDER_OR_READY_CONTRACT_FAILED")
                lines.append(
                    "| "+str(ix)+" | "+cell(row["kind"])+
                    " | "+cell(row["action"])+" | "+
                    cell(row["when_source_IF"])+" | "+
                    cell(row["control_or_action_effect"])+" |")
                total_rows+=1
            lines.append("")
        lines.extend([
            "**Not proven:** exact per-action source row, simultaneous competitor",
            "readiness, global optimality, phase transition/end, or dummy mistake.",
            "",
        ])
    lines.extend([
        "## Status and next proof",
        "",
        "Original SimC source APL rows rendered: **"+str(total_rows)+"**.",
        "Native action-record cases: **"+str(len(cases))+"**; observed records: **"+
            str(doc["actual_simc_JSON2_observed_action_count"])+"**.",
        "",
        "Next: reconcile this simulated performed-action sequence with exact",
        "original SimC source choices and relevant decision-time guard states;",
        "then lock WCL blind candidates before held-out comparison.",
        "",
        "WoW addon training feedback cannot flag an error from this report alone.",
        "",
    ])
    return "\n".join(lines)


def selftest()->dict:
    def action():
        return {"at_simc_ms":300,"action_token":"alpha","numeric_spell_id":123,
                "exact_source_row_used":"UNKNOWN",
                "same_timestamp_SimC_snapshot_is_strict_PRE":False,
                "source_or_competitor_readiness":"UNKNOWN",
                "user_mistake_proven":False,
                "potential_APL_source_rows_by_action_name_ONLY":[]}
    row={"rank_in_source_list":1,"kind":"ACTION","action":"alpha",
         "when_source_IF":"buff.example.up",
         "control_or_action_effect":None,
         "independent_native_READINESS":"UNKNOWN",
         "expected_player_skill":"UNKNOWN"}
    cases=[]
    for spec in ("synthetic_a","synthetic_b"):
        for t,name in ((1,"st"),(2,"2t")):
            cases.append({
                "source_spec_key":spec,"case":name,"target_count":t,
                "source_profile_git_blob_sha1":"a"*40,
                "original_simc_root_source_returns_not_casts":3,
                "simc_JSON2_observed_combat_action_count":1,
                "first_real_player_cast":"UNKNOWN",
                "opener_end_transition":"UNKNOWN",
                "dummy_error_verdict":"UNKNOWN",
                "opener_window_ms_for_observation_only":10000,
                "observed_first_window_actions":[action()],
                "observed_after_window_actions":[],
                "source_APL_priority_model":{"default":[row]}})
    v={"schema":INPUT_SCHEMA,"policy_id":POLICY,
       "source_model_count":2,"target_count_cases":4,
       "full_ready_proven":0,"opener_true_end_and_competing_READY":"UNKNOWN",
       "post_opener_conditioned_source_program_complete":True,
       "WCL_independent_holdout":"NOT_RUN",
       "target_dummy_error_verdict":"UNKNOWN","MAIN_promoted":False,
       "research_cases":cases,"actual_simc_JSON2_observed_action_count":4}
    report=render(v,sha256_of_input="f"*64)
    assert "source IF/ELSE" in report
    assert "buff.example.up" in report
    assert "rows rendered: **2**" in report
    wrong=json.loads(json.dumps(v))
    wrong["research_cases"][0]["observed_first_window_actions"][0][
        "exact_source_row_used"]="fake"
    try:render(wrong,sha256_of_input="f"*64)
    except ReadableReportError:pass
    else:raise AssertionError("UNVERIFIED_SOURCE_ROW_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":12,"source_APL_reparsed":False,
            "WCL_API_calls":0,"full_READY_proven":0}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--input",type=Path)
    cli.add_argument("--expected-sha256")
    cli.add_argument("--out",type=Path)
    a=cli.parse_args()
    if a.input is None:
        if a.expected_sha256 or a.out:cli.error("input required")
        print(json.dumps(selftest(),sort_keys=True));return
    require(a.out is not None and
            isinstance(a.expected_sha256,str) and
            HASH.fullmatch(a.expected_sha256) is not None,
            "INPUT_SHA256_AND_OUTPUT_REQUIRED")
    original=a.input.read_bytes()
    require(sha256(original).hexdigest()==a.expected_sha256,
            "MARKDOWN_SOURCE_RAW_SHA_CHANGED")
    report=render(json.loads(original),sha256_of_input=a.expected_sha256)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as out:out.write(report.encode("utf-8"))
    print("SIMC_GENERAL_ROTATION_READABLE_REPORT_SHA256="+
          sha256(a.out.read_bytes()).hexdigest())


if __name__=="__main__":main()
