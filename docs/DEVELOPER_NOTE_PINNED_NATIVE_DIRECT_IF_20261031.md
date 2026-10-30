# Native direct IF guard audit — pinned two-profile evidence (2026-10-31)

Owner BR-SIMC-APL-BOOTSTRAP; BRANCH research only, NOT MAIN gameplay authority.

## Scope, source, code and validations

Official SimulationCraft source PIN: 710c2408bfd3ae4df71b8cd55cdf01f63fd6c926.
Research code commit: d43374850c51420ffea82f934ffd7684faf6b414.
Native run 41084262760: SUCCESS, Fury + Havoc public MID2 fixed profiles,
one iteration, single thread, same fixed seed as V6. Pinned C++ compiled
binary SHA256 f906f0518d90f13b56fa05467e0e591b783f070e0e311b1443a1889ff7256980.
Offline run 41084262818: SUCCESS Python 3.12 and 3.14.

Earlier draft commit 4fdf8b2a20477a92cb2a665d3da81c5078174bda:
offline run 41082893461 SUCCESS but Native run **41082893641 FAILURE**.
The original Native C++ compile succeeded and first fixture was audited,
but Python summary failed with TypeError: PosixPath object is not
subscriptable, due to replacing the original pointer evidence dict
by a temporary compressed marker path named evidence. No final Native
result or evidence claim was promoted from the failed run. Corrected
in code commit d433748 and added AST offline regression requiring
the pointer proof binding name to be assigned exactly once. Full
Native source was recompiled and tested independently; old success
or binary SHA was not reused.

Added actual source-pinned direct guard instrumentation:
- simc_native_if_guard_instrument.py: in engine/action/action.cpp wraps
  the TWO exact original if_expr->success() source callsites in
  action_t::action_ready and call_action_list_t::action_ready.
  Original expression is delegated exactly ONCE, with source-monotonic
  ZROT_NATIVE_APL_IF_GUARD_V1 BEGIN/END and actual original
  boolean outcome. Original source action signature-pointer equal to
  owning APL row, actor/spawn, reset epoch, source time/sequence.
  No new readiness gate, class/boss-specialized logic or choice algorithm.
- simc_native_if_guard_audit.py: independent raw event projection,
  correct epoch and monotonic sequence, genuine IF expression enclosed
  resource reference eval, owning native action-attempt BEGIN/END,
  row pointer identity matched to exact effective exported APL.
  Tamper/duplicate sequence/scope drift fail closed. Evaluations
  outside a directly proven IF guard remain non-IF or UNKNOWN.

Existing Native runner now accepts --specs fury,havoc to avoid the
other unchanged public fixtures and --marker-output-dir to retain
only public-source ZROT_NATIVE_ audit markers compressed with gzip.
It independently reruns the full source guard audit on the marker-only
subset and requires identical counts before accepting. Native full logs,
profiles and JSON2 are not uploaded (CI runner ephemeral).
Only bounded two-profile marker-only evidence + source receipt + summary
are uploaded; this directly fixes V6's lack of replayable raw markers.

## Observed denominators and outcomes

| Specialization | Total bare resource eval | Actual direct IF guard eval | Source-observed variable (not direct IF) | UNKNOWN |
| --- | ---: | ---: | ---: | ---: |
| Fury rage | 137 | 55 | 82 | 0 |
| Havoc fury | 129 | 124 | 0 | 5 |
| Total | 266 | 179 | 82 | 5 |

Direct IF guard execution counts include expressions with NO bare
resource evaluation: Fury 426 guards (124 true, 302 false);
Havoc 1749 guards (32 true, 1717 false). They must NOT be mistaken for
179 bare resource evaluations.

Pointer-matched direct resource-guard proof, with guard result:
- Fury Slayer rampage ordinal 3: 13 guard TRUE and 35 guard FALSE
  for the bare rage eval (48 total).
- Fury Slayer rampage ordinal 13: 4 TRUE and 3 FALSE (7 total).
- Fury variables ordinal 4: 82 bare rage evaluations in source-confirmed
  VARIABLE action attempts, **not** direct if guard evaluations.
- Havoc default pick_up_fragment ordinal 9 FOREGROUND: 11 FALSE.
- Havoc default pick_up_fragment ordinal 9 OFF_GCD: 5 TRUE + 105 FALSE.
- Havoc default felblade ordinal 26 FOREGROUND: 3 TRUE.
- Havoc five bare fury evaluations with no source action attempt / IF:
  UNKNOWN. Never assign by name, timestamp, or nearby event.

