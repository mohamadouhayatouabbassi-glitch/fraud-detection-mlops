"""Synthetic transaction generator with realistic fraud patterns.

We use synthetic data on purpose: the project is fully reproducible, no
proprietary or personal data leaves the repo. The generator implements
real-world fraud patterns so the ML model and the rules engine have
something meaningful to learn / catch:

  * Card testing : many small ECOM transactions in a short window.
  * Geo anomaly  : card issued in country A used in country B (CNP).
  * Cashout     : ATM at unusual hour, near max limit.
  * Account takeover : sudden burst of large transactions far from the
    customer's 30d average.
  * High-risk MCC : adult / gambling MCC for a customer that never uses
    them.

The generator is deterministic given a seed so training is reproducible.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from fraud_detection.data.schemas import KNOWN_MCC
from fraud_detection.utils.logging import get_logger

log = get_logger(__name__)


COUNTRIES = ["FR", "DE", "ES", "IT", "BE", "NL", "GB", "US", "MA", "RO", "NG", "BR"]
CHANNELS = ["POS", "ECOM", "ATM", "MOTO"]


def _rng(seed: int) -> tuple[np.random.Generator, random.Random]:
    return np.random.default_rng(seed), random.Random(seed)


def _draw_customers(n_customers: int, rng: np.random.Generator) -> pd.DataFrame:
    """Pre-compute customer behavioural baseline."""
    return pd.DataFrame(
        {
            "customer_id": [f"C{i:07d}" for i in range(n_customers)],
            "card_id": [f"K{i:07d}" for i in range(n_customers)],
            "home_country": rng.choice(
                COUNTRIES[:6], size=n_customers, p=[0.4, 0.2, 0.15, 0.1, 0.1, 0.05]
            ),
            "avg_amount": rng.lognormal(mean=3.5, sigma=0.6, size=n_customers).clip(5, 500),
            "std_amount": rng.uniform(2, 40, size=n_customers),
            "customer_age_days": rng.integers(30, 365 * 8, size=n_customers),
            "card_age_days": rng.integers(1, 365 * 4, size=n_customers),
        }
    )


def _legit_transaction(customer: pd.Series, ts: datetime, rng: np.random.Generator) -> dict:
    """Build a legitimate transaction respecting the customer's baseline.

    `ts` is unused inside this function but is part of the signature for
    symmetry with `_fraud_transaction`, which uses it.
    """
    del ts  # noqa: F841 — explicit "intentionally unused"
    amount = max(0.5, rng.normal(customer["avg_amount"], customer["std_amount"] + 1e-3))
    channel = rng.choice(CHANNELS, p=[0.55, 0.30, 0.13, 0.02])
    is_cnp = channel in ("ECOM", "MOTO")
    # Most transactions happen in home country
    same_country = rng.random() < 0.95
    merchant_country = customer["home_country"] if same_country else rng.choice(COUNTRIES)
    mcc = rng.choice([m for m in KNOWN_MCC if m not in ("7995", "5967")])

    return {
        "amount": round(float(amount), 2),
        "currency": "EUR",
        "merchant_id": f"M{rng.integers(0, 20000):06d}",
        "merchant_country": merchant_country,
        "merchant_mcc": mcc,
        "card_country": customer["home_country"],
        "channel": channel,
        "is_cnp": is_cnp,
        "n_tx_last_1h": int(max(0, rng.poisson(0.3))),
        "n_tx_last_24h": int(max(0, rng.poisson(3.0))),
        "amount_avg_30d": float(customer["avg_amount"]),
        "amount_std_30d": float(customer["std_amount"]),
        "distinct_countries_last_24h": int(rng.choice([1, 1, 1, 2], p=[0.7, 0.15, 0.1, 0.05])),
        "is_fraud": 0,
    }


def _fraud_transaction(
    customer: pd.Series, ts: datetime, rng: np.random.Generator, pattern: str
) -> dict:
    """Generate a fraud transaction following a specific attack pattern."""
    del ts  # noqa: F841 — accepted for signature symmetry, may be used later
    if pattern == "card_testing":
        amount = round(float(rng.uniform(0.5, 5.0)), 2)
        channel = "ECOM"
        is_cnp = True
        merchant_country = rng.choice(["US", "GB", "RO", "NG"])
        mcc = rng.choice(["5999", "5732", "5912"])
        n_1h = int(rng.integers(6, 20))
        n_24h = n_1h + int(rng.integers(0, 5))
        countries_24h = int(rng.integers(2, 5))

    elif pattern == "geo_anomaly":
        amount = round(float(rng.uniform(80, 600)), 2)
        channel = "ECOM"
        is_cnp = True
        # Card used far from issuing country
        foreign = [c for c in COUNTRIES if c != customer["home_country"]]
        merchant_country = rng.choice(foreign)
        mcc = rng.choice(["5732", "5999", "5812"])
        n_1h = int(rng.integers(1, 4))
        n_24h = int(rng.integers(2, 7))
        countries_24h = int(rng.integers(2, 4))

    elif pattern == "cashout":
        amount = round(float(rng.uniform(400, 950)), 2)
        channel = "ATM"
        is_cnp = False
        merchant_country = rng.choice([customer["home_country"], rng.choice(COUNTRIES)])
        mcc = "6011"
        n_1h = int(rng.integers(2, 6))
        n_24h = int(rng.integers(3, 10))
        countries_24h = int(rng.integers(1, 3))

    elif pattern == "account_takeover":
        # Amounts far above the customer's 30d average
        multiplier = float(rng.uniform(6, 15))
        amount = round(float(customer["avg_amount"]) * multiplier, 2)
        channel = rng.choice(["ECOM", "POS"], p=[0.7, 0.3])
        is_cnp = channel == "ECOM"
        merchant_country = rng.choice(COUNTRIES)
        mcc = rng.choice(["5732", "5999"])
        n_1h = int(rng.integers(1, 5))
        n_24h = int(rng.integers(2, 8))
        countries_24h = int(rng.integers(1, 3))

    else:  # high_risk_mcc
        amount = round(float(rng.uniform(100, 800)), 2)
        channel = "ECOM"
        is_cnp = True
        merchant_country = rng.choice(COUNTRIES)
        mcc = rng.choice(["7995", "5967"])
        n_1h = int(rng.integers(1, 4))
        n_24h = int(rng.integers(2, 6))
        countries_24h = int(rng.integers(1, 3))

    return {
        "amount": amount,
        "currency": "EUR",
        "merchant_id": f"M{rng.integers(0, 20000):06d}",
        "merchant_country": merchant_country,
        "merchant_mcc": mcc,
        "card_country": customer["home_country"],
        "channel": channel,
        "is_cnp": is_cnp,
        "n_tx_last_1h": n_1h,
        "n_tx_last_24h": n_24h,
        "amount_avg_30d": float(customer["avg_amount"]),
        "amount_std_30d": float(customer["std_amount"]),
        "distinct_countries_last_24h": countries_24h,
        "is_fraud": 1,
    }


FRAUD_PATTERNS = ("card_testing", "geo_anomaly", "cashout", "account_takeover", "high_risk_mcc")


def generate_transactions(
    n_rows: int = 200_000,
    fraud_rate: float = 0.012,
    n_customers: int = 20_000,
    seed: int = 42,
    start_date: datetime | None = None,
) -> pd.DataFrame:
    """Generate a labelled transactions dataset."""
    np_rng, py_rng = _rng(seed)
    start = start_date or datetime(2025, 1, 1, tzinfo=UTC)

    customers = _draw_customers(n_customers, np_rng)
    n_fraud = int(n_rows * fraud_rate)
    n_legit = n_rows - n_fraud
    log.info(
        "generating_transactions",
        n_rows=n_rows,
        n_legit=n_legit,
        n_fraud=n_fraud,
        n_customers=n_customers,
        seed=seed,
    )

    rows: list[dict] = []
    # Legit transactions
    legit_customer_idx = np_rng.integers(0, n_customers, size=n_legit)
    for i, ci in enumerate(legit_customer_idx):
        ts = start + timedelta(seconds=int(np_rng.integers(0, 90 * 24 * 3600)))
        cust = customers.iloc[ci]
        row = _legit_transaction(cust, ts, np_rng)
        row.update(
            {
                "transaction_id": f"T{i:09d}",
                "timestamp": ts,
                "customer_id": cust["customer_id"],
                "card_id": cust["card_id"],
                "customer_age_days": int(cust["customer_age_days"]),
                "card_age_days": int(cust["card_age_days"]),
            }
        )
        rows.append(row)

    # Fraud transactions
    fraud_customer_idx = np_rng.integers(0, n_customers, size=n_fraud)
    fraud_patterns = np_rng.choice(FRAUD_PATTERNS, size=n_fraud, p=[0.30, 0.25, 0.15, 0.20, 0.10])
    for i, (ci, pat) in enumerate(zip(fraud_customer_idx, fraud_patterns, strict=True)):
        ts = start + timedelta(seconds=int(np_rng.integers(0, 90 * 24 * 3600)))
        # Frauds skew toward unusual hours (0-5 AM)
        if np_rng.random() < 0.35:
            ts = ts.replace(hour=int(np_rng.integers(0, 6)))
        cust = customers.iloc[ci]
        row = _fraud_transaction(cust, ts, np_rng, str(pat))
        row.update(
            {
                "transaction_id": f"F{i:09d}",
                "timestamp": ts,
                "customer_id": cust["customer_id"],
                "card_id": cust["card_id"],
                "customer_age_days": int(cust["customer_age_days"]),
                "card_age_days": int(cust["card_age_days"]),
                "fraud_pattern": pat,
            }
        )
        rows.append(row)

    df = pd.DataFrame(rows)
    # Random shuffle + sort by timestamp for realism
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def save_dataset(df: pd.DataFrame, out_dir: Path, val_size: float = 0.2) -> tuple[Path, Path]:
    """Time-based split: oldest 80% to train, newest 20% to test."""
    out_dir.mkdir(parents=True, exist_ok=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    cut = int(len(df) * (1 - val_size))
    train_df = df.iloc[:cut]
    test_df = df.iloc[cut:]
    train_path = out_dir / "transactions_train.parquet"
    test_path = out_dir / "transactions_test.parquet"
    train_df.to_parquet(train_path, index=False)
    test_df.to_parquet(test_path, index=False)
    log.info(
        "dataset_saved",
        train_rows=len(train_df),
        test_rows=len(test_df),
        train_fraud_rate=float(train_df["is_fraud"].mean()),
        test_fraud_rate=float(test_df["is_fraud"].mean()),
        train_path=str(train_path),
        test_path=str(test_path),
    )
    return train_path, test_path
