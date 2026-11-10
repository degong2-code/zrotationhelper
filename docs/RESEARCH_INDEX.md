# zRotationHelper — 연구·개발 기록 탐색 시작점

> **왜 이 문서가 있나:** 코드와 2026년 10~11월의 인계·실험·증거가 여러 위치에 나뉘어 있다. 이 페이지는 과거 파일을 이동하거나 삭제하지 않고, 원하는 기능의 **역사 → 코드 → 원본 증거 → CI → 현재 남은 문제**를 찾아가는 단일 탐색 출입구다.
>
> **현재 위치:** `work/gr-simc-st-2t-wcl-blind-20261102` 격리 브랜치. GitHub 기본 `main`은 최초 bootstrap README만 있으며 이 브랜치의 작업을 정본으로 승격한 상태가 아니다.

## 가장 먼저 볼 3개 문서

1. **[현재 연구 상태 — 무엇이 완료·미완료인가](CURRENT_RESEARCH_STATUS.md)**: 제품 목표, SimC / WCL / 허수아비 영역의 실증 상태, 지금 중요한 작업.
2. **[기능별 개발 이력 — 왜 이렇게 구현됐는가](FEATURE_HISTORY_INDEX.md)**: 최초 구현·후속 개선·검증과 해결되지 않은 원인을 시간순으로 연결.
3. **[증거 지도 — 실제 코드와 CI는 어디인가](EVIDENCE_NAVIGATION_INDEX.md)**: 주요 범용 엔진, 원본 JSON, 검증 Actions, 실패 후 후속 교정의 링크.

이 세 문서가 **탐색용 요약층**이고, 기존 누적 기록은 아래처럼 보존된다.

## 연구 파이프라인으로 탐색

| 찾고 싶은 연구 과정 | 확인 경로 | 현 상태의 핵심 구분 |
| --- | --- | --- |
| 1. SimC 기본 APL과 오프닝 | [APL/parser](../tools/research/simc_apl_semantic_ir_v2.py) → [소스 IF/ELSE 엔진](../tools/research/general_rotation_simc_e2e_research_engine_v1.py) → [관련 증거](EVIDENCE_NAVIGATION_INDEX.md#simc-연구-경로) | 소스 가설은 최적 행동 인증이 아님 |
| 2. 실제 Native 선택과 상황별 타겟 수 | [1·2·3·5타겟 모델](../tools/research/general_rotation_simc_native_target_grid_v1.py) → [실제 증거](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SIMC_ACTUAL_NATIVE_1_2_3_5_TARGET_GRID_20261110.json) | 이름·순서 관측 ≠ 경쟁 후보 READY |
| 3. 원본 PRE → IF TRUE·UNKNOWN | [최소 충분 IF 엔진](../tools/research/general_rotation_original_simc_if_minimal_frontier_v1.py) → [실제 증거](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_ORIGINAL_SIMC_49_IF_PARTIAL_MINIMAL_WITNESS_20261110.json) | 원본 49 TRUE·44 UNKNOWN, READY는 별개 |
| 4. 앞선 스킬의 배제·우선순위 | [범용 경쟁 후보 판단](../tools/research/general_rotation_source_competitor_frontier_v1.py) → [증거](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SOURCE_COMPETITOR_READY_FRONTIER_20261110.json) | 8개 행의 독립 배제·2개 미확인, 전체 우선순위 UNKNOWN |
| 5. WCL 독립 후보 발견 | [원본 재생](../tools/engine_first/fresh_wcl_engine_v1.py) → [blind 후보 lock](../tools/engine_first/wcl_blind_numeric_candidate_lock_v1.py) → [postlock 대조](../tools/research/general_rotation_wcl_postlock_source_ir_bridge_v1.py) | **SimC 답을 blind 후보 lock 이전에 주입하지 않음** |
| 6. 현재 게임 메커니즘·허수아비 | [공식 메커니즘 증거 게이트](../tools/research/general_rotation_mechanic_epoch_evidence_gate_v1.py) → [연습기 조사](../addons/research/ZRotDummyProbe/README.md) | 현재 WoW API·READY가 보이지 않으면 UNKNOWN |

## 공식 권한과 과거 자료 보존

- **제품 범위(최우선):** [정책 lock JSON](PRODUCT_SCOPE_LOCK_V1.json) · [General Rotation + Dummy Trainer 범위](PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md) · [Engine-First Charter](ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md).
- **분기 현재 상태의 원문:** [기존 누적 상태](branches/BR-GR-ST2T-WCL-BLIND-20261102/HANDOFF_STATUS_20261109.md), [기능별 원본 재사용 인덱스](branches/BR-GR-ST2T-WCL-BLIND-20261102/FEATURE_EVIDENCE_REUSE_INDEX_20261105.md), [개발자 기록](branches/BR-GR-ST2T-WCL-BLIND-20261102/DEVELOPER_NOTES_20261105.md).
- **새 채팅 인계:** [branch-local 최신 LATEST_HANDOFF.json](../_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json) · [이전 세대 archive](../_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/archive/) · [연속성 프로토콜](HANDOFF_CONTINUITY_PROTOCOL_V1.md). 현재 인계부터 과거 Gen5·Gen4를 필요한 범위에서 따라간다.
- **기타 과거 브랜치:** [분기별 handoff 컬렉션](../_UPLOAD_TO_CHATGPT/branches/) 및 [과거 SimC 인계 문서](BRANCH_SIMC_HANDOFF_20261031_V16.md). 예전 레이드/NSRT 목표는 현재 제품 범위로 부활하지 않는다.
- **공유 승격 원칙:** MAIN만 정본·CURRENT_STATE·전역 pointer·FROZEN을 변경한다. 이 브랜치의 PASS는 격리 개발 증거이며 공유 승격이 아니다.

## 새 연구 결과를 남기는 기본 순서

새 개발이 생기면 (1) 실제 코드·원본·CI 증거 보존 → (2) [기능별 이력](FEATURE_HISTORY_INDEX.md)에 처음/수정/검증/남은 한계 1행 추가 → (3) [증거 지도](EVIDENCE_NAVIGATION_INDEX.md)의 구현·영수증·CI 연결 갱신 → (4) [현재 상태](CURRENT_RESEARCH_STATUS.md)를 간결하게 갱신 → (5) 누적 기록·branch-local 최신 인계와 정책 연속성 검증 순서로 기록한다.

**중복 개발 방지:** 신규 코드 작성 전에 기능별 이력과 증거 지도를 검색해 `REUSE / EXTEND / REPLACE / UNKNOWN`을 판정한다. 만료된 Actions artifact나 미존재 역사 파일은 가짜 링크나 성공으로 대체하지 않는다. 
