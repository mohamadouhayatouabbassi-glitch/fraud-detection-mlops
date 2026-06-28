# On-call Runbook — Fraud Detection Service

This is the day-1 runbook used by the on-call engineer. Keep it short,
actionable, and up to date.

## Service map

| What         | Where                                                          |
|--------------|----------------------------------------------------------------|
| Image        | `ghcr.io/<org>/fraud-detection-mlops:vX.Y.Z`                   |
| Container    | `fraud-api` (uvicorn, 2 workers, port 8000)                    |
| Healthcheck  | `GET /healthz`                                                 |
| Metrics      | `GET /metrics`                                                 |
| Logs         | stdout JSON, shipped to <log platform>, index `fraud-api-*`    |
| Dashboards   | <link to Grafana dashboard>                                    |
| MLflow runs  | <link to MLflow UI>                                            |
| Model artifact| `s3://<bucket>/fraud/model.joblib` (versioned)                |
| Config       | `configs/rules.yaml`, `configs/model.yaml` (mounted)           |

## SLOs

| Indicator                                | Target          |
|------------------------------------------|-----------------|
| Availability                             | 99.95% monthly  |
| `/v1/score` p99 latency                  | < 100 ms        |
| Decision distribution (DECLINE rate)     | 0.5% - 3%       |
| Model freshness (last retrain age)       | < 35 days       |

## Common alerts

### A1 — `fraud_service_healthy == 0`

**Likely cause**: model artifact missing or unreadable at startup.

1. Check pod logs for `model_missing` log line.
2. Verify the artifact is present in the mounted volume / S3 path.
3. If the deployment is mid-rollout, roll back to the previous image tag.

```
kubectl rollout undo deployment/fraud-api
```

### A2 — `/v1/score` p99 latency > 100 ms

1. Check `fraud_inference_latency_seconds` percentiles vs baseline.
2. CPU saturated → scale out (HPA on CPU).
3. If LightGBM step regressed: confirm `lgbm_best_iteration` in
   `/healthz` payload matches expected. Roll back image if mismatched.

### A3 — DECLINE rate doubled

1. Check `fraud_rule_hits_total` per code: a single rule going wild is the
   #1 suspect (e.g. someone changed `R002` threshold from 5000 to 500).
2. Diff `configs/rules.yaml` against last known good commit.
3. Roll back the config-only deployment if the code itself is unchanged.

### A4 — Feature drift PSI > 0.25 on a top-5 feature

1. Investigate the upstream feature store: stale or incorrect data is the
   most common cause of sudden drift.
2. If genuine concept drift, schedule a retrain (`workflow_dispatch` on
   `train.yml`) and validate on the shadow traffic before promoting.

## Routine ops

### Deploy a new image

1. Merge to `main`, CI green.
2. Tag a release: `git tag v1.2.3 && git push --tags`. `cd.yml` builds and
   pushes the image to GHCR.
3. Update the helm chart image tag, deploy to staging, run the smoke suite.
4. Canary 10% on prod for 30 min, watch metrics, then full rollout.

### Retrain & promote a model

1. Trigger `train.yml` via `gh workflow run train.yml`.
2. Download artifacts, inspect the metrics table.
3. Run shadow scoring on 24h of recent traffic, compare decision distribution
   with the live model.
4. If green, upload to the artifact store and roll the API (model is loaded
   at startup).

### Rollback

* **Code rollback**: `kubectl rollout undo deployment/fraud-api`.
* **Model rollback**: revert the artifact pointer (`MODEL_VERSION` env var
  or the S3 path) to the previous version, then rolling restart.
* **Rules-only rollback**: revert `configs/rules.yaml` in git, redeploy
  config-only (no image rebuild needed).
