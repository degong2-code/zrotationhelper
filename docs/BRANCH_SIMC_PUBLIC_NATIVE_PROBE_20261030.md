# zRotationHelper — Public Native SimC Reference Probe (2026-10-30)

**Authority:** branch-local research evidence only, NOT MAIN `CURRENT_STATE`, not global handoff, not production, not FROZEN. This supplements `BRANCH_SIMC_HANDOFF_20261030_V2.md`. The research topology remains SimC-first APL hypothesis bootstrap plus **independent blind WCL candidate lock before comparison**. `timestamp < decision_time` remains the only Strict PRE admissibility rule; missing readiness remains UNKNOWN.

## Scope and identity
- Repository: `degong2-code/zrotationhelper`, branch `work/github-ci-bootstrap`.
- Native capture workflow: `.github/workflows/simc-public-native-probe.yml`.
- Native workflow implementation SHA: `baf48c92afe62a0b5f6537ec3167d26903b19cc7`.
- GitHub Actions run: https://github.com/degong2-code/zrotationhelper/actions/runs/40999290228 ; completed SUCCESS. The predecessor unseeded public runs `40998973676` and `40999165171` succeeded but varied, and are **not** fixed-seed comparison evidence.
- Official SimulationCraft Docker image digest: `sha256:a6cfbc243456825d2dbecd607fe025948680219f4b4348603ed77a081b5f5895`.
- Image-internal SimC executable SHA256: `804fc81296fe1ae5208161df5cece258e2ac7489de60c3816d2097da3612e6fc`.
- Public profile: image-internal `profiles/MID2/MID2_Shaman_Enhancement.simc`, SHA256 `732a7ab8e2494d2e2a87a4b6546119f9b5ed31e6d6547d121b7cc319cf9981cd`.
- Effective APL SHA256: `6d414a0ebd18cba4b0304362325309f982698b7e33ae64d4daae4b5ef7a89bdf`.
- SimC options: `iterations=1`, `threads=1`, `max_time=60`, `vary_combat_length=0`, `seed=1247695`, `log=1`, `log_spell_id=1`, `report_details=1`, `save_actions`, `json2`. Fixed seed is set, but independent repeated fixed-seed equivalence was NOT RUN.

## Empirical observations (one fixed-seed public SimC run)
- Native CLI exit zero; effective APL, text action log, and JSON2 outputs present and SHA-pinned.
- The existing hash-gated native text event parser extracted **1,265** `performs Action` events; unrecognized-performs count **0**.
- The existing JSON2 parser extracted **7 precombat** and **69 combat** sequence rows (76 `SAMPLE_ACTION` rows in total).
- Cross-format exact `(timestamp_ms, action_token)` multiset diagnostic: **71/76 matched**, **5 unmatched** JSON2 sample action rows; 1,194 native performs remain unmatched to JSON2 samples.
- All 76 JSON2 sample actions had a native performs event at the same timestamp, but **66/76 timestamps had multiple native events**. This strongly prevents naive event-to-foreground attribution by timestamp alone. The diagnostic is **not** an independent classification of APL-origin actions and does not establish token/spell semantic correctness.
- Public summary-only artifact: id `12952652515`, archive SHA256 `afc77726a12e0de696fd8fd1ec16a9f06f237b165a0d400e6df250897bcab205`; raw log, profile and effective APL were NOT uploaded. Retention: seven days.

## Claims and exclusions
- **PASS:** actual pinned public SimC native CLI execution; capture provenance; existing parsers processing real native formats; structural cross-format exact identity diagnostic.
- **NOT VERIFIED:** current user's PC/build/profile equivalence; foreground APL choice; same-time JSON2 state as PRE; resource/cooldown/buff state provider; independent WCL discovery; complete APL interpreter; General Rotation decision correctness, encounter deviation, UI.
- **NOT RUN:** WCL live calls, private profile capture, independent holdout, MAIN state promotion. Seq637 UNKNOWN; Seq578/FROZEN unchanged by this branch.

## Focused exact next
1. Preserve public-only source pin, run seed, and evidence; do **not** treat 1,265 native events as 1,265 APL decisions.
2. Investigate the **five unmatched** JSON2 samples and same-time event collisions by independent event/actor/target identification, without assigning foreground by name or same timestamp.
3. Establish valid decision-time PRE transitions/readiness from actual source semantics; equal-time snapshots are inadmissible.
4. Then expand interpreter semantics and compare state-conditioned predictions to a certified native foreground decision subset; proceed to independently locked WCL cohort only afterwards.
5. MAIN alone may assess compatibility and promote after focused verification. Latest local MAIN `CURRENT_STATE`, global `LATEST_HANDOFF`, active manifest and Cloud-only Work OS boot remain UNKNOWN in this chat.

No changes to MAIN `main`, shared product pointers, frozen contracts, or user-private data.
