#!/usr/bin/env python3
"""Controlled ST/2-target native SimC opener study (SimC-first hypothesis only).

Two separately captured native SimulationCraft references are accepted only
when the actor build/profile, native binary, effective APL, fixed seed and
fixed fight window are pinned and identical. The target count MUST be
different (1 vs 2), and both captures must be real or both synthetic.

JSON2 sample actions are observations, not a Strict PRE action chooser,
proof of why a difference happened, nor player-facing advice. In
particular, we do not claim optimality or feed SimC into WCL blind discovery.

No-argument mode runs synthetic offline self-test. No external network.
"""
from __future__ import annotations
from difflib import SequenceMatcher
import argparse
import json
import hashlib
from pathlib import Path
from typing import Any

from simc_native_json_sequence import extract_json_sequence

SCHEMA="ZrotNativeSimcStTwoTargetOpenerComparisonV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
MAX_PREVIEW=30


def _load(folder:Path, expected_targets:int)->tuple[dict,dict]:
    f=folder.resolve(strict=True)
    if not f.is_dir():
        raise ValueError("NOT_DIRECTORY")
    receipt=json.loads((f/"simc_reference_receipt.json").read_text(encoding="utf-8"))
    if receipt.get("schema")!="ZrotSimcNativeReferenceCaptureV1":
        raise ValueError("CAPTURE_RECEIPT_SCHEMA")
    if receipt.get("controlled_target_count")!=expected_targets:
        raise ValueError("TARGET_COUNT_CAPTURE_NOT_ATTESTED")
    if type(receipt.get("controlled_seed")) is not int:
        raise ValueError("SEED_CAPTURE_NOT_ATTESTED")
    if type(receipt.get("controlled_fight_seconds")) is not int:
        raise ValueError("FIXED_FIGHT_WINDOW_NOT_ATTESTED")
    if receipt.get("controlled_fixed_time") is not True:
        raise ValueError("FIXED_FIGHT_TIME_NOT_ATTESTED")
    sequence=extract_json_sequence(f)  # verified hashes, single actor, strict types
    if sequence.get("source_capture_status")!=receipt.get("status"):
        raise ValueError("SEQUENCE_PROVENANCE_MISMATCH")
    if sequence["source_apl_sha256"]!=receipt["effective_apl_sha256"]:
        raise ValueError("EFFECTIVE_APL_IDENTITY_MISMATCH")
    return receipt,sequence


def _fingerprints(p:dict)->dict:
    return {k:p.get(k) for k in ("profile_sha256","simc_executable_sha256",
             "effective_apl_sha256","simc_spec","controlled_seed",
             "controlled_fight_seconds","controlled_fixed_time")}


def _extract(seq:dict,window_ms:int)->dict:
    raw=seq["combat_sequence"]
    before=[r for r in raw if 0<=r["timestamp_ms"]<window_ms]
    performed=[r for r in before if r["record_kind"]=="SAMPLE_ACTION"]
    wait=[r for r in before if r["record_kind"]=="WAIT_NON_ACTION"]
    queued=[r for r in before if r["record_kind"]=="ACTION_RECORDED_QUEUE_FAILED"]
    if len(before)!=len(performed)+len(wait)+len(queued):
        raise ValueError("UNKNOWN_SEQUENCE_KIND")
    if any(r["queue_failed"] for r in performed):
        raise ValueError("QUEUE_FAILED_MISTAKEN_FOR_ACTION")
    def trim(r):
        return {
          "time_ms":r["timestamp_ms"],
          "ordinal":r["ordinal"],
          "spell_token":r["action_token"],
          "spell_id":r["numeric_action_id"],
          "resources_at_action":r["resources_snapshot"],
          "buff_count_at_action":len(r["buffs_snapshot"]),
          "cooldown_count_at_action":len(r["cooldowns_snapshot"]),
          "same_timestamp_strict_pre_state":"UNKNOWN",
          "foreground_apl_selected":"UNKNOWN",
        }
    return {
        "total_json2_combat_records":len(raw),
        "precombat_json2_records":seq["precombat_count"],
        "window_record_count":len(before),
        "window_observed_action_count":len(performed),
        "window_wait_count":len(wait),
        "window_queued_failure_count":len(queued),
        "actions":list(map(trim,performed)),
        "window_explicitly_bounded":True,
    }


