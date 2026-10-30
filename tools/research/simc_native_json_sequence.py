#!/usr/bin/env python3
"""Pinned SimulationCraft JSON2 sample-sequence extractor (research-only).

Uses documented report_details=1/json2 output and the upstream JSON writer's
sim.players[*].collected_data.action_sequence[_precombat] schema. This is
structured sample *action* state, not a complete reconstruction of SimC's
decision-time state or proof of optimal APL choice.
No network, no client identity is emitted; all private files remain local.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path


def _raw_verified(directory: Path):
    root=directory.resolve(strict=True)
    receipt=json.loads((root/"simc_reference_receipt.json").read_text("utf-8"))
    if receipt.get("schema")!="ZrotSimcNativeReferenceCaptureV1":
        raise ValueError("REFERENCE_RECEIPT_SCHEMA")
    if receipt.get("status") not in ("SIMC_NATIVE_CAPTURED_UNPARSED","SYNTHETIC_CAPTURE_TEST"):
        raise ValueError("REFERENCE_RECEIPT_STATUS")
    records=receipt.get("outputs")
    if not isinstance(records,list) or not records:
        raise ValueError("REFERENCE_OUTPUT_LIST_REQUIRED")
    blobs={}
    for r in records:
        if not isinstance(r,dict):
            raise ValueError("REFERENCE_OUTPUT_RECORD_INVALID")
        name=r.get("file")
        if name not in ("simc_native_log.txt","simc_effective_actions.simc",
                        "simc_native_sequence.json") or name in blobs:
            raise ValueError("REFERENCE_FILE_NOT_WHITELISTED")
        p=root/name
        if p.is_symlink() or not p.is_file():
            raise ValueError("REFERENCE_FILE_NOT_REGULAR")
        b=p.read_bytes()
        if len(b)!=r.get("bytes") or hashlib.sha256(b).hexdigest()!=r.get("sha256"):
            raise ValueError("REFERENCE_FILE_SHA_OR_SIZE_MISMATCH")
        blobs[name]=b
    if set(blobs)!={"simc_native_log.txt","simc_effective_actions.simc",
                    "simc_native_sequence.json"}:
        raise ValueError("REFERENCE_JSON2_CAPTURE_MISSING")
    for name,claim in (
        ("simc_native_log.txt","native_log_sha256"),
        ("simc_effective_actions.simc","effective_apl_sha256"),
        ("simc_native_sequence.json","native_json2_sha256"),
    ):
        if hashlib.sha256(blobs[name]).hexdigest()!=receipt.get(claim):
            raise ValueError("REFERENCE_RECEIPT_PIN_MISMATCH")
    return receipt,blobs["simc_native_sequence.json"]


def _finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def _parse_sequence(rows,kind):
    if not isinstance(rows,list):
        raise ValueError("SIMC_ACTION_SEQUENCE_NOT_LIST")
    out=[]
    previous=None
    for i,row in enumerate(rows):
        if not isinstance(row,dict) or not _finite(row.get("time")):
            raise ValueError("SIMC_ACTION_SEQUENCE_ROW_OR_TIME_INVALID")
        time=Decimal(str(row["time"]))
        try:
            timestamp=int(time*1000)
        except (InvalidOperation,OverflowError) as e:
            raise ValueError("SIMC_SEQUENCE_TIMESTAMP_INVALID") from e
        # Sample sequence is ordered. Identical timestamps are preserved
        # by ordinal; never assert t=cast state as a strictly earlier PRE state.
        if previous is not None and timestamp<previous:
            raise ValueError("SIMC_SEQUENCE_TIMESTAMP_REVERSED")
        previous=timestamp
        if "name" in row:
            name=row["name"]
            spell_id=row.get("id")
            if not isinstance(name,str) or not name or type(spell_id) is not int or spell_id<0:
                raise ValueError("SIMC_SEQUENCE_ACTION_IDENTITY_INVALID")
            queued=row.get("queue_failed",False)
            if type(queued) is not bool:
                raise ValueError("SIMC_SEQUENCE_QUEUE_STATUS_INVALID")
            record_kind="ACTION_RECORDED_QUEUE_FAILED" if queued else "SAMPLE_ACTION"
        elif "wait" in row and _finite(row["wait"]):
            name=None
            spell_id=None
            queued=None
            record_kind="WAIT_NON_ACTION"
        else:
            raise ValueError("SIMC_SEQUENCE_UNRECOGNIZED_ROW")
        resources=row.get("resources",{})
        if not isinstance(resources,dict) or any(
            not isinstance(k,str) or not _finite(v) for k,v in resources.items()):
            raise ValueError("SIMC_SEQUENCE_RESOURCE_FORMAT_INVALID")
        buffs=row.get("buffs",[])
        cooldowns=row.get("cooldowns",[])
        targets=row.get("targets",[])
        for prop,data in (("buffs",buffs),("cooldowns",cooldowns),("targets",targets)):
            if not isinstance(data,list) or any(not isinstance(x,dict) for x in data):
                raise ValueError("SIMC_SEQUENCE_"+prop.upper()+"_FORMAT_INVALID")
        out.append({
            "sequence":"PRECOMBAT" if kind=="precombat" else "COMBAT",
            "ordinal":i,
            "timestamp_ms":timestamp,
            "time_seconds":float(time),
            "record_kind":record_kind,
            "action_token":name,
            "numeric_action_id":spell_id,
            "queue_failed":queued,
            "resources_snapshot":resources,
            "buffs_snapshot":buffs,
            "cooldowns_snapshot":cooldowns,
            "targets_snapshot":targets,
            "timestamp_is_strict_pre_for_own_action":False,
            "apl_row_identity":"UNKNOWN",
            "full_readiness_reconstructed":False,
        })
    return out


def extract_json_sequence(directory: Path) -> dict:
    receipt,raw=_raw_verified(directory)
    try:
        doc=json.loads(raw)
    except (UnicodeDecodeError,json.JSONDecodeError) as e:
        raise ValueError("SIMC_JSON2_INVALID_JSON") from e
    sim=doc.get("sim") if isinstance(doc,dict) else None
    players=sim.get("players") if isinstance(sim,dict) else None
    if not isinstance(players,list) or len(players)!=1 or not isinstance(players[0],dict):
        raise ValueError("SIMC_JSON2_SINGLE_ACTOR_REQUIRED")
    collected=players[0].get("collected_data")
    if not isinstance(collected,dict) or "action_sequence" not in collected:
        raise ValueError("SIMC_JSON2_ACTION_SEQUENCE_MISSING_REPORT_DETAILS")
    pre=_parse_sequence(collected.get("action_sequence_precombat",[]),"precombat")
    combat=_parse_sequence(collected["action_sequence"],"combat")
    status="SEQUENCE_SNAPSHOTS_EXTRACTED" if combat else "NO_COMBAT_ACTION_SEQUENCE"
    return {
        "schema":"ZrotSimcNativeJson2ActionSequenceResearchV1",
        "status":status,
        "source_capture_status":receipt["status"],
        "simc_spec":receipt.get("simc_spec"),
        "source_apl_sha256":receipt["effective_apl_sha256"],
        "source_native_json2_sha256":receipt["native_json2_sha256"],
        "source_simc_executable_sha256":receipt["simc_executable_sha256"],
        "source_profile_sha256":receipt["profile_sha256"],
        "source_upstream_schema_basis":"simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926",
        "precombat_count":len(pre),
        "combat_count":len(combat),
        "precombat_sequence":pre,
        "combat_sequence":combat,
        "same_time_event_pre_leakage_forbidden":True,
        "sample_action_is_not_apl_decision_certification":True,
        "full_readiness_reconstruction":"NOT_RUN",
        "simc_apl_equivalence":"NOT_VALIDATED",
        "live_simc_capture":"NOT_RUN" if receipt["status"]=="SYNTHETIC_CAPTURE_TEST" else "CAPTURE_RECEIPT_CLAIM_UNVERIFIED",
        "authority_promotion":False,
    }


def selftest():
    import tempfile
    with tempfile.TemporaryDirectory(prefix="zrot_json2_seq_") as td:
        root=Path(td)
        apl=b"spec=fury\nactions=auto_attack\n"
        log=b"0.1 Actor performs Action 'auto_attack' (0) (50)\n"
        sample={"sim":{"players":[{"collected_data":{
            "action_sequence_precombat":[{"time":-0.5,"name":"variable",
                                         "id":0,"queue_failed":False,
                                         "resources":{"rage":0}}],
            "action_sequence":[
                {"time":0.0,"name":"auto_attack","id":0,
                 "resources":{"rage":10},"buffs":[{"name":"test","stacks":1}]},
                {"time":0.0,"wait":0.1},
                {"time":0.1,"name":"rampage","id":184367,"queue_failed":True,
                 "cooldowns":[{"name":"rampage","remains":0.0}]}
            ]
        }}]}}
        raw=json.dumps(sample).encode()
        files={
            "simc_effective_actions.simc":apl,
            "simc_native_log.txt":log,
            "simc_native_sequence.json":raw,
        }
        receipt={
            "schema":"ZrotSimcNativeReferenceCaptureV1",
            "status":"SYNTHETIC_CAPTURE_TEST","simc_spec":"fury",
            "profile_sha256":"a"*64,"simc_executable_sha256":"b"*64,
            "effective_apl_sha256":hashlib.sha256(apl).hexdigest(),
            "native_log_sha256":hashlib.sha256(log).hexdigest(),
            "native_json2_sha256":hashlib.sha256(raw).hexdigest(),
            "outputs":[{"file":k,"sha256":hashlib.sha256(v).hexdigest(),"bytes":len(v)}
                       for k,v in files.items()],
        }
        for k,v in files.items():(root/k).write_bytes(v)
        (root/"simc_reference_receipt.json").write_text(json.dumps(receipt))
        out=extract_json_sequence(root)
        assert out["status"]=="SEQUENCE_SNAPSHOTS_EXTRACTED"
        assert out["precombat_count"]==1 and out["combat_count"]==3
        assert out["combat_sequence"][0]["numeric_action_id"]==0
        assert out["combat_sequence"][1]["record_kind"]=="WAIT_NON_ACTION"
        assert out["combat_sequence"][2]["record_kind"]=="ACTION_RECORDED_QUEUE_FAILED"
        assert not out["combat_sequence"][0]["timestamp_is_strict_pre_for_own_action"]
        assert out["simc_apl_equivalence"]=="NOT_VALIDATED"
        # Tampering must fail before any JSON2 content is trusted.
        (root/"simc_native_sequence.json").write_bytes(raw+b" ")
        try:extract_json_sequence(root)
        except ValueError as e:assert str(e)=="REFERENCE_FILE_SHA_OR_SIZE_MISMATCH"
        else:raise AssertionError("TAMPERED_JSON2_ACCEPTED")
        (root/"simc_native_sequence.json").write_bytes(raw)
        bad=json.loads(json.dumps(sample))
        del bad["sim"]["players"][0]["collected_data"]["action_sequence"]
        altered=json.dumps(bad).encode()
        (root/"simc_native_sequence.json").write_bytes(altered)
        receipt["native_json2_sha256"]=hashlib.sha256(altered).hexdigest()
        receipt["outputs"][-1]["sha256"]=receipt["native_json2_sha256"]
        receipt["outputs"][-1]["bytes"]=len(altered)
        (root/"simc_reference_receipt.json").write_text(json.dumps(receipt))
        try:extract_json_sequence(root)
        except ValueError as e:
            assert str(e)=="SIMC_JSON2_ACTION_SEQUENCE_MISSING_REPORT_DETAILS"
        else:raise AssertionError("MISSING_REPORT_DETAILS_ACCEPTED")
    print("SIMC_NATIVE_JSON2_SEQUENCE_EXTRACTION_SELF_TEST=PASS")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference-dir",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test or args.reference_dir is None:
        selftest()
        return
    result=extract_json_sequence(args.reference_dir)
    output=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(output,encoding="utf-8")
    else:
        print(output)


if __name__=="__main__":
    main()
