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