def compare(st_folder:Path, two_folder:Path, *,window_seconds:int=15)->dict:
    if type(window_seconds) is not int or not 1<=window_seconds<=120:
        raise ValueError("WINDOW_OUT_OF_BOUNDS")
    st,st_seq=_load(st_folder,1)
    tw,tw_seq=_load(two_folder,2)
    if st["status"]!=tw["status"] or st["status"] not in (
        "SIMC_NATIVE_CAPTURED_UNPARSED","SYNTHETIC_CAPTURE_TEST"
    ):
        raise ValueError("MIXED_OR_UNVERIFIED_CAPTURE_PROVENANCE")
    l=_fingerprints(st);r=_fingerprints(tw)
    if l!=r or any(v is None for v in l.values()):
        raise ValueError("PROFILE_EXECUTABLE_APL_SEED_OR_FIGHT_NOT_IDENTICAL")
    a=_extract(st_seq,window_seconds*1000)
    b=_extract(tw_seq,window_seconds*1000)
    def tokens(x):
        return [(i["spell_token"],i["spell_id"]) for i in x["actions"]]
    at,bt=tokens(a),tokens(b)
    prefix=0
    while prefix<min(len(at),len(bt)) and at[prefix]==bt[prefix]:
        prefix+=1
    sm=SequenceMatcher(None,at,bt,autojunk=False)
    blocks=[{"op":tag,"st_span":[i1,i2],"two_target_span":[j1,j2]}
            for tag,i1,i2,j1,j2 in sm.get_opcodes()]
    known_target_effect=at!=bt
    return {
       "schema":SCHEMA,"scope_policy_id":POLICY,
       "source_provenance":st["status"],
       "spec":st["simc_spec"],
       "native_binary_sha256":st["simc_executable_sha256"],
       "input_profile_sha256":st["profile_sha256"],
       "effective_apl_sha256":st["effective_apl_sha256"],
       "fixed_seed":st["controlled_seed"],
       "fixed_fight_seconds":st["controlled_fight_seconds"],
       "window_seconds":window_seconds,
       "same_actor_build_apl_binary_seed_fight_window_verified":True,
       "ST":a,"TWO_TARGET":b,
       "opening_action_sequences_identical":not known_target_effect,
       "common_prefix_action_count":prefix,
       "sequence_edit_blocks":blocks,
       "observed_target_count_association":
           "DIFFERENT_SAMPLED_ACTION_SEQUENCES" if known_target_effect
           else "NO_SAMPLED_DIFFERENCE_WITHIN_OBSERVATION_WINDOW",
       "target_count_caused_specific_decision":"UNPROVEN",
       "rng_stream_effects_controlled_completely":False,
       "sample_sequence_is_not_STRICT_PRE_state":True,
       "background_proc_vs_foreground_action":"UNKNOWN",
       "precombat_separate_from_combat":True,
       "WCL_blind_candidate_lock":"NOT_RUN",
       "WCL_high_ranker_validation":"NOT_RUN",
       "general_priority_thresholds_derived":"NONE",
       "opener_optimality":"UNVERIFIED",
       "dummy_trainer_rules_ready":False,
       "MAIN_promotion":False,
    }


