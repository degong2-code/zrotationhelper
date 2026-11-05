#!/usr/bin/env python3
"""Spec-neutral, source-pinned *passive* Original SELECT-PRE Native producer.

Generates one passive read-only marker block before the one original
player_t::select_action -> action_t::action_ready call. No native ready,
cost, target, sync, RNG, cooldown or class-ready method is called by patch.

This is a SELECT_ACTION_PRE snapshot, NOT source-method-entry PRE or an
independent action_ready proof. The source-pinned SpecAdapter declares which
already-audited operands to request; the emitter supports a small reviewed
catalog of general actor/action reads only. No arbitrary C++ expressions.

CLI with no arguments is PyCharm-safe offline selftest. The instrumented
SimC source is generated only from a pinned official pristine checkout.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
from pathlib import Path
import re
import subprocess

from general_rotation_source_route_audit_v1 import git_blob
from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_source_route_fixture_v1 import audit_both
from general_rotation_original_pre_capture_fixture_v1 import (
    declared_operands, warrior_route, mage_route
)
from general_rotation_original_pre_capture_engine_v1 import compile_template

SCHEMA = "ZrotGeneralRotationGenericSelectPREPassiveProducerV1"
MARK = "ZROT_GENERIC_SELECT_PRE_V1|"
PHASE = "SIMC_SELECT_ACTION_PRE"
REVISION = "b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
PLAYER = "engine/player/player.cpp"
PLAYER_BLOB = "88e03a01ca87ff66fd3902c9d6e047fe1a03ecb8"
START = "action_t* player_t::select_action( const action_priority_list_t& list,"
END = "\nplayer_t* player_t::actor_by_name_str"
CALL = "    if ( a->action_ready() )"
# Only expression recipes allowed; these are general action_t/player_t fields.
# Native function returns and behavioral decisions are deliberately absent.
READS = {
    "usable_while_casting":("bool", "( a->usable_while_casting ? 1 : 0 )"),
    "gcd_ready_ms":("int", "a->player->gcd_ready.total_millis()"),
    "player_is_moving":("bool", "( a->player->is_moving() ? 1 : 0 )"),
}


class PassiveProducerError(ValueError):
    pass


def sha(data:bytes)->str:
    return sha256(data).hexdigest()


def approved_shared_fields(source_audit_root:Path)->list[dict]:
    """Intersect existing independently source-audited class fixtures."""
    report = audit_both(source_audit_root)
    if report["pinned_source_commit"]!=REVISION:
        raise PassiveProducerError("SIMC_SOURCE_REVISION_NOT_PINNED")
    templates = [
        compile_template(report["audits"]["warrior_fury"],
                         declared_operands(warrior_route())),
        compile_template(report["audits"]["mage_arcane"],
                         declared_operands(mage_route())),
    ]
    shared={field["operand_name"]:field
            for field in templates[0]["fields"] if field["operand_name"] in READS}
    other={field["operand_name"]:field
           for field in templates[1]["fields"] if field["operand_name"] in READS}
    if set(shared)!=set(READS) or set(other)!=set(READS):
        raise PassiveProducerError("SHARED_GENERIC_SOURCE_PRE_FIELD_MISSING")
    fields=[]
    for name in sorted(READS):
        a,b=shared[name],other[name]
        if (a["field_id"]!=b["field_id"] or
            a["source_git_blob_sha1"]!=b["source_git_blob_sha1"] or
            a["source_method_body_sha256"]!=b["source_method_body_sha256"] or
            a["source_guard_fragment_sha256"]!=b["source_guard_fragment_sha256"] or
            a["value_kind"]!=READS[name][0]):
            raise PassiveProducerError("TWO_SPEC_SHARED_SOURCE_READ_DRIFT")
        fields.append({
            "field_id":a["field_id"],"operand_name":name,
            "kind":a["value_kind"],"guard_source_sha256":a["source_guard_fragment_sha256"],
            "source_node":a["source_node"],
            "source_git_blob_sha1":a["source_git_blob_sha1"],
            "actual_capture_phase":PHASE
        })
    return fields


def block(fields:list[dict])->str:
    if len(fields)!=len(READS) or len({x["field_id"] for x in fields})!=len(fields):
        raise PassiveProducerError("INCOMPLETE_SHARED_SOURCE_READS")
    lines=[
        "    // Passive original action-selection PRE reads. Never consume native",
        "    // readiness as a predicate; preserve its one original call below.",
        "    if ( sim->log && !is_pet() && !is_enemy() && a->action_list && a->signature )",
        "    {",
        "      const auto& zrot_capture_owner = *a->action_list;",
        "      for ( std::size_t zrot_capture_idx = 0;",
        "            zrot_capture_idx < zrot_capture_owner.action_list.size(); ++zrot_capture_idx )",
        "      {",
        "        if ( &( zrot_capture_owner.action_list[ zrot_capture_idx ] ) == a->signature )",
        "        {",
    ]
    seen=set()
    for item in fields:
        name=item["operand_name"]
        if name not in READS or name in seen:
            raise PassiveProducerError("SOURCE_EXPRESSION_NOT_IN_REVIEWED_CATALOG")
        seen.add(name)
        kind,expr=READS[name]
        if (kind!=item["kind"] or
            not re.fullmatch(r"[0-9a-f]{64}",item["field_id"]) or
            item["actual_capture_phase"]!=PHASE):
            raise PassiveProducerError("CAPTURE_FIELD_TYPE_OR_ID_DRIFT")
        # Fixed, manually audited expression catalog. Do not escape or
        # interpolate profile, character, dynamic field labels into C++.
        lines.extend([
            '          sim->print_log( "'+MARK+'{}|{}|{}|{}|'+
             item["field_id"]+'|'+kind+'|{}",',
            '            sim->current_time().total_millis(),',
            '            zrot_capture_owner.name_str,',
            '            static_cast<unsigned>( zrot_capture_idx + 1 ),',
            '            a->name_str, '+expr+' );'
        ])
    lines.extend([
        "          break;",
        "        }",
        "      }",
        "    }",
    ])
    return "\n".join(lines)+"\n"


def instrument(pristine:bytes,fields:list[dict],*,enforce_pin:bool=True)->bytes:
    if enforce_pin and git_blob(pristine)!=PLAYER_BLOB:
        raise PassiveProducerError("ORIGINAL_PLAYER_CPP_SOURCE_BLOB_DRIFT")
    text=pristine.decode("utf-8")
    if MARK in text or text.count(START)!=1 or text.count(END)!=1:
        raise PassiveProducerError("ALREADY_PATCHED_OR_SOURCE_FUNCTION_DRIFT")
    start=text.index(START)
    end=text.index(END,start)
    segment=text[start:end]
    if segment.count(CALL)!=1 or segment.count("a->action_ready()")!=1:
        raise PassiveProducerError("SOURCE_ORIGINAL_ACTION_READY_CALL_NOT_UNIQUE")
    changed=segment.replace(CALL,block(fields)+CALL,1)
    if (changed.count(CALL)!=1 or changed.count("a->action_ready()")!=1 or
        changed.count(MARK)!=len(fields) or
        changed.index(MARK)>changed.index(CALL)):
        raise PassiveProducerError("PATCH_CHANGED_ORIGINAL_NATIVE_READY_CALL")
    return (text[:start]+changed+text[end:]).encode("utf-8")


def generate(source_root:Path)->dict:
    root=source_root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       capture_output=True,check=True,text=True).stdout.strip()
    if rev!=REVISION:
        raise PassiveProducerError("SIMC_REVISION_NOT_OFFICIAL_PINNED")
    original=(root/PLAYER).read_bytes()
    fields=approved_shared_fields(root)
    output=instrument(original,fields)
    (root/PLAYER).write_bytes(output)
    return {
        "schema":SCHEMA,"source_revision":REVISION,
        "source_phase":PHASE,"field_count":len(fields),
        "fields":fields,"original_source_git_blob_sha1":git_blob(original),
        "original_source_sha256":sha(original),
        "instrumented_source_sha256":sha(output),
        "original_action_ready_call_count":1,
        "new_action_ready_calls":0,"new_RNG_or_target_selection_calls":0,
        "CXX_compiled":False,"native_behavior_nonperturbation":"NOT_TESTED",
        "positive_READY_proven":0,"WCL_API_calls":0,
    }


def selftest():
    marker=(
        START+"\n{\n  for ( action_t* a : a_list )\n  {\n"
        "    if ( a->action_ready() )\n      return a;\n"
        "  }\n  return nullptr;\n}\n"+END+"\n{}\n").encode()
    def sample(name,kind):
        return {"operand_name":name,"kind":kind,"field_id":sha(name.encode()),
                "actual_capture_phase":PHASE}
    fs=[sample(n,READS[n][0]) for n in sorted(READS)]
    patched=instrument(marker,fs,enforce_pin=False)
    t=patched.decode()
    assert t.count(MARK)==3
    assert t.count("a->action_ready()")==1
    assert t.index(MARK)<t.index(CALL)
    assert all(x["field_id"] in t for x in fs)
    for forged in (
        marker.replace(b"if ( a->action_ready() )",b"if ( a->ready() )"),
        marker.replace(b"if ( a->action_ready() )",
                       b"if ( a->action_ready() && a->action_ready() )"),
        patched
    ):
        try:instrument(forged,fs,enforce_pin=False)
        except PassiveProducerError:pass
        else:raise AssertionError("UNSAFE_GENERIC_SELECT_PRE_PATCH_ACCEPTED")
    for bad in (
        fs[:-1], fs+[fs[0]], [dict(fs[0],kind="bool")]+fs[1:],
        [dict(fs[0],field_id="x")]+fs[1:]
    ):
        # The type-alteration may leave a bool type unchanged; mutate an int.
        if bad!=fs:
            try:instrument(marker,bad,enforce_pin=False)
            except PassiveProducerError:pass
            else:raise AssertionError("INVALID_CAPTURE_FIELD_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":13,"capture_field_count":3,
        "actual_SimC_executed":False,"full_READY_proven":False,
        "WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--receipt",type=Path)
    args=p.parse_args()
    result=generate(args.simc_root) if args.simc_root else selftest()
    payload=canonical(result)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True,exist_ok=True)
        with args.receipt.open("xb") as f:f.write(payload)
    else:
        print(payload.decode(),end="")


if __name__=="__main__":
    main()
