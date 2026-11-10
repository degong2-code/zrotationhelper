#!/usr/bin/env python3
"""Generic same-run SimC original competitor IF proof by bounded source domains.

Reuses the archived original SELECT-PRE/extra-PRE/native IF/selected-return raw
trace. Requires original source Git blobs, authenticated raw/receipt hashes,
same foreground dispatch, exact attempted APL row and native comparator.
An externally declared binary source operand domain is allowed ONLY after
pinning its exact source C++ implementation and semantic anchors.

The Native comparator is comparison-only. An all-false source IF supports
exclusion of that APL row at THAT original source call; not skill-global
NOT_READY, full positive READY, an opener end or WoW user advice.
Default without arguments: synthetic cross-spec fail-closed regression.
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
import subprocess
import zipfile

from simc_apl_semantic_ir_v2 import (
    canonical, git_blob, parse_profile, evaluate_ast, truth, Expression,
)
from general_rotation_original_select_extra_pre_v1 import (
    valid_plan, MARK as EXTRA_MARK, sha as digest,
)
from general_rotation_original_select_extra_pre_replay_v1 import (
    SCHEMA as SELECTED_SCHEMA,
)

SCHEMA="ZrotGenericOriginalSimCAttemptBoundedIFReplayV1"
ADAPTER="ZrotOriginalSimCSourceBoundedIFAdapterV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SOURCE_REV="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
PRE_MARK="ZROT_ORIGINAL_SELECT_IF_PRE_V1|"
IF_MARK="ZROT_ORIGINAL_SELECT_NATIVE_IF_V1|"
PERFORM_MARK="ZROT_GR_JSON2_ACTION_SOURCE_ROW_V1|"
BEGIN_MARK="ZROT_GR_FOREGROUND_APL_BEGIN_V1|"
HEXDIGEST=re.compile(r"^[0-9a-f]{64}$")
GIT40=re.compile(r"^[0-9a-f]{40}$")
PTR=re.compile(r"^0x[0-9a-fA-F]+$")

class SourceCounterfactualError(ValueError): pass

def need(ok:bool,reason:str):
    if not ok: raise SourceCounterfactualError(reason)

def hash_bytes(b:bytes)->str:
    return sha256(b).hexdigest()

def bounded_if(ast:list, facts:dict, domains:dict)->dict:
    """All finite assignments from code-certified domains; do not impute facts."""
    need(type(ast) is list and type(facts) is dict and type(domains) is dict
         and len(domains)<=5 and
         all(type(k) is str and type(v) in (int,float,bool) and
             math.isfinite(float(v)) for k,v in facts.items()) and
         all(type(k) is str and type(v) is list and v==[0,1]
             and k not in facts for k,v in domains.items()),
         "UNTRUSTED_SOURCE_OR_DOMAIN_FACTS")
    names=sorted(domains)
    outcomes=[]
    for values in product(*[domains[n] for n in names]):
        params={**facts,**dict(zip(names,values))}
        verdict=truth(evaluate_ast(ast,params))
        outcomes.append((dict(zip(names,values)),
                         "TRUE" if verdict is True else
                         "FALSE" if verdict is False else "UNKNOWN"))
    states={x[1] for x in outcomes}
    classification=(
        "ALL_FALSE" if states=={"FALSE"} else
        "ALL_TRUE" if states=={"TRUE"} else
        "MIXED_OR_UNKNOWN")
    minimal=dict(facts)
    if classification=="ALL_FALSE":
        for symbol in sorted(facts):
            trial={k:v for k,v in minimal.items() if k!=symbol}
            for vals in product(*[domains[n] for n in names]):
                if truth(evaluate_ast(ast,{**trial,**dict(zip(names,vals))})) is not False:
                    break
            else:
                minimal=trial
        for key in minimal:
            trial={k:v for k,v in minimal.items() if k!=key}
            need(any(truth(evaluate_ast(ast,{**trial,**dict(zip(names,vals))}))
                     is not False
                     for vals in product(*[domains[n] for n in names])),
                 "NOT_MINIMAL_SOURCE_FACTS")
    return {
        "classification":classification,
        "enumerated_synthetic_source_domain_assignments":len(outcomes),
        "assignment_source_IF_outcomes":outcomes,
        "minimal_observed_original_PRE_facts_for_ALL_FALSE":
            {k:minimal[k] for k in sorted(minimal)}
            if classification=="ALL_FALSE" else None,
        "missing_outside_declared_domains_not_assumed_zero":True,
        "Native_POST_not_a_condition_input":True,
    }

def validate_source_domains(root:Path,adapter:dict)->dict:
    need(adapter.get("schema")==ADAPTER and
         adapter.get("policy_id")==POLICY and
         adapter.get("source_revision")==SOURCE_REV and
         type(adapter.get("domain_rules")) is list and
         len(adapter["domain_rules"])<=5,
         "UNPINNED_OR_OVERBROAD_DOMAIN_ADAPTER")
    result={}
    for rule in adapter["domain_rules"]:
        need(type(rule) is dict and
             set(rule)=={"symbol","domain","source_path","source_git_blob",
                         "required_anchors"} and
             type(rule["symbol"]) is str and
             rule["symbol"] not in result and
             rule["domain"]==[0,1] and
             type(rule["source_path"]) is str and
             rule["source_path"].startswith("engine/") and
             ".." not in rule["source_path"].split("/") and
             GIT40.fullmatch(rule["source_git_blob"]) is not None and
             type(rule["required_anchors"]) is list and
             1<=len(rule["required_anchors"])<=5 and
             all(type(a) is str and len(a)>15 for a in rule["required_anchors"]),
             "UNTRUSTED_OR_DUPLICATE_DOMAIN_CXX_ANCHORS")
        file=(root/rule["source_path"]).resolve(strict=True)
        need(file.is_relative_to(root) and
             git_blob(file.read_bytes())==rule["source_git_blob"],
             "DOMAIN_CXX_BLOB_NOT_PINNED")
        cpp=file.read_text(encoding="utf-8")
        need(all(cpp.count(anchor)==1 for anchor in rule["required_anchors"]),
             "DOMAIN_CXX_SEMANTICS_ANCHOR_NOT_UNIQUE")
        result[rule["symbol"]]=rule["domain"]
    need(result, "SOURCE_DOMAIN_RULES_REQUIRED")
    # A generic typed SOURCE-EXPRESSION contract, not a spec/action rule.
    for symbol,domain in result.items():
        if symbol.startswith("talent."):
            need(re.fullmatch(r"talent\\.[a-z0-9_]+",symbol) is not None,
                 "UNSAFE_TALENT_EXPRESSION_SHAPE")
            owner=next(r for r in adapter["domain_rules"]
                       if r["symbol"]==symbol)
            need(owner["source_path"]=="engine/player/player.cpp" and
                 any("_talent.enabled()" in a for a in
                     owner["required_anchors"]),
                 "TALENT_BOOLEAN_CXX_MECHANIC_NOT_PINNED")
        elif symbol.startswith("prev_gcd."):
            need(re.fullmatch(r"prev_gcd\\.[1-9][0-9]*\\.[a-z0-9_]+",
                              symbol) is not None,
                 "UNSAFE_PREVIOUS_GCD_EXPRESSION_SHAPE")
            owner=next(r for r in adapter["domain_rules"]
                       if r["symbol"]==symbol)
            need(owner["source_path"]=="engine/action/action.cpp" and
                 any("internal_id ==" in a for a in
                     owner["required_anchors"]),
                 "PREV_GCD_BOOLEAN_CXX_MECHANIC_NOT_PINNED")
        else:
            raise SourceCounterfactualError(
                "UNPROVEN_SOURCE_EXPRESSION_BOOLEAN_DOMAIN")
    talent=adapter.get("supporting_pinned_talent_boolean_source")
    if any(k.startswith("talent.") for k in result):
        need(type(talent) is dict and
             talent.get("path")=="engine/player/talent.hpp" and
             GIT40.fullmatch(talent.get("git_blob","")) is not None and
             type(talent.get("anchor")) is str,
             "TALENT_ENABLED_BOOLEAN_DEFINITION_NOT_PINNED")
        source=(root/talent["path"]).read_bytes()
        need(git_blob(source)==talent["git_blob"] and
             talent["anchor"].replace("\\n","\n") in source.decode("utf-8"),
             "PINNED_TALENT_ENABLED_RETURN_TYPE_NOT_VERIFIED")
    return result

def verified_archive(zpath:Path,adapter:dict)->dict:
    items=adapter["archive_members"]
    need(type(items) is dict and
         set(items)=={"log","selected","native_receipt"} and
         all(type(x) is dict and set(x)=={"path","sha256"} and
             type(x["path"]) is str and
             x["path"].startswith("zrot-original-extra-pre/") and
             ".." not in x["path"].split("/") and
             HEXDIGEST.fullmatch(x["sha256"]) is not None
             for x in items.values()),
         "ARCHIVE_MEMBER_PIN_FORMAT_INVALID")
    with zipfile.ZipFile(zpath) as z:
        names=z.namelist()
        need(len(names)==len(set(names)) and
             all(".." not in name.split("/") and
                 not name.startswith("/") for name in names),
             "DUPLICATE_OR_TRAVERSAL_IN_SOURCE_ARCHIVE")
        extracted={}
        for name,ref in items.items():
            need(ref["path"] in names, "ORIGINAL_SOURCE_ARTIFACT_MEMBER_MISSING")
            b=z.read(ref["path"])
            need(0<len(b)<=3_000_000 and
                 hash_bytes(b)==ref["sha256"],
                 "ORIGINAL_SOURCE_ARTIFACT_BYTES_CHANGED")
            extracted[name]=b
    return extracted

def parse_attempts(raw:str,plan:dict)->dict:
    """Pair original SELECT_PRE, EXTRA_PRE, Native POST by *call ID and ptr*."""
    markers={}
    begun={}
    performed={}
    for seq,line in enumerate(raw.splitlines()):
        for mark,kind in ((PRE_MARK,"pre"),(EXTRA_MARK,"extra"),
                          (IF_MARK,"if")):
            if mark not in line:continue
            need(line.count(mark)==1,"ORIGINAL_MARKER_DUPLICATED_IN_LINE")
            pieces=line.split(mark,1)[1].strip().split("|")
            need(len(pieces)>=4 and pieces[0].isdecimal() and
                 pieces[1].isdecimal() and int(pieces[1])>0,
                 "ORIGINAL_MARKER_TIME_OR_ID_INVALID")
            tm,ident=int(pieces[0]),int(pieces[1])
            entry=markers.setdefault(ident,{})
            need(kind not in entry,"DUPLICATE_SAME_ROOT_MARKER")
            if kind=="pre":
                need(len(pieces)==7 and
                     pieces[3].isdecimal() and int(pieces[3])>=1 and
                     PTR.fullmatch(pieces[4]) is not None,
                     "ORIGINAL_PRE_SOURCE_ROW_OR_PTR_INVALID")
                entry[kind]={"line":seq,"t":tm,"owner":pieces[2],
                             "rank":int(pieces[3]),"ptr":pieces[4].lower()}
            elif kind=="extra":
                need(len(pieces)==4+2*len(plan["fields"]) and
                     PTR.fullmatch(pieces[2]) is not None and
                     pieces[3]==digest(canonical(plan)),
                     "EXTRA_SOURCE_PRE_PLAN_SHA_OR_PTR_DRIFT")
                vals={}
                for i,field in enumerate(plan["fields"]):
                    present=pieces[4+2*i]
                    need(present in ("0","1"),"ORIGINAL_EXTRA_PRESENT_NOT_BOOL")
                    try:n=float(pieces[5+2*i])
                    except (TypeError,ValueError,OverflowError) as exc:
                        raise SourceCounterfactualError("INVALID_EXTRA_PRE_NUMBER") from exc
                    need(math.isfinite(n),"NONFINITE_EXTRA_PRE")
                    if present=="1":
                        vals[field["symbol"]]=n
                entry[kind]={"line":seq,"t":tm,"ptr":pieces[2].lower(),
                             "observed_numeric_fields":vals}
            else:
                need(len(pieces)==4 and
                     PTR.fullmatch(pieces[2]) is not None and
                     pieces[3] in ("0","1"),
                     "NATIVE_IF_POST_INVALID")
                entry[kind]={"line":seq,"t":tm,"ptr":pieces[2].lower(),
                             "Native_IF_POST":pieces[3]}
        if BEGIN_MARK in line:
            p=line.split(BEGIN_MARK,1)[1].strip().split("|")
            need(len(p)==3 and p[0].isdecimal() and p[1].isdecimal() and
                 PTR.fullmatch(p[2]) is not None,
                 "FOREGROUND_DISPATCH_ROOT_INVALID")
            key=(int(p[0]),int(p[1]))
            need(key not in begun,"DUPLICATE_FOREGROUND_BEGIN")
            begun[key]={"line":seq,"ptr":p[2].lower()}
        if PERFORM_MARK in line:
            p=line.split(PERFORM_MARK,1)[1].strip().split("|")
            need(len(p)==7 and p[0].isdecimal() and
                 p[2].isdecimal() and p[5].isdecimal() and
                 PTR.fullmatch(p[6]) is not None,
                 "ORIGINAL_NATIVE_PERFORM_ROW_INVALID")
            key=(int(p[0]),int(p[2]))
            need(key not in performed,"DUPLICATE_ORIGINAL_PERFORMED_EVENT")
            performed[key]={"line":seq,"channel":p[1],"action":p[3],
                            "owner":p[4],"rank":int(p[5]),"ptr":p[6].lower()}
    for cid,entry in markers.items():
        need("pre" in entry and "extra" in entry and
             entry["pre"]["line"]<entry["extra"]["line"] and
             entry["pre"]["t"]==entry["extra"]["t"] and
             entry["pre"]["ptr"]==entry["extra"]["ptr"],
             "UNPAIRED_OR_NOT_STRICT_ORIGINAL_PRE")
        if "if" in entry:
            need(entry["extra"]["line"]<entry["if"]["line"] and
                 entry["if"]["ptr"]==entry["pre"]["ptr"] and
                 entry["if"]["t"]==entry["pre"]["t"],
                 "NATIVE_POST_BEFORE_PRE_OR_WRONG_ROOT")
    return {"attempts":markers,"foreground_begin":begun,"performed":performed}

def run(source_root:Path,archive:Path,adapter_path:Path,plan_path:Path)->dict:
    root=source_root.resolve(strict=True)
    git=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       capture_output=True,text=True,check=True).stdout.strip()
    need(git==SOURCE_REV,"SIMC_SOURCE_REVISION_NOT_PINNED")
    adapter=json.loads(adapter_path.read_bytes())
    domains=validate_source_domains(root,adapter)
    plan=json.loads(plan_path.read_bytes())
    valid_plan(plan,root)
    artifacts=verified_archive(archive,adapter)
    native=json.loads(artifacts["native_receipt"])
    selected=json.loads(artifacts["selected"])
    need(native.get("status")=="SIMC_NATIVE_CAPTURED_UNPARSED" and
         native.get("controlled_target_count")==adapter["target_count"] and
         native.get("controlled_seed")==31459 and
         native.get("controlled_fight_seconds")==30 and
         native.get("native_log_sha256")==hash_bytes(artifacts["log"]) and
         selected.get("schema")==SELECTED_SCHEMA and
         selected.get("source_spec")==adapter["source_spec_key"] and
         selected.get("targets")==adapter["target_count"] and
         selected.get("source_adapter_sha256")==digest(canonical(plan)) and
         selected.get("full_physical_READY_proven")==0 and
         selected.get("competitor_ready_proven")==0 and
         selected.get("dummy_wrong_cast")=="UNKNOWN",
         "NATIVE_CAPTURE_OR_SELECTED_VERIFICATION_MISMATCH")
    profile=(root/adapter["source_profile"]).resolve(strict=True)
    need(profile.is_relative_to(root) and
         git_blob(profile.read_bytes())==adapter["source_profile_git_blob"] and
         hash_bytes(profile.read_bytes())==native["profile_sha256"],
         "PINNED_ORIGINAL_APL_SOURCE_NOT_SAME_NATIVE_PROFILE")
    parsed=parse_profile(profile.read_bytes(),require_source=True,
                         expected_git_blob=adapter["source_profile_git_blob"])
    action_list=parsed["action_lists"].get(adapter["source_list"])
    need(type(action_list) is list and
         1<=adapter["candidate_rank"]<adapter["selected_rank"]<=len(action_list),
         "SOURCE_LIST_OR_PRIORITY_RANK_INVALID")
    candidate=action_list[adapter["candidate_rank"]-1]
    chosen=action_list[adapter["selected_rank"]-1]
    need(candidate["behavior"]=="ACTION" and
         chosen["behavior"]=="ACTION" and
         candidate["expression_fields"].get("if") is not None and
         set(domains).issubset(
             set(candidate["expression_fields"]["if"]["symbols"])),
         "SOURCE_EXPRESSION_NOT_OWNED_BY_ADAPTER")
    trace=parse_attempts(artifacts["log"].decode("utf-8"),plan)
    rows=[s for s in selected["selected_source_IF_samples"]
          if s["source_list"]==adapter["source_list"] and
             s["source_rank"]==adapter["selected_rank"] and
             s["source_action"]==chosen["action"]]
    need(len(rows)==adapter["expected_selected_occurrences"],
         "ORIGINAL_SELECTED_SOURCE_COHORT_CHANGED")
    output=[]
    seen_roots=set()
    for source in rows:
        t=source["t_ms"]
        winner_id=source["original_selected_call_id"]
        dispatch=source["original_dispatch_token"]
        key=(t,dispatch)
        begin=trace["foreground_begin"].get(key)
        perform=trace["performed"].get(key)
        winner=trace["attempts"].get(winner_id)
        need(begin and perform and winner and
             source["source_row_sha256"]==chosen["source_sha256"] and
             perform["channel"]=="C" and
             perform["action"]==source["source_action"] and
             perform["owner"]==adapter["source_list"] and
             perform["rank"]==adapter["selected_rank"] and
             perform["ptr"]==winner["pre"]["ptr"] and
             begin["line"]<winner["pre"]["line"]<perform["line"] and
             winner["pre"]["rank"]==adapter["selected_rank"] and
             winner["pre"]["owner"]==adapter["source_list"] and
             winner["pre"]["t"]==t and
             source["original_native_IF_comparator"]=="TRUE" and
             winner.get("if",{}).get("Native_IF_POST")=="1",
             "CHOICE_NOT_ORIGINAL_FOREGROUND_SOURCE_SAME_ROOT")
        matches=[(cid,v) for cid,v in trace["attempts"].items()
                 if v["pre"]["t"]==t and
                 v["pre"]["owner"]==adapter["source_list"] and
                 v["pre"]["rank"]==adapter["candidate_rank"] and
                 begin["line"]<v["pre"]["line"]<winner["pre"]["line"]]
        need(len(matches)==1, "NO_UNIQUE_EARLIER_NATIVE_SOURCE_ROW_ROOT")
        cid,attempt=matches[0]
        need((t,cid) not in seen_roots and
             cid<winner_id and
             attempt.get("if",{}).get("Native_IF_POST")=="0",
             "ORIGINAL_EARLIER_IF_NATIVE_POST_NOT_FALSE")
        seen_roots.add((t,cid))
        facts={f["symbol"]:attempt["extra"]["observed_numeric_fields"][
                   f["symbol"]]
               for f in plan["fields"] if
               f["owner_class"]==adapter["actor_class"] and
               f["symbol"] in attempt["extra"]["observed_numeric_fields"]}
        expression=candidate["expression_fields"]["if"]
        states=bounded_if(expression["ast"],facts,domains)
        need(states["classification"]!="ALL_TRUE",
             "INDEPENDENT_SOURCE_IF_ALWAYS_TRUE_VS_NATIVE_FALSE")
        output.append({
            "t_original_simc_ms":t,
            "same_run_foreground_dispatch_id":dispatch,
            "original_source_candidate_call_id":cid,
            "original_source_candidate_pointer":attempt["pre"]["ptr"],
            "candidate_original_source_list":adapter["source_list"],
            "candidate_original_source_rank":adapter["candidate_rank"],
            "candidate_original_source_row_sha256":candidate["source_sha256"],
            "source_original_APL_IF":expression["source"],
            "native_if_POST_comparison_only":"FALSE",
            "observed_exact_original_root_PRE_facts":facts,
            "source_binary_domain_proof":domains,
            "source_IF_counterfactual_proof":states,
            "source_local_APL_candidate_EXCLUDED":
                states["classification"]=="ALL_FALSE",
            "global_ability_NOT_READY":"UNKNOWN",
            "parent_CALL_RUN_full_route":"UNKNOWN",
            "selected_full_ready":"UNKNOWN",
            "real_WoW_expected_cast":"UNKNOWN",
        })
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "source_revision":SOURCE_REV,
        "source_spec_key":adapter["source_spec_key"],
        "source_profile_git_blob_sha1":adapter["source_profile_git_blob"],
        "source_native_log_sha256":hash_bytes(artifacts["log"]),
        "selected_source_replay_sha256":hash_bytes(artifacts["selected"]),
        "reused_original_workflow_run":adapter["original_workflow_run"],
        "original_selected_cohort_count":len(rows),
        "original_source_IF_all_FALSE_candidate_count":sum(
            x["source_local_APL_candidate_EXCLUDED"] for x in output),
        "original_source_IF_not_decidable_candidate_count":sum(
            not x["source_local_APL_candidate_EXCLUDED"] for x in output),
        "source_only_competitor_counterfactuals":output,
        "this_is_NOT_same_native_run_as_older_ready_ledger":True,
        "original_source_competing_full_READY_proven":0,
        "current_Retail_gameplay_priority_proven":0,
        "opener_end":"UNKNOWN",
        "actual_player_wrong_cast":"UNKNOWN",
        "new_WCL_API_calls":0,"new_SimC_CXX_builds":0,
        "MAIN_promoted":False,
    }

def selftest()->dict:
    def evaluate(expr,facts,domains):
        return bounded_if(Expression(expr).parse(),facts,domains)
    domains={"talent.flag":[0,1],"prev_gcd.1.spell":[0,1]}
    phrase="buff.react>=(20-talent.flag)&(active_enemies<variable.aoe_count|buff.charges=4)|prev_gcd.1.spell&buff.stack>=(10+5*talent.flag)"
    first=evaluate(phrase,{"active_enemies":2,"variable.aoe_count":2,
                          "buff.react":3,"buff.charges":2,"buff.stack":4},
                   domains)
    second=evaluate(phrase,{"active_enemies":2,"variable.aoe_count":2,
                           "buff.react":20,"buff.charges":3,"buff.stack":20},
                    domains)
    need(first["classification"]=="ALL_FALSE" and
         first["enumerated_synthetic_source_domain_assignments"]==4 and
         second["classification"]=="MIXED_OR_UNKNOWN" and
         first["minimal_observed_original_PRE_facts_for_ALL_FALSE"] is not None and
         second["minimal_observed_original_PRE_facts_for_ALL_FALSE"] is None,
         "GENERIC_BOUNDED_SOURCE_REPLAY_STATIC_CASE_FAILED")
    rejects=0
    for expr,facts,ds in [
        ("x|y",{"x":float("nan")},{"y":[0,1]}),
        ("x|y",{"x":0},{"y":[0,2]}),
        ("x|y",{"x":0},{"x":[0,1]}),
        ("x|y",{"x":float("inf")},{"y":[0,1]}),
    ]:
        try:evaluate(expr,facts,ds)
        except SourceCounterfactualError:rejects+=1
        else:raise AssertionError("UNSAFE_BOUNDED_SOURCE_INPUT_ACCEPTED")
    return {
        "status":"PASS_OFFLINE_GENERIC_SYNTHETIC",
        "two_arbitrary_state_hypotheses":2,
        "negative_invalid_inputs_rejected":rejects,
        "actual_original_native_replay_performed":False,
        "physical_READY_proven":0,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--artifact-zip",type=Path)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--pre-plan",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any((a.source_root,a.artifact_zip,a.adapter,a.pre_plan)):
        result=selftest()
    else:
        if not all((a.source_root,a.artifact_zip,a.adapter,a.pre_plan)):
            p.error("Provide source root, artifact zip, adapter and original PRE plan together")
        result=run(a.source_root,a.artifact_zip,a.adapter,a.pre_plan)
    b=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(b)
        print(json.dumps({"status":"WRITTEN",
                          "sha256":hash_bytes(b),"bytes":len(b)}))
    else:
        print(b.decode(),end="")

if __name__=="__main__":
    main()
