# Developer Note — Source-resolved bare resource expression semantics (2026-10-30)

**Owner:** research-only `work/github-ci-bootstrap`. This is a SimC-first hypothesis/semantic-bootstrap result, **not** a gameplay General Rotation promotion. MAIN `CURRENT_STATE`, canonical registry, active pointer, global `LATEST_HANDOFF.json`, FROZEN and Seq578 are unchanged. Seq637 remains UNKNOWN.

## Motivation: bridge the actual source gap, not invent a Native state mapping

The previous [Native resource semantic gap note](DEVELOPER_NOTE_SIMC_APL_NATIVE_RESOURCE_SEMANTIC_GAPS_20261030.md) and official four-profile coverage CI established 294 APL operand requirements, 90 distinct source action-readiness requirements, and four *lexical* bare resource candidates (`rage`, `rune`, `runic_power`, `fury`). Lexical similarity to native `resource_type_string()` did **not** previously prove how SimC evaluates those APL expressions. The right Exact Next was to trace the C++ parser path before binding an observed state.

## Actual pinned source resolution

Upstream is **exactly** `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`, not assumed current retail Blizzard truth.

- `engine/player/player.cpp` — `player_t::create_expression(expression_str)` first tries `create_resource_expression(expression_str)`. In `player_t::create_resource_expression`, the first dot-delimited token passes through `util::parse_resource_type`; when `splits.size() == 1`, it returns `make_ref_expr(expression_str, resources.current[r])`. This is an explicit C++ **current-value reference**, not resource percent, deficit, regeneration, or charge readiness. Other suffix forms follow different branches and are NOT covered by this bare-name proof.
- `engine/util/util.cpp` — `util::resource_type_string` identifies `rage`→`RESOURCE_RAGE`, `rune`→`RESOURCE_RUNE`, `runic_power`→`RESOURCE_RUNIC_POWER`, `fury`→`RESOURCE_FURY`, and `util::parse_resource_type` parses that resource label family.
- `engine/class_modules/sc_death_knight.cpp` — `death_knight_t::create_expression` has a **special dotted** `rune.time_to_*` branch gated on `splits.size() > 1`, then falls back to `player_t::create_expression`. Therefore **bare `rune` is not `rune.time_to_n`**: it follows the base current resource reference. The functional meaning/completeness of the rune subsystem and action availability still require separate validation.
- `engine/class_modules/sc_demon_hunter.cpp` — `demon_hunter_t::create_expression` has explicit custom expressions for other tokens but falls back to `player_t::create_expression` for bare `fury`. This is a constrained source static-path check, not a runtime-selected expression-value trace.
- `engine/class_modules/sc_warrior.cpp` — `warrior_t` inherits `parse_player_effects_t` and the inspected pinned source contains no `warrior_t::create_expression` override. Thus the bare `rage` candidate uses the generic player resource expression in this source fixture.

All source files are downloaded or read at the exact pinned upstream commit; C++ source SHA256 and function/control-flow anchors are checked, rather than relying on search snippets or the source token name alone.

## Implementation

- New `tools/research/simc_apl_native_resource_expression_proof.py` accepts the existing source-attributed `ZrotNativeResourceAplObservabilityGapAuditV1`, pinned util.cpp resource identity inventory, pinned player.cpp and optional pinned class module source. It checks exact SHA256 of each file, presence/uniqueness and order of the base C++ parser branch, source label→resource enum identity, class-specific bare-token interception and explicit fallback to player expressions.
- It emits one source-proof row per source APL candidate preserving the original APL references: enum, base current-value semantics, source file hashes, and the degree of class override evidence. It is intentionally a **read-only semantic evidence result**: `native_producer_semantic_value_link=NOT_VALIDATED_PER_DECISION`, `native_epoch_strict_pre_state=UNKNOWN`, `ability_readiness=UNKNOWN`, `general_rotation_promotion=false`.
- The generic module does not hardcode class/spec/ability names; the CI **fixture** selects the appropriate source class module for the official profiles. Negative synthetic cases reject a forged class intercept, source hash mismatch, nonexistent fallback, or fabricated Native binding.
- `.github/workflows/simc-public-source-coverage.yml` now runs the same source proof on all four pinned public MID2 APLs along with existing decision graph, raw event, source requirements and readiness fail-closed tests. It does **not** trigger a redundant Native C++ rebuild.

