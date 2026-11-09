#!/usr/bin/env python3
"""Source-neutral initial burst buff presence -> first absent snapshot interval.

Read only previously captured original SimC JSON2 + SHA-bound native receipt.
The source buff ID is declared by an external pinned source adapter; it is
NOT guessed from spell names or WCL action counts. The inferred interval is
a snapshot observation, NOT exact aura expiry, an APL opener end, source IF
truth at decision time, or target dummy player advice.

No flags: synthetic offline tests. Arguments: old saved Native captures only.
"""
from __future__ import annotations
import argparse
from hashlib import sha256,sha1
import json
from pathlib import Path
import re
import subprocess

from simc_apl_semantic_ir_v2 import canonical

SCHEMA="ZrotGenericSimcBurstAuraSnapshotIntervalV1"
POLICY="ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"
ADAPTER_SCHEMA="ZrotSimcPinnedSourceBurstAuraAdapterV1"

class SnapshotIntervalError(ValueError): pass

def need(ok,label):
    if not ok:raise SnapshotIntervalError(label)

def is_int(x):
    return type(x) is int

def observe(rows,aura_id):
    """Return first confirmed active->absent pair, with strict ordering."""
    need(is_int(aura_id) and aura_id>0 and isinstance(rows,list),
         "INVALID_AURA_SOURCE_OR_ROWS")
    timed=[]
    for row in rows:
        need(type(row)==dict and type(row.get("time")) in (int,float) and
             row["time"]>=0,"NATIVE_JSON2_SAMPLE_TIME_INVALID")
        ts=round(row["time"]*1000)
        need(ts>=0 and abs(row["time"]*1000-ts)<1e-5,
             "NONINTEGRAL_MILLISECOND_SAMPLE")
        if "name" not in row:continue
        if row.get("queue_failed",False) is True:continue
        # A missing snapshot field is UNKNOWN, not an explicitly empty aura list.
        if "buffs" not in row:
            continue
        buffs=row["buffs"]
        need(type(buffs) is list and all(type(b) is dict and
             is_int(b.get("id")) and b["id"]>=0 for b in buffs),
             "BUFF_SNAPSHOT_UNTRUSTED")
        hit=any(b["id"]==aura_id for b in buffs)
        timed.append((ts,hit))
    need(all(timed[i][0]<=timed[i+1][0]
             for i in range(len(timed)-1)),
         "UNSORTED_JSON2_ACTION_SAMPLES")
    active_seen=False
    last_active=None
    first_active=None
    absent=None
    for ts,hit in timed:
        if hit:
            if not active_seen:first_active=ts
            active_seen=True
            last_active=ts
        elif active_seen:
            # Different states in the same timestamp cannot establish order.
            if ts == last_active:
                return {"status":"UNKNOWN_SAME_TIMESTAMP_CONFLICT",
                        "first_seen_active_ms":first_active,
                        "last_seen_active_ms":last_active,
                        "first_seen_absent_after_active_ms":None,
                        "opener_end_certified":False}
            if ts>last_active:
                absent=ts
                break
    state=("OBSERVED_BOUNDED_AURA_SNAPSHOT_EXIT" if absent is not None
           else "UNKNOWN_NOT_SEEN_ABSENT_AFTER_ACTIVE" if active_seen
           else "UNKNOWN_NO_AURA_PRESENT")
    return {
        "status":state,
        "first_seen_active_ms":first_active,
        "last_seen_active_ms":last_active,
        "first_seen_absent_after_active_ms":absent,
        "interval_is_NOT_exact_aura_expiration":True,
        "same_timestamp_not_strict_PRE":True,
        "opener_end_certified":False,
        "source_priority_or_PLAYER_CAST_certified":False,
    }

