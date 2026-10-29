#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unholy Death Knight Golden-Fixture SpecAdapter.

This is not a claim that the specialization is fully solved.
It exposes only semantics/evidence already admitted by the Golden Fixture
pipeline and keeps unresolved features explicit.
"""

from __future__ import annotations

from raid_dps.specs.protocol import (
    ActionFamilyDef,
    ActionOverrideDef,
    StateFeatureDef,
)


class UnholyDeathKnightAdapter:
    spec_slug = "unholy_death_knight"
    class_name = "Death Knight"
    spec_name = "Unholy"
    variant = "Golden Fixture"

    def action_families(self):
        # No speculative action IDs are introduced here.
        # Concrete resolution remains artifact-backed until migrated from
        # authoritative Unholy canonical artifacts.
        return ()

    def state_features(self):
        return (
            StateFeatureDef(
                key="runes",
                primitive="RESOURCE_SCALAR",
                trackability="PARTIAL",
                notes="Observed coverage was partial in Stage 5.",
            ),
            StateFeatureDef(
                key="runic_power_deficit",
                primitive="RESOURCE_DEFICIT",
                trackability="TRACKABLE",
            ),
            StateFeatureDef(
                key="forbidden_knowledge_active",
                primitive="BUFF_ACTIVE",
                trackability="TRACKABLE",
            ),
            StateFeatureDef(
                key="festering_scythe_ready",
                primitive="PROC_ACTIVE",
                trackability="TRACKABLE",
            ),
            StateFeatureDef(
                key="vampiric_strike_usable",
                primitive="ACTION_OVERRIDE",
                trackability="TRACKABLE",
            ),
            StateFeatureDef(
                key="target_count_5s_observed",
                primitive="TARGET_COUNT_CONTEXT",
                trackability="TRACKABLE",
                notes="Validated observed target-count proxy, not exact active_enemies.",
            ),
            StateFeatureDef(
                key="target_hp_pct_pre",
                primitive="TARGET_HEALTH",
                trackability="PARTIAL",
            ),
            StateFeatureDef(
                key="putrefy_charges",
                primitive="CHARGE_STATE",
                trackability="UNRESOLVED",
                notes="Sprint 5 mask; do not reconstruct by guesswork.",
            ),
        )

    def action_overrides(self):
        # The Golden Fixture has frozen mechanic overrides, but concrete action
        # IDs are intentionally not guessed here. They remain evidence-backed
        # references until canonical ID migration is performed from source artifacts.
        return ()

    def frozen_evidence_ids(self):
        return (
            "GLOBAL_ARMY_DARK_TRANSFORMATION_PAIR",
            "GLOBAL_DARK_TRANSFORMATION_TO_BLIGHTFALL_SEQUENCE",
            "GLOBAL_EPIDEMIC_MULTITARGET_USAGE_CONTEXT",
            "SPEC_OVERRIDE_FORBIDDEN_KNOWLEDGE_SPENDERS",
            "SPEC_OVERRIDE_VAMPIRIC_STRIKE",
            "SPEC_OVERRIDE_FESTERING_SCYTHE",
            "SPEC_CONTEXT_BLIGHTFALL_SOUL_REAPER",
        )

    def known_masks(self):
        return (
            "PUTREFY_CHARGES_UNRESOLVED_MASK_IN_SPRINT5",
            "EXACT_EPIDEMIC_TARGET_BREAKPOINT_UNRESOLVED",
            "TARGET_HP_EXECUTE_STATE_PARTIAL",
            "TARGET_DURATION_UNAVAILABLE",
        )


ADAPTER = UnholyDeathKnightAdapter()
