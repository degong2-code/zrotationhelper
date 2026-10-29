#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common specialization adapter protocol.

The adapter layer owns specialization semantics only.
It MUST NOT perform network I/O or alter renderer/evidence semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Protocol, Sequence, Tuple, runtime_checkable


@dataclass(frozen=True)
class ActionFamilyDef:
    key: str
    base_action_ids: Tuple[int, ...] = ()
    upgraded_action_ids: Tuple[int, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class StateFeatureDef:
    key: str
    primitive: str
    identity_ids: Tuple[int, ...] = ()
    trackability: str = "UNSPECIFIED"
    notes: str = ""


@dataclass(frozen=True)
class ActionOverrideDef:
    key: str
    family_key: str
    trigger_feature: str
    when_active_action_ids: Tuple[int, ...]
    when_inactive_action_ids: Tuple[int, ...]
    evidence_id: str
    notes: str = ""


@runtime_checkable
class SpecAdapter(Protocol):
    spec_slug: str
    class_name: str
    spec_name: str
    variant: str

    def action_families(self) -> Sequence[ActionFamilyDef]:
        ...

    def state_features(self) -> Sequence[StateFeatureDef]:
        ...

    def action_overrides(self) -> Sequence[ActionOverrideDef]:
        ...

    def frozen_evidence_ids(self) -> Sequence[str]:
        ...

    def known_masks(self) -> Sequence[str]:
        ...


def validate_adapter(
    adapter: SpecAdapter,
    *,
    allowed_primitives: Iterable[str],
) -> list[str]:
    errors: list[str] = []

    required_text = {
        "spec_slug": getattr(adapter, "spec_slug", ""),
        "class_name": getattr(adapter, "class_name", ""),
        "spec_name": getattr(adapter, "spec_name", ""),
        "variant": getattr(adapter, "variant", ""),
    }

    for field, value in required_text.items():
        if not str(value).strip():
            errors.append(f"missing {field}")

    allowed = {
        str(value)
        for value in allowed_primitives
    }

    feature_keys = set()

    for feature in adapter.state_features():
        if not feature.key:
            errors.append("state feature missing key")
            continue

        if feature.key in feature_keys:
            errors.append(
                f"duplicate state feature: {feature.key}"
            )

        feature_keys.add(
            feature.key
        )

        if feature.primitive not in allowed:
            errors.append(
                f"unsupported primitive {feature.primitive!r} for {feature.key}"
            )

    family_keys = set()

    for family in adapter.action_families():
        if not family.key:
            errors.append("action family missing key")
            continue

        if family.key in family_keys:
            errors.append(
                f"duplicate action family: {family.key}"
            )

        family_keys.add(
            family.key
        )

    override_keys = set()

    for override in adapter.action_overrides():
        if not override.key:
            errors.append("action override missing key")
            continue

        if override.key in override_keys:
            errors.append(
                f"duplicate action override: {override.key}"
            )

        override_keys.add(
            override.key
        )

        if override.family_key not in family_keys:
            errors.append(
                f"override {override.key} references unknown family {override.family_key}"
            )

        if override.trigger_feature not in feature_keys:
            errors.append(
                f"override {override.key} references unknown feature {override.trigger_feature}"
            )

    return errors
