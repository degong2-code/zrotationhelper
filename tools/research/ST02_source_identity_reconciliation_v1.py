#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ST-02: pinned SimC source-obligation/typed-identity reconciliation.

RESEARCH ONLY. Never use this file in independent WCL blind discovery.
This is a structural source coverage compiler for the EXISTING ST-01 gate,
NOT a new readiness evaluator, independent mechanic attestation, or
current-game action-ID certification. Source documents remain candidates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping

GATE_SCHEMA = "ZrotSourceObligationGateV1"
PHASE = "POST_SIMC_HYPOTHESIS_RESEARCH_ONLY"
HEX40 = re.compile(r"^[a-f0-9]{40}$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")
KINDS = frozenset((
    "SIMC_APL_ACTION_TOKEN", "SIMC_ACTION_OBJECT_ID",
    "GAME_SPELL_ID_CANDIDATE", "WCL_CAST_EVENT_ID",
    "WCL_AURA_EFFECT_ID", "WCL_DAMAGE_EFFECT_ID",
))


class ST02ContractError(ValueError):
    pass


@dataclass(frozen=True)
class SourceAudit:
    coverage_status: str
    identity_status: str
    source_spec: str
    identity_spec: str
    action_token: str
    missing_gate_ids: tuple[str, ...]
    unverified_gate_ids: tuple[str, ...]
    accepted_gate_ids: tuple[str, ...]
    source_pin_sha1: str
    identity_pin_sha1: str
    gameplay_ready_certified: int = 0
    wcl_blind_candidate_lock: str = "NOT_IN_SCOPE"
    user_recommendation_eligible: bool = False
    authority_promotion: bool = False

    def to_dict(self):
        return asdict(self)


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _pinned_json(data: bytes, pin: str, name: str) -> Mapping[str, Any]:
    if not isinstance(data, bytes) or not HEX40.fullmatch(pin or ""):
        raise ST02ContractError("INVALID_" + name + "_PIN")
    if git_blob_sha1(data) != pin:
        raise ST02ContractError(name + "_SOURCE_BYTES_MISMATCH")
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ST02ContractError(name + "_INVALID_JSON") from exc
    if not isinstance(obj, dict):
        raise ST02ContractError(name + "_INVALID_ROOT")
    return obj


def _one(items: object, predicate, name: str) -> Mapping[str, Any]:
    if not isinstance(items, list):
        raise ST02ContractError(name + "_LIST_REQUIRED")
    matches = [x for x in items if isinstance(x, dict) and predicate(x)]
    if len(matches) != 1:
        raise ST02ContractError(name + "_MISSING_OR_AMBIGUOUS")
    return matches[0]


