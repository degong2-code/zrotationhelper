# zRotationHelper — SimC research branch continuity handoff V4

Date: 2026-10-30 KST. Branch owner: BR-SIMC-APL-BOOTSTRAP.
Repository: degong2-code/zrotationhelper, branch work/github-ci-bootstrap.
Status: BRANCH_VALIDATED research evidence. NOT MAIN/FROZEN. NOT MERGE_READY for gameplay rules.
V4 supersedes V3 only for research-branch continuation; V1–V3 and original CI remain immutable history.

## 1. Authority and immutable boundaries

Use current Project Instructions, ROTATION_RESEARCH_SYSTEM_CORE_CONTRACT_V1.md (dual-lane),
GENERAL_ROTATION_PLAYBOOK_DUAL_LANE_SUCCESSOR_PROPOSAL_v2.md (WCL/SimC rigor),
PARALLEL_WORKSTREAM_AND_MERGE_CONTRACT.md (branch scope), and actual approved
MAIN CURRENT_STATE/global LATEST_HANDOFF/active manifest only if independently retrieved.
Cloud Work OS Runtime live Manifest/Loader SHA boot: UNKNOWN; MAIN CURRENT_STATE:
UNKNOWN; global latest/active manifest/production: UNKNOWN; Core Contract exact
approved bytes: UNKNOWN; product Seq637: UNKNOWN. Seq578 and project-wide FROZEN
unchanged. MAIN-only pointers, registry, General Rotation baseline and encounter
authority NOT modified. The GitHub main snapshot remains 4790f77f76a75f26ff0558d1d18c16cd9d630c4b,
not proof of active product MAIN state.

Product topology: SimC-first generic IF/ELSE *hypothesis* in parallel with
independent WCL blind discovery; do NOT inject SimC answers before WCL candidate
lock. WCL replay and Blizzard truth reconciliation after lock; selective
counterfactual/holdout for important user decisions. Strict PRE timestamp must
be strictly less than decision timestamp, same actual source reset epoch, actor,
spawn and monotonic source sequence; same time is UNKNOWN. Missing readiness
does not mean NOT_READY. No spec/boss-specific meaning hardcoded in generic engine.

## 2. Implemented research increment

Code evidence snapshot: work/github-ci-bootstrap@45eceaa88835fe3c5deac2f8095763fd30f154f1.
Pinned official upstream source:
simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926.

New branch-only code:
- tools/research/simc_native_bare_resource_eval_instrument.py
  Decorates the original bare resource make_ref_expr evaluator with an actual
  delegate->eval() and a source-stamped runtime EVAL marker. All resource names
  generic; stamp shares existing sim_t monotonic source counter.
- tools/research/simc_native_bare_resource_eval_audit.py
  Parses raw source markers and independently previously validated epoch
  projection; matches eval to SELECT_BEGIN/END via thread, iteration, reset,
  actor/spawn and shared source sequence. Compares only with last actual
  resource source transition whose timestamp is < selection BEGIN and sequence
  < BEGIN. Same-time, source write during selection, clock contradictions,
  missing predecessor and outside-selection remain excluded/UNKNOWN.
- Existing simc_apl_pointer_native_probe.py and native workflow now include
  those receipts on the SAME four public fixed source profiles.
No change to MAIN, generic evaluator or in-game UI. No new APL interpreter.

## 3. Actual CI evidence and denominators

Offline CI 41075553005: SUCCESS, Python 3.12/3.14, source commit 45eceaa,
offline/synthetic scope only. Native workflow 41075553050: SUCCESS, SAME code
commit 45eceaa; freshly compiled actual C++ Native SimC, four public profiles,
source synthetic preflight, runtime source-independent epoch audit and comparison.
Research binary SHA256:
0d234a886ceb5bb9b7addf642af311b2ad09dce60c7345dcbc90037a29d42dac.
The Actions summary/receipts apply to pinned source/profiles/one-iteration
fixed-seed fixture. Raw Native logs were not uploaded by this workflow.

| Profile | Resource eval records | Inside exact selection | MATCH_PARTIAL_PRODUCER | SAME_TIME_NOT_STRICT_PRE | OUTSIDE_EXACT_SELECTION |
| --- | ---: | ---: | ---: | ---: | ---: |
| Enhancement | 0 | 0 | 0 | 0 | 0 |
| Fury (rage) | 137 | 137 | 133 | 4 | 0 |
| Unholy (rune, runic_power) | 0 | 0 | 0 | 0 | 0 |
| Havoc (fury) | 129 | 14 | 13 | 1 | 115 |
| TOTAL | 266 | 151 | 146 | 5 | 115 |

These counts are **expression evaluations**, not distinct decisions/actions.
A partial match means ONLY that the evaluated resource reference agrees with
the latest observed same-epoch, strictly earlier source producer value in that
specific comparison. Producer write completeness and original uninstrumented
Native foreground action equivalence are NOT verified. No resource evaluation
marker can become a PRE transition. No per-APL-source-row runtime expression
identity certified. Unholy 0 means "not observed in this fixed run", not
"no source semantics". Havoc 115 outside foreground selection are explicitly
not decision observations. No conflicts were observed in the eligible fixture
subset; this is not proof they never occur.

Previous source-only proof (41064679658 and offline 41064679434) established
four bare resource semantics: rage, rune, runic_power, fury resolve through
resources.current[RESOURCE_*] in pinned C++ parser paths; 294 source operand
requirements and 90 action-readiness requirements across four APLs.
Current certified actual APL source-row decision operands: 0.
Current READY-certified action tokens: 0/90.
Current gameplay General Rotation promotion: 0; WCL blind independent cohort,
candidate lock, live WCL replay, Blizzard current-game truth, raid/addon/UI
and user-PC production NOT VERIFIED.

## 4. Exact Next based on evidence value

Product Exact Next:
1. Read-only source/fixture audit explaining why Unholy bare rune/runic_power
   have zero runtime eval records in the fixed one-iteration run; identify APL
   branch reachability and source-row ownership. Do NOT claim parser failure
   solely from zero evaluation count, nor run more Native builds until needed.
2. For Fury rage and Havoc fury, distinguish actual original APL source-row
   ownership of logged expression evaluations from other expression callers.
   Identify resource producer write completeness or explicit missing paths.
   The 146 partial matches must remain uncertified until necessary producer
   completeness/identity is supported.
3. Only if source audit exposes an unresolvable important gap, perform ONE
   focused native experiment with predeclared fixture and independent raw
   validation; avoid 4-profile repeated C++ builds with unchanged source.
4. Thereafter source-certify the smallest user-impactful readiness family for
   the first IF/ELSE decision. WCL lane stays independent until blind candidate
   lock. MAIN alone may review compatibility and promote a gameplay contract.

Session Exact Next: Continue from V4 and this pinned CI evidence, inspect
limited Unholy source row reachability/producer identity, then plan one
focused fix. Do not rerun prior same-SHA CI proofs reflexively. If user
requests restoration only, report and stop; if user explicitly says 진행,
proceed within branch ownership. Any MAIN dependency:
cross_branch_dependency: MAIN needs to provide verified current authoritative
CURRENT_STATE, global LATEST_HANDOFF, active manifest, Work OS Runtime, FROZEN
baseline and integration approval.

Local user action: none. No executable Python delivery. No private credentials,
raw WCL data or proprietary user profile stored. Always separate actual native
CI PASS from empirical gameplay or live production PASS.
