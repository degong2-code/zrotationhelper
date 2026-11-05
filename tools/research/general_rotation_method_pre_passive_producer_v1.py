#!/usr/bin/env python3
"""Generic, source-pinned, passive Native method-entry PRE instrumentation.

Inserts audited read-only markers *inside original C++ method entries*;
observes dispatch rather than guessing it from class/module names.
SpecAdapter provides signed source-template-derived method sites; the
generic producer imports no specialization. No extra ready(), RNG,
target, sync or cost methods. New raw records are NOT full READY evidence.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from general_rotation_source_route_audit_v1 import (
    git_blob, _source_code_mask, _class_scope, _bounded_body,
    SourceRouteAuditError
)
from general_rotation_original_pre_capture_engine_v1 import (
    canonical, digest, SCHEMA as TEMPLATE_SCHEMA
)
from general_rotation_select_pre_passive_producer_v1 import REVISION

SCHEMA = "ZrotGenericOriginalMethodEntryPREPassiveProducerV1"
MARK = "ZROT_GENERIC_METHOD_PRE_V1|"
PHASE = "SIMC_ORIGINAL_METHOD_PRE"
# Reviewed, specialization-independent action_t field reads only.
# A method site may have no fields and still produce an ENTRY record.
SOURCE_READS = {
    ("base_ready", "gcd_ready_ms"): (
        "int", "player->gcd_ready.total_millis()"),
    ("base_ready", "usable_while_casting"): (
        "bool", "( usable_while_casting ? 1 : 0 )"),
}
SITE_KEY = re.compile(r"[a-z][a-z0-9_]*\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class MethodPREError(ValueError):
    pass


# This grammar is deliberately narrower than a C++ expression parser.
# Only a pinned member path or the original const buff_t::check() accessor
# may be emitted. No C++ dynamic dispatch, target, ready, RNG, mutation,
# arbitrary function calls, new operators, delimiters or source-derived code
# from an untrusted profile may enter the generated instrumented C++.
MEMBER_PATH=re.compile(
    r"(?:this->|p\(\)->)[a-z_][a-z0-9_]*"
    r"(?:(?:->|\.)[a-z_][a-z0-9_]*)*(?:->check\(\))?\Z"
)
READ_RULES=frozenset((
    "bool_nonnull", "bool_weapon_none", "bool_const_buff_check"
))


def _read_recipe(field:dict,source_method_body:str | None=None)->tuple[str,str]:
    rule=field.get("original_pre_read_kind")
    token=field.get("source_operand_literal")
    if (rule not in READ_RULES or not isinstance(token,str) or
        not MEMBER_PATH.fullmatch(token)):
        raise MethodPREError("UNSAFE_OR_UNDECLARED_CXX_SOURCE_READ")
    if rule=="bool_nonnull":
        if token.endswith("->check()") or token.endswith(".type"):
            raise MethodPREError("NONNULL_SOURCE_FIELD_NOT_A_POINTER")
        expr="( "+token+" != nullptr ? 1 : 0 )"
    elif rule=="bool_weapon_none":
        if not token.startswith("p()->") or not token.endswith(".type"):
            raise MethodPREError("WEAPON_NONE_SOURCE_READ_NOT_TYPED")
        expr="( "+token+" == WEAPON_NONE ? 1 : 0 )"
    else:
        if (not token.startswith("p()->buffs.") or
            not token.endswith("->check()")):
            raise MethodPREError("CONST_BUFF_CHECK_SOURCE_READ_NOT_TYPED")
        # buff.hpp: buff_t::check() const returns current_stack only;
        # unlike up()/stack(), no benefit counter mutation.
        expr="( "+token+" ? 1 : 0 )"
    if field.get("value_kind")!="bool":
        raise MethodPREError("SPECIALIZATION_RAW_BOOL_KIND_REQUIRED")
    if source_method_body is not None:
        if token not in source_method_body:
            raise MethodPREError("DECLARED_OPERAND_ABSENT_FROM_PINNED_METHOD")
        if rule=="bool_weapon_none" and "WEAPON_NONE" not in source_method_body:
            raise MethodPREError("WEAPON_NONE_GUARD_ABSENT_FROM_SOURCE")
    return "bool",expr


def _validate_plan(manifest: dict) -> list[dict]:
    if (not isinstance(manifest, dict) or
        manifest.get("schema") != "ZrotGenericPassiveSelectTemplateManifestV1" or
        manifest.get("pinned_source_commit") != REVISION or
        not isinstance(manifest.get("templates"), list) or
        not manifest["templates"] or
        not isinstance(manifest.get("method_entry_sites"), list) or
        not manifest["method_entry_sites"]):
        raise MethodPREError("PINNED_EXTERNAL_METHOD_SITE_MANIFEST_REQUIRED")
    templates = manifest["templates"]
    mapped = defaultdict(list)
    for template in templates:
        if template.get("schema") != TEMPLATE_SCHEMA:
            raise MethodPREError("UNEXPECTED_SOURCE_TEMPLATE")
        verify = dict(template)
        sig = verify.pop("template_sha256", None)
        if sig != digest(verify):
            raise MethodPREError("AUDITED_TEMPLATE_BYTES_CHANGED")
        for field in template["fields"]:
            mapped[field["source_node"]].append(field)
    sites = manifest["method_entry_sites"]
    if len(sites) != len({s.get("method_key") for s in sites}):
        raise MethodPREError("DUPLICATE_METHOD_SITE")
    used_reads = set()
    for site in sites:
        if (not SITE_KEY.fullmatch(str(site.get("method_key", ""))) or
            not isinstance(site.get("signature"), str) or
            not site["signature"].startswith("bool ") or
            not isinstance(site.get("source_path"), str) or
            Path(site["source_path"]).is_absolute() or
            ".." in Path(site["source_path"]).parts or
            not HEX40.fullmatch(str(site.get("source_git_blob_sha1", ""))) or
            not HEX64.fullmatch(str(site.get("source_method_body_sha256", ""))) or
            not isinstance(site.get("fields"), list) or
            not isinstance(site.get("class_anchor"), (type(None), str))):
            raise MethodPREError("INVALID_EXTERNAL_METHOD_SITE")
        expected_fields = mapped[site["method_key"]]
        if not expected_fields:
            raise MethodPREError("METHOD_SITE_NOT_AUDITED_IN_TEMPLATES")
        for field in expected_fields:
            if (field["source_path"] != site["source_path"] or
                field["source_git_blob_sha1"] != site["source_git_blob_sha1"] or
                field["source_method_body_sha256"] !=
                    site["source_method_body_sha256"]):
                raise MethodPREError("METHOD_TEMPLATE_SOURCE_PROVENANCE_DRIFT")
        seen = set()
        for field in site["fields"]:
            key = (site["method_key"], field.get("operand_name"))
            if key in seen:
                raise MethodPREError("DUPLICATE_METHOD_READ")
            seen.add(key)
            if field.get("field_id") not in {
                src["field_id"] for src in expected_fields
                if src["operand_name"] == key[1]
            }:
                raise MethodPREError("METHOD_READ_FIELD_NOT_SOURCE_PINNED")
            if key in SOURCE_READS:
                if (field.get("value_kind")!=SOURCE_READS[key][0] or
                    "original_pre_read_kind" in field or
                    "source_operand_literal" in field):
                    raise MethodPREError("GENERIC_BASE_FIELD_RECIPE_DRIFT")
                used_reads.add(key)
            else:
                _read_recipe(field)
    if used_reads != set(SOURCE_READS):
        raise MethodPREError("REQUIRED_COMMON_BASE_METHOD_READS_MISSING")
    return sorted(sites, key=lambda x: (x["source_path"], x["method_key"]))


def _block(site: dict,source_method_body: str | None=None) -> str:
    key = site["method_key"]
    fmt = ('    if ( this->sim->log && this->player &&'
           ' !this->player->is_pet() && !this->player->is_enemy() &&'
           ' this->action_list && this->signature )\n'
           '    {\n'
           '      const auto& zrot_method_owner = *this->action_list;\n'
           '      for ( std::size_t zrot_method_idx = 0;\n'
           '            zrot_method_idx < zrot_method_owner.action_list.size();\n'
           '            ++zrot_method_idx )\n'
           '      {\n'
           '        if ( &( zrot_method_owner.action_list[ zrot_method_idx ] )'
           ' == this->signature )\n'
           '        {\n')
    def record(event: str, field_id: str, kind: str, expression: str | None):
        # Names/ids are strictly source-audited, never profile/actor input.
        line = ('          this->sim->print_log( "' + MARK +
                '{}|{}|{}|{}|' + key + '|' + event + '|' +
                field_id + '|' + kind + '|' +
                ('{}' if expression is not None else '-') +
                '",\n'
                '            this->sim->current_time().total_millis(),\n'
                '            zrot_method_owner.name_str,\n'
                '            static_cast<unsigned>( zrot_method_idx + 1 ),\n'
                '            this->name_str')
        if expression is not None:
            line += ', ' + expression
        return line + ' );\n'
    fmt += record("ENTRY", "-", "-", None)
    for field in sorted(site["fields"], key=lambda x:x["operand_name"]):
        slot=(key,field["operand_name"])
        if slot in SOURCE_READS:
            kind,expr=SOURCE_READS[slot]
        else:
            kind,expr=_read_recipe(field,source_method_body)
        fmt += record("FIELD", field["field_id"], kind, expr)
    fmt += '          break;\n        }\n      }\n    }\n'
    return "\n" + fmt


def patch_files(originals: dict[str, bytes], manifest: dict,
                *, enforce_pin: bool = True) -> dict[str, bytes]:
    sites = _validate_plan(manifest)
    groups = defaultdict(list)
    for site in sites:
        groups[site["source_path"]].append(site)
    if set(originals) != set(groups):
        raise MethodPREError("ORIGINAL_SOURCE_FILES_NOT_EXACT")
    result = {}
    for path, raw in originals.items():
        if not isinstance(raw, bytes):
            raise MethodPREError("SOURCE_BYTES_REQUIRED")
        pins = {x["source_git_blob_sha1"] for x in groups[path]}
        if len(pins) != 1:
            raise MethodPREError("METHOD_SOURCE_BLOB_CONFLICT")
        if enforce_pin and git_blob(raw) != next(iter(pins)):
            raise MethodPREError("PRISTINE_METHOD_SOURCE_BLOB_CHANGED")
        code = raw.decode("utf-8")
        if MARK in code:
            raise MethodPREError("METHOD_SOURCE_ALREADY_INSTRUMENTED")
        lexical = _source_code_mask(code)
        injections = []
        for site in groups[path]:
            try:
                scope = _class_scope(code, lexical, site["class_anchor"])
                body, opening = _bounded_body(
                    code, lexical, site["signature"], scope)
            except SourceRouteAuditError as exc:
                raise MethodPREError("DECLARED_METHOD_SITE_NOT_IN_PINNED_SOURCE") from exc
            if (sha256(body.encode("utf-8")).hexdigest() !=
                site["source_method_body_sha256"]):
                raise MethodPREError("EXACT_METHOD_BODY_CHANGED")
            injections.append((opening, _block(site,body)))
        if len({o for o, _ in injections}) != len(injections):
            raise MethodPREError("DUPLICATE_METHOD_ENTRY_LOCATION")
        for opening, fragment in sorted(injections, reverse=True):
            code = code[:opening + 1] + fragment + code[opening + 1:]
        if code.count(MARK) != sum(1 + len(x["fields"]) for x in groups[path]):
            raise MethodPREError("EMITTED_METHOD_MARKER_COUNT_CHANGED")
        result[path] = code.encode("utf-8")
    return result


def generate(source_root: Path, manifest_path: Path) -> dict:
    root = source_root.resolve(strict=True)
    rev = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                         check=True, capture_output=True, text=True).stdout.strip()
    if rev != REVISION:
        raise MethodPREError("SOURCE_COMMIT_CHANGED")
    manifest = json.loads(manifest_path.read_bytes())
    sites = _validate_plan(manifest)
    paths = sorted({x["source_path"] for x in sites})
    original = {p: (root / p).read_bytes() for p in paths}
    updated = patch_files(original, manifest)
    for p, raw in updated.items():
        (root / p).write_bytes(raw)
    return {
        "schema": SCHEMA, "source_revision": REVISION,
        "source_phase": PHASE,
        "source_method_sites": [x["method_key"] for x in sites],
        "source_method_count": len(sites),
        "requested_original_method_PRE_operands": sum(len(x["fields"]) for x in sites),
        "source_files": [{
            "path": p, "original_git_blob_sha1": git_blob(original[p]),
            "original_sha256": sha256(original[p]).hexdigest(),
            "modified_sha256": sha256(updated[p]).hexdigest()
        } for p in paths],
        "new_original_ready_or_virtual_calls": 0,
        "new_rng_target_or_sync_calls": 0,
        "native_compiled_and_executed": False,
        "original_vs_instrumented_behavior": "NOT_TESTED",
        "full_dynamic_dispatch_closed": False,
        "positive_READY_certified": 0,
        "WCL_API_calls": 0,
    }


def selftest() -> dict:
    from general_rotation_original_pre_capture_engine_v1 import canonical
    src = (b"bool action_t::action_ready()\n{\n  if ( !ready() ) return false;"
           b"\n  return true;\n}\n"
           b"bool action_t::ready()\n{\n  if ( !cooldown->is_ready() )"
           b" return false;\n  return true;\n}\n")
    code = src.decode("utf-8")
    lexical = _source_code_mask(code)
    def site(key, signature, fields):
        body, _ = _bounded_body(code, lexical, signature, (0, len(code)))
        return {
            "method_key": key, "signature": signature,
            "class_anchor": None, "source_path": "action.cpp",
            "source_git_blob_sha1": git_blob(src),
            "source_method_body_sha256": sha256(body.encode()).hexdigest(),
            "fields": fields,
        }
    template_fields = []
    for name,kind in (("gcd_ready_ms","int"),
                      ("usable_while_casting","bool")):
        template_fields.append({
            "source_node":"base_ready", "operand_name":name,
            "field_id":sha256(name.encode()).hexdigest(),
            "value_kind":kind, "source_path":"action.cpp",
            "source_git_blob_sha1":git_blob(src),
            "source_method_body_sha256":site(
                "base_ready","bool action_t::ready()",[])["source_method_body_sha256"]
        })
    template_fields.append({
        "source_node":"base_action","operand_name":"repeat_cast_allowed",
        "field_id":sha256(b"repeat").hexdigest(),
        "value_kind":"bool","source_path":"action.cpp",
        "source_git_blob_sha1":git_blob(src),
        "source_method_body_sha256":site(
            "base_action","bool action_t::action_ready()",[])["source_method_body_sha256"]
    })
    t={"schema":TEMPLATE_SCHEMA,"fields":template_fields}
    t["template_sha256"]=digest(t)
    manifest={
        "schema":"ZrotGenericPassiveSelectTemplateManifestV1",
        "pinned_source_commit":REVISION,
        "templates":[t], "method_entry_sites":[
            site("base_action","bool action_t::action_ready()",[]),
            site("base_ready","bool action_t::ready()",template_fields[:2]),
        ],
    }
    revised=patch_files({"action.cpp":src}, manifest)
    output=revised["action.cpp"].decode()
    assert output.count(MARK)==4
    assert output.count("if ( !ready() )")==1
    assert output.count("!cooldown->is_ready()")==1
    assert output.index(MARK)<output.index("if ( !ready() )")
    assert "this->sim->print_log" in output
    assert "this->sim->current_time().total_millis()" in output
    assert "this->signature" in output
    assert "this->action_list" in output
    try:
        patch_files({"action.cpp":revised["action.cpp"]},manifest,
                    enforce_pin=False)
    except MethodPREError:
        pass
    else:raise AssertionError("DOUBLE_INSTRUMENTATION_ACCEPTED")
    for altered in (
        dict(manifest,method_entry_sites=[
            dict(manifest["method_entry_sites"][0],signature="bool fake()"),
            manifest["method_entry_sites"][1]]),
        dict(manifest,method_entry_sites=[
            manifest["method_entry_sites"][0],
            dict(manifest["method_entry_sites"][1],
                 source_method_body_sha256="0"*64)]),
        dict(manifest,method_entry_sites=[
            manifest["method_entry_sites"][0],
            dict(manifest["method_entry_sites"][1],fields=[])]),
    ):
        try:patch_files({"action.cpp":src},altered,enforce_pin=False)
        except MethodPREError:pass
        else:raise AssertionError("SOURCE_METHOD_GUARD_DRIFT_ACCEPTED")
    # Source-owned typed collection can be added without changing the
    # generic producer logic or trusting arbitrary injected C++ expressions.
    valid={
        "operand_name":"replacement_action_exists","value_kind":"bool",
        "original_pre_read_kind":"bool_nonnull",
        "source_operand_literal":"this->replacement_action"
    }
    assert _read_recipe(valid,"if ( !this->replacement_action )")[0]=="bool"
    assert _read_recipe(dict(valid,original_pre_read_kind="bool_weapon_none",
         source_operand_literal="p()->main_hand_weapon.type"),
         "if ( p()->main_hand_weapon.type == WEAPON_NONE )")[0]=="bool"
    assert _read_recipe(dict(valid,original_pre_read_kind="bool_const_buff_check",
         source_operand_literal="p()->buffs.prismatic_bolt->check()"),
         "if ( p()->buffs.prismatic_bolt->check() )")[0]=="bool"
    for forged in (
        dict(valid,source_operand_literal="p()->ready()"),
        dict(valid,source_operand_literal="this->replacement_action; ready()"),
        dict(valid,original_pre_read_kind="random_expression"),
        dict(valid,value_kind="enum"),
    ):
        try:_read_recipe(forged,"if ( !this->replacement_action )")
        except MethodPREError:pass
        else:raise AssertionError("UNSAFE_SOURCE_READ_RECIPE_ACCEPTED")
    try:_read_recipe(valid,"return true;")
    except MethodPREError:pass
    else:raise AssertionError("SOURCE_UNPINNED_READ_ACCEPTED")
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":20, "source_method_site_count":2,
        "positive_READY_certified":0,
        "actual_native_compiled":False,"WCL_API_calls":0
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--simc-root",type=Path)
    p.add_argument("--source-templates",type=Path)
    p.add_argument("--receipt",type=Path)
    args=p.parse_args()
    if args.simc_root is None and args.source_templates is None:
        result=selftest()
    elif args.simc_root is not None and args.source_templates is not None:
        result=generate(args.simc_root,args.source_templates)
    else:
        p.error("simc-root and source-templates required together")
    output=canonical(result)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True,exist_ok=True)
        with args.receipt.open("xb") as fd:fd.write(output)
    else:print(output.decode(),end="")


if __name__=="__main__":
    main()
