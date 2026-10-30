# Developer Note — Native SimC resource lifecycle completeness boundary (2026-10-30)

**Owner:** research branch `work/github-ci-bootstrap`. Research-only, no MAIN/FROZEN promotion. Target: a single generic engine for arbitrary WoW Retail specialization, build and encounter. Previous source-backed actions and explicit resource gain/loss events are not a license to infer arbitrary `READY` or General Rotation priority.

## Prior verified source evidence

- [Native resource-gain/loss run 41023255296](https://github.com/degong2-code/zrotationhelper/actions/runs/41023255296): pinned official SimC source `710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`. 496 observed gain/loss function records in Enhancement/Fury/Unholy public 1-iteration runs; 489 records strictly before the corresponding final `SELECT_ACTION_FOREGROUND` timestamp in those runs. Zero PRE records before first selected action at t=0 ms. All replay recommendations BLOCKED due to absent verified semantic operand binding, complete resource mechanics and readiness. This is resource *mutation log provenance*, not source-state completeness.
- Existing `simc_native_resource_change_instrument.py` patches `player_t::resource_gain/loss` ONLY; ignores initialization, resource max recalculation and direct assignments.

## Source audit and important negative discovery

Pin `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`, `engine/player/player.cpp`:
- `player_t::init_resources(bool force)` sets `resources.initial[resource]`, `resources.max[resource]`, and `resources.current[resource]` according to initial options and actor type. It is invoked from reset/precombat/arise paths and may execute repeatedly. These are genuine function-exit initial-state observations, not necessarily *changes* and not automatically PRE to t=0.
- `player_t::recalculate_resource_max` computes a new maximum, may increase current health before combat or clamp current to the recalculated maximum; its function-exit current/max pair is relevant to later decision evaluation.
- `pool_resource_t::ready()` in the same file TEMPORARILY subtracts resource cost/sets to max and restores original current resources while testing whether the next action could be ready. A simplistic hook on every `resources.current[...] =` or `-=` would report these **nonpersistent trial values as genuine state transitions**. Do not instrument them as authoritative resource state.
- A bounded source audit sees direct `resources.current/max/initial` assignments in the pinned player.cpp, but it is NOT a repository-wide proof; official source search returns resource state accesses in `engine/class_modules/*`, actions, items and raid-event code. No claim all persistent direct-write sites are covered.

## New generic implementation and evidence contract

- `tools/research/simc_native_resource_lifecycle_instrument.py`: exact-upstream source SHA and unique-anchor guard; source-only reporter hooks inside `init_resources` and at the end of `recalculate_resource_max`, producing `ZROT_NATIVE_RESOURCE_LIFECYCLE_V1` with native timestamp ms, actor index, actor spawn index, resource enum, current, max, and `INIT` or `RECALC`. No actor/spec ability table, no change to actual resource math, readiness or decision selection. Avoid tracing pets/enemies and absent/zero maximum resources. It also emits a scoped direct-assignment-site inventory for `player.cpp` only.
- `tools/research/simc_native_resource_lifecycle_probe.py`: parses the original SHA-pinned Native log, exact line SHA/offset, native actor+spawn identity and function-exit values. Separately re-parses the raw bytes and independently reconstructs line receipts and typed rows, detects tampering, rejects mixed actor indexes, nonnumeric/invalid values and malformed markers. Multiple **spawn instances of the same actor** are allowed and separated; never join across a spawn transition.
- For the explicitly selected actor/spawn, typed current/max observations are passed to the prior independent raw transition adapter and StrictPreStateProvider, using **only timestamps strictly earlier than the reference native select_action time**. The actual source observation at `t` is excluded. No temporal shifting or deriving PRE by differencing JSON2 action snapshots.
- Existing `tools/research/simc_apl_pointer_native_probe.py` and isolated `.github/workflows/simc-apl-pointer-provenance.yml` incorporate the additional reporter in the SAME pinned-source C++ build as prior pointer/callsite/foreground and resource gain/loss instrumentation. Only GitHub runner-local raw source/logs are read; upload summary and source-receipts only. Source, profile, APL, binary and raw log SHA differ by build/run and must never be conflated.

## Claim strength

A valid `INIT` marker proves the source-instrumented function exited with a specific current/max pair for a specified native actor and spawn. A valid `RECALC` marker proves the corresponding function exited with a current/max pair. It does **not** prove all resource writes are recorded or that last-observed current/max equals the next decision's resource, nor correct SimC APL operand semantics; target, GCD, cooldown, charge, buffs, fight length, and Blizzard current-patch mechanics are outside these two hooks. Readiness remains `UNKNOWN`. Same-timestamp events cannot be PRE for a decision at that timestamp; actor spawn IDs must match. A line hash demonstrates provenance within supplied Native log bytes; only actual source-locked binary CI evidence supports native origin.

## Verification and follow-up

- Synthetic three-label suite: exact source pin/unique anchors, repeated instrumentation fail, malformed markers, independent line and value tampering, negative timestamp exclusion, same-time strict PRE exclusion, actor spawn mismatch, no READY promotion, preserved blocking.
- **Native C++ CI:** https://github.com/degong2-code/zrotationhelper/actions/runs/41030582477 — result should be checked explicitly before setting PASS. Earlier 41023255296 is prior source reporter only and cannot substitute. The next note update must record actual INIT/RECALC counts and how many observations were STRICTLY PRE the final selected action per actor/spawn, as well as the new binary SHA.
- Offline CI: https://github.com/degong2-code/zrotationhelper/actions/runs/41030582482 — result must be independently verified.
- Next higher-impact task after this bounded increment: establish *actual resource state coverage* against source-verified **independent diagnostic samples at decision points**, with source-level actor identity and no same-time leakage; classify unknown direct-write/callback paths and fix them only where gameplay-facing priority would change. Add buff/cooldown/charge producers as needed and only then attempt conditional APL parity. New, unused build/spec holdout after candidate lock; WCL blind candidate discovery stays isolated from SimC semantics before its lock.

**Authority:** MAIN `CURRENT_STATE`, global `LATEST_HANDOFF`, canonical registry, General Rotation/FROZEN, Seq578, product pointer unchanged. Seq637 UNKNOWN. No WCL/Blizzard live gameplay claims.


## Source-level direct-write counterexamples (bounded audit)

Pinned **upstream** tree `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926` yielded concrete non-`resource_gain/loss` current-resource assignments outside the instrumented generic functions:

- `engine/class_modules/sc_warrior.cpp` lines ~8148, 8162, 8193, 8207 and 8238 contain current-health multiplier changes adjacent to `recalculate_resource_max(RESOURCE_HEALTH)`. Importantly some happen **after** that generic recalc hook, so observing recalc's function exit alone can miss the final current-health value.
- `engine/class_modules/sc_mage.cpp` line ~6778 sets `resources.current[rt] = resources.max[rt] * pct` after changing max for an aura interaction, outside generic gain/loss and generic recalc.
- `engine/player/player.cpp` `pool_resource_t::ready()` temporary write/restore cases are a counterexample to simply recording **every** direct assignment as a combat-state transition. Only durable changes belong in persistent PRE features. The exact set of class/source sites is build-dependent.

This negative evidence demonstrates why `source_completeness=PARTIAL` and `readiness=UNKNOWN` are mandatory even if **all** INIT/RECALC logs in a small profile run parse successfully. A future read-only, pinned-tree write-site inventory or an independently captured *decision-time diagnostic snapshot* may locate missing transitions; snapshots taken at the current selection timestamp must never be retroactively treated as `t-1` PRE observations.


## Native executed evidence — verified successor result, 2026-10-30

**Pinned actual Native C++ CI**: https://github.com/degong2-code/zrotationhelper/actions/runs/41030582477 — **SUCCESS**, including upstream source pin, exact anchor applied, synthetic fail-closed checks, newly instrumented executable compiled, public pinned Enhancement/Fury/Unholy profile runs, full Native reference hash audit, independent INIT/RECALC source-log parse and typed Strict PRE adapter.

- Pinned upstream commit `710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`; **new executable SHA256 `03117f21a65769b583bb384d16b1688f18422e1f236d519977970de78e357eb3`**. This binary is distinct from prior `55f977...` resource-gain/loss run and cannot borrow its provenance receipt.
- Existing native gain/loss count stayed **496 total**: Enhancement 165, Fury 192, Unholy 139. Previous foreground source-pointer counts also remained 64, 76 and 66 respectively.
- **32 observed INIT lifecycle function-exit records**: Enhancement 12, Fury 8, Unholy 12. Native actor index 0 had separate spawn instances `-1` (pre-arise/reset) and `1` (actual combat actor). Only spawn 1 was admitted to the current actor's Strict PRE observations: Enhancement 9, Fury 6, Unholy 9 = **24 source-backed INIT observations strictly before the corresponding final select_action**. None was strictly prior to the first select_action at t=0 ms.
- Independent lifecycle log parser recalculated each raw line SHA256, line offset, timestamp, actor+spawn, current/max values and marker type in all three profiles: `PASS_EXACT_NATIVE_SOURCE_LOG_RECALC`. Existing raw-event projection and Strict PRE adapter were used with **no operand binding, no readiness assertion**.
- **0 real RECALC marks** in these three source-locked fixture runs. The `recalculate_resource_max` reporting hook compiled and its source-anchor/synthetic validation passed, but **no real dynamic maximum-resource recalc event was exercised** here. Do not report native RECALC proof. Source-labeled INIT exposes max at initialization, which is different from dynamic max change.
- The `pool_resource.ready()` temporary direct-write/restore exclusion is source-established, not a claim that the whole engine's other direct assignments are instrumented. Warrior health and Mage mana class-module write-site examples remain unresolved **persistent direct-write** gaps. No decision-time independent diagnostic snapshots were collected; no completeness measured.
- Native resource lifecycle readiness stays **UNKNOWN**. Observed INIT value is evidence of a function-exit value, not proof the complete state is known at a later decision; same-timestamp and unobserved changes are never implicitly filled. Action trace still BLOCKED, no playable priority rule released.
- Offline Python 3.12 / 3.14 CI for implementation commit: https://github.com/degong2-code/zrotationhelper/actions/runs/41030582482 — both **SUCCESS**. Synthetic 3-spec lifecycle parser/provenance failures were covered by the Native workflow precompile stage.

### Focused Exact Next after evidence

Before expanding source hooks or claiming full resource readiness:
1. Independently capture **decision-time diagnostic resource current/max** for a source-pointer-backed select_action sample (for *audit only*, never backdated to Strict PRE). Compare against the last source-logged transition under same actor+spawn and native event time, distinguishing **missing direct-write**, **same-timestamp ambiguity**, **initialization/spawn**, **source-feature semantic ambiguity**. Lock comparison policy before new held-out fixture.
2. Find a *generic deterministic fixture* that actually executes `recalculate_resource_max()` and validates its C++ trace on a real event, or record it as NOT COVERED. Avoid a class-specific hack in generic engine.
3. Inventory/classify real persistent direct-write paths across the pinned source tree without mistaking temporary `pool_resource.ready()` trials for genuine state changes. Only instrument gaps shown to materially affect user-facing condition/readiness.
4. After state producer semantics and completeness are adequate, add buff/cooldown/charge/target state and source-backed operand mapping, then compare generic evaluator to actual select_action decisions. Independent WCL blind lane remains locked separately until candidate lock; no MAIN promotion, frozen baseline or Seq changes.


## Later critical source-order qualification (successor 2026-10-30)

The independent select-entry diagnostic source audit uncovered **noncausal/ambiguous producer joins** that earlier time-filtered counts could not detect. See [DEVELOPER_NOTE_NATIVE_SELECT_RESOURCE_DIAGNOSTIC_20261030.md](DEVELOPER_NOTE_NATIVE_SELECT_RESOURCE_DIAGNOSTIC_20261030.md) and Native run [41034104957](https://github.com/degong2-code/zrotationhelper/actions/runs/41034104957).

The former **24 spawn-associated INIT observations with `timestamp < final select_action time`** and **489 gain/loss events with `timestamp < final select_action time`** are valid **source event count and timestamp-filter counts**, but **NOT independently certified members of the same causal native execution epoch**. Native comparison found 1,390 log-order ambiguous and 62 same-ms ambiguous pairs across 1,452 resource field checks; zero comparisons were eligible for a certified consistency conclusion. Earlier CI PASS remains authentic for exactly the checks it ran (source hook, log SHA, projection, local `<t` filter), not for a stronger causal state claim. This is a **producer identity/causal join insufficiency**, not evidence that SimC APL is wrong or a specific class resource rule failed.

**Authoritative research Exact Next:** add runtime-generated monotonic event sequence plus genuine simulation iteration/epoch identity to ALL resource and select-entry markers at source emission, then independently verify joining and only then repeat actual PRE current/max comparison. Do not retroactively reinterpret the previous sample as full PRE, READY or user-facing General Rotation.
