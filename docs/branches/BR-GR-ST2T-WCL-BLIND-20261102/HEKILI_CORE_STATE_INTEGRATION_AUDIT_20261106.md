# Hekili Core / Scripts / State / Classes — actionable integration audit

**Branch-local, 2026-11-06.** Product scope ID `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`. This is an **applied integration audit** (with actual executable output), not a proposal to port historical 11.x Hekili source or move the decision engine into current WoW 12.1.5.

## 1. Exact inspected historical source and source-to-engine responsibilities

Pinned Hekili repo: `Hekili/hekili@36daec382e6557fd57a263bbfb060856ef9fe9d8` (`thewarwithin`; pre-Midnight). This specific historical checkout is the source for the line numbers below.

| Old Hekili actual module / lines | Verified behavior in source | zRotationHelper existing owner to REUSE | Newly applied / still missing |
|---|---|---|---|
| **`Scripts.lua:349-410`** `SimToLua`, `:426+` `SplitExpr`, `:1043+` `Loadstring` | Converts SimC-like conditions to Lua, compiles executable evaluators | `simc_apl_semantic_ir_v2.py`: `Expression`, `evaluate_ast`, `ast_symbols`; `simc_apl_semantic_resolver.py` | **APPLIED:** source IF string from pinned *original Native source-root PRE row* is parsed into existing typed AST. It is not evaluated true by assuming unknown buff/resource facts; never dynamic `loadstring`. |
| **`Core.lua:695+` `GetPredictionFromAPL`**, `:882-905`, `:1025-1042` | Builds ordered candidates; emits reasons for disabled/unknown abilities, timing, script failures and usability | `general_rotation_original_selection_return_replay_v1.py`, `general_rotation_source_decision_reason_ledger_v1.py`, `general_rotation_time_scoped_priority_ir_v1.py` | **APPLIED:** native source-selected action plus preceding candidates' typed reasons, but independently complete physical READY is **0** and selected root detailed sampling **64/262**. |
| **`Core.lua:912-985`** LIST/CALL/RUN | Old Hekili recursively evaluates `call_action_list` and `run_action_list` when generating a prediction | `simc_apl_semantic_ir_v2.py` `bounded_decision`, `bounded_control_step` | **CRITICAL SEMANTIC DIVERGENCE:** original pinned SimC `player.cpp:14264-14300` selects `run_action_list` control action, which changes active list when executed; `call_action_list` recurses during selection. Hekili's forecast-path recursion must NOT overwrite SimC source semantics. Source-replay preserves control event separately from spell action. |
| **`State.lua:6787+` `state.reset`, `:7174+` `state.advance`** | Resets snapshots; progresses time, queued events and resource regeneration; maintains effect/cooldown/buff state | `general_rotation_strict_pre_state_engine_v1.py`, `simc_apl_semantic_ir_v2.bounded_control_step` and existing Native PRE | **PARTIAL:** a synthetic-only, deterministic `simulate_synthetic_state` is implemented; actual Native selected time and source target context are recorded. Effects from unobserved buffs/resources are **UNKNOWN**. Native-parity dynamic state simulator still missing, and must be evidence-backed for each mechanic. |
| **`Classes.lua:138+` resources, `:210+` talents, `:232+` aura, `:410+` state expressions** plus `TheWarWithin/MageArcane.lua`, `WarriorFury.lua` | Specialization-local definitions register abilities/resources/auras/effects into common engine | Existing proof gate contracts in `general_rotation_decision_proof_engine_v1.py`, preliminary specialized adapters | **TO IMPLEMENT:** source-pinned `SpecAdapter` for real abilities, substitutions, cooldown/charges, resource/cost/procs, GCD, target. No old expansion/patch mechanics hardcoded into generic core. |
| **`Hekili.lua:202-257` `Debug`, `SaveDebugSnapshot`** | Candidate reason trail and issue-snapshot machinery | Source row SHA + Native root/sweep IDs + reason-ledger event stream | **APPLIED:** per-return `source_row_sha256`, source list, ordinal, exact original C++ sweep, ordered candidate reasons and original C++ timestamp. **MISSING:** full 262 root selection stream and nested leaf paths, complete state PRE snapshot. |
| **`Core.lua:1444+` `GetNextPrediction`**, `Core.lua:1633+`, `:1738+` | Iterated forecasts and virtual time advance | Native proof replay + source-hypothesis IR, future `StateProjection` | **NOT CURRENTLY CLAIMED:** original selected source rows `!=` forecasted next 5 casts, and original Native selection `!=` independently optimal priority. No HekiLight secondary-icons-as-forecast. |
| **`Events.lua:158+`, `Targets.lua:361+`** | In-game event collection, nameplate/enemy tracking | `addons/research/ZRotDummyProbe` safe own-cast candidate, WCL/offline Strict PRE research | **DO NOT PORT:** in-game combat-state decision logic or legacy `COMBAT_LOG_EVENT_UNFILTERED`/aura sniffing, especially through secret or forbidden aspects. Client capability gate applies first. |

