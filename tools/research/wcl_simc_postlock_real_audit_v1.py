#!/usr/bin/env python3
"""Post-lock evidence audit; generic engine with spec-specific pinned input contract.

Only compare SimC AFTER independent WCL raw/strict-PRE and blind SHA checks.
No-argument invocation is offline synthetic regression. No network calls.
"""
from __future__ import annotations
import argparse
from collections import Counter
from itertools import groupby
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

SCHEMA = "ZrotPinnedPostlockWclSimcComparisonFixtureV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"

class EvidenceError(ValueError): pass

def _canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False)+"\n").encode()

def _sha(data): return hashlib.sha256(data).hexdigest()

def _pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result: raise EvidenceError("DUPLICATE_JSON_KEY")
        result[k] = v
    return result

def _nonfinite(_): raise EvidenceError("NONFINITE_JSON")

def _json(data):
    return json.loads(data, object_pairs_hook=_pairs, parse_constant=_nonfinite)

def _zip(path):
    if not path.is_file() or not 0 < path.stat().st_size < 12000000:
        raise EvidenceError("MISSING_OR_OVERSIZE_SOURCE_ARCHIVE")
    result = {}
    with zipfile.ZipFile(path) as z:
        if not 1 <= len(z.infolist()) <= 40: raise EvidenceError("ARCHIVE_MEMBERS_INVALID")
        for f in z.infolist():
            n = f.filename
            if (n in result or f.is_dir() or n.startswith("/") or ".." in PurePosixPath(n).parts
                    or "\\" in n or f.file_size > 7000000):
                raise EvidenceError("UNSAFE_ARCHIVE_MEMBER")
            result[n] = z.read(f)
    if sum(map(len,result.values())) > 8000000:
        raise EvidenceError("DECOMPRESSED_ARCHIVE_EXCESSIVE")
    return result

def _num(x):
    if type(x) is int: return x
    if isinstance(x,str) and x.lstrip("-").isdigit(): return int(x)
    return None

def _spell(e):
    for key in ("abilityGameID","abilityID","guid"):
        x=_num(e.get(key))
        if x is not None: return x
    a=e.get("ability")
    if isinstance(a,dict):
        for key in ("gameID","guid","id"):
            x=_num(a.get(key))
            if x is not None: return x
    return None

def _transition(e):
    typ=str(e.get("type","")).casefold()
    stacks=_num(e.get("stack"))
    if stacks is None: stacks=_num(e.get("stacks"))
    if typ in ("applybuff","refreshbuff","applybuffstack"):
        return {"active":True,"stacks":stacks if stacks is not None and stacks>0 else None}
    if typ=="removebuff": return {"active":False,"stacks":0}
    if typ=="removebuffstack":
        return {"active":stacks>0,"stacks":max(0,stacks)} if stacks is not None else {"active":None,"stacks":None}
    return None

def independently_replay_pre(events,actor):
    """Cast rows before applying ALL same-timestamp aura transitions."""
    if type(actor) is not int or actor<=0: raise EvidenceError("BAD_ACTOR")
    ordered=sorted(enumerate(events),key=lambda x:(x[1]["timestamp"],x[0]))
    state={}
    casts=[]
    for ts,rows in groupby(ordered,key=lambda x:x[1]["timestamp"]):
        batch=list(rows)
        for _,e in batch:
            if (str(e.get("type","")).casefold() in ("cast","begincast")
                    and _num(e.get("sourceID"))==actor):
                casts.append({"timestamp":ts,"source_actor_id":actor,
                              "ability_id":_spell(e),"aura_pre":dict(state),
                              "readiness":"UNKNOWN"})
        for _,e in batch:
            if _num(e.get("targetID"))!=actor: continue
            change=_transition(e)
            spell=_spell(e)
            if change is not None and spell is not None: state[str(spell)]=change
    return casts

