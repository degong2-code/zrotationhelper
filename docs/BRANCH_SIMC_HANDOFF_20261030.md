# zRotationHelper — SimC 연구 브랜치 인계 (2026-10-30 KST)

**성격:** `work/github-ci-bootstrap`의 branch-local 개발·증거 인계. MAIN 승인, 제품 상태 또는 FROZEN 승격 문서가 아니다.  
**작성 기준:** 작업 시작 전 HEAD `ba2aa9dfa5ca823c96974ee6ab060fb1262f5f7d`; `main` `4790f77f76a75f26ff0558d1d18c16cd9d630c4b`. 이후 이 문서 커밋으로 개발 브랜치 HEAD가 달라지므로 새 채팅에서 다시 조회한다.

## 1. 목적과 권위

제품은 현재 시즌 WoW Retail의 일반 조건부 딜사이클을 허수아비 연습에, 검증된 보스별 편차를 레이드 결정에 활용하는 Raid Rotation Helper다. UI는 스킬 아이콘·현지화 이름·짧은 조건/행동으로 지금 결정할 것을 제시한다. 분석 엔진과 UI를 분리한다.

연구는 **SimC APL/profile 가설 생성 + 독립 WCL blind 발견**의 이중 경로다. WCL 후보를 numeric/structural 상태로 먼저 고정하고 이후 SimC 가설·Blizzard mechanic과 대조한다. SimC는 가설이며, 오프라인 CI나 WCL 반복은 최적성·인과성·실전 우선순위의 증거가 아니다. 의사결정 상태는 `timestamp < t`의 유효 전이만 쓴다. 정보 부재는 `UNKNOWN`이다. 규칙의 권위는 현재 프로젝트 지침 → `ROTATION_RESEARCH_SYSTEM_CORE_CONTRACT_V1.md`(현재 MAIN 원본/해시를 별도 확인) → Project Source `GENERAL_ROTATION_PLAYBOOK_DUAL_LANE_SUCCESSOR_PROPOSAL_v2.md`의 WCL/SimC 세부 → `PARALLEL_WORKSTREAM_AND_MERGE_CONTRACT.md`의 owner 경계 순으로 확인한다.

2026-10-28 MAIN Work OS closeout confirmation `MAIN_FINAL_CLOSEOUT_CONFIRMATION_zRotationHelper_20261028_v2.json`은 **Cloud-only, PORTABLE_HANDOFF_ONLY** adoption을 확인했다. 제품 코드·결과·Seq637 승인을 의미하지 않는다. 승인된 runtime identity: environment `20261027-v1.2.1-ordinal-fingerprint-correction`, manifest SHA256 `baca3ce9a4745e54bc81e106b0e6a74acd0ee95384f355ffe466dc5140e1c3cb`, loader SHA256 `790b05d73a97a4d93916edfa5c106285ffc71f149e9ac0a002bc084c61709dcc`. 새 채팅에서 승인 runtime 실제 파일을 확보했다면 먼저 검증하고 Work State를 복원한다. 파일이 없으면 검증했다고 말하지 않는다.

## 2. 확인한 현재 상태

