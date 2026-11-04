# Feature and evidence reuse index — 2026-11-04
**Authority:** branch-local reuse guide only. Scope policy ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1. This is not a MAIN/FROZEN or completed-product index.

**Official SimC source pin:** simulationcraft/simc commit b522cded8c26b97dac03fdf56e57a03ec7e8faa6; Fury profile Git blob 3225992ed5b754ad5d61e8b785d9d859f1eed1be; Enhancement profile Git blob 2f2c951ae07489d124db36c464ab66d1efd262ce. Before changing a parser/provider, inspect this index AND the source path and receipt first.

| Capability / role | Reusable source and receipt | Proven / not proven |
|---|---|---|
| Policy and handoff continuity | docs/PRODUCT_SCOPE_LOCK_V1.json; tools/governance/validate_scope_continuity_v1.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41423414896 | Scope + five SIMULATED hops PASS; new actual handoff must be verified separately. |
| Legacy reusable SimC parser/control | tools/research/simc_apl_source_engine.py; simc_apl_condition_research.py; simc_apl_variable_runtime.py; simc_apl_priority_trace.py; simc_apl_precombat_replay.py | Existing source routines are assets, NOT automatically native-equivalent; inspect rather than rewrite. |
| Exact APL AST/source compiler v2 | tools/research/simc_apl_semantic_ir_v2.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41563832907 | Fury 121/121 and Enhancement 114/114 source lines parsed; second specialization source-syntax pilot only. |
| Effective Native action-list parity | tools/research/simc_native_reference_capture.py; simc_native_effective_apl_crosscheck_v1.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41563013349 | Fury native effective APL 121/121 source-equal; not selected-action state parity. |
| General Rotation source hypothesis | tools/research/simc_general_rotation_source_model_v1.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41565944271 | Slayer/Thane ST versus >1 target routing and all 121 source rows retained; hypothesis, not validated playable priority. |
| CALL/RUN control correction | tools/research/simc_apl_semantic_ir_v2.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41565030261 | RUN is queued control and next-scan active-list switch, not same-scan CALL recursion. Retest any old incorrect model outputs. |
| Native selected-source-row oracle | tools/research/simc_native_select_trace_instrument_v1.py; simc_native_select_trace_audit_v1.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41565722906 | ST/2T actual source rows identified with pointer proof; pristine-versus-instrumented native sequences match. |
| Ordered selection structural replay | tools/research/simc_native_foreground_structural_replay_v1.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41580466416 | 214 foreground scans, 190 selected actions, structural replay conditional on 2,572 **Native-supplied ready()** results; NOT independent readiness parity. |
| Native IF evaluation coverage | tools/research/simc_native_if_expression_instrument_v1.py; simc_native_if_condition_coverage_v1.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41582637785 | 477 actual IF evaluated (142 true, 335 false); 2,095 checks did not show an IF evaluation, **not** known false conditions. |
| Exact PRE resource/enemy operand | tools/research/simc_native_if_pre_operand_instrument_v1.py; simc_native_if_pre_operand_replay_v1.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41584822737 | Real Native source-pointer PRE facts, 477 IF evaluations; 3 fully-known numeric AST + 63 decisive partial AST = 66/477 correct comparisons; 411 UNKNOWN. Receipt SHA256 ebf8a902bff1c1167306217535ac5fc10466bc3a1d4512adc175a2449e7fbd13. |
| Cheap real-fixture replay without Native build | tools/research/simc_native_if_ledger_offline_replay_v1.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41585210821 | All 477 ledger rows rechecked using SAME Python AST, reproducing 66 matches/411 unknown; NOT independent second implementation. Offline receipt SHA256 aacc90fa495c78b90d69251fa0fae7265c1a2ad60d17dafd021d890dbd641855. |
| Older source state and mechanics producers | tools/research/simc_apl_readiness_provider.py; simc_native_apl_eval_scope_instrument.py; simc_native_bare_resource_eval_instrument.py; simc_native_resource_lifecycle_instrument.py; docs/DEVELOPER_NOTE_PINNED_NATIVE_APL_EVAL_OWNER_20261031.md; docs/DEVELOPER_NOTE_SIMC_APL_NATIVE_RESOURCE_SEMANTIC_GAPS_20261030.md | **Source code / focused prior evidence exists**; check semantic compatibility before building another provider or replay. Historical source gates are not automatically latest user-facing rotation. |
| WCL discovery and separate report holdout | tools/research/wcl_simc_postlock_real_audit_v1.py; wcl_dual_cohort_state_observability_v1.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41463589665 and https://github.com/degong2-code/zrotationhelper/actions/runs/41473060401 | **Actual WCL collected**, 54 discovery + 51 holdout casts from distinct reports; source-limited PRE and blind candidate receipts exist. Historical 2026-11-02 handoff text saying WCL was NOT_COLLECTED is stale. Different report does not prove different player or actual priority. |
| WCL identity/mechanics mapping | tools/research/wcl_simc_build_alignment_v1.py; wcl_actor_resource_owner_strict_pre_v1.py; wcl_source_action_family_readiness_v1.py; https://github.com/degong2-code/zrotationhelper/actions/runs/41475935231 | Some build/auras/actor-owned resource reconstructed; exact alternative readiness/active enemies and complete build equivalence UNKNOWN. |
| Dummy practice research prototype | addons/research/ZRotDummyProbe; https://github.com/degong2-code/zrotationhelper/actions/runs/41560976098 | Offline Lua/mock tests only; actual WoW API in-game not tested. **PAUSED** under user SimC-first priority; not a finished dummy trainer. |

