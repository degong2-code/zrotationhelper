# Native APL action-attempt source ownership — research evidence (2026-10-31)

Owner: BR-SIMC-APL-BOOTSTRAP. Branch-only research; not gameplay authority.
Code SHA df6d055bfd3f3e837cc703baf9c38f6ed3fe9f1b.
Pinned official SimC SHA 710c2408bfd3ae4df71b8cd55cdf01f63fd6c926.
Native CI https://github.com/degong2-code/zrotationhelper/actions/runs/41080523109 SUCCESS, four pinned public profiles.
Offline CI https://github.com/degong2-code/zrotationhelper/actions/runs/41080523421 SUCCESS, Python 3.12 and 3.14.
New instrumented binary SHA256 e6562a937e81ba11c12167e83e99ffb53a55fa0bf44a8f5c7eee9a96839dbc5e.

## Change

Research-only files simc_native_apl_eval_scope_instrument.py and
simc_native_apl_eval_scope_audit.py are integrated into the existing
Native probe, existing workflow and offline CI. Source-pinned C++ RAII
action-attempt BEGIN/END envelopes are emitted around the existing
player_t::select_action action_ready and variable execute path.
The scope proves an actual action signature pointer matched an item
in its owning action priority list. It records exact list name,
1-based ordinal, Native execution mode, actor/spawn, reset epoch,
source timestamp and source monotonic sequence. Separate Python raw-byte
audit independently verifies nested envelopes, source sequence uniqueness,
source epoch, original EVAL markers and matching effective source rows.
Unknown pointer or absent scope stays UNKNOWN.

DO NOT infer that pointer-matched action-attempt context proves direct
if_expr evaluation. A readiness or other expression may also evaluate
during the action attempt. None of this certifies READY or a gameplay
priority. Eval markers are NEVER treated as earlier state transitions.

## Actual results and exact denominators

| Pinned public specialization | Source attempt BEGIN markers | Bare resource evaluations | Pointer-matched action-attempt contexts | UNKNOWN contexts |
| --- | ---: | ---: | ---: | ---: |
| Enhancement | 1353 | 0 | 0 | 0 |
| Fury | 1548 | 137 | 137 | 0 |
| Unholy | 1566 | 0 | 0 | 0 |
| Havoc | 4868 | 129 | 124 | 5 |
| Total | 9335 | 266 | 261 | 5 |

Fury rage source contexts, all FOREGROUND:
- Slayer list ordinal 3, rampage: 48 actual evals.
- Slayer list ordinal 13, rampage: 7 actual evals.
- Variables list ordinal 4, variable: 82 actual evals.

Havoc fury source contexts:
- Default list ordinal 9, pick_up_fragment, FOREGROUND: 11 evals.
- Default list ordinal 9, pick_up_fragment, OFF_GCD: 110 evals.
- Default list ordinal 26, felblade, FOREGROUND: 3 evals.
- UNKNOWN_NO_NATIVE_ACTION_ATTEMPT_CONTEXT: 5 evals.
Thus 115 formerly outside the FOREGROUND select window split into
110 source-confirmed OFF_GCD action-attempt contexts plus 5 UNKNOWN.

Resource comparison is a SEPARATE dimension: prior Native source
STRICT PRE partial-producer matches 146, same-timestamp excluded 5,
outside foreground selection 115. Never add 261 pointer-matched
contexts to 146 partial resource matches as disjoint success cases.
Source event marker counts, selected action counts and profile source
requirements are not interchangeable denominators.

Actual per-decision directly certified IF-guard operands: 0.
Complete resource producer coverage: UNKNOWN.
Action readiness certified: 0/90; General Rotation gameplay promotion: 0.
Native original uninstrumented action parity: NOT_VALIDATED.
WCL independent blind discovery/replay/holdout and Blizzard current
Retail mechanic verification: NOT_RUN in this branch.

Native original log SHA256:
- Enhancement: 50a3da1d8a1e05ad11ecfc4733a2e07e0a76eb7cd01b2fa7d791676c844c051f
- Fury: cbb211ea73ed4a0f1b69a5c2c82c6893a0834f58e8add7f6a1502ab66149c0b4
- Unholy: 1d15cab9ee6fbaf07b2fbcb832881388deb722937a5c37aaa3b7cc3ead342ade
- Havoc: b5da08bfdf3cf55f31b769bff45e67054d42d704f639ce709c1e5ef9d2939139

Raw Native logs were independently audited in the CI runner but not
retained in the artifact upload. Hash receipts do not constitute
downloadable raw evidence or post-run independent byte recalculation;
further strong claims need bounded public marker-only retained
evidence or equivalent independent source-locked replay.
The actual source pointer relation is runtime source-generated
and cannot be recertified from merely copied ordinal labels.

## Scope and next work

Branch research: BRANCH_VALIDATED for this exact fixed fixture and
Native source instrumentation only, NOT gameplay MERGE_READY or FROZEN.
No change to MAIN, Seq578, canonical registry, CURRENT_STATE, global
LATEST_HANDOFF or General Rotation baseline. Seq637 remains UNKNOWN.

Next, statically check direct guard call sites and smallest necessary
readiness evidence for a useful Fury rampage / Havoc felblade conditional
decision. Do not recompile full four-profile SimC merely to chase five
UNKNOWN cases without demonstrated user-facing consequence.
Maintain WCL blind lane independence and strict timestamp-less-than
decision state semantics. No user local PyCharm action.
