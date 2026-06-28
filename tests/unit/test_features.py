"""Feature engineering unit tests."""

from __future__ import annotations

import pandas as pd

from fraud_detection.features.build_features import (
    FEATURE_COLUMNS,
    build_features,
    select_feature_matrix,
    transaction_to_feature_row,
)


def test_feature_columns_are_unique_and_non_empty():
    assert len(FEATURE_COLUMNS) == len(set(FEATURE_COLUMNS))
    assert len(FEATURE_COLUMNS) > 0


def test_transaction_to_feature_row_returns_all_features(sample_transaction):
    df = transaction_to_feature_row(sample_transaction)
    matrix = select_feature_matrix(df)
    assert list(matrix.columns) == FEATURE_COLUMNS
    assert len(matrix) == 1


def test_geo_mismatch_flag(sample_transaction, fraud_transaction):
    legit = transaction_to_feature_row(sample_transaction)
    fraud = transaction_to_feature_row(fraud_transaction)
    assert legit["is_geo_mismatch"].iloc[0] == 0
    assert fraud["is_geo_mismatch"].iloc[0] == 1


def test_high_risk_mcc_flag(sample_transaction, fraud_transaction):
    legit = transaction_to_feature_row(sample_transaction)
    fraud = transaction_to_feature_row(fraud_transaction)
    assert legit["is_high_risk_mcc"].iloc[0] == 0
    assert fraud["is_high_risk_mcc"].iloc[0] == 1


def test_night_flag(sample_transaction, fraud_transaction):
    legit = transaction_to_feature_row(sample_transaction)  # 14:30 UTC
    fraud = transaction_to_feature_row(fraud_transaction)  # 03:10 UTC
    assert legit["is_night"].iloc[0] == 0
    assert fraud["is_night"].iloc[0] == 1


def test_amount_ratio_avg_30d_handles_zero_average():
    df = pd.DataFrame(
        [
            {
                "transaction_id": "T0",
                "timestamp": "2025-01-01T00:00:00Z",
                "customer_id": "C0",
                "card_id": "K0",
                "amount": 50.0,
                "currency": "EUR",
                "merchant_id": "M0",
                "merchant_country": "FR",
                "merchant_mcc": "5411",
                "card_country": "FR",
                "channel": "POS",
                "is_cnp": False,
                "customer_age_days": 100,
                "card_age_days": 50,
                "n_tx_last_1h": 0,
                "n_tx_last_24h": 0,
                "amount_avg_30d": 0.0,
                "amount_std_30d": 0.0,
                "distinct_countries_last_24h": 1,
            }
        ]
    )
    out = build_features(df)
    # zero division must not produce inf/nan
    assert out["amount_ratio_avg_30d"].iloc[0] == 1.0
    assert out["amount_zscore_30d"].iloc[0] == 0.0
