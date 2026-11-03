# SimC APL → General Rotation Model: engine completion contract (branch successor)

**Policy:** `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1` (2026-11-02).  
**Owner:** `work/gr-simc-st-2t-wcl-blind-20261102` research branch.  
**Goal:** Produce a source-faithful, executable, verified SimulationCraft-origin General Rotation **hypothesis**, before any WCL behavior comparison or player error verdict. No Encounter Rotation Plan, NSRT, raid phase advice, addon feature expansion, or MAIN promotion.

## Precise distinction

SimC is the initial hypothesis **oracle**, not independent proof of optimal play. APL source parsing, effective APL model execution, native SimC decision selection, and actual WCL player behavior are **four distinct authorities**. Do not write “SimC model complete” just because every raw action row can be parsed. Do not use WCL to patch a SimC grammar/parser error: reconcile against native SimC itself.

## Source roles and reusability

- `tools/research/simc_apl_source_engine.py` — generic SimC effective `save_actions` acquisition and action-list/provenance fingerprinting.
- `tools/research/simc_apl_syntax_inventory.py` and `simc_apl_conditional_ir.py` — existing structural parser/IR.
- `tools/research/simc_apl_condition_research.py`, `simc_apl_variable_runtime.py`, `simc_apl_priority_trace.py`, `simc_apl_precombat_replay.py` — existing research-only numeric/variable/priority semantics; **reuse** when source verified, do not silently replace with contradictory implementations.
- `tools/research/simc_apl_semantic_ir_v2.py` — independent, exact **source line** and typed AST compiler for the pinned Fury profile; branch research reference. Its evaluator has bounded proof and deliberately does not certify native behavior.
- `tools/research/simc_native_reference_capture.py` — verified native binary, effective `save_actions`, log and JSON2 capture.
- `tools/research/simc_native_effective_apl_crosscheck_v1.py` — direct original-source versus actual **native effective APL** identity/structural comparison. A difference must be reported and reconciled, not hidden.
- `tools/research/simc_apl_readiness_provider.py` — externally supplied readiness hypothesis requiring all eight current generic dimensions; does **not** prove source-complete spell readiness or patch truth.

This is a **consolidation plan**, not a new queue of mutually independent parser frameworks. When native proof identifies a reusable implementation already present, integrate it with the production research pipeline instead of maintaining duplicate output authority.

## Acceptance gates

| Gate | Requirement | Current evidence |
|---|---|---|
| G1 **source identity + lossless static extraction** | Verify exact SimC commit, profile/build/effective APL identities, preserve every applicable list/row/order/parameter and detect unsupported expression syntax without dropping it | 2026-11-03 Fury pinned source: `121/121` APL rows, eight lists, 51 `if`, 18 `value`, eight `value_else`, eight `condition`; Python 3.12/3.14 + real-source CI PASS #41562454066 |
| G2 **SimC language semantics** | Exact scalar arithmetic (`%` division, `%%` remainder), boolean truth/precedence; variable initialization/mutations, `call` fallback vs `run` no-fallback; all source-modifier semantics that affect priority, including side-effect/background actions, precombat, item use and off-GCD | Core syntax AST/limited side-effect and call/run synthetic behavior implemented; full SimC native semantic equivalence **UNKNOWN** |
| G3 **current build's effective APL** | Native SimC must export effective action lists; compare original profile vs saved effective action list and use latter where the two differ | Actual native effective parity CI #41563013349 initiated, outcome must be checked; not a static source PASS substitution |
| G4 **stateful action-choice parity** | Independently reproduce native SimC *foreground selected action* and reasons under identical strict PRE state, call/run persistent sequence state, resource, aura, cooldown, charge, GCD, target count and relevant fight duration; prove exact match on locked synthetic/native test scenarios without tuning on holdout | **NOT ESTABLISHED**. Prior SimC JSON2 sample **performed** actions are not proof of selected foreground APL row; do not equate the two |
| G5 **opener + conditional IR completeness** | Preserve precombat/non-damage directives separately, derive stateful opener and opener termination, ST / exactly 2 targets / cleave / AoE target breakpoints, talent/build changes, proc/execute/pooling and fallback. Emit priority order, IF condition, alternative actions, unknown/coverage, source evidence | **NOT ESTABLISHED** |
| G6 **cross-spec generic regression** | After one complete vertical specialization, run at least one different spec/build using the same generic engine and a new native reference; forbid Fury-specific branching in the core | **NOT ESTABLISHED** |
| G7 **WCL comparison eligibility** | Only after G1–G6 scope-relevant criteria, replay independent locked WCL strict-PRE states against the **version-pinned SimC model**; distinguish missing game state from actual SimC–WCL disagreement and report candidate/conflict/unknown | **BLOCKED**, by design, until meaningful SimC model fidelity |

G1 syntax/source fidelity is **not** a completion declaration for the product. Some additional unsupported features may be introduced by profiles outside the pinned Fury fixture; each unsupported action/operand must remain an explicit coverage gap.

## Non-negotiable correctness tests

1. **Losslessness:** input action lines, source-line hashes, modifiers, order, list graph and `variable` overwrites reconcile byte-for-byte with source.
2. **Independent oracle:** v2 evaluator and earlier generic engine may agree with each other and **both still be wrong**; compare against native SimulationCraft and authoritative source semantics.
3. **Same-build replay:** separate native 1-target and 2-target scenarios are useful, but different *sampled action sequences* alone never establish why SimC selected an action.
4. **Strict PRE:** `latest transition timestamp < action timestamp`; never use same-time/future events or later WCL data as decision state.
5. **Candidate vs gameplay truth:** SimC APL priority is only a source hypothesis. No mandatory priority, optimality, WCL validation or dummy mistake until independently supported.
6. **Failure discipline:** distinguish parser/grammar failure, model interpreter semantic mismatch, native profile/build/effective APL divergence, unavailable state, and WCL/API failure. Track exact mismatched row/case; do not rerun source collection merely to obtain another green CI badge.

## Session exact next

1. Inspect #41563013349 actual native effective APL comparison. Reconcile any differing row or parameter against source/native output.
2. Reuse `simc_apl_priority_trace` and `simc_apl_variable_runtime` where correct, then build a small **native per-decision foreground selection oracle**; start with Fury ST/2-target and locked state/fight fixtures. Unknown native decision state is not parity.
3. Only after native decision parity, turn source-level rows into the user-readable General Rotation opener/conditional action IR. Expand to a second spec/build using the same core.
4. Resume WCL blind post-lock comparison and dummy feedback **after** the SimC engine is fit to serve as the reference model.

No user-side WoW addon installation or manual local task is required for this stage.
