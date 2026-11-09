#!/usr/bin/env python3
"""Generic original SimC foreground selection -> JSON2 recording callsite witness.

This deliberately distinguishes a causal *original C++ method-local dataflow*
from an actually executed WoW ability, physical READY or optimal priority.
The exact original player_t::execute_action local 'action' is passed first to
queue_execute and then to sequence_add. A unique passive dispatch token,
emitted on the method's original path, links that same local action with the
original JSON2 ordinal. Precombat/off-GCD/queue/strict-sequence remain separate.

No specialized spell/source action identity in the core. No new calls to
ready(), action_ready(), RNG, target state, SimC scheduling, or WoW APIs.
PyCharm with no script parameters: offline synthetic fail-closed tests only.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from simc_apl_semantic_ir_v2 import canonical, git_blob
from simc_native_select_trace_instrument_v1 import SIMC_COMMIT, PLAYER_CPP_BLOB
from general_rotation_same_run_return_emitter_v1 import (
    parse as parse_original_emitter,
    RETURN as OLD_RETURN, ACTOR as OLD_ACTOR,
    EMITTER_MARK, POLICY, LinkError,
)
from simc_original_select_if_pre_witness_v1 import SEL, NATIVE

SCHEMA="ZrotOriginalSimCForegroundSelectToEmissionCallsiteWitnessV1"
PATCH_SCHEMA="ZrotOriginalSimCForegroundDispatchCausalPatchV1"
BEGIN="ZROT_GR_FOREGROUND_APL_BEGIN_V1|"
SELECT="ZROT_GR_FOREGROUND_APL_RETURN_V1|"
CALLSITE="ZROT_GR_FOREGROUND_JSON2_CALLSITE_V1|"
EXEC="action_t* player_t::execute_action()\n{"
END="\nvoid player_t::regen( timespan_t periodicity )"
ROOT_LINE="    action = select_action( *active_action_list, execute_type::FOREGROUND );"
APPEND_BLOCK=("      if ( !is_add() && ( !is_pet() || collect_pet_sequence_data ) )\n"
              "        sequence_add( action, action->target );")
QUEUED_LINE="    action->queue_execute( execute_type::FOREGROUND );"
PTR=re.compile(r"0x[0-9a-fA-F]+\Z")


class DispatchError(ValueError):
    pass


def require(ok,reason):
    if not ok:
        raise DispatchError(reason)


def digest(x):
    return sha256(x).hexdigest()


def patch(player:bytes)->bytes:
    """Static anchored original method edit, after previous pinned producers."""
    source=player.decode("utf-8")
    require(OLD_ACTOR in source and OLD_RETURN in source and
            EMITTER_MARK in source and SEL in source and
            all(x not in source for x in (BEGIN,SELECT,CALLSITE)),
            "PINNED_ORIGINAL_SAME_RUN_PRODUCERS_REQUIRED")
    require(source.count(EXEC)==1 and source.count(END)==1,
            "OFFICIAL_EXECUTE_ACTION_FUNCTION_BOUNDARY_CHANGED")
    a=source.index(EXEC);b=source.index(END,a)
    method=source[a:b]
    require(method.count(ROOT_LINE)==1 and method.count(APPEND_BLOCK)==1
            and method.count(QUEUED_LINE)==1
            and method.count("sequence_add( action, action->target );")==1
            and method.count("action->queue_execute( execute_type::FOREGROUND );")==1,
            "ORIGINAL_FOREGROUND_SELECTED_QUEUE_JSON2_PATH_CHANGED")
    begin=r"""  // Only research instrumentation. Never changes native selection or queue.
  static std::atomic<std::uint64_t> zrot_foreground_serial{0};
  const std::uint64_t zrot_dispatch_id =
    (sim->log && !is_pet() && !is_enemy()) ?
    zrot_foreground_serial.fetch_add(1,std::memory_order_relaxed)+1 : 0;
  const char* zrot_route="NON_APL_FOREGROUND";
