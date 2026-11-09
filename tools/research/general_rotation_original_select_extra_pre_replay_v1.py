#!/usr/bin/env python3
"""Original SimC same SELECT call extra state -> typed APL IF audit.

Consumes the previous ORIGINAL dispatcher proof and *same* raw C++ log.
Only an externally pinned class/profile SpecAdapter binds numeric PRE
observations. The original native IF result is a comparison target, never an
input. A source IF success does not establish physical READY, priority or a
WoW player's mistake. Default no args runs synthetic fail-closed tests.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import (
    parse_profile,canonical,git_blob,evaluate_ast,truth
)
from general_rotation_original_dispatch_if_replay_v1 import (
    replay as previous_replay,_profile_class,DispatchIFError
)
from simc_original_select_if_pre_witness_v1 import SEL
from general_rotation_original_foreground_dispatch_v1 import SELECT
from general_rotation_original_select_extra_pre_v1 import (
    valid_plan,MARK,sha,PREError
)

SCHEMA="ZrotOriginalSimCSelectedSameCallExtraPRESourceIFReplayV1"
SOURCE_REVISION="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
MATCH="SOURCE_IF_EXTRA_ORIGINAL_PRE_AST_MATCH_NATIVE_COMPARATOR"
NO_NATIVE="SOURCE_IF_EXTRA_ORIGINAL_PRE_AST_KNOWN_NO_NATIVE_COMPARATOR"
UNKNOWN="UNKNOWN_SOURCE_IF_EXTRA_PRE_INCOMPLETE"
NO_IF="SOURCE_APL_NO_EXPLICIT_IF_NOT_READY_PROOF"
PTR=re.compile(r"^0x[0-9a-fA-F]+$")
HEXDIGEST=re.compile(r"^[0-9a-f]{64}$")


class ExtraError(ValueError):pass


def need(ok,why):
    if not ok:raise ExtraError(why)


def _load(path:Path):
    need(path.is_file() and not path.is_symlink(),"INPUT_FILE_REQUIRED")
    raw=path.read_bytes()
    need(0<len(raw)<9_000_000,"UNBOUNDED_OR_EMPTY_INPUT")
    obj=json.loads(raw)
    need(type(obj)==dict,"JSON_OBJECT_REQUIRED")
    return obj


def replay(log:str,profile:bytes,plan:dict,legacy_plan:dict, *,
           source_label:str,targets:int,
           original_dispatch_sha256:str|None=None)->dict:
    valid_plan(plan)
    old=previous_replay(log,profile,legacy_plan,
                        source_label=source_label,targets=targets,
                        expected_dispatch_sha256=original_dispatch_sha256)
    cls=_profile_class(profile)
    entries=[p for p in plan["profiles"] if p["actor_class"]==cls]
    need(len(entries)==1,"SOURCE_CLASS_NOT_BOUND_TO_EXTRA_PRE_ADAPTER")
    need(git_blob(profile)==entries[0]["profile_git_blob"] and
         plan["source_revision"]==SOURCE_REVISION,
         "EXACT_ORIGINAL_PROFILE_OR_SOURCE_REVISION_MISMATCH")
    typed=parse_profile(profile,require_source=False)
    # A parsed PRE record is tied to a single original scope id and action ptr.
    plan_sha=sha(canonical(plan))
    extra={};selected={};pre={}
    fields=plan["fields"]
    all_lines=log.splitlines()
    for line_n,line in enumerate(all_lines):
        if SEL in line:
            p=line.split(SEL,1)[1].strip().split("|")
            need(len(p)==7 and p[1].isdecimal() and PTR.fullmatch(p[4]) is not None,
                 "LEGACY_ORIGINAL_PRE_MARKER_MALFORMED")
            token=int(p[1]);need(token not in pre,"DUPLICATED_ORIGINAL_PRE_CALL_ID")
            pre[token]=(line_n,int(p[0]),p[4].lower())
        if SELECT in line:
            p=line.split(SELECT,1)[1].strip().split("|")
            need(len(p)==4 and p[1].isdecimal() and
                 PTR.fullmatch(p[3]) is not None,"ORIGINAL_SELECT_MARKER_INVALID")
            token=int(p[1]);need(token not in selected,"REUSED_DISPATCH_TOKEN")
            selected[token]=(line_n,int(p[0]),p[3].lower())
        if MARK not in line:
            continue
        need(line.count(MARK)==1,"DUPLICATE_EXTRA_PRE_MARKER")
        p=line.split(MARK,1)[1].strip().split("|")
        need(len(p)==4+2*len(fields) and
             p[0].isdecimal() and p[1].isdecimal() and int(p[1])>0 and
             PTR.fullmatch(p[2]) is not None and
             p[3]==plan_sha and HEXDIGEST.fullmatch(p[3]) is not None,
             "EXTRA_PRE_FIELDS_OR_PLAN_FINGERPRINT_MISMATCH")
        token=int(p[1]);need(token not in extra,"REUSED_EXTRA_SOURCE_PRE_CALL_ID")
        data={}
        for i,f in enumerate(fields):
            valid=p[4+2*i]
            need(valid in ("0","1"),"INVALID_PRE_VALUE_PRESENT_BIT")
            try:value=float(p[5+2*i])
            except (TypeError,ValueError,OverflowError) as e:
                raise ExtraError("EXTRA_NATIVE_PRE_NONNUMERIC") from e
            need(math.isfinite(value),"EXTRA_PRE_NONFINITE")
            if valid=="1":
                data[f["symbol"]]=value
        extra[token]=(line_n,int(p[0]),p[2].lower(),data)
    need(extra and set(extra)==set(pre),
         "EXTRA_ORIGINAL_SELECT_PRE_RECORDS_INCOMPLETE")
    counted=Counter();first=Counter();samples=[];known_source=[]
    for row in old["source_IF_exact_selected_rows"]:
        call_id=row["original_selected_same_call_id"]
        dispatch=row["exact_original_dispatch_token"]
        sel=selected.get(dispatch)
        x=extra.get(call_id);original=pre.get(call_id)
        need(sel and x and original and
             original[0]<x[0]<sel[0] and
             original[1]==x[1] and
             x[1]<=sel[1] and
             original[2]==x[2]==sel[2],
             "EXTRA_FACT_NOT_SAME_SELECTED_ROOT_PRE_SCOPE")
        name=row["source_list"];rank=row["source_rank"]
        need(name in typed["action_lists"] and
             1<=rank<=len(typed["action_lists"][name]),
             "SELECTED_SOURCE_IF_ROW_OUT_OF_PROFILE")
        original_row=typed["action_lists"][name][rank-1]
        need(original_row["source_sha256"]==row["source_row_sha256"] and
             original_row["action"]==row["source_action"],
             "SELECTED_SOURCE_IF_ROW_IDENTITY_DRIFT")
        expr=original_row["expression_fields"].get("if")
        facts={f["symbol"]:x[3][f["symbol"]] for f in fields
               if f["owner_class"]==cls and f["symbol"] in x[3]}
        if expr is None:
            kind=NO_IF;truth_value=None
        else:
            truth_value=truth(evaluate_ast(expr["ast"],facts))
            if truth_value is None:
                kind=UNKNOWN
            elif row["native_IF_same_call_comparator"]=="NOT_REACHED":
                kind=NO_NATIVE
            else:
                need((row["native_IF_same_call_comparator"]=="TRUE")==truth_value,
                     "INDEPENDENT_ORIGINAL_SOURCE_IF_VS_NATIVE_COMPARATOR_CONFLICT")
                kind=MATCH
        counted[kind]+=1
        if row["t_ms"]<10000:first[kind]+=1
        selected_record={
            "t_ms":row["t_ms"],"source_list":name,
            "source_rank":rank,"source_action":row["source_action"],
            "source_row_sha256":row["source_row_sha256"],
            "original_dispatch_token":dispatch,
            "original_selected_call_id":call_id,
            "original_SOURCE_IF_evidence":kind,
            "original_source_IF_independent_truth":
                "UNKNOWN" if truth_value is None else
                ("TRUE" if truth_value else "FALSE"),
            "original_native_IF_comparator":row["native_IF_same_call_comparator"],
            "original_PRE_fields":facts,
            "source_IF_required_symbols":expr["symbols"] if expr else [],
            "unobserved_symbols":(
                sorted(set(expr["symbols"])-set(facts)) if expr else []),
            "original_physical_READY":"UNKNOWN",
            "competitor_priority":"UNKNOWN",
            "dummy_error":"UNKNOWN"}
        samples.append(selected_record)
        if kind==MATCH:known_source.append(selected_record)
    need(len(samples)==old["original_foreground_selected_direct_count"] and
         sum(counted.values())==len(samples),
         "EXTRA_PRE_SELECTED_SOURCE_IF_COVERAGE_INCOMPLETE")
    need(old["native_IF_same_call_comparator_used_as_input"] is False and
         old["full_physical_READY_proven"]==0 and
         old["WCL_blind_holdout"]=="NOT_RUN",
         "PRIOR_SOURCE_PROVENANCE_BOUNDARY_DRIFT")
    # Pure source-side IF AST. Never use the comparator as an input field.
    return {
        "schema":SCHEMA,"policy_id":plan["policy_id"],
        "original_SimC_source_revision":SOURCE_REVISION,
        "original_profile_blob":git_blob(profile),
        "source_spec":source_label,"targets":targets,
        "source_class":cls,"source_adapter_sha256":plan_sha,
        "original_dispatch_replay_sha256":old["original_dispatch_replay_sha256"],
        "original_json2_emitter_records":old["actual_original_emitter_records"],
        "original_selected_direct_foreground":len(samples),
        "extra_pre_marker_total":len(extra),
        "native_if_comparator_count":old["native_IF_comparator_count"],
        "source_independent_IF_triage":dict(sorted(counted.items())),
        "first_10s_not_exact_opener_end":dict(sorted(first.items())),
        "selected_source_IF_samples":samples,
        "narrow_source_IF_matches":known_source,
        "nonforeground_combat_emitter_rows":
            old["non_foreground_combat_emitter_rows"],
        "source_if_comparator_not_replay_input":True,
        "source_if_not_full_physical_READY":True,
        "full_physical_READY_proven":0,
        "competitor_ready_proven":0,
        "actual_spell_execution_complete":"UNKNOWN",
        "opener_end":"UNKNOWN","WCL_blind_holdout":"NOT_RUN",
        "dummy_wrong_cast":"UNKNOWN",
        "new_WCL_API_calls":0,"MAIN_promoted":False
    }


def selftest():
    from general_rotation_original_foreground_dispatch_v1 import BEGIN,CALLSITE
    from general_rotation_same_run_return_emitter_v1 import RETURN,ACTOR,EMITTER_MARK
    from general_rotation_original_select_extra_pre_v1 import SCHEMA as PLAN_SCHEMA
    from simc_native_select_trace_instrument_v1 import SIMC_COMMIT
    source=b'warrior="Synthetic"\nspec=fury\nactions=/synthetic,if=rage>80\n'
    plan={"schema":PLAN_SCHEMA,
          "policy_id":"ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
          "source_revision":SIMC_COMMIT,
          "profiles":[{"actor_class":"warrior",
                       "path":"profiles/MID2/MID2_Warrior_Fury.simc",
                       "profile_git_blob":git_blob(source),
                       "class_cpp":"engine/class_modules/sc_warrior.cpp",
                       "class_cpp_git_blob":"a"*40}],
          "fields":[{"owner_class":"warrior","symbol":"rage",
                     "kind":"actor_resource","name":"RESOURCE_RAGE"}]}
    legacy_plan={"schema":"ZrotOriginalSimCSourceIFPreSpecAdapterV1",
                 "policy_id":"ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
                 "source_revision":SIMC_COMMIT,
                 "resource_enum":"RESOURCE_RAGE","resource_symbol":"rage",
                 "buff_name":"recklessness","buff_symbol":"buff.recklessness.up",
                 "class_cpp":"engine/class_modules/sc_warrior.cpp",
                 "original_class_cpp_blob":"38ee3dd0d5943eb9227ec55aefb21e7d47244f96",
                 "source_expected_buff_construction":
                   'make_buff( this, "recklessness"',
                 "approved_source_only_nongame_capture":True}
    adapter_sha=sha(canonical(plan))
    lines=[
      BEGIN+"100|1|0x11",
      SEL+"100|21|default|1|0xaa|92|1",
      MARK+"100|21|0xaa|"+adapter_sha+"|1|92",
      "ZROT_ORIGINAL_SELECT_NATIVE_IF_V1|100|21|0xaa|1",
      RETURN+"100|DIRECT|0x11|default|default|1|0xaa|1",
      SELECT+"100|1|0x11|0xaa",
      CALLSITE+"100|1|APL_ROOT|0x11|0xaa|0",
      ACTOR+"100|C|0|0x11|0xaa",
      EMITTER_MARK+"100|C|0|synthetic|default|1|0xaa"]
    base="\n".join(lines)
    good=replay(base,source,plan,legacy_plan,source_label="synthetic",targets=1)
    assert good["original_selected_direct_foreground"]==1
    assert good["source_independent_IF_triage"][MATCH]==1
    assert good["full_physical_READY_proven"]==0
    failures=0
    for bad in (
      base.replace(adapter_sha,"0"*64),
      base.replace(MARK+"100|21",MARK+"101|21"),
      base.replace(MARK+"100|21",MARK+"100|22"),
      base.replace("ZROT_ORIGINAL_SELECT_NATIVE_IF_V1|100|21|0xaa|1",
                   "ZROT_ORIGINAL_SELECT_NATIVE_IF_V1|100|21|0xaa|0"),
      base.replace(MARK+"100|21|0xaa|"+adapter_sha+"|1|92",""),
    ):
        try:replay(bad,source,plan,legacy_plan,source_label="synthetic",targets=1)
        except (ExtraError,DispatchIFError,PREError):failures+=1
        else:raise AssertionError("FOREIGN_OR_FUTURE_EXTRA_FACT_PRODUCED_READY")
    missing=base.replace(MARK+"100|21|0xaa|"+adapter_sha+"|1|92",
                         MARK+"100|21|0xaa|"+adapter_sha+"|0|92")
    safe=replay(missing,source,plan,legacy_plan,
                source_label="synthetic",targets=1)
    assert safe["source_independent_IF_triage"][UNKNOWN]==1
    assert safe["full_physical_READY_proven"]==0
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls":failures,
            "source_IF_independent":True,
            "physical_READY_proven":0,"WCL_calls":0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-log",type=Path)
    parser.add_argument("--profile",type=Path)
    parser.add_argument("--plan",type=Path)
    parser.add_argument("--legacy-plan",type=Path)
    parser.add_argument("--source-label")
    parser.add_argument("--targets",type=int)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if all(v is None for v in vars(args).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(v is not None for v in vars(args).values()),
         "EXPLICIT_ORIGINAL_SOURCE_CAPTURE_REPLAY_INPUTS_REQUIRED")
    result=replay(args.native_log.read_text("utf-8"),
                  args.profile.read_bytes(),
                  _load(args.plan),_load(args.legacy_plan),
                  source_label=args.source_label,targets=args.targets)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("xb") as f:f.write(canonical(result))
    print("ORIGINAL_SAME_CALL_EXTRA_PRE_SOURCE_IF_SHA256="+
          sha(args.out.read_bytes()))
    print("ORIGINAL_SAME_CALL_EXTRA_PRE_SOURCE_IF_COUNTS="+
          json.dumps(result["source_independent_IF_triage"],sort_keys=True))


if __name__=="__main__":
    main()
