# zRotationHelper — Engine-First / Reproducible Research Charter

**사용자 승인:** 2026-11-02  
**목적:** 개발이 과거 자산 복구에 묶여 멈추지 않도록, 앞으로의 우선순위·자가점검·검증 기준을 지속 참조한다.  
**적용 범위:** 이 브랜치의 개발 및 인계 판단 기준. 공유 MAIN 권위로의 승격은 MAIN만 수행한다. 기존 FROZEN evidence, 실험의 threshold/holdout, 기존 계약을 소급 변경하지 않는다.

> **과거 시스템을 보존하려고 개발하지 않는다. 필요할 때 새로운 데이터를 수집·재생·독립 검증하고, 전문화·특성·대상 수가 달라져도 일반화되는 General Rotation 엔진을 개발한다. 과거 자료는 자산이지만 실행과 개발의 전제조건은 아니다.**

**Handoff continuity:** Each new chat/owner reads [machine-readable product scope lock](PRODUCT_SCOPE_LOCK_V1.json), [five-hop handoff protocol](HANDOFF_CONTINUITY_PROTOCOL_V1.md), and [new-chat boot](../handoff/NEW_CHAT_BOOT_PROMPT.md). Do not let older Raid/NSRT plans override the current user-declared objective.

**2026-11-02 공식 제품 범위 변경:** [General Rotation 오프닝·우선순위 + 허수아비 훈련 애드온](PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md)이 기존 Encounter Plan·레이드 실전·NSRT 목표를 대체한다. 본 Charter의 개발 철학은 유지되지만 구제품 범위와 충돌하는 문장은 새로운 제품 범위 문서가 우선한다.

## 1. 무엇이 완성 기준인가?

성공은 복구한 파일 개수, CI PASS 개수, 과거 포인터의 복원 여부가 아니다.

- 처음부터 새 자료를 수집할 수 있는가? (자격증명은 사용자 환경의 `.env`, 비밀은 커밋 금지)
- 같은 입력 증거로 상태·후보·판정을 재생 및 재현할 수 있는가?
- WCL/SimC/Blizzard 각각의 역할을 분리한 채 **일반화 가능한 조건부 IF/ELSE General Rotation**을 산출하는가?
- 새로운 전문화·특성·1/2/AoE 타겟 상황이 들어오면 generic engine 변경 없이 데이터·semantic layer로 확장 가능한가?
- 결과가 General Rotation 오프닝·조건부 우선순위와 허수아비 연습 피드백(어느 행동이 왜 잘못되었고 어떻게 고치는가)으로 연결되는가?

## 2. 우선순위: 복원보다 작동

기본 개발 순서는:

1. **현재 실행 가능한 최소 엔진과 독립 재현 환경**을 확보한다. 과거 MAIN 실행 경로에 안전 문제가 있으면 그 진입점을 우회하거나 successor를 만든다.
2. **Fresh WCL 수집 → 원본 snapshot → 정규화 → Strict PRE → observability → WCL blind candidate lock** 경로를 작동시킨다.
3. 별도 **SimC APL/profile → semantic hypothesis bootstrap** 경로를 만든다. WCL blind candidate lock 전에는 이 경로의 답을 WCL 독립 발견에 주입하지 않는다.
4. 두 경로를 candidate lock 이후 비교(replay: match/conflict/missing/unknown)하고 Blizzard truth와 대조한다. 사용자에게 중요한 ambiguity만 선택적 SimC counterfactual / independent holdout으로 확대한다.
5. 검증된 **General Rotation opener + IF/ELSE decision IR → 허수아비 연습 오류 판정 → 경량 애드온 또는 세션 후 분석 피드백**을 연결한다. 보스별 Encounter deviation, 레이드 실전 UI, NSRT는 현재 개발 범위에서 제외한다.

이전 단계의 전체 복원이 완료될 때까지 다음 단계를 무조건 막지 않는다. 다만 검증 전의 후보·추정을 FROZEN 또는 gameplay-ready로 승격하지 않는다.

## 3. 새 자료 수집은 엔진의 E2E 테스트

한 번의 실제 수집을 다음 계약의 통합 시험으로 사용한다.

| Gate | 기대 동작 |
| --- | --- |
| Cold start | 과거 snapshot/cache 없이 새 자료 수집 가능 |
| API / identity | 공식 WCL API와 합법 접근 로그만 사용; report/fight/actor/ability/target identity 추적 |
| Snapshot & replay | 입력·버전·고정 조건 기록, 동일 증거에서 결정론적 재생 |
| Resume | API 제한/중단 후 중복 최소화하며 이어서 수집 |
| Strict PRE | `state_at_action(t)`은 오직 `timestamp < t` 전이만 사용 |
| Observability | 미관측 readiness/resource를 거짓 확정하지 않고 `UNKNOWN` |
| Blindness | WCL 독립 후보는 SimC semantics 유입 전 lock |
| Generality | 전문화·특성·ST/2타겟/AoE 변경 시 generic code 재작성 불필요 |
| Output | 실제 조건·추천 스킬·대안·확신도·증거·제한점 표시 |

