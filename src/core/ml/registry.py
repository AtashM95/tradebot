from __future__ import annotations

from dataclasses import dataclass

from src.core.contracts import ModelVersionMeta


@dataclass
class ModelRegistry:
    active: ModelVersionMeta | None = None

    def promote(self, meta: ModelVersionMeta) -> None:
        self.active = meta

    def rollback(self, meta: ModelVersionMeta) -> None:
        self.active = meta
