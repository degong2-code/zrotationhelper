# Developer Note — Native clock-epoch generalization fixture, Havoc (2026-10-30)

**Owner:** `work/github-ci-bootstrap` research BRANCH. **No MAIN, FROZEN, global handoff, canonical registry, Seq578, or production pointer promotion. Seq637 remains UNKNOWN.**

## Why this work was chosen

Previous verified source-locked SimC experiment [41055221198](https://github.com/degong2-code/zrotationhelper/actions/runs/41055221198) demonstrated a Native-generated monotonic sequence and `sim_t::reset()` source boundary, with 828 resource current/max **field comparisons** consistent with a prior same-epoch source value and 624 same-millisecond comparisons properly excluded. This solved the source epoch attribution blocker **only for Enhancement, Fury, Unholy in one pinned run each**, not complete General Rotation or optimality.

The next proportionate test was whether the **same generic instrumentation and independently recalculated raw-source identity** works on a fourth specialization with different resource behavior, rather than adding more semantic gates or repeatedly recompiling the same three fixtures.

## Code change (no new class-specific engine)

`tools/research/simc_apl_pointer_native_probe.py` adds a new pinned public profile:
`profiles/MID2/MID2_Demon_Hunter_Havoc.simc` (spec `havoc`), verified present in exact upstream `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`.

No class-specific resource name, spell, boss, APL priority, readiness, or exception was added. The existing reporter-only C++ hooks in the exact source are unchanged, and one GitHub Actions build executes all **four** profiles under the same fixed-seed, one-iteration research contract.

The same native probe now includes two previously missing summary receipts: `native_epoch_reset_boundary_count` and `native_epoch_reset_thread_iteration_pairs`. Each profile must have at least one source-stamped actual `sim_t::reset` boundary. `simc_native_epoch_sequence_audit.py` continues to independently reparse original V2 event markers and resets, check shared source-sequence uniqueness, V1/V2 source parity, actor/spawn identity and causal native reset epoch. No timestamp-only source joins are accepted.

## Actual source and validation proof

**Native GitHub CI:** [41059211056](https://github.com/degong2-code/zrotationhelper/actions/runs/41059211056) — **SUCCESS**, including exact source checkout, unchanged C++ source patches, fresh Native compiler/build, independent source-raw audit and all four public profile runs.

- Pinned official source SHA: `710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`.
- **Freshly compiled modified Native executable SHA256:** `92019e3205e09be7cbcb895c4682fb9cec73987574ba15c7b8732693bce59d2f`. This is separate from previous executable `4eb6c175cda08834ee2454c4ef183c824c727f3f4b56852d61fa0c0a3187fd79`.
- Every profile's original Native event log had its own SHA receipt; all independent epoch log byte audits returned `PASS_EPOCH_NATIVE_SOURCE_BYTES_INDEPENDENT_RECALC`.
- Each profile emitted **2 source-stamped reset boundaries** for thread 0 / reported current_iteration 0; the separate actual reset sequence differentiates clock epochs even when `current_iteration` stays the same.

| Pinned public profile | Native source V2 events | Actual reset boundaries | Native select_action diagnostic entries | Pointer-backed foreground action rows | Consistent strictly earlier current/max comparisons | Same-ms excluded |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Enhancement | 305 | 2 | 64 | 64 | 272 | 112 |
| Fury | 536 | 2 | 168 | 76 | 372 | 300 |
| Unholy DK | 283 | 2 | 66 | 66 | 184 | 212 |
| Havoc DH (**new independent source profile fixture**) | **416** | **2** | **64** | **64** | **140** | **116** |
| **Total** | **1,540** | **8 (across separate runs)** | **362** | **270** | **968** | **740** |

The **1,708** field comparisons (968 + 740) are current/max *diagnostic fields*, not 1,708 actions or complete state samples. An admitted predecessor had matching source run log hash, thread, current_iteration, exact reset boundary, actor and spawn, plus `source sequence < decision BEGIN sequence` AND `source timestamp < decision timestamp`. The 740 same-ms comparisons are **UNKNOWN**, even when the source emission order was earlier. There were **0 eligible mismatches in these four fixed fixtures**, which does NOT establish that any current/max direct-write or resource producer gap is impossible.

The 362 `select_action` invocations are not equivalent to 270 pointer-backed recorded actions. Some invocations return no recordable action, or belong to different action callsite semantics; the counts are intentionally not treated as one denominator.

**Offline CI:** [41059210999](https://github.com/degong2-code/zrotationhelper/actions/runs/41059210999) — Python 3.12 and 3.14 both SUCCESS at implementation commit `920810bb5d383397d0577d2b26fc0c3fd9a3615e`. The executable build and live Native test were separate verified evidence from the offline compile checks.

## Precise conclusion and boundaries

**Validated:** source-generated epoch/reset identity, monotonic event sequence, actor/spawn tracking and strict-timestamp current/max comparison work in a fourth different public specialization under fixed source, fixed seed and one run each. Previous source event identity, raw-line SHA and APL action-pointer provenance are maintained.

**Not validated:** completeness of all resource current/max writes (class modules and temporary readiness trial writes remain distinct), correct interpretation/availability of all APL operands, action readiness (resource/buff/cooldown/charge/target), user-facing optimal priority, a holdout of independent WCL behavior, or live Blizzard Retail mechanics. A Native SimC reference is still only a hypothesis source. **No IF/ELSE playable decision was promoted, and no diagnostic snapshot was backdated as PRE.** This new Havoc source profile is a **producer-generalization fixture**, not a WCL blind/holdout or causal proof of action selection optimality.

## Current practical follow-up (higher user impact than further epoch instrumentation)

1. Use existing `simc_apl_observability_contract.py` and semantic route plan on real APL sources to inventory which required operands are still not independently bound/observable, and which readiness dimensions block recommendations. Source-only public profile CI [41020542529](https://github.com/degong2-code/zrotationhelper/actions/runs/41020542529) counted, respectively, Enhancement 77 operands/24 readiness tokens; Fury 68/26; Unholy 92/21; Havoc 57/19. These are **source requirements**, not 294 observed values or 90 verified ready actions.
2. Prioritize generic resource operand current/max and source identity semantics first where Native evidence supports it; do not assume lexical similarity is mechanical identity. Expand to buff/debuff and cooldown/charge/target state when these change a user-facing IF/ELSE.
3. Separately compare source-locked Native selected actions vs the existing shared generic evaluator. Distinguish matched, conflict, omitted readiness, unknown, and unsupported. Require prospective independent holdout and WCL blind candidate lock before gameplay claims.
4. Keep `main` `4790f77f76a75f26ff0558d1d18c16cd9d630c4b` and authoritative MAIN/FROZEN/Seq578 untouched. Owner BRANCH only; verify MAIN compatibility before any promotion.

No local user/PyCharm command was needed, and no downloadable Python artifact is being delivered (GitHub source/CI references are the evidence).
