# zRotationHelper — CURRENT USER-APPROVED PRODUCT GOAL

**Official user-declared scope (2026-11-02):** Complete a verified **General Rotation OPENER and conditional IF/ELSE spell priority** for ST, 2-target, cleave and AoE; deliver a **lightweight target dummy practice feedback** addon/analyzer. Prefer truthful live feedback if Blizzard supported APIs allow it; otherwise use post-session combat-log analysis. Unobserved state is UNKNOWN.

**Research order:** **SimC APL/profile** initial rotation hypothesis → independent **WCL high-ranker** state/action verification and correction → validated General Rotation model. Preserve WCL blind candidate lock before injecting SimC-derived answers.

**OUT OF SCOPE:** boss/encounter-specific raid execution plans, live raid assistant, NSRT, HTML raid timelines, boss guide outputs. Historic raid logs can serve general rotation target-count and opener validation.

**Every new chat / every handoff MUST read, inherit, and validate:**
1. [Canonical machine-readable scope lock](docs/PRODUCT_SCOPE_LOCK_V1.json)
2. [Full product scope declaration](docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md)
3. [Agent instructions](AGENTS.md) and [Engine-First Charter](docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md)
4. [Handoff continuity protocol](docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md) and [New chat boot prompt](handoff/NEW_CHAT_BOOT_PROMPT.md)
   - [Parallel Workstream contract (2026-11-02 scope-aligned)](docs/PARALLEL_WORKSTREAM_AND_MERGE_CONTRACT.md) controls branch ownership, never expands the product scope.
5. The task's **current actual branch** latest handoff, with full `scope_continuity.policy_snapshot`.

The policy ID is `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`. Simulated five-hop inheritance is a test, not five real chat handoffs. For a policy check on a docs-only checkout use:

```bash
python tools/governance/validate_scope_continuity_v1.py --validate --self-test --handoff handoff/HANDOFF_TEMPLATE_V1.json
```

This default-branch documentation anchor is **not** a gameplay-ready codebase or a promotion of old FROZEN/MAIN production pointers. Engine code and source validation reside in separate development branches. Only MAIN promotes shared product state; a future explicit user declaration is needed to supersede this final product scope.
