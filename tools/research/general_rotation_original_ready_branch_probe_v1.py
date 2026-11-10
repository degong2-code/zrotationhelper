#!/usr/bin/env python3
"""Passive, source-neutral trace of ORIGINAL SimC action_t readiness branches.

Adds print_log only to already-taken return branches, without calling ready(),
action_ready(), IF, RNG, cooldown or queue accessors again. A marker observed
between the original SELECT PRE and POST belongs to that ONE Native call;
it is an in-call causal branch witness, not an independent gameplay-ready PRE.
No-argument run is a PyCharm-safe synthetic/static regression.
"""
from __future__ import annotations
import argparse
from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess

REV = "b522cded8c26b97dac03fdf56e57a03ec7e8faa6"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
SOURCE = "engine/action/action.cpp"
GIT_BLOB = "399ecd9453b3f30bfc2ebf2b3ffd8f56cce8f8d4"
SCHEMA = "ZrotOriginalActionReadyBranchPassivePatchV1"
PARENT_SCHEMA = "ZrotOriginalSimCSelectedRowSameCallIFSourcePatchV1"
MARK = "ZROT_ORIGINAL_ACTION_READY_BRANCH_V1|"
START_COMPOSITE = "bool action_t::action_ready()\n{"
END_COMPOSITE = "\nbool action_t::cost_affordable()"
START_BASE = "bool action_t::ready()\n{"
END_BASE = "\nvoid action_t::init()"

class BranchPatchError(ValueError):
    pass

def require(ok, name):
    if not ok:
        raise BranchPatchError(name)

def gitblob(raw):
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def sha(raw):
    return sha256(raw).hexdigest()

def emit(reason, indent="    "):
    require(reason.isupper() and reason.replace("_","").isalnum(), "INVALID_ORIGINAL_BRANCH_CODE")
    return (
        indent + "if ( sim->log && player )\n" +
        indent + '  sim->print_log("' + MARK + '{}|{}|{}|{}",\n' +
        indent + "    sim->current_time().total_millis(),\n" +
        indent + "    static_cast<const void*>(player),\n" +
        indent + '    static_cast<const void*>(this), "' + reason + '");\n'
    )

def once(text, old, new, gate):
    require(text.count(old) == 1, gate)
    return text.replace(old, new, 1)

