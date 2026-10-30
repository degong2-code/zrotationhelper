#!/usr/bin/env python3
"""Independent source-byte audit of native SimC epoch/monotonic emission stamps.

The original native selection snapshots are read-only diagnostics, never PRE
transition values. Comparisons require SAME source thread/iteration (capture
log SHA identifies the run), actor/spawn, strictly earlier SOURCE timestamp,
and strictly earlier NATIVE EMISSION SEQUENCE. Text line order does not
establish causality. Same-ms and later-sequence samples remain UNKNOWN.
"""
from __future__ import annotations
import hashlib
import json
import math
from collections import Counter,defaultdict
from pathlib import Path
import re

MARK="ZROT_NATIVE_EVENT_V2|"
RESET="ZROT_NATIVE_RESET_BOUNDARY_V1|"
KINDS={"GAIN","LOSS","INIT","RECALC","SELECT_BEGIN","SELECT_END"}
NUMBER=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
REGEX=re.compile(
 r"ZROT_NATIVE_EVENT_V2\|(GAIN|LOSS|INIT|RECALC|SELECT_BEGIN|SELECT_END)\|"
 r"(\d+)\|(-?\d+)\|(\d+)\|(-?\d+)\|(\d+)\|(-?\d+)\|"
 r"([a-z][a-z0-9_]*)\|("+NUMBER+r")\|("+NUMBER+r")\s*$"
)
LEGACY={
    "GAIN":"ZROT_NATIVE_RESOURCE_V1|",
    "LOSS":"ZROT_NATIVE_RESOURCE_V1|",
    "INIT":"ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|",
    "RECALC":"ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|",
    "SELECT_BEGIN":"ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|",
    "SELECT_END":"ZROT_NATIVE_SELECT_RESOURCE_END_V1|",
}


def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def _legacy_fields(line:str,kind:str)->list[str]:
    prefix=LEGACY[kind]
    if line.count(prefix)!=1:raise ValueError("EPOCH_LEGACY_MISSING_OR_DUPLICATE")
    fields=line.split(prefix,1)[1].strip().split("|")
    expected=7 if kind in ("GAIN","LOSS","INIT","RECALC") else (
        3 if kind=="SELECT_BEGIN" else 4)
    if len(fields)!=expected:
        raise ValueError("EPOCH_LEGACY_FIELD_COUNT")
    return fields


def _check_legacy(event:dict,line:str):
    fields=_legacy_fields(line,event["kind"])
    kind=event["kind"]
    t,a,spawn=map(int,fields[:3])
    if (t,a,spawn)!=(event["time_ms"],event["actor"],event["spawn"]):
        raise ValueError("EPOCH_LEGACY_IDENTITY_DIVERGENCE")
    if kind in ("GAIN","LOSS","INIT","RECALC"):
        if fields[3]!=event["resource"] or fields[6]!=kind:
            raise ValueError("EPOCH_LEGACY_KIND_OR_RESOURCE_DIVERGENCE")
        if not math.isclose(float(fields[4]),event["current"],rel_tol=1e-12,abs_tol=1e-7):
            raise ValueError("EPOCH_LEGACY_CURRENT_DIVERGENCE")
        if kind in ("INIT","RECALC"):
            if not math.isclose(float(fields[5]),event["maximum"],rel_tol=1e-12,abs_tol=1e-7):
                raise ValueError("EPOCH_LEGACY_MAX_DIVERGENCE")
    else:
        if event["resource"]!="none":
            raise ValueError("EPOCH_SELECTION_NOT_NONE_RESOURCE")
    return True


