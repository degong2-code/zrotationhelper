#!/usr/bin/env python3
"""Same-run SimC source-return to JSON2-emitter provenance, fail-closed.

Generic, passive source instrumentation on a pinned original SimC tree.
A matching return and JSON2 emitter object proves a bounded *same-run
temporal identity witness*, NOT that the return caused the emission.
No source choice, IF, physical READY, full priority, or WoW player cast
is inferred from an object pointer alone.

Default/no-argument PyCharm execution: offline synthetic self-test only.
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
from simc_original_select_if_pre_witness_v1 import (
    CPP_START, CPP_END, PLAYER, HEADER, SEL, NATIVE,
    OriginalIFError, POLICY, EMITTER_MARK,
)
from general_rotation_native_sequence_row_replay_v1 import (
    parse_marker_log, compare_pristine,
)
from simc_native_json_sequence import extract_json_sequence

SCHEMA = "ZrotOriginalSameRunReturnToEmitterIdentityBoundaryV1"
PATCH_SCHEMA = "ZrotOriginalSameRunPassiveReturnEmitterPatchV1"
RETURN = "ZROT_GR_NATIVE_RETURN_ROW_V1|"
ACTOR = "ZROT_GR_EMITTER_ACTOR_V1|"
POINTER = re.compile(r"0x[0-9a-fA-F]+\Z")
SITES = {
    "DIRECT": "        return a;",
    "CHILD_PROPAGATED": "          return real_a;",
}


class LinkError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise LinkError(reason)


def sha(raw):
    return sha256(raw).hexdigest()


DEPTH = r"""
inline thread_local unsigned zrot_select_depth_v1 = 0;
struct zrot_select_depth_guard_v1 {
  zrot_select_depth_guard_v1() { ++zrot_select_depth_v1; }
  ~zrot_select_depth_guard_v1() { --zrot_select_depth_v1; }
  zrot_select_depth_guard_v1(const zrot_select_depth_guard_v1&) = delete;
  zrot_select_depth_guard_v1& operator=(const zrot_select_depth_guard_v1&) = delete;
};
"""

LAMBDA = r"""  zrot_original_select_if_v1::zrot_select_depth_guard_v1 zrot_select_scope;
  // Passive source-row identity at the actual original selection return.
  const auto zrot_return_row_witness = [this, &list](
      const action_t* chosen, const char* route) {
    if (!chosen || !sim->log || is_pet() || is_enemy()) return;
    unsigned rank=0;
    const char* owner="-";
    if (chosen->action_list && chosen->signature) {
      const auto& src=*chosen->action_list;
      for (std::size_t i=0;i<src.action_list.size();++i) {
        if (&(src.action_list[i])==chosen->signature) {
          rank=static_cast<unsigned>(i+1);
          owner=src.name_str.c_str();
          break;
        }
      }
    }
    sim->print_log(
      "ZROT_GR_NATIVE_RETURN_ROW_V1|{}|{}|{}|{}|{}|{}|{}|{}",
      sim->current_time().total_millis(), route,
      static_cast<const void*>(this), list.name_str, owner, rank,
      static_cast<const void*>(chosen),
      zrot_original_select_if_v1::zrot_select_depth_v1);
  };
"""

ACTOR_CXX = r"""        sim->print_log("ZROT_GR_EMITTER_ACTOR_V1|{}|{}|{}|{}|{}",
          sim->current_time().total_millis(),
          a->is_precombat ? "P" : "C",
          a->is_precombat ? collected_data.action_sequence_precombat.size()
                          : collected_data.action_sequence.size(),
          static_cast<const void*>(this), static_cast<const void*>(a));
