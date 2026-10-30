#!/usr/bin/env python3
"""Research-only pinned Native hook: log actual bare resource reference evaluation.

Decorates the original make_ref_expr without inventing a resource value.
Requires the existing common Native epoch source counter. Evaluations are NOT
Strict PRE transitions, READY evidence, or certified APL-source-row ownership.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from simc_apl_pointer_instrument import UPSTREAM_SHA

FILE = "engine/player/player.cpp"
HEADER = "engine/sim/sim.hpp"
ANCHOR = """  if ( splits.size() == 1 )
    return make_ref_expr( expression_str, resources.current[ r ] );"""
COUNTER = "unsigned long long zrot_native_event_sequence = 0;"
REPLACEMENT = """  if ( splits.size() == 1 )
  {
    // Decorate, rather than replace, the exact ref_expr_t evaluation.
    // These are runtime evals and must NEVER be backdated to Strict PRE.
    struct zrot_resource_ref_eval_t final : public expr_t
    {
      player_t* owner;
      resource_e resource;
      std::unique_ptr<expr_t> original;
      zrot_resource_ref_eval_t( util::string_view label, player_t* p, resource_e r,
                                std::unique_ptr<expr_t> base )
        : expr_t( label ), owner( p ), resource( r ), original( std::move( base ) ) {}
      double evaluate() override
      {
        const double actual_value = original->eval();
        if ( owner->sim->log && !owner->is_pet() && !owner->is_enemy() )
        {
          owner->sim->print_log(
            "ZROT_NATIVE_APL_RESOURCE_EVAL_V1|{}|{}|{}|{}|{}|{}|{}|{:.17g}",
            owner->sim->thread_index, owner->sim->current_iteration,
            owner->sim->zrot_native_event_sequence++,
            owner->sim->current_time().total_millis(),
            owner->actor_index, owner->actor_spawn_index,
            util::resource_type_string( resource ), actual_value );
        }
        return actual_value;
      }
    };
    return std::make_unique<zrot_resource_ref_eval_t>(
      expression_str, this, r,
      make_ref_expr( expression_str, resources.current[ r ] ) );
  }"""


def patch(source: str, header: str) -> str:
    if header.count(COUNTER) != 1:
        raise ValueError("EVAL_HOOK_SHARED_NATIVE_EPOCH_COUNTER_REQUIRED")
    if source.count(ANCHOR) != 1 or "ZROT_NATIVE_APL_RESOURCE_EVAL_V1" in source:
        raise ValueError("EVAL_HOOK_UNIQUE_BARE_REF_ANCHOR_REQUIRED")
    patched = source.replace(ANCHOR, REPLACEMENT)
    if (patched.count("make_ref_expr( expression_str, resources.current[ r ] )") != 1 or
            patched.count("original->eval()") != 1 or
            patched.count("zrot_native_event_sequence++") < 7):
        # Six prior V2 hooks plus this actual reference eval hook.
        raise ValueError("EVAL_HOOK_DELEGATE_OR_COUNTER_MISSING")
    return patched


def apply(root: Path) -> dict:
    revision = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              capture_output=True, check=True, text=True).stdout.strip()
    if revision != UPSTREAM_SHA:
        raise ValueError("EVAL_HOOK_UPSTREAM_REVISION_MISMATCH")
    file = root / FILE
    old = file.read_bytes()
    header = (root / HEADER).read_text("utf-8")
    new = patch(old.decode("utf-8"), header).encode("utf-8")
    file.write_bytes(new)
    return {
        "schema": "ZrotPinnedNativeBareResourceEvaluationHookV1",
        "upstream_sha": UPSTREAM_SHA,
        "source_file": FILE,
        "source_sha256_before": hashlib.sha256(old).hexdigest(),
        "source_sha256_after": hashlib.sha256(new).hexdigest(),
        "marker": "ZROT_NATIVE_APL_RESOURCE_EVAL_V1",
        "delegates_original_ref_eval": True,
        "same_source_monotonic_counter": True,
        "source_row_owner": "UNKNOWN",
        "strict_pre_state_certified": False,
        "readiness_certified": False,
        "gameplay_rule_promotion": False,
    }


def selftest() -> None:
    source = ("prefix\n" + "sim->zrot_native_event_sequence++\n" * 6 +
              ANCHOR + "\nsuffix\n")
    result = patch(source, COUNTER)
    assert result.count("ZROT_NATIVE_APL_RESOURCE_EVAL_V1") == 1
    assert result.count("original->eval()") == 1
    assert "return actual_value;" in result
    for broken, header in ((result, COUNTER), (source.replace(ANCHOR, ""), COUNTER),
                           (source + ANCHOR, COUNTER), (source, "")):
        try:
            patch(broken, header)
        except ValueError:
            pass
        else:
            raise AssertionError("EVAL_HOOK_UNPINNED_SOURCE_ACCEPTED")
    print("SIMC_NATIVE_BARE_RESOURCE_EVAL_SOURCE_SELF_TEST=PASS SYNTHETIC_ONLY")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test or args.upstream_root is None:
        selftest()
    else:
        print(json.dumps(apply(args.upstream_root), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
