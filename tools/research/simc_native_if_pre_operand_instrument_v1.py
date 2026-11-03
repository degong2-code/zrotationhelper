#!/usr/bin/env python3
"""SimC native IF passive PRE operand readout successor.

Uses the already exact-source-pinned V1 one-time IF result instrumentation,
then adds a single PRE native resource/active-enemies read BEFORE the original
expression evaluation. It does not call if_expr again. This adds source-input
facts to test a deliberately bounded independent Python AST subset; no
native truth value is used as a Python operand.

No args = synthetic source transformer tests; no network or WCL.
"""
from __future__ import annotations
import argparse,hashlib,json,subprocess
from pathlib import Path
from simc_native_if_expression_instrument_v1 import (
    PINNED_COMMIT,ACTION_CPP_BLOB,TARGET,instrument as instrument_v1,PatchError
)

MARK="ZROT_NATIVE_IF_FACT_V1|"
OLD="""    const bool zrot_original_if_result = if_expr->success();"""
NEW="""    // Capture ONLY the two pre-evaluation operands by read-only access.
    // For Fury, primary_resource() is RESOURCE_RAGE (warrior source).
    const auto zrot_pre_primary_resource_kind = player->primary_resource();
    const double zrot_pre_primary_resource = player->resources.current[ zrot_pre_primary_resource_kind ];
    const unsigned zrot_pre_active_enemies = static_cast<unsigned>( sim->active_enemies );
    const bool zrot_original_if_result = if_expr->success();"""
OLD_LOG="""      sim->print_log( "ZROT_NATIVE_IF_V1|{}|{}|{}|{}|{}",
        sim->current_time().total_millis(), zrot_source_list,
        zrot_source_ordinal, name_str, zrot_original_if_result ? 1 : 0 );"""
NEW_LOG=OLD_LOG+"""
      sim->print_log( "ZROT_NATIVE_IF_FACT_V1|{}|{}|{}|{}|{}|{}|{:.17g}|{}",
        sim->current_time().total_millis(), zrot_source_list,
        zrot_source_ordinal, name_str, zrot_original_if_result ? 1 : 0,
        static_cast<int>( zrot_pre_primary_resource_kind ),
        zrot_pre_primary_resource, zrot_pre_active_enemies );"""

class OperandPatchError(PatchError):pass

def sha(blob):return hashlib.sha256(blob).hexdigest()
def git_blob(blob):return hashlib.sha1(b"blob "+str(len(blob)).encode()+b"\0"+blob).hexdigest()

def instrument(raw,*,strict=True):
    v1=instrument_v1(raw,strict=strict).decode("utf-8")
    if v1.count(OLD)!=1 or v1.count(OLD_LOG)!=1:
        raise OperandPatchError("IF_SOURCE_PRE_OPERAND_SITE_OR_RESULT_MARKER_CHANGED")
    revised=v1.replace(OLD,NEW).replace(OLD_LOG,NEW_LOG)
    # Enforce evaluation count within the EXACT function being patched.
    # Other native actions may legitimately call if_expr->success() elsewhere
    # in the 175 KB official action.cpp source; those remain untouched.
    from simc_native_if_expression_instrument_v1 import BEFORE,AFTER
    region=revised.split(BEFORE,1)[1].split(AFTER,1)[0]
    if region.count("if_expr->success()")!=1:
        raise OperandPatchError("NATIVE_ACTION_READY_IF_REEVALUATED")
    if revised.count(MARK)!=1 or revised.count("ZROT_NATIVE_IF_V1|")!=1:
        raise OperandPatchError("MISSING_SOURCE_FACT_ORIGINAL_RESULT_MARKERS")
    if revised.index("zrot_pre_primary_resource =")>revised.index("zrot_original_if_result ="):
        raise OperandPatchError("PRE_FACTS_CAPTURED_AFTER_EVALUATION")
    if revised.index("zrot_pre_active_enemies =")>revised.index("zrot_original_if_result ="):
        raise OperandPatchError("PRE_TARGET_COUNT_CAPTURED_AFTER_EVALUATION")
    return revised.encode("utf-8")


def run(root):
    root=root.resolve(strict=True)
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
        check=True,capture_output=True,text=True).stdout.strip()
    if rev!=PINNED_COMMIT:raise OperandPatchError("SOURCE_COMMIT_NOT_PINNED")
    path=root/TARGET
    original=path.read_bytes()
    if git_blob(original)!=ACTION_CPP_BLOB:
        raise OperandPatchError("NATIVE_ACTION_CPP_SOURCE_BLOB_MISMATCH")
    patched=instrument(original)
    path.write_bytes(patched)
    return {"schema":"ZrotNativeIfPreOperandPassivePatchV1",
      "official_simc_commit":rev,
      "original_action_cpp_git_blob_sha1":ACTION_CPP_BLOB,
      "source_action_cpp_sha256":sha(original),
      "patched_action_cpp_sha256":sha(patched),
      "uses_single_native_if_evaluation":True,
      "fact_read_before_original_if_eval":True,
      "native_value_source":"PLAYER_PRIMARY_RESOURCE_AND_SIM_ACTIVE_ENEMIES",
      "native_if_predicate_result_used_as_fact":False,
      "pristine_vs_instrumented_seq":"NOT_YET_VALIDATED",
      "WCL_API_calls":0,"MAIN_promotion":False}


def selftest():
    from simc_native_if_expression_instrument_v1 import BEFORE,AFTER,OLD as V1_OLD
    example=(BEFORE+"  if ( !ready() ) return false;\n"
             +V1_OLD+"\n  return true;\n}\n"+AFTER+"  return true;\n}\n").encode()
    changed=instrument(example,strict=False).decode()
    assert changed.count("if_expr->success()")==1
    # Unrelated source functions can have their own single native IF call.
    # Those must not change the function-scoped instrumentation contract.
    extended=example+b"\nvoid unrelated() { if_expr->success(); }\n"
    assert instrument(extended,strict=False).decode().count("if_expr->success()")==2
    assert changed.count(MARK)==1
    assert "zrot_pre_primary_resource" in changed
    assert "zrot_pre_active_enemies" in changed
    assert changed.index("zrot_pre_active_enemies =")<changed.index("zrot_original_if_result =")
    assert changed.index("zrot_original_if_result =")<changed.index("ZROT_NATIVE_IF_FACT_V1")
    try:instrument(changed.encode(),strict=False)
    except PatchError:pass
    else:raise AssertionError("ACCEPTED_DOUBLE_INSTRUMENT")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":8,
            "native_runtime":"NOT_RUN","if_evaluation_count_unchanged":True,
            "WCL_API_calls":0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    data=run(a.simc_root) if a.simc_root else selftest()
    blob=(json.dumps(data,sort_keys=True,separators=(",",":"))+"\n").encode()
    if a.receipt:
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.receipt.open("xb") as f:f.write(blob)
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