This proof only identifies evaluated IF expression and its result in
pinned SimC, not a successfully available/selected/performed action.
True guard is not READY, state snapshot Strict PRE, mandatory priority,
causality, WCL parity or optimality. Full readiness 0/90 certified,
gameplay General Rotation rules promoted 0. Source resource producers
are still incomplete. Strict PRE remains source time < t, same reset
epoch, actor and source sequence. Same timestamp excludes evidence.
Source action parity to uninstrumented SimC is NOT VERIFIED.

Existing partial producer-state counts are a DIFFERENT dimension:
Fury 133 partial matches and 4 same timestamp excluded;
Havoc 13 partial matches, one same timestamp excluded and
115 outside foreground selection. Do NOT add 146 partial matches
to 179 directly proven IF evaluated resources as separate evidence.

## Evidence digests / independent replay

Run https://github.com/degong2-code/zrotationhelper/actions/runs/41084262760.
GitHub Actions artifact ID 12990129697, artifact name
zrot-pointer-source-summary-d43374850c51420ffea82f934ffd7684faf6b414.
Artifact compressed size reported by GitHub: 122724 bytes; storage
retention expires 2026-11-06T15:54:14Z (GitHub metadata).

Fury original Native full log SHA256:
fcfd6404e7881086618b873e080ce305d96158b321cfd5ba3ff0ba128a3ceae6.
Effective APL SHA256:
98635a684638d241000c0f9b3a78b9eb43d9579b522f864b8aaf5ebaa159e737.
Fury marker-only uncompressed bytes: 498721,
SHA256 98b82c7ff4b17a4db44e6c5d2988b9b2aacb67e786dc13bcc781b8f2e6c4b204;
gzip file fury.zrot_native_markers.txt.gz 35635 bytes,
SHA256 f300242ac4bfe122e4ac301026c5537305f2dee5a3f8b9e6655f863965f952b7.

Havoc original Native full log SHA256:
1c91b847e641d31b81e3d5e4dda048226e50f2c8c9bbdde1c450daa4957bba1b.
Effective APL SHA256:
bee79d14337f12b7c98fdb426849480342f7292d3da0cb60e8a805883d65a995.
Havoc marker-only uncompressed bytes: 1315084,
SHA256 5b2e2646e3e20eecbde785fc86dcf74d6fe7c472b5123a519d31425ee784374f;
gzip file havoc.zrot_native_markers.txt.gz 94696 bytes,
SHA256 9ede7dbc80dae554900474e98bccddbc4bd707fbd0fb8f04850eac5780c01c9b.

Both independently replayed marker-only sources were compared to their
original full source audit and returned
PASS_SAME_DIRECT_IF_SOURCE_OUTCOMES (same count and direct owner/status
data). This supports independent recalculation within the pinned test,
not live WoW Retail state.

## Static readiness reconciliation (not gameplay verification)

Pinned source engine/action/action.cpp::action_t::action_ready tests
ready(), target, directionality, line CD, sync and movement conditions
before the original if_expr->success() in the common code path; further
conditions can still reject after a guard returns true.

Pinned engine/class_modules/sc_warrior.cpp::rampage_parent_t::ready
requires both main-hand and off-hand weapon; its cost() overrides add a
conditional rage-cost modifier for rampaging_berserker_2 while
recklessness is active.

Pinned engine/class_modules/sc_demon_hunter.cpp::felblade_t::ready
checks a shared felblade_vengeful_retreat_movement cooldown before
base_t::ready; it also applies movement_directionality TOWARDS.
These are source-defined SpecAdapter readiness obligations, NOT
generic engine hardcoded rules, and current Blizzard mechanic parity
is UNKNOWN. Guard result 1 is not a fully ready or used action.

## Decision / exact next

This narrow high-value IF source ownership gap is sufficiently resolved
for two public profiles. Avoid further brute SimC C++ builds or chasing
the five unknown events with no shown user-facing impact.

Next branch-local research: minimum per-action readiness evidence and
source-derived IF/ELSE hypothesis for Fury rampage and Havoc felblade
must use exact source/talent profile and full source ownership, but
readiness remains UNKNOWN until tested. WCL blind independent cohort
and candidate lock must proceed WITHOUT exposure to this SimC result.
Only then compare SimC hypothesis vs WCL PRE, Blizzard game truth
and proportionate holdout/counterfactual.

MAIN-only CURRENT_STATE, global handoff, active manifest, registry,
General Rotation baseline and FROZEN/Seq578 untouched. Seq637 UNKNOWN.
Approved Cloud Runtime/Manifest/Loader and active MAIN state UNKNOWN.
No local user PyCharm/WCL API/credentials needed in this increment.
