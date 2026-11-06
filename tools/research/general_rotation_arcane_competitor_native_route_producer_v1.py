#!/usr/bin/env python3
"""Source-locked passive Native C++ READY-branch witness for three Arcane rivals.

Original 2026-11-06 SimC source ONLY, external to WoW's 2026 addon API.
Extends *existing* original action_t ready/action_ready branch-return wrappers
with a competitor-only logging wrapper. Adds original Mage prismatic_bolt_t
and arcane_missiles_t ready() return-path logs and read-only PRE buff checks.

No new action_ready, ready, RNG, cost or target-selection invocations.
Each original inherited/base ready() delegates once. Exact A/B original vs
instrumented executable action-sequence parity is an acceptance condition.

No CLI flags: synthetic source-shape checks, safe for PyCharm.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_source_route_audit_v1 import git_blob
from general_rotation_arcane_orb_native_ready_stage_producer_v1 import (
    _region, READY_ROUTES,ACTION_ROUTES,STAGE as ORB_STAGE,REVISION,
    SCHEMA as ORB_PRODUCER,
)
from general_rotation_arcane_orb_spec_state_pre_producer_v1 import (
    SCHEMA as ORB_SPEC_PRODUCER, ORIGINAL_CPP_BLOB as MAGE_BLOB,
)

SCHEMA="ZrotOriginalArcaneRivalNativeCXXReturnSourceProducerV1"
ACTION_CPP="engine/action/action.cpp"
MAGE_CPP="engine/class_modules/sc_mage.cpp"
ACTION_BLOB="399ecd9453b3f30bfc2ebf2b3ffd8f56cce8f8d4"
MARK_ACTION="ZROT_ARCANE_RIVALS_ORIGINAL_ACTION_RETURN_V1|"
MARK_CLASS="ZROT_ARCANE_RIVALS_ORIGINAL_CLASS_RETURN_V1|"
MARK_PRE="ZROT_ARCANE_RIVALS_ORIGINAL_CLASS_PRE_V1|"
RIVALS=("prismatic_bolt","arcane_barrage","arcane_missiles")
CLASS_NAMES={"prismatic_bolt":"prismatic_bolt_t","arcane_missiles":"arcane_missiles_t"}
STARTS={
 "prismatic_bolt":("struct prismatic_bolt_t final : public arcane_mage_spell_t",
                   "struct arcane_explosion_t final : public arcane_mage_spell_t"),
 "arcane_missiles":("struct arcane_missiles_t final : public custom_state_spell_t<arcane_mage_spell_t, am_data_t>",
                   "struct arcane_blast_t final"),
}

class RivalRouteProducerError(ValueError):pass

def need(c:bool,s:str)->None:
    if not c:raise RivalRouteProducerError(s)

def _method_header(phase:str)->str:
    need(phase in ("BASE","ACTION"),"RIVAL_SOURCE_PHASE_INVALID")
    return (
        "  const bool zrot_rival_enabled = sim->log && player &&\n"
        "      !player->is_pet() && !player->is_enemy() &&\n"
        "      ( name_str == \"prismatic_bolt\" ||\n"
        "        name_str == \"arcane_barrage\" ||\n"
        "        name_str == \"arcane_missiles\" ) &&\n"
        "      zrot_generic_call_scope_v1::current_root() != 0;\n"
        "  const auto zrot_rival_return = [&]( const char* why, bool result ) -> bool {\n"
        "    if ( zrot_rival_enabled )\n"
        '      sim->print_log( "'+MARK_ACTION+'{}|{}|'+phase+'|{}|{}",\n'
        "        sim->current_time().total_millis(),\n"
        "        zrot_generic_call_scope_v1::current_root(), why, result ? 1 : 0 );\n"
        "    return result;\n"
        "  };\n"
    )

def _patch_shared_method(body:str,phase:str,expected:tuple)->str:
    need(body.startswith("{") and
         MARK_ACTION not in body and ORB_STAGE in body and
         body.count("zrot_arcane_stage_return( ")==len(expected),
         "PRIOR_ORB_NATIVE_STAGE_METHOD_REQUIRED_"+phase)
    for literal,label in expected:
        old='return zrot_arcane_stage_return( "'+label+'", '+literal+' );'
        new='return zrot_rival_return( "'+label+'", zrot_arcane_stage_return( "'+label+'", '+literal+' ) );'
        need(body.count(old)==1,
             "ORIGINAL_RETURN_SOURCE_ROUTE_NOT_ONE_"+phase+"_"+label)
        body=body.replace(old,new)
    body="{\n"+_method_header(phase)+body[1:]
    need(body.count(MARK_ACTION)==1 and
         body.count("return zrot_rival_return( ")==len(expected) and
         body.count("zrot_arcane_stage_return( ")==len(expected) and
         body.count(ORB_STAGE)==1,
         "ORIGINAL_ACTION_NATIVE_RETURN_WRAPPER_MULTIPLICITY_DRIFT")
    return body

def _source_class_range(source:str,who:str)->tuple[str,int,int]:
    start_token,end_token=STARTS[who]
    start=source.find(start_token)
    end=source.find(end_token,start+len(start_token))
    need(start>=0 and end>start and
         source.count(start_token)==1 and source.count(end_token)>=1,
         "ORIGINAL_RIVAL_CPP_CLASS_BOUNDARIES_CHANGED_"+who)
    return source[start:end],start,end

def _class_probe(who:str)->str:
    if who=="prismatic_bolt":
        buff="p()->buffs.prismatic_bolt->check()"
        other="0"
        delay="0"
        original='''  bool ready() override
  {
    if ( !p()->buffs.prismatic_bolt->check() )
      return false;
    return arcane_mage_spell_t::ready();
  }
'''
        reason='PRISMATIC_BUFF_NOT_PRESENT'
        next_ready="arcane_mage_spell_t::ready()"
    elif who=="arcane_missiles":
        buff="p()->buffs.clearcasting->check()"
        other="p()->state.gained_initial_clearcasting ? 1 : 0"
        delay="allow_arcane_missiles_delay ? 1 : 0"
        original='''  bool ready() override
  {
    if ( !p()->buffs.clearcasting->check() )
      return false;

    // Arcane Missiles cannot be queued immediately after gaining the first stack of Clearcasting.
    if ( p()->state.gained_initial_clearcasting && !allow_arcane_missiles_delay )
      return false;

    return custom_state_spell_t::ready();
  }
'''
        reason="MISSILES_CLEARCASTING_MISSING"
        next_ready="custom_state_spell_t::ready()"
    else:raise RivalRouteProducerError("INVALID_CLASS_RIVAL")
    # Original C++ guard expression must remain unchanged and evaluated
    # once; extra read-only check() in logger is distinct and documented.
    cls=CLASS_NAMES[who]
    header=(
        "  bool ready() override\n"
        "  {\n"
        "    const bool zrot_rival_scope = sim->log &&\n"
        "      zrot_generic_call_scope_v1::current_root() != 0;\n"
        "    if ( zrot_rival_scope )\n"
        '      sim->print_log( "'+MARK_PRE+'{}|{}|'+who+'|{}|{}|{}",\n'
        "        sim->current_time().total_millis(),\n"
        "        zrot_generic_call_scope_v1::current_root(),\n"
        "        "+buff+",\n"
        "        "+other+",\n"
        "        "+delay+" );\n"
        "    const auto zrot_rival_class_return = [&]( const char* label, bool value ) -> bool {\n"
        "      if ( zrot_rival_scope )\n"
        '        sim->print_log( "'+MARK_CLASS+'{}|{}|'+who+'|{}|{}",\n'
        "          sim->current_time().total_millis(),\n"
        "          zrot_generic_call_scope_v1::current_root(), label, value ? 1 : 0 );\n"
        "      return value;\n"
        "    };\n"
    )
    tail=original[len("  bool ready() override\n  {\n"):]
    need(tail.endswith("  }\n"),"READY_METHOD_ORIGINAL_END_BRACE_MISSING")
    tail=tail[:-4]
    need(tail.count("return false;")==(2 if who=="arcane_missiles" else 1) and
         tail.count("return "+next_ready+";")==1,
         "CLASS_FALSE_TRUE_RETURN_COUNT_CHANGED")
    tail=tail.replace("return false;",
                      'return zrot_rival_class_return( "'+reason+'", false );',1)
    if who=="arcane_missiles":
        tail=tail.replace("return false;",
                  'return zrot_rival_class_return( "MISSILES_IMMEDIATE_CLEARCAST_DELAY", false );',1)
    tail=tail.replace("return "+next_ready+";",
           'return zrot_rival_class_return( "CLASS_BASE_READY_DELEGATED", '+next_ready+' );')
    return original,header+tail+"  }\n"

def patch_action(pristine:bytes,original_patched:bytes)->bytes:
    need(git_blob(pristine)==ACTION_BLOB,"ORIGINAL_ACTION_CPP_PIN_MISMATCH")
    prev=original_patched.decode("utf8")
    need(MARK_ACTION not in prev and ORB_STAGE in prev and
         prev.count(ORB_STAGE)==2,
         "REQUIRES_ORIGINAL_ARCANE_ORB_STAGE_PATCH")
    for phase,signature,routes in (
        ("BASE","bool action_t::ready()",READY_ROUTES),
        ("ACTION","bool action_t::action_ready()",ACTION_ROUTES)):
        body,start=_region(prev,signature)
        updated=_patch_shared_method(body,phase,routes)
        prev=prev[:start]+updated+prev[start+len(body):]
    need(prev.count(MARK_ACTION)==2 and
         prev.count(ORB_STAGE)==2,
         "MIXED_ORIGINAL_CPP_READY_RIVAL_STAGE_PATCH_COUNT")
    return prev.encode("utf8")

def patch_mage(pristine:bytes,original_patched:bytes)->bytes:
    need(git_blob(pristine)==MAGE_BLOB,"ORIGINAL_MAGE_CPP_PIN_MISMATCH")
    old=pristine.decode("utf8")
    out=original_patched.decode("utf8")
    need(MARK_PRE not in out and MARK_CLASS not in out and
         '#include "zrot_generic_call_scope_v1.hpp"' in out,
         "MISSING_EXISTING_NATIVE_ORB_ROOT_SCOPE")
    for who in ("prismatic_bolt","arcane_missiles"):
        prior,_,_=_source_class_range(old,who)
        block,a,b=_source_class_range(out,who)
        need(block==prior,"UNAPPROVED_ORIGINAL_RIVAL_CLASS_MUTATION_"+who)
        original,patched=_class_probe(who)
        need(block.count(original)==1,
             "ORIGINAL_RIVAL_READY_SOURCE_CHANGED_"+who)
        candidate=block.replace(original,patched)
        need(candidate.count(MARK_PRE)==1 and candidate.count(MARK_CLASS)==1,
             "ORIGINAL_CLASS_REPLAY_SOURCE_LOG_UNSAFE_"+who)
        out=out[:a]+candidate+out[b:]
    need(out.count(MARK_PRE)==2 and out.count(MARK_CLASS)==2,
         "MAGE_RIVAL_CPP_PATCH_MULTIPLICITY_DRIFT")
    return out.encode("utf8")

def generate(root:Path,prior_stage:Path,prior_orb_spec:Path)->dict:
    root=root.resolve(strict=True)
    revision=subprocess.run(
        ["git","-C",str(root),"rev-parse","HEAD"],check=True,
        capture_output=True,text=True).stdout.strip()
    need(revision==REVISION,"ORIGINAL_SIMC_SOURCE_REVISION_NOT_PINNED")
    stage_raw=prior_stage.read_bytes()
    orb_raw=prior_orb_spec.read_bytes()
    stage=json.loads(stage_raw);orb=json.loads(orb_raw)
    need(stage.get("schema")==ORB_PRODUCER and
         orb.get("schema")==ORB_SPEC_PRODUCER and
         stage.get("source_revision")==orb.get("source_revision")==REVISION and
         stage.get("official_action_cpp_git_blob_sha1")==ACTION_BLOB and
         orb.get("pristine_git_blob_sha1")==MAGE_BLOB,
         "NATIVE_ORB_STAGE_AND_SPEC_PRE_RECEIPT_MISMATCH")
    before={};after={}
    for path,receipt_key,pinner in (
       (ACTION_CPP,"source_after_sha256",patch_action),
       (MAGE_CPP,"after_sha256",patch_mage)):
        filepath=root/path
        raw=filepath.read_bytes()
        receipt=stage if path==ACTION_CPP else orb
        need(sha256(raw).hexdigest()==receipt[receipt_key],
             "ORIGINAL_RIVAL_SOURCE_PREV_RECEIPT_HASH_MISMATCH:"+path)
        pinned=subprocess.run(
           ["git","-C",str(root),"show",REVISION+":"+path],check=True,
           capture_output=True).stdout
        result=pinner(pinned,raw)
        before[path]=sha256(raw).hexdigest()
        after[path]=sha256(result).hexdigest()
        filepath.write_bytes(result)
    return {
      "schema":SCHEMA,"source_revision":REVISION,
      "pinned_action_cpp_git_blob":ACTION_BLOB,
      "pinned_mage_cpp_git_blob":MAGE_BLOB,
      "source_before_sha256":before,"source_after_sha256":after,
      "stage_marker":MARK_ACTION,"derived_return_marker":MARK_CLASS,
      "derived_pre_marker":MARK_PRE,
      "sources":list(RIVALS),
      "added_action_READY_calls":0,"added_RNG_calls":0,
      "added_cost_affordable_calls":0,"added_target_selection_calls":0,
      "extra_read_only_buff_check_PER_derived_READY":1,
      "original_cpp_native_action_sequence_parity":"NOT_TESTED",
      "independent_full_READY":False,
      "WCL_API_calls":0,
    }

def selftest()->dict:
    class_cases={}
    for who in CLASS_NAMES:
        original,modified=_class_probe(who)
        need(original!=modified and MARK_CLASS in modified and MARK_PRE in modified,
             "DERIVED_METHOD_PRE_AND_RETURN_PROBE_NOT_INSERTED")
        class_cases[who]=modified.count("return zrot_rival_class_return")
        need(class_cases[who]==(3 if who=="arcane_missiles" else 2),
             "CLASS_SOURCE_RETURN_WRAPPING_NOT_EXHAUSTIVE")
    base='{\n const bool marker = true;\n '+(
        ' '.join('return zrot_arcane_stage_return( "'+label+'", '+lit+' );'
                 for lit,label in READY_ROUTES))+' ZROT_ORIGINAL_ARCANE_ORB_READY_STAGE_V1| }'
    # C++ string used only for source-shape syntax here, actual production
    # uses exact original pinned C++ source identity.
    updated=_patch_shared_method(base,"BASE",READY_ROUTES)
    need(updated.count("return zrot_rival_return")==len(READY_ROUTES),
         "ORIGINAL_BASE_RETURN_BRANCH_REEVALUATED")
    for bad in (base.replace('BASE_READY_TRUE','FORGED_BASE_READY'),
                base.replace('BASE_COOLDOWN_NOT_READY','BASE_NEW_RULE')):
        try:_patch_shared_method(bad,"BASE",READY_ROUTES)
        except RivalRouteProducerError:pass
        else:raise AssertionError("FORGED_READY_BRANCH_SHAPE_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":7,"Native_CPP_actual":False,
            "physical_FULL_READY_proven":0,"WCL_API_calls":0}

def main()->None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--simc-root",type=Path)
    ap.add_argument("--prior-native-orb-stage-receipt",type=Path)
    ap.add_argument("--prior-native-orb-spec-receipt",type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    items=(a.simc_root,a.prior_native_orb_stage_receipt,a.prior_native_orb_spec_receipt)
    if all(v is None for v in items):
        out=selftest()
    elif all(v is not None for v in items):
        out=generate(*items)
    else:ap.error("all three pinned native source state receipts required")
    raw=canonical(out)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(raw)
    else:
        import sys
        sys.stdout.buffer.write(raw)

if __name__=="__main__":main()
