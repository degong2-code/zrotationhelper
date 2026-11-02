#!/usr/bin/env python3
"""ST-06 independent reparse of *actual* Native source obligation eval markers.

This reviewer does not import the patch producer, never synthesizes gate
readiness, and treats all function-call-time observations as non-Strict-PRE.
Reuses only the existing independent native epoch reader.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path

from simc_native_epoch_sequence_audit import (
    parse_epoch_native_log, independent_epoch_audit,
)

PREFIX = "ZROT_NATIVE_SOURCE_OBLIGATION_V1|"
GATES = {
    "fury": {"MAIN_AND_OFF_HAND_WEAPON", "DYNAMIC_RESOURCE_COST"},
    "havoc": {"SHARED_MOVEMENT_COOLDOWN"},
}
ACTION_OBJECT_IDS = {"fury":184367, "havoc":232893}


class NativeSourceGateAuditError(ValueError):
    pass


def review(raw: bytes, *, spec: str) -> dict:
    if spec not in GATES or not isinstance(raw, bytes) or not raw.endswith(b"\n"):
        raise NativeSourceGateAuditError("INVALID_NATIVE_SOURCE_SCOPE")
    digest = hashlib.sha256(raw).hexdigest()
    epoch = parse_epoch_native_log(raw,digest)
    independent = independent_epoch_audit(raw,epoch)
    if independent["status"] != "PASS_EPOCH_NATIVE_SOURCE_BYTES_INDEPENDENT_RECALC":
        raise NativeSourceGateAuditError("EPOCH_INDEPENDENT_RECALC_MISSING")
    existing_seq = {(r["thread"],r["sequence"])
                    for r in epoch["events"]+epoch["reset_boundaries"]}
    stamped = []
    for lineno, line in enumerate(raw.splitlines(),1):
        if PREFIX.encode() not in line:
            continue
        text = line.decode("utf-8")
        if text.count(PREFIX) != 1:
            raise NativeSourceGateAuditError("DUPLICATE_SOURCE_MARKER")
        items = text.split(PREFIX,1)[1].strip().split("|")
        if len(items) != 12:
            raise NativeSourceGateAuditError("SOURCE_MARKER_ARITY")
        kind = items[0]
        if kind not in GATES[spec]:
            raise NativeSourceGateAuditError("SOURCE_GATE_KIND_CROSS_SPEC")
        try:
            th,it,seq,clock,actor,spawn,action_id = (int(x) for x in items[1:8])
            nums = tuple(float(x) for x in items[8:12])
        except ValueError as exc:
            raise NativeSourceGateAuditError("SOURCE_MARKER_VALUE_PARSE") from exc
        if (min(th,seq) < 0 or action_id != ACTION_OBJECT_IDS[spec]
                or any(not math.isfinite(v) for v in nums)):
            raise NativeSourceGateAuditError("SOURCE_ACTION_ID_OR_NONFINITE")
        pair = th,seq
        if pair in existing_seq:
            raise NativeSourceGateAuditError("SOURCE_SEQUENCE_COLLISION")
        existing_seq.add(pair)
        # Encoded producer values are observation of source evaluation, not
        # independent truth of user-facing spell readiness.
        if kind == "MAIN_AND_OFF_HAND_WEAPON" and any(v not in (0,1)
                                                     for v in nums[:2]):
            raise NativeSourceGateAuditError("WEAPON_BOOLEAN_VALUES_INVALID")
        if kind == "SHARED_MOVEMENT_COOLDOWN" and nums[0] not in (0,1):
            raise NativeSourceGateAuditError("SHARED_COOLDOWN_BOOLEAN_INVALID")
        stamped.append({"kind":kind,"thread":th,"iteration":it,
                        "sequence":seq,"time_ms":clock,"actor":actor,
                        "spawn":spawn,"native_action_object_id":action_id,
                        "values":nums,"source_line":lineno})
    if not stamped:
        raise NativeSourceGateAuditError("NATIVE_OBLIGATION_EVALUATIONS_MISSING")
    resets = epoch["reset_boundaries"]
    samples=defaultdict(list)
    for item in epoch["events"]:
        key=(item["thread"],item["iteration"],
             item["reset_boundary_sequence"],item["actor"],item["spawn"])
        if item["kind"] in ("SELECT_BEGIN","SELECT_END"):
            samples[key].append(item)
    windows=defaultdict(list)
    for key, rows in samples.items():
        pending=None
        for item in sorted(rows,key=lambda x:x["sequence"]):
            if item["kind"] == "SELECT_BEGIN":
                if pending is not None:
                    raise NativeSourceGateAuditError("OVERLAPPING_SELECT")
                pending=item
            else:
                if pending is None:
                    raise NativeSourceGateAuditError("ORPHAN_SELECT_END")
                windows[key].append((pending,item))
                pending=None
        if pending is not None:
            raise NativeSourceGateAuditError("ORPHAN_SELECT_BEGIN")
    counts=Counter()
    contexts=Counter()
    examples=[]
    for ev in stamped:
        prev_reset=[r["sequence"] for r in resets
                    if r["thread"]==ev["thread"] and r["iteration"]==ev["iteration"]
                    and r["sequence"]<ev["sequence"]]
        ep=(ev["thread"],ev["iteration"],max(prev_reset) if prev_reset else None,
            ev["actor"],ev["spawn"])
        segments=[(a,b) for a,b in windows.get(ep,())
                  if a["sequence"]<ev["sequence"]<b["sequence"]]
        if not prev_reset:
            relation="UNKNOWN_NO_EPOCH"
        elif len(segments) != 1:
            relation="UNKNOWN_NOT_IN_EXACT_SELECT"
        elif segments[0][0]["time_ms"] != ev["time_ms"]:
            relation="UNKNOWN_SELECT_CLOCK_MISMATCH"
        else:
            relation="OBSERVED_INSIDE_NATIVE_SELECT_EVAL_ONLY"
        counts[ev["kind"]]+=1
        contexts[relation]+=1
        if len(examples)<15:
            examples.append({"kind":ev["kind"],"context":relation,
                             "source_sequence":ev["sequence"],
                             "actor":ev["actor"],"spawn":ev["spawn"],
                             "time_ms":ev["time_ms"]})
    return {
        "schema":"ZrotST06ActualNativeSourceObligationEvaluationAuditV1",
        "scope_spec":spec,
        "source_sha256":digest,
        "native_eval_count":len(stamped),
        "source_gate_evaluations":dict(sorted(counts.items())),
        "decision_context_classification":dict(sorted(contexts.items())),
        "examples_max_15":examples,
        "native_epoch_independent_recalculation":"PASS",
        "source_eval_is_state_transition":False,
        "strict_pre_gate_eligible":False,
        "source_gate_gameplay_ready_certified":0,
        "actual_spell_client_id_certified":0,
        "source_obligation_coverage":"PARTIAL_NATIVE_EVALUATION_SITES_ONLY",
        "unobserved_gate_status":"UNKNOWN",
        "current_game_blizzard_verification":"NOT_RUN",
        "wcl_blind_semantic_join":"FORBIDDEN",
        "main_frozen_promotion":False,
    }


def selftest():
    # No counterfeit Native result claims: only negative input contract checks.
    failures=0
    for raw, spec in ((b"", "fury"),(b"not native\n","havoc"),
                      (b"x\n","not_a_known_fixture")):
        try:review(raw,spec=spec)
        except (NativeSourceGateAuditError,ValueError):
            failures+=1
        else: raise AssertionError("INVALID_NATIVE_INPUT_ACCEPTED")
    return {"status":"PASS","synthetic_negative_contract_n":failures,
            "actual_native_execution":"NOT_RUN_IN_SELFTEST"}


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--spec")
    parser.add_argument("--marker-gzip",type=Path)
    parser.add_argument("--self-test",action="store_true")
    p=parser.parse_args()
    result=(selftest() if p.self_test else review(
        gzip.decompress(p.marker_gzip.read_bytes()),spec=p.spec))
    print(json.dumps(result,sort_keys=True,indent=2))
