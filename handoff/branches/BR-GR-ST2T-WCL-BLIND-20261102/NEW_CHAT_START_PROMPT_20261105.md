# zRotationHelper — 새 채팅 시작 프롬프트 (2026-11-05, generation 3)

GitHub 저장소 `degong2-code/zrotationhelper`. 브랜치 `work/gr-simc-st-2t-wcl-blind-20261102`. 인계 시점 검증된 코드 HEAD `d4358213e451194e1a78d3d29292857e8f7125e2`, 인계 준비 시작 HEAD `5e883b990248cc4a4eb15e481990316ad951620a`; **현재 브랜치 HEAD는 새 채팅에서 반드시 직접 재조회**. MAIN은 인계 준비 시 `4790f77f76a75f26ff0558d1d18c16cd9d630c4b` (읽기 전용 관측값). 정책 ID `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`; policy SHA256 `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`.

**첫 응답에서는 읽기 전용 복원·독립 증거 대조·장단기 로드맵 보고만 수행하고 중단하라. 내가 새로운 '진행'이라고 명시하기 전에는 코드/문서 개발·수정, Python·Native SimC 실행, WCL/API 수집, GitHub Actions 실행·rerun, 커밋·PR·브랜치 변경·승격을 하지 마라.** 과거 대화의 '진행' 승인으로 새 채팅을 자동 실행하지 않는다.

## 반드시 읽을 순서
1. `docs/PRODUCT_SCOPE_LOCK_V1.json`; `docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md`.
2. `AGENTS.md`; `docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md`; `docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md`.
3. `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json` generation3. 전체 정책 snapshot, policy SHA, parent SHA, archive 파일 대조.
4. `docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/HANDOFF_STATUS_20261105.md`; `docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/FEATURE_EVIDENCE_REUSE_INDEX_20261105.md`; `docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/DEVELOPER_NOTES_20261105.md`; `docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/HANDOFF_PREPARATION_WORKLOG_20261105.md`.
5. `docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/SIMC_APL_MODEL_COMPLETION_CONTRACT_20261103.md` 및 원본 code/영수증/최근 Actions와 Project Core Contract·dual-lane playbook. 과거 Encounter/NSRT 로드맵을 최신 제품 목표로 복원하지 않는다.

## 제품 목적·엔진 우선
최종 제품은 **개별 고술/전사/마법사 딜사이클이나 기능 조각이 아니라**, 새로운 전문화·빌드·ST/2T/cleave/AoE·이동 조건에서도 소스에서 조건부 오프닝과 IF/ELSE 우선순위를 생성·독립 검증하는 **범용 General Rotation 연구·검증 엔진**과, 검증된 IR을 재사용하는 **경량 허수아비 연습 오류 피드백**이다. SimC-first 초기 가설과 WCL blind 독립 후보 잠금은 별개 경로다. 관측 불가 상태는 UNKNOWN. 보스별 계획·레이드 실전 가이드·NSRT는 제외.

**매 작업 전에 기존 개발 기록→기능별 인덱스→코드/원본→실제 Actions 영수증을 검색하여 REUSE/EXTEND/REPLACE/UNKNOWN을 판정하라.** 같은 증거와 통일된 완료 기준을 재사용하고, 독립 작업은 묶어 처리하라. 원본 재수집이나 반복 Native 빌드는 새 정보가 필요할 때만 한다. 검증 PASS 수보다 새로운 전문화에서 재현 가능한 정확한 READY/선택/훈련 개선이 중요하다. generic semantics에 Warrior나 특정 보스 hardcode 금지; SpecAdapter 사용.

## 첫 복원에서 반드시 독립 대조할 숫자·적용 범위
- 최신 source join Actions #41938527598 SUCCESS: 5,408 source readiness 시도, 953 Native IF 관측, 독립 FALSE 657/TRUE 282/UNKNOWN 14(939/953 계산 가능), 증거 JSON SHA256 `ac18255a0570e53968d97007f75a3d16333d64df1d66036c656b7d52070ae93c`. IF 판정과 full skill READY는 다르다. 이 657을 이전 2,313 NOT_READY에 더하지 말 것.
- 범용 source IR Fury 121행 + Arcane 51행 = 172행; Actions #41799789205 및 #41935516360 SUCCESS. 원본 state/READY 없으면 172 UNKNOWN. Arcane Native 준비 상태 자체는 NOT_RUN.
- Native source-proof cohort: 5,408 action_ready 시도 중 2,313 independently NOT_READY/3,095 UNKNOWN/0 complete READY. 387 source returns = APL 제어 213 + 실행 후보 174, 이 중 79/174 이전 후보 모두 제외되지만 당사자 READY UNKNOWN. Actions #41794691821.
- 과거 477 Native IF는 66 independently decidable / 411 UNKNOWN (#41584822737), 최신 953과 별도 cohort. 기존 WCL discovery 54 casts와 별도 holdout 51 casts (#41463589665/#41473060401)는 수집됨, 아직 General Rotation 우선순위 독립 확증 아님.
- Native 압축 PRE fixture 8,432,350→470,328B(94.42% 축소), 원본/압축 guard replay 동등 #41797208028; 실제 유효기간과 재생 방법 확인. WCL strict PRE replay는 합성 검증, 실제 최신 상태 수집/잠금 비교는 미완료.
- 사용자-facing General Rotation opener/우선순위, 독립 positive READY, 독립 WCL reconciliation, 실제 WoW 허수아비 API·피드백은 **아직 미완료**. 증거 부재 / 구현 결손 / 제품 연결 미완료를 반드시 구분하라.

## 첫 응답에 포함할 보고
공식 범위·실제 GitHub HEAD 및 MAIN 관측값·policy SHA·handoff generation/parent·증거 및 적용 범위·완료/미완료·병목·재사용/효율 대안·장단기 로드맵·Product Exact Next·Session Exact Next·사용자 당장 할 일을 간결하게 보고하라. 잘못된 이전 HEAD 또는 시간 제한 artifact는 부정확한 현재 상태로 표시하지 마라. 이 메시지는 개발 승인 명령이 아니다.

**마지막 문장은 반드시:** 복원 보고를 완료했습니다. 사용자의 '진행' 지시를 기다립니다.
