#!/usr/bin/env python3
"""Source-pinned native action-object ID vs DBC spell-query candidate reconciliation.

The native JSON2 'action_sequence' reports action_t::id, not a certified
foreground APL decision or necessarily the DBC spell ID. Treat equality as
supporting identity evidence; disagreement as conflict, never an auto-fix.
Snapshot values at sequence timestamp are NOT Strict PRE. No spell/class
specific decisions or WCL evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from simc_spell_query_catalog import (
    _SCHEMA as CATALOG_SCHEMA,
    link_catalog_candidates_to_route,
)
from simc_apl_semantic_resolver import _SCHEMA as ROUTE_SCHEMA

_SCHEMA="ZrotSimcNativeActionInstanceIdReconciliationV1"
_SEQUENCE_SCHEMA="ZrotSimcNativeJson2ActionSequenceResearchV1"


def reconcile_native_action_ids(route:dict,catalog:dict,sequence:dict)->dict:
    if route.get("schema")!=ROUTE_SCHEMA or catalog.get("schema")!=CATALOG_SCHEMA:
        raise ValueError("NATIVE_ID_ROUTE_CATALOG_SCHEMA")
    if not isinstance(sequence,dict) or sequence.get("schema")!=_SEQUENCE_SCHEMA:
        raise ValueError("NATIVE_ID_SEQUENCE_SCHEMA")
    if sequence.get("source_capture_status") not in (
        "SIMC_NATIVE_CAPTURED_UNPARSED","SYNTHETIC_CAPTURE_TEST"):
        raise ValueError("NATIVE_ID_CAPTURE_STATUS_INVALID")
    for target,source in (
        ("simc_spec","spec"),("source_apl_sha256","source_apl_sha256"),
        ("source_profile_sha256","source_profile_sha256"),
        ("source_simc_executable_sha256","simc_executable_sha256")):
        if sequence.get(target)!=catalog.get(source):
            raise ValueError("NATIVE_ID_CAPTURE_CATALOG_PIN_MISMATCH_"+target)
    for field in ("spec","source_apl_sha256","source_profile_sha256"):
        if route.get(field)!=catalog.get(field):
            raise ValueError("NATIVE_ID_ROUTE_CATALOG_PIN_MISMATCH_"+field)
    route_executable=route.get("source_simc_executable_sha256")
    if route_executable is not None and route_executable!=catalog["simc_executable_sha256"]:
        raise ValueError("NATIVE_ID_ROUTE_BINARY_PIN_MISMATCH")
    if (route.get("gameplay_rule_promotion") is not False or
            catalog.get("gameplay_rule_promotion") is not False or
            sequence.get("authority_promotion") is not False):
        raise ValueError("NATIVE_ID_SOURCE_PREMATURE_AUTHORITY")
    linked=link_catalog_candidates_to_route(route,catalog)
    all_records=sequence.get("precombat_sequence",[])+sequence.get("combat_sequence",[])
    if (not isinstance(sequence.get("precombat_sequence"),list) or
            not isinstance(sequence.get("combat_sequence"),list)):
        raise ValueError("NATIVE_ID_SEQUENCE_RECORDS_INVALID")
    if sequence.get("precombat_count")!=len(sequence["precombat_sequence"]) or (
            sequence.get("combat_count")!=len(sequence["combat_sequence"])):
        raise ValueError("NATIVE_ID_SEQUENCE_COUNT_MISMATCH")
    observed=defaultdict(Counter)
    matched_sample_events=0
    skipped_queue_failed=skipped_zero_id=unmapped_event_tokens=0
    for event in all_records:
        if not isinstance(event,dict):
            raise ValueError("NATIVE_ID_EVENT_INVALID")
        if event.get("record_kind")!="SAMPLE_ACTION":
            if event.get("record_kind")=="ACTION_RECORDED_QUEUE_FAILED":
                skipped_queue_failed+=1
            continue
        token=event.get("action_token")
        if token not in {x["action_token"] for x in linked["action_candidates"]}:
            unmapped_event_tokens+=1
            continue
        instance_id=event.get("numeric_action_id")
        if type(instance_id) is not int or instance_id<0:
            raise ValueError("NATIVE_ID_SAMPLE_ID_INVALID")
        if instance_id==0:
            skipped_zero_id+=1
            continue
        observed[token][instance_id]+=1
        matched_sample_events+=1
    outcomes=Counter()
    details=[]
    for item in linked["action_candidates"]:
        token=item["action_token"]
        candidate_ids=set(item["spell_id_candidates"])
        sequence_ids=dict(sorted(observed[token].items()))
        if item["query_status"]=="NOT_QUERYED":
            status="NOT_QUERYED"
        elif not sequence_ids:
            status="NO_NATIVE_EXECUTION_SAMPLE"
        elif len(sequence_ids)>1:
            status="MULTIPLE_NATIVE_ACTION_IDS_NEED_REVIEW"
        elif next(iter(sequence_ids)) in candidate_ids:
            status="NATIVE_ACTION_ID_IN_DBC_NAME_CANDIDATES_UNCERTIFIED"
        else:
            status="NATIVE_ACTION_ID_NOT_IN_DBC_NAME_CANDIDATES_CONFLICT"
        outcomes[status]+=1
        details.append({
            "action_token":token,
            "source_dbc_spell_id_candidates":sorted(candidate_ids),
            "native_action_object_ids_and_counts":sequence_ids,
            "status":status,
            "sampled_sequence_is_not_apl_row_or_foreground_proof":True,
            "source_xml_sha256":item["source_xml_sha256"],
            "final_spell_id":"UNKNOWN",
            "readiness":"UNKNOWN",
        })
    return {
        "schema":_SCHEMA,
        "spec":route["spec"],
        "source_apl_sha256":route["source_apl_sha256"],
        "source_profile_sha256":route["source_profile_sha256"],
        "source_simc_executable_sha256":catalog["simc_executable_sha256"],
        "source_native_json2_sha256":sequence.get("source_native_json2_sha256"),
        "route_action_count":linked["route_action_count"],
        "queried_action_count":linked["queried_action_count"],
        "sampled_valid_source_action_events":matched_sample_events,
        "sampled_unmapped_native_event_tokens":unmapped_event_tokens,
        "skipped_queue_failed":skipped_queue_failed,
        "skipped_zero_action_id":skipped_zero_id,
        "reconciliation_status_counts":dict(sorted(outcomes.items())),
        "action_id_evidence":details,
        "native_action_t_id_is_not_necessarily_dbc_spell_id":True,
        "sequence_sample_is_not_certified_foreground_apl_selection":True,
        "json2_same_timestamp_is_not_strict_pre":True,
        "source_action_identity_certified":False,
        "all_readiness":"UNKNOWN",
        "simc_native_apl_decision_parity":"NOT_VALIDATED",
        "independent_wcl_validation":"NOT_RUN",
        "gameplay_rule_promotion":False,
    }


def selftest():
    from simc_apl_source_engine import ingest_actions
    from simc_apl_conditional_ir import compile_structural_ir
    from simc_apl_observability_contract import compile_requirements
    from simc_apl_semantic_resolver import compile_semantic_route_plan
    from simc_spell_query_catalog import make_query_plan,build_catalog,sha
    for spec,a in (("enhancement","alpha_strike"),("unholy","gamma_strike"),
                   ("hypothetical","omega_strike")):
        src=(f"spec={spec}\nactions={a}\nactions+=/zz_second\n").encode()
        profile_sha="b"*64
        binary_sha="c"*64
        model=ingest_actions(src,expected_spec=spec,
                             profile_sha256=profile_sha,
                             simc_executable_sha256=binary_sha,
                             profile_spec=spec,profile_dependencies_verified=True)
        route=compile_semantic_route_plan(
            compile_requirements(compile_structural_ir(model)))
        request=make_query_plan(route,max_queries=1)
        assert request["selected_query_tokens"]==[a]
        raw=(f'<spell_query><spell id="101" name="{a.replace("_"," ").title()}" />'
             f'<spell id="202" name="{a.replace("_"," ").title()}" /></spell_query>').encode()
        catalog=build_catalog(request,binary_sha256=binary_sha,
                              image_digest="sha256:"+"d"*64,
                              query_blobs={a:raw},query_sha256={a:sha(raw)})
        def ev(token,identity,kind="SAMPLE_ACTION"):
            return {"record_kind":kind,"action_token":token,
                    "numeric_action_id":identity,
                    "timestamp_ms":500,"timestamp_is_strict_pre_for_own_action":False}
        base={
            "schema":_SEQUENCE_SCHEMA,"source_capture_status":"SYNTHETIC_CAPTURE_TEST",
            "simc_spec":spec,"source_apl_sha256":route["source_apl_sha256"],
            "source_profile_sha256":profile_sha,
            "source_simc_executable_sha256":binary_sha,
            "source_native_json2_sha256":"e"*64,
            "precombat_sequence":[],"precombat_count":0,
            "combat_sequence":[ev(a,101),ev("zz_second",0),
                               ev(a,999,"ACTION_RECORDED_QUEUE_FAILED"),
                               ev("background_proc",555)],
            "combat_count":4,"authority_promotion":False,
        }
        out=reconcile_native_action_ids(route,catalog,base)
        assert out["reconciliation_status_counts"]=={
            "NATIVE_ACTION_ID_IN_DBC_NAME_CANDIDATES_UNCERTIFIED":1,"NOT_QUERYED":1}
        assert out["sampled_valid_source_action_events"]==1
        assert out["skipped_queue_failed"]==1
        assert out["skipped_zero_action_id"]==1
        assert out["sampled_unmapped_native_event_tokens"]==1
        assert not out["source_action_identity_certified"]
        assert out["all_readiness"]=="UNKNOWN"
        conflict=dict(base,combat_sequence=[ev(a,777)],combat_count=1)
        check=reconcile_native_action_ids(route,catalog,conflict)
        assert check["reconciliation_status_counts"][
            "NATIVE_ACTION_ID_NOT_IN_DBC_NAME_CANDIDATES_CONFLICT"]==1
        mixed=dict(base,combat_sequence=[ev(a,101),ev(a,202)],combat_count=2)
        check=reconcile_native_action_ids(route,catalog,mixed)
        assert check["reconciliation_status_counts"][
            "MULTIPLE_NATIVE_ACTION_IDS_NEED_REVIEW"]==1
        for target,value in (
            ("source_apl_sha256","0"*64),("source_profile_sha256","0"*64),
            ("source_simc_executable_sha256","0"*64)):
            changed=dict(base,**{target:value})
            try:reconcile_native_action_ids(route,catalog,changed)
            except ValueError as e:
                assert str(e)=="NATIVE_ID_CAPTURE_CATALOG_PIN_MISMATCH_"+target
            else:
                raise AssertionError("MISMATCHED_CAPTURE_ACCEPTED")
    print("SIMC_NATIVE_ACTION_ID_RECONCILIATION_SELF_TEST=PASS SPECS=3")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--route",type=Path)
    p.add_argument("--catalog",type=Path)
    p.add_argument("--native-sequence",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test or args.route is None:
        selftest()
        return
    if args.catalog is None or args.native_sequence is None:
        p.error("--catalog and --native-sequence required")
    obj=reconcile_native_action_ids(
        json.loads(args.route.read_text("utf-8")),
        json.loads(args.catalog.read_text("utf-8")),
        json.loads(args.native_sequence.read_text("utf-8")))
    content=json.dumps(obj,sort_keys=True,indent=2)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(content,encoding="utf-8")
        print("WROTE_SIMC_NATIVE_ACTION_ID_RECONCILIATION")
    else:
        print(content)


if __name__=="__main__":
    main()
