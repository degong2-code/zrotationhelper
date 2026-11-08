# zRotationHelper — General Rotation / Dummy Trainer current status (2026-11-09)

**Authoritative product policy:** `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1` · lock SHA256 `157daa151bc60b0d059aab4fbb8b0d7f5fb4a8e9e42811e401edffecfc1df295`. The final deliverable is a reusable specialization-neutral General Rotation opener + state-conditioned ST/2T/cleave/AoE priority research/validation engine and lightweight evidence-bounded target-dummy practice feedback. **No encounter/raid execution plans, NSRT, boss timelines or in-combat Hekili solver.** MAIN alone promotes canonical state; this branch is an implementation/validation candidate.

## Live HEAD observed BEFORE the 2026-11-09 handoff commits

- Repository `degong2-code/zrotationhelper`, branch `work/gr-simc-st-2t-wcl-blind-20261102` HEAD **`8964eca590390ee93427fc41523b12a0b7f120c8`**, MAIN **`4790f77f76a75f26ff0558d1d18c16cd9d630c4b`** (GitHub independent queries on 2026-11-09). **Requery both after the handoff commit**; never pass this pre-handoff HEAD as final.
- Branch current handoff before successor: `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json`, scope generation **3**, external schema `ZrotGeneralRotationEngineFirstHandoffV4`, old version field 4. Contains history through Nov 8 and must be archived unmodified before replacing with a compact generation **4** successor. MAIN global handoff stays unchanged.
- The previous `HANDOFF_STATUS_20261105.md`, 20261105 boot prompt and Gen4 portable ZIP are historical date-scoped evidence, not current state. Read this document and the new handoff first after scope/core rules.

## Independent evidence and claim boundaries

