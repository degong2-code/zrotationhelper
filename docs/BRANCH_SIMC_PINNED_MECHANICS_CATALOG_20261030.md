# zRotationHelper — Pinned Native SimC Spell Query Mechanics Catalog (Research Branch)

Date: 2026-10-30. **No MAIN promotion.** Status: source-backed *candidate extraction* PASS; rotation semantic correctness NOT VALIDATED.

## Primary product requirement
Build **one generic engine that automatically reads new SimC APL/profile/builds and derives/verifies conditional rotation hypotheses**, not handcrafted Enhancement/Fury rules. A DBC name-to-ID query is only part of a generic semantic acquisition pipeline. Do not turn text matches, even single exact names, into APL action identity, usable cooldown, learned talent, or playable IF/ELSE.

## Architecture and actual implementation
- `tools/research/simc_spell_query_catalog.py` takes a generic semantic route plan (generated from source APL → Structural IR → Decision Graph → observability requirements). It chooses bounded **source-derived** action tokens, generates `spell_query=spell.name=TOKEN` requests, and imports XML from the actual SimulationCraft binary; no 27-spec action table.
- XML `<spell_query><spell ...></spell_query>` is supported by official `simulationcraft/simc` code (`engine/sim/sim.cpp` `spell_query_xml_output_file`, `engine/report/reports.cpp`, `engine/dbc/sc_spell_info.cpp`). Raw public XML is size-bounded, XML DTD/ENTITY rejected, the expected spell IDs are positive integers, duplicates rejected, and each exact queried file is checked against SHA256. Import keeps fields actually present only: spell ID, name, class/spec/resource child attributes, cooldown, GCD, duration, stacks, replacement, effect metadata. No missing attribute is converted to a zero-valued gameplay mechanic.
- `link_catalog_candidates_to_route` connects candidate IDs to the exact action tokens in the source-derived semantic plan under matching spec/APL/profile/binary pins. This is **action candidate enrichment only**: `apl_action_identity_certified=false`, all readiness UNKNOWN, no automatic action identification through text.
- `tools/research/simc_spell_query_public_probe.py` executes native `spell_query` for bounded action tokens from each of two **public fixture** profiles within a digest-pinned official Docker image. Actual XML lives temporarily on the CI runner only. Public summary has source hashes, query names, counts, blob SHA receipts, no raw XML, private logs, personal profiles, WCL credentials or client identifiers.
- The catalog workflow is separated from quick source/synthetic CI. Native probe runs only for its own two files or workflow and can also be dispatched manually; avoids triggering Docker pulls on unrelated code/document edits.

## Native evidence

Pinned official Docker image `simulationcraftorg/simc@sha256:a6cfbc243456825d2dbecd607fe025948680219f4b4348603ed77a081b5f5895`; executable SHA256 `804fc81296fe1ae5208161df5cece258e2ac7489de60c3816d2097da3612e6fc`.