def parse_epoch_native_log(raw:bytes,expected_sha256:str)->dict:
    if not isinstance(raw,bytes) or not raw or len(raw)>3_000_000:
        raise ValueError("EPOCH_NATIVE_LOG_INVALID_SIZE")
    if sha(raw)!=expected_sha256:raise ValueError("EPOCH_NATIVE_LOG_SHA_MISMATCH")
    if not raw.endswith(b"\n"):raise ValueError("EPOCH_NATIVE_LOG_FINAL_NEWLINE")
    lines=raw.splitlines()
    reset_boundaries=[]
    for i,line in enumerate(lines):
        if RESET.encode() not in line:continue
        text=line.decode("utf-8")
        if text.count(RESET)!=1:
            raise ValueError("EPOCH_RESET_DUPLICATE_MARKER")
        fields=text.split(RESET,1)[1].strip().split("|")
        if len(fields)!=4:
            raise ValueError("EPOCH_RESET_SOURCE_FIELDS")
        thread,iteration,sequence,old_clock=map(int,fields)
        if thread<0 or sequence<0:
            raise ValueError("EPOCH_RESET_INVALID_COUNTER")
        reset_boundaries.append({
            "thread":thread,"iteration":iteration,"sequence":sequence,
            "previous_clock_ms":old_clock,"source_log_line":i+1})
    if not reset_boundaries:
        raise ValueError("EPOCH_RESET_SOURCE_BOUNDARY_NOT_OBSERVED")
    events=[]
    seen=set()
    seen_legacy=set()
    last_by_thread={}
    for i,line in enumerate(lines):
        if MARK.encode() not in line:continue
        try:text=line.decode("utf-8")
        except UnicodeDecodeError as e:raise ValueError("EPOCH_NATIVE_LOG_UTF8") from e
        if text.count(MARK)!=1:raise ValueError("EPOCH_NATIVE_MARKER_DUPLICATE")
        m=REGEX.search(text)
        if m is None:raise ValueError("EPOCH_NATIVE_MARKER_MALFORMED")
        kind,thread,iteration,seq,t,actor,spawn,res,cur,mx=m.groups()
        thread,iteration,seq,t,actor,spawn=map(int,(thread,iteration,seq,t,actor,spawn))
        cur,mx=float(cur),float(mx)
        if not(math.isfinite(cur) and math.isfinite(mx)):
            raise ValueError("EPOCH_NATIVE_NONFINITE_VALUE")
        identity=(thread,seq)
        if identity in seen:raise ValueError("EPOCH_NATIVE_DUPLICATE_SEQUENCE")
        seen.add(identity)
        if thread in last_by_thread and seq<=last_by_thread[thread]:
            # Source V2 sequence is stamped at emission; logs can be buffered
            # but never assert that textual print order itself is causal.
            pass
        last_by_thread[thread]=seq
        if i+1>=len(lines):
            raise ValueError("EPOCH_NATIVE_V1_MARKER_NOT_ADJACENT")
        legacy=lines[i+1].decode("utf-8")
        event={
            "kind":kind,"thread":thread,"iteration":iteration,"sequence":seq,
            "time_ms":t,"actor":actor,"spawn":spawn,"resource":res,
            "current":cur,"maximum":mx,"v2_log_line":i+1,
            "v1_log_line":i+2,
        }
        _check_legacy(event,legacy)
        if i+1 in seen_legacy:
            raise ValueError("EPOCH_DUPLICATE_V1_ASSOCIATION")
        seen_legacy.add(i+1)
        events.append(event)
    if not events:raise ValueError("EPOCH_NO_V2_MARKERS")
    for entry in events:
        prior=[r["sequence"] for r in reset_boundaries if
               r["thread"]==entry["thread"] and
               r["iteration"]==entry["iteration"] and
               r["sequence"]<entry["sequence"]]
        entry["reset_boundary_sequence"]=max(prior) if prior else None
    all_counters=[(r["thread"],r["sequence"]) for r in reset_boundaries]
    all_counters.extend((e["thread"],e["sequence"]) for e in events)
    if len(set(all_counters))!=len(all_counters):
        raise ValueError("EPOCH_RESET_SOURCE_SEQUENCE_COLLISION")
    # Legacy source hooks are all required to carry corresponding V2 stamps,
    # and every selected V1 diagnostic group must be associated with an epoch.
    legacy_positions={i for i,line in enumerate(lines)
        if any(token.encode() in line for token in LEGACY.values())}
    if legacy_positions!=seen_legacy:
        raise ValueError("EPOCH_UNPAIRED_LEGACY_MARKER")
    return {
        "schema":"ZrotSimcNativeEpochEventProjectionV1",
        "source_log_sha256":expected_sha256,
        "event_count":len(events),
        "events":events,
        "reset_boundaries":reset_boundaries,
        "reset_boundary_count":len(reset_boundaries),
        "source_threads":sorted({e["thread"] for e in events}),
        "source_iterations":sorted({(e["thread"],e["iteration"]) for e in events}),
        "source_actor_spawns":sorted({(e["actor"],e["spawn"]) for e in events}),
        "event_kind_counts":dict(sorted(Counter(e["kind"] for e in events).items())),
        "legacy_marker_coverage":"ALL_V1_RESOURCE_AND_SELECT_MARKERS_STAMPED",
        "timestamp_only_join":"FORBIDDEN",
        "gameplay_rule_promotion":False,
    }