def _nonempty(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ST02ContractError("MISSING_" + name)
    return value


def _typed_node(value: object) -> tuple[str, object]:
    if not isinstance(value, dict) or set(value) != {"kind", "id"}:
        raise ST02ContractError("INVALID_TYPED_NODE")
    kind, id_value = value["kind"], value["id"]
    if kind not in KINDS:
        raise ST02ContractError("UNKNOWN_IDENTITY_KIND")
    if kind == "SIMC_APL_ACTION_TOKEN":
        _nonempty(id_value, "ACTION_TOKEN")
    elif type(id_value) is not int or id_value <= 0:
        raise ST02ContractError("INVALID_NUMERIC_IDENTITY")
    if kind.startswith("WCL_"):
        raise ST02ContractError("WCL_PRE_LOCK_SEMANTIC_RELATION_FORBIDDEN")
    return kind, id_value


def _relations(edges: object, token: str, object_id: int, spell_id: int) -> None:
    """Require two EXPLICIT typed candidate links; equal numbers prove nothing."""
    if not isinstance(edges, list) or len(edges) != 2:
        raise ST02ContractError("TWO_EXPLICIT_IDENTITY_LINKS_REQUIRED")
    expected = {
        (("SIMC_APL_ACTION_TOKEN", token),
         ("SIMC_ACTION_OBJECT_ID", object_id)),
        (("SIMC_ACTION_OBJECT_ID", object_id),
         ("GAME_SPELL_ID_CANDIDATE", spell_id)),
    }
    actual = set()
    for edge in edges:
        if not isinstance(edge, dict):
            raise ST02ContractError("INVALID_IDENTITY_EDGE")
        source = _typed_node(edge.get("from"))
        target = _typed_node(edge.get("to"))
        _nonempty(edge.get("evidence_ref"), "IDENTITY_EDGE_EVIDENCE")
        if edge.get("status") != "UNVERIFIED_CANDIDATE":
            raise ST02ContractError("IDENTITY_AUTHORITY_NOT_ESTABLISHED")
        pair = (source, target)
        if pair in actual:
            raise ST02ContractError("DUPLICATE_IDENTITY_EDGE")
        actual.add(pair)
    if actual != expected:
        raise ST02ContractError("IDENTITY_RELATION_MISMATCH")


def reconcile(
    *, source_json: bytes, source_blob_sha1: str,
    identity_json: bytes, identity_blob_sha1: str,
    selector: Mapping[str, Any], relation_edges: list[Mapping[str, Any]],
    declared_gates: list[Mapping[str, Any]],
) -> tuple[SourceAudit, dict[str, Any]]:
    """Return audit + fail-closed ST-01 Gate inputs; no gameplay verdict."""
    source = _pinned_json(source_json, source_blob_sha1, "SOURCE_OBLIGATION")
    identities = _pinned_json(identity_json, identity_blob_sha1, "IDENTITY")
    if source.get("schema") != "ZrotBranchSimcReadinessSourceGapV1":
        raise ST02ContractError("SOURCE_SCHEMA_MISMATCH")
    if identities.get("schema") != "ZrotSimcExternalGameSpellIdentityCandidateV13":
        raise ST02ContractError("IDENTITY_SCHEMA_MISMATCH")
    if identities.get("all_gameplay_ids_certified") != 0 or identities.get("gameplay_rule_promotion") is not False:
        raise ST02ContractError("UNAPPROVED_GAMEPLAY_ID_AUTHORITY_CHANGE")
    for field in ("source_spec", "identity_spec", "action_token",
                  "spec_scope_evidence_ref", "mapping_evidence_ref"):
        _nonempty(selector.get(field), field)
    action = _one(
        source.get("candidate_actions"),
        lambda x: x.get("spec") == selector["source_spec"]
        and x.get("action") == selector["action_token"],
        "PINNED_SOURCE_ACTION")
    candidate = _one(
        identities.get("candidates"),
        lambda x: x.get("spec") == selector["identity_spec"]
        and x.get("action_token") == selector["action_token"],
        "PINNED_IDENTITY_ACTION")
    native_id = candidate.get("native_action_t_id")
    candidate_id = candidate.get("candidate_game_spell_id")
    if type(native_id) is not int or native_id <= 0 or \
            type(candidate_id) is not int or candidate_id <= 0:
        raise ST02ContractError("PINNED_CANDIDATE_NUMERIC_ID_INVALID")
    if (selector.get("simc_action_object_id") != native_id or
            selector.get("candidate_game_spell_id") != candidate_id or
            type(selector.get("simc_action_object_id")) is not int or
            type(selector.get("candidate_game_spell_id")) is not int):
        raise ST02ContractError("SOURCE_CANDIDATE_ID_MISMATCH")
    apl_sha = action.get("effective_apl_sha256")
    if not isinstance(apl_sha, str) or not HEX64.fullmatch(apl_sha):
        raise ST02ContractError("SOURCE_APL_SHA256_INVALID")
    if selector.get("effective_apl_sha256") != apl_sha:
        raise ST02ContractError("SOURCE_APL_VERSION_MISMATCH")
    if (selector.get("profile_build") != action.get("profile_build") or
            not isinstance(action.get("profile_build"), str)):
        raise ST02ContractError("SOURCE_BUILD_SCOPE_MISMATCH")
    _relations(relation_edges, selector["action_token"], native_id, candidate_id)

    source_gates = action.get("extra_source_obligations")
    if not isinstance(source_gates, list) or not source_gates:
        raise ST02ContractError("SOURCE_OBLIGATIONS_MISSING")
    expected = {}
    for gate in source_gates:
        if not isinstance(gate, dict):
            raise ST02ContractError("MALFORMED_SOURCE_GATE")
        gid = _nonempty(gate.get("id"), "SOURCE_GATE_ID")
        symbol = _nonempty(gate.get("source_symbol"), "SOURCE_SYMBOL")
        states = gate.get("required_state")
        if (not isinstance(states, list) or not states or
                any(not isinstance(x, str) or not x for x in states)):
            raise ST02ContractError("SOURCE_REQUIRED_STATE_INVALID")
        if gate.get("live_status") != "UNKNOWN" or gid in expected:
            raise ST02ContractError("SOURCE_GATE_DUPLICATE_OR_AUTHORITY_DRIFT")
        expected[gid] = (symbol, states)

    if not isinstance(declared_gates, list):
        raise ST02ContractError("DECLARED_GATE_LIST_REQUIRED")
    actual: dict[str, Mapping[str, Any]] = {}
    for gate in declared_gates:
        if not isinstance(gate, dict):
            raise ST02ContractError("INVALID_DECLARED_GATE")
        gid = _nonempty(gate.get("gate_id"), "DECLARED_GATE_ID")
        if gid in actual:
            raise ST02ContractError("DUPLICATE_DECLARED_GATE")
        if gid not in expected:
            raise ST02ContractError("UNDECLARED_GATE_ID")
        actual[gid] = gate

    missing = sorted(set(expected) - set(actual))
    unverified = []
    accepted = []
    normalized = []
    for gid, gate in actual.items():
        symbol, states = expected[gid]
        # Source and policy may share a producer; this checks STRUCTURE only.
        source_tied = (
            gate.get("source_symbol") == symbol
            and gate.get("required_state") == states
            and gate.get("source_manifest_blob_sha1") == source_blob_sha1
            and isinstance(gate.get("evidence_ref"), str)
            and bool(gate["evidence_ref"].strip())
        )
        # A self-declared waiver cannot establish non-applicability.
        valid = source_tied and gate.get("mode") == "REQUIRED" \
            and gate.get("op") in ("eq", "ne", "gt", "ge", "lt", "le") \
            and type(gate.get("threshold")) in (int, float)
        if valid:
            accepted.append(gid)
            normalized.append({
                "gate_id": gid, "mode": "REQUIRED",
                "op": gate["op"], "threshold": gate["threshold"],
                "evidence_ref": gate["evidence_ref"],
            })
        else:
            unverified.append(gid)
            # Fail closed in original ST-01 Gate instead of accepting a waiver.
            normalized.append({"gate_id": gid, "mode": "UNVERIFIED_SOURCE_GATE"})
    coverage = "DECLARED_SOURCE_COVERAGE_CANDIDATE_ONLY"
    if missing or unverified:
        coverage = "UNKNOWN_INCOMPLETE_SOURCE_DECLARATION"
    result = SourceAudit(
        coverage, "TYPED_RELATIONS_UNVERIFIED_CANDIDATE",
        selector["source_spec"], selector["identity_spec"],
        selector["action_token"], tuple(missing), tuple(sorted(unverified)),
        tuple(sorted(accepted)), source_blob_sha1, identity_blob_sha1)
    st01_identity = {
        "spec_slug": selector["identity_spec"],
        "build_key": selector["profile_build"],
        "action_id": native_id, "source_sha256": apl_sha,
    }
    # The inventory is one PINNED SOURCE CANDIDATE, never exhaustive proof.
    inventory = {
        "schema": GATE_SCHEMA, "phase": PHASE, **st01_identity,
        "declared_required_gate_ids": sorted(expected),
        "source_completeness": "DECLARED_CANDIDATE",
    }
    policy = {"schema": GATE_SCHEMA, "phase": PHASE,
              **st01_identity, "gates": normalized}
    return result, {"identity": st01_identity,
                    "source_inventory": inventory, "action_policy": policy}
