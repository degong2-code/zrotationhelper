#!/usr/bin/env python3
"""Independently pair exact SimC Mage override guard with original APL PRE.

Replays the ORIGINAL Native trace, not a vendor-provided "ready" Boolean:
   Generic PRE row/field -> same action_t* POINTER -> Mage ready() guard
   -> one original action_ready() ATTEMPT return (POST COMPARATOR ONLY).

One false necessary predicate can certify a scoped NOT_READY even though
the full positive ready route is unclosed. A true necessary predicate
NEVER yields full READY. WCL same-time events/observed casts are irrelevant.

IMPORTANT: only the already controlled, pinned CI native run (with exact
source patch, pristine/instrumented cast parity, and artifact byte checks)
can authorize original-source provenance. An arbitrary user-supplied JSON
or synthetic log must not be upgraded into independent evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from simc_apl_semantic_ir_v2 import git_blob
from general_rotation_decision_proof_engine_v1 import (
    Fact,GateContract,Identity,decide_candidate,NOT_READY,UNKNOWN)
from general_rotation_original_pre_field_transport_v1 import (
    parse_marker,parse_attempt,MARK as FIELD_MARK,FieldCaptureError)
from general_rotation_source_pre_field_capture_v1 import FIELDS
from general_rotation_mage_source_fixture_v1 import (
    rules as mage_source_rules, CPP_BLOB, PROFILE_BLOB as MAGE_PROFILE_BLOB)
from simc_native_mage_exact_ready_guard_producer_v1 import (
    MAGE_PATH,PLAYER_PATH,PROFILE_PATH,POINTER_MARK,METHOD_MARK,
    SIMC_COMMIT,verify_pristine_root)
from general_rotation_condition_ir_v1 import (
    ObservedField,inspect_requirement)

SCHEMA="ZrotOriginalSimcMageExactReadyGuardIndependentReplayV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
HEX_ADDRESS=re.compile(r"^0x[0-9a-fA-F]+$")
REQUIRED_OPEN=("BASE_VIRTUAL_COMPLETE","CAST_GCD","MOVEMENT",
               "SPEC_OVERRIDE_TOTAL")


class MageGuardReplayError(ValueError):
    pass


def ensure(x:bool,code:str)->None:
    if not x:raise MageGuardReplayError(code)


def sha(raw:bytes)->str:
    return sha256(raw).hexdigest()


def parse_pointer(line:str)->dict|None:
    start=line.find(POINTER_MARK)
    if start<0:return None
    p=line[start:].strip().split("|")
    ensure(len(p)==4,"ACTION_POINTER_PRE_FORMAT_INVALID")
    try:t=int(p[1])
    except ValueError as e:raise MageGuardReplayError("POINTER_PRE_TIME_INVALID") from e
    ensure(t>=0 and bool(p[2]) and bool(HEX_ADDRESS.fullmatch(p[3])),
           "ACTION_POINTER_ADDRESS_OR_NAME_INVALID")
    return {"time_ms":t,"native_action_name":p[2],"pointer":p[3].lower()}


def parse_guard(line:str)->dict|None:
    start=line.find(METHOD_MARK)
    if start<0:return None
    p=line[start:].strip().split("|")
    ensure(len(p)==6,"ORIGINAL_METHOD_GUARD_FORMAT_INVALID")
    try:t=int(p[1]);stack=int(p[5])
    except ValueError as e:raise MageGuardReplayError("ORIGINAL_METHOD_GUARD_VALUE_INVALID") from e
    ensure(t>=0 and stack>=0 and p[2] in ("arcane_blast","prismatic_bolt")
           and bool(p[3]) and bool(HEX_ADDRESS.fullmatch(p[4])),
           "ORIGINAL_METHOD_GUARD_UNSUPPORTED_SCOPE")
    return {"time_ms":t,"method_key":p[2],
            "native_action_name":p[3],"pointer":p[4].lower(),
            "raw_buff_stack":stack}


def parse_original_attempts(trace:str)->dict:
    pending=None;rows=[];count=0;orphan_guard_events=0
    for line in trace.splitlines():
        raw=parse_marker(line,FIELDS)
        if raw is not None:
            ensure(pending is None,"ORIGINAL_PRE_ROW_RECURSIVE_OR_UNPAIRED")
            pending={"raw":raw,"pointer":None,"guards":[]}
            continue
        pointer=parse_pointer(line)
        if pointer is not None:
            ensure(pending is not None and pending["pointer"] is None and
                   pointer["time_ms"]==pending["raw"]["time_ms"] and
                   pointer["native_action_name"]==pending["raw"]["native_action_name"],
                   "ORIGINAL_ACTION_POINTER_NOT_BOUND_TO_PRE_ROW")
            pending["pointer"]=pointer["pointer"]
            continue
        guard=parse_guard(line)
        if guard is not None:
            if pending is None:
                orphan_guard_events+=1
            else:
                pending["guards"].append(guard)
            continue
        attempt=parse_attempt(line)
        if attempt is None:continue
        count+=1
        ensure(pending is not None and pending["pointer"] is not None and
               all(pending["raw"][k]==attempt[k] for k in
                   ("time_ms","source_list","ordinal_1based",
                    "native_action_name")),
               "ORIGINAL_NATIVE_CALL_NOT_EXACTLY_PAIRED")
        # Other readiness checks can happen during the same call; only
        # THIS original action object's pointer is admissible. A nested
        # invocation or another action name cannot authenticate this row.
        matching=[
            g for g in pending["guards"]
            if g["time_ms"]==pending["raw"]["time_ms"] and
               g["native_action_name"]==pending["raw"]["native_action_name"] and
               g["method_key"]==pending["raw"]["native_action_name"] and
               g["pointer"]==pending["pointer"]
        ]
        ensure(len(matching)<=1,
               "SAME_ACTION_METHOD_GUARD_DUPLICATED_IN_ONE_ORIGINAL_CALL")
        rows.append({"raw":pending["raw"],
                     "object_pointer":pending["pointer"],
                     "own_method_guard":matching[0] if matching else None,
                     "non_matching_method_events":len(pending["guards"])-len(matching),
                     "native_post_comparator_only":True})
        pending=None
    ensure(count>0 and pending is None and len(rows)==count,
           "TRUNCATED_OR_EMPTY_ORIGINAL_METHOD_PRE")
    return {"rows":rows,"original_native_attempts":count,
            "unattributed_method_events":orphan_guard_events}


def replay_cases(rows:list[dict],source_rules:list[tuple],*,
                 trace_sha256:str,source_patch_sha256:str,
                 parity_sha256:str)->dict:
    proof=[]
    counts=Counter()
    for rule,base_ident in source_rules:
        owner,action=base_ident.scope.split("::",1)
        relevant=[
            r for r in rows
            if r["raw"]["source_list"]==owner and
               r["raw"]["ordinal_1based"]==base_ident.ordinal+1 and
               r["raw"]["native_action_name"]==action
        ]
        observed=0
        statuses=Counter()
        raw_examples=[]
        seen=Counter()
        for row in relevant:
            r=row["raw"];t=r["time_ms"]
            key=(t,owner,r["ordinal_1based"],action)
            occurrence=seen[key];seen[key]+=1
            guard=row["own_method_guard"]
            if guard is None:
                statuses["UNKNOWN_NO_ORIGINAL_OVERRIDE_ENTRY"]+=1
                continue
            # Paired generic source PRE buff field and the direct
            # original override guard MUST describe the identical state.
            raw_buff=r["values"][2]
            ensure(raw_buff in (0,1) and
                   (guard["raw_buff_stack"]>0)==bool(raw_buff),
                   "ORIGINAL_METHOD_BUFF_CONFLICT_WITH_SAME_ACTION_PRE")
            ident=replace(base_ident,t_ms=t,occurrence=occurrence)
            expected=rule.expression["value"]
            ensure(rule.expression["field"]=="buff.prismatic_bolt.active"
                   and rule.expression["op"]=="compare"
                   and rule.expression["cmp"]=="eq"
                   and type(expected) is bool,
                   "SOURCE_GUARD_SPEC_ADAPTER_CONTRACT_DRIFT")
            actual_allowed=(guard["raw_buff_stack"]>0)==expected
            # Source guard was executed as the original virtual method
            # on the exact same action_t*; independently this necessary
            # guard is TRUE or FALSE. This is not complete READY.
            fact=Fact(
                identity=ident,gate=rule.gate,value=actual_allowed,
                basis="INDEPENDENT_SOURCE_REPLAY",
                captured="SIMC_ORIGINAL_METHOD_PRE",
                event_t_ms=t,
                receipt=("source_run_sha256:"+trace_sha256+
                         "|original_method_patch_sha256:"+source_patch_sha256+
                         "|same_seed_cast_parity_sha256:"+parity_sha256))
            contract=GateContract(
                source="PINNED_MAGE_ORIGINAL_ACTUAL_OVERRIDE_ENTRY_ONLY",
                source_sha256=ident.source_sha256,
                required=(rule.gate,)+REQUIRED_OPEN,
                closed=False,closure_receipt=None)
            result=decide_candidate(
                ident,contract,(fact,),is_physical_action=True)
            expected_decision=UNKNOWN if actual_allowed else NOT_READY
            ensure(result["decision"]==expected_decision and
                   result["dummy_error_permitted"] is False and
                   result["positive_route_closed"] is False,
                   "NECESSARY_FALSE_OR_OPEN_POSITIVE_PROOF_DRIFT")
            observed+=1
            statuses[result["decision"]]+=1
            if len(raw_examples)<3:
                raw_examples.append({
                    "source_time_ms":t,
                    "source_occurrence":occurrence,
                    "original_method_stacks":guard["raw_buff_stack"],
                    "raw_pre_buff_active":bool(raw_buff),
                    "guard_passed":actual_allowed,
                    "independently_certified_scoped_gate":rule.gate,
                    "candidate_readiness":result["decision"],
                    "positive_route_closed":False,
                    "method_entry_pointer_equal_to_original_action":True,
                    "source_native_return_used_to_certify":False,
                })
        proof.append({
            "action":action,"source_row_sha256":base_ident.source_sha256,
            "source_rule_id":rule.stable_rule_id,
            "original_source_row_attempts":len(relevant),
            "override_entered_on_exact_action_count":observed,
            "status_distribution":dict(sorted(statuses.items())),
            "examples":raw_examples,
            "full_positive_READY":0,
        })
        counts["source_rows_visited"]+=len(relevant)
        counts["guard_entries_proven"]+=observed
        counts["scoped_NOT_READY"]+=statuses[NOT_READY]
        counts["UNKNOWN"]+=statuses[UNKNOWN]+statuses[
            "UNKNOWN_NO_ORIGINAL_OVERRIDE_ENTRY"]
    return {"candidate_proofs":proof,"counts":dict(counts),
            "full_positive_READY":0,
            "user_dummy_practice_error_permitted":False,
            "independent_WCL_PRE_reconstructed":False}


def validate_native_run(root:Path,patch_bytes:bytes,parity_bytes:bytes):
    # These records only have validity when minted within a CI job that
    # actually compiled/reran the pinned pristine/instrumented source.
    # JSON in isolation is not a verifiable trust channel.
    original=verify_pristine_root(root)
    patch=json.loads(patch_bytes)
    parity=json.loads(parity_bytes)
    ensure(patch.get("schema")==
           "ZrotMageOriginalReadyMethodGuardWitnessProducerV1" and
           patch.get("policy_id")==POLICY and
           patch.get("original_action_ready_call_count_preserved") is True and
           patch.get("original_buff_check_count_preserved") is True and
           patch.get("new_independent_ready_method_calls")==0 and
           sha((root/PLAYER_PATH).read_bytes())==
                patch.get("player_after_sha256") and
           sha((root/MAGE_PATH).read_bytes())==
                patch.get("mage_after_sha256") and
           original["source_git_blobs"][MAGE_PATH]==CPP_BLOB,
           "SOURCE_PRODUCER_BYTES_NOT_PINNED_TO_OFFICIAL_ORIGINAL")
    ensure(parity.get("schema")=="ZrotOriginalMageMethodGuardSequenceParityV1" and
           parity.get("official_source_sha")==SIMC_COMMIT and
           parity.get("precombat_equal") is True and
           parity.get("combat_equal") is True and
           type(parity.get("combat_cast_count")) is int and
           parity["combat_cast_count"]>0 and
           parity.get("native_build_executed") is True,
           "INDEPENDENT_SOURCE_RUN_PARITY_NOT_PRESENT")
    profile=(root/PROFILE_PATH).read_bytes()
    ensure(git_blob(profile)==MAGE_PROFILE_BLOB,
           "ORIGINAL_MAGE_PROFILE_BLOB_CHANGED")
    original_mage=subprocess.run(
        ["git","-C",str(root),"show","HEAD:"+MAGE_PATH],
        capture_output=True,check=True).stdout
    rules=mage_source_rules(original_mage,profile)
    return rules,parity


def audit(root:Path,trace_bytes:bytes,patch_bytes:bytes,
          parity_bytes:bytes)->dict:
    rules,parity=validate_native_run(root,patch_bytes,parity_bytes)
    trace=trace_bytes.decode("utf-8")
    source=parse_original_attempts(trace)
    outcome=replay_cases(
        source["rows"],rules,trace_sha256=sha(trace_bytes),
        source_patch_sha256=sha(patch_bytes),
        parity_sha256=sha(parity_bytes))
    # Some original rows can fail other early gates before this override.
    # Proof is accepted ONLY for rows where the actual method was entered.
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "official_source_rev":SIMC_COMMIT,
        "Mage_source_profile_git_blob":MAGE_PROFILE_BLOB,
        "observed_actual_source_scope":"ORIGINAL_SIMC_METHOD_PRE",
        "original_native_attempts":source["original_native_attempts"],
        "unattributed_override_events":source["unattributed_method_events"],
        "raw_log_sha256":sha(trace_bytes),
        "source_patch_receipt_sha256":sha(patch_bytes),
        "same_seed_parity_receipt_sha256":sha(parity_bytes),
        "Mage_original_combat_casts_preserved":parity["combat_cast_count"],
        **outcome,
        "native_selected_action_is_post_comparator_only":True,
        "producer_claims_not_trustworthy_without_same_run_CI":True,
        "WCL_STRICT_PRE_tested":False,
        "dummy_practice_mistake_proven":False,
        "MAIN_promoted":False,
    }


def selftest():
    # Synthetic test cannot mint real source facts; it exercises only
    # pairing and scoped decision logic with distinct fake addresses.
    from general_rotation_original_pre_field_transport_v1 import MARK
    t=2414
    pre=MARK+"2414|spellslinger|5|prismatic_bolt|1|0|0"
    ptr=POINTER_MARK+"2414|prismatic_bolt|0x1111"
    guard=METHOD_MARK+"2414|prismatic_bolt|prismatic_bolt|0x1111|0"
    attempt="ZROT_NATIVE_SELECT_V1|ATTEMPT|2414|spellslinger|spellslinger|5|prismatic_bolt|0"
    one=parse_original_attempts("\n".join((pre,ptr,guard,attempt)))
    assert one["original_native_attempts"]==1
    assert one["rows"][0]["own_method_guard"]["raw_buff_stack"]==0
    from general_rotation_condition_ir_v1 import SourceBoundRequirement
    fake=SourceBoundRequirement(
        semantic_key="buff.synthetic.required",
        source_profile_git_blob="f"*40,
        source_row_sha256="a"*64,
        source_method_path="engine/class_modules/test.cpp",
        source_method_git_blob="f"*40,
        source_guard_sha256="f"*64,
        gate="necessary_eligibility",
        expression={"op":"compare","field":"buff.prismatic_bolt.active",
                    "cmp":"eq","value":True})
    ident=Identity("spellslinger::prismatic_bolt","a"*64,2414,4,0)
    evaluated=replay_cases(
        one["rows"],[(fake,ident)],
        trace_sha256="a"*64,source_patch_sha256="b"*64,
        parity_sha256="c"*64)
    assert evaluated["counts"]["scoped_NOT_READY"]==1
    assert evaluated["counts"]["guard_entries_proven"]==1
    assert evaluated["full_positive_READY"]==0
    # At the SAME SimC millisecond, two different source rows and
    # different action_t* objects must never borrow each other's
    # necessary guard. Blast's observed buff-absent gate is positive
    # only, while Bolt's observed buff-present requirement is negative.
    blast_pre=MARK+"2414|spellslinger|8|arcane_blast|1|0|0"
    blast_ptr=POINTER_MARK+"2414|arcane_blast|0x2222"
    blast_guard=METHOD_MARK+"2414|arcane_blast|arcane_blast|0x2222|0"
    blast_attempt="ZROT_NATIVE_SELECT_V1|ATTEMPT|2414|spellslinger|spellslinger|8|arcane_blast|1"
    both=parse_original_attempts("\n".join((
        pre,ptr,guard,attempt,
        blast_pre,blast_ptr,blast_guard,blast_attempt)))
    blast_rule=replace(
        fake,semantic_key="buff.synthetic.absent",
        source_row_sha256="b"*64,
        expression={"op":"compare","field":"buff.prismatic_bolt.active",
                    "cmp":"eq","value":False})
    blast_ident=Identity("spellslinger::arcane_blast","b"*64,2414,7,0)
    two=replay_cases(both["rows"],[(fake,ident),(blast_rule,blast_ident)],
                     trace_sha256="a"*64,source_patch_sha256="b"*64,
                     parity_sha256="c"*64)
    assert two["counts"]["guard_entries_proven"]==2
    assert two["counts"]["scoped_NOT_READY"]==1
    assert two["counts"]["UNKNOWN"]==1
    assert two["full_positive_READY"]==0
    for changed in (
        guard.replace("0x1111","0x2222"),
        guard.replace("|0","|1"),
        guard+"\n"+guard,
    ):
        changed_trace="\n".join((pre,ptr,changed,attempt))
        try:
            matched=parse_original_attempts(changed_trace)
            r=replay_cases(
                matched["rows"],[(fake,ident)],
                trace_sha256="a"*64,source_patch_sha256="b"*64,
                parity_sha256="c"*64)
            if r["counts"]["scoped_NOT_READY"]==1:
                raise AssertionError("FORGED_METHOD_ENTRY_WAS_ACCEPTED")
        except MageGuardReplayError:
            pass
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":17,"synthetic_authorized_as_real":False,
            "strict_action_object_pointer_link":True,
            "negative_necessary_gate_without_full_READY":True,
            "real_CPP_executed":False,"WCL_API_calls":0,
            "full_positive_READY":0}


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--raw-log",type=Path)
    p.add_argument("--patch-receipt",type=Path)
    p.add_argument("--parity-receipt",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    inp=(a.simc_root,a.raw_log,a.patch_receipt,a.parity_receipt,a.out)
    if all(x is None for x in inp):
        print(json.dumps(selftest(),sort_keys=True))
        return
    if any(x is None for x in inp):
        p.error("simc-root, raw-log, patch/parity receipts and out required")
    result=audit(a.simc_root,a.raw_log.read_bytes(),
                 a.patch_receipt.read_bytes(),
                 a.parity_receipt.read_bytes())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:
        f.write((json.dumps(result,sort_keys=True,indent=2)+"\n").encode())
    print("PINNED_MAGE_EXACT_READY_GUARD_REPLAY_SHA256="+
          sha(a.out.read_bytes()))


if __name__=="__main__":
    main()
