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
    NOT_READY, READY, UNKNOWN, CONTROL_COMMANDS, DecisionProofError
)
from simc_native_cooldown_tolerance_replay_v1 import independent_raw_tolerance_queue
from simc_native_resource_cost_replay_v1 import (
    read_cost, read_base_resource, independent_numeric_resource
)
from simc_native_resource_cost_pre_instrument_v1 import ACTION_MARK, PLAYER_MARK
from simc_native_postguard_source_replay_v1 import (
    parse_line, parse_cast, independent_postguard_subset,
    LINE_MARK, CAST_MARK
)
from simc_native_target_eligibility_source_replay_v1 import (
    parse_config,parse_target,independent_basic_target_truth,direct_path
)

SCHEMA="ZrotSimcNativeGeneralRotationOpenWorldProofBridgeV1"
GATES=(
    "NECESSARY_ELIGIBILITY","APL_IF","COOLDOWN","RESOURCE",
    "BASE_TARGET","MOVEMENT","CAST_GCD","SYNC_LINE",
    # Source-subguard facts, not closure of their MOVEMENT/CAST_GCD parents.
    "MOVEMENT_BASE_GUARD_PASS","MOVEMENT_APL_OPTION_CLEAR",
    "CAST_REPEAT_CLEAR",
    "SPEC_LOCAL","SPEC_OVERRIDE_TOTAL","BASE_VIRTUAL_COMPLETE"
)

class NativeProofBridgeError(ValueError):
    pass


