#!/usr/bin/env python3
"""SimC Native evidence adapter to spec-neutral General Rotation proof engine.

Reuses already recorded, exact scoped Original PRE facts. Does not read an
observed Native ready Boolean as evidence. Source base-return, even positive,
is comparator-only. Captured source target and time are original method reads.
WoW/WCL PRE has its own stricter timestamp contract in the generic engine.

Specialization-specific gates are optional adapter contributions and must
never be hard-coded here. Necessary negative proof reuses the prior validated
priority frontier status; no generic source library rewrites are needed.
"""
from __future__ import annotations

from collections import Counter

from general_rotation_decision_proof_engine_v1 import (
    Identity, Fact, GateContract, decide_candidate, evaluate_priority,
    NOT_READY, READY, UNKNOWN, DecisionProofError
)
from simc_native_cooldown_tolerance_replay_v1 import independent_raw_tolerance_queue
from simc_native_target_eligibility_source_replay_v1 import (
    parse_config,parse_target,independent_basic_target_truth,direct_path
)

SCHEMA="ZrotSimcNativeGeneralRotationOpenWorldProofBridgeV1"
GATES=(
    "NECESSARY_ELIGIBILITY","APL_IF","COOLDOWN","RESOURCE",
    "BASE_TARGET","MOVEMENT","CAST_GCD","SYNC_LINE",
    "SPEC_LOCAL","SPEC_OVERRIDE_TOTAL","BASE_VIRTUAL_COMPLETE"
)

class NativeProofBridgeError(ValueError):
    pass


