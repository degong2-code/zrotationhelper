#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""First cross-spec synthetic integration probe.

Claim boundary:
- validates control-plane -> bound-workflow execution,
- validates specialization-agnostic IR/SpecAdapter contract with two contrasting synthetic specs,
- validates strict-PRE state semantics on synthetic timelines,
- DOES NOT prove full existing General Rotation engine portability,
- DOES NOT use network, WCL, Blizzard API, or SimC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

STAGE="ZRAID_FIRST_CROSS_SPEC_SYNTHETIC_INTEGRATION_PROBE_V1"
ROOT=Path(__file__).resolve().parents[3]
CONFIG=ROOT/"01_WORKFLOW"/"config"/"MAIN_CONTROL_PLANE.json"

@dataclass(frozen=True)
class SyntheticSpec:
    spec_id: str
    resource_name: str
    resource_min: int
    resource_max: int
    spend_threshold: int
    primary_action: str
    spender_action: str
    proc_name: str
    charge_cap: int

REFERENCE = SyntheticSpec(
    spec_id="SYNTH_STACK10_REFERENCE",
    resource_name="stack_resource",
    resource_min=0,
    resource_max=10,
    spend_threshold=5,
    primary_action="reference_builder",
    spender_action="reference_spender",
    proc_name="reference_proc",
    charge_cap=1,
)
CONTRAST = SyntheticSpec(
    spec_id="SYNTH_ENERGY100_CHARGE2",
    resource_name="energy_resource",
    resource_min=0,
    resource_max=100,
    spend_threshold=60,
    primary_action="contrast_builder",
    spender_action="contrast_spender",
    proc_name="contrast_proc",
    charge_cap=2,
)

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()

def state_at_action(events:Sequence[Mapping[str,Any]], t:int, initial:Mapping[str,Any])->Dict[str,Any]:
    state=dict(initial)
    for ev in sorted(events,key=lambda x:(int(x["timestamp"]),int(x.get("seq",0)))):
        if int(ev["timestamp"]) >= t:
            break
        key=str(ev["key"])
        state[key]=ev["value"]
    return state

def recommend(spec:SyntheticSpec,state:Mapping[str,Any])->str:
    resource=int(state.get(spec.resource_name,0))
    proc=bool(state.get(spec.proc_name,False))
    charges=int(state.get("charges",0))
    targets=int(state.get("targets",1))
    if proc and resource >= spec.spend_threshold:
        return spec.spender_action
    if charges >= spec.charge_cap:
        return spec.primary_action
    if targets >= 3 and resource >= spec.spend_threshold:
        return spec.spender_action
    return spec.primary_action

def synthetic_case(spec:SyntheticSpec)->Mapping[str,Any]:
    initial={spec.resource_name:spec.resource_min,spec.proc_name:False,"charges":0,"targets":1}
    t=1000
    events=[
        {"timestamp":900,"seq":1,"key":spec.resource_name,"value":spec.spend_threshold},
        {"timestamp":950,"seq":1,"key":spec.proc_name,"value":True},
        {"timestamp":1000,"seq":1,"key":"targets","value":4},  # same timestamp MUST NOT leak
        {"timestamp":1010,"seq":1,"key":"charges","value":spec.charge_cap},
    ]
    pre=state_at_action(events,t,initial)
    action=recommend(spec,pre)
    strict_pre_ok=(pre["targets"]==1 and pre[spec.proc_name] is True and pre[spec.resource_name]==spec.spend_threshold)
    decision_ok=(action==spec.spender_action)
    bounds_ok=(spec.resource_min <= pre[spec.resource_name] <= spec.resource_max and spec.charge_cap >= 1)
    return {
        "spec_id":spec.spec_id,
        "strict_pre_state":pre,
        "recommended_action":action,
        "strict_pre_ok":strict_pre_ok,
        "decision_ok":decision_ok,
        "resource_bounds_ok":bounds_ok,
        "pass":bool(strict_pre_ok and decision_ok and bounds_ok),
    }

