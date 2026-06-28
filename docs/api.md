# API Reference

Auto-generated OpenAPI at `/docs` (Swagger UI) and `/redoc`. This file
captures the contract guarantees and SLAs around it.

## `POST /v1/score`

Score a single transaction.

### Request

`Content-Type: application/json`
Optional header: `X-Correlation-ID: <uuid>` — echoed back in the response.

```json
{
  "transaction_id": "string",
  "timestamp": "2025-06-15T03:10:00Z",
  "customer_id": "string",
  "card_id": "string",
  "amount": 0.0,
  "currency": "EUR",
  "merchant_id": "string",
  "merchant_country": "FR",
  "merchant_mcc": "5411",
  "card_country": "FR",
  "channel": "POS",
  "is_cnp": false,
  "customer_age_days": 0,
  "card_age_days": 0,
  "n_tx_last_1h": 0,
  "n_tx_last_24h": 0,
  "amount_avg_30d": 0.0,
  "amount_std_30d": 0.0,
  "distinct_countries_last_24h": 0
}
```

`channel` ∈ `{POS, ECOM, ATM, MOTO}`. Country codes are ISO-3166 alpha-2.
MCC is the 4-digit ISO 18245 code.

### Response

```json
{
  "transaction_id": "TX_001",
  "action": "REVIEW",
  "fraud_probability": 0.412345,
  "risk_score": 462,
  "reasons": [
    "rule:R001_HIGH_AMOUNT_CNP",
    "ml:p=0.462>=review_threshold"
  ],
  "rule_hits": [
    {"code": "R001_HIGH_AMOUNT_CNP", "severity": "SUSPECT", "description": "..."}
  ],
  "model_version": "20250615-031000",
  "latency_ms": 12.4
}
```

### Status codes

| Code | Meaning                                                      |
|------|--------------------------------------------------------------|
| 200  | Decision returned                                            |
| 422  | Validation error (malformed payload)                         |
| 500  | Internal error (logged with correlation_id, contact on-call) |
| 503  | Service not ready (model not loaded)                         |

### SLA

* Availability: 99.95% monthly.
* Latency p99: < 100 ms.
* Backwards compatibility: the response shape is stable within `/v1`.
  Any breaking change ships under `/v2`.

## `POST /v1/score/batch`

Same body wrapped under `{"transactions": [...]}`, up to 100 items per call.

## `GET /healthz`

```json
{ "status": "ok", "model_loaded": true, "model_version": "20250615-031000", "git_sha": "..." }
```

Returns `status: "degraded"` if the model failed to load.

## `GET /metrics`

Prometheus exposition format. See `docs/architecture.md` § Observability.
