# zRotationHelper — offline CI bootstrap (candidate)

This repository snapshot is a **development/CI experiment**, not the complete WoW Rotation Helper product or an authoritative gameplay baseline. Its eight source/contract files are copied byte-for-byte from a selected local Windows Source Snapshot. No Warcraft Logs, Blizzard API or SimulationCraft credentials, reports, raw evidence or local deployment state are included.

## CI purpose

The sole workflow runs on designated branch pushes and tests Python **3.12** and **3.14** independently. It checks syntax, generic evaluator synthetic regression, strict-PRE state handling, readiness unknown isolation, cross-spec synthetic self-test and contract shape. The test suite uses Python's standard library and makes **no external service requests**. It never invokes the project's MAIN launcher, a production collector, or the FEX full execution route.

Run locally from repository root:

```text
python -B tools/ci_offline.py
```

Machine-readable results are written to `ci_artifacts/ci_receipt.json` and `ci_artifacts/source_sha256.txt`, and are excluded from git commits. GitHub Actions uploads these short receipts in each Python matrix job. Receipts record GitHub commit SHA when GitHub supplies it, and the actual interpreter version. An offline PASS is **not** a Windows/SimC/WCL production PASS or a Seq637 result.

## Authoritative project boundary

Seq637: UNKNOWN. Seq578: quarantined/unchanged. Existing FROZEN artifacts, CURRENT_STATE, lifecycle locks, and MAIN-only promotion remain unchanged. Product-source baseline promotion is explicitly **not** granted by this repository bootstrap.

## Publication scope

No private personal paths, WCL credentials, evidence bundles, private logs, old branches, migration staging files, or unreviewed contracts should be committed. A targeted heuristic scan passed on the initial eight files, but it cannot certify the absence of every secret or third-party right. Review all files and repository settings **before any public push**.

No open-source license is included in this bootstrap draft; public visibility alone is not an open-source license. Choose and approve a license separately if open-source reuse is intended.
## CI execution smoke trigger

This branch-only README update is a deliberate push event after the workflow file was installed. The expected checks are offline Python 3.12 and 3.14; results remain unverified until the actual GitHub Actions jobs and receipts are inspected. No product-source or authoritative-state files are changed.

## SpecAdapter structural smoke (second source batch)

The eight verbatim `raid_dps/specs/` sources are published here for **structural smoke tests only**. Three adapters (Enhancement Stormbringer, Fury Slayer, Unholy Golden Fixture) are importable and checked for declaration consistency. Primitive allowlists in this bootstrap test are **self-derived**, not independently loaded from the frozen onboarding contract. Their `frozen_evidence_ids()` methods preserve pre-existing labels; this repository does **not** validate or promote those evidence claims. WCL readiness, ability identities, gameplay priority, and Seq637 remain unvalidated here.
