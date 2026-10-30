# BR-SIMC-APL-BOOTSTRAP — branch handoff V9 (2026-10-31)

Status: BRANCH-ONLY source/readiness compatibility research.
V9 succeeds V8 for continuity. Neither MAIN, global LATEST_HANDOFF,
CURRENT_STATE, approved Runtime/Manifest, General Rotation baseline,
canonical registry, production pointer, Seq578 nor FROZEN changed.
Seq637 UNKNOWN.

## Read order

1. This V9 handoff and the branch-specific LATEST_HANDOFF.json.
2. docs/DEVELOPER_NOTE_SIMC_READINESS_COVERAGE_COMPAT_20261031.md.
3. tools/research/simc_readiness_source_coverage_compat.py
   plus the V8 source obligations JSON.
4. V8 and V7 branch handoffs and pinned Native evidence.
5. Project authoritative dual-lane Core Contract and successor
   Playbook; Parallel Workstream Contract. Separately verify the
   approved MAIN state/Runtime, not the GitHub main commit alone.

## Actual new work and validation

Research code commit:
a1629b3373eb1f47124e14cb133b75796eee23a5.
Python 3.12/3.14 offline Actions 41088639687: both SUCCESS.
New branch-only research audit module checks source-extra-gate
declaration completeness and demonstrates actual unmodified
existing readiness provider behavior with SYNTHETIC STRICT PRE.
No shared provider or SpecAdapter changed, no new Native build,
no WCL API or current retail mechanic validation.

Discovered nuanced contract gap: current provider's eight mandatory
readiness dimensions do not ensure their source requirements are
complete; eight synthetic observed fields can produce research
READY even if source-required specialized gates are undeclared.
A ninth dimension is rejected; some extra source predicates can
already be folded into an existing dimension, if semantically valid.
Dynamic comparator to another feature such as actual cost is not
supported. MAIN must approve a source-completeness interface,
not necessarily indiscriminately add ninth or tenth dimensions.

Existing SpecAdapter protocol does NOT expose per-action
source-complete readiness obligations. Existing behavioral
evaluator already expects externally supplied ternary readiness
and excludes UNKNOWN; no reason to duplicate it.

Prior fixed official SimC:
simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926.
V7 Native run 41084262760 SUCCESS with Fury and Havoc:
266 bare resource evals, 179 directly within original IF,
82 variable action, 5 UNKNOWN; not READY certifications.
Ready 0/90 and gameplay General Rotation rules promoted 0.
Retained two-profile marker artifact ID 12990129697 expires
2026-11-06T15:54:14Z UTC. Earlier failed Native run
41082893641 remains FAIL, never re-labeled PASS.

## Next steps and ownership

Product exact next: MAIN-owned per-action source completeness
contract that reuses the present eight-dimension provider; extra
source obligations missing or unknown must prevent playable READY.
Blizzard mechanic verification and true numeric ability/build
identity are still required. WCL blind numeric discovery and
candidate lock MUST precede SimC cross-lane reconciliation.

Session exact next: deliver this compatibility note to MAIN for
review when an authorized MAIN context is available. Until then,
branch-local work may assess precise action/ability numeric identity
and source-backed observation coverage without leaking SimC
answers to the blind WCL owner or changing shared semantics.
No new full Native build unless user-facing impact justifies it.

cross_branch_dependency: MAIN needs approved CURRENT_STATE,
active manifest, Runtime/fingerprint and SpecAdapter readiness
coverage interface compatibility approval.
cross_branch_dependency: WCL owner needs candidate-locked independent
numeric evidence and Strict PRE readiness/UNKNOWN accounting.

No user local actions; no downloadable .py provided.