"""
    root=r"""    zrot_route="APL_ROOT";
    if ( zrot_dispatch_id )
      sim->print_log("ZROT_GR_FOREGROUND_APL_BEGIN_V1|{}|{}|{}",
        sim->current_time().total_millis(),zrot_dispatch_id,
        static_cast<const void*>(this));
    action = select_action( *active_action_list, execute_type::FOREGROUND );
    if ( action && zrot_dispatch_id )
      sim->print_log("ZROT_GR_FOREGROUND_APL_RETURN_V1|{}|{}|{}|{}",
        sim->current_time().total_millis(),zrot_dispatch_id,
        static_cast<const void*>(this),static_cast<const void*>(action));"""
    append=r"""      if ( !is_add() && ( !is_pet() || collect_pet_sequence_data ) )
      {
        if ( zrot_dispatch_id )
          sim->print_log("ZROT_GR_FOREGROUND_JSON2_CALLSITE_V1|{}|{}|{}|{}|{}|{}",
            sim->current_time().total_millis(),zrot_dispatch_id,zrot_route,
            static_cast<const void*>(this),static_cast<const void*>(action),
            collected_data.action_sequence.size());
        sequence_add( action, action->target );
      }"""
    method=method.replace(EXEC,EXEC+"\n"+begin,1)
    method=method.replace(ROOT_LINE,root,1)
    method=method.replace(APPEND_BLOCK,append,1)
    updated=source[:a]+method+source[b:]
    require(updated.count(BEGIN)==updated.count(SELECT)==
            updated.count(CALLSITE)==1
            and updated.count(OLD_ACTOR)==source.count(OLD_ACTOR)
            and updated.count(OLD_RETURN)==source.count(OLD_RETURN)
            and updated.count(EMITTER_MARK)==source.count(EMITTER_MARK)
            and updated.count(SEL)==source.count(SEL)
            and updated.count("a->action_ready()")==source.count("a->action_ready()")
            and updated.count("action->queue_execute( execute_type::FOREGROUND );")
               ==source.count("action->queue_execute( execute_type::FOREGROUND );")
            and updated.count("sequence_add( action, action->target );")
               ==source.count("sequence_add( action, action->target );"),
            "ORIGINAL_READY_QUEUE_APPEND_OR_EXISTING_MARKERS_MODIFIED")
    return updated.encode("utf-8")


def install(root:Path,prior:dict)->dict:
    root=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       check=True,capture_output=True,text=True).stdout.strip()
    require(rev==SIMC_COMMIT,"ORIGINAL_SIMC_SOURCE_REVISION_CHANGED")
    file=root/"engine/player/player.cpp"
    before=file.read_bytes()
    require(prior.get("schema")==
            "ZrotOriginalSameRunPassiveReturnEmitterPatchV1" and
            prior.get("source_revision")==SIMC_COMMIT and
            prior.get("source_blob_sha1")==PLAYER_CPP_BLOB and
            prior.get("patched_player_sha256")==digest(before) and
            prior.get("original_ready_calls_added")==0 and
            prior.get("original_emitter_appends_changed") is False,
            "PINNED_PARENT_SAME_RUN_INSTRUMENTATION_RECEIPT_INVALID")
    after=patch(before)
    file.write_bytes(after)
    return {"schema":PATCH_SCHEMA,"policy_id":POLICY,
            "original_source_revision":SIMC_COMMIT,
            "official_player_git_blob":PLAYER_CPP_BLOB,
            "original_parent_patched_sha256":digest(before),
            "foreground_patched_sha256":digest(after),
            "new_ready_or_RNG_or_queue_calls":0,
            "native_queue_and_JSON2_append_original_call_count_preserved":True,
            "causal_scope":"APL_FOREGROUND_ROOT_TO_SAME_METHOD_JSON2_CALLSITE_ONLY",
            "actual_queued_action_was_executed_proven":False,
            "original_action_READY_proven":0,"WCL_calls":0}


def _positive_int(raw):
    return raw.isdecimal() and int(raw)>0


def _pointer(raw):
    return isinstance(raw,str) and PTR.fullmatch(raw) is not None


def inspect_log(log:str)->dict:
    """Consume one original SimC log, never join unrelated runs or names."""
    try:
        _,emit=parse_original_emitter(log)
    except LinkError as e:
        raise DispatchError("PARENT_ORIGINAL_EMITTER_LOG_INVALID") from e
    events=log.splitlines()
    begin={};selected={};callsite={};native_if={};pre=[]
    for i,line in enumerate(events):
        for marker,kind in ((BEGIN,"begin"),(SELECT,"select"),
                            (CALLSITE,"site"),(SEL,"pre"),(NATIVE,"native")):
            if marker not in line:
                continue
            require(line.count(marker)==1,"DUPLICATE_NATIVE_MARKER_PREFIX")
            fields=line.split(marker,1)[1].strip().split("|")
            if kind=="begin":
                require(len(fields)==3 and fields[0].isdecimal() and
                        _positive_int(fields[1]) and _pointer(fields[2]),
                        "ORIGINAL_DISPATCH_BEGIN_MALFORMED")
                t,token,actor=fields;token=int(token)
                require(token not in begin,"REUSED_FOREGROUND_DISPATCH_TOKEN")
                begin[token]={"index":i,"t_ms":int(t),"actor":actor.lower()}
            elif kind=="select":
                require(len(fields)==4 and fields[0].isdecimal() and
                        _positive_int(fields[1]) and
                        _pointer(fields[2]) and _pointer(fields[3]),
                        "ORIGINAL_APL_RETURN_MALFORMED")
                t,token,actor,action=fields;token=int(token)
                require(token not in selected,"DUPLICATE_FOREGROUND_APL_RETURN")
                selected[token]={"index":i,"t_ms":int(t),
                                 "actor":actor.lower(),"action":action.lower()}
            elif kind=="site":
                require(len(fields)==6 and fields[0].isdecimal() and
                        _positive_int(fields[1]) and fields[2] in
                        ("APL_ROOT","NON_APL_FOREGROUND") and
                        _pointer(fields[3]) and _pointer(fields[4]) and
                        fields[5].isdecimal(),"ORIGINAL_CALLSITE_MALFORMED")
                t,token,route,actor,action,ordinal=fields;token=int(token)
                key=("C",int(ordinal))
                require(key not in callsite,"DUPLICATE_JSON2_FOREGROUND_CALLSITE")
                callsite[key]={"index":i,"t_ms":int(t),"token":token,
                               "route":route,"actor":actor.lower(),
                               "action":action.lower(),"ordinal":int(ordinal)}
            elif kind=="pre":
                require(len(fields)==7 and fields[0].isdecimal() and
                        _positive_int(fields[1]) and fields[3].isdecimal() and
                        _pointer(fields[4]),
                        "ORIGINAL_SELECT_SOURCE_PRE_MALFORMED")
                t,call_id,owner,rank,ptr,resource,buff=fields
                pre.append({"index":i,"t_ms":int(t),"id":int(call_id),
                            "owner":owner,"rank":int(rank),
                            "ptr":ptr.lower()})
            else:
                require(len(fields)==4 and fields[0].isdecimal() and
                        _positive_int(fields[1]) and _pointer(fields[2]) and
                        fields[3] in ("0","1"),
                        "ORIGINAL_NATIVE_IF_COMPARATOR_MALFORMED")
                t,id_,ptr,value=fields
                key=(int(id_),ptr.lower())
                require(key not in native_if,"DUPLICATE_NATIVE_IF_CALL_COMPARATOR")
                native_if[key]={"index":i,"t_ms":int(t),
                                "value":bool(int(value))}
    require(bool(begin) and bool(selected) and bool(callsite),
            "ORIGINAL_FOREGROUND_DISPATCH_MARKERS_ABSENT")
    require(set(selected).issubset(begin),"ROOT_SELECT_WITHOUT_BEGIN")
    require(len({x["token"] for x in callsite.values()})==len(callsite),
            "DISPATCH_TOKEN_APPEARS_AT_MULTIPLE_EMITTER_CALLS")
    by_key={("C",r["ordinal"]):r for r in emit if r["kind"]=="C"}
    require(set(callsite).issubset(by_key),
            "ORIGINAL_CALLSITE_WITHOUT_SAME_JSON2_EMITTER")
    counts=Counter();if_counts=Counter();sample=[];first_window=Counter()
    used_select=set()
    for record in emit:
        key=(record["kind"],record["ordinal"])
        site=callsite.get(key)
        status="UNKNOWN_NOT_ORIGINAL_FOREGROUND_EXECUTE_ACTION"
        if site is not None:
            token=site["token"];route=site["route"]
            require(record["kind"]=="C" and
                    record["actor"]==site["actor"] and
                    record["ptr"]==site["action"] and
                    record["t_ms"]==site["t_ms"] and
                    site["index"]<record["index"],
                    "ACTUAL_ORIGINAL_APPEND_AND_CALLSITE_IDENTITY_MISMATCH")
            if route=="NON_APL_FOREGROUND":
                require(token not in selected and token not in begin,
                        "NON_APL_FOREGROUND_FORGED_APL_ROOT")
                status="SOURCE_FOREGROUND_NON_APL_PATH_NOT_PRIORITY"
            else:
                root=selected.get(token);start=begin.get(token)
                require(root is not None and start is not None and
                        start["actor"]==root["actor"]==site["actor"] and
                        root["action"]==site["action"] and
                        start["index"]<root["index"]<site["index"] and
                        start["t_ms"]<=root["t_ms"]<=site["t_ms"],
                        "FOREIGN_SELECTED_ACTION_NOT_ORIGINAL_QUEUE_CALLSITE")
                used_select.add(token)
                status="ORIGINAL_APL_FOREGROUND_SELECT_TO_JSON2_CALLSITE_PROVEN"
                exact=[x for x in pre if
                       start["index"]<x["index"]<root["index"] and
                       x["ptr"]==site["action"] and
                       x["owner"]==record["owner"] and
                       x["rank"]==record["rank_one_based"]]
                if len(exact)==1:
                    gate=native_if.get((exact[0]["id"],exact[0]["ptr"]))
                    if gate is not None:
                        require(exact[0]["index"]<gate["index"]<
                                root["index"] and
                                exact[0]["t_ms"]==gate["t_ms"],
                                "NATIVE_IF_NOT_SAME_SELECTED_ACTION_READY_CALL")
                        if_counts["SELECTED_SAME_CALL_NATIVE_IF_COMPARATOR_ONLY"]+=1
                    else:
                        if_counts["SELECTED_SAME_CALL_PRE_NATIVE_IF_NOT_REACHED"]+=1
                elif exact:
                    if_counts["MULTIPLE_SOURCE_PRE_CALLS_SAME_SELECTED_ROW"]+=1
                else:
                    if_counts["UNKNOWN_SELECTED_SOURCE_PRE_CALL_NOT_UNIQUE"]+=1
        counts[status]+=1
        if record["kind"]=="C" and record["t_ms"]<10000:
            first_window[status]+=1
        if len(sample)<250:
            sample.append({
                "t_ms":record["t_ms"],"phase":record["kind"],
                "JSON2_ordinal":record["ordinal"],
                "source_APL_list":record["owner"],
                "source_APL_rank":record["rank_one_based"],
                "source_action":record["action_name"],
                "source_attribution":status,
                "original_selected_to_JSON2_callsite":
                    status=="ORIGINAL_APL_FOREGROUND_SELECT_TO_JSON2_CALLSITE_PROVEN",
                "actually_executed_spell_proven":False,
                "full_positive_READY":"UNKNOWN",
                "IF_necessary_condition_truth":"UNKNOWN",
                "competing_action_priority":"UNKNOWN",
                "dummy_player_error":"UNKNOWN",
            })
    require(len(used_select)==sum(
        counts.get("ORIGINAL_APL_FOREGROUND_SELECT_TO_JSON2_CALLSITE_PROVEN",0)
        for _ in (0,)) and
        sum(counts.values())==len(emit),
        "FOREIGN_DISPATCH_DOUBLE_ASSIGNED_OR_EMITTER_DISCARDED")
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "original_simc_revision":SIMC_COMMIT,
        "source_evidence_level":
            "PINNED_ACTUAL_CPP_FOREGROUND_APL_SELECT_TO_JSON2_CALLSITE",
        "emitter_total":len(emit),
        "dispatch_markers":{"begin":len(begin),"selected":len(selected),
                            "json2_callsite":len(callsite)},
        "path_counts":dict(sorted(counts.items())),
        "first_10s_emitter_counts":dict(sorted(first_window.items())),
        "original_selected_IF_witness_counts":dict(sorted(if_counts.items())),
        "sample":sample,
        "physical_action_execute_event_proven":False,
        "original_source_IF_independently_evaluated_here":False,
        "complete_source_physical_READY_proven":0,
        "competing_priority_rule_proven":False,
        "opener_end":"UNKNOWN","WCL_blind_holdout":"NOT_RUN",
        "dummy_player_mistake":"UNKNOWN",
        "simc_same_run_original_JSON2_emission_validated":True,
        "WCL_API_calls":0,
        "MAIN_promoted":False,
    }


def selftest():
    dummy=("  // "+OLD_ACTOR+"\n  // "+OLD_RETURN+"\n"
           "  // "+EMITTER_MARK+"\n  // "+SEL+"\n"
           +EXEC+"\n  assert(!readying);\n"
           "  action_t* action=nullptr;\n"
           "  else\n  {\n    visited_apls_=0;\n"+ROOT_LINE+"\n  }\n"
           "  if ( action )\n  {\n"+QUEUED_LINE+"\n"
           "    if ( !action->quiet )\n    {\n"+APPEND_BLOCK+
           "\n    }\n  }\n  return action;\n}\n"+END+"\n{}\n")
    changed=patch(dummy.encode()).decode()
    assert changed.count(BEGIN)==changed.count(SELECT)==changed.count(CALLSITE)==1
    assert changed.count("a->action_ready()")==0
    assert changed.count(QUEUED_LINE)==changed.count(APPEND_BLOCK.split("\n")[-1])==1
    good="\n".join((
      BEGIN+"100|1|0x11",
      SEL+"100|21|default|1|0xaa|92|1",
      NATIVE+"100|21|0xaa|1",
      OLD_RETURN+"100|DIRECT|0x11|default|default|1|0xaa|1",
      SELECT+"100|1|0x11|0xaa",
      CALLSITE+"100|1|APL_ROOT|0x11|0xaa|0",
      OLD_ACTOR+"100|C|0|0x11|0xaa",
      EMITTER_MARK+"100|C|0|synthetic|default|1|0xaa"
    ))
    result=inspect_log(good)
    assert result["path_counts"][
      "ORIGINAL_APL_FOREGROUND_SELECT_TO_JSON2_CALLSITE_PROVEN"]==1
    assert result["original_selected_IF_witness_counts"][
      "SELECTED_SAME_CALL_NATIVE_IF_COMPARATOR_ONLY"]==1
    assert result["complete_source_physical_READY_proven"]==0
    n=0
    for broken in (
        good.replace(SELECT+"100|1|0x11|0xaa",SELECT+"100|1|0x11|0xbb"),
        good.replace(CALLSITE+"100|1|APL_ROOT|0x11|0xaa|0",
                     CALLSITE+"100|1|APL_ROOT|0x12|0xaa|0"),
        good.replace(CALLSITE+"100|1|APL_ROOT|0x11|0xaa|0",
                     CALLSITE+"100|1|APL_ROOT|0x11|0xbb|0"),
        good.replace(CALLSITE+"100|1|APL_ROOT|0x11|0xaa|0",
                     CALLSITE+"100|2|APL_ROOT|0x11|0xaa|0"),
        good.replace(BEGIN+"100|1|0x11",""),
        good.replace(OLD_ACTOR+"100|C|0|0x11|0xaa",
                     OLD_ACTOR+"100|C|0|0x11|0xbb"),
        good.replace(OLD_RETURN+"100|DIRECT|0x11|default|default|1|0xaa|1",""),
        good.replace(NATIVE+"100|21|0xaa|1",NATIVE+"101|21|0xaa|1"),
    ):
        try:inspect_log(broken)
        except DispatchError:n+=1
        else:raise AssertionError("ORIGINAL_DISPATCH_FORGED_CAUSAL_PROOF")
    try:patch(changed.encode())
    except DispatchError:n+=1
    else:raise AssertionError("DUPLICATE_CPP_DISPATCH_PATCH_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "negative_controls":n,
            "same_method_source_patch":True,
            "source_selected_to_original_JSON2_callsite":True,
            "full_READY_proven":0,"new_CXX_builds":0,"WCL_API_calls":0}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--simc-root",type=Path)
    cli.add_argument("--prior-receipt",type=Path)
    cli.add_argument("--patch-receipt",type=Path)
    cli.add_argument("--log",type=Path)
    cli.add_argument("--out",type=Path)
    a=cli.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True))
        return
    if a.simc_root is not None:
        require(a.prior_receipt is not None and a.patch_receipt is not None and
                a.log is None and a.out is None,
                "EXPLICIT_PINNED_CPP_PATCH_MODE_REQUIRED")
        prior=json.loads(a.prior_receipt.read_bytes())
        result=install(a.simc_root,prior)
        a.patch_receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.patch_receipt.open("xb") as output:
            output.write(canonical(result))
        print("ORIGINAL_FOREGROUND_CPP_PATCH_SHA256="+
              digest(a.patch_receipt.read_bytes()))
    else:
        require(a.log is not None and a.out is not None and
                a.prior_receipt is None and a.patch_receipt is None,
                "EXPLICIT_NATIVE_LOG_REPLAY_MODE_REQUIRED")
        result=inspect_log(a.log.read_text("utf-8"))
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as output:output.write(canonical(result))
        print("ORIGINAL_FOREGROUND_DISPATCH_REPLAY_SHA256="+
              digest(a.out.read_bytes()))
        print("ORIGINAL_FOREGROUND_CAUSAL_JSON2_CALLS="+str(
            result["path_counts"].get(
                "ORIGINAL_APL_FOREGROUND_SELECT_TO_JSON2_CALLSITE_PROVEN",0)))


if __name__=="__main__":
    main()
