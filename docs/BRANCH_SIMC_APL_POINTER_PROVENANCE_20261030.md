# BRANCH — SimC native APL action-object pointer provenance (2026-10-30)

## Intent and proof boundary

Build a **generic, reusable SimC APL/profile research engine**, not a hand-coded specialization rotation. After source-derived conditional graphs, generic state/readiness requirements, DBC lookup and sampled action_t IDs, the important unresolved identity question is: **which instantiated APL source row produced this native action object?**

An actor's `action_t::name()` and timing do not prove its source APL line. Repeated tokens, same-timestamp actions, replacements, procs, pets and control/variable actions break naïve matching.

## Pinned upstream C++ evidence

At `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`:
- `engine/player/player.cpp`, `player_t::create_actions()`: assigns `a->action_list = apl` and `a->signature = &(action_priority)`, retaining a pointer to the actual owning APL priority row. `a->signature_str = action_str` retains the instantiated row string, subject to SimC's action modification options.
- `engine/player/action_priority_list.hpp`: each list contains `std::vector<action_priority_t> action_list`; its ordinal is recovered by comparing the stored pointer to the entry address, **not** by name or time.
- `engine/report/json/report_json.cpp`: native JSON2 `action_sequence` currently writes `entry.action->id`, `entry.action->name()` but does not export the owning APL pointer information.
- `engine/player/player.cpp` and `engine/action/action.cpp`: sampled action sequences include more than proven selected foreground APL decisions. This approach proves instantiated object-to-APL row pointer relation only, **not** decision optimality, complete readiness or strict PRE.

## Branch implementation

- `tools/research/simc_apl_pointer_instrument.py`: Git HEAD pin check and exact-one anchor guards on upstream `report_json.cpp`, adds the one missing include, then outputs additional JSON fields only when `entry.action->signature` pointer equals an entry's address in its own `action_list->action_list`. Fields: `zrot_apl_object_list`, 1-based `zrot_apl_object_ordinal`, `zrot_apl_object_signature`, and `zrot_origin_proof=OWNING_LIST_SIGNATURE_POINTER_EQUALITY`. No changes to APL or action selection; opt-in separate research build only.
- `tools/research/simc_apl_pointer_provenance_audit.py`: validates the exact effective APL SHA and typed native pointer evidence, joins list+ordinal to parsed effective APL source. If source row signature matches, records `POINTER_ROW_AND_EXACT_EFFECTIVE_APL_SIGNATURE_MATCH`; source mutation gets a distinct `...SIGNATURE_DRIFT_NEEDS_REVIEW`; missing pointer remains `NO_POINTER_PROVENANCE`; any incomplete/fake pointer evidence fails closed. Queue failure is separately labeled. Same-time and duplicate-name rows are tested explicitly.
- `tools/research/simc_apl_pointer_native_probe.py`: uses independently compiled research binary, actual public pinned upstream profiles in temporary CI storage (Enhancement and Fury fixtures only), exported `save_actions`, JSON2 and log. Hash-verifies binary, profile, effective APL, JSON2 and log before examining provenance; raw native data is never uploaded.
- `.github/workflows/simc-apl-pointer-provenance.yml`: separate scoped **expensive** C++ build workflow. Exact SHA upstream fetch, reporter-only instrumentation, CMake/Ninja no-networking CLI build, public fixture audit; uploads summary JSON + instrumented-source SHA receipt only. This does not run on unrelated repo edits, unlike quick offline CI.

## Validation and lifecycle

**Initial proof achieved:** pinned source checkout/instrumentation contract and synthetic fail-closed audits pass on the dedicated GitHub job, including two same-time/same-name actions with different source-row ordinals. Python 3.12/3.14 offline CI from the initial instrumentation commit `61af08a3bf4e37d6c7d09f06086dd03d2d5ec1a5` was SUCCESS.

**Dedicated native build run:** https://github.com/degong2-code/zrotationhelper/actions/runs/41013989448. Its compile/native verification result must be checked explicitly: synthetic and patch application successes **must not** be recorded as a compiled-native PASS.

Even after actual instrumented binary success, this identifies the provenance of *recorded action instances*. It still does not observe the decision's complete Strict PRE (strictly `<t`), establish native foreground APL selection for every action, infer applicable talent/build readiness, prove Blizzard live-patch mechanics, or validate General Rotation/WCL. Source instrumentation revision and newly compiled executable SHA must never be confused with prior pinned official Docker executable `804fc81296fe1ae5208161df5cece258e2ac7489de60c3816d2097da3612e6fc`.

## Focused next, after build result

- If the separately compiled SimC executes, quantify **exact pointer-backed APL row provenance vs UNKNOWN/signature drift** for both profiles. Compare repeated tokens/multiple priority rows and precombat separately; never fill missing provenance from a same-timestamp event.
- Determine from actual source control flow which sampled actions are selected *foreground decisions* vs variable/control/other effects; this claim is stronger than object provenance and should have its own evidence/validation.
- Then build valid state-at-decision from timestamp transitions strictly earlier than action time and replay shared generic evaluator using certified readiness, followed by independent blind WCL candidate lock and only post-lock SimC comparison.

No changes to MAIN branch, `CURRENT_STATE`, canonical registry, active manifest, global `LATEST_HANDOFF`, FROZEN, Seq578 or product pointer. Seq637 UNKNOWN. This is BRANCH evidence, not a MAIN promotion.