class NativeProofBridge:
    def __init__(self):
        self.counters=Counter()
        self.occurrences=Counter()

    def consume(self,line:str,pending:dict|None):
        # Only current source-pointer-scope events are accepted. Nested
        # or otherwise unmatched source reads do not become positive facts.
        cfg=parse_config(line)
        if cfg is not None:
            if (pending is None or
                (cfg["time_ms"],cfg["list"],cfg["ordinal"],cfg["native_name"])!=(
                    pending["pre"]["time_ms"],pending["pre"]["list"],
                    pending["pre"]["ordinal"],pending["pre"]["native_name"])):
                self.counters["unpaired_target_config"]+=1
            else:
                pending.setdefault("generic_target_configs",[]).append(cfg)
            return
        target=parse_target(line)
        if target is not None:
            if (pending is None or
                (target["time_ms"],target["action"])!=(
                  pending["pre"]["time_ms"],pending["pre"]["native_name"])):
                self.counters["unscoped_or_other_base_target"]+=1
            else:
                pending.setdefault("generic_target_evidence",[]).append(target)

    def evaluate_attempt(self,pending:dict,row:dict,*,spec_adapter=None)->dict:
        k=row["source_key"]
        occurrence=self.occurrences[tuple(k)]
        self.occurrences[tuple(k)]+=1
        identity=Identity(f"{k[1]}::{k[3]}",row["source_sha256"],
                          k[0],k[2]-1,occurrence)
        # Never set closed=True from an observed Native return/READY bit.
        contract=GateContract(
            source="SIMC_SOURCE_BASE_WITH_OPEN_VIRTUAL_DISPATCH",
            source_sha256=row["source_sha256"],required=GATES,
            closed=False
        )
        facts={}
        def insert(gate,value,basis="INDEPENDENT_SOURCE_REPLAY",
                   captured="SIMC_ORIGINAL_METHOD_PRE",receipt=""):
            if gate in facts:
                raise NativeProofBridgeError("DUPLICATE_GATE_CONTRIBUTION")
            facts[gate]=Fact(identity,gate,value,basis,captured,k[0],
                            receipt or ("source:"+gate))
        if row["status"].startswith("EXCLUDED_"):
            why=row["source_exclusion_reason"]
            if not why:
                raise NativeProofBridgeError("PROVEN_NEGATIVE_WITHOUT_ORIGIN")
            insert("NECESSARY_ELIGIBILITY",False,
                   receipt="previous_proven_negative:"+why)
        if row["independent_IF_bool"] is not None:
            insert("APL_IF",bool(row["independent_IF_bool"]),
                   receipt="chronological_official_APL_independent_AST")
        if (pending["clock"] is not None and pending["tolerance"] is not None and
            pending["base_ready_entries"]==1):
            cd=independent_raw_tolerance_queue(pending["clock"],
                                               pending["tolerance"])
            insert("COOLDOWN",bool(cd["numeric_cooldown_ready"]),
                   receipt="source_raw_cooldown_integer_tolerance_replay")
        configs=pending.get("generic_target_configs",[])
        targets=pending.get("generic_target_evidence",[])
        if (len(configs)==1 and len(targets)==1 and
            direct_path(configs[0]) and
            row["method_base_path_source_observed"]):
            truth,_=independent_basic_target_truth(targets[0])
            # If a *direct* target is ineligible the observed base
            # method must terminate at target false, else it cannot
            # prove the candidate itself was blocked.
            if not truth:
                if row["source_base_exit_observed"]!="TARGET_FALSE":
                    raise NativeProofBridgeError("DIRECT_TARGET_NEGATIVE_WITHOUT_SOURCE_EXIT")
                insert("BASE_TARGET",False,receipt="source_direct_original_base_target_numeric")
            else:
                insert("BASE_TARGET",True,receipt="source_direct_original_base_target_numeric")
        if spec_adapter is not None and hasattr(spec_adapter,"partial_positive_gate"):
            spec=spec_adapter.partial_positive_gate(pending,row)
            if spec is not None:
                if type(spec) is not bool:
                    raise NativeProofBridgeError("SPEC_ADAPTER_GATE_MUST_BE_BOOLEAN")
                insert("SPEC_LOCAL",spec,receipt="scoped_source_spec_adapter_partial_numeric")
        if row["source_base_exit_observed"]=="FULL_BASE_TRUE":
            # This is only an observed source route, never positive
            # independent virtual readiness.
            insert("BASE_VIRTUAL_COMPLETE",True,"NATIVE_SOURCE_OBSERVED",
                   "OBSERVED_POST_COMPARATOR",
                   "original_native_base_action_ready_exit_NOT_PROOF")
        verdict=decide_candidate(identity,contract,facts.values(),
                                row["source_action"] not in (
                                    "variable","call_action_list","run_action_list",
                                    "swap_action_list","sequence","strict_sequence",
                                    "wait","pool_resource"))
        if verdict["decision"]==READY:
            raise NativeProofBridgeError("UNCLOSED_SIMC_VIRTUAL_ROUTE_CANNOT_PROVE_READY")
        if verdict["decision"]==NOT_READY and not row["status"].startswith("EXCLUDED_"):
            # Soundness review required before upgrading old bounded
            # candidate negative evidence; don't change settled old
            # results based on new raw target/CD data silently.
            self.counters["additional_numeric_negative_pending_review"]+=1
            verdict=decide_candidate(
                identity,contract,
                [f for f in facts.values() if f.value is not False],
                row["source_action"] not in (
                    "variable","call_action_list","run_action_list",
                    "swap_action_list","sequence","strict_sequence",
                    "wait","pool_resource"))
        self.counters["attempts"]+=1
        self.counters["proof_"+verdict["decision"]]+=1
        for field in verdict["independent_true"]:
            self.counters["independent_true_"+field]+=1
        for field in verdict["missing_or_unverified"]:
            self.counters["missing_"+field]+=1
        for field in verdict["blockers"]:
            if verdict["decision"]==UNKNOWN:
                self.counters["UNKNOWN_"+field]+=1
        return {
            "identity":{
                "scope":identity.scope,"source_sha256":identity.source_sha256,
                "at_ms":identity.t_ms,"ordinal":identity.ordinal,
                "same_key_occurrence":identity.occurrence},
            "decision":verdict["decision"],
            "blockers":verdict["blockers"],
            "independent_true_gates":verdict["independent_true"],
            "independent_false_gates":verdict["independent_false"],
            "source_only_positive_gates":verdict["source_only"],
            "full_ready_positive_closed":False,
            "Native_ready_comparator_NOT_USED":True,
            "dummy_error_permitted":False
        }

    def evaluate_root(self,attempts:list[dict],returned:bool,
                      observed_name:str|None)->dict:
        if not attempts:
            return {"decision":"UNKNOWN","earlier_NOT_READY":0,
                    "earlier_UNKNOWN":0,"returned_READINESS":None,
                    "dummy_error_permitted":False,
                    "reason":"NO_SCOPED_SOURCE_ATTEMPTS"}
        proof=[one["generic_proof"] for one in attempts]
        selected=len(proof)-1 if returned else None
        # Native source path recorded in order but a call/run list may
        # alter the candidate set. Do NOT certify exhaustive source
        # ordering from the same observed Native action sequence.
        result=evaluate_priority(proof,selected,source_order_complete=False,
                                 native_selected_name=observed_name)
        self.counters["source_root_scans"]+=1
        if returned:
            self.counters["source_returned_roots"]+=1
            self.counters["returned_"+result["returned_READINESS"]]+=1
            if result["earlier_UNKNOWN"]==0:
                self.counters["returned_all_prior_proven_not_ready_but_winner_unknown"]+=1
            for field in proof[-1]["blockers"]:
                self.counters["selected_blocker_"+field]+=1
        return result

    def summary(self)->dict:
        return {"schema":SCHEMA,
                "counts":dict(sorted(self.counters.items())),
                "Source_and_Native_comparators_not_readiness_operands":True,
                "spec_semantics_only_via_adapter_callback":True,
                "full_positive_ready_certified":False,
                "WCL_API_calls":0}

