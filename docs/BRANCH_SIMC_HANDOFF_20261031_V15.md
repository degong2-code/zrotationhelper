# BR-SIMC-APL-BOOTSTRAP — V15 blind lock input hardening (2026-10-31)

Owner: BR-SIMC-APL-BOOTSTRAP. Branch-only SimC post-lock research.
This is NOT approval of WCL blind independence, readiness, MAIN or gameplay.

## Exact base and file evidence

V14 branch HEAD: 93190728b58c61f33d9761af5e1332d3c619f06b.
V14 GitHub CI 41104971837: COMPLETED/SUCCESS Python 3.12+3.14.
V14 corrected portable source aggregate remains authoritative;
original V12 invalid portable positive_ids stays failure history.
V15 tested research code HEAD:
6da1ea068ad93862f4b9973cf6ea8d639833e355.
Modified ONLY tools/research/post_lock_simc_wcl_guard_replay.py
(old blob 43b48eff80cc51d6cb232d35660cd0c982663956,
 new blob 6c583745b8554740c9369ae8a0e8581dd293f608).
No SpecAdapter, runtime readiness provider, main HEAD,
source ID registry, shared state, active manifest,
global LATEST_HANDOFF or FROZEN modification.

## Specific problem and minimal fix

Old _locked_numeric_actions SHA-valid numeric lock reader checked
its fixed schema, LOCKED_NUMERIC_ONLY flag, declared candidate count,
numeric positive spell IDs, semantic_name=null, and no priority/
causality/gameplay claims. It did NOT reject additional fields
carrying hidden SimC action/guard/guide content; Python json.loads
also accepts duplicate JSON keys and nonfinite NaN by default.

Added three fail-closed checks inside the EXISTING research
post-lock consumer, not an extra engine:

1. _unique_json_object_pairs rejects duplicate JSON keys at any
   nested object depth: BLIND_LOCK_DUPLICATE_JSON_KEY.
2. _reject_nonfinite_json_constant rejects NaN/Infinity/-
   Infinity: BLIND_LOCK_NONFINITE_JSON_CONSTANT.
3. _reject_obvious_semantic_leakage recursively rejects clearly
   semantic/SimC/guide field names or string values, including
   source action names, APL guard/path references, Blizzard or
   Wowhead injected answers, when present in nested or top-level
   metadata: SIMC_SEMANTIC_CONTAMINATION.
   The known empty semantic_name and false
   semantic_names_attached sentinel fields remain allowed.

This guards against accidental obvious leakage, NOT intentional
obfuscation or proof of historical independence. The latter
requires an independently produced WCL raw record, source and
candidate-lock timestamps/bytes SHA, pre-lock workflow history,
and holdout governance verified by the MAIN/WCL owners.

Regression tests added IN THE EXISTING research module selftest:
- top-level SimC APL guard injected -> rejects;
- source='SimulationCraft' -> rejects;
- nested action_name field -> rejects;
- 'WOWHEAD_GUIDE' metadata -> rejects;
- duplicate JSON status field -> rejects;
- NaN numeric threshold -> rejects;
- valid numerical actor/resource + WCL evidence metadata ->
  still accepts existing guarded research replay, returns
  blind_independence_verification=NOT_RUN;
- prior source/strict-PRE/profile SHA/semantic flag tests
  continue to pass.

## Actual validation results and limitations

GitHub Actions workflow 41105867712 (code HEAD above):
COMPLETED SUCCESS, jobs Python 3.12 SUCCESS and 3.14 SUCCESS.
Confirmed log for Python 3.12:
source_syntax PASS, contract_shape PASS,
simc_wcl_post_lock_guard_replay_research_only PASS,
simc_readiness_source_coverage_compat_synthetic PASS,
simc_wcl_batch_reconciliation_research_only PASS.
The CI runs module's synthetic self-test with negative injections;
no real WCL blind artifact was supplied here.

V7 real source Native evidence, V12 independently replayed
2,175 source IF envelopes, V14 positive-ID aggregate correction,
and V13 public third-party game ID hypotheses are unchanged.
No new Native execution or WCL/Blizzard actual live API.
Current game action identity certified 0; readiness 0/90;
General Rotation gameplay rule promotions 0.

## Known boundaries

A hash matches the provided bytes but does not establish
independent WCL provenance. Numeric-only input may still
contain biased candidate selection, unobserved readiness,
or guessed cast identity; this module cannot determine those.
Forbidden semantic patterns are conservative, may cause
some false-positive rejections, and are NOT a general-purpose
proof of blind discovery. Hidden/obfuscated contaminations
could evade keyword scans; treat as WCL provenance BLOCKED.
If WCL's actual lock schema legitimately needs richer fields,
MAIN/WCL owners should approve a strictly versioned,
numeric-structural schema and update tests before promotion,
rather than weakening safeguards ad hoc.

## Next and owner boundary

Product exact next: independent WCL numerical candidate +
threshold/holdout lock, valid Strict PRE observability,
and MAIN-approved source-complete SpecAdapter readiness/
numeric ability identity contract. Post-lock only,
compare SimC hypotheses to WCL and Blizzard current truth.
No blind lock (raw bytes/provenance) supplied to this branch.

cross_branch_dependency: WCL discovery owner needs to
supply independent numeric candidate lock artifact,
strict PRE readiness UNKNOWN coverage, source raw evidence
and pre-lock/holdout governance WITHOUT receiving SimC
action/guard/threshold hypotheses.

cross_branch_dependency: MAIN needs to approve the
numeric action identity, source readiness completeness
and runtime compatibility and validate current authoritative
state before any shared promotion.

No PyCharm/local user execution needed.
Seq578/FROZEN unchanged. Seq637 UNKNOWN.
