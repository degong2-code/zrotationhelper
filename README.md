# zRotationHelper — CURRENT USER-APPROVED PRODUCT GOAL (2026-11-02)

> **Complete the General Rotation OPENER and verified IF/ELSE spell priority**, then help users correct their rotation while practicing on a target dummy. Initial hypothesis comes from **SimC APL/profile**, verified and corrected using **high-ranking WCL player logs**, with independent blind WCL candidate lock before receiving SimC answers. Practice feedback is live only when supported WoW APIs reveal enough evidence; otherwise use post-session combat-log analysis.

**NOT product targets:** raid execution, encounter-specific boss rotation plans, NSRT, HTML raid timelines or boss guide export. Raid logs may be reused as **general ST / two-target / AoE evidence**. Historical files and CI bootstrap descriptions below are NOT the current roadmap.

## 처음 방문한 개발자를 위한 탐색

**현재 개발 기록과 실증 코드는 GitHub 기본 `main`이 아니라 격리 브랜치 `work/gr-simc-st-2t-wcl-blind-20261102`에 있습니다.** MAIN으로의 제품 승격은 아직 승인되지 않았습니다.

| 무엇을 알고 싶은가 | 바로가기 |
| --- | --- |
| **연구 전체 지도 / 권장 읽기 순서** | [연구·개발 탐색 시작점](docs/RESEARCH_INDEX.md) |
| 현재까지 구현·검증·미완료 | [현재 연구 상태](docs/CURRENT_RESEARCH_STATUS.md) |
| 과거에 왜 만들었고 어떻게 개선했나 | [기능별 개발 이력](docs/FEATURE_HISTORY_INDEX.md) |
| 기능별 코드·원본 증거·Actions 검증 | [증거 및 CI 지도](docs/EVIDENCE_NAVIGATION_INDEX.md) |
| 날짜별 상세 원문 기록 | [기존 기능별 재사용 인덱스](docs/branches/BR-GR-ST2T-WCL-BLIND-20261102/FEATURE_EVIDENCE_REUSE_INDEX_20261105.md) |
| 새 채팅용 최신 인계 | [branch-local LATEST_HANDOFF.json](_UPLOAD_TO_CHATGPT/branches/BR-GR-ST2T-WCL-BLIND-20261102/LATEST_HANDOFF.json) |

과거 코드·증거·인계는 삭제하거나 재배치하지 않았습니다. 상단 탐색 문서는 **짧은 연결 지도**이며, 전문화별 General Rotation 정확도 검증 및 사용자 허수아비 피드백의 완료 선언이 아닙니다.

**Mandatory read-first (including any future chat / handoff):**
1. [Machine-readable user scope lock](docs/PRODUCT_SCOPE_LOCK_V1.json)
2. [Full official scope declaration](docs/PRODUCT_SCOPE_GENERAL_ROTATION_DUMMY_TRAINER_20261102.md)
3. [Agent instructions](AGENTS.md) + [Engine-First Charter](docs/ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md)
4. [Five-or-more-handoff protocol](docs/HANDOFF_CONTINUITY_PROTOCOL_V1.md) + [new chat boot prompt](handoff/NEW_CHAT_BOOT_PROMPT.md)
5. The newest verified branch-local `LATEST_HANDOFF.json` for the task at hand. Historic handoffs are evidence, not scope authority.

**Continuity check:** `python tools/governance/validate_scope_continuity_v1.py --validate` then `--self-test`. The test simulates five *future* handoffs and must not be reported as five real handoffs.

The source of truth is the **explicit user scope decision**, not a previous assistant-generated plan. Only the MAIN integration owner can promote shared project state; this branch records the approved goal without rewriting FROZEN or global pointers.

---

## Archived development/CI bootstrap description (historical context)

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

## Cross-spec runtime bridge smoke

The bootstrap CI also executes a small synthetic **Enhancement/Fury** integration:
SpecAdapter action families and declared features feed StrictPreStateProvider
(strictly earlier events only), GeneralRotationEvaluator, and BehavioralEvaluator.
It checks upgraded ability-family normalization, UNKNOWN readiness exclusion, and
UNOBSERVABLE state exclusion. The readiness and state inputs are **synthetic**;
there is no O4 live WCL stream, independently verified primitive allowlist, or
gameplay/optimality claim. The existing WAVE3 15-check scaffold was reviewed
locally but its project-bound execution/manifest is **not** deployed by this
bootstrap.

## Native aura / O4 boundary smoke

A byte-identical `core/coverage.py` joins the selected bootstrap source.
One offline synthetic test now checks WCL-shaped aura event identities into
`AuraIdIndex` (strictly earlier transitions only), then synthetic General
Rotation decisions and semantic MASK precedence. This is **not** the full O4
`prestate_coverage.py` producer, O1/O3 artifact validation, WCL ingestion,
or game-optimality proof. O4 runtime dependencies and authoritative input
manifests must be migrated and independently tested before a runnable
Windows product baseline can be claimed.
