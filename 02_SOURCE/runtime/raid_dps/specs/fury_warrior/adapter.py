#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fury Warrior / Slayer SpecAdapter.

This package contains specialization semantics only.
No network, cohort, evidence-threshold, or renderer logic belongs here.
"""

from __future__ import annotations

from raid_dps.specs.protocol import (
    ActionFamilyDef,
    ActionOverrideDef,
    StateFeatureDef,
)


class FurySlayerAdapter:
    spec_slug = "fury_warrior_slayer"
    class_name = "Warrior"
    spec_name = "Fury"
    variant = "Slayer"

    def action_families(self):
        return (
            ActionFamilyDef(
                key="BLOODTHIRST_FAMILY",
                base_action_ids=(23881,),
                upgraded_action_ids=(335096,),
                notes="Bloodthirst -> Bloodbath action family.",
            ),
            ActionFamilyDef(
                key="RAGING_BLOW_FAMILY",
                base_action_ids=(85288,),
                upgraded_action_ids=(335097,),
                notes="Raging Blow -> Crushing Blow action family.",
            ),
        )

    def state_features(self):
        return (
            StateFeatureDef(
                key="rage",
                primitive="RESOURCE_SCALAR",
                trackability="TRACKABLE",
            ),
            StateFeatureDef(
                key="enrage_active",
                primitive="BUFF_ACTIVE",
                identity_ids=(184362,),
                trackability="TRACKABLE",
            ),
            StateFeatureDef(
                key="recklessness_active",
                primitive="BUFF_ACTIVE",
                identity_ids=(1719,),
                trackability="TRACKABLE",
                notes="Locale-safe abilityGameID identity.",
            ),
            StateFeatureDef(
                key="recklessness_remains",
                primitive="BUFF_REMAINS",
                identity_ids=(1719,),
                trackability="TRACKABLE",
            ),
            StateFeatureDef(
                key="sudden_death_active",
                primitive="PROC_ACTIVE",
                identity_ids=(52437,),
                trackability="TRACKABLE",
            ),
            StateFeatureDef(
                key="whirlwind_cleave_stacks",
                primitive="BUFF_STACKS",
                identity_ids=(85739,),
                trackability="TRACKABLE",
            ),
            StateFeatureDef(
                key="bladestorm_active",
                primitive="BUFF_ACTIVE",
                identity_ids=(446035,),
                trackability="TRACKABLE",
            ),
            StateFeatureDef(
                key="target_count_5s_observed",
                primitive="TARGET_COUNT_CONTEXT",
                trackability="TRACKABLE",
                notes="Observed damage-engagement proxy, not exact active_enemies.",
            ),
            StateFeatureDef(
                key="target_hp_pct_pre",
                primitive="TARGET_HEALTH",
                trackability="MASKED",
                notes="Target-owned HP state unavailable in Fury bootstrap.",
            ),
        )

    def action_overrides(self):
        evidence_id = (
            "FURY_SLAYER_RECKLESS_ABANDON_ACTION_FAMILY_OVERRIDE"
        )

        return (
            ActionOverrideDef(
                key="RECKLESS_ABANDON_BLOODTHIRST",
                family_key="BLOODTHIRST_FAMILY",
                trigger_feature="recklessness_active",
                when_active_action_ids=(335096,),
                when_inactive_action_ids=(23881,),
                evidence_id=evidence_id,
            ),
            ActionOverrideDef(
                key="RECKLESS_ABANDON_RAGING_BLOW",
                family_key="RAGING_BLOW_FAMILY",
                trigger_feature="recklessness_active",
                when_active_action_ids=(335097,),
                when_inactive_action_ids=(85288,),
                evidence_id=evidence_id,
            ),
        )

    def frozen_evidence_ids(self):
        return (
            "FURY_SLAYER_RECKLESS_ABANDON_ACTION_FAMILY_OVERRIDE",
        )

    def known_masks(self):
        return (
            "EXACT_WHIRLWIND_TARGET_BREAKPOINT_UNRESOLVED",
            "TARGET_HP_EXECUTE_STATE_MASKED",
            "RAMPAGE_CONTEXT_CANDIDATES_NOT_PROMOTED",
            "STORM_BOLT_BLADESTORM_CONTEXT_NOT_PROMOTED",
        )


ADAPTER = FurySlayerAdapter()
