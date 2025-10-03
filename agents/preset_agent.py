"""Preset agent responsible for authoring preset.v1.json structures."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

from .schema import (
    MAX_PARTICLE_RATE,
    AccumulationSettings,
    AppearanceSettings,
    BackgroundSettings,
    BurstSettings,
    EmitterSettings,
    FXSettings,
    MotionSettings,
    ObstacleSettings,
    PresetSchema,
    SizeRange,
    SpawnBand,
    TargetsSettings,
    clamp,
)


@dataclass
class PresetConstraints:
    max_particles: int = MAX_PARTICLE_RATE
    target_fps: int = 60
    internal_scale: float = 0.75


@dataclass
class PresetRequest:
    prompt: str
    palette: Optional[Sequence[str]] = None
    emitter_type: str = "generic"
    base_name: str = "custom"
    desired_rate: int = 2000
    burst_interval: Optional[float] = None
    burst_count: Optional[int] = None
    sprite: str = "res://runtime/preset_sprite.png"
    notes: Optional[str] = None


class PresetAgent:
    """Generate preset schemas using lightweight heuristics."""

    def __init__(self, constraints: PresetConstraints | None = None) -> None:
        self.constraints = constraints or PresetConstraints()

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        return slug or "preset"

    @staticmethod
    def _choose_motion(prompt: str) -> MotionSettings:
        prompt_lower = prompt.lower()
        if "storm" in prompt_lower or "strong" in prompt_lower:
            return MotionSettings(drag=0.05, sway_amp=50.0, sway_freq=0.9, spin_deg_per_sec=120.0, gravity=320.0, glide_lift=0.4)
        if "calm" in prompt_lower or "gentle" in prompt_lower:
            return MotionSettings(drag=0.18, sway_amp=18.0, sway_freq=0.4, spin_deg_per_sec=40.0, gravity=120.0, glide_lift=0.2)
        return MotionSettings(drag=0.12, sway_amp=30.0, sway_freq=0.6, spin_deg_per_sec=90.0, gravity=240.0, glide_lift=0.3)

    @staticmethod
    def _appearance(palette: Optional[Sequence[str]], sprite: str) -> AppearanceSettings:
        if not palette:
            palette = ["#ffffff", "#dddddd", "#bbbbbb"]
        size = SizeRange(min=6, max=14)
        return AppearanceSettings(list(palette), size, sprite)

    def generate(self, request: PresetRequest) -> PresetSchema:
        slug = self._slugify(request.base_name or request.prompt)
        emitter_rate = int(clamp(float(request.desired_rate), min_value=1.0, max_value=float(self.constraints.max_particles)))
        burst = None
        if request.burst_interval is not None and request.burst_count is not None:
            burst = BurstSettings(interval_sec=request.burst_interval, count=request.burst_count)
        emitter = EmitterSettings(
            type=request.emitter_type,
            rate_per_sec=emitter_rate,
            spawn_band=SpawnBand(y=0.05, height=0.02),
            burst=burst,
        )
        appearance = self._appearance(request.palette, request.sprite)
        motion = self._choose_motion(request.prompt)
        accumulation = AccumulationSettings(enabled=True, mode="heightmap", max_height_px=180.0, diffusion=0.08)
        obstacle = ObstacleSettings(collide_mask="res://runtime/obstacles_mask.png", stickiness=0.2)
        fx = FXSettings(bloom=0.2, background=BackgroundSettings(["#0b1120", "#1e293b"], cycle_by_clock=False))
        targets = TargetsSettings(fps=self.constraints.target_fps, internal_scale=self.constraints.internal_scale)
        notes = (request.notes or request.prompt)[:80]
        return PresetSchema(
            name=slug,
            emitter=emitter,
            appearance=appearance,
            motion=motion,
            accumulation=accumulation,
            obstacle=obstacle,
            fx=fx,
            targets=targets,
            notes=notes,
        )


__all__ = ["PresetAgent", "PresetRequest", "PresetConstraints"]
