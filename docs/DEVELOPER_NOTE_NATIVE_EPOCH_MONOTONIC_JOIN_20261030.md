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
