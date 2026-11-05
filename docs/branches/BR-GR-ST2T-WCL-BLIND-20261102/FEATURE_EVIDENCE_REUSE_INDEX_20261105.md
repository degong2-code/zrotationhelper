# zRotationHelper — Feature Evidence Reuse Index (2026-11-05)
이 파일은 20261104 장문 인덱스를 대체하는 **최신 길잡이**다. 구 인덱스·원본·FROZEN을 삭제/수정하지 않는다.

| 기능·소유 코드 | 검증된 최근 증거 | REUSE / 미검증 지점 |
| --- | --- | --- |
| SimC APL parser `tools/research/simc_apl_semantic_ir_v2.py` | Fury/Mage source Cold Start #41796659187, #41799789205 SUCCESS | 기존 typed AST/variable 문법 재사용. Native readiness는 별도 |
| Source General Rotation IR `general_rotation_source_hypothesis_ir_v1.py` | #41799789205; 172행, Fury 121 Mage Arcane 51; original JSON SHA `7b32ae86ad20120360790020055c2bf1f761bddd7cdeed41a2d9e0d1e0020b5b` | source-only 오프닝/priority 가설. 실행 시전 순서 아님 |
| 범용 IF/ELSE 해석 `simc_apl_semantic_ir_v2.py:bounded_decision` + `general_rotation_ir_proof_replay_v1.py` | #41935516360 SUCCESS, 172행 정확한 source graph & AST, no input → 172 UNKNOWN | 새 evaluator 만들지 말 것; 완전 gate positive producer 필요 |
| Tri-state source READY `general_rotation_decision_proof_engine_v1.py`, `simc_native_decision_proof_bridge_v1.py` | #41794691821 SUCCESS, 5408 attempts: 2313 source-proven NOT_READY, 3095 UNKNOWN, READY 0 | 관측된 Native ready를 입력으로 사용 금지; full route closure gap |
| 직업별 선택적 의미론 `simc_native_warrior_priority_frontier_adapter_v1.py` | #41791958183 SUCCESS, Warrior 거리/채널링 1003 필요한 부정 증거 | 특정 직업은 SpecAdapter, Generic engine은 중립 |
| Original-call Native PRE source instrumentation + `general_rotation_native_pre_trace_compactor_v1.py` | #41797208028 SUCCESS, 8,432,350→470,328B, 4 source cohorts parity | 원시 시전·damage 출력이 아닌 source markers. 재생 fixture 7일 만료 |
| Native IF+source IR 연결 `general_rotation_native_ir_pre_evidence_join_v1.py` SHA `cbc179f61c6726ec7cb46aa4c0b04698cc504f3c6da3249dd4266573b6d3cdf5` | #41938527598 SUCCESS, 953 source IF: 657 proven false, 282 true, 14 UNKNOWN; artifact 13374384181 JSON SHA `ac18255a0570e53968d97007f75a3d16333d64df1d66036c656b7d52070ae93c` | IF 상태만, actual skill READY=UNKNOWN, WCL API 0 |
| WCL event Strict PRE `general_rotation_strict_pre_state_engine_v1.py` | #41796021165 Py3.12/3.14 합성 PASS; same-time/future/expired ambiguous → UNKNOWN | 실재 WCL producer + lock/holdout 독립 검증 미완 |
| 이전 실제 WCL 원자료/holdout | #41463589665(54 casts discovery) / #41473060401(51 holdout) SUCCESS | 수집 증거는 있음. **최신 General Rotation 모델 검증과 연결은 없음** |
| 허수아비 프로브/평가 | 이전 offline mock | 실제 Retail client capability/완결된 rotation 모델 연결 미완 |

**영수증 우선순위:** #41938527598 최신 actual source-IR IF join → #41935516360 Fury/Mage IR decision fail-closed → #41797208028 source fixture → #41794691821 tri-state negative/prefix. 과거 477건 #41584822737는 별도 cohort: 66/477, UNKNOWN 411. 새 953건과 분모를 누적하지 않는다. CI FAIL #41938411129(40자 Git blob vs 64자 SHA contract), #41935436081(0건 counter assertion) 보존; 해당 successor PASS와 구분.

**적용 경계:** source parsing≠Native cast parity≠full READY≠WCL optimality≠target dummy feedback. 각 주장에 맞는 actual production evidence 필요. 생성 영수증은 기간 제한이므로 재생산 경로와 SHA를 기록. 새로운 기능 전 `INDEX→실제 코드→원본→Actions 로그/아티팩트`를 읽고 REUSE/EXTEND/REPLACE/UNKNOWN 결정.

### 2026-11-05 actual source-selected positive-gap successor
- 코드: `simc_native_decision_proof_bridge_v1.py` → `simc_native_if_false_priority_frontier_v1.py` → `general_rotation_native_ir_pre_evidence_join_v1.py`.
- #41945383199 actual source fixture PASS; **79** source-pinned selected executable candidates with all earlier attempted candidates independently excluded, details output; generic actual READY remains 0. Bridge reuses `simc_native_resource_cost_replay_v1.py` original method cost/source player-resource numeric proof only for scoped positive `RESOURCE` gate, no user READY or mistake promotion.
- Closest selected fixture: Fury `rampage` moving ST at 20,031ms, 6 earlier independent negatives; source row `217c49dcce32cbc0d975679ed09e0a79c71f05e2615e6566f46bffc9b1ffece2`; missing gates 7→6, still `UNKNOWN`. Actual JSON SHA256 `995ee68d1aeb9da02b078bb9c16039a0a7e943325cd549800577fea626195c6c`, artifact 13378442205.
- CI history: failed #41944807494/#41944807502 (producer schema/synthetic test defects), corrected pass #41944965565/#41944965873, resource successor pass #41945383199. Index is branch-scoped only; do not claim new engine-wide completion.

