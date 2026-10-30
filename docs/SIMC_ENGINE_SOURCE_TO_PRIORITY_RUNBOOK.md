# SimC Rotation Research Engine — local source-to-priority execution (branch pilot)

**Status:** Research-only. Produces a conditional **action hypothesis**, not a validated General Rotation or a gameplay recommendation. No specialization, boss, or historical test cohort is hardcoded.

## 1. Export the specialization's effective APL

With a real local SimulationCraft executable and an appropriate single-actor profile:

```powershell
python tools/research/simc_apl_source_engine.py --spec enhancement --profile "C:\simc\my_character.simc" --simc-bin "C:\simc\simc.exe" --out "C:\zrot\model.json"
```

The `--spec` value must match the profile's exact SimC specialization name. The importer hashes the **profile**, the **effective APL** and the **local SimC executable**. Existing exported action lists can instead be ingested with `--actions-file` (this does **not** independently verify the original profile/build).

For an immutable **official public profile** source (not an executed effective APL), use:

```powershell
python tools/research/simc_apl_source_engine.py --spec fury --upstream-profile "profiles/MID2/MID2_Warrior_Fury.simc" --upstream-revision "710c2408bfd3ae4df71b8cd55cdf01f63fd6c926" --out "C:\\zrot\\model.json"
```

This path ran successfully in GitHub Actions against both MID2 Fury and Enhancement at the pinned commit. It does **not** establish current-game or actual SimC executable equivalence.

**Status of this local executable path:** implemented, but actual user-PC SimC production execution **NOT RUN**. The program checks single-actor/profile consistency and refuses external unpinned profile includes.

## 2. Provide one decision's strictly earlier state

Save as `C:\zrot\snapshot.json` (synthetic example, **not** real WCL evidence):

```json
{
  "spec_slug": "enhancement",
  "decision_timestamp_ms": 1000,
  "transitions": [
    {"timestamp_ms": 900, "key": "target_count", "value": 2},
    {"timestamp_ms": 950, "key": "maelstrom_stacks", "value": 5},
    {"timestamp_ms": 970, "key": "stormstrike_ready", "value": "READY"}
  ],
  "operand_to_feature": {
    "active_enemies": "target_count",
    "buff.maelstrom_weapon.stack": "maelstrom_stacks"
  },
  "readiness_feature_keys": {
    "stormstrike": "stormstrike_ready"
  }
}
```

For the SimC `auto_attack` control directive, explicitly supply a timestamped PRE observation, for example a `transitions` entry `{"timestamp_ms": 900, "key": "auto_attack_active", "value": 1}` and top-level `"control_feature_keys": {"auto_attack_active":"auto_attack_active"}`. If it is already active, the engine can continue to subsequent APL rows; if inactive it reports `AUTO_ATTACK_START_REQUIRED`, and if unobserved it reports `AUTO_ATTACK_STATE_UNKNOWN`. A synthetic `1` must never be mistaken for verified WCL evidence. Persistent precombat variables likewise need legitimate earlier state provenance; they are not auto-initialized from missing observations.

These bindings are illustrative. **Do not equate any such buff or readiness field with genuine WCL identity or Blizzard mechanics without independent verification.** Unmapped conditions and missing readiness remain `UNKNOWN`. State events with timestamps equal to or later than decision time are excluded.

## 3. Produce a priority candidate and trace

```powershell
python tools/research/simc_apl_priority_trace.py --model "C:\zrot\model.json" --snapshot "C:\zrot\snapshot.json" --output "C:\zrot\priority_trace.json"
```

Output status is `HYPOTHESIS_CANDIDATE`, `BLOCKED`, or `NO_DETERMINABLE_ACTION`. The output includes the source APL line, action token, reason, and decision trace. It **never** marks a gameplay rule as frozen or actionable.

Run `python tools/research/simc_apl_priority_trace.py --self-test` to check its offline fixtures.


## Additional input: complete readiness requirements (research-only)

