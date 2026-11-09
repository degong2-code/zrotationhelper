# Actual SimC selected-row condition PRE validation — 2026-11-09

Policy: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`. Owner: isolated `BR-GR-ST2T-WCL-BLIND-20261102`; MAIN/FROZEN unchanged.

## Actual E2E

CI [#42573758563](https://github.com/degong2-code/zrotationhelper/actions/runs/42573758563) **3/3 PASS**. Original official SimC `b522cded8c26b97dac03fdf56e57a03ec7e8faa6`. Original Fury/Mage MID2, ST and 2 target each, 30-second action sample, seed=31459. The modified single original SimC binary was built once. Python3.12/3.14 synthetic/compile PASS.

The `simc_original_select_if_pre_witness_v1.py` source witness is passive: C++ select_action obtains call ID and direct source actor resource plus named buff before original action_ready(). The original action_ready() `if_expr->success()` is called once only, emitting native Boolean comparator with identical action pointer+call ID if reached. The independent AST replay uses only original same-call C++ PRE raw state. Fury fields were selected via source-pinned SpecAdapter (original code for warrior Recklessness buff construction, RESOURCE_RAGE).

| Case | Original JSON2 action samples unchanged | Exact source IF AST/native original matches | Initial 10 s matched |
|---|---:|---:|---:|
| Fury ST | 43 | 58 | 10 |
| Fury 2T | 44 | 2 | 2 |
| Arcane ST | 30 | 0 (Fury fields not applicable) | 0 |
| Arcane 2T | 32 | 0 (Fury fields not applicable) | 0 |
| **Total** | **149/149** | **60** | **12** |

**Cautions:** AST known but native IF was not evaluated in original call: Fury ST 236, Fury 2T 67. Neither NOT_READY nor IF false is inferred from this. An action can have no explicit APL IF but still fail native readiness. Matching original native IF is not proof of global priority or simultaneous competitor readiness. Selected source root to JSON2 emission causal match still unknown. WCL independent holdout not run. Target dummy error verdict UNKNOWN.

## Evidence identities

- Code `tools/research/simc_original_select_if_pre_witness_v1.py` SHA256 `9dc29736ec9dca355efb8cf29cb45102f448cedb840e5f6ec696178f2355f49d`.
- Actual native source patch receipt sha256 `ce911273cb9a382ae2e123437f4a94f6a59a1c93a6d3e4c461dea19a49e5e8e5`.
- Case output JSON SHA256: Fury ST `4454b21a9fa3699d6f06c3803880bde69352b7383be3ff042b4fe67d1ecc2ccd`, Fury 2T `82824b9fb3732e641620cf9c917f954e89dc526777d01c9d0e1c777843ee756c`, Arcane ST `a17d90153789e853fc8baf067ac407964f906a45e5ff4740c1de4b9802530600`, Arcane 2T `c95f01fbbd29d3389ca57c86444808d0977fde4040142adc8191b4d1d33a7717`.
- Artifact #13654636939 `zrot-simc-original-same-call-source-if-pre-v1`, zip digest `sha256:29fe90ae0433965513d79556e1d40199bc5e295d59ac0f48ef88acc56ebe27b4`, scheduled 2026-11-16 expiry. Generator code/source pins remain in repo for regeneration.

## Next precise steps

Develop a minimal original same-run select-root→JSON2-emitter identity witness without action/time-only or timestamp-pair leakage. Extend source-pinned SpecAdapter only where Arcane state is material to original APL IF (e.g. `buff.arcane_salvo.stack`, `variable.aoe_count`), then build a conditional IF/ELSE replay with competitor readiness UNKNOWN until source evidence closes its significant gates. Test ST/2T/AoE transitions and opener-ending states before WCL blind holdout. Do not expand to Encounter/NSRT.