## Evidence and claim-strength ledger

**Official public SimC source CI:** [41064679658](https://github.com/degong2-code/zrotationhelper/actions/runs/41064679658) — **SUCCESS**. **Offline CI:** [41064679434](https://github.com/degong2-code/zrotationhelper/actions/runs/41064679434), Python 3.12 and Python 3.14 **SUCCESS**.

| Public specialization | Pinned source-resolved bare operands | Proven expression source path | Actually observed Native Strict PRE operand value | Action tokens READY-certified |
| --- | --- | --- | --- | ---: |
| Enhancement Shaman | none (0) | Not applicable | 0 | 0 / 24 |
| Fury Warrior | `rage` | `resources.current[RESOURCE_RAGE]` | 0 | 0 / 26 |
| Unholy Death Knight | `rune`, `runic_power` | `resources.current[RESOURCE_RUNE]`, `resources.current[RESOURCE_RUNIC_POWER]` | 0 | 0 / 21 |
| Havoc Demon Hunter | `fury` | `resources.current[RESOURCE_FURY]` | 0 | 0 / 19 |
| **Total** | **4 source-resolved expressions** | **4 static source semantics** | **0 certified per-decision operands** | **0 / 90** |

The previously validated Native source epoch/reset sequence [41059211056](https://github.com/degong2-code/zrotationhelper/actions/runs/41059211056) found 968 consistent current/max **diagnostic field** comparisons and 740 same-ms excluded fields across the four fixed profiles. This evidence proves some source-local native state consistency, **not** the actual evaluated APL expression for any source row. No automatic operand-to-Native feature binding was made. **Source expression identity is distinct from source event completeness, same-epoch state reconstruction, and readiness.**

## Verified and unverified

**Verified (source semantics, pinned C++ static scope):** the bare tokens named above resolve via the generic current-resource expression path in the inspected source and class-module fallback chain.

**Not verified:** true resource current for a given user-facing decision after every direct-write/regen event; entire resource transition coverage; whether the expression was evaluated at any specific Native foreground selection; action readiness (including rune availability, GCD, cooldown, charges, proc, target, talent, replacements and full APL control); independent WCL ranking decision evidence or current Blizzard mechanic correctness. Do not use `rune` source semantics as proof of readiness or assume priority from selected actions.

## Next proportionate work

1. Prove **source-to-producer runtime correspondence at the same Native selection** without borrowing a diagnostic snapshot as PRE: hook or inspect the actual evaluated expression `rage`/`rune`/`runic_power`/`fury` and independently compare with the source-epoch preceding resource observations, categorizing `match/conflict/same_timestamp/unknown`. If the last current value has no complete transition coverage, preserve UNKNOWN even if matching diagnostic fields.
2. Only after this producer/semantic alignment identify the first minimal readiness family required for a specific important IF/ELSE branch. Capture action availability separately, including other dimensions, and never silently convert unobserved readiness to NOT_READY.
3. Preserve WCL **independent blind discovery** until candidate lock; use the source semantics for SimC hypothesis/bootstrap and post-lock comparison, not to contaminate WCL discovery. Validate held-out specs/builds and Blizzard current-game authority proportional to user-facing claim strength.
4. MAIN alone may promote production General Rotation IR or encounter plans after compatibility review. No FROZEN/Seq/main changes in this increment.

**Local user action:** none. GitHub source + CI are the deliverables; no downloadable standalone Python file was handed out.

## Branch continuity reference (2026-10-30; documentation only)

For the current operational recovery order, evidence ledger and **distinct product vs session Exact Next**, read [BRANCH_SIMC_HANDOFF_20261030_V3.md](BRANCH_SIMC_HANDOFF_20261030_V3.md) as the branch-local successor to earlier branch V1/V2 notes. The minimal machine pointer is `_UPLOAD_TO_CHATGPT/branches/BR-SIMC-APL-BOOTSTRAP/LATEST_HANDOFF.json` (branch-local, **NOT** the MAIN global latest handoff). This cross-reference changes **no underlying static source proof, Native action/parity result, readiness state, or gameplay rule status**. All approved MAIN identity, active production file and Runtime boot requirements remain independently unverified / UNKNOWN until their actual authoritative bytes are checked. A fresh chat must report restoration, then **stop until the user writes “진행”**.