Native probe run [41010173997](https://github.com/degong2-code/zrotationhelper/actions/runs/41010173997): **SUCCESS** after candidate link check. Initial XML extraction run [41009997843](https://github.com/degong2-code/zrotationhelper/actions/runs/41009997843): SUCCESS.

| Pinned public image-internal profile | APL source SHA256 | Rows | Action tokens in full route | Native name queries | Per-query single candidate | Per-query ambiguous | Matched ID candidates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Enhancement `MID2_Shaman_Enhancement.simc` | `732a7ab8e2494d2e2a87a4b6546119f9b5ed31e6d6547d121b7cc319cf9981cd` | 115 | 24 | 5 | 2 | 3 | 26 |
| Fury `MID2_Warrior_Fury.simc` | `e872cca507063e3d63b84e522688b4ad44b2f7f7664e50e3f5553cf3f858088c` | 121 | 26 | 5 | 4 | 1 | 8 |
| **Total** | — | 236 | 50 | 10 | 6 | 4 | 34 |

Example: `ascendance` returned **16** exact conservatively normalized name records in this actual image. The code does **not** choose an ID. All 50 readiness requirements remain **UNKNOWN**, including the 40 not queried in this bounded sample. `ancestral_call` appears in both fixture APLs, illustrating that a string match cannot establish class/spec applicability.

**Noninterchangeable source baselines:** Earlier structural coverage used the GitHub public source `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926` and found 114 Enhancement rows. The pinned Docker image contains a different Enhancement profile with 115 rows and a different hash. These are separate input authorities; do not compare counts, conditions or outputs as if they were the same APL. The Docker binary itself is pinned and verified, but this does not prove it matches the current WoW Retail patch/hotfix.

## Tests / exact claim boundaries

- Catalog synthetic self-test: three arbitrary specialization labels, DBC spell XML field extraction, ambiguous duplicate-name candidates, invalid raw XML SHA, binary source pin mismatch, forbidden DTD. **PASS** (not live mechanics equivalence).
- Actual native public XML extraction: ten generated queries across two pinned profiles, every raw XML hashed, parsed, candidate joined to corresponding route with exact source identity. **PASS**.
- Offline matrix [41010174071](https://github.com/degong2-code/zrotationhelper/actions/runs/41010174071): Python 3.12 and 3.14 **SUCCESS**. Previous source-structure four-profile tests and 28-case synthetic priority bridge PASS at their prior pinned commits; not re-run as live SimC parity.
- No Blizzard live API cross-check, effective APL action implementation inspection, learned talent/build eligibility, replacement verification, class/spec/actor selection, readiness resource/CD/charge calculation, Strict PRE state, native foreground decision parity, blind WCL candidate lock, WCL replay or General Rotation freeze in this increment.
- Public native query ≠ Blizzard truth, spell.name match ≠ cast identity, sole name match ≠ ability learned, cooldown DBC metadata ≠ live cooldown readiness, generated conditional model ≠ validated gameplay recommendation.

## Next exact step, justified by user impact

Develop a **generic evidence-based actor/spec/build filter** for the multiple spell candidates using XML class/spec metadata + source profile/talent information, while preserving all candidates and rejecting insufficient or conflicting provenance. Measure how often it narrows ambiguous results **without false-positive certification** on new held-out profiles. Then compare inferred action IDs with independently certified native foreground SimC action/effect IDs, and cross-check Blizzard official mechanic/patch authority. Only complete, earlier-than-decision Strict PRE transitions and certified readiness policy can reach the shared runtime. WCL blind independent discovery must remain unexposed to SimC semantics until its candidate lock; reconcile and holdout afterward.

Maintain branch-only ownership: `main`, MAIN `CURRENT_STATE`, global `LATEST_HANDOFF`, Work OS, Seq578, frozen baselines, manifests and production pointers were not changed. Seq637 remains UNKNOWN. The current local MAIN/Work OS approved runtime remains UNKNOWN.


## Successor increment — generic profile actor/spec candidate evidence (2026-10-30)

**User priority audit:** This increment develops the generic engine's **ability to automatically investigate arbitrary new SimC profiles**, not one fixed spec rotation. No class-specific spell ID mappings, class decision tree, manual action rules or encounter semantics are introduced. Branch-only, no MAIN promotion.

### Implementation and bounded proof

- `tools/research/simc_spell_query_scope_filter.py` derives exact pinned profile SHA, single actor class, verified spec name and presence/fingerprint (SHA256) of its raw talent directives. The fingerprint does **not** interpret selected talents or prove build eligibility. The source profile is still an independently supplied file in the same pinned Docker image and is hashed before parsing.
- `assess_candidate_scope` requires matching route/APL/profile/spec/binary identities via existing `link_catalog_candidates_to_route`, then compares XML `<class name>` and `<spec name>` to that profile. Only conservative exact normalization and class/spec concatenations are considered explicit positive **lexical evidence**. Missing names stay UNSTATED; nonmatching labels are REVIEW, not grounds for deletion because class/spec/racial/pet/internal spells can have different identities. All candidate IDs survive intact.
- Output includes per-token source candidate IDs, explicit class/spec support, explicit class nonmatch, unresolved candidates, original/retained count, and UNKNOWN final ID/readiness. A singleton support set is still not proof of actual native APL action binding. `talent_directive_count` and `talent_directives_sha256` carry reproducibility only, not inferred talent mechanics.
- Existing standalone native Docker CI `.github/workflows/simc-public-mechanics-catalog.yml` now tests cross-spec synthetic examples and adds **held-out Unholy Death Knight** public profile to the native probe (three fixtures, five source-derived action token spell queries each). The source tokens are selected by generic alphabetical bounded request plan, not cherry-picked spells and not the full APL. XML is ephemeral; only summary JSON is uploaded.

### Native evidence

**Native run SUCCESS:** https://github.com/degong2-code/zrotationhelper/actions/runs/41011274525

**Offline CI SUCCESS:** https://github.com/degong2-code/zrotationhelper/actions/runs/41011274599 (Python 3.12 and 3.14).

Fixed official image: `simulationcraftorg/simc@sha256:a6cfbc243456825d2dbecd607fe025948680219f4b4348603ed77a081b5f5895`. SimC binary SHA256 `804fc81296fe1ae5208161df5cece258e2ac7489de60c3816d2097da3612e6fc`.

| Docker image internal public spec/profile | APL rows | Name-matched DBC spell IDs | Explicit class/spec positive support | Other retained, not certified | Explicit class nonmatch review | Talent source directives |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Enhancement Shaman | 115 | 26 | 11 | 15 | 2 | 1 |
| Fury Warrior | 121 | 8 | 5 | 3 | 0 | 1 |
| Unholy Death Knight (**new scope fixture**) | 63 | 23 | 12 | 11 | 11 | 1 |
| **Total** | 299 | **57** | **28** | **29** | **13** | 3 |

The remaining 29 includes 13 candidates with explicit class nonmatch and 16 with no positive class/spec label. Not all 29 are invalid: race/pet/shared/internal spell data may differ. **All 57 IDs are retained**. Each profile queried exactly five APL-derived action strings. Native status `PINNED_SIMC_PUBLIC_DBC_SPELL_QUERY_NATIVE=PASS QUERIES=15 SPECS=3`; the synthetic module self-test `SIMC_PINNED_PROFILE_SCOPE_FILTER_SELF_TEST=PASS SPECS=3 SYNTHETIC_ONLY` covers the exact profile SHA, actor/spec mismatch, ambiguous names, class conflicting or absent labels, full candidate preservation and fail-closed readiness.

Examples: `ascendance` from Enhancement has 16 exact-name DBC candidates, 7 with explicit positive scope labels; neither the 7 nor the remaining 9 are automatically certified/excluded. `arcane_torrent` from Unholy has 9 name candidates, one positive label and eight class nonmatch review candidates; racial applicability cannot be inferred solely from these labels. The generic filter preserves all.

### Claim-strength and data separation

- **PASS**: extraction of exact pinned profile actor/spec/talent fingerprints, XML scope label comparison and evidence ranking, no dropped IDs, three actual pinned public profiles, CI Python 3.12/3.14.
- **UNKNOWN / NOT RUN**: actual learned talents, spell/ability identity in actor-specific SimC implementation, cooldown/action replacement, race/gear legality, Blizzard live/current patch truth, foreground action parity, WCL blind discovery/replay, real Strict PRE state, full semantics across all 27 specializations, General Rotation decision accuracy.
- The earlier public GitHub source APL Enhancement count **114** and image-internal profile Enhancement count **115** remain distinct hashes/baselines; do not compare those row counts as one fixture. The new native probe reused the image-internal profile and did not update either authoritative input.
- No real action is promoted merely from one matching `<class>`/`<spec>` tag, and no assertion of zero false-positive candidate IDs is made: **0 gameplay identities certified** is a policy, not accuracy measurement.

### Focused Exact Next

1. Inspect **actual SimulationCraft actor-action binding paths** generically to link an APL action token to instantiated `action_t::id` / runtime source identity, with source provenance and handling of replacements/race/pet/procs; source DBC name match alone is insufficient.
2. Add independent/native foreground event evidence to test these candidate mappings; if the resolved effective action differs from name-based DBC IDs, preserve conflict and keep UNKNOWN.
3. Build a generic talent/build applicability reader from pinned SimC profile and talent database (not class-specific manually written ability maps). Verify on a *new held-out* spec/build.
4. Only when identities/mechanics are certified, generate source-accountable readiness policies and valid Strict PRE transitions; independent WCL blind discovery must lock separately before SimC replay.

No changes to `main`, MAIN `CURRENT_STATE`, global `LATEST_HANDOFF`, FROZEN, Seq578 or production pointers. Seq637 remains UNKNOWN; local MAIN/Work OS authoritative state not verified here.


## Successor — native action_t instance ID vs source-pinned DBC candidate comparison (2026-10-30)

**Primary success criterion:** The project builds one *generic, cross-specialization automatic research engine*. This stage advances the *evidence path* for action identity; it does **not** hand-write rules for Enhancement, Fury or Unholy. Exact source/fixture provenance and honest uncertainty are more important than candidate coverage scores.

### Upstream SimulationCraft identity authority

Pinned upstream `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926` code:
- `engine/action/action.cpp`: `action_t::execute()` emits `performs` broadly, including nonforeground effects; this must not be used as a stand-in for APL decision selection.
- `engine/player/player.cpp`: `player_t::sequence_add(const action_t* a, ...)` appends `a` to `action_sequence[_precombat]`; other code paths including `variable_t`/control may also contribute. Sequence membership alone is not independently certified foreground origin.
- `engine/report/json/report_json.cpp`: JSON2 `action_sequence` serializes `entry.action->id` to `id` and `entry.action->name()` to `name`, including `queue_failed`. This is an actual **action-object instance ID** recorded by the source binary, not a guaranteed DBC primary spell ID, learned ability proof, Strict PRE observation or optimal APL priority decision.
- The existing `simc_native_json_sequence.py` verifies the receipt and raw JSON2 sha, parses sample events and distinguishes queue failures, nonaction waits and precombat. No equal-time snapshot is promoted to PRE.

### Implementation and CI

- Added `tools/research/simc_native_action_id_reconcile.py`: checks exact spec, **effective APL SHA256**, profile SHA256 and SimC executable SHA256 across route/DBC catalog/native JSON2 receipt. For each source-derived action token, it compares positive native `action_t::id` values against **all retained** exact-name DBC IDs and reports `NATIVE_ACTION_ID_IN_DBC_NAME_CANDIDATES_UNCERTIFIED`, `CONFLICT`, `MULTIPLE_NATIVE_ACTION_IDS_NEED_REVIEW`, `NO_NATIVE_EXECUTION_SAMPLE` or `NOT_QUERYED`. Failed queueing, zero IDs and non-source events do not generate positive ID evidence. No candidate ID is selected as gameplay truth; all readiness remains UNKNOWN.
- Added `tools/research/simc_native_action_id_public_probe.py`: runs 1 deterministic native SimulationCraft iteration per public profile (fixed seed `1247695`), captures `save_actions`, JSON2 `report_details=1,full_states=1`, and log only inside ephemeral runner storage. **Critically, the APL route is rebuilt from that very run's exported effective APL bytes**; it is not guessed from a different profile revision or equated with the profile's raw SHA. The fixed binary/image/profile hashes and individual output hashes are verified by the existing native receipt parser.
- Selects five bounded DBC queries per profile from **positive-ID native sampled action tokens that also exist in the effective APL**. This makes the test relevant and reduces query calls compared to cataloguing all 24–26 source actions. But this is **native-guided selection bias**, not independent holdout, general mapping precision/recall or a test of nonexecuted abilities.
- Existing native mechanics CI now runs this after its prior class/spec 15-query probe, reusing the cached pinned Docker image. Only the two summary JSON files are uploaded; no raw XML/log/effective APL/client profile. The old structural-only workflow was not broadened to this more expensive probe.
- Synthetic `SIMC_NATIVE_ACTION_ID_RECONCILIATION_SELF_TEST=PASS SPECS=3`: matching native ID, conflict, multiple native IDs for the same token, missing query, skipped queue-failed, ID zero, unrelated native event, and identity-pin mutation cases. Offline and native CI PASS.

### Actual pinned public native evidence

- **Native CI:** https://github.com/degong2-code/zrotationhelper/actions/runs/41013002893 **SUCCESS**, three independently supplied public class/spec fixture profiles, fixed image `simulationcraftorg/simc@sha256:a6cfbc243456825d2dbecd607fe025948680219f4b4348603ed77a081b5f5895`.
- **Binary SHA:** `804fc81296fe1ae5208161df5cece258e2ac7489de60c3816d2097da3612e6fc`.
- **Offline CI:** https://github.com/degong2-code/zrotationhelper/actions/runs/41013002796 **SUCCESS**, Python 3.12 + 3.14.
- All native queries are sample-selected post-execution and are hypothesis support only:

| Image-internal profile | Profile SHA256 | Exported effective APL SHA256 | Native sampled queries | DBC candidate set includes native action-object ID | Conflicts |
| --- | --- | --- | ---: | ---: | ---: |
| Enhancement | `732a7ab8e2494d2e2a87a4b6546119f9b5ed31e6d6547d121b7cc319cf9981cd` | `6d414a0ebd18cba4b0304362325309f982698b7e33ae64d4daae4b5ef7a89bdf` | 5 | 5 | 0 |
| Fury | `e872cca507063e3d63b84e522688b4ad44b2f7f7664e50e3f5553cf3f858088c` | `98635a684638d241000c0f9b3a78b9eb43d9579b522f864b8aaf5ebaa159e737` | 5 | 5 | 0 |
| Unholy DK | `6a931073fc75752615f56eaa0a054d5e36d85109d0d6c2c650ba3e08f34de102` | `0e17b8c00c7d03b83f6560d57d19f3844e665ba1fba34d929c289e31ee92c097` | 5 | 5 | 0 |

Native positive-ID examples from the exact public summary, **not source-independent cast certifications**:
- Enhancement `ascendance`: 16 DBC name candidates, recorded action-object ID `114051`; `crash_lightning`: 6 DBC name candidates, recorded ID `187874` in 14 sampled events.
- Fury `bladestorm`: 7 DBC candidates, recorded action ID `446035`; `execute`: 7 candidates, recorded action ID `5308`.
- Unholy `dark_transformation`: 5 candidates, recorded action ID `1233448`; `death_coil`: 4 candidates, recorded action ID `47541` in 21 sampled events.

**Caveat:** `15/15` measures the selected **native-observed** sample's ID membership in a name-matched DBC candidate set. It does not mean 15/15 independent identity precision, 15 abilities certified, all 27 specs validated, no unknown spell replacements, or complete Native SimC rotation fidelity. This proof makes no claim on source actions that were not executed in this seed/window, effects not recorded in JSON2, or patch/Blizzard authority. The source-native comparable action tokens were already used in query selection, and data was generated by the same pinned SimC binary. All 15 lookup outcomes explicitly remain **UNCERTIFIED**.

### Exact Next after this increment

1. Use actual SimC action **creation/binding provenance** (`player_t::create_action`, specialized actor `create_action`, `action_t::id`, internal ID and spell data reporting differences) to identify which initialized APL action object corresponds to each effective APL row. Prefer a generic opt-in source-compiled instrumentation or a pinned implementation export, **not timestamp/name heuristics**. This resolves the foreground APL decision vs native action sample ambiguity; document unsupported classes/gates without single-spec code.
2. Measure on *new source-locked but unused fixtures* with candidate/threshold lock before independent holdout. Track native IDs that do not appear among DBC name candidates and unsupported action replacements separately.
3. Cross-verify Blizzard live spell identity and current patch/hotfix, actual talent/build eligibility and resource/cooldown/charge mechanics before any readiness policy is declared.
4. Generate valid STRICT PRE snapshots from transitions **strictly earlier than action time** and replay the existing evaluator. Keep WCL blind discovery independent until its candidate lock. No WCL calls/MAIN promotions in this branch turn.

MAIN-only authority untouched: `main`, `CURRENT_STATE`, product active manifest/pointers, global `LATEST_HANDOFF`, Work OS, Seq578 and all FROZEN state. Seq637 remains UNKNOWN. No authority promotion.
