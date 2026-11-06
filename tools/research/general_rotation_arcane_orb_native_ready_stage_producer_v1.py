#!/usr/bin/env python3
"""Original SimC Arcane Orb READY branch witness, passive and source pinned.

Instrument *existing returns*, never call a decision method twice. This
producer is intentionally a source-specific probe, NOT the Generic Engine
or a port of Hekili's in-client prediction engine.

Requires pinned upstream SimC C++ plus preceding exact original Native IF
bridge patch receipt. Original C++ source and the modified method's full
boolean return signatures are checked. Every original 'return true/false;'
is replaced by a SINGLE return expression which logs its original branch
tag and returns the same literal. A/B action parity is mandatory in CI.

Default (no CLI args): zero-network synthetic checks for safe PyCharm use.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_source_route_audit_v1 import _bounded_body,_source_code_mask,git_blob
from general_rotation_select_pre_passive_producer_v1 import REVISION
from general_rotation_original_root_if_bridge_v1 import SCHEMA as IF_SCHEMA, MARK as IF_MARK

SCHEMA="ZrotOriginalArcaneOrbNativeReadyStageWitnessProducerV1"
CPP_PATH="engine/action/action.cpp"
OFFICIAL_CPP_BLOB="399ecd9453b3f30bfc2ebf2b3ffd8f56cce8f8d4"
STAGE="ZROT_ORIGINAL_ARCANE_ORB_READY_STAGE_V1|"
PRE="ZROT_ORIGINAL_ARCANE_ORB_READY_PRE_V1|"
SIGNATURE_ACTION="bool action_t::action_ready()"
SIGNATURE_READY="bool action_t::ready()"
RETURN=re.compile(r"\breturn\s+(true|false)\s*;")

# Each ordinal labels the actual, source-ordered return. 'IF_FALSE' refers
# to the ORIGINAL if_expr->success() evaluation, NOT a second check.
READY_ROUTES=(
 ("false","BASE_COOLDOWN_NOT_READY"),
 ("false","BASE_INTERNAL_COOLDOWN_DOWN"),
 ("false","BASE_MOVING_NOT_USABLE"),
 ("false","BASE_RESOURCE_UNAFFORDABLE"),
 ("false","BASE_CAST_WHILE_CASTING_TIME"),
 ("false","BASE_CAST_WHILE_CASTING_GCD"),
 ("true","BASE_READY_TRUE"),
)
ACTION_ROUTES=(
 ("false","ACTION_BASE_READY_FALSE"),
 ("false","ACTION_TARGET_SELECTION_FALSE"),
 ("true","ACTION_CYCLE_TARGETS_SHORT_CIRCUIT_TRUE"),
 ("true","ACTION_RNG_FALSE_POSITIVE_TRUE"),
 ("false","ACTION_RNG_FALSE_NEGATIVE_FALSE"),
 ("false","ACTION_MOVEMENT_DIRECTION_FALSE"),
 ("false","ACTION_LINE_COOLDOWN_DOWN"),
 ("false","ACTION_SYNC_ACTION_FALSE"),
 ("false","ACTION_OPTION_MOVING_MISMATCH"),
 ("false","ACTION_APL_IF_FALSE"),
 ("false","ACTION_RECAST_BLOCKED"),
 ("true","ACTION_READY_TRUE"),
)

class ArcaneNativeGateError(ValueError):
    pass


def need(ok:bool,label:str)->None:
    if not ok:raise ArcaneNativeGateError(label)


def _region(src:str,signature:str)->tuple[str,int]:
    return _bounded_body(src,_source_code_mask(src),signature,(0,len(src)))


def _returns(body:str)->list[str]:
    return [m.group(1) for m in RETURN.finditer(body)]


def _source_gate_lambda(phase:str)->str:
    need(phase in ("BASE","ACTION"),"INVALID_CPP_METHOD_TRACE_PHASE")
    # The filter is *only* for this narrow source-physical-ability probe.
    # It does not alter the original result or insert RNG/cost/READY calls.
    return (
        "  const bool zrot_arcane_stage_enabled = sim->log && player &&\n"
        "    !player->is_pet() && !player->is_enemy() &&\n"
        "    name_str == \"arcane_orb\" &&\n"
        "    zrot_generic_call_scope_v1::current_root() != 0;\n"
        "  const auto zrot_arcane_stage_return = [&](const char* stage, bool value) -> bool {\n"
        "    if ( zrot_arcane_stage_enabled )\n"
        '      sim->print_log( "'+STAGE+'{}|{}|'+phase+'|{}|{}",\n'
        "        sim->current_time().total_millis(),\n"
        "        zrot_generic_call_scope_v1::current_root(), stage, value ? 1 : 0 );\n"
        "    return value;\n"
        "  };\n"
    )


PRE_FIELDS=(
 "sim->current_time().total_millis()",
 "zrot_generic_call_scope_v1::current_root()",
 "static_cast<double>( player->resources.current[ RESOURCE_MANA ] )",
 "static_cast<double>( player->resources.max[ RESOURCE_MANA ] )",
 "cooldown->current_charge",
 "cooldown->charges",
 "cooldown->ready.total_millis()",
 "internal_cooldown->ready.total_millis()",
 "line_cooldown->ready.total_millis()",
 "player->gcd_ready.total_millis()",
 "option.moving",
 "option.cycle_targets ? 1 : 0",
 "if_expr ? 1 : 0",
 "sync_action ? 1 : 0",
 "player->executing ? 1 : 0",
 "player->channeling ? 1 : 0",
)
PRE_SYMBOLS=(
 "simc_ms","original_CPP_ready_root_id",
 "mana_current","mana_max","cooldown_current_charge","cooldown_max_charges",
 "cooldown_ready_ms","internal_cooldown_ready_ms","line_cooldown_ready_ms",
 "player_gcd_ready_ms","option_moving","option_cycle_targets",
 "if_expr_present","sync_action_present","executing_present","channeling_present"
)


def _pre_log()->str:
    need(len(PRE_FIELDS)==len(PRE_SYMBOLS)==16,"RAW_READY_PRE_FIELDS_DRIFT")
    fmt="|".join(["{}","{}","{:.17g}","{:.17g}"]+["{}"]*12)
    return (
        "  if ( zrot_arcane_stage_enabled )\n"
        "    sim->print_log(\n"
        '      "'+PRE+fmt+'",\n'
        +"      "+",\n      ".join(PRE_FIELDS)+" );\n"
    )


def _add_stage_method(body:str,phase:str,expected:tuple)->str:
    old=_returns(body)
    need(old==[v for v,_ in expected],
         "ORIGINAL_CPP_RETURN_ORDINALS_CHANGED_"+phase+":"+str(old))
    need(body.startswith("{"),"ORIGINAL_CPP_METHOD_BRACES_MISSING")
    matches=list(RETURN.finditer(body))
    # Work backwards to preserve stable source offsets. The replaced
    # expression remains ONE C++ return statement, safe under unbraced if.
    for match,(literal,label) in reversed(list(zip(matches,expected))):
        before=body[:match.start()]
        after=body[match.end():]
        body=before+'return zrot_arcane_stage_return( "'+label+'", '+literal+' );'+after
    header=_source_gate_lambda(phase)
    if phase=="ACTION":
        header+=_pre_log()
    body="{\n"+header+body[1:]
    need(body.count(STAGE)==1 and
         (body.count(PRE)==1 if phase=="ACTION" else PRE not in body) and
         body.count("zrot_arcane_stage_return( ")==len(expected) and
         "rng().roll(" not in header and "cost_affordable(" not in header,
         "ADDITIONAL_ACTION_READY_OR_RNG_EVALUATION_DETECTED")
    return body


def patch(pristine:bytes,previous:bytes)->bytes:
    original=pristine.decode("utf8")
    current=previous.decode("utf8")
    need(git_blob(pristine)==OFFICIAL_CPP_BLOB,
         "UNPINNED_ORIGINAL_SIMC_ACTION_CPP_BLOB")
    need('#include "zrot_generic_call_scope_v1.hpp"' in current and
         IF_MARK in current and STAGE not in current and PRE not in current,
         "PRIOR_ORIGINAL_METHOD_IF_BRIDGE_REQUIRED")
    for phase,signature,expected in (
        ("BASE",SIGNATURE_READY,READY_ROUTES),
        ("ACTION",SIGNATURE_ACTION,ACTION_ROUTES)):
        official_region,_=_region(original,signature)
        old_region,start=_region(current,signature)
        need(_returns(official_region)==[v for v,_ in expected],
             "OFFICIAL_CPP_READY_RETURN_ORDER_DRIFT_"+phase)
        updated=_add_stage_method(old_region,phase,expected)
        current=current[:start]+updated+current[start+len(old_region):]
    need(current.count(STAGE)==2 and current.count(PRE)==1 and
         current.count(IF_MARK)==1 and
         current.count("if_expr->success()")==previous.decode("utf8").count("if_expr->success()") and
         current.count("rng().roll(")==previous.decode("utf8").count("rng().roll(") and
         current.count("cost_affordable()")==previous.decode("utf8").count("cost_affordable()") and
         current.count("action_ready()")==previous.decode("utf8").count("action_ready()"),
         "DUPLICATED_OR_MOVED_ORIGINAL_NATIVE_READY_RNG_IF_CALLS")
    return current.encode("utf8")


def generate(root:Path,prior_if_receipt:Path)->dict:
    root=root.resolve(strict=True)
    head=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    need(head==REVISION,"PINNED_ORIGINAL_SIMC_REVISION_REQUIRED")
    prior_bytes=prior_if_receipt.read_bytes()
    prior=json.loads(prior_bytes)
    need(prior.get("schema")==IF_SCHEMA and prior.get("source_revision")==REVISION and
         prior.get("official_action_blob_sha1")==OFFICIAL_CPP_BLOB and
         prior.get("original_native_if_expression_evaluations_per_callsite")==1 and
         prior.get("new_IF_ready_rng_target_calls")==0,
         "PINNED_EARLIER_ORIGINAL_IF_SOURCE_RECEIPT_REQUIRED")
    path=root/CPP_PATH
    original=subprocess.run(["git","-C",str(root),"show",
        f"{REVISION}:{CPP_PATH}"],check=True,capture_output=True).stdout
    current=path.read_bytes()
    need(sha256(current).hexdigest()==prior["source_after_sha256"],
         "CPP_SOURCE_NOT_IDENTICAL_TO_NATIVE_IF_RECEIPT")
    out=patch(original,current)
    path.write_bytes(out)
    return {
        "schema":SCHEMA,"source_revision":REVISION,
        "official_action_cpp_git_blob_sha1":OFFICIAL_CPP_BLOB,
        "original_action_source":CPP_PATH,
        "source_before_sha256":sha256(current).hexdigest(),
        "source_after_sha256":sha256(out).hexdigest(),
        "prior_IF_receipt_sha256":sha256(prior_bytes).hexdigest(),
        "stage_marker":STAGE,"source_root_PRE_marker":PRE,
        "raw_source_PRE_fields":list(PRE_SYMBOLS),
        "covered_source_methods":[SIGNATURE_READY,SIGNATURE_ACTION],
        "original_base_READY_return_branches":len(READY_ROUTES),
        "original_ACTION_READY_return_branches":len(ACTION_ROUTES),
        "new_ACTION_READY_calls":0,
        "new_RNG_calls":0,
        "new_cost_evaluations":0,
        "captured_original_branch_actual_return_not_independent_READY":True,
        "required_original_CPP_vs_patched_CPP_action_parity":"NOT_RUN",
        "full_independent_READY_proven":0,
        "WCL_API_calls":0,
    }


def selftest()->dict:
    base='{\n if (p) return false;\n return true;\n}'
    updated=_add_stage_method(base,"BASE",(
        ("false","TEST_FALSE"),("true","TEST_TRUE")))
    need("if (p) return zrot_arcane_stage_return( \"TEST_FALSE\", false );" in updated,
         "ORIGINAL_SINGLE_LINE_IF_SEMANTIC_CHANGED")
    need(updated.count("return zrot_arcane_stage_return(")==2,
         "DUPLICATE_RETURN_IN_SOURCE_FIXTURE")
    assert _pre_log().count(PRE)==1
    assert len(PRE_FIELDS)==len(PRE_SYMBOLS)==16
    for bad in (base.replace("false","true",1),
                base+"return false;",
                base.replace("return true;","return;")):
        try:_add_stage_method(bad,"BASE",(
            ("false","TEST_FALSE"),("true","TEST_TRUE")))
        except ArcaneNativeGateError:pass
        else:raise AssertionError("MODIFIED_NATIVE_READY_SOURCE_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":8,"actual_Native_CPP_executed":False,
        "independent_FULL_READY_proven":0,"WCL_API_calls":0,
    }


def main()->None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--simc-root",type=Path)
    ap.add_argument("--prior-original-IF-receipt",type=Path)
    ap.add_argument("--receipt",type=Path)
    args=ap.parse_args()
    if args.simc_root is None and args.prior_original_IF_receipt is None:
        result=selftest()
    elif args.simc_root is not None and args.prior_original_IF_receipt is not None:
        result=generate(args.simc_root,args.prior_original_IF_receipt)
    else:
        ap.error("original SimC checkout and prior original Native IF receipt required")
    data=canonical(result)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True,exist_ok=True)
        args.receipt.write_bytes(data)
    else:
        import sys
        sys.stdout.buffer.write(data)

if __name__=="__main__":
    main()
