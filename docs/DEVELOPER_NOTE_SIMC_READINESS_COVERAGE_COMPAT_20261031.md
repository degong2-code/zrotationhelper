# Readiness Source Coverage — MAIN compatibility review (2026-10-31)

Owner: BR-SIMC-APL-BOOTSTRAP. Research hypothesis, not gameplay authority.

## Verified environment and evidence

Research code commit a1629b3373eb1f47124e14cb133b75796eee23a5.
Offline CI run 41088639687: SUCCESS for Python 3.12 and 3.14.
No new Native C++ run and no live WCL/Blizzard API. Prior pinned
official SimC 710c2408bfd3ae4df71b8cd55cdf01f63fd6c926
and V7 actual Native run 41084262760 remain previous evidence.
READY certified 0/90; gameplay rules promoted 0.

Inspected exact Git source and blob identities:
- tools/research/simc_apl_readiness_provider.py
  e59d2ea46455fc3e764daddd0abc3a8b6cce4c0c:
  requires eight MANDATORY dimensions; each permits ALL/ANY
  scalar constant predicates or source-evidenced NOT_APPLICABLE.
  Extra ninth dimension raises UNRECOGNIZED_READINESS_DIMENSION.
  Does not itself verify whether declared dimensions cover every
  source-required class/spell readiness gate.
- 02_SOURCE/runtime/raid_dps/specs/protocol.py
  605dfdc8cd76d0f3a8d9d811521ce56d49131cd:
  SpecAdapter offers action_families, state_features, action_overrides,
  frozen_evidence_ids and known_masks. It does not declare
  source-complete per-action readiness requirements.
- 02_SOURCE/runtime/raid_dps/core/behavioral_evaluator.py
  cee6a06cad8836e04d0a585f15e0ff3c60fbf6c2:
  consumes externally produced ternary readiness; excludes UNKNOWN
  from observed mismatch denominator, not a readiness producer.
- 02_SOURCE/runtime/raid_dps/core/general_rotation_evaluator.py
  7289dd2719a25e4cecf9be7cba700f21d69ac893:
  evaluates externally supplied rules, not runtime skill readiness.
- docs/BR_SIMC_MINIMUM_READINESS_SOURCE_GAP_20261031.json
  e437da47d632737c9eacc3901c945590aff0308b:
  two source-pinned examples only, Fury Rampage and Havoc Felblade.
  The source requirements are pinned-SimC hypotheses, not current
  Retail Blizzard mechanic verification.

## Actual tested compatibility findings (SYNTHETIC ONLY)

Added tools/research/simc_readiness_source_coverage_compat.py,
with tools/ci_offline.py integration. It invokes the UNMODIFIED
existing readiness provider using synthetic STRICT PRE events and
audits the pinned source manifest's declared extra gate IDs. This
is a contract coverage audit, NOT a second readiness engine.

1. All eight explicitly declared synthetic common feature checks PASS.
   Current provider returns READY, empirical_authority NOT_VERIFIED,
   EVEN WHEN source-required extra gates are omitted from policy.
   This is expected under an incomplete policy; it is unsafe to
   interpret as actual action readiness.
2. A ninth dimension is rejected, as specified.
3. SOME extra gates CAN fit existing dimensions. An explicit second
   shared-cooldown predicate in an existing cooldown dimension:
   absent PRE -> UNKNOWN, false -> NOT_READY, true -> research-only
   READY, same-time only -> UNKNOWN.
   Therefore adding a ninth dimension is NOT automatically required
   for every spec-specific condition. Exhaustive obligation
   completeness and source provenance are the actual gaps.
4. Provider predicates compare a feature against a numeric constant;
   direct feature-to-feature comparison of resource and a dynamic
   actual spell cost is unsupported. Avoid guessing a static cost
   from source APL IF threshold. Derived affordability needs source
   mechanic + independently observed timestamped inputs.
5. The research-only source completeness checker rejects a missing
   declared gate (BLOCKED_MISSING_SOURCE_GATES), unknown gate IDs,
   tampered source inventory, unauthorized READY claims and
   mismatched canonical JSON SHA. Even complete declarations remain
   DECLARED_ONLY_LIVE_READINESS_STILL_UNKNOWN; ZERO READY certified.
   Not all sources or spell readiness rules have been inventoried.

## Minimal MAIN-owned integration proposal (NOT applied)

An authorized SpecAdapter or equivalent semantic layer declares
per-action source requirements, numeric game action identity,
build/profile, and mechanic provenance. The generic policy compiler
checks ALL applicable source-required gates have verified mappings,
including evidence-backed nonapplicability. Missing, unobservable or
future/same-time features must not become READY.

Reuse current eight-dimension readiness provider for actual common
feature checks. Fold source-specific gates into existing dimensions
only when grouping/semantics are equivalent. For truly orthogonal
conditions, MAIN may approve one generic data-driven supplementary
gate list and small ternary combiner; avoid a parallel readiness
engine. Source-derived dynamic cost must be traceable to the actual
build/buff/talent and source timestamp. Spec-specific mechanics stay
in SpecAdapter, not generic engine code.

Required regression cases for MAIN: (a) missing extra gate blocks READY,
(b) observed false extra gate does not become READY, (c) same-time/future
state cannot satisfy readiness, (d) dynamic cost and ability identity
are build-pinned, (e) unchanged source-complete eight-dimension policy
retains prior behavior, (f) UNKNOWN excluded from match denominator.

No leakage into WCL blind lane before candidate lock. Only the V8
semantic-free blind observability request may be sent to WCL owner.
Post-lock comparison uses independent WCL STRICT PRE then Blizzard
mechanics and proportionate holdout/counterfactual.

## Authority and next

Branch cannot modify shared SpecAdapter protocol, MAIN current
state or General Rotation baseline. MAIN work/runtime authority
remains UNKNOWN. GitHub main pointer is historical, not validated
MAIN product state. Seq578/FROZEN unchanged; Seq637 UNKNOWN.

cross_branch_dependency: MAIN needs to provide/approve source-complete
per-action readiness policy and SpecAdapter compatibility, approved
CURRENT_STATE and runtime/active manifest.

cross_branch_dependency: WCL owner needs independently locked
numeric/structural candidates and PRE/UNKNOWN coverage, with no
SimC action/threshold leakage before lock.

No PyCharm execution or downloadable Python file delivered.