def audit_wcl(files,contract):
    required=("derived/blind_lock.json","derived/blind_replay.json",
              "derived/identity.json","derived/receipt.json","derived/selection.json")
    if any(k not in files for k in required): raise EvidenceError("WCL_DERIVED_MISSING")
    locked=files[required[0]]
    if _sha(locked)!=contract["wcl_blind_lock_sha256"]: raise EvidenceError("WCL_LOCK_SHA_MISMATCH")
    lock,view,gate,receipt,selection=(_json(files[k]) for k in required)
    if (lock.get("status")!="LOCKED_NUMERIC_ONLY" or lock.get("semantic_names_attached") is not False
            or lock.get("threshold_retuned_after_discovery") is not False
            or lock.get("holdout_validated") is not False or lock.get("gameplay_rule_eligible") is not False):
        raise EvidenceError("LOCK_SEMANTIC_OR_PRIORITY_PROMOTION")
    for k,expected in (("blind_lock_sha256",contract["wcl_blind_lock_sha256"]),
                       ("blind_actor_view_sha256",_sha(files[required[1]])),
                       ("actor_gate_sha256",_sha(files[required[2]])),
                       ("ranking_selection_sha256",_sha(files[required[4]]))):
        if receipt.get(k)!=expected: raise EvidenceError("RECEIPT_CHAIN_MISMATCH_"+k)
    if receipt.get("scope_policy_id")!=POLICY: raise EvidenceError("POLICY_CHANGED")
    for k,expected in (("report_code",contract["report_code"]),
                       ("fight_id",contract["fight_id"]),("actor_id",contract["actor_id"])):
        if gate.get(k)!=expected or selection.get(k)!=expected:
            raise EvidenceError("SPECIFIC_ACTOR_IDENTITY_MISMATCH")
    if (gate.get("observed_spec","").casefold()!=contract["expected_spec"].casefold()
            or gate.get("talent_build")!="UNKNOWN"
            or selection.get("exact_rank_verified") is not False
            or view.get("cooldown_or_resource_readiness")!="UNKNOWN"):
        raise EvidenceError("BUILD_RANK_OR_READINESS_INFERRED")
    identity=view["identity"]
    if (identity.get("evidence_window")!="FIGHT_START_BOUNDED"
            or identity.get("requested_window_ms")!=contract["window_ms"]
            or identity.get("full_fight_end")!=gate["fight_end_ms"]
            or identity.get("end")!=min(gate["fight_end_ms"],gate["fight_start_ms"]+contract["window_ms"])):
        raise EvidenceError("WINDOW_PROVENANCE_INVALID")
    stem=f"raw/{contract['report_code']}/fight_{contract['fight_id']}/"
    checkpoint=_json(files[stem+"checkpoint.json"])
    if checkpoint.get("schema")!="FreshWCLCheckpointV1" or checkpoint.get("complete") is not True:
        raise EvidenceError("PARTIAL_RAW_CHECKPOINT")
    if checkpoint.get("identity")!={k:v for k,v in identity.items()
                                     if k not in ("actor_id","source_replay_sha256")}:
        raise EvidenceError("CHECKPOINT_WINDOW_MISMATCH")
    raw=[]
    pages=checkpoint.get("pages",[])
    if not 1<=len(pages)<=5: raise EvidenceError("PAGE_COUNT_INVALID")
    for idx,info in enumerate(pages):
        page_name=f"page_{idx:05d}.json"
        blob=files.get(stem+page_name)
        if info.get("file")!=page_name or blob is None or _sha(blob)!=info["sha256"]:
            raise EvidenceError("RAW_PAGE_SHA_INVALID")
        page=_json(blob)
        if (page.get("schema")!="FreshWCLPageV1" or page.get("start")!=info["start"]
                or page.get("next")!=info["next"] or len(page.get("events",[]))!=info["event_count"]):
            raise EvidenceError("PAGE_LEDGER_INVALID")
        raw.extend(page["events"])
    if len(raw)!=contract["expected_raw_event_count"] or len(raw)!=view["event_count"]:
        raise EvidenceError("SOURCE_EVENT_COUNT")
    if any(type(e.get("timestamp")) not in (int,float) or
           not identity["start"]<=e["timestamp"]<=identity["end"] for e in raw):
        raise EvidenceError("RAW_TIME_OUTSIDE_WINDOW")
    computed=independently_replay_pre(raw,gate["actor_id"])
    if computed!=view["decisions"] or len(computed)!=view["decision_count"]:
        raise EvidenceError("INDEPENDENT_STRICT_PRE_MISMATCH")
    if (_sha(_canonical({k:v for k,v in view.items() if k!="replay_sha256"}))!=view["replay_sha256"]
            or lock.get("source_replay_sha256")!=[view["replay_sha256"]]):
        raise EvidenceError("BLIND_PRE_SOURCE_SHA_DIVERGED")
    tally=Counter(x["ability_id"] for x in computed if x["ability_id"] is not None)
    selected={int(row["action_spell_id"]):row["observed_event_count"] for row in lock["candidates"]}
    if selected!={k:v for k,v in tally.items() if v>=lock["prelocked_min_observations"]}:
        raise EvidenceError("LOCKED_CAST_COUNTS_NOT_FROM_RAW")
    signal=contract["diagnostic_spell_id"]
    return {"counts":tally,"locked_counts":selected,"cast_count":len(computed),
            "events":len(raw),"pages":len(pages),
            "diagnostic_id":signal,"diagnostic_casts":tally.get(signal,0),
            "diagnostic_damages":sum(_num(e.get("sourceID"))==gate["actor_id"] and
                  str(e.get("type","")).casefold()=="damage" and _spell(e)==signal for e in raw)}