The snapshot may include `"build_key"` and `"readiness_contract"`.
`tools/research/simc_apl_readiness_provider.py` derives candidate READY /
NOT_READY / UNKNOWN from **strictly earlier** observations.

Every action requires an explicit, provenance-linked policy for all eight
applicability dimensions: `ability_learned`, `cooldown_or_charge`,
`resource`, `gcd`, `cast_state`, `movement`, `range`, `target`.
Each dimension either has observed numeric predicates (ALL/ANY) or a documented
NOT_APPLICABLE waiver. Missing dimensions/observations produce UNKNOWN.
Policies are supplied by the caller and are **not automatically certified**
against Blizzard mechanics. A READY computed from a declared policy remains
research-only. The same action's contradictory observed readiness is rejected.

**Precombat variable boundary:** the runtime does not silently materialize
`actions.precombat` variable assignments. Values used later as
`variable.*` must be supplied as strictly earlier features or derived
independently from a verified precombat execution state. A source-only
`variable` declaration is not evidence that the initialization executed.

## Precombat APL variables → in-combat priority (research-only)

A `snapshot.json` can include `"precombat_replay"` with `"row_timeline"`
and `"source_transitions"`. The replay executes numeric `variable` operations
in **strictly increasing, negative precombat timestamps** and carries the
derived `variable.*` values into the later APL scan. Every precombat APL row
must have an externally attested `source_line`, `timestamp_ms`, `status`
(`EXECUTED` or `SKIPPED`) and `evidence_ref`; relevant state operands must
be provided with timestamps strictly before their respective variable rows.

This is **not** proof that a SimC precombat action executed, nor that the
assumed non-variable precombat actions produced the declared state changes.
When a row or operand is missing the replay stops with `BLOCKED` instead
of defaulting a variable to zero. Derived features are explicitly marked
`SOURCE_DERIVED_NOT_EMPIRICALLY_OBSERVED`, and the CLI output sets
`derived_variable_values_are_observed=false`. Do not feed these
hypothetical values into an independently discovered WCL candidate cohort
as if they were measured PRE combat states.

The standalone interface is:

```powershell
python tools/research/simc_apl_precombat_replay.py --model "C:\zrot\model.json" --timeline "C:\zrot\precombat_timeline.json" --out "C:\zrot\precombat_result.json"
```

The existing `simc_apl_priority_trace.py` consumes the same timeline
if included as `precombat_replay` inside its `--snapshot` input. A narrow native
performed-action parser exists; independent foreground classification and
actual native state-based per-event validation remain NOT RUN.

## Native SimC reference acquisition (local, private)

Run the actual SimC executable to collect the action log and the effective
APL together:

```powershell
python tools/research/simc_native_reference_capture.py --spec enhancement --profile "C:\simc\my_character.simc" --simc-bin "C:\simc\simc.exe" --out-dir "C:\zrot\simc_native_reference"
```

The script uses SimC's documented `log=1`, `log_spell_id=1`,
`save_actions` and `output` options. It writes a SHA256 receipt.
**It does not yet parse the log or validate action-by-action equivalence.**
This actual SimC run has **NOT RUN** on the user's PC in the current
GitHub-only verification. Keep these outputs private: logs can contain
character/gear details, and never commit them to this public repository.

## Native SimC performed-action events (local, private)

After `simc_native_reference_capture.py` creates the local reference folder,
the extracted action log can be converted into a hash-checked event list:

```powershell
python tools/research/simc_native_performed_events.py --reference-dir "C:\zrot\simc_native_reference" --out "C:\zrot\simc_native_events.json"
```

The parser reads the native receipt and validates the raw APL/log SHA256 and
byte counts before processing. Its narrow syntax is derived from official
SimulationCraft `action_t::execute()` and `sim_ostream_t` source at commit
`710c2408bfd3ae4df71b8cd55cdf01f63fd6c926`.
It recognizes only timestamped `performs Action '<token>' (<id>) (<resource>)`
lines. Unrecognized performed-action formats are reported as partial/blocked,
never silently counted as verified matches. A `performs` event can be an
autoattack, proc, background effect, or an actual foreground APL action:
**the parser does not yet determine which.** It is *not* a complete per-action
SimC prediction comparison, and actual native SimC execution remains NOT RUN
within this GitHub development session.

