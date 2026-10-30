# BR-SIMC-APL-BOOTSTRAP — V13 source identity corroboration and continuity

Date: 2026-10-31 KST. OWNER BR-SIMC-APL-BOOTSTRAP.
**Branch-only source/external candidate identity review; no MAIN promotion.**

## Restore and evidence order

1. This V13 branch handoff and branch-only LATEST_HANDOFF.json.
2. docs/BR_SIMC_EXTERNAL_GAME_SPELL_ID_CANDIDATE_20261031.json,
   containing two external identity candidates and all URLs/claim tiers.
3. V12 independent full archived marker replay receipt and handoff,
   V11 original archive replay, V10 action-object ID semantics,
   V9 readiness completeness, V8 source obligations, V7 native raw proof.
4. Separately MAIN-approved CURRENT_STATE, Runtime/Manifest Loader,
   active product manifest, dual-lane Core Contract, successor
   Playbook, and Parallel Workstream Contract. The branch did not
   recover/approve MAIN authority.

## Existing evidence verified

Pinned original simulationcraft/simc commit
710c2408bfd3ae4df71b8cd55cdf01f63fd6c926.
Archived raw markers: original V7 run 41084262760.
V12 independent source IF scope replay 2175/2175:
Fury 426, Havoc 1749; 806 evaluations have positive
SimC action_t::id, 1369 zero. Native IDs 184367
from Fury Slayer Rampage source rows 3 and 13;
232893 from Havoc Felblade default source row 26.
Zero on Havoc pick_up_fragment is NOT an in-game skill ID.
The effective APL original export bytes are unavailable,
so no full source byte-parity replay was claimed.

Prior V12 branch code/document HEAD
d129b6434848286a7ea5643e20e9a0278e969f93.
At first V13 read, its last GitHub Actions run
41101539582 remained **QUEUED**, not PASS.
No new Native, WCL or production client execution V13.

## New externally corroborated identity hypotheses

- Native Fury source action_t ID 184367 matches the
  third-party Wowhead and WoWDB Rampage/광란 entry.
  https://www.wowhead.com/spell=184367/rampage
  https://www.wowdb.com/spells/184367-rampage
- Native Havoc source action_t ID 232893 matches
  the third-party Wowhead and WoWDB Felblade/지옥칼 entry.
  https://www.wowhead.com/ko/spell=232893/
  https://www.wowdb.com/spells/232893-felblade

These are real name/ID *external candidate corroborations*.
They are NOT an authenticated Blizzard Game Data API record,
nor current WoW client actual known/actionbar/cast mapping,
nor any independently locked WCL game event identity.
Do not promote a user skill icon, branch FROZEN, or gameplay
recommendation. Both are still UNKNOWN for current client.

A concrete same-name disambiguation hazard:
third-party spell entries 204497 and 236167
also use localized 지옥칼/Felblade but represent distinct
effect/aura/proc source entries. A source action name alone
may match several numeric IDs; do not use localized names as
runtime identities or substitute a proc/child for a button.

## Official game mechanic claims with STRICT authority boundary

Official Blizzard Midnight Apex Talent notes state that
Rampaging Berserker rank 2 reduces Rampage Rage cost
during Recklessness:
https://worldofwarcraft.blizzard.com/en-gb/news/24244472
Official Blizzard Midnight pre-expansion notes state
Rampage replaces Slam, and Felblade was changed to generate
15 Fury:
https://worldofwarcraft.blizzard.com/en-us/news/24244455

These are official descriptions of MECHANICS, not published
proof that source object 184367/232893 is the current
in-client actionbar ID in every build/talent/form, or proof
of the precise dynamic cost for the pinned active build.

