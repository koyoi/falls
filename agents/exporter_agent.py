"""Exporter agent prepares capture instructions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .schema import CaptureSettings, ExporterSchema


@dataclass
class ExporterRequest:
    capture: CaptureSettings
    watermark: Optional[dict] = None
    seed: Optional[int] = None


class ExporterAgent:
    """Compose exporter schemas suitable for runtime consumption."""

    def generate(self, request: ExporterRequest) -> ExporterSchema:
        return ExporterSchema(capture=request.capture, watermark=request.watermark, seed=request.seed)


__all__ = ["ExporterAgent", "ExporterRequest"]
