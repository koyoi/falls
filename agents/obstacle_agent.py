"""Obstacle agent generates obstacles.v1.json compatible data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .schema import ClearRule, DrawOp, ObstaclesSchema


@dataclass
class ObstacleRequest:
    clear_rules: Iterable[ClearRule]
    draw_ops: Iterable[DrawOp]
    mask_path: str = "res://runtime/obstacles_mask.png"


class ObstacleAgent:
    """Create obstacle layouts from structured instructions."""

    def generate(self, request: ObstacleRequest) -> ObstaclesSchema:
        return ObstaclesSchema(
            clear_rules=list(request.clear_rules),
            draw_ops=list(request.draw_ops),
            mask_path=request.mask_path,
        )


__all__ = ["ObstacleAgent", "ObstacleRequest"]