**단, 과거와 동일한 원본 획득이 불가능한 것이 항상 엔진 결함은 아니다.** 로그 삭제, API 접근/보존 범위, Blizzard 패치 변경 등 외부 제약은 엔진 수집·재현 결함과 분리해서 기록한다.

## 4. 과거 코드·계약의 취급

- 기존 코드는 **검증된 기능을 재사용하기 위한 자료**이지, 새 구조가 따라야 할 절대 설계가 아니다.
- 한 기능에 더 단순하고 재현 가능한 구현이 있으면 **교체를 허용**한다. 기존 코드 SHA 동일성 자체가 새 엔진의 목표가 아니다.
- 기존 **FROZEN·raw evidence·holdout·정확도 판정은 불변**으로 보존한다. 새 증거와 충돌하면 별도 successor/검증으로 처리한다.
- 기존 MAIN의 불확실한 권위와 역사적 실행 옵션이 개발을 막으면, 이를 동결·격리하고 **새 개발용 실행 경로**를 독립적으로 만든다. 과거 불안전한 `RUN_zRAID_MAIN.py` 실행을 우회한다.
- MAIN만 공유 `CURRENT_STATE`, architecture contract, canonical registry, active manifest, production pointer, FROZEN baseline을 승격한다. Branch는 **MERGE_READY / PROMOTION_PROPOSED**까지만 주장한다.

## 5. 개발 단계마다 반드시 묻는 질문

1. **이 일이 새 데이터로 더 정확하고 일반화 가능한 결정을 생산하는 엔진에 직접 기여하는가?**
2. 같은 기능을 과거 복원 없이 더 적은 코드·단계·비용으로 구현할 수 있는가?
3. **실제 재수집·재생·E2E 테스트가 더 가치 있는 다음 검증인가**, 아니면 과거 파일 해시·호환성 재검증인가?
4. 검증된 동작과 미검증 주장(OBSERVED/CANDIDATE/UNKNOWN/REPLICATED/FROZEN)을 명확히 나눴는가?
5. 이번 변경으로 오프닝·IF/ELSE 판단 또는 허수아비 연습 오류 교정이 개선되는가?
6. 실패가 **가설 실패**인지, **수집·파이프라인 실패**인지, **외부 제공 제약**인지 구분했는가?

**검사만 늘어나는 개발 방지:** 과거 증거가 이미 충분하고 파일이 바뀌지 않았다면 동일 검사를 반복하지 않는다. 테스트 개수는 KPI가 아니다. 새 데이터 E2E 실행과 사용자 의사결정 향상을 우선한다.

## 6. 지금부터의 개발 Exact Next (제품 방향)

**최소 실행 가능한 Fresh-Data Research Engine**을 별도 개발 진입점으로 구성한다.

1. 공식 WCL 수집기·credential autodiscovery(`.env`)·checkpoint/cold-start·snapshot 재생의 최소 골격.
2. 신규 합법 공개 전투 1건을 fixture로 사용한 오프라인 리플레이 및 Strict PRE/UNKNOWN 검증.
3. 동일한 일반 IR을 사용하는 blind WCL lane과 SimC bootstrap lane의 기초 출력 생성.
4. 1 전문화에서 출발해 다른 전문화/특성/대상 수 fixture로 generic boundary 확인. 실제 보스 전투 로그는 일반 로테이션 검증 표본으로 사용할 수 있지만 보스별 실행 계획을 산출하지 않는다.
5. 로테이션의 유효성·적용 범위가 독립 검증되기 전에는 현재 시즌 최적성이나 관측 불가 상황의 실수 판정을 주장하지 않는다.

진입점 구현은 **소스의 안전한 격리와 공식 자격증명 정책이 갖춰진 뒤에 실행**한다. CI/샌드박스에서 먼저 synthetic, 이어 실제 fresh API 시험을 분리 보고한다.

## 7. 모든 새 채팅 / 인계에서 읽는 규칙

- 먼저 **새 제품 범위 문서** `PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md`와 **이 문서**를 읽고, 최신 MAIN authoritative Runtime/Work State가 있다면 확인한다.
- 이 문서의 개발 철학은 사용자가 승인한 방향이며, MAIN 승격 전에는 브랜치 제안/노트로 취급한다.
- 브랜치 `LATEST_HANDOFF.json`은 본 문서 경로를 `read_first`로 가리킨다.
- 최근 과제가 과거 파일 복구에 멈춰 있다면 본 Charter의 **Cold Start → Fresh Data → Replay → Decision** 경로로 재평가한다.
- `Seq578=FAILED_QUARANTINED`, `Seq637=UNKNOWN`과 미검증 증거 상태를 조용히 덮어쓰지 않는다.

**한 문장 자가점검:** *“우리는 낡은 데이터를 지키는 시스템을 만들고 있는가, 아니면 새 데이터를 다시 생산하고 더 나은 로테이션 결정을 검증할 수 있는 엔진을 만들고 있는가?”*
