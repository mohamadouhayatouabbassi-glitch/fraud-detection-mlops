"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from fraud_detection.data.schemas import Transaction


@pytest.fixture
def sample_transaction() -> Transaction:
    return Transaction(
        transaction_id="TX_TEST_0001",
        timestamp=datetime(2025, 6, 15, 14, 30, tzinfo=UTC),
        customer_id="C0000001",
        card_id="K0000001",
        amount=87.50,
        currency="EUR",
        merchant_id="M001234",
        merchant_country="FR",
        merchant_mcc="5411",
        card_country="FR",
        channel="POS",  # type: ignore[arg-type]
        is_cnp=False,
        customer_age_days=900,
        card_age_days=400,
        n_tx_last_1h=1,
        n_tx_last_24h=4,
        amount_avg_30d=70.0,
        amount_std_30d=20.0,
        distinct_countries_last_24h=1,
    )


@pytest.fixture
def fraud_transaction() -> Transaction:
    """A transaction matching multiple SUSPECT rules + high-risk ML pattern."""
    return Transaction(
        transaction_id="TX_FRAUD_0001",
        timestamp=datetime(2025, 6, 15, 3, 10, tzinfo=UTC),
        customer_id="C0000001",
        card_id="K0000001",
        amount=1500.0,
        currency="EUR",
        merchant_id="M999999",
        merchant_country="NG",
        merchant_mcc="7995",
        card_country="FR",
        channel="ECOM",  # type: ignore[arg-type]
        is_cnp=True,
        customer_age_days=900,
        card_age_days=400,
        n_tx_last_1h=4,
        n_tx_last_24h=10,
        amount_avg_30d=70.0,
        amount_std_30d=20.0,
        distinct_countries_last_24h=2,
    )


@pytest.fixture
def hard_block_transaction() -> Transaction:
    """A transaction that should be DECLINED by a HARD_BLOCK rule alone."""
    return Transaction(
        transaction_id="TX_HARD_0001",
        timestamp=datetime(2025, 6, 15, 12, 0, tzinfo=UTC),
        customer_id="C0000001",
        card_id="K0000001",
        amount=6500.0,  # > 5000 EUR -> R002_VERY_HIGH_AMOUNT
        currency="EUR",
        merchant_id="M001234",
        merchant_country="FR",
        merchant_mcc="5732",
        card_country="FR",
        channel="POS",  # type: ignore[arg-type]
        is_cnp=False,
        customer_age_days=900,
        card_age_days=400,
        n_tx_last_1h=1,
        n_tx_last_24h=4,
        amount_avg_30d=70.0,
        amount_std_30d=20.0,
        distinct_countries_last_24h=1,
    )


@pytest.fixture
def rules_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "configs" / "rules.yaml"
