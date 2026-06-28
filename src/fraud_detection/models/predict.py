"""Inference-side model wrapper. Loaded once at API startup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from fraud_detection.features.build_features import select_feature_matrix
from fraud_detection.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class FraudModel:
    """Thin wrapper around the persisted artifact.

    Holds the calibrated estimator + the feature column ordering + metadata.
    The .predict_proba method is the hot path used by the API.
    """

    estimator: Any
    feature_columns: list[str]
    metadata: dict[str, Any]

    @property
    def version(self) -> str:
        return str(self.metadata.get("model_version", "unknown"))

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        """Return P(fraud) for each row."""
        X = select_feature_matrix(features)
        return self.estimator.predict_proba(X)[:, 1]

    def predict_one(self, features_row: pd.DataFrame) -> float:
        return float(self.predict_proba(features_row)[0])


def load_model(path: Path) -> FraudModel:
    log.info("loading_model", path=str(path))
    bundle = joblib.load(path)
    model = FraudModel(
        estimator=bundle["model"],
        feature_columns=bundle["feature_columns"],
        metadata=bundle["metadata"],
    )
    log.info("model_loaded", version=model.version)
    return model
