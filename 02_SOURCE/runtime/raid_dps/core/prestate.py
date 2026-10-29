#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strict PRE-state reconstruction for aura/buff streams.

Temporal invariant:
  state_at_action(t) = latest transition with timestamp < t

Therefore same-timestamp transitions never leak into the current action.
"""

from __future__ import annotations

import bisect
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .identity import as_int, event_ability_id, normalize_name


AuraState = Tuple[bool, int]


def as_float(
    value: Any,
) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def aura_transition(
    event: Dict[str, Any],
) -> Optional[AuraState]:
    """Convert WCL-style buff events into (active, stack) state transitions."""
    typ = normalize_name(
        event.get("type")
    )

    if typ in {
        "applybuff",
        "refreshbuff",
        "applybuffstack",
    }:
        stack = (
            as_int(
                event.get("stack")
            )
            or as_int(
                event.get("stacks")
            )
            or 1
        )
        return (
            True,
            max(
                int(stack),
                1,
            ),
        )

    if typ == "removebuff":
        return (
            False,
            0,
        )

    if typ == "removebuffstack":
        stack = (
            as_int(
                event.get("stack")
            )
            or as_int(
                event.get("stacks")
            )
        )

        # WCL payloads can omit the post-event stack count. In that case we
        # know the aura has not been fully removed by event type alone.
        if stack is None:
            return (
                True,
                1,
            )

        return (
            int(stack) > 0,
            max(
                int(stack),
                0,
            ),
        )

    return None


class AuraIdIndex:
    """Locale-safe aura state index keyed by stable abilityGameID."""

    def __init__(
        self,
        events: Iterable[Dict[str, Any]],
    ):
        self.by_id: Dict[
            int,
            List[
                Tuple[
                    float,
                    bool,
                    int,
                ]
            ],
        ] = defaultdict(list)

        for event in events:
            if not isinstance(
                event,
                dict,
            ):
                continue

            timestamp = as_float(
                event.get(
                    "timestamp"
                )
            )
            ability_id = (
                event_ability_id(
                    event
                )
            )
            transition = (
                aura_transition(
                    event
                )
            )

            if (
                timestamp is None
                or ability_id is None
                or transition is None
            ):
                continue

            active, stack = (
                transition
            )

            self.by_id[
                int(
                    ability_id
                )
            ].append(
                (
                    float(
                        timestamp
                    ),
                    bool(
                        active
                    ),
                    int(
                        stack
                    ),
                )
            )

        self.timestamps: Dict[
            int,
            List[float],
        ] = {}

        for (
            ability_id,
            values,
        ) in self.by_id.items():
            values.sort(
                key=lambda item: (
                    item[0]
                )
            )
            self.timestamps[
                ability_id
            ] = [
                item[0]
                for item in values
            ]

    def state_pre(
        self,
        ability_id: int,
        timestamp: float,
    ) -> AuraState:
        """Return aura state strictly before `timestamp`."""
        ability_id = int(
            ability_id
        )
        values = self.by_id.get(
            ability_id
        )

        if not values:
            return (
                False,
                0,
            )

        timestamps = (
            self.timestamps[
                ability_id
            ]
        )

        index = (
            bisect.bisect_left(
                timestamps,
                float(
                    timestamp
                ),
            )
            - 1
        )

        if index < 0:
            return (
                False,
                0,
            )

        _, active, stack = (
            values[index]
        )

        return (
            bool(
                active
            ),
            int(
                stack
            ),
        )

    def active_pre(
        self,
        ability_id: int,
        timestamp: float,
    ) -> bool:
        return bool(
            self.state_pre(
                ability_id,
                timestamp,
            )[0]
        )

    def stack_pre(
        self,
        ability_id: int,
        timestamp: float,
    ) -> int:
        return int(
            self.state_pre(
                ability_id,
                timestamp,
            )[1]
        )

    def any_active_pre(
        self,
        ability_ids: Iterable[int],
        timestamp: float,
    ) -> bool:
        """Return True if any stable ability ID is active strictly before t."""
        return any(
            self.active_pre(
                ability_id,
                timestamp,
            )
            for ability_id
            in ability_ids
        )

    def latest_state_pre(
        self,
        ability_ids: Iterable[int],
        timestamp: float,
    ) -> AuraState:
        """Return the latest transition among equivalent stable IDs.

        Useful only when a canonical feature explicitly maps to multiple IDs.
        It does not merge localized display names.
        """
        latest: Optional[
            Tuple[
                float,
                bool,
                int,
            ]
        ] = None

        for raw_id in ability_ids:
            ability_id = int(
                raw_id
            )
            values = self.by_id.get(
                ability_id
            )
            if not values:
                continue

            timestamps = (
                self.timestamps[
                    ability_id
                ]
            )

            index = (
                bisect.bisect_left(
                    timestamps,
                    float(
                        timestamp
                    ),
                )
                - 1
            )

            if index < 0:
                continue

            candidate = (
                values[index]
            )

            if (
                latest is None
                or candidate[0]
                > latest[0]
            ):
                latest = candidate

        if latest is None:
            return (
                False,
                0,
            )

        return (
            bool(
                latest[1]
            ),
            int(
                latest[2]
            ),
        )