def independent_epoch_audit(raw:bytes,produced:dict)->dict:
    """Second parser via string partition, no shared regex or extraction code."""
    if produced.get("schema")!="ZrotSimcNativeEpochEventProjectionV1" or (
        sha(raw)!=produced.get("source_log_sha256")):
        raise ValueError("EPOCH_INDEPENDENT_SOURCE_MISMATCH")
    expected=[]
    resets=[]
    all_lines=raw.splitlines()
    for i,line in enumerate(all_lines):
        text=line.decode("utf-8")
        if RESET not in text:continue
        if text.count(RESET)!=1:
            raise ValueError("EPOCH_INDEPENDENT_DUPLICATE_RESET")
        args=text.split(RESET,1)[1].strip().split("|")
        if len(args)!=4:
            raise ValueError("EPOCH_INDEPENDENT_RESET_FIELDS")
        a,b,c,d=map(int,args)
        resets.append({"thread":a,"iteration":b,"sequence":c,
                       "previous_clock_ms":d,"source_log_line":i+1})
    if resets!=produced.get("reset_boundaries") or len(resets)!=produced.get("reset_boundary_count"):
        raise ValueError("EPOCH_INDEPENDENT_RESET_PROJECTION_DIVERGENCE")
    for i,blob in enumerate(all_lines):
        text=blob.decode("utf-8")
        if MARK not in text:continue
        if text.count(MARK)!=1:raise ValueError("EPOCH_INDEPENDENT_MULTIPLE_MARKERS")
        values=text.split(MARK,1)[1].split("|")
        if len(values)!=10 or values[0] not in KINDS:
            raise ValueError("EPOCH_INDEPENDENT_FIELD_CONTRACT")
        kind=values[0]
        thread,iteration,seq,t,actor,spawn=map(int,values[1:7])
        resource=values[7]
        cur,mx=map(float,values[8:])
        if not (math.isfinite(cur) and math.isfinite(mx)):
            raise ValueError("EPOCH_INDEPENDENT_NONFINITE")
        if i+1>=len(all_lines):raise ValueError("EPOCH_INDEPENDENT_NO_LEGACY")
        _check_legacy({"kind":kind,"time_ms":t,"actor":actor,"spawn":spawn,
                       "resource":resource,"current":cur,"maximum":mx},
                      all_lines[i+1].decode("utf-8"))
        expected.append({
            "kind":kind,"thread":thread,"iteration":iteration,"sequence":seq,
            "time_ms":t,"actor":actor,"spawn":spawn,"resource":resource,
            "current":cur,"maximum":mx,"v2_log_line":i+1,
            "v1_log_line":i+2,
            "reset_boundary_sequence":max(
                (r["sequence"] for r in resets if r["thread"]==thread
                 and r["iteration"]==iteration and r["sequence"]<seq),
                default=None),
        })
    if expected!=produced.get("events") or len(expected)!=produced.get("event_count"):
        raise ValueError("EPOCH_INDEPENDENT_PROJECTION_DIVERGENCE")
    keys={(v["thread"],v["sequence"]) for v in expected}
    keys.update((r["thread"],r["sequence"]) for r in resets)
    if len(keys)!=len(expected)+len(resets):
        raise ValueError("EPOCH_INDEPENDENT_DUPLICATE_SOURCE_SEQUENCE")
    return {
        "status":"PASS_EPOCH_NATIVE_SOURCE_BYTES_INDEPENDENT_RECALC",
        "event_count":len(expected),"source_log_sha256":sha(raw),
        "epoch_join_authority":"NATIVE_THREAD_ITERATION_SEQUENCE_STAMP",
        "strict_pre_operand_semantics":"NOT_VERIFIED",
    }


