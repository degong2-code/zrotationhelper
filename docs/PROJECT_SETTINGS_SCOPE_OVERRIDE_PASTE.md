# zRotationHelper — Project Settings custom-instruction override (copy/paste candidate)

**Why this exists:** GitHub edits do **not** automatically change ChatGPT Project Settings → Instructions or Project Source attachments. The original Project Core Instructions still refer to Raid Rotation Helper / Encounter Rotation and NSRT as product outputs. Those sections must NOT quietly override the 2026-11-02 user-approved change when future chats restart. Only the user/project owner can update the ChatGPT Project Settings instructions directly.

## Put this block **at the top** of the existing Project Instructions (preserve the historical research/evidence safety constraints underneath)

> ### §0 — 2026-11-02 official user scope override (HIGHEST ACTIVE PRODUCT PRIORITY)
>
> The user's FINAL zRotationHelper goal is **a verified General Rotation OPENING sequence + conditional IF/ELSE spell-priority model**, covering general ST, 2-target/cleave, AoE, builds, buffs, resources, procs, cooldowns and replacement conditions. **A lightweight target-dummy practice analyzer/addon** is the second deliverable, helping users see which observed opener/priority action was wrong, why, and what action/condition should change. Support LIVE feedback only where Blizzard's legitimate addon APIs provide sufficient state; otherwise provide POST-SESSION analysis of recorded combat logs. Missing readiness/secret values must be UNKNOWN, not invented mistakes.
>
> The research flow is **SimC APL/profile baseline hypothesis first → WCL high-ranking player logs to verify, challenge and correct it → validated General Rotation**. Inside WCL verification, preserve **independent blind numeric/structural candidate discovery and candidate lock before exposure to SimC semantic answers**. Reconcile with Blizzard mechanics and use selective SimC counterfactual/holdout where the ambiguity impacts user rules. This is NOT a WCL-first replacement of SimC bootstrap.
>
> Encounter-specific boss Rotation Plans, live raid assistants, NSRT exports, HTML raid timelines and raid-guide outputs are explicitly **OUT OF CURRENT PRODUCT SCOPE**. Boss logs can be used as evidence of GENERAL target-count/opener situations, not to create boss-specific plans. Older instructions about encounter research or raid gameplay must be treated as HISTORICAL/INACTIVE product goals unless the user explicitly reauthorizes them.
>
> **Engine-first:** new legitimate data collection, cold start, replay, strict PRE, reproducibility and generalizable analysis matter more than restoring old files or legacy MAIN. Prior FROZEN evidence stays immutable; branch promotion and authoritative shared state remain MAIN-controlled.
>
> **EVERY NEW CHAT AND EVERY HANDOFF:** read `docs/PRODUCT_SCOPE_LOCK_V1.json`, `docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md`, `AGENTS.md`, `docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md` in `degong2-code/zrotationhelper`; carry the COMPLETE scope policy snapshot and policy ID `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`, and validate five-hop inheritance. Do NOT revive raid/NSRT goals via old handoffs.
>
> If any old Project Instruction section conflicts with §0 on final deliverables or roadmap, **§0 prevails**. The existing dual-lane rigor, WCL evidence uncertainty, STRICT PRE, source authority, no false PASS, FROZEN immutability and MAIN ownership rules stay valid.

## What I can and cannot mark complete

- GitHub feature branch scope policy, README, AGENTS, technical runbook headers, handoff snapshot, reusable boot, and scope CI: can be edited/verified here.
- ChatGPT Project Settings → Instructions: **requires user action outside this GitHub connection**, unless a dedicated Project Settings editor is made available. Never claim it was modified merely because this patch exists.
- Project Source copies of old Core Contract/Playbook: do not rewrite old frozen evidence; mark the new product scope as a higher-priority **user-approved product override**, not a hidden semantic change to the scientific contract.
