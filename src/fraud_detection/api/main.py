"""FastAPI service exposing the fraud scoring endpoint.

Performance budget:
  * Pydantic validation : < 5 ms
  * Feature build       : < 5 ms
  * Rules               : < 2 ms
  * ML predict          : < 30 ms (LightGBM, single row)
  * Total p99           : < 100 ms

Endpoints:
  GET  /healthz             liveness/readiness probe
  GET  /metrics             Prometheus exposition format
  POST /v1/score            score a single transaction
  POST /v1/score/batch      score up to 100 transactions in one call
"""

from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from fraud_detection.data.schemas import (
    DecisionResponse,
    HealthResponse,
    Transaction,
)
from fraud_detection.decision.engine import DecisionEngine, DecisionInputs
from fraud_detection.features.build_features import transaction_to_feature_row
from fraud_detection.models.predict import FraudModel, load_model
from fraud_detection.monitoring.metrics import (
    REGISTRY,
    decision_counter,
    fraud_probability_hist,
    health_gauge,
    inference_latency_hist,
    rule_hit_counter,
)
from fraud_detection.rules.engine import RulesEngine
from fraud_detection.utils.config import get_settings, load_yaml
from fraud_detection.utils.logging import (
    configure_logging,
    get_logger,
    set_correlation_id,
)

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# App-wide state container. Filled on startup, read on every request.
# ---------------------------------------------------------------------------
class AppState:
    model: FraudModel | None = None
    rules_engine: RulesEngine | None = None
    decision_engine: DecisionEngine | None = None


state = AppState()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Bootstrap heavy objects ONCE at startup."""
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info("service_starting", environment=settings.environment)

    # Load model artifact
    try:
        state.model = load_model(settings.model_path)
        health_gauge.set(1)
    except FileNotFoundError:
        log.error(
            "model_missing",
            path=str(settings.model_path),
            hint="Run `make data && make train` first.",
        )
        health_gauge.set(0)

    # Load rules
    state.rules_engine = RulesEngine.from_yaml(settings.configs_dir / "rules.yaml")

    # Load decision thresholds from model.yaml
    model_cfg = load_yaml(settings.configs_dir / "model.yaml")
    decision_cfg = model_cfg.get("decision", {})
    state.decision_engine = DecisionEngine(
        threshold_review=decision_cfg.get("threshold_review", 0.30),
        threshold_decline=decision_cfg.get("threshold_decline", 0.70),
        suspect_uplift_per_hit=decision_cfg.get("suspect_uplift_per_hit", 0.05),
        max_suspect_uplift=decision_cfg.get("max_suspect_uplift", 0.20),
    )
    log.info(
        "decision_engine_configured",
        threshold_review=state.decision_engine.threshold_review,
        threshold_decline=state.decision_engine.threshold_decline,
    )

    yield

    log.info("service_shutting_down")


app = FastAPI(
    title="Fraud Detection Service",
    description="Hybrid rules + ML credit-card fraud scoring.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware: correlation ID + access log
# ---------------------------------------------------------------------------
@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    set_correlation_id(cid)
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    log.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=round(elapsed, 2),
    )
    response.headers["X-Correlation-ID"] = cid
    set_correlation_id(None)
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/healthz", response_model=HealthResponse, tags=["ops"])
def healthz() -> HealthResponse:
    """Liveness + readiness combined: returns 'ok' only if model is loaded."""
    return HealthResponse(
        status="ok" if state.model is not None else "degraded",
        model_loaded=state.model is not None,
        model_version=state.model.version if state.model else None,
        git_sha=os.environ.get("GIT_SHA"),
    )


@app.get("/metrics", tags=["ops"])
def metrics() -> Response:
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


class BatchScoreRequest(BaseModel):
    transactions: list[Transaction] = Field(..., min_length=1, max_length=100)


def _score_one(tx: Transaction) -> DecisionResponse:
    if state.model is None or state.rules_engine is None or state.decision_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready: model or rules not loaded",
        )

    start = time.perf_counter()

    # 1. Feature engineering (single source of truth)
    features = transaction_to_feature_row(tx)
    row: dict[str, Any] = features.iloc[0].to_dict()

    # 2. Rules
    hits = state.rules_engine.evaluate(row)
    for h in hits:
        rule_hit_counter.labels(code=h.code, severity=h.severity).inc()

    # 3. ML (skipped if a HARD_BLOCK already fired — saves latency on obvious frauds)
    proba = 1.0 if RulesEngine.has_hard_block(hits) else state.model.predict_one(features)

    fraud_probability_hist.observe(proba)

    # 4. Decision
    decision = state.decision_engine.decide(DecisionInputs(fraud_probability=proba, rule_hits=hits))
    decision_counter.labels(action=decision.action.value).inc()

    elapsed_ms = (time.perf_counter() - start) * 1000
    inference_latency_hist.observe(elapsed_ms / 1000)

    log.info(
        "scoring_done",
        transaction_id=tx.transaction_id,
        action=decision.action.value,
        fraud_probability=round(proba, 4),
        risk_score=decision.risk_score,
        rule_hits=[h.code for h in hits],
        latency_ms=round(elapsed_ms, 2),
    )

    return DecisionResponse(
        transaction_id=tx.transaction_id,
        action=decision.action,
        fraud_probability=round(proba, 6),
        risk_score=decision.risk_score,
        reasons=decision.reasons,
        rule_hits=hits,
        model_version=state.model.version,
        latency_ms=round(elapsed_ms, 2),
    )


@app.post("/v1/score", response_model=DecisionResponse, tags=["scoring"])
def score(tx: Transaction) -> DecisionResponse:
    return _score_one(tx)


@app.post("/v1/score/batch", response_model=list[DecisionResponse], tags=["scoring"])
def score_batch(req: BatchScoreRequest) -> list[DecisionResponse]:
    return [_score_one(tx) for tx in req.transactions]


# ---------------------------------------------------------------------------
# Error handler — return JSON, log the error, never leak internals
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):  # noqa: ARG001
    log.exception("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "internal_error"},
    )
