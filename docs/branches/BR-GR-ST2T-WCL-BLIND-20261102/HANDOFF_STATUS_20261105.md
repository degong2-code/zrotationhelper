# zRotationHelper — 브랜치 최신 검증 상태 (2026-11-05)

## Authority / 기준
- 정책: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`; lock Git blob `14b9f5174a9d1652a56dcca03af1f2302b78c22d`; SHA256 `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`. 정책 변경 없음.
- 실제 GitHub 인계 이전 HEAD: `5e883b990248cc4a4eb15e481990316ad951620a`; MAIN 읽기 전용 HEAD: `4790f77f76a75f26ff0558d1d18c16cd9d630c4b`; 현재 검증한 코드 HEAD: `d4358213e451194e1a78d3d29292857e8f7125e2`. 인계 후 HEAD는 읽기 전용 재조회로 확인해야 한다.
- 연구 브랜치 소유권만 행사. MAIN / CURRENT_STATE / canonical registry / FROZEN / global LATEST_HANDOFF / 제품 포인터 수정·승격 없음. Seq578=FAILED_QUARANTINED, Seq637=UNKNOWN.
- 범위: **범용 General Rotation 연구·검증 엔진**, SimC APL 최초 가설 → 독립 WCL blind 후보 잠금 → 잠금 후 비교/Blizzard mechanics 확인 → 오프닝+ST/2T/cleave/AoE IF/ELSE 모델 → 허수아비 연습 분석. Encounter/boss/raid plan, NSRT, 레이드 타임라인 제외.

## 확인된 실제 구현·증거
| 능력 / 재사용 자산 | 확인한 실제 증거 | 완료 판정의 상한 |
| --- | --- | --- |
| 공식 SimC 파서 + 다중 전문화 source IR | Fury 121행·8리스트, Mage Arcane 51행·5리스트, 합계 172행; `general_rotation_source_hypothesis_ir_v1.py`; Actions #41799789205 SUCCESS | **APL 소스 가설**, 실행 오프닝/최적 READY 아님 |
| 기존 bounded IF/ELSE evaluator + source IR proof replay | `general_rotation_ir_proof_replay_v1.py`; Actions #41935516360 SUCCESS. 실재 소스 172/172 검증, 상태 미입력 172 UNKNOWN, 실제 긍정 READY 0 | 합성 조건의 가상 선택만 검증, 실제 사용 권고 아님 |
| Source-backed Native 조건 재생 | 4 시나리오, 5,408 readiness 시도; 2,313 독립 필수조건 부정(NOT_READY), 3,095 UNKNOWN, **독립 전체 READY 0**; Actions #41794691821 SUCCESS | 수치가 별개 스킬 개수/전체 로테이션 완성률 아님 |
| 선택 후보 source-order | 387개 root source return 중 APL 제어 213, 비제어 실행 후보 174; 79/174만 이전 시도를 모두 제외, 선택 후보 READY는 UNKNOWN | 우선순위·optimality 0건 확정 |
| 최신 Generic Native PRE IF → IR 연결 | `general_rotation_native_ir_pre_evidence_join_v1.py` SHA256 `cbc179f61c6726ec7cb46aa4c0b04698cc504f3c6da3249dd4266573b6d3cdf5`, Actions #41938527598 SUCCESS. 953 source IF = 독립 FALSE 657 + TRUE 282 + UNKNOWN 14, 939/953 계산 가능; Native 원본 판정은 사후 대조용 | **IF 결과만**; 657은 제어·중복을 포함하며 이전 2,313 NOT_READY와 합산 금지 |
| 경량 source-PRE 재생 fixture | 원본 8,432,350B → gzip 470,328B(94.42% 감소), 4 시나리오 5,408/953 유지; 기존 기본·후속 guard Python 재생 원본/압축 정확히 동일. Actions #41797208028 SUCCESS | 압축 기록은 전체 SimC 원본 전투 출력이나 독립 READY를 대체하지 않음 |
| WCL Strict PRE 계약 | `general_rotation_strict_pre_state_engine_v1.py`, Actions #41796021165 **합성 검증** SUCCESS: strict 이전 전이, 같은 시각/만료/불명확한 상태 UNKNOWN | 실제 WCL 최신값 정규화/lock 독립 실증 아님 |
| 역사적 실제 WCL 자료 | #41463589665 discovery 54 casts, #41473060401 별도 report holdout 51 casts. 두 Actions SUCCESS | 최신 source IR과 WCL 비교/완성된 우선순위 검증 **미연결** |
| 허수아비 프로브 | 과거 offline mock 존재 | WoW Retail 실제 클라이언트·API 관측성·훈련 오류 판단 미검증 |

**역사적 범위 주의:** 기존 477 Native IF 중 66 계산 가능/411 UNKNOWN (#41584822737)은 더 오래된 **별도 cohort/계측**에 대한 부분 증거다. 최신 953 중 939 계산 가능/14 UNKNOWN과 분모·coverage가 다르며 두 값을 누적하거나 이전 상태를 조용히 지우지 말 것. 이전 939/953은 IF의 독립 계산이며 실제 스킬 준비 완료를 뜻하지 않는다.

**원본/영수증:** 공식 SimC source commit `b522cded8c26b97dac03fdf56e57a03ec7e8faa6`; Fury profile Git blob `3225992ed5b754ad5d61e8b785d9d859f1eed1be`, Mage Arcane blob `8d06eda4f69374dd1ed2e2d1eb8076b82cbbaf7f`. 최신 CI #41938527598 JSON `native-to-general-rotation-ir-evidence-join.json` SHA256 `ac18255a0570e53968d97007f75a3d16333d64df1d66036c656b7d52070ae93c`, artifact #13374384181(2026-11-12T00:04:45Z 만료). Native compact source artifact #13306210922는 2026-11-11T08:10:09Z 만료 예정; 만료는 외부 증거 제공 한계이지 엔진 고장이 아니다. 소스 증거는 이미 충분히 재생됐으면 다시 사용하고, 필요한 경우 재생성 가능해야 한다.

## 미완료 상태를 세 가지로 분리
1. **증거 부족:** 실제 선택 스킬의 완전한 독립 positive READY (proc, buff/debuff, charge, resource/GCD, replacement, execute/target override, movement), 별도 마법사 Native 자료, AoE/대상 수 전환점, 독립 WCL post-lock holdout, 실제 허수아비 상태 관측.
2. **구현/semantic gap:** Source-pinned 완전 경로 닫힘 검증과 실제 상태 → GateContract 입력의 범용 증명 producer, stateful source action-list/opener parity, READY 판단과 source IR을 실제 결정까지 연결한 결정론적 선택 검증. 파서·IF evaluator·Strict PRE·source join은 이미 구현됨: 중복 개발하지 말 것.
3. **제품 연결 미완료:** 근거 있는 선택 행동 + 이유·대안·확신도·관측 한계의 General Rotation 모델 미완성; 실사용 데이터와 WCL/Blizzard reconciliation 미연결; 허수아비 애드온/API 가능한 범위 검증·사용자 행동 교정 미완료. 이들 부족을 단순 PASS 부족으로 해석하지 않는다.

## 실제 병목·효율 최적화
- **최우선:** 실제 선택 후보의 전체 readiness를 긍정 증명한 0건 문제. 부분 IF와 부정 조건 PASS를 추가하는 것만으로 완료되지 않는다.
- 기존 source-pinned IR, `bounded_decision`, open-world tri-state `decide_candidate`, `NativeProofBridge`, Warrior `SpecAdapter`, portable source markers, WCL strict-PRE 복원기를 **REUSE**.
- 실재 Native 재실행은 기존 fixture로 못 보는 새로운 원시 상태나 타 전문화에서만 필요. 독립 경로는 일괄 조사하고, 같은 입력·계약이면 기존 영수증 재사용. 분리된 검증기/holdout은 공통 parser 오염 위험에 비례해 사용.
- 일반 엔진에 Warrior/Arcane/보스 하드코딩하지 않는다. WCL blind 발견에는 candidate lock 이전 SimC 의미론을 주입하지 않는다.

## 로드맵
- **단기:** 선택된 실행 후보 1개 이상에 대해 실제 원시 PRE + *전체* 가상 메서드/특성 경로의 독립 positive READY closure를 과장 없이 증명 → 현재 Generic IR/bounded evaluator에 재생 → 별도 Arcane Native Cold Start로 일반성 평가. 같은 작업에서 오프닝의 실행 상태와 종료 조건을 관찰·검증한다.
- **중기:** ST/2T/cleave/AoE와 이동/비이동·target breakpoint별 조건을 확장 → WCL 독립 후보 lock/holdout → 잠금 후 SimC/Blizzard 대조 및 중요한 ambiguity만 반사실 시험 → 검증된 General Rotation IR·대안·근거·UNKNOWN 생성.
- **장기:** 사용자 허수아비 실제 행동과 검증된 IR을 동일 evaluator에서 대조. Retail API 현장 관측성 검증 후 허용되는 실시간 피드백, 아니면 연습 후 로그 분석. 광범위 전문화/빌드에 데이터·SpecAdapter 확장.

## Product Exact Next
**완전한 General Rotation 오프닝·조건부 우선순위를 생성·독립 검증할 수 있는 범용 엔진**을 위해 실제 source-pinned positive READY 경로를 닫고, 소스 IR·선행 후보 제외·오프닝/타겟 수 상태를 연결하며, 이후 Mage Native/독립 WCL 실증과 허수아비 평가로 확장한다.

## Session Exact Next
**새 채팅 첫 응답은 GitHub 실제 HEAD/정책 SHA/이전 인계 SHA/영수증을 읽기 전용 복원·검증하고 위 장·단기 로드맵과 완료·미완료를 보고한 뒤 중단한다. 사용자의 새로운 '진행' 이전에는 코드·문서 수정, Python/SimC 실행, WCL/API 수집, Actions/PR/커밋·승격을 하지 않는다.**

## 2026-11-05 branch successor — 실제 선택 후보 READY 증명 공백 및 자원 조건
- **현재 코드 HEAD**: `86849c9e6b5e117f3099cdfaeb623ad01119fb84` (브랜치 격리 변경). 기존 인계 gen3, MAIN/global pointers, FROZEN, Seq578/Seq637은 변경하지 않음.
- **새 코드 경로**: 기존 `simc_native_decision_proof_bridge_v1.py`에 source-row/occurrence/timestamp 단위의 actual selected positive-gap preflight 및 기존 `simc_native_resource_cost_replay_v1.py`를 재사용하는 `RESOURCE` **부분적 독립 양성 증거**를 추가. `simc_native_if_false_priority_frontier_v1.py`에서 정확한 root에 연결하고 `general_rotation_native_ir_pre_evidence_join_v1.py`에 코호트별 사례를 노출. 기존 Generic `decide_candidate`/SpecAdapter/승격된 상태는 변경 없음.
- **실제 Native 증거 재생**: [GitHub Actions #41945383199](https://github.com/degong2-code/zrotationhelper/actions/runs/41945383199) SUCCESS. 기존 5,408 attempts / 2,313 NOT_READY / 3,095 UNKNOWN / 0 READY, IF 953(939 independent, 14 UNKNOWN), 선행 후보 제외된 실행 후보 79건 불변. 최신 JSON SHA256 `995ee68d1aeb9da02b078bb9c16039a0a7e943325cd549800577fea626195c6c`; artifact `13378442205` (2026-11-12T01:00:18Z 만료).
- **정확한 연구 fixture**: moving ST, `at_simc_ms=20031`, APL list `slayer` source_index 6 (0-based), `rampage`, 원본 row SHA256 `217c49dcce32cbc0d975679ed09e0a79c71f05e2615e6566f46bffc9b1ffece2`, same-key occurrence 0. 이전 후보 6개 독립 NOT_READY, 이 선택 행동의 `RESOURCE` 독립 참으로 개선. 남은 blocker 6개: `BASE_VIRTUAL_COMPLETE` (Native post comparator only), `CAST_GCD`, `MOVEMENT`, `NECESSARY_ELIGIBILITY`, `SPEC_OVERRIDE_TOTAL`, `SYNC_LINE`. **스킬 전체 READY·실제 source-order 확정·WCL optimality·허수아비 실수 증명은 여전히 0/UNKNOWN.**
- **검증 실패 보존**: 첫 코드 커밋 `27d033fa...` CI #41944807494 / #41944807502 FAILED (신규 필드 누락 및 기존 synthetic fixture 형식). 교정 `8dfb0fdf...`의 #41944965565 source-pre evidence SUCCESS 및 #41944965873 native CI SUCCESS. 최종 자원조건 successor #41945383199 SUCCESS. 이전 실패를 PASS로 바꾸지 않는다.
- **실제 다음 개발**: 20.031초 선택 사례의 남은 여섯 gate를 원본 SimC 코드·actual PRE source marker·SpecAdapter 경로로 감사하고, source completeness 검증 없는 `closed=True`를 금지. 완전 positive READY 1건 이후에만 G4 source selection parity, Arcane Native, opener/G5 및 WCL 비교로 진행한다.

## 2026-11-05 branch successor — 원본 SimC PRE `SYNC_LINE` 양성 부분 증명
- **실제 코드 HEAD**: `71d0b1b66476e62109001612178fed2f05ac7a8f`; 기존 gen3 인계, MAIN/global pointers/FROZEN은 불변.
- 기존 `simc_native_postguard_source_instrument_v1.py`의 Original `player_t::select_action` PRE 계측과 `simc_native_postguard_source_replay_v1.py:parse_line`을 **재사용**. `NativeProofBridge`에서 exact source row/list/ordinal/timestamp와 원본 base action/ready 경로를 결합. `line_cd_present=1`, `line_cd_ready_ms <= source at_ms`, `has_sync_action=0`이면 독립 수치/포인터 증거 `SYNC_LINE=True`. 원본 공식 SimC `cooldown_t::down() == ready>now` 계약에 한정. sync 대상이 존재하거나 원본 마커/경로가 모호하면 UNKNOWN. observed Native exit/ready는 양성 입력에 사용하지 않음.
- **실제 4-case source PRE 재생**: [Actions #41946685338](https://github.com/degong2-code/zrotationhelper/actions/runs/41946685338) SUCCESS, Python 3.12/3.14 synthetic PASS. JSON SHA256 `50cf08813a5056acd0490e734675a0bf7115688905b9e653c8b24270a276c8cb`, artifact `13379061462` expires 2026-11-12T01:11:00Z. 동일 5,408 action_ready attempts, 953 IF(657 false/282 true/14 unknown), 2,313 NOT_READY/3,095 UNKNOWN/0 READY, 선택 전 후보 모두 제외된 79건 보존.
- **독립된 Native 비침투 회귀**: [Actions #41946685439](https://github.com/degong2-code/zrotationhelper/actions/runs/41946685439) SUCCESS (offline Python 3.12/3.14 and real Native source-oracle regression). 신규 독립 READY나 WCL/허수아비 판정이 아니라 기존 Native source replay의 보존 증거임.
- **고정된 연구 사례**: moving ST at 20,031ms, `slayer[6]` `rampage`, source row SHA256 `217c49dcce32cbc0d975679ed09e0a79c71f05e2615e6566f46bffc9b1ffece2`; 이전 후보 6건 독립 NOT_READY, `RESOURCE`와 `SYNC_LINE` 독립 양성, READY는 UNKNOWN. missing gates **7 → 6 → 5**: `BASE_VIRTUAL_COMPLETE:NOT_INDEPENDENT`, `CAST_GCD:MISSING`, `MOVEMENT:MISSING`, `NECESSARY_ELIGIBILITY:MISSING`, `SPEC_OVERRIDE_TOTAL:MISSING`.
- **실패는 실패로 보존**: 최초 `79aca619...` #41946570894/#41946570928에서 합성 테스트용 mutable pending 재사용으로 FAILED; `71d0b1b...` 테스트 격리 후 actual source/Native PASS. 테스트 fixture 오류와 실제 가설/입력 오류를 구분.
- **다음 실제 구현**: 남은 5개 중 `MOVEMENT`의 원본 virtual `usable_moving()`·`has_movement_directionality()` 경로와 `CAST_GCD` 원시 repeat/GCD 상태, `SPEC_OVERRIDE_TOTAL` class-owned 경로의 완전성부터 공식 SimC 소스와 비교한다. source-pinned full virtual route closure receipt 없이는 `closed=True` 금지, source priority/실사용 허수아비 실수 판정 금지.
