# New chat boot — zRotationHelper General Rotation engine (2026-11-09)

저장소 `degong2-code/zrotationhelper`; 격리 브랜치 `work/gr-simc-st-2t-wcl-blind-20261102`; owner `BR-GR-ST2T-WCL-BLIND-20261102`. 공식 제품 ID `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`; 정책 잠금 파일 `docs/PRODUCT_SCOPE_LOCK_V1.json`, SHA256 `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`. 현재 인계는 브랜치 로컬 `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json`의 **scope generation 4**이며 이전 원본은 archive 링크로 복원한다.

**첫 응답은 읽기 전용 복원·독립 증거 대조·완료/미완료 보고·장단기 로드맵 정리 후 중단.** 나의 새 채팅 명시적 **'진행'** 전에는 코드·문서 작성/수정, 테스트, SimC/WCL/API/게임 클라이언트 호출, GitHub Actions, 커밋, PR, 공유 승격을 시작하지 마라. 과거 채팅의 진행 승인은 승계되지 않는다.

반드시 순서대로 읽어라: (1) `docs/PRODUCT_SCOPE_LOCK_V1.json` → (2) `docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md` → (3) `AGENTS.md` → (4) `docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md` → (5) `docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md` → (6) 기존 Gen3/부모 archive 연결 확인 → (7) 브랜치 `LATEST_HANDOFF.json` → (8) `HANDOFF_STATUS_20261109.md`, `FEATURE_EVIDENCE_REUSE_INDEX_20261105.md`, `DEVELOPER_NOTES_20261105.md`, `HANDOFF_PREPARATION_WORKLOG_20261109.md`, `GENERAL_ROTATION_HEKILI_POLICY_ROADMAP_20261106.md`, 관련 원본 코드·CI/evidence. GitHub 브랜치 HEAD와 MAIN HEAD는 **각각 지금 직접 조회**, 이전 답변에 적힌 SHA를 재사용하지 마라.

목표는 개별 전문화·스킬 구현이 아니라 **새 전문화에도 재사용되는 General Rotation 연구/검증 엔진** 및 가벼운 허수아비 행동 평가기 완성이다. SimC APL/profile → 오프닝과 조건부 ST/2T/cleave/AoE IF/ELSE, 변수·특성·자원·버프·쿨다운·proc·풀링·execute → WCL 상위 플레이어 **독립 blind 후보 고정 전 SimC 의미 유입 금지** → 사후 대조·Blizzard 공식 메커니즘·필요시 독립 holdout → 사용자 실제 훈련 행동 비교. 레이드 실행 계획, 보스별 NSRT/타임라인은 제품 제외. 실제 addon 보호 값/secret 우회 금지; 관측 못 하면 UNKNOWN, 실시간 불가하면 연습 후 로그.

복원할 핵심 증거(재확인 필수): #42195342553 SimC 전체 소스 우선순위 172행·원본 Native source-return/PRE 262/262·2전문화 4조건 PASS. #42444206139 Generic Strict PRE/지역 변수/조건부 1-scan 평가기 Py3.12+3.14 15 synthetic checks/Python + 실제 두 전문화 소스 fail-closed PASS. 이는 **완전한 실제 Native READY/동적 오프닝/최적 우선순위 증명 아님**. 과거 WCL 수집 54 discovery/51 holdout 존재하지만 현 IR에 대한 독립 후보 lock·검증은 미완료. 허수아비 실제 API/평가도 미완료. 분노전사·비전마법사 특성 adapter에서 필요한 소스 readiness를 완전히 증명한 Positive FULL_READY는 0.

**진행 승인 후** 매 작업 전 과거 개발 기록·기능별 인덱스·원본·코드·증거 영수증을 우선 조회하여 `REUSE / EXTEND / REPLACE / UNKNOWN`을 판정하고, 증거 부족 vs 엔진 구현 결손 vs 최종 제품 연결 미완료를 분리하라. 독립 작업은 묶어 처리하고 이전 동일 검증 기준·artifact를 재사용하라. 엔진이 실제 General Rotation과 dummy 피드백을 개선하는지 자가점검하고, 불필요한 과거 복구·중복 C++/WCL 조회·PASS 집계를 피하라. Strict PRE `timestamp < decision_time`; 같은 시각 미래 상태 누출 금지. MAIN만 공유 승격한다.

첫 보고에는 공식 목표, 실제 HEAD·MAIN, 정책/인계 generation/parent SHA, 최신 원본 증거의 범위와 한계, 완료/미완료, 병목, 재사용 전략, 단기·중기·장기 로드맵, Product Exact Next, Session Exact Next, 사용자 당장 할 일을 포함하고 중단하라.

**첫 보고 마지막 문장 정확히:** 복원 보고를 완료했습니다. 사용자의 '진행' 지시를 기다립니다.