def run(source_root:Path, captures_root:Path, adapter_path:Path)->dict:
    adapter=json.loads(adapter_path.read_bytes())
    need(type(adapter)==dict and adapter.get("schema")==ADAPTER_SCHEMA and
         adapter.get("source_repo")=="simulationcraft/simc" and
         type(adapter.get("source_commit")) is str and
         re.fullmatch(r"[0-9a-f]{40}",adapter["source_commit"]) and
         type(adapter.get("specs")) is list and
         len(adapter["specs"])>=2,
         "PINNED_SOURCE_AURA_ADAPTER_INVALID")
    root=source_root.resolve(strict=True)
    need(root.is_dir(),"SOURCE_ROOT_INVALID")
    rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                       check=True,capture_output=True,text=True).stdout.strip()
    need(rev==adapter["source_commit"],
         "ORIGINAL_SIMC_SOURCE_COMMIT_NOT_PINNED")
    results=[]
    seen=set()
    for item in adapter["specs"]:
        need(type(item)==dict and
             set(item)=={"spec_key","native_spec","aura_id","source_cpp","source_anchor"} and
             re.fullmatch(r"[a-z][a-z0-9_]*",item["spec_key"]) and
             re.fullmatch(r"[a-z][a-z0-9_]*",item["native_spec"]) and
             item["spec_key"] not in seen and
             is_int(item["aura_id"]) and item["aura_id"]>0 and
             re.fullmatch(r"engine/class_modules/sc_[a-z]+\.cpp",
                          item["source_cpp"]) and
             type(item["source_anchor"]) is str and
             "find_spell( " + str(item["aura_id"]) + " )" in item["source_anchor"],
             "INVALID_OR_UNGROUNDED_BURST_AURA_MAPPING")
        seen.add(item["spec_key"])
        cpp=(root/item["source_cpp"]).resolve(strict=True)
        need(cpp.is_relative_to(root) and
             cpp.read_text(encoding="utf-8").count(item["source_anchor"])==1,
             "PINNED_CPP_AURA_SPELL_ID_LOOKUP_NOT_FOUND")
        cases=[]
        common=None
        for label,count in (("st",1),("2t",2)):
            folder=captures_root/(item["spec_key"]+"-"+label)
            receipt=json.loads((folder/"simc_reference_receipt.json").read_bytes())
            raw=(folder/"simc_native_sequence.json").read_bytes()
            need(receipt.get("schema")=="ZrotSimcNativeReferenceCaptureV1" and
                 receipt.get("status")=="SIMC_NATIVE_CAPTURED_UNPARSED" and
                 receipt.get("controlled_target_count")==count and
                 receipt.get("controlled_seed")==31459 and
                 receipt.get("controlled_fight_seconds")==30 and
                 receipt.get("simc_spec")==item["native_spec"] and
                 receipt.get("native_json2_sha256")==sha256(raw).hexdigest(),
                 "ORIGINAL_NATIVE_JSON2_RECEIPT_NOT_ATTESTED")
            fingerprint=(receipt["simc_executable_sha256"],
                         receipt["profile_sha256"],
                         receipt["effective_apl_sha256"])
            if common is None:common=fingerprint
            need(common==fingerprint,"NATIVE_CAPTURES_NOT_CONTROLLED")
            data=json.loads(raw)
            players=data.get("sim",{}).get("players",[])
            need(type(players) is list and len(players)==1 and
                 type(players[0]) is dict,
                 "SINGLE_SIMC_ACTOR_REQUIRED")
            seq=players[0].get("collected_data",{}).get("action_sequence")
            obs=observe(seq,item["aura_id"])
            cases.append({"targets":count,
                          "native_json2_sha256":sha256(raw).hexdigest(),
                          **obs})
        results.append({
            "spec_key":item["spec_key"],
            "source_cpp_path":item["source_cpp"],
            "source_cpp_git_blob_sha1":sha1(
                b"blob "+str(cpp.stat().st_size).encode()+b"\0"+
                cpp.read_bytes()).hexdigest(),
            "source_buff_numeric_id":item["aura_id"],
            "source_cpp_anchor_exactly_once":True,
            "native_same_binary_profile_apl_between_1_2_targets":True,
            "cases":cases,
            "opener_end_proof":"UNKNOWN_NOT_NATIVE_APL_PHASE_FLAG",
        })
    return {
        "schema":SCHEMA,"policy_id":POLICY,
        "source_commit_expected":adapter["source_commit"],
        "source_only_pinned_CPP_number_identity":True,
        "burst_aura_state_snapshot_intervals":results,
        "actual_Native_buff_expiration_exact":"UNKNOWN",
        "first_offensive_cooldown_window_is_NOT_opener_end":True,
        "actual_opener_exit_condition":"UNKNOWN",
        "independent_full_READY":0,
        "WCL_API_calls":0,
        "MAIN_promoted":False,
    }

def selftest():
    def a(t,active,queued=False):
        return {"time":t,"name":"x","queue_failed":queued,
                "buffs":[{"id":9}] if active else []}
    positive=observe([a(0,False),a(1,True),a(2,True),
                      a(2.25,True,True),a(3,False)],9)
    need(positive["status"]=="OBSERVED_BOUNDED_AURA_SNAPSHOT_EXIT" and
         positive["last_seen_active_ms"]==2000 and
         positive["first_seen_absent_after_active_ms"]==3000 and
         positive["opener_end_certified"] is False,
         "BURST_INTERVAL_SYNTHETIC_WRONG")
    same=observe([a(1,True),a(1,False)],9)
    need(same["status"]=="UNKNOWN_SAME_TIMESTAMP_CONFLICT",
         "SAME_TIMESTAMP_CAUSAL_LEAKAGE")
    need(observe([a(1,True)],9)["status"]==
         "UNKNOWN_NOT_SEEN_ABSENT_AFTER_ACTIVE","NO_EXIT_SHOULD_BE_UNKNOWN")
    # Missing snapshot may not be treated as an observed absent aura.
    missing=observe([a(1,True),{"time":2,"name":"x"},a(3,False)],9)
    need(missing["first_seen_absent_after_active_ms"]==3000,
         "MISSING_BUFFS_NOT_AN_EXPLICIT_ABSENCE")
    bad=0
    for val in ([a(2,True),a(1,False)],
                [{"time":-1,"name":"x","buffs":[]}],
                [{"time":1,"name":"x","buffs":[{"id":"nine"}]}]):
        try:observe(val,9)
        except SnapshotIntervalError:bad+=1
        else:raise AssertionError("BAD_BURST_OBSERVATION_ACCEPTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC",
            "positive":4,"negative":bad,
            "opener_end_inferred":False,
            "full_READY_inferred":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-root",type=Path)
    p.add_argument("--captures-root",type=Path)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if not any((a.source_root,a.captures_root,a.adapter)):
        d=selftest()
    else:
        if not all((a.source_root,a.captures_root,a.adapter)):
            p.error("Use --source-root --captures-root --adapter together")
        d=run(a.source_root,a.captures_root,a.adapter)
    b=canonical(d)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_bytes(b)
        print(json.dumps({"status":"WRITTEN","sha256":sha256(b).hexdigest()}))
    else:print(b.decode(),end="")

if __name__=="__main__":main()