def selftest()->dict:
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(prefix="zrot-st2t-") as d:
        root=Path(d)
        def make(target:int,action_names:list[str]):
            folder=root/str(target)
            folder.mkdir()
            apl=b"spec=fury\nactions=rampage\n"
            native=b"0.000 Player 'Test' performs Action 'rampage' (184367) (80)\n"
            sample={"sim":{"players":[{"collected_data":{
                "action_sequence_precombat":[{"time":0,"name":"snapshot_stats","id":0}],
                "action_sequence":[
                    {"time":i*.5,"name":name,"id":184367+i,
                     "queue_failed":False,"resources":{"rage":80+i}}
                    for i,name in enumerate(action_names)
                ]+[{"time":4.5,"wait":0.1},{"time":5.,"name":"failed","id":99,
                      "queue_failed":True},{"time":16.,"name":"later","id":1}]
            }}]}}
            data={"simc_effective_actions.simc":apl,"simc_native_log.txt":native,
                  "simc_native_sequence.json":json.dumps(sample).encode()}
            for name,bytes_ in data.items():(folder/name).write_bytes(bytes_)
            receipt={"schema":"ZrotSimcNativeReferenceCaptureV1",
              "status":"SYNTHETIC_CAPTURE_TEST","controlled_target_count":target,
              "controlled_seed":31459,"controlled_fight_seconds":75,
              "controlled_fixed_time":True,"profile_sha256":"a"*64,
              "effective_apl_sha256":hashlib.sha256(apl).hexdigest(),
              "simc_executable_sha256":"b"*64,"simc_spec":"fury",
              "native_json2_sha256":hashlib.sha256(data["simc_native_sequence.json"]).hexdigest(),
              "native_log_sha256":hashlib.sha256(data["simc_native_log.txt"]).hexdigest(),
              "outputs":[{"file":name,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}
                         for name,raw in data.items()]}
            (folder/"simc_reference_receipt.json").write_text(json.dumps(receipt))
            return folder
        st=make(1,["charge","rampage","bloodthirst"])
        tw=make(2,["charge","whirlwind","bloodthirst"])
        results=compare(st,tw)
        assert results["source_provenance"]=="SYNTHETIC_CAPTURE_TEST"
        assert results["common_prefix_action_count"]==1
        assert results["observed_target_count_association"]=="DIFFERENT_SAMPLED_ACTION_SEQUENCES"
        assert results["ST"]["window_observed_action_count"]==3
        assert results["TWO_TARGET"]["window_wait_count"]==1
        assert results["ST"]["window_queued_failure_count"]==1
        assert results["WCL_blind_candidate_lock"]=="NOT_RUN"
        assert results["target_count_caused_specific_decision"]=="UNPROVEN"
        assert results["dummy_trainer_rules_ready"] is False
        count=9
        for mutation,err in [
          ({"controlled_seed":31460},"PROFILE_EXECUTABLE"),
          ({"controlled_fight_seconds":60},"PROFILE_EXECUTABLE"),
          ({"controlled_fixed_time":False},"FIXED_FIGHT_TIME"),
          ({"controlled_target_count":3},"TARGET_COUNT_CAPTURE"),
          ({"profile_sha256":"f"*64},"PROFILE_EXECUTABLE"),
          ({"status":"SIMC_NATIVE_CAPTURED_UNPARSED"},"MIXED_OR_UNVERIFIED"),
        ]:
            f=tw/"simc_reference_receipt.json"
            saved=json.loads(f.read_text())
            f.write_text(json.dumps({**saved,**mutation}))
            try:compare(st,tw)
            except ValueError as ex:assert err in str(ex),str(ex)
            else:raise AssertionError("INVALID_PAIR_ACCEPTED "+str(mutation))
            f.write_text(json.dumps(saved))
            count+=1
        for invalid in (0,121,True,1.3):
            try:compare(st,tw,window_seconds=invalid)
            except ValueError as ex:assert "WINDOW_OUT_OF_BOUNDS" in str(ex)
            else:raise AssertionError("INVALID_WINDOW_ACCEPTED")
            count+=1
        # Full-file SHA check enforces raw native JSON2 provenance.
        f=tw/"simc_native_sequence.json"; original=f.read_bytes()
        f.write_bytes(original+b" ")
        try:compare(st,tw)
        except ValueError as ex:assert "SHA_OR_SIZE_MISMATCH" in str(ex)
        else:raise AssertionError("ALTERED_JSON2_ACCEPTED")
        count+=1
    return {"result":"PASS","synthetic_case_count":count,
            "WCL_API_calls":"NOT_RUN","native_SimC_executions":"NOT_RUN_IN_SELFTEST",
            "same_timestamp_readiness":"UNKNOWN"}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--st-reference",type=Path)
    p.add_argument("--two-target-reference",type=Path)
    p.add_argument("--window-seconds",type=int,default=15)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test or (a.st_reference is None and a.two_target_reference is None):
        result=selftest()
    else:
        if a.st_reference is None or a.two_target_reference is None:
            p.error("--st-reference and --two-target-reference are required together")
        result=compare(a.st_reference,a.two_target_reference,window_seconds=a.window_seconds)
    output=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(output,encoding="utf-8")
        print("WROTE_ST_TWO_TARGET_OBSERVATIONAL_COMPARISON")
    else:print(output,end="")

if __name__=="__main__":
    main()
