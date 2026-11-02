# zRotationHelper — Development Agent Instructions (branch-local proposal)

**REQUIRED AT EVERY CHAT AND EACH HANDOFF (scope lock ID `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`):** Read [machine-readable scope lock](docs/PRODUCT_SCOPE_LOCK_V1.json), [new-chat continuity protocol](docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md) and [reusable boot](handoff/NEW_CHAT_BOOT_PROMPT.md). Do not inherit historical encounter/raid goals from old handoffs. An explicit later user instruction is the only authority for changing final scope.

**Read first (newest user-approved product scope):** [General Rotation + Dummy Trainer Scope](docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md), then [Engine-First / Reproducible Research Charter](docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md).

## Non-negotiable product objective

Build a **reproducible, generic World of Warcraft Retail rotation research engine**, not a museum of historic scripts, hashes and snapshots. Existing source/evidence is useful but must not become a prerequisite that prevents new development. The ability to acquire fresh legitimate data, replay it, discover conditional decisions, validate them, and expand across specializations and general combat situations (ST, 2-target, AoE) is the product.

**Official scope override (user 2026-11-02):** The final output is a validated **General Rotation opener and IF/ELSE spell priority**, with a **lightweight target-dummy practice analyzer/addon** that flags observable rotation mistakes live when permitted, otherwise diagnoses from post-session logs. Raid encounter-specific rotation plans, live raid assist, NSRT and raid timeline exports are explicitly **OUT OF SCOPE** unless the user reauthorizes them. Real-time feedback must respect Midnight secret combat state and unavailable combat-log events; never infer unobserved readiness. The addon is a thin consumer of the verified research IR, not the engine itself.

## How to prioritize work

1. Prefer an executable **fresh-data E2E vertical slice** over repeated historic restoration or superficial CI pass counts.
2. Treat new WCL collection as a **test of the engine**: cold start, identity, snapshot, checkpoint/resume, deterministic replay, strict PRE, observability and independent holdout.
3. Implement two separate lanes: **SimC APL/profile → semantic hypothesis bootstrap** and **blind WCL numeric/structural discovery → Strict PRE/readiness → candidate lock**. No SimC-derived labels or answers may contaminate the WCL blind lane before candidate lock. Compare lanes afterward and escalate important ambiguity selectively.
4. Preserve **truth and evidence levels**: UNKNOWN readiness remains UNKNOWN; repetition does not prove priority, optimality or causality. For decisions, use only transitions with `timestamp < action_timestamp`. Never leak future/same-timestamp state.
5. Simplify/replace old implementation when it impedes a working generic engine. Do not reuse historical MAIN entrypoints with side effects merely to preserve compatibility. Keep original FROZEN evidence immutable; new claims belong in successor evidence with appropriate validation.
6. Do not casually modify shared authority. **MAIN alone** promotes CURRENT_STATE, contracts, registry, General Rotation baseline, active manifest/pointer and FROZEN. Branches produce validated candidates and merge handoff only.
7. At every task ask: **Does this make the engine more capable of re-collecting data and making a correct, generalizable user-facing rotation decision?** If not, justify why it is necessary on the critical path.

**Current product direction:** Safe independent data collection/replay → SimC APL conditional baseline + opener → WCL high-ranker independent blind validation/candidate lock → post-lock comparison and corrected General Rotation IF/ELSE IR → lightweight target-dummy practice evaluation (in-game only where supported, otherwise post-session log analysis). No encounter plan, NSRT or raid execution output.

**Important distinction:** Historical inability to reproduce an original dataset may result from external WCL availability/log retention or patch changes. Separate these from engine defects.

**Future handoffs must carry the exact full scope policy snapshot and pinned identity; run `python tools/governance/validate_scope_continuity_v1.py --validate --self-test` and maintain a true generation counter. Five simulated transitions are a test, not five completed handoffs.**

**This file is a branch-local instruction proposal, not an authoritative MAIN promotion.** Consult the latest approved Runtime/Work State and project core contracts before any promotion or actual live production operation. Keep Seq578 FAILED_QUARANTINED and Seq637 UNKNOWN unless MAIN accepts new independent evidence.
