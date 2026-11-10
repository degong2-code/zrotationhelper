# zRotationHelper — 현재 연구 상태 (2026-11-10)

> **범위:** 공식 제품 목표 `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`. SimC APL/profile에서 전문화별 General Rotation 오프닝과 조건부 IF/ELSE 가설을 만들고, 독립 WCL blind 후보 고정 후 비교·수정하며, 관측 가능한 사용자 허수아비 연습만 평가한다. 보스별 실행 계획·NSRT는 범위 밖이다.
>
> **권한:** 이 문서는 `work/gr-simc-st-2t-wcl-blind-20261102` **격리 브랜치의 연구 현황**이다. MAIN의 제품 정본·FROZEN을 승격하지 않는다. 아래 결과의 날짜는 증거가 검증된 시점이지 현재 게임에서의 최적 우선순위 확정일이 아니다.

[연구 길잡이](RESEARCH_INDEX.md) · [기능별 개발 이력](FEATURE_HISTORY_INDEX.md) · [코드·증거·CI 지도](EVIDENCE_NAVIGATION_INDEX.md)

## 현재까지 확인된 것

| 연구 영역 | 확인된 범위 | 아직 주장할 수 없는 것 |
| --- | --- | --- |
| SimC APL 해석 | 고정 Fury/Arcane/Enhancement 원본 3프로필, 소스 **286 APL 행 / 19 리스트**, 순서·조건·CALL/RUN 구분 | 나머지 전문화 및 현재 Retail 최적성 |
| ST·2T·AoE 소스 분기 | **3클래스·12개 명시적 가상 타겟/특성 조건**에 대해 루트 CALL/RUN IF 48건 평가: TRUE 24, FALSE 24. 원본 APL 소스 조건 결과만 인증 | 실제 해당 리스트 진입, 전체 READY, 유저 오답 판정 및 오프닝 종료는 UNKNOWN |
| 오프닝 / ST / 2T / 3+ | **3전문화·12개 원본 Native 1·2·3·5타겟 사례**, 실제 SimC 행동 464건(첫 10초 표본 185건). 서로 다른 바이너리/실행 코호트 분리하여 같은 APL source 모델에 결합 | 첫 10초는 오프닝 종료 아님. 고술 원본 선택 행·동일 호출 PRE·전체 경쟁 READY, 현재 Retail 최적성 UNKNOWN |
| 선택 순간 IF | ST/2T 원본 행동 147건 중 49건 같은 원본 호출의 독립 IF TRUE, 44건 UNKNOWN, 54건 명시적 IF 없음 | IF TRUE = 전체 스킬 READY 또는 최적 우선순위 |
| 최소 충분 상태 | IF TRUE 49건의 관측값 122개 사용에서 89개로 동일 IF 결론 유지 | 실제 수집 실행시간/비용 27% 절감 |
| 경쟁 후보 | 이전 Native 실행의 선행 APL 행 10건 중 **8건 배제·2건 UNKNOWN** 보존; 별도 새 Native 실행의 선행 비전 탄막 후보 **2건 모두 동일 원본 root PRE로 IF FALSE 검증** | 서로 다른 원본 호출을 합산하지 않음. APL 행 배제 ≠ 스킬 자체 NOT_READY 또는 전체 우선순위 |
| WCL 독립 증거 | 기존 실제 로그 Strict PRE·원본 holdout 및 actor 빌드 추출 검증 | WCL 사용 빈도에서 필수 우선순위·인과성 도출 |
| 훈련기 | 연구 IR / UNKNOWN 처리·경량 연습기 인터페이스의 부분 설계 및 코드 | 실제 WoW 허수아비에서 검증된 오답 피드백 또는 실시간 관측 가능 확정 |

## 확인된 최신 증거로 바로 이동