| Feature / source | Verified evidence | What it does NOT prove |
|---|---|---|
| Reused typed SimC APL parser, source graph and multi-spec loader | `simc_apl_semantic_ir_v2.py`, `general_rotation_source_hypothesis_ir_v1.py`, `general_rotation_simc_multi_spec_cold_start_v1.py`; Fury **121** / Arcane **51** source rows, 172 total | Not complete dynamic physical readiness or actual player rotation |
| New generic source→conditional opener E2E | [Actions #42195342553](https://github.com/degong2-code/zrotationhelper/actions/runs/42195342553): actual official pinned source + previous original C++ receipt; **262/262** source returns/root PRE linked in Fury/Arcane ST/2T, four cases; two Python synthetic jobs PASS | Original source-return is not a player cast. 10s opener **sample**, not opener end; no WCL verified optimality |
| Generic single new-class `.simc` source-only input | `general_rotation_simc_single_profile_v1.py`, verified on both actual pinned Fury/Arcane profiles by #42195342553 | Arbitrary **new** spec across all content patches is not validated; unpinned user-provided source is not official-current; no Native selection without evidence |
| Generic state-conditioned IF/ELSE *single-scan* evaluator | `general_rotation_simc_state_conditioned_evaluator_v1.py`, [Actions #42444206139](https://github.com/degong2-code/zrotationhelper/actions/runs/42444206139) success, 2026-11-08; Python 3.12/3.14 synthetic **15 checks/version** plus original source on Fury/Arcane gracefully `UNKNOWN` | Synthetic gate/control examples do **not** establish actual full READY or original native action selection parity; local variable lifetime/control execution unproven |
| Special-case source/READY evidence as regression fixture | Original Orb READY **158** roots / four TRUE source returns; Mage spec original C++ evaluated IF **73/73** AST matches (#42181561000); prior 2T Arcane Orb earlier candidates **8/10** independent local/IF exclusion proof (#42186794065) | Observed Native return does not prove global priority or actual player cast; Barrage prior IF independent truth **2 UNKNOWN** |
| Previous WCL discovery evidence | Prior discovery **54 casts** / disjoint holdout **51 casts**, Actions #41463589665, #41473060401 both completed/success | Not an independent locked/validated WCL-vs-General-Rotation result; no new WCL/API calls in this handoff |
| Retail addon policy / Hekili reference | Branch Hekili architecture and Retail addon API-policy docs | Actual current game-client API observability / full live dummy feedback **NOT TESTED**; no secret-value workaround |

**Actual last evaluated state-engine code commit:** `18ee1f4c475a0da6dbe23ea41c4777f94816ee37`, Actions #42444206139 complete/success, artifact `13603106491` (artifact ZIP SHA256 `1af8cec0847108765732410649739414e108b3d8a3cf6dabe9bd0a4d4c6f291e`, GitHub expiry Nov 15). The code artifact is a fail-closed proof, not a production gameplay rule. Branch evidence: `active/branches/BR-GR-ST2T-WCL-BLIND-20261102/evidence/GENERIC_SIMC_STATE_CONDITIONED_EVALUATOR_20261108.json`.

**Original official source pin:** `simulationcraft/simc@b522cded8c26b97dac03fdf56e57a03ec7e8faa6`; Fury profile Git blob `3225992ed5b754ad5d61e8b785d9d859f1eed1be`, Arcane `8d06eda4f69374dd1ed2e2d1eb8076b82cbbaf7f`. Original Native return receipt run #42155157024 reused. Artifacts may expire; code, pin and branch evidence receipts persist. Do not make historical artifact recovery a blocker to new isolated engine tests.

## Explicit gap classification

- **Evidence insufficient:** independently closed positive virtual-method READY for a selected Fury and Arcane physical action, preceding competing physical candidates, variable/execute event provenance, meaningful opener-end condition, multi-build & AoE thresholds, independent WCL candidate-lock/holdout, real Retail dummy input observability.
- **Engine/semantic implementation incomplete:** generic source-state SpecAdapter gate collection and complete inherited READY closure, faithful CALL/RUN scheduling and APL variable effects across scans, action replacement/proc/resource/pooling/execute, runnable state-conditioned priority that reproduces **actual** original Native chosen action without feeding the answer.
- **Product integration incomplete:** validated generalized General Rotation IR and confidence/reason/UNKNOWN for ST/2T/cleave/AoE/build, WCL+Blizzard post-lock reconciliation, dummy own-action comparison and actionable safe UI. **Full independent positive READY = 0; user mistake verdict remains UNKNOWN.**
- **External vs internal failure:** original C++/WCL source unavailability or addon policy limits differ from an engine bug. Prior failed instrumentation/regex probes are recorded separately; do not count them as rotation hypothesis failure.

## REUSE / EXTEND / REPLACE / UNKNOWN and roadmap

- **REUSE** existing source parser, source graph/typed AST, deterministic E2E 172/262 reference, Strict PRE validator, independent `GateContract`/Identity proof engine, synthetic 15-check state evaluator, Hekili modular architecture reference and available WCL blind cohorts.
- **EXTEND** generic external SpecAdapter + actual source gate state; integrate action selection, variable effects and CALL/RUN *across scans*; compare original Native outcomes with independent prediction (answer held out); add build and target-count scenarios as evidence arrives.
- **REPLACE only if justified** a blocking or duplicated adapter with simpler source-verified logic. Do **not** rewrite the historical FROZEN/raw evidence or introduce per-spec mechanics into Generic.
- **UNKNOWN** current client combat-state availability, some earlier Arcane Barrage branch operands, full readiness, realistic opener end, and final priority optimality.

**Short-term (critical path):** construct a generic source-pinned SpecAdapter/Gate provider that independently predicts one original chosen READY action and higher competing exclusions for **Fury + Arcane**; validate exact root PRE, effect/variable/CALL/RUN state and deterministic original Native replay without comparator leakage. New source collection is a test only if the necessary fields are missing; reuse existing fixtures.

**Medium-term:** multi-build ST/2T→cleave/AoE target breakpoints; independent WCL numeric/structural blind discovery → candidate/threshold lock → post-lock SimC replay + Blizzard mechanics and bounded holdout. Mark match/conflict/missing/UNKNOWN; avoid claiming optimality from repetition.

**Long-term:** authoritative General Rotation opener and IF/ELSE recommendation, evidence/confidence/reason/alternative/UNKNOWN; lightweight addon as permitted own-action recorder/UI, with post-session combat-log evaluator when live data is insufficient.

**Product Exact Next:** Finish **state-conditioned executable Generic General Rotation IF/ELSE** backed by independent positive READY, complete priority and opener transitions across specs/target contexts; WCL independent validation and policy-safe dummy feedback follow. **Session Exact Next after explicit new-chat '진행':** inspect and extend existing `general_rotation_simc_state_conditioned_evaluator_v1.py`, SpecAdapter and gate sources; close one actual original selected READY + preceding competitors each for Fury and Arcane, with source-verified variable/control effects. Reuse the existing 15-check/172-row/262-return fixtures and no unnecessary C++ builds.

**New-chat first-turn gate:** read-only restore and independently requery GitHub branch+MAIN/policy/evidence, report completed/incomplete/roadmap, then STOP. The current chat's historical `진행` approvals do not transfer.

## Handoff continuity gate — independently executed after successor creation

[Actions #42499559385](https://github.com/degong2-code/zrotationhelper/actions/runs/42499559385) **SUCCESS** (Python 3.12 + 3.14). The existing `tools/governance/validate_scope_continuity_v1.py --validate --self-test --handoff <branch-local latest>` was reused; both jobs verified: complete policy snapshot equality and pinned ID/lock SHA, **14 negative scope-drift cases rejected**, five successive simulated handoffs with valid parent links, old generation 3 → new generation 4, archive SHA256 **`acfe285053e6ee9b4662cef9a475a7b321a4e281c8c65f67539acde84d45816f`**, no user '진행' inheritance, MAIN/FROZEN untouched. This is an **actual governance CI PASS**, not a new SimC/WCL/gameplay engine test.

Archive: `_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/archive/LATEST_HANDOFF_SCOPEGEN3_BEFORE_20261109.json`, original Git blob `05a9c5d65a1120e82d052dc07c3f5bf6c844059b`. New compact handoff: branch-local `LATEST_HANDOFF.json`, schema V5, scope generation 4. Do not confuse simulated five future successors with five actual successive chats.

## 2026-11-09 승인 이후 Branch 개발 진행 — SpecAdapter claim ingestion

- **기능:** `general_rotation_simc_state_conditioned_evaluator_v1.py`에 JSON `--adapter-gates` 증명 입력과 `decode_adapter_gate_bundle`를 추가했다. 원본 APL 행 SHA/스킬/list/0-based index, profile Git blob, 시각 및 occurrence를 일치시키고, 기존 `Identity / GateContract / Fact`를 그대로 사용한다.
- **실제 영수증:** [Actions #42501155498](https://github.com/degong2-code/zrotationhelper/actions/runs/42501155498) completed/success, Python3.12 및 3.14 합성(각 30로 표시된 검사), 기존 공식 Fury/Arcane pinned-profile 소스 fail-closed 실증, 3/3 jobs SUCCESS. 최종 코드 SHA256 `dd20ce39744c04776fc9009420cc92ddbb1272d697f01a1eadbe6f2e46354705`.
- **입력 검증:** 행·SHA·시각·occurrence·중복 후보/게이트 및 WCL same-timestamp 거부, Native post-comparator는 READY 불가, 미완성 route는 UNKNOWN. JSON 서명/원본 사실의 진위를 단독 인증하지 않으므로 출력에 `external_gate_bundle_provenance_authenticity_verified_here=false`를 명시한다.
- **제품 한계:** 본 변경은 외부 SpecAdapter 증명 자료를 범용 엔진에서 다룰 수 있게 한 것이다. 실제 Original Fury/Arcane 물리 READY 완전 독립 증명은 **여전히 0**, 원본 C++ 선택 parity/실제 WCL 모델 검증/허수아비 판정은 **NOT_RUN / NOT_READY**. 합성으로 closure를 주장한 예제는 실제 게임 검증이 아니다.
- **다음 critical path:** 기존 source-PRE producer·virtual method 경로를 실제 동작 데이터에서 독립 검증해 이 입력 계약에 연결한다. 원본 선택 결과는 comparator로만 사용한다. 이어 Fury+Arcane의 실제 양성 READY와 앞선 후보 배제 판정, 효과/변수 및 CALL/RUN 전이 parity를 마무리한다.
- **범위:** Branch-only, 공식 scope/gen4 유지, MAIN/FROZEN 불변, Seq578=FAILED_QUARANTINED, Seq637=UNKNOWN.
