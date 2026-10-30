# Developer Note — Generic SimC Strict PRE Source Bridge (2026-10-30)

**Owner:** research branch `work/github-ci-bootstrap`. **Authority:** branch evidence only; NOT MAIN, NOT FROZEN. Program objective: generic automatic `SimC APL/profile → IF/ELSE hypothesis → independent WCL candidate lock → native/WCL replay → verified General Rotation`. Never hard-code a class, spell, boss or timing rule into the research engine.

## Why this increment exists

The prior source-instrumented SimC experiment [41017244770](https://github.com/degong2-code/zrotationhelper/actions/runs/41017244770) confirmed **206** direct `select_action` foreground records with actual APL source-row pointer matches in Enhancement (64), Fury (76), Unholy (66), plus 35 precombat records and two nonaction waits. This is strong **action-side source/provenance evidence**, not a state-at-decision dataset. Its JSON2 `action_sequence` state snapshots are at event/sample time, not automatically valid Strict PRE at `timestamp < decision_time`. An action record does NOT license a state-transition producer or readiness claim.

The existing engine already provides:
- `simc_apl_source_engine.py` → pinned `ZrotGenericSimcAplSourceHypothesisV1`
- `simc_apl_conditional_ir.py` → source-linked conditional structural IR
- `simc_apl_decision_graph.py` → canonical IF/ELSE graph (may be independently recomputed)
- `simc_apl_observability_contract.py` → required operand/readiness names with explicit UNKNOWN
- `02_SOURCE/runtime/raid_dps/core/behavioral_evaluator.py::StrictPreStateProvider` → reconstruct latest valid transition `<t`, excluding `=t` and future; track source timestamp / excluded counts
- `simc_apl_condition_research.py::bind_strict_pre` → numeric observations only with explicit operand-to-feature mapping
- `simc_apl_priority_trace.py::trace_priority` → existing generic list/call/run/variable evaluator with fail-closed UNKNOWN readiness

**Decision:** introduce only one adapter, not another SimC expression evaluator or a second readiness engine.

## Implemented module and input contract

`tools/research/simc_strict_pre_source_bridge.py`

API: `replay_explicit_pre(model, fixture, graph=None)`. CLI: `--model model.json --fixture fixture.json [--graph decision-graph.json] [--output result.json]`. `--self-test` works without arguments. PyCharm can run without Script Parameters (starts selftest).

Input schema `ZrotSimcSourceAccountableStrictPreFixtureV1`:
- Exact `spec`, `source_apl_sha256`, `source_profile_sha256`, `source_simc_executable_sha256`; these must match the source model byte-identities.
- `provenance_class`: `SYNTHETIC_TEST` or `EXTERNAL_CALLER_DECLARED_UNVERIFIED`; `independently_verified_producer=false`, `gameplay_rule_promotion=false`. The adapter **rejects** claims that a caller-declared producer is already certified; it cannot verify source authenticity.
- `decision_timestamp_ms`: nonnegative integer; `operand_to_feature`: explicit one-to-one mapping restricted to operands required by the *canonical* source IR; no SimC text-name inference.
- `transitions`: event rows containing integer timestamp, integer sequence, feature key, finite numeric value, producer reference, evidence reference, boolean valid. `transitions_sha256` is a SHA256 digest of deterministic compact sorted-key JSON serialization. This ensures *local row integrity*, **not independent truth of provenance**. `unobservable_features` is explicit.
- `synthetic_action_readiness`: allowed **only** when provenance class is `SYNTHETIC_TEST`. No real caller-declared readiness can be asserted READY/NOT_READY until certified producer + mechanic policy are implemented.

Output schema `ZrotSimcSourceAccountableStrictPreReplayV1`:
- Source pins and ledger hash, every source event receipt with PRE eligibility, decision timestamp, maximum accepted earlier timestamp and excluded same/future/invalid counts.
- Exact per-operand diagnostics `OBSERVED_STRICT_PRE_CLAIM`, `UNKNOWN_UNBOUND`, `UNKNOWN_NO_PRE_OBSERVATION`, `UNOBSERVABLE`, etc.; values are **caller-supplied claims**.
- `trace_status`, `trace_reason`, `trace_candidate_action_token`, trace source list/row and trace events **from existing shared priority trace**, not an additional implementation.
- `actionable=false`, `gameplay_rule_promotion=false`, `native_simc_decision_time_state=NOT_CAPTURED`, `native_foreground_parity=NOT_VALIDATED`, `independent_wcl=NOT_RUN`.

## Completed verification

- [Official source coverage CI 41020542529](https://github.com/degong2-code/zrotationhelper/actions/runs/41020542529) **SUCCESS**: synthetic Strict PRE tests with three arbitrary spec labels and multiple action tokens, canonical source identity, direct provider replay, same/future/invalid transitions, unknown bindings, unobservable status, tampered ledger hash, false producer certification and forbidden external READY; existing 28-case generic graph-to-runtime regression PASS. The same new bridge ran on four actual pinned *public source* APLs (Enhancement/Fury/Unholy/Havoc), each with no observed state/readiness; **all correctly BLOCKED, 0 recommended actions**.
- [Offline CI 41020542478](https://github.com/degong2-code/zrotationhelper/actions/runs/41020542478) Python 3.12 + 3.14 both **SUCCESS**.
- Validation scope: **synthetic decision states only**, genuine official APL source fixture coverage. No Native runtime state readings were captured or retrospectively invented for this test. No WCL data/API or Blizzard live-patch verification. The public source APL and previous instrumented binary are different evidence layers; do not mix their SHAs.

### Known limitations and failure modes

- `StrictPreStateProvider` excludes same/future timestamps; a JSON2 simultaneous resource/buff snapshot is NOT a transition that could be injected at `t-1` without real producer evidence. No fabricated earlier timestamp.
- A digest over supplied events does not establish the events are authentic; `producer_ref` and `evidence_ref` remain **caller-declared** until a separate source producer validator independently verifies the underlying raw record.
- Explicit operand mapping is not automated semantic truth; namespace classification and source DBC name matching alone do not certify ability identity or readiness.
- Unsupported guards, action substitutions, variable lifetime, target availability, and unverified readiness must continue to block user advice; synthetic READY intentionally only tests evaluator wiring.
- 4/4 `BLOCKED` is a **safety gate success**, not proof of rotation match, causality or accuracy. The 206 previous Native decisions have not been replayed against their *own* decision-time states.

## Exact Next, prioritized

1. Build a **source-checked state transition producer** that emits event type, observed actor/target, key, value, strict earlier-than-decision timestamp, sequence, source identity and source hash, and audits the identity against trusted native/WCL/Blizzard material before any source-verified input is allowed. Native SimC JSON2 action snapshots alone do not satisfy this.
2. Join a prior validated state snapshot and real *source-pointer & `SELECT_ACTION_FOREGROUND`* reference at a pinned decision timestamp, with independent provenance; keep uncertainty partitioned by missing binding, readiness, target, and unsupported native semantics.
3. Run cross-build, cross-spec comparisons with a discovery cohort → candidate lock → independent holdout. Do not report match on censored/UNKNOWN decisions as a mismatch or success. Do not infer all pairwise priority from repetitions.
4. WCL blind discovery remains isolated from SimC semantic hypotheses before lock. After lock, replay SimC and compare discrepancies, escalate selectively to counterfactual/Blizzard/holdout where user-facing IF/ELSE rules depend on the ambiguity.

**Promotion:** none. MAIN-only current state, architecture contract, global `LATEST_HANDOFF`, FROZEN/Seq578, active manifests and registry unchanged; Seq637 remains UNKNOWN. Research evidence requires MAIN compatibility review before any authoritative promotion.
