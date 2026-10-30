# Developer Note — Strict PRE raw-event producer and independent audit

Date: 2026-10-30. Owner: research branch only. Not a MAIN/FROZEN promotion.

## Purpose
The generic zRotationHelper engine must automatically ingest any pinned SimC APL/profile, derive conditional hypotheses, and later compare them with independently locked blind WCL discoveries. Earlier Strict PRE tests used explicit caller-declared transition ledgers with unverified producer/evidence strings. This step adds byte-addressed raw event evidence and an independently implemented recalculation check, without rewriting the existing APL/condition/readiness engine.

## Implementation
- tools/research/simc_raw_transition_adapter.py accepts a bounded UTF-8 NDJSON stream containing only typed FEATURE_TRANSITION rows. The capture receipt pins the exact APL/spec/profile/executable identities, byte count and SHA256. Each row requires event ID, timestamp, sequence, feature key, numeric value, scope and validity. A record is never synthesized from a SimC action_sequence snapshot.
- The adapter derives producer and evidence references from the original raw file hash and individual line number, offset and hash. It passes an exact source-derived ledger to the existing simc_strict_pre_source_bridge.py, which delegates to StrictPreStateProvider and the shared trace_priority.
- tools/research/simc_raw_transition_independent_audit.py re-parses the original bytes separately, reprojects every expected transition, reconstructs line receipts and recalculates the ledger digest without invoking producer routines. It rejects altered event values, fabricated line receipts, altered ledger hashes and unauthorized READY claims.
- Provenance classes remain SYNTHETIC_TEST or EXTERNAL_CALLER_DECLARED_UNVERIFIED, never independently verified. No actual WCL/Native API collector has been authenticated. The produced event receipt is byte-backed, not authority-certified.
- Strict PRE accepts source-declared valid timestamps strictly earlier than the decision; same-time/future/invalid events are excluded and recorded. No synthetic READY is injected by the raw adapter. Unbound conditions and action readiness remain UNKNOWN.
- TARGET scope is currently rejected because no target subject identity/instance has been provided; mixed ACTOR/ENCOUNTER records sharing one feature key fail closed. A future source-subject identity schema is required to prevent target-switch and namespace leakage.

## Evidence and tests
Source coverage CI: https://github.com/degong2-code/zrotationhelper/actions/runs/41021457247 — SUCCESS. Three synthetic source adapter spec labels and three independent audit test labels passed. Negative regression cases cover raw capture SHA, duplicate/missing event IDs, non-transition snapshot type, falsified source authority, unqualified target identity, scope collision, transition mutation, line receipt tampering, ledger SHA tampering and unauthorized readiness. Four real upstream SimC APL source profiles (Enhancement, Fury, Unholy, Havoc) were processed with only a synthetic unrelated event, and all correctly BLOCKED without recommendations. The existing 28-case graph-to-runtime synthetic regression was retained.

Offline CI: https://github.com/degong2-code/zrotationhelper/actions/runs/41021457101 — Python 3.12/3.14 final job status to be independently verified before PASS is claimed. No new native C++ build was necessary for raw ingestion tests.

## Critical claim boundary
Exact agreement between raw bytes and output ledger is NOT proof that the raw stream is from the official WCL API, Blizzard or SimulationCraft. The capture and raw bytes are caller controlled. Actual native decision-time states have NOT been collected and current Retail Blizzard mechanics have NOT been independently verified. The 206 previously validated native SELECT_ACTION_FOREGROUND event origins cannot yet be replayed against their own trusted PRE states. Do not invent a t-1 timestamp for any JSON2 action snapshot or promote a gameplay rule from these tests.

## Exact Next
1. Build one trusted official source producer: native SimC feature-transition instrumentation with genuine timestamps and action source identity, or an official WCL raw event collector with independently authenticated response metadata. Respect WCL blind candidate lock; do not inject SimC hypotheses into blind discovery.
2. Reconcile source event semantics and identity against Blizzard/SimC mechanics; add actor/target subject identifiers and prevent stale target state leakage.
3. Replay certified strictly-before-decision state with the existing shared APL evaluator; separate match, conflict, missing readiness, unknown and unsupported semantics and test independent holdouts.
4. MAIN alone may promote canonical product state after compatibility review. FROZEN, Seq578 and global LATEST_HANDOFF remain unchanged; Seq637 is UNKNOWN.