def audit_simc(files,contract):
    b=files.get("public_receipt.json")
    if b is None or _sha(b)!=contract["simc_public_receipt_sha256"]:
        raise EvidenceError("SIMC_RECEIPT_UNPINNED")
    d=_json(b)
    if (d.get("schema")!="ZrotNativeSimcStTwoTargetOpenerComparisonV1"
            or d.get("scope_policy_id")!=POLICY
            or d.get("spec")!=contract["expected_spec"]
            or d.get("window_seconds")!=contract["window_ms"]/1000
            or d.get("fixed_seed")!=contract["simc_fixed_seed"]
            or d.get("ST_sample_actions")!=contract["simc_sample_actions"]
            or d.get("TWO_TARGET_sample_actions")!=contract["simc_sample_actions"]
            or d.get("common_prefix_action_count")!=contract["simc_common_prefix_actions"]
            or d.get("same_actor_build_apl_binary_seed_fight_window_verified") is not True):
        raise EvidenceError("SIMC_SOURCE_CONTRACT_DRIFT")
    for k in ("ST_first_12","TWO_TARGET_first_12"):
        if not isinstance(d.get(k),list) or len(d[k])!=12:
            raise EvidenceError("SIMC_PUBLIC_PREFIX_INCOMPLETE")
        if any(type(r.get("spell_id")) is not int or
               type(r.get("time_ms")) is not int or
               not isinstance(r.get("spell_token"),str) for r in d[k]):
            raise EvidenceError("SIMC_ACTION_SCHEMA")
    return d

