# WCL independent-lane observability request — BLIND SAFE

Owner: BR-SIMC-APL-BOOTSTRAP, proposed dependency to WCL discovery owner.
Status: **REQUEST ONLY**; not an instruction to run or a locked candidate.
No SimC source rows, ability names, talent thresholds, specific actions,
expected results or rankings are provided here. Do not expose the
separate SimC readiness manifest to blind discovery before candidate lock.

## Requested independent evidence by actor/action/target identity

For each **eligible** action opportunity in a discovery cohort, retain:

- Raw evidence provenance: report/fight identity, difficulty, eligible
  target availability, actor and target numeric identities, spec/build
  identity if observable, action numeric identity and timing.
- Strict PRE states for resource amount/maximum, cooldown/charges,
  applicable buffs/debuffs, movement/range, target and cast state,
  equipment/talent requirements where actually observable.
- Readiness quality per dimension: OBSERVED, derivable only with a
  frozen mechanic and source evidence, or UNKNOWN. Absence of casts
  or delayed cooldown is not evidence of NOT_READY/hold.
- Reset epoch and event ordering: only source transitions with
  timestamp strictly earlier than decision; no future/same-time
  readiness leakage.
- Priority confounders: preceding action options, on-/off-GCD context,
  composition, target switching, fight remains, downtime, resource
  pooling, cooldown sync, padding and strategy-family grouping.
- Lock candidate action identities, rule conditions, thresholds,
  cohort and proposed holdout **before** any SimC hypothesis is shared.
  Preserve raw events and source receipts for independent replay.

## Missing data protocol

If cooldown availability, equipment, movement, targeted action
affordability or identity cannot be reconstructed from WCL/Blizzard
source evidence, label UNKNOWN and return it as an observability
blocker. Never infer readiness from silence, target damage, spell name
or post-action state. Do not fill values using SimC answers.

## Integration boundary

After blind candidate lock, MAIN may arrange a post-lock comparison
to a separately maintained, pinned SimC action+readiness hypothesis
and official Blizzard mechanics. The WCL owner does not promote MAIN,
FROZEN or General Rotation. No API collection or live WCL run has
occurred from this request.

cross_branch_dependency: WCL owner needs to supply independently
locked candidate + Strict PRE coverage/UNKNOWN classification before
comparison.
