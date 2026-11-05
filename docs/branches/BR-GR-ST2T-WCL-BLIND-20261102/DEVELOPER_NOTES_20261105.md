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

## 2026-11-05 follow-on — original PRE sync/line eligibility
- Branch code commit `71d0b1b66476e62109001612178fed2f05ac7a8f` proves the narrow source-conjoined `SYNC_LINE` gate from already acquired original `line_cooldown.ready_ms` and null sync pointer before Native `action_ready()`, with exact scope/entry matching, fail-closed duplicate and row mismatches.
- Real portable source CI #41946685338 PASS (JSON SHA256 `50cf08813a5056acd0490e734675a0bf7115688905b9e653c8b24270a276c8cb`) and real Native regression #41946685439 PASS. `rampage` at 20,031ms, 6 prior negatives, missing 5 gates, full READY 0. Initial #41946570894/#41946570928 FAILED on synthetic mutable pending fixture; correction not a Native model mismatch.
- Reuse existing `simc_native_postguard_source_replay_v1.py`, do not rewrite guard parser. Next `MOVEMENT`/cast/GCD and subclass override source truth to be independently replayed, then signed exhaustive closure; stay engine-first and do not conflate source positive with real user-cast priority.

## 2026-11-05 후속 진행: Original physical PRE 하위 조건 / 독립 상태
- 코드 `ef391b398d21db032e5b72063842adde003f3d0c`에서 실제 source `post_line`+`post_cast`를 exact action pointer에 묶고 기존 독립 postguard subset evaluator를 재사용. Selected Fury `rampage` at 20,031ms: 원본 PRE의 stationary branch bypass, 이동 옵션 비교, repeat-cast guard 모두 True. 하지만 GATES의 전체 MOVEMENT·CAST_GCD는 UNKNOWN, remaining blockers 5 및 full READY 0 유지.
- Actions #41948011588 (source real portable + Python 3.12/3.14) SUCCESS; output SHA256 `2d29ef250344d27e88453dacdfb6f29319753e39130306d81805a9d8404a3777`, artifact #13380330094; #41948011638 Native PASS. First #41947894977 synthetic missing movement input KeyError FAIL, corrected to None UNKNOWN. Do not conflate with source hypothesis failure.
- Original source lookup pinned `action.cpp` Git blob `399ecd9453b3f30bfc2ebf2b3ffd8f56cce8f8d4`, `sc_warrior.cpp` Git blob `38ee3dd0d5943eb9227ec55aefb21e7d47244f96`. Source partial type gates do not close full virtual route. Next use narrowly scoped original PRE capture of movement directionality and GCD/execution fields, then source-proof and closure reviewers; do not spend WCL points for SimC source limitations.

## 2026-11-05 — General Rotation 범용 엔진 경로 계측 프리플라이트
- **현재 브랜치 코드 기준** `ac002437df656eac8fbfa24f8ab0c0e206a06345`, MAIN/global pointer/inherited frozen unaffected. New generic `MethodSite`/`RoutePlan` source audit with independent official file blobs, C++ method bodies, scoped guards and graph checks; adapter-specific manifests isolated from engine.
- Two distinct source fixtures: Fury Rampage 6 verified methods; Arcane Blast 4 verified methods; **not** Arcane Native simulation. Actual Fury source evidence worklist from 20,031 ms: 5 UNKNOWN gates → pinned source methods (2/4/2/3) or no declared coverage for `BASE_VIRTUAL_COMPLETE`. Proven static site ≠ source guard exhaustive ≠ actual physical READY.
- CI #41951187215 SUCCESS; new route worklist artifact SHA256 `66511eaa61a441fae61f1c42db3f94eba1a936cc8138ad691b2bfaa96140fec6`, artifact 13380797965. Reuses Fury 5,408 attempts and IR 953 source IF, previous JSON `2d29ef250344d27e88453dacdfb6f29319753e39130306d81805a9d8404a3777`. Prior synthetic casing failures #41950958149/#41951060324 preserved as FAIL, successor corrected.
- **Next exact development**: source-pinned worklist → generic Original-PRE typed raw operand capture/request schema → minimal spec Semantic Adapter → actual E2E source snapshot/replay/independent validator. Do not let narrow Fury polishing become Generic Engine's development goal. `closed=True` forbidden until exhaustive reviewed dispatch graph and all independent guards. WCL blind path stays independent until candidate lock; trainer remains UNKNOWN without WoW Retail real observability.

