"""Shared schema and validation helpers for runtime JSON generation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

SCHEMA_VERSION = "1.0"
MAX_PARTICLE_RATE = 100_000
MAX_BURST_COUNT = 100_000
MAX_WIND_SPEED = 400.0
MAX_VORTEX_SPEED = 500.0
MAX_TORNADO_RADIUS = 0.5
MAX_ACCUMULATION_HEIGHT = 512.0
MAX_EXPORT_DURATION = 120.0
MAX_EXPORT_RESOLUTION = 4096


class ValidationError(ValueError):
    """Raised when incoming data violates schema constraints."""


def clamp(value: float, *, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
    """Clamp *value* inside the provided range."""

    if value != value:  # NaN check
        raise ValidationError("value cannot be NaN")
    if min_value is not None and value < min_value:
        value = min_value
    if max_value is not None and value > max_value:
        value = max_value
    return value


def ensure_runtime_path(path: str) -> str:
    """Validate that a resource path lives under ``res://runtime/``."""

    if not path.startswith("res://runtime/"):
        raise ValidationError("runtime assets must be stored under res://runtime/")
    return path


def ensure_palette(palette: Iterable[str]) -> List[str]:
    colors = [color for color in palette if color]
    if not colors:
        raise ValidationError("palette must contain at least one color")
    return colors


@dataclass
class RuntimeJSON:
    version: str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:  # pragma: no cover - subclasses override
        raise NotImplementedError


@dataclass
class BurstSettings:
    interval_sec: float
    count: int

    def __post_init__(self) -> None:
        self.interval_sec = clamp(self.interval_sec, min_value=0.0)
        self.count = int(clamp(float(self.count), min_value=0.0, max_value=MAX_BURST_COUNT))

    def to_dict(self) -> Dict[str, Any]:
        return {"interval_sec": self.interval_sec, "count": self.count}


@dataclass
class SpawnBand:
    y: float
    height: float

    def __post_init__(self) -> None:
        self.y = clamp(self.y, min_value=0.0, max_value=1.0)
        self.height = clamp(self.height, min_value=0.0, max_value=1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {"y": self.y, "height": self.height}


@dataclass
class EmitterSettings:
    type: str
    rate_per_sec: int
    spawn_band: SpawnBand
    burst: Optional[BurstSettings] = None
    random_seed: Optional[int] = None

    def __post_init__(self) -> None:
        self.rate_per_sec = int(
            clamp(float(self.rate_per_sec), min_value=0.0, max_value=float(MAX_PARTICLE_RATE))
        )
        if self.random_seed is not None:
            self.random_seed = int(self.random_seed) & 0xFFFFFFFF

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "type": self.type,
            "rate_per_sec": self.rate_per_sec,
            "spawn_band": self.spawn_band.to_dict(),
        }
        if self.burst:
            data["burst"] = self.burst.to_dict()
        if self.random_seed is not None:
            data["random_seed"] = self.random_seed
        return data


@dataclass
class SizeRange:
    min: float
    max: float

    def __post_init__(self) -> None:
        self.min = clamp(self.min, min_value=0.0)
        self.max = clamp(self.max, min_value=max(self.min, 0.0))

    def to_dict(self) -> Dict[str, Any]:
        return {"min": self.min, "max": self.max}


@dataclass
class AppearanceSettings:
    palette: List[str]
    size_px: SizeRange
    sprite: str

    def __post_init__(self) -> None:
        self.palette = ensure_palette(self.palette)
        if not self.sprite:
            raise ValidationError("sprite path cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "palette": self.palette,
            "size_px": self.size_px.to_dict(),
            "sprite": self.sprite,
        }


@dataclass
class MotionSettings:
    drag: float
    sway_amp: float
    sway_freq: float
    spin_deg_per_sec: float
    gravity: float
    glide_lift: float

    def __post_init__(self) -> None:
        self.drag = clamp(self.drag, min_value=0.0, max_value=5.0)
        self.sway_amp = clamp(self.sway_amp, min_value=0.0, max_value=180.0)
        self.sway_freq = clamp(self.sway_freq, min_value=0.0, max_value=5.0)
        self.spin_deg_per_sec = clamp(self.spin_deg_per_sec, min_value=-720.0, max_value=720.0)
        self.gravity = clamp(self.gravity, min_value=-5000.0, max_value=5000.0)
        self.glide_lift = clamp(self.glide_lift, min_value=0.0, max_value=5.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drag": self.drag,
            "sway": {"amp": self.sway_amp, "freq": self.sway_freq},
            "spin": {"deg_per_sec": self.spin_deg_per_sec},
            "gravity": self.gravity,
            "glide": {"lift": self.glide_lift},
        }


@dataclass
class AccumulationSettings:
    enabled: bool
    mode: str
    max_height_px: float
    diffusion: float

    def __post_init__(self) -> None:
        self.max_height_px = clamp(self.max_height_px, min_value=0.0, max_value=MAX_ACCUMULATION_HEIGHT)
        self.diffusion = clamp(self.diffusion, min_value=0.0, max_value=1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "max_height_px": self.max_height_px,
            "diffusion": self.diffusion,
        }


