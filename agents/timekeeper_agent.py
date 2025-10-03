"""Timekeeper agent manages time and seasonal adjustments."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .schema import SeasonalAdjust, TimekeeperSchema


@dataclass
class TimekeeperRequest:
    region: str
    adjustments: Iterable[SeasonalAdjust]


class TimekeeperAgent:
    """Create timekeeper schemas from scheduling data."""

    def generate(self, request: TimekeeperRequest) -> TimekeeperSchema:
        return TimekeeperSchema(region=request.region, adjustments=list(request.adjustments))


__all__ = ["TimekeeperAgent", "TimekeeperRequest"]
