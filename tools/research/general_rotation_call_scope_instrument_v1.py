#!/usr/bin/env python3
"""Generic strict original action_ready invocation stack trace instrumenter.

Stage 3, after the pinned generic SELECT-PRE and METHOD-PRE producers, adds
one globally unique per-call ID and RAII begin/end to the *existing* readiness
call (still exactly once). Nested method invocation IDs and parent IDs derive
from a thread-local synchronous call stack, never from timestamp equality.

A fresh, header-only C++ helper is generated in the temporary SimC checkout.
The generic patcher consumes typed source method sites, not any spec skill.
It preserves the previously emitted original METHOD-PRE value records, adding
call_id as an explicit final token to distinguish same-millisecond calls.

This instrumentation is research-only. It does not certify exhaustive
virtual dispatch, actual action READY or correct in-game user actions.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from general_rotation_source_route_audit_v1 import (
    _bounded_body, _class_scope, _source_code_mask
)
from general_rotation_method_pre_passive_producer_v1 import (
    _validate_plan, MARK as METHOD_MARK
)
from general_rotation_select_pre_passive_producer_v1 import (
    REVISION, PLAYER, START, END, CALL, MARK as SELECT_MARK
)
from general_rotation_original_pre_capture_engine_v1 import canonical

SCHEMA="ZrotGenericOriginalReadyCallScopeTraceProducerV1"
TRACE_MARK="ZROT_GENERIC_CALL_SCOPE_V1|"
SKIP_MARK="ZROT_GENERIC_SELECT_SKIP_V1|"
HEADER="engine/zrot_generic_call_scope_v1.hpp"
METHOD_PHASE="SIMC_ORIGINAL_METHOD_PRE"
SOURCE_PHASE="SIMC_SELECT_ACTION_PRE"

# This header introduces no SimC decision logic. It only owns identity and
# stack restoration. One atomic counter supplies IDs unique across compiler
# translation units and across concurrent SimC worker threads.
CPP_HEADER = r"""#pragma once
#include <atomic>
#include <cstdint>
#include <type_traits>
#include <utility>
namespace zrot_generic_call_scope_v1 {
struct stack_context {
  std::uint64_t active = 0;
  std::uint64_t root = 0;
};
inline thread_local stack_context context{};
inline std::atomic<std::uint64_t> next_id{0};
inline std::uint64_t active_id() noexcept { return context.active; }
inline std::uint64_t current_root() noexcept { return context.root; }
template<class Callback> class scope {
  Callback callback_;
  bool enabled_ = false;
  std::uint64_t previous_active_ = 0, previous_root_ = 0;
  std::uint64_t id_ = 0, parent_ = 0, root_ = 0;
 public:
  scope(bool enabled, bool selection, Callback callback)
    : callback_(std::move(callback)), enabled_(enabled) {
    if (enabled_) {
      previous_active_ = context.active;
      previous_root_ = context.root;
      id_ = next_id.fetch_add(1, std::memory_order_relaxed) + 1;
      parent_ = previous_active_;
      root_ = selection ? id_ : previous_root_;
      context.active = id_;
      if (selection) context.root = id_;
      callback_("BEGIN", id_, parent_, root_);
    }
  }
  scope(const scope&) = delete;
  scope& operator=(const scope&) = delete;
  ~scope() {
    if (enabled_) {
      callback_("END", id_, parent_, root_);
      context.active = previous_active_;
      context.root = previous_root_;
    }
  }
};
template<class Callback>
auto make_scope(bool enabled, bool selection, Callback&& callback) {
  return scope<std::decay_t<Callback>>(
    enabled, selection, std::forward<Callback>(callback));
}
}
"""


class CallScopeError(ValueError):
    pass


def _sh(data:bytes)->str:
    return sha256(data).hexdigest()


def _add_header_include(data:bytes)->bytes:
    source=data.decode("utf-8")
    include='#include "zrot_generic_call_scope_v1.hpp"\n'
    if include in source:
        raise CallScopeError("SOURCE_ALREADY_HAS_CALL_SCOPE")
    i=source.find("#include ")
    if i<0:
        raise CallScopeError("SIMC_CPP_INCLUDE_ANCHOR_MISSING")
    return (source[:i]+include+source[i:]).encode("utf-8")


def _selector_scope(original:bytes)->bytes:
    src=original.decode("utf-8")
    if src.count(START)!=1 or src.count(END)!=1 or src.count(CALL)!=1:
        raise CallScopeError("ORIGINAL_NATIVE_SELECT_CALL_DRIFT")
    start=src.index(START)
    end=src.index(END,start)
    body=src[start:end]
    if body.count(SELECT_MARK)<3 or body.count("a->action_ready()")!=1:
        raise CallScopeError("SELECT_PRE_SOURCE_PRODUCER_NOT_APPLIED")
    replacement=r"""    if ( ([&]() -> bool {
      const auto* zrot_scope_owner = a->action_list;
      std::size_t zrot_scope_ordinal = 0;
      if ( zrot_scope_owner && a->signature )
      {
        for ( std::size_t zrot_scope_idx = 0;
              zrot_scope_idx < zrot_scope_owner->action_list.size();
              ++zrot_scope_idx )
        {
          if ( &( zrot_scope_owner->action_list[ zrot_scope_idx ] ) == a->signature )
          {
            zrot_scope_ordinal = zrot_scope_idx + 1;
            break;
          }
        }
      }
      auto zrot_scope_root = zrot_generic_call_scope_v1::make_scope(
        sim->log && !is_pet() && !is_enemy() && zrot_scope_ordinal != 0,
        true,
        [&](const char* zrot_event, std::uint64_t zrot_id,
            std::uint64_t zrot_parent, std::uint64_t zrot_root) {
          sim->print_log( "ZROT_GENERIC_CALL_SCOPE_V1|{}|{}|SELECT|{}|{}|{}|select_call|{}|{}|{}",
            sim->current_time().total_millis(), zrot_event,
            zrot_id, zrot_parent, zrot_root,
            zrot_scope_owner->name_str, zrot_scope_ordinal, a->name_str );
        } );
      return a->action_ready();
    })() )"""
    source_skip='    if ( a->background )\n      continue;'
    if body.count(source_skip)!=1 or SKIP_MARK in body:
        raise CallScopeError("ORIGINAL_BACKGROUND_SKIP_SOURCE_BRANCH_DRIFT")
    background_skip=r"""    if ( a->background )
    {
      // Source loop excluded this action before readiness evaluation.
      if ( sim->log && !is_pet() && !is_enemy() &&
           a->action_list && a->signature )
      {
        const auto& zrot_skip_owner = *a->action_list;
        for ( std::size_t zrot_skip_index = 0;
              zrot_skip_index < zrot_skip_owner.action_list.size();
              ++zrot_skip_index )
        {
          if ( &( zrot_skip_owner.action_list[ zrot_skip_index ] ) == a->signature )
          {
            sim->print_log( "ZROT_GENERIC_SELECT_SKIP_V1|{}|{}|{}|{}|BACKGROUND",
              sim->current_time().total_millis(),zrot_skip_owner.name_str,
              static_cast<unsigned>( zrot_skip_index + 1 ),a->name_str );
            break;
          }
        }
      }
      continue;
    }"""
    body=body.replace(source_skip,background_skip,1)
    new=body.replace(CALL,replacement,1)
    if (new.count("a->action_ready()")!=1 or new.count(TRACE_MARK)!=1 or
        new.count(SKIP_MARK)!=1 or
        new.count(SELECT_MARK)!=body.count(SELECT_MARK)):
        raise CallScopeError("ORIGINAL_READINESS_OR_BACKGROUND_SKIP_DRIFT")
    return (src[:start]+new+src[end:]).encode("utf-8")


def _method_scope(site:dict)->str:
    key=site["method_key"]
    if not re.fullmatch(r"[a-z][a-z0-9_]*",key):
        raise CallScopeError("UNSAFE_SOURCE_METHOD_SITE_KEY")
    return r"""
    const auto* zrot_method_scope_owner = this->action_list;
    std::size_t zrot_method_scope_ordinal = 0;
    if ( zrot_generic_call_scope_v1::current_root() != 0 &&
         zrot_method_scope_owner && this->signature )
    {
      for ( std::size_t zrot_scope_idx = 0;
            zrot_scope_idx < zrot_method_scope_owner->action_list.size();
            ++zrot_scope_idx )
      {
        if ( &( zrot_method_scope_owner->action_list[ zrot_scope_idx ] ) == this->signature )
        {
          zrot_method_scope_ordinal = zrot_scope_idx + 1;
          break;
        }
      }
    }
    auto zrot_method_scope = zrot_generic_call_scope_v1::make_scope(
      this->sim->log && zrot_generic_call_scope_v1::current_root() != 0 &&
      this->player && !this->player->is_pet() && !this->player->is_enemy() &&
      zrot_method_scope_ordinal != 0,
      false,
      [&](const char* zrot_event, std::uint64_t zrot_id,
          std::uint64_t zrot_parent, std::uint64_t zrot_root) {
        this->sim->print_log( "ZROT_GENERIC_CALL_SCOPE_V1|{}|{}|METHOD|{}|{}|{}|""" + key + r"""|{}|{}|{}",
          this->sim->current_time().total_millis(), zrot_event,
          zrot_id, zrot_parent, zrot_root,
          zrot_method_scope_owner->name_str, zrot_method_scope_ordinal, this->name_str );
      } );
"""


def _append_method_call_ids(source:str, expected:int)->str:
    """Explicitly label every existing PRE field with the *current method ID*."""
    offset=0
    count=0
    while True:
        i=source.find(METHOD_MARK,offset)
        if i<0:
            break
        q=source.find('"',i)
        if q<0:
            raise CallScopeError("METHOD_PRE_FORMAT_STRING_MISSING")
        end=source.find(");",q)
        if end<0 or end-q>900:
            raise CallScopeError("METHOD_PRE_PRINT_STATEMENT_UNBOUNDED")
        # Only pre-existing generated print-log statements are accepted.
        prefix=source[max(0,i-38):i]
        if "print_log" not in prefix:
            raise CallScopeError("METHOD_PRE_MARKER_NOT_IN_GENERATED_LOG")
        # Append one safely generated format placeholder and one integer arg.
        source=source[:q]+'|{}'+source[q:end].rstrip() + (
            ', zrot_generic_call_scope_v1::active_id() ')+source[end:]
        count+=1
        offset=q+4
    if count!=expected:
        raise CallScopeError("METHOD_PRE_FIELD_TOKENIZATION_COUNT_DRIFT")
    return source


def instrument_sources(pristine_patched:dict[str,bytes],manifest:dict,
                       select_receipt:dict,method_receipt:dict)->dict[str,bytes]:
    sites=_validate_plan(manifest)
    required={PLAYER}|{x["source_path"] for x in sites}
    if set(pristine_patched)!=required:
        raise CallScopeError("GENERIC_TRACE_SOURCE_FILE_SET_MISMATCH")
    if (select_receipt.get("source_revision")!=REVISION or
        select_receipt.get("source_phase")!=SOURCE_PHASE or
        select_receipt.get("original_action_ready_call_count")!=1 or
        select_receipt.get("new_action_ready_calls")!=0 or
        method_receipt.get("source_revision")!=REVISION or
        method_receipt.get("source_phase")!=METHOD_PHASE or
        method_receipt.get("source_method_count")!=len(sites) or
        set(method_receipt.get("source_method_sites",[]))!=
            {x["method_key"] for x in sites}):
        raise CallScopeError("SOURCE_PINNED_PRE_PRODUCER_RECEIPTS_REQUIRED")
    documented={x["path"]:x["modified_sha256"] for x in method_receipt["source_files"]}
    documented[PLAYER]=select_receipt["instrumented_source_sha256"]
    for path,data in pristine_patched.items():
        if documented.get(path)!=_sh(data):
            raise CallScopeError("PREVIOUS_PRODUCER_BYTES_DRIFT:"+path)
    augmented={}
    for path,raw in pristine_patched.items():
        # Add the trace scope *before* any original PRE value reads.
        if path==PLAYER:
            updated=_selector_scope(raw)
        else:
            updated=raw
        text=updated.decode("utf-8")
        if path!=PLAYER:
            lexical=_source_code_mask(text)
            injections=[]
            for site in sites:
                if site["source_path"]!=path:
                    continue
                scope=_class_scope(text,lexical,site["class_anchor"])
                body,opening=_bounded_body(text,lexical,site["signature"],scope)
                label=(METHOD_MARK+"{}|{}|{}|{}|"+site["method_key"]+"|ENTRY")
                if body.count(label)!=1:
                    raise CallScopeError("AUDITED_METHOD_PRE_ENTRY_NOT_UNIQUE:"+site["method_key"])
                injections.append((opening,_method_scope(site)))
            if len(set(p for p,_ in injections))!=len(injections):
                raise CallScopeError("DUPLICATE_CXX_TRACE_METHOD_ENTRY")
            for pos,content in sorted(injections,reverse=True):
                text=text[:pos+1]+content+text[pos+1:]
            expected=sum(1+len(site["fields"]) for site in sites if site["source_path"]==path)
            text=_append_method_call_ids(text,expected)
            updated=text.encode("utf-8")
        augmented[path]=_add_header_include(updated)
    return augmented


def generate(source_root:Path,manifest_path:Path,
             select_receipt_path:Path,method_receipt_path:Path)->dict:
    root=source_root.resolve(strict=True)
    revision=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                            capture_output=True,text=True,check=True).stdout.strip()
    if revision!=REVISION:
        raise CallScopeError("OFFICIAL_SIMC_SOURCE_REVISION_CHANGED")
    manifest=json.loads(manifest_path.read_bytes())
    source_select=json.loads(select_receipt_path.read_bytes())
    source_methods=json.loads(method_receipt_path.read_bytes())
    sites=_validate_plan(manifest)
    paths={PLAYER}|{s["source_path"] for s in sites}
    before={path:(root/path).read_bytes() for path in paths}
    out=instrument_sources(before,manifest,source_select,source_methods)
    new_header=root/HEADER
    if new_header.exists():
        raise CallScopeError("GENERIC_TRACE_HEADER_ALREADY_EXISTS")
    new_header.write_text(CPP_HEADER,encoding="utf8")
    for path,data in out.items():
        (root/path).write_bytes(data)
    return {
        "schema":SCHEMA,"source_revision":REVISION,
        "trace_marker":TRACE_MARK,
        "source_select_skip_marker":SKIP_MARK,
        "source_select_skip_contract":"ORIGINAL_BACKGROUND_BRANCH_BEFORE_ACTION_READY",
        "method_PRE_marker_call_id_appended":True,
        "header_source_sha256":_sh(CPP_HEADER.encode()),
        "source_method_count":len(sites),
        "original_action_ready_call_count":1,
        "new_action_ready_calls":0,
        "new_original_rng_target_sync_calls":0,
        "trace_scope_strategy":"THREAD_LOCAL_PARENT_STACK_GLOBAL_ATOMIC_IDS_RAII",
        "source_files":[{"path":p,"before_sha256":_sh(before[p]),
                         "after_sha256":_sh(out[p])} for p in sorted(paths)],
        "native_cxx_compiled":False,"behavior_A_B_proven":False,
        "complete_virtual_dispatch":False,"positive_READY_certified":0,
        "WCL_API_calls":0
    }


def selftest()->dict:
    # Verify exact call count and receipt hashes against synthetic C++.
    source=(START+"\n{\n  // select\n"+SELECT_MARK+"{}|{}\n"+
            "    if ( a->background )\n      continue;\n"+
            "    if ( a->action_ready() )\n  {}\n}\n"+END+"\n").encode()
    # source has deliberately insufficient 3 original SELECT markers.
    try:_selector_scope(source)
    except CallScopeError:pass
    else:raise AssertionError("UNPINNED_SELECTION_PRE_PATCH_ACCEPTED")
    source=source.decode("utf-8").replace(SELECT_MARK+"{}|{}",
        "\n".join((SELECT_MARK+"{}|{}") for _ in range(3))).encode("utf-8")
    patched=_selector_scope(source)
    assert patched.decode().count("a->action_ready()")==1
    assert "make_scope" in patched.decode()
    assert patched.decode().count(TRACE_MARK)==1
    assert patched.decode().count(SKIP_MARK)==1
    assert patched.decode().count("if ( a->background )")==1
    assert patched.decode().count("continue;")==1
    method=(r'this->sim->print_log( "'+METHOD_MARK+
            r'{}|{}|{}|{}|base_ready|ENTRY|-|-|-",'+
            "\n            this->name_str );\n")
    rewritten=_append_method_call_ids(method,1)
    assert "active_id()" in rewritten
    assert METHOD_MARK+"{}|{}|{}|{}|base_ready|ENTRY|-|-|-|{}" in rewritten
    assert "namespace zrot_generic_call_scope_v1" in CPP_HEADER
    assert "inline thread_local" in CPP_HEADER
    assert "return a->action_ready();" in patched.decode()
    for bad in (method+method, "METHOD_ENTRY_FABRICATED"):
        try:_append_method_call_ids(bad,1)
        except CallScopeError:pass
        else:raise AssertionError("AMBIGUOUS_METHOD_CALL_ID_PATCH_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":11,"original_ready_call_preserved":True,
        "actual_Native_CXX_compiled":False,"positive_READY_certified":0,
        "WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--source-templates",type=Path)
    p.add_argument("--select-pre-receipt",type=Path)
    p.add_argument("--method-pre-receipt",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    needed=(a.simc_root,a.source_templates,
            a.select_pre_receipt,a.method_pre_receipt)
    if all(x is None for x in needed):
        receipt=selftest()
    elif all(x is not None for x in needed):
        receipt=generate(*needed)
    else:
        p.error("all four source/manifest/producer receipt inputs are required")
    payload=canonical(receipt)
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as handle:handle.write(payload)
    else:
        print(payload.decode(),end="")


if __name__=="__main__":
    main()
