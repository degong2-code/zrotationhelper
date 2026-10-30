# Pinned SimC bare-resource APL source-route audit — 2026-10-31

Branch: BR-SIMC-APL-BOOTSTRAP / work/github-ci-bootstrap. Scope: **source-only, not a new Native run**. No gameplay or MAIN promotion.

## Source and applicable evidence

- Pinned source: `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`.
- Official upstream Git blob SHAs: Unholy profile `3a94484f15b5fb8b454c05dbdfd78b799979560e`; Fury `3225992ed5b754ad5d61e8b785d9d859f1eed1be`; Havoc `9cab6566a655df9cf1d73bb92e7173ed1e708a25`.
- Native pinned execution `41075553050`, code SHA `45eceaa88835fe3c5deac2f8095763fd30f154f1`, binary SHA256 `0d234a886ceb5bb9b7addf642af311b2ad09dce60c7345dcbc90037a29d42dac`: 266 *bare-reference evaluations* recorded. No raw Native per-event log uploaded in that workflow.
- Original profile text and exported `save_actions` are different data artifacts: effective APL SHA from Native receipt is not the profile's source hash. A profile file line is a **source-location candidate**, NOT proven identity of a live evaluated APL row.

## Exact pinned public profile occurrences (bare tokens only)

| Spec | Profile source lines and APL lists | Bare resource tokens | Static reachability constraints |
|---|---|---|---|
| Unholy | 53,56 in `actions.aoe` (`epidemic`, `death_coil`) | `rune` | Root `actions` calls `aoe` only under `active_enemies>=3` (line 46). These expressions are also in branches of larger OR guards, which may short circuit. |
| Unholy | 73,74,75,79 in `actions.racials` (`arcane_pulse`, `arcane_torrent`, `bag_of_tricks`, `lights_judgment`) | `runic_power`, `rune` | Root `racials` call conditional at line 42; these actions may be skipped by ability availability or condition checks. |
| Fury | 65,75 in `actions.slayer` (`rampage`) | `rage` | Root `run_action_list,slayer` under talent+target gate (line 58); action readiness/earlier priority can skip evaluation. |
| Fury | 103 in `actions.thane`, 130 in `actions.thane_aoe` (`rampage`) | `rage` | Different root talents and enemy-count conditions (lines 60–61). |
| Fury | 156 in `actions.variables`, `variable,name=on_gcd_racials,value=...` | `rage` | Variable evaluation is a potential non-ability source of bare reference values. Root list calls `variables` at line 50. |
| Havoc | 47 in root `actions`, `pick_up_fragment,type=all,use_off_gcd=1,if=fury<=40` | `fury` | Explicit off-GCD option; a possible source of evaluations **outside** the existing FOREGROUND-only selection window. No runtime source owner recorded. |
| Havoc | 64 in root `actions`, `felblade,if=hero_tree.felscarred&fury<=100` | `fury` | Main action conditional, but actual evaluation also depends on action readiness and earlier priorities. |

Unholy `actions.single_target` (root call at line 47 under `active_enemies<3`) has `runic_power.deficit` conditions, for example lines 84–90. These **dotted** expressions are not the pinned source-proof bare `runic_power`. There are no bare `rune`/`runic_power` source occurrences in that list. This is a static source finding, not a runtime proof that active_enemies was 1 or that racials were unavailable.

## Upstream C++ control flow evidence

- `engine/action/action.cpp::action_t::action_ready` checks `ready()` (cooldown/resource/movement), target and further conditions *before* `if_expr->success()`; failure can prevent expression evaluation.
- `engine/action/action.cpp::call_action_list_t::action_ready` checks target, line cooldown and its own `if` condition before recursion.
- `engine/player/player.cpp::player_t::select_action` iterates lists, skips background/wait entries, calls `a->action_ready()`, and recursively enters `call_action_list` only if eligible.
- The same selection function uses a separate `execute_type::OFF_GCD` action list; the existing research `ZROT_NATIVE_SELECT_RESOURCE_BEGIN/END` selection window instruments only `select_action(...FOREGROUND)` [spelling clarification: `FOREGROUND`]. The outside-window Havoc pattern is consistent with, but does NOT prove, the off-GCD source-row hypothesis.
- Original `ZROT_NATIVE_APL_RESOURCE_EVAL_V1` records resource and source time/sequence/actor/epoch, **not** the action/APL owner, list ordinal, `if`/variable context, or execution type. The existing JSON2 pointer proof attaches source APL ordinal to *recorded actions*, not each independent expression evaluation. Temporal coincidence cannot bridge that missing identity.

## Inference vs observed outcome

Native Run `41075553050` reported:
- Unholy bare `rune` and `runic_power`: **0 evaluated**, cause NOT IDENTIFIED. Static AoE/racial gates explain a possible absence, not a certified actual cause.
- Fury `rage`: 137 evaluations inside exact foreground selection; 133 consistent with earlier partial producer observations and 4 same-time excluded. **Which of the five profile source rows actually evaluated remains UNKNOWN**.
- Havoc `fury`: 129 evaluations, 14 in foreground selection (13 partial producer matches, 1 same-time exclusion) and 115 outside it. **Off-GCD attribution remains a candidate, not an established mapping**.
- 146 partial matches DO NOT certify full resource transitions, per-source-row values, ability readiness, action priority, current retail gameplay or optimality.
- Strict PRE still requires source time **strictly** earlier than decision and correct source-generated reset epoch; same timestamp excluded. Missing readiness UNKNOWN, never NOT_READY.

## Evidence-based next decision

**Do not rerun an unchanged four-profile Native build.** Source-only review cannot resolve row ownership from the already uploaded summary because the original evaluator marker omits it and raw Native logs were not uploaded.

Smallest useful follow-up: a **source-pinned, reporter-only, action/variable evaluation-scope marker** that carries (i) actor/epoch/source sequence, (ii) exact owning `action_t::signature` pointer match to its owning APL `action_list` ordinal when available, (iii) evaluation context and execute type; envelope each original condition/variable evaluation without changing priority semantics or treating the marker as a PRE transition. Independently reparse raw provenance and reject ambiguous/nonadjacent ownership. Use one fixed build and narrowly selected Fury/Havoc fixtures; add Unholy multi-target/racial eligible fixture only if required to demonstrate bare expression reachability. Predeclare fixture/inputs and keep holdout independent. Claim only observed owner/partial producer consistency, not readiness or optimality.

Separate WCL blind lane remains untouched. MAIN must provide approved CURRENT_STATE/Work OS Runtime/global handoff/active manifest before any integration. FROZEN and Seq578 unchanged; Seq637 UNKNOWN.
