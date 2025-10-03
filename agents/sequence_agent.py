"""Simulation sequence agent to orchestrate preset/forcefile changes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .schema import SequenceSchema, SequenceTrack


@dataclass
class SequenceRequest:
    tracks: Iterable[SequenceTrack]
    loop: bool = True


class SequenceAgent:
    """Build a sequence schema from provided timeline tracks."""

    def generate(self, request: SequenceRequest) -> SequenceSchema:
        return SequenceSchema(tracks=list(request.tracks), loop=request.loop)


__all__ = ["SequenceAgent", "SequenceRequest"]
