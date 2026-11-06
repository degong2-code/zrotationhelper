# WoW Retail 12.1.5 — addon policy, API capability and deployment gate

**Branch-local engineering constraint reference, reviewed 2026-11-06 (KST).** Product policy `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`. Scope: **target-dummy training** only, not live raid/encounter or in-combat rotation assistant. This document is not a legal opinion or Blizzard approval; each live API-specific conclusion remains conditional on a real Retail client check.

## 1. Source reliability hierarchy

| Grade | Source and link | What it supports / explicit limit |
|---|---|---|
| `BLIZZARD_OFFICIAL` | Blizzard: [How Midnight's Upcoming Game Changes Will Impact Combat Addons](https://news.blizzard.com/en-us/article/24244638/how-midnights-upcoming-game-changes-will-impact-combat-addons) | Stated intent: addons may customize presentation of combat information but should not process it to automate combat decisions. This is a **product design boundary**, not a per-function legal verdict. |
| `BLIZZARD_OFFICIAL` | Blizzard game director: [Combat Philosophy and Addon Disarmament in Midnight](https://news.blizzard.com/en-us/article/24246290/combat-philosophy-and-addon-disarmament-in-midnight) | Secret Values protect live combat state from addon logic; Blizzard Assisted Highlight / One-Button Rotation are **first-party** features, not proof third-party independent solvers are authorized. Specific UI API contracts still vary. |
| `BLIZZARD_DEVELOPER_NOTE_REPRINT` | [12.1.0 API changes / UI Engineering developer notes](https://warcraft.wiki.gg/wiki/Patch_12.1.0/API_changes/notes) | Dated 2026-06-18 onwards; AuraContainer/AuraButton and Forbidden Aspects; aura list/data restrictions and later exception changes. This is a **community-hosted transcription** of Blizzard-origin developer notes: identify provenance, verify client before deployment. |
| `BLIZZARD_DEVELOPER_NOTE_REPRINT` | [12.1.5 API changes / developer notes](https://warcraft.wiki.gg/wiki/Patch_12.1.5/API_changes/notes) | Dated Sep-Oct 2026; continued addon security changes. Reference version, not immutable permission guarantee. |
| `SECONDARY_BLUETRACKER_HISTORICAL` | [UI Add-On Development Policy mirror](https://www.bluetracker.gg/wow/topic/us-en/24534-ui-add-on-development-policy/) | Reprints Blizzard's 8 historical policy items: free distribution, visible source, no performance/server harm, no in-game ads/donations, age-appropriate, ToU/EULA, Blizzard disable authority. **Direct official support article** https://kr.battle.net/support/ko/article/75792 currently redirects to a dynamically rendered loading page in this research context; these 8 items are **not claimed freshly verified against live official text**. |
| `SECONDARY_API_REFERENCE` | [UNIT_SPELLCAST_SUCCEEDED](https://warcraft.wiki.gg/wiki/UNIT_SPELLCAST_SUCCEEDED); [GetSpellCooldown](https://warcraft.wiki.gg/wiki/API:C_Spell.GetSpellCooldown); [GetSpellCharges](https://warcraft.wiki.gg/wiki/API:C_Spell.GetSpellCharges) | Candidate method signatures and documented secret fields, not current live observation of all values in training combat. |
| `USER_ATTACHMENT_HISTORICAL_IMPLEMENTATION` | HekiLight v0.7.0 ZIP SHA256 `d0c8af119de9d0ebd34b50bda11a24cbe4a8c4cbafd8b1e1f4c6de320315fc0d`; `HekiLight.lua:674-688` | The addon catches errors from comparisons with secret cooldown values and uses the error as information. This **does not confer Blizzard permission**; do not copy this pattern. |

**Revalidation trigger:** on each Retail patch/hotfix/API change, refresh official Blizzard statement and per-field API contracts; recorded client test receipts take precedence over assumptions, but cannot override Blizzard restrictions.

## 2. Distinguish three kinds of claims

- **Policy prohibited / excluded by product:** no automated input, target selection or spell casting, no protected-function manipulation, no injected client/memory hook, no unapproved third-party automation and no workaround to recover secret combat data. Full in-combat custom rotation decision automation runs contrary to Blizzard's published disarmament direction; **do not implement** even if a loophole temporarily exists.
- **API technically restricted:** a frame can display secret Aura/Cooldown fields while addon Lua cannot compare, enumerate, branch on, serialize or derive them. Forbidden Aspects can also prevent scripts, hooks, events and click/query operations. Different calls, fields and contexts have different restrictions. "The API exists" != "we may safely use all results".
- **Permissible in principle but not yet demonstrated:** localized spell icon/info, opt-in recording of own non-secret cast events, bounded SavedVariables, small post-session UI. Specific data provenance, client version, combat context, and whether the event payload is non-secret **must be tested**. A training/education purpose is NOT a blanket special exemption.

**Scope-safe processing split:** SimC/WCL/files **outside the WoW Lua addon** can analyze legitimate, authorized historical combat data; the in-game addon must not scan arbitrary external files or run network clients. WoW's supported `/combatlog` disk logger, if available, feeds a separate offline import, never a hidden in-game file read bridge. Never bypass availability/security controls.

## 3. Why old Hekili source cannot be an in-game implementation blueprint

Hekili old `State.lua`, `Targets.lua`, old `Events.lua`, and `TheWarWithin/MageArcane.lua` / `WarriorFury.lua` assume readable real-time combat state and some `COMBAT_LOG_EVENT_UNFILTERED` usage. It is a historical offline **architecture sample**, not tested-compatible 12.1.5 telemetry. Blizzard's API direction specifically targets this class of live decision logic. Preserve Hekili's **source-conditioned reason ledger/state machine separation** in an independent research engine, while moving only restricted safe presentation/own-cast recorders into the client.

### 12.1+ aura specificity (do not overgeneralize)

Blizzard-origin 12.1 development notes describe secret UnitAura payloads and protected aura containers, but also exemptions for explicitly non-secret auras and evolving method-specific rules. 12.1.0 PTR updates modify restrictions more than once (e.g. 2026-06-30, 2026-07-14, 2026-07-23). This is **not** an assertion that every buff or every API is always secret. Generic rule: field-by-field assessment and UNKNOWN when not proven.

## 4. Mandatory feature and capability gates

| Feature | Development permission within project | Current evidence / state | Gate required to release |
|---|---|---|---|
| Offline SimC source-APL/Native conditional logic & multi-step state simulation | YES, outside WoW | Existing source-native four-scenario and AST receipts, partial | No prohibited game-client connection; source pin, tests and honest READY/UNKNOWN |
| Offline WCL/authorized client combat-log analysis | YES, outside WoW | Engine fixtures; new dummy session import not actually executed | Authorized data, deterministic replay, Strict PRE, correct player and spell identity, no secret workaround |
| Game addon own `UNIT_SPELLCAST_SUCCEEDED` spell-ID record | CANDIDATE | `addons/research/ZRotDummyProbe` research source exists, mock tests only | **Real Retail 12.1.5 target-dummy in-combat client**: player event, numeric non-secret spellID, dedup/correlation, casts lost/duplicate, false manual attribution |
| Non-secret spell icon/name, keybind, basic opt-in UI | CANDIDATE | HekiLight historic source; not product client test | Real client compatibility, accessible/protected API constraints, no action manipulation |
| Bounded SavedVariables of non-secret own-cast events | CANDIDATE | Research addon has bounded data contract; real client not verified | Persistence on reload/logout, no hidden/protected/secret fields, user opt-in, retention limits |
| Secret-value buff/cooldown/charge/access as a `lua if` operand | NO, absent explicit non-secret exception | 12.1+ secret/forbidden mechanics | Must remain UNKNOWN; using `pcall` to convert comparison error to Boolean is specifically rejected |
| Game addon enumerate enemy auras/targets to infer live best ability | DO NOT BUILD | Old Hekili design conflicts with Midnight stated intent | Do not resurrect as an "education" exemption |
| Real-time proprietary APL recommendation engine in combat | OUT OF CURRENT BUILD | Blizzard's disarmament policy | Not part of Dummy Trainer, no implementation |
| Post-session expected-vs-actual explanation | YES, offline by default | General Rotation model and exact actual session evidence not complete | Source/SpecAdapter IR + validated rule + player cast sequence + strict PRE/readiness; otherwise UNKNOWN |
| In-game live education cue | DEFERRED | Policy/API boundaries not proven sufficiently | Separate feature-by-feature official API and client proof; no live combat-state solver |

For every adapter event/field maintain this **Capability Receipt** (machine-readable, code implemented later):
```json
{
  "retail_patch": "12.1.5",
  "feature": "player-own-cast-event",
  "api_event": "UNIT_SPELLCAST_SUCCEEDED",
  "unit": "player",
  "context": "target-dummy-in-combat",
  "api_contract_source": "URL_AND_DATE",
  "real_client_tested": false,
  "payload_secret": "UNKNOWN",
  "observed_fields": [],
  "can_store_in_savedvariables": "UNKNOWN",
  "can_decide_rotation_condition": false,
  "decision": "UNKNOWN_NOT_YET_PROVEN"
}
```

A supported display API cannot be used to infer the hidden value by appearance, OnShow, frame parenting, layout size, exception behavior, tooltip parsing, changing taint, animation timing, error branch, or any other covert observation.

## 5. Mandatory pre-merge checks

1. Source-proven distinction: `OFFICIAL_POLICY` vs `BLIZZARD_DEV_NOTE_MIRROR` vs `COMMUNITY_API_REFERENCE` vs `CLIENT_OBSERVED` vs `UNKNOWN`.
2. Require real Retail client evidence before `SUPPORTED_LIVE` status; mock Lua/CI only establishes compile/offline behavior.
3. No combat logging hooks removed in Midnight, secret comparisons, side-channel, protected action execution or arbitrary file/network access.
4. No false action-error claim: own cast does not prove keyboard input; unknown competing-skill readiness → `UNKNOWN`.
5. Addon keeps record payload minimal, opt-in, bounded size, no other player identity or combat sensitive tracking.
6. Strong policy assertions require an official accessible source; unsupported prohibitions/permissions remain labelled design guardrail or UNKNOWN.
7. User educational feedback only with validated full rotation IR and observable Strict PRE: otherwise descriptive recap instead of accuracy verdict.
8. If policy/API changes, fail closed and version the capability receipt rather than silently re-enabling old behavior.

## 6. Open issues and true status

- **NOT TESTED in real Retail client:** `UNIT_SPELLCAST_SUCCEEDED` full field availability, safe cooldown/charge in combat on dummy, SavedVariables persistence under real secret constraints, timing of `/combatlog` file export, in-game post-practice UI.
- **NOT established:** a broad Blizzard authorization for any proprietary custom real-time spell advisor; nor a blanket prohibition on offline educational log review.
- **No claim:** exact current terms text of support article `75792` verified on 2026-11-06 (dynamic redirect unavailable to this read).
- **No code or MA​IN promotion** is implied by this research note.

Linked design: `HEKILI_ARCHITECTURE_REFERENCE_20261106.md`; roadmap: `GENERAL_ROTATION_HEKILI_POLICY_ROADMAP_20261106.md`.