def compare(wcl_files,simc_files,contract):
    # The WCL numeric lock and raw strict-PRE gate must pass BEFORE opening SimC.
    w=audit_wcl(wcl_files,contract)
    sim=audit_simc(simc_files,contract)
    wset=set(w["counts"])
    compared={}
    for name,k in (("ST","ST_first_12"),("2T","TWO_TARGET_first_12")):
        seq=sim[k]
        ids={r["spell_id"] for r in seq if r["spell_id"]>0}
        compared[name]={"prefix_action_records":len(seq),
            "prefix_last_time_ms":max(r["time_ms"] for r in seq),
            "overlap_numeric_ids":sorted(ids & wset),
            "simc_prefix_only_ids":sorted(ids-wset),
            "wcl_15s_only_ids":sorted(wset-ids),
            "controlled_same_build_and_WCL_target_count":False,
            "prefix_is_not_full_apl_or_priority_test":True}
    return {"schema":"ZrotPostlockRealWclSimcNumericAuditV1",
            "scope_policy_id":POLICY,
            "status":"POSTLOCK_OBSERVATION_ONLY",
            "source_lock_sha256":contract["wcl_blind_lock_sha256"],
            "simc_receipt_sha256":contract["simc_public_receipt_sha256"],
            "verified_wcl_raw_events":w["events"],
            "verified_wcl_event_pages":w["pages"],
            "actor_cast_decisions":w["cast_count"],
            "blind_locked_candidate_counts":[{"spell_id":k,"observations":v}
               for k,v in sorted(w["locked_counts"].items())],
            "strict_pre_recomputed_from_raw":True,
            "same_timestamp_updates_excluded":True,
            "postlock_diagnostic_id":{"numeric_spell_id":w["diagnostic_id"],
               "cast_events":w["diagnostic_casts"],
               "damage_events":w["diagnostic_damages"],
               "autoattack_hypothesis":"UNVERIFIED_MECHANIC_TRUTH_REQUIRED",
               "manual_priority_claim":False,
               "original_lock_modified":False},
            "simc_first_12_prefix_comparison":compared,
            "simc_target_count_sample_divergence":{
               "common_prefix":sim["common_prefix_action_count"],
               "ST":sim["ST_first_12"][9],
               "2T":sim["TWO_TARGET_first_12"][9],
               "causal_interpretation":"UNPROVEN"},
            "WCL_current_build_vs_SimC_equivalence":"UNKNOWN",
            "WCL_target_count_at_cast":"UNKNOWN",
            "readiness_and_alternative_actions":"UNKNOWN",
            "decision_level_apl_replay":"NOT_IMPLEMENTED_IN_THIS_AUDIT",
            "independent_holdout":"NOT_RUN",
            "priority_or_optimality_proven":False,
            "trainer_model_eligible":False,
            "MAIN_promotion":False}

def selftest():
    events=[
      {"timestamp":100,"type":"applybuff","targetID":7,"abilityGameID":9,"stack":2},
      {"timestamp":110,"type":"cast","sourceID":7,"abilityGameID":100},
      {"timestamp":110,"type":"removebuff","targetID":7,"abilityGameID":9},
      {"timestamp":120,"type":"cast","sourceID":7,"abilityGameID":101},
      {"timestamp":130,"type":"cast","sourceID":8,"abilityGameID":202},
      {"timestamp":140,"type":"cast","sourceID":7,"abilityGameID":102},
      {"timestamp":140,"type":"applybuff","targetID":7,"abilityGameID":8,"stack":1}
    ]
    casts=independently_replay_pre(events,7)
    assert [r["ability_id"] for r in casts]==[100,101,102]
    assert casts[0]["aura_pre"]["9"]=={"active":True,"stacks":2}
    assert casts[1]["aura_pre"]["9"]=={"active":False,"stacks":0}
    assert "8" not in casts[2]["aura_pre"]
    assert all(r["readiness"]=="UNKNOWN" for r in casts)
    try: _json(b'{"a":1,"a":2}')
    except EvidenceError: pass
    else: raise AssertionError("DUPLICATE_JSON_NOT_REJECTED")
    return {"status":"PASS_OFFLINE_SYNTHETIC","checks":6,
            "actual_WCL_source":"NOT_ACCESSED","actual_SimC_source":"NOT_ACCESSED"}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wcl-zip",type=Path)
    ap.add_argument("--simc-zip",type=Path)
    ap.add_argument("--contract",type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    if not a.wcl_zip and not a.simc_zip and not a.contract:
        output=selftest()
    elif a.wcl_zip and a.simc_zip and a.contract:
        cfg=_json(a.contract.read_bytes())
        if cfg.get("schema")!=SCHEMA or cfg.get("scope_policy_id")!=POLICY:
            raise EvidenceError("SCOPE_CONTRACT_MISSING")
        for k in ("wcl_blind_lock_sha256","simc_public_receipt_sha256"):
            if not isinstance(cfg.get(k),str) or not re.fullmatch("[0-9a-f]{64}",cfg[k]):
                raise EvidenceError("SOURCE_SHA_PIN_MISSING")
        output=compare(_zip(a.wcl_zip),_zip(a.simc_zip),cfg)
    else: ap.error("--wcl-zip --simc-zip --contract are required together")
    blob=_canonical(output)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(blob)
        print("POSTLOCK_AUDIT_SHA256="+_sha(blob))
    else:print(blob.decode(),end="")

if __name__=="__main__": main()
