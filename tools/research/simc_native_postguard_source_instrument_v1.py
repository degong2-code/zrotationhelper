#!/usr/bin/env python3
"""Passive base action_ready postguard branch and raw clock/option evidence.

Preserves exactly one original ready(), select_target(), movement direction,
sync_action->action_ready(), line_cooldown->down() and if_expr->success() call.
A direct source branch exit marker reports the observed path, NOT an
independent ready decision. Raw fields are sampled by player_t::select_action
BEFORE its only original action_ready call. Numeric replay computes the
line-cooldown, option.moving and repeated-cast predicates independently;
method overrides, RNG, target selection, movement directionality and sync
are deliberately UNKNOWN unless a source branch actually reached them.

No specialization hardcoding, no boss timeline, no WCL queries.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from simc_apl_semantic_ir_v2 import git_blob,parse_profile
from simc_native_if_expression_instrument_v1 import PINNED_COMMIT,ACTION_CPP_BLOB
from simc_native_resource_cost_pre_instrument_v1 import (
    patch as prior_patch,verify_resource_source,
)
from simc_native_ready_guard_witness_instrument_v1 import (
    ACTION_CPP,PLAYER_CPP,PLAYER_CPP_BLOB
)

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SCHEMA="ZrotNativeSourceBasePostguardAndRawSelectionPreV1"
LINE_MARK="ZROT_NATIVE_POST_LINE_PRE_V1|"
CAST_MARK="ZROT_NATIVE_POST_CAST_PRE_V1|"
EXIT_MARK="ZROT_NATIVE_BASE_POST_EXIT_V1|"
HEAD="bool action_t::action_ready()\n{\n"
TAIL="\nbool action_t::cost_affordable()"
REASONS=(
    "BASE_READY_FALSE","TARGET_FALSE","CYCLE_TRUE",
    "SKILL_RNG_TRUE","SKILL_RNG_FALSE","MOVEMENT_DIR_FALSE",
    "LINE_COOLDOWN_FALSE","SYNC_FALSE","MOVING_OPTION_FALSE",
    "IF_FALSE","REPEAT_CAST_FALSE","FULL_BASE_TRUE"
)
class PostguardProducerError(ValueError):
    pass

def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def verify_postguard_source(root:Path):
    context=verify_resource_source(root)
    action=(root/ACTION_CPP).read_bytes()
    if git_blob(action)!=ACTION_CPP_BLOB:
        raise PostguardProducerError("ORIGINAL_POSTGUARD_ACTION_CPP_DRIFT")
    txt=action.decode("utf-8")
    if txt.count(HEAD)!=1 or txt.count(TAIL)!=1:
        raise PostguardProducerError("SOURCE_BASE_ACTION_READY_BOUNDARY_CHANGED")
    body=txt.split(HEAD,1)[1].split(TAIL,1)[0]
    anchors=(
        "if ( !ready() )",
        "if ( !select_target() )",
        "if ( option.cycle_targets && sim->target_non_sleeping_list.size() > 1 )",
        "if ( rng().roll( false_positive_pct() ) )",
        "if ( rng().roll( false_negative_pct() ) )",
        "if ( !has_movement_directionality() )",
        "if ( line_cooldown->down() )",
        "if ( sync_action && !sync_action->action_ready() )",
        "if ( option.moving != -1 && option.moving != ( player->is_moving() ? 1 : 0 ) )",
        "if ( if_expr && !if_expr->success() )",
        "if ( !cooldown_allow_casting_success &&",
    )
    pos=[]
    for s in anchors:
        if body.count(s)!=1:
            raise PostguardProducerError("ORIGINAL_POSTGUARD_GUARD_CHANGED:"+s)
        pos.append(body.index(s))
    if pos!=sorted(pos):
        raise PostguardProducerError("ORIGINAL_POSTGUARD_CHECK_ORDER_CHANGED")
    cooldown=(root/"engine/sim/cooldown.cpp").read_bytes()
    if b"bool cooldown_t::down() const\n{ return ready > sim.current_time(); }" not in cooldown:
        raise PostguardProducerError("LINE_COOLDOWN_DOWN_SOURCE_CHANGED")
    return {
        "prior_source_contract":context,
        "official_action_cpp_blob_sha1":ACTION_CPP_BLOB,
        "guard_order":list(anchors),
        "raw_independent_subguards":["line_cooldown.ready>now","option.moving != actual_moving","repeat_cast_first"],
        "nonindependent_method_guards":["select_target","has_movement_directionality","sync_action","skill_rng"],
        "native_exit_markers_not_independent_oracle":True,
    }

def emit(stage:str,indent:str)->str:
    return (
        indent+"if ( sim->log && player && !player->is_pet() && !player->is_enemy() )\n"
        +indent+'  sim->print_log( "'+EXIT_MARK+'{}|{}|'+stage+'",\n'
        +indent+"    sim->current_time().total_millis(), name_str );\n"
    )

def extend_action(base:bytes)->bytes:
    txt=base.decode("utf-8")
    if txt.count(HEAD)!=1 or txt.count(TAIL)!=1 or EXIT_MARK in txt:
        raise PostguardProducerError("SOURCE_POSTGUARD_METHOD_BOUNDARY_UNIQUE")
    lead,rem=txt.split(HEAD,1)
    body,tail=rem.split(TAIL,1)
    def replace(before:str,after:str):
        nonlocal body
        if body.count(before)!=1:
            raise PostguardProducerError("SOURCE_GUARD_PATCH_ANCHOR_CHANGED:"+before[:75])
        body=body.replace(before,after,1)
    for guard,reason in (
        ("!ready()","BASE_READY_FALSE"),
        ("!select_target()","TARGET_FALSE"),
    ):
        block="if ( "+guard+" )\n  {\n    return false;\n  }"
        updated="if ( "+guard+" )\n  {\n"+emit(reason,"    ")+"    return false;\n  }"
        replace(block,updated)
    block=("if ( option.cycle_targets && sim->target_non_sleeping_list.size() > 1 )\n"
           "  {\n    return true;\n  }")
    updated=block.replace("    return true;",emit("CYCLE_TRUE","    ")+"    return true;")
    replace(block,updated)
    for guard,return_type,reason in (
        ("rng().roll( false_positive_pct() )","true","SKILL_RNG_TRUE"),
        ("rng().roll( false_negative_pct() )","false","SKILL_RNG_FALSE"),
        ("!has_movement_directionality()","false","MOVEMENT_DIR_FALSE"),
        ("line_cooldown->down()","false","LINE_COOLDOWN_FALSE"),
        ("sync_action && !sync_action->action_ready()","false","SYNC_FALSE"),
        ("option.moving != -1 && option.moving != ( player->is_moving() ? 1 : 0 )","false","MOVING_OPTION_FALSE"),
    ):
        original_indent = "      " if guard.startswith("rng().roll(") else "    "
        brace_indent = "    " if guard.startswith("rng().roll(") else "  "
        body_indent = "      " if guard.startswith("rng().roll(") else "    "
        block="if ( "+guard+" )\n"+original_indent+"return "+return_type+";"
        updated=("if ( "+guard+" )\n"+brace_indent+"{\n"+emit(reason,body_indent)
                 +body_indent+"return "+return_type+";\n"+brace_indent+"}")
        replace(block,updated)
    # Source IF has been instrumented once upstream; retain its only call.
    block="    if ( !zrot_original_if_result )\n      return false;"
    updated=("    if ( !zrot_original_if_result )\n    {\n"
             +emit("IF_FALSE","      ")+"      return false;\n    }")
    replace(block,updated)
    block=(
        "if ( !cooldown_allow_casting_success &&\n"
        "       ( ( player->last_foreground_action == this && player->last_foreground_action->time_to_execute > 0_ms ) ||\n"
        "         ( player->executing == this ) ) )\n"
        "  {\n    return false;\n  }"
    )
    updated=block.replace("    return false;",emit("REPEAT_CAST_FALSE","    ")+"    return false;")
    replace(block,updated)
    last="  return true;\n}\n"
    if not body.endswith(last):
        raise PostguardProducerError("FINAL_BASE_ACTION_READY_RETURN_CHANGED")
    body=body[:-len(last)]+emit("FULL_BASE_TRUE","  ")+last
    out=lead+HEAD+body+TAIL+tail
    if (out.count(EXIT_MARK)!=len(REASONS) or
        out.count("if_expr->success()")!=txt.count("if_expr->success()") or
        out.count("sync_action->action_ready()")!=txt.count("sync_action->action_ready()") or
        out.count("select_target()")!=txt.count("select_target()")):
        raise PostguardProducerError("POSTGUARD_ORIGINAL_CALL_COUNT_DRIFT")
    return out.encode("utf-8")

def extend_player(base:bytes)->bytes:
    txt=base.decode("utf-8")
    anchor="        zrot_tol_sim_default );"
    original="    bool zrot_native_ready = a->action_ready();"
    if txt.count(anchor)!=1 or txt.count(original)!=1 or LINE_MARK in txt or CAST_MARK in txt:
        raise PostguardProducerError("PRE_SCOPED_SOURCE_POINTER_NOT_UNIQUE")
    more=(
        "\n      // Source option fields and line cooldown clock, no method calls.\n"
        "      const int zrot_line_exists = a->line_cooldown ? 1 : 0;\n"
        "      const auto zrot_line_ready_ms = zrot_line_exists ? a->line_cooldown->ready.total_millis() : 0;\n"
        '      sim->print_log( "'+LINE_MARK+'{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}",\n'
        "        sim->current_time().total_millis(), zrot_pre_owner,\n"
        "        zrot_pre_ordinal, a->name_str, zrot_line_exists,\n"
        "        zrot_line_ready_ms, a->option.cycle_targets ? 1 : 0,\n"
        "        sim->target_non_sleeping_list.size(), a->option.moving,\n"
        "        zrot_moving, a->sync_action ? 1 : 0 );\n"
        "      const int zrot_skill_rng = ( a->action_skill != 1 || a->player->current.skill_debuff != 0 ) ? 1 : 0;\n"
        "      const int zrot_last_same = ( a->player->last_foreground_action == a ) ? 1 : 0;\n"
        "      const int zrot_last_foreground_execute_positive =\n"
        "        a->player->last_foreground_action && a->player->last_foreground_action->time_to_execute > 0_ms ? 1 : 0;\n"
        '      sim->print_log( "'+CAST_MARK+'{}|{}|{}|{}|{}|{}|{}|{}|{}|{}",\n'
        "        sim->current_time().total_millis(), zrot_pre_owner,\n"
        "        zrot_pre_ordinal, a->name_str, zrot_skill_rng,\n"
        "        a->if_expr ? 1 : 0, a->cooldown_allow_casting_success ? 1 : 0,\n"
        "        zrot_last_same, zrot_last_foreground_execute_positive,\n"
        "        a->player->executing == a ? 1 : 0 );"
    )
    out=txt.replace(anchor,anchor+more,1)
    if out.count(LINE_MARK)!=1 or out.count(CAST_MARK)!=1 or out.index(anchor)>out.index(LINE_MARK) or out.index(CAST_MARK)>out.index(original):
        raise PostguardProducerError("PRE_POSTGUARD_SCOPE_OR_CALL_DRIFT")
    return out.encode("utf-8")

def run(root:Path,profile:Path,expected_blob:str|None):
    root=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       check=True,capture_output=True,text=True).stdout.strip()
    if rev!=PINNED_COMMIT:
        raise PostguardProducerError("OFFICIAL_SOURCE_REVISION_CHANGED")
    contract=verify_postguard_source(root)
    raw=profile.read_bytes()
    if not expected_blob or git_blob(raw)!=expected_blob:
        raise PostguardProducerError("OFFICIAL_APL_PROFILE_CHANGED")
    ir=parse_profile(raw,require_source=False)
    a=root/ACTION_CPP;p=root/PLAYER_CPP
    if git_blob(a.read_bytes())!=ACTION_CPP_BLOB or git_blob(p.read_bytes())!=PLAYER_CPP_BLOB:
        raise PostguardProducerError("SIMC_CPP_NOT_PRISTINE")
    a2,p2=prior_patch(a.read_bytes(),p.read_bytes(),ir)
    final_a=extend_action(a2)
    final_p=extend_player(p2)
    a.write_bytes(final_a);p.write_bytes(final_p)
    return {
        "schema":SCHEMA,"scope_policy_id":POLICY,"official_simc_revision":rev,
        "profile_git_blob":git_blob(raw),
        "modified_action_cpp_sha256":sha(final_a),
        "modified_player_cpp_sha256":sha(final_p),
        "source_provenance":contract,
        "source_EXIT_codes":list(REASONS),
        "new_select_target_calls":0,"new_ready_calls":0,
        "new_sync_or_rng_calls":0,"new_IF_calls":0,
        "source_observed_exit_not_independent_ready":True,
        "nonperturbation":"NOT_YET_PROVEN",
        "full_action_ready_not_proven":True,"WCL_API_calls":0,
        "MAIN_promoted":False,
    }

def selftest():
    from simc_native_if_expression_instrument_v1 import NEW as IF_NEW
    from simc_native_select_trace_instrument_v1 import START,END
    from simc_native_ready_guard_witness_instrument_v1 import patched_player
    from simc_native_cooldown_queue_clock_instrument_v1 import extend_player as cd_extend
    from simc_native_cooldown_tolerance_pre_instrument_v1 import extend_player as tolerance_extend
    # The synthetic source deliberately includes every real early-return
    # source guard and original IF structure, not an unrelated toy.
    b=(
        HEAD+"  if ( !ready() )\n  {\n    return false;\n  }\n"
        "  if ( !select_target() )\n  {\n    return false;\n  }\n"
        "  if ( option.cycle_targets && sim->target_non_sleeping_list.size() > 1 )\n"
        "  {\n    return true;\n  }\n"
        "  if ( action_skill != 1 || player->current.skill_debuff != 0 )\n"
        "  {\n"
        "    if ( rng().roll( false_positive_pct() ) )\n      return true;\n"
        "    if ( rng().roll( false_negative_pct() ) )\n      return false;\n"
        "  }\n"
        "  if ( !has_movement_directionality() )\n    return false;\n"
        "  if ( line_cooldown->down() )\n    return false;\n"
        "  if ( sync_action && !sync_action->action_ready() )\n    return false;\n"
        "  if ( option.moving != -1 && option.moving != ( player->is_moving() ? 1 : 0 ) )\n    return false;\n"
        +IF_NEW+"\n"
        "  if ( !cooldown_allow_casting_success &&\n"
        "       ( ( player->last_foreground_action == this && player->last_foreground_action->time_to_execute > 0_ms ) ||\n"
        "         ( player->executing == this ) ) )\n"
        "  {\n    return false;\n  }\n"
        "  return true;\n}\n"+TAIL+"\n{}\n"
    ).encode()
    changed=extend_action(b).decode()
    for code in REASONS:
        assert EXIT_MARK in changed and "|"+code+"\"" in changed
    assert changed.count(EXIT_MARK)==12
    assert changed.count("if_expr->success()")==1
    player=(
        START+"\n{\n"
        "  // Mark this action list as visited with the APL internal id\n"
        "    if ( a->action_ready() )\n"
        "          return real_a;\n"
        "        return a;\n"
        "  return nullptr;\n}\n"+END+"\n{}\n"
    ).encode()
    prior=tolerance_extend(cd_extend(patched_player(player,strict=False)))
    out=extend_player(prior).decode()
    assert out.count(LINE_MARK)==1 and out.count(CAST_MARK)==1
    assert out.index(LINE_MARK)<out.index("bool zrot_native_ready = a->action_ready();")
    assert out.count("a->action_ready()")==1
    for fn,data in ((extend_action,changed.encode()),(extend_player,out.encode())):
        try:fn(data)
        except PostguardProducerError:pass
        else:raise AssertionError("DUPLICATE_POSTGUARD_SOURCE_PATCH_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":16,
            "Native_CXX_compile":"NOT_RUN","WCL_API_calls":0,
            "full_action_ready_independent":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--official-profile",type=Path)
    p.add_argument("--expected-profile-git-blob")
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    if a.simc_root and a.official_profile:
        result=run(a.simc_root,a.official_profile,a.expected_profile_git_blob)
    elif not a.simc_root and not a.official_profile:
        result=selftest()
    else:p.error("SimC root and profile required together")
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as f:f.write(raw)
    else:print(raw.decode(),end="")

if __name__=="__main__":
    main()
