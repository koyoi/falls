"""Forcefield agent builds forcefield.v1.json compatible structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from .schema import ForceEvent, ForcefieldSchema, MAX_WIND_SPEED, clamp


@dataclass
class ForceEventSpec:
    t: float
    type: str
    dir_deg: Optional[float] = None
    speed: Optional[float] = None
    dur: Optional[float] = None
    center: Optional[List[float]] = None
    radius: Optional[float] = None
    vortex: Optional[float] = None


@dataclass
class ForcefieldConstraints:
    max_speed: float = MAX_WIND_SPEED


@dataclass
class ForcefieldRequest:
    prompt: str
    events: Iterable[ForceEventSpec]
    use_prebaked_texture: bool = False


class ForceFieldAgent:
    """Generate forcefield schemas based on structured event specs."""

    def __init__(self, constraints: ForcefieldConstraints | None = None) -> None:
        self.constraints = constraints or ForcefieldConstraints()

    def _apply_constraints(self, event: ForceEventSpec) -> ForceEvent:
        speed = event.speed
        if speed is not None:
            speed = clamp(speed, min_value=0.0, max_value=self.constraints.max_speed)
        vortex = event.vortex
        if vortex is not None:
            vortex = clamp(vortex, min_value=0.0, max_value=self.constraints.max_speed * 1.25)
        return ForceEvent(
            t=event.t,
            type=event.type,
            dir_deg=event.dir_deg,
            speed=speed,
            dur=event.dur,
            center=event.center,
            radius=event.radius,
            vortex=vortex,
        )

    def generate(self, request: ForcefieldRequest) -> ForcefieldSchema:
        events = [self._apply_constraints(event) for event in request.events]
        return ForcefieldSchema(timeline=events, use_prebaked_texture=request.use_prebaked_texture)


__all__ = ["ForceFieldAgent", "ForcefieldRequest", "ForcefieldConstraints", "ForceEventSpec"]
