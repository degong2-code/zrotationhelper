# zRotationHelper — Parallel Workstream & Merge Contract

> **제품 범위 우선순위 (사용자 공식 변경: 2026-11-02)**  
> 제품 범위 ID: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`  
> 최신 제품 범위 정본: `docs/PRODUCT_SCOPE_LOCK_V1.json` 및 `docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md`.  
> 이 문서는 **병렬 개발·소유권·병합 운영 계약**이며, 제품 범위를 새로 정하거나 과거 로드맵을 복원하는 권한이 없다. 충돌 시 최신 사용자 승인 제품 범위가 우선한다. 최종 제품은 **SimC APL 기반 일반 로테이션 가설 → WCL 랭커 독립 검증·수정 → General Rotation 오프닝·조건부 우선순위 완성 → 경량 허수아비 훈련 피드백**이다.  
> **Encounter-Specific Rotation Plan, 레이드 실전 안내, NSRT·레이드 타임라인·보스 가이드 출력은 현행 개발 목표에서 제외**한다. 과거 보스 로그는 일반 ST·2타겟·AoE 등의 검증 fixture로만 사용할 수 있다. 사용자의 새로운 명시적 변경 선언 없이는 제외 기능을 복원하지 않는다.

## 1. 목적

이 문서는 zRotationHelper / zRAID_DEALCYCLE 프로젝트에서 병렬 작업을 사용할 때의 공식 운영 계약을 정의한다.

목표는 채팅 수를 늘리는 것이 아니라 **전체 critical path를 줄이면서 authoritative state와 semantic consistency를 보존하는 것**이다.

병렬화는 다음의 순이익이 명확할 때만 사용한다.

- wall-clock time 단축
- 긴 실행/검증 대기시간 활용
- context isolation
- subsystem별 집중도 향상
- independent validation
- defect/research 격리

다음 비용이 이익보다 크면 병렬화하지 않는다.

- branch dependency 관리
- 중복 조사/중복 구현
- stale base
- merge/revalidation 비용
- semantic drift
- 동일 artifact 동시 수정 위험
- MAIN integration 부담

필요하면 일부만 병렬화하는 hybrid structure를 사용한다.

---

## 2. MAIN / Integration Owner

기존 메인 프로젝트 채팅을 기본적으로 `MAIN / Integration Owner`로 유지한다.

MAIN만 다음 shared authoritative state를 승격할 수 있다.

- CURRENT_STATE
- architecture / semantic contract
- canonical action-family registry
- General Rotation 오프닝·ST/2타겟·AoE 조건부 우선순위 authoritative baseline 및 허수아비 훈련 평가 계약
- active manifest
- canonical DB/cache
- production pointer
- shared runtime configuration
- project-wide roadmap authoritative status
- global `_UPLOAD_TO_CHATGPT/LATEST_HANDOFF.json`

Branch는 위 authoritative state를 직접 교체하거나 승격하지 않는다.

---

## 3. Branch가 할 수 있는 일

Branch는 자신의 ownership 범위에서 다음을 독립적으로 수행할 수 있다.

- source audit
- research
- data/state reconstruction
- candidate discovery
- implementation
- branch-local validation
- independent validation
- proposed patch
- versioned successor artifact
- unresolved blocker 정리
- cross-branch dependency/interface requirement 정의
- merge handoff 작성

Branch lifecycle의 최대 상태는 원칙적으로 다음과 같다.

- `OBSERVED`
- `CANDIDATE`
- `BRANCH_VALIDATED`
- `MERGE_READY`
- `PROMOTION_PROPOSED`

Branch가 스스로 project-wide `FROZEN` 또는 authoritative promotion을 선언하지 않는다.

---

## 4. Branch 생성 기준

다음 조건이 충족될수록 별도 branch가 적합하다.

- 다른 작업의 결과를 기다리지 않고 의미 있는 조사/구현/검증을 시작할 수 있음
- 서로 다른 source/artifact/subsystem을 소유함
- 같은 semantic decision을 중복해서 내리지 않음
- shared authoritative file을 동시에 수정하지 않아도 됨
- branch-local output interface를 명확히 정의할 수 있음
- context isolation의 이점이 큼
- merge/revalidation 비용보다 작업량이 충분히 큼

다음 경우 별도 branch를 만들지 않는다.

- 작업량이 작아 MAIN에서 처리하는 편이 빠름
- 같은 source나 같은 semantic authority를 지속적으로 동시에 수정해야 함
- 앞 단계 결과 없이는 의미 있는 다음 작업을 시작할 수 없음
- branch communication/merge 비용이 작업 자체보다 큼
- 동일 semantic decision을 여러 branch가 각각 내려야 함
- 거의 완료된 작업을 형식적으로 분리하는 경우

---

## 5. Base pinning / stale-base 관리

모든 branch artifact와 handoff에는 가능한 한 다음을 기록한다.

- `branch_id`
- `base_authoritative_stage`
- `base_authoritative_handoff_sha256`
- 관련 frozen contract SHA256
- 관련 source/artifact SHA256
- branch-local run stamp

MAIN이 진전된 후 branch가 오래된 base를 사용 중이라면 branch는 이를 숨기지 않고 `stale_base` 여부를 명시한다.

Stale base라고 해서 결과를 자동 폐기하지는 않는다. MAIN은 해당 변화가 branch 결과와 semantic compatibility에 영향을 주는지 판단하고 필요한 focused revalidation을 수행한다.

---

## 6. Namespace

병렬 작업에서는 global convenience pointer 충돌을 막기 위해 branch-local namespace를 사용한다.

권장 branch handoff:

`_UPLOAD_TO_CHATGPT/branches/<BRANCH_ID>/LATEST_HANDOFF.json`

권장 branch artifact:

`active/branches/<BRANCH_ID>/...`

Global:

`_UPLOAD_TO_CHATGPT/LATEST_HANDOFF.json`

은 MAIN 전용이다.

Shared frozen artifact는 branch에서 read-only로 사용한다.

---

## 7. Ownership / Boundary

각 branch는 최소한 다음을 명시한다.

### Branch ID / 이름
짧고 명확한 식별자.

### 목적
이 branch가 해결하는 정확한 문제.

### Ownership
소유하는 source / artifact / semantic 영역.

### Boundary
직접 수정하거나 흡수하지 말아야 할 영역.

### Inputs
시작 시 필요한 authoritative state / contract / source / evidence.

### Outputs
MAIN에 반환할 successor artifact / validation evidence / handoff.

### Dependencies
다른 branch/MAIN과의 interface requirement.

### Validation Gate
integration-ready 판단 기준.

### Merge Risk
병합 시 focused revalidation이 필요한 지점.

---

## 8. Cross-branch dependency 규칙

Branch가 다른 branch 또는 MAIN 영역의 결함을 발견했다고 해서 그 구현까지 자동으로 흡수하지 않는다.

원칙적으로 다음 형태로 반환한다.

`cross_branch_dependency: <owner> needs to provide/fix <requirement>`

다만 branch 자체 결과가 성립하지 않을 정도로 interface가 잘못되었고, 분리 유지보다 ownership 재조정이 명백히 안전한 경우에는 branch 구조를 다시 설계한다.

Boundary 자체가 목적은 아니다. 최종 목표는 정확성과 개발 효율이다.

---

## 9. Independent validation branch

Independent validation은 구현 속도보다 **가정 독립성**이 실제로 확보될 때 사용한다.

특히 다음과 같은 경우 별도 validator가 유용할 수 있다.

- producer와 validator가 동일한 잘못된 parser/transform assumption을 공유할 위험
- counterfactual paired-run 결과
- semantic/provider transformation
- canonical identity mapping
- state reconstruction의 중요한 변환
- frozen threshold/window acceptance
- authoritative promotion 직전 핵심 artifact

Independent validator는 가능하면 producer의 summary를 신뢰하지 않고:

`raw evidence + frozen contract`

에서 결과를 독립 재계산한다.

검증 branch를 늘리는 것 자체는 목적이 아니다.

---

## 10. Branch merge handoff

Branch 완료 시 가능한 한:

`BRANCH_<BRANCH_ID>_MERGE_HANDOFF.json`

을 만든다.

최소 권장 필드:

- `branch_id`
- `base_authority`
- `branch_scope`
- `owned_artifacts`
- `validation`
- `key_results`
- `evidence_level`
- `unresolved_blockers`
- `cross_branch_dependencies`
- `merge_risks`
- `focused_revalidation_required`
- `proposed_successor_artifacts`
- `shared_authoritative_state_mutated: false`
- `scope_continuity` (현재 제품 범위 ID, 전체 정책 스냅샷, policy SHA256, 인계 세대, 이전 인계 SHA256)
- `product_exact_next` (General Rotation 오프닝·우선순위 또는 허수아비 훈련 목표)
- `chat_exact_next` (해당 세션의 구체적 후속 작업)

---

## 11. Merge / Promotion flow

권장 흐름:

`branch work`
→ `branch-local validation`
→ `merge handoff`
→ `MAIN 전달`
→ `cross-branch compatibility 검토`
→ `필요한 focused revalidation`
→ `integration candidate`
→ `authoritative promotion`

MAIN은 branch의 결론을 기계적으로 복사하지 않는다.

다음을 검토한다.

- branch base가 아직 유효한가
- 다른 branch 결과와 semantic conflict가 없는가
- frozen invariant를 침범하지 않는가
- candidate가 주장 강도에 맞는 evidence를 갖는가
- integration으로 인해 기존 regression이 깨지지 않는가

---

## 12. Branch와 shared General Rotation / Dummy Training state

General Rotation 오프닝·조건부 우선순위 및 허수아비 훈련 평가 모델은 여러 branch의 후보를 받을 수 있지만, 최종 authoritative rule/model promotion은 MAIN에서만 한다. Encounter Plan은 현재 제품 산출물이 아니며, 과거 보스별 로그는 일반 로테이션의 상황별 검증 근거로만 활용한다.

예:

- Proc branch가 proc-conditioned candidate를 발견
- Target-count branch가 target-count breakpoint candidate를 발견
- 두 candidate가 interaction을 가진다면 각 branch가 상대 branch의 rule을 수정하지 않고 MAIN이 interaction revalidation을 수행

이 구조를 통해 branch-local discovery 속도와 project-wide semantic consistency를 동시에 유지한다.

---

## 13. 성공 기준

병렬 구조의 성공은 branch 수가 아니라 다음으로 판단한다.

- critical path가 실제로 줄어들었는가
- MAIN context가 더 명확해졌는가
- duplicated implementation이 줄었는가
- independent validation의 가치가 있었는가
- stale-base/merge 재작업이 통제되었는가
- authoritative state가 단일하고 추적 가능한가

병렬화가 이 기준을 만족하지 않으면 다시 순차 구조로 축소한다.

---

## 14. 최신 제품 범위 준수 및 다중 인계

본 계약의 병렬 운영 절차는 **현행 제품 범위 고정 계약**에 종속된다.

- **연구의 전체 순서:** SimC APL/profile에서 General Rotation 초기 가설·오프닝을 추출 → WCL 상위 플레이어 로그로 독립 검증·수정 → 검증된 ST/2타겟/cleave/AoE IF/ELSE 모델을 산출 → 허수아비 훈련 피드백에 사용한다.
- **WCL blind는 내부 검증 절차:** WCL의 숫자·구조 기반 후보는 SimC의 답을 유입하기 전에 고정하고, 이후 두 경로를 비교한다. 전체 연구를 WCL-first로 변경하지 않는다.
- **엔진 우선:** 과거 MAIN·소스·로그를 완전히 복원할 때까지 새 수집·재생·분석 엔진의 개발을 멈추지 않는다. Fresh WCL 수집, Cold Start, checkpoint/resume, deterministic replay는 개발 E2E TEST다. 기존 FROZEN 증거는 불변이다.
- **애드온의 역할:** 연구 엔진과 분리된 경량 허수아비 연습 인터페이스다. 합법적으로 관측 가능한 조건에서만 실시간 오류를 판정하고, 미관측 상태는 `UNKNOWN`; 필요한 경우 연습 후 전투 로그 분석으로 피드백한다.
- **현재 제외:** Encounter Rotation Plan, 레이드 실전 안내, NSRT, 보스별 타임라인·가이드. 해당 주제의 역사적 Branch handoff·evidence는 보존하되 active 제품 목표나 다음 작업으로 재승격하지 않는다.
- **매번 인계 시:** `docs/PRODUCT_SCOPE_LOCK_V1.json` → `docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md` → `AGENTS.md` → `docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md` → `docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md` → branch-local `LATEST_HANDOFF.json` 순으로 확인한다. 새 인계에는 제품 정책 전체·정책 SHA256·연결된 이전 인계·제품/세션 Exact Next를 전달한다. 5회 연속 인계에서도 범위가 바뀌지 않는지 자동 검증한다.
- **승격:** Branch는 제안·검증·Merge handoff까지만 담당한다. MAIN이 공유 authority를 최종 승격한다. 사용자 명시적 정책 변경 없이는 현재 제품 목표를 수정하지 않는다.

본 문서에서 **권위**라는 표현은 코드·산출물의 병합 운영 권위를 뜻하며, 제품 범위를 과거 레이드 목표로 되돌리는 권한을 뜻하지 않는다.
