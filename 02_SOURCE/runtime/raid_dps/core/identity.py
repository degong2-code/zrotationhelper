#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stable identity helpers for Warcraft Logs events.

Runtime identity MUST use stable game/ability IDs.
Localized display names are presentation metadata only.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


def as_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except Exception:
        return None


def normalize_name(value: Any) -> str:
    """Presentation/search normalization only — never runtime state identity."""
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip(),
    ).casefold()


def event_ability_id(
    event: Dict[str, Any],
) -> Optional[int]:
    """Resolve the stable ability game ID from a WCL-like event.

    Supported shapes:
    - event["abilityGameID"]
    - event["abilityID"]
    - event["guid"]
    - event["ability"]["gameID"|"guid"|"id"]

    Display names are deliberately ignored.
    """
    for key in (
        "abilityGameID",
        "abilityID",
        "guid",
    ):
        value = as_int(
            event.get(key)
        )
        if value is not None:
            return value

    ability = event.get(
        "ability"
    )

    if isinstance(
        ability,
        dict,
    ):
        for key in (
            "gameID",
            "guid",
            "id",
        ):
            value = as_int(
                ability.get(key)
            )
            if value is not None:
                return value

    return None


def stable_ability_identity(
    event: Dict[str, Any],
) -> Optional[str]:
    """Return a locale-independent string key for an ability event."""
    ability_id = event_ability_id(
        event
    )
    if ability_id is None:
        return None
    return f"ability:{ability_id}"
