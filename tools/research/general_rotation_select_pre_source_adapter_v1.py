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