**Do not upload native action logs or character profile dumps to this public
repository.** Retain local outputs for later empirical comparison.

## Native SimC decision comparison — explicit PRE fixtures (research-only)

The local reusable comparison engine is:

```powershell
python tools/research/simc_native_oracle_reconciliation.py --reference-dir "C:\zrot\simc_native_reference" --cases-file "C:\zrot\simc_oracle_cases.json" --spec enhancement --build-key "caller_pinned_build" --out "C:\zrot\simc_oracle_replay.json"
```

Input `cases` must refer to an *existing hash-checked native performs event* by
`native_source_line`. For each case, include the exact native actor literal
(locally only), native event `decision_timestamp_ms`, pinned
`source_apl_sha256`, `spec_slug`, `build_key`, strict-PRE `transitions`,
`operand_to_feature`, and `readiness_feature_keys`.
Only events explicitly labeled `native_event_scope:
"CALLER_ATTESTED_FOREGROUND_APL"` with a `scope_evidence_ref` are eligible
for a provisional comparison; the label **is not independent certification**.
Other native performed events are excluded, not automatically called mistakes.

Output classes:
- `PROVISIONAL_MATCH` — exact native vs predicted action *token* match
- `PROVISIONAL_DIFFERENCE` — different tokens; action replacements,
  background effects and timing semantics are not yet controlled
- `UNKNOWN` — missing state, unreadiness, or unsupported APL semantics
- `EXCLUDED` — no relevant event or insufficient identity/foreground scope

This step does **not** extract PRE resource/cooldown/target state from native
logs, identify true APL-foreground casts, or validate token/spell identity.
It does not create gameplay rules. Native logs and local actor identities
must remain private and must not be uploaded to this public GitHub repository.
The only completed validation is **offline synthetic**, not actual local
SimulationCraft production.

## Native JSON2 action-state sequence

The native reference producer also requests \`report_details=1\` and \`json2\`,
creating \`simc_native_sequence.json\` alongside the existing text log and APL.
All three files are hash-pinned in the reference receipt.

\`\`\`powershell
python tools/research/simc_native_json_sequence.py --reference-dir "C:\zrot\simc_native_reference" --out "C:\zrot\simc_json2_sequence.json"
\`\`\`

This input separates \`action_sequence_precombat\` and \`action_sequence\`,
with action id/name/time, and available resources, buffs, cooldowns and
target snapshots. The SimC upstream basis is
\`simulationcraft/simc@710c2408bfd3ae4df71b8cd55cdf01f63fd6c926\`
(\`engine/report/json/report_json.cpp\`). It **does not assert that a snapshot
at time t is a Strict-PRE event at t**; observed snapshot equality and
foreground APL origin remain separate questions. Missing \`report_details\`
output, corrupted files, multiple actors and unsupported schemas fail closed.

This extractor is *not* yet connected as a verified state/readiness provider.
The JSON2 shape has been tested synthetically against the upstream C++ writer
structure, but **real local SimC production capture remains NOT RUN**.
Do not add private character/gear logs to the public repository.

## 4. Missing before engine completion

- Verify effective default APL exports from the current actual SimC binary across representative specs/builds.
- Complete SimC expressions, variable lifetimes, other non-GCD directives (auto-attack active-state handling is partial), `target_if` target selection, `pool_resource`, `sync`, `line_cd`, GCD and charge/cooldown readiness.
- Make source-state and readiness providers derive values from legitimate game/WCL/Blizzard sources instead of handcrafted snapshots.
- Build a multi-state conditional `IF/ELSE` model, then compare its predictions with SimC itself before WCL post-lock reconciliation.
- Verify with independent WCL holdouts and never inject SimC outputs into blind discovery before candidate lock.

**Operational authority:** `main`, FROZEN, CURRENT_STATE, Seq578 and Seq637 unchanged. This document does not confer MAIN promotion.
