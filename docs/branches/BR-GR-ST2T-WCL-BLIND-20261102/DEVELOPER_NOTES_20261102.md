# zRotationHelper — Engine Research Developer Notes (2026-11-02)

**Status:** Branch-local engineering plan and integration guard; not a new product scope or an authoritative MAIN promotion.

## 1. Scientific and product contracts

- Official product scope lock: `docs/PRODUCT_SCOPE_LOCK_V1.json` (`ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`), SHA256 `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`.
- Product endpoint: **general opener and conditional spell priorities** with target-count/build/resource/proc/charge/execute changes, plus **lightweight target-dummy practice feedback**. Raid execution, Encounter Rotation Plans, NSRT and boss timelines are excluded.
- Whole research is **SimC-first**: APL/profile baseline hypotheses → independent high-ranker WCL validation/correction → evidence-bounded General Rotation. WCL Blind is an isolated verification lane; do not feed spell names, SimC priorities or guides into numeric candidate discovery before lock.
- Observation ≠ readiness ≠ causality ≠ optimality. `state_at_action(t)` uses latest valid event with timestamp strictly `< t`. Same-timestamp and future events are not PRE.
- Source-derived APL rows are conditional *hypotheses*. A successful native SimC execution proves an execution sample for that profile/seed/conditions, **not** a verified player optimum or the full opener in current Retail.

## 2. Code that already exists — reuse, do not rewrite

| Layer | Existing entrypoint | Exact use |
|---|---|---|
| SimC native reference | `tools/research/simc_native_reference_capture.py` | Existing CLI and receipt; optional `--targets 1/2 --seed 31459 --fight-seconds 75`. Pin executable/profile/APL identity. No-args safe offline selftest. |
| SimC JSON2 parsing | `tools/research/simc_native_json_sequence.py` | Identify `action_sequence_precombat`, combat `action_sequence`, queue failures, waits and observed snapshots. Do not reclassify them as casts. |
| Native action extraction | `tools/research/simc_native_performed_events.py` | Use executable-format-informed native log parser rather than an additional regex implementation. |
| ST vs 2T comparison | `tools/research/simc_native_target_count_compare_v1.py` | Require same binary/profile/effective APL/seed/duration, target count 1 vs 2; output observational action alignment. |
| SimC structural IR | `tools/research/simc_apl_source_engine.py`, `simc_apl_conditional_ir.py`, `simc_apl_decision_graph.py` | Reuse for opener/IF-ELSE source hypothesis; precombat directives ≠ complete combat opener. |
| Fresh WCL E2E | `tools/engine_first/fresh_wcl_engine_v1.py` | Cold-start authorized collection, snapshot, checkpoint/resume, identity and strict PRE replay. Distinguish external API deletion/restrictions from engine failure. |
| Blind numeric candidate lock | `tools/engine_first/wcl_blind_numeric_candidate_lock_v1.py` | Consume verified `FreshWCLReplayV1` numeric snapshots only; lock before any SimC semantics. Current CI covers synthetic fixtures, not actual WCL rankers. |
| Post-lock comparison guard | `tools/research/post_lock_simc_wcl_guard_replay.py` | May consume fixed WCL lock *after* freeze/lock; compare SimC replay predictions separately. |
| Product continuity | `tools/governance/validate_scope_continuity_v1.py` | Scope integrity, handoff snapshot and 5 synthetic successor generations. |

## 3. Baseline evidence and exact test limits

**Pinned SimC source:** `simulationcraft/simc@b522cded8c26b97dac03fdf56e57a03ec7e8faa6`; Fury profile Git blob `3225992ed5b754ad5d61e8b785d9d859f1eed1be`.

**Native controlled ST/2T run:** Actions `41422148326` at commit `e15b790e870ab28b9d56ec138859f7374e3ad052`: 1T/2T 24 first-15-second action records each, common first 9. First divergent record (index 9): ST `crushing_blow` @3800ms vs 2T `rampage` @3786ms. Same native profile/APP/seed/window does **not** prove deterministic causal target selection. Profiler artifacts can expire; compare hashes before any reuse.

**WCL Blind candidate lock:** Actions `41422536988` at commit `a8326e7373dcb83d1a7a5a470dc46e33201eea50`, Python 3.12/3.14 offline synthetic PASS; **WCL raw ranker acquisition NOT RUN**. Pairwise action availability and holdout not proven.

**Scope regression:** Actions `41423414896` at code HEAD `1061e9b9686b5f45402d25fa26a797eab4780a89`, synthetic 5 future handoffs and 14 negative mutations PASS. Simulated tests are not real handoffs. The new handoff's own validation must be checked separately.

## 4. Next implementation batch — optimize for information gained per run

Do **not** build a new special-case Fury rotation or a raid plan. Use one engine-side batch that delivers all independent prerequisites:

