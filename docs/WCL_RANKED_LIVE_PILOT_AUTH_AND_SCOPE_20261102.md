# WCL ranked-Fury live pilot — only approved missing external dependency

Policy ID: `ZROT_GENERAL_ROTATION_OPENER_DUMMY_TRAINER_20261102_V1`  
Owner: isolated research branch `work/gr-wcl-ranker-live-coldstart-20261102`.  
Product target: validated General Rotation opener and conditional priorities + lightweight target-dummy feedback. **No Encounter Plan, live raid helper, NSRT.**

## Results actually verified (2026-11-02)

- GH Actions `zrot-live-wcl-ranker-preflight` run **41429553206**: compiler, synthetic ranker selection and player identity PASS. The workflow's actual WCL API preflight returned `BLOCKED_MISSING_WCL_CLIENT_CREDENTIALS_IN_ACTIONS`, WCL API calls **0**.
- GH Actions `zrot-live-ranked-wcl-fresh-pilot` run **41429991816**: synthetic full E2E ranker selection → unique report/fight/player mapping → fresh WCL snapshot → Strict PRE → numeric-only blind candidate lock **PASS**. Live status again `BLOCKED_MISSING_WCL_CLIENT_CREDENTIALS_IN_ACTIONS`, collected events **0**, real candidate lock **NOT CREATED**.
- GH Actions `zrot-wcl-ranker-scope-chain` run **41430316187**: product-scope invariants, 5 simulated handoffs + 14 negative cases PASS.
- WCL public API OAuth must use **HTTP Basic** `client_id:client_secret` and `grant_type=client_credentials` form data, per official WCL docs. Client token is never uploaded. 2026-11-02 final code change aligned the preflight transport with this contract.

No claim that top-ranked Fury actor/build, full WCL ready state, ST-vs-2T cast priority, or actual WCL API production has been validated.

## User action: repository secrets, never in chat

1. In the user's Warcraft Logs API client management, copy their existing **Client ID** and **Client Secret**. Create a client only if needed. Official docs: `https://www.warcraftlogs.com/api/docs`.
2. In GitHub, open **`degong2-code/zrotationhelper` → Settings → Secrets and variables → Actions → Repository secrets → New repository secret**.
3. Store exact two names, **`WCL_CLIENT_ID`** and **`WCL_CLIENT_SECRET`**, each with the matching value. Never put values in GitHub source, issues, workflow YAML, CLI examples, ChatGPT messages, uploaded files, or screenshots.
4. Open GH Actions [run #41429991816](https://github.com/degong2-code/zrotationhelper/actions/runs/41429991816), select **Re-run all jobs** after secrets exist (or ask the assistant to commit a follow-up on the same branch to trigger a fresh `push` run).
5. Read the actual receipt status and stop at the earliest evidence failure. Green GH run does not prove WCL production; `BLOCKED_*` must remain BLOCKED.

**Important:** Use *this repository*. Other project's secrets, local `.env`, user private data and GitHub PAT are not automatically available to this workflow. GitHub Actions must be enabled for the repo.

## Fixed live pilot limits

- Public WCL API `/api/v2/client`, OAuth client credentials. No private report grant or cookie/browser bypass.
- 1 top-ranked Fury Warrior fight (Heroic difficulty=4), first metadata discovery through official `worldData.zones` and `Encounter.characterRankings` under the `Voidspire` raid-zone matching rule.
- Numeric actor match against the **same report/fight** and player/class masterData; reject duplicates/partial identity.
- Same revision during metadata selection and fresh snapshot collection.
- No more than **6 event pages** in the initial pilot (API point behavior must be observed; no unlimited retry).
- If full snapshot exists, Strict PRE with timestamp `<` cast timestamp; actor-only numeric blind candidate lock before any SimC semantic comparison.
- If snapshot is partial or readiness unavailable, mark UNKNOWN/PARTIAL instead of a completed proof. WCL frequency alone proves neither priority nor optimality.
- Artifacts contain sanitized receipts only; bearer token, character names and full raw WCL event files are not published. Future deterministic replay persistence must be added with a scoped data-retention policy.

## Exact next once secret is active

Run one official high-ranked fresh WCL pilot and compare its record identity and timestamp/revision bounds; validate whether masterData and ranks have the required shape, then capture *real* actor-scoped opener decisions and numeric candidate lock. Only after candidate lock introduce SimC Fury 1T/2T opener hypothesis for post-lock replay. HOLD OUT a separate set of real reports before claiming a user-facing General Rotation rule.