def selftest():
    from simc_native_if_false_priority_frontier_v1 import one_attempt
    # Minimal source-pointer-compatible proof: independent proven
    # negative stays negative, source-observed true stays UNKNOWN.
    h="a"*64
    bridge=NativeProofBridge()
    pending={"pre":{"time_ms":20,"list":"default","ordinal":1,
                    "native_name":"alpha"},"clock":None,"tolerance":None,
             "base_ready_entries":0}
    row={"source_key":(20,"default",1,"alpha"),
         "source_sha256":h,"source_action":"alpha",
         "independent_IF_bool":None,
         "status":"EXCLUDED_BY_INDEPENDENT_WARRIOR_DISTANCE_FALSE",
         "source_exclusion_reason":"source_distance",
         "method_base_path_source_observed":True,
         "source_base_exit_observed":"BASE_READY_FALSE"}
    a=bridge.evaluate_attempt(pending,row)
    assert a["decision"]==NOT_READY
    assert a["independent_false_gates"]==["NECESSARY_ELIGIBILITY"]
    nxt=dict(row,status="UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED",
             source_exclusion_reason=None,
             source_base_exit_observed="FULL_BASE_TRUE")
    b=bridge.evaluate_attempt(pending,nxt)
    assert b["decision"]==UNKNOWN
    assert "BASE_VIRTUAL_COMPLETE" in b["source_only_positive_gates"]
    assert b["identity"]["same_key_occurrence"]==1
    root=bridge.evaluate_root([{"generic_proof":a},{"generic_proof":b}],
                              returned=True,observed_name="alpha")
    assert root["earlier_NOT_READY"]==1
    assert root["decision"]==UNKNOWN
    assert root["returned_READINESS"]==UNKNOWN
    ctl=dict(nxt,source_action="run_action_list")
    assert bridge.evaluate_attempt(pending,ctl)["decision"]==UNKNOWN
    # Fake native positive bit cannot certify a skill: this adapter does
    # not even expose Native ready as an accepted input.
    assert "native_ready" not in bridge.summary()["counts"]
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":10,"real_native":"NOT_RUN","WCL_API_calls":0}

if __name__=="__main__":
    import json
    print(json.dumps(selftest(),sort_keys=True))
