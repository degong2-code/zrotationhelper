#!/usr/bin/env python3
"""Method-entry PRE trace replayer with strict source provenance and UNKNOWN.

Every ENTRY is a dynamically observed original C++ action method entry,
not proof the action was fully ready or that a particular source-priority
candidate was chosen. A method can be reached outside selection; cross-call
identity and full virtual dispatch require separate evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from simc_apl_semantic_ir_v2 import git_blob, parse_profile
from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_method_pre_passive_producer_v1 import (
    SCHEMA as PRODUCER_SCHEMA, MARK, PHASE, _validate_plan, SOURCE_READS
)
from general_rotation_source_false_guard_engine_v1 import (
    verify_rules, assess_method_entry, FALSE as METHOD_FALSE
)

SCHEMA = "ZrotGenericOriginalMethodEntryPREReplayV1"


class MethodReplayError(ValueError):
    pass


def replay(log_text: str, producer_receipt:dict, manifest:dict, profile:bytes,
           false_guard_receipt:dict | None=None)->dict:
    if (producer_receipt.get("schema") != PRODUCER_SCHEMA or
        producer_receipt.get("source_phase") != PHASE or
        producer_receipt.get("new_original_ready_or_virtual_calls") != 0 or
        producer_receipt.get("source_method_count") is None):
        raise MethodReplayError("NONORIGINAL_METHOD_PRE_PRODUCER_RECEIPT")
    sites=_validate_plan(manifest)
    certified=verify_rules(false_guard_receipt,manifest) if false_guard_receipt is not None else {}
    expected={x["method_key"]:x for x in sites}
    if (set(producer_receipt["source_method_sites"])!=set(expected) or
        producer_receipt["source_method_count"]!=len(sites) or
        producer_receipt["requested_original_method_PRE_operands"]!=
            sum(len(x["fields"]) for x in sites)):
        raise MethodReplayError("SOURCE_METHOD_RECEIPT_SITE_DRIFT")
    profile_ir=parse_profile(profile,require_source=False)
    action_lists=profile_ir["action_lists"]
    keycounts=Counter()
    methods=Counter()
    raw_values=Counter()
    source_bool_value_counts=Counter()
    proven_method_false=Counter()
    false_examples=[]
    real_entries=[]
    active=None
    groups=0

    def finalize():
        nonlocal active,groups
        if active is None:
            return
        site=expected[active["source_method_key"]]
        if set(active["raw_fields"])!={
            x["operand_name"] for x in site["fields"]}:
            raise MethodReplayError("INCOMPLETE_METHOD_ENTRY_PRE_FIELDS")
        groups+=1
        methods[active["source_method_key"]]+=1
        raw_values[active["source_method_key"]]+=len(active["raw_fields"])
        for field,value in active["raw_fields"].items():
            if type(value) is bool:
                source_bool_value_counts[
                    (active["source_method_key"],field,value)]+=1
        verdict=assess_method_entry(active,certified)
        if verdict["method_return_verdict"]==METHOD_FALSE:
            proven_method_false[verdict["source_guard_rule_id"]]+=1
            if len(false_examples)<3:
                false_examples.append({
                    "source_method_key":active["source_method_key"],
                    "at_simc_ms":active["at_simc_ms"],
                    "source_row_sha256":active["source_row_sha256"],
                    "same_time_source_method_occurrence":
                        active["same_time_source_method_occurrence"],
                    "source_rule":verdict["source_guard_rule_id"],
                    "method_verdict":METHOD_FALSE,
                    "action_READY":"UNKNOWN"})
        if len(real_entries)<5:
            real_entries.append(active)
        active=None

    for line in log_text.splitlines():
        if MARK not in line:
            continue
        if line.count(MARK)!=1:
            raise MethodReplayError("MULTIPLE_METHOD_MARKERS_ON_ONE_LINE")
        source=line.split(MARK,1)[1].strip().split("|")
        if len(source)==9:
            clock,owner,ordinal,native,method,event,field_id,kind,raw=source
            call_scope_id=None
        elif len(source)==10:
            clock,owner,ordinal,native,method,event,field_id,kind,raw,scope=source
            if not scope.isdigit():
                raise MethodReplayError("METHOD_ENTRY_SCOPE_ID_INVALID")
            call_scope_id=int(scope)
        else:
            raise MethodReplayError("MALFORMED_SOURCE_METHOD_ENTRY_RECORD")
        if (not clock.isdigit() or not ordinal.isdigit() or
            not owner or not native or int(ordinal)<1):
            raise MethodReplayError("INVALID_METHOD_ENTRY_PRE_TIME_OR_OWNER")
        site=expected.get(method)
        if site is None:
            raise MethodReplayError("UNDECLARED_CXX_METHOD_MARKER")
        rows=action_lists.get(owner)
        if rows is None or int(ordinal)>len(rows):
            raise MethodReplayError("SOURCE_APL_METHOD_POINTER_INVALID")
        row=rows[int(ordinal)-1]
        scope=(int(clock),owner,int(ordinal),native,method,
               row["source_sha256"])
        if event=="ENTRY":
            finalize()
            if (field_id,kind,raw)!=("-","-","-"):
                raise MethodReplayError("METHOD_ENTRY_WITH_FAKE_FIELD")
            ix=keycounts[scope];keycounts[scope]+=1
            active={
                "at_simc_ms":int(clock),"source_list":owner,
                "ordinal_one_based":int(ordinal),"native_name_identity_only":native,
                "source_action":row["action"],"source_row_sha256":row["source_sha256"],
                "source_method_key":method,
                "source_method_body_sha256":site["source_method_body_sha256"],
                "same_time_source_method_occurrence":ix,
                "capture_phase":PHASE,"raw_fields":{},
                "explicit_method_call_scope_id":call_scope_id,
            }
        elif event=="FIELD":
            if (active is None or (
                active["at_simc_ms"],active["source_list"],
                active["ordinal_one_based"],active["native_name_identity_only"],
                active["source_method_key"],active["source_row_sha256"]) != scope or
                active["explicit_method_call_scope_id"]!=call_scope_id):
                raise MethodReplayError("METHOD_FIELD_OUTSIDE_EXACT_ENTRY_SCOPE")
            declarations=[x for x in site["fields"] if x["field_id"]==field_id]
            if len(declarations)!=1:
                raise MethodReplayError("METHOD_FIELD_NOT_SOURCE_DECLARED")
            f=declarations[0]
            if kind!=f["value_kind"] or f["operand_name"] in active["raw_fields"]:
                raise MethodReplayError("METHOD_FIELD_KIND_OR_DUPLICATE")
            if kind=="bool":
                if raw not in ("0","1"):
                    raise MethodReplayError("NON_BOOLEAN_ORIGINAL_PRE_VALUE")
                value=raw=="1"
            elif kind=="int":
                if not re.fullmatch(r"-?[0-9]+",raw):
                    raise MethodReplayError("NON_INTEGER_ORIGINAL_PRE_VALUE")
                value=int(raw)
            else:
                raise MethodReplayError("UNSUPPORTED_NATIVE_ENTRY_FIELD_KIND")
            active["raw_fields"][f["operand_name"]]=value
        else:
            raise MethodReplayError("UNRECOGNIZED_METHOD_ENTRY_EVENT")
    finalize()
    if groups==0:
        raise MethodReplayError("NO_ACTUAL_ORIGINAL_METHOD_PRE_ENTRY")
    return {
        "schema":SCHEMA, "source_profile_git_blob_sha1":git_blob(profile),
        "source_method_entry_total":groups,
        "by_method":dict(sorted(methods.items())),
        "original_method_PRE_raw_field_count":sum(raw_values.values()),
        "raw_field_counts_by_method":dict(sorted(raw_values.items())),
        "method_source_boolean_distributions":{
            f"{method}.{field}.{str(value).lower()}":count
            for (method,field,value),count in sorted(source_bool_value_counts.items())
        },
        "source_method_entry_before_original_guard":True,
        "source_false_guard_rules_certified":len(certified),
        "independent_method_return_false_total":sum(proven_method_false.values()),
        "independent_method_return_false_by_rule":dict(sorted(proven_method_false.items())),
        "bounded_method_false_examples":false_examples,
        "negative_scope":"ONE_METHOD_INVOCATION_ONLY_NOT_ACTION_READY",
        "independent_positive_method_ready_total":0,
        "source_method_entry_dynamically_observed":True,
        "dynamic_override_route_total_proven":False,
        "same_time_selection_call_pairing_proven":False,
        "full_SOURCE_ORDER_choice_proven":False,
        "full_action_READY_proven":False,
        "positive_READY_certified":0,
        "dummy_error_permitted":False,
        "bounded_raw_method_entry_examples":real_entries,
        "raw_log_not_embedded_or_exported":True,
        "WCL_API_calls":0,
    }


def selftest():
    from hashlib import sha256
    from general_rotation_method_pre_passive_producer_v1 import selftest as producer_selftest
    # The real source patcher exercises guard/source pins. This replay test
    # independently checks the event format, grouping and time/row identity.
    assert producer_selftest()["status"]=="PASS_OFFLINE_SYNTHETIC"
    profile=b'warrior="Synthetic"\nspec=fury\nactions=/rampage\n'
    r=parse_profile(profile,require_source=False)
    sha="a"*64
    original=[
        {"source_node":"base_ready","source_path":"action.cpp",
         "source_git_blob_sha1":"f"*40,"source_method_body_sha256":sha,
         "field_id":sha256(n.encode()).hexdigest(),"operand_name":n,
         "value_kind":kind}
        for n,kind in (("gcd_ready_ms","int"),("usable_while_casting","bool"))]
    original.append({"source_node":"base_action","source_path":"action.cpp",
         "source_git_blob_sha1":"f"*40,"source_method_body_sha256":"b"*64,
         "field_id":"c"*64,"operand_name":"repeat_cast_allowed",
         "value_kind":"bool"})
    from general_rotation_original_pre_capture_engine_v1 import digest
    t={"schema":"ZrotGeneralRotationOriginalPRECaptureContractV1",
       "fields":original}
    t["template_sha256"]=digest(t)
    sites=[
        {"method_key":"base_action","signature":"bool action_t::action_ready()",
         "class_anchor":None,"source_path":"action.cpp",
         "source_git_blob_sha1":"f"*40,
         "source_method_body_sha256":"b"*64,"fields":[]},
        {"method_key":"base_ready","signature":"bool action_t::ready()",
         "class_anchor":None,"source_path":"action.cpp",
         "source_git_blob_sha1":"f"*40,
         "source_method_body_sha256":sha,"fields":original[:2]}
    ]
    manifest={"schema":"ZrotGenericPassiveSelectTemplateManifestV1",
              "pinned_source_commit":
                  "b522cded8c26b97dac03fdf56e57a03ec7e8faa6",
              "templates":[t],"method_entry_sites":sites}
    receipt={"schema":PRODUCER_SCHEMA,"source_phase":PHASE,
             "new_original_ready_or_virtual_calls":0,
             "source_method_sites":["base_action","base_ready"],
             "source_method_count":2,
             "requested_original_method_PRE_operands":2}
    def mark(method,event,field="-",kind="-",value="-",ordinal=1):
        return MARK+f"20|default|{ordinal}|rampage|{method}|"+\
            f"{event}|{field}|{kind}|{value}"
    records=[
        mark("base_action","ENTRY"),
        mark("base_ready","ENTRY"),
        mark("base_ready","FIELD",sha256(b"gcd_ready_ms").hexdigest(),"int","1000"),
        mark("base_ready","FIELD",sha256(b"usable_while_casting").hexdigest(),
             "bool","1"),
        mark("base_action","ENTRY")
    ]
    result=replay("\n".join(records),receipt,manifest,profile)
    assert result["source_method_entry_total"]==3
    assert result["original_method_PRE_raw_field_count"]==2
    assert result["by_method"]=={"base_action":2,"base_ready":1}
    assert result["positive_READY_certified"]==0
    assert result["bounded_raw_method_entry_examples"][0]["source_row_sha256"]==\
        r["action_lists"]["default"][0]["source_sha256"]
    for invalid in (
        records[:3], records+[mark("base_ready","FIELD")],
        [x.replace("|default|","|invalid|",1) for x in records],
        [x.replace("|bool|1","|bool|8") for x in records],
        [x.replace("|default|1|","|default|8|") for x in records],
    ):
        try:replay("\n".join(invalid),receipt,manifest,profile)
        except MethodReplayError:pass
        else:raise AssertionError("INVALID_GENERIC_METHOD_PRE_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":10,"actual_Native_method_entries_NOT_RUN":True,
        "positive_READY_certified":0,"WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-log",type=Path)
    p.add_argument("--profile",type=Path)
    p.add_argument("--producer-receipt",type=Path)
    p.add_argument("--source-templates",type=Path)
    p.add_argument("--certified-false-guards",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    fields=(a.native_log,a.profile,a.producer_receipt,a.source_templates)
    if all(x is None for x in fields) and a.certified_false_guards is None:
        result=selftest()
    elif all(x is not None for x in fields):
        result=replay(
            a.native_log.read_text(encoding="utf-8"),
            json.loads(a.producer_receipt.read_bytes()),
            json.loads(a.source_templates.read_bytes()),
            a.profile.read_bytes(),
            json.loads(a.certified_false_guards.read_bytes())
            if a.certified_false_guards else None)
    else:
        p.error("all native-log, profile, producer-receipt, source-templates required")
    raw=canonical(result)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("xb") as f:f.write(raw)
    else:print(raw.decode(),end="")


if __name__=="__main__":
    main()
