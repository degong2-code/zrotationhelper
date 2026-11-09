#!/usr/bin/env python3
"""Bounded, source-pinned passive extra original SimC SELECT PRE fact capture.

Only instruments the original (already proved) player_t::select_action()
single action_ready call immediately after the original PRE marker.
All class-specific source names live in an external SpecAdapter JSON. Captures
the **same** original SELECT call ID and action pointer. Never changes call
count, scheduling, game data or SimC original IF comparator outcome.

No args runs synthetic patch & negative contract tests, safe in PyCharm.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from simc_apl_semantic_ir_v2 import parse_profile,canonical,git_blob
from simc_native_select_trace_instrument_v1 import SIMC_COMMIT,PLAYER_CPP_BLOB
from general_rotation_original_foreground_dispatch_v1 import (
    BEGIN,SELECT,CALLSITE,PATCH_SCHEMA as PARENT_SCHEMA
)
from simc_original_select_if_pre_witness_v1 import SEL,NATIVE,CPP_START,CPP_END

SCHEMA="ZrotOriginalSimCSelectExtraPREBoundedSourceAdapterV1"
PATCH_SCHEMA="ZrotOriginalSimCSelectedExtraPREOneNativeCallPatchV1"
MARK="ZROT_ORIGINAL_SELECT_EXTRA_PRE_FIELDS_V1|"
INSERT="      zrot_if_ready=a->action_ready();"
FIELD_NAME=re.compile(r"^[a-z][a-z0-9_]*$")
GIT40=re.compile(r"^[a-f0-9]{40}$")
CXX_EXPR={
 "sim_active_enemies": lambda f:
   "std::pair<int,double>{1,static_cast<double>(sim->active_enemies)}",
 "player_variable": lambda f:
   f'zrot_extra_var("{f["name"]}")',
 "buff_stack":lambda f:
   f'zrot_extra_buff_stack("{f["name"]}")',
 "buff_up":lambda f:
   f'zrot_extra_buff_up("{f["name"]}")',
 "buff_react":lambda f:
   f'zrot_extra_buff_react("{f["name"]}")'
}
BUFF_SEMANTICS={
 "buff_stack":"stack","buff_up":"up","buff_react":"react"
}


class PREError(ValueError):pass


def need(ok,why):
    if not ok:raise PREError(why)


def sha(data:bytes)->str:return sha256(data).hexdigest()


def valid_plan(p:dict,root:Path|None=None)->None:
    need(type(p)==dict and p.get("schema")==SCHEMA and
         p.get("policy_id")=="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1" and
         p.get("source_revision")==SIMC_COMMIT,
         "INVALID_SPEC_ADAPTER_ID_OR_REVISION")
    classes={};files=set()
    for x in p.get("profiles",[]):
        cls=x.get("actor_class");src=x.get("path");cpp=x.get("class_cpp")
        need(type(cls)==str and FIELD_NAME.fullmatch(cls) is not None and
             type(src)==str and re.fullmatch(r"profiles/MID2/MID2_[A-Za-z0-9_]+\.simc",src) is not None and
             cpp==f"engine/class_modules/sc_{cls}.cpp" and
             GIT40.fullmatch(x.get("profile_git_blob","")) is not None and
             GIT40.fullmatch(x.get("class_cpp_git_blob","")) is not None and
             cls not in classes and src not in files,
             "INVALID_PINNED_SOURCE_PROFILE_DECLARATION")
        if root is not None:
            f=root/src;g=root/cpp
            need(f.is_file() and g.is_file() and
                 git_blob(f.read_bytes())==x["profile_git_blob"] and
                 git_blob(g.read_bytes())==x["class_cpp_git_blob"],
                 "OFFICIAL_SOURCE_ADAPTER_PROFILE_OR_CLASS_HASH_DRIFT")
            ast=parse_profile(f.read_bytes(),require_source=False)
            used=set(ast["source_symbol_dependencies"])
            classes[cls]=(x,ast,used)
        else:classes[cls]=(x,None,None)
        files.add(src)
    need(1<=len(classes)<=8,"BOUNDED_PINNED_SOURCE_CLASSES_REQUIRED")
    fields=p.get("fields",[])
    need(type(fields)==list and 1<=len(fields)<=24,"BOUNDED_SOURCE_PRE_FIELD_COUNT")
    symbols=set()
    for f in fields:
        need(type(f)==dict and type(f.get("owner_class"))==str and
             f["owner_class"] in classes and f.get("kind") in CXX_EXPR and
             type(f.get("symbol"))==str and f["symbol"] not in symbols,
             "INVALID_OR_DUPLICATE_CAPTURE_SYMBOL")
        typ=f["kind"];name=f.get("name")
        expected={"sim_active_enemies":"active_enemies"} .get(typ)
        if typ=="player_variable":
            need(type(name)==str and FIELD_NAME.fullmatch(name) is not None,
                 "INVALID_PLAYER_VARIABLE_NAME")
            expected="variable."+name
        elif typ in BUFF_SEMANTICS:
            need(type(name)==str and FIELD_NAME.fullmatch(name) is not None,
                 "INVALID_BUFF_LOOKUP_NAME")
            expected=f"buff.{name}.{BUFF_SEMANTICS[typ]}"
        else:
            need(name is None,"SPURIOUS_SOURCE_FIELD_NAME")
        need(f["symbol"]==expected,"CAPTURE_SYMBOL_SEMANTICS_NOT_SOURCE_EQUIVALENT")
        if root is not None:
            x,ast,used=classes[f["owner_class"]]
            need(f["symbol"] in used,"CAPTURE_NOT_A_SOURCE_APL_OPERAND")
            if typ=="player_variable":
                need(name in ast["variable_definitions"],
                     "CAPTURE_VARIABLE_NOT_DEFINED_IN_APL")
        symbols.add(f["symbol"])
    need(len(symbols)==len(fields),"SOMETHING_WRONG_WITH_SPEC_ADAPTER")


def patch_cpp(pristine:bytes,plan:dict)->bytes:
    valid_plan(plan)
    src=pristine.decode("utf-8")
    need(src.count(CPP_START)==src.count(CPP_END)==1 and
         src.count(INSERT)==1 and src.count(SEL)==1 and
         src.count(NATIVE)==0 and
         src.count(BEGIN)==1 and src.count(SELECT)==1 and
         src.count(CALLSITE)==1 and MARK not in src,
         "PINNED_PARENT_ORIGINAL_CXX_INSTRUMENTATION_REQUIRED")
    start=src.index(CPP_START);end=src.index(CPP_END,start)
    segment=src[start:end]
    need(segment.count(INSERT)==1 and
         segment.count("a->action_ready()")==1,
         "ONE_ORIGINAL_ACTION_READY_SCOPE_REQUIRED")
    payload_sha=sha(canonical(plan))
    helper=r"""      if ( sim->log && !is_pet() && !is_enemy() )
      {
        // Original select PRE scope, strictly before the single native readiness call.
        // All accessors below are read-only and never execute an IF expression.
        const auto zrot_extra_var = [this](const char* key)->std::pair<int,double> {
          for (const auto* v: variables) {
            if (util::str_compare_ci(v->name_,key))
              return {1,static_cast<double>(v->current_value_)};
          }
          return {0,0.0};
        };
        const auto zrot_extra_buff_stack = [this](const char* key)->std::pair<int,double> {
          buff_t* b=buff_t::find(this,key);
          return b?std::pair<int,double>{1,static_cast<double>(b->check())}:
                   std::pair<int,double>{0,0.0};
        };
        const auto zrot_extra_buff_up = [this](const char* key)->std::pair<int,double> {
          buff_t* b=buff_t::find(this,key);
          return b?std::pair<int,double>{1,b->check()>0?1.0:0.0}:
                   std::pair<int,double>{0,0.0};
        };
        const auto zrot_extra_buff_react = [this](const char* key)->std::pair<int,double> {
          buff_t* b=buff_t::find(this,key);
          return b?std::pair<int,double>{1,static_cast<double>(b->stack_react())}:
                   std::pair<int,double>{0,0.0};
        };
"""
    vars_text=[]
    for i,f in enumerate(plan["fields"]):
        vars_text.append(f"        const auto zrot_extra_field_{i}={CXX_EXPR[f['kind']](f)};\n")
    # Typed trace: t, original PRE scoped call id, original action pointer,
    # canonical source adapter sha; per field (present integer, numeric value).
    format_=("ZROT_ORIGINAL_SELECT_EXTRA_PRE_FIELDS_V1|"
             "{}|{}|{}|"+payload_sha)
    fmtargs=("sim->current_time().total_millis(),zrot_pre_scope.id,"
             "static_cast<const void*>(a)")
    for i in range(len(plan["fields"])):
        format_+="|{}|{:.17g}"
        fmtargs+=f",zrot_extra_field_{i}.first,zrot_extra_field_{i}.second"
    logger=f'        sim->print_log("{format_}",\n          {fmtargs});\n'
    helper+="".join(vars_text)+logger+"      }\n"
    patched=src[:start]+segment.replace(INSERT,helper+INSERT,1)+src[end:]
    need(patched.count(MARK)==1 and
         patched.count(INSERT)==1 and
         patched.count("a->action_ready()")==src.count("a->action_ready()") and
         patched.count("action->queue_execute( execute_type::FOREGROUND );")==
             src.count("action->queue_execute( execute_type::FOREGROUND );") and
         patched.count("sequence_add( action, action->target );")==
             src.count("sequence_add( action, action->target );") and
         patched.count(SEL)==src.count(SEL) and
         patched.count(BEGIN)==src.count(BEGIN),
         "NONPASSIVE_ORIGINAL_SOURCE_MUTATION")
    return patched.encode("utf-8")


def install(root:Path,plan:dict,prior:dict)->dict:
    root=root.resolve(strict=True)
    revision=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                            capture_output=True,text=True,check=True).stdout.strip()
    need(revision==SIMC_COMMIT,"WRONG_ORIGINAL_SIMC_REVISION")
    valid_plan(plan,root)
    file=root/"engine/player/player.cpp"
    current=file.read_bytes()
    need(prior.get("schema")==PARENT_SCHEMA and
         prior.get("original_source_revision")==SIMC_COMMIT and
         prior.get("official_player_git_blob")==PLAYER_CPP_BLOB and
         prior.get("foreground_patched_sha256")==sha(current) and
         prior.get("new_ready_or_RNG_or_queue_calls")==0,
         "PARENT_FOREGROUND_DISPATCH_RECEIPT_NOT_BOUND")
    updated=patch_cpp(current,plan)
    file.write_bytes(updated)
    return {
      "schema":PATCH_SCHEMA,
      "policy_id":plan["policy_id"],
      "source_revision":SIMC_COMMIT,
      "original_pinned_player_cpp_git_blob":PLAYER_CPP_BLOB,
      "parent_foreground_patch_sha256":sha(current),
      "updated_original_player_cpp_sha256":sha(updated),
      "source_spec_adapter_sha256":sha(canonical(plan)),
      "captured_fields":[dict(f) for f in plan["fields"]],
      "original_action_ready_cxx_call_added":0,
      "original_queue_and_JSON2_methods_added":0,
      "original_if_native_comparator_calls_added":0,
      "claims_complete_physical_READY":False,
      "causal_route_off_gcd_traced":False,
      "WCL_API_calls":0
    }


def selftest():
    # This is a *static patch* test, never a simulated source READY claim.
    source=(CPP_START+"\n"
            "    if ( a->action_ready() )\n"
            '    sim->print_log("'+SEL+'{}");\n'
            "      zrot_if_ready=a->action_ready();\n"
            "}\n"+CPP_END+"\n"
            "//"+BEGIN+"\n//"+SELECT+"\n//"+CALLSITE+"\n")
    plan={"schema":SCHEMA,
          "policy_id":"ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
          "source_revision":SIMC_COMMIT,
          "profiles":[
            {"actor_class":"mage","path":"profiles/MID2/MID2_Mage_Arcane.simc",
             "profile_git_blob":"a"*40,"class_cpp":"engine/class_modules/sc_mage.cpp",
             "class_cpp_git_blob":"b"*40},
            {"actor_class":"warrior","path":"profiles/MID2/MID2_Warrior_Fury.simc",
             "profile_git_blob":"c"*40,"class_cpp":"engine/class_modules/sc_warrior.cpp",
             "class_cpp_git_blob":"d"*40}],
          "fields":[{"owner_class":"mage","symbol":"active_enemies",
                     "kind":"sim_active_enemies"},
                    {"owner_class":"mage","symbol":"variable.aoe_count",
                     "kind":"player_variable","name":"aoe_count"},
                    {"owner_class":"mage","symbol":"buff.arcane_salvo.react",
                     "kind":"buff_react","name":"arcane_salvo"}]}
    source=source.replace("    if ( a->action_ready() )\n","")
    raw=patch_cpp(source.encode(),plan).decode()
    assert raw.count(MARK)==1 and raw.count("zrot_if_ready=a->action_ready();")==1
    assert "b->stack_react()" in raw and "sim->active_enemies" in raw
    assert "current_value_" in raw and sha(canonical(plan)) in raw
    n=0
    for bad in (
       {**plan,"source_revision":"x"},
       {**plan,"fields":plan["fields"]*2},
       {**plan,"fields":[{"owner_class":"mage","symbol":"buff.arcane_salvo.react",
                          "kind":"buff_stack","name":"arcane_salvo"}]},
       {**plan,"fields":[{"owner_class":"priest","symbol":"active_enemies",
                          "kind":"sim_active_enemies"}]},
    ):
       try:patch_cpp(source.encode(),bad)
       except PREError:n+=1
       else:raise AssertionError("UNPINNED_OR_SEMANTICALLY_WRONG_SOURCE_ACCEPTED")
    for bad in (raw.encode(),source.replace(SEL,"OTHER").encode()):
       try:patch_cpp(bad,plan)
       except PREError:n+=1
       else:raise AssertionError("REPEATED_OR_UNSOURCED_CXX_PATCH_ACCEPTED")
    return {"schema":PATCH_SCHEMA,"result":"PASS_SYNTHETIC_STATIC",
            "negative_controls":n,"new_CXX_builds":0,
            "new_ready_calls":0,"WCL_API_calls":0}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source-root",type=Path)
    cli.add_argument("--plan",type=Path)
    cli.add_argument("--prior-receipt",type=Path)
    cli.add_argument("--out-receipt",type=Path)
    args=cli.parse_args()
    if not any(vars(args).values()):
        print(json.dumps(selftest(),sort_keys=True))
        return
    need(all(vars(args).values()),"ORIGINAL_SOURCE_EXTRA_PRE_EXPLICIT_INPUTS_REQUIRED")
    plan=json.loads(args.plan.read_bytes())
    prior=json.loads(args.prior_receipt.read_bytes())
    receipt=install(args.source_root,plan,prior)
    args.out_receipt.parent.mkdir(parents=True,exist_ok=True)
    with args.out_receipt.open("xb") as f:f.write(canonical(receipt))
    print("SELECT_ORIGINAL_EXTRA_PRE_PATCH_RECEIPT_SHA256="+
          sha(args.out_receipt.read_bytes()))


if __name__=="__main__":
    main()