@dataclass
class ObstacleSettings:
    collide_mask: str
    stickiness: float

    def __post_init__(self) -> None:
        self.collide_mask = ensure_runtime_path(self.collide_mask)
        self.stickiness = clamp(self.stickiness, min_value=0.0, max_value=1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {"collide_mask": self.collide_mask, "stickiness": self.stickiness}


@dataclass
class BackgroundSettings:
    gradient: List[str]
    cycle_by_clock: bool = False

    def __post_init__(self) -> None:
        self.gradient = ensure_palette(self.gradient)

    def to_dict(self) -> Dict[str, Any]:
        return {"gradient": self.gradient, "cycle_by_clock": self.cycle_by_clock}


@dataclass
class FXSettings:
    bloom: float
    background: BackgroundSettings

    def __post_init__(self) -> None:
        self.bloom = clamp(self.bloom, min_value=0.0, max_value=2.0)

    def to_dict(self) -> Dict[str, Any]:
        return {"bloom": self.bloom, "background": self.background.to_dict()}


@dataclass
class TargetsSettings:
    fps: int
    internal_scale: float

    def __post_init__(self) -> None:
        self.fps = int(clamp(float(self.fps), min_value=1.0, max_value=240.0))
        self.internal_scale = clamp(self.internal_scale, min_value=0.1, max_value=1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {"fps": self.fps, "internal_scale": self.internal_scale}


@dataclass
class PresetSchema(RuntimeJSON):
    name: str = ""
    emitter: EmitterSettings = field(default_factory=lambda: EmitterSettings(
        type="generic",
        rate_per_sec=10,
        spawn_band=SpawnBand(0.0, 1.0),
    ))
    appearance: AppearanceSettings = field(
        default_factory=lambda: AppearanceSettings(
            palette=["#ffffff"], size_px=SizeRange(1, 1), sprite="res://runtime/default.png"
        )
    )
    motion: MotionSettings = field(
        default_factory=lambda: MotionSettings(0.1, 10.0, 0.5, 0.0, 0.0, 0.0)
    )
    accumulation: AccumulationSettings = field(
        default_factory=lambda: AccumulationSettings(True, "heightmap", 32.0, 0.1)
    )
    obstacle: ObstacleSettings = field(
        default_factory=lambda: ObstacleSettings("res://runtime/obstacles_mask.png", 0.0)
    )
    fx: FXSettings = field(
        default_factory=lambda: FXSettings(0.0, BackgroundSettings(["#000000", "#000000"], False))
    )
    targets: TargetsSettings = field(default_factory=lambda: TargetsSettings(60, 1.0))
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "emitter": self.emitter.to_dict(),
            "appearance": self.appearance.to_dict(),
            "motion": self.motion.to_dict(),
            "accumulation": self.accumulation.to_dict(),
            "obstacle": self.obstacle.to_dict(),
            "fx": self.fx.to_dict(),
            "targets": self.targets.to_dict(),
            "notes": self.notes,
        }


@dataclass
class ForceEvent:
    t: float
    type: str
    dir_deg: Optional[float] = None
    speed: Optional[float] = None
    dur: Optional[float] = None
    center: Optional[List[float]] = None
    radius: Optional[float] = None
    vortex: Optional[float] = None

    def __post_init__(self) -> None:
        self.t = clamp(self.t, min_value=0.0)
        if self.dir_deg is not None:
            self.dir_deg = clamp(self.dir_deg, min_value=0.0, max_value=360.0)
        if self.speed is not None:
            self.speed = clamp(self.speed, min_value=0.0, max_value=MAX_WIND_SPEED)
        if self.dur is not None:
            self.dur = clamp(self.dur, min_value=0.0)
        if self.center is not None:
            if len(self.center) != 2:
                raise ValidationError("center must be a pair")
            self.center = [clamp(c, min_value=0.0, max_value=1.0) for c in self.center]
        if self.radius is not None:
            self.radius = clamp(self.radius, min_value=0.0, max_value=MAX_TORNADO_RADIUS)
        if self.vortex is not None:
            self.vortex = clamp(self.vortex, min_value=0.0, max_value=MAX_VORTEX_SPEED)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"t": self.t, "type": self.type}
        if self.dir_deg is not None:
            data["dir_deg"] = self.dir_deg
        if self.speed is not None:
            data["speed"] = self.speed
        if self.dur is not None:
            data["dur"] = self.dur
        if self.center is not None:
            data["center"] = self.center
        if self.radius is not None:
            data["radius"] = self.radius
        if self.vortex is not None:
            data["vortex"] = self.vortex
        return data


@dataclass
class ForcefieldSchema(RuntimeJSON):
    timeline: List[ForceEvent] = field(default_factory=list)
    use_prebaked_texture: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "timeline": [event.to_dict() for event in self.timeline],
            "texture": {"use_prebaked": self.use_prebaked_texture},
        }


