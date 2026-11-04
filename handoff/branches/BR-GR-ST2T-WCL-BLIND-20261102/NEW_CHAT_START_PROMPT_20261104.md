# zRotationHelper — NEW CHAT START PROMPT / Read-only restore (2026-11-04)
다음 본문을 **새 zRotationHelper 채팅 첫 메시지**로 사용한다.

---

zRotationHelper **General Rotation Research Engine / Lightweight Target Dummy Trainer** 최신 인계를 복원하라.

**절대적인 첫 응답 규칙: READ-ONLY RESTORE → REPORT → STOP.** 최신 GitHub HEAD·범위 정책·현재 증거·완료/미완료·장단기 로드맵을 독립 대조하여 **복원 보고만** 하라. 사용자의 명시적 **'진행'** 전에는 **코드 작성·수정, 파일 커밋·push·PR, Actions 재실행/dispatch, Python/SimC 실행, 신규 WCL/API 수집, 애드온 실행, 작업 병합·MAIN/FROZEN 승격을 절대 시작하지 마라**. 읽기 전용 GitHub 조회와 자료 확인만 허용한다. 문서가 오래됐으면 사실을 보고하되 임의로 갱신하지 않는다. 첫 보고 후 중단한다.

## Repository / identity
- GitHub: degong2-code/zrotationhelper
- Isolated research branch: work/gr-simc-st-2t-wcl-blind-20261102
- Branch owner: BR-GR-ST2T-WCL-BLIND-20261102
- Branch HEAD **before this documentation handoff**: 502e2e9c8364034d7b485c86aa5d49bcc0d8476b; MUST fetch **actual latest branch HEAD**, which has changed after handoff commit.
- Observed MAIN HEAD (read-only): 4790f77f76a75f26ff0558d1d18c16cd9d630c4b; independently re-query.
- Active policy: ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1
- Policy complete SHA256: 157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295; Git blob SHA1: 14b9f5174a9d1652a56dcca03af1f2302b78c22d.
- New branch handoff: _UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json (generation 2); prior exact generation-1 archive: _UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/archive/LATEST_HANDOFF_GEN1_20261102.json; parent SHA256: f2c4181a31662fa8868705b3d0ff949443017da9c73e07a5517f531a588ad2c1.

## Read order, each chat
1. docs/PRODUCT_SCOPE_LOCK_V1.json (policy full object) and docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md.
2. AGENTS.md and docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md.
3. docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md, then branch-local LATEST_HANDOFF.json; validate policy snapshot, generation 2 and archived parent SHA using read-only inspection.
4. docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/HANDOFF_STATUS_20261104.md (short verified checkpoint), FEATURE_EVIDENCE_REUSE_INDEX_20261104.md (exact code/source/receipts), SIMC_APL_MODEL_COMPLETION_CONTRACT_20261103.md.
5. docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/DEVELOPER_NOTES_20261102.md and CURRENT_STATUS_20261102.md for extended history; inspect only necessary code and CI runs. Feature sources should be examined before any later change.
6. Project sources: GENERAL_ROTATION_PLAYBOOK_DUAL_LANE_SUCCESSOR_PROPOSAL_v2.md, PARALLEL_WORKSTREAM_AND_MERGE_CONTRACT.md, relevant generic rotation Core Contract. Older raid/NSRT handoffs are historical only.

## Goal, current work and proof boundary
**The final goal is a reusable, general-purpose ENGINE**, not a handcrafted Fury skill list or standalone addon. Derive accurate SimC APL opener and priority behavior across specialization/build/target counts. Then validate against separately locked WCL discovery cohorts and official Blizzard mechanics, producing ST/2T/cleave/AoE IF/ELSE General Rotation IR. Only then implement evidence-bounded target-dummy practice feedback; never use restricted WoW addon APIs, and return UNKNOWN when readiness is unobserved. Encounter-specific raid rotation, boss timelines, NSRT outputs excluded.

**Current explicit user priority** overrides old handoff's "collect WCL next" instruction: **complete exact SimC APL → independent Native-tested General Rotation model FIRST**. Preserve WCL blind as separate research lane but pause new WCL comparison and dummy-addon work.

Latest confirmed implementation:
- Fury 121/121 SimC AST rows and Enhancement 114/114 source syntax, CI 41563832907.
- Fury 121/121 official Native effective APL match, CI 41563013349.
- Native ST+2T 214 foreground scans / 190 chosen source rows structurally reproduced using **Native ready bits**, CI 41580466416; this is NOT independent readiness parity.
- 477 genuine Native IF evaluations / 2,572 readiness attempts. 2,095 never observed IF result, not proof of FALSE.
- 66/477 Native IF comparisons independently calculated by Python AST from PRE Rage/enemy count (3 all-known + 63 logically decisive partial); 411 UNKNOWN, official Native result **comparison only**. CI 41584822737.
- Frozen 477-row ledger replay CI 41585210821 reproduces 66/411 **without native recompilation**; same Python evaluator, **not** second independent semantic oracle.
- Historical WCL real discovery 54 casts and disjoint-report holdout 51 casts **already exist** (runs 41463589665 and 41473060401); do NOT trust older 2026-11-02 handoff "WCL NOT_COLLECTED" fields. No full gameplay priority validation.
- Dummy prototype isolated and offline only, no actual in-game test.

**Status:** source compiler substantial, Native IF parity partial, complete opener and conditional General Rotation model **NOT FINISHED**. Hero talents, buff.recklessness.up, variable.*, broader aura/proc/resource/cooldown/charge/GCD/target-count state, second-spec native behavior and true user errors remain unproven. Time-limited artifact receipts around 2026-11-10 UTC; do not make expired old artifacts a permanent blocker.

## Engine-first rule and after-approval exact next
**Before EVERY proposed task**, first search existing historical/feature index, raw sources, code, receipts and GitHub run proof. Classify REUSE/EXTEND/REPLACE/UNKNOWN; **do not re-implement existing validated functions or rerun costly Native SimC without a new evidence need**. Batch independent work, share the same completion tests, use deterministic inputs, separate scientific hypothesis FAIL from pipeline/API FAIL, preserve strict PRE (event.timestamp < action.timestamp), readiness UNKNOWN and candidate-lock independence. Never treat CI PASS count as product progress; prefer the smallest verified, generic engine delta. Generic layer cannot hardcode Fury/boss semantics; use a SpecAdapter.

**Only after a new explicit '진행'**: inspect existing SimC operand/variable/provider source, extend a minimal generic source-backed pre-IF observation for high-impact missing facts (first Recklessness buff, hero talent branches, variable.*), replay existing pinned 477-row ledger offline cheaply, run Native once only if new facts truly require it. Compare evaluated expressions and stateful selected action decisions without feeding Native final Boolean result into the model. The broader product next is complete SimC-accurate General Rotation engine → WCL/Blizzard correction → dummy training.

## Required initial reply (do not perform follow-on work)
Report (1) unchanged product scope and generic engine objective, (2) actual GitHub HEAD/main/policy and handoff continuity, (3) evidence-grounded done/undone/UNKNOWN and CI claim limits, (4) missing evidence versus product integration deficits, (5) reuse efficiency and long/short roadmap, (6) Product Exact Next and Session Exact Next, (7) user action. Distinguish verified GitHub reads from stale documents; explain if any source is inaccessible. **No write/test/run in initial reply.** End literally:

**복원 보고를 완료했습니다. 사용자의 '진행' 지시를 기다립니다.**
