"""End-to-end integration tests: real model artifact + real FastAPI app.

These tests train a tiny model on a small synthetic dataset, save the
artifact to a temp directory, point the service at it via env vars,
then exercise /healthz and /v1/score with httpx/TestClient.
"""

from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fraud_detection.data.synthetic import generate_transactions, save_dataset
from fraud_detection.models.train import train_model
from fraud_detection.utils.config import get_settings


@pytest.fixture(scope="module")
def trained_artifacts(tmp_path_factory) -> Path:
    """Train a small model once and reuse for all tests in the module."""
    workdir = tmp_path_factory.mktemp("fraud_e2e")
    data_dir = workdir / "data" / "processed"
    artifacts_dir = workdir / "artifacts"
    data_dir.mkdir(parents=True)
    artifacts_dir.mkdir(parents=True)

    # Configure the service to use the temp dirs
    import os

    os.environ["FRAUD_ARTIFACTS_DIR"] = str(artifacts_dir)
    os.environ["FRAUD_DATA_DIR"] = str(workdir / "data")
    # Reset the cached settings
    get_settings.cache_clear()  # type: ignore[attr-defined]

    df = generate_transactions(n_rows=8000, fraud_rate=0.03, n_customers=800, seed=11)
    train_path, test_path = save_dataset(df, data_dir)

    project_root = Path(__file__).resolve().parents[2]
    train_model(train_path, test_path, project_root / "configs" / "model.yaml")
    return workdir


@pytest.fixture(scope="module")
def client(trained_artifacts):
    """Spin up the FastAPI app pointing at the freshly trained artifact."""
    # Force re-import so lifespan runs against the new settings
    import fraud_detection.api.main as api_main

    importlib.reload(api_main)
    with TestClient(api_main.app) as c:
        yield c


@pytest.mark.integration
def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["model_version"]


@pytest.mark.integration
def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "fraud_decisions_total" in r.text


@pytest.mark.integration
def test_score_legit_transaction(client):
    payload = {
        "transaction_id": "TX_INT_LEGIT_001",
        "timestamp": datetime(2025, 6, 15, 14, 0, tzinfo=UTC).isoformat(),
        "customer_id": "C0000099",
        "card_id": "K0000099",
        "amount": 42.5,
        "currency": "EUR",
        "merchant_id": "M001234",
        "merchant_country": "FR",
        "merchant_mcc": "5411",
        "card_country": "FR",
        "channel": "POS",
        "is_cnp": False,
        "customer_age_days": 1000,
        "card_age_days": 500,
        "n_tx_last_1h": 1,
        "n_tx_last_24h": 3,
        "amount_avg_30d": 50.0,
        "amount_std_30d": 15.0,
        "distinct_countries_last_24h": 1,
    }
    r = client.post("/v1/score", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["transaction_id"] == "TX_INT_LEGIT_001"
    assert body["action"] in {"APPROVE", "REVIEW", "DECLINE"}
    assert 0.0 <= body["fraud_probability"] <= 1.0
    assert 0 <= body["risk_score"] <= 1000
    assert "model_version" in body


@pytest.mark.integration
def test_score_hard_block_transaction(client):
    payload = {
        "transaction_id": "TX_INT_HARD_001",
        "timestamp": datetime(2025, 6, 15, 12, 0, tzinfo=UTC).isoformat(),
        "customer_id": "C0000099",
        "card_id": "K0000099",
        "amount": 7500.0,  # > 5000 -> R002 HARD_BLOCK
        "currency": "EUR",
        "merchant_id": "M001234",
        "merchant_country": "FR",
        "merchant_mcc": "5732",
        "card_country": "FR",
        "channel": "POS",
        "is_cnp": False,
        "customer_age_days": 1000,
        "card_age_days": 500,
        "n_tx_last_1h": 1,
        "n_tx_last_24h": 2,
        "amount_avg_30d": 50.0,
        "amount_std_30d": 15.0,
        "distinct_countries_last_24h": 1,
    }
    r = client.post("/v1/score", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["action"] == "DECLINE"
    assert any(rh["code"] == "R002_VERY_HIGH_AMOUNT" for rh in body["rule_hits"])


@pytest.mark.integration
def test_invalid_payload_returns_422(client):
    bad = {"transaction_id": "x", "amount": -5}
    r = client.post("/v1/score", json=bad)
    assert r.status_code == 422


@pytest.mark.integration
def test_batch_endpoint(client):
    base = {
        "transaction_id": "TX_BATCH_1",
        "timestamp": datetime(2025, 6, 15, 14, 0, tzinfo=UTC).isoformat(),
        "customer_id": "C1",
        "card_id": "K1",
        "amount": 30.0,
        "currency": "EUR",
        "merchant_id": "M1",
        "merchant_country": "FR",
        "merchant_mcc": "5411",
        "card_country": "FR",
        "channel": "POS",
        "is_cnp": False,
        "customer_age_days": 500,
        "card_age_days": 300,
        "n_tx_last_1h": 0,
        "n_tx_last_24h": 1,
        "amount_avg_30d": 40.0,
        "amount_std_30d": 10.0,
        "distinct_countries_last_24h": 1,
    }
    payload = {"transactions": [{**base, "transaction_id": f"TX_BATCH_{i}"} for i in range(5)]}
    r = client.post("/v1/score/batch", json=payload)
    assert r.status_code == 200
    out = r.json()
    assert len(out) == 5
    assert all("action" in d for d in out)