def patch(raw):
    before = raw.decode("utf-8")
    require(MARK not in before and before.count(START_COMPOSITE)==1 and
            before.count(START_BASE)==1 and before.count(END_COMPOSITE)==1 and
            before.count(END_BASE)==1, "UNPINNED_OR_ALREADY_INSTRUMENTED_ORIGINAL_ACTION_CPP")
    cs=before.index(START_COMPOSITE);ce=before.index(END_COMPOSITE,cs)
    rs=before.index(START_BASE);re=before.index(END_BASE,rs)
    require(cs<ce<rs<re, "ACTION_CPP_BASE_COMPOSITE_FUNCTION_SCOPE_DRIFT")
    composite=before[cs:ce];base=before[rs:re]

    # This captures the ORIGINAL virtual ready() result without invoking it
    # twice. If a class override rejects before base ready(), no BASE_* marker
    # exists; the replay must classify that as OVERRIDE_OR_EARLY_UNKNOWN.
    original="  if ( !ready() )\n  {\n    return false;\n  }"
    replaced="  if ( !ready() )\n  {\n"+emit("COMPOSITE_BASE_READY_FALSE")+"    return false;\n  }"
    composite=once(composite,original,replaced,"ORIGINAL_ACTION_READY_GATE_CHANGED")

    # Do not re-evaluate the if expression. This records the result AFTER
    # its one actual native evaluation. No conversion into Strict PRE evidence.
    original="    if ( !zrot_original_native_if )\n      return false;"
    replaced=("    if ( !zrot_original_native_if )\n    {\n"+
              emit("COMPOSITE_SOURCE_IF_FALSE")+"      return false;\n    }")
    composite=once(composite,original,replaced,"ORIGINAL_NATIVE_IF_GATE_CHANGED")

    for predicate, label in (
        ("!cooldown->is_ready()", "BASE_COOLDOWN_NOT_READY"),
        ("internal_cooldown->down()", "BASE_INTERNAL_COOLDOWN_DOWN"),
        ("player->is_moving() && !usable_moving()", "BASE_MOVING_UNUSABLE"),
    ):
        original=f"  if ( {predicate} )\n    return false;"
        updated=(f"  if ( {predicate} )\n  {{\n"+
                 emit(label)+"    return false;\n  }")
        base=once(base,original,updated,"BASE_RETURN_BRANCH_DRIFT:"+label)

    original=("  if ( !cost_affordable() )\n  {\n"
              "    if ( starved_proc )\n      starved_proc->occur();\n"
              "    return false;\n  }")
    updated=("  if ( !cost_affordable() )\n  {\n"
             "    if ( starved_proc )\n      starved_proc->occur();\n"+
             emit("BASE_RESOURCE_NOT_AFFORDABLE")+"    return false;\n  }")
    base=once(base,original,updated,"BASE_RESOURCE_GATE_DRIFT")

    original=("    if ( execute_time() > timespan_t::zero() )\n"
              "    {\n      return false;\n    }")
    updated=("    if ( execute_time() > timespan_t::zero() )\n"
             "    {\n"+emit("BASE_CAST_WHILE_CASTING_EXECUTION_TIME",indent="      ")+
             "      return false;\n    }")
    base=once(base,original,updated,"BASE_WHILE_CASTING_EXECUTE_GATE_DRIFT")
    original=("    if ( ( player->executing || player->channeling ) && gcd() > timespan_t::zero() &&\n"
              "         player->gcd_ready > sim->current_time() )\n"
              "    {\n      return false;\n    }")
    updated=("    if ( ( player->executing || player->channeling ) && gcd() > timespan_t::zero() &&\n"
             "         player->gcd_ready > sim->current_time() )\n"
             "    {\n"+emit("BASE_GCD_WHILE_CASTING",indent="      ")+
             "      return false;\n    }")
    base=once(base,original,updated,"BASE_GCD_WHILE_CASTING_GATE_DRIFT")
    require(base.endswith("  return true;\n}\n") or base.endswith("  return true;\n}\n\n"),
            "BASE_READY_TAIL_CHANGED")
    base=once(base,"  return true;\n}\n",emit("BASE_READY_TRUE",indent="  ")+
              "  return true;\n}\n","BASE_READY_SUCCESS_GATE_DRIFT")

    after=before[:cs]+composite+before[ce:rs]+base+before[re:]
    require(after.count(MARK)==9 and
            after.count("zrot_original_native_if=if_expr->success()")==1 and
            after.count("!cooldown->is_ready()")==before.count("!cooldown->is_ready()") and
            after.count("internal_cooldown->down()")==before.count("internal_cooldown->down()") and
            after.count("!cost_affordable()")==before.count("!cost_affordable()") and
            after.count("ready()")==before.count("ready()") and
            after.count("action_ready()")==before.count("action_ready()") and
            after.count("rng().roll(")==before.count("rng().roll(") and
            after.count("if_expr->success()")==before.count("if_expr->success()") and
            after.count("starved_proc->occur()")==before.count("starved_proc->occur()") and
            after.count("return false;")==before.count("return false;") and
            after.count("return true;")==before.count("return true;"),
            "ORIGINAL_READY_OR_IF_RNG_RETURN_CALL_STRUCTURE_CHANGED")
    return after.encode("utf-8")

def install(root,prior):
    root=root.resolve(strict=True)
    version=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                           text=True,capture_output=True,check=True).stdout.strip()
    require(version==REV,"ORIGINAL_SIMC_REVISION_CHANGED")
    path=root/SOURCE
    before=path.read_bytes()
    require(prior.get("schema")==PARENT_SCHEMA and
            prior.get("source_revision")==REV and
            prior.get("official_action_git_blob")==GIT_BLOB and
            prior.get("patch_sha256",{}).get(SOURCE)==sha(before) and
            prior.get("original_action_ready_calls_added")==0 and
            prior.get("original_if_expr_success_calls_added")==0,
            "PRIOR_ORIGINAL_ACTION_CPP_IF_PATCH_RECEIPT_NOT_BOUND")
    patched=patch(before)
    path.write_bytes(patched)
    return {"schema":SCHEMA,"policy_id":POLICY,"original_simc_revision":REV,
            "original_action_cpp_git_blob":GIT_BLOB,
            "original_sha256":sha(before),"patched_sha256":sha(patched),
            "parent_original_native_IF_receipt_sha256":sha(
                (json.dumps(prior,sort_keys=True,separators=(",",":"))).encode("utf-8")
            ),
            "original_calls_added":{"action_ready":0,"ready":0,"IF":0,"RNG":0,
                                    "cooldown":0,"queue":0},
            "branch_markers_per_source":9,
            "readiness_proof":"IN_ORIGINAL_NATIVE_CALL_ONLY_NOT_INDEPENDENT_WOW_PRE",
            "current_Retail_ready":"UNKNOWN","WCL_blind_postlock":"NOT_RUN",
            "new_general_rotation_rules_promoted":0,"MAIN_promoted":False}

