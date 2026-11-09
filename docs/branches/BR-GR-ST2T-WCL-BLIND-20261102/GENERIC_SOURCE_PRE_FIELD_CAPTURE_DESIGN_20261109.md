# General Rotation — Generic Source PRE Field Capture v1

Scope: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`. Branch-only. MAIN/FROZEN unchanged.

## Engine-first architecture

`tools/research/general_rotation_original_pre_field_transport_v1.py` is the generic reusable transport: 
- Typed `FieldRequest(key, reader, argument)`, bounded field IDs and safe argument parser. **No specialization, action or class name logic in this core.**
- Two current generic read families: `actor_weapon_slot_equipped(slot)` (main/offhand), and `actor_named_buff_active(name)` (current stack via pinned `buff_t::check()`).
- Generates one passive C++ producer at the original `player_t::select_action()` before exactly one `a->action_ready()`. Uses original APL signature-pointer (list, row, action) and SimC time. Explicitly forbids arbitrary C++ expression injection and extra virtual readiness calls.
- Parses paired original marker + Native attempt (the later Native READY boolean is comparator only, never gate evidence). Buff is `-1` if lookup unknown/fallback; translate to UNKNOWN not false.
- **Does not issue trusted `Fact` or READY on its own.** Source truth, read-only correctness, dynamic dispatch and raw producer identity must be validated by an independent consumer.

`tools/research/general_rotation_source_pre_field_capture_v1.py` is a two-spec **integration fixture**, not the reusable interpreter. It assembles official pinned `SpecAdapter` rules:
- Warrior Fury `rampage_parent_t::ready()`: source guard requires both weapon slots occupied. Original static rule was `weapon_type != NONE` for each slot; equivalent normalized capture `equipment.main_hand.equipped == true` and `equipment.off_hand.equipped == true`. No claim of a two-handed weapon.
- Arcane Mage `arcane_blast_t::ready()` vs `prismatic_bolt_t::ready()`: inverted `buff.prismatic_bolt.active` source requirement. The engine field reader receives the buff's validated name as a declarative parameter; no `if mage`/action name in C++ transport.
- Both source files/profiles and source row SHA are pinned to official `simulationcraft/simc@b522cded8c26b97dac03fdf56e57a03ec7e8faa6`. The contract is an exact-source test, not current WoW server mechanic truth.
- A new specialization adds new adapter declarations + required fields to the integration plan, **not another generic parser or a hardcoded spell branch**. New field categories (e.g. item subclass, charges) require bounded generic reader extensions **once**, with concrete source need and independent validation.

## Verification and evidence stages

1. Generic Python 3.12 / 3.14 compile + synthetic fail-closed checks (generic transport 11, two-spec harness 13).
2. Official source contract and static C++ patch validate BEFORE any original SimC compile. Read-only field injection verifies one original `action_ready()` call. Static [Actions #42545694098](https://github.com/degong2-code/zrotationhelper/actions/runs/42545694098) completed SUCCESS; Native job intentionally SKIPPED.
3. For actual new source state, one opt-in Native run is triggered by approved explicit branch commit message `[native-pre-e2e]` or workflow_dispatch; same compiled official SimC binary runs pristine Fury + Mage, then rebuilds only modified `player.cpp` and reruns same profiles/seeds. Compare performed precombat/combat action sequences **for each specialization**.
4. Independently replay original C++ source markers to `ObservedField(..., SIMC_ORIGINAL_METHOD_PRE)` at exact original t; use source-pinned rule and original APL row identity. Never substitute WCL Strict PRE (requires latest transition timestamp strictly < action t). Numeric TRUE/FALSE/UNKNOWN is hypothesis until actual producer/virtual path independently authenticated. No trainer error claims.
5. Separate any hypothesis mismatch from capture/producer failure. Existing old failed CI runs are retained, not counted as PASS. An opt-in Native run must not be called successful before conclusion reported.

## Existing evidence and limitations

- [#42545015114](https://github.com/degong2-code/zrotationhelper/actions/runs/42545015114) FAIL — synthetic test incorrectly expected semantic field **key text** inside generated C++; fixed by testing emitted direct reader.
- [#42545071202](https://github.com/degong2-code/zrotationhelper/actions/runs/42545071202) FAIL in original-source preflight — old safety check assumed no other `buff_t::find` in the entire original `player.cpp`, which in fact already has 10 occurrences; fixed to compare **before/after call-count delta**, preserving other original lookups. Original pristine C++ build and capture step had succeeded before preflight failure; no instrumented C++ or PRE field proof in that run.
- [#42545694098](https://github.com/degong2-code/zrotationhelper/actions/runs/42545694098) PASS 3 essential static jobs; real Native correctly skipped as non-E2E commit.
- [#42545789084](https://github.com/degong2-code/zrotationhelper/actions/runs/42545789084) is the explicit source Native E2E run (check live run conclusion separately; at writing, initial original compile/capture stage IN_PROGRESS). It is NOT evidence of dynamic eligibility until completed.

## Product Exact Next

Validate the fresh two-spec original C++ performance/field evidence; move independently authenticated source PRE necessary gate facts into the open-world proof without positive READY until dynamic dispatch and exhaustive guards established. Extend generic reader families only when a concrete specialization needs them (weapon subclass, buff stack, cost/cooldown). After SimC-first General Rotation hypotheses, use WCL blind candidate lock and post-lock holdout to verify general ST/2T/AoE priorities and tie them to lightweight dummy training with game API observability checks.

## 2026-11-09 후속: 동일 Generic PRE Producer의 실제 Fury·Arcane 원본 E2E

Actual verified E2E [#42545789084](https://github.com/degong2-code/zrotationhelper/actions/runs/42545789084) (4/4 PASS) complements the earlier source static test. Original 46 Fury and 31 Mage combat casts invariant under one generic passive PRE field generator, with no duplicated per-spec C++ patch. Actual raw scoped fields are now available for Fury equipment presence and Arcane buff up/down. Numeric condition evaluation used `ObservedField` and still does **not** emit independently trusted READY/NOT_READY GateContract facts; dispatch must be proven. In particular the Mage `prismatic_bolt` source condition FALSE when buff=0 is an interesting negative candidate, not yet an audited actual class override invocation. Keep original build/pin, raw SHA evidence and future addon/WCL data layers separate.

See successor real E2E JSON receipt for actual numeric values, per-spec counts and hash IDs. Prior original SimC (t=20031ms) source frontier and this newly sampled (t=1681/2414ms) do not represent the same action occurrence.

## 2026-11-09 후속 — Arcane 원본 ready 메서드 실증으로 scoped NOT_READY 독립 증명

The generic PRE producer was reused without modifications: source field values and APL row identity are sampled immediately before the single original action_ready. The Mage-owned bounded source adapter patches the original two C++ `ready()` override guard expressions, captures the same one check-stack value and object identity; a separately authored replay reconstructs the method-to-action link. This method-entry evidence is the missing **causal route** needed to turn a false necessary hypothesis into a scoped independent `NOT_READY`. Numeric-only source PRE observation remains insufficient. Verified all source steps with pristine-vs-instrumented sequence equality (31 original Mage casts) and official source SHA pins in #42548160936. Exact results: Bolt 4 NOT_READY / 1 UNKNOWN, Blast 4 UNKNOWN despite necessary true. No READY positive or General Rotation opener established.

**Scalability recommendation:** Extract only the reusable source-method pointer-to-APL-event pairing, tri-state necessary gate composer, and source-pin/provenance check into a truly generic `OriginalMethodGuardWitness` bridge. Keep Mage/Warrior individual `ready()` guard text, bool inverse, and source-row mapping in SpecAdapter. Resist writing a new per-specialization parser, but do not build a universal C++ AST compiler before a second source method proves need. Use one bounded Fury equipment case as the cross-spec regression, then return to APL opener/priority research.
