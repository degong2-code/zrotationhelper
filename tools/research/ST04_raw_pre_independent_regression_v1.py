#!/usr/bin/env python3
"""ST-04 focused offline raw->Strict PRE independent-audit regression.

Exercises real ST03 evaluation and independently re-parsed raw evidence bytes.
All feature data fabricated, not current-game mechanics or WCL discovery.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import ST03_source_pre_observability_regression_v1 as st03_fixture
import ST04_raw_pre_capture_adapter_v1 as producer
import ST04_independent_raw_pre_audit_v1 as independent


def make(which="fury", *, external=False):
    base = st03_fixture.fixture(which)
    ledger = base["ledger"]
    raw = b"".join(json.dumps(event,sort_keys=True,separators=(",",":"),
                              allow_nan=False).encode("utf-8") + b"\n"
                   for event in ledger["events"])
    capture = {
        "schema": producer.SCHEMA, "phase": producer.st03.PHASE,
        "capture_ref": "ST04_SYNTHETIC_RAW_FIXTURE",
        "capture_kind": ("EXTERNAL_FEATURE_TRANSITIONS_UNVERIFIED" if external
                         else "SYNTHETIC_FEATURE_TRANSITIONS"),
        "source_authority": "CALLER_SUPPLIED_UNVERIFIED",
        "verified_producer": False, "gameplay_promotion": False,
        "event_semantics": "DECLARED_FEATURE_CHANGE_NOT_SNAPSHOT",
        "decision_timestamp_ms": ledger["decision_timestamp_ms"],
        "decision_actor_id": ledger["decision_actor_id"],
        "decision_target_id": ledger["decision_target_id"],
        "action_token": ledger["action_token"],
        "feature_bindings": deepcopy(ledger["feature_bindings"]),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_size_bytes": len(raw),
    }
    return {"raw": raw, "capture": capture, "st02_case": base["st02_case"],
            "readiness_contract": base["readiness_contract"]}


def mutate_raw(case, fn):
    events = [json.loads(x) for x in case["raw"].splitlines()]
    fn(events)
    case["raw"] = b"".join(json.dumps(e,sort_keys=True,separators=(",",":"),
                             allow_nan=False).encode()+b"\n" for e in events)
    case["capture"]["raw_sha256"] = hashlib.sha256(case["raw"]).hexdigest()
    case["capture"]["raw_size_bytes"] = len(case["raw"])


def find(events, name):
    return next(x for x in events if x["feature_key"] == name)


def tests():
    passed = []

    def success(name, case, expect_status):
        result, projected, independent_receipt = producer.run(**case)
        assert result.status == expect_status, (name,result)
        assert independent_receipt["status"] == "INDEPENDENT_MATCH_UNTRUSTED_SOURCE"
        assert independent_receipt["gameplay_ready_certified"] == 0
        assert independent_receipt["main_or_frozen_promotion"] is False
        assert len(projected["raw_line_receipts"]) > 0
        passed.append(name)
        return result

    def reject(name, fn, code):
        try:
            fn()
        except (independent.ST04IndependentFailure, producer.ST04CaptureError,
                producer.st03.ST03ContractError, ValueError) as exc:
            assert code in str(exc), (name,str(exc),code)
            passed.append(name)
        else:
            raise AssertionError("MISSING_REJECTION_"+name)

    for which in ("fury","havoc"):
        case = make(which)
        success(which+"_raw_positive_unverified_only",case,
                "ALL_DECLARED_GATES_PASS_RESEARCH_ONLY")
        case = make(which)
        feature = next(k for k in case["capture"]["feature_bindings"]
                       if k != "synthetic.cost_affordable" and
                       not k.startswith("source_gate::"))
        mutate_raw(case,lambda events: find(events,feature).update(timestamp_ms=1000))
        result=success(which+"_source_state_same_time_unknown",case,"UNKNOWN")
        assert result.excluded_same_timestamp_n == 1
        case=make(which)
        mutate_raw(case,lambda events: find(events,feature).update(timestamp_ms=1001))
        result=success(which+"_source_state_future_unknown",case,"UNKNOWN")
        assert result.excluded_future_n == 1
        case=make(which)
        mutate_raw(case,lambda events: find(events,feature).update(valid=False))
        result=success(which+"_invalid_transition_unknown",case,"UNKNOWN")
        assert result.excluded_invalid_n == 1
        case=make(which)
        def conflict(events):
            copy=deepcopy(find(events,feature))
            copy["event_id"]+="_second"
            copy["value"]=0
            events.append(copy)
        mutate_raw(case,conflict)
        success(which+"_conflicting_same_pre_unknown",case,"UNKNOWN")
        case=make(which)
        def later_unknown(events):
            copy=deepcopy(find(events,feature))
            copy["event_id"]+="_later"
            copy.update(timestamp_ms=950,status="UNKNOWN",value=None)
            events.append(copy)
        mutate_raw(case,later_unknown)
        success(which+"_later_unknown_overrides_old",case,"UNKNOWN")
        case=make(which)
        gid=case["st02_case"]["declared_gates"][0]["gate_id"]
        mutate_raw(case,lambda events: find(events,"source_gate::"+gid).update(value=0))
        success(which+"_declared_gate_negative_not_ready",case,
                "OBSERVED_NEGATIVE_RESEARCH_ONLY")
        case=make(which)
        mutate_raw(case,lambda events: find(events,"synthetic.cost_affordable").update(value=0))
        success(which+"_upstream_known_negative",case,"OBSERVED_NEGATIVE_RESEARCH_ONLY")

    case=make("havoc")
    case["capture"]["decision_target_id"]=None
    success("missing_target_context_unknown",case,"UNKNOWN")
    case=make("havoc")
    mutate_raw(case,lambda events: find(events,"target.position_relation").update(subject_id="OTHER_TARGET"))
    success("target_switch_unknown",case,"UNKNOWN")
    case=make("fury",external=True)
    result=success("external_capture_explicitly_unverified",case,
                   "ALL_DECLARED_GATES_PASS_RESEARCH_ONLY")
    assert result.source_authenticity == "NOT_INDEPENDENTLY_VERIFIED"
    case=make("fury")
    mutate_raw(case,lambda events: find(events,"synthetic.cost_affordable").update(timestamp_ms=1000))
    result=success("real_provider_same_time_unknown",case,"UNKNOWN")
    assert result.upstream_readiness == "UNKNOWN"
    case=make("fury")
    case["st02_case"]["declared_gates"].pop()
    success("source_policy_missing_gate_unknown",case,"UNKNOWN")

    case=make()
    case["raw"]+=b" "
    reject("raw_bytes_tamper_sha_rejected",lambda:producer.reconstruct(case["raw"],case["capture"]),
           "RAW_FINAL_NEWLINE_REQUIRED")
    case=make()
    case["capture"]["raw_sha256"]="0"*64
    reject("raw_capture_wrong_sha_rejected",lambda:producer.reconstruct(case["raw"],case["capture"]),
           "RAW_SOURCE_BYTES_SHA_MISMATCH")
    case=make()
    case["capture"]["verified_producer"]=True
    reject("producer_auth_claim_rejected",lambda:producer.reconstruct(case["raw"],case["capture"]),
           "CAPTURE_PREMATURE_PROMOTION")
    case=make()
    case["capture"]["event_semantics"]="AT_ACTION_SNAPSHOT"
    reject("snapshot_semantics_rejected",lambda:producer.reconstruct(case["raw"],case["capture"]),
           "RAW_SNAPSHOT_OR_POST_ACTION_FORBIDDEN")
    case=make()
    case["capture"]["phase"]="WCL_BLIND"
    reject("WCL_blind_leak_rejected",lambda:producer.reconstruct(case["raw"],case["capture"]),
           "BLIND_WCL_SEMANTIC_LEAKAGE_FORBIDDEN")
    case=make()
    first=case["raw"].splitlines()[0]
    # Inject duplicate JSON key (raw must remain byte-pinned).
    malformed=first[:-1]+b',"event_id":"duplicate"}'
    case["raw"]=malformed+b"\n"+b"\n".join(case["raw"].splitlines()[1:])+b"\n"
    case["capture"]["raw_sha256"]=hashlib.sha256(case["raw"]).hexdigest()
    case["capture"]["raw_size_bytes"]=len(case["raw"])
    reject("duplicate_JSON_key_rejected",lambda:producer.reconstruct(case["raw"],case["capture"]),
           "RAW_DUPLICATE_JSON_KEY")

    case=make()
    ledger, projection=producer.reconstruct(case["raw"],case["capture"])
    ledger["events"][0]["value"]=777
    ledger["ledger_sha256"]=producer.st03.digest(ledger["events"])
    reject("fake_pre_transition_recomputed_ledger_rejected",
           lambda:independent.check_raw_projection(case["raw"],case["capture"],ledger,projection),
           "INDEPENDENT_LEDGER_PROJECTION_CONFLICT")
    case=make()
    ledger, projection=producer.reconstruct(case["raw"],case["capture"])
    projection["raw_line_receipts"][0]["raw_line_sha256"]="0"*64
    reject("fake_raw_line_provenance_rejected",
           lambda:independent.check_raw_projection(case["raw"],case["capture"],ledger,projection),
           "INDEPENDENT_LINE_RECEIPT_CONFLICT")
    case=make()
    result, projected, _=producer.run(**case)
    ledger,_=producer.reconstruct(case["raw"],case["capture"])
    forged=result.to_dict()
    forged["required_state_diagnostics"]["synthetic.cost_affordable"]["status"]="OBSERVED_FORGED"
    reject("fake_pre_observability_receipt_rejected",
           lambda:independent.check_pre_decision(case["raw"],case["capture"],ledger,projected,
                                                 case["st02_case"],case["readiness_contract"],forged),
           "INDEPENDENT_STATE_DIAGNOSTIC_CONFLICT")
    case=make()
    result, projected, _=producer.run(**case)
    ledger,_=producer.reconstruct(case["raw"],case["capture"])
    forged=result.to_dict()
    gid=next(iter(forged["source_gate_diagnostics"]))
    forged["source_gate_diagnostics"][gid]="SOURCE_GATE_FABRICATED"
    reject("fake_gate_diagnostic_receipt_rejected",
           lambda:independent.check_pre_decision(case["raw"],case["capture"],ledger,projected,
                                                 case["st02_case"],case["readiness_contract"],forged),
           "INDEPENDENT_GATE_DIAGNOSTIC_CONFLICT")
    case=make()
    result, projected, _=producer.run(**case)
    ledger,_=producer.reconstruct(case["raw"],case["capture"])
    forged=result.to_dict()
    forged["status"]="UNKNOWN"
    reject("fake_research_verdict_receipt_rejected",
           lambda:independent.check_pre_decision(case["raw"],case["capture"],ledger,projected,
                                                 case["st02_case"],case["readiness_contract"],forged),
           "INDEPENDENT_RESEARCH_VERDICT_CONFLICT")
    case=make()
    result, projected, _=producer.run(**case)
    ledger,_=producer.reconstruct(case["raw"],case["capture"])
    forged=result.to_dict()
    forged["user_recommendation_eligible"]=True
    reject("fake_gameplay_promotion_rejected",
           lambda:independent.check_pre_decision(case["raw"],case["capture"],ledger,projected,
                                                 case["st02_case"],case["readiness_contract"],forged),
           "INDEPENDENT_AUTHORITY_BOUNDARY")
    return {"schema":"ZrotST04RawIndependentAuditRegressionV1",
            "status":"PASS","passed":len(passed),"cases":passed,
            "scope":"SYNTHETIC_EXPLICIT_RAW_NDJSON_AND_PINNED_SOURCE_CANDIDATE",
            "native_simc_feature_producer":"NOT_VERIFIED",
            "live_wcl":"NOT_RUN","blizzard_mechanics":"NOT_VERIFIED",
            "independent_wcl_blind":"NOT_RUN",
            "live_ready_certified":0,"authority_promotion":False,
            "seq578":"FAILED_QUARANTINED_PRESERVED","seq637":"UNKNOWN"}


if __name__=="__main__":
    print(json.dumps(tests(),ensure_ascii=False,indent=2,sort_keys=True))
