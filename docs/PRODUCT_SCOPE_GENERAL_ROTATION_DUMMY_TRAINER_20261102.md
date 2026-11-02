# zRotationHelper — Official product-scope change: General Rotation + Dummy Trainer

**User-declared effective date: 2026-11-02**
**Fixed policy ID:** `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`
**Machine-readable lock:** [PRODUCT_SCOPE_LOCK_V1.json](PRODUCT_SCOPE_LOCK_V1.json)
**Handoff rule:** [HANDOFF_CONTINUITY_PROTOCOL_V1.md](HANDOFF_CONTINUITY_PROTOCOL_V1.md). All future handoffs carry the full policy snapshot, not only a link.  
**Change type:** Explicit product objective and roadmap override (user-approved).  
**Repository state:** Recorded as branch-local scope proposal. Shared MAIN pointer, archived/FROZEN evidence, existing run states and frozen contracts are NOT mutated; MAIN is the integration/promotion owner.

## A. New final product objective

**Complete the General Rotation opener and conditional spell-priority model, and help a user practice that rotation correctly on a target dummy.**

The goal is NOT to output a raid execution plan. Do not describe a Raid Rotation Helper, encounter-specific boss plan, NSRT output, boss-phase timer or raid live recommendation as a required deliverable or an acceptance criterion without a fresh user authorization.

### In scope

1. For each specialization/build and current patch, derive the **General Rotation**: opener/pre-pull sequence where applicable, conditional priorities, single target, 2-target/cleave, AoE and target-count breakpoints, resources, procs, buffs/debuffs, cooldowns/charges, replacement actions, fight-remains/execute if materially generalizable.
2. Research sequence: **SimC APL/profile as initial baseline/hypothesis** → **WCL high-performing player verification and correction** → independently validated IF/ELSE General Rotation. WCL independent numeric/structural candidate lock remains an internal scientific safeguard: do not inject SimC semantic answers into the blind WCL discovery before lock. Replay, compare match/conflict/missing/unknown, reconcile Blizzard mechanics; escalate ambiguity to selective counterfactual/holdout proportionally to decision impact.
3. WCL real raid logs MAY serve as empirical fixtures for general ST, 2-target, AoE, opener, buff/resource and target-breakpoint verification, but **do not derive encounter-specific boss plans** as a product output.
4. A **lightweight target-dummy practice addon**: user enables the addon, attacks the target dummy, and receives actionable feedback about opener or priority mistakes. Two acceptable evidence modes, selected after real API feasibility testing:
   - **Live partial feedback:** collect permissible own-cast and accessible state information while practicing; flag only errors supported by observable state. It must not claim to know hidden readiness/buffs/cooldowns.
   - **Post-session analysis:** ingest actual combat logging data, reconstruct Strict PRE and use the same General Rotation model to explain exactly which decision was questionable, why, and what action should replace it. Feedback can be shown in a lightweight UI/in-game view when technically viable; an external analyzer/import workflow may be used where the WoW addon sandbox makes direct reading impossible.
5. User-facing feedback should be specific: time/order, skill icon/localized name, observed state, actual action, rule/alternative, short correction and evidence confidence. Unknown state yields **insufficient information**, never a fabricated mistake.

### Explicitly out of scope (until new user direction)

- Encounter Rotation Plan / boss phase/raid-specific deviation output
- Live raid decision assistant or boss strategy assistant
- NSRT conversion, HTML raid timeline or other raid guide/export adapters
- Requiring raid-ready optimality or encounter plan promotion for the product to be considered finished

Legacy encounter artifacts may remain archived evidence and are not deleted, but must NOT drive active roadmap or block general-rotation development.

## B. Recommended implementation architecture

```text
Official Blizzard spell/patch identity and mechanic truth
                   +
SimC APL/profile hypothesis bootstrap
                   |
                  base
                   |
WCL high-ranker raw log collection -> normalization -> Strict PRE/readiness
                   |                 |
                   +- independent blind candidate lock (no SimC leakage)
                   |                 |
                   +------ post-lock hypothesis replay/comparison ------+
                                                                        |
                         validated conditional General Rotation + opener
                                                                        |
                                    canonical neutral Rotation IR
                                                                        |
                   target-dummy practice evaluator (same IR)
                                     /                         \
                         permitted live own-cast data     post-session combat log
                                     \                         /
                                        small feedback UI
```

