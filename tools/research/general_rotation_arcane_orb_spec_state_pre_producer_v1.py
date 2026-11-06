#!/usr/bin/env python3
"""Source-pinned, read-only Mage Arcane Orb specialization PRE state probe.

Unlike Hekili's historical in-client State interpreter, this is an OFFLINE
SimulationCraft experiment. Adds a single forwarding ready() override to
arcane_orb_t::NORMAL, reads buff_t::check() (const, no benefit update) and
cooldown_t::charges_fractional() (const) immediately BEFORE the *one*
existing inherited base ready() evaluation. The original action_t::ready()
and action_t::action_ready() return-stage traces cross-check the wrapper.

No new cooldown-is-ready, cost-affordable, target-select, RNG, buff stack(),
or full action_ready() calls. Native action sequence parity is required.
Default zero-argument mode is a synthetic source-insertion test.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from general_rotation_arcane_orb_native_ready_stage_producer_v1 import (
    REVISION, canonical, ArcaneNativeGateError,
)
from general_rotation_source_route_audit_v1 import git_blob

SCHEMA="ZrotOriginalArcaneOrbSpecExactReadyRootPREProducerV1"
CPP_PATH="engine/class_modules/sc_mage.cpp"
ORIGINAL_CPP_BLOB="306d835f2db5f7418da221ce155d32e81c53f45c"
CLASS_ANCHOR="struct arcane_orb_t final : public arcane_mage_spell_t"
NEXT_ANCHOR="struct arcane_barrage_t final : public arcane_mage_spell_t"
METHOD_ANCHOR="\n  void execute() override\n"
MARK="ZROT_ORIGINAL_ARCANE_ORB_SPEC_PRE_V1|"
SYMBOLS=(
 "at_simc_ms","ready_root_id","talent.splintering_sorcery",
 "talent.spellfire_spheres","talent.orb_mastery","talent.charged_orb",
 "buff.arcane_charge.stack","buff.arcane_surge.stack",
 "buff.arcane_salvo.stack","cooldown.arcane_orb.charges_fractional"
)

class OrbSpecProducerError(ValueError):
    pass

def need(ok:bool,label:str)->None:
    if not ok:raise OrbSpecProducerError(label)

def _class_chunk(text:str)->tuple[str,int,int]:
    i=text.find(CLASS_ANCHOR)
    j=text.find(NEXT_ANCHOR,i+len(CLASS_ANCHOR))
    need(i>=0 and j>i and text.count(CLASS_ANCHOR)==1,
         "SOURCE_ORIGINAL_ARCANE_ORB_CLASS_SCOPE_DRIFT")
    return text[i:j],i,j

def _insert_ready(chunk:str)->str:
    need(chunk.startswith(CLASS_ANCHOR) and
         chunk.count(METHOD_ANCHOR)==1 and
         "bool ready() override" not in chunk and
         MARK not in chunk and "arcane_mage_spell_t::ready()" not in chunk,
         "ORIGINAL_MAGE_ORB_VIRTUAL_READY_SHAPE_DRIFT")
    # 10 source-PRE fields: 2 identities, 4 class talents, 3 buffs,
    # and 1 *const* cooldown fractional-charge getter.
    fmt="|".join(["{}"]*9+["{:.17g}"])
    meth=(
        "\n  // zRotationHelper: source-pinned offline original-readiness PRE probe.\n"
        "  bool ready() override\n"
        "  {\n"
        "    if ( type == ao_type::NORMAL && sim->log &&\n"
        "         zrot_generic_call_scope_v1::current_root() != 0 )\n"
        "    {\n"
        '      sim->print_log( "'+MARK+fmt+'",\n'
        "        sim->current_time().total_millis(),\n"
        "        zrot_generic_call_scope_v1::current_root(),\n"
        "        p()->talents.splintering_sorcery.ok() ? 1 : 0,\n"
        "        p()->talents.spellfire_spheres.ok() ? 1 : 0,\n"
        "        p()->talents.orb_mastery.ok() ? 1 : 0,\n"
        "        p()->talents.charged_orb.ok() ? 1 : 0,\n"
        "        p()->buffs.arcane_charge->check(),\n"
        "        p()->buffs.arcane_surge->check(),\n"
        "        p()->buffs.arcane_salvo->check(),\n"
        "        cooldown->charges_fractional() );\n"
        "    }\n"
        "    return arcane_mage_spell_t::ready();\n"
        "  }\n"
    )
    new=chunk.replace(METHOD_ANCHOR,meth+METHOD_ANCHOR)
    need(new.count(MARK)==1 and
         new.count("arcane_mage_spell_t::ready()")==1 and
         new.count("->check()")==3 and
         new.count("->charges_fractional()")==1 and
         new.count("return arcane_mage_spell_t::ready();")==1,
         "ORIGINAL_MAGE_SPEC_PRE_INJECTION_SEMANTIC_DRIFT")
    return new

def patch(original:bytes,prior:bytes)->bytes:
    need(git_blob(original)==ORIGINAL_CPP_BLOB,
         "UNPINNED_OFFICIAL_SIMC_MAGE_CPP_SOURCE")
    source=prior.decode("utf8")
    pristine=original.decode("utf8")
    need("zrot_generic_call_scope_v1::current_root" in source and
         '#include "zrot_generic_call_scope_v1.hpp"' in source and
         MARK not in source,
         "SAME_NATIVE_ROOT_CONTEXT_NOT_INSTALLED")
    orig_chunk,_,_=_class_chunk(pristine)
    chunk,start,end=_class_chunk(source)
    need(chunk==orig_chunk,
         "BEFORE_NEW_MAGE_ORB_READY_PROBE_CLASS_NOT_IDENTICAL_TO_UPSTREAM")
    injected=_insert_ready(chunk)
    out=source[:start]+injected+source[end:]
    need(out.count(MARK)==1 and
         out.count("arcane_mage_spell_t::ready()")==1 and
         out.count("rng().roll(")==source.count("rng().roll(") and
         out.count("action_ready()")==source.count("action_ready()") and
         out.count("cost_affordable()")==source.count("cost_affordable()"),
         "ORIGINAL_NATIVE_REEVALUATION_OR_SCOPE_CHANGED")
    return out.encode("utf8")

def generate(root:Path,prior_method:Path)->dict:
    root=root.resolve(strict=True)
    git=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,text=True,capture_output=True).stdout.strip()
    need(git==REVISION,"OFFICIAL_SIMC_SOURCE_REVISION_MISMATCH")
    receipt=json.loads(prior_method.read_bytes())
    # This source has already been pinned by generic method scope producer.
    need(receipt.get("source_revision")==REVISION and
         receipt.get("source_method_count")==6 and
         "arcane_blast_ready" in receipt.get("source_method_sites",[]),
         "ORIGINAL_MAGE_PRE_METHOD_RECEIPT_REQUIRED")
    original=subprocess.run(["git","-C",str(root),"show",
        f"{REVISION}:{CPP_PATH}"],check=True,capture_output=True).stdout
    path=root/CPP_PATH
    before=path.read_bytes()
    after=patch(original,before)
    path.write_bytes(after)
    return {
        "schema":SCHEMA,"source_revision":REVISION,
        "source_cpp":CPP_PATH,"pristine_git_blob_sha1":ORIGINAL_CPP_BLOB,
        "before_sha256":sha256(before).hexdigest(),
        "after_sha256":sha256(after).hexdigest(),
        "marker":MARK,"source_pre_field_names":list(SYMBOLS),
        "original_CPP_base_ready_calls_per_virtual_ORB_invocation":1,
        "added_direct_action_ready_calls":0,
        "added_direct_rng_calls":0,
        "added_direct_cost_calls":0,
        "additional_read_only_buff_check_calls_per_orb_root":3,
        "additional_const_charges_fractional_calls_per_orb_root":1,
        "physical_class_specific_state_pre_is_not_WCL_STRICT_PRE":True,
        "Native_CPP_A_B_action_parity":"NOT_RUN",
        "independent_complete_action_READY":False,
        "user_dummy_feedback_permitted":False,
        "WCL_API_calls":0
    }

def selftest()->dict:
    minimal=(CLASS_ANCHOR+"\n{\n  arcane_orb_t() {}\n"+
             METHOD_ANCHOR+"  {}\n};\n")
    built=_insert_ready(minimal)
    need(built.count(MARK)==1 and
         built.count("return arcane_mage_spell_t::ready();")==1,
         "ORIGINAL_ONE_BASE_READY_DELEGATION_MISSING")
    for v in (minimal.replace("void execute()","void cast()"),
              minimal.replace("  arcane_orb_t() {}", "  bool ready() override {}\n"),
              minimal.replace(CLASS_ANCHOR,"struct fake_t final : public arcane_mage_spell_t"),
              built):
        try:_insert_ready(v)
        except OrbSpecProducerError:pass
        else:raise AssertionError("SYNTHETIC_ORB_READY_PROBE_SCOPE_FORGERY_ACCEPTED")
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":6,"Native_CPP_actual":False,
            "independent_complete_action_READY":False,"WCL_API_calls":0}

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--prior-method-receipt",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root is None and a.prior_method_receipt is None:
        result=selftest()
    elif a.simc_root is not None and a.prior_method_receipt is not None:
        result=generate(a.simc_root,a.prior_method_receipt)
    else:p.error("existing original SimC source and method receipt both required")
    data=canonical(result)
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        a.receipt.write_bytes(data)
    else:
        import sys
        sys.stdout.buffer.write(data)

if __name__=="__main__": main()
