# Developer Note — Native resource evidence versus actual SimC APL operand requirements

Date: 2026-10-30. Owner: research BRANCH `work/github-ci-bootstrap`; not a MAIN promotion or a user-facing rotation rule.

## Motivation and decision

Previous pinned Native SimC experiments verified source-emitted reset epochs and monotonically stamped resource events on Enhancement, Fury, Unholy, and Havoc (Native run [41059211056](https://github.com/degong2-code/zrotationhelper/actions/runs/41059211056)). The actual values from that run gave 968 **strictly earlier source-value-consistent diagnostic field comparisons** and 740 **same-millisecond excluded comparisons**. These are not observations of SimC APL expression values, spell readiness or rotation optimality.

The next user-impactful dependency is source-aware **APL operand and readiness semantic coverage**. The existing `simc_apl_observability_contract.py` and `simc_apl_semantic_resolver.py` already produce a canonical cross-spec source inventory, including source line references, but deliberately leave all operand identities and action readiness `UNKNOWN`. Reimplementing a general APL interpreter or another new Native resource logger would duplicate valid work.

**This increment** adds a small, fail-closed requirements-to-producer gap audit, not a speculative value binding.

## Implementation

- `tools/research/simc_apl_native_observability_gap.py` consumes the exact existing `ZrotSimcGenericObservationRequirementsV1` and canonical `ZrotSimcGenericSemanticRoutePlanV1`, recomputes the latter independently from the former and rejects altered source references, forged Native feature identities, fabricated readiness and promoted gameplay rules. Every source operand and action token is retained with APL source references.
- The first source-profile run revealed **zero** operands spelled `resource.<...>` across all four pinned upstream APLs. This is NOT evidence that none contains resource expressions: SimC can express resources with bare tokens. Auditing only `resource.` grammar would be materially misleading.
- The audit therefore accepts a separately fetched **exact upstream** `engine/util/util.cpp` file from `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`. It validates the file SHA256, unique `util::resource_type_string` source anchors and the `parse_resource_type` function's link to the same labels, extracts resource enum label **names** from the upstream C++ rather than maintaining specialization-specific or fabricated token lists, and checks whether **unqualified APL tokens are lexical resource-name candidates**.
- The C++ `resource_type_string` list is an authoritative source for how the pinned SimC calls its resources, **not** proof that every APL expression with that spelling maps to `player_t::resources.current`. No mechanical mapping is inferred from text. The candidate is explicitly marked `PINNED_SIMC_RESOURCE_LABEL_CANDIDATE_NOT_EXPRESSION_PROOF`; the Native observed feature, current/max semantic type, mechanic identity, Strict PRE decision state and action readiness remain unbound/UNKNOWN.
- Readiness is independently tracked for every source action token with the shared mandatory readiness dimensions; missing readiness cannot silently mean NOT_READY or permit a lower-priority action. No candidate action is released.
- CI `.github/workflows/simc-public-source-coverage.yml` downloads the exact source file at the pinned public commit via HTTPS, computes SHA256, parses four real upstream APLs and their structural IR + decision graphs, and asserts full source requirement coverage, stable original source hash, no accidental Native semantic binding, full readiness UNKNOWN and no gameplay promotion. No new expensive C++ rebuild; existing 28-case and Strict PRE synthetic regression suites remain.

## Verified results (source requirements, NOT bound or observed actions)

**Four-profile pinned official source CI:** [41062906668](https://github.com/degong2-code/zrotationhelper/actions/runs/41062906668) — **SUCCESS**. Python 3.12/3.14 offline CI: [41062906694](https://github.com/degong2-code/zrotationhelper/actions/runs/41062906694) — both **SUCCESS**.

| Actual source APL | Operand requirements | `resource.` grammar operands | Bare token matching pinned resource label | Readiness action tokens, all UNKNOWN |
| --- | ---: | ---: | --- | ---: |
| Enhancement Shaman | 77 | 0 | none | 24 |
| Fury Warrior | 68 | 0 | `rage` | 26 |
| Unholy Death Knight | 92 | 0 | `rune`, `runic_power` | 21 |
| Havoc Demon Hunter | 57 | 0 | `fury` | 19 |
| **Aggregate across profiles** | **294** | **0** | **4 lexical candidates (not bindings)** | **90** |

`rage`, `rune`, `runic_power`, `fury` are **source-lexical matches only**. In particular, an APL `rune` expression could have additional class-specific readiness/count semantics not represented by a simple last resource current value; the current audit does **not** resolve that ambiguity. No actual APL operand was automatically bound to the Native state producer, and **zero** action readiness tokens were certified.

### Failure history preserved

The first new source-coverage CI [41062265206](https://github.com/degong2-code/zrotationhelper/actions/runs/41062265206) failed because the synthetic negative readiness test expected a rejection from the new audit while the existing upstream semantic resolver rejected the forged READY claim **earlier** with `SOURCE_READINESS_CANNOT_BE_CERTIFIED`. This is a pipeline **test expectation failure**, not proof a gameplay hypothesis is wrong. The unchanged fail-closed readiness behavior was retained; the test expectation was corrected.

The [41062365187](https://github.com/degong2-code/zrotationhelper/actions/runs/41062365187) successor passed and proved zero dotted resource candidates in real APL profiles. The subsequent pinned `util.cpp` lexical route was added to avoid that source coverage blind spot and independently passed [41062906668](https://github.com/degong2-code/zrotationhelper/actions/runs/41062906668). No source-only counts are described as observed gameplay effects.

## Exact Next, based on actual missing evidence

1. For the **four concrete bare candidate operands** at their original APL source rows, inspect the actual pinned SimC `player_t::create_expression` / class-specific `create_expression` parser chain and resource-expression implementation. Prove *which* exact operator/value each expression resolves to for the relevant profile; lexical matches alone are not sufficient. Distinguish `rune` availability/count semantics from `runic_power` and resource current/max. Do not hardcode specialization logic in the generic evaluator; use source-backed SpecAdapter semantics if necessary.
2. Join only proven, source-accountable value semantics to the already epoch-pinned Native resource producer, with same actor/build/instance and source transition strictly `timestamp < decision_timestamp`. The 740 same-time field comparisons from Native CI must remain excluded. A decision-time diagnostic snapshot remains audit-only, never a PRE transition.
3. Readiness is still unknown for all 90 source action tokens. Choose the smallest user-relevant readiness family (actual action available, cooldown/charges, resource, buff/proc, target, replacement), establish official SimC/Blizzard mechanics and a source-backed producer before resolving the first IF/ELSE action. Refuse to infer A>B merely because B was not cast or not proven available.
4. Compare Native source-locked selected actions against the shared generic IF/ELSE evaluator as **match / conflict / missing / unknown**, preserve unsupported cases and independent WCL blind candidate lock until after WCL discovery. Only MAIN may promote validated gameplay contracts after compatibility and holdout review.

**Authority & product scope:** MAIN `CURRENT_STATE`, global `LATEST_HANDOFF.json`, canonical registry, active manifest/pointer, frozen General Rotation and Seq578 unchanged; Seq637 UNKNOWN. No local PyCharm action required. No downloadable `.py` artifact provided in this step; research source remains in GitHub, tested there.
