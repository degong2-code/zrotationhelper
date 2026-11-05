# zRotationHelper — Developer Notes / Branch Local (2026-11-05)

## 엔진 우선·유효 권위
공식 범위: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`, 전체 scope snapshot은 branch-local `LATEST_HANDOFF.json`와 불변 `docs/PRODUCT_SCOPE_LOCK_V1.json`에 포함. 사용자 승인 없는 Encounter/NSRT 목표 복원 금지. MAIN만 공유 pointer/contract/registry/FROZEN 승격. 연구 브랜치에는 승인된 격리 구현·검증·인계만.

## 새 채팅 읽기 순서와 멈춤
Scope Lock → Scope prose → AGENTS → Engine-first Charter → Handoff Continuity Protocol → branch LATEST_HANDOFF(gen3) → `HANDOFF_STATUS_20261105.md` → `FEATURE_EVIDENCE_REUSE_INDEX_20261105.md` → 이 notes → 최근 code/actual CI. 먼저 GitHub HEAD·policy SHA·previous parent SHA를 독립 검증. **첫 응답 READ-ONLY 복원 보고 후 STOP**. 새 '진행' 전에 코드/문서 변경, 실행, 수집, CI dispatch, commit/PR/승격 금지.

## 기존 함수·영수증 재사용 우선
1. `simc_apl_semantic_ir_v2.py`: source pin, typed AST, `bounded_decision` source IF/ELSE/CALL/RUN/variable.
2. `general_rotation_source_hypothesis_ir_v1.py`: 2개 실제 전문화의 172 APL row and opener hypothesis.
3. `general_rotation_ir_proof_replay_v1.py`: source row/occurrence timestamp binding, no evidence = UNKNOWN.
4. `general_rotation_decision_proof_engine_v1.py` and `simc_native_decision_proof_bridge_v1.py`: NOT_READY/READY/UNKNOWN, positive closed route, no Native comparator used as operand.
5. `simc_native_if_false_priority_frontier_v1.py`, `simc_native_warrior_priority_frontier_adapter_v1.py`: previously proved necessary-negative guards and scoped Warrior semantics.
6. `general_rotation_native_pre_trace_compactor_v1.py` & `general_rotation_native_ir_pre_evidence_join_v1.py`: portable source markers and IR PRE IF evidence from the same source without C++ rebuild; 5,408 attempts/953 IF, independent 939/953 IF post-comparison.
7. `general_rotation_strict_pre_state_engine_v1.py`: WCL historical transition strict < action time; synthetic only, not live WCL producer.

## 후속 구현의 완료 계약 (다음 세션 진행 승인 이후)
- Exact source/actor/time/row binding and independent original PRE facts; avoid time == t and future leakage.
- Physical skill's **complete** virtual method route, replacement, all-gate readiness, target, charges, proc/buff, resource/GCD must be exhaustively audited. Reviewer/SpecAdapter closure certificate from official pinned source; no arbitrary manual `closed=true` on observation.
- With independently proven prior NOT_READY and winner READY, generic candidate ordering can produce evidence-bounded source selection. Control commands/side effects not user spell.
- For different specialization repeat cold-start actual Native E2E. SimC-first source initial model, but WCL independent blind lock before semantic injection.
- New 953 IF observation is not independent full ready proof; 657 IF-false includes control/overlap. Do not add to 2,313 NOT_READY.
- SimC movement scenarios are research fixtures, not future WoW movement prediction or protected API bypass.
- Unobserved game state => UNKNOWN; do not call it dummy error. No in-game feedback claim without a Retail client observation matrix.
- Prefer bundled independent tasks, small focused regression and proven existing receipts over full Native recompile, WCL recollection or historical reconstruction. IF hypothesis failure ≠ pipeline failure.

## Exact next
After a fresh approval, read source-mapped `ready()` paths for selected executable actions and create a specialization-neutral gate-completeness registry / SpecAdapter extension, using the existing 79/174 partial-prefix cases and compact fixture, then cross-class actual Native and post-lock WCL as justified. Keep Product Exact Next General Rotation opener & conditional priority engine, then truthful dummy feedback.

## 2026-11-05 진행 중 개발 결과 (gen3 인계 이후, branch-only)
- 브랜치 실제 코드 HEAD `86849c9e6b5e117f3099cdfaeb623ad01119fb84` 확인. 이 개발은 handoff gen3의 원래 인계 스냅샷 이후 successor이며 gen3 또는 MAIN/FROZEN을 소급 변경하지 않는다.
- Source-pinned selected READY-gap preflight는 79건을 원본 SimC 시각/리스트/행 SHA로 식별해 최소 공백 사례를 고른다. 기존 `RESOURCE` 독립 원시 비용 비교 재사용으로 Fury `rampage` at 20,031ms, 6 prior NOT_READY의 미확인 gate가 7→6이 되었다.
- Actual 4-case fixture CI #41945383199 SUCCESS; 5,408 attempts, READY 0, IF 판정 939/953; JSON SHA256 `995ee68d1aeb9da02b078bb9c16039a0a7e943325cd549800577fea626195c6c`. First implementation CI FAIL #41944807494/#41944807502 is retained, fixed successor PASS #41944965565/#41944965873.
- Next: `BASE_VIRTUAL_COMPLETE`, `CAST_GCD`, `MOVEMENT`, `NECESSARY_ELIGIBILITY`, `SPEC_OVERRIDE_TOTAL`, `SYNC_LINE` on actual selected `rampage` 20,031ms; source-audited complete route proof without Native ready bit as input. Cannot claim full READY before that, or source-order completeness, WCL optimum, target dummy errors. Keep first-response-only read-only rule for **new** chats; the user has authorized this session with “진행”.
