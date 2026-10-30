# zRotationHelper — SimC research branch continuity V7 (2026-10-31)

Owner BR-SIMC-APL-BOOTSTRAP, branch work/github-ci-bootstrap.
Status BRANCH_VALIDATED actual narrow source evidence; NOT MAIN,
NOT gameplay MERGE_READY, NOT FROZEN.

## Read order and authority

1. This V7 branch handoff and its LATEST_HANDOFF.json pointer.
2. docs/DEVELOPER_NOTE_PINNED_NATIVE_DIRECT_IF_20261031.md (exact Native evidence).
3. docs/BRANCH_SIMC_HANDOFF_20261031_V6.md and its source owner proof,
   then V5 source-route audit as historical baseline.
4. Project Core Instructions + the authoritative
   ROTATION_RESEARCH_SYSTEM_CORE_CONTRACT_V1.md dual-lane flow,
   GENERAL_ROTATION_PLAYBOOK_DUAL_LANE_SUCCESSOR_PROPOSAL_v2.md,
   PARALLEL_WORKSTREAM_AND_MERGE_CONTRACT.md.
5. Separate authenticated MAIN-approved CURRENT_STATE/global LATEST_HANDOFF,
   active manifest and Work OS Runtime Manifest/Loader fingerprint if available.
   Exact approved MAIN state and Runtime remain UNKNOWN here.

## Source code and actual validation

Code evidence SHA: d43374850c51420ffea82f934ffd7684faf6b414.
Official pinned SimC SHA: 710c2408bfd3ae4df71b8cd55cdf01f63fd6c926.
Native actual C++ run 41084262760 **SUCCESS** with two public
profiles Fury/Havoc, same pinned one-iteration seed.
Native binary SHA256
f906f0518d90f13b56fa05467e0e591b783f070e0e311b1443a1889ff7256980.
Python offline run 41084262818 **SUCCESS** for Python 3.12/3.14.

Implementation: tools/research/simc_native_if_guard_instrument.py (new),
tools/research/simc_native_if_guard_audit.py (new),
existing simc_apl_pointer_native_probe.py, tools/ci_offline.py and
pinned Native workflow. Actual action.cpp original if_expr->success()
is delegated ONCE at each of two source callsites, with same Native
actor/spawn, reset epoch and source sequence; row ownership from
original action signature-pointer equality to owning APL item.
Independent audit validates guard BEGIN/END, nested actual bare ref
evaluation, pointer-matched action attempt and exact effective APL row.

FIRST CODE COMMIT 4fdf8b2a20477a92cb2a665d3da81c5078174bda
Native run 41082893641 **FAIL**: Python marker archive Path shadowed
the source pointer evidence dict during summary assembly. Failure
evidence retained, no Native PASS assigned. Corrected in
d43374850c51420ffea82f934ffd7684faf6b414, with AST offline
regression, completely fresh successful compile and Native run.
Do not reuse first run's nonexistent summary as evidence.

## Actual product-significant observations

Baseline V6 identified 261/266 bare resource evals in native
pointer-matched ACTION ATTEMPT contexts. V7 stronger DIRECT IF scope:
- Fury rage 137: **55 actual inside original IF guard** and 82
  variable action evaluations (not IF).
- Havoc fury 129: **124 inside original IF guard**, 5 UNKNOWN
  with no exact action-attempt/IF context.
- Combined 266: **179 directly proven IF-evaluated bare reference
  values**, 82 variable action context, 5 UNKNOWN.
- Fury 426 executed IF guards (124 true, 302 false);
  Havoc 1749 executed IF guards (32 true, 1717 false).
  The 2175 IF guard executions and 179 bare resource evals have
  DISTINCT denominators.
- Of the 179 source-owned resource IF evaluations, 25 belonged to
  TRUE full IF guard results and 154 to FALSE.
  Fury rampage: 17 true and 38 false.
  Havoc pick_up_fragment/felblade: 8 true and 116 false.
  IF guard truth is NOT action readiness, user recommendation,
  selected action, WCL causality or optimality.
- Full resource write completeness NOT VERIFIED, Strict PRE still
  requires source timestamp strictly before decision in the same
  reset epoch; expression eval at decision is not a state transition.
  0/90 action READY tokens certified, 0 gameplay rules promoted.

Native replay artifact, run 41084262760, artifact ID 12990129697:
name zrot-pointer-source-summary-d43374850c51420ffea82f934ffd7684faf6b414,
retained marker-only GZIP logs for TWO public profiles, source patch
receipts and summary. Both condensed sources independently re-audited
and matched full raw Native direct-IF outcomes.
Artifact expires 2026-11-06T15:54:14Z UTC by GitHub metadata.
Exact original, filtered and compressed SHA256 in the Developer Note.
Do not confuse this marker-only retention with full Native game logs.
No private WCL, game user data or credentials used.

## Readiness source-gap (hypotheses only)

Pinned generic action_t::action_ready normally tests core readiness
before IF; a TRUE IF alone is not an available/performed action.
Pinned Warrior Fury rampage_parent_t::ready adds dual weapon
requirement; cost() changes under talent+buff.
Pinned Demon Hunter Havoc felblade_t::ready adds shared
Vengeful Retreat movement cooldown gate. SpecAdapter semantic
obligations, never hardcode class logic into generic evaluator.
Current Blizzard patch parity NOT VERIFIED.

## Exact next and integration boundaries

Product Exact Next: complete **minimum user-impact readiness**
for the first pairwise action choice with source, actual build,
observable state / unknown dimensions, while WCL lane independently
finds blind numeric/structural candidate actions and locks
cohort/threshold before seeing any SimC result. After lock,
compare source-derived SimC IF hypotheses with independent WCL
STRICT PRE, Blizzard mechanic, then proportionate holdout /
optional counterfactual. No encounter promotion from one fixture.

Session Exact Next: on this research branch, perform a read-only
readiness obligation table (core versus Fury Rampage / Havoc Felblade),
separate observable and UNKNOWN dimensions. Decide whether a
minimal source-confirmed action readiness trace is actually required
to change the user's IF/ELSE (not just increase rigor for its own sake).
Avoid another full C++ rebuild by default. Provide a branch-local
merge handoff for MAIN compatibility when sufficiently evidenced.
No premature integration into WCL blind discovery; no class/boss
hardcode in generic engine.

Approved MAIN/current Work OS pointers UNKNOWN in this branch.
MAIN controls CURRENT_STATE/global LATEST_HANDOFF, registry,
General Rotation baseline, encounter generic assumptions, active
manifest, production pointer, product Seq578 and FROZEN. All
unchanged by this branch. Seq637 local result UNKNOWN.
GitHub main historical observed SHA
4790f77f76a75f26ff0558d1d18c16cd9d630c4b
does not establish authoritative runtime state.

cross_branch_dependency: WCL blind owner needs candidate-locked
STRICT PRE and readiness evidence without SimC leakage.
cross_branch_dependency: MAIN needs current approved state, Runtime,
source/branch compatibility review and explicit promotion decision.

User local action: NONE. No PyCharm execution or downloadable .py
artifact in this turn. If newly started conversation restore and
report V7 but stop until user explicitly says 진행.
