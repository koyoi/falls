"""UI hints agent surfaces tutorial suggestions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .schema import UIHintsSchema


@dataclass
class UIHintsRequest:
    tips: Iterable[str]
    recommended_presets: Iterable[str]


class UIHintsAgent:
    """Aggregate tutorial hints into schema compliant JSON."""

    def generate(self, request: UIHintsRequest) -> UIHintsSchema:
        return UIHintsSchema(tips=list(request.tips), recommended_presets=list(request.recommended_presets))


__all__ = ["UIHintsAgent", "UIHintsRequest"]
