from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.contracts import ModelVersionMeta


@dataclass
class ModelRegistry:
    base_dir: Path

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self.base_dir / "registry.json"
        if not self._registry_path.exists():
            self._registry_path.write_text(json.dumps({"models": []}, indent=2), encoding="utf-8")

    def _load(self) -> Dict[str, Any]:
        return json.loads(self._registry_path.read_text(encoding="utf-8"))

    def _save(self, payload: Dict[str, Any]) -> None:
        self._registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def register_model(
        self,
        model_id: str,
        artifact_path: str,
        metrics: Dict[str, float],
        feature_list: List[str],
        algorithm: str,
        trained_range: str = "unknown",
        feature_schema: str = "v1",
        set_active: bool = False,
    ) -> Dict[str, Any]:
        payload = self._load()
        entry = {
            "model_id": model_id,
            "artifact_path": artifact_path,
            "metrics": metrics,
            "feature_list": feature_list,
            "algorithm": algorithm,
            "trained_range": trained_range,
            "feature_schema": feature_schema,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": False,
        }
        payload["models"] = [m for m in payload.get("models", []) if m.get("model_id") != model_id]
        if set_active:
            for model in payload["models"]:
                model["active"] = False
            entry["active"] = True
        payload["models"].append(entry)
        self._save(payload)
        return entry

    def list_models(self) -> List[Dict[str, Any]]:
        payload = self._load()
        return list(payload.get("models", []))

    def get_active_model(self) -> Optional[Dict[str, Any]]:
        for model in self.list_models():
            if model.get("active"):
                return model
        return None

    def set_active_model(self, model_id: str) -> None:
        payload = self._load()
        updated = False
        for model in payload.get("models", []):
            if model.get("model_id") == model_id:
                model["active"] = True
                updated = True
            else:
                model["active"] = False
        if not updated:
            raise ValueError(f"Model {model_id} not found in registry.")
        self._save(payload)

    def promote(self, meta: ModelVersionMeta) -> None:
        self.set_active_model(meta.model_id)

    def rollback(self, meta: ModelVersionMeta) -> None:
        self.set_active_model(meta.model_id)


def register_model(
    model_dir: str,
    model_id: str,
    artifact_path: str,
    metrics: Dict[str, float],
    feature_list: List[str],
    algorithm: str,
    trained_range: str = "unknown",
    feature_schema: str = "v1",
    set_active: bool = False,
) -> Dict[str, Any]:
    registry = ModelRegistry(base_dir=Path(model_dir))
    return registry.register_model(
        model_id=model_id,
        artifact_path=artifact_path,
        metrics=metrics,
        feature_list=feature_list,
        algorithm=algorithm,
        trained_range=trained_range,
        feature_schema=feature_schema,
        set_active=set_active,
    )


def list_models(model_dir: str) -> List[Dict[str, Any]]:
    registry = ModelRegistry(base_dir=Path(model_dir))
    return registry.list_models()


def get_active_model(model_dir: str) -> Optional[Dict[str, Any]]:
    registry = ModelRegistry(base_dir=Path(model_dir))
    return registry.get_active_model()


def set_active_model(model_dir: str, model_id: str) -> None:
    registry = ModelRegistry(base_dir=Path(model_dir))
    registry.set_active_model(model_id)
