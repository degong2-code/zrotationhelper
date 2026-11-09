# SimC-first General Rotation — 실제 오프닝 관측 및 APL 조건부 우선순위

정본 범위: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`.

## 이번 단계 실증

- 원본 SimC `simulationcraft/simc@b522cded8c26b97dac03fdf56e57a03ec7e8faa6`, 공식 Fury/Arcane MID2 profile, 30초, seed=31459, ST·2타겟, 4개 사례 단일 원본 바이너리
- APL source rule 172행과 original Native source returns 262건은 이전 단계의 기존 증거
- 이번 신규 실증 JSON2 실제 시뮬레이션 SAMPLE_ACTION **149건** (Fury ST 43 / 2T 44, Arcane ST 30 / 2T 32). 자동 공격·소비품·아이템 등을 포함하며 전부 GCD 딜스킬은 아님
- 행동 표본↔APL 행 이름 매핑은 가능한 소스 후보 목록일 뿐 유일한 원인/정확한 IF/ELSE path나 full READY 증명 아님

## 관측 첫 10초 요약 — 실제 시뮬레이션 기록, 오프닝 정답 아님

| 전문화·대상 | 관측 오프닝 초반 |
|---|---|
| Fury ST | 0s auto_attack/charge/recklessness/potion/item/rampage → 0.899s bladestorm → 1.681s storm_bolt → 3.045s rampage → 3.800s crushing_blow |
| Fury 2T | 동일한 0s 초기 동작 → 0.899s bladestorm → 1.681s storm_bolt → 3.032s rampage → 3.786s rampage → 4.542s odyns_fury |
| Arcane ST | 0s potion/arcane_orb → 0.907s arcane_surge → 2.513s arcane_missiles → 4.048s arcane_blast → 4.971s arcane_barrage/touch_of_the_magi → 6.955s prismatic_bolt |
| Arcane 2T | 0s potion/arcane_orb → 0.907s arcane_surge → 2.510s arcane_missiles → 3.908s arcane_blast → 4.819s arcane_barrage/touch_of_the_magi → 6.775s arcane_barrage → 7.667s arcane_orb |

10초는 임의의 연구 관측 창이다. 실제 오프닝 종료 시점과 조건은 여전히 UNKNOWN.

## APL source-based conditional priority

상세한 전문화별 **전체 172행의 local source priority, RUN/CALL control semantics, IF/ELSE guard 및 first-window observed sample actions**는 Actions [#42563131631](https://github.com/degong2-code/zrotationhelper/actions/runs/42563131631)의 389줄 Markdown artifact `zrot-simc-general-rotation-readable-source-and-openers-v1`에 있다.

실제 4개 사례 raw JSON2 + 전체 General Rotation IR: Actions [#42562520191](https://github.com/degong2-code/zrotationhelper/actions/runs/42562520191), `zrot-general-rotation-first-real-cast-and-source-ir`; JSON SHA256 `584819145ec6e51bd7596bd273da74402622adf7bd0ecf1ea25ce19b0f26c715`.

실제 소스 기반 Fury Slayer 우선순위에는 `recklessness`, 격노 잔여시간/분노 자원을 조건으로 반복되는 `rampage` 행, 다중 대상에서 `whirlwind` 중첩/특성 조건 등이 있다. 개별 스킬의 실제 조건과 우선순위 확정에는 정확한 APL branch·source method PRE readiness와 동시 경쟁 후보 검증이 추가로 필요하다.

## 현재 연구용 모델 vs 완성 기준

| 항목 | 이번 상태 |
|---|---|
| APL full ordered source priority (Fury/Arcane ST/2T) | 확인된 source 가설 |
| 실제 원본 SimC 초반 행동 순서 | 4개 사례 OBSERVED |
| SOURCE 조건 TRUE/FALSE, 실제 우선순위의 원인 | 일부만 증명, 상당수 UNKNOWN |
| 정확한 APL 행 매핑과 경쟁 스킬 동시 사용 가능성 | UNKNOWN |
| 조건에 따른 오프닝 종료와 ST/2T/AoE 전환 | UNKNOWN/AoE 미검증 |
| WCL 독립 blind holdout | NOT RUN |
| 실제 게임 허수아비 로테이션 실수 | UNKNOWN (오류라고 단정 금지) |

다음 단계는 WCL로 넘어가기 전에 SimC 실제 행동과 source-row IF/ELSE 의사결정의 **동일 시각 exact matching**, 시작 상태 및 종료 조건 재생을 완성하는 것이다. 새 전문화도 동일 엔진으로 확장하고 필요한 추가 필드만 SpecAdapter에 선언한다.
