# General Rotation 전문화별 모델 — 산출물 인덱스

> **제품 목표:** 전문화별 범용 General Rotation 오프닝과 조건부 IF/ELSE 우선순위를 완성하고, 충분히 검증된 경우에만 허수아비 연습 오류를 설명한다. 보스별/Encounter/NSRT는 제외한다.
>
> **현재 단계 (2026-11-10):** 원본 SimC APL 구조에서 생성된 **전문화별 완전한 소스 우선순위 초안**. 현재 게임의 최적 로테이션이나 그대로 실행 가능한 허수아비 판정 규칙으로 승격한 상태가 아니다.

## 실제 생성된 전문화별 로테이션 모델

| 전문화 | APL 원본 행 | 특성·타겟 상황 | 실제 Native 첫 10초 행동 표본 | 생성된 파일 | 연구 검증 경계 |
| --- | ---: | ---: | ---: | --- | --- |
| **고양 주술사 (Enhancement)** | 114 | 4 | 1·2·3·5타겟 각 16건 | `shaman_enhancement.md` + `shaman_enhancement.json` | 정확한 선택 행·READY·오프닝 종료 UNKNOWN |
| **분노 전사 (Fury)** | 121 | 4 | 1·2·3·5타겟 각 18건 | `warrior_fury.md` + `warrior_fury.json` | 다른 Native 실행의 개별 근거와 혼합 금지 |
| **비전 마법사 (Arcane)** | 51 | 4 | 1/2/3/5타겟 12/13/12/12건 | `mage_arcane.md` + `mage_arcane.json` | 부분적인 동일 호출 IF 배제는 증명, 전체 READY 아님 |
| **현재 합계** | **286** | **12** | **185건** | **Markdown 3개 + JSON 3개 + INDEX.json** | 최종 General Rotation 아직 미완성 |

**바로 확인:** [생성 CI #42747802703](https://github.com/degong2-code/zrotationhelper/actions/runs/42747802703) 하단 Artifacts의 `zrot-general-rotation-per-spec-source-drafts-923f49018aba12aefd97d2260e9f9697c6353ae4` ZIP에 7개 파일이 있다. CI 3/3 PASS, 원본 APL 286/286행 보존, JSON/Markdown 파일 각각 SHA256 확인. GitHub Actions 아티팩트는 **2026-11-24 03:11:54 UTC** 만료 예정이므로 영구 저장소의 정본과 혼동하지 않는다.

**재생 가능한 코드:** [범용 전문화별 출력 엔진](../tools/research/general_rotation_spec_model_export_v1.py) · [고정 3클래스 소스 manifest](../tools/research/fixtures/general_rotation_simc_pinned_three_class_v1.json) · [외부 target/build 시나리오](../tools/research/fixtures/general_rotation_source_guard_scenarios_three_class_v1.json) · [생성 결과의 SHA 및 증거 수명](../active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERAL_ROTATION_PER_SPEC_DRAFT_MODEL_EXPORT_20261110.json).

## 모든 전문화에 동일하게 적용하는 모델 구성

1. **Precombat:** 원본 `actions.precombat` 순서, 전투 시작 오프닝의 확정 시전 순서와 혼동 금지.
2. **오프닝 행동 관측:** 각 타겟 수에서 원본 Native SimC의 실제 첫 10초 행동 이름·시각 표본. 이 10초는 종료 조건이 아니다.
3. **General Rotation 조건:** 스킬 및 제어 행동의 원본 APL **전체 IF/ELSE 순서**, 소스 리스트별 로컬 우선순위와 `CALL` 복귀, `RUN` 제어 이관의 차이를 보존한다.
4. **타겟·빌드 분기:** ST / 2타겟 / AoE, 히어로 특성 유무 등은 외부 시나리오 입력으로 원본 조건식의 TRUE/FALSE/UNKNOWN을 계산한다. 시나리오 가정은 실제 게임 PRE가 아니다.
5. **경쟁 READY·증거:** 해당 원본 호출 시 앞선 후보의 IF FALSE/실제 NOT_READY, 선택된 스킬의 사용 가능성, 오프닝 종료, WCL 독립 holdout과 사용자 피드백은 독립적인 증거가 있을 때만 승격한다.

소스 분기가 TRUE라도 실제 CALL/RUN 리스트가 실행됐다고 선언하지 않는다. 실제 우선순위와 오프닝을 결정하려면 **같은 실행의 원본 선택 행, Strict PRE, 모든 중요한 상위 후보의 readiness**가 필요하다.

## 다음 전문화부터 적용하는 규칙

- **Generic Engine에 전문화·영웅 특성·보스별 우선순위를 하드코딩하지 않는다.** 새로운 전문화는 고정된 SimC profile의 Git blob을 source manifest에 추가하고, 타겟/빌드 조건을 SpecAdapter/scenario에 선언한다.
- 소스 파서와 원본 PRE 계측기, Native 실행 결과, WCL blind 증거는 서로 독립된 근거 축이다. SimC-first 가설을 생성한 뒤에만 **잠금이 완료된** WCL blind 후보와 대조한다.
- 처음에는 source 가설 출력이 가능하다. 이후 동일 원본 실행의 선택 행·READY 및 독립 WCL 근거를 붙여 **전문화별 General Rotation의 검증 수준**을 단계적으로 올린다.
- 실제 플레이어에게 추천한 행동과 실제 행동이 다른 경우, 충분한 상태와 대안의 사용 가능성을 확인하지 못하면 **UNKNOWN**이며 오류로 표시하지 않는다.

## 현재 최우선 구체화 작업

**고양 주술사**를 첫 검증 대상 전문화로 삼아 ST와 AoE의 초기 행동에서 실제 선택 소스 행, 당시 자원·버프·쿨다운·특성 상태, 상위 경쟁 행동의 IF/READY를 같은 SimC 실행에서 재구성한다. 이것을 새로 생성된 `shaman_enhancement.json`의 스킬 규칙에 **검증 상태를 추가하는 방식**으로 반영한다. 모델 자체는 다른 전문화에 동일하게 적용된다.

**관련 장기 이력:** [현재 연구 상태](CURRENT_RESEARCH_STATUS.md) · [기능별 개발 이력](FEATURE_HISTORY_INDEX.md) · [코드·근거·CI 탐색](EVIDENCE_NAVIGATION_INDEX.md) · [MAIN과 Branch 운영](../PARALLEL_WORKSTREAM_AND_MERGE_CONTRACT.md).
