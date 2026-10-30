#!/usr/bin/env python3
"""Generic SimC APL source acquisition and structured hypothesis ingestion.

Production-oriented *source* functionality with a non-authoritative boundary:
- local SimulationCraft executable can export its built-in APL via save_actions;
- alternatively ingest a user/exported actions .simc file;
- fingerprint provenance and emit an ordered, cross-spec APL research model.

The output is NOT a General Rotation recommendation until full APL execution,
build verification, spell readiness, identity and WCL comparisons are validated.
No class, specialization, boss, or historical test-sequence semantics are coded.
Official SimC docs: simulationcraft/simc Wiki / Output and ActionLists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request

from simc_apl_syntax_inventory import parse as parse_apl

_SHA = re.compile(r"^[0-9a-f]{64}$")
_SPEC = re.compile(r"^[a-z][a-z0-9_]*$")
_ACTOR = re.compile(
    r"^(?:deathknight|death_knight|demonhunter|demon_hunter|"
    r"druid|evoker|hunter|mage|monk|"
    r"paladin|priest|rogue|shaman|warlock|warrior)\s*=", re.I
)
_NON_ACTION = {
    "variable", "cycling_variable", "call_action_list", "run_action_list",
    "snapshot_stats", "auto_attack", "auto_shot", "retarget",
    "pool_resource", "wait", "wait_fixed", "cancel_buff", "stop_moving",
    "start_moving", "swap_action_list", "invoke_external_buff",
}


class SourceContractError(RuntimeError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fingerprint(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def _text(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise SourceContractError("NOT_UTF8_SIMC_SOURCE") from e


def _profile_fields(text: str) -> dict[str, str | int | bool | None]:
    spec = None
    actors = []
    custom_apl = False
    external_dependencies = False
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if _ACTOR.match(s):
            actors.append(s.split("=", 1)[0].strip().lower())
        if s.startswith("spec="):
            spec = s.split("=", 1)[1].strip().lower()
        if s.startswith("actions=") or s.startswith("actions+=") or s.startswith("actions."):
            custom_apl = True
        if s.startswith(("input=", "include=", "armory=", "local_json=")):
            external_dependencies = True
    return {
        "spec":spec, "actor_count":len(actors),
        "custom_apl_in_profile":custom_apl,
        "external_profile_dependencies_detected":external_dependencies,
    }


def ingest_actions(
    actions_bytes: bytes, *,
    expected_spec: str,
    profile_sha256: str | None = None,
    simc_executable_sha256: str | None = None,
    profile_spec: str | None = None,
    input_contains_custom_apl: bool | None = None,
    profile_dependencies_verified: bool = False,
) -> dict:
    """Build reusable per-spec action-list *hypotheses*, not cast recommendations.

    APL semantic scope deliberately records variables, nested list calls,
    target_if, selector metadata, and readiness as unresolved obligations.
    """
    if not _SPEC.fullmatch(expected_spec):
        raise SourceContractError("INVALID_SPEC_SLUG")
    for label, value in (("PROFILE", profile_sha256),
                         ("EXECUTABLE", simc_executable_sha256)):
        if value is not None and not _SHA.fullmatch(value):
            raise SourceContractError("INVALID_" + label + "_SHA256")
    txt = _text(actions_bytes)
    meta, lists = parse_apl(txt)
    exported_spec = meta.get("spec")
    for name, value in (("PROFILE", profile_spec), ("APL", exported_spec)):
        if value is not None and value != expected_spec:
            raise SourceContractError(name + "_SPEC_MISMATCH")
    rows = []
    requirements = set()
    for list_name, items in lists.items():
        for item in items:
            params = dict(item["params"])
            command = item["command"]
            conditional = item["condition"]
            # A conditional guard never implies readiness or priority selection.
            if conditional is not None:
                requirements.add("CONDITION_OPERAND_BINDING")
            if command in ("call_action_list", "run_action_list"):
                requirements.add("NESTED_APL_CONTROL_FLOW")
            if command in ("variable", "cycling_variable"):
                requirements.add("APL_VARIABLE_STATE")
            if "target_if" in params or "cycle_targets" in params:
                requirements.add("TARGET_SELECTION")
            if "line_cd" in params or "use_off_gcd" in params:
                requirements.add("ACTION_TIMING_MODIFIERS")
            rows.append({
                "list":list_name, "list_rank":item["rank"],
                "source_line":item["line"], "command_token":command,
                "params":item["params"], "guard":conditional,
                "call_target":item["call_target"],
                "role":"DIRECTIVE" if command in _NON_ACTION else "ACTION_TOKEN",
                "readiness":"UNKNOWN",
                "numeric_spell_identity":"UNKNOWN",
                "hypothesis_only":True,
            })
    requirements.update(("SPELL_IDENTITY", "SPELL_READINESS",
                         "BUILD_TO_WCL_BINDING", "BLIND_WCL_RECONCILIATION",
                         "INDEPENDENT_VALIDATION"))
    if profile_sha256 is None or profile_spec is None or not profile_dependencies_verified:
        requirements.add("PROFILE_PROVENANCE_OR_DEPENDENCIES_UNVERIFIED")
    return {
        "schema":"ZrotGenericSimcAplSourceHypothesisV1",
        "expected_spec":expected_spec,
        "source_kind":"SIMC_EXPORTED_ACTION_LIST",
        "apl_sha256":sha(actions_bytes),
        "profile_sha256":profile_sha256,
        "simc_executable_sha256":simc_executable_sha256,
        "profile_spec_verified":profile_spec == expected_spec,
        "exported_apl_spec_verified":exported_spec == expected_spec,
        "custom_apl_in_profile":input_contains_custom_apl,
        "profile_dependencies_verified":profile_dependencies_verified,
        "action_list_count":len(lists), "apl_row_count":len(rows),
        "lists":list(lists), "rows":rows,
        "unresolved_requirements":sorted(requirements),
        "actionable_general_rotation":False,
        "current_patch_verified":False,
        "wcl_actual_replay":"NOT_RUN",
        "lifecycle":"OBSERVED_SOURCE_HYPOTHESIS_ONLY",
    }


def capture_from_simc(
    *, profile_file: Path, expected_spec: str,
    simc_executable: Path | None = None, timeout_seconds: int = 180,
) -> dict:
    """Export **current executable's** effective APL, including builtin APL.

    Caller must supply/choose a genuine up-to-date profile for their build.
    One actor is required to prevent actor-scope save_actions ambiguity.
    The binary runs locally; no network or credentials are handled here.
    """
    p=profile_file.expanduser().resolve(strict=True)
    if not p.is_file():
        raise SourceContractError("PROFILE_NOT_FILE")
    source=p.read_bytes()
    fields=_profile_fields(_text(source))
    if fields["actor_count"]!=1:
        raise SourceContractError("SINGLE_EXPLICIT_ACTOR_REQUIRED")
    if fields["spec"] != expected_spec:
        raise SourceContractError("PROFILE_SPEC_NOT_EXACT")
    if fields["external_profile_dependencies_detected"]:
        raise SourceContractError("EXTERNAL_PROFILE_DEPENDENCIES_NEED_PINNING")
    chosen = (
        str(simc_executable) if simc_executable is not None else
        os.environ.get("SIMC_BIN") or
        shutil.which("simc") or shutil.which("simc.exe")
    )
    if not chosen:
        raise SourceContractError("SIMC_EXECUTABLE_NOT_FOUND")
    binary=Path(chosen).expanduser().resolve(strict=True)
    if not binary.is_file():
        raise SourceContractError("SIMC_EXECUTABLE_NOT_FILE")
    if timeout_seconds <= 0 or timeout_seconds > 3600:
        raise SourceContractError("SIMC_TIMEOUT_OUT_OF_RANGE")
    with tempfile.TemporaryDirectory(prefix="zrot_simc_apl_") as temp:
        dest=Path(temp)/"effective_actions.simc"
        # No shell, and no mutation of the supplied source profile.
        cmd=[str(binary), str(p), f"save_actions={dest}",
             "iterations=1", "threads=1", "calculate_scale_factors=0"]
        try:
            proc=subprocess.run(cmd, cwd=str(p.parent), shell=False,
                                capture_output=True, timeout=timeout_seconds,
                                check=False)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise SourceContractError("SIMC_EXPORT_EXECUTION_FAILED") from e
        if proc.returncode != 0:
            # Do not echo stdout/stderr: profile/character details may appear.
            raise SourceContractError("SIMC_EXPORT_NONZERO_EXIT")
        if not dest.is_file() or dest.stat().st_size == 0:
            raise SourceContractError("SIMC_ACTION_EXPORT_MISSING")
        data=dest.read_bytes()
    result=ingest_actions(
        data, expected_spec=expected_spec, profile_sha256=sha(source),
        simc_executable_sha256=_fingerprint(binary),
        profile_spec=fields["spec"],
        input_contains_custom_apl=fields["custom_apl_in_profile"],
        profile_dependencies_verified=True,
    )
    result["source_kind"]="SIMC_EXECUTABLE_SAVE_ACTIONS"
    return result


_SIMC_UPSTREAM_REVISION = re.compile(r"^[0-9a-f]{40}$")
_SIMC_UPSTREAM_PROFILE = re.compile(
    r"^profiles/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+\.simc$")


def capture_official_simc_profile(
    *, upstream_profile_path: str, commit_sha: str, expected_spec: str,
    fetch_bytes=None,
) -> dict:
    """Load a pinned PUBLIC SimC profile directly from the official repo.

    This is an APL source input, NOT the executed effective APL from a SimC
    binary. It cannot certify the client's patch, build or spell semantics.
    Git URL is immutable and fixed to the official public source.
    """
    if not _SIMC_UPSTREAM_REVISION.fullmatch(commit_sha):
        raise SourceContractError("UPSTREAM_REVISION_MUST_BE_FULL_COMMIT_SHA")
    if not _SIMC_UPSTREAM_PROFILE.fullmatch(upstream_profile_path):
        raise SourceContractError("INVALID_UPSTREAM_PROFILE_PATH")
    uri=("https://raw.githubusercontent.com/simulationcraft/simc/"
         + commit_sha + "/" + upstream_profile_path)
    if fetch_bytes is None:
        def fetch_bytes():
            request=urllib.request.Request(
                uri,headers={"User-Agent":"zRotationHelper-Public-APL-Research/1"})
            try:
                with urllib.request.urlopen(request,timeout=20) as response:
                    raw=response.read(2_000_001)
            except (OSError, ValueError) as e:
                raise SourceContractError("OFFICIAL_SIMC_FETCH_FAILED") from e
            return raw
    raw=fetch_bytes()
    if not isinstance(raw, bytes) or not raw or len(raw)>2_000_000:
        raise SourceContractError("INVALID_OFFICIAL_SIMC_SOURCE_SIZE")
    fields=_profile_fields(_text(raw))
    if fields["actor_count"]!=1:
        raise SourceContractError("OFFICIAL_PROFILE_SINGLE_ACTOR_REQUIRED")
    if fields["spec"]!=expected_spec:
        raise SourceContractError("OFFICIAL_PROFILE_SPEC_MISMATCH")
    if fields["external_profile_dependencies_detected"]:
        raise SourceContractError("OFFICIAL_PROFILE_EXTERNAL_DEPENDENCIES_UNPINNED")
    if not fields["custom_apl_in_profile"]:
        raise SourceContractError("OFFICIAL_PROFILE_INLINE_APL_MISSING")
    out=ingest_actions(
        raw,expected_spec=expected_spec,
        profile_sha256=sha(raw),profile_spec=fields["spec"],
        input_contains_custom_apl=True,profile_dependencies_verified=True)
    out["source_kind"]="SIMC_PUBLIC_REPO_INLINE_PROFILE_APL"
    out["official_upstream_repo"]="simulationcraft/simc"
    out["official_upstream_commit"]=commit_sha
    out["official_upstream_path"]=upstream_profile_path
    out["profile_and_apl_are_same_bytes"]=True
    out["actual_simc_executable_run"]="NOT_RUN"
    out["current_game_build_verified"]=False
    return out


def selftest():
    # Contract tests are supporting evidence, not the intended output.
    a=b"actions=call_action_list,name=st,if=active_enemies=1\n" \
      b"actions.st=stormstrike,if=buff.proc.up\n"
    model=ingest_actions(a,expected_spec="enhancement")
    assert model["action_list_count"]==2
    assert model["apl_row_count"]==2
    assert "NESTED_APL_CONTROL_FLOW" in model["unresolved_requirements"]
    assert model["rows"][1]["readiness"]=="UNKNOWN"
    assert not model["actionable_general_rotation"]
    assert model["rows"][1]["role"]=="ACTION_TOKEN"
    assert model["rows"][0]["role"]=="DIRECTIVE"
    b=a.replace(b"stormstrike",b"bloodthirst")
    other=ingest_actions(b,expected_spec="fury")
    assert other["expected_spec"]=="fury" and other["apl_sha256"]!=model["apl_sha256"]
    try:ingest_actions(a,expected_spec="fury",profile_spec="enhancement")
    except SourceContractError:pass
    else:raise AssertionError("CROSS_SPEC_PROFILE_ACCEPTED")
    # Official upstream actor directives are unseparated for these classes.
    # A generic profile ingester must not fail before it reads their APL.
    for cls, spec in (("deathknight", "unholy"), ("demonhunter", "havoc")):
        specimen=(f'{cls}="Synthetic"\nspec={spec}\n'
                  'actions=auto_attack\nactions+=/synthetic_action\n').encode()
        fields=_profile_fields(_text(specimen))
        assert fields["actor_count"]==1 and fields["spec"]==spec
        extracted=ingest_actions(specimen,expected_spec=spec,
                                 profile_spec=spec,profile_dependencies_verified=True)
        assert extracted["apl_row_count"]==2
    upstream=(
        b'shaman="Synthetic"\n'
        b'spec=enhancement\n'
        b'actions=auto_attack\n'
        b'actions+=/stormstrike,if=active_enemies=1\n')
    captured=capture_official_simc_profile(
        upstream_profile_path="profiles/MID2/Synthetic_Enhancement.simc",
        commit_sha="a"*40,expected_spec="enhancement",
        fetch_bytes=lambda:upstream)
    assert captured["apl_row_count"]==2
    assert captured["source_kind"]=="SIMC_PUBLIC_REPO_INLINE_PROFILE_APL"
    assert captured["profile_and_apl_are_same_bytes"]
    assert captured["actual_simc_executable_run"]=="NOT_RUN"
    for bad in ("../private.simc","profiles/MID2/../../secret.simc",
                "https://example.com/profile.simc"):
        try:
            capture_official_simc_profile(
                upstream_profile_path=bad,commit_sha="a"*40,
                expected_spec="enhancement",fetch_bytes=lambda:upstream)
        except SourceContractError:
            pass
        else:
            raise AssertionError("UNSAFE_PUBLIC_SOURCE_PATH_ACCEPTED")
    print("SIMC_PUBLIC_PROFILE_SOURCE_SELF_TEST=PASS")
    print("SIMC_GENERIC_SOURCE_HYPOTHESIS_SELF_TEST=PASS")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile",type=Path)
    parser.add_argument("--actions-file",type=Path)
    parser.add_argument("--upstream-profile",type=str)
    parser.add_argument("--upstream-revision",type=str)
    parser.add_argument("--spec")
    parser.add_argument("--simc-bin",type=Path)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--self-test",action="store_true")
    opts=parser.parse_args()
    if opts.self_test:
        selftest()
        return
    selected=sum(x is not None for x in
                 (opts.profile,opts.actions_file,opts.upstream_profile))
    if opts.spec is None or selected!=1:
        parser.error("--spec and exactly one source: --profile, --actions-file, --upstream-profile")
    if opts.actions_file is not None:
        raw=opts.actions_file.read_bytes()
        result=ingest_actions(raw, expected_spec=opts.spec)
    elif opts.upstream_profile is not None:
        if opts.upstream_revision is None:
            parser.error("--upstream-revision requires full immutable commit SHA")
        result=capture_official_simc_profile(
            upstream_profile_path=opts.upstream_profile,
            commit_sha=opts.upstream_revision,expected_spec=opts.spec)
    else:
        result=capture_from_simc(profile_file=opts.profile,
                                 expected_spec=opts.spec,
                                 simc_executable=opts.simc_bin)
    output=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
    if opts.out is not None:
        opts.out.parent.mkdir(parents=True,exist_ok=True)
        opts.out.write_text(output,encoding="utf-8")
        print("WROTE_SIMC_APL_HYPOTHESIS")
    else:
        print(output)


if __name__=="__main__":
    main()