### Architecture judgment (engineering, not a Blizzard statement)

**Correct separation for zRotationHelper:**
```text
SimC profile / original Native observation / WCL blind (independent)
       |
       +--> Existing typed APL AST (Scripts-like)
       +--> Existing causal Native choice / candidate ledger (Core-like)
       +--> Source-pinned SpecAdapter capabilities (Classes-like)
       +--> Explicit observed snapshot / hypothetical state reducer (State-like)
       |                                  (NO mixing of simulated with observed)
       v
Versioned General Rotation Opener + Conditional Decision IR
       |
WCL discovery lock -> independent holdout -> Blizzard mechanics
       |
Evidence-bounded Dummy Practice Evaluator (post-session by default)
       |
Tiny addon only records non-secret own actions and renders safe UI
```

The offline simulator may simulate fully specified source-reviewed mechanics for research, but no old Hekili code should be injected into the game-client addon. Current Blizzard API/policy boundaries live in `RETAIL_ADDON_POLICY_CAPABILITY_GATE_20261106.md`.

## 2. Actual integrated implementation (not just a diagram)

Code: `tools/research/general_rotation_integrated_opener_research_v1.py` on branch `work/gr-simc-st-2t-wcl-blind-20261102`. It **reuses** (a) original C++ source selected-row + causal sweep ledger; (b) independently proof-bounded source reason ledger; (c) original C++ source-root actor PRE **per-row aggregates**. It compiles only the actually stored source IF into the preexisting typed Python AST.

For each retained early source return it outputs:

- `simc_ms`, source `list`, ordinal, `source_row_sha256`, exact top-level sweep ID, `DIRECT/CHILD_PROPAGATED`.
- A kind classifier separating `run_action_list`, `auto_attack`, potion/item action and **potentially executable** source rows. These are **SimC-returned rows, NOT user keypresses/casts**.
- Source IF and its AST symbol dependencies categorised by existing namespace groups. Original PRE receipt only gives the IF **per source-row aggregate**, not exact facts for each selected root: `condition: UNKNOWN_MISSING_EXACT_SELECTED_ROOT_FACTS` is preserved even if original selected the action. This prevents fabricated independent IF/READY.
- Prior candidate source decision counts from root/sweep; independently confirmed IF FALSE on a control is not promoted to whole-skill NOT_READY.
- A hypothetical state model is separate: unknown resource, buff, cooldown, effects and next state remain unknown; `simulate_synthetic_state` performs explicit **synthetic-only** deltas without input mutation. Real Native source/actor cannot pass through this synthetic fixture path.

