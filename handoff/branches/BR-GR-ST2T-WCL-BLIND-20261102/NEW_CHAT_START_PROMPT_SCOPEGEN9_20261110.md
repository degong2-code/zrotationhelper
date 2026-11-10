# zRotationHelper — Scope Gen9 읽기 전용 독립 복원 (2026-11-10)

**첫 응답은 GitHub 읽기 전용 복원·검증·보고 후 반드시 중단한다.** 이전 채팅의 `진행` 승인은 승계하지 않는다. 새로운 채팅에서 사용자가 별도 **'진행'**이라고 지시하기 전에는 코드·문서 수정, 새 테스트, SimC/WCL/Blizzard/API 호출, Actions, 커밋·PR·병합·MAIN/FROZEN 승격을 하지 않는다.

## 저장소·권한·정본

- Repo: `degong2-code/zrotationhelper`; owner: `BR-GR-ST2T-WCL-BLIND-20261102`; 격리 브랜치: `work/gr-simc-st-2t-wcl-blind-20261102`; 기준 `main`.
- 인계 준비 당시 HEAD: branch `2ba1a5cdfdb86bb458b2dc2eb5d852a5d396f41f`, main `4790f77f76a75f26ff0558d1d18c16cd9d630c4b` — **참고값, 시작 시 독립 재조회 필수**.
- 최신 단일 인계 정본: `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json` (**Scope Gen9**). full policy snapshot와 policy SHA256 `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`.
- 보존 Gen8: `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/archive/LATEST_HANDOFF_SCOPEGEN8_BEFORE_20261110.json`, 원본 바이트 SHA256 `e9ab9c45f13097d23a6141b5789f5653c7f2273d058d91acf88ab7cf9ee4a557`, 원본 Git blob `941d66a3a4c5bfcaa2651bc1dd7fd3094db9b6d2`. Gen7 SHA `ad5a68834f6341029ba7933e25ef65c06f771c1aba0b960508836bb10da577c6`; Gen6 `5df57d1c4577bbf408bb5016f5f2001ad7511c15986192c62e725834ba7f6010`; Gen5 `ab04457130b37bce8c55e359e60c77a75d9abcfd5f8806da952d8fc070742bd5`. 새 채팅에서 실제 파일 내용과 재계산해야 한다.
- MAIN만 공유 CURRENT_STATE, 정책·정본·IR baseline, global handoff, 기존 FROZEN을 승격한다. 다른 활성 채팅의 최신 소유권은 미확인; 브랜치 충돌 전 HEAD부터 확인한다.

## 공식 제품 목표

`ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`: 모든 전문화에 재사용 가능한 **General Rotation** SimC APL/profile 오프닝/우선순위 가설 → 독립 WCL blind 후보 잠금 → Strict PRE readiness/IF 및 호출 경로 검증 → 잠금 후 WCL·Blizzard mechanic 대조 → 현재 Retail ST·2타겟·cleave·AoE IF/ELSE와 opener 종료 → 같은 모델로 허수아비 연습 오류 설명. 비관측 readiness는 UNKNOWN. **Encounter/raid execution, NSRT/보스 타임라인은 범위 밖.** 과거 FROZEN, `Seq578=FAILED_QUARANTINED`, `Seq637=UNKNOWN` 불변.

## 필수 읽기 순서

1. `docs/PRODUCT_SCOPE_LOCK_V1.json` → `docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md` → `AGENTS.md` → `docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md` → `docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md`.
2. 위 Gen9 `LATEST_HANDOFF.json`, 원본 Gen8/Gen7/Gen6 archives (필요 시 Gen5); 정책 snapshot 및 parent SHA256 검증.
3. `docs/CURRENT_RESEARCH_STATUS.md` → `docs/RESEARCH_INDEX.md` → `docs/FEATURE_HISTORY_INDEX.md` → `docs/EVIDENCE_NAVIGATION_INDEX.md` → `docs/GENERAL_ROTATION_PER_SPEC_MODEL_INDEX.md`.
4. `docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/HANDOFF_STATUS_20261109.md`, `FEATURE_EVIDENCE_REUSE_INDEX_20261105.md`, `DEVELOPER_NOTES_20261105.md`, 그리고 링크된 해당 코드·증거·CI만 선별 조회.

