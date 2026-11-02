# zRotationHelper — BR-GR-ST2T-WCL-BLIND-20261102 Current Status

**As-of verification:** 2026-11-02 (Asia/Seoul)  
**Owner:** `BR-GR-ST2T-WCL-BLIND-20261102` — branch-local research, not MAIN promotion  
**Observed code HEAD BEFORE this handoff update:** `1061e9b9686b5f45402d25fa26a797eab4780a89`  
**Official policy:** `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`; lock SHA256 `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`  
**Canonical current handoff:** `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json`. Read this for the complete policy snapshot and latest chain; this note is explanatory, not an alternative pointer.

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