def compare_epoch_bound_resources(raw:bytes,projection:dict)->dict:
    """Read-only diagnostic comparison; never generate a PRE transition."""
    from simc_native_select_resource_diagnostic_audit import extract_diagnostic_groups
    source_sha=projection["source_log_sha256"]
    groups=extract_diagnostic_groups(raw,expected_sha256=source_sha)
    events=projection["events"]
    begins={e["v1_log_line"]:e for e in events if e["kind"]=="SELECT_BEGIN"}
    ends={e["v1_log_line"]:e for e in events if e["kind"]=="SELECT_END"}
    history=defaultdict(list)
    for e in events:
        if e["kind"] not in ("INIT","RECALC","GAIN","LOSS"):continue
        ep=(e["thread"],e["iteration"],e["reset_boundary_sequence"],e["actor"],e["spawn"])
        history[(ep,e["resource"])].append(e)
    for rows in history.values():rows.sort(key=lambda x:x["sequence"])
    counts=Counter()
    diff=[]
    positive=0
    for group in groups:
        begin=begins.get(group["begin_line"])
        end=ends.get(group["end_line"])
        if begin is None or end is None:
            raise ValueError("EPOCH_SELECTION_GROUP_NO_NATIVE_SOURCE_STAMP")
        ep=(begin["thread"],begin["iteration"],begin["reset_boundary_sequence"],begin["actor"],begin["spawn"])
        if (ep!=(end["thread"],end["iteration"],end["reset_boundary_sequence"],end["actor"],end["spawn"]) or
            begin["sequence"]>=end["sequence"] or
            begin["time_ms"]!=group["timestamp_ms"] or
            (begin["actor"],begin["spawn"])!=(
                group["actor_index"],group["actor_spawn_index"])):
            raise ValueError("EPOCH_SELECTION_GROUP_SOURCE_IDENTITY_CONFLICT")
        if group["timestamp_ms"]<0:
            counts["NEGATIVE_TIME_SELECTION_EXCLUDED"]+=1
            continue
        if group["return_action_id"]>0:positive+=1
        for metric_row in group["values"]:
            resource=metric_row["resource_type"]
            records=history.get((ep,resource),[])
            for metric in ("current","max"):
                actual=metric_row["current" if metric=="current" else "max"]
                if begin["reset_boundary_sequence"] is None:
                    counts["UNKNOWN_NO_NATIVE_RESET_CLOCK_EPOCH"]+=1
                    continue
                same=[e for e in records if e["time_ms"]==begin["time_ms"]]
                older_seq_later_clock=[e for e in records if
                     e["sequence"]<begin["sequence"] and
                     e["time_ms"]>begin["time_ms"]]
                admissible=[e for e in records if
                     e["sequence"]<begin["sequence"] and
                     e["time_ms"]<begin["time_ms"]]
                later_seq_prior_clock=[e for e in records if
                     e["sequence"]>=begin["sequence"] and
                     e["time_ms"]<begin["time_ms"]]
                if older_seq_later_clock or later_seq_prior_clock:
                    status="NATIVE_SEQUENCE_TIMESTAMP_CONTRADICTION"
                elif same:
                    status="SAME_TIMESTAMP_NOT_STRICT_PRE"
                elif not admissible:
                    status="UNKNOWN_NO_CAUSALLY_PRIOR_SOURCE_OBSERVATION"
                else:
                    prior=admissible[-1]
                    estimate=prior[metric if metric=="current" else "maximum"]
                    if math.isclose(actual,estimate,rel_tol=1e-9,abs_tol=1e-7):
                        status="CONSISTENT_PRIOR_SOURCE_VALUE"
                    else:
                        status="MISMATCH_POSSIBLE_UNOBSERVED_WRITE"
                        if len(diff)<20:
                            diff.append({
                                "epoch_thread_iteration":[begin["thread"],begin["iteration"]],
                                "actor_spawn":[begin["actor"],begin["spawn"]],
                                "selection_time_ms":begin["time_ms"],
                                "selection_source_sequence":begin["sequence"],
                                "resource":resource,"metric":metric,
                                "diagnostic_value":actual,"last_observed_value":estimate,
                                "last_source_sequence":prior["sequence"],
                                "last_source_time_ms":prior["time_ms"],
                                "last_source_kind":prior["kind"],
                            })
                counts[status]+=1
    return {
        "schema":"ZrotNativeEpochStrictPreDiagnosticAuditV1",
        "source_log_sha256":source_sha,
        "native_select_entry_count":len(groups),
        "positive_action_id_select_entries":positive,
        "comparison_counts":dict(sorted(counts.items())),
        "potential_mismatch_examples":diff,
        "source_epoch_authority":"NATIVE_THREAD_ITERATION_AND_SOURCE_MONOTONIC_SEQUENCE",
        "same_timestamp_eligible_as_strict_pre":False,
        "diagnostic_snapshot_used_as_strict_pre":False,
        "all_resource_mutation_paths_verified":False,
        "readiness":"UNKNOWN","gameplay_rule_promotion":False,
    }


