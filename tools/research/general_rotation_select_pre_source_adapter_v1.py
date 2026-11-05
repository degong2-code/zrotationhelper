#!/usr/bin/env python3
"""Source adapter provider for passive generic SELECT-PRE Native capture.

All specialization-specific source route fixtures are *outside* the generic
producer. The producer accepts only this portable template manifest and may
accept other class/spec template providers without altering its code.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from general_rotation_original_pre_capture_engine_v1 import (
    canonical, compile_template
)
from general_rotation_source_route_fixture_v1 import (
    audit_both, UPSTREAM, warrior_route, mage_route
)
from general_rotation_original_pre_capture_fixture_v1 import declared_operands

SCHEMA="ZrotGenericPassiveSelectTemplateManifestV1"


def pinned_method_entry_sites(templates:list[dict])->list[dict]:
    """Declare *common* original C++ method entry sites; no raw C++ code."""
    from general_rotation_source_route_fixture_v1 import warrior_route, mage_route
    declared=[
        ("base_action","bool action_t::action_ready()",()),
        ("base_ready","bool action_t::ready()",
         ("gcd_ready_ms","usable_while_casting")),
    ]
    class_routes=(warrior_route(),mage_route())
    sites=[]
    for key,signature,names in declared:
        methods=[next(x for x in route.methods if x.key==key)
                 for route in class_routes]
        if (any(x.signature!=signature or x.path!="engine/action/action.cpp"
                or x.class_anchor is not None or
                x.source_blob_sha1!=methods[0].source_blob_sha1
                for x in methods)):
            raise ValueError("CROSS_SPEC_METHOD_SIGNATURE_SOURCE_MISMATCH")
        selected=[]
        source_fingerprint=None
        for template in templates:
            all_fields=[f for f in template["fields"] if f["source_node"]==key]
            if not all_fields:
                raise ValueError("REQUIRED_BASE_METHOD_SOURCE_SITE_MISSING")
            for f in all_fields:
                p=(f["source_path"],f["source_git_blob_sha1"],
                   f["source_method_body_sha256"])
                if source_fingerprint is None:source_fingerprint=p
                if p!=source_fingerprint:
                    raise ValueError("CROSS_SPEC_BASE_METHOD_BODY_DRIFT")
            wanted=[f for f in all_fields if f["operand_name"] in names]
            if set(x["operand_name"] for x in wanted)!=set(names):
                raise ValueError("METHOD_ENTRY_RAW_FIELDS_NOT_SOURCE_DECLARED")
            if not selected:selected=wanted
            elif ({x["field_id"] for x in selected}!=
                  {x["field_id"] for x in wanted}):
                raise ValueError("CROSS_SPEC_METHOD_ENTRY_FIELD_IDS_DIFFER")
        sites.append({
            "method_key":key,"signature":signature,"class_anchor":None,
            "source_path":source_fingerprint[0],
            "source_git_blob_sha1":source_fingerprint[1],
            "source_method_body_sha256":source_fingerprint[2],
            "fields":sorted(selected,key=lambda x:x["operand_name"]),
        })
    # Specialization-owned original source routes are declared solely here.
    # The generic C++ patcher receives opaque source-site records and does
    # not know Warrior, Mage, Rampage or Arcane Blast semantics.
    owned=(
        ("warrior_fury","warrior_action"),
        ("warrior_fury","warrior_ready"),
        ("warrior_fury","rampage_ready"),
        ("mage_arcane","arcane_blast_ready"),
    )
    source_plans={"warrior_fury":warrior_route(), "mage_arcane":mage_route()}
    report_templates={
        "warrior_fury":templates[0],"mage_arcane":templates[1]
    }
    for spec,key in owned:
        plan=source_plans[spec]
        source=[method for method in plan.methods if method.key==key]
        if len(source)!=1:
            raise ValueError("SPECIALIZATION_SOURCE_METHOD_NOT_UNIQUE")
        method=source[0]
        template=report_templates[spec]
        if template["source_route_name"]!=plan.name:
            raise ValueError("SPECIALIZATION_TEMPLATE_IDENTITY_DRIFT")
        facts=[field for field in template["fields"]
               if field["source_node"]==key]
        if not facts or any(
            field["source_path"]!=method.path or
            field["source_git_blob_sha1"]!=method.source_blob_sha1
            for field in facts):
            raise ValueError("SPECIALIZATION_METHOD_SOURCE_FACTS_MISSING")
        expected_body={field["source_method_body_sha256"] for field in facts}
        if len(expected_body)!=1:
            raise ValueError("SPECIALIZATION_SOURCE_BODY_CONFLICT")
        sites.append({
            "method_key":key,
            "signature":method.signature,
            "class_anchor":method.class_anchor,
            "source_path":method.path,
            "source_git_blob_sha1":method.source_blob_sha1,
            "source_method_body_sha256":next(iter(expected_body)),
            "fields":[],
        })
    if len(sites)!=6 or len({site["method_key"] for site in sites})!=6:
        raise ValueError("SOURCE_METHOD_SITE_COHORT_MISMATCH")
    return sites


def build(root:Path)->dict:
    audits=audit_both(root)
    if (audits.get("pinned_source_commit")!=UPSTREAM or
        audits.get("dynamic_dispatch_and_guard_exhaustiveness_reviewed") is not False):
        raise ValueError("SOURCE_ROUTE_ADAPTER_OR_REVISION_DRIFT")
    templates=[
        compile_template(audits["audits"]["warrior_fury"],
                         declared_operands(warrior_route())),
        compile_template(audits["audits"]["mage_arcane"],
                         declared_operands(mage_route())),
    ]
    return {
        "schema":SCHEMA,
        "pinned_source_commit":UPSTREAM,
        "source_fixture_count":len(templates),
        "templates":templates,
        "method_entry_sites":pinned_method_entry_sites(templates),
        "actual_native_CAPTURE_execution":False,
        "positive_READY_proven":0,
        "WCL_API_calls":0,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=build(a.simc_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("xb") as f:f.write(canonical(result))
    print("GENERIC_PRE_SOURCE_TEMPLATE_MANIFEST_PASS")


if __name__=="__main__":
    main()