1. **Fresh WCL acquisition contract:** select a public/current high-rank report/fight, identify player+spec+build and target/encounter eligibility. Use only legitimate credentials via approved secrets/env. Record source, identity, GraphQL responses, cursors, point usage, checkpoint and failure category. A WCL endpoint error or missing old report is external-data status until diagnosed, not automatically an engine defect.
2. **Strict PRE and blind lock:** derive numeric cast/auras/target state from transitions strictly earlier than each action. Keep readiness UNKNOWN where buffs, cooldowns, resources, target context, or talent-derived availability are unobservable. Predeclare discovery cohort and candidate/threshold criteria; lock numeric candidates without SimC answer leakage. Holdout must be separate and not used to retune thresholds.
3. **Only post-lock** attach spell identity, compare against SimC baseline, label `MATCH / CONFLICT / MISSING / UNKNOWN`. For high-impact unresolved pairwise priority, request independent holdout or selective SimC counterfactual rather than guessing.
4. **Generic output contract:** `state predicate → recommended action → alternative → priority → observational limits → evidence IDs/confidence`; opener vs post-opener separated; ST/2T/cleave/AoE transitions. Keep specialization semantics in SpecAdapter or equivalent instead of hardcoding in generic engine.
5. **Dummy feedback later:** record user actions via supported WoW Retail APIs or a post-session combat log; only compare against sufficiently validated rules. Avoid secret/protected combat value bypass, arbitrary addon file IO or combat automation.

**Efficient alternative to repeated "review → fail → review":** batch independent implementation/instrumentation in one branch, run the same reusable synthetic matrix and one bounded fresh data E2E pass, classify the failure (scientific hypothesis, source/API constraint, engine defect) once, and fix the narrow component. Recollect evidence instead of indefinitely reconstructing old FROZEN code.

## 5. Reusable acceptance gates / reporting language

Use a single verification table per change with the following dimensions; never collapse them into a bare `PASS`.

- **static/compile**: final delivered file compilation (and Python 3.12/3.14 where applicable).
- **self-test/synthetic**: final file's own selftest, fixed test input hashes, strict PRE same-time rejection and readiness UNKNOWN.
- **offline artifact**: binary/source/receipt SHA256, actor/fight identity and deterministic replay, changed-file vs tested-file identity.
- **actual native SimC**: source revision, profile, binary hash, seed, fight/targets, observed action sequence. Do not label this WCL validation.
- **actual WCL ranker**: authorized live API, report/fight/player/spec/build identity, replay, blind lock, cohort/holdout and raw provenance.
- **post-lock General Rotation**: major SimC/WCL discrepancies, mechanics truth, rules and alternatives/limits, independent replication proportional to impact.
- **dummy client capability**: real addon API observation matrix, supported live vs post-session path; no unsupported conclusions.
- **scope continuity**: policy ID, full snapshot SHA256, proper parent handoff SHA256 and generation, first response STOP instruction, no shared MAIN pointer changes.

Run only tests whose inputs you actually have. `UNKNOWN` is not `FAIL`, and offline synthetic PASS is not actual production PASS.

## 6. GitHub and authority boundaries

Use branch `work/gr-simc-st-2t-wcl-blind-20261102`. Its latest handoff lives at `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json`. MAIN observed HEAD `4790f77f76a75f26ff0558d1d18c16cd9d630c4b`; docs-only Draft PR #2 remains unmerged. Do not mutate `CURRENT_STATE`, global `LATEST_HANDOFF.json`, authoritative architecture/semantic contracts, FROZEN, `Seq578=FAILED_QUARANTINED`, `Seq637=UNKNOWN` from a research branch.

The repository tree on this research branch does not contain a local copy of `ROTATION_RESEARCH_SYSTEM_CORE_CONTRACT_V1.md` or the Project-source Playbook. If those are needed, read the user's Project Sources explicitly. The Playbook clarifies that SimC-first is the global flow and WCL blind candidate lock is internal; do not invent a different authority based on historical WCL-first notes.

## 7. Immediate next chat: **RESTORE ONLY, THEN STOP**

Before the next user's explicit `진행`: read-only HEAD/CI/source inspection and a concise restoration report are allowed. **Do not implement, run simulations/collect WCL, trigger workflows, write files, create branches/commits/PRs, or change promotion pointers.** After reporting the exact restored goal, evidence ranges, blockers and both Exact Next fields, wait for user instruction. No background execution.


## 2026-11-04 verified SimC-first handoff successor

Historical sections above include superseded "collect WCL next" directions; latest **user mandate** is to FINISH APL → Native-equivalent reusable General Rotation **engine before** WCL comparison or addon expansion. New canonical branch-local short status: HANDOFF_STATUS_20261104.md; detailed feature/source/receipt reuse index: FEATURE_EVIDENCE_REUSE_INDEX_20261104.md; generation-2 LATEST_HANDOFF and NEW_CHAT_START_PROMPT_20261104.md. The latest Native operand proof is **66/477** cases (3 numeric + 63 logically partial), **411 UNKNOWN**; 477-row ledger cheap offline recheck uses the same Python evaluator, not a second independent oracle. Native ST/2T selected-root structural match requires Native ready() booleans. Reuse earlier resource/variable/IF instrumenters; implement a minimal *generic* provenance-gated operand provider before new pipelines. Missing evidence ≠ code not written ≠ product model validation. New chat FIRST RESPONSE READ-ONLY RESTORE AND STOP until '진행'.
