"""Centralised configuration loaded from env vars + YAML files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime settings, overridable through env vars (12-factor)."""

    model_config = SettingsConfigDict(env_prefix="FRAUD_", env_file=".env", extra="ignore")

    # General
    log_level: str = "INFO"
    environment: str = "dev"

    # Paths (overridable)
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    artifacts_dir: Path = PROJECT_ROOT / "artifacts"
    configs_dir: Path = PROJECT_ROOT / "configs"

    # Model
    model_artifact_name: str = "model.joblib"
    feature_schema_name: str = "feature_schema.json"
    training_stats_name: str = "training_stats.json"

    # Decision thresholds (will be loaded from YAML but provide defaults)
    threshold_review: float = Field(0.30, ge=0.0, le=1.0)
    threshold_decline: float = Field(0.70, ge=0.0, le=1.0)

    # MLflow
    mlflow_tracking_uri: str = f"sqlite:///{(PROJECT_ROOT / 'mlruns.db').as_posix()}"
    mlflow_experiment: str = "fraud-detection"

    @property
    def model_path(self) -> Path:
        return self.artifacts_dir / self.model_artifact_name

    @property
    def feature_schema_path(self) -> Path:
        return self.artifacts_dir / self.feature_schema_name

    @property
    def training_stats_path(self) -> Path:
        return self.artifacts_dir / self.training_stats_name


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
