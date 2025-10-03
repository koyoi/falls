"""Asset pack agent ensures runtime assets are catalogued."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .schema import AssetPackSchema


@dataclass
class AssetPackRequest:
    required_assets: Iterable[str]
    available_assets: Iterable[str]


class AssetPackAgent:
    """Produce asset pack reports listing missing dependencies."""

    def generate(self, request: AssetPackRequest) -> AssetPackSchema:
        required = list(dict.fromkeys(request.required_assets))
        available = set(request.available_assets)
        missing = [asset for asset in required if asset not in available]
        return AssetPackSchema(required_assets=required, missing_assets=missing)


__all__ = ["AssetPackAgent", "AssetPackRequest"]
