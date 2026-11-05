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
