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
