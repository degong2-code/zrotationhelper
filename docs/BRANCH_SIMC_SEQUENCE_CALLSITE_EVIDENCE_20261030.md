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


## Verified Native successor result — source-callsite classification PASS

**Superseding result:** research branch commit `33c2b4d60640943846d182902e0bed84c649f356`, [Native CI run 41016072868](https://github.com/degong2-code/zrotationhelper/actions/runs/41016072868) completed **SUCCESS**. The GitHub Actions job completed source check, synthetic tests, C++ compile, two native profile runs, receipt verification and summary-only artifact upload.

- **Newly compiled instrumented binary SHA256:** `15d1eb46fc3af3aeaafb31ace6cdb33825675ac5b436f6db0ccfe8218258ef86`, distinct from prior `9f480f0c...`. Upstream source SHA fixed at `710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`.
- **Enhancement:** 71 Native sampled sequence rows; 71 exact pointer→APL row+signature matches; 0 drift; `FOREGROUND_EXECUTE_ACTION=64`, `PRECOMBAT_DIRECT=7`.
- **Fury:** 94 sequence rows; 92 exact pointer→APL row+signature matches; 0 drift; `FOREGROUND_EXECUTE_ACTION=76`, `PRECOMBAT_DIRECT=16`, **`WAIT_NON_ACTION=2`**. These two wait records have no action pointer by design and must not count as uncertain spell actions.
- **Together:** 165 recorded sequence entries = **163 genuine action entries with 163 exact APL pointer provenance matches** + two identified nonaction waits. `0` signature drift; `140` foreground **execute_action callsites**, `23` precombat callsites, `2` wait records. No queued-specialized or variable-side-effect entry occurred in these two small public fixtures: their detection remains synthetic/static verified, not empirically covered.
- **Important false-confidence correction:** Initial same-feature C++ run [41015679751](https://github.com/degong2-code/zrotationhelper/actions/runs/41015679751) had **compile PASS / native audit FAIL** (`LIVE_POINTER_UNCLASSIFIED_SEQUENCE_CALLSITE_fury`) because it included the two waits among unknown **actions**. This is a validation pipeline classification failure, *not* a failure of the SimC hypothesis or APL pointer algorithm. The follow-on patch explicitly distinguishes `WAIT_NON_ACTION` from `UNKNOWN_CALLSITE` for genuine actions, then independently recompiled and passed.
- Offline Python 3.12/3.14 CI run [41016072936](https://github.com/degong2-code/zrotationhelper/actions/runs/41016072936) both SUCCESS at the corrected implementation commit.

**Evidence interpretation:** The 163/163 ratio is conditional on the *recorded action sequence entries in these two source-pinned public runs*, not a cross-build identity-precision or recommendation-accuracy estimate. A source `FOREGROUND_EXECUTE_ACTION` callsite can arise from `strict_sequence` / `spell_queued_action` as well as `select_action`; it is not independently proof of a normal foreground priority decision. No strict PRE state reconstructed and no readiness policy validated. Source pointer count is unrelated to whether SimC is optimal and cannot substitute for independent blind WCL discovery.

**Next product-critical task:** discriminate actual `select_action` returns vs strict-sequence/queued foreground paths at the action selection event, preserving queue/aborted action evidence; then record only earlier-than-decision source state transitions with explicit observability limitations to begin state-conditioned priority replay. Favor a small generic reporter change over repeated costly full C++ rebuilds when an offline source or synthetic fixture suffices. Next native source fixture should be a genuine held-out specialization/build (not repeat existing two for percentage inflation).

MAIN authority remains unchanged; no global handoff, FROZEN, Seq578, or project pointer modifications, and Seq637 is UNKNOWN.