class NativeProofBridge:
    def __init__(self,*,export_source_gate_claims:bool=False,
                 export_focus_at_ms:int|None=None):
        if (export_focus_at_ms is not None and
            (type(export_focus_at_ms) is not int or
             export_focus_at_ms<0 or not export_source_gate_claims)):
            raise NativeProofBridgeError("INVALID_OR_UNSCOPED_GATE_EXPORT_FOCUS")
        self.export_source_gate_claims=export_source_gate_claims
        self.export_focus_at_ms=export_focus_at_ms
        self.portable_source_gate_claims=[]
        self.counters=Counter()
        self.occurrences=Counter()
        # Bounded, source-pinned gap witnesses, not positive READY certificates.
        self.positive_gap_shortlist=[]
        # Source-original cost/resource reads occur before the PRE guard
        # marker; pair by exact action/time at the only original invocation.
        self._raw_cost=None
        self._raw_resource=None
        self._resource_ambiguous=False

    def consume(self,line:str,pending:dict|None):
        # Only current source-pointer-scope events are accepted. Nested
        # or otherwise unmatched source reads do not become positive facts.
        cost=read_cost(line)
        if cost is not None:
            if pending is None:
                if self._raw_cost is not None:
                    self.counters["pre_resource_cost_unpaired_superseded"]+=1
                self._raw_cost=cost
                self._raw_resource=None
                self._resource_ambiguous=False
            else:
                self.counters["nested_or_unscoped_base_cost"]+=1
            return
        resource=read_base_resource(line)
        if resource is not None:
            cost=self._raw_cost
            if (pending is None and cost is not None and
                not cost["resource_none"] and
                (cost["time_ms"],cost["resource_id"],cost["cost"])==
                (resource["time_ms"],resource["resource_id"],resource["cost"])):
                if self._raw_resource is not None:
                    self._resource_ambiguous=True
                else:
                    self._raw_resource=resource
            else:
                self.counters["unpaired_player_resource_base_read"]+=1
            return
        # The original player_t::select_action() emits this physical option
        # snapshot immediately before its only action_ready() invocation.
        # It is an original PRE read, not a virtual/native verdict.
        line_pre=parse_line(line)
        if line_pre is not None:
            if pending is None or (
                line_pre["time_ms"],line_pre["list"],line_pre["ordinal"],
                line_pre["native_name"])!=(
                pending["pre"]["time_ms"],pending["pre"]["list"],
                pending["pre"]["ordinal"],pending["pre"]["native_name"]):
                raise NativeProofBridgeError("SYNC_LINE_PRE_SOURCE_POINTER_DRIFT")
            pending.setdefault("original_post_line_pre",[]).append(line_pre)
            if len(pending["original_post_line_pre"])!=1:
                raise NativeProofBridgeError("DUPLICATE_SYNC_LINE_PRE_SOURCE_MARKER")
            return
        cast_pre=parse_cast(line)
        if cast_pre is not None:
            if pending is None or (
                cast_pre["time_ms"],cast_pre["list"],cast_pre["ordinal"],
                cast_pre["native_name"])!=(
                pending["pre"]["time_ms"],pending["pre"]["list"],
                pending["pre"]["ordinal"],pending["pre"]["native_name"]):
                raise NativeProofBridgeError("CAST_PRE_SOURCE_POINTER_DRIFT")
            pending.setdefault("original_post_cast_pre",[]).append(cast_pre)
            if len(pending["original_post_cast_pre"])!=1:
                raise NativeProofBridgeError("DUPLICATE_CAST_PRE_SOURCE_MARKER")
            return
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
        raw_cost=self._raw_cost
        raw_resource=self._raw_resource
        ambiguous_resource=self._resource_ambiguous
        self._raw_cost=None
        self._raw_resource=None
        self._resource_ambiguous=False
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
        if (not ambiguous_resource and raw_cost is not None and
            (raw_cost["time_ms"],raw_cost["native_action"])==(k[0],k[3]) and
            pending["pre"].get("source_cost_affordable")==1 and
            pending["base_action_entries"]==1 and
            pending["base_ready_entries"]==1):
            numerical,reason=independent_numeric_resource(raw_cost,raw_resource)
            if numerical is not None:
                if numerical!=1:
                    raise NativeProofBridgeError(
                        "ORIGINAL_PRE_COST_SUCCESS_CONTRADICTS_INDEPENDENT_NUMERIC")
                insert("RESOURCE",True,
                       receipt="original_cost_invocation_plus_independent_numeric:"+reason)
                self.counters["independent_source_resource_positive"]+=1
        # Source-gated conjunction for base action_t::action_ready():
        #   !line_cooldown->down() AND !sync_action
        # A present line cooldown with ready_ms <= now is numerically
        # ready (pinned cooldown_t::down() source). A null sync pointer
        # makes virtual sync_action->action_ready() inapplicable.
        # Do NOT promote a positive marker when a sync target exists:
        # its own recursive readiness is not independently known.
        # Nor treat absence of a line cooldown pointer as proof that
        # the unconditional base method can run.
        post_lines=pending.get("original_post_line_pre",[])
        if len(post_lines)>1:
            raise NativeProofBridgeError("DUPLICATE_SYNC_LINE_PRE_SOURCE_MARKER")
        if post_lines:
            line=post_lines[0]
            if (line["time_ms"],line["list"],line["ordinal"],
                line["native_name"])!=k:
                raise NativeProofBridgeError("SYNC_LINE_PRE_ATTEMPT_IDENTITY_CHANGED")
            if (pending.get("base_action_entries")==1 and
                pending.get("base_ready_entries")==1 and
                row["method_base_path_source_observed"]):
                if not line["line_cd_present"]:
                    self.counters["sync_line_base_cooldown_pointer_missing_unknown"]+=1
                elif line["line_cd_ready_ms"]>k[0]:
                    self.counters["sync_line_base_cooldown_down_unknown"]+=1
                elif line["has_sync_action"]:
                    self.counters["sync_line_nested_sync_readiness_unknown"]+=1
                else:
                    if row["source_base_exit_observed"] in (
                            "LINE_COOLDOWN_FALSE","SYNC_FALSE"):
                        raise NativeProofBridgeError(
                            "INDEPENDENT_PRE_SYNC_LINE_VS_NATIVE_EXIT_CONFLICT")
                    insert("SYNC_LINE",True,
                           receipt="source_original_select_PRE_line_clock_and_no_sync")
                    self.counters["independent_source_sync_line_positive"]+=1
            else:
                self.counters["sync_line_base_route_missing_unknown"]+=1
        # Reuse the already audited numeric postguard subset. These are
        # specific source predicates, NOT a proof of full MOVEMENT or
        # CAST_GCD: class-specific movement directionality and the base
        # usable-while-casting/GCD route still need source evidence.
        original_postguard_subguards=None
        post_casts=pending.get("original_post_cast_pre",[])
        if len(post_casts)>1:
            raise NativeProofBridgeError("DUPLICATE_CAST_PRE_SOURCE_MARKER")
        if post_casts and not post_lines:
            raise NativeProofBridgeError("CAST_PRE_WITHOUT_LINE_PRE_MARKER")
        if pending.get("base_ready_entries")==1 and (
                pending["pre"].get("player_is_moving") == 0):
            # action_t::ready(): is_moving() && !usable_moving()
            # is independent false when stationary (no method shortcut bit).
            insert("MOVEMENT_BASE_GUARD_PASS",True,
                   receipt="original_ready_PRE_nonmoving_short_circuit")
            self.counters["independent_base_movement_nonmoving"]+=1
        if post_lines and post_casts:
            cast=post_casts[0]
            if (cast["time_ms"],cast["list"],cast["ordinal"],
                cast["native_name"])!=k:
                raise NativeProofBridgeError("CAST_PRE_ATTEMPT_IDENTITY_CHANGED")
            source_subset=independent_postguard_subset(post_lines[0],cast)
            movement_option_ok=not source_subset["moving_option_mismatch"]
            repeat_cast_ok=not source_subset["repeat_cast_prohibited"]
            # Replayed raw PRE, not the later Native selected/ready result.
            if (pending.get("base_action_entries")==1 and
                pending.get("base_ready_entries")==1):
                actor_moving=post_lines[0]["actor_moving"]
                source_moving=pending["pre"].get("player_is_moving")
                if source_moving in (0,1) and actor_moving!=source_moving:
                    raise NativeProofBridgeError(
                        "SAME_ATTEMPT_PRE_MOVEMENT_FIELDS_CONFLICT")
                if movement_option_ok:
                    insert("MOVEMENT_APL_OPTION_CLEAR",True,
                           receipt="original_postguard_PRE_moving_option_boolean")
                    self.counters["independent_moving_option_clear"]+=1
                if repeat_cast_ok:
                    insert("CAST_REPEAT_CLEAR",True,
                           receipt="original_postguard_PRE_repeat_cast_boolean")
                    self.counters["independent_cast_repeat_clear"]+=1
            if row["source_base_exit_observed"]=="FULL_BASE_TRUE" and not (
                    movement_option_ok and repeat_cast_ok):
                raise NativeProofBridgeError(
                    "ORIGINAL_PRE_GUARD_VS_FINAL_BASE_EXIT_CONFLICT")
            original_postguard_subguards={
                "movement_option_matches_source_PRE":movement_option_ok,
                "repeat_cast_rule_matches_source_PRE":repeat_cast_ok,
                "base_ready_movement_branch_bypassed":(
                    True if (pending.get("base_ready_entries")==1 and
                             pending["pre"].get("player_is_moving") == 0)
                    else False if (pending.get("base_ready_entries")==1 and
                                   pending["pre"].get("player_is_moving") == 1)
                    else None),
                "movement_directionality":"UNKNOWN",
                "cast_GCD_full_route":"UNKNOWN",
                "movement_full_route":"UNKNOWN",
                "original_source_virtual_ready_used_as_operand":False,
            }
            self.counters["independent_source_postguard_subset"]+=1
            if movement_option_ok:
                self.counters["independent_source_moving_option_pass"]+=1
            if repeat_cast_ok:
                self.counters["independent_source_repeat_cast_pass"]+=1
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
        # Preserve adjudicated facts for portable export. A negative gate
        # withheld for independent soundness review must not reappear later.
        effective_facts=list(facts.values())
        verdict=decide_candidate(identity,contract,effective_facts,
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
            effective_facts=[f for f in effective_facts if f.value is not False]
            verdict=decide_candidate(
                identity,contract,effective_facts,
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
        # Opt-in transfer; legacy portable source receipts remain unchanged.
        # Only source-exact physical actions and independently replayed
        # method-PRE facts are eligible. No Native post comparator is exported
        # as a gate. Full virtual route remains open and hence not READY.
        portable_candidate=None
        if (self.export_source_gate_claims and
            (self.export_focus_at_ms is None or
             k[0]==self.export_focus_at_ms)):
            if (row.get("source_behavior")=="ACTION" and
                row["source_action"]==k[3]):
                trusted=[f for f in effective_facts
                         if f.basis=="INDEPENDENT_SOURCE_REPLAY" and
                         f.captured=="SIMC_ORIGINAL_METHOD_PRE"]
                portable_candidate={
                    "source_list":k[1],"source_index":k[2]-1,
                    "action":row["source_action"],
                    "source_row_sha256":row["source_sha256"],
                    "route":{"source":contract.source,
                             "required":list(contract.required),
                             "closed":False,"closure_receipt":None},
                    "facts":[{
                        "gate":f.gate,"value":f.value,"basis":f.basis,
                        "captured":f.captured,"event_t_ms":f.event_t_ms,
                        "receipt":f.receipt} for f in trusted]
                }
                if len(self.portable_source_gate_claims)>=10000:
                    raise NativeProofBridgeError("PORTABLE_SOURCE_CLAIM_VOLUME_EXCEEDED")
                self.portable_source_gate_claims.append({
                    "decision_at_ms":identity.t_ms,
                    "source_occurrence":identity.occurrence,
                    "source_gate_decision":verdict["decision"],
                    "candidate":portable_candidate,
                    "native_ready_or_selected_used_as_gate":False,
                    "complete_positive_route_proven":False,
                })
            else:
                self.counters["portable_claim_control_or_alias_skipped"]+=1
        return {
            "identity":{
                "scope":identity.scope,"source_sha256":identity.source_sha256,
                "at_ms":identity.t_ms,"ordinal":identity.ordinal,
                "same_key_occurrence":identity.occurrence},
            "decision":verdict["decision"],
            "source_action_kind":(
                "APL_CONTROL" if row["source_action"] in CONTROL_COMMANDS
                else "EXECUTABLE_SOURCE_ACTION"),
            "blockers":verdict["blockers"],
            "missing_or_unverified":verdict["missing_or_unverified"],
            "original_PRE_postguard_subpredicates":original_postguard_subguards,
            "independent_true_gates":verdict["independent_true"],
            "independent_false_gates":verdict["independent_false"],
            "source_only_positive_gates":verdict["source_only"],
            "full_ready_positive_closed":False,
            "Native_ready_comparator_NOT_USED":True,
            "portable_source_claim_optional":portable_candidate,
            "portable_claim_positive_ROUTE_CLOSURE":False,
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
            kind=proof[-1]["source_action_kind"]
            if kind not in ("APL_CONTROL","EXECUTABLE_SOURCE_ACTION"):
                raise NativeProofBridgeError("UNKNOWN_SELECTED_SOURCE_KIND")
            result["source_return_kind"]=kind
            if (kind=="EXECUTABLE_SOURCE_ACTION" and
                    result["returned_READINESS"]==UNKNOWN and
                    result["earlier_UNKNOWN"]==0 and
                    result["earlier_READY"]==0):
                # The Native-selected row is a provenance comparator only.
                # Proof gates and prior NOT_READY outcomes came from
                # independent source replay, not the Native ready bit.
                chosen=attempts[-1]
                candidate=proof[-1]
                key=chosen["source_key"]
                if (key[0]!=candidate["identity"]["at_ms"] or
                    key[1]!=candidate["identity"]["scope"].split("::",1)[0] or
                    key[2]-1!=candidate["identity"]["ordinal"] or
                    chosen["source_sha256"]!=candidate["identity"]["source_sha256"]):
                    raise NativeProofBridgeError("POSITIVE_GAP_SOURCE_POINTER_DRIFT")
                if (candidate["full_ready_positive_closed"] or
                    candidate["decision"]!=UNKNOWN):
                    raise NativeProofBridgeError("UNCERTIFIED_SOURCE_SELECTED_READY")
                self.counters["positive_gap_actual_selected_candidates"]+=1
                if result["earlier_NOT_READY"]>0:
                    self.counters["positive_gap_with_nonempty_proven_prior"]+=1
                else:
                    self.counters["positive_gap_vacuous_empty_prior"]+=1
                gap={
                    "at_simc_ms":key[0],"source_list":key[1],
                    "source_index":key[2]-1,"source_action":chosen["source_action"],
                    "source_native_name_identity_only":key[3],
                    "source_row_sha256":chosen["source_sha256"],
                    "same_source_key_occurrence":candidate["identity"]["same_key_occurrence"],
                    "earlier_candidates":len(proof)-1,
                    "earlier_independent_NOT_READY":result["earlier_NOT_READY"],
                    "unproved_gates":candidate["missing_or_unverified"],
                    "original_PRE_postguard_subpredicates":(
                        candidate["original_PRE_postguard_subpredicates"]),
                    "native_observed_post_only_gates":candidate["source_only_positive_gates"],
                    "native_observed_base_exit_comparator":chosen["source_base_exit_observed"],
                    "physical_skill_READY":"UNKNOWN","source_order_complete":False
                }
                # Keep the smallest evidence gap first; preference is for
                # a proven, nonempty earlier priority prefix. The shortlist
                # is a source-grounded *research target*, not a recommendation.
                self.positive_gap_shortlist.append(gap)
                self.positive_gap_shortlist.sort(key=lambda e:(
                    len(e["unproved_gates"]),len(e["native_observed_post_only_gates"]),
                    -e["earlier_independent_NOT_READY"],
                    e["at_simc_ms"],e["source_list"],e["source_index"],
                    e["same_source_key_occurrence"]))
                del self.positive_gap_shortlist[12:]
            self.counters["source_returned_roots"]+=1
            self.counters["returned_"+kind]+=1
            self.counters["returned_"+result["returned_READINESS"]]+=1
            if result["earlier_UNKNOWN"]==0:
                self.counters["returned_all_prior_proven_not_ready_but_winner_unknown"]+=1
                self.counters["returned_"+kind+"_all_prior_excluded_but_winner_UNKNOWN"]+=1
            else:
                self.counters["returned_"+kind+"_with_prior_UNKNOWN"]+=1
            for field in proof[-1]["blockers"]:
                self.counters["selected_blocker_"+field]+=1
        return result

    def summary(self)->dict:
        return {"schema":SCHEMA,
                "counts":dict(sorted(self.counters.items())),
                "Source_and_Native_comparators_not_readiness_operands":True,
                "spec_semantics_only_via_adapter_callback":True,
                "full_positive_ready_certified":False,
                "positive_ready_preflight":{
                    "schema":"ZrotSourcePinnedPositiveReadyGapPreflightV1",
                    "candidate_count":self.counters["positive_gap_actual_selected_candidates"],
                    "with_proven_nonempty_prior":self.counters["positive_gap_with_nonempty_proven_prior"],
                    "vacuous_empty_prior":self.counters["positive_gap_vacuous_empty_prior"],
                    "bounded_source_candidates":list(self.positive_gap_shortlist),
                    "complete_source_virtual_route_closure":False,
                    "Native_return_never_positive_ready_evidence":True,
                    "WCL_priority_or_dummy_error_proven":False},
                "WCL_API_calls":0}

def selftest():
    # Minimal source-pointer-compatible proof: independent proven
    # negative stays negative, source-observed true stays UNKNOWN.
    h="a"*64
    bridge=NativeProofBridge()
    pending={"pre":{"time_ms":20,"list":"default","ordinal":1,
                    "native_name":"alpha"},"clock":None,"tolerance":None,
             "base_ready_entries":0}
    row={"source_key":(20,"default",1,"alpha"),
         "source_sha256":h,"source_action":"alpha",
         "source_behavior":"ACTION",
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
    resource_bridge=NativeProofBridge()
    resource_bridge.consume(ACTION_MARK+"20|alpha|1|0|10",None)
    resource_bridge.consume(PLAYER_MARK+"20|1|10|30|0",None)
    resource_pending=dict(pending,
        pre=dict(pending["pre"],source_cost_affordable=1),
        base_action_entries=1,base_ready_entries=1)
    positive_resource=resource_bridge.evaluate_attempt(resource_pending,nxt)
    assert positive_resource["decision"]==UNKNOWN
    assert "RESOURCE" in positive_resource["independent_true_gates"]
    assert resource_bridge.summary()["counts"]["independent_source_resource_positive"]==1
    assert "RESOURCE:MISSING" not in positive_resource["missing_or_unverified"]
    # Two source-original physical predicates are both sufficient for
    # SYNC_LINE, but not for the action's full virtual READY route.
    line_ready=LINE_MARK+"20|default|1|alpha|1|10|0|1|-1|0|0"
    sync_bridge=NativeProofBridge()
    sync_bridge.consume(line_ready,resource_pending)
    sync_ok=sync_bridge.evaluate_attempt(resource_pending,nxt)
    assert sync_ok["decision"]==UNKNOWN
    assert "SYNC_LINE" in sync_ok["independent_true_gates"]
    assert "SYNC_LINE:MISSING" not in sync_ok["missing_or_unverified"]
    scoped_sub=NativeProofBridge()
    scoped_pending=fresh_post_pending() if "fresh_post_pending" in locals() else dict(
        resource_pending,original_post_line_pre=[])
    scoped_sub.consume(line_ready,scoped_pending)
    scoped_sub.consume(CAST_MARK+"20|default|1|alpha|0|0|0|0|0|0",scoped_pending)
    sub_out=scoped_sub.evaluate_attempt(scoped_pending,nxt)
    check=sub_out["original_PRE_postguard_subpredicates"]
    assert check["movement_option_matches_source_PRE"] is True
    assert check["repeat_cast_rule_matches_source_PRE"] is True
    assert check["base_ready_movement_branch_bypassed"] is None
    assert check["movement_full_route"]=="UNKNOWN"
    assert check["cast_GCD_full_route"]=="UNKNOWN"
    assert "MOVEMENT_APL_OPTION_CLEAR" in sub_out["independent_true_gates"]
    assert "CAST_REPEAT_CLEAR" in sub_out["independent_true_gates"]
    assert "MOVEMENT_BASE_GUARD_PASS:MISSING" in sub_out["missing_or_unverified"]
    assert "MOVEMENT:MISSING" in sub_out["missing_or_unverified"]
    assert "CAST_GCD:MISSING" in sub_out["missing_or_unverified"]
    assert sub_out["decision"]==UNKNOWN
    # A source-PRE stationary actor proves only the base movement
    # short-circuit, not the full movement directionality route.
    still_bridge=NativeProofBridge()
    still_pending=dict(resource_pending,
        pre=dict(resource_pending["pre"],player_is_moving=0),
        original_post_line_pre=[],original_post_cast_pre=[])
    still_bridge.consume(line_ready,still_pending)
    still_bridge.consume(
        CAST_MARK+"20|default|1|alpha|0|0|0|0|0|0",still_pending)
    stationary=still_bridge.evaluate_attempt(still_pending,nxt)
    assert "MOVEMENT_BASE_GUARD_PASS" in stationary["independent_true_gates"]
    assert "MOVEMENT_BASE_GUARD_PASS:MISSING" not in stationary["missing_or_unverified"]
    assert "MOVEMENT:MISSING" in stationary["missing_or_unverified"]
    assert "CAST_GCD:MISSING" in stationary["missing_or_unverified"]
    assert stationary["decision"]==UNKNOWN
    # Same source decision/occurrence contradictory movement facts
    # cannot be silently treated as an independent positive gate.
    disagree=NativeProofBridge()
    conflict=dict(still_pending,original_post_line_pre=[],
                  original_post_cast_pre=[])
    disagree.consume(
        LINE_MARK+"20|default|1|alpha|1|10|0|1|-1|1|0",conflict)
    disagree.consume(
        CAST_MARK+"20|default|1|alpha|0|0|0|0|0|0",conflict)
    try:disagree.evaluate_attempt(conflict,nxt)
    except NativeProofBridgeError:pass
    else:raise AssertionError("CONTRADICTORY_SOURCE_MOVING_PRE_ACCEPTED")
    wrong_repeat=NativeProofBridge()
    wrong_pending=dict(resource_pending,original_post_line_pre=[],
                       original_post_cast_pre=[])
    wrong_repeat.consume(line_ready,wrong_pending)
    wrong_repeat.consume(CAST_MARK+"20|default|1|alpha|0|0|0|1|1|0",
                         wrong_pending)
    try:wrong_repeat.evaluate_attempt(wrong_pending,nxt)
    except NativeProofBridgeError:pass
    else:raise AssertionError("FORGED_POSTGUARD_FINAL_BASE_SUCCESS_ACCEPTED")
    wrong_pointer=NativeProofBridge()
    try:wrong_pointer.consume(
        CAST_MARK+"20|default|2|alpha|0|0|0|0|0|0",
        dict(resource_pending,original_post_line_pre=[]))
    except NativeProofBridgeError:pass
    else:raise AssertionError("CAST_PRE_POINTER_DRIFT_ACCEPTED")
    assert sync_bridge.summary()["counts"]["independent_source_sync_line_positive"]==1
    # A sync child requires its own unknown readiness; one positive
    # outer cooldown cannot certify its virtual recursive action_ready.
    def fresh_post_pending():
        # Every original source attempt has its own pending marker buffer.
        # Reusing the prior test's mutable dict for a second attempt
        # would correctly be flagged as a duplicate marker.
        return dict(resource_pending,original_post_line_pre=[])
    with_sync=NativeProofBridge()
    with_sync_pending=fresh_post_pending()
    with_sync.consume(LINE_MARK+"20|default|1|alpha|1|10|0|1|-1|0|1",
                      with_sync_pending)
    sync_unknown=with_sync.evaluate_attempt(with_sync_pending,nxt)
    assert "SYNC_LINE:MISSING" in sync_unknown["missing_or_unverified"]
    line_down=NativeProofBridge()
    down_pending=fresh_post_pending()
    line_down.consume(LINE_MARK+"20|default|1|alpha|1|30|0|1|-1|0|0",
                      down_pending)
    down_unknown=line_down.evaluate_attempt(down_pending,nxt)
    assert "SYNC_LINE:MISSING" in down_unknown["missing_or_unverified"]
    absent_line=NativeProofBridge()
    absent_pending=fresh_post_pending()
    absent_line.consume(LINE_MARK+"20|default|1|alpha|0|0|0|1|-1|0|0",
                        absent_pending)
    absent_unknown=absent_line.evaluate_attempt(absent_pending,nxt)
    assert "SYNC_LINE:MISSING" in absent_unknown["missing_or_unverified"]
    duplicate=NativeProofBridge()
    duplicate_pending=fresh_post_pending()
    duplicate.consume(line_ready,duplicate_pending)
    try:duplicate.consume(line_ready,duplicate_pending)
    except NativeProofBridgeError:pass
    else:raise AssertionError("DUPLICATE_SYNC_LINE_SOURCE_PRE_ACCEPTED")
    mismatched=NativeProofBridge()
    try:mismatched.consume(line_ready.replace("|default|1|alpha|",
                                                  "|default|2|alpha|"),
                           fresh_post_pending())
    except NativeProofBridgeError:pass
    else:raise AssertionError("MISMATCHED_SYNC_LINE_SOURCE_ROW_ACCEPTED")
    not_base=NativeProofBridge()
    no_base_pending=dict(fresh_post_pending(),base_action_entries=0)
    not_base.consume(line_ready,no_base_pending)
    not_base_result=not_base.evaluate_attempt(no_base_pending,nxt)
    assert "SYNC_LINE:MISSING" in not_base_result["missing_or_unverified"]
    rejected_resource=NativeProofBridge()
    rejected_resource.consume(ACTION_MARK+"20|alpha|1|0|50",None)
    rejected_resource.consume(PLAYER_MARK+"20|1|50|30|0",None)
    try:
        rejected_resource.evaluate_attempt(resource_pending,nxt)
    except NativeProofBridgeError:
        pass
    else:
        raise AssertionError("INDEPENDENT_NUMERIC_COST_CONFLICT_ACCEPTED")
    assert b["identity"]["same_key_occurrence"]==1
    root=bridge.evaluate_root([
        {"generic_proof":a,"source_key":row["source_key"],
         "source_sha256":h,"source_action":row["source_action"],
         "source_base_exit_observed":row["source_base_exit_observed"]},
        {"generic_proof":b,"source_key":nxt["source_key"],
         "source_sha256":h,"source_action":nxt["source_action"],
         "source_base_exit_observed":nxt["source_base_exit_observed"]}],
        returned=True,observed_name="alpha")
    assert root["earlier_NOT_READY"]==1
    assert root["decision"]==UNKNOWN
    assert root["returned_READINESS"]==UNKNOWN
    assert root["source_return_kind"]=="EXECUTABLE_SOURCE_ACTION"
    ctl=dict(nxt,source_action="run_action_list")
    control_proof=bridge.evaluate_attempt(pending,ctl)
    assert control_proof["decision"]==UNKNOWN
    assert control_proof["source_action_kind"]=="APL_CONTROL"
    root_control=bridge.evaluate_root(
        [{"generic_proof":a},{"generic_proof":control_proof}],
        returned=True,observed_name="run_action_list")
    assert root_control["source_return_kind"]=="APL_CONTROL"
    assert bridge.summary()["counts"]["returned_APL_CONTROL"]==1
    assert bridge.summary()["counts"]["returned_EXECUTABLE_SOURCE_ACTION"]==1
    preflight=bridge.summary()["positive_ready_preflight"]
    assert preflight["candidate_count"]==1
    assert preflight["with_proven_nonempty_prior"]==1
    assert preflight["vacuous_empty_prior"]==0
    assert preflight["bounded_source_candidates"][0]["source_row_sha256"]==h
    assert preflight["bounded_source_candidates"][0]["physical_skill_READY"]==UNKNOWN
    assert "BASE_VIRTUAL_COMPLETE" in preflight["bounded_source_candidates"][0]["native_observed_post_only_gates"]
    assert preflight["complete_source_virtual_route_closure"] is False
    # Producer -> pinned APL decoder -> generic evaluator round-trip.
    # This only replays synthetic source facts; not new original SimC proof.
    from simc_apl_semantic_ir_v2 import parse_profile,git_blob
    from general_rotation_simc_state_conditioned_evaluator_v1 import (
        ADAPTER_GATE_BUNDLE_SCHEMA,POLICY,decode_adapter_gate_bundle,
        evaluate as evaluate_source_scan)
    synthetic_profile=b"actions=alpha\n"
    profile_blob=git_blob(synthetic_profile)
    parsed=parse_profile(
        synthetic_profile,require_source=True,
        expected_git_blob=profile_blob)
    source_row=parsed["action_lists"]["default"][0]
    scoped=dict(row,source_sha256=source_row["source_sha256"])
    producer=NativeProofBridge(export_source_gate_claims=True)
    scoped_negative=producer.evaluate_attempt(dict(pending),scoped)
    claim=scoped_negative["portable_source_claim_optional"]
    assert claim is not None
    assert claim["route"]["closed"] is False
    assert claim["facts"][0]["gate"]=="NECESSARY_ELIGIBILITY"
    assert claim["facts"][0]["value"] is False
    def full_bundle(candidate):
        return {"schema":ADAPTER_GATE_BUNDLE_SCHEMA,"policy_id":POLICY,
                "source_git_blob_sha1":profile_blob,
                "decision_at_ms":20,"source_occurrence":0,
                "candidates":[candidate]}
    # Upstream verified raw-source replay can independently adjudicate
    # necessary gates against a pinned APL row. The plain JSON API has no
    # such producer authentication and MUST NOT use either false or true
    # claims to select/skip an action.
    mapping=decode_adapter_gate_bundle(
        full_bundle(claim),parsed["action_lists"],
        source_blob=profile_blob,at_ms=20,occurrence=0)
    verified=next(iter(mapping.values()))
    independently_replayed=decide_candidate(
        verified.identity,verified.contract,verified.facts,
        is_physical_action=True)
    assert independently_replayed["decision"]==NOT_READY
    negative_replay=evaluate_source_scan(
        synthetic_profile,profile_blob,at_ms=20,
        external_strict_pre={},adapter_gate_bundle=full_bundle(claim))
    assert negative_replay["result"]["status"]=="UNKNOWN"
    assert negative_replay["source_reason_ledger"][0][
        "ready_gate_blockers"]==[
        "UNAUTHENTICATED_EXTERNAL_GATE_CLAIM_NOT_DECISION"]
    assert negative_replay["reason_counts"].get("READY_FALSE",0)==0
    assert negative_replay["dummy_trainer_error_permitted"] is False
    positive_producer=NativeProofBridge(export_source_gate_claims=True)
    scoped_unknown=dict(nxt,source_sha256=source_row["source_sha256"])
    scoped_positive=positive_producer.evaluate_attempt(
        dict(pending),scoped_unknown)
    positive_claim=scoped_positive["portable_source_claim_optional"]
    assert positive_claim is not None
    assert all(f["basis"]=="INDEPENDENT_SOURCE_REPLAY"
               for f in positive_claim["facts"])
    assert "BASE_VIRTUAL_COMPLETE" not in {
        f["gate"] for f in positive_claim["facts"]}
    incomplete_replay=evaluate_source_scan(
        synthetic_profile,profile_blob,at_ms=20,
        external_strict_pre={},adapter_gate_bundle=full_bundle(positive_claim))
    assert incomplete_replay["result"]["status"]=="UNKNOWN"
    assert incomplete_replay["external_gate_bundle_claims"]==1
    assert incomplete_replay[
        "external_gate_bundle_provenance_authenticity_verified_here"] is False
    # Even an opt-in original method exporter must preserve the independently
    # adjudicated negative and open-world UNKNOWN contracts.
    focused=NativeProofBridge(export_source_gate_claims=True,
                              export_focus_at_ms=20)
    focus_row=dict(scoped,source_key=(20,"default",1,"alpha"))
    focused.evaluate_attempt(dict(pending),focus_row)
    assert len(focused.portable_source_gate_claims)==1
    assert focused.portable_source_gate_claims[0]["source_occurrence"]==0
    assert focused.portable_source_gate_claims[0][
        "source_gate_decision"]==NOT_READY
    ignored=dict(focus_row,source_key=(21,"default",1,"alpha"))
    ignored_pending=dict(pending,pre=dict(pending["pre"],time_ms=21))
    focused.evaluate_attempt(ignored_pending,ignored)
    assert len(focused.portable_source_gate_claims)==1
    nonphysical=NativeProofBridge(export_source_gate_claims=True,
                                  export_focus_at_ms=20)
    side_effect=dict(scoped,source_behavior="SIDE_EFFECT_SOURCE_MODEL_UNVERIFIED")
    excluded=nonphysical.evaluate_attempt(dict(pending),side_effect)
    assert excluded["portable_source_claim_optional"] is None
    assert len(nonphysical.portable_source_gate_claims)==0
    for bad in (
        lambda:NativeProofBridge(export_focus_at_ms=20),
        lambda:NativeProofBridge(export_source_gate_claims=True,
                                 export_focus_at_ms=-1),
    ):
        try:bad()
        except NativeProofBridgeError:pass
        else:raise AssertionError("UNSCOPED_SOURCE_GATE_EXPORT_ALLOWED")
    # Fake native positive bit cannot certify a skill: this adapter does
    # not even expose Native ready as an accepted input.
    assert "native_ready" not in bridge.summary()["counts"]
    return {"schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
            "checks":41,"portable_adapter_round_trip":True,
             "partial_movement_and_cast_guards_independently_replayed":True,
             "portable_gates_positive_READY":0,
             "real_native":"NOT_RUN","WCL_API_calls":0}

if __name__=="__main__":
    import json
    print(json.dumps(selftest(),sort_keys=True))
