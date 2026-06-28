"""Synthetic data generator smoke tests."""

from __future__ import annotations

import pytest

from fraud_detection.data.synthetic import FRAUD_PATTERNS, generate_transactions


def test_generate_transactions_basic():
    df = generate_transactions(n_rows=2000, fraud_rate=0.02, n_customers=200, seed=7)
    assert len(df) == 2000
    assert df["is_fraud"].mean() == pytest.approx(0.02, abs=0.005)
    # All required columns are present (sample)
    for col in [
        "transaction_id",
        "timestamp",
        "customer_id",
        "amount",
        "merchant_country",
        "card_country",
        "merchant_mcc",
        "channel",
        "is_cnp",
        "n_tx_last_1h",
        "amount_avg_30d",
        "is_fraud",
    ]:
        assert col in df.columns, f"missing column: {col}"


def test_generate_transactions_deterministic():
    df1 = generate_transactions(n_rows=1000, fraud_rate=0.02, n_customers=100, seed=42)
    df2 = generate_transactions(n_rows=1000, fraud_rate=0.02, n_customers=100, seed=42)
    assert df1.equals(df2)


def test_all_fraud_patterns_appear():
    df = generate_transactions(n_rows=20_000, fraud_rate=0.05, n_customers=2000, seed=42)
    frauds = df[df["is_fraud"] == 1]
    patterns_seen = set(frauds["fraud_pattern"].dropna().unique())
    assert patterns_seen == set(FRAUD_PATTERNS)
