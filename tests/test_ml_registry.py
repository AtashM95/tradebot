from pathlib import Path

from src.core.ml.registry import ModelRegistry


def test_model_registry_persists_and_sets_active(tmp_path: Path):
    registry = ModelRegistry(base_dir=tmp_path)
    entry = registry.register_model(
        model_id="model-a",
        artifact_path=str(tmp_path / "model-a.pkl"),
        metrics={"f1": 0.8},
        feature_list=["a", "b"],
        algorithm="rule_based",
        set_active=True,
    )
    assert entry["active"] is True
    assert registry.get_active_model()["model_id"] == "model-a"
    registry.register_model(
        model_id="model-b",
        artifact_path=str(tmp_path / "model-b.pkl"),
        metrics={"f1": 0.9},
        feature_list=["a", "b"],
        algorithm="rule_based",
        set_active=False,
    )
    registry.set_active_model("model-b")
    assert registry.get_active_model()["model_id"] == "model-b"