def selftest():
    # Synthetic exact original function bodies; do not execute the spell.
    composite=(START_COMPOSITE+'\n'
       "  if ( !ready() )\n  {\n    return false;\n  }\n"
       "  if ( if_expr )\n  {\n    const bool zrot_original_native_if=if_expr->success();\n"
       "    if ( !zrot_original_native_if )\n      return false;\n  }\n"
       "  return true;\n}\n")
    base=(START_BASE+"\n"+
       "  if ( !cooldown->is_ready() )\n    return false;\n"
       "  if ( internal_cooldown->down() )\n    return false;\n"
       "  if ( player->is_moving() && !usable_moving() )\n    return false;\n"
       "  if ( !cost_affordable() )\n  {\n    if ( starved_proc )\n      starved_proc->occur();\n    return false;\n  }\n"
       "  if ( usable_while_casting )\n  {\n"
       "    if ( execute_time() > timespan_t::zero() )\n    {\n      return false;\n    }\n"
       "    if ( ( player->executing || player->channeling ) && gcd() > timespan_t::zero() &&\n"
       "         player->gcd_ready > sim->current_time() )\n"
       "    {\n      return false;\n    }\n  }\n"
       "  return true;\n}\n")
    src=(composite+END_COMPOSITE+"\n"+base+END_BASE+"\n").encode()
    built=patch(src).decode()
    require(built.count(MARK)==9 and
            "COMPOSITE_BASE_READY_FALSE" in built and
            "COMPOSITE_SOURCE_IF_FALSE" in built and
            "BASE_RESOURCE_NOT_AFFORDABLE" in built and
            "BASE_COOLDOWN_NOT_READY" in built and
            built.count("if_expr->success()")==1,
            "SYNTHETIC_ORIGINAL_BRANCH_REPLAY_INVALID")
    neg=0
    for bad in (
        src.replace(b"!cooldown->is_ready()",b"!cooldown->up()"),
        src.replace(b"!zrot_original_native_if",b"!other_if_result"),
        src.replace(b"starved_proc->occur();",b"starved_proc->execute();"),
        src.replace(b"internal_cooldown->down()",b"internal_cooldown->ready()"),
        src.replace(b"return true;\n}\n"+END_BASE.encode(),b"return false;\n}\n"+END_BASE.encode()),
        built.encode()
    ):
        try:patch(bad)
        except BranchPatchError:neg+=1
        else:raise AssertionError("UNPINNED_NATIVE_BASE_BRANCH_ACCEPTED")
    require(neg==6,"MISSING_NATIVE_PATCH_NEGATIVE_CONTROLS")
    return {"schema":SCHEMA,"status":"PASS_SYNTHETIC_STATIC",
            "negative_controls":neg,"source_branch_markers":9,
            "new_original_action_ready_calls":0,"new_native_IF_RNG_calls":0,
            "physical_READY_independent_of_Native":"UNKNOWN"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--prior-receipt",type=Path)
    p.add_argument("--out-receipt",type=Path)
    a=p.parse_args()
    if all(x is None for x in vars(a).values()):
        print(json.dumps(selftest(),sort_keys=True));return
    require(all(x is not None for x in vars(a).values()),"PINNED_ORIGINAL_ROOT_AND_OUT_REQUIRED")
    result=install(a.source_root,json.loads(a.prior_receipt.read_bytes()))
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    a.out_receipt.parent.mkdir(parents=True,exist_ok=True)
    with a.out_receipt.open("xb") as f:f.write(raw)
    print("ORIGINAL_NATIVE_READY_BRANCH_PATCH_SHA256="+sha(raw))

if __name__=="__main__":
    main()
