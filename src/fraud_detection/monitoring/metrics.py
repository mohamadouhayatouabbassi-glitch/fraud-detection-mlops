"""Prometheus metrics exposed at /metrics.

Why these metrics:
  * decisions_total{action}        : product KPI, alert if APPROVE rate drops.
  * rule_hits_total{code,severity} : rule-level explainability, helps Risk team
                                     spot a noisy / silent rule.
  * fraud_probability              : distribution drift signal.
  * inference_latency_seconds      : SLO (p99 < 100ms).
  * health_status                  : 1 if model is loaded and ready.
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

REGISTRY = CollectorRegistry()

decision_counter = Counter(
    "fraud_decisions_total",
    "Total number of decisions emitted, by action.",
    ["action"],
    registry=REGISTRY,
)

rule_hit_counter = Counter(
    "fraud_rule_hits_total",
    "Total rule hits, by rule code and severity.",
    ["code", "severity"],
    registry=REGISTRY,
)

fraud_probability_hist = Histogram(
    "fraud_probability",
    "Distribution of predicted fraud probabilities.",
    buckets=(0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.99),
    registry=REGISTRY,
)

inference_latency_hist = Histogram(
    "fraud_inference_latency_seconds",
    "End-to-end /score latency (Pydantic + features + rules + ML + decision).",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=REGISTRY,
)

health_gauge = Gauge(
    "fraud_service_healthy",
    "1 if the model is loaded and the service is healthy, 0 otherwise.",
    registry=REGISTRY,
)
