# zRotationHelper — Development Agent Instructions (branch-local proposal)

**Read first:** [Engine-First / Reproducible Research Charter](docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md).

## Non-negotiable product objective

Build a **reproducible, generic World of Warcraft Retail rotation research engine**, not a museum of historic scripts, hashes and snapshots. Existing source/evidence is useful but must not become a prerequisite that prevents new development. The ability to acquire fresh legitimate data, replay it, discover conditional decisions, validate them, and expand across specializations and encounters is the product.

## How to prioritize work

1. Prefer an executable **fresh-data E2E vertical slice** over repeated historic restoration or superficial CI pass counts.
2. Treat new WCL collection as a **test of the engine**: cold start, identity, snapshot, checkpoint/resume, deterministic replay, strict PRE, observability and independent holdout.
3. Implement two separate lanes: **SimC APL/profile → semantic hypothesis bootstrap** and **blind WCL numeric/structural discovery → Strict PRE/readiness → candidate lock**. No SimC-derived labels or answers may contaminate the WCL blind lane before candidate lock. Compare lanes afterward and escalate important ambiguity selectively.
4. Preserve **truth and evidence levels**: UNKNOWN readiness remains UNKNOWN; repetition does not prove priority, optimality or causality. For decisions, use only transitions with `timestamp < action_timestamp`. Never leak future/same-timestamp state.
5. Simplify/replace old implementation when it impedes a working generic engine. Do not reuse historical MAIN entrypoints with side effects merely to preserve compatibility. Keep original FROZEN evidence immutable; new claims belong in successor evidence with appropriate validation.
6. Do not casually modify shared authority. **MAIN alone** promotes CURRENT_STATE, contracts, registry, General Rotation baseline, active manifest/pointer and FROZEN. Branches produce validated candidates and merge handoff only.
7. At every task ask: **Does this make the engine more capable of re-collecting data and making a correct, generalizable user-facing rotation decision?** If not, justify why it is necessary on the critical path.

**Current product direction:** Safe minimal development entrypoint → fresh WCL sample collection/snapshot → offline strict PRE and UNKNOWN replay → independent WCL candidate lock + SimC bootstrap → verified conditional General Rotation IR → encounter deviation and UI.

**Important distinction:** Historical inability to reproduce an original dataset may result from external WCL availability/log retention or patch changes. Separate these from engine defects.

**This file is a branch-local instruction proposal, not an authoritative MAIN promotion.** Consult the latest approved Runtime/Work State and project core contracts before any promotion or actual live production operation. Keep Seq578 FAILED_QUARANTINED and Seq637 UNKNOWN unless MAIN accepts new independent evidence.
