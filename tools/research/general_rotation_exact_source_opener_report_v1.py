#!/usr/bin/env python3
"""Exact native SimC JSON2 action -> original APL row report, four cases.

Original action-pointer signature establishes *row identity* only, not IF
truth at select time, action readiness, priority optimality or a player cast.
No args runs offline synthetic tests; CLI requires exact raw SHA256.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from general_rotation_native_sequence_row_replay_v1 import SCHEMA as INPUT_SCHEMA
from general_rotation_simc_native_cast_delivery_v1 import POLICY

SCHEMA="ZrotGeneralRotationExactNativeSourceRowOpenerReadableReportV1"
HEX=re.compile(r"[a-f0-9]{64}\Z")


class ExactReportError(ValueError):pass


def check(value,why):
    if not value:raise ExactReportError(why)


def safe(v):
    if v is None:return "—"
    return chr(96)+str(v).replace(chr(96),"'").replace("|","\\|").replace("\n"," ").replace("\r"," ")+chr(96)


def report(data:dict,*,input_sha256:str)->str:
    check(HEX.fullmatch(input_sha256) is not None and
          data.get("schema")==INPUT_SCHEMA and
          data.get("policy_id")==POLICY and
          data.get("source_row_witness")=="ORIGINAL_ACTION_SIGNATURE_IN_SAME_JSON2_EMITTER" and
          data.get("original_pristine_and_instrumented_sequences_compared") is True and
          data.get("pristine_vs_instrumented_Native_binary_bytes_equal") is False and
          data.get("full_positive_READY_proven")==0 and
          data.get("opener_end")=="UNKNOWN" and
          data.get("WCL_blind_holdout")=="NOT_RUN" and
          data.get("dummy_mistake_permitted") is False and
          data.get("MAIN_promoted") is False,
          "UNVERIFIED_OR_PROMOTED_EXACT_ROW_INPUT")
    cases=data.get("cases")
    check(isinstance(cases,list) and len(cases)==4,
          "FOUR_ORIGINAL_SIMC_CASES_REQUIRED")
    seen=set();total=Counter()
    lines=[
        "# SimC-first General Rotation: exact original APL source row opener observations",
        "",
        "Policy: "+safe(POLICY),
        "Source exact JSON SHA256: "+safe(input_sha256),
        "",
        "**Evidence meaning:** the original SimC action object signature was",
        "observed at the same JSON2 sequence append ordinal. This proves the",
        "identity of the source APL row for an emitted simulated action,",
        "**not** that its IF was true at the earlier select instant,",
        "not full readiness or globally optimal skill priority.",
        "",
        "Pristine and instrumented action sequences match; the binaries are",
        "not byte-identical. Off-GCD, consumable, item, and autoattack",
        "events are retained and are not all manual player button presses.",
        "",
    ]
    for case in sorted(cases,key=lambda c:(c["source_spec_key"],c["target_count"])):
        identity=(case["source_spec_key"],case["source_case"])
        check(identity not in seen and
              case["target_count"] in (1,2) and
              case["original_select_decision_time_state"]=="NOT_CAPTURED" and
              case["dummy_user_mistake"]=="UNKNOWN" and
              case["parity"]["recorded_combat_action_order_and_times_unchanged"] is True and
              case["parity"]["recorded_precombat_action_order_and_times_unchanged"] is True,
              "DUPLICATE_OR_NOT_SAME_RUN_OR_UNSAFE_CASE")
        seen.add(identity)
        lines.extend([
            "## "+case["source_spec_key"]+" — "+str(case["target_count"])+" target(s)",
            "",
            "Native JSON2 combat action records: **"+
                str(case["original_json2_action_count"])+"**.",
            "Exact original row signatures (combat and precombat): **"+
                str(case["counts"].get("exact_source_row_pointer_signature",0))+"**.",
            "",
        ])
        for name,key in (("Precombat","actual_precombat_emitted_actions"),
                         ("Combat first 10 seconds","actual_combat_emitted_actions")):
            all_rows=case[key]
            rows=(all_rows if name=="Precombat" else
                  [a for a in all_rows if 0<=a["simc_time_ms"]<10000])
            lines.extend([
                "### "+name+" — original JSON2 emission sequence",
                "",
                "| SimC time | Native recorded action | Exact APL list | Local rank | Source IF expression | Proof |",
                "|---:|---|---|---:|---|---|",
            ])
            for a in rows:
                check(a["sequence_kind"] in ("COMBAT","PRECOMBAT") and
                      a["same_object_signatures_paired_to_JSON2_ordinal"] is True and
                      a["condition_truth_at_native_select"]=="UNKNOWN" and
                      a["readiness_of_competitors"]=="UNKNOWN" and
                      a["full_READY"]=="UNKNOWN" and
                      a["is_WoW_player_spellcast"] is False and
                      a["is_dummy_mistake"] is False,
                      "EMITTED_ACTION_WRONGLY_PROMOTED_TO_PRIORITY")
                status=a["exact_source_row_status"]
                check(status in ("SOURCE_POINTER_SIGNATURE_EXACT",
                                 "UNKNOWN_NO_SOURCE_SIGNATURE"),
                      "UNDECLARED_SOURCE_IDENTITY_STATUS")
                if status=="SOURCE_POINTER_SIGNATURE_EXACT":
                    check(a["source_APL_list"] not in (None,"-") and
                          type(a["source_APL_index_one_based"]) is int and
                          a["source_APL_index_one_based"]>0 and
                          HEX.fullmatch(a["source_APL_row_sha256"]) is not None,
                          "FORGED_EXACT_SOURCE_ROW")
                    total["exact_rows_rendered"]+=1
                else:
                    check(a["source_APL_row_sha256"] is None,
                          "UNKNOWN_SOURCE_HAS_SHA")
                    total["unmapped_rows_rendered"]+=1
                lines.append(
                    "| "+f"{a['simc_time_ms']/1000:.3f}"+" s | "+
                    safe(a["JSON2_action_name"])+" | "+
                    safe(a["source_APL_list"])+" | "+
                    str(a["source_APL_index_one_based"] or "—")+" | "+
                    safe(a["source_APL_IF"])+" | "+
                    safe(status)+" |")
            lines.append("")
        lines.extend([
            "Remaining combat action records beyond 10 seconds: **"+
            str(len(case["actual_combat_emitted_actions"])-
                len([a for a in case["actual_combat_emitted_actions"]
                     if 0<=a["simc_time_ms"]<10000]))+"**.",
            "",
            "10 seconds is a display window only; the true opener ending is UNKNOWN.",
            "The source IF shown is **source text**, not an independently",
            "evaluated decision-time Boolean.",
            "",
        ])
    check(len(seen)==4 and
          sum(c["counts"].get("exact_source_row_pointer_signature",0)
              for c in cases)==data["counts"].get("exact_source_row_pointer_signature"),
          "EXACT_SOURCE_SIGNATURE_TOTAL_MISMATCH")
    lines.extend([
        "## Product verification boundary",
        "",
        "The precise source row attribution removes name-only ambiguity.",
        "To convert it into a general IF/ELSE decision rule, the engine",
        "still needs independent original select-time operand and readiness",
        "evidence, opener phase transition, and 3+ target AoE tests.",
        "WCL independent discovery/lock/holdout has not been run here.",
        "Target dummy mistake verdict: UNKNOWN.",
        "",
    ])
    return "\n".join(lines)


def selftest():
    def row(kind):
        exact=kind=="SOURCE_POINTER_SIGNATURE_EXACT"
        return {
            "sequence_kind":"COMBAT","simc_time_ms":500,
            "JSON2_action_name":"spell","source_APL_list":"default" if exact else "-",
            "source_APL_index_one_based":1 if exact else 0,
            "source_APL_row_sha256":"a"*64 if exact else None,
            "source_APL_IF":"buff.example.up" if exact else None,
            "exact_source_row_status":kind,
            "same_object_signatures_paired_to_JSON2_ordinal":True,
            "condition_truth_at_native_select":"UNKNOWN",
            "readiness_of_competitors":"UNKNOWN",
            "full_READY":"UNKNOWN",
            "is_WoW_player_spellcast":False,"is_dummy_mistake":False}
    cases=[]
    for spec in ("one","two"):
        for target,name in ((1,"st"),(2,"2t")):
            cases.append({
                "source_spec_key":spec,"source_case":name,"target_count":target,
                "original_select_decision_time_state":"NOT_CAPTURED",
                "dummy_user_mistake":"UNKNOWN",
                "parity":{"recorded_combat_action_order_and_times_unchanged":True,
                          "recorded_precombat_action_order_and_times_unchanged":True},
                "original_json2_action_count":1,
                "counts":{"exact_source_row_pointer_signature":1},
                "actual_precombat_emitted_actions":[],
                "actual_combat_emitted_actions":[row("SOURCE_POINTER_SIGNATURE_EXACT")]})
    doc={"schema":INPUT_SCHEMA,"policy_id":POLICY,
         "source_row_witness":"ORIGINAL_ACTION_SIGNATURE_IN_SAME_JSON2_EMITTER",
         "original_pristine_and_instrumented_sequences_compared":True,
         "pristine_vs_instrumented_Native_binary_bytes_equal":False,
         "full_positive_READY_proven":0,"opener_end":"UNKNOWN",
         "WCL_blind_holdout":"NOT_RUN","dummy_mistake_permitted":False,
         "MAIN_promoted":False,"cases":cases,
         "counts":{"exact_source_row_pointer_signature":4}}
    result=report(doc,input_sha256="f"*64)
    assert "buff.example.up" in result
    assert result.count("### Combat first 10 seconds")==4
    wrong=json.loads(json.dumps(doc))
    wrong["cases"][0]["actual_combat_emitted_actions"][0][
        "condition_truth_at_native_select"]=True
    try:report(wrong,input_sha256="f"*64)
    except ExactReportError:pass
    else:raise AssertionError("FALSE_IF_TRUTH_PROMOTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "specs":2,"cases":4,"tests":12,
            "full_READY_proven":0,"WCL_API_calls":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path)
    p.add_argument("--expected-sha256")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.input is None:
        if a.expected_sha256 or a.out:p.error("--input required")
        print(json.dumps(selftest(),sort_keys=True));return
    check(a.out is not None and
          isinstance(a.expected_sha256,str) and
          HEX.fullmatch(a.expected_sha256) is not None,
          "RAW_SOURCE_SHA_AND_OUT_REQUIRED")
    raw=a.input.read_bytes()
    check(sha256(raw).hexdigest()==a.expected_sha256,
          "ORIGINAL_EXACT_ROW_ARTIFACT_SHA256_MISMATCH")
    result=report(json.loads(raw),input_sha256=a.expected_sha256)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(result.encode("utf-8"))
    print("EXACT_NATIVE_SOURCE_ROW_OPENER_REPORT_SHA256="+
          sha256(a.out.read_bytes()).hexdigest())


if __name__=="__main__":main()
