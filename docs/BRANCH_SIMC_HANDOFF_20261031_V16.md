# BR-SIMC-APL-BOOTSTRAP — V16 MAIN compatibility decision handoff

Date: 2026-10-31 KST. **Branch-only merge candidate; not MAIN approval or promotion.**

## Read order

1. `_UPLOAD_TO_CHATGPT/branches/BR-SIMC-APL-BOOTSTRAP/LATEST_HANDOFF.json`
2. `docs/BRANCH_BR-SIMC-APL-BOOTSTRAP_MERGE_HANDOFF_20261031.json` — the single MAIN-facing structured decision/revalidation packet.
3. Prior V15 code-validation handoff, V14 corrected portable aggregate, V12 archived source rows, V9 readiness gap, V8 blind-safe observability request.
4. Independently restore authorized MAIN CURRENT_STATE, Runtime/active Manifest and frozen contracts before any shared integration.

## Outcome

**Ready to review, not eligible to promote.** The requested MAIN review is now a concrete four-decision, five-targeted-regression packet. No new readiness engine, WCL calls, native SimC build, or shared code edits.

| Scope | Status |
| --- | --- |
| Existing SpecAdapter numeric family/replacement | Available |
| Existing strict PRE latest < decision time | Available at state-provider level |
| Existing SimC eight-dimension research-only readiness | Available, source requirement completeness missing |
| Existing post-lock SimC/WCL research reconciliation | Available, empirical independence unverified |
| MAIN source-complete readiness/ability-ID mapping approval | BLOCKED |
| Independent WCL numeric lock + holdout | NOT PROVIDED IN THIS BRANCH |
| Live Retail client actionbar / WCL cast identity | UNKNOWN |
| Production gameplay/READY | **0 promoted** |

MAIN decisions are precisely:
M1. Where to version per-action, build-specific **exhaustive source gate obligations**, and block READY when required gates are missing.
M2. How to certify numeric **SimC action object ↔ Retail game ability ↔ WCL CAST** relations, including many-to-many parent/child/proc/replacement.
M3. How to supply evidence-backed Strict PRE and dynamic affordability (talent/buff/build), without assuming APL IF resource threshold is cost.
M4. Which approved current-state/Runtime/frozen baseline and merge owner applies.

Recommended minimal design: **reuse** existing readiness evaluator and SpecAdapter numeric identities, add a versioned source-gate coverage/identity *data record* in MAIN-approved semantic layer, and require independent live producer provenance. Do not insert a ninth hardcoded specialization gate into generic engine or invent a parallel readiness system.

## Explicit self-validation

- Verified prior V15 source commit `6da1ea068ad93862f4b9973cf6ea8d639833e355`, CI `41105867712` SUCCESS Python 3.12/3.14.
- Verified V15 documentation commit `f0712ed025787623083a1c795296037d92a67ca2`, CI `41106200589` SUCCESS Python 3.12/3.14.
- Compared Git blob SHA of existing SpecAdapter protocol, behavioral/strict-PRE evaluator, SimC readiness provider and existing reconciler.
- Verified archived Native source-only IF total `806 + 1369 = 2175` and corrected Fury/Havoc positive source-ID summaries `343 + 463 = 806`. Legacy V12 portable `positive_ids` remains INVALID, original rows unchanged.
- V16 decision packet asserts all four MAIN decisions remain NOT_APPROVED, five regressions remain MAIN/WCL NOT_RUN, no client ID/READY/rule promotion and exactly one WCL-safe pre-lock transfer artifact.
- Exact approved MAIN authoritative source/Runtime: **UNKNOWN**. GitHub `main` HEAD is only an observed Git source pointer, not proof of production authority.
- V16 GitHub document CI: record only after the new commit has actually completed.

## Owner contracts

**Before WCL lock**, send only `docs/BR_WCL_BLIND_SAFE_OBSERVABILITY_REQUEST_20261031.md` to its owner; this merge handoff contains SimC-specific evidence and must not be shared with blind discovery.

`cross_branch_dependency: MAIN needs to approve SpecAdapter source completeness and numeric identity evidence contracts, check approved Runtime/CURRENT_STATE and run focused compatibility validations.`

`cross_branch_dependency: WCL discovery owner needs to deliver independent numeric candidate+threshold lock, raw provenance, discovery/holdout identity and Strict PRE/UNKNOWN evidence before post-lock SimC comparison.`

Seq578 / FROZEN / global pointer and shared authoritative state remain unchanged. Seq637 unknown. Local PyCharm action **NONE**.

Next for branch: **stop expanding synthetic guards until MAIN decision or independent WCL lock becomes available**. If approval inputs remain absent, report the dependency rather than create additional speculative tests.
