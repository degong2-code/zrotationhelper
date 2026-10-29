#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic observability coverage classification.

Coverage is NOT evidence strength.
A semantic mask may override apparent numerical coverage.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


TRACKABLE_MIN_PCT = 95.0
PARTIAL_MIN_PCT = 20.0

TRACKABLE = "TRACKABLE"
PARTIAL = "PARTIAL"
MASKED = "MASKED"


def coverage_pct(
    covered: int,
    total: int,
) -> Optional[float]:
    if total <= 0:
        return None

    return (
        100.0
        * int(covered)
        / int(total)
    )


def classify_coverage(
    covered: int,
    total: int,
    *,
    semantic_mask: bool = False,
) -> str:
    """Return TRACKABLE / PARTIAL / MASKED.

    Default contract:
      >=95%   TRACKABLE
      >=20%   PARTIAL
      <20%    MASKED

    semantic_mask=True forces MASKED even when numerical
    coverage is high, for example when the observed field is
    not semantically safe for the intended inference.
    """
    if semantic_mask:
        return MASKED

    value = coverage_pct(
        covered,
        total,
    )

    if value is None:
        return MASKED

    if value >= TRACKABLE_MIN_PCT:
        return TRACKABLE

    if value >= PARTIAL_MIN_PCT:
        return PARTIAL

    return MASKED


def coverage_record(
    *,
    field: str,
    covered: int,
    total: int,
    semantic_mask: bool = False,
    semantic_route: Optional[str] = None,
) -> Dict[str, Any]:
    value = coverage_pct(
        covered,
        total,
    )

    return {
        "field": field,
        "covered_rows": int(covered),
        "total_rows": int(total),
        "coverage_pct": (
            round(value, 3)
            if value is not None
            else None
        ),
        "status": classify_coverage(
            covered,
            total,
            semantic_mask=semantic_mask,
        ),
        "semantic_mask": bool(
            semantic_mask
        ),
        "semantic_route": semantic_route,
    }
