# Developer Note — Pinned native SimC resource-mutation producer

Date: 2026-10-30. Owner: research branch `work/github-ci-bootstrap`. This is **not** a MAIN/FROZEN production promotion.

## Why
Earlier steps proved real `select_action` action-object provenance (206 Native foreground examples) and the byte-consistency of caller-provided state-transition files. The missing dependency was an **actual native state producer**, not another SHA of fabricated synthetic events. This increment chooses one bounded, cross-class state family: resource gains/losses at the real SimulationCraft mutation codepaths.

## Source instrumentation and provenance
Pinned upstream: `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`.

- `tools/research/simc_native_resource_change_instrument.py` requires pinned source commit and exactly matched source anchors inside `engine/player/player.cpp::player_t::resource_gain()` and `resource_loss()`. It adds reporter-only `ZROT_NATIVE_RESOURCE_V1` log markers after actual mutation, with the native `sim->current_time().total_millis()`, actor index and spawn index, native resource enum name, current value at the mutation site, actual delta and gain/loss direction. It does not alter the source's action selection, cooldowns, resource equations or priority lists. The resulting binary is a **new** research executable, never identified with the earlier official/modified executables.
- `tools/research/simc_native_resource_change_probe.py` reads the raw, hash-pinned Native log and extracts only these markers, retaining source byte offset, exact log-line hash, actor index/spawn, native event time and actual value. It emits **typed, explicit FEATURE_TRANSITION rows**, never differences between JSON2 action snapshots. A separate independently written log-marker parser replays the raw log and compares the full byte-projection, receipts and SHA.
- The existing `simc_raw_transition_adapter.py` and its independent NDJSON audit then recompute the derived source bytes once more. The existing `StrictPreStateProvider` excludes event timestamps equal to or later than the reference `select_action` timestamp. No token→mechanic mapping or READY/NOT_READY is automatically asserted.
- `tools/research/simc_apl_pointer_native_probe.py` checks the same three source-locked public profiles (Enhancement/Fury/Unholy) with one pinned C++ binary build, validates the complete original log SHA from the Native capture receipt, combines resource-log evidence with source-pointer-backed `SELECT_ACTION_FOREGROUND` references, and reports resource count and strict earlier-than-decision event count. It never uploads raw profile, log, JSON2 or executable. The separate native CI workflow is scoped to changed source instrumentation and this probe only; normal offline CI stays inexpensive.

## Observability and limitations

`player_t::resource_gain/loss` does **not** enumerate every resource mutation: resource initialization, maximum recalculation/clamps and direct writes outside those two functions are not captured. A logged value from this producer cannot imply *complete* resource state coverage or availability; a resource with no qualifying observed event stays UNKNOWN. Native event timestamps have millisecond resolution; same-timestamp changes remain excluded from PRE even when engine-internal event order may be known. Negative precombat event times are counted but not silently shifted to nonnegative time.

The parser currently assumes a single tracked nonpet/nonenemy actor and rejects multiple actor-index/spawn tuples; it does not certify general multi-actor/target identity, build eligibility, all class mechanics, buffs, debuffs, charges or global priorities. No target-specific event is mapped. All source-reconstructed features remain **unbound** until independent semantic verification. This is a test of actual resource *producer path*, not a test that the engine correctly recommends an ability.

The raw resource log is a Native research binary artifact tied to source SHA, but the subsequent generalized raw NDJSON contract remains `CALLER_SUPPLIED_UNVERIFIED` to prevent an unsupported jump from source byte equality to Blizzard current-patch or fully certified gameplay truth.

## Required tests

- Synthetic source patch guard: exactly two native hooks (gain/loss), source changes and double patch fail closed.
- Synthetic log: positive/negative event timestamps, native actor tuple, native decimal values, direction, source log SHA, source-line integrity, exact independent bytes, same-timestamp exclusion, future exclusion, mixed actors and malformed marker failure. Three synthetic specialization labels; readiness UNKNOWN.
- Public Native C++ run must compile the **same** fixed upstream with the new reporter, and run each of three public profiles and report true resource event counts. This is separately checked through GitHub Actions; do not call it PASS before actual job success.
- Prior 206 source-pointer-backed foreground actions were verified on a DIFFERENT modified binary; no SHA/evidence from that run substitutes for this new resource producer.

## Next after actual Native evidence

1. Audit actor and resource identity on a new held-out spec/build; explicitly account for initial, max, direct writes and missing native events before claiming resource coverage.
2. Source-check one more mechanic family as needed (buff stack transitions or cooldown/charge state) and preserve effect identity/target scoping, then build *actual* decision-time PRE with source transition timestamps strictly `< t`.
3. Only with validated semantic bindings and complete readiness dimensional policy compare the shared APL evaluator with Native foreground reference. Unknown and missing state are distinct from conflict; independent WCL blind candidate lock comes before any SimC comparison.
4. MAIN alone can promote frozen contracts and canonical General Rotation. `main`, Seq578, global handoff, production pointer and FROZEN unchanged; Seq637 UNKNOWN.

## Evidence pointer
Dedicated Native workflow: https://github.com/degong2-code/zrotationhelper/actions/runs/41022542615 (result pending as of this initial note). A subsequent branch-local evidence update shall record actual run conclusion, resource counts, patch and executable SHA and any pipeline failure. No claim of actual live WCL or Blizzard production validation.