**CI:** [Actions #42148518679](https://github.com/degong2-code/zrotationhelper/actions/runs/42148518679) — Python 3.12 and 3.14 synthetic PASS and no-new-C++ actual earlier SimC Native receipt integration PASS on the same 4 cases. Prior original input Native run #42140591685; causal reason ledger run #42146818557. GitHub artifact ID `13471655637`, ZIP SHA256 `dc3193c306162222146de66afcf1b1267af92073429665d9e3a183838d44bf7e`, inner JSON SHA256 `fd55601886e10e6ffb73d3e2638b6df6c44b38626a15ce2d1fb0d7761eadda92` (expires 2026-11-13). No WCL API or WoW client runs.

**Coverage:** 2,121 original Native SELECT sweeps **reused**; 64 initial source-return rows across Fury ST, Fury 2T, Arcane ST, Arcane 2T, 16 per case; 198 remaining root returns unsampled. 38 potential executable source return rows, 16 run-list control, 2 auto-attack setup, 4 potion, 2 item use, 2 use-items control. "38 potential executable" **does not** certify 38 physical casts/READY.

## 3. Example original observed source action flow (NOT a gameplay prescription)

| Original source profile context | First observed returned source rows | Interpretation |
|---|---|---|
| Fury ST | `auto_attack → charge → run_action_list → recklessness → potion → use_item → run_action_list → rampage → run_action_list …` | `run_action_list` is a selected *control action*, not an extra manually cast spell; known return path `slayer` |
| Fury 2T | `auto_attack → charge → run_action_list → recklessness → potion → use_item → run_action_list → rampage → run_action_list …` | Same names, but action originates in `slayer_aoe` list rather than `slayer`, showing a meaningful 1-vs-2 target route; cannot infer why every buff/charge condition held |
| Arcane ST | `potion → arcane_orb → arcane_surge → use_items → arcane_missiles → arcane_blast → arcane_barrage → touch_of_the_magi …` | Source selected return, with nested `cooldowns`/`spellslinger` paths, not proven player casts |
| Arcane 2T | `potion → arcane_orb → arcane_surge → use_items → arcane_missiles → arcane_blast → arcane_barrage → touch_of_the_magi …` | Similar sampled source action names but different Native timings; **not evidence of identical optimized target count priority** |

Example timestamps: Arcane ST source chooses `arcane_surge` at 907ms and `arcane_missiles` at 2513ms; Arcane 2T at 907ms and 2510ms, respectively. Multiple returns at 0ms can be off-GCD/control, not a sequence of manual keypresses at same time. The time field is SimC source selection time, *not* WCL event Strict PRE.

## 4. High-value next steps, with explicit completion criteria

1. **Reproducible StateSnapshot adapter**: lift source-root actor/mana PRE into per-chosen root facts (not a row aggregate), with actual `root_id`/timestamp/source hash, and hard unknown for missing buffs/procs/resources. Integrate independently checked `Expression` results to the same root BEFORE using them for choice reason.
2. **SpecAdapter and transition reducer**, reused from existing native/source proofs: one current real physical ability, source-pinned all READY gates + spell effect/regen/cooldown/charge events, distinguish actual source choice from hypothetical effect at each virtual time. No old Hekili mechanics copied from 11.x.
3. **Bounded parity target**: a single true executable opener row + earlier-source candidate reasons fully source-linked in both ST and 2T. A source-proven actual Native chosen row alone is insufficient. Keep G4 parity and G5 model INCOMPLETE until tested with independent inputs.
4. **WCL blind validation**: numeric/structural independent candidate and frozen thresholds before any SimC/Hekili meaningful answer is injected. Only then post-lock SimC source state comparison, mechanic reconciliation, targeted holdout/counterfactual.
5. **Training**: offline practice comparison with versioned validated General Rotation. In-game adapter does not run APL/State solver; only permitted own-cast recording or UI, after actual 12.1.5 client observability testing.

Do not replace this integrated code with another parser/heuristic priority engine; extend existing core interfaces, using cheap replay first and new Native build only for missing causal state or method route. Never expand the product to encounter-specific/NSRT outputs. No MAIN/FROZEN promotion from this branch.

Reference: `HEKILI_ARCHITECTURE_REFERENCE_20261106.md`, `GENERAL_ROTATION_HEKILI_POLICY_ROADMAP_20261106.md`, `RETAIL_ADDON_POLICY_CAPABILITY_GATE_20261106.md`.
