#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enhancement Shaman / Stormbringer SpecAdapter for P4 third-spec acceptance.

Scope:
- specialization semantics only;
- no network I/O;
- no renderer logic;
- no evidence thresholds;
- no claim that current WCL behavior has already validated these mechanics.

Canonical mechanic intent for the adapter:
- Maelstrom Weapon is represented as a stack state (BUFF_STACKS), not as a
  Fury-style scalar resource bar.
- Ascendance replaces Stormstrike with Windstrike.
- Stormbringer Tempest replaces Lightning Bolt while available.
- target count remains the generic observed 5s damage-engagement proxy.

Multiple stable IDs may be listed where current/live WCL identity still needs
P4 live confirmation. O4 will fail closed if the corresponding stream is not
observed; this package does not guess from localized names.
"""

from __future__ import annotations

from raid_dps.specs.protocol import (
    ActionFamilyDef,
    ActionOverrideDef,
    StateFeatureDef,
)


class EnhancementStormbringerAdapter:
    spec_slug = "enhancement_shaman_stormbringer"
    class_name = "Shaman"
    spec_name = "Enhancement"
    variant = "Stormbringer"

    def action_families(self):
        return (
            ActionFamilyDef(
                key="STORMSTRIKE_FAMILY",
                # 17364 is the long-lived player spell identity; 1249148 is
                # also retained as a Midnight-era spell identity candidate.
                # P4 live evidence decides which ID(s) WCL actually emits.
                base_action_ids=(17364, 1249148),
                upgraded_action_ids=(115356,),
                notes="Stormstrike -> Windstrike during Ascendance.",
            ),
            ActionFamilyDef(
                key="LIGHTNING_BOLT_FAMILY",
                base_action_ids=(188196,),
                upgraded_action_ids=(452201,),
                notes="Lightning Bolt -> Tempest when Stormbringer Tempest is available.",
            ),
            ActionFamilyDef(
                key="CHAIN_LIGHTNING_FAMILY",
                base_action_ids=(188443,),
                upgraded_action_ids=(),
                notes="AoE Maelstrom Weapon spender family; no replacement asserted here.",
            ),
            ActionFamilyDef(
                key="CRASH_LIGHTNING_FAMILY",
                base_action_ids=(187874,),
                upgraded_action_ids=(),
                notes="Enhancement AoE strike family.",
            ),
        )

    def state_features(self):
        return (
            StateFeatureDef(
                key="maelstrom_weapon_stacks",
                primitive="BUFF_STACKS",
                # 344179 is the historically observed player aura identity.
                # 1219440 is retained as a current Midnight spell identity
                # candidate. Live O3/O4 must resolve actual WCL emission.
                identity_ids=(344179, 1219440),
                trackability="TRACKABLE",
                notes=(
                    "Stack resource model. Runtime identity remains stable-ID based; "
                    "live P4 evidence must confirm the emitted aura ID."
                ),
            ),
            StateFeatureDef(
                key="ascendance_active",
                primitive="BUFF_ACTIVE",
                identity_ids=(114051, 467263),
                trackability="TRACKABLE",
                notes=(
                    "Ascendance state for Stormstrike -> Windstrike family replacement. "
                    "Live P4 evidence must confirm emitted aura identity."
                ),
            ),
            StateFeatureDef(
                key="tempest_available",
                primitive="PROC_ACTIVE",
                identity_ids=(454015,),
                trackability="TRACKABLE",
                notes=(
                    "Stormbringer Tempest availability. This is canonical semantics, "
                    "not yet behavioral proof."
                ),
            ),
            StateFeatureDef(
                key="target_count_5s_observed",
                primitive="TARGET_COUNT_CONTEXT",
                trackability="TRACKABLE",
                notes=(
                    "Observed 5s damage-engagement proxy, never exact active_enemies."
                ),
            ),
            StateFeatureDef(
                key="target_hp_pct_pre",
                primitive="TARGET_HEALTH",
                trackability="MASKED",
                notes=(
                    "Target-owned HP is not assumed available during third-spec bootstrap."
                ),
            ),
            StateFeatureDef(
                key="stormbringer_build_variant",
                primitive="BUILD_VARIANT",
                trackability="CANONICAL",
                notes=(
                    "Declared onboarding variant; not inferred from WCL aura events."
                ),
            ),
        )

    def action_overrides(self):
        return (
            ActionOverrideDef(
                key="ASCENDANCE_STORMSTRIKE_TO_WINDSTRIKE",
                family_key="STORMSTRIKE_FAMILY",
                trigger_feature="ascendance_active",
                when_active_action_ids=(115356,),
                when_inactive_action_ids=(17364, 1249148),
                evidence_id="ENHANCEMENT_ASCENDANCE_WINDSTRIKE_ACTION_FAMILY_OVERRIDE",
                notes=(
                    "Documented mechanic candidate; P4 live evidence has not yet "
                    "validated current WCL behavioral replication."
                ),
            ),
            ActionOverrideDef(
                key="STORMBRINGER_LIGHTNING_BOLT_TO_TEMPEST",
                family_key="LIGHTNING_BOLT_FAMILY",
                trigger_feature="tempest_available",
                when_active_action_ids=(452201,),
                when_inactive_action_ids=(188196,),
                evidence_id="ENHANCEMENT_STORMBRINGER_TEMPEST_ACTION_FAMILY_OVERRIDE",
                notes=(
                    "Documented hero-tree replacement candidate; not frozen on adapter "
                    "declaration alone."
                ),
            ),
        )

    def frozen_evidence_ids(self):
        # Third-spec onboarding starts with zero frozen behavioral evidence.
        return ()

    def known_masks(self):
        return (
                                                "TARGET_HP_STATE_MASKED",
            "EXACT_ST_AOE_BREAKPOINT_UNRESOLVED",
            "INTER_FAMILY_PRIORITY_NOT_VALIDATED",
        )


ADAPTER = EnhancementStormbringerAdapter()
