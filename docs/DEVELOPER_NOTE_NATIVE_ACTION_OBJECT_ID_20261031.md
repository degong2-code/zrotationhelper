# V10: Native source action-object ID boundary — 2026-10-31

Owner BR-SIMC-APL-BOOTSTRAP. BRANCH RESEARCH ONLY.
No MAIN, General Rotation, FROZEN, active manifest, Seq578 or global handoff promotion.

## Source evidence

Pinned SimulationCraft source: 710c2408bfd3ae4df71b8cd55cdf01f63fd6c926.
- engine/action/action.hpp: action_t::id = spell-data ID if available, otherwise zero; internal_id is a separate player/action-name identifier.
- engine/action/action.cpp: action_t constructor initializes id independently from internal_id; when data().ok() it parses spell data; parse_spell_data assigns id = spell_data.id().
- engine/class_modules/sc_warrior.cpp: create_action rampage -> rampage_parent_t -> p->talents.fury.rampage data.
- engine/class_modules/sc_demon_hunter.cpp: create_action felblade -> felblade_t -> p->talent.demon_hunter.felblade data.

These source paths are NOT a certified current Blizzard/WCL game ability ID, skill replacement resolution, or user action recommendation.

## Added code and actual checks

Research code commit 9b2f92091af1bb19f96d5090fd3f408ca8f90ce3.
File tools/research/simc_native_pointer_action_id_consistency.py audits exact Native IF markers under an independently verified source epoch and effective APL pointer. It groups positive SimC action_t IDs for each matched APL list/ordinal; a single observed ID remains a source-only candidate, multiple IDs are a conflict, 0 and unmatched scope are UNKNOWN. Never equate a same-timestamp nearby action or display token to a game ability identity.

Synthetic tests check single and conflicting IDs, 0, mismatched action scope UNKNOWN, malformed duplicate marker rejection. Actual Python 3.12/3.14 CI run 41096210210: SUCCESS.
Initial code CI 41095848633 FAIL and diagnostic CI 41096036252 FAIL because synthetic test incorrectly expected unmatched guard/scope to throw rather than remain UNKNOWN. Test expectation corrected, failures preserved.

Prior independent Native run 41084262760 SUCCESS (Fury/Havoc public profiles): 266 bare resource evaluations = 179 directly in original IF, 82 variable context, 5 UNKNOWN. These counts are NOT numeric game-ID certifications, READY certifications or playable rules. No new Native run, WCL API, current Blizzard verification, or extracted genuine ID inventory in V10.
READY certified 0/90, gameplay rules promoted 0.

Existing V7 marker-only evidence artifact 12990129697 on run 41084262760 expires 2026-11-06T15:54:14Z UTC. Its full matching exported effective APL bytes were not retained in the branch; marker-only replay cannot simply assert the complete source model.

## Exact next

Check feasibility of retrieving bounded already-recorded public marker evidence AND matching effective APL source bytes before attempting actual numeric source-ID inventory. If either is missing, classify BLOCKED rather than infer a numeric ID. Avoid new Native build absent user-facing need.

cross_branch_dependency: MAIN needs approved SpecAdapter source-complete readiness/numeric game identity contract and authoritative Runtime/current-state.
cross_branch_dependency: independent WCL lane needs candidate lock and Strict PRE coverage before SimC row/threshold exposure.
