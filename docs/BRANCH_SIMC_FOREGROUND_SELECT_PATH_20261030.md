# BRANCH — SimC Native foreground selection-branch provenance

Research date: 2026-10-30. **No MAIN or product pointer promotion.**

## Why this is required for the general rotation engine

The target is a **generic engine that can automatically investigate any SimulationCraft profile/APL/build**, independently validate locked WCL discoveries, and eventually teach a player IF/ELSE action decisions. This increment closes a source attribution ambiguity: the existing native `FOREGROUND_EXECUTE_ACTION` callsite was not enough to distinguish an action selected by `player_t::select_action` from `strict_sequence` or `spell_queued_action` returning an action from `player_t::execute_action`.

This is *selection-branch provenance*, not native optimality, user-ready rotation, cooldown readiness or strict PRE reconstruction.

## Exact SimulationCraft C++ authority

Pinned source: `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`, `engine/player/player.cpp`, `action_t* player_t::execute_action()`.

This function contains mutually exclusive branches:
1. `if ( strict_sequence ) action = strict_sequence;`
2. `else if ( enable_spell_queue && spell_queued_action ) if ( spell_queued_action->ready() ) action = spell_queued_action;`
3. `else action = select_action( *active_action_list, execute_type::FOREGROUND );`

Immediately after the branch, an `action` may cause `sequence_add( action, action->target, "FOREGROUND_EXECUTE_ACTION" )`; a quiet action can be skipped in the source sequence. The function distinguishes native execution **return path**, not all evaluated/failed APL rows, the `select_action` recursion path, live spell readiness or a prior state snapshot.

The existing pointer reporter in `engine/report/json/report_json.cpp` proves `entry.action->signature == &(action->action_list->action_list[row])`; the existing callsite reporter preserves direct precombat, specialized queue and variable-side-effect records independently.

## Code

- `tools/research/simc_apl_foreground_selection_instrument.py` uses fail-closed, exact-match source anchors to add `zrot_foreground_selection_path` to sequence samples. It is set within the *actual* `player_t::execute_action()` branch, passed to `sequence_add`, and serialized by the same JSON2 report, with one source-checked C++ instrumentation build. No actor/spec spell map, no priority evaluator modification.
  - `SELECT_ACTION_FOREGROUND`: return from actual foreground `select_action` branch, **not** a certified gameplay decision rule
  - `STRICT_SEQUENCE`: strict-sequence bypass branch
  - `SPELL_QUEUED_ACTION`: queued action was considered ready under native SimC and returned, **not** our own readiness proof
  - `NOT_APPLICABLE`: actual action sequence samples from precombat, specialized queue, variable-side-effect callsites
  - `UNKNOWN_FOREGROUND_BRANCH`: explicit fail-closed unknown if no branch provenance
- `tools/research/simc_apl_pointer_provenance_audit.py` audits direct branch separately from source pointer identity, checks source/build provenance, forbids `NOT_APPLICABLE` on foreground, forbids foreground branch on other callsites, labels waits `WAIT_NON_ACTION`, and never treats missing/unknown selection as `SELECT_ACTION_FOREGROUND`. `source_bound_native_select_action_rows` requires both (a) exact pointer/source-row/signature match and (b) actual recorded select_action branch.
- `tools/research/simc_apl_pointer_native_probe.py` adds third *held-out* Unholy Death Knight official profile from the same source snapshot; original Enhancement and Fury remain. 1 iteration, fixed seed and no WCL/Blizzard/API credentials. Hash-pin source profile, saved effective APL and native JSON2, new modified executable per CI run. Never upload raw logs/profiles/executable.
- `.github/workflows/simc-apl-pointer-provenance.yml` invokes the third opt-in reporter after existing pointer+callsite instrumentation, compiles the pinned source once, and tests 3 public profiles. Python 3.12/3.14 offline workflows are independent.

## Validation boundaries and known proof

Earlier independent Native run `41016072868` **SUCCESS** using a different, separately instrumented executable SHA256 `15d1eb46fc3af3aeaafb31ace6cdb33825675ac5b436f6db0ccfe8218258ef86`: 165 total JSON2 rows, 163 pointer-exact source-backed actions (71 Enhancement, 92 Fury) and 2 nonaction waits; 140 recorded `FOREGROUND_EXECUTE_ACTION` callsites and 23 PRECOMBAT. The 140 were **not** yet source-proven to come from the normal `select_action` branch.

Synthetic self-tests for this increment cover exact source anchors, false double instrumentation, all three selection branches, stale/missing/wrong selection tags, same-name same-time duplicate source APL rows, and nonforeground/foreground contradiction.

**Native C++ source build/experiment CI for this increment:** https://github.com/degong2-code/zrotationhelper/actions/runs/41017244770. Its result must be read from the actual job/summary before reporting PASS. Reuse no previous modified binary hash.

## Explicit limits and next