Important: public Wowhead Rampage indicates baseline
80 Rage, while the actual source APL contains rage>=100
and rage>100 guards. The APL conditions are strategic
state gates, not necessarily cost or readiness thresholds.
The pinned SimC rampage_parent_t::cost() includes
a Recklessness/talent-specific signed spell-data effect.
Do not interpret a source expression's '+=' as a verified
*increase* without signed live effectN metadata; that would
contradict the official description of a cost reduction.
Preserve magnitude/sign as UNKNOWN until read from source
game build/effects or authoritative game API. The IF
expression being true never proves source spell can cast.

Havoc Felblade APL fury<=100 is also NOT an affordability
condition. Pinned SimC source Felblade readiness contains a
separate shared movement cooldown and directionality.
In-game actual current readiness still UNKNOWN.

## MAIN adapter compatibility (read-only audit)

Inspected common
02_SOURCE/runtime/raid_dps/specs/protocol.py,
blob 605dfdc8cd76d0f3a8d9d811521ce56d49131cd2.
Existing ActionFamilyDef uses numeric base/upgraded action IDs
and ActionOverrideDef can describe replacement by numeric
IDs; StateFeatureDef supports primitive/identity metadata.
But it lacks a complete per-action source readiness
obligation declaration and source-specific variant identity.

Inspected existing Fury Slayer spec adapter
02_SOURCE/runtime/raid_dps/specs/fury_warrior/adapter.py,
blob a7c35cc6f5bbbdfe47b65bc63be4bba22a60cc97.
Current action families are BLOODTHIRST_FAMILY and
RAGING_BLOW_FAMILY; Rampage is not an active family and
known_masks includes RAMPAGE_CONTEXT_CANDIDATES_NOT_PROMOTED.
Do not fill this FROZEN mask from external name ID matching.

Minimal MAIN-owned extension proposal is a **data-driven
source-obligation/identity candidate record** keyed by
source lane, spec/build, effective APL SHA, list/ordinal,
action_t ID and numeric game ability candidate, with
separate source-provenance, current client build/known
spell, replacement/child action relation, WCL post-lock
numeric event kinds, and Strict PRE readiness coverage.
No new production evaluator, no common contract edit.

## Current-client validation route (NOT RUN)

Current Retail API documentation indicates
C_Spell.GetSpellInfo(spellID) returns localized name,
iconID, originalIconID, and spellID; a separate
C_Spell.GetSpellTexture can include conditionalIconID
as of patch 12.1.0 per community API notes.
https://warcraft.wiki.gg/wiki/API_C_Spell.GetSpellInfo
https://warcraft.wiki.gg/wiki/API_C_Spell.GetSpellTexture

A successful lookup establishes an in-client spell
data entry, NOT learned status, selected/overridden
action bar identity, full source-of-truth mechanic
or readiness. A future authorized client observation
should record build, spec/talents, known/override,
numeric cast/actionbar ID, icon mapping and timestamp
without inferring PRE from same-time/future events.

## Exact next and remaining blockers

Source ID *name corroboration* is now available but
current Retail action ID/authoritative build validation
is NOT completed. Repeating more Wowhead name queries
or Native source audits cannot solve WCL blind lock.

cross_branch_dependency: MAIN needs approved
Runtime/CURRENT_STATE and compatible source-complete
SpecAdapter readiness plus numeric action/child identity
contract. Only MAIN may promote shared IR/semantic state.

cross_branch_dependency: WCL independent blind
discovery owner needs candidate/threshold lock and
numeric Strict PRE/UNKNOWN readiness coverage. Before
that lock, share ONLY V8 blind-safe observability
request, never this document's SimC names/IDs/guards.

After candidate lock, replay the SimC source hypotheses
against independent WCL rows, corroborate Blizzard
numeric identity and actual current mechanics; only
then consider a General Rotation IF/ELSE game rule.
Original V7 marker artifact expires
2026-11-06T15:54:14Z UTC; V12 portable bundle is
separately available in current conversation.

State: source candidate 2, **game identities 0,
READY certified 0/90, gameplay rules 0**.
No MAIN/global pointer/FROZEN/Seq578 changes. Seq637
UNKNOWN. No local action or .py download in V13.
