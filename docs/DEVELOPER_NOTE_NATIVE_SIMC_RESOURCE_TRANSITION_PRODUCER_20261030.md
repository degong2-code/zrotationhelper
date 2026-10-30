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


## Native verification successor — confirmed actual PRE events

The initial resource-trace native run [41022542615](https://github.com/degong2-code/zrotationhelper/actions/runs/41022542615) **SUCCESS** with source C++ compile, three public profiles, 496 actual resource mutations, full logged-marker byte-projection and independent recomputation. Every profile's first pointer-backed `SELECT_ACTION_FOREGROUND` was at `t=0ms`, leaving zero nonnegative resource events strictly earlier than that first decision. That result was kept as a genuine boundary, not altered by negative timestamps or post-action snapshots.

The **successor run** [41023255296](https://github.com/degong2-code/zrotationhelper/actions/runs/41023255296) **SUCCESS**. Same source instrumentation and fixed public profile set; Python research probe added a second event-relative anchor: **the actual final pointer-backed `SELECT_ACTION_FOREGROUND` timestamp from that exact run**. SHA receipt, native log and original effective APL identity all match the modified executable. No synthetic resource events were added or timestamps moved.

| Source-pinned public profile | Native gain/loss markers | First select_action ms | Strictly before first | Final select_action ms | Strictly before final | Actual pointer-backed native select_action samples |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Enhancement Shaman | 165 | 0 | 0 | 54411 | 162 | 64 |
| Fury Warrior | 192 | 0 | 0 | 54181 | 191 | 76 |
| Unholy Death Knight | 139 | 0 | 0 | 54381 | 136 | 66 |
| **Total** | **496** | — | **0** | — | **489** | **206** |

Source upstream commit: `710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`. Newly compiled **successor-run** executable SHA256 `55f9770682c177cc45c95a0af3c2516e6b989691bfebce4c8d05278f74170da3`. Previous initial-run executable SHA256 `a15852626098eca38b188a72c2a4de72e4aaab3496065a1431581c6f8`; they are separate run artifacts and were not conflated.

**Both native runs** independently recalculated the raw logged mutation rows and byte-addressed normalized NDJSON, and ran the existing Strict PRE adapter; latest run classified all three final decision boundaries as `NATIVE_RESOURCE_MUTATIONS_OBSERVED_BUT_UNBOUND`. **All three conditional APL replays were BLOCKED with no recommended action**. This is an appropriate result: no verified SimC operand mapping, full resource state producer coverage, buff/cooldown/charge/target readiness or native decision-time semantic equivalence is in evidence.

The 489 figure is the number of actual gain/loss change records strictly prior to the final selected action in these three source-locked fixture runs. It is **not** 489 fully observed actions, an instruction accuracy rate, a complete state snapshot, or 489 usable gameplay rules. The independently captured Native action-selection count 206 belongs to an action-identity evidence lane, not the same denominator as 489 resource mutation events.

**Offline verification:** [41023255328](https://github.com/degong2-code/zrotationhelper/actions/runs/41023255328) Python 3.12/3.14 SUCCESS at the successor Python-probe code commit. Synthetic producer/validator tests at the native workflow step passed. No WCL API, live Blizzard patch, current game actor readiness or independent blind WCL replay was performed.

### Decision and exact next

The source-backed resource gain/loss producer is now empirically functioning; repeating fixed profiles or expanding lexical candidate counts is lower value than closing the *state completeness and semantics* gap.

- Identify and capture native **resource initialization and max/current direct-write** paths, preferably with a bounded completeness audit against independent in-simulator snapshots. Do not infer missing resource values from last observed gain/loss or backdate snapshots to decision PRE.
- Add verified actor/target identity, spec/build binding and a generic resource operand semantics adapter. Before mapping to `rage`, `runic_power`, etc., establish exact native expression evaluation equivalence; do not use a textual name match as truth.
- Capture source-accountable buff/cooldown/charge changes if they alter decisions. Only then apply the shared evaluator to source-locked Native foreground rows; report match/conflict/unknown separately and use a previously unused build/spec as holdout.
- Preserve independent WCL blind discovery until candidate lock. Native SimC source consistency is not optimality or user-facing rule validation.

Owner remains BRANCH. No changes to MAIN, FROZEN/Seq578, canonical registry, global handoff or active production pointer. Seq637 UNKNOWN.
