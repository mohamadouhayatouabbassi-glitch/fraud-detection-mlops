# Fraud Detection MLOps — End-to-End Hybrid Rules + ML

> Production-grade credit-card fraud scoring service combining **business
> rules** (auditable, owned by Risk) and a **calibrated LightGBM model**
> (adaptive, owned by Data Science), exposed via a FastAPI service,
> packaged in Docker, with CI/CD, monitoring, tests, and full documentation.

---

## Table of contents

1. [Objective](#1-objective)
2. [Architecture](#2-architecture)
3. [Tech stack](#3-tech-stack)
4. [Project steps (what was built and why)](#4-project-steps)
5. [Repository layout](#5-repository-layout)
6. [Quickstart](#6-quickstart)
7. [API reference](#7-api-reference)
8. [Configuration](#8-configuration)
9. [Observability](#9-observability)
10. [CI/CD](#10-cicd)
11. [Documentation](#11-documentation)
12. [Performance achieved](#12-performance-achieved)

---

## 1. Objective

Build a **real-time fraud scoring service** that takes a credit-card
transaction as input and returns one of three actions in under 100ms p99:

* `APPROVE` — let the transaction through
* `REVIEW` — route to manual review queue
* `DECLINE` — reject the transaction

The service combines **two complementary signals**:

| Signal              | Owner          | Strengths                                              | Limits                                |
|---------------------|----------------|--------------------------------------------------------|---------------------------------------|
| Business rules      | Risk team      | Auditable, regulatory-compliant, explainable           | Slow to adapt, blind to subtle signals|
| Calibrated ML model | Data Science   | Catches subtle multi-variate patterns, adapts via retrain | Less interpretable, requires labels |

A **Decision Engine** fuses both signals into the final verdict. Hard-block
rules short-circuit the ML call entirely (saves latency on obvious frauds).

---

## 2. Architecture

```
                  +----------------------+
                  |   Caller (PSP)       |
                  +----------+-----------+
                             | HTTPS POST /v1/score
                             v
+----------------------------+-----------------------------+
| FastAPI service                                          |
|   1. Pydantic validation  (Transaction schema)           |
|   2. Feature engineering  (build_features.py)            |
|   3. Rules engine         (rules/engine.py + YAML)       |
|   4. ML model             (LightGBM + isotonic calib.)   |
|   5. Decision engine      (rules + ML -> action)         |
+----------------------------+-----------------------------+
                             |
                             +---> JSON logs (correlation_id)
                             +---> Prometheus /metrics
                             +---> DecisionResponse
```

Detailed design: see [`docs/architecture.md`](docs/architecture.md).

---

## 3. Tech stack

| Layer                  | Choice                          | Why                                                            |
|------------------------|---------------------------------|----------------------------------------------------------------|
| Language               | Python 3.11                     | LightGBM + FastAPI + sklearn ecosystem                         |
| ML                     | LightGBM 4.3                    | Fast, strong on tabular, native handling of class imbalance    |
| Calibration            | sklearn `CalibratedClassifierCV` + `FrozenEstimator` | Probabilities you can interpret as thresholds  |
| Tracking               | MLflow (SQLite backend)         | Experiment tracking + artifact logging                         |
| Validation             | Pydantic v2                     | Strict, fast input validation at the API boundary              |
| API                    | FastAPI + uvicorn               | Async, OpenAPI auto-docs, lifespan hooks                       |
| Logging                | structlog                       | JSON logs with correlation_id via contextvars                  |
| Metrics                | prometheus-client               | Industry-standard exposition format                            |
| Config                 | pydantic-settings + PyYAML      | 12-factor env vars + versioned YAML for rules/hyperparameters  |
| CLI                    | Typer + Rich                    | Easy `generate-data`, `train`, `score-file`, `model-info`      |
| Packaging              | hatchling + pyproject.toml      | PEP 621 compliant, no setup.py legacy                          |
| Tests                  | pytest + pytest-cov + httpx     | Unit + integration with real model artifacts                   |
| Lint / format / types  | ruff + black + mypy             | Fast modern toolchain                                          |
| Pre-commit             | pre-commit                      | Hooks for every commit                                         |
| Container              | Docker multi-stage, non-root    | Slim runtime, libgomp1 for LightGBM, healthcheck               |
| Orchestration          | docker-compose (local)          | Local stack with mounted artifacts                             |
| CI/CD                  | GitHub Actions                  | Lint+test+build on PR, image push on tag, manual retrain       |
| Notebook               | Jupyter + matplotlib + seaborn  | EDA on the synthetic dataset                                   |

---

## 4. Project steps

What was built, in the order it was built, and the rationale.

### Step 1 — Project bootstrap
* `pyproject.toml` (PEP 621), `Makefile` for one-line ops, `.pre-commit-config.yaml`, `.gitignore`.
* **Why** — sets up a reproducible dev experience from minute one.

### Step 2 — Strict input contract
* Pydantic v2 `Transaction` schema with field-level constraints (amount > 0, ISO codes, MCC length).
* **Why** — invalid payloads must be rejected at the door, not deep in the model.

### Step 3 — Synthetic data generator with five fraud patterns
* `card_testing`, `geo_anomaly`, `cashout`, `account_takeover`, `high_risk_mcc`.
* Deterministic given a seed → fully reproducible training.
* **Why** — the project is reproducible without proprietary data; the patterns mirror what real fraud rings do.

### Step 4 — Feature engineering as the **single source of truth**
* `build_features(df)` is called by **both** the training pipeline (batch DataFrame) and the online API (single-row DataFrame).
* **Why** — eliminates training/serving skew, the most common ML production bug.

### Step 5 — Declarative rules engine
* YAML rules with predicates (`amount_gte`, `mcc_in`, `geo_mismatch`, `hour_between`, ...) loaded at startup.
* Three severities: `HARD_BLOCK`, `SUSPECT`, `INFO`.
* **Why** — Risk team can edit rules without touching code, and the file is auditable in git.

### Step 6 — Training pipeline (LightGBM + isotonic calibration)
* Time-based train/val/test split.
* Early stopping on validation set.
* Isotonic calibration on validation set → probabilities map linearly to thresholds.
* MLflow logs params + metrics + artifact.
* **Why** — calibrated probabilities make the decision policy (thresholds) interpretable.

### Step 7 — Decision engine
* Hard-block rules force `DECLINE` (and skip ML for latency).
* Each `SUSPECT` rule adds a small uplift to the ML probability, capped at +0.20.
* Final action = thresholding on the adjusted probability.
* **Why** — rules and ML each contribute, no single component can override the other silently.

### Step 8 — FastAPI service
* `POST /v1/score`, `POST /v1/score/batch`, `GET /healthz`, `GET /metrics`.
* Correlation-ID middleware propagates a trace identifier across every log line.
* Lifespan hooks load the model **once** at startup.
* **Why** — production hot path: validated input -> features -> rules -> ML -> decision.

### Step 9 — Monitoring
* Prometheus counters (`fraud_decisions_total`, `fraud_rule_hits_total`).
* Histograms for probability distribution and latency.
* PSI drift utility for offline analysis vs. training distribution.
* **Why** — you can't operate a model you don't observe.

### Step 10 — Tests
* Unit: features, rules, decision engine, drift, synthetic generator (22 tests).
* Integration: real trained model + real FastAPI app via `TestClient` (6 tests).
* 88% coverage.
* **Why** — integration tests catch the bugs unit tests miss (train/serve skew, model loading).

### Step 11 — Containerisation
* Multi-stage Dockerfile, non-root user, healthcheck, only `libgomp1` in runtime.
* `docker-compose.yml` mounts `artifacts/` and `configs/` read-only.
* **Why** — small attack surface, the model is loaded from a trusted volume.

### Step 12 — CI/CD with GitHub Actions
* `ci.yml`: ruff + black + mypy + pytest with coverage + docker build (every PR).
* `cd.yml`: build and push image to GHCR on `v*.*.*` tag.
* `train.yml`: manual `workflow_dispatch` to retrain and upload artifacts.
* **Why** — every PR is verifiable; releases are reproducible; retraining is a one-click operation.

### Step 13 — Documentation
* `docs/architecture.md` — components and data flow.
* `docs/model_card.md` — Google-style model card (intended use, limits, fairness).
* `docs/runbook.md` — on-call alerts and rollback procedures.
* `docs/api.md` — API contract.
* `notebooks/01_eda.ipynb` — exploratory analysis of the dataset.

---

## 5. Repository layout

```
.
+-- README.md                       <- you are here
+-- pyproject.toml                  <- packaging + tool config (ruff/black/mypy/pytest)
+-- Makefile                        <- make install / data / train / serve / test / docker-up
+-- Dockerfile                      <- multi-stage, non-root, libgomp1
+-- docker-compose.yml              <- local stack
+-- .pre-commit-config.yaml         <- pre-commit hooks
+-- .github/workflows/
|   +-- ci.yml                      <- lint + test + docker build (every PR)
|   +-- cd.yml                      <- push image to GHCR on tag
|   +-- train.yml                   <- manual retrain workflow
+-- configs/
|   +-- rules.yaml                  <- business rules (Risk team)
|   +-- model.yaml                  <- LightGBM hyperparameters + decision thresholds
+-- data/
|   +-- README.md                   <- dataset layout + schema reference
|   +-- sample/                     <- 5000-row sample committed for quick start
|   |   +-- transactions_train.parquet
|   |   +-- transactions_test.parquet
|   +-- raw/                        <- placeholder
|   +-- processed/                  <- generated locally by `make data` (gitignored)
+-- notebooks/
|   +-- 01_eda.ipynb                <- EDA: imbalance, feature signal, time, geo
+-- scripts/
|   +-- smoke_test.py               <- 4-scenario end-to-end check via TestClient
+-- src/fraud_detection/
|   +-- __init__.py
|   +-- cli.py                      <- Typer: generate-data / train / score-file / model-info
|   +-- api/main.py                 <- FastAPI app + lifespan + middleware
|   +-- data/schemas.py             <- Pydantic Transaction / DecisionResponse contracts
|   +-- data/synthetic.py           <- 5 fraud patterns generator
|   +-- features/build_features.py  <- SINGLE source of truth for features
|   +-- rules/engine.py             <- YAML rules engine
|   +-- models/train.py             <- LightGBM + isotonic calibration + MLflow
|   +-- models/predict.py           <- inference-time wrapper loaded at startup
|   +-- decision/engine.py          <- rules + ML -> APPROVE/REVIEW/DECLINE
|   +-- monitoring/metrics.py       <- Prometheus exposition
|   +-- monitoring/drift.py         <- PSI (Population Stability Index)
|   +-- utils/config.py             <- pydantic-settings
|   +-- utils/logging.py            <- structlog JSON + correlation_id
+-- tests/
|   +-- conftest.py                 <- shared fixtures (sample / fraud / hard_block transactions)
|   +-- unit/                       <- features, rules, decision, drift, synthetic (22 tests)
|   +-- integration/                <- real model + real FastAPI (6 tests)
+-- docs/
    +-- architecture.md             <- components + data flow
    +-- model_card.md               <- Google-style model card
    +-- runbook.md                  <- on-call procedures
    +-- api.md                      <- API contract
```

---

## 6. Quickstart

### 6.1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 6.2. Verify

```bash
make lint        # ruff + black --check
make test        # pytest unit + integration (uses sample/full dataset)
```

### 6.3. Generate the full dataset (200k rows)

```bash
make data
# or
fraud generate-data --n-rows 200000 --fraud-rate 0.012
```

### 6.4. Train the model

```bash
make train
# or
fraud train
```

You'll see a metrics table:

```
        Test set evaluation
+------------------------+---------+
| Metric                 |   Value |
+------------------------+---------+
| ROC AUC                |  0.9914 |
| PR AUC                 |  0.9830 |
| Recall @ 1% FPR        |  0.9828 |
| Precision @ top 1%     |  1.0000 |
| F1 @ default threshold |  0.9913 |
+------------------------+---------+
```

Artifact saved to `artifacts/model.joblib`, MLflow run logged to `mlruns.db`.

### 6.5. Run the API

```bash
make serve
# or
uvicorn fraud_detection.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Open <http://localhost:8000/docs> for the Swagger UI.

### 6.6. Score a transaction

```bash
curl -s -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: demo-001" \
  -d '{
    "transaction_id": "TX_DEMO_001",
    "timestamp": "2025-06-15T03:10:00Z",
    "customer_id": "C0000001",
    "card_id": "K0000001",
    "amount": 1500.0,
    "currency": "EUR",
    "merchant_id": "M999999",
    "merchant_country": "NG",
    "merchant_mcc": "7995",
    "card_country": "FR",
    "channel": "ECOM",
    "is_cnp": true,
    "customer_age_days": 900,
    "card_age_days": 400,
    "n_tx_last_1h": 4,
    "n_tx_last_24h": 10,
    "amount_avg_30d": 70.0,
    "amount_std_30d": 20.0,
    "distinct_countries_last_24h": 2
  }' | jq .
```

Sample response (fraud case):

```json
{
  "transaction_id": "TX_DEMO_001",
  "action": "DECLINE",
  "fraud_probability": 1.0,
  "risk_score": 1000,
  "reasons": [
    "rule:R001_HIGH_AMOUNT_CNP",
    "rule:R003_GEO_MISMATCH_ECOM",
    "rule:R005_HIGH_RISK_MCC",
    "ml:p=1.000>=decline_threshold"
  ],
  "rule_hits": [
    {"code": "R001_HIGH_AMOUNT_CNP",   "severity": "SUSPECT", "description": "..."},
    {"code": "R003_GEO_MISMATCH_ECOM", "severity": "SUSPECT", "description": "..."},
    {"code": "R005_HIGH_RISK_MCC",     "severity": "SUSPECT", "description": "..."}
  ],
  "model_version": "20260628-181316",
  "latency_ms": 13.09
}
```

### 6.7. Run the EDA notebook

```bash
pip install jupyterlab matplotlib seaborn
jupyter lab notebooks/01_eda.ipynb
```

### 6.8. Docker

```bash
make docker-build
make docker-up    # starts the API on :8000 with local artifact + config mounted
```

---

## 7. API reference

Full reference: [`docs/api.md`](docs/api.md). Auto-generated OpenAPI at `/docs`.

| Method | Path              | Purpose                              |
|--------|-------------------|--------------------------------------|
| POST   | `/v1/score`       | Score a single transaction           |
| POST   | `/v1/score/batch` | Score up to 100 transactions at once |
| GET    | `/healthz`        | Liveness + readiness                 |
| GET    | `/metrics`        | Prometheus exposition                |

---

## 8. Configuration

12-factor: env vars override defaults; YAML files for domain configuration.

| Variable                    | Default       | Purpose                          |
|-----------------------------|---------------|----------------------------------|
| `FRAUD_LOG_LEVEL`           | `INFO`        | Service log level                |
| `FRAUD_ENVIRONMENT`         | `dev`         | dev / staging / prod             |
| `FRAUD_DATA_DIR`            | `./data`      | Data root                        |
| `FRAUD_ARTIFACTS_DIR`       | `./artifacts` | Where the model is loaded from   |
| `FRAUD_CONFIGS_DIR`         | `./configs`   | Where rules.yaml / model.yaml live |
| `FRAUD_THRESHOLD_REVIEW`    | `0.30`        | Threshold for REVIEW             |
| `FRAUD_THRESHOLD_DECLINE`   | `0.70`        | Threshold for DECLINE            |
| `FRAUD_MLFLOW_TRACKING_URI` | `sqlite:///mlruns.db` | MLflow backend           |

Business rules: [`configs/rules.yaml`](configs/rules.yaml) — 9 rules in three severities.
Model hyperparameters: [`configs/model.yaml`](configs/model.yaml).

---

## 9. Observability

* **Logs** — structlog emits JSON, every log line carries a `correlation_id` either provided by the caller via `X-Correlation-ID` or generated. Trivial to correlate across components in Loki/Elastic/CloudWatch.
* **Metrics** at `/metrics`:
  * `fraud_decisions_total{action}` — product KPI
  * `fraud_rule_hits_total{code,severity}` — rule-level explainability
  * `fraud_probability` — histogram for drift signal
  * `fraud_inference_latency_seconds` — SLO (p99 < 100ms)
  * `fraud_service_healthy` — gauge for readiness
* **Drift** — `fraud_detection.monitoring.drift.psi()` for offline jobs:
  * PSI < 0.10: stable
  * 0.10–0.25: investigate
  * > 0.25: retrain

---

## 10. CI/CD

| Workflow      | Trigger             | Steps                                                          |
|---------------|---------------------|----------------------------------------------------------------|
| `ci.yml`      | Push / PR to `main` | ruff + black + mypy (informational) + pytest with coverage + docker build (no push) |
| `cd.yml`      | Tag push `v*.*.*`   | Build + push image to GHCR with multi-tag                      |
| `train.yml`   | Manual              | Generate data + train + upload artifacts                       |

---

## 11. Documentation

* [`docs/architecture.md`](docs/architecture.md) — components & data flow, training-serving parity invariant, scaling considerations
* [`docs/model_card.md`](docs/model_card.md) — Google-style model card (intended use, training data, evaluation, fairness, limitations)
* [`docs/runbook.md`](docs/runbook.md) — on-call alerts (A1–A4) and rollback procedures
* [`docs/api.md`](docs/api.md) — API contract details (status codes, SLA, backward compatibility)
* [`data/README.md`](data/README.md) — dataset layout + schema

---

## 12. Performance achieved

Verified end-to-end in the sandbox:

| Check                                | Result                                                                |
|--------------------------------------|-----------------------------------------------------------------------|
| Lint (ruff)                          | Clean                                                                 |
| Format (black --check)               | Clean                                                                 |
| Unit + integration tests             | **28 / 28 passed**, **88% coverage**                                  |
| Model — ROC AUC                      | **0.991**                                                             |
| Model — PR AUC                       | **0.983**                                                             |
| Model — Recall at 1% FPR             | **0.98**                                                              |
| End-to-end latency (smoke_test.py)   | 9 – 17 ms per request (well under the 100ms SLO)                      |
| 4 business scenarios                 | APPROVE / DECLINE multi-rule / HARD_BLOCK amount / HARD_BLOCK velocity — all correct |

---

## License

Proprietary — example project.