| 항목 | 확인 결과와 범위 |
|---|---|
| `main` | 초기 커밋 `4790f77f...`. 이 GitHub `main`을 로컬 MAIN 제품 전체나 FROZEN baseline으로 간주하지 않는다. |
| 연구 브랜치 | 인계 전 `ba2aa9dfa5ca...`. `tools/research/`의 SimC APL 파서·조건부 IR·priority trace·PRE variable replay·readiness provider·native capture/text events/oracle/JSON2, SimC↔WCL 대조 프로토타입. 모두 연구용. |
| APL 구조 | 앞선 공식 MID2 pinned-profile 실험에서 고양 114행·분노 121행을 IR로 변환했다는 이전 기록. 171개 조건 구문 분석은 실제 상태 평가나 SimC 행동 일치를 뜻하지 않는다. 이 인계 작업에서 해당 외부 프로필 실험을 다시 돌리지 않았다. |
| 현재 CI | [run 40979247340](https://github.com/degong2-code/zrotationhelper/actions/runs/40979247340), HEAD `ba2aa9dfa5ca...`, Python 3.12.15·3.14.9 각각 27개 오프라인 항목 PASS. 두 작업 로그와 약 3.1 KB씩의 receipt artifact 업로드를 확인. 실제 artifact 내용/ZIP을 이 인계에서 재다운로드해 재검증하지 않았다. |
| 실제 SimC/WCL | 실제 `simc.exe` 생산 실행, JSON2 실제 출력, native foreground 분류, 행동별 일치, WCL 실측 검증은 **NOT RUN**. Seq637 사용자 PC 결과 `UNKNOWN`. |
| 기존 785건 | 과거 SimC source-side 연구 자료로 기록된 442+343건. readiness 모두 UNKNOWN. 현재 엔진의 행동 일치율·WCL 실측·제품 완성도로 세지 않는다. 동일 기준 검증은 재사용하되 무의미한 재실행은 하지 않는다. |
| 공유 상태 | `CURRENT_STATE`, global `LATEST_HANDOFF.json`, active manifest, FROZEN, Seq578, 제품 pointer는 이 브랜치에서 바꾸지 않았다. 현재 승인 MAIN 제품 파일과 정확한 최신 SHA는 이 세션에서 확보하지 못해 **UNKNOWN**. Library의 `/zRotationHelper/LATEST_HANDOFF.json`(2026-10-12)은 `BR-WCL-XSP-ACQUIRE` branch handoff이며 현재 global MAIN handoff가 아니다. |

## 3. 완료와 미완료

**구현·오프라인 검증:** 공식 upstream 프로필 또는 로컬 effective APL을 구조화하는 소스 엔진; APL의 일부 조건·변수·목록 흐름에 대한 순차 평가; 명시된 상태 제약을 이용한 readiness; precombat variable replay; native text performed-event 추출과 explicit PRE case 대조; `json2`의 precombat/combat sequence 추출 및 파일 해시 검사. 모르는 상태·operand는 UNKNOWN 또는 BLOCKED로 남긴다.

**미완료:** 전문화·빌드만으로 현재 SimC effective APL과 빌드 상태 자동 확보; 모든 주요 APL 표현식, `target_if`, `pool_resource`, `sync`, `line_cd`, GCD/charge/쿨다운, 전투 전 의미론의 완전 실행; native JSON2 snapshot의 **행동 직전** 상태/Readiness 증명; foreground APL 행동 식별; 여러 상태에서 실행 가능한 IF/ELSE 모델 생성; 실제 native SimC 행동별 정합성; WCL blind cohort와 holdout; 게임 내 UI. 따라서 SimC Engine **미완성**, 현 출력은 비실전 연구 가설이다.

**병목:** 유효한 실제 SimC reference capture와 상태 시점·범위 증거가 없다. JSON2의 행동 시점 snapshot을 자동으로 PRE로 소급하면 미래 정보 누출이 생긴다. 사용자 프로필/로그는 민감할 수 있어 공개 저장소에 올리지 않는다. MAIN의 최신 approved source/manifest가 여기에는 없어 통합·승격 판단도 보류한다.

## 4. 다음 작업과 검증 기준

1. 먼저 현재 승인 runtime/MAIN handoff·CURRENT_STATE·active manifest의 실물 및 SHA를 확보해 브랜치 base의 호환성을 확인한다. 접근 불가 시 `MAIN_ACTIVE_SOURCE=UNKNOWN`으로 유지하고 branch-local 개발만 한다.
2. SimC 자체 완성을 우선한다. 작은 **실제 native capture**(가능한 공개 공식 프로필 또는 사용자의 로컬 private 프로필)에서 JSON2/text/effective APL의 SHA·spec/build·actor·시간 단위를 고정한다. 전투 전과 전투 중 sequence, 실제 foreground 여부, 각 필드의 기록 시점을 검토한다. 공개 프로필은 현재 게임 버전·사용자 빌드 일치 증거가 아니다.
3. 필드별 `PRE_VERIFIED / SAME_TIME_AMBIGUOUS / UNKNOWN`을 정의하고, 증거 있는 이전 전이만 readiness/condition provider에 연결한다. 모르는 쿨다운·대상·자원은 임의 READY 처리하지 않는다. unsupported semantics를 빈도와 사용자 영향으로 분류해 공통 동작부터 구현한다.
4. 고정된 spec/build/APL과 검증된 PRE 상태의 native foreground action에 대해 `match / difference / unknown / excluded`을 비교한다. 분모·제외 사유와 출처를 함께 기록한다. 이후 독립 WCL blind lock과 post-lock 대조를 진행한다.
5. 이미 통과한 같은 SHA의 27개 오프라인 CI는 회귀 기준으로 재사용한다. 코드/fixture/계약 변경에 영향을 받는 검증만 추가 수행하고, 새로운 HEAD에는 새 CI 범위를 명시한다. 실제 SimC 행동 정합성과 user-facing IF/ELSE가 충족되기 전 `완성`으로 표현하지 않는다.

효율 판단: 합성 항목 수를 늘리기보다 실제 native output 한 건의 PRE semantics를 고정하는 일이 다음 불확실성을 가장 크게 줄인다. 공개 runner에서 고정 공개 프로필과 SimC 실행 파일을 재현할 수 있으면 로컬 사용자 요청을 줄일 수 있지만, 바이너리·프로필 버전과 결과의 적용 범위를 별도로 확인한다. 독립적인 조사·검증은 묶어 진행하되 동일 소스/권위 파일의 동시 수정을 피한다.

## 5. 새 채팅 읽는 순서

1. 현 프로젝트 지침과 첨부 Project Source 두 개; 먼저 승인 runtime을 실제로 검증하고 Work State 복원. 로컬에 존재하지 않는 Core Contract/MAIN 문서는 찾거나 요청하고, 기억/브랜치 문서로 대체하지 않는다.
2. 이 문서의 기준·미완료·증거 범위.
3. GitHub `main`, `work/github-ci-bootstrap` HEAD, compare, 이 문서의 최신 SHA를 재조회. 브랜치가 전진했으면 새 코드/CI를 재대조.
4. `docs/SIMC_ENGINE_SOURCE_TO_PRIORITY_RUNBOOK.md` → `tools/research/simc_apl_source_engine.py`, `simc_apl_priority_trace.py`, `simc_apl_precombat_replay.py`, `simc_apl_readiness_provider.py`, `simc_native_reference_capture.py`, `simc_native_json_sequence.py`, `simc_native_oracle_reconciliation.py` → `tools/ci_offline.py`. 필요할 때만 `docs/REAL_EVIDENCE_INTEGRATION_GATE_20261029.md`와 이전 소스 감사 자료를 읽는다.
5. [기준 CI run](https://github.com/degong2-code/zrotationhelper/actions/runs/40979247340)의 head SHA, 두 job 로그와 receipts의 적용 범위를 확인. CI artifact는 7일 보존이므로 만료되면 로그를 근거로 명시한다. 새 문서 커밋 이후 CI가 별도로 돌면 해당 SHA의 범위를 다시 확인한다.

## 6. 인계 범위와 미승격

이 문서는 개발 브랜치의 상태/개발자 노트이며 global `LATEST_HANDOFF.json`이나 제품 `CURRENT_STATE`가 아니다. 이번 인계에서 Project Instructions·두 Project Sources·Core Contract·MAIN state/manifest·FROZEN·Seq578·Seq637·제품 코드는 갱신하지 않았다. MAIN 실물 부재와 live SimC/WCL 부재가 이유다. 이 문서의 GitHub 반영 자체도 MAIN 승격이 아니다.

## 7. 새 채팅 시작 프롬프트

> zRotationHelper 인계를 복원해 줘. 먼저 현 프로젝트 지침과 두 Project Source를 읽고, 승인된 Cloud Work OS runtime의 실제 파일을 확보할 수 있으면 manifest/loader SHA를 검증하여 Work State를 복원해. 다음으로 개발 브랜치 `docs/BRANCH_SIMC_HANDOFF_20261030.md`를 읽고 GitHub `main` 및 `work/github-ci-bootstrap`의 현 HEAD와 CI run 40979247340의 SHA·검증 범위를 대조해. 최신 MAIN `LATEST_HANDOFF`, `CURRENT_STATE`, active manifest는 실물·해시를 확인하고, 없으면 UNKNOWN이라고 명시해. SimC Engine은 미완성이며 실제 native SimC/WCL 검증은 NOT RUN, Seq637은 UNKNOWN이다. 장기 목표(정확한 일반 IF/ELSE 연습과 보스별 검증된 편차·실전 UI)에 비추어 현재 작업의 필요성을 계속 점검해. 독립 작업은 중복과 충돌 없이 묶어 처리하고, 동일 SHA·동일 기준의 완료 검증은 재사용해. 권위 파일과 FROZEN은 MAIN 승격 전 변경하지 마. **먼저 복원 결과와 증거의 적용 범위·막힌 점·다음 작업만 보고하고, 내가 '진행'이라고 할 때까지 구현·승격을 시작하지 마.**
