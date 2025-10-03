"""Utility script to generate runtime JSON files using agents."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents import (  # noqa: E402  # pylint: disable=wrong-import-position
    AssetPackAgent,
    AssetPackRequest,
    ExporterAgent,
    ExporterRequest,
    ForceFieldAgent,
    ForceEventSpec,
    ForcefieldRequest,
    ObstacleAgent,
    ObstacleRequest,
    PresetAgent,
    PresetRequest,
    SequenceAgent,
    SequenceRequest,
    TimekeeperAgent,
    TimekeeperRequest,
    UIHintsAgent,
    UIHintsRequest,
)
from agents.schema import (  # noqa: E402  # pylint: disable=wrong-import-position
    CaptureSettings,
    ClearRule,
    DrawOp,
    SeasonalAdjust,
    SequenceTrack,
)

DEFAULT_OUTPUTS = {
    "preset": "preset.json",
    "forcefield": "forcefield.json",
    "sequence": "sequence.json",
    "timefx": "timefx.json",
    "uihints": "uihints.json",
    "exporter": "capture.json",
    "assets": "assets.json",
    "obstacles": "obstacles.json",
}


def write_json(data: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_preset(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config:
        return None
    request = PresetRequest(
        prompt=config["prompt"],
        palette=config.get("palette"),
        emitter_type=config.get("emitter_type", "generic"),
        base_name=config.get("base_name", config.get("prompt", "preset")),
        desired_rate=config.get("desired_rate", 2000),
        burst_interval=config.get("burst", {}).get("interval_sec"),
        burst_count=config.get("burst", {}).get("count"),
        sprite=config.get("sprite", "res://runtime/preset_sprite.png"),
        notes=config.get("notes"),
    )
    schema = PresetAgent().generate(request)
    return schema.to_dict()


def build_forcefield(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config:
        return None
    event_specs = [
        ForceEventSpec(
            t=event.get("t", 0.0),
            type=event["type"],
            dir_deg=event.get("dir_deg"),
            speed=event.get("speed"),
            dur=event.get("dur"),
            center=event.get("center"),
            radius=event.get("radius"),
            vortex=event.get("vortex"),
        )
        for event in config.get("events", [])
    ]
    schema = ForceFieldAgent().generate(
        ForcefieldRequest(
            prompt=config.get("prompt", ""),
            events=event_specs,
            use_prebaked_texture=config.get("use_prebaked_texture", False),
        )
    )
    return schema.to_dict()


def build_obstacles(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config:
        return None
    clear_rules = [ClearRule(**rule) for rule in config.get("clear_rules", [])]
    draw_ops = [DrawOp(**op) for op in config.get("draw_ops", [])]
    schema = ObstacleAgent().generate(
        ObstacleRequest(
            clear_rules=clear_rules,
            draw_ops=draw_ops,
            mask_path=config.get("mask_path", "res://runtime/obstacles_mask.png"),
        )
    )
    return schema.to_dict()


def build_sequence(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config:
        return None
    tracks = [SequenceTrack(t=track.get("t", 0.0), apply=track.get("apply", {})) for track in config.get("tracks", [])]
    schema = SequenceAgent().generate(SequenceRequest(tracks=tracks, loop=config.get("loop", True)))
    return schema.to_dict()


def build_timekeeper(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config:
        return None
    adjustments = [
        SeasonalAdjust(parameter=adj["parameter"], values=adj.get("values", {}))
        for adj in config.get("adjustments", [])
    ]
    schema = TimekeeperAgent().generate(
        TimekeeperRequest(region=config.get("region", "UTC"), adjustments=adjustments)
    )
    return schema.to_dict()


def build_uihints(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config:
        return None
    schema = UIHintsAgent().generate(
        UIHintsRequest(tips=config.get("tips", []), recommended_presets=config.get("recommended_presets", []))
    )
    return schema.to_dict()


def build_exporter(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config:
        return None
    capture = (
        CaptureSettings(**config["capture"]) if config.get("capture") else CaptureSettings("video", 1920, 1080, 60, 10.0)
    )
    schema = ExporterAgent().generate(
        ExporterRequest(capture=capture, watermark=config.get("watermark"), seed=config.get("seed"))
    )
    return schema.to_dict()


def build_assets(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config:
        return None
    schema = AssetPackAgent().generate(
        AssetPackRequest(
            required_assets=config.get("required_assets", []),
            available_assets=config.get("available_assets", []),
        )
    )
    return schema.to_dict()


BUILDERS = {
    "preset": build_preset,
    "forcefield": build_forcefield,
    "obstacles": build_obstacles,
    "sequence": build_sequence,
    "timefx": build_timekeeper,
    "uihints": build_uihints,
    "exporter": build_exporter,
    "assets": build_assets,
}


def generate_files(config: Dict[str, Any], repo_root: Path) -> Dict[str, Path]:
    outputs: Dict[str, Path] = {}
    for key, builder in BUILDERS.items():
        section = config.get(key)
        result = builder(section) if section is not None else None
        if result is None:
            continue
        filename = DEFAULT_OUTPUTS[key]
        output_path = repo_root / "runtime" / filename
        write_json(result, output_path)
        outputs[key] = output_path
    return outputs


def load_config(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return {
            "preset": {
                "prompt": "Sample petals gently swaying",
                "palette": ["#ffd6e7", "#ffc1dc", "#ffe9f2"],
            },
            "forcefield": {
                "prompt": "Calm breeze with a short gust",
                "events": [
                    {"t": 0, "type": "wind", "dir_deg": 180, "speed": 120},
                    {"t": 30, "type": "gust", "dir_deg": 150, "speed": 240, "dur": 6},
                ],
            },
            "sequence": {
                "tracks": [
                    {
                        "t": 0,
                        "apply": {
                            "preset": "res://runtime/preset.json",
                            "force": "res://runtime/forcefield.json",
                        },
                    }
                ],
                "loop": True,
            },
        }
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate runtime JSON files using the agent package")
    parser.add_argument("--config", type=Path, help="JSON file describing agent inputs", default=None)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    outputs = generate_files(config, args.repo_root)
    for name, path in outputs.items():
        print(f"wrote {name}: {path}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
