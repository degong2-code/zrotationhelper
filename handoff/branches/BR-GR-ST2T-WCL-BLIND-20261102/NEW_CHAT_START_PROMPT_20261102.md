# zRotationHelper — 새 채팅 시작 프롬프트 (2026-11-02)

아래 본문은 **새 zRotationHelper 프로젝트 채팅에 그대로 붙여넣는 단일 시작 프롬프트**다. 다음 채팅의 첫 응답은 반드시 **복원·증거 검증 보고만** 하고 중단한다.

---

zRotationHelper **General Rotation Research Engine / Target Dummy Trainer** 인계 복원 요청.

**첫 응답에서 해야 할 일은 오직 복원과 검증 보고다.** 저장소를 읽기 전용으로 확인하는 것은 허용하지만, 코드 작성·수정, 새 API/WCL 데이터 수집, SimC 실행, GitHub Actions dispatch, 새 브랜치/커밋/PR, MAIN 승격, FROZEN 수정 또는 후속 실험을 **사용자 승인 없이 시작하지 마라**. 복원 결과를 보고한 다음 사용자 메시지 **'진행'을 기다리며 멈춰라.** 반복 확인이나 파일 복구를 진행의 선행조건으로 만들지 마라.

## 프로젝트 기준

GitHub 저장소: `degong2-code/zrotationhelper`  
현재 개발 브랜치: `work/gr-simc-st-2t-wcl-blind-20261102`  
현재 Branch Owner: `BR-GR-ST2T-WCL-BLIND-20261102`  
공식 제품 범위 ID: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`  
범위 계약 SHA256: `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`  
기준 개발 코드 HEAD (인계 문서 갱신 이전): `1061e9b9686b5f45402d25fa26a797eab4780a89`. 실제 최신 브랜치 HEAD는 새 채팅에서 **읽기 전용으로 재조회**하며 문서 커밋 때문에 이 SHA와 다를 수 있다.

## 반드시 읽을 순서

1. `docs/PRODUCT_SCOPE_LOCK_V1.json` — 제품 범위 전체 정본.
2. `docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md` — 자연어 제품 범위.
3. `AGENTS.md` → `docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md` — 개발 원칙.
4. `docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md` — 실제 인계 세대 및 SHA256 연속성.
5. `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json` — **완전한 정책 스냅샷·이전 인계 연결·현재 상태의 단일 인계 정본**.
6. `docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/CURRENT_STATUS_20261102.md` — 증거와 완료·미완료 매트릭스.
7. `docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/DEVELOPER_NOTES_20261102.md` — 재사용 가능한 엔진 구조·검증 게이트·후속 개발 세부.
8. 관련 Core Contract 및 Project Source의 `GENERAL_ROTATION_PLAYBOOK_DUAL_LANE_SUCCESSOR_PROPOSAL_v2.md`, `PARALLEL_WORKSTREAM_AND_MERGE_CONTRACT.md`. 구 Encounter/NSRT 로드맵은 현행 제품 범위보다 우선하지 않는다.

## 절대 흔들리면 안 되는 장기 목표

**이 프로젝트의 장기 목표는 한 전문화에 대한 구체적 딜사이클 기능을 수작업으로 만드는 것이 아니라, 새로운 SimC/WCL 데이터를 합법적으로 수집하고 오프닝·IF/ELSE 우선순위를 재현 가능하게 연구·검증해 범용 모델을 생산하는 '엔진'의 개발이다.**

연구 순서는 **SimC APL/profile·네이티브 시뮬레이션으로 초기 General Rotation 가설 → WCL 상위 랭커의 독립 숫자/구조 Blind discovery·candidate lock → post-lock replay·Blizzard mechanic truth 대조·필요시 독립 holdout/선택적 counterfactual → 검증된 opener와 ST/2타겟/cleave/AoE 조건부 우선순위 → 경량 허수아비 훈련 오류 교정**이다.

레이드 실전, Encounter Rotation Plan, NSRT, 보스별 실행 계획·타임라인은 **제품 범위 밖**이다. 레이드 로그는 일반 1타겟·2타겟 등의 경험적 검증 fixture에만 쓴다. Strict PRE는 항상 `event_timestamp < action_timestamp`, readiness 미관측은 `UNKNOWN`. SimC 결과나 WCL 빈도만으로 최적성·필수 우선순위를 선언하지 않는다.

**Engine-First 효율 자가점검을 매 단계 수행하라:** 이번 작업이 범용 오프닝/우선순위·허수아비 피드백 정확도를 실제로 높이는가? 과거 자산 복구보다 신규 데이터 Cold Start/Replay가 나은가? 독립 작업들을 하나의 배치로 묶어 중복 API 호출·중복 검증·중복 커밋을 줄일 수 있는가? 이미 존재하는 기준 테스트·완료 판단 기준을 재사용했는가? 가설 실패와 파이프라인/API 실패를 구분했는가? PASS 개수나 Sprint 자체는 제품 성과가 아니다.

## 현시점 검증된 것 / 아직 아닌 것

- **실제 공식 SimC 네이티브 ST/2T 실험 PASS:** Actions `41422148326`; 분노 전사 동일 프로필/바이너리/효과적 APL, seed 31459, fixed 75s. 첫 15초 행동 1T 24건, 2T 24건, 공통 앞 9건. 시퀀스 차이는 실측 **association**이지 우선순위 인과/최적성 증명이 아니다.
- **WCL blind numeric candidate lock 오프라인 PASS:** Actions `41422536988`, Python 3.12·3.14. **실제 랭커 cohort 수집·후속 holdout·SimC 대조는 NOT RUN.**
- **제품 범위·인계 연속성 PASS:** Actions `41423414896`, 5회는 **모의 인계**, 실제 채팅 5회가 아님.
- **General Rotation 모델 완성·허수아비 애드온 실시간 API 실증·WCL live ranker 검증:** 미완료. 확인하지 않은 행동 가용성은 UNKNOWN.
- **MAIN 승격:** 미실시. MAIN 구 HEAD `4790f77f76a75f26ff0558d1d18c16cd9d630c4b`; 문서용 PR #2는 확인 시점 Draft/open/미병합. 공유 상태·FROZEN, `Seq578=FAILED_QUARANTINED`, `Seq637=UNKNOWN` 유지.

## 첫 응답에서 보고할 형식

**(1) 공식 범위·장기 엔진 목표 (2) 최신 브랜치 HEAD·문서 해시·정본 읽기 결과 (3) 완료/미완료/UNKNOWN과 CI 증거의 적용 범위 (4) 미승격·갱신 누락 항목 (5) 현재 blocker와 더 효율적인 접근 (6) Product Exact Next와 Session Exact Next (7) 지금 사용자에게 요구되는 조치**를 간결하게 보고하라.

그다음 마지막 문장을 반드시 **"복원 보고를 완료했습니다. 사용자의 '진행' 지시를 기다립니다."**로 끝내라. 첫 응답에서 추가 개발이나 후속 실험을 시작하지 마라.

*상태와 검증 증거를 복원한 것 자체가 제품 연구를 완료했다는 뜻은 아니다.*
