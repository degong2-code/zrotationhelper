# zRotationHelper — 새 채팅 시작 프롬프트 (Scope Gen7, 2026-11-10)

zRotationHelper를 **읽기 전용으로 독립 복원**한다. 첫 응답은 실제 GitHub 브랜치·MAIN HEAD, 정책 연속성, 최신 개발 증거와 미완료 상태를 검증·보고하는 데만 사용하고, 사용자가 **새 채팅에서 명시적으로 '진행'**하기 전까지 코드/문서 수정·Actions 실행·WCL/SimC/API 호출·PR·MAIN 승격을 하지 않는다.

**공식 제품 목표** `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`: SimC APL/profile 기반 범용 General Rotation 오프닝·조건부 IF/ELSE 우선순위 가설 → WCL 상위 랭커의 **독립 blind 숫자/구조 후보 생성·잠금** → Strict PRE·readiness 검증 후 사후 대조·수정 → ST/2타겟/Cleave/AoE 모델 → 사용자의 허수아비 실제 행동 오류 원인과 개선 피드백. 실시간 WoW API가 지원하지 않는 상태는 UNKNOWN으로 둔다. 과거 보스별 레이드 실행 계획·NSRT·보스 타임라인은 현재 제품 범위 밖이다.

## GitHub 복원 출발점

저장소 `degong2-code/zrotationhelper`. 분기 `work/gr-simc-st-2t-wcl-blind-20261102`; 브랜치 ID `BR-GR-ST2T-WCL-BLIND-20261102`. `main`과 브랜치 HEAD를 **각각 별도 실시간 조회**한다. 격리 브랜치 기록을 MAIN 정본으로 취급하지 않는다.

필수 읽기 순서:

1. `docs/PRODUCT_SCOPE_LOCK_V1.json`
2. `docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md`
3. `AGENTS.md`, `docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md`
4. `docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md`
5. `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json` (**Gen7**) 및 `archive/LATEST_HANDOFF_SCOPEGEN6_BEFORE_20261110.json` (**정확히 보존한 Gen6**, SHA256 `5df57d1c4577bbf408bb5016f5f2001ad7511c15986192c62e725834ba7f6010`). 정책 SHA256 `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`와 parent 링크를 확인한다.
6. **읽기 쉬운 현재 상태** `docs/CURRENT_RESEARCH_STATUS.md` → `docs/RESEARCH_INDEX.md` → `docs/FEATURE_HISTORY_INDEX.md` → `docs/EVIDENCE_NAVIGATION_INDEX.md`. 각 링크가 가리키는 실제 원본 코드·증거·CI를 확인한다.
7. 원본 상세 기록 `docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/HANDOFF_STATUS_20261109.md`, `FEATURE_EVIDENCE_REUSE_INDEX_20261105.md`, `DEVELOPER_NOTES_20261105.md`, `HANDOFF_PREPARATION_WORKLOG_20261109.md`. 최신 내용은 2026-11-10 구간에 추가되어 있으며 파일명 날짜가 전체 내용의 최신성을 뜻하지는 않는다.

## 필수 실증 상태 경계

- 원본 SimC 2전문화 ST/2T/3T/5T 행동 샘플 8개 사례. 분노 전사·비전 마법사 대상이며 전체 전문화 검증이 아님.
- 기존 source 선택 147건에서 독립 원본 IF TRUE 49, IF UNKNOWN 44, 명시적 IF 없음 54. 49건의 최소 충분 PRE 89 operand instances(기존 관측 122). 이는 IF 증거이며 FULL READY 0.
- 기존 비전 마법사 2타겟 Orb source 루트 두 사례의 앞선 APL 행 10건 중 소스 지역 배제 8건, 독립 PRE 불충분 2건 UNKNOWN. 선택 스킬도 FULL READY가 아니다.
- WCL 실증 수집/strict PRE/holdout은 **독립 증거**다. 빈도/반복만으로 원인·우선순위·최적성을 확정하지 않는다.
- 오프닝 종료·현재 Retail 완전 READY/전체 우선순위·허수아비 실제 오답 판정은 아직 UNKNOWN. `Seq578=FAILED_QUARANTINED`, `Seq637=UNKNOWN` 유지.
- 모델 연구 엔진은 전문화 불문 Generic + 외부 `SpecAdapter`이다. 새 전문화의 의미론이나 보스 규칙을 generic core에 하드코딩하지 않는다.
- 새 데이터 수집은 엔진 테스트로 유용하나, 이미 저장된 원본·증거·실행 가능 CI를 재활용하고 무의미한 복원/검증 반복을 피한다.

## 첫 응답 결과 양식

현재 제품 목적, 실제 브랜치/MAIN, Gen7→Gen6→Gen5 정책/byte 체인, 새 연구 내비게이션 경로, 확보한 실증 PASS와 UNKNOWN, `REUSE / EXTEND / REPLACE / UNKNOWN`, evidence/implementation/product 연결 미완료, 장·단기 다음 작업 및 사용자의 로컬 조치를 간결하게 보고한다.

**첫 응답에서는 읽기·검증만 한 뒤 STOP.** 동일 채팅의 이후 작업은 사용자가 새로 '진행'을 보냈을 때만 시작한다. 마지막 문장을 정확히 다음과 같이 작성한다.

복원 보고를 완료했습니다. 사용자의 '진행' 지시를 기다립니다.
