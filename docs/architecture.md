# Architecture

## 1. Components

| Component         | Role                                                                      | Code path                                    |
|-------------------|---------------------------------------------------------------------------|----------------------------------------------|
| Transaction schema| Strict input contract (Pydantic v2)                                       | `src/fraud_detection/data/schemas.py`        |
| Feature builder   | Derives ~20 features used by both training and serving                    | `src/fraud_detection/features/build_features.py` |
| Rules engine      | Declarative YAML rules, evaluates against the feature row                 | `src/fraud_detection/rules/engine.py`        |
| ML model          | LightGBM with isotonic probability calibration                            | `src/fraud_detection/models/`                |
| Decision engine   | Combines rules + ML into APPROVE / REVIEW / DECLINE                        | `src/fraud_detection/decision/engine.py`     |
| API               | FastAPI, lifespan hooks, correlation ID middleware                        | `src/fraud_detection/api/main.py`            |
| Monitoring        | Prometheus metrics + PSI drift                                            | `src/fraud_detection/monitoring/`            |

## 2. Online request flow

```
HTTP POST /v1/score
       |
       v
[Pydantic Transaction]   <-- 422 on malformed payload
       |
       v
[transaction_to_feature_row]
       |
       v
[RulesEngine.evaluate]     -- hits[]
       |
       +-- if HARD_BLOCK -----> skip ML, force DECLINE
       |
       v
[FraudModel.predict_one]   -- p_ml
       |
       v
[DecisionEngine.decide]    -- action, risk_score, reasons
       |
       v
[DecisionResponse]         -- structured JSON
```

## 3. Why split rules and ML?

Rules and ML model **different things**:

* Rules encode **regulatory and policy constraints** (e.g. transaction
  above 5000 EUR must be reviewed). They are **deterministic, explainable,
  and easy to audit**. The Risk team owns them.
* ML captures **subtle, multi-variate patterns** that no human can encode
  exhaustively (e.g. unusual combinations of MCC + amount + velocity).
  The DS team owns the model.

Mixing them in one black box (e.g. injecting business rules as features)
makes both teams unable to act independently. Splitting them is the
industry standard for this reason.

## 4. Training / serving parity

A common bug in ML systems is **training/serving skew** — when features
are computed differently in the offline pipeline vs the online API.

This project enforces parity by having a **single function**
`build_features(df)` used by both:

* The training pipeline (batch DataFrame).
* The online API (single-row DataFrame via `transaction_to_feature_row`).

The integration tests in `tests/integration/test_api.py` cover this end-to-end.

## 5. Scaling considerations

This repo runs the API as 2 uvicorn workers. Production scaling:

| Concern         | Approach                                                                |
|-----------------|-------------------------------------------------------------------------|
| Throughput      | Horizontal: stateless API, add replicas behind a load balancer / k8s.   |
| Latency         | LightGBM single-row inference < 5ms. Pydantic + feature build dominate. |
| Model loading   | Loaded once at startup (lifespan). No per-request I/O.                  |
| Velocity features (`n_tx_last_1h`, etc.) | Computed by an upstream feature store (e.g. Redis, Feast). This repo accepts them in the payload. |
| Async retraining| Airflow / Kubeflow / GitHub Actions `train.yml`.                        |
| Shadow deploys  | Run new model alongside the old one, log both predictions, compare.     |

## 6. Trust boundaries

* **Input** (PSP → API): validated by Pydantic. No SQL, no eval.
* **Config** (`configs/*.yaml`): mounted read-only in containers, owned by code.
* **Model artifact**: signed and versioned (model_version = timestamp +
  commit SHA via `GIT_SHA` env var); loaded from a trusted artifact store.
* **Logs**: never contain PAN or full PII. Card IDs are tokens.
