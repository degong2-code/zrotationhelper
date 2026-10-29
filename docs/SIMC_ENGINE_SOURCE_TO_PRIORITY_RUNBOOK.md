# SimC Rotation Research Engine — local source-to-priority execution (branch pilot)

**Status:** Research-only. Produces a conditional **action hypothesis**, not a validated General Rotation or a gameplay recommendation. No specialization, boss, or historical test cohort is hardcoded.

## 1. Export the specialization's effective APL

With a real local SimulationCraft executable and an appropriate single-actor profile:

```powershell
python tools/research/simc_apl_source_engine.py --spec enhancement --profile "C:\simc\my_character.simc" --simc-bin "C:\simc\simc.exe" --out "C:\zrot\model.json"
```

The `--spec` value must match the profile's exact SimC specialization name. The importer hashes the **profile**, the **effective APL** and the **local SimC executable**. Existing exported action lists can instead be ingested with `--actions-file` (this does **not** independently verify the original profile/build).

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

These bindings are illustrative. **Do not equate any such buff or readiness field with genuine WCL identity or Blizzard mechanics without independent verification.** Unmapped conditions and missing readiness remain `UNKNOWN`. State events with timestamps equal to or later than decision time are excluded.

## 3. Produce a priority candidate and trace

```powershell
python tools/research/simc_apl_priority_trace.py --model "C:\zrot\model.json" --snapshot "C:\zrot\snapshot.json" --output "C:\zrot\priority_trace.json"
```

Output status is `HYPOTHESIS_CANDIDATE`, `BLOCKED`, or `NO_DETERMINABLE_ACTION`. The output includes the source APL line, action token, reason, and decision trace. It **never** marks a gameplay rule as frozen or actionable.

Run `python tools/research/simc_apl_priority_trace.py --self-test` to check its offline fixtures.

## 4. Missing before engine completion

- Verify effective default APL exports from the current actual SimC binary across representative specs/builds.
- Complete SimC expressions, variable lifetimes, non-GCD directives, `target_if` target selection, `pool_resource`, `sync`, `line_cd`, GCD and charge/cooldown readiness.
- Make source-state and readiness providers derive values from legitimate game/WCL/Blizzard sources instead of handcrafted snapshots.
- Build a multi-state conditional `IF/ELSE` model, then compare its predictions with SimC itself before WCL post-lock reconciliation.
- Verify with independent WCL holdouts and never inject SimC outputs into blind discovery before candidate lock.

**Operational authority:** `main`, FROZEN, CURRENT_STATE, Seq578 and Seq637 unchanged. This document does not confer MAIN promotion.
