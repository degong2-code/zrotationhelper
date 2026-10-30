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