## 실제 검증 상태 (새 채팅에서 다시 대조)

- 3전문화 286 APL행/19리스트; source-only Markdown 3 + JSON 3, [CI #42747802703](https://github.com/degong2-code/zrotationhelper/actions/runs/42747802703). 원본 Native 1/2/3/5타겟 총 12사례, 행동 464건, 첫 10초 185건(오프닝 종료 증명 아님).
- 고술 정확 SELECT root: ST 40 + AoE 39 = 79건. 독립 IF MATCH 5 / 명시 IF 없는 경우 15 / 독립 PRE 부족 59 UNKNOWN. Native POST TRUE를 독립 PRE로 쓰지 말 것. [#42749660209](https://github.com/degong2-code/zrotationhelper/actions/runs/42749660209) · [#42750471988](https://github.com/degong2-code/zrotationhelper/actions/runs/42750471988) 통과.
- Gen8 이후 Generic original source Native 확장: [candidate-stage #42776023820](https://github.com/degong2-code/zrotationhelper/actions/runs/42776023820), [foreground membership #42778722554](https://github.com/degong2-code/zrotationhelper/actions/runs/42778722554), [create/init lifecycle #42786821103](https://github.com/degong2-code/zrotationhelper/actions/runs/42786821103), [cross-class spell dependency #42792819485](https://github.com/degong2-code/zrotationhelper/actions/runs/42792819485). AoE source `sundering` 행은 원본 Native POST_CREATE부터 `s_data=not_found/background=1`, 실행 foreground 제외, ready 호출되지 않음.
- 최신 특성 해시/DBC generic `tools/research/general_rotation_original_talent_hash_dbc_v1.py`, source pin `b522cded8c26b97dac03fdf56e57a03ec7e8faa6` 및 trait 3435 rows. [CI #42795917750](https://github.com/degong2-code/zrotationhelper/actions/runs/42795917750) Python 3.12/3.14 2/2 PASS. 고술 원본 프로필 `spec263`: Sundering node80975 entry101841 spell197214 **source profile not selected/not starter-granted**. Fury 원본 프로필 `spec72`: Bloodthirst node90392 entry112261 spell23881 rank1 selected (**source-only**, Fury Native READY 아님). 영수증 `active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_PINNED_TALENT_HASH_DBC_SUCCESSOR_20261110.json`.
- 이 모든 검증은 **핀 고정된 SimC/DBC/부분 Native 선택 경로**에 대한 것. 현재 Retail 메커니즘, 유저 빌드와 동시 사용 가능한 모든 스킬의 물리적 READY, 오프닝 종료, 완성된 General Rotation priority, 새 WCL blind postlock 및 실제 허수아비 오답 모두 미검증. 유저 규칙 승격 0개. 과거 FROZEN 변경 0.

## 개발 재개 (새 채팅의 별도 승인 이후에만)

**Product Exact Next:** 전문화별 General Rotation opener 및 ST/2타겟/cleave/AoE 조건부 IF/ELSE 모델을 독립 WCL 검증으로 완성하고, 같은 IR로 허수아비에서 실제 행동을 UNKNOWN-safe 평가.

**Session Exact Next:** 고술 79 source-root 중 제품 영향이 큰 ST·AoE 몇 개만 선정. 기존 generic profile talent/hash/DBC 및 Native source→객체/foreground/lifecycle/IF 증거를 **REUSE+CONNECT**하고, 동일 호출의 Strict PRE에서 상위 경쟁 스킬의 IF·물리적 readiness 및 ordered CALL/RUN을 확인한다. SimC 의미론을 blind WCL 잠금 이전에 주입하지 않는다. 필요 없는 재수집·전면 원본 빌드·새 추상화는 **STOP**. 현재 Retail Blizzard mechanic truth와 독립 holdout 이후에만 규칙 승격.

**첫 응답 계약:** 실제 branch/main HEAD, Gen9 정책·Gen8/7/6/5 연결, 검증된 새 Native/DBC 결과와 한계, 구현/증거/제품 연결 미완료, 실패와 UNKNOWN 구분, 병목, 단기·중장기 로드맵, Product/Session Exact Next와 사용자 조치를 보고한 후 중단한다.

마지막 문장은 반드시 다음과 같이 한다.

복원 보고를 완료했습니다. 사용자의 '진행' 지시를 기다립니다.