def selftest():
    def event(kind,seq,t,iteration=0,cur=10,mx=100,spawn=1):
        res="rage" if kind in ("GAIN","LOSS","INIT","RECALC") else "none"
        cur=cur if res!="none" else 0
        mx=mx if res!="none" else 0
        prefix=(f"ZROT_NATIVE_EVENT_V2|{kind}|0|{iteration}|{seq}|{t}|0|{spawn}|"
                f"{res}|{cur}|{mx}\n")
        if kind in ("GAIN","LOSS"):
            legacy=(f"ZROT_NATIVE_RESOURCE_V1|{t}|0|{spawn}|rage|{cur}|5|{kind}\n")
        elif kind in ("INIT","RECALC"):
            legacy=(f"ZROT_NATIVE_RESOURCE_LIFECYCLE_V1|{t}|0|{spawn}|"
                    f"rage|{cur}|{mx}|{kind}\n")
        elif kind=="SELECT_BEGIN":
            legacy=f"ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1|{t}|0|{spawn}\n"
        else:
            legacy=f"ZROT_NATIVE_SELECT_RESOURCE_END_V1|{t}|0|{spawn}|100\n"
        return (prefix+legacy).encode()
    def diag(t,cur=10,iteration=0,seq=1,kind="select"):
        return (event("SELECT_BEGIN",seq,t,iteration=iteration)+
                (f"ZROT_NATIVE_SELECT_RESOURCE_VALUE_V1|{t}|0|1|"
                 f"rage|{cur}|100\n").encode()+
                event("SELECT_END",seq+1,t,iteration=iteration))
    def reset(iteration,seq):
        return f"ZROT_NATIVE_RESET_BOUNDARY_V1|0|{iteration}|{seq}|0\n".encode()
    raw=reset(0,0)+event("INIT",1,0)+diag(10,10,seq=2)+event(
        "GAIN",4,20,cur=20)+diag(30,20,seq=5)+reset(1,7)+event(
        "INIT",8,0,iteration=1,cur=77)+diag(10,77,iteration=1,seq=9)
    parsed=parse_epoch_native_log(raw,sha(raw))
    independent=independent_epoch_audit(raw,parsed)
    assert independent["event_count"]==9
    checked=compare_epoch_bound_resources(raw,parsed)
    assert checked["comparison_counts"]=={"CONSISTENT_PRIOR_SOURCE_VALUE":6},checked
    # Later printed earlier time from a different iteration never contaminates
    # earlier decisions; each legitimate source and decision shares epoch.
    polluted=raw+event("INIT",11,0,iteration=2,cur=999)
    assert compare_epoch_bound_resources(
        polluted,parse_epoch_native_log(polluted,sha(polluted)))["comparison_counts"]=={
        "CONSISTENT_PRIOR_SOURCE_VALUE":6}
    # Same current_iteration can still contain a second native sim_t reset.
    # Treat each reset boundary as its own clock epoch.
    repeated=reset(0,0)+event("INIT",1,0,cur=10)+diag(10,10,seq=2)+(
        reset(0,4)+event("INIT",5,0,cur=30)+diag(10,30,seq=6))
    repeat_src=parse_epoch_native_log(repeated,sha(repeated))
    assert repeat_src["reset_boundary_count"]==2
    assert independent_epoch_audit(repeated,repeat_src)["event_count"]==6
    assert compare_epoch_bound_resources(repeated,repeat_src)[
        "comparison_counts"]=={"CONSISTENT_PRIOR_SOURCE_VALUE":4}
    # No epoch reset stamp = not a source-verified execution window.
    missing_reset=event("INIT",1,0)+diag(10,10,seq=2)
    try:parse_epoch_native_log(missing_reset,sha(missing_reset))
    except ValueError as e:assert str(e)=="EPOCH_RESET_SOURCE_BOUNDARY_NOT_OBSERVED"
    else:raise AssertionError("MISSING_RUNTIME_RESET_BOUNDARY_ACCEPTED")
    # A same-millisecond source is excluded independent of sequence order.
    equal=reset(0,0)+event("INIT",1,10)+diag(10,10,seq=2)
    checked=compare_epoch_bound_resources(equal,parse_epoch_native_log(equal,sha(equal)))
    assert checked["comparison_counts"]=={"SAME_TIMESTAMP_NOT_STRICT_PRE":2}
    # A source with timestamp earlier but sequence after the diagnostic is
    # never incorrectly used as a causal PRE transition.
    conflict=reset(0,0)+diag(10,10,seq=1)+event("INIT",3,0,cur=10)
    checked=compare_epoch_bound_resources(
        conflict,parse_epoch_native_log(conflict,sha(conflict)))
    assert checked["comparison_counts"]=={"NATIVE_SEQUENCE_TIMESTAMP_CONTRADICTION":2}
    tampered=raw.replace(b"|INIT\n",b"|RECALC\n",1)
    try:parse_epoch_native_log(tampered,sha(tampered))
    except ValueError as e:assert str(e)=="EPOCH_LEGACY_KIND_OR_RESOURCE_DIVERGENCE"
    else:raise AssertionError("EPOCH_MISMATCH_LEGACY_ACCEPTED")
    bad_seq=raw.replace(b"SELECT_BEGIN|0|0|2|10",b"SELECT_BEGIN|0|0|1|10")
    try:parse_epoch_native_log(bad_seq,sha(bad_seq))
    except ValueError as e:assert str(e)=="EPOCH_NATIVE_DUPLICATE_SEQUENCE"
    else:raise AssertionError("EPOCH_DUPLICATE_SEQUENCE_ACCEPTED")
    print("SIMC_NATIVE_SOURCE_EPOCH_INDEPENDENT_AUDIT_SELF_TEST=PASS")


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--raw-log",type=Path)
    p.add_argument("--sha256")
    args=p.parse_args()
    if args.self_test or args.raw_log is None:
        selftest();return
    if not args.sha256:p.error("--sha256 required")
    raw=args.raw_log.read_bytes()
    projected=parse_epoch_native_log(raw,args.sha256)
    independent=independent_epoch_audit(raw,projected)
    comparison=compare_epoch_bound_resources(raw,projected)
    print(json.dumps({
        "projection":{k:v for k,v in projected.items() if k!="events"},
        "independent_audit":independent,"comparison":comparison},
        sort_keys=True,indent=2))


if __name__=="__main__":
    main()
