from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from agents.forcefield_agent import ForceEventSpec, ForceFieldAgent, ForcefieldConstraints, ForcefieldRequest
from agents.preset_agent import PresetAgent, PresetConstraints, PresetRequest
from agents.schema import MAX_PARTICLE_RATE, clamp


class SchemaClampTests(unittest.TestCase):
    def test_clamp_enforces_bounds(self) -> None:
        self.assertEqual(clamp(500.0, min_value=0.0, max_value=200.0), 200.0)
        self.assertEqual(clamp(-10.0, min_value=0.0, max_value=200.0), 0.0)


class PresetAgentTests(unittest.TestCase):
    def test_particle_rate_is_clamped(self) -> None:
        agent = PresetAgent(PresetConstraints(max_particles=1_000))
        schema = agent.generate(
            PresetRequest(prompt="storm of petals", desired_rate=MAX_PARTICLE_RATE * 2, base_name="Storm")
        )
        self.assertLessEqual(schema.emitter.rate_per_sec, 1_000)


class ForcefieldAgentTests(unittest.TestCase):
    def test_wind_speed_is_clamped(self) -> None:
        agent = ForceFieldAgent(ForcefieldConstraints(max_speed=150.0))
        schema = agent.generate(
            ForcefieldRequest(
                prompt="intense gust",
                events=[ForceEventSpec(t=0.0, type="gust", dir_deg=90.0, speed=500.0, dur=5.0)],
            )
        )
        self.assertEqual(schema.timeline[0].speed, 150.0)


class CLITests(unittest.TestCase):
    def test_cli_generates_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            runtime_dir = repo_root / "runtime"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            subprocess.check_call(
                [
                    sys.executable,
                    str(Path(__file__).resolve().parents[1] / "tools" / "generate_runtime_files.py"),
                    "--repo-root",
                    str(repo_root),
                ]
            )
            preset_path = runtime_dir / "preset.json"
            self.assertTrue(preset_path.exists())
            data = json.loads(preset_path.read_text(encoding="utf-8"))
            self.assertEqual(data["version"], "1.0")


if __name__ == "__main__":
    unittest.main()
