# zRotationHelper — Reusable new-chat boot (Scope Lock V1)

You are continuing zRotationHelper after one or more handoffs. **Do not trust an old roadmap, a past assistant explanation or an old `LATEST_HANDOFF` over the current user-approved scope.**

**Mandatory read order:** `docs/PRODUCT_SCOPE_LOCK_V1.json` → `docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md` → `AGENTS.md` → `docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md` → `docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md` → current branch `LATEST_HANDOFF.json` → relevant Core Contract/Playbook and code/evidence. Check actual GitHub HEAD and CI; avoid treating historic PASS as current production PASS.

## Non-negotiable scope to restate before doing work

**Final product:** a correct, evidence-validated **General Rotation opener and IF/ELSE conditional spell-priority model** across ST / 2 targets / cleave / AoE and relevant builds, plus a **small target-dummy practice-feedback addon** (live only when supported/observable, otherwise post-session combat-log analysis). It must tell the user when/why an observed action deviates and how to correct it, with UNKNOWN where readiness/state is not observable.

**Research path:** SimC APL/profile as the initial conditional hypothesis → Warcraft Logs high-ranker state/action comparison and correction. Inside the WCL lane, keep independent blind numeric/structural discovery and candidate lock *before* exposure to SimC semantic answers; after lock compare, use Blizzard mechanic truth and optional selective counterfactual/holdout. APL is a hypothesis, WCL frequency is not mandatory optimality.

**OUT OF SCOPE until a fresh user direction:** encounter-specific boss plans, raid execution assistant, NSRT, HTML raid timeline, boss guide exports. Real raid logs can still serve as general target-count/opener evidence.

**Engine-first:** fresh legitimate data collection, reproducible snapshots/replay and generic rules matter more than restoring legacy files. Never let old MAIN snapshot restoration become a prerequisite; preserve FROZEN evidence without assigning it new authority.

**Execution safeguards:** Strict PRE only `timestamp < decision t`; unknown readiness stays UNKNOWN; addon respects Blizzard API restrictions; no hardcoding boss-specific semantics; don't invent live test PASS. MAIN alone promotes shared CURRENT_STATE, pointers and FROZEN. Seq578 FAILED_QUARANTINED / Seq637 UNKNOWN unless a separately authorized verified successor changes them.

## At the end of *every* chat

1. Write/update a branch-local `LATEST_HANDOFF.json` with a **complete unchanged `scope_continuity.policy_snapshot`** from the canonical lock; include `policy_id`, Git blob, true `generation` increment and previous handoff SHA256.
2. Keep product exact-next separate from this chat's exact-next; product next must concern General Rotation opener/priority or dummy practice feedback.
3. Run `python tools/governance/validate_scope_continuity_v1.py --validate` and `--self-test`; record actual PASS/FAIL and unverified surfaces.
4. Include this boot text or its stable link plus the policy snapshot for the next chat. If an inherited handoff drops scope, **fail closed** and restore from the canonical lock, not from stale raid notes.
5. Do not overwrite historical handoffs or freeze prior evidence to make the latest version look consistent.

The scope policy ID is `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`. An explicit later user policy change is the only normal way to supersede it; give the new policy a new ID and describe the migration.
