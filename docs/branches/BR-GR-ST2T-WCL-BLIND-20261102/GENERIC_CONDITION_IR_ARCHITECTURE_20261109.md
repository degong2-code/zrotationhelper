# General Rotation: Source-bound Conditional IR v1 (Branch only)

- Policy ID: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`
- Authority: branch-local design, NOT canonical MAIN architecture promotion.
- Scope: specialization-neutral general opener and conditional priority. NO boss plan or NSRT.

## Product-oriented decision

**Do not add `if action == rampage`, `if class == warrior`, or `if spec == arcane` to the generic interpreter.** Put the semantics of individual ability prerequisites in a **source-anchored declarative SpecAdapter** and evaluate them with one spec-neutral condition interpreter. Distinguish *which ability/variant the rule applies to* from *how to evaluate the rule*.

| Layer | Responsibility | Must not infer |
|---|---|---|
| SimC APL source-row loader | action-list/priority order, build identity, original source row SHA, source occurrence | readiness of an APL action from its presence in profile |
| Mechanic source audit + SpecAdapter | source-pinned C++ method/guard provenance, semantic field bindings, typed necessary condition IR; dispatch/variant worklist | complete virtual route from a static guard site |
| Runtime PRE capture adapter | scoped raw equipment, buff/proc, resource, cooldown, talent, target, cast/sequence fields; source and time receipts | no zero-fill, no inferred gear from profile alone, no protected WoW API workaround |
| **Generic Condition IR** `general_rotation_condition_ir_v1.py` | one Boolean/numeric AST interpreter with `all/any/not/compare`, exact typed comparisons and 3-valued TRUE/FALSE/UNKNOWN | any spell names, weapon slot meanings, buff names, trusted producer status, READY |
| Generic `GateContract` + priority proof | convert independently authenticated PRE facts into bounded NOT_READY/READY/UNKNOWN, with exhaustive dynamic route closure for full positive READY | Native chosen action as independent availability; WCL observed cast as optimality |
| Independent WCL candidate/holdout, General Rotation IR, Dummy evaluator | disjoint numerical validation and actor feedback only when game state observable | an error when state or causal priority is unknown |

## Two examples from actual pinned official SimC

1. **Warrior Fury Rampage (source requirement only):** `sc_warrior.cpp@38ee3dd0...` checks `main_hand_weapon.type == WEAPON_NONE || off_hand_weapon.type == WEAPON_NONE` and returns false. This necessary predicate is **both equipment slots nonempty**. It does **not** mean a single two-handed (2H) weapon. The source adapter declares `all(main_hand.weapon_type != NONE, off_hand.weapon_type != NONE)`. Actual state at target time is **UNKNOWN** because the original source PRE fixture has not yet captured these two field values. The adapter is source-verified; equipment state is not.
2. **Arcane Mage Arcane Blast and Prismatic Bolt (two distinct physical skills):** `sc_mage.cpp@306d835f...` has opposite checks against `buffs.prismatic_bolt->check()`, mapped to `buff.prismatic_bolt.active == false` vs `== true`. Original APL `MID2_Mage_Arcane.simc@8d06eda4...` has independent source rows in `spellslinger`. Both C++ source guards verified. No real Mage PRE buff observation in this fixture; consequently both physical READY statuses UNKNOWN. Synthetic state true/false shows opposite truth numerically with the identical generic evaluator.

A **hypothetical dual-dagger ability** requires both slots equipped **and** both normalized `weapon_subclass == DAGGER`. No new engine branch is needed, regardless of action name. This synthetic requirement is NOT a claim about an existing live retail ability. Slot/category mapping is a producer- and SpecAdapter-reviewed semantic layer; actual WoW/SimC item-subclass numeric IDs are not guessed by generic core.

## Binding and provenance contract

A rule uses `semantic_key` (e.g. `equipment.mainhand_offhand_present`), `source_profile_git_blob`, `source_row_sha256`, `source_method_path/git_blob`, `source_guard_sha256`, `gate`, and a bounded declarative expression. A rule ID is hashed from the entire definition. The generic interpreter never selects rules by action-name string. Its caller must resolve the correct *source row + specialization + build + instantiated action/variant*, including class method dispatch. Static row/source pin alone does not prove that runtime dispatch traversed that method.

A state observation has `key,value,event_t_ms,captured,receipt` with explicit phase:
- `SIMC_ORIGINAL_METHOD_PRE`: exact original method PRE time `t`.
- `WCL_STRICT_PRE`: latest authenticated valid transition strictly `timestamp < t`. Same-time/future rejected, no cross-basis substitution.
- `SYNTHETIC_TEST_ONLY`: tests, never production evidence.

The core rejects duplicate field observations, cross-phase inputs, source profile/row mismatches and incompatible types. It evaluates arbitrary named fields without recognizing weapon, talent or spell names. No implicit numeric 0, no `bool`↔`int` coercion, no unsupported expression execution or Python `eval`. Three-valued conjunction/disjunction preserve partial knowledge; a proven false subpredicate may numerically dominate an unknown sibling, but **a numeric declaration does not become a gameplay NOT_READY without independently verified source and raw operands**.

**Trust boundary is deliberate:** `inspect_requirement` reports `hypothesis`, but feeds **zero** unverified Facts into the `GateContract`; its open-world output stays UNKNOWN even when a user constructs `false` or `true` evidence. Existing separately authenticated source PRE producer/consumer is the promotion boundary; do not let external JSON strings `INDEPENDENT_SOURCE_REPLAY` or fake `closed=true` bypass it.

## Expansion without per-ability engine branches

- New specialization: supply original profile and source guard manifest, then register field capture and mechanic binding. No edits to `general_rotation_condition_ir_v1.py` for ordinary equipment/buff/talent/resource/count comparisons.
- New build/talent or replacement: re-evaluate resolved action *implementation identity* and source method route. The same skill name may resolve to a different implementation; no rule inheritance without a validated dispatch/variant receipt.
- New source field: first check existing PRE fixtures. Capture only missing state with a passive source accessor, preserve original method-call counts, compare pristine/instrumented action sequences. Keep original, WCL and addon provenance separate.
- New predicate operator: add to generic interpreter **only if an actual source case cannot be modeled** by present compare/all/any/not IR, with cross-spec synthetic and real source validation. Avoid a speculative universal compiler.
- Actual user training: require current Blizzard addon API observability of needed state. Unavailable equipment/buff readiness, target counts or GCD means UNKNOWN rather than erroneous-user verdict.

## Verified this branch, not yet a product-ready rotation

CI [#42543426130](https://github.com/degong2-code/zrotationhelper/actions/runs/42543426130): Python 3.12 and 3.14 compile/self-test PASS, original SimC Warrior & Mage C++ guard and APL binding audit PASS, 3/3. **No new SimC C++ compile, WCL API or WoW client replay**. Existing 20,031ms Fury source facts and previous focused C++ PASS remain separate. The present evidence proves reusability of static semantics and numeric IR, NOT runtime equipment/buff truth, full positive READY, best GCD priority, independent WCL holdout or training error.

### Product Exact Next

Finish general opener and conditional priority across ST / 2T / AoE by connecting source-verified necessary conditions with independently authenticated PRE, source-closed positive READY, post-lock WCL comparator, and dummy feedback with explicit observability.

### Session Exact Next

1. Reuse the actual Fury original method PRE and source guard pin to design **one generic `FieldCapturePlan` contract** for equipment-slot fields and Arcane buff fields; source adapter supplies safe exact read expressions/verified source access, not a hardcoded action name.
2. Capture only missing evidence, verify pristine vs instrumented choices on bounded cases, and check producer authenticity separately. Keep user-borne external JSON unable to create a trusted GateContract Fact.
3. Move independently proven necessary FALSE/TRUE into typed `Fact` via a producer-authenticated bridge; keep full READY UNKNOWN until dynamic route closure. Test both specializations and target-count branches without copying the generic evaluator.