Even a new source-backed `SELECT_ACTION_FOREGROUND` count is **NOT** equivalent to "optimal IF/ELSE action rules": it lacks precise availability/readiness, SimC own decision-time operand values, previous strictly-before-action transitions, actor/talent and target eligibility, independent WCL discovery/holdout, and current Blizzard patch cross-check. A native `select_action` return proves that branch was used; it does not prove no other higher-priority action was ready in the research engine.

Next: use source-locked new profile/build to test the exact path and preserved UNKNOWN; then reconstruct **only** Strict PRE observable operand states from source-accountable transitions, and replay the shared generic APL evaluator without future/same timestamp leakage. WCL blind candidate lock remains independent of SimC labels and hypotheses; counterfactual SimC selectively when decision ambiguity affects gameplay.

Owner: BRANCH. No changes to MAIN `CURRENT_STATE`, FROZEN, Seq578, active manifest/production pointer, canonical registry or global `LATEST_HANDOFF`. Seq637 UNKNOWN.


## Verified Native evidence — new 3-spec holdout (same research increment)

**Native C++ run:** https://github.com/degong2-code/zrotationhelper/actions/runs/41017244770 — **SUCCESS**, including source-pin checkout, all three independent synthetic source-module selftests, complete C++ compile, 3 public-profile executions, provenance audit and summary-only artifact upload.

- Upstream `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`.
- Newly compiled modified executable SHA256 **`cd218f6479a22b11e32d85dce0feb764f8c17bbddb6873f1512e117550c72df3`**; no previous binary SHA or execution evidence was substituted.
- Actual Native run captures **243** JSON2 sequence entries: **241** pointer-matched source action objects with exact effective APL row signatures, **2** confirmed nonaction waits, 0 signature drift or unknown genuine action calls.
- **206** source-pointer-backed action entries were directly labeled `SELECT_ACTION_FOREGROUND` inside the `player_t::execute_action` branch, **35** PRECOMBAT actions were `NOT_APPLICABLE`. No strict sequence, spell queue, variable or specialized queue records appeared in this limited fixed-seed fixture run. Those source variants passed synthetic/static checks but were not empirically covered by this Native sample.

| Public fixed-source profile | Effective APL rows | Native records | Exact source-pointer action rows | Real selected foreground branch, pointer matched | Precombat | Nonaction waits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Enhancement Shaman | 114 | 71 | 71 | 64 | 7 | 0 |
| Fury Warrior | 121 | 94 | 92 | 76 | 16 | 2 |
| Unholy Death Knight (**new held-out profile**) | 63 | 78 | 78 | 66 | 12 | 0 |
| **Total** | **298** | **243** | **241** | **206** | **35** | **2** |

Pinned exact effective APL SHA256:
- Enhancement: `298594da9057781c67f8ec90161d9e5529523b1797e73f5b7aef3c5c400d4bc4`.
- Fury: `98635a684638d241000c0f9b3a78b9eb43d9579b522f864b8aaf5ebaa159e737`.
- Unholy: `0e17b8c00c7d03b83f6560d57d19f3844e665ba1fba34d929c289e31ee92c097`.

Pinned source profile SHA256:
- Enhancement: `b9f78fb9043cd6596ce5f4b025a4998d631bde96def9ec1abdf591c2e8d06abf`.
- Fury: `e872cca507063e3d63b84e522688b4ad44b2f7f7664e50e3f5553cf3f858088c`.
- Unholy: `6a931073fc75752615f56eaa0a054d5e36d85109d0d6c2c650ba3e08f34de102`.

Python 3.12 and 3.14 offline CI at the feature commit: https://github.com/degong2-code/zrotationhelper/actions/runs/41017244704 — both SUCCESS. Independent audit synthetic tests included duplicated same-time action name but different APL ordinal, strict/queued vs `SELECT_ACTION_FOREGROUND`, missing source branch, invalid category crossover and source SHA mismatches.

**Exactly what is proven:** The actual executable in the pinned run returned these 206 sampled actions through the normal `select_action` branch, and the instantiated action objects point to and match their precise effective APL source rows. It does **not** establish that every APL condition, readiness input or target is semantically reconstructed; that a missing action should have been available; that `SimC` rules are optimally correct; or that Blizzard's current Retail combat mechanics match this pinned data. This is **Native source event identity verification**, not **shared generic engine priority parity**. Only one fixed seed and one profile per spec were tested; 206/206 is not a population accuracy statistic or independent WCL validation.

**Next focused user-impactful research:** a generic Strict PRE operand/feature producer contract with precise source event time and state provenance, then evaluate the already-built structural conditional IR/graph against the independently captured Native foreground selected APL rows. Keep unknown ability readiness, unobservable variables and target changes UNKNOWN, and hold off on gameplay advice until cross-spec comparison and post-lock independent WCL validation. An explicit strict/queued selection fixture is useful if these source routes become relevant to actual rule decisions, but do not repeat expensive native builds merely to increase a superficial branch-count metric.

MAIN-only authority unchanged. No global handoff, General Rotation FROZEN, Seq578, Seq637 (UNKNOWN), product manifest, production pointer or MAIN branch edits.
