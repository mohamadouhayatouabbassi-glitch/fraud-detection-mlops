"""End-to-end smoke test using the real FastAPI app via TestClient.

Runs the same code path as a live HTTP call (Pydantic + features + rules + ML
+ decision + JSON serialisation) and prints the response. Use this as a
post-deploy verification or as a 1-line demo.

Usage:
    python scripts/smoke_test.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from fraud_detection.api.main import app

CASES = [
    {
        "label": "1) LEGIT in-country grocery POS  -> expect APPROVE",
        "payload": {
            "transaction_id": "TX_LEGIT_001",
            "timestamp": datetime(2025, 6, 15, 14, 0, tzinfo=timezone.utc).isoformat(),
            "customer_id": "C0000001",
            "card_id": "K0000001",
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
        },
    },
    {
        "label": "2) SUSPECT mix: CNP, geo mismatch, high-risk MCC, night  -> expect DECLINE/REVIEW",
        "payload": {
            "transaction_id": "TX_FRAUD_001",
            "timestamp": datetime(2025, 6, 15, 3, 10, tzinfo=timezone.utc).isoformat(),
            "customer_id": "C0000001",
            "card_id": "K0000001",
            "amount": 1500.0,
            "currency": "EUR",
            "merchant_id": "M999999",
            "merchant_country": "NG",
            "merchant_mcc": "7995",
            "card_country": "FR",
            "channel": "ECOM",
            "is_cnp": True,
            "customer_age_days": 900,
            "card_age_days": 400,
            "n_tx_last_1h": 4,
            "n_tx_last_24h": 10,
            "amount_avg_30d": 70.0,
            "amount_std_30d": 20.0,
            "distinct_countries_last_24h": 2,
        },
    },
    {
        "label": "3) HARD_BLOCK: amount > 5000 EUR  -> expect DECLINE on rules alone",
        "payload": {
            "transaction_id": "TX_HARD_001",
            "timestamp": datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc).isoformat(),
            "customer_id": "C0000001",
            "card_id": "K0000001",
            "amount": 7500.0,
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
        },
    },
    {
        "label": "4) VELOCITY HARD_BLOCK: 12 tx in last hour  -> expect DECLINE",
        "payload": {
            "transaction_id": "TX_VELO_001",
            "timestamp": datetime(2025, 6, 15, 9, 0, tzinfo=timezone.utc).isoformat(),
            "customer_id": "C0000001",
            "card_id": "K0000001",
            "amount": 30.0,
            "currency": "EUR",
            "merchant_id": "M111111",
            "merchant_country": "FR",
            "merchant_mcc": "5411",
            "card_country": "FR",
            "channel": "ECOM",
            "is_cnp": True,
            "customer_age_days": 1000,
            "card_age_days": 500,
            "n_tx_last_1h": 12,
            "n_tx_last_24h": 25,
            "amount_avg_30d": 50.0,
            "amount_std_30d": 15.0,
            "distinct_countries_last_24h": 1,
        },
    },
]


def main() -> int:
    with TestClient(app) as client:
        health = client.get("/healthz").json()
        print("=" * 78)
        print("HEALTH:", json.dumps(health, indent=2))
        print("=" * 78)
        for case in CASES:
            r = client.post(
                "/v1/score",
                json=case["payload"],
                headers={"X-Correlation-ID": case["payload"]["transaction_id"]},
            )
            body = r.json()
            print(case["label"])
            print(f"  HTTP {r.status_code}")
            print(
                f"  action={body['action']}  "
                f"p={body['fraud_probability']:.4f}  "
                f"risk_score={body['risk_score']}  "
                f"latency_ms={body['latency_ms']}"
            )
            if body["rule_hits"]:
                for h in body["rule_hits"]:
                    print(f"    rule_hit: {h['code']:<28s} severity={h['severity']}")
            print(f"  reasons: {body['reasons']}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
