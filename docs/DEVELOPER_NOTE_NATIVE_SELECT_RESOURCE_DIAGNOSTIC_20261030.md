# Developer Note — Native select_action-entry resource diagnostic vs earlier source transitions

**Date:** 2026-10-30. **Owner:** research BRANCH `work/github-ci-bootstrap`; no MAIN/FROZEN promotion. Goal: advance generic, source-accountable state observability for *arbitrary* SimC specs/builds toward IF/ELSE replay. Do not hardcode spell/class/boss priority or infer current Blizzard mechanics from pinned SimC.

## Why this particular increment

Earlier verified Native SimC runs captured 496 persistent `player_t::resource_gain/loss` markers (489 strictly before the final select_action across Enhancement/Fury/Unholy) and 32 resource INIT observations (24 matched to the active combat actor+spawn) from `player_t::init_resources`. The recalc reporter compiled but 0 genuine RECALC occurrences were exercised. Exact upstream source and Native binary provenance were pinned; replay remained BLOCKED because full resource state and action readiness were not certified.

*Question:* at an actual native `select_action` entry, do the **last strictly earlier** observed current and max resource values explain the true in-simulator value? A new sampled diagnostic from the current decision timestamp may be compared *retrospectively*, but **must not be passed back into the Strict PRE state engine** or shifted to t-1.

## Verified upstream semantic placement

Pinned official `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`, `engine/player/player.cpp`:

- `player_t::execute_action()` may invoke `do_dynamic_regen()` before its select branch. The actual `select_action(*active_action_list, execute_type::FOREGROUND)` invocation is the precise diagnostic entry point.
- Existing source instrumentation tracks the mutually exclusive strict-sequence / queued-action / `select_action` branches, action_t::signature pointer identity to the effective APL row, and Native action event identity. This new reporter is **read-only** and does not change those decisions.
- `pool_resource_t::ready()` mutates current resources *temporarily* during readiness checks and restores them; such trial writes must not be reinterpreted as persistent events. Official class modules also contain persistent direct writes outside generic `resource_gain/loss` and INIT/RECALC; upstream examples include Warrior current-health and Mage maximum/current-mana paths. Expect explicit conflict/unknown rather than assuming 100% completeness.

## New implementation

1. `tools/research/simc_native_select_entry_resource_instrument.py`: fail-closed exact source SHA and anchor. Before the actual native `select_action` invocation, logs a `ZROT_NATIVE_SELECT_RESOURCE_BEGIN_V1` event (native time, actor index, spawn), then values for every resource with positive max (current/max at entry), followed by an END marker *after* `select_action` returns (same clock and action_t::id or 0 if no action). No state mutation or readiness shortcut, no emission for nonnormal foreground branches. All record grouping stays in the native log and is tied to that run's executable/log SHA.
2. `tools/research/simc_native_select_resource_diagnostic_audit.py`: parses and independently re-parses native log BEGIN/VALUE/END groups with strict grouping, timestamp and actor/spawn agreement, unique resource IDs and valid finite numeric values. Computes last strict-timestamp-earlier values from **two independently audited producers**: `native.resource.current` from actual gain/loss and INIT/RECALC function marks; `native.resource.max` from INIT/RECALC marks. Pairs are matched by resource and exact actor+spawn; never mix spawn -1 into combat spawn 1.
3. Comparison labels:
   - `CONSISTENT_WITH_LAST_OBSERVED_SOURCE_VALUE`: latest source value strictly earlier than entry agrees with Native diagnostic within a bounded numeric tolerance. Consistency is **not** proof of full resource coverage.
   - `SAME_TIMESTAMP_SOURCE_AMBIGUITY`: any candidate source event has the **same millisecond** as selection. It cannot satisfy `timestamp < t`; do not count as proof or mismatch.
   - `UNKNOWN_NO_STRICTLY_EARLIER_SOURCE_OBSERVATION`: no eligible prior source event, including the first t=0 selection.
   - `CONFLICT_POSSIBLE_MISSING_TRANSITION`: earlier observed value disagrees with Native entry. This is a *gap signal*, not proof which class-specific direct-write or semantic rule caused it.
4. The Native public probe combines existing source-pointer-backed APL selection, source gain/loss and lifecycle raw log SHA, and this diagnostic comparator in **one** C++ research-only build. It reports aggregate counts and up to 25 source-referenced possible conflicts in summary JSON only; raw logs, profiles and executables remain runner-local. It never uses diagnostic snapshots to create source transition records, never supplies READY/NOT_READY and never reports playable rotation parity.

## Validation contract

- Synthetic same-time duplicate/grouping and mismatched actor/clock/sha checks must fail closed. Three unrelated synthetic spec labels test known matching, conflict, same timestamp ambiguity. The diagnostic parser is independently recalculated by an alternative token-splitting audit, not the same regex.
- Native action audit must still prove source-pointer-backed `SELECT_ACTION_FOREGROUND`; resource producer projections must independently pass; the diagnostic is compared only after native logfile receipt and executable SHA are independently pinned.
- **Actual new Native CI run:** https://github.com/degong2-code/zrotationhelper/actions/runs/41033216189 — check *conclusion and summary* before claiming actual evidence. **Offline CI:** https://github.com/degong2-code/zrotationhelper/actions/runs/41033216188 — check both Python 3.12 and 3.14 job conclusions. Earlier Native run evidence cannot be substituted for a new binary.
- This increments the *observability audit*, not the core General Rotation IR, current Blizzard mechanic authority, WCL blind lane, benchmark optimality, or approved FROZEN.

## Critical limitations and Exact Next

Even an accurate same-time Native diagnostic snapshot is **not** a Strict PRE observation under the strict transition rule `source_ts < action_ts`. This experiment intentionally does not verify a new buff/cooldown/charge producer, resource state completeness, target availability, active talents, or the correctness of SimC APL condition semantics. It will also observe select_action invocations that return no action (ID 0), unlike the action_sequence which may contain only recorded/quiet-filtered selected actions. Therefore `diagnostic entry count` and `recorded selected action count` have different denominators.

Once Native results are available:
1. Examine per-resource disagreement/same-time/unknown distribution, source timestamps, actor+spawn, and identify highest-impact **persisting direct writes**; explicitly distinguish transient `pool_resource` trials.
2. If a prior source-observation disagreement is reproducible and affects user-facing IF/ELSE decisions, add the narrowest necessary source hook; do not instrument all C++ assignments blindly.
3. Validate a true dynamic RECALC fixture or retain `NOT_COVERED`. Add buff, cooldown and charge source transitions with separate semantics/observability contracts.
4. Only then bind verified native operands/readiness and compare existing generic APL evaluator with actual source-pinned foreground decision references. Keep independent WCL blind candidate discovery isolated until lock and use Blizzard/current patch for mechanic truth.

**Authority:** Branch-only. MAIN `CURRENT_STATE`, architecture/global handoff, registry, active manifest, General Rotation baseline, FROZEN/Seq578 unchanged. Seq637 UNKNOWN. User local/PyCharm work not required.