def self_test()->int:
    rows=[synthetic_case(REFERENCE),synthetic_case(CONTRAST)]
    checks=[
        rows[0]["pass"],rows[1]["pass"],
        REFERENCE.resource_max != CONTRAST.resource_max,
        REFERENCE.charge_cap != CONTRAST.charge_cap,
        REFERENCE.spec_id != CONTRAST.spec_id,
        "Enhancement" not in REFERENCE.spec_id+CONTRAST.spec_id,
    ]
    print("SELF_TEST="+("PASS" if all(checks) else "FAIL"))
    print("SELF_TEST_CASE_N="+str(len(checks)))
    print("SELF_TEST_FAILURE_N="+str(sum(1 for x in checks if not x)))
    return 0 if all(checks) else 2

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:return self_test()

    print("STAGE="+STAGE)
    print("PROJECT_ROOT="+str(ROOT))
    if not CONFIG.is_file():
        print("ERROR=CONTROL_CONFIG_MISSING",file=sys.stderr);return 2
    cfg=json.loads(CONFIG.read_text(encoding="utf-8"))
    active=cfg.get("active_workflow") or {}
    expected=active.get("sha256")
    current=sha(Path(__file__).resolve())
    if active.get("id")!="FIRST_CROSS_SPEC_SYNTHETIC_PROBE_V1":
        print("ERROR=ACTIVE_WORKFLOW_ID_MISMATCH",file=sys.stderr);return 2
    if active.get("execution_ready") is not True:
        print("ERROR=ACTIVE_WORKFLOW_NOT_READY",file=sys.stderr);return 2
    if expected!=current:
        print("ERROR=ACTIVE_WORKFLOW_SHA_MISMATCH::"+current+"::"+str(expected),file=sys.stderr);return 2

    rows=[synthetic_case(REFERENCE),synthetic_case(CONTRAST)]
    ok=all(r["pass"] for r in rows)
    run_id=datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    outdir=ROOT/"05_EVIDENCE"/"01_VALIDATION"/"cross_spec_synthetic_probe"/run_id
    outdir.mkdir(parents=True,exist_ok=True)
    result=outdir/"CROSS_SPEC_SYNTHETIC_PROBE_RESULT.json"
    obj={
        "schema":"ZraidCrossSpecSyntheticProbeResult","version":"1.0","stage":STAGE,"run_id":run_id,
        "status":"PASS" if ok else "FAIL",
        "case_n":len(rows),"cases":rows,
        "validation_scope":"CONTROL_PLANE_SPEC_ADAPTER_IR_AND_STRICT_PRE_CONTRACT_ONLY",
        "full_generic_rotation_engine_cross_spec_validation":"NOT_YET_PROVEN",
        "cross_spec_empirical_validation":"NOT_RUN",
        "network_used":False,"simc_used":False,"gameplay_evidence_reopened":False,
    }
    result.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print("SYNTHETIC_CASE_N="+str(len(rows)))
    print("SYNTHETIC_CASE_PASS_N="+str(sum(1 for r in rows if r["pass"])))
    print("VALIDATION_SCOPE=CONTROL_PLANE_SPEC_ADAPTER_IR_AND_STRICT_PRE_CONTRACT_ONLY")
    print("FULL_GENERIC_ROTATION_ENGINE_CROSS_SPEC_VALIDATION=NOT_YET_PROVEN")
    print("CROSS_SPEC_EMPIRICAL_VALIDATION=NOT_RUN")
    print("NETWORK_USED=false");print("SIMC_USED=false");print("GAMEPLAY_EVIDENCE_REOPENED=false")
    print("RESULT="+str(result));print("RESULT_SHA256="+sha(result))
    print("ROUTE="+("FIRST_CROSS_SPEC_SYNTHETIC_INTEGRATION_PROBE_PASS" if ok else "FIRST_CROSS_SPEC_SYNTHETIC_INTEGRATION_PROBE_FAIL"))
    return 0 if ok else 2

if __name__=="__main__":
    import sys
    raise SystemExit(main())
