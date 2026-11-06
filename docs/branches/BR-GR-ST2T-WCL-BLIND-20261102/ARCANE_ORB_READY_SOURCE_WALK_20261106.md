# Arcane Orb full action READY — official pinned SimC source walk

**Date 2026-11-06 | Branch research only | No positive readiness claim.**
Product: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`.
Only official pinned source `simulationcraft/simc@b522cded8c26b97dac03fdf56e57a03ec7e8faa6` is evidence; historic Hekili contributes the modular `SpecAdapter → State → DecisionReason` architecture, **not** gameplay truth or a live WoW addon implementation.

## 1. Exact virtual method ancestry

| Base / derived class | Source location and blob (exact pinned checkout) | Evidence |
|---|---|---|
| `arcane_orb_t final : public arcane_mage_spell_t` | `engine/class_modules/sc_mage.cpp:2602–2678`, blob `306d835f2db5f7418da221ce155d32e81c53f45c` | The class implements constructor, `execute()` and `impact()`; **no local `ready()` or `action_ready()` override** in this class definition. |
| `arcane_mage_spell_t : public mage_spell_t` | Same `sc_mage.cpp:2070–2095` | Contains constructor and time/charge multiplier, **no override**. |
| `mage_spell_t : public spell_t` | Same `sc_mage.cpp:1547–~1985` | Combat effects/cost/multiplier overrides, **no `ready()` override** in the inspected class body; cost can be virtual and buff-sensitive. |
| `spell_t : public spell_base_t` | `engine/action/spell.hpp:12–25`, blob `78e881efa8c56ed0e034b6147c0bc8f194c91955` | Header declares amount/accuracy/damage overrides, **no `ready()` override**. |
| `spell_base_t : public action_t` | `engine/action/spell_base.hpp:12–33`, blob `bc7a3a1d9ab3709cd8563242a8cd279a9983ee44` | Header declares **virtual `cost()` override** and related spell methods but **no `ready()` override**. |
| `action_t::ready()` and `action_t::action_ready()` | `engine/action/action.cpp:2640–2676` and `:2576–2630`, blob `399ecd9453b3f30bfc2ebf2b3ffd8f56cce8f8d4` | Original source uses the shared base-class gate sequence, before the actual caller returns its selected APL source action. |

This is a pinned static inspection, **not** compilation-time verification of every possible virtual target, mutable field, specialization variant, active talent or readiness input. Its main value is identifying exactly which gates need per-root evidence.

## 2. Original `action_t::ready()` stage order (spell-ability property layer)

| Order | Official source | Gate / potential blocking condition | Required proof to independently classify |
|---|---|---|---|
| R1 | `action.cpp:2643–2644` | `!cooldown->is_ready()` | Original cooldown/charges state and cooldown method semantics; **not known per selected root** |
| R2 | `:2646–2647` | `internal_cooldown->down()` | Original internal cooldown PRE + clock |
| R3 | `:2649–2650` | `player->is_moving() && !usable_moving()` | Movement / casting, norgannons sagacity, execute_time, channel/range |
| R4 | `:2652–2657` | `!cost_affordable()`, can trigger starved proc on failure | Current resource type, virtual `cost()`, buffs and mana; **do not call twice** (side effects). For Arcane Orb virtual `spell_base_t::cost()` at `spell.cpp:37–43` can return zero with Chilled Clarity. |
| R5 | `:2659–2664` | `usable_while_casting` and nonzero execute_time | Current cast state, effective cast time |
| R6 | `:2666–2672` | While casting/channeling, nonzero GCD and player GCD not ready | Current GCD, cast/channel status |
| R7 | `:2675` | All above passed → base `ready()` true | Source Native return alone is **not** independent full-route closure |

## 3. Original `action_t::action_ready()` stage order (action/user-input layer)

| Order | Official source | Mechanic or branch | Independent closure requirement |
|---|---|---|---|
| A1 | `action.cpp:2580–2583` | Calls `ready()`; if false, returns false | Verify R1–R7 and any virtual changes |
| A2 | `:2585–2589` | Calls `select_target()`, false excludes | `select_target` at `:2435–2574` can select target, check target viability/distance, and **recursively evaluate action_ready** for explicit target cycling; source options and target PRE mandatory |
| A3 | `:2591–2596` | `cycle_targets && target_non_sleeping_list.size()>1` may return true immediately | Need source options/target count, not just later gate results |
| A4 | `:2598–2605` | If action skill/skill debuff differs, two **RNG rolls** may short-circuit with false positive or false negative | Never replay RNG calls for observation, preserve original method-exit reason. An observed true may originate from a false-positive route |
| A5 | `:2607–2608` | `!has_movement_directionality()` excludes | Movement/directionality/state |
| A6 | `:2610–2611` | `line_cooldown->down()` excludes | Line cooldown method/time PRE |
| A7 | `:2613–2614` | `sync_action && !sync_action->action_ready()` excludes | The separately selected synced action can recurse/readiness-call; do **not** infer all candidate READY from just caller |
| A8 | `:2616–2617` | Explicit `option.moving` constraint mismatches player movement | Option/movement PRE |
| A9 | `:2619–2620` | `if_expr && !if_expr->success()` excludes | Source-pinned AST + exact root PRE facts. Existing 209 independent checks are not whole readiness |
| A10 | `:2622–2627` | Last action/executing duplicate-casting exclusion unless `cooldown_allow_casting_success` | Current foreground/cast identity, time_to_execute |
| A11 | `:2629` | All above passes → `action_ready()` true | Requires proof no skipped or virtual altered branch; **not equivalent to priority optimality** |

`action_t::target_ready` (`:2418–2433`) rejects sleeping/invulnerable/out-of-range targets. `select_target()` can mutate the original action target and invalidate caches; a separate instrumented re-evaluation could affect the simulation and is forbidden by this engineering contract.

## 4. Arcane Orb virtual spell effects are separate from READY

`arcane_orb_t::execute` at `sc_mage.cpp:2651–2663` can schedule Orb Mastery child events, then invoke inherited spell execution, `trigger_arcane_charge()`, `trigger_arcane_salvo()`. `impact` at `:2665–2678` conditionally triggers splinter events. These source-defined stages tell us **which** next-state values to model, but not how many, at what real PRE/POST tick, whether procs fired, or what the user pressed. Source effects must be replayed by a separate phase-aware deterministic reducer, never by an unverified name-based heuristic.

## 5. Facts currently retained and explicit unknowns

- Previous original Native A/B #42140591685: 2,121 select-sweep calls, 262 returned source APL root rows and 4,682 ready-call PRE events (actor count and mana observed internally, but old JSON receipts deliberately retained only a small sample).
- Hekili-informed source opener #42149094904 and leaf reconciliation #42152415986: 64 early returned rows have exact ready-root ID including 30 child-propagated; same-root actor PRE survives for **only 9** samples in those older receipts. No complete independent READY.
- **New successor (in verification):** Instead of new C++ method calls, retain full already instrumented actor/Mana PRE and selected root rows from one fresh original C++ replay. The separate `general_rotation_full_root_state_join_v1.py` binds per-action source IF AST to actual same-root `active_enemies` and `mana.pct`. Other operands (buff/talent/cooldown/charges/cast target/skill RNG branch) remain UNKNOWN.
- **Important source-evidence gap:** Merely observing the original Native success and all source input names does not prove the comprehensive method gates. Next candidate is passive stage-specific C++ original return-path instrumentation for the first physical spell / prior blockers, with no duplicate `ready()`, `action_ready()`, cooldown, cost or RNG methods.

## 6. Engineering acceptance / future gate

1. Full source rooted original PRE and source return evidence (new dedicated artifact) must be real C++ executed, A/B action sequence identical, source hashes/version pinned; no developer assumption enters the WCL blind lane.
2. A root IF condition is independently determinate only from **same physical READY root** facts and trusted source AST. Missing symbolic operands → UNKNOWN; a condition evaluated true ≠ full READY.
3. Complete READY may only be promoted after source code route (including virtual methods and short circuits) and independently collected PRE operands/branch receipts are closed; Hekili old `Core.lua` isn't proof of 2026 mechanics.
4. Entire General Rotation optimum requires ST/2T/AoE/build-specific hypothesis and WCL independent candidate lock/holdout; recorded Native action return is the simulation's choice only.
5. Game addon remains a tiny official API-limited own-cast recorder/UI; no Hekili live combat-state solver, protected action manipulation or Secret Value inference.

This is a **source-walk artifact** tied to the product goal, not a new encounter or NSRT plan. MAIN/FROZEN unchanged.
