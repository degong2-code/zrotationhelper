#!/usr/bin/env python3
"""Generic original SimC select-call PRE -> exact source IF evaluation witness.

Source-pinned original player_t::select_action action_ready() call is executed
EXACTLY ONCE. Captures a configured raw actor resource and a named buff stack,
and compares a separately evaluated source APL IF to original native
if_expr->success() from that same call, using a unique thread-local call ID
and the EXACT original action object pointer. No action_name/timestamp-only
join and no dependence on another SimC run's PRE state.

The named field and enum are supplied by a *source-pinned SpecAdapter*. The
generic selector, C++ scope and AST replay contain no specialization logic.

No arguments: synthetic/local source-patch/self-test only, no live SimC.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import subprocess

from simc_apl_semantic_ir_v2 import (
    parse_profile, Expression, ast_symbols, evaluate_ast, truth, canonical, git_blob
)
from simc_native_sequence_apl_row_producer_v1 import patch as emitter_patch, MARK as EMITTER_MARK
from simc_native_select_trace_instrument_v1 import SIMC_COMMIT, PLAYER_CPP_BLOB, RELATIVE
from general_rotation_simc_native_cast_delivery_v1 import POLICY

SCHEMA="ZrotOriginalSimCSelectedRowSameCallIFPreWitnessV1"
PRODUCER_SCHEMA="ZrotOriginalSimCSelectedRowSameCallIFSourcePatchV1"
SEL="ZROT_ORIGINAL_SELECT_IF_PRE_V1|"
NATIVE="ZROT_ORIGINAL_SELECT_NATIVE_IF_V1|"
HEADER="engine/zrot_original_select_if_scope_v1.hpp"
PLAYER="engine/player/player.cpp"
ACTION="engine/action/action.cpp"
ACTION_BLOB="399ecd9453b3f30bfc2ebf2b3ffd8f56cce8f8d4"
CPP_START="action_t* player_t::select_action( const action_priority_list_t& list,"
CPP_END="\nplayer_t* player_t::actor_by_name_str"
ACTION_START="bool action_t::action_ready()"
ACTION_END="\nbool action_t::cost_affordable()"
EXACT_CALL="    if ( a->action_ready() )"
EXACT_IF="  if ( if_expr && !if_expr->success() )\n    return false;"
HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")
POINTER=re.compile(r"^0x[0-9A-Fa-f]+$")

SCOPE=r"""#pragma once
#include <atomic>
#include <cstdint>
namespace zrot_original_select_if_v1 {
inline thread_local std::uint64_t active_id = 0;
inline std::atomic<std::uint64_t> next_id{0};
struct guard {
  std::uint64_t saved;
  std::uint64_t id;
  guard():saved(active_id), id(next_id.fetch_add(1, std::memory_order_relaxed)+1) { active_id=id; }
  ~guard() { active_id=saved; }
  guard(const guard&)=delete;
  guard& operator=(const guard&)=delete;
};
}
"""

class OriginalIFError(ValueError):pass


def need(x,reason):
    if not x:raise OriginalIFError(reason)


def sha(data:bytes)->str:return sha256(data).hexdigest()


def plan_check(p:dict)->None:
    need(p.get("schema")=="ZrotOriginalSimCSourceIFPreSpecAdapterV1" and
         p.get("policy_id")==POLICY and
         p.get("source_revision")==SIMC_COMMIT and
         p.get("resource_enum") in ("RESOURCE_RAGE","RESOURCE_MANA") and
         re.fullmatch("[a-z][a-z0-9_.]{1,90}",p.get("resource_symbol","")) is not None and
         re.fullmatch("[a-z][a-z0-9_]{1,70}",p.get("buff_name","")) is not None and
         p.get("buff_symbol")=="buff."+p["buff_name"]+".up" and
         re.fullmatch("[0-9a-f]{40}",p.get("original_class_cpp_blob","")) is not None and
         re.fullmatch("engine/class_modules/sc_[a-z]+.cpp",p.get("class_cpp","")) is not None and
         p.get("source_expected_buff_construction")==
            'make_buff( this, "'+p["buff_name"]+'"' and
         p.get("approved_source_only_nongame_capture") is True,
         "INVALID_PINNED_SPEC_ADAPTER_FIELD_PLAN")


def patch_cpp(player:bytes,action:bytes,plan:dict,*,enforce_pin:bool=True)->dict[str,bytes]:
    plan_check(plan)
    if enforce_pin:
        need(git_blob(player)==PLAYER_CPP_BLOB and git_blob(action)==ACTION_BLOB,
             "ORIGINAL_SIMC_PLAYER_ACTION_BLOB_CHANGED")
    origp=player.decode("utf-8")
    origa=action.decode("utf-8")
    need(origp.count(CPP_START)==1 and origp.count(CPP_END)==1 and
         origa.count(ACTION_START)==1 and origa.count(ACTION_END)==1 and
         origa.count(EXACT_IF)>=1 and
         "zrot_original_select_if_v1" not in origp+origa,
         "PINNED_SELECT_OR_ACTION_METHOD_ANCHOR_NOT_UNIQUE")
    # Prior native emitter only instruments original JSON2 sequence append.
    emitted=emitter_patch(player,enforce_pin=enforce_pin).decode("utf-8")
    begin=emitted.index(CPP_START); end=emitted.index(CPP_END,begin)
    segment=emitted[begin:end]
    need(segment.count(EXACT_CALL)==1 and segment.count("a->action_ready()")==1,
         "SELECT_ACTION_ORIGINAL_READY_CALL_DRIFT")
    res=plan["resource_enum"];buff=plan["buff_name"]
    raw=r"""    bool zrot_if_ready=false;
    {
      zrot_original_select_if_v1::guard zrot_pre_scope;
      if ( sim->log && !is_pet() && !is_enemy() )
      {
        unsigned zrot_apl_row=0;
        const char* zrot_apl_owner="-";
        if ( a->action_list && a->signature )
        {
          const auto& zrot_apl=*a->action_list;
          for ( std::size_t zrot_i=0; zrot_i<zrot_apl.action_list.size(); ++zrot_i )
          {
            if ( &(zrot_apl.action_list[zrot_i]) == a->signature )
            {
              zrot_apl_owner=zrot_apl.name_str.c_str();
              zrot_apl_row=static_cast<unsigned>(zrot_i+1);
              break;
            }
          }
        }
        const buff_t* zrot_pre_buff=buff_t::find(this,"__BUFF__");
        const int zrot_pre_stacks=zrot_pre_buff ? zrot_pre_buff->check() : -1;
        sim->print_log("ZROT_ORIGINAL_SELECT_IF_PRE_V1|{}|{}|{}|{}|{}|{:.17g}|{}",
          sim->current_time().total_millis(),zrot_pre_scope.id,zrot_apl_owner,
          zrot_apl_row,static_cast<const void*>(a),
          static_cast<double>(resources.current[__RESOURCE__]),zrot_pre_stacks);
      }
      zrot_if_ready=a->action_ready();
    }
    if ( zrot_if_ready )"""
    raw=raw.replace("__BUFF__",buff).replace("__RESOURCE__",res)
    updated=segment.replace(EXACT_CALL,raw,1)
    need(updated.count("a->action_ready()")==1 and
         updated.count(SEL)==1 and
         updated.index(SEL)<updated.index("zrot_if_ready=a->action_ready()"),
         "SELECT_PRE_ORDER_OR_READY_SEMANTICS_CHANGED")
    patched_player=emitted[:begin]+updated+emitted[end:]
    insert='#include "zrot_original_select_if_scope_v1.hpp"\n'
    need(patched_player.count('#include "action/action.hpp"')==1,
         "PLAYER_CPP_INCLUDE_ANCHOR_CHANGED")
    patched_player=patched_player.replace('#include "action/action.hpp"',
                                          insert+'#include "action/action.hpp"',1)
    start=origa.index(ACTION_START);stop=origa.index(ACTION_END,start)
    abody=origa[start:stop]
    need(abody.count(EXACT_IF)==1 and abody.count("if_expr->success()")==1,
         "ORIGINAL_ACTION_NATIVE_IF_ONCE_REQUIRED")
    comparison=r"""  if ( if_expr )
  {
    const bool zrot_original_native_if=if_expr->success();
    if ( sim->log && player && !player->is_pet() && !player->is_enemy() &&
         zrot_original_select_if_v1::active_id!=0 )
      sim->print_log("ZROT_ORIGINAL_SELECT_NATIVE_IF_V1|{}|{}|{}|{}",
        sim->current_time().total_millis(),zrot_original_select_if_v1::active_id,
        static_cast<const void*>(this),zrot_original_native_if ? 1 : 0);
    if ( !zrot_original_native_if )
      return false;
  }"""
    changed=abody.replace(EXACT_IF,comparison,1)
    need(changed.count("if_expr->success()")==1 and changed.count(NATIVE)==1,
         "NATIVE_IF_EXPRESSION_EVALUATED_MORE_THAN_ONCE")
    patched_action=origa[:start]+changed+origa[stop:]
    need(patched_action.count('#include "action/action.hpp"')==1,
         "ACTION_CPP_INCLUDE_ANCHOR_CHANGED")
    patched_action=patched_action.replace('#include "action/action.hpp"',
                                          insert+'#include "action/action.hpp"',1)
    return {PLAYER:patched_player.encode("utf-8"),
            ACTION:patched_action.encode("utf-8"),
            HEADER:SCOPE.encode("utf-8")}


def verify_official_source(root:Path,p:dict):
    plan_check(p)
    need(subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
            capture_output=True,text=True,check=True).stdout.strip()==SIMC_COMMIT,
         "OFFICIAL_SIMC_REVISION_DRIFT")
    originals={}
    for name,blob in ((PLAYER,PLAYER_CPP_BLOB),(ACTION,ACTION_BLOB),
                      (p["class_cpp"],p["original_class_cpp_blob"])):
        raw=subprocess.run(["git","-C",str(root),"show","HEAD:"+name],
            capture_output=True,check=True).stdout
        need(git_blob(raw)==blob,"OFFICIAL_SOURCE_BLOB_DRIFT:"+name)
        originals[name]=raw
    need(p["source_expected_buff_construction"].encode() in originals[p["class_cpp"]],
         "SPEC_ADAPTER_NAMED_BUFF_CONSTRUCTION_NOT_IN_ORIGINAL_SOURCE")
    need(b"static buff_t* find( player_t*" in
         subprocess.run(["git","-C",str(root),"show","HEAD:engine/buff/buff.hpp"],
                        capture_output=True,check=True).stdout,
         "ORIGINAL_BUFF_LOOKUP_SIGNATURE_DRIFT")
    return originals


def install(root:Path,p:dict)->dict:
    root=root.resolve(strict=True)
    pristine=verify_official_source(root,p)
    need((root/PLAYER).read_bytes()==pristine[PLAYER] and
         (root/ACTION).read_bytes()==pristine[ACTION] and
         not (root/HEADER).exists(),
         "INSTRUMENTATION_SOURCE_NOT_PRISTINE")
    patched=patch_cpp(pristine[PLAYER],pristine[ACTION],p)
    for location,bytes_ in patched.items():
        file=root/location
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_bytes(bytes_)
    return {"schema":PRODUCER_SCHEMA,"policy_id":POLICY,
       "source_revision":SIMC_COMMIT,
       "source_plan":p,
       "official_player_git_blob":PLAYER_CPP_BLOB,
       "official_action_git_blob":ACTION_BLOB,
       "patch_sha256":{k:sha(v) for k,v in patched.items()},
       "original_action_ready_calls_added":0,
       "original_if_expr_success_calls_added":0,
       "source_IF_comparator_is_post_and_not_READY":True,
       "json2_original_emission_marker":EMITTER_MARK,
       "native_runtime_execution":"NOT_RUN",
       "wcl_api_calls":0}


def read_markers(log:str,profile:bytes,plan:dict,*,target:int)->dict:
    plan_check(plan)
    need(type(target) is int and target in (1,2,3,4,5,6,7,8),
         "TARGET_COUNT_REQUIRED")
    lists=parse_profile(profile,require_source=False)["action_lists"]
    captures={};native={};counter=Counter();source_seen=set()
    for ln in log.splitlines():
        if SEL in ln:
            need(ln.count(SEL)==1,"DUPLICATE_SOURCE_PRE_MARKER")
            payload=ln.split(SEL,1)[1].strip().split("|")
            need(len(payload)==7,"SOURCE_PRE_FIELD_COUNT")
            timestamp,id_s,owner,rank_s,ptr,rage_s,stack_s=payload
            need(timestamp.isdecimal() and id_s.isdecimal() and
                 rank_s.isdecimal() and
                 POINTER.fullmatch(ptr) is not None and
                 re.fullmatch(r"-?\d+",stack_s) is not None,
                 "ORIGINAL_SOURCE_PRE_LOG_FORMAT_INVALID")
            rowid=int(id_s);rank=int(rank_s)
            need(rowid>0 and rowid not in captures and
                 int(timestamp)>=0 and (rank==0 or owner in lists) and
                 math.isfinite(float(rage_s)),
                 "SOURCE_PRE_CALL_DUPLICATE_OR_UNPINNED")
            if rank:
                need(rank<=len(lists[owner]),"SOURCE_PRE_ROW_OUTSIDE_PINNED_PROFILE")
            captures[rowid]={
                "t_ms":int(timestamp),"root_id":rowid,
                "source_list":owner,"row_rank":rank,
                "original_action_pointer":ptr.lower(),
                "raw_resource":float(rage_s),"buff_stacks":int(stack_s)}
        if NATIVE in ln:
            need(ln.count(NATIVE)==1,"DUPLICATE_ORIGINAL_IF_MARKER")
            p=ln.split(NATIVE,1)[1].strip().split("|")
            need(len(p)==4 and p[0].isdecimal() and p[1].isdecimal() and
                 POINTER.fullmatch(p[2]) is not None and p[3] in ("0","1"),
                 "NATIVE_IF_MARKER_MALFORMED")
            key=(int(p[1]),p[2].lower())
            need(key not in native,"DUPLICATE_SAME_ROOT_OBJECT_IF")
            native[key]={"timestamp":int(p[0]),"value":int(p[3])}
    need(bool(captures),"NO_ACTUAL_ORIGINAL_SELECT_ROOT_PRE")
    results=[];total=Counter()
    allowed={plan["resource_symbol"],plan["buff_symbol"]}
    for id,pre in captures.items():
        owner=pre["source_list"];rank=pre["row_rank"]
        if rank==0:
            total["source_signature_unmapped"]+=1
            continue
        source=lists[owner][rank-1]
        attr=source["expression_fields"].get("if")
        symbols=set(attr["symbols"]) if attr else set()
        facts={plan["resource_symbol"]:pre["raw_resource"]}
        if pre["buff_stacks"]>=0:
            facts[plan["buff_symbol"]]=float(pre["buff_stacks"]>0)
        comparison=native.get((id,pre["original_action_pointer"]))
        if comparison:
            need(comparison["timestamp"]==pre["t_ms"],
                 "ROOT_IF_COMPARATOR_DIFFERENT_NATIVE_CALL_TIME")
        if attr is None:
            status="SOURCE_WITHOUT_EXPLICIT_IF_NOT_READY_PROOF"
            result=None
        else:
            # Reuse existing three-valued AST and only source-pinned PRE.
            value=evaluate_ast(attr["ast"],facts)
            result=truth(value)
            if result is None:
                status="UNKNOWN_MISSING_PRE_OPERAND"
            elif comparison is None:
                status="IF_AST_VALUE_KNOWN_BUT_NATIVE_IF_NOT_EVALUATED"
            else:
                need(result==bool(comparison["value"]),
                     "INDEPENDENT_PRE_AST_NATIVE_IF_CONFLICT")
                status="MATCH_ORIGINAL_SAME_ROOT_SOURCE_IF"
        total[status]+=1
        if pre["t_ms"]<10000:
            total["first_10s_"+status]+=1
        results.append({
            "t_ms":pre["t_ms"],"source_list":owner,"source_rank":rank,
            "source_row_sha256":source["source_sha256"],
            "source_action":source["action"],
            "source_if":None if attr is None else attr["source"],
            "source_IF_symbols":sorted(symbols),
            "unobserved_IF_symbols":sorted(symbols-set(facts)),
            "original_select_call_id":id,
            "original_action_pointer":pre["original_action_pointer"],
            "raw_source_resource":pre["raw_resource"],
            "raw_source_buff_stacks":pre["buff_stacks"],
            "independent_source_IF_AST":result,
            "original_native_if_comparator":None if comparison is None
                else bool(comparison["value"]),
            "if_scope_proof":status,
            "full_positive_READY":"UNKNOWN",
            "actual_JSON2_row_join":"NOT_PROVEN_FROM_SELECT_POINTER_ALONE",
            "dummy_error":"UNKNOWN"})
    for key,n in native.items():
        need(key[0] in captures,"NATIVE_IF_RESULT_WITHOUT_UNIQUE_CALL_SCOPE")
        # sync_action can be nested inside same scope with different ptr:
        if key[1]!=captures[key[0]]["original_action_pointer"]:
            total["nested_native_if_comparison_excluded"]+=1
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "plan":plan,"target_count":target,
        "original_simc_source_profile_git_blob":git_blob(profile),
        "original_select_PRE_calls":len(captures),
        "comparisons":dict(sorted(total.items())),
        "bounded_first_10sec_decision_examples":
            [x for x in results if x["t_ms"]<10000][:200],
        "all_rows_replayed":len(results),
        "exact_same_call_ID_and_object_comparison":True,
        "native_if_original_call_once":True,
        "source_IF_is_not_full_action_READY":True,
        "JSON2_emission_cast_alignment_proven":False,
        "full_ready_proven":0,"opener_end":"UNKNOWN",
        "WCL_holdout":"NOT_RUN","dummy_verdict":"UNKNOWN",
        "WCL_API_calls":0
    }


def selftest():
    plan={"schema":"ZrotOriginalSimCSourceIFPreSpecAdapterV1",
        "policy_id":POLICY,"source_revision":SIMC_COMMIT,
        "resource_enum":"RESOURCE_RAGE","resource_symbol":"rage",
        "buff_name":"recklessness","buff_symbol":"buff.recklessness.up",
        "class_cpp":"engine/class_modules/sc_warrior.cpp",
        "original_class_cpp_blob":"38ee3dd0d5943eb9227ec55aefb21e7d47244f96",
        "source_expected_buff_construction":'make_buff( this, "recklessness"',
        "approved_source_only_nongame_capture":True}
    # Offline symbolic test of C++ patch on source-synthetic method anchors:
    raw_player=('''#include "player.hpp"\n#include "action/action.hpp"\n'''+
        'void player_t::sequence_add( const action_t* a, const player_t* t )\n{\n'
        '  if ( !sim->collect_action_sequence )\n    return;\n'
        '    if ( collected_data.action_sequence.size() <= sim->expected_max_time() * 2.0 + 3.0 )\n'
        '    {\n      if ( a->is_precombat )\n      {\n'
        '        auto& data = collected_data.action_sequence_precombat.emplace_back( a, t, sim->current_time(), this );\n'
        '        a->sequence_add_fn( data.action_reporting, data.target_reporting );\n'
        '      }\n      else\n      {\n'
        '        auto& data = collected_data.action_sequence.emplace_back( a, t, sim->current_time(), this );\n'
        '        a->sequence_add_fn( data.action_reporting, data.target_reporting );\n'
        '      }\n    }\n}\n'
        'void player_t::precombat_init()\n{}\n'
        +CPP_START+'\n{\n    if ( a->action_ready() )\n{}\n'+CPP_END+'\n{}\n')
    raw_action=('#include "action/action.hpp"\n'+ACTION_START+'\n{\n'+
                EXACT_IF+'\n}\n'+ACTION_END+'\n{}\n')
    patched=patch_cpp(raw_player.encode(),raw_action.encode(),plan,enforce_pin=False)
    assert SEL in patched[PLAYER].decode() and EMITTER_MARK in patched[PLAYER].decode()
    assert NATIVE in patched[ACTION].decode()
    assert patched[ACTION].decode().count("if_expr->success()")==1
    assert patched[PLAYER].decode().count("a->action_ready()")==1
    profile=(b"actions=spell,if=buff.recklessness.up&rage>=80\n"
             b"actions+=/fallback\n")
    example=("ZROT_ORIGINAL_SELECT_IF_PRE_V1|100|21|default|1|0xabc|92|1\n"
             "ZROT_ORIGINAL_SELECT_NATIVE_IF_V1|100|21|0xabc|1\n"
             "ZROT_ORIGINAL_SELECT_IF_PRE_V1|120|22|default|1|0xabd|40|0\n"
             "ZROT_ORIGINAL_SELECT_NATIVE_IF_V1|120|22|0xabd|0\n")
    r=read_markers(example,profile,plan,target=1)
    assert r["comparisons"]["MATCH_ORIGINAL_SAME_ROOT_SOURCE_IF"]==2
    assert r["full_ready_proven"]==0
    wrong=example.replace("0xabd|0\n","0xabd|1\n")
    try:read_markers(wrong,profile,plan,target=1)
    except OriginalIFError:pass
    else:raise AssertionError("FALSE_NATIVE_IF_MATCH_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":20,"same_run_AST_and_native_IF_comparisons":2,
        "new_ready_calls":0,"WCL_API_calls":0}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root",type=Path)
    ap.add_argument("--plan",type=Path)
    ap.add_argument("--receipt",type=Path)
    ap.add_argument("--log",type=Path)
    ap.add_argument("--profile",type=Path)
    ap.add_argument("--target-count",type=int)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if all(v is None for v in vars(args).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    need(args.plan is not None,"PINNED_SPEC_ADAPTER_REQUIRED")
    plan=json.loads(args.plan.read_bytes())
    if args.source_root is not None:
        need(args.receipt is not None and not args.log and not args.profile,
             "SOURCE_PATCH_AND_REPLAY_MODES_SEPARATE")
        result=install(args.source_root,plan)
        args.receipt.parent.mkdir(parents=True,exist_ok=True)
        with args.receipt.open("xb") as f:f.write(canonical(result))
        print("SIMC_ORIGINAL_SELECT_IF_PRE_CPP_PATCH_SHA256="+
              sha(args.receipt.read_bytes()))
        return
    need(args.log and args.profile and args.target_count and args.out,
         "ORIGINAL_NATIVE_LOG_AND_PINNED_PROFILE_REQUIRED")
    result=read_markers(args.log.read_text(encoding="utf-8"),
                        args.profile.read_bytes(),plan,target=args.target_count)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("xb") as f:f.write(canonical(result))
    print("SIMC_ORIGINAL_SAME_CALL_IF_PRE_REPLAY_SHA256="+
          sha(args.out.read_bytes()))

if __name__=="__main__":
    main()
