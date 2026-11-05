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
    git_blob, _source_code_mask, _class_scope, _bounded_body
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
            if key not in SOURCE_READS or key in seen:
                raise MethodPREError("UNAPPROVED_OR_DUPLICATE_METHOD_READ")
            seen.add(key)
            if (field.get("field_id") not in {
                src["field_id"] for src in expected_fields
                if src["operand_name"] == key[1]
            } or field.get("value_kind") != SOURCE_READS[key][0]):
                raise MethodPREError("METHOD_READ_FIELD_OR_TYPE_UNPINNED")
            used_reads.add(key)
    if used_reads != set(SOURCE_READS):
        raise MethodPREError("REQUIRED_COMMON_BASE_METHOD_READS_MISSING")
    return sorted(sites, key=lambda x: (x["source_path"], x["method_key"]))


def _block(site: dict) -> str:
    key = site["method_key"]
    fmt = ('    if ( sim->log && player && !player->is_pet() &&'
           ' !player->is_enemy() && action_list && signature )\n'
           '    {\n'
           '      const auto& zrot_method_owner = *action_list;\n'
           '      for ( std::size_t zrot_method_idx = 0;\n'
           '            zrot_method_idx < zrot_method_owner.action_list.size();\n'
           '            ++zrot_method_idx )\n'
           '      {\n'
           '        if ( &( zrot_method_owner.action_list[ zrot_method_idx ] )'
           ' == signature )\n'
           '        {\n')
    def record(event: str, field_id: str, kind: str, expression: str | None):
        # Names/ids are strictly source-audited, never profile/actor input.
        line = ('          sim->print_log( "' + MARK +
                '{}|{}|{}|{}|' + key + '|' + event + '|' +
                field_id + '|' + kind + '|' +
                ('{}' if expression is not None else '-') +
                '",\n'
                '            sim->current_time().total_millis(),\n'
                '            zrot_method_owner.name_str,\n'
                '            static_cast<unsigned>( zrot_method_idx + 1 ),\n'
                '            name_str')
        if expression is not None:
            line += ', ' + expression
        return line + ' );\n'
    fmt += record("ENTRY", "-", "-", None)
    for field in sorted(site["fields"], key=lambda x:x["operand_name"]):
        kind,expr = SOURCE_READS[(key, field["operand_name"])]
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
            scope = _class_scope(code, lexical, site["class_anchor"])
            body, opening = _bounded_body(
                code, lexical, site["signature"], scope)
            if (sha256(body.encode("utf-8")).hexdigest() !=
                site["source_method_body_sha256"]):
                raise MethodPREError("EXACT_METHOD_BODY_CHANGED")
            injections.append((opening, _block(site)))
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
    return {
        "schema":SCHEMA,"status":"PASS_OFFLINE_SYNTHETIC",
        "checks":12, "source_method_site_count":2,
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
