#!/usr/bin/env python3
"""Source-specific field declarations; generic capture engine is unmodified.

Pinned Fury Rampage and Arcane Blast method-graph fixtures define possible
PRE operand requests. Fury's actual Native evidence joins to its requests.
Arcane has NO Native E2E; its template is static source coverage only.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from general_rotation_original_pre_capture_engine_v1 import (
    SCHEMA as TEMPLATE_SCHEMA, BOUND_SCHEMA, REPLAY_SCHEMA,
    Operand, compile_template, bind_worklist, validate_pre_records,
    CaptureContractError, canonical,
)
from general_rotation_source_route_fixture_v1 import (
    warrior_route, mage_route, UPSTREAM,
)

SCHEMA="ZrotGeneralRotationTwoSpecPRECaptureContractFixtureV1"


def field(plan, gate, node, name, kind, anchor_index, meaning):
    match=[x for x in plan.methods if x.key==node]
    if len(match)!=1:
        raise CaptureContractError("SPEC_FIXTURE_METHOD_NOT_UNIQUE")
    method=match[0]
    anchor=method.guard_anchors[anchor_index]
    return Operand(gate,node,name,kind,sha256(anchor.encode()).hexdigest(),meaning)


def declared_operands(plan):
    if plan.name == "warrior_fury_rampage_static_sites":
        values=[
            ("CAST_GCD","base_ready","usable_while_casting","bool",4,
             "base ready cast-while-casting selector"),
            ("CAST_GCD","base_ready","gcd_ready_ms","int",5,
             "original actor GCD ready timestamp"),
            ("CAST_GCD","base_action","repeat_cast_allowed","bool",7,
             "source action repeat-cast option, distinct from GCD"),
            ("MOVEMENT","base_directionality","movement_directionality","enum",0,
             "configured action-instance directionality"),
            ("MOVEMENT","base_directionality","player_movement_direction","enum",1,
             "actor movement direction at original method PRE"),
            ("MOVEMENT","base_ready","player_is_moving","bool",2,
             "actor is moving before source ready guard"),
            ("MOVEMENT","warrior_ready","distance_to_move","finite_float",2,
             "source actor actual target movement distance"),
            ("NECESSARY_ELIGIBILITY","rampage_ready","main_hand_weapon_none","bool",0,
             "source action main-hand WEAPON_NONE guard predicate"),
            ("NECESSARY_ELIGIBILITY","rampage_ready","off_hand_weapon_none","bool",0,
             "source action off-hand WEAPON_NONE guard predicate"),
            ("SPEC_OVERRIDE_TOTAL","warrior_action","replacement_action_exists","bool",0,
             "source replacement-action pointer presence"),
            ("SPEC_OVERRIDE_TOTAL","warrior_action","replacement_action_active","bool",1,
             "source replacement route branch if reached"),
            ("SPEC_OVERRIDE_TOTAL","warrior_ready","warrior_channeling","bool",3,
             "source warrior channel action state"),
        ]
    elif plan.name == "mage_arcane_blast_static_sites":
        values=[
            ("CAST_GCD","base_ready","usable_while_casting","bool",4,
             "base ready cast-while-casting selector"),
            ("CAST_GCD","base_ready","gcd_ready_ms","int",5,
             "original actor GCD ready timestamp"),
            ("CAST_GCD","base_action","repeat_cast_allowed","bool",7,
             "source action repeat-cast option"),
            ("MOVEMENT","base_directionality","movement_directionality","enum",0,
             "configured action-instance directionality"),
            ("MOVEMENT","base_directionality","player_movement_direction","enum",1,
             "actor movement direction at method PRE"),
            ("MOVEMENT","base_ready","player_is_moving","bool",2,
             "actor movement state at base ready entry"),
            ("NECESSARY_ELIGIBILITY","arcane_blast_ready","prismatic_bolt_buff_up","bool",0,
             "original Arcane Blast upgrade restriction"),
            ("SPEC_OVERRIDE_TOTAL","arcane_blast_ready","prismatic_bolt_override","bool",1,
             "source Arcane Blast class override path"),
        ]
    else:
        raise CaptureContractError("UNKNOWN_SPEC_FIXTURE_ROUTE")
    return tuple(field(plan,*args) for args in values)


def run(source_route_report: Path)->dict:
    audit=json.loads(source_route_report.read_bytes())
    if (audit.get("schema")!="ZrotGeneralRotationTwoSpecSourceRouteFixtureAuditV1"
        or audit.get("pinned_source_commit")!=UPSTREAM or
        audit.get("spec_fixture_count")!=2 or
        audit.get("positive_READY_certified")!=0 or
        audit.get("real_Arcane_Native_E2E") is not False):
        raise CaptureContractError("SOURCE_ROUTE_CROSS_SPEC_AUDIT_DRIFT")
    warrior=compile_template(audit["audits"]["warrior_fury"],
                             declared_operands(warrior_route()))
    mage=compile_template(audit["audits"]["mage_arcane"],
                          declared_operands(mage_route()))
    if warrior["field_count"]!=12 or mage["field_count"]!=8:
        raise CaptureContractError("SPEC_SEMANTIC_FIELD_COVERAGE_DRIFT")
    example=audit["actual_native_gap_example"]
    if (example is None or example.get("at_simc_ms")!=20031 or
        example.get("positive_READY")!="UNKNOWN"):
        raise CaptureContractError("REAL_SOURCE_PRE_CANDIDATE_MISSING")
    bound=bind_worklist(warrior,example["generic_unmet_source_worklist"])
    if (bound["requested_operand_count"]!=12 or
        bound["source_missing_gate_count"]!=5 or
        bound["gates_without_declared_operand_capture"]!=["BASE_VIRTUAL_COMPLETE"]):
        raise CaptureContractError("ACTUAL_FURY_CAPTURE_SCOPE_DRIFT")
    # The prior source replay observed these *derived* subpredicates, but
    # it did NOT produce the raw capture records declared in this plan.
    # Preserve the distinction; never insert synthetic or post comparator
    # values into the original PRE raw evidence channel.
    reused={
        "scope":"EXISTING_SIMC_ORIGINAL_PRE_DERIVED_SUBPREDICATES",
        "original_source_candidate_row":"217c49dcce32cbc0d975679ed09e0a79c71f05e2615e6566f46bffc9b1ffece2",
        "example_at_simc_ms":20031,
        "raw_records_for_NEW_request_contract_collected":0,
        "prior_ready_result":"UNKNOWN"
    }
    actual_raw_channel=validate_pre_records(bound,[])
    if (actual_raw_channel["records_transport_validated"]!=0 or
        actual_raw_channel["missing_request_count"]!=12):
        raise CaptureContractError("INVENTED_REAL_ORIGINAL_PRE_RECORD")
    return {
        "schema":SCHEMA,
        "policy":"ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1",
        "pinned_upstream_source":UPSTREAM,
        "generic_engine_template_schema":TEMPLATE_SCHEMA,
        "generic_engine_bound_schema":BOUND_SCHEMA,
        "generic_engine_replay_schema":REPLAY_SCHEMA,
        "spec_template_count":2,
        "warrior_fury_template":warrior,
        "mage_arcane_template":mage,
        "source_selected_actual_warrior_capture_plan":bound,
        "existing_replayed_subpredicates_reused_not_raw_capture":reused,
        "raw_capture_transport_validation":actual_raw_channel,
        "raw_capture_producer_executed":False,
        "actual_arcane_native_E2E_executed":False,
        "source_virtual_dispatch_closed":False,
        "positive_READY_certified":0,
        "WCL_API_calls":0,
        "MAIN_promoted":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--route-report",type=Path,required=True)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    result=run(args.route_report)
    data=canonical(result)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("xb") as h:
            h.write(data)
        print("GENERIC_PRE_CAPTURE_PLAN_SHA256="+sha256(data).hexdigest())
    else:
        print(data.decode(),end="")


if __name__=="__main__":
    main()