@dataclass
class ClearRule:
    trigger: str
    action: str
    at: Optional[str] = None
    gte: Optional[float] = None
    radius_px: Optional[float] = None

    def __post_init__(self) -> None:
        if self.radius_px is not None:
            self.radius_px = clamp(self.radius_px, min_value=0.0, max_value=4096.0)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"trigger": self.trigger, "action": self.action}
        if self.at is not None:
            data["at"] = self.at
        if self.gte is not None:
            data["gte"] = self.gte
        if self.radius_px is not None:
            data["radius_px"] = self.radius_px
        return data


@dataclass
class DrawOp:
    op: str
    pos: Optional[List[float]] = None
    radius: Optional[float] = None
    rect: Optional[List[float]] = None
    mode: str = "solid"

    def __post_init__(self) -> None:
        if self.pos is not None:
            if len(self.pos) != 2:
                raise ValidationError("pos must have length 2")
            self.pos = [clamp(p, min_value=0.0, max_value=1.0) for p in self.pos]
        if self.radius is not None:
            self.radius = clamp(self.radius, min_value=0.0, max_value=1.0)
        if self.rect is not None:
            if len(self.rect) != 4:
                raise ValidationError("rect must have length 4")
            self.rect = [clamp(r, min_value=0.0, max_value=1.0) for r in self.rect]

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"op": self.op, "mode": self.mode}
        if self.pos is not None:
            data["pos"] = self.pos
        if self.radius is not None:
            data["radius"] = self.radius
        if self.rect is not None:
            data["rect"] = self.rect
        return data


@dataclass
class ObstaclesSchema(RuntimeJSON):
    clear_rules: List[ClearRule] = field(default_factory=list)
    draw_ops: List[DrawOp] = field(default_factory=list)
    mask_path: str = "res://runtime/obstacles_mask.png"

    def __post_init__(self) -> None:
        self.mask_path = ensure_runtime_path(self.mask_path)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "clear_rules": [rule.to_dict() for rule in self.clear_rules],
            "draw_ops": [op.to_dict() for op in self.draw_ops],
            "mask": self.mask_path,
        }


@dataclass
class SequenceTrack:
    t: float
    apply: Dict[str, str]

    def __post_init__(self) -> None:
        self.t = clamp(self.t, min_value=0.0)
        self.apply = {key: ensure_runtime_path(value) for key, value in self.apply.items()}

    def to_dict(self) -> Dict[str, Any]:
        return {"t": self.t, "apply": self.apply}


@dataclass
class SequenceSchema(RuntimeJSON):
    tracks: List[SequenceTrack] = field(default_factory=list)
    loop: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "tracks": [track.to_dict() for track in self.tracks],
            "loop": self.loop,
        }


@dataclass
class CaptureSettings:
    type: str
    w: int
    h: int
    fps: int
    dur_sec: float

    def __post_init__(self) -> None:
        self.w = int(clamp(float(self.w), min_value=1.0, max_value=float(MAX_EXPORT_RESOLUTION)))
        self.h = int(clamp(float(self.h), min_value=1.0, max_value=float(MAX_EXPORT_RESOLUTION)))
        self.fps = int(clamp(float(self.fps), min_value=1.0, max_value=240.0))
        self.dur_sec = clamp(self.dur_sec, min_value=0.0, max_value=MAX_EXPORT_DURATION)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "w": self.w,
            "h": self.h,
            "fps": self.fps,
            "dur_sec": self.dur_sec,
        }


@dataclass
class ExporterSchema(RuntimeJSON):
    capture: CaptureSettings = field(
        default_factory=lambda: CaptureSettings("video", 1920, 1080, 60, 10.0)
    )
    watermark: Optional[Dict[str, Any]] = None
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.seed is not None:
            self.seed = int(clamp(float(self.seed), min_value=0.0, max_value=2**32 - 1))

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "version": self.version,
            "capture": self.capture.to_dict(),
        }
        if self.watermark is not None:
            data["watermark"] = self.watermark
        if self.seed is not None:
            data["seed"] = self.seed
        return data


@dataclass
class SeasonalAdjust:
    parameter: str
    values: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"parameter": self.parameter, "values": self.values}


@dataclass
class TimekeeperSchema(RuntimeJSON):
    region: str = "UTC"
    adjustments: List[SeasonalAdjust] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "region": self.region,
            "adjustments": [adj.to_dict() for adj in self.adjustments],
        }


@dataclass
class UIHintsSchema(RuntimeJSON):
    tips: List[str] = field(default_factory=list)
    recommended_presets: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "tips": self.tips,
            "recommended_presets": self.recommended_presets,
        }


@dataclass
class AssetPackSchema(RuntimeJSON):
    required_assets: List[str] = field(default_factory=list)
    missing_assets: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "required_assets": self.required_assets,
            "missing_assets": self.missing_assets,
        }


__all__ = [
    "SCHEMA_VERSION",
    "MAX_PARTICLE_RATE",
    "MAX_WIND_SPEED",
    "ValidationError",
    "RuntimeJSON",
    "PresetSchema",
    "ForcefieldSchema",
    "ObstaclesSchema",
    "SequenceSchema",
    "ExporterSchema",
    "TimekeeperSchema",
    "UIHintsSchema",
    "AssetPackSchema",
    "clamp",
    "ensure_runtime_path",
]