## Native artefact / cost reuse
- Native PRE operand source receipt: run 41584822737 artifact 13207192856, 7-day expiry around 2026-11-10 UTC. The full 477-IF derived receipt may be downloaded using its exact run and SHA, but never assume indefinite preservation.
- Cheap offline replay receipt: run 41585210821 artifact 13207547286, 7-day expiry around 2026-11-10 UTC. Re-run the existing offline workflow while still available rather than recompiling Native SimC for an unchanged operand set.
- Historical CI failures (#41584302584 and others) remain FAIL, not erased by later PASS. Preserve job dates, commit SHA and artifacts when reusing.
- If the transient artifact expires, identify the missing input and regenerate it only if the next validation genuinely needs it; never make old evidence restoration the engineering bottleneck.

## No redundant work / scientific boundary
1. Check this index, the exact source and currently pinned receipts before starting each task; classify REUSE / EXTEND / REPLACE / UNKNOWN.
2. Source AST PASS ≠ effective APL PASS ≠ structural selection PASS ≠ independently evaluated operand PASS ≠ full native behavior parity ≠ WCL gameplay priority.
3. Native truth bits are held out of AST inputs; they are a comparison target only. Same implementation in a second workflow is regression reuse, not an independent second semantic implementation.
4. Strict PRE requires transition timestamp < action time. Do not use same-time/future state. Absent alternate cooldown/charge/readiness remains UNKNOWN.
5. Do not add Fury/Slayer meaning to the generic engine. Put specialization specifics in adapters; validate generality with another executed spec/build after Fury vertical semantics.
6. MAIN alone may elevate shared state. Seq578=FAILED_QUARANTINED; Seq637=UNKNOWN; FROZEN unchanged.

## Source-clock successor reuse — 2026-11-04

| Capability / role | Reusable source and receipt | Scope |
| --- | --- | --- |
| Native PRE-IF time operand using immutable 477-row ledger | tools/research/simc_native_if_source_clock_successor_v1.py; [Actions #41753660425](https://github.com/degong2-code/zrotationhelper/actions/runs/41753660425); receipt SHA256 310eb9f369e537eac5916ebbcb23ea34bc6de558ca34f43b3e359bc76c57d85d | Source-pinned official event_mgr.current_time clock; old 66 matched + 2 new = 68/477, remaining 409 UNKNOWN. No Native/WCL run, no readiness or complete action-choice parity. |

Source file SHA256 41e23ede7e0aa5fb7c3ef5b56f5472ca3a7aff96967b0e95cefb2c2860967abd. New artifact 13286884187 expires 2026-11-11T01:23:24Z. This is a successor, NOT a rewrite of the original 66/477 frozen-corpus result. The largest observed unresolved symbol is talent.slayers_dominance (103 overlapping appearances); next work should produce source-accounted passive talent state with a generic APL-symbol inventory instead of hardcoding Fury interpretation or expanding WCL/addon.

## Native talent PRE evidence reuse (2026-11-04)

| Capability | Code and exact receipt | Scientific status |
| --- | --- | --- |
| Generic APL-IF talent actor fact producer | tools/research/simc_native_if_talent_pre_instrument_v1.py; SHA256 535fbae496684ca57bc75fe1316dfd82b173adc6cc3b5324ed90ca99ae02d4e9 | Five symbols extracted from official IF fields, not all seven profile-wide symbols. Original single IF evaluation and pre-existing Rage/enemies facts preserved. |
| Native pre-state independent source AST verifier | tools/research/simc_native_if_talent_pre_replay_v1.py; SHA256 ed7328bef214196257a915e895dea7005e51b7a638475a6cf03d627b7da61125; [Actions #41757998253](https://github.com/degong2-code/zrotationhelper/actions/runs/41757998253) | Real ST/2T source-identified 477 IFs; source-clock 68 + 142 independently decisive talent cases = 210 matches, 267 UNKNOWN. Original and patched actions exactly equal. No complete action_ready/choice parity. |

Derived receipt SHA256 8fd2df01ebdba7096a3c9c10c9718e168205005f064edbbc4647b8e1f28f6948. Artifact ID 13288848180 expires 2026-11-11T02:03:07Z. Intermediate actions #41757715589 and #41757774893 are failed tests with superseded syntactic/spec-scope assertions, NOT PASS. Older 66/477 and 68/477 receipts remain historically intact. The next operand should come from current UNKNOWN symbol incidence and official Native source, not a hardcoded Fury priority.

## Actual Native buff PRE successor reuse (2026-11-04)

| Capability | Exact reusable implementation + evidence | Boundary |
| --- | --- | --- |
| Generic source-derived buff value producer | tools/research/simc_native_if_buff_pre_instrument_v1.py; SHA256 697597c23b1d78a11abe46b418b870eaa46b8cd40c81e011d6d679609797e0c5 | Auto-inventory of 13 buff.* up/down/stack/remains IF symbols from official APL; exact official SimC buff.cpp/player.cpp Git blob pin; reads actor Native PRE IF facts before original single if_expr evaluation. |
| Existing AST with buff extension | tools/research/simc_native_if_buff_pre_replay_v1.py; SHA256 7165c5fc28517b4e7759583434bae9f3da2ffc09fe2a5b9d1a294a704c971092; [Actions #41761805054](https://github.com/degong2-code/zrotationhelper/actions/runs/41761805054) | 477 actual Native Fury IF events (ST 131/255, 2T 142/222), 273 independent matches / 204 UNKNOWN. Prior talent-only 210 reproduced and +63 new sound cases. Original-vs-reporter exact actions unchanged. Not a full ready() or action choice oracle. |

Receipt SHA256 1be31f4c758079d2c19b63a7bac4a1cc619c63cd59f7454da42431911583ff72. Artifact #13291335905 expires 2026-11-11T02:37:39Z. Historical CI #41761382312 and #41761581156 failed source pin order and C++ log scope respectively, and remain failure evidence; #41761805054 is the tested successor. Remaining 204 UNKNOWN are primarily simulation movement and raid event, plus GCD, cooldown, time-to-die and trinket/variable. Reuse existing generic AST/readiness providers and test baseline, never create Fury-specific semantic shortcut. MAIN/FROZEN not updated.

## Native action-scoped GCD/cooldown evidence reuse — 2026-11-04

| Function | Reusable artifact | Proven boundary |
| --- | --- | --- |
| APL-if action-context GCD/cooldown PRE observation | tools/research/simc_native_if_action_gcd_cd_pre_instrument_v1.py, SHA256 9025dd4916f80e811e2cd30dce8772af39f5b7e92c7e9b0031a1bd8bd16ff37a | Official action_t::gcd duration and existing cooldown_t::up. NOT player GCD remaining or queueable is_ready. Unrecognized source suffix and absent cooldown stay UNKNOWN. |
| Source-tied typed AST replay with previous 273 proofs | tools/research/simc_native_if_action_gcd_cd_pre_replay_v1.py, SHA256 42ef54af6a805e9efbf47206bf8a100f2c639cd5930355eee79975fc0ad2906a; [Actions #41763588110](https://github.com/degong2-code/zrotationhelper/actions/runs/41763588110) | Real Native IF: 273 old + 44 new ST = 317/477 independently matched, 160 UNKNOWN; ST 175/255 and 2T 142/222. Actual pristine/instrumented action sequence identical. No full Native action_ready oracle. |

Result receipt SHA256 f0c410f6e86bfe98e0d7921d65e66a8cdb1b1a3b009dfa8dd7dd0d15597a67bb. Artifact #13291702924 expires 2026-11-11T02:54:43Z. Failed intermediary Actions #41763311442 preserved. Next priority is proving generic readiness across actual action-ready attempts, not merely more IF truth matches. MAIN/FROZEN not promoted.

## Stationary-dummy context and opener native-candidate reuse (2026-11-04)

| Capability | Evidence / code | Boundary |
| --- | --- | --- |
| General Rotation core vs SimC environment lane and actual source-identified opener candidate output | tools/research/simc_general_rotation_dummy_context_opener_v1.py, tested SHA256 4ddfe35569220288d97c4101a90ec0e55805458444b2fb1a831784f5268d9ea8; [Actions #41768561410](https://github.com/degong2-code/zrotationhelper/actions/runs/41768561410) | Fixed 477 real IFs: 323 core-only, 81 environment-only, 73 mixed; NOT partition of 160 unknown IFs. No numeric movement assumption. 190 actual source selected rows, 42 source-verified 0-12-second events per target count, with control RUN vs actionable selection separated; not independent readiness or mandatory priority. |

Receipt SHA256 158e08b32a44755446da7c0cad5a9c841e230449a02a2479a6cbfab0e028edb2, artifact ID 13294025913 expires 2026-11-11T03:40:40Z. Pin to official SimC Fury profile blob 3225992ed5b754ad5d61e8b785d9d859f1eed1be, source selected proof d75b1b1fd614b03e73ff3ab269b4735da237f1707740a011b96f4f508509a816 and direct PRE ledger 7d33ae0746d3d595e3012acb8590e78e476d3e4bf5d3b5e94f244329ea215027. Native effective source line and official source file line are separately accounted with exact row content/hash identity. Earlier new-flow CI #41768297223 and #41768425424 failed strict line-origin equivalence, superseded by #41768561410 but not rewritten. Next reuse native structural auditor and generic readiness provider; do not produce WCL-blind candidates from SimC Native selections. Readiness 2572 native outcomes observed, 0 independently rebuilt. MAIN and FROZEN unchanged.

## Unified SimC movement and active-condition evidence (2026-11-04)

| Capability | Reusable implementation or source | Verified applicability |
| --- | --- | --- |
| Official SimC current actor movement and future simulated-event PRE facts | tools/research/simc_native_if_movement_event_pre_instrument_v1.py, SHA256 2092709599cd581c34555c4c3a2f283d03d93139646269e865671ee77311fa62 | Official player movement.distance, sim_t raid_event.movement.in/distance expression, official raid_event no-matching-event semantics. Generic source-derived names, Native snapshot only; no real-game event forecast. |
| Previously proven typed AST and direct Native IF comparison | tools/research/simc_native_if_movement_event_pre_replay_v1.py, SHA256 fbc917642900b8e38f8378e78f645825381e4db2bf4a81dcf072b2ead293aeeb; [Actions #41772291682](https://github.com/degong2-code/zrotationhelper/actions/runs/41772291682) | Default no-movement cohort 477 real IFs: prior 317 + 152 new = 469 matched, 8 UNKNOWN (ST 250/255, 2T 219/222). Native outcome post-computation comparator only, no readiness operand. |
| Generic actually moving scenario E2E in same Native workflow | SimC built-in LightMovement, profile Git blob 063cce2e3072e8bd9ae52f42118971c684e46f12, same seed 31459 and fixed 30s, controlled ST/2T | Native movement occurred: ST 253 PRE-IF readout groups, 8 positive movement distances; 2T 223 groups, 9 positive distances. Future-event state observed. Original and instrumented actual performed actions exact equality for each scenario. Independent AST parity for moving scenario NOT RUN. |

Current fixed default-context replay SHA256 f9894123ba2440fded52dbd228e3e4b2350f7b1b105f6cb97a6272be34d2d5c5; active-movement receipt SHA256 17a8859fa680e9fccb8179659670b7f29595b25c778dc61de1a83f59bae94007. Retained artifact #13294949311 until 2026-11-11T04:18:54Z. No WCL query. Do not confuse SimC LightMovement source event with an observable WoW future event or create encounter plans. User-approved research is UNIFIED: stationary is a conditional branch, not a prerequisite phase. Next evidence producer is independent moving-scenario AST source replay and full generic readiness witness. No MAIN/FROZEN promotion.

## Independent moving Native source replay reuse (2026-11-04)

| Item | Actual provenance | Scope |
| --- | --- | --- |
| Moving ST and 2 target source-based IF replay | tools/research/simc_native_moving_cohort_if_replay_v1.py; SHA256 159e0588efd415df8adcba3c9eb8a708598522ff9ecbf5f7d58e153fcaa8aa01; [Actions #41773228489](https://github.com/degong2-code/zrotationhelper/actions/runs/41773228489) | Real generic LightMovement ST=250/253 matches, 2T=220/223 matches; 470/476 matches, 6 UNKNOWN, zero observed conflicts. Pristine/instrumented performed actions exact, Native IF truth only comparison. |
| Previous separate no-event source-based replay | tools/research/simc_native_if_movement_event_pre_replay_v1.py | 469/477 matches, 8 UNKNOWN, also passed in newest CI. Separate cohort, no event imputation in live WoW. |

Moving receipt SHA256 fc47a022c97387fad29b5c3016eca6f7979ab4c46387bdbe6fc66bc6f2e70e61; GitHub artifact 13295369177 expires 2026-11-11. Reuse existing typed AST, original Native source pin and scenario nonperturbation. Next high-value engine work: independent source-guard readiness witness and source-ordered action selection. Previous 2572 observed Native ready attempts are not independent readiness proofs. MAIN/FROZEN untouched.

## Bounded actual Native base readiness source witness (2026-11-04)

| Engine feature | Reusable code and actual receipt | Proof boundary |
| --- | --- | --- |
| Passive source PRE base guard producer and base-method entry labels | tools/research/simc_native_ready_guard_witness_instrument_v1.py, SHA256 ddb4efe9f7f129e7220eb78086ffe93be0a8da63107d14fc2e59e3308f49f425 | Official pinned action.cpp/player.cpp/action.hpp and cooldown source; one original native action_ready per visited row, no redundant native ready evaluation; source values for cooldown is_ready, internal cooldown, actor movement/castability and cost affordable. Other override paths UNKNOWN. Original action sequence exact. |
| Tri-state negative-only guard replay | tools/research/simc_native_ready_guard_witness_replay_v1.py, SHA256 1d9803d1c0b1966c2f8004d451f3c79612d77380953803b22198de508e88ea35; [Actions #41775800827](https://github.com/degong2-code/zrotationhelper/actions/runs/41775800827) | Real 5,408 Native attempts across ST/2T + moving ST/2T. 881 source-method-confirmed base negative failures, 4,527 UNKNOWN (2,462 observed base guards pass but further checks remain; 2,065 base method path not conclusively witnessed). Native return only comparator, never source input. NOT full independent queue/cost mechanics nor action readiness/choice parity. |

Guard negative reason counts: queueable cooldown 750, resource cost affordability 111, internal cooldown 20. No validated movement-specific negative in sampled actions. Receipt SHA256 e1b09ac1fd27643f0e343569e84ec000dd002bf4d23a1ef2c21797aea3e328ad; retained Actions artifact #13296298893 until 2026-11-11. Old failed CI #41775643329 remains failure evidence, corrected successor #41775800827 PASS. Reuse pinned source guard ordering and strict per-attempt identity; do not infer class overrides from missed method markers alone. Next engine work separate override/path witness and post-base remaining guard checks, then independently implement numeric queue/cost mechanics. MAIN/FROZEN not promoted.

## Numeric Native cooldown source-clock successor (2026-11-04)

| Evidence / reusable capability | Source | Verified limit |
| --- | --- | --- |
| Source PRE cooldown raw clock and queueable threshold producer | tools/research/simc_native_cooldown_queue_clock_instrument_v1.py, SHA256 be04f06ea67e114d9ee593644289a4165b569c21d6d2b4c1365415db42658ae9 | Raw cooldown ready, queueable time, binding flags and current time before exactly one native action_ready. Queueable threshold still SimC method-computed. |
| Numeric independent cooldown comparison at actual action attempts | tools/research/simc_native_cooldown_queue_clock_replay_v1.py, SHA256 25213ff2e2bf2fd91c821ed6afd060700f10d3854df2a25a4543483cae75815b; [Actions #41778567485](https://github.com/degong2-code/zrotationhelper/actions/runs/41778567485) | 5,403/5,408 source-clock numeric Boolean matches; 5 within-1ms UNKNOWN; 750 necessary source-base cooldown negatives supported, not 750 new failures. Full action-ready and skill-choice not validated. |

Receipt SHA256 fe693e20dbe6b22c7ebb26cf4f1f5fddc2fc84ec9638b99a829d8c1a49e7c123. Artifact #13297753559 expires 2026-11-11T05:21:07Z. C++ scope first attempt Actions #41778347185 remains FAILED; successful successor #41778567485. Next generic engine work: source guard numeric costs/queueable tolerance and subclass/target/GCD conditions. MAIN and historical FROZEN untouched.

## Exact source cooldown tolerance and queueability completed subproof (2026-11-04)

| Capability | Existing reusable evidence | Proven boundary |
| --- | --- | --- |
| Source-pinned exact actor/default tolerance PRE producer | tools/research/simc_native_cooldown_tolerance_pre_instrument_v1.py; SHA256 15659a066545de6809bbb9aec94b1c2b6985a44ef63f093ca6576e505b5f4df9 | Read raw actor tolerance, SimC default, clock and bound flags BEFORE exact one original action_ready call; Native queueable clock only comparator. |
| Exact integer tolerance selection/subtraction and cooldown is_ready independent replay | tools/research/simc_native_cooldown_tolerance_replay_v1.py; SHA256 4dc6765babd3c82a7fffdee967c6dc6615919c35e65257148b6a2caa1ceaaa77; [CI #41781223582](https://github.com/degong2-code/zrotationhelper/actions/runs/41781223582) | Same 4 actual Native scenarios 5408/5408 cooldown decisions, 5183/5183 queueable time exact source parity, prior 5 boundary UNKNOWN resolved. Not full READY, action priority or trainer verdict. |

Raw independent result SHA256 bdd55ac2790b2dd2f85bdaf421009fd556f26d39c8031ed8b4086cb2a718766f, ZIP 13299362136 expires 2026-11-11T05:47:08Z. Historical initial source-assert FAIL run #41781051121 preserved, later #41781223582 Native SUCCESS. Next work should combine independent resource/cost and postguards, subclass semantics, selected priority choice; MAIN and FROZEN unmodified.

## Base resource affordability numeric original-method witness (2026-11-04)

| Reusable evidence | Source | Strength/limit |
| --- | --- | --- |
| Source-pinned original-call action cost and player resource PRE producer | tools/research/simc_native_resource_cost_pre_instrument_v1.py SHA256 2750bcdc0b6222b475acd1e599d18d06d39095699b6eb12e3c3ad0bc90a7dd4c | Logs actual dynamic cost from original action_t::cost_affordable and direct player_t::resource_available raw current/infinite facts, WITHOUT extra cost() or resource_available() calls. Subclass base entry absent -> UNKNOWN. |
| Generic Python numeric base resource guard witness | tools/research/simc_native_resource_cost_replay_v1.py SHA256 af08d4c8102421386dd4fc1bd3eacca4987e5ce6b9618fcc874e5d682dc39d40; [Actions #41783176189](https://github.com/degong2-code/zrotationhelper/actions/runs/41783176189) | Actual 5408 attempts, 1167 prior guards gated cost off, 4241 cost booleans independently computed and match Native PRE, including 3350 RESOURCE_NONE, 891 numeric cost comparisons, 111 previously observed resource-insufficiency base negatives. Dynamic cost modifiers and full action_ready still not independently reconstructed. |

Retained actual JSON SHA256 f6c1d587ac2f46a7194c8724445845429ac30f8ed6b528a1ac28474f3d70a8ed, artifact #13299523699 until 2026-11-11T06:06:20Z, tested code head d3ae69aa145d44cca0eb4b152c460a9e6c15db34. Earlier 881 source negative, 5408 exact queue ready, 469/477 stationary and 470/476 moving source IF proven unchanged. Next source capability: positive readiness postguard and subclass selection; no MAIN or historical FROZEN mutation.
