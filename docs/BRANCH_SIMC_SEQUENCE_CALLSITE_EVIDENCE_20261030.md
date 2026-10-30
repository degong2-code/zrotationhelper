# BRANCH_SIMC_SEQUENCE_CALLSITE_EVIDENCE_20261030

## Mission
One generic research engine: arbitrary pinned SimC profile -> automated conditional APL hypotheses -> source-backed action object and decision-time evidence -> independent blind WCL comparison after candidate lock. This branch increment labels the **actual C++ source callsite of each sampled action-sequence entry**. It does NOT infer a cast recommendation or import SimC priority into blind WCL discovery.

## Previous completed proof (authoritative receipt scope)

Dedicated fixed-source instrumented SimC build `41013989448` **SUCCESS**. Upstream `simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`, instrumented binary SHA256 `9f480f0cafb0b1b394abc242829e95b494495547049220ca69bb71caa0dad884`.

- Enhancement public run: 71/71 native sequence rows had pointer-matched source APL row and exact effective-row signature; no signature drift. Effective APL 114 rows.
- Fury public run: 92/94 exact pointer match; 2 rows recorded `NO_POINTER_PROVENANCE`; no signature drift. Effective APL 121 rows.
- Aggregate 163/165 exact pointer provenance (not 163 verified foreground priority decisions). Unproven 2 preserve UNKNOWN. No blind WCL or Strict PRE inference.
- Source patch instrumentation and independent real native run SUCCESS (not just static self-tests).

## Next research increment: native sequence-add callsite evidence

- `tools/research/simc_apl_selection_callsite_instrument.py`: adds an explicit recorded callsite label at the **actual** SimC `player_t::sequence_add` entry from four source pathways: `PRECOMBAT_DIRECT`, `FOREGROUND_EXECUTE_ACTION`, `QUEUED_SPECIALIZED_EXECUTE`, `VARIABLE_SIDE_EFFECT`. Others retain `UNKNOWN_CALLSITE`. The record owns the tag; JSON2 serializer reads it. Pin-guarded edits in player header/source, player_collected_data header, action.cpp, variable.cpp and report_json.cpp; zero class/spec action knowledge, no generic APL priority changes.
- `tools/research/simc_apl_pointer_provenance_audit.py`: counts exact source-callsite tags separately from pointer row matching, and surfaces each event's category. Refuses missing/invalid action callsite when strict audit is requested. **No tag is equivalent to verified live decision state:** a `FOREGROUND_EXECUTE_ACTION` callsite can execute from strict sequences/spell queue branches as well as `select_action`; `QUEUED_SPECIALIZED_EXECUTE` is not an ordinary foreground selection, and `VARIABLE_SIDE_EFFECT` is not a spell recommendation.
- `tools/research/simc_apl_pointer_native_probe.py` requires explicit source callsite data, preserves original pointer evidence, reports distinct tallies; user-private profiles/logs not uploaded.
- `.github/workflows/simc-apl-pointer-provenance.yml` runs synthetic fail-closed selftests, checks fixed upstream SHA, applies both reporters, compiles a **new** instrumented SimC executable, executes public Enhancement and Fury profiles, uploads receipts and summary only.
- Test classifications: synthetic PASS per CI job source-step; offline Python 3.12/3.14 SUCCESS at code revision `362e8883abb6c7cf33afdcf1452bf87a7b08b1d2`.

## Explicit proof boundary and next work

New native compile/execution is **PENDING_RESULT** at https://github.com/degong2-code/zrotationhelper/actions/runs/41015679751. Do not claim its results before checking actual job conclusion and native summary.

Even with native callsite evidence, no decision PRE state; no actual eligibility/readiness policy; no guaranteed APL `select_action` branch (foreground includes other pathways), no native/independent WCL optimality. Do not treat source callsite counts as class ability mapping correctness. Candidate/threshold lock remains before independent holdout.

The new instrumented binary is a separate artifact with a fresh SHA and cannot reuse the previous `9f480f0c...` hash. Research-only; no changes to MAIN, active manifest, General Rotation baseline, FROZEN, Seq578, Seq637 UNKNOWN, or global handoff.

Exact Next: resolve new native CI outcome; if it fails, separate generic pipeline failure from hypothesis failure. If PASS, compare source pointer + caller origin on the same raw action entries, especially unproven Fury events. Progress next to instrument exact `select_action` return and Strict PRE transitions, avoiding replay of same-timestamp post-action states.
