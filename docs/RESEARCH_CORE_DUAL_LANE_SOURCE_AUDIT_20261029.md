# zRotationHelper — dual-lane Research Core source audit (2026-10-29)

**Status:** branch-local READ-ONLY source assessment / NOT a promoted architecture contract.  
**Target:** `work/github-ci-bootstrap`. Product authority, frozen evidence, CURRENT_STATE, and MAIN pointers are unchanged.

## Authority used

The source snapshot's `ROTATION_RESEARCH_SYSTEM_CORE_CONTRACT_V1.md` (SHA256 `5d8051cf107a61700efeb89e94e042e64a26f0813a4c2e9689163d42872123bd`) explicitly supersedes older global WCL-first wording.

Overall research topology:

1. **SimC APL/profile hypothesis bootstrap** extracts action lists, conditions, target/variable semantics, and initial conditional-rotation hypotheses.
2. **Independent WCL blind discovery** reconstructs strict-PRE state/readiness and locks numeric/structural behavior candidates **without ingesting SimC answers**.
3. **Post-lock reconciliation** replays the SimC hypothesis against WCL states and compares the independently locked WCL candidates with Blizzard mechanic authority; classify `match / conflict / missing / unknown`.
4. **Selective validation** uses holdout and SimC counterfactual only where evidence/impact warrant it.
5. **User deliverables** are a validated General Rotation and encounter-specific deviations layered on top, not inferred from CI success.

SimC-first refers to the **efficient hypothesis bootstrap**, not a license to contaminate blind WCL discovery or treat SimC as gameplay ground truth.

## Source inspection (snapshot, not current production approval)

| Observed source | Concrete finding | Implication |
|---|---|---|
| `core/GenericSimcAplHypothesisCompilerV1.py` | Parses APL action-list rows, `if` tokens, and list-call structure. But `compute()` requires sequence-568-specific pinned inputs and tuple counts; marks expressions `OPAQUE_NOT_EVALUATED`, readiness `UNKNOWN`, `can_compile_to_canonical_RotationRule=False`, and `rules_promoted=0`. | Useful research prototype; **not** the generic current-APL semantic bootstrap or actionable provider. SHA256 `48ef1f8620e44bb06f2d637ee9ed382e25acc3673e509148d88ad57d3b935c2d`. |
| `pipelines/stage_registry.py` + `onboard_spec_v1_8.py` | Existing `O0–O8` registry routes O3 to WCL evidence bootstrap, O4 PRE-state, O5 discovery, O6 validation. No explicit SimC hypothesis lane or central three-source reconciler in this registry. | Do not mistake the older onboarding path for the complete dual-lane research engine. |
| `CORE_CONFORMANCE_LEDGER_V1.md` | At snapshot time: SimC APL semantic bootstrap #11, reconciliation #20, frozen-rule provider #21, and General Rotation compiler #23 were `BLOCKER`; automatic specialization bootstrap #8 was `INCOMPLETE`. | These are **historical snapshot judgments**, not revalidated current MAIN statuses. |
| Existing GitHub `general_rotation_evaluator.py`, `behavioral_evaluator.py`, `SpecAdapter`, `coverage.py` | Offline synthetic CI passes on Python 3.12/3.14; code can evaluate provided rules and reconstructed states. | Evaluation infrastructure is not automatic research/discovery nor empirical or optimality proof. |

**Observed source snapshot:** `ZROT_GITHUB_SOURCE_SNAPSHOT_REVIEW_BUNDLE.zip` (locally provided, not uploaded to this public repository). This audit includes **no private source contents, raw WCL data, secrets, or report identifiers**.

## Corrected GitHub development critical path

1. **Authority / active-source check (MAIN-owned):** identify the latest approved producer, config, and current SimC profile/APL inputs. Do not promote snapshot scripts by filename alone.
2. **SimC semantic bootstrap scope:** preserve the useful parser behavior, separate generic source parsing from sequence-568 fixture gates, and define testable condition/variable/list-call semantics. Hypotheses stay non-actionable.
3. **Blind WCL lane stays isolated:** maintain strict PRE and candidate lock independent of semantic answers from SimC.
4. **Reconciliation interface:** compare SimC predicted actions with WCL observed actions/readiness and independently locked candidates; preserve `UNKNOWN` when state/readiness or build match is unavailable.
5. **MAIN-approved IR/provider integration:** freeze generic Spec Model and General Rotation Rule IR before an actionable rule provider or IF/ELSE compiler is treated as authoritative.
6. **Cross-spec empirical validation, then encounter deviations and user-facing adapters.**

### Deliberately not done

- No migration of the historical APL compiler into the production provider.
- No modification of `main`, Project Sources/Instructions, `CURRENT_STATE`, FROZEN assets, Seq578, or Seq637 (remains `UNKNOWN`).
- No live WCL, Blizzard API, or SimulationCraft production run; no gameplay priority/optimality claims.
- No automatic closure of the snapshot's conformance blockers.

**Next implementation candidate:** a small generic SimC APL semantic-bootstrap fixture and independent offline tests **only after** latest MAIN source/manifest authority is resolved.
