# BR-SIMC-APL-BOOTSTRAP — V14 self-validation correction and branch handoff

Date: 2026-10-31 KST. Branch ownership only.
No MAIN/General Rotation/FROZEN/production pointer promotion.

## Restore and evidence order
1. This V14 handoff and BRANCH-ONLY LATEST_HANDOFF.json.
2. docs/BR_SIMC_NATIVE_V12_PORTABLE_CORRECTION_20261031.json
   (source row independent recalc + original/corrected bytes hashes).
3. Source V12 full-row evidence, V13 two identity hypotheses,
   V9 completeness note; previously V7 native real source proof.
4. Recover authoritative MAIN CURRENT_STATE/Runtime/active manifest
   independently, plus dual-lane Core Contract, successor Playbook,
   and Parallel Workstream Contract. Do not infer MAIN state from
   GitHub main HEAD.

## Actual V14 work: correction after independent review

V13 final offline CI run 41102726023 was rechecked COMPLETED/SUCCESS
on branch HEAD 7a63e0dea3550e58b679209d378f99cb7f48a2f5.
V13 SHA pointers matched.

Independently inspected the original distributed V12 portable replay:
the legacy Python return field `positive_ids` accidentally used
dict comprehension over owner key (APL list, ordinal, native ID);
identical positive IDs in multiple rows retained only the last
entry rather than a sum. The `if_by_apl_row` original raw marker
source data was NOT affected.

The original V12 portable JSON had invalid convenience sums:
- Fury sum positive source object IF evals 164; true 343;
  native source Rampage ID 184367 reported 7; true 169;
  5308 3->19, 385059 1->2.
- Havoc sum positive source object IF evals 294; true 463;
  Felblade 232893 3->34; 201427 44->96;
  258860 1->5; 258920 20->102.
- Zero-ID 83 Fury + 1286 Havoc unchanged.
- Total original IF guard scopes 426 + 1749 = 2175 unchanged.

The branch V12 full-row evidence JSON git blob
fabe13596b4fbf5b30af64c5b4581b204db1f259
already had correct per-source-row counts and combined summary.
It was independently re-aggregated from all 37 observed
source (list,ordinal,ID) groups to confirm true totals;
no overwrite or V12 source evidence mutation was necessary.

Corrected the actual standalone portable Python by using
Counter + additive increments keyed by positive action_t ID.
Added explicit synthetic regression for the duplicate-ID
multiple APL rows case, assertions reconciling every ID total
to its source rows, zero+positive to overall IF counts,
and each IF TRUE+FALSE to its owner row count.
The corrected portable bundle contains exact original
archived V7 source ZIP, corrected Python, corrected JSON,
legacy JSON marked INVALID SUMMARY, README, receipt, SHA256SUMS.

### Validation levels explicitly separated
- Corrected Python final file compile: PASS.
- Corrected Python --self-test actual raw ZIP: PASS.
- Duplicate-ID / tampered action scope synthetic: PASS.
- Full 2175 original IF source marker replay/hash: PASS.
- Corrected JSON vs prior V12 JSON: PASS, only the erroneous
  derived positive_ids mapping changed.
- Exact corrected portable ZIP extract, SHA256SUMS and
  contained script compile/self-test/reproduced JSON byte
  identity: PASS.
- Independently recalc source GitHub V12 all-row evidence:
  PASS, positive 343/463, zero 83/1286.
- Actual live WCL/SimC rerun/current Blizzard client: NOT RUN.
- MAIN source-complete identity readiness approval: BLOCKED.
- WCL independent candidate lock: NOT RUN in this branch.

Corrected portable script SHA256:
1db610ccd35d3b054c9e94d7d9ee53c314f14f9e7b9d1fed6437d35023b8958f
Corrected portable JSON SHA256:
b668fce4619f01dc0615b8202f3d858a814e8722e1d7aee99f84d2df2a39b215
Corrected package ZIP SHA256:
a919566a860ee1625228b9cdf68ec36d80dd65418670917c5e5bc4e63a65a329
Original V7 marker ZIP SHA256:
da88d27ea027b2eacaa6675c9ee22afdffa8a307852ab21b661dabdbb2faab3e

The initial V12 bundle is preserved as historical failure
evidence and MUST NOT be used for positive_ids aggregates.
Corrected bundle linked from current ChatGPT conversation;
raw bytes not committed to GitHub history.

## External identity risk: separate from this numeric correction

V13 external ID candidates from Wowhead/other databases and
official Blizzard mechanic descriptions remain candidate only.
Public Wowhead Felblade ID 232893 lists 'Not an Action' flag,
and other Felblade IDs 236167 (proc aura), 472802 (different
spell) use the same displayed name. Do not deduce actionbar
or WCL cast identity solely from SimC source action_t ID
or localized text. The flag alone is not an authoritative
conclusion about game button actionability either.

No current client known spell/cast ID parity, exact dynamic
cost, Strict PRE readiness or user IF/ELSE rules certified.
READY 0/90; gameplay rules 0; client game IDs 0. Independent
WCL candidate lock still required before cross-lane replay.

## Exact next and ownership

Current source ID counting evidence is now internally consistent;
stop redundant provenance loops. MAIN needs to approve the
source-complete SpecAdapter readiness/identity binding and
current approved Runtime/CURRENT_STATE and focused merge review.
WCL blind owner must independently discover/lock numeric
action candidates and Strict PRE readiness/UNKNOWN evidence
WITHOUT receiving SimC IDs, guards or names before lock.
Only V8 blind-safe generic request can cross pre-lock.

cross_branch_dependency: MAIN needs to approve/implement
the source-complete numeric game ability and readiness
interface, perform source byte+mechanic validation.
cross_branch_dependency: WCL owner needs independent
candidate/threshold lock before SimC reconciliation.

Owner BRANCH, no shared state modification; Seq578/FROZEN
unchanged, Seq637 UNKNOWN. Local PyCharm action NONE.
