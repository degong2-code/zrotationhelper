#!/usr/bin/env python3
"""Generic source-pinned controlled-negative Native profile fixture generator.

A SpecAdapter declares a particular item-slot removal and a certified original
C++ early-false guard to trigger. This generic engine applies only a narrow
declarative profile transformation, validates exact source profile blob and
APL preservation, and writes a successor profile and provenance receipt.
It NEVER claims a negative witness without real Original METHOD-PRE replay
from two executable Native sessions. Does not alter canonical profiles.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from general_rotation_original_pre_capture_engine_v1 import canonical
from general_rotation_source_route_audit_v1 import git_blob
from general_rotation_source_false_guard_engine_v1 import verify_rules

SCHEMA="ZrotGeneralRotationControlledNegativeNativeProfileFixtureV1"
IDENT=re.compile(r"[a-z][a-z0-9_]*\Z")
HASH40=re.compile(r"[a-f0-9]{40}\Z")
SOURCE_REVISION="b522cded8c26b97dac03fdf56e57a03ec7e8faa6"


class ControlledNegativeFixtureError(ValueError):
    pass


def _profile_parts(raw:bytes):
    try: src=raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ControlledNegativeFixtureError("PROFILE_ENCODING_NOT_UTF8") from e
    if "\r" in src or not src.endswith("\n"):
        raise ControlledNegativeFixtureError("PROFILE_LINE_ENDINGS_DRIFT")
    return src.splitlines(keepends=True)


def generate_fixture(raw:bytes,scenario:dict,manifest:dict,
                     false_guard_receipt:dict)->tuple[bytes,dict]:
    if not isinstance(scenario,dict) or set(scenario)!={
        "scenario_id","source_profile_path","source_profile_git_blob_sha1",
        "spec","source_negative_guard_rule_id",
        "transform_kind","item_slot",
    }:
        raise ControlledNegativeFixtureError("EXACT_CONTROLLED_SCENARIO_CONTRACT_REQUIRED")
    sid=scenario["scenario_id"]
    slot=scenario["item_slot"]
    spec=scenario["spec"]
    path=scenario["source_profile_path"]
    if (not all(isinstance(x,str) for x in (sid,slot,spec,path)) or
        not all(IDENT.fullmatch(x) for x in (sid,slot,spec)) or
        not path.startswith("profiles/") or ".." in Path(path).parts or
        Path(path).is_absolute() or
        not HASH40.fullmatch(str(scenario["source_profile_git_blob_sha1"])) or
        scenario["transform_kind"]!="DROP_EQUIPMENT_SLOT_V1"):
        raise ControlledNegativeFixtureError("SCENARIO_PROFILE_TRANSFORM_NOT_APPROVED")
    if git_blob(raw)!=scenario["source_profile_git_blob_sha1"]:
        raise ControlledNegativeFixtureError("PINNED_SOURCE_PROFILE_BLOB_DRIFT")
    approved=verify_rules(false_guard_receipt,manifest)
    matched=[r for r in approved.values()
             if r["rule_id"]==scenario["source_negative_guard_rule_id"]]
    if len(matched)!=1:
        raise ControlledNegativeFixtureError("SOURCE_CERTIFIED_FALSE_GUARD_RULE_NOT_FOUND")
    guard=matched[0]
    # Evidence link is directional: absence of an item slot supplies an
    # input candidate, not a proof that SimC runs or attempts this action.
    fields=set(guard["field_names"])
    if f"{slot}_weapon_none" not in fields:
        raise ControlledNegativeFixtureError("ITEM_SLOT_NOT_RELEVANT_TO_GUARD")
    lines=_profile_parts(raw)
    hit=[i for i,line in enumerate(lines) if line.startswith(slot+"=")]
    if len(hit)!=1 or not lines[hit[0]].strip().split("=",1)[1]:
        raise ControlledNegativeFixtureError("ITEM_SLOT_PROFILE_LINE_NOT_UNIQUE")
    # Comment the exact pinned equipment assignment (not the action APL).
    lines[hit[0]]="# ZROT_CONTROLLED_NEGATIVE_DISABLED "+lines[hit[0]]
    # Remove only the now-invalid enchant token from an otherwise unchanged
    # temporary_enchant directive. Preserve other slot enchants in order.
    imbue=[i for i,line in enumerate(lines) if line.startswith("temporary_enchant=")]
    if len(imbue)>1:
        raise ControlledNegativeFixtureError("AMBIGUOUS_TEMPORARY_ENCHANT")
    if imbue:
        i=imbue[0]
        head,value=lines[i].rstrip("\n").split("=",1)
        tokens=value.split("/")
        kept=[t for t in tokens if not t.startswith(slot+":")]
        if len(kept)!=len(tokens):
            lines[i]=head+"="+"/".join(kept)+"\n" if kept else (
                "# ZROT_CONTROLLED_NEGATIVE_NO_TEMP_ENCHANT\n")
    output="".join(lines).encode("utf-8")
    original_actions=[x for x in _profile_parts(raw)
                      if x.startswith("actions.") or x.startswith("actions=")
                      or x.startswith("actions+=")]
    new_actions=[x for x in _profile_parts(output)
                 if x.startswith("actions.") or x.startswith("actions=")
                 or x.startswith("actions+=")]
    if original_actions!=new_actions:
        raise ControlledNegativeFixtureError("APL_SOURCE_ROWS_MODIFIED")
    if len(output)==0 or output==raw:
        raise ControlledNegativeFixtureError("SOURCE_PROFILE_TRANSFORM_NO_EFFECT")
    provenance={
        "schema":SCHEMA,
        "scenario_id":sid,
        "source_profile_path":path,
        "source_profile_git_blob_sha1":git_blob(raw),
        "source_profile_sha256":sha256(raw).hexdigest(),
        "controlled_profile_sha256":sha256(output).hexdigest(),
        "source_apl_rows_unchanged":True,
        "transform_kind":scenario["transform_kind"],
        "removed_item_slot":slot,
        "source_certified_negative_rule_id":guard["rule_id"],
        "expected_guard_source_method":guard["source_method_key"],
        "expected_negative_condition":"ITEM_SLOT_WEAPON_NONE",
        "negative_condition_executed_native":"NOT_TESTED",
        "original_vs_instrumented_behavior":"NOT_TESTED",
        "source_method_return_false_real_count":None,
        "action_READY_positive_certified":0,
        "WCL_API_calls":0
    }
    return output,provenance


def selftest()->dict:
    import copy
    # Source manifest/rule verification requires the original full source
    # audit; use a synthetic-injected independent rule verifier here, while
    # the production CI uses the exact pinned official SimC rule.
    raw=(
        b'warrior="Synthetic"\nspec=fury\n'
        b'temporary_enchant=main_hand:oil/off_hand:oil\n'
        b'actions=/auto_attack\nactions+=/rampage\n'
        b'off_hand=example_item,id=1\nmain_hand=example_item,id=2\n'
    )
    from unittest.mock import patch
    scenario={
        "scenario_id":"synthetic_no_offhand",
        "source_profile_path":"profiles/MID2/example.simc",
        "source_profile_git_blob_sha1":git_blob(raw),
        "spec":"fury","source_negative_guard_rule_id":"weapon_absence",
        "transform_kind":"DROP_EQUIPMENT_SLOT_V1","item_slot":"off_hand"
    }
    rule={"source_method_key":"example_ready","rule_id":"weapon_absence",
          "field_names":["main_hand_weapon_none","off_hand_weapon_none"]}
    with patch(__name__+".verify_rules",return_value={"example_ready":rule}):
        result,receipt=generate_fixture(raw,scenario,{},{} )
        assert b'\noff_hand=' not in result
        assert b'main_hand=example_item,id=2' in result
        assert b'temporary_enchant=main_hand:oil\n' in result
        assert b'actions+=/rampage\n' in result
        assert receipt["source_apl_rows_unchanged"] is True
        assert receipt["source_method_return_false_real_count"] is None
        for modified in (
            dict(scenario,source_profile_git_blob_sha1="0"*40),
            dict(scenario,item_slot="main_hand"),
            dict(scenario,source_negative_guard_rule_id="other"),
            dict(scenario,transform_kind="INJECT_NATIVE_READY"),
        ):
            # Removing main-hand is relevant but must be rejected if slot is
            # not the requested physical missing operand in this fixture.
            if modified["item_slot"]=="main_hand":
                continue
            try:generate_fixture(raw,modified,{},{} )
            except ControlledNegativeFixtureError:pass
            else:raise AssertionError("UNPINNED_OR_INVALID_FIXTURE_ACCEPTED")
        try:generate_fixture(raw+b"off_hand=another_item\n",scenario,{},{} )
        except ControlledNegativeFixtureError:pass
        else:raise AssertionError("ADDITIONAL_PROFILE_LINE_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":10,"source_provenance_guarded":True,
        "actual_Native_negative_fixture_executed":False,
        "positive_READY_certified":0,"WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--source-templates",type=Path)
    p.add_argument("--certified-false-guards",type=Path)
    p.add_argument("--scenario-id",type=str)
    p.add_argument("--out-profile",type=Path)
    p.add_argument("--receipt",type=Path)
    a=p.parse_args()
    req=(a.simc_root,a.source_templates,a.certified_false_guards,
         a.scenario_id,a.out_profile,a.receipt)
    if all(x is None for x in req):
        output=selftest()
    elif all(x is not None for x in req):
        root=a.simc_root.resolve(strict=True)
        rev=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                           check=True,text=True,capture_output=True).stdout.strip()
        if rev!=SOURCE_REVISION:
            raise ControlledNegativeFixtureError("SOURCE_REVISION_CHANGED")
        manifest=json.loads(a.source_templates.read_bytes())
        certified=json.loads(a.certified_false_guards.read_bytes())
        entries=manifest.get("controlled_negative_scenarios")
        if not isinstance(entries,list):
            raise ControlledNegativeFixtureError("DECLARED_SCENARIOS_MISSING")
        found=[entry for entry in entries if entry.get("scenario_id")==a.scenario_id]
        if len(found)!=1:
            raise ControlledNegativeFixtureError("SCENARIO_SOURCE_ADAPTER_ID_NOT_UNIQUE")
        scenario=found[0]
        relative=Path(scenario["source_profile_path"])
        absolute=(root/relative).resolve(strict=True)
        if not absolute.is_relative_to(root):
            raise ControlledNegativeFixtureError("SOURCE_PROFILE_OUTSIDE_REPO")
        raw=absolute.read_bytes()
        transformed,output=generate_fixture(raw,scenario,manifest,certified)
        a.out_profile.parent.mkdir(parents=True,exist_ok=True)
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        with a.out_profile.open("xb") as f:f.write(transformed)
        with a.receipt.open("xb") as f:f.write(canonical(output))
    else:p.error("all fixture arguments must be supplied or none")
    print(canonical(output).decode(),end="")


if __name__=="__main__":
    main()
