"""Feature engineering shared between training and online inference.

KEY INVARIANT: this module is the SINGLE source of truth for feature
construction. Both the training pipeline and the live API call the same
function. Any feature added here is automatically available everywhere.

This avoids the classic "training/serving skew" bug.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fraud_detection.data.schemas import Transaction

# Ordered list of feature columns the model consumes. Order matters because
# LightGBM accepts numpy arrays; we always go through the DataFrame though.
FEATURE_COLUMNS: list[str] = [
    # Numeric raw
    "amount",
    "amount_log",
    "customer_age_days",
    "card_age_days",
    "n_tx_last_1h",
    "n_tx_last_24h",
    "amount_avg_30d",
    "amount_std_30d",
    "distinct_countries_last_24h",
    # Behavioural derived
    "amount_ratio_avg_30d",
    "amount_zscore_30d",
    "velocity_score",
    "is_burst_1h",
    # Temporal
    "hour",
    "is_night",
    "is_weekend",
    # Geo
    "is_geo_mismatch",
    # Channel / MCC
    "is_cnp",
    "is_ecom",
    "is_atm",
    "is_high_risk_mcc",
]

HIGH_RISK_MCC = {"7995", "5967"}  # Gambling, adult content


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build the model's feature matrix from a DataFrame of raw transactions.

    The input DataFrame must contain at least the columns from `Transaction`.
    Output keeps the input columns and adds the derived ones.
    """
    out = df.copy()

    # Ensure timestamp is timezone-aware datetime
    if not pd.api.types.is_datetime64_any_dtype(out["timestamp"]):
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)

    # Numeric transforms
    out["amount_log"] = np.log1p(out["amount"].astype(float))

    # Behavioural derived (handle division-by-zero defensively)
    avg = out["amount_avg_30d"].replace(0, np.nan)
    std = out["amount_std_30d"].replace(0, np.nan)
    out["amount_ratio_avg_30d"] = (out["amount"] / avg).fillna(1.0).clip(0, 100)
    out["amount_zscore_30d"] = (
        ((out["amount"] - out["amount_avg_30d"]) / std).fillna(0.0).clip(-20, 20)
    )

    # Velocity score: weighted sum, normalised
    out["velocity_score"] = (
        out["n_tx_last_1h"].astype(float) * 3.0 + out["n_tx_last_24h"].astype(float)
    ) / 10.0
    out["is_burst_1h"] = (out["n_tx_last_1h"] >= 5).astype(int)

    # Temporal
    ts = out["timestamp"]
    out["hour"] = ts.dt.hour.astype(int)
    out["is_night"] = ts.dt.hour.between(0, 5, inclusive="both").astype(int)
    out["is_weekend"] = ts.dt.dayofweek.isin([5, 6]).astype(int)

    # Geo
    out["is_geo_mismatch"] = (
        out["merchant_country"].astype(str).str.upper()
        != out["card_country"].astype(str).str.upper()
    ).astype(int)

    # Channel
    out["is_cnp"] = out["is_cnp"].astype(int)
    out["is_ecom"] = (out["channel"].astype(str) == "ECOM").astype(int)
    out["is_atm"] = (out["channel"].astype(str) == "ATM").astype(int)

    # MCC
    out["is_high_risk_mcc"] = out["merchant_mcc"].astype(str).isin(HIGH_RISK_MCC).astype(int)

    return out


def select_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Project a feature-enriched DataFrame onto the columns the model expects."""
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    return df[FEATURE_COLUMNS].astype(float)


def transaction_to_feature_row(tx: Transaction) -> pd.DataFrame:
    """Online path: build a single-row feature matrix from a Transaction object."""
    payload: dict[str, Any] = tx.model_dump()
    channel = payload["channel"]
    payload["channel"] = channel.value if hasattr(channel, "value") else channel
    df = pd.DataFrame([payload])
    enriched = build_features(df)
    return enriched
