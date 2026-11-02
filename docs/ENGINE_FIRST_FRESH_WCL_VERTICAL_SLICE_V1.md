> **Current product scope (user 2026-11-02):** [Machine-readable General Rotation + target-dummy trainer lock](PRODUCT_SCOPE_LOCK_V1.json) takes precedence over any earlier Encounter/raid/NSRT roadmap. SimC APL first, WCL high-ranker independent blind verification and correction, validated opener and IF/ELSE priority, then evidence-bounded dummy practice feedback. This document supplies **technical component evidence only**, not a separate product goal.

# Engine-First Fresh WCL Vertical Slice V1

## Goal

Prove that a newly collected public Warcraft Logs fight can be stored, interrupted, resumed, integrity-checked, and replayed as numeric/structural **Strict PRE** decision features **without requiring historical MAIN, Inbox, FROZEN source restoration or old snapshots**.

This is a development engine slice, **not** a completed General Rotation, blind candidate-lock system, SimC APL lane, real encounter rotation, or gameplay-ready release.

## Files

- `tools/engine_first/fresh_wcl_engine_v1.py` — isolated Python 3.12+ standard-library collector, checkpoint, replay and synthetic self-test.
- `tools/engine_first/test_fresh_wcl_engine_v1.py` — independent unittest and failure injection.
- `.github/workflows/zrot-engine-first-fresh-data-ci.yml` — offline CI on Python 3.12 / 3.14; never invokes WCL, SimC or gameplay entrypoints.

## How to execute

With PyCharm, **Run** on `fresh_wcl_engine_v1.py` with no Script Parameters runs the safe offline self-test.

Or from a command prompt:

```shell
python tools/engine_first/fresh_wcl_engine_v1.py self-test
python -m unittest discover -s tools/engine_first -p 'test_fresh_wcl_engine_v1.py' -v
```

**Optional explicit live collection** (public reports only; the account's own credentials must remain local):

```shell
python tools/engine_first/fresh_wcl_engine_v1.py collect --report YOUR_PUBLIC_REPORT_CODE --fight 1 --env /path/to/.env --max-pages 3
```

The report code and fight ID are real report identifiers, **not the boss encounter ID**. If a fight has a different id, replace `1` with its id. Nothing is collected when no `collect` command is provided.

`WCL_CLIENT_ID` and `WCL_CLIENT_SECRET` in local `.env` (aliases `WCL_ID` / `WCL_SECRET`) are loaded without printing secrets. Environment variables override local settings. The collector uses WCL's official OAuth2 client-credentials endpoint and public GraphQL API. Private reports require separately authorized user OAuth and **are not supported by this slice**.

The output defaults to `tools/engine_first/snapshots/<code>/fight_<id>/`, and can be overridden with `--out`.

After a **completed** collection:

```shell
python tools/engine_first/fresh_wcl_engine_v1.py replay --folder tools/engine_first/snapshots/YOUR_PUBLIC_REPORT_CODE/fight_1
```

The replay prints JSON containing numeric-only cast decisions, previously observed auras, unknown cooldown/readiness, and deterministic replay SHA256. Redirect output to a file if needed.

## Concrete acceptance behavior

- Cold start requires no old cache.
- Report `revision` is pinned, so later re-export stops incremental reuse.
- Each event page is atomically persisted with checksum and a separate checkpoint; all committed pages are checked before resume/replay.
- A page written just before a crash but not yet entered into the checkpoint can be adopted after validating its cursor, payload and consistency, avoiding repeated API page consumption.
- Corrupted pages, orphan gaps, non-monotonic `nextPageTimestamp`, incomplete snapshots or invalid fight windows stop without inventing data.
- Strict PRE builds actor+numeric-aura state only from transitions with timestamps strictly earlier than the cast; same-timestamp transitions cannot leak.
- Explicit `removebuffstack(stack=0)` = absent; missing stack count = unknown. An actor or ability never observed does not become known absent.
- WCL localized names are never runtime identity.
- No SimC labels are injected; no WCL independent candidate is locked in this slice.

## Known limits and next development

1. **API contract:** Query fields were checked against publicly available WCL schema docs as of 2026-11-02, but *actual live WCL production has NOT been run* for this revision. Client-credentials only supports public report scope. API rate/point behavior is not verified in production.
2. **Data privacy:** raw WCL pages can contain actor names and report information; keep local snapshots out of public GitHub.
3. **Coverage:** source/target identity and auras are partial. `readiness=UNKNOWN` is correct until resource/cooldown and actor-state observability are actually reconstructed; no fake pairwise priority.
4. **Snapshot changes:** a report revision change is a fail-closed condition; create a new snapshot directory or later implement versioned snapshots. This candidate does not silently mutate old evidence.
5. **Pagination:** page caps prevent uncontrolled collection per invocation; sequential reruns resume. Rate-limit budgeting, backoff and proactive points policy remain upcoming engineering work.
6. **Proof scope:** The test has 21 synthetic end-to-end checks and independent defensive tests, not high-level gameplay accuracy. Source replay and WCL/SimC hypothesis comparison are separate future steps.

## Roadmap

- V1: fresh collector + atomic snapshot + resume + deterministic Strict PRE replay (**this candidate**).
- V2: WCL API live smoke with user's own credentials on one new public fight, budget guard, revision-safe checkpoint and recovery validation.
- V3: observability/readiness state model and generic numeric/structural WCL blind candidate lock.
- Parallel: independent SimC APL/profile semantic bootstrap, no information shared with WCL blind lane until candidate lock.
- V4: post-lock compare, counterfactual/holdout when impactful, conditional action IR, second spec/encounter generality fixture.

See [Engine-First Charter](ENGINE_FIRST_REPRODUCIBLE_RESEARCH_CHARTER_20261102.md). Only MAIN may promote current shared state, production pointer or FROZEN claims.