"""


def patch(player: bytes, header: bytes) -> tuple[bytes, bytes]:
    source=player.decode("utf-8")
    h=header.decode("utf-8")
    require(SEL in source and EMITTER_MARK in source
            and NATIVE not in source and RETURN not in source and ACTOR not in source,
            "PREVIOUS_ORIGINAL_SAME_CALL_PRODUCER_REQUIRED")
    require(h.count("namespace zrot_original_select_if_v1 {")==1
            and "zrot_select_depth_v1" not in h,
            "PINNED_SOURCE_SCOPE_HEADER_REQUIRED")
    h=h.replace("namespace zrot_original_select_if_v1 {",
                "namespace zrot_original_select_if_v1 {\n"+DEPTH,1)
    require(source.count(CPP_START)==1 and source.count(CPP_END)==1,
            "ORIGINAL_SELECT_METHOD_BOUNDARY_DRIFT")
    i=source.index(CPP_START);j=source.index(CPP_END,i)
    method=source[i:j]
    require(method.count("\n{\n")==1 and method.count(SEL)==1
            and method.count("a->action_ready()")==1,
            "SOURCE_SELECT_ORIGINAL_CALL_COUNT_DRIFT")
    for name,line in SITES.items():
        require(method.splitlines().count(line)==1,
                "PINNED_RETURN_SITE_DRIFT:"+name)
        pointer="a" if name=="DIRECT" else "real_a"
        method=method.replace("\n"+line+"\n",
            "\n        zrot_return_row_witness("+pointer+', "'+name+'");\n'+line+"\n",1)
    method=method.replace("\n{\n","\n{\n"+LAMBDA,1)
    require(method.count(RETURN)==1 and method.count("a->action_ready()")==1,
            "SELECT_RETURN_PATCH_READY_OR_MARKER_DRIFT")
    source=source[:i]+method+source[j:]
    find='        sim->print_log(\n          "'+EMITTER_MARK
    require(source.count(find)==1,"ORIGINAL_JSON2_EMITTER_INSERTION_DRIFT")
    source=source.replace(find,ACTOR_CXX+find,1)
    require(source.count(EMITTER_MARK)==1 and source.count(ACTOR)==1
            and source.count(SEL)==1,
            "ORIGINAL_JSON2_EMITTER_OR_PRE_CHANGED")
    return source.encode("utf-8"),h.encode("utf-8")


def install(root:Path,prior:dict)->dict:
    root=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       capture_output=True,text=True,check=True).stdout.strip()
    require(rev==SIMC_COMMIT,"OFFICIAL_SIMC_REVISION_DRIFT")
    player=root/PLAYER;hdr=root/HEADER
    require(prior.get("source_revision")==SIMC_COMMIT
            and prior.get("official_player_git_blob")==PLAYER_CPP_BLOB
            and prior.get("original_action_ready_calls_added")==0
            and prior.get("original_if_expr_success_calls_added")==0
            and prior.get("json2_original_emission_marker")==EMITTER_MARK
            and prior.get("patch_sha256",{}).get(PLAYER)==sha(player.read_bytes())
            and prior.get("patch_sha256",{}).get(HEADER)==sha(hdr.read_bytes()),
            "PRIOR_SAME_CALL_PATCH_RECEIPT_REQUIRED")
    before=player.read_bytes();beforeh=hdr.read_bytes()
    after,afterh=patch(before,beforeh)
    player.write_bytes(after);hdr.write_bytes(afterh)
    return {"schema":PATCH_SCHEMA,"policy_id":POLICY,
            "source_revision":rev,"source_blob_sha1":PLAYER_CPP_BLOB,
            "prior_player_sha256":sha(before),"patched_player_sha256":sha(after),
            "prior_header_sha256":sha(beforeh),"patched_header_sha256":sha(afterh),
            "original_ready_calls_added":0,"original_emitter_appends_changed":False,
            "passive_return_marker":RETURN,"passive_emitter_actor_marker":ACTOR,
            "compile_and_actual_simc_execution":"NOT_RUN_BY_PATCHER",
            "full_ready_proven":0,"causal_schedule_token_proven":False}


def parse(log:str):
    returns=[];actors={};source_events={}
    source_events=parse_marker_log(log)  # existing exact JSON2 marker contract
    for n,line in enumerate(log.splitlines()):
        if RETURN in line:
            require(line.count(RETURN)==1,"DUPLICATE_RETURN_PREFIX")
            p=line.split(RETURN,1)[1].strip().split("|")
            require(len(p)==8,"RETURN_FIELD_COUNT")
            t,kind,actor,active_list,owner,rank,ptr,depth=p
            require(t.isdecimal() and kind in SITES and
                    POINTER.fullmatch(actor) and POINTER.fullmatch(ptr)
                    and rank.isdecimal() and depth.isdecimal() and
                    int(depth)>=1 and active_list and
                    ((int(rank)>0 and owner!="-") or
                     (int(rank)==0 and owner=="-")),
                    "RETURN_MARKER_INVALID")
            returns.append({"index":n,"t_ms":int(t),"kind":kind,
                            "actor":actor.lower(),"list":active_list,
                            "owner":owner,"rank":int(rank),
                            "ptr":ptr.lower(),"depth":int(depth)})
        if ACTOR in line:
            require(line.count(ACTOR)==1,"DUPLICATE_ACTOR_PREFIX")
            p=line.split(ACTOR,1)[1].strip().split("|")
            require(len(p)==5,"ACTOR_FIELD_COUNT")
            t,phase,ordinal,actor,ptr=p
            require(t.isdecimal() and phase in ("P","C") and
                    ordinal.isdecimal() and POINTER.fullmatch(actor)
                    and POINTER.fullmatch(ptr),"EMITTER_ACTOR_INVALID")
            key=(phase,int(ordinal))
            require(key not in actors,"DUPLICATE_EMITTER_ACTOR_KEY")
            actors[key]={"index":n,"t_ms":int(t),"actor":actor.lower(),
                         "ptr":ptr.lower()}
    require(bool(returns) and bool(actors),
            "ORIGINAL_NATIVE_RETURN_OR_EMITTER_ACTOR_MISSING")
    require(set(actors)==set(source_events),
            "ORIGINAL_JSON2_ACTOR_AND_SOURCE_ORDINAL_DISAGREE")
    emit=[]
    for key,source in source_events.items():
        actor=actors[key]
        require(actor["t_ms"]==source["t_ms"] and
                actor["ptr"]==source["ptr"] and
                actor["index"]<len(log.splitlines()),
                "EMISSION_ACTOR_POINTER_OR_TIMESTAMP_MISMATCH")
        emit.append({"key":key,**source,"actor":actor["actor"],
                     "index":actor["index"]})
    return returns,sorted(emit,key=lambda x:x["index"])


def evaluate(log:str)->dict:
    returns,emit=parse(log)
    by_pointer=defaultdict(list)
    for x in returns:
        by_pointer[(x["actor"],x["ptr"])].append(x)
    last_emission=defaultdict(lambda:-1)
    counts=Counter()
    examples=[]
    for m in emit:
        key=(m["actor"],m["ptr"])
        past=[r for r in by_pointer[key]
              if last_emission[key]<r["index"]<m["index"]
              and r["t_ms"]<=m["t_ms"]]
        last_emission[key]=m["index"]
        if m["rank_one_based"]==0:
            status="UNKNOWN_EMITTER_NO_SOURCE_SIGNATURE"
        else:
            roots=[r for r in past if r["depth"]==1]
            if not roots:
                status="UNKNOWN_NO_ROOT_RETURN_BEFORE_EMITTER"
            elif len(roots)!=1:
                status="UNKNOWN_MULTIPLE_ROOT_RETURNS"
            elif (roots[0]["owner"]!=m["owner"] or
                  roots[0]["rank"]!=m["rank_one_based"]):
                status="UNKNOWN_SOURCE_IDENTITY_MISMATCH"
            else:
                status="UNIQUE_SAME_RUN_RETURN_POINTER_ROW_TEMPORAL_WITNESS"
        counts[status]+=1
        if len(examples)<60:
            examples.append({"t_ms":m["t_ms"],"emitter_phase":m["kind"],
                "emitter_ordinal":m["ordinal"],"emitter_action":m["action_name"],
                "source_list":m["owner"],"source_row_rank":m["rank_one_based"],
                "matching_root_return_count":len([x for x in past if x["depth"]==1]),
                "identity_status":status,
                "source_if_at_selection":"UNKNOWN",
                "complete_readiness":"UNKNOWN",
                "causal_scheduling":"UNKNOWN",
                "dummy_mistake":"UNKNOWN"})
    return {"schema":SCHEMA,"policy_id":POLICY,
            "emitter_records":len(emit),"source_return_records":len(returns),
            "identity_counts":dict(sorted(counts.items())),
            "sample":examples,
            "evidence_level":"SAME_RUN_TEMPORAL_SOURCE_IDENTITY_ONLY",
            "selection_to_emission_causality_proven":False,
            "source_readiness_proven":0,"actual_woW_casts_proven":0,
            "opener_termination":"UNKNOWN","WCL_holdout":"NOT_RUN",
            "dummy_error":"UNKNOWN"}


def selftest():
    player=("void player_t::sequence_add( const action_t* a, const player_t* t )\n"
            "{\n  if ( !sim->collect_action_sequence )\n"
            "    return;\n        sim->print_log(\n          \""+EMITTER_MARK
            +"{}\",0);\n}\n"
            "void player_t::precombat_init()\n{}\n"
            +CPP_START+"\n execute_type et, const action_t* context )\n"
            "{\n  // "+SEL+"\n"
            "  if ( zrot_if_ready ) {}\n"
            "    if ( a->action_ready() ) {}\n"
            "        return a;\n          return real_a;\n}\n"
            +CPP_END+"\n{}\n")
    header="namespace zrot_original_select_if_v1 {\n}\n"
    changed,h=patch(player.encode(),header.encode())
    assert RETURN.encode() in changed and ACTOR.encode() in changed
    assert changed.count(b"a->action_ready()")==1
    assert b"zrot_select_depth_v1" in h
    good=(
        RETURN+"100|DIRECT|0x10|default|default|1|0xaa|1\n"
        +ACTOR+"110|C|0|0x10|0xaa\n"
        +EMITTER_MARK+"110|C|0|spell|default|1|0xaa\n")
    r=evaluate(good)
    assert r["identity_counts"].get(
        "UNIQUE_SAME_RUN_RETURN_POINTER_ROW_TEMPORAL_WITNESS")==1
    assert r["selection_to_emission_causality_proven"] is False
    duplicate=(RETURN+"101|DIRECT|0x10|default|default|1|0xaa|1\n"
               +good)
    assert evaluate(duplicate)["identity_counts"].get(
        "UNKNOWN_MULTIPLE_ROOT_RETURNS")==1
    after=(ACTOR+"90|C|0|0x10|0xaa\n"
           +EMITTER_MARK+"90|C|0|spell|default|1|0xaa\n"
           +RETURN+"100|DIRECT|0x10|default|default|1|0xaa|1\n")
    assert evaluate(after)["identity_counts"].get(
        "UNKNOWN_NO_ROOT_RETURN_BEFORE_EMITTER")==1
    nested=(RETURN+"100|DIRECT|0x10|child|default|1|0xaa|2\n"
            +ACTOR+"110|C|0|0x10|0xaa\n"
            +EMITTER_MARK+"110|C|0|spell|default|1|0xaa\n")
    assert evaluate(nested)["identity_counts"].get(
        "UNKNOWN_NO_ROOT_RETURN_BEFORE_EMITTER")==1
    bad=good.replace("110|C|0|0x10|0xaa","110|C|0|0x10|0xbb")
    try:evaluate(bad)
    except LinkError:pass
    else:raise AssertionError("CROSS_POINTER_EMITTER_ACCEPTED")
    try:patch(changed,h)
    except LinkError:pass
    else:raise AssertionError("DOUBLE_PATCH_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":22,"passive_cpp_patch":True,
            "negative_identity_controls":5,
            "full_ready_proven":0,"actual_simc_run":False,"WCL_API_calls":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--prior-receipt",type=Path)
    p.add_argument("--patch-receipt",type=Path)
    p.add_argument("--log",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any(vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    if a.source_root is not None:
        require(a.prior_receipt is not None and a.patch_receipt is not None
                and a.log is None,"EXPLICIT_PATCH_MODE_REQUIRED")
        prior=json.loads(a.prior_receipt.read_bytes())
        result=install(a.source_root,prior)
        a.patch_receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.patch_receipt.open("xb") as f:f.write(canonical(result))
        print("SAME_RUN_RETURN_EMITTER_PATCH_SHA256="+sha(a.patch_receipt.read_bytes()))
        return
    require(a.log is not None and a.out is not None,
            "EXPLICIT_REPLAY_MODE_REQUIRED")
    result=evaluate(a.log.read_text("utf-8"))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canonical(result))
    print("SAME_RUN_RETURN_EMITTER_REPLAY_SHA256="+sha(a.out.read_bytes()))


if __name__=="__main__":
    main()