The analytical/research engine is independently testable and does not require the addon. The addon is deliberately lightweight and does not reimplement the research engine.

## C. Current Retail addon feasibility boundary (as researched 2026-11-02)

- Blizzard's Midnight addon restrictions remove `COMBAT_LOG_EVENT_UNFILTERED` / `COMBAT_LOG_EVENT` access for ordinary addons and introduce *secret* combat values. Do NOT design a solution around bypassing these restrictions. Official explanation: https://news.blizzard.com/en-us/article/24246290/combat-philosophy-and-addon-disarmament-in-midnight
- Own-player spellcast event `UNIT_SPELLCAST_SUCCEEDED` is an API candidate for collecting spell IDs. Whether the target-dummy environment permits sufficiently rich state for precise *live* priority feedback must be tested in a real client. API reference: https://warcraft.wiki.gg/wiki/UNIT_SPELLCAST_SUCCEEDED
- Combat logs can be written to disk using `/combatlog`, but WoW's in-game Lua addon cannot simply open an arbitrary external log file. Analyze via an **offline companion/import workflow** if needed; in-game SavedVariables persist on logout or UI reload and are not a live arbitrary-file I/O bridge. References: https://www.warcraftlogs.com/help/start and https://warcraft.wiki.gg/wiki/Saved_Variables
- Post-combat log file flushing may be delayed, especially for solo target-dummy practice. Measure actual delay in a client before promising immediate feedback. Warcraft Logs documents delayed writes for dummy content: https://www.warcraftlogs.com/help/start
- Restrict telemetry collection to legitimate supported APIs; do not build a hidden desktop overlay, injected addon hook or disallowed combat data workaround.
- **Implementation verdict:** real-time action-sequence feedback is *plausible but unproven*. Full conditional priority judgment in real time is NOT yet proven. A post-session analysis path is the accuracy fallback.

## D. Acceptance criteria, not arbitrary CI counts

- The General Rotation explicitly models a correct **opener** as well as the post-opener IF/ELSE priority decision with specialization/build/target-count transitions.
- Strict PRE, action availability and observability prevent false mistakes; ambiguous states produce UNKNOWN.
- Independent WCL analysis checks and corrects the SimC baseline; blind candidate lock precedes injection of SimC answers. Neither ranking frequency nor SimC alone proves optimality.
- The exact same frozen/validated rule IR can evaluate synthetic fixture + fresh combat log + second specialization without per-spec generic hard-coding.
- Target-dummy practice: begin → act → gather supported data → identify supported mistakes → show *what, why, and how to improve* → practice again. Target dummy is the first supported user experience.
- Cold-start new data acquisition and deterministic replay must work independently of historic archived files.
- No real live API / client / gameplay success may be claimed before it is actually tested.

## E. Immediate development plan

1. Keep the existing Fresh-WCL V1 collector/replay as a **building block**, not as a completed general research engine.
2. Prioritize **SimC APL/profile parser → conditional baseline IR (including opener)**; parallelize independent WCL sample/discovery only where it shortens critical path without contaminating blind candidate lock.
3. Add General Rotation decision replay/evaluator that outputs OBSERVED / rule-match / conflict / UNKNOWN and reasons.
4. Build an API-capability-only **tiny dummy telemetry proof** with own-cast and state visibility matrix; avoid constructing a full addon before checking permissible evidence.
5. Implement first post-session practice feedback loop from a known fresh log/fixture; integrate optional live warnings only for proven observable situations.
6. Test another specialization/target-count setting and prove generic reuse.

## F. Mandatory checkpoint question

**“Does this change help accurately complete the general opener and IF/ELSE priority model or help the user improve their target-dummy practice using supported evidence?”**

If not, do not put it on the active critical path. Preserve older research evidence without making it the reason development stops.
