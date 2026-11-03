#!/usr/bin/env python3
"""Compare source-faithful SimC profile IR with actually saved native effective APL.

Native SimC save_actions proves effective action-list bytes for the pinned
profile/build/binary, not a matched per-decision action selection. A difference
is never silently "corrected": report the first mismatched list/row/attribute.
If native differs, only the matching native effective APL may be compared with
native action choices, never the raw input profile.

Default execution: isolated synthetic comparison only; no network or native
runtime. The real mode requires verified native capture identity and sha256.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from simc_apl_semantic_ir_v2 import parse_profile,sha256,canonical,SCHEMA,PROFILE_GIT_BLOB

POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

class NativeIdentityError(ValueError):pass

def compare_lists(source,eff):
    names=sorted(set(source["action_lists"])|set(eff["action_lists"]))
    diff=[]
    match_count=0
    for name in names:
        ls=source["action_lists"].get(name,[])
        es=eff["action_lists"].get(name,[])
        for i in range(max(len(ls),len(es))):
            if i>=len(ls) or i>=len(es):
                diff.append({"list":name,"index":i,
                   "type":"MISSING_SOURCE_ROW" if i>=len(ls) else "MISSING_EFFECTIVE_ROW"})
                continue
            a,b=ls[i],es[i]
            aa={x["key"]:x["value"] for x in a["attributes"]}
            bb={x["key"]:x["value"] for x in b["attributes"]}
            if a["action"]!=b["action"] or aa!=bb:
                diff.append({"list":name,"index":i,"type":"SOURCE_EFFECTIVE_ACTION_OR_ATTRIBUTE_DIFFERENCE",
                             "source_action":a["action"],"effective_action":b["action"],
                             "source_attrs":aa,"effective_attrs":bb})
            elif a["expression_fields"]!=b["expression_fields"]:
                diff.append({"list":name,"index":i,"type":"SEMANTIC_AST_MISMATCH"})
            else:
                match_count+=1
    return {"source_rows":source["source_action_line_count"],
            "effective_rows":eff["source_action_line_count"],
            "semantic_rows_matching":match_count,
            "differences":diff,
            "comparison_scope":"SOURCE_ROWS_ACTION_NAMES_MODIFIERS_AND_EXPRESSION_ASTS",
            "source_to_effective_structure_identical":not diff}

def compare(profile, effective, capture):
    raw=profile.read_bytes()
    native=effective.read_bytes()
    if hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=PROFILE_GIT_BLOB:
        raise NativeIdentityError("PINNED_PUBLIC_PROFILE_CHANGED")
    receipt=json.loads(capture.read_bytes())
    if (receipt.get("schema")!="ZrotSimcNativeReferenceCaptureV1"
        or receipt.get("status")!="SIMC_NATIVE_CAPTURED_UNPARSED"
        or receipt.get("source_kind")!="LOCAL_SIMC_EXECUTABLE"
        or receipt.get("simc_spec")!="fury"
        or receipt.get("profile_sha256")!=sha256(raw)
        or receipt.get("effective_apl_sha256")!=sha256(native)
        or len(receipt.get("simc_executable_sha256",""))!=64
        or receipt.get("actionable_rotation") is not False):
        raise NativeIdentityError("UNTRUSTED_NATIVE_REFERENCE_CAPTURE")
    source_ir=parse_profile(raw,require_source=True)
    effective_ir=parse_profile(native,require_source=False)
    matching=compare_lists(source_ir,effective_ir)
    return {"schema":"ZrotNativeEffectiveAplCrosscheckV1",
        "scope_policy_id":POLICY,
        "status":"NATIVE_SOURCE_ACTIONS_VERIFIED_NOT_NATIVE_DECISION_PARITY",
        "source_profile_git_blob_sha1":PROFILE_GIT_BLOB,
        "source_sha256":sha256(raw),
        "native_simc_binary_sha256":receipt["simc_executable_sha256"],
        "native_effective_apl_sha256":sha256(native),
        "real_native_capture":True,
        "capture_target_count":receipt.get("controlled_target_count"),
        "native_effective_action_lists":effective_ir["action_list_counts"],
        "native_effective_control_graph":effective_ir["graph_edges"],
        "native_effective_ast_compilation":"PASS",
        "source_to_native_effective":matching,
        "source_to_native_action_selection_parity":"NOT_RUN",
        "precombat_opener_native_execution_parity":"NOT_RUN",
        "source_model_general_rotation_complete":False,
        "WCL_ready_to_replay":False,
        "dummy_trainer_rule_authorized":False,
        "MAIN_promotion":False}


def selftest():
    a=parse_profile(
       b"actions=call_action_list,name=foo\n"
       b"actions+=/beta,if=x>=2\n"
       b"actions.foo=alpha,if=2%3<1\n",require_source=False)
    same=parse_profile(
       b"actions=call_action_list,name=foo\n"
       b"actions+=/beta,if=x>=2\n"
       b"actions.foo=alpha,if=2%3<1\n",require_source=False)
    diff=parse_profile(
       b"actions=call_action_list,name=foo\n"
       b"actions+=/beta,if=x>2\n"
       b"actions.foo=alpha,if=2%3<1\n",require_source=False)
    assert compare_lists(a,same)["source_to_effective_structure_identical"] is True
    v=compare_lists(a,diff)
    assert not v["source_to_effective_structure_identical"]
    assert v["differences"][0]["list"]=="default"
    assert len(v["differences"])==1
    assert v["differences"][0]["type"]=="SOURCE_EFFECTIVE_ACTION_OR_ATTRIBUTE_DIFFERENCE"
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":5,
            "actual_native_simc_executed":False,
            "native_choice_parity_verified":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",type=Path)
    p.add_argument("--native-effective",type=Path)
    p.add_argument("--native-receipt",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    paths=(a.profile,a.native_effective,a.native_receipt)
    if all(v is None for v in paths):obj=selftest()
    elif all(v is not None for v in paths):obj=compare(*paths)
    else:p.error("all three pinned inputs are required or none")
    blob=canonical(obj)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("SIMC_NATIVE_EFFECTIVE_APL_CROSSCHECK_SHA256="+sha256(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__":main()
