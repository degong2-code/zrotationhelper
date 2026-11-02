# zRotationHelper — BR-GR-ST2T-WCL-BLIND-20261102 Current Status

**As-of verification:** 2026-11-02 (Asia/Seoul)  
**Owner:** `BR-GR-ST2T-WCL-BLIND-20261102` — branch-local research, not MAIN promotion  
**Observed code HEAD BEFORE this handoff update:** `1061e9b9686b5f45402d25fa26a797eab4780a89`  
**Official policy:** `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`; lock SHA256 `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`  
**Canonical current handoff:** `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json`. Read this for the complete policy snapshot and latest chain; this note is explanatory, not an alternative pointer.

## Follow-up implementation result — 2026-11-02 (branch-local, no MAIN promotion)

This section records new implementation after the generation-1 handoff. It does **not** create another handoff generation or replace historical evidence.

- Final tested research-code commit: `349313851f32734b58792fb61c14569f4d432820`.
- New engine component: `tools/engine_first/wcl_actor_scoped_cohort_v1.py`. It uses the official WCL report fight `friendlyPlayers`/`friendlySpecs` and `masterData.actors` contracts to reject mismatched report/fight/actor/spec/class. It filters the verified numeric Strict-PRE replay to one actor **before** the independent blind numeric candidate lock. Its output does not contain SimC spell labels.
- Added CI: `.github/workflows/zrot-wcl-actor-scoped-identity.yml`.
- Final source SHA256: `07433e51e8c4253f788aee2744f3ce580a51d6f2ec2e09caeff97279bbdf0566`.
- Final CI proof: [Actions 41455193036](https://github.com/degong2-code/zrotationhelper/actions/runs/41455193036), Python 3.12 and 3.14 **PASS** on compile + offline synthetic source identity, other-actor exclusion, Strict PRE same-timestamp guard, blind count lock, tampered replay, negative identity checks and existing collector/lock regression.
- **Real high-ranking WCL source and authorized live API execution remain NOT RUN.** Ranking provenance and talent build are UNKNOWN; this synthetic PASS is not evidence of gameplay priority, current season validity, independent holdout, or post-lock SimC replay.
- The explicit `--live` CLI requires a genuine report code/fight/actor/spec/class and lawful WCL OAuth environment. It saves raw pages locally, supports bounded `--max-pages` and partial checkpoint/resume, and never auto-runs with no arguments. No GitHub secret, production pointer, global handoff, MAIN or FROZEN was modified.
- Product Exact Next unchanged. Session Exact Next narrows to verified fresh high-ranker discovery and bounded authorized acquisition, then real actor-scoped blind lock and only post-lock SimC comparison. Avoid sourcing actor/rank assertions from undocumented or stale secondary listings.

## Product and why this branch exists

**Long-term goal is a reusable engine capable of producing and validating General Rotation models for changing specs/builds/patches**, not an ad hoc Fury Warrior rotation, a stack of CI PASS counts or a historical system restoration.

Required product sequence: **SimC-first APL/profile hypothesis and native opener study → independent WCL high-ranker Strict PRE discovery/candidate lock → post-lock hypothesis replay and mechanic reconciliation → evidence-bounded General Rotation opener and ST/2-target/AoE IF/ELSE priority → lightweight target-dummy practice correction**.

Encounter/boss-specific rotation plans, live raid help, NSRT and raid timeline/guide outputs remain **OUT OF SCOPE**. Raid fight logs may serve generic ST/2T/AoE validation fixtures.

## Evidence matrix (each success is limited to its actual execution scope)

| Layer | Observation / run | Exact conclusion |
|---|---|---|
| Native SimC ST vs 2-target | [Actions 41422148326](https://github.com/degong2-code/zrotationhelper/actions/runs/41422148326), run commit `e15b790e870ab28b9d56ec138859f7374e3ad052` | **PASS**. Same official native executable, profile, effective APL, seed `31459`, fixed 75s fight, `desired_targets=1` vs `2`. Synthetic contract on Python 3.12 + 3.14, genuine native capture on Linux. |
| Real SimC first 15 seconds | Same run, small receipt artifact ID `13131110674` | ST 24 observed action records; 2T 24; common first 9 records. First difference (zero-based record index 9): ST `crushing_blow` @ 3800ms versus 2T `rampage` @ 3786ms. **Observed association only; not a priority or causal claim.** |
| SimC source pin | Same run | Upstream `simulationcraft/simc` commit `b522cded8c26b97dac03fdf56e57a03ec7e8faa6`; Fury profile `profiles/MID2/MID2_Warrior_Fury.simc` Git blob `3225992ed5b754ad5d61e8b785d9d859f1eed1be`; native binary SHA256 `f85553adbd4df104cd59f01be8543d620aefddd591d1f593f650932539e035f9`; effective APL SHA256 `98635a684638d241000c0f9b3a78b9eb43d9579b522f864b8aaf5ebaa159e737`. |
| WCL blind candidate lock | [Actions 41422536988](https://github.com/degong2-code/zrotationhelper/actions/runs/41422536988), commit `a8326e7373dcb83d1a7a5a470dc46e33201eea50` | **Offline synthetic PASS** on Python 3.12/3.14. Numeric cast-ID counts, checkpoint/replay input hash requirements and no pre-lock SimC semantic injection. **No live WCL ranker report was collected.** |
| Product scope continuity | [Actions 41423414896](https://github.com/degong2-code/zrotationhelper/actions/runs/41423414896), code HEAD `1061e9b9686b5f45402d25fa26a797eab4780a89` | PASS: complete scope lock, 14 mutation rejection cases, 5 **simulated** successor handoffs. Not 5 actual chats. |
| Fresh WCL collector | Earlier engine-first CI; `tools/engine_first/fresh_wcl_engine_v1.py` | Offline collection/replay and Strict PRE regressions exist; **actual high-ranker live production remains NOT RUN in this branch**. |
| Product output | Not yet validated | **General Rotation final IR NOT READY**; addon live API observability NOT VERIFIED; target-dummy feedback NOT READY. |

The native receipt from Actions has finite artifact retention (7 days in the workflow). Its SHA256 recorded in the branch handoff is `a878a2b5720e842faa14ac1375e526c153d7d1852033a3757b6097d88d393f37`. Do not assume the artifact remains downloadable after expiration, and do not mark a missing artifact as a regression of the historical successful run. Recollect new data with the engine when needed.

## Current implementation

- `tools/research/simc_native_reference_capture.py`: now supports optional `--targets`, `--seed`, `--fight-seconds`, recording control settings in native receipt.
- `tools/research/simc_native_target_count_compare_v1.py`: compares same pinned native profile/engine/seed/fight conditions; separates precombat/queued failures/waits and reports prefix/edit positions. Results are observational.
- `tools/engine_first/wcl_blind_numeric_candidate_lock_v1.py`: independent numeric-only WCL candidate lock from hashed FreshWCLReplayV1 input. This is **NOT** WCL high-ranker priority validation.
- `tools/research/post_lock_simc_wcl_guard_replay.py`: existing post-lock guard, can be used only **after** the independent numeric candidate lock.
- `tools/engine_first/fresh_wcl_engine_v1.py`: fresh authorized WCL snapshot/Strict PRE replay building block.
- `.github/workflows/zrot-general-rotation-st-vs-2t-native-simc.yml`, `zrot-wcl-independent-candidate-lock.yml`, `zrot-st2t-research-scope-survival.yml`.

Historical FROZEN remains untouched; `Seq578=FAILED_QUARANTINED`, `Seq637=UNKNOWN`.

## Unfinished work / blockers

1. No independently selected, legitimately retrieved **current high-ranker WCL report/fight/actor/spec/build cohort** validated here. Authentication/authorization and API point limits must be handled with the user's lawful credentials, without exposing secrets. A ranker's action choices without competing-action readiness are insufficient for a mandatory priority claim.
2. No locked discovery cohort vs independent holdout, no state-conditioned WCL-vs-SimC replay, no Blizzard spell/patch mechanic reconciliation for a current release.
3. SimC 1T/2T comparison is a **single-seed, single-profile illustrative sample**. Procs, resource timing and action availability may confound action choices even with the same seed; do not infer target-count breakpoint causality.
4. Precombat records and time-zero combat actions must be separated; a JSON2 action snapshot is **not automatically a Strict PRE state**. No same-timestamp or future transition may leak into an action-time state.
5. No proven complete opener, no ST/2T/AoE General Rotation IF/ELSE model, no verified target-dummy addon API/feedback.
6. Branch code and product state have **not been promoted to MAIN**. MAIN HEAD observed `4790f77f76a75f26ff0558d1d18c16cd9d630c4b`; docs-only PR #2 is **open Draft, not merged** (checked 2026-11-02). Do not silently promote or rewrite MAIN/shared/FROZEN state.

## Recommended near-term milestones

**N1.** Independently acquire a fresh high-ranker WCL sample via the authorized existing engine; verify report/fight/actor/spec/build identity, source and checkpoint/replay. Distinguish external data/access blocker from engine defect.

**N2.** Using **WCL-only numeric/state inputs**, reconstruct Strict PRE readiness and target exposure; predeclare discovery/holdout and lock blind candidate thresholds before accessing SimC labels. Missing state is UNKNOWN.

**N3.** Replay locked SimC opener/priority hypotheses against those WCL states, identify match/conflict/missing/unknown, reconcile Blizzard mechanic truth; use independent holdout / selective SimC counterfactual only for consequential unresolved rules.

**N4.** Produce a generic, confidence-bounded opener + conditional priority IR for ST/2T/cleave/AoE; prove second spec/build reuse without semantic hardcoding.

**N5.** Evaluate user dummy actions against **only verified/observable** rules. Test legitimate current Retail addon APIs before choosing live or post-session feedback.

**More efficient alternative:** reuse the pinned native SimC capture, WCL cold-start collector, Strict PRE replay and lock validator; batch discovery-independent actions and rerun a single reusable acceptance matrix. Do not recreate old MAIN, reimplement solved parsers, or spend API points on inconsequential precision debates.

## New-chat operating gate

The successor chat must **read sources and report the restored scope, current evidence, owner, blockers, exact next and any discrepancy; then STOP**. No coding, GitHub mutations, WCL/SimC live calls, workflow dispatch or approval/promotion **until the user says '진행' or explicitly authorizes an action**. Reporting is allowed to use read-only checks. Consult the branch-specific start prompt.


## Successor update — official ranker discovery / 2026-11-02

Branch-local development only; historical generation-1 handoff remains unchanged.

- Implemented `tools/engine_first/wcl_official_ranker_discovery_v1.py` (GitHub commit `e89d0c23171ae09c8b60ab182cc6b3aa6042884d`). Source SHA256 `15eec9f1e5ed6a4fa446c45925bf1617641cee381344b442e606dbc169c980b0` as printed by final CI both Python 3.12/3.14 jobs.
- Uses official `worldData.encounter.characterRankings` candidate ranks, then cross-checks official report metadata, report/fight/actor/spec/class, encounter/difficulty and report+fight age before bounded event collection. This is reusable across specializations via CLI arguments; it does not hardcode a Fury-only scientific decision in the engine.
- Added `.github/workflows/zrot-official-ranker-actor-scope-smoke.yml`, branch push smoke with 3.12/3.14 offline synthetic coverage and a single bounded live pilot requiring repository secrets `WCL_CLIENT_ID`, `WCL_CLIENT_SECRET`. Live query is limited to one page of rankings, maximum 3 candidate metadata checks and maximum 5 event pages, with no raw logs or secrets uploaded to CI artifacts.
- Actions run [41460152986](https://github.com/degong2-code/zrotationhelper/actions/runs/41460152986): offline 3.12 **PASS**, offline 3.14 **PASS**; live pilot job **SUCCESS/SKIP**, with explicit `SKIPPED_MISSING_REPO_SCOPED_OAUTH_SECRETS`. Therefore actual WCL API calls: **ZERO**, actual ranker observed: **NONE**, live raw snapshot and Blind Lock: **NOT RUN**.
- Recorded blocker type: **MISSING_EXTERNAL_CREDENTIAL_CONFIGURATION**; not a gameplay hypothesis failure, WCL GraphQL failure or demonstrated engine defect. No credential content was printed, stored or requested in chat.
- The pilot encounter 3420 (heroic, Fury) is a provisional discovery input from public season context, not independently established as the authoritative current-season reference. Real official zone/encounter/fight verification must pass on a credentialed run before any claim.
- Important bounds: rankings JSON is changeable and parser must fail closed on unexpected fields; rank does not imply action readiness/optimality. Talent build remains **UNKNOWN** until playerDetails/COMBATANT_INFO are verified. A single observed fight and cast-frequency lock cannot establish pairwise priority or independent holdout. Partial runs on ephemeral GitHub runners preserve status metadata only, not persistent raw checkpoint; use a controlled durable evidence store for production research.
- Next step: authorize repository-scoped WCL OAuth secrets securely (user action in GitHub Settings, not in chat), run the same bounded credentialed pilot, review exact result and API point use, then expand replay/readiness only when actual data validates the contract. Do not repeatedly rerun the skip or promote MAIN.


## Live WCL bounded opener E2E — 2026-11-02

This is a **branch-local research E2E result**. It does not promote General Rotation rules or modify MAIN/FROZEN.

- OAuth repository secrets `WCL_CLIENT_ID`/`WCL_CLIENT_SECRET` were successfully consumed by the bounded GitHub pilot without disclosure. Real official WCL `worldData.encounter.characterRankings` returned 100 rows in one requested page. Ranking JSON omitted numeric `rank`; therefore only `ranking_page_position=1` is observed, and **exact official numeric rank remains UNKNOWN**.
- After correcting rankless-JSON handling, adding official `Report.startTime` and `masterData.actors.name`, a fresh official report/fight/actor/spec/class/encounter/difficulty cross-check **PASSED**. The selected fight was about 3.98 days old at collection. This proves source join identity under the implemented contracts; player talent/build equivalence remains UNKNOWN.
- Prior full-fight `max_pages=5` test returned `PARTIAL_API_COLLECTION_CHECKPOINT_ONLY`. This was an intentionally bounded collection, not a collector crash; ephemeral runner checkpoint was not preserved in that attempt. No global promotion.
- Introduced an explicitly bounded **15,000 ms fight-start window** in `fresh_wcl_engine_v1.collect(window_ms=15000)` with distinct `COMPLETE_WINDOW` status, `full_fight_end`, and scope tag `FIGHT_START_BOUNDED`. `scope_replay` validates that the window end derives from the verified full fight metadata and cannot masquerade as full-fight completion. No SimC semantics are injected before candidate lock.
- Final successful bounded E2E run: [GitHub Actions #41463589665](https://github.com/degong2-code/zrotationhelper/actions/runs/41463589665), head `d1f2b82c9d4958fe3e28daafbe2530992d0c68e1`, three jobs **SUCCESS** (Python 3.12 offline; Python 3.14 offline; actual OAuth WCL pilot).
  - Actual official WCL API: **EXECUTED**. Retrieved **17,083 raw events** in **2 pages** for the first **15 seconds**, `window_completed=true`, `full_fight_completed=false`.
  - Actor-scoped numeric Strict PRE and independent observational Blind Lock: **COMPLETE**, **4 numeric cast-frequency candidates**. Lock SHA256 `c5e2bedeb7f4f0152e8ba86a30b1b13ecc5aa1374af4c0b01237a16151a1c98e`.
  - A separate CI step re-read all source snapshot page hashes, replayed them, and recalculated actor-view/lock fingerprints: `LIVE_WCL_RAW_REPLAY_AND_BLIND_LOCK_REVALIDATED=PASS`. This is a same-run artifact check, **not an independent producer/validator implementation or independent holdout**.
  - Raw pages, checkpoint, actor-scoped replay, identity receipt, numeric lock, and ranking selection archived to [Actions Artifact #13149059210](https://github.com/degong2-code/zrotationhelper/actions/runs/41463589665/artifacts/13149059210), 7-day retention, ~475 kB compressed. Metadata [Artifact #13149403224](https://github.com/degong2-code/zrotationhelper/actions/runs/41463589665/artifacts/13149403224). Artifacts are **temporary**, not FROZEN, MAIN, or a production canonical baseline. No OAuth secret is in those outputs.
  - Final ranker script SHA256 at Python 3.12 CI: `e6897caa9dafc14d6c9bc52db164b6ee9881d4ff08db22e5a82df1dcffafefcd`.
  - Actual API points: **NOT_MEASURED**. Dynamic WCL ranking JSON exact-rank semantics: **UNKNOWN**. Combatant talent build: **UNKNOWN**. Competing-action availability/cooldown/resource readiness: **UNKNOWN**.
  - No real independent holdout, no current-season mechanic truth reconciliation, no full-APl post-lock replay and **no General Rotation rule validation**. Cast frequency is not optimality or priority.
- Engine-first session objective (fresh new data acquisition + actor isolation + numeric blind prelock) **implemented and live-tested**. Next research work is to use the retained artifact as an independent raw input, recover build/readiness where officially observable, declare and lock discovery/holdout cohorts, and perform **post-lock** SimC hypothesis comparisons. Do not confuse this bounded opener sample with complete ST/2-target/AoE model coverage.


## Post-lock WCL ↔ SimC numeric research E2E — 2026-11-02 follow-up

This is an observed **post-lock comparison**, **not** a validated General Rotation IF/ELSE model or evidence of optimality.

- Input A: actual official WCL Fury 15-second opener, 17,083 raw events across 2 pages and 54 actor cast events; immutable numeric blind lock SHA256 `c5e2bedeb7f4f0152e8ba86a30b1b13ecc5aa1374af4c0b01237a16151a1c98e`.
- Input B: pinned, previously produced native SimC Fury ST/2-target 15-second receipt, whose public artifact contains only the **first 12 action records** per target count. Public receipt SHA256 `a878a2b5720e842faa14ac1375e526c153d7d1852033a3757b6097d88d393f37`. SimC native simulation was **not rerun** in this audit.
- Implemented generic comparison kernel `tools/research/wcl_simc_postlock_real_audit_v1.py` and separate fixed-source/spec identity contract `docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/POSTLOCK_FURY_WCL_SIMC_FIXTURE_V1.json`. Scientific source spell ID semantics and Fury specifics are **not hard-coded** as generic engine priority; fixture input pins source hashes, actor and diagnostic numeric ID.
- [Actions #41466009694](https://github.com/degong2-code/zrotationhelper/actions/runs/41466009694), head `8c8d0e8cdec5443e9e62cce081f8d3d9390740bf`: offline Python 3.12/3.14 PASS; real external artifact pull & recomputation PASS; WCL raw page SHA/checkpoint and Strict-PRE aura state independently rebuilt and match existing actor replay; tampered immutable lock rejected *before* SimC input accessed. Generic kernel SHA256 `9245ce5324b9e01078d03c38fa923c2fe44d9df38cd4e90f4e08522d84cc03da`.
- Real evidence audit receipt SHA256 `20bc99fd1b9fd73f55ce9f12d94389afaed97a30541dbf57526385015183f534` from final Actions run, retained [Artifact #13151675454](https://github.com/degong2-code/zrotationhelper/actions/runs/41466009694/artifacts/13151675454), expiring 2026-11-09. Source raw and SimC archives also have 7-day retention; do not assert permanent evidence availability after expiry.
- The 4 prior-lock numeric candidates are `1 × 30`, `184367 × 9`, `335096 × 2`, `335097 × 6`. Numeric spell `1` has 30 `cast` and 30 `damage` records in this window, **post-lock auto-attack hypothesis only**; not a player-button priority and not removed from the original immutable lock.
- Numeric ID overlap between WCL 15s and only the **public SimC first-12 prefix**: ST `{100,1719,184367,335097,446035}`; 2T `{100,1719,184367,446035}`. SimC target-count sample divergences remain **observational**; compare does not execute a full APL or certify each WCL decision.
- Unknowns not promoted: WCL exact target count at decision, target count threshold, player/SimC talent build equivalence, cast readiness/competing available actions, independent holdout, Blizzard mechanic truth, causal target-count effect, priority/optimality, and dummy trainer model. **Final rotation and mistake rules remain NOT VALIDATED.**
- Next prioritized work: declare a separate **disjoint source cohort** with independent holdout selection/lock contract before additional WCL exposure; capture bounded opener(s), recover observable combatant build and resource evidence with Strict PRE, then carry out more complete guard/action replay without using new evidence to retune original thresholds. Keep SimC-first global flow and WCL blind internal discovery boundary.
