# zRotationHelper — Handoff Continuity Protocol (2026-11-02)

## Purpose

The user explicitly requires that the **final product objective survive five or more consecutive chat handoffs**. This protocol prevents old raid/encounter/NSRT roadmaps from silently becoming current, while preserving historical evidence and the MAIN-only promotion boundary.

## Read order — repeat on **EVERY** new chat, not only the first one

1. `docs/PRODUCT_SCOPE_LOCK_V1.json` — fixed policy ID, exact values and excluded deliverables.
2. `docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md` — authorized natural-language specification and feasible addon boundaries.
3. `AGENTS.md` → `docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md` — execution standards and no historical restoration dependency.
4. `_UPLOAD_TO_CHATGPT/branches/<CURRENT_BRANCH>/LATEST_HANDOFF.json` — operational progress, owner, evidence, blockers, exact next.
5. Research details / Core Contract / successor playbook, read as scientific guardrails. Older encounter-specific plans are historical, not a current product requirement.

If this chat has only a handoff text and cannot access GitHub, that handoff **must include the complete policy snapshot**, not merely a broken relative link. Ask for the source only if neither complete snapshot nor accessible policy exists. Do not reinterpret old files as newer product decisions.

## Product goal fixed until a later explicit user change

**SimC APL/profile conditional General Rotation hypothesis (including opener) → WCL high-ranker empirical validation and correction, protecting an independent blind WCL candidate lock → validated opener + ST/2-target/AoE IF/ELSE priority model → lightweight target-dummy practice feedback**.

For training, prefer truthful live feedback only if permitted WoW API observability supports the decision; otherwise support post-session combat-log analysis. Missing state implies **UNKNOWN**, never a confidently false error claim. Do not spend time on raid-specific encounter plan, NSRT, HTML raid timeline, live raid support, boss-specific cooldown planning or other old outputs.

## Required fields in every future latest handoff

`scope_continuity`:
- `policy_id`: unchanged `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`
- `policy_git_blob_sha1`: exact Git blob of read-first policy; does not substitute for checking contents.
- `policy_sha256`: exact SHA256 of the complete lock file; current approved value `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`. Fail if absent or mismatched.
- `policy_snapshot`: complete exact policy JSON copy, including goals, research order, out-of-scope, dummy feedback and engine-first rule.
- `generation`: integer 0+; increment by exactly 1 on each **actual** handoff.
- `parent_handoff_sha256`: actual prior handoff file byte digest, or `null` at first seeded generation.
- `carried_forward_at`: date.
- `scope_override`: `false`, unless the user **explicitly authorizes a newer scope** (then create a new policy and successor ID, do not rewrite this file as if historical).
- `new_user_scope_override_evidence`: `null` unless a true user authorization exists.

Also carry the current `product_exact_next` (within General Rotation/dummy training), active owner, validation state, blockers and unchanged Seq578/Seq637 evidence. Do not confuse a simulation of five handoffs with five real handoffs.

## Verification gate

Run:
```bash
python tools/governance/validate_scope_continuity_v1.py --validate
python tools/governance/validate_scope_continuity_v1.py --self-test
```

The gate must:
- compare policy against a pinned ID and fixed semantic invariants;
- confirm the README, agent guidance, scope note and charter point to the new product goal;
- fail when the current/latest handoff omits or alters the full policy snapshot;
- **simulate five sequential successors** and reject drift at each hop;
- fail if a successor reintroduces an excluded raid/NSRT deliverable;
- not mutate MAIN, historic handoffs, FROZEN or live WCL state.

Use `--next-handoff SOURCE.json DEST.json` to generate the next branch-local handoff while copying the policy and retaining parent linkage. Source or target must not be a global MAIN-only latest handoff unless operating with MAIN authority. No automatic promotion is performed.

## Historical files are never silently rewritten

Old `docs/BRANCH_SIMC_HANDOFF_*`, historical `_UPLOAD_TO_CHATGPT/branches/*/LATEST_HANDOFF.json` and original FROZEN records are evidence of their date, not current product targets. They stay intact. The *new* root README and this protocol explicitly supersede their stale proposed encounter/raid deliverables.

## MAIN / Project instructions limitation

Only MAIN approves shared `CURRENT_STATE`, product pointer, canonical scope promotion and global `LATEST_HANDOFF.json`. This GitHub branch is a durable **promotion candidate** with an independently testable handoff rule. The project Settings' top-level custom instructions and Project Sources are separate from GitHub: updating GitHub does not automatically change those account-level settings. MAIN owner should reconcile them with the same policy ID and wording before marking global promotion complete.