- **SimC 타겟별 Native 행동:** [1/2/3/5타겟 실측 증거](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SIMC_ACTUAL_NATIVE_1_2_3_5_TARGET_GRID_20261110.json) · [Actions #42716911610](https://github.com/degong2-code/zrotationhelper/actions/runs/42716911610)
- **Same-call IF:** [49건 최소 충분 PRE 검증](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_ORIGINAL_SIMC_49_IF_PARTIAL_MINIMAL_WITNESS_20261110.json) · [Actions #42721244205](https://github.com/degong2-code/zrotationhelper/actions/runs/42721244205)
- **경쟁 후보 — 이전 Native 실행:** [8건 독립 배제 / 2건 미확인](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SOURCE_COMPETITOR_READY_FRONTIER_20261110.json) · [Actions #42723323648](https://github.com/degong2-code/zrotationhelper/actions/runs/42723323648)
- **경쟁 후보 — 이전 재생:** [7.667초 IF FALSE, 14.950초 직전 GCD 한 입력 필요](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SIMC_ORIGINAL_SAME_RUN_BOUNDED_IF_AND_SINGLE_PRE_FRONTIER_20261110.json) · [#42729673496](https://github.com/degong2-code/zrotationhelper/actions/runs/42729673496)
- **경쟁 후보 — 이번 Native 실제 PRE:** [7.667초·14.950초 모두 `prev_gcd.1.arcane_surge=0` → 원본 APL IF FALSE](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_ORIGINAL_SIMC_PREV_GCD_PRE_TWO_SOURCE_EXCLUSIONS_20261110.json) · [#42732275535](https://github.com/degong2-code/zrotationhelper/actions/runs/42732275535) — 기존 31행·JSON2 43행 행동 패리티 확인, 원본 C++ 새 빌드 1회, WCL API 0회
- **실제 WCL 빌드:** [Strict PRE actor combatantinfo](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_WCL_COMBATANTINFO_PRE_ACTOR_BUILD_AND_PINNED_SOURCE_LOOKUPS_20261110.json) · [Actions #42642973309](https://github.com/degong2-code/zrotationhelper/actions/runs/42642973309)
- **WCL 종합 관측 한계:** [메커니즘·패치 증거 게이트](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_POSTLOCK_MECHANIC_EPOCH_EVIDENCE_FRONTIER_20261109.json) · [Actions #42624671123](https://github.com/degong2-code/zrotationhelper/actions/runs/42624671123)

- **3클래스 타겟·특성 가설 검증:** [12개 시나리오·48개 루트 CALL/RUN IF의 참/거짓 판정](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SIMC_THREE_CLASS_TARGET_BUILD_SOURCE_GUARD_FRONTIER_20261110.json) · [Actions #42742497979](https://github.com/degong2-code/zrotationhelper/actions/runs/42742497979); **가상 입력에 대한 원본 소스 IF 계산**이며 실제 실행 리스트나 READY 인증이 아님.

- **3개 전문화 실제 Native 오프닝 표본:** [Fury·Arcane 재수집 없이 고술 4타겟 추가 후 원본 286행 source 우선순위 IR과 12실행/464행 통합](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_THREE_CLASS_ORIGINAL_SIMC_NATIVE_OPENING_PORTFOLIO_20261110.json) · [고술 신규 Native CI #42744084203](https://github.com/degong2-code/zrotationhelper/actions/runs/42744084203) · [3클래스 모델 결합 CI #42745179980](https://github.com/degong2-code/zrotationhelper/actions/runs/42745179980). **실제 Native 행동 이름 관측**이지만 정확한 선택 APL 행/READY/오프닝 종료는 UNKNOWN.

## 정확한 다음 연구 작업

**제품 Exact Next:** 범용 연구 엔진으로 현재 Retail 전문화별 General Rotation 오프닝과 ST/2T/Cleave/AoE 상태별 IF/ELSE 모델을 완성한다. 독립 WCL blind 후보를 고정한 뒤 대조·보정하고, 허수아비 실제 행동과 비교 가능한 경우에만 오류를 설명한다.

**세션 Exact Next:** 3개 전문화의 실제 원본 Native 12개 타겟별 행동 표본까지 확보했다. 이제 **고술 ST와 AoE의 영향이 큰 초기 선택 호출을 특정**하고, 기존 source-neutral C++ 계측으로 실제 선택 APL 행·원본 CALL/RUN 진입·필요한 Strict PRE 상태·선행 후보 사용 가능 여부를 동일 실행에서 입증한다. 과거 Fury/Arcane 8개 실행은 반복 수집하지 않는다. 이전 단계의 가상 3클래스 분기 검증은 통과했다. 다음에는 소스 가설만 반복하지 말고 영향이 큰 오프닝/일반 전환과 실제 이전 후보 READY를 **같은 원본 SimC 호출의 PRE/전체 CALL·RUN 경로**로 검증한다. WCL blind는 후보 잠금 전까지 SimC 의미론 입력 금지. 이전에 개발한 원본 동작 보존이 검증된 범용 `prev_gcd.N.action` PRE 읽기 기능과 IF/경쟁 후보 증거를 다른 전문화·빌드의 **General Rotation 오프닝, ST/2T/Cleave/AoE 조건부 우선순위 모델**로 연결한다. 이 두 선행 APL IF만 반복 검증하지 말고 실제 우선순위에 중요한 CALL/RUN 상위 경로·물리 READY·대안을 우선 검토한다. 이전 Native 실행의 2건 UNKNOWN은 별도 그대로 두며, 소스 가설을 WCL blind lock 이전에 유입하지 않는다.

## 상태를 읽을 때 주의

- **소스 가설**(SimC IF TRUE) ≠ **원본 Native 행동 관측** ≠ **독립 WCL 검증** ≠ **현재 게임 최적성** ≠ **사용자 오류 확정**.
- `state_at_action(t)`에 사용할 상태는 `timestamp < t`인 유효한 전이뿐이다. 같은 시각·미래 이벤트는 금지한다.
- `UNKNOWN`을 우선순위 오류로 판정하지 않는다. `Seq578=FAILED_QUARANTINED`, `Seq637=UNKNOWN` 유지.
- 기록을 업데이트할 때 완료/미완료와 CI 검증 범위를 분리한다. GitHub Actions artifact는 만료될 수 있으므로 원본 증거 영수증과 commit/sha가 장기 탐색 기준이다.
- 자세한 기존 개발 기록은 [보존된 기능별 인덱스](branches/BR-GR-ST2T-WCL-BLIND-20261102/FEATURE_EVIDENCE_REUSE_INDEX_20261105.md)와 [누적 상태 기록](branches/BR-GR-ST2T-WCL-BLIND-20261102/HANDOFF_STATUS_20261109.md)에서 확인한다.

*이 파일은 날짜 기준의 간결한 현황 안내다. 실제 브랜치 HEAD와 CI 상태는 GitHub에서 다시 조회해야 한다.*
