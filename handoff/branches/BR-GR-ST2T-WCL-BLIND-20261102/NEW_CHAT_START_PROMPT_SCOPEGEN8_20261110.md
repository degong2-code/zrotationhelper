# zRotationHelper — 새 채팅 독립 복원 (Scope Gen8, 2026-11-10)

**첫 작업은 읽기 전용 복원·검증·보고 후 중단한다.** 이 새 채팅에서 사용자가 별도로 **'진행'**이라고 지시하기 전에는 코드·문서 수정, 새 테스트, SimC/WCL/Blizzard API 호출, GitHub Actions 실행, 커밋·PR·병합·MAIN 승격을 시작하지 않는다. 이전 채팅의 승인은 승계하지 않는다.

## 공식 제품 목표와 저장소

- 정책: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`; 정책 원본 SHA256 `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`.
- GitHub: `degong2-code/zrotationhelper`.
- Branch owner: `BR-GR-ST2T-WCL-BLIND-20261102`. 격리 브랜치: `work/gr-simc-st-2t-wcl-blind-20261102`. 통합 기준: `main`.
- 인계 준비 시작 시 브랜치 HEAD `9832f0a889405f69cbf1da2cd303b85149063a78`, main HEAD `4790f77f76a75f26ff0558d1d18c16cd9d630c4b`. **둘 다 참고값일 뿐 새 채팅에서 반드시 독립 재조회할 것.**
- 단일 최신 인계: `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json` (**Scope Gen8**).
- 역사 연결: `archive/LATEST_HANDOFF_SCOPEGEN7_BEFORE_20261110.json`의 원본 바이트 SHA256 `ad5a68834f6341029ba7933e25ef65c06f771c1aba0b960508836bb10da577c6`; 이전 Gen6 SHA256 `5df57d1c4577bbf408bb5016f5f2001ad7511c15986192c62e725834ba7f6010`, Gen5 SHA256 `ab04457130b37bce8c55e359e60c77a75d9abcfd5f8806da952d8fc070742bd5`. 최신 인계의 **전체 정책 스냅샷, parent SHA, generation+1**을 파일 원문과 대조한다.

## 반드시 먼저 읽을 것 (효율적인 순서)

1. `docs/PRODUCT_SCOPE_LOCK_V1.json`
2. `docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md`
3. `AGENTS.md`
4. `docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md`
5. `docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md`
6. 위 Gen8 `LATEST_HANDOFF.json`, 보존된 Gen7과 Gen6 원본
7. `docs/CURRENT_RESEARCH_STATUS.md` → `docs/RESEARCH_INDEX.md` → `docs/FEATURE_HISTORY_INDEX.md` → `docs/EVIDENCE_NAVIGATION_INDEX.md` → `docs/GENERAL_ROTATION_PER_SPEC_MODEL_INDEX.md`
8. 최근 상세 `docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/HANDOFF_STATUS_20261109.md`, `FEATURE_EVIDENCE_REUSE_INDEX_20261105.md`, `DEVELOPER_NOTES_20261105.md`, 필요 시 worklog/branch 운영 계약. 해당 인덱스가 가리키는 원본 코드·영수증·CI만 선별 점검.

## 검증된 최신 제품 구현과 한계 (숫자 합산 주의)

- 원본 SimC pin `b522cded8c26b97dac03fdf56e57a03ec7e8faa6`. 3개 전문화(고술 114, 분전 121, 비법 51)의 APL 286행 / 19 리스트를 범용 SimC 원본 파서가 보존. 각 전문화별 **Markdown + JSON** General Rotation *소스 가설* 생성: [CI #42747802703](https://github.com/degong2-code/zrotationhelper/actions/runs/42747802703) 3/3 PASS.
- Native 원본 행동 표본: 고술·분전·비법 각각 1/2/3/5타겟, 별도 Native 실행 코호트 총 12사례·464개 행동, 첫 10초 185개. [CI #42745179980](https://github.com/degong2-code/zrotationhelper/actions/runs/42745179980) PASS. **첫 10초는 증명된 오프닝 종료가 아니다.**
- **가장 최신 Gen7 이후 실제 구현:** 고술 1타겟/ST 40행, 3타겟/AoE 39행 원본 SimC **정확한 SELECT 소스 행·호출 ID 및 부분 PRE 79건**을 114행 General Rotation 소스 모델에 증거로 병합. 독립 PRE로 원본 IF TRUE/Native 일치 **5건**, 명시적 IF 없는 원본 선택 **15건**, 결정적인 PRE 부족 **59건 UNKNOWN**. 독립 소스 계측 [#42749660209](https://github.com/degong2-code/zrotationhelper/actions/runs/42749660209) 3/3 PASS; 증거 병합 [#42750471988](https://github.com/degong2-code/zrotationhelper/actions/runs/42750471988) 3/3 PASS. 첫 병합 CI [#42750341471](https://github.com/degong2-code/zrotationhelper/actions/runs/42750341471)은 Native POST의 TRUE를 미관측 독립 PRE로 잘못 취급하는 실패를 드러내어 수정했다. 따라서 **59 UNKNOWN을 TRUE로 승격하지 않는다.** 정본 영수증: `active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/SHAMAN_GENERAL_ROTATION_NATIVE_SOURCE_ROW_PRE_EVIDENCE_SUCCESSOR_20261110.json`.
- 기존 WCL 독립 수집/숫자 blind 후보 잠금/Strict PRE/holdout은 별도 재사용 가능한 검증 축이지만, **이 고술 79행이 WCL 랭커에서 최적임을 검증한 것은 아니다.** 의미론을 WCL blind 후보 lock 전 주입 금지.
- 확인된 한계: **같은 호출에서 앞선 경쟁 스킬의 물리적 READY/NOT_READY 전체 증명 없음**, 고술 오프닝 종료 상태 전이 미확정, 동시 사용 가능 스킬의 실제 우선순위 미확정, 현재 Retail 패치·특성/메커니즘 정합 및 허수아비 사용자 오류 미검증. 미관측은 UNKNOWN. 관측/코드 미비/최종 제품 연결 미비를 구분해 보고.
- 역사 상태: `Seq578=FAILED_QUARANTINED`, `Seq637=UNKNOWN` 보존; MAIN/FROZEN/공유 pointer 미승격.

## 다음 작업 (새 채팅의 두 번째 단계, 사용자가 '진행'한 후에만)

**Product Exact Next:** 모든 전문화에서 현재 Retail General Rotation의 정확한 오프닝 및 ST/2타겟/Cleave/AoE IF/ELSE 우선순위를 완성하고, 검증된 동일 IR로 실제 허수아비 행동을 UNKNOWN-safe 교정한다.

**Session Exact Next:** **고술 79개 정확 SELECT 소스 루트** 중 제품 영향이 큰 ST 및 AoE 시전 각 소수만 먼저 골라 원본 `CALL/RUN` 우선순위 경로와 앞선 경쟁 스킬의 IF·물리적 READY/NOT_READY를 **같은 Native 루트의 Strict PRE**로 입증한다. 이미 있는 범용 C++ source PRE/선택행 overlay/SpecAdapter를 재사용한다. 행동 이름·Native POST TRUE·스킬 빈도·첫 10초 임의 창만으로 mandatory priority나 opener exit를 주장하지 않는다. 소스 가설은 WCL blind 독립 잠금 이후 대조한다. 정확도 개선 없이 더 많은 시험/신규 추상화/과거 복원을 반복하지 않는다.

재사용 판단은 `REUSE / CONNECT / EXTEND / REPLACE / NEW / STOP`으로 기록한다. Generic Engine에 고술 전용 스킬/보스 로직을 hardcode하지 않는다. Main만 공유/프로덕션 상태를 승격한다.

## 새 채팅 첫 응답 계약

실제 브랜치/MAIN HEAD, 정책 Gen8→Gen7→Gen6 연속성, 최신 Actions와 근거의 범위, 완료·미완료·미실증·실패, 실제 증거 부족/엔진 구현 부족/제품 연결 부족, 중요 재사용/교체 의사결정, 단기·중기·장기 로드맵, Product/Session Exact Next와 사용자의 로컬 필요 작업을 **읽기 전용으로 보고**한다. 결과를 보고한 후 **반드시 멈춘다**. 새 채팅에서 사용자가 별도로 '진행'하기 전에는 새 검증도 실행하지 않는다.

첫 응답의 마지막 문장은 정확히 다음과 같이 작성한다.

복원 보고를 완료했습니다. 사용자의 '진행' 지시를 기다립니다.
