#!/usr/bin/env python3
"""Reusable, source-pinned C++ readiness-route *obligation* auditor.

The provider (e.g. a SpecAdapter) supplies a declarative method graph.
This engine checks exact source bytes, method scopes, named guard sites and
reachability. It does NOT infer an exhaustive C++ virtual dispatch graph
from text search, and never issues a positive READY or closure certificate.

The audit can guide further original-PRE instrumentation for any class/spec.
Source-site existence != guard truth != dynamic dispatch != full READY.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
from pathlib import Path
import json
import re

SCHEMA = "ZrotGeneralRotationSourceRouteObligationAuditV1"
POLICY = "ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1"


class SourceRouteAuditError(ValueError):
    pass


def git_blob(data: bytes) -> str:
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _source_code_mask(raw: str) -> str:
    """Preserve positions while excluding C++ comments and literal strings."""
    chars = list(raw)
    i, n = 0, len(chars)
    mode = "code"
    while i < n:
        a = chars[i]
        b = chars[i + 1] if i + 1 < n else ""
        if mode == "code":
            if a == "/" and b == "/":
                mode = "line"
                chars[i] = chars[i + 1] = " "
                i += 2
                continue
            if a == "/" and b == "*":
                mode = "block"
                chars[i] = chars[i + 1] = " "
                i += 2
                continue
            if a in ("'", '"'):
                mode = a
                chars[i] = " "
                i += 1
                continue
        elif mode == "line":
            if a == "\n":
                mode = "code"
            else:
                chars[i] = " "
            i += 1
            continue
        elif mode == "block":
            if a == "*" and b == "/":
                chars[i] = chars[i + 1] = " "
                mode = "code"
                i += 2
                continue
            if a != "\n":
                chars[i] = " "
            i += 1
            continue
        else:
            if a == "\\":
                chars[i] = " "
                if i + 1 < n:
                    chars[i + 1] = " "
                i += 2
                continue
            if a == mode:
                mode = "code"
            chars[i] = " "
            i += 1
            continue
        i += 1
    if mode not in ("code", "line"):
        raise SourceRouteAuditError("UNTERMINATED_CPP_SOURCE_LEXEME")
    return "".join(chars)


def _bounded_body(src: str, code: str, signature: str,
                  scope: tuple[int, int]) -> tuple[str, int]:
    start, end = scope
    view = code[start:end]
    if view.count(signature) != 1:
        raise SourceRouteAuditError("METHOD_SIGNATURE_NOT_UNIQUE_IN_SOURCE_SCOPE:" + signature)
    pos = start + view.index(signature) + len(signature)
    opening = code.find("{", pos, end)
    semicolon = code.find(";", pos, end)
    if opening < 0 or (semicolon >= 0 and semicolon < opening):
        raise SourceRouteAuditError("METHOD_BODY_NOT_INLINE_OR_NOT_DEFINED")
    depth = 0
    for j in range(opening, end):
        if code[j] == "{":
            depth += 1
        elif code[j] == "}":
            depth -= 1
            if depth == 0:
                return src[opening:j + 1], opening
    raise SourceRouteAuditError("UNBALANCED_METHOD_BODY")


def _class_scope(src: str, code: str, anchor: str | None) -> tuple[int, int]:
    if anchor is None:
        return 0, len(code)
    if code.count(anchor) != 1:
        raise SourceRouteAuditError("CLASS_SCOPE_NOT_UNIQUE:" + anchor)
    pos = code.index(anchor) + len(anchor)
    rest, opening = _bounded_body(src, code, anchor, (0, len(code)))
    # A class is bounded by its own braces, including nested class members.
    return opening, opening + len(rest)


@dataclass(frozen=True)
class MethodSite:
    key: str
    path: str
    source_blob_sha1: str
    signature: str
    class_anchor: str | None
    guard_anchors: tuple[str, ...]
    next_nodes: tuple[str, ...]
    gate_hints: tuple[str, ...]
    dispatch_unresolved: bool = False

    def __post_init__(self):
        path = Path(self.path)
        if (not self.key or path.is_absolute() or not path.parts or
                ".." in path.parts or self.path.startswith("/") or
                any(p in ("", ".") for p in path.parts) or
                not re.fullmatch(r"[a-f0-9]{40}", self.source_blob_sha1) or
                not self.signature or not self.guard_anchors or
                len(self.guard_anchors) != len(set(self.guard_anchors)) or
                any(not v for v in self.guard_anchors) or
                not self.gate_hints or
                len(self.gate_hints) != len(set(self.gate_hints))):
            raise SourceRouteAuditError("METHOD_SITE_DECLARATION_INVALID")


@dataclass(frozen=True)
class RoutePlan:
    name: str
    root_node: str
    required_gates: tuple[str, ...]
    methods: tuple[MethodSite, ...]

    def __post_init__(self):
        if (not self.name or not self.root_node or not self.required_gates
                or len(set(self.required_gates)) != len(self.required_gates)
                or any(not x for x in self.required_gates)):
            raise SourceRouteAuditError("SOURCE_ROUTE_PLAN_INVALID")


def audit(plan: RoutePlan, source_root: Path) -> dict:
    if not isinstance(plan, RoutePlan):
        raise SourceRouteAuditError("ROUTE_PLAN_REQUIRED")
    node_map = {node.key: node for node in plan.methods}
    if (not node_map or len(node_map) != len(plan.methods)
            or plan.root_node not in node_map):
        raise SourceRouteAuditError("ROUTE_NODES_OR_ROOT_NOT_UNIQUE")
    for node in plan.methods:
        if (any(dst not in node_map for dst in node.next_nodes) or
                any(gate not in plan.required_gates for gate in node.gate_hints)):
            raise SourceRouteAuditError("ROUTE_EDGE_OR_GATE_NOT_DECLARED")

    visited, active = set(), set()
    def walk(node_key: str):
        if node_key in active:
            raise SourceRouteAuditError("SOURCE_ROUTE_CYCLE_REQUIRES_EXPLICIT_BOUND")
        if node_key in visited:
            return
        active.add(node_key)
        for child in node_map[node_key].next_nodes:
            walk(child)
        active.remove(node_key)
        visited.add(node_key)
    walk(plan.root_node)
    if len(visited) != len(node_map):
        raise SourceRouteAuditError("UNREACHABLE_METHOD_SITE_CANNOT_BE_AUDITED")

    root = source_root.resolve(strict=True)
    original = {}
    entries = []
    for node in sorted(plan.methods, key=lambda x: x.key):
        if node.path not in original:
            target = (root / node.path).resolve(strict=True)
            if not target.is_relative_to(root) or not target.is_file():
                raise SourceRouteAuditError("SOURCE_FILE_OUTSIDE_PINNED_ROOT")
            data = target.read_bytes()
            try:
                src = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise SourceRouteAuditError("NON_UTF8_PINNED_SOURCE") from exc
            original[node.path] = (data, src, _source_code_mask(src))
        data, src, code = original[node.path]
        if git_blob(data) != node.source_blob_sha1:
            raise SourceRouteAuditError("PINNED_SOURCE_BLOB_DRIFT:" + node.path)
        scope = _class_scope(src, code, node.class_anchor)
        body, _ = _bounded_body(src, code, node.signature, scope)
        guard_proofs = []
        for fragment in node.guard_anchors:
            if body.count(fragment) != 1:
                raise SourceRouteAuditError(
                    "GUARD_SITE_MISSING_OR_AMBIGUOUS:" + node.key)
            guard_proofs.append({
                "fragment_sha256":sha256(fragment.encode()).hexdigest(),
                "source_fragment_seen_once":True,
            })
        entries.append({
            "node_key":node.key, "source_path":node.path,
            "source_git_blob_sha1":node.source_blob_sha1,
            "method_body_sha256":sha256(body.encode()).hexdigest(),
            "guard_sites":guard_proofs,
            "gate_hints":list(node.gate_hints),
            "next_nodes":list(node.next_nodes),
            "dispatch_unresolved":node.dispatch_unresolved,
            "source_anchor_verified_only":True,
        })
    covered = {gate for node in plan.methods for gate in node.gate_hints}
    return {
        "schema":SCHEMA, "product_policy_id":POLICY,
        "source_route_name":plan.name,
        "source_method_nodes_verified":len(entries),
        "source_guard_anchors_verified":sum(len(x["guard_sites"]) for x in entries),
        "root_method":plan.root_node, "source_method_evidence":entries,
        "gates_with_source_site_hints":sorted(covered),
        "gates_without_source_site_hints":sorted(set(plan.required_gates) - covered),
        "unresolved_virtual_dispatch_nodes":sorted(
            node.key for node in plan.methods if node.dispatch_unresolved),
        "source_static_route_claim":"PINNED_DECLARED_METHOD_SITES_ONLY",
        "unmodeled_source_branches_reviewed":False,
        "source_dispatch_exhaustive":False,
        "independent_guard_PRE_truth_proven":False,
        "source_positive_READY_closure_eligible":False,
        "action_READY":"UNKNOWN",
        "opener_priority_proven":False,
        "target_dummy_error_permitted":False,
        "WCL_API_calls":0,
    }


def selftest() -> dict:
    import tempfile
    sample = (b"struct A : B { bool ready() { if (x) return false; "
              b"return B::ready(); } };\n"
              b"bool B::ready() { if (y) return false; return true; }\n")
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        (root / "pinned.cpp").write_bytes(sample)
        pin = git_blob(sample)
        nodes = (
            MethodSite("a", "pinned.cpp", pin, "bool ready()", "struct A : B",
                       ("if (x)",), ("b",), ("resource",), True),
            MethodSite("b", "pinned.cpp", pin, "bool B::ready()", None,
                       ("if (y)",), (), ("cooldown",), False),
        )
        plan = RoutePlan("SPEC_ALPHA", "a", ("resource", "cooldown", "movement"), nodes)
        report = audit(plan, root)
        assert report["source_method_nodes_verified"] == 2
        assert report["gates_without_source_site_hints"] == ["movement"]
        assert not report["source_positive_READY_closure_eligible"]
        assert report["action_READY"] == "UNKNOWN"
        for bad in (
            RoutePlan("SPEC_BETA", "a", plan.required_gates, (
                nodes[0], MethodSite("b", "pinned.cpp", "0" * 40,
                    nodes[1].signature, None, nodes[1].guard_anchors,
                    (), nodes[1].gate_hints),)),
            RoutePlan("SPEC_GAMMA", "a", plan.required_gates, (
                nodes[0], MethodSite("b", "pinned.cpp", pin,
                    nodes[1].signature, None, ("if (missing)",),
                    (), nodes[1].gate_hints),)),
            RoutePlan("SPEC_DELTA", "a", plan.required_gates, (
                MethodSite("a", "pinned.cpp", pin, nodes[0].signature,
                    nodes[0].class_anchor, nodes[0].guard_anchors,
                    ("b",), nodes[0].gate_hints), 
                MethodSite("b", "pinned.cpp", pin, nodes[1].signature,
                    None, nodes[1].guard_anchors, ("a",), nodes[1].gate_hints))),
        ):
            try:
                audit(bad, root)
            except SourceRouteAuditError:
                pass
            else:
                raise AssertionError("SOURCE_ROUTE_DRIFT_OR_CYCLE_ACCEPTED")
    return {
        "schema":SCHEMA, "status":"PASS_OFFLINE_SYNTHETIC",
        "synthetic_spec_count":4,
        "positive_READY_proven":0,
        "checks":9,
        "source_checkout_or_real_native_used":False,
        "WCL_API_calls":0,
    }


if __name__ == "__main__":
    print(json.dumps(selftest(), sort_keys=True))
