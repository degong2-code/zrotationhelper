# Hekili architecture research reference — General Rotation + Dummy Trainer

**Branch-local design successor — 2026-11-06.** Owner: `BR-GR-ST2T-WCL-BLIND-20261102`. Product lock: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`. **NOT** a policy change, MAIN promotion, WoW runtime validation or an authorization to copy GPL/unknown-license source. Reference material for all future General Rotation IR, decision-explanation, SpecAdapter and dummy-trainer design reviews.

## 1. Evidence, authority and source pins

- Hekili source: https://github.com/Hekili/hekili at **`thewarwithin` commit `36daec382e6557fd57a263bbfb060856ef9fe9d8`** (GitHub source inspected with a connected read-only API on 2026-11-06). **Historical TWW 11.2.5 code, not current Retail 12.1.5-compatible runtime behavior.** Project README explicitly says Retail Hekili ended at the 12.0 Midnight prepatch, 2026-01-20: https://github.com/Hekili/hekili.
- Hekili `Core.lua` blob `118f1c9eee14f32bcf449ceb0b73e923b3da25f9` (2,318 lines); `Scripts.lua` `0ad5af73d39e64722d4f59bbbc6ad855f02769af` (2,198 lines); `State.lua` `6760efd89a3ef2e72e002a5e38a1a310d01677ce` (8,100 lines); `Classes.lua` `5405d93549b13ce1c8808633c22af63fc91dfc34`; `Targets.lua` `55b5ff58e5934865a77261f1caa37f9834abc017`; `Hekili.lua` `fb7f1695e1c16c39403dd75241de0f632847b67e`; `Events.lua` `66025e99b5b4370d45b6211b6cafb500c339c406`.
- Hekili SpecAdapter-like examples: `TheWarWithin/MageArcane.lua` blob `82ef9bccc032f88ba8cf5376ed50616df16f5672` and `TheWarWithin/WarriorFury.lua` blob `a9ab19dff4a24b87d9f6636e9d57d14720c24738`. **Old specialization data is not 2026 mechanic truth**; use pinned current SimC + Blizzard spell data instead.
- User-supplied **HekiLight v0.7.0** ZIP independently read locally: `HekiLight-v0.7.0(1).zip`, SHA256 `d0c8af119de9d0ebd34b50bda11a24cbe4a8c4cbafd8b1e1f4c6de320315fc0d`. Lua `HekiLight.lua`, `Settings.lua`, `Locale.lua` and `HekiLight.toc` inspected. This ZIP is a third-party implementation sample, **not** a Blizzard compliance certification.
- Useful public source: https://www.curseforge.com/wow/addons/hekili and https://github.com/Hekili/hekili ; policy limits are recorded separately in `RETAIL_ADDON_POLICY_CAPABILITY_GATE_20261106.md`.
- **License gate:** Treat external code as *research-only* until its exact version's copyright/license conditions are verified. The inspected Hekili repository root tree has no `LICENSE` file and GitHub repository metadata returned `license:null`; do NOT assert a verified GPL license from this snapshot. HekiLight ZIP contains `LICENSE` (actual contents can be consulted at integration). No verbatim adoption without explicit license review and MAIN approval. Prefer independent implementation of architectural ideas.

## 2. Source-derived architectural lessons and exact locations

| Module and source witness | What the old Hekili source actually does | Reusable design principle, not code |
|---|---|---|
| `Core.lua:695+` `GetPredictionFromAPL` | Iterates pack/list/action entries, checks known/enabled status, script condition, time-to-ready; `Core.lua:882-905` emits reject reasons, `:912+` treats `call_action_list`/`run_action_list` as control flow. | Make every *candidate* a structured evaluation trace, with one reason per gate and nested LIST/CALL/RUN route provenance. |
| `Core.lua:1444+` `GetNextPrediction`, `Core.lua:1625+`, `:1738+` | Recomputes recommendation and advances simulated state/time for subsequent predictions. | Use an **offline isolated state transition/replay engine** and branch-safe counterfactual probes only when required. Do not promise accurate multi-step advice in the in-game addon. |
| `Scripts.lua:349-410` `SimToLua`, `:426+` `SplitExpr`, `:790+` `RecheckExpr`, `:1043+` `Loadstring` | Translates SimC-like expressions into Lua and compiles/evaluates conditions. | Retain source-pinned **typed Python APL AST** and explicit operand provenance. Do **not** copy dynamic `loadstring` or assume semantic equivalence to pinned SimC C++. |
| `State.lua:97-101`, `:832+` cooldown state, `:1067+` aura state; `state.advance` calls from Core | Tracks resource/cooldown/buff/proc and future simulated state. | Isolate a `StateSnapshot` plus deterministic transition reducer, with per-field `OBSERVED/INFERRED/UNKNOWN` and timestamps, separate real vs hypothetical state. |
| `Classes.lua:138+`, `:210+`, `:232+`, `:379+`, `:410+` | Registers resources, talents, auras, class-specific state expressions/functions. `TheWarWithin/MageArcane.lua:33-49` and `WarriorFury.lua:36+` illustrate specialization modules. | Generic Engine consumes `SpecAdapter` declarative action identity, replacements and mechanic gates. Avoid hardcoding Fury/Arcane into Generic Core. |
| `Hekili.lua:202-257`, `:257-644` | Debug logs and bounded snapshots include target state, reasons and original choice. | Evidence-bounded `DecisionExplanationReceipt` with selected candidate, earlier rejected candidates, state provenance, unknown gaps, confidence and human-readable feedback. Snapshot **never** contains raw protected/secret state. |
| `Events.lua:158+` event registrations and update scheduling; Hekili wiki performance article | Multiple signals can trigger redundant refreshes. | Use **event-driven bounded own-cast collection** in the addon and **batch, cached deterministic analysis outside**. No 20Hz real-time combat decision engine. |
| `Targets.lua:361+` nameplate/count rules; `WarriorFury.lua:711+` combat log handler; `MageArcane.lua:789+` COMBAT_LOG_EVENT_UNFILTERED | Past in-game enemy counts and combat event interpretation underpin old logic. | **Historical / incompatible as live 12.1.5 data collection.** Offline WCL/file-based target reconstruction with Strict PRE; in-game unknown unless API-tested non-secret. |

## 3. Key Hekili insight: an actionable *why* engine

Do NOT convert a source APL list into a linear spell queue. It is a **nested, conditional ordered decision tree**.

For each decision:
1. **Source identity**: patch, spec, build, source APL line/hash, call stack and list, action variant/replacement, ST/2T/AoE context.
2. **Candidate iteration**: ordered candidate at source point, `VARIABLE` side effects and `CALL/RUN` routing distinct from executable abilities; preserve `wait_on_ready`, `background`, precombat, execute and pooling mechanics.
3. **Predicate evaluation**: `IF_TRUE/IF_FALSE/UNKNOWN` with operand name/value, provenance, timestamps. Missing readiness does not become false.
4. **Readiness evidence**: `INDEPENDENT_READY/INDEPENDENT_NOT_READY/UNKNOWN`. The original SimC `action_ready()` Boolean remains an **observed Native post-comparator** rather than independent readiness closure.
5. **Original-choice trace**: observed exact returned APL row and prior candidates from the *same* C++ select-sweep root; no timestamp-only join and no selection=optimality assertion.
6. **Research validation**: SimC-first hypothesis + WCL blind structural candidate lock → independent holdout → post-lock cross-check and Blizzard mechanics; conflicts and incomplete state remain explicit.
7. **User output**: for post-session dummy training, show actual, expected if verified, state, alternative action, reason, uncertainty. If comparing expected vs actual is not justified, show **UNKNOWN / needs more evidence**, not an error.

Illustrative **schema sketch, not a completed implementation**:

```json
{
  "decision_id": "source:spec:build:sweep",
  "candidate": {"apl_list": "example", "ordinal": 4, "type": "ACTION|CALL|RUN|VARIABLE", "spell_id": null},
  "operands": [{"symbol": "buff.example.up", "value": null, "observability": "UNKNOWN", "timestamp": null}],
  "predicate": "TRUE|FALSE|UNKNOWN",
  "readiness": "INDEPENDENT_READY|INDEPENDENT_NOT_READY|UNKNOWN",
  "native_action_ready_post": "TRUE|FALSE|NOT_OBSERVED",
  "source_choice_observed": "YES|NO|UNKNOWN",
  "prior_candidate_exclusion": "SOURCE_IF_FALSE|CERTIFIED_MECHANIC_NOT_READY|NATIVE_POST_FALSE_ONLY|BACKGROUND|CONTROL|UNKNOWN",
  "feedback_verdict": "MATCH|CONFLICT|UNKNOWN",
  "feedback_release_gate": "NO_GAMEPLAY_MISTAKE_CLAIM_BEFORE_STATE_AND_MODEL_VALIDATION"
}
```

## 4. HekiLight contrast: useful thin UI, NOT an independent rotation

- `HekiLight.lua:9-11`, `:718-739` use `C_AssistedCombat.GetNextCastSpell(false)` as Blizzard's **current** recommendation; `:910-925` fills additional icons from a registered spell list and cooldown filters. Thus secondary icons are **not a verified predicted temporal opener/sequence**.
- `HekiLight.lua:32-39` bounded `SavedVariables` session log; `HekiLight.toc` defines SavedVariables; useful UI/opt-in logging concept. No proof of a complete current WoW Lua API contract until game-client exercise.
- `HekiLight.lua:674-688` explicitly compares `C_Spell.GetSpellCooldown().duration` inside `pcall`, interpreting a secret-number comparison error as absence of cooldown. **Never transplant** this side-channel pattern into zRotationHelper. Expected failure is `UNKNOWN`, not a Boolean derived from an error.
- HekiLight UI spells/icons/localization/press feedback can guide small display, but **Blizzard Assisted Combat baseline is NOT the SimC/WCL-validated model**, and querying a current recommendation must not become a realtime custom rotation solver.
- Keep current research addon `addons/research/ZRotDummyProbe` separate; any approved UI successor is tiny, opt-in, cannot read arbitrary external files, no protected action calls, and never reasons from secret auras.

## 5. Product architecture successor (engine outside WoW)

```text
[Blizzard spell/patch facts]      [SimC pinned source profiles + Native execution]
                \                         /
           [Typed APL AST / SourceIdentity / SpecAdapter]
                                 |
          [Snapshot + Conditional Priority Evaluator]
               (source-trace reason ledger, UNKNOWN)
                                 |
