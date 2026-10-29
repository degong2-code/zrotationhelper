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

The snapshot may include \`"build_key"\` and \`"readiness_contract"\`.
\`tools/research/simc_apl_readiness_provider.py\` derives candidate READY /
NOT_READY / UNKNOWN from **strictly earlier** observations.

Every action requires an explicit, provenance-linked policy for all eight
applicability dimensions: \`ability_learned\`, \`cooldown_or_charge\`,
\`resource\`, \`gcd\`, \`cast_state\`, \`movement\`, \`range\`, \`target\`.
Each dimension either has observed numeric predicates (ALL/ANY) or a documented
NOT_APPLICABLE waiver. Missing dimensions/observations produce UNKNOWN.
Policies are supplied by the caller and are **not automatically certified**
against Blizzard mechanics. A READY computed from a declared policy remains
research-only. The same action's contradictory observed readiness is rejected.

**Precombat variable boundary:** the runtime does not silently materialize
\`actions.precombat\` variable assignments. Values used later as
\`variable.*\` must be supplied as strictly earlier features or derived
independently from a verified precombat execution state. A source-only
\`variable\` declaration is not evidence that the initialization executed.

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
if included as `precombat_replay` inside its `--snapshot` input. Native
SimC-log format parsing and actual per-event trace validation remain NOT RUN.

## Native SimC reference acquisition (local, private)

Run the actual SimC executable to collect the action log and the effective
APL together:

\`\`\`powershell
python tools/research/simc_native_reference_capture.py --spec enhancement --profile "C:\simc\my_character.simc" --simc-bin "C:\simc\simc.exe" --out-dir "C:\zrot\simc_native_reference"
\`\`\`

The script uses SimC's documented \`log=1\`, \`log_spell_id=1\`,
\`save_actions\` and \`output\` options. It writes a SHA256 receipt.
**It does not yet parse the log or validate action-by-action equivalence.**
This actual SimC run has **NOT RUN** on the user's PC in the current
GitHub-only verification. Keep these outputs private: logs can contain
character/gear details, and never commit them to this public repository.

## 4. Missing before engine completion

- Verify effective default APL exports from the current actual SimC binary across representative specs/builds.
- Complete SimC expressions, variable lifetimes, other non-GCD directives (auto-attack active-state handling is partial), `target_if` target selection, `pool_resource`, `sync`, `line_cd`, GCD and charge/cooldown readiness.
- Make source-state and readiness providers derive values from legitimate game/WCL/Blizzard sources instead of handcrafted snapshots.
- Build a multi-state conditional `IF/ELSE` model, then compare its predictions with SimC itself before WCL post-lock reconciliation.
- Verify with independent WCL holdouts and never inject SimC outputs into blind discovery before candidate lock.

**Operational authority:** `main`, FROZEN, CURRENT_STATE, Seq578 and Seq637 unchanged. This document does not confer MAIN promotion.
