#!/usr/bin/env python3
"""Independent diagnostic comparison: Native select_action ENTRY snapshot vs source events.

Read-only capture values are NEVER injected as Strict PRE transitions. Compare
them against last authenticated source-log INIT/RECALC or gain/loss records
strictly earlier than the selection timestamp, with actor spawn identity.
Same-timestamp events are AMBIGUOUS, not retroactively accepted. A mismatch
may indicate a missing direct-write, incomplete source coverage, or semantics;
it does not prove a particular class rule or gameplay priority.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import hashlib
import json
import math
import re

_SCHEMA="ZrotNativeSelectResourceDiagnosticComparisonV1"
_B="ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|"
_V="ZROT_NATIVE_SELECT_RESOURCE_VALUE_V1|"
_E="ZROT_NATIVE_SELECT_RESOURCE_END_V1|"
_NUM=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_PATTERNS={
    "BEGIN":re.compile(r"ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1\|(-?\d+)\|(\d+)\|(-?\d+)\s*$"),
    "VALUE":re.compile(r"ZROT_NATIVE_SELECT_RESOURCE_VALUE_V1\|(-?\d+)\|(\d+)\|(-?\d+)\|([a-z][a-z0-9_]*)\|("+_NUM+r")\|("+_NUM+r")\s*$"),
    "END":re.compile(r"ZROT_NATIVE_SELECT_RESOURCE_END_V1\|(-?\d+)\|(\d+)\|(-?\d+)\|(\d+)\s*$"),
}


def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def extract_diagnostic_groups(raw:bytes,*,expected_sha256:str)->list[dict]:
    if not isinstance(raw,bytes) or not raw or len(raw)>3_000_000:
        raise ValueError("DIAG_NATIVE_RAW_LOG_LIMIT")
    if sha(raw)!=expected_sha256:raise ValueError("DIAG_NATIVE_LOG_SHA_MISMATCH")
    if not raw.endswith(b"\n"):raise ValueError("DIAG_NATIVE_LOG_NEWLINE_REQUIRED")
    active=None
    results=[]
    for line_number,blob in enumerate(raw.splitlines(keepends=True),1):
        row=blob[:-1].removesuffix(b"\r")
        try:text=row.decode("utf-8")
        except UnicodeDecodeError as e:raise ValueError("DIAG_NATIVE_LOG_UTF8") from e
        markers=[(kind,token) for kind,token in (
            ("BEGIN",_B),("VALUE",_V),("END",_E)) if token in text]
        if not markers:continue
        if len(markers)!=1 or text.count(markers[0][1])!=1:
            raise ValueError("DIAG_NATIVE_MARKER_DUPLICATE")
        kind,_=markers[0]
        match=_PATTERNS[kind].search(text)
        if match is None:raise ValueError("DIAG_NATIVE_MARKER_MALFORMED")
        vals=match.groups()
        t,actor,spawn=map(int,vals[:3])
        if kind=="BEGIN":
            if active is not None:raise ValueError("DIAG_NATIVE_NESTED_BEGIN")
            active={"begin_line":line_number,"timestamp_ms":t,
                    "actor_index":actor,"actor_spawn_index":spawn,
                    "values":[]}
        else:
            if active is None:raise ValueError("DIAG_NATIVE_ORPHAN_VALUE_OR_END")
            if (t,actor,spawn)!=(active["timestamp_ms"],
                                  active["actor_index"],active["actor_spawn_index"]):
                raise ValueError("DIAG_NATIVE_GROUP_IDENTITY_OR_CLOCK_CHANGE")
            if kind=="VALUE":
                resource=vals[3]
                current,maximum=float(vals[4]),float(vals[5])
                if not (math.isfinite(current) and math.isfinite(maximum) and maximum>0):
                    raise ValueError("DIAG_NATIVE_VALUE_INVALID")
                if any(r["resource_type"]==resource for r in active["values"]):
                    raise ValueError("DIAG_NATIVE_DUPLICATE_RESOURCE_IN_GROUP")
                active["values"].append({"resource_type":resource,"current":current,
                                         "max":maximum,"native_log_line":line_number})
            else:
                active["return_action_id"]=int(vals[3])
                active["end_line"]=line_number
                results.append(active)
                active=None
                if len(results)>5000:raise ValueError("DIAG_NATIVE_TOO_MANY_SELECTIONS")
    if active is not None:raise ValueError("DIAG_NATIVE_UNCLOSED_GROUP")
    return results


def independent_diagnostic_audit(raw:bytes,groups:list[dict])->dict:
    """Separate token partition and group reconstruction; no regex re-use."""
    expected=[]
    current=None
    for ln,line in enumerate(raw.splitlines(keepends=True),1):
        try:text=line[:-1].removesuffix(b"\r").decode("utf-8")
        except UnicodeDecodeError as e:raise ValueError("DIAG_INDEPENDENT_UTF8") from e
        hit=[(kind,m) for kind,m in (
            ("BEGIN",_B),("VALUE",_V),("END",_E)) if m in text]
        if not hit:continue
        if len(hit)!=1 or text.count(hit[0][1])!=1:
            raise ValueError("DIAG_INDEPENDENT_AMBIGUOUS_MARKER")
        kind,mark=hit[0]
        tokens=text.split(mark,1)[1].split("|")
        if kind=="BEGIN":
            if current is not None or len(tokens)!=3:
                raise ValueError("DIAG_INDEPENDENT_BEGIN_CONTRACT")
            t,a,spawn=map(int,tokens)
            current={"begin_line":ln,"timestamp_ms":t,"actor_index":a,
                     "actor_spawn_index":spawn,"values":[]}
        elif kind=="VALUE":
            if current is None or len(tokens)!=6:
                raise ValueError("DIAG_INDEPENDENT_VALUE_CONTRACT")
            t,a,spawn=map(int,tokens[:3])
            if (t,a,spawn)!=(current["timestamp_ms"],current["actor_index"],
                             current["actor_spawn_index"]):
                raise ValueError("DIAG_INDEPENDENT_VALUE_IDENTITY")
            res=tokens[3]
            val,mx=map(float,tokens[4:])
            if not re.fullmatch(r"[a-z][a-z0-9_]*",res) or (
                not math.isfinite(val) or not math.isfinite(mx) or mx<=0):
                raise ValueError("DIAG_INDEPENDENT_BAD_RESOURCE")
            current["values"].append({"resource_type":res,"current":val,
                                      "max":mx,"native_log_line":ln})
        else:
            if current is None or len(tokens)!=4:
                raise ValueError("DIAG_INDEPENDENT_END_CONTRACT")
            t,a,spawn=map(int,tokens[:3])
            if (t,a,spawn)!=(current["timestamp_ms"],current["actor_index"],
                             current["actor_spawn_index"]):
                raise ValueError("DIAG_INDEPENDENT_END_IDENTITY")
            current["return_action_id"]=int(tokens[3])
            current["end_line"]=ln
            expected.append(current)
            current=None
    if current is not None or expected!=groups:
        raise ValueError("DIAG_INDEPENDENT_BYTE_PROJECTION_DIVERGENCE")
    return {"status":"PASS_EXACT_DIAGNOSTIC_NATIVE_RAW_RECALC",
            "decision_entry_count":len(expected),
            "source_log_sha256":sha(raw),
            "snapshot_is_strict_pre":False}


def _source_observations(raw_resource:dict,lifecycle:dict):
    if raw_resource["source_log_sha256"]!=lifecycle["source_log_sha256"]:
        raise ValueError("DIAG_RESOURCE_LIFECYCLE_SOURCE_MISMATCH")
    obs=defaultdict(list)
    nrows=[json.loads(line) for line in raw_resource["projected_ndjson"].splitlines()]
    receipts=raw_resource["source_line_receipts"]
    if len(nrows)!=len(receipts):
        raise ValueError("DIAG_GAIN_LOSS_RECEIPT_COUNT_MISMATCH")
    for event,receipt in zip(nrows,receipts):
        resource=receipt["resource_type"]
        actor=(receipt["native_actor_index"],receipt["native_actor_spawn_index"])
        if event["feature_key"]!="native.resource.current."+resource or (
            event["timestamp_ms"]!=receipt["native_event_timestamp_ms"]):
            raise ValueError("DIAG_GAIN_LOSS_RECEIPT_IDENTITY_MISMATCH")
        obs[(actor,resource,"current")].append(
            (event["timestamp_ms"],receipt["source_log_line"],event["value"],"GAIN_LOSS"))
    for row in lifecycle["lifecycle_rows"]:
        actor=(row["actor_index"],row["actor_spawn_index"])
        resource=row["resource_type"]
        for kind in ("current","max"):
            obs[(actor,resource,kind)].append(
                (row["native_event_timestamp_ms"],row["source_log_line"],
                 row["current" if kind=="current" else "maximum"],
                 row["source_mutation_path"]))
    for records in obs.values():records.sort(key=lambda r:(r[0],r[1]))
    return obs


def compare_diagnostics(raw_log:bytes,*,expected_log_sha256:str,
                        resource_projection:dict,lifecycle_projection:dict)->dict:
    if resource_projection["source_log_sha256"]!=expected_log_sha256 or (
        lifecycle_projection["source_log_sha256"]!=expected_log_sha256):
        raise ValueError("DIAG_UNPINNED_SOURCE_PROJECTIONS")
    groups=extract_diagnostic_groups(raw_log,expected_sha256=expected_log_sha256)
    independent=independent_diagnostic_audit(raw_log,groups)
    if not groups:raise ValueError("DIAG_NO_NATIVE_SELECT_ACTION_ENTRY")
    obs=_source_observations(resource_projection,lifecycle_projection)
    checks=Counter()
    counts=Counter()
    samples=[]
    for group in groups:
        t=group["timestamp_ms"]
        if t<0:
            counts["negative_precombat_entries_excluded"]+=1
            continue
        counts["nonnegative_select_action_entries"]+=1
        if group["return_action_id"]>0:
            counts["positive_return_action_entries"]+=1
        actor=(group["actor_index"],group["actor_spawn_index"])
        for row in group["values"]:
            resource=row["resource_type"]
            for metric in ("current","max"):
                value=row["current" if metric=="current" else "max"]
                key=(actor,resource,metric)
                history=obs.get(key,[])
                earlier=[v for v in history if v[0]<t]
                same=[v for v in history if v[0]==t]
                if same:
                    status="SAME_TIMESTAMP_SOURCE_AMBIGUITY"
                    reference=None
                elif not earlier:
                    status="UNKNOWN_NO_STRICTLY_EARLIER_SOURCE_OBSERVATION"
                    reference=None
                else:
                    reference=earlier[-1]
                    status=("CONSISTENT_WITH_LAST_OBSERVED_SOURCE_VALUE" if
                            math.isclose(float(value),float(reference[2]),
                                         abs_tol=1e-7,rel_tol=1e-9)
                            else "CONFLICT_POSSIBLE_MISSING_TRANSITION")
                checks[status]+=1
                if len(samples)<25 and status=="CONFLICT_POSSIBLE_MISSING_TRANSITION":
                    samples.append({
                        "entry_line":group["begin_line"],"actor_spawn":list(actor),
                        "timestamp_ms":t,"resource":resource,"metric":metric,
                        "actual_entry_value":value,
                        "last_strict_pre_value":reference[2],
                        "source_event_timestamp_ms":reference[0],
                        "source_log_line":reference[1],
                        "source_kind":reference[3]})
    return {
        "schema":_SCHEMA,"source_log_sha256":expected_log_sha256,
        "source_selection_diagnostic_audit":independent,
        "native_selection_entry_count":len(groups),
        "selection_entry_status_counts":dict(sorted(counts.items())),
        "comparison_counts":dict(sorted(checks.items())),
        "conflict_examples_at_most_25":samples,
        "source_completeness":"PARTIAL_RESOURCE_GAIN_LOSS_INIT_RECALC_ONLY",
        "same_timestamp_source_events_are_strict_pre":False,
        "native_entry_snapshot_used_as_reconstructed_pre":False,
        "does_not_prove_why_any_conflict_occurred":True,
        "actual_action_readiness":"UNKNOWN",
        "gameplay_rule_promotion":False}


def selftest():
    from simc_native_resource_change_probe import native_log_to_ndjson
    from simc_native_resource_lifecycle_probe import project_lifecycle_log
    def life(t,cur,mx):return (
        f"ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|{t}|0|1|rage|{cur}|{mx}|INIT\n").encode()
    def gain(t,cur):return (
        f"ZROT_NATIVE_RESOURCE_V1|{t}|0|1|rage|{cur}|10|GAIN\n").encode()
    def block(t,cur,action=1):
        return (f"ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|{t}|0|1\n"
                f"ZROT_NATIVE_SELECT_RESOURCE_VALUE_V1|{t}|0|1|rage|{cur}|100\n"
                f"ZROT_NATIVE_SELECT_RESOURCE_END_V1|{t}|0|1|{action}\n").encode()
    raw=life(0,10,100)+gain(5,20)+block(10,20)+block(15,25)+gain(20,30)+block(20,30)
    for spec in ("enhancement","fury","unholy"):
        resource=native_log_to_ndjson(raw,expected_log_sha256=sha(raw))
        lifeproj=project_lifecycle_log(raw,sha(raw))
        proof=compare_diagnostics(raw,expected_log_sha256=sha(raw),
                                  resource_projection=resource,lifecycle_projection=lifeproj)
        assert proof["comparison_counts"]=={
            "CONSISTENT_WITH_LAST_OBSERVED_SOURCE_VALUE":5,
            "CONFLICT_POSSIBLE_MISSING_TRANSITION":1,
            "SAME_TIMESTAMP_SOURCE_AMBIGUITY":1},proof
        assert proof["source_selection_diagnostic_audit"]["decision_entry_count"]==3
        assert not proof["native_entry_snapshot_used_as_reconstructed_pre"]
        assert proof["gameplay_rule_promotion"] is False
        altered=raw.replace(b"END_V1|10|0|1|1",b"END_V1|12|0|1|1")
        try:extract_diagnostic_groups(altered,expected_sha256=sha(altered))
        except ValueError as e:assert str(e)=="DIAG_NATIVE_GROUP_IDENTITY_OR_CLOCK_CHANGE"
        else:raise AssertionError("MISMATCHED_DIAG_GROUP_ACCEPTED")
        invalid=raw.replace(b"BEGIN_V1|10|0|1\n",b"BEGIN_V1|10|0|1\nZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|10|0|1\n")
        try:extract_diagnostic_groups(invalid,expected_sha256=sha(invalid))
        except ValueError as e:assert str(e)=="DIAG_NATIVE_NESTED_BEGIN"
        else:raise AssertionError("NESTED_GROUP_ACCEPTED")
        try:extract_diagnostic_groups(raw,expected_sha256="0"*64)
        except ValueError as e:assert str(e)=="DIAG_NATIVE_LOG_SHA_MISMATCH"
        else:raise AssertionError("SOURCE_SHA_MISMATCH_ACCEPTED")
    print("SIMC_NATIVE_SELECT_RESOURCE_DIAGNOSTIC_COMPARISON_SELF_TEST=PASS SPECS=3 SYNTHETIC_ONLY")


def main():
    import argparse
    from pathlib import Path
    from simc_native_resource_change_probe import native_log_to_ndjson
    from simc_native_resource_lifecycle_probe import project_lifecycle_log
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--raw-log",type=Path)
    p.add_argument("--sha256")
    args=p.parse_args()
    if args.self_test or args.raw_log is None:
        selftest();return
    if not args.sha256:p.error("--sha256 required with --raw-log")
    raw=args.raw_log.read_bytes()
    result=compare_diagnostics(raw,expected_log_sha256=args.sha256,
        resource_projection=native_log_to_ndjson(raw,expected_log_sha256=args.sha256),
        lifecycle_projection=project_lifecycle_log(raw,args.sha256))
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
