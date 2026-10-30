# Developer Note — SimC native iteration + emission-sequence causal join

Date: 2026-10-30. Owner: `work/github-ci-bootstrap` research branch; NO MAIN/FROZEN/Seq578/global pointer promotion. Seq637 UNKNOWN.

## Why the existing evidence was insufficient

Earlier source-locked native C++ run [41034104957](https://github.com/degong2-code/zrotationhelper/actions/runs/41034104957) read 298 `select_action` entry groups and 1,452 current/max value comparisons across Enhancement, Fury and Unholy. **1,390** were `SOURCE_LOG_ORDER_AMBIGUITY`, **62** were `SAME_TIMESTAMP_SOURCE_AMBIGUITY`. Native source event time alone and text log line position do not establish the same *source iteration* or emission order; prior apparent conflicts are NOT proof that a specific resource callback is missing. Using an INIT at t=0 printed after the selection at t=942 as causal PRE would be unsound.

## Source authority and minimal design

Fixed official upstream SimulationCraft commit `710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`:
- `engine/sim/sim.hpp` includes `sim_t::current_iteration` (initial -1, then incremented in the sim work loop) and `sim_t::thread_index`. These are **runtime iteration/thread** identity, not arbitrary new counters inferred by sorting logs.
- Separate reporter adds a `sim_t`-owned `unsigned long long zrot_native_event_sequence = 0`. It is incremented **at every source event emission** using `sim->zrot_native_event_sequence++`, including six types: `GAIN,LOSS,INIT,RECALC,SELECT_BEGIN,SELECT_END`.
- Each new `ZROT_NATIVE_EVENT_V2` source marker contains type, thread index, current iteration, sequence, native event time ms, actor, spawn, resource, current and max. A separately executed public SimC binary and exact source/profile/APL/log SHA constitute the capture reference. Counter is monotonic for the `sim_t` lifetime and intentionally **not** reset at iteration boundaries. Older V1 markers are emitted unchanged immediately adjacent to their matching V2 markers, allowing the old audit to remain independent.
- `tools/research/simc_native_epoch_sequence_instrument.py`: source SHA check; exact insertion anchors in already-patched resource gain/loss, init/recalc and select_entry; asserts exactly six sites, and sim.hpp counter field. No changes to action selection or resource semantics.
- `tools/research/simc_native_epoch_sequence_audit.py`: first parser rechecks V2 format and immediately paired V1 action/source marker including exact native current/max values; second parser independently splits all raw native lines and recomputes full event projection and uniqueness. Duplicated source sequence, mixed marker data, absent V1, unknown iteration and malformed source fail closed. The capture's original log SHA and new executable SHA must be kept separate from previous runs.
- `compare_epoch_bound_resources`: pairs native entry diagnostic groups with V2 `SELECT_BEGIN/END` and resource source values only for **matching** thread, iteration, actor, spawn; requires `source_event_sequence < selection_sequence` and `source_time_ms < selection_time_ms`. Same timestamp cannot enter Strict PRE even when sequence is earlier. Cross-epoch events never inherit prior state; sequence/timestamp contradictions remain `UNKNOWN`. Diagnostic current/max values are **read-only comparator references**, never injected as PRE state transitions.

This is an **evidence join** for only instrumented resource source sites; it does NOT prove complete actor resource state, current Blizzard mechanics, target/talent/charge/buff/cooldown readiness, or the correctness/optimality of any SimC APL. Neither WCL blind discovery nor action recommendation changes.

## Validation and failure history

- First feature CI [41053513707](https://github.com/degong2-code/zrotationhelper/actions/runs/41053513707) failed synthetic patch fixture for `SELECT_END` because a two-line fake source did not match the genuine three-line SimC statement: **PIPELINE TEST FIXTURE FAILURE**, not SimC priority failure.
- Second [41053577615](https://github.com/degong2-code/zrotationhelper/actions/runs/41053577615) passed the synthetic preflight but failed source patch on INIT, whose `INIT` tag is in the format string, not the trailing argument. Corrected source anchor and fixture separately.
- Current code commit at initial note writing: `be05b9100f42425bfbfe5a963924f04ac57c8db2`; further code commits supersede that provisional SHA. Source-locked Native C++ CI [41053700577](https://github.com/degong2-code/zrotationhelper/actions/runs/41053700577) was in progress when initially documented; **MUST verify final job result before claiming Native PASS**.
- Synthetic tests cover matching thread/iteration/actor+spawn; cross-iteration resets with identical timestamps; source sequence duplicates; earlier clock but later sequence; same timestamp exclusion; V2/V1 data mismatch; independent reparsing and no readiness promotion.

## Exact next after real native evidence

1. Report event counts per actual `sim_t::current_iteration`, source-sequence monotonicity and proof of V1/V2 adjacency; inspect causal match/mismatch/unknown distributions for all three public profiles, without asserting representative population precision.
2. If the native output contradicts the proposed epoch contract, preserve FAIL and fix the source evidence producer rather than relaxing the join to timestamp-only.
3. Investigate the most impactful repeatable resource discrepancies by source value and native direct-write callsite; don't instrument temporary `pool_resource.ready()` writes as persisted changes. Continue to require Strict PRE, verified identity and readiness.
4. A future **new** build/spec holdout plus independent WCL candidate lock and Blizzard mechanic check are needed before any playable IF/ELSE rule can be promoted.

The user has no local PyCharm steps. MAIN only owns canonical pointers and shared FROZEN state. No production/runtime gameplay rules updated.


## Empirical V2 source run and reset-boundary successor

Initial **Native monotonic sequence run** [41053700577](https://github.com/degong2-code/zrotationhelper/actions/runs/41053700577) **SUCCESS**: compiled source SHA-pinned SimC, all three Native profile runs, old V1 resource/action provenance retained, V2 raw source marker reconciliation independently PASS. Executable SHA256 `31b0f6d5e27def3c7d410cd0707052e19491e47250ba4a2591f703977d1e6b00`.

| Profile | Source-stamped V2 events | thread/iteration | Sequence vs timestamp contradictory comparison fields | Same-time fields |
| --- | ---: | --- | ---: | ---: |
| Enhancement | 305 | `[0,0]` | 366 | 18 |
| Fury | 536 | `[0,0]` | 640 | 32 |
| Unholy | 283 | `[0,0]` | 384 | 12 |
| **Total** | **1,124** | — | **1,390** | **62** |

This proves genuine **runtime source emission sequence**, not causally consistent join. All resource and select-entry samples carried the **same** SimC `current_iteration=0` in each profile's log. However genuine source events with timestamp earlier than a decision had a later runtime emission sequence. The result confirms that **thread+iteration+actor/spawn is not enough to establish a continuous event clock epoch**; same iteration can contain additional reset/initialization or other time-base changes. The 1,390 contradictions are UNKNOWN, not confirmed resource write conflicts. Do not count them as priority mismatches or try to fix by moving event timestamps.

**Successor minimal source addition** `tools/research/simc_native_reset_boundary_instrument.py`: patches pinned `engine/sim/sim.cpp::sim_t::reset()` to emit `ZROT_NATIVE_RESET_BOUNDARY_V1|thread|current_iteration|source_sequence|previous_clock_ms` **before** the native event manager reset. It increments the SAME `sim_t` monotonic counter as resource/selection stamps. No post-hoc log-line time sorting. Each V2 source event is now paired with the latest preceding source-stamped reset boundary **within the same thread and iteration**. This yields a reset-boundary-specific epoch key `(source_log_sha, thread, current_iteration, reset_boundary_sequence, actor, spawn)`; no reset boundary means UNKNOWN. The independently reimplemented parser verifies all reset fields/sequence uniqueness and rejects missing boundaries, tampering, same-iteration clock resets, same-ms leakage and cross-boundary state carry. This improves evidence linkage but still does not assert all state mutations are instrumented.

**New Native run** [41054849471](https://github.com/degong2-code/zrotationhelper/actions/runs/41054849471): pending at the initial note update; confirm its conclusion, report counts of reset boundaries, cross-epoch same-time ambiguities and certified current/max comparisons before recording PASS. The original V2 run's C++ success cannot substitute for this new reporter.

**Boundary requirement:** even if RESET-stamped pairs agree, that proves *consistency* of their observed current/max values in pinned SimC; not general readiness, optimality, Blizzard current Retail semantics, unrecorded direct writes or live WCL gameplay. More resource current/max transitions and optional native diagnostic counterfactual may be needed. The current Native log summaries are owner-branch evidence, not MAIN promotion.


## Reset clock epoch and source proof contract — successor

The first real V2 source run at [41053700577](https://github.com/degong2-code/zrotationhelper/actions/runs/41053700577) passed compiled/native and independent log parity, but all three profiles carried `current_iteration=0` while late source emissions had earlier Native clock times than already recorded selection entries. The underlying **causal epoch** was still unidentified. We did NOT force a successful state join: 1,390 comparisons retained a source-sequence/timestamp contradiction and 62 were same-time excluded.

A new **minimal reset-boundary source reporter** at `tools/research/simc_native_reset_boundary_instrument.py` instruments pinned `engine/sim/sim.cpp::sim_t::reset()` just before `event_mgr.reset()`. It emits:
`ZROT_NATIVE_RESET_BOUNDARY_V1|thread_index|current_iteration|shared_source_sequence|previous_clock_ms`.
The sequence is taken from the **same SimC `sim_t`-owned counter** used for all `ZROT_NATIVE_EVENT_V2` resource and selection markers. No post-hoc elapsed time / text log position is used to infer the reset.

`tools/research/simc_native_epoch_sequence_audit.py` now parses and independently re-parses all reset stamps, verifies unique shared source sequences (reset and V2), then labels every V2 source event with the **most recent same-thread/same-iteration source reset whose sequence precedes its own**. The candidate causal source key is `(capture_log_sha256, thread, current_iteration, reset_boundary_sequence, actor_index, actor_spawn_index)`. Selection begins/ends must refer to the exact same reset epoch, and a resource predecessor must have both `source sequence < decision sequence` and `source timestamp < decision timestamp`. Missing reset identity, same timestamp, later sequence or contradictory time remain UNKNOWN, not false-confirmed priority conflict. Same `current_iteration` after a genuine second `sim_t::reset()` becomes a **different epoch**, with no resource carry-over.

### Pipeline failure preservation

- [41054849471](https://github.com/degong2-code/zrotationhelper/actions/runs/41054849471) synthetic FAIL because a fake reset row mistakenly encoded a literal backslash+n rather than a real newline. No C++ compilation commenced.
- [41055040759](https://github.com/degong2-code/zrotationhelper/actions/runs/41055040759) synthetic FAIL because producer code initially referenced `resets` in the first parser scope before that independent parser's reset list existed. The code now binds reset boundary in the correct independent audit.
- [41055147815](https://github.com/degong2-code/zrotationhelper/actions/runs/41055147815) synthetic FAIL due to test numerator confusion: 6 Native V2 source events **plus** 2 distinct reset markers were incorrectly asserted as 8 V2 events. Corrected assertion to 6 without hiding the two reset stamps.

These are **pipeline/test failures**, not invalidated SimC APL hypotheses or evidence that a certain resource policy is wrong. Do not mark Native PASS for this successor until a compiled public-profile run independently proves reset stamps and epoch-aware comparison.

**Successor CI:** [41055221198](https://github.com/degong2-code/zrotationhelper/actions/runs/41055221198). Source-pinned V2-only run 41053700577 remains separate evidence. Next exact action: inspect the actual reset-count/epoch distribution and per-resource match/conflict/unknown results from the successor, then audit what remains unverified. No user-facing recommendation or MAIN/FROZEN promotion.


## Verified Native clock-reset epoch successor — completed

[Native CI run 41055221198](https://github.com/degong2-code/zrotationhelper/actions/runs/41055221198) **SUCCESS**: pinned official upstream checkout, reporter-only source patches to player.cpp/sim.hpp/sim.cpp, complete C++ compile, three actual public profile simulations, complete V1/V2 resource and selection identity checks, source-stamped `sim_t::reset` boundary parser and independent byte recalculation, epoch+source-sequence+strict-time diagnostic comparison, summary-only artifact. Exact compiled instrumented binary SHA256 **`4eb6c175cda08834ee2454c4ef183c824c727f3f4b56852d61fa0c0a3187fd79`**, upstream SHA **`710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`**; do not reuse V2-only binary `31b0f6...` as proof for this run.

| Pinned public profile | Source-stamped resource/selection V2 events | Native `select_action` entry diagnostics | Source-pointer-backed selected actions | Strictly older source value consistent | Same-ms excluded | Eligible contradictory |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Enhancement Shaman | 305 | 64 | 64 | 272 | 112 | 0 |
| Fury Warrior | 536 | 168 | 76 | 372 | 300 | 0 |
| Unholy Death Knight | 283 | 66 | 66 | 184 | 212 | 0 |
| **Aggregate** | **1,124** | **298** | **206** | **828** | **624** | **0** |

The 828 `CONSISTENT_PRIOR_SOURCE_VALUE` entries are **field comparisons**, not verified decisions or complete resource states. Every admitted predecessor was from the **same source-run/Native thread/current_iteration/actual reset boundary/actor/spawn**, with `source_sequence < native selection BEGIN sequence` and `source timestamp < selection timestamp`. The reset-boundary evidence is emitted at actual `sim_t::reset()` using the exact same SimC-owned monotonic source counter. The old 1,390 source sequence/timestamp contradictions are no longer falsely joined across clock epochs, not converted into an invented 1,390 successful conditions.

The other 624 field comparisons are `SAME_TIMESTAMP_NOT_STRICT_PRE`. They remain **UNKNOWN**, even if there is a source event sequence preceding the diagnostic within that millisecond. A source-emission order alone does not change the authoritative `< action_time` rule. The 0 eligible mismatches is **not** proof of full source-mutation coverage or SimC's optimal action choice. SimC resource initial/max and gain/loss functions are still partial (direct writes in class modules and untracked state families remain). The exact number of reset boundaries is not surfaced in this run's summary: **UNKNOWN**, though each profile's validation required reset-boundary evidence. Do not invent counts.

**Validation granularity:** Source anchored source/synthetic tests PASS. Python 3.12 and 3.14 offline CI for the successor code commit: [41055221257](https://github.com/degong2-code/zrotationhelper/actions/runs/41055221257) both SUCCESS. Prior synthetic failures (newline, parser binding, test denominator) are preserved above as pipeline regressions, not simulated rotation claims. A post-code documentation update is independent of the native executable receipt.

### Decision and user-impact-focused Exact Next

The initial state-join *identity blocker* has been resolved **for this pinned source/3 public-fixture scope**. Do not keep extending sequence/epoch gates without a concrete mismatch. Next, audit which **APL operands and actual action readiness** remain unobserved at the now source-pinned foreground decisions. Establish generic semantic bindings (resource max/current only with verified actor/build, then proc/buff/debuff/cooldown/charges/target) against actual source mechanics and Blizzard current game authority. Run bounded native `select_action` replay with match/conflict/UNKNOWN separately. A completely new build/spec or independent holdout plus post-lock independent WCL discovery remains required for gameplay priority/freeze. The 624 same-time exclusions can be studied for material user impact, but do not relax the Strict PRE timestamp rule or treat source sequence as permission to leak same-time state.

**No** gameplay addon/UI recommendation is released from this evidence; no MAIN/current state/FROZEN/Seq578/canonical pointers/global handoff were altered; Seq637 UNKNOWN. Local PyCharm step is not required.
