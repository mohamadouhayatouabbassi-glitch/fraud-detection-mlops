"""Training pipeline.

Steps:
  1. Load raw transactions (parquet).
  2. Build features (single source of truth for train/serve parity).
  3. Time-based train/val split.
  4. Fit LightGBM with early stopping + class imbalance handling.
  5. Calibrate probabilities (isotonic) on the validation fold.
  6. Evaluate (ROC AUC, PR AUC, recall@1%FPR, business metrics).
  7. Persist artifact + feature schema + training stats.
  8. Log everything to MLflow.

The artifact persisted is a single joblib bundle containing the calibrated
sklearn pipeline + metadata. This keeps the serving layer simple (one file
to load, no glue code).
"""

from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from fraud_detection.features.build_features import (
    FEATURE_COLUMNS,
    build_features,
    select_feature_matrix,
)
from fraud_detection.utils.config import Settings, get_settings, load_yaml
from fraud_detection.utils.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Calibration wrapper. LightGBM exposes a sklearn-compatible API but we wrap
# it with CalibratedClassifierCV (prefit) so probabilities are well calibrated.
# ---------------------------------------------------------------------------
class _LGBMWrapper(ClassifierMixin, BaseEstimator):
    """Sklearn-compatible wrapper around a fitted LightGBM Booster.

    Used by `CalibratedClassifierCV` via `FrozenEstimator` so we can wrap an
    already-trained booster without sklearn trying to re-fit it.
    """

    def __init__(
        self,
        booster: lgb.Booster | None = None,
        feature_names: list[str] | None = None,
    ):
        self.booster = booster
        self.feature_names = feature_names
        # Setting classes_ here marks the estimator as "already fitted" so
        # FrozenEstimator's check_is_fitted passes immediately.
        self.classes_ = np.array([0, 1])

    def __sklearn_is_fitted__(self) -> bool:
        return self.booster is not None

    def fit(self, X, y):  # noqa: ARG002, N803
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):  # noqa: N803
        feat = self.feature_names or list(X.columns)
        if isinstance(X, np.ndarray):
            X = pd.DataFrame(X, columns=feat)
        p = self.booster.predict(X[feat])
        return np.column_stack([1 - p, p])

    def predict(self, X):  # noqa: N803
        return (self.predict_proba(X)[:, 1] > 0.5).astype(int)


@dataclass
class TrainingReport:
    roc_auc: float
    pr_auc: float
    recall_at_1pct_fpr: float
    precision_at_top_1pct: float
    f1_at_default_threshold: float
    n_train: int
    n_val: int
    n_test: int
    fraud_rate_train: float
    fraud_rate_val: float
    fraud_rate_test: float
    feature_importance: dict[str, float]


def _recall_at_fpr(y_true: np.ndarray, y_score: np.ndarray, target_fpr: float) -> float:
    """Recall achieved while keeping FPR below `target_fpr`."""
    order = np.argsort(-y_score)
    y_sorted = y_true[order]
    n_pos = int(y_true.sum())
    n_neg = int(len(y_true) - n_pos)
    if n_pos == 0 or n_neg == 0:
        return 0.0
    fp = np.cumsum(y_sorted == 0)
    tp = np.cumsum(y_sorted == 1)
    fpr = fp / n_neg
    tpr = tp / n_pos
    mask = fpr <= target_fpr
    return float(tpr[mask].max()) if mask.any() else 0.0


def _precision_at_top_k(y_true: np.ndarray, y_score: np.ndarray, k_pct: float) -> float:
    order = np.argsort(-y_score)
    k = max(1, int(len(y_true) * k_pct))
    return float(y_true[order[:k]].mean())


def _train_lgbm(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    params: dict[str, Any],
    num_boost_round: int,
    early_stopping_rounds: int,
) -> lgb.Booster:
    dtrain = lgb.Dataset(X_train, label=y_train)
    dval = lgb.Dataset(X_val, label=y_val, reference=dtrain)
    booster = lgb.train(
        params,
        dtrain,
        num_boost_round=num_boost_round,
        valid_sets=[dtrain, dval],
        valid_names=["train", "val"],
        callbacks=[
            lgb.early_stopping(early_stopping_rounds, verbose=False),
            lgb.log_evaluation(period=0),
        ],
    )
    return booster


