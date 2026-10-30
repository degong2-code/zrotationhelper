#!/usr/bin/env python3
"""Native source-pointer action ID consistency: evidence, not game identity.

Consumes the existing independently-audited marker-only Native bytes and
effective APL source model. Action id == SimC action_t::id (spell data ID IF
present), not a certified WCL cast ID, main-hand hit, replacement or user
keybind. No runtime source mutation, WCL access or readiness promotion.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from simc_native_if_guard_audit import audit as audit_direct_if, RE as GUARD_RE, GUARD
from simc_native_apl_eval_scope_audit import REGEX as SCOPE_RE
from simc_native_epoch_sequence_audit import parse_epoch_native_log, sha

SCHEMA = "ZrotSimcNativePointerActionIdConsistencyV1"
SOURCE_PIN = "710c2408bfd3ae4df71b8cd55cdf01f63fd6c926"
GUARD_MARK = GUARD.encode()
SCOPE_MARK = b"ZROT_NATIVE_APL_EVAL_SCOPE_V1|"


def audit(raw: bytes, expected_sha256: str, model: dict) -> dict:
    # Independently validates actual bare resource IF marker source,
    # source epoch, sequence uniqueness, nesting, and expected exact APL model.
    predecessor = audit_direct_if(raw, expected_sha256, model)
    epoch = parse_epoch_native_log(raw, expected_sha256)
    resets = epoch["reset_boundaries"]
    rows = {}
    for item in model["rows"]:
        key = (item["list"], item["list_rank"])
        if key in rows: raise ValueError("ID_AUDIT_DUPLICATE_EFFECTIVE_APL_ROW")
        rows[key] = item

    seen = {(x["thread"],x["sequence"]) for x in
            epoch["events"] + resets}
    records = []
    for raw_line in raw.splitlines():
        for marker, pattern, kind in (
            (GUARD_MARK, GUARD_RE, "GUARD"),
            (SCOPE_MARK, SCOPE_RE, "SCOPE"),
        ):
            if marker not in raw_line: continue
            line = raw_line.decode("utf-8")
            if line.count(marker.decode()) != 1:
                raise ValueError("ID_AUDIT_DUPLICATE_MARK")
            match = pattern.search(line)
            if match is None: raise ValueError("ID_AUDIT_MALFORMED_MARK")
            fields = match.groups()
            if kind=="GUARD":
                phase,th,it,seq,t,actor,spawn,apl,ordinal,action_id,result=fields
                context=None
                mode=None
            else:
                phase,th,it,seq,t,actor,spawn,mode,apl,ordinal,action_id,context=fields
                result=None
            th,it,seq,t,actor,spawn,ordinal,action_id=map(
                int,(th,it,seq,t,actor,spawn,ordinal,action_id))
            stamp=(th,seq)
            if stamp in seen:raise ValueError("ID_AUDIT_SEQUENCE_DUPLICATE")
            seen.add(stamp)
            previous=[r["sequence"] for r in resets if
                      r["thread"]==th and r["iteration"]==it
                      and r["sequence"]<seq]
            if not previous: raise ValueError("ID_AUDIT_NO_RESET")
            records.append({
                "origin":kind,"phase":phase,"thread":th,"iteration":it,
                "sequence":seq,"time_ms":t,"actor":actor,"spawn":spawn,
                "epoch":max(previous),"apl":apl,"ordinal":ordinal,
                "action_id":action_id,"context":context,"mode":mode,
                "result":result
            })
    scope_by_epoch=defaultdict(list)
    guard_by_epoch=defaultdict(list)
    for r in records:
        key=(r["thread"],r["iteration"],r["epoch"],r["actor"],r["spawn"])
        if r["origin"]=="SCOPE":
            scope_by_epoch[key].append(r)
        else:guard_by_epoch[key].append(r)
    counts=Counter()
    owner_ids=defaultdict(Counter)
    for key,items in guard_by_epoch.items():
        scopes=sorted(scope_by_epoch.get(key,()),key=lambda r:r["sequence"])
        active=[]
        scope_windows=[]
        for r in scopes:
            if r["phase"]=="BEGIN":active.append(r)
            else:
                if not active:raise ValueError("ID_AUDIT_ORPHAN_SCOPE")
                begin=active.pop()
                if (begin["apl"],begin["ordinal"],begin["action_id"],begin["context"],begin["mode"])!=(
                    r["apl"],r["ordinal"],r["action_id"],r["context"],r["mode"]):
                    raise ValueError("ID_AUDIT_SCOPE_OWNER_CHANGED")
                scope_windows.append((begin,r))
        if active:raise ValueError("ID_AUDIT_UNCLOSED_SCOPE")
        for r in items:
            if r["phase"]!="BEGIN": continue
            row=rows.get((r["apl"],r["ordinal"]))
            if row is None or row.get("guard") is None or r["ordinal"]<=0:
                counts["UNKNOWN_NO_SOURCE_IF_ROW"]+=1
                continue
            matched=[(b,e) for b,e in scope_windows
                     if b["sequence"]<r["sequence"]<e["sequence"]
                     and (b["apl"],b["ordinal"],b["action_id"])==(
                         r["apl"],r["ordinal"],r["action_id"])]
            if not matched:
                counts["UNKNOWN_NO_EXACT_ACTION_ATTEMPT_SCOPE"]+=1
                continue
            if r["action_id"]<=0:
                counts["UNKNOWN_NONPOSITIVE_NATIVE_ACTION_ID"]+=1
                continue
            # This is an actual source-pointer-equal ACTION OBJECT observed
            # in the original Native IF; not game ability identity.
            label=(r["apl"],r["ordinal"],row["command_token"])
            owner_ids[label][r["action_id"]]+=1
            counts["OBSERVED_SOURCE_POINTER_ACTION_OBJECT_ID"]+=1
    owners=[]
    for key,id_counts in sorted(owner_ids.items()):
        owners.append({
            "list":key[0],"ordinal":key[1],"action_token":key[2],
            "native_action_t_ids":dict(sorted(id_counts.items())),
            "source_action_object_id_status":(
                "SINGLE_OBSERVED_ID_NOT_GAME_ID_CERTIFIED"
                if len(id_counts)==1 else
                "CONFLICT_MULTIPLE_NATIVE_IDS_SAME_APL_ROW"
            ),
            "numeric_game_ability_identity":"UNKNOWN",
            "gameplay_action_ready":"UNKNOWN",
        })
    total=sum(counts.values())
    if total!=predecessor["guard_begin_count"]:
        raise ValueError("ID_AUDIT_TOTAL_GUARD_PROVENANCE_MISMATCH")
    return {
        "schema":SCHEMA,
        "simc_upstream_sha":SOURCE_PIN,
        "raw_sha256":expected_sha256,
        "effective_apl_sha256":model["apl_sha256"],
        "guard_begin_count":total,
        "source_owned_action_ids":owners,
        "status_counts":dict(sorted(counts.items())),
        "numeric_game_ability_identity_certified":False,
        "source_id_is_not_full_game_action_identity":True,
        "readiness_certified":0,
        "gameplay_rule_promotion":False,
        "actual_blizzard_wcl_comparison":"NOT_RUN",
        "original_native_source_auditor":"ZrotNativeDirectIfBareEvalAuditV1",
    }


def _synthetic_raw(*, id2:int=100, scope_id2:int=100) -> bytes:
    output=[]
    def put(s): output.append(s)
    put("ZROT_NATIVE_RESET_BOUNDARY_V1|0|0|0|0")
    put("ZROT_NATIVE_EVENT_V2|INIT|0|0|1|0|0|1|rage|10|100")
    put("ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|0|0|1|rage|10|100|INIT")
    put("ZROT_NATIVE_EVENT_V2|SELECT_BEGIN|0|0|2|10|0|1|none|0|0")
    put("ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|10|0|1")
    def scope(phase,seq,aid):
        put(f"ZROT_NATIVE_APL_EVAL_SCOPE_V1|{phase}|0|0|{seq}|10|0|1|FOREGROUND|default|1|{aid}|IF_ACTION_ATTEMPT")
    def guard(phase,seq,aid,val):
        put(f"ZROT_NATIVE_APL_IF_GUARD_V1|{phase}|0|0|{seq}|10|0|1|default|1|{aid}|{val}")
    scope("BEGIN",3,100);guard("BEGIN",4,100,-1)
    put("ZROT_NATIVE_APL_RESOURCE_EVAL_V1|0|0|5|10|0|1|rage|10")
    guard("END",6,100,1);scope("END",7,100)
    scope("BEGIN",8,scope_id2);guard("BEGIN",9,id2,-1)
    guard("END",10,id2,0);scope("END",11,scope_id2)
    put("ZROT_NATIVE_EVENT_V2|SELECT_END|0|0|12|10|0|1|none|0|0")
    put("ZROT_NATIVE_SELECT_RESOURCE_END_V1|10|0|1|100")
    return ("\n".join(output)+"\n").encode()


def selftest() -> None:
    model={
        "schema":"ZrotGenericSimcAplSourceHypothesisV1",
        "apl_sha256":"a"*64,"actionable_general_rotation":False,
        "rows":[{"list":"default","list_rank":1,"command_token":"synthetic_spell",
                 "source_line":3,"guard":"rage>0","role":"ACTION_TOKEN"}]
    }
    raw=_synthetic_raw()
    good=audit(raw,sha(raw),model)
    assert good["guard_begin_count"]==2
    assert good["source_owned_action_ids"][0]["native_action_t_ids"]=={100:2}
    assert good["numeric_game_ability_identity_certified"] is False
    conflict=_synthetic_raw(id2=200,scope_id2=200)
    different=audit(conflict,sha(conflict),model)
    assert different["source_owned_action_ids"][0]["source_action_object_id_status"]==(
        "CONFLICT_MULTIPLE_NATIVE_IDS_SAME_APL_ROW"
    )
    zero=_synthetic_raw(id2=0,scope_id2=0)
    missing=audit(zero,sha(zero),model)
    assert missing["status_counts"]["UNKNOWN_NONPOSITIVE_NATIVE_ACTION_ID"]==1
    # A mismatched action object and action scope is UNATTRIBUTABLE,
    # not positive evidence and not necessarily a malformed source log.
    unmatched=_synthetic_raw(id2=200,scope_id2=100)
    result=audit(unmatched,sha(unmatched),model)
    assert result["status_counts"]["UNKNOWN_NO_EXACT_ACTION_ATTEMPT_SCOPE"]==1
    assert result["source_owned_action_ids"][0]["native_action_t_ids"]=={100:1}
    for bad in (
        raw.replace(b"|END|0|0|10|",b"|END|0|0|9|"),
        raw.replace(b"|BEGIN|0|0|4|",b"|BEGIN|0|0|5|"),
    ):
        try:audit(bad,sha(bad),model)
        except ValueError:pass
        else:raise AssertionError("NATIVE_SOURCE_ID_TAMPER_ACCEPTED")
    print("SIMC_NATIVE_ACTION_ID_SOURCE_POINTER_SELF_TEST=PASS SYNTHETIC_ONLY")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--native-markers",type=Path)
    p.add_argument("--model",type=Path)
    p.add_argument("--sha256")
    args=p.parse_args()
    if args.self_test or args.native_markers is None:
        selftest();return
    if args.model is None or args.sha256 is None:
        p.error("--model and --sha256 required for replay")
    obj=audit(args.native_markers.read_bytes(),args.sha256,
              json.loads(args.model.read_text("utf-8")))
    print(json.dumps(obj,sort_keys=True,indent=2))


if __name__=="__main__":
    main()
