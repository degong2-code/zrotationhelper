# zRotationHelper — SimC Engine Developer Review (2026-10-30)

Scope: branch-local developer notes; no authority or production promotion.

## Main architectural risk
The deliverable is a **generic SimC rotation interpreter/conditional-rule engine**, then an independently discovered WCL empirical engine and **post-lock** reconciliation. A fixed-sample result such as Seq623's 785 source decisions does not replace either engine. Avoid reimplementing frozen MAIN work or class hardcoding.

## Source and runtime separation
- Source input: `simc_apl_source_engine.py` supports public pinned profile/actual local SimC effective APL. The former is a source snapshot, not a native execution proof.
- Structure: `simc_apl_conditional_ir.py` preserves every APL row and records unresolved semantics; structural coverage is not behavioral coverage.
- Limited runtime: `simc_apl_priority_trace.py`, `simc_apl_variable_runtime.py`, `simc_apl_precombat_replay.py`, `simc_apl_readiness_provider.py`. Inputs and policies are explicit and sometimes caller-declared. Do not claim inferred readiness if the predicate policy itself has not been verified against real spell/build mechanics.
- Independent native reference: `simc_native_reference_capture.py`, `simc_native_performed_events.py`, `simc_native_json_sequence.py`, `simc_native_oracle_reconciliation.py`. Native logs may reveal action events but background casts/autoattacks/procs confound foreground inference; JSON2 equal-time snapshots cannot be assumed PRE. Caller label `CALLER_ATTESTED_FOREGROUND_APL` is not independent classification.
- WCL research consumer: `simc_wcl_reconciliation_engine.py` remains an offline prototype; code-level numeric candidate lock does not independently certify blind discovery.

## Next implementation acceptance gates
1. **Native-source provenance**: pin SHA of executable, profile, effective APL, actor/spec/build/patch, raw JSON2/text. Refuse incompatible binary/profiles. Keep real sensitive logs off public GitHub.
2. **Decision source**: independently classify foreground vs background action, actor-target scope, reliable event identity; record unknown/excluded coverage.
3. **Actual PRE reconstruction**: prove transition time and sample semantics for resources, aura/refresh/expiry, CD/charges, target, GCD, precombat variables; `source_time < decision_time`. Distinguish inferred simulation state from measured WCL PRE.
4. **Execution parity**: replay the *whole relevant APL* with call/run action lists, variable history, expression operators, target_if, pool_resource, use_item, GCD, line_cd, movement/casting. Compare identifiable candidates to native SimC action events; report match/difference/missing/unknown by spec/build and impact, rather than counting supported syntax.
5. **WCL isolation**: numeric/structural blind cohort/candidate lock before semantic SimC replay; valid build and sample identity, readiness UNKNOWN if unavailable; holdout after candidate lock and threshold freeze.
6. **Rule/UI eligibility**: only after claim-appropriate independent evidence, conditional IF/ELSE model with confidence/evidence/observability; user output skill icon + localized name + short condition; no production promotion without MAIN.

## Developer validation etiquette
- Research branch `work/github-ci-bootstrap` and `main` are separate. MAIN local source and approved manifest need current hash inspection before merge.
- Stable implementation reference `fb03b443c6bcebbcfbde896d443537840e5291e7`: run `40982022833` verified 27/27 × Python 3.12.15, 3.14.9; receipts ZIP CRC and source_sha256 parity PASS.
- CI receipt claims `OFFLINE_SYNTHETIC_SPEC_STRUCTURE_AND_SIMC_APL_SYNTAX_ONLY`, `simc_live=NOT_RUN`, `wcl_live=NOT_RUN`, `seq637=UNKNOWN`, `authority_promotion=NONE`. Never uplift to SimC native parity/real WCL.
- No WCL secrets, profiles, local personal paths, raw user logs, caches, or old entire local code snapshot in public repo.
- Bundle related independent checks in one iteration; do not rerun 785 source decisions or same-SHA 27 CI just to inflate pass counts. For changed code run focused checks then CI and preserve failures.
- **Potential issue for next review**: `SIMC_ENGINE_SOURCE_TO_PRIORITY_RUNBOOK.md` retains a statement saying native log acquisition “does not parse log” in an older section despite downstream parser and oracle additions; reconcile documentation in focused cleanup, without claiming the captures have been actually run. Also note some literal escaped backtick sequences in JSON2 runbook section.
- Do not mechanically convert Work OS older 2026-10-28 WCL-first instruction backup into current Project Instructions. Current project-level dual-lane contract supersedes that historical snapshot.

## Operational next
Use `docs/BRANCH_SIMC_HANDOFF_20261030_V2.md` and existing runbook as continuity; review latest branch HEAD + CI run before declaring exact state. First restore/report, **wait for user '진행'**. Main owner only promotes.