### 2026-11-05 source-original sync/line positive partial successor
- `simc_native_decision_proof_bridge_v1.py` reuses original preselection line cooldown/sync pointer from `simc_native_postguard_source_replay_v1.py` and pinned native official source. Only a present ready line cooldown and absent sync pointer make `SYNC_LINE=True`; missing/out-of-scope/nested sync readiness remains UNKNOWN. No Native ready as operand.
- [Source replay #41946685338](https://github.com/degong2-code/zrotationhelper/actions/runs/41946685338) PASS: 5,408 attempts, 953 source IF / 939 decidable, selected-prefix 79, full READY 0. JSON SHA256 `50cf08813a5056acd0490e734675a0bf7115688905b9e653c8b24270a276c8cb` and artifact `13379061462`.
- [Native regression #41946685439](https://github.com/degong2-code/zrotationhelper/actions/runs/41946685439) PASS. Selected Fury `rampage` moving ST at 20,031ms, six earlier independently NOT_READY, missing positive gates **5** (previous 6): BASE_VIRTUAL_COMPLETE/CAST_GCD/MOVEMENT/NECESSARY_ELIGIBILITY/SPEC_OVERRIDE_TOTAL. All user READY/optimality/dummy verdicts still UNKNOWN.
- First trial #41946570894/#41946570928 FAILED because synthetic test reused one mutable pending record; corrected commit `71d0b1b` passes. Preserve provenance and actual reason.

### 2026-11-05 physical-postguard partial source truth reuse
- `simc_native_postguard_source_replay_v1.py`의 기존 Original PRE `parse_line/parse_cast/independent_postguard_subset`을 `simc_native_decision_proof_bridge_v1.py`로 재사용; action row/time 및 중복 마커 계약 검증. 실제 Fury rampage moving ST 20,031ms: base ready moving guard bypass + source moving option pass + repeat-cast guard pass. **원본 동적 movement_directionality/GCD 경로 UNKNOWN**, 이전 READY missing 5개 그대로, full READY 0.
- Real portable source run [#41948011588](https://github.com/degong2-code/zrotationhelper/actions/runs/41948011588) PASS; SHA256 `2d29ef250344d27e88453dacdfb6f29319753e39130306d81805a9d8404a3777`, artifact 13380330094 (2026-11-12T01:22:21Z expires). Native regression [#41948011638](https://github.com/degong2-code/zrotationhelper/actions/runs/41948011638) PASS. Initial #41947894977 FAIL on synthetic omitted movement fact, corrected as UNKNOWN, preserve failure.
- Next targeted source obligations: pinned action.cpp has `has_movement_directionality()` virtual guard (line 2607), cast-while-casting GCD block (2659–2673); warrior chain has `usable_moving` static true but not proof of actual dynamic directionality, weapon/override. Do not use a static default or native selection as closure certificate.

### 2026-11-05 Engine-first generic C++ method route + evidence worklist
- REUSE/EXTEND: `general_rotation_source_route_audit_v1.py` implements source SHA1 git blob / method scoped fragments / source guard site / acyclic reachable graph validation for arbitrary `MethodSite` and `RoutePlan`. `missing_source_obligation_worklist` joins source-pinned method candidates to exact native UNKNOWN gate list, without setting READY. Independent of Fury/Arcane engine semantics.
- Spec-specific source fixture only in `general_rotation_source_route_fixture_v1.py`: Warrior Fury Rampage 6 methods, Mage Arcane Blast 4 methods; checked against pinned official SimC source via [Actions #41951187215](https://github.com/degong2-code/zrotationhelper/actions/runs/41951187215) SUCCESS. Py3.12/Py3.14 selftest + actual upstream source and existing Fury 5,408/953 replay PASS.
- Worklist Fury 20.031s: `BASE_VIRTUAL_COMPLETE` 0 relevant declared method hints; `CAST_GCD` 2; `MOVEMENT` 4; `NECESSARY_ELIGIBILITY` 2; `SPEC_OVERRIDE_TOTAL` 3. These counts are just declared source candidates; dynamic dispatch closure UNKNOWN. New cross-spec JSON SHA256 `66511eaa61a441fae61f1c42db3f94eba1a936cc8138ad691b2bfaa96140fec6`; artifact 13380797965 expires 2026-11-12T01:50:40Z.
- Worklist first attempts #41950958149 and #41951060324 synthetic uppercase gate fixture FAIL; successor #41951187215 PASS. No WCL calls/MAIN/FROZEN promotion, no Arcane Native E2E yet, 0 real READY. Next create reusable raw-PRE producer/SpecAdapter state requests, not another Fury-specific patch or just extra CI check.