## 2026-11-05 original PRE capture engine implementation — branch-only
- Source-worklist reuse now yields executable *collection contract*, not fabricated state: `compile_template`, `bind_worklist`, `validate_pre_records` in `general_rotation_original_pre_capture_engine_v1.py`. Per-spec field declarations isolated to `general_rotation_original_pre_capture_fixture_v1.py`, not in generic evaluator. Source origin pin (Git blob/body/guard hashes) + exact row/time/typed value / duplicate rejection, deterministic template/bound hash.
- Actual Fury 20.031s Rampage preflight has 12 bounded requests, no NEW raw records, one unresolved `BASE_VIRTUAL_COMPLETE` gate; Arcane source fixture 8 planned fields, NOT real Native. Previous original PRE derived subguards reused as provenance/context only, not newly collected.
- CI #41952335859 PASS, Py3.12/Py3.14 synthetic plus official two-spec source and actual Fury Native 5,408 attempts. New JSON `c14457a0e6a4d56c49740aae11af13518416f534f7db6278ddd82557ae464e68`, 7-day artifact 13381402273. Generality: one engine, two spec inputs.
- NEXT: implement shared passive Native original PRE capture producer, source patch purity checks, original/modified SimC output nonperturbation validation; then real source capture consumed by typed validator, independent guard semantics and dispatch closure, actual Arcane cold start. Do not claim production data or dummy error READY until demonstrated.

## 2026-11-05 generic Native passive producer — verified execution
- `general_rotation_select_pre_passive_producer_v1.py` C++ patch on one exact pristine player.cpp select_action before-call anchored site, source-pinned original action ready invoked exactly once; immutable recognized generic actor/action fields, no spec-specific classification. The spec-specific template provider `general_rotation_select_pre_source_adapter_v1.py` constructs audited source typed templates and passes JSON externally; producer does not import spec fixture.
- `general_rotation_select_pre_passive_replay_v1.py` validates typed actual raw log records, APL list+signature ordinal+source-row SHA, source time and occurrence; doesn't promote source selection PRE as virtual method-entry PRE; doesn't claim READY.
- Final actual pristine and modified C++ run #41954389294 SUCCESS. Fury 1542 attempt groups, Arcane 1106 attempt groups; actor GCD ready time, usable while casting and moving state captured in common producer. Exact performed sequence and APL provenance parity with original for both 30-second ST sessions, seed 31459. Compact result hash `0076d7adf85d96e844a7b56218fdf44ae199661147a64cfe4a98c812b5a3e630`; artifact `13382537813`. First combined-fixture #41953846399 also passed but was refined due to cross-class dependency.
- **Next**: generic method-site original PRE producer with original operands at route entry, per-SpecAdapter guarded source method definitions, build A/B parity, provenance and replay. General goal remains opener + post-opener conditional priority + dummy trainer, not isolated ST field counts. No actual full READY yet.

## 2026-11-05 Original METHOD-ENTRY PRE generic producer successor
- `general_rotation_method_pre_passive_producer_v1.py` (spec-neutral) accepts external `method_entry_sites` from source-pinned `ZrotGenericPassiveSelectTemplateManifestV1`, validates C++ method-body and site blob prior to insertion; currently exposes 2 standard action_t virtual method entry sites (one `action_ready` marker and one `ready` marker + 2 raw fields). No extra original decision-function invocations.
- `general_rotation_method_pre_passive_replay_v1.py` checks actual method entry+field groups against original profile list/ordinal/time and method-body SHA; output phase `SIMC_ORIGINAL_METHOD_PRE`. It doesn't assert exact dynamic SELECT attempt pairing or closed subclass routes.
- Actual pinned official CXX A/B CI #41956159253 PASS: Fury SELECT 1542 / common action_ready 1201 / common ready 985, Arcane SELECT 1106 / common action_ready 781 / common ready 678, both original vs patched performed-action sequence exact. Receipt SHA256 `6de67fed16d616a2ccbab0b371ded6f0f32c4535d9cc57e02abe12b97773b53e`, artifact 13383002915 expires 2026-11-12T02:36:16Z. No WCL points and no raw logs committed.
- Previous failed #41955868482/#41955963801/#41956052806 pipeline selftest/exception/grouping errors now corrected, not overwritten. **Next** generic C++ class-owned method entry adapters then strict source-dispatch/guard closure and independent READY, original model priority, WCL comparison and dummy evaluator, not a Fury one-off.