[WCL original raw] -> [Strict PRE blind discovery/candidate LOCK]
                                 |
             [post-lock conflict / holdout / counterfactual]
                                 |
                [Validated General Rotation IR]
                                 |
      [Dummy Practice Evaluator, post-session default]
                      /                 \
     [Own-cast opt-in safe addon]     [external /combatlog/WCL parser]
                      \                 /
                 [Evidence-bound Feedback Receipt]
                                 |
            [Tiny localized icon / explanation UI]
```

**Strict PRE distinction:** For original SimC C++ source, a physical read directly before the call can share the same clock timestamp because its C++ execution order is proven. WCL transitions use strictly `event.timestamp < action.timestamp`; same-timestamp data never leaks into `state_at_action(t)`. The two provenance classes must remain different.

**Reuse already verified engine:** `simc_apl_semantic_ir_v2.py`, `general_rotation_time_scoped_priority_ir_v1.py`, root actor/mana PRE/replays, original IF bridge, and `general_rotation_original_selection_return_replay_v1.py`. Latest actual source selection evidence is **2,121 exact native sweeps, 262 root returned source rows; 209 matched original Native IF (not 209 DPS rules), zero independently closed full READY**. This is a foundation for typed decision reason ledgers, not a completed rotation or training feedback.

## 6. Validation and product acceptance

- Every reason code traced to source, actor/target, action state and proof; no spurious cross-action attribution.
- `UNKNOWN` is first-class for missing readiness, secret information, unverified target count, cooldown/proc, fight-remains.
- Native unmodified-versus-instrumented action sequence and causal call identity verified when instrumenting; only relevant changes re-run costly C++ E2E.
- SimC/WCL independence retained: never inject Hekili recommendation, guide or SimC answer before WCL blind candidate lock.
- At least one **real executable ability** opener and prior candidate exclusion demonstrated in ST and 2T; later AoE & different spec; WCL independent holdout; user feedback after evidence closure.
- **Do not** move full decision engine into WoW, claim live target-dummy support from old TWW source, or reinstate encounter-specific/NSRT roadmap.

**Linked successors:** `RETAIL_ADDON_POLICY_CAPABILITY_GATE_20261106.md` and `GENERAL_ROTATION_HEKILI_POLICY_ROADMAP_20261106.md`. Branch-only, not MAIN promotion.
