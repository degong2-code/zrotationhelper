#!/usr/bin/env python3
"""Generic passive DoT snapshot at the original SimC SELECT call, before ready().

Reads target->find_dot() ONLY; never get_dot(), get_target_data(), execute(),
ready(), IF, RNG, or a queue method. Source-order PRE at t is NOT automatically
a state transition observed at timestamp < t (Strict PRE). Pinned SpecAdapter
holds class, profile, source DoT name and focus operands.
No-args is a PyCharm-safe synthetic/static regression.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from simc_apl_semantic_ir_v2 import parse_profile, git_blob
from general_rotation_original_action_lifecycle_v1 import (
    SCHEMA as PARENT_SCHEMA, REV, POLICY
)
from simc_original_select_if_pre_witness_v1 import CPP_START, CPP_END

SCHEMA="ZrotGenericOriginalSelectPassiveDotBeforeReadyV1"
PLAN_SCHEMA="ZrotOriginalSelectPassiveDotSourceAdapterV1"
MARK="ZROT_ORIGINAL_SELECTED_DOT_BEFORE_READY_V1|"
EXACT="      zrot_if_ready=a->action_ready();"
SOURCE="engine/player/player.cpp"
NAME=re.compile(r"^[a-z][a-z0-9_]{0,64}$")

class DotPatchError(ValueError):
    pass
def need(ok,why):
    if not ok:raise DotPatchError(why)
def digest(x):
    return sha256(x).hexdigest()
def canonical(x):
    return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()

def validate(plan,root=None):
    need(plan.get("schema")==PLAN_SCHEMA and plan.get("policy_id")==POLICY and
         plan.get("source_revision")==REV and
         re.fullmatch(r"[a-f0-9]{40}",plan.get("source_profile_git_blob","")) and
         re.fullmatch(r"[a-f0-9]{40}",plan.get("source_class_cpp_git_blob","")) and
         NAME.fullmatch(plan.get("actor_class","")) is not None and
         NAME.fullmatch(plan.get("source_dot_action","")) is not None and
         plan.get("profile_path","")==
           "profiles/MID2/MID2_"+plan.get("profile_stem","")+".simc" and
         re.fullmatch(r"[A-Za-z0-9_]+",plan.get("profile_stem","")) is not None and
         plan.get("class_cpp_path","")==
           "engine/class_modules/sc_"+plan["actor_class"]+".cpp" and
         plan.get("source_operands")==[
           "dot."+plan["source_dot_action"]+".remains","ticking"
         ] and plan.get("target_semantics")=="BASE_ACTION_EXPRESSION_TARGET_NO_VIRTUAL_CALL" and
         plan.get("evidence_time_contract")=="SOURCE_ORDER_BEFORE_READY_NOT_STRICT_TIMESTAMP_LT",
         "UNPINNED_DOT_SOURCE_ADAPTER_OR_INVALID_SEMANTICS")
    if root is not None:
        profile=(root/plan["profile_path"]).read_bytes()
        cls=(root/plan["class_cpp_path"]).read_bytes()
        need(git_blob(profile)==plan["source_profile_git_blob"] and
             git_blob(cls)==plan["source_class_cpp_git_blob"],
             "ORIGINAL_PROFILE_OR_CLASS_SOURCE_BLOB_DRIFT")
        ast=parse_profile(profile,require_source=False)
        known={x["action"] for rows in ast["action_lists"].values() for x in rows}
        operands=set(ast["source_symbol_dependencies"])
        need(plan["source_dot_action"] in known and
             all(x in operands for x in plan["source_operands"]) and
             b"get_expression_target()" not in cls,
             "ACTION_EXPRESSION_TARGET_OVERRIDE_OR_SOURCE_OPERAND_UNSUPPORTED")
        base=(root/"engine/action/action.cpp").read_text("utf-8")
        need("player_t* action_t::get_expression_target()" in base and
             "return ( target == player ) ? player->target : target;" in base,
             "BASE_TARGET_SEMANTICS_CHANGED")
    return True

def patch(raw,plan):
    validate(plan)
    src=raw.decode("utf-8")
    need(MARK not in src and src.count(CPP_START)==src.count(CPP_END)==1 and
         src.count(EXACT)==1 and
         src.count('#include "action/dot.hpp"')==1,
         "PARENT_SELECT_PRE_OR_DOT_HEADER_MISSING")
    a=src.index(CPP_START);b=src.index(CPP_END,a);scope=src[a:b]
    need(scope.count(EXACT)==1 and
         scope.count("zrot_pre_scope.id")>=1 and
         scope.count("a->action_ready()")==1,
         "ORIGINAL_SELECTED_ACTION_CALL_NOT_UNIQUE")
    psha=digest(canonical(plan))
    # NO dynamic/mutable target getter, no get_dot(), no implicit allocation.
    # When the original target's dot is absent, remains/ticking are known 0.
    # Null expression target is separately marked absent/unknown by target=0.
    injected=(
      "      if ( sim->log && !is_pet() && !is_enemy() )\n"
      "      {\n"
      "        // Base action_t::get_expression_target source: (a->target==this)?target:a->target\n"
      "        player_t* zrot_dot_target=(a->target==this)?target:a->target;\n"
      f'        const dot_t* zrot_dot=zrot_dot_target ? zrot_dot_target->find_dot("{plan["source_dot_action"]}",this):nullptr;\n'
      "        const int zrot_dot_present=zrot_dot?1:0;\n"
      "        const int zrot_dot_ticking=zrot_dot&&zrot_dot->is_ticking()?1:0;\n"
      "        const double zrot_dot_remains=zrot_dot?zrot_dot->remains().total_seconds():0.0;\n"
      f'        sim->print_log("{MARK}{{}}|{{}}|{{}}|{{}}|{{}}|{{}}|{{}}|{{:.17g}}|{psha}",\n'
      "          sim->current_time().total_millis(),zrot_pre_scope.id,\n"
      "          static_cast<const void*>(this),static_cast<const void*>(a),\n"
      "          static_cast<const void*>(zrot_dot_target),zrot_dot_present,\n"
      "          zrot_dot_ticking,zrot_dot_remains);\n"
      "      }\n"
    )
    out=src[:a]+scope.replace(EXACT,injected+EXACT,1)+src[b:]
    need(out.count(MARK)==1 and
         out.index(MARK)<out.index(EXACT) and
         out.count(EXACT)==src.count(EXACT) and
         out.count("a->action_ready()")==src.count("a->action_ready()") and
         out.count("if_expr->success()")==src.count("if_expr->success()") and
         out.count("rng().roll(")==src.count("rng().roll(") and
         out.count("queue_execute(")==src.count("queue_execute(") and
         out.count("get_dot(")==src.count("get_dot(")+1 and # comment only
         out.count("->find_dot(")==src.count("->find_dot(")+1 and
         out.count("->remains()")==src.count("->remains()")+1,
         "NON_PASSIVE_DOT_CAPTURE_OR_ORIGINAL_READY_MUTATION")
    return out.encode("utf-8")

def install(root,plan,prior):
    root=root.resolve(strict=True)
    revision=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                           capture_output=True,text=True,check=True).stdout.strip()
    need(revision==REV,"ORIGINAL_SIMC_REVISION_DRIFT")
    validate(plan,root)
    src=root/SOURCE
    previous=src.read_bytes()
    need(prior.get("schema")==PARENT_SCHEMA and prior.get("source_revision")==REV and
         prior.get("policy_id")==POLICY and
         prior.get("patched_sha256")==digest(previous) and
         prior.get("zero_additional_original_create_init_calls")==True and
         prior.get("added_native_ready_or_RNG_or_queue_or_IF_calls")==0,
         "PARENT_ORIGINAL_SELECT_LIFECYCLE_RECEIPT_NOT_BOUND")
    new=patch(previous,plan)
    src.write_bytes(new)
    return {"schema":SCHEMA,"policy_id":POLICY,"original_source_revision":REV,
            "parent_original_player_cpp_sha256":digest(previous),
            "patched_original_player_cpp_sha256":digest(new),
            "adapter_sha256":digest(canonical(plan)),"marker":MARK,
            "original_readiness_IF_RNG_queue_calls_added":0,
            "target_actor_dot_creation_calls_added":0,
            "source_capture_stage":"BEFORE_ORIGINAL_ACTION_READY_IN_CALL",
            "Strict_PRE_timestamp_lt_action":"NOT_PROVEN",
            "current_Retail_gameplay_ready":"UNKNOWN",
            "new_general_rotation_priority_promotions":0,
            "WCL_API_calls":0,"MAIN_promoted":False}

def selftest():
    plan={"schema":PLAN_SCHEMA,"policy_id":POLICY,"source_revision":REV,
          "source_profile_git_blob":"a"*40,"source_class_cpp_git_blob":"b"*40,
          "actor_class":"mage","source_dot_action":"synthetic_dot",
          "profile_path":"profiles/MID2/MID2_Mage_Test.simc",
          "profile_stem":"Mage_Test","class_cpp_path":"engine/class_modules/sc_mage.cpp",
          "source_operands":["dot.synthetic_dot.remains","ticking"],
          "target_semantics":"BASE_ACTION_EXPRESSION_TARGET_NO_VIRTUAL_CALL",
          "evidence_time_contract":"SOURCE_ORDER_BEFORE_READY_NOT_STRICT_TIMESTAMP_LT"}
    src=('#include "action/dot.hpp"\n'+CPP_START+'\n'
         '      zrot_pre_scope.id;\n'
         '      zrot_if_ready=a->action_ready();\n'+CPP_END).encode()
    good=patch(src,plan).decode()
    need(good.count(MARK)==1 and
         good.index(MARK)<good.index(EXACT) and
         '->find_dot("synthetic_dot",this)' in good and
         'zrot_dot->remains().total_seconds()' in good and
         good.count("a->action_ready()")==1,
         "SOURCE_PASSIVE_DOT_PATCH_SYNTHETIC_FAIL")
    n=0
    for bad in (
      src.replace(b"zrot_if_ready=a->action_ready();",b"a->action_ready();"),
      src.replace(b'#include "action/dot.hpp"',b"// no dot header"),
      src.replace(b'zrot_pre_scope.id;',b'zrot_fake_id;'),
      good.encode(),
    ):
        try:patch(bad,plan)
        except DotPatchError:n+=1
        else:raise AssertionError("UNPINNED_SELECT_DOT_PATCH_WAS_ACCEPTED")
    need(n==4,"PASSIVE_DOT_PATCH_NEGATIVES")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls":n,
            "new_native_ready_or_IF_calls":0,"new_get_dot_or_alloc_calls":0,
            "Strict_PRE_timestamp_lt_action":"NOT_PROVEN",
            "MAIN_promoted":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--prior-receipt",type=Path)
    p.add_argument("--out-receipt",type=Path)
    a=p.parse_args()
    if all(x is None for x in vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(all(x is not None for x in vars(a).values()),
         "EXPLICIT_ORIGINAL_SOURCE_AND_PARENT_RECEIPT_REQUIRED")
    plan=json.loads(a.adapter.read_bytes())
    out=install(a.source_root,plan,json.loads(a.prior_receipt.read_bytes()))
    raw=canonical(out)
    a.out_receipt.parent.mkdir(parents=True,exist_ok=True)
    with a.out_receipt.open("xb") as f:f.write(raw)
    print("ORIGINAL_PASSIVE_DOT_PATCH_SHA256="+digest(raw))

if __name__=="__main__":
    main()