def train_model(
    train_path: Path,
    test_path: Path,
    model_config_path: Path,
    settings: Settings | None = None,
) -> TrainingReport:
    settings = settings or get_settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_yaml(model_config_path)
    lgbm_params = cfg["lightgbm"]
    training_cfg = cfg["training"]

    log.info("loading_data", train=str(train_path), test=str(test_path))
    train_df_raw = pd.read_parquet(train_path)
    test_df_raw = pd.read_parquet(test_path)

    log.info("building_features")
    train_df = build_features(train_df_raw)
    test_df = build_features(test_df_raw)

    # Time-based val split: take the last val_fraction of the train set
    train_df = train_df.sort_values("timestamp").reset_index(drop=True)
    cut = int(len(train_df) * (1 - training_cfg["val_fraction"]))
    fit_df = train_df.iloc[:cut]
    val_df = train_df.iloc[cut:]

    X_fit = select_feature_matrix(fit_df)
    y_fit = fit_df["is_fraud"].astype(int).to_numpy()
    X_val = select_feature_matrix(val_df)
    y_val = val_df["is_fraud"].astype(int).to_numpy()
    X_test = select_feature_matrix(test_df)
    y_test = test_df["is_fraud"].astype(int).to_numpy()

    log.info(
        "split_sizes",
        n_fit=len(X_fit),
        n_val=len(X_val),
        n_test=len(X_test),
        fraud_rate_fit=float(y_fit.mean()),
        fraud_rate_val=float(y_val.mean()),
        fraud_rate_test=float(y_test.mean()),
    )

    # ---- MLflow ----
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment)
    run = mlflow.start_run(run_name=f"train-{datetime.now(UTC).isoformat()}")
    log.info("mlflow_run_started", run_id=run.info.run_id)
    try:
        mlflow.log_params({f"lgbm.{k}": v for k, v in lgbm_params.items()})
        mlflow.log_params(
            {
                "training.num_boost_round": training_cfg["num_boost_round"],
                "training.early_stopping_rounds": training_cfg["early_stopping_rounds"],
                "training.val_fraction": training_cfg["val_fraction"],
                "training.calibration_method": training_cfg["calibration_method"],
                "data.train_rows": len(train_df_raw),
                "data.test_rows": len(test_df_raw),
            }
        )

        log.info("fitting_lightgbm")
        booster = _train_lgbm(
            X_fit,
            y_fit,
            X_val,
            y_val,
            lgbm_params,
            training_cfg["num_boost_round"],
            training_cfg["early_stopping_rounds"],
        )

        log.info("calibrating")
        wrapper = _LGBMWrapper(booster, FEATURE_COLUMNS)
        # sklearn >=1.6 removed cv='prefit'; FrozenEstimator is the new way to
        # calibrate on top of an already-trained estimator.
        calibrator = CalibratedClassifierCV(
            FrozenEstimator(wrapper), method=training_cfg["calibration_method"]
        )
        calibrator.fit(X_val, y_val)

        # ---- Evaluation on held-out test set ----
        y_proba = calibrator.predict_proba(X_test)[:, 1]
        roc = float(roc_auc_score(y_test, y_proba))
        pr = float(average_precision_score(y_test, y_proba))
        r1 = _recall_at_fpr(y_test, y_proba, target_fpr=0.01)
        p_top1 = _precision_at_top_k(y_test, y_proba, k_pct=0.01)

        y_pred_default = (y_proba >= 0.5).astype(int)
        f1 = float(f1_score(y_test, y_pred_default))
        prec = float(precision_score(y_test, y_pred_default, zero_division=0))
        rec = float(recall_score(y_test, y_pred_default, zero_division=0))
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred_default).ravel()

        importance = dict(
            zip(
                FEATURE_COLUMNS,
                booster.feature_importance(importance_type="gain").tolist(),
                strict=True,
            )
        )
        # Normalise so the dict is human-readable
        total = sum(importance.values()) or 1.0
        importance = {k: round(v / total, 4) for k, v in importance.items()}

        report = TrainingReport(
            roc_auc=roc,
            pr_auc=pr,
            recall_at_1pct_fpr=r1,
            precision_at_top_1pct=p_top1,
            f1_at_default_threshold=f1,
            n_train=len(X_fit),
            n_val=len(X_val),
            n_test=len(X_test),
            fraud_rate_train=float(y_fit.mean()),
            fraud_rate_val=float(y_val.mean()),
            fraud_rate_test=float(y_test.mean()),
            feature_importance=importance,
        )

        mlflow.log_metrics(
            {
                "test.roc_auc": roc,
                "test.pr_auc": pr,
                "test.recall_at_1pct_fpr": r1,
                "test.precision_at_top_1pct": p_top1,
                "test.f1": f1,
                "test.precision_default": prec,
                "test.recall_default": rec,
                "test.tp": int(tp),
                "test.fp": int(fp),
                "test.fn": int(fn),
                "test.tn": int(tn),
            }
        )

        # ---- Persist artifact ----
        model_version = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        artifact = {
            "model": calibrator,
            "feature_columns": FEATURE_COLUMNS,
            "metadata": {
                "model_version": model_version,
                "trained_at": datetime.now(UTC).isoformat(),
                "python_version": platform.python_version(),
                "git_sha": os.environ.get("GIT_SHA", "unknown"),
                "lgbm_best_iteration": booster.best_iteration,
                "params": lgbm_params,
                "training": training_cfg,
                "report": asdict(report),
            },
        }
        model_path = settings.model_path
        joblib.dump(artifact, model_path)
        log.info("model_saved", path=str(model_path), version=model_version)

        # Feature schema (for online validation) + training stats (for drift)
        schema = {
            "feature_columns": FEATURE_COLUMNS,
            "model_version": model_version,
        }
        settings.feature_schema_path.write_text(json.dumps(schema, indent=2))

        train_stats = {
            col: {
                "mean": float(X_fit[col].mean()),
                "std": float(X_fit[col].std() + 1e-9),
                "p01": float(np.quantile(X_fit[col], 0.01)),
                "p99": float(np.quantile(X_fit[col], 0.99)),
            }
            for col in FEATURE_COLUMNS
        }
        settings.training_stats_path.write_text(json.dumps(train_stats, indent=2))

        mlflow.log_artifact(str(model_path))
        mlflow.log_artifact(str(settings.feature_schema_path))
        mlflow.log_artifact(str(settings.training_stats_path))

        log.info(
            "training_done",
            roc_auc=roc,
            pr_auc=pr,
            recall_at_1pct_fpr=r1,
            version=model_version,
        )
        return report
    finally:
        mlflow.end_run()
