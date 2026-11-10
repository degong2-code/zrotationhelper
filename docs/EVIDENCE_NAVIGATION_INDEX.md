# zRotationHelper — 기능 → 구현 코드 → 증거 → CI 지도

> **읽는 법:** 하나의 기능에 대해 *코드가 무엇을 수행하는지*, *실제 원본이 무엇을 증명했는지*, *어떤 CI가 이를 검증했는지*를 빠르게 역추적한다. **CI 성공 = 해당 CI 계약 PASS**이지 WoW 현재 시즌 로테이션 최적성 인증이 아니다.

[연구 지도](RESEARCH_INDEX.md) · [기능별 개발 이력](FEATURE_HISTORY_INDEX.md) · [현재 상태](CURRENT_RESEARCH_STATUS.md)

## SimC 연구 경로

| 기능 | 원본·구현 | 검증 영수증 | 실제 CI / 근거 수준 |
| --- | --- | --- | --- |
| APL AST·순서·CALL/RUN 보존 | [공통 파서](../tools/research/simc_apl_semantic_ir_v2.py), [General Rotation source engine](../tools/research/general_rotation_simc_e2e_research_engine_v1.py) | [고정 프로필·조건 IR](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_CONDITION_IR_TWO_SPEC_STATIC_AUDIT_20261109.json) | **SOURCE_HYPOTHESIS**; APL 행이 게임 내 최적성을 뜻하지 않음 |
| 원본 Native 선택·PRE | [원본 선택 호출 경로](../tools/research/general_rotation_original_foreground_dispatch_v1.py), [원본 PRE 증거](../tools/research/general_rotation_original_select_extra_pre_v1.py) | [12필드 PRE 후속](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SOURCE_PRE_12_FIELD_ORIGINAL_IF_SUCCESSOR_20261109.json) | [#42589894203](https://github.com/degong2-code/zrotationhelper/actions/runs/42589894203) — **ORIGINAL_NATIVE_PRE** |
| 원본 source IF 가설·동일 호출 귀속 | [원본 source bridge](../tools/research/general_rotation_original_source_evidence_bridge_v1.py) | [49 IF source IR](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SOURCE_CONDITIONAL_IR_49_PROOF_BRIDGE_20261109.json) | [#42594344188](https://github.com/degong2-code/zrotationhelper/actions/runs/42594344188) — **IF 일부 검증, READY 미완** |
| 타겟 수·특성 가정 | [범용 분기 투영](../tools/research/general_rotation_simc_target_count_projection_v1.py), [외부 특성 시나리오](../tools/research/fixtures/general_rotation_simc_target_scenarios_v1.json) | [1~10타겟 source 조건](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SIMC_SOURCE_3PLUS_TARGET_AND_TALENT_PROJECTION_20261110.json) | [#42651150670](https://github.com/degong2-code/zrotationhelper/actions/runs/42651150670) — **SOURCE_ONLY** |
| 1·2·3·5타겟 Native 행동 | [범용 Native 비교](../tools/research/general_rotation_simc_native_target_grid_v1.py) | [실제 8개 Native 케이스](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SIMC_ACTUAL_NATIVE_1_2_3_5_TARGET_GRID_20261110.json) | [#42716911610](https://github.com/degong2-code/zrotationhelper/actions/runs/42716911610) — **실제 행동 관측, 전체 READY 아님** |
| 초기 주요 버프 관측 구간 | [일반화된 버프 snapshot 경계](../tools/research/general_rotation_simc_burst_snapshot_interval_v1.py), [소스 ID adapter](../tools/research/fixtures/general_rotation_simc_pinned_burst_aura_source_adapter_v1.json) | [버프가 보이다 사라지는 관측 구간](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SIMC_INITIAL_BURST_SNAPSHOT_EXIT_BOUNDS_20261110.json) | [#42718056047](https://github.com/degong2-code/zrotationhelper/actions/runs/42718056047) — **정확한 만료·오프닝 종료 아님** |
| 소스 IF 최소 충분 PRE | [공통 최소 증거](../tools/research/general_rotation_source_if_minimal_witness_v1.py), [원본 검증기](../tools/research/general_rotation_original_simc_if_minimal_frontier_v1.py) | [49 TRUE / 44 UNKNOWN](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_ORIGINAL_SIMC_49_IF_PARTIAL_MINIMAL_WITNESS_20261110.json) | [#42721244205](https://github.com/degong2-code/zrotationhelper/actions/runs/42721244205) — **조건 결과 일부 검증** |
| 상위 후보 독립 배제 | [일반화된 경쟁 후보](../tools/research/general_rotation_source_competitor_frontier_v1.py), [특성/원본 필드 adapter](../tools/research/fixtures/general_rotation_simc_competitor_arcane_source_adapter_v1.json) | [기존 실행 10건 중 8건 독립 배제](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SOURCE_COMPETITOR_READY_FRONTIER_20261110.json) | [#42723323648](https://github.com/degong2-code/zrotationhelper/actions/runs/42723323648) — **기존 2건 UNKNOWN, 전체 우선순위 미검증** |
| 미관측 소스 IF 이진 범위 전수 검증·민감도 | [범용 동일 원본 호출 PRE bounded IF](../tools/research/general_rotation_original_attempt_bounded_if_v1.py), [원본 C++ 도메인 및 사례 adapter](../tools/research/fixtures/general_rotation_original_source_bounded_if_adapter_v1.json) | [구형 Native 로그에서 7.667초 FALSE / 14.950초 UNKNOWN](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SIMC_ORIGINAL_SAME_RUN_BOUNDED_IF_AND_SINGLE_PRE_FRONTIER_20261110.json) | [#42729673496](https://github.com/degong2-code/zrotationhelper/actions/runs/42729673496) — **전수 조합 4개로 직전 GCD 필요성 확인; FULL READY 0** |
| 실제 이전 GCD PRE·선행 APL 후보 확인 | [읽기 전용 `prev_gcd.N.action` 수집기](../tools/research/general_rotation_original_select_extra_pre_v1.py), [소스 의미론 adapter](../tools/research/fixtures/zrot_original_select_prev_gcd_pre_successor_v1.json), [bounded IF 재생](../tools/research/general_rotation_original_attempt_bounded_if_v1.py) | [새 Native 실행의 두 원본 후보 IF FALSE](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_ORIGINAL_SIMC_PREV_GCD_PRE_TWO_SOURCE_EXCLUSIONS_20261110.json) | [#42732275535](https://github.com/degong2-code/zrotationhelper/actions/runs/42732275535) — **원본 31개 직접 선택·43개 출력 동일, 두 원본 PRE 값 0, 경쟁 source IF FALSE; 물리 READY 미검증** |

## WCL 독립 연구 경로

| 기능 | 원본·구현 | 검증 영수증 | 실제 CI / 근거 수준 |
| --- | --- | --- | --- |
| 재현 가능한 Cold Start·checkpoint | [원본 WCL 수집·재생 엔진](../tools/engine_first/fresh_wcl_engine_v1.py), [actor cohort](../tools/engine_first/wcl_actor_scoped_cohort_v1.py) | [실제 다른 리포트 재생](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_WCL_REAL_COLDSTART_DISJOINT_REPLAY_THIRD_REPORT_20261109.json) | **REAL_WCL_REPLAY**, 최신 수집 가능성 보장 아님 |
| blind 숫자 후보 잠금 | [blind lock](../tools/engine_first/wcl_blind_numeric_candidate_lock_v1.py), [독립 holdout](../tools/engine_first/wcl_disjoint_holdout_v1.py) | [WCL+source 사후 통합](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_WCL_BLIND_STRICT_PRE_POSTLOCK_SOURCE_IR_BRIDGE_20261109.json) | **WCL 독립 발견 → 후보 lock → 사후 SimC 대조** |
| 배우(actor)의 빌드·장비 | [Generic combatantinfo PRE](../tools/engine_first/wcl_actor_combatantinfo_pre_v1.py) | [실제 holdout+3번째 리포트 증거](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_WCL_COMBATANTINFO_PRE_ACTOR_BUILD_AND_PINNED_SOURCE_LOOKUPS_20261110.json) | [#42642973309](https://github.com/degong2-code/zrotationhelper/actions/runs/42642973309) — **숫자 장비/특성 관측만 인증** |
| 숫자 aura·자원 Strict PRE | [raw aura 시각·스택](../tools/engine_first/wcl_raw_actor_aura_temporal_pre_v1.py), [actor numeric power](../tools/engine_first/wcl_raw_actor_numeric_power_pre_v1.py) | [raw aura PRE](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_WCL_RAW_AURA_TEMPORAL_STACK_PRE_20261109.json) | **STRICT_PRE**, 가용성/지속시간 READY와 구분 |
| post-lock 소스 비교·메커니즘 | [Generic source replay](../tools/research/general_rotation_wcl_postlock_source_ir_bridge_v1.py), [mechanic/epoch gate](../tools/research/general_rotation_mechanic_epoch_evidence_gate_v1.py) | [공식 메커니즘·증거 관측 한계](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_POSTLOCK_MECHANIC_EPOCH_EVIDENCE_FRONTIER_20261109.json) | [#42624671123](https://github.com/degong2-code/zrotationhelper/actions/runs/42624671123) — **실제 priority 인증 0** |

## 사용자 연습 피드백 경로

- [허수아비 연구 애드온 README](../addons/research/ZRotDummyProbe/README.md) → [General Rotation IR 피드백 평가기 초안](../tools/research/general_rotation_source_ir_dummy_feedback_v1.py).
- **관측 불가 = UNKNOWN.** 현재 게임 클라이언트에서 완전한 원본 READY/실시간 오답이 인증됐다고 표시하지 않는다.
- 실제 Blizzard 애드온 API의 허용·비허용 관측 범위는 [기존 정책 조사](branches/BR-GR-ST2T-WCL-BLIND-20261102/RETAIL_ADDON_POLICY_CAPABILITY_GATE_20261106.md)를 **현재 시점에 재검증해야 하는 자료**로만 활용한다.

## 과거 실패의 위치 찾기

| 실패/보류 | 그때의 원인 | 후속 교정·성공 |
| --- | --- | --- |
| 원본 WCL 비어 있는 장비 슬롯 | `gear[].id=0`을 잘못 거부 | [빌드 PRE 완료 증거](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_WCL_COMBATANTINFO_PRE_ACTOR_BUILD_AND_PINNED_SOURCE_LOOKUPS_20261110.json) · [#42642973309](https://github.com/degong2-code/zrotationhelper/actions/runs/42642973309) |
| Native sample 음수 시각 허용 | 합성 음수 timestamp 검증 결함 | [Native 3+ 최종 증거](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SIMC_ACTUAL_NATIVE_1_2_3_5_TARGET_GRID_20261110.json) · [#42716911610](https://github.com/degong2-code/zrotationhelper/actions/runs/42716911610) |
| 합성 원본/관측 identity가 동일 객체 | 변조 테스트에서 alias 공유로 누락 | [IF 최소 충분 최종 증거](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_ORIGINAL_SIMC_49_IF_PARTIAL_MINIMAL_WITNESS_20261110.json) · [#42721244205](https://github.com/degong2-code/zrotationhelper/actions/runs/42721244205) |
| 경쟁 IF 2건 증거 부족 (이전 별도 원본 실행) | Native POST false만 있고 독립 PRE 없음 | [기존 8건 배제 / 2건 UNKNOWN](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SOURCE_COMPETITOR_READY_FRONTIER_20261110.json). [다른 원본 실행에서는 1건 source IF FALSE로 확인·1건 UNKNOWN](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SIMC_ORIGINAL_SAME_RUN_BOUNDED_IF_AND_SINGLE_PRE_FRONTIER_20261110.json). **서로 다른 원본 root 증거는 혼합 금지** |

## 영수증과 원본의 수명

GitHub Actions의 성공/실패·커밋은 기록으로 남지만 다운로드 가능한 **Actions artifact는 보존기간이 있다**. 영구 기록은 이 브랜치의 증거 JSON, 고정 원본 SHA와 코드 버전, 과거 [누적 기능 인덱스](branches/BR-GR-ST2T-WCL-BLIND-20261102/FEATURE_EVIDENCE_REUSE_INDEX_20261105.md)를 기준으로 한다. Artifact 만료는 검증 부재 또는 엔진 실패와 동일하지 않지만, 해당 원본을 새로 실행해 재현했다는 증거도 아니다.

**검증 상태 표기:** `COMPILE / SELF-TEST / SYNTHETIC-STATIC / OFFLINE ORIG-REPLAY / ACTUAL NATIVE / LIVE WCL / ACTUAL WOW CLIENT`를 구분한다. 이 문서 자체는 탐색용이며 게임 내 완성 증거가 아니다.
