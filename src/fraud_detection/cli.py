"""Typer CLI: ``fraud generate-data``, ``fraud train``, ``fraud score-file``.

Use this for local development, CI jobs, or to schedule retraining from
Airflow / GitHub Actions / cron.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from fraud_detection.data.synthetic import generate_transactions, save_dataset
from fraud_detection.models.predict import load_model
from fraud_detection.models.train import train_model
from fraud_detection.utils.config import get_settings
from fraud_detection.utils.logging import configure_logging, get_logger

app = typer.Typer(help="Fraud Detection MLOps CLI", no_args_is_help=True)
console = Console()
log = get_logger(__name__)


@app.callback()
def _root(log_level: str = typer.Option("INFO", help="Log level (DEBUG/INFO/WARNING/ERROR)")):
    configure_logging(log_level)


@app.command("generate-data")
def generate_data(
    n_rows: int = typer.Option(200_000, help="Total number of transactions"),
    fraud_rate: float = typer.Option(0.012, help="Fraction of fraud rows"),
    n_customers: int = typer.Option(20_000, help="Distinct customers / cards"),
    seed: int = typer.Option(42, help="Random seed for reproducibility"),
    out_dir: Path = typer.Option(None, help="Output directory (default: data/processed)"),
):
    """Generate synthetic train + test parquet datasets."""
    settings = get_settings()
    out = out_dir or settings.data_dir / "processed"
    df = generate_transactions(
        n_rows=n_rows, fraud_rate=fraud_rate, n_customers=n_customers, seed=seed
    )
    train_path, test_path = save_dataset(df, out)
    console.print(f"[green]\u2713 Train:[/green] {train_path}")
    console.print(f"[green]\u2713 Test :[/green] {test_path}")


@app.command("train")
def train(
    train_path: Path = typer.Option(None, help="Train parquet path"),
    test_path: Path = typer.Option(None, help="Test parquet path"),
    model_config: Path = typer.Option(None, help="Model config YAML"),
):
    """Train the LightGBM fraud model."""
    settings = get_settings()
    train_path = train_path or settings.data_dir / "processed" / "transactions_train.parquet"
    test_path = test_path or settings.data_dir / "processed" / "transactions_test.parquet"
    model_config = model_config or settings.configs_dir / "model.yaml"

    report = train_model(train_path, test_path, model_config, settings=settings)

    table = Table(title="Test set evaluation")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("ROC AUC", f"{report.roc_auc:.4f}")
    table.add_row("PR AUC", f"{report.pr_auc:.4f}")
    table.add_row("Recall @ 1% FPR", f"{report.recall_at_1pct_fpr:.4f}")
    table.add_row("Precision @ top 1%", f"{report.precision_at_top_1pct:.4f}")
    table.add_row("F1 @ default threshold", f"{report.f1_at_default_threshold:.4f}")
    table.add_row("Train fraud rate", f"{report.fraud_rate_train:.4%}")
    table.add_row("Test fraud rate", f"{report.fraud_rate_test:.4%}")
    console.print(table)

    importance = sorted(report.feature_importance.items(), key=lambda kv: -kv[1])
    imp_table = Table(title="Top 10 features (normalised gain)")
    imp_table.add_column("Feature")
    imp_table.add_column("Importance", justify="right")
    for name, val in importance[:10]:
        imp_table.add_row(name, f"{val:.4f}")
    console.print(imp_table)


@app.command("score-file")
def score_file(
    input_file: Path = typer.Argument(..., exists=True, help="Parquet file of transactions"),
    output_file: Path = typer.Argument(..., help="Where to write predictions"),
):
    """Batch score a parquet file (offline, e.g. nightly job)."""
    from fraud_detection.features.build_features import build_features

    settings = get_settings()
    model = load_model(settings.model_path)
    df = pd.read_parquet(input_file)
    features = build_features(df)
    df["fraud_probability"] = model.predict_proba(features)
    df.to_parquet(output_file, index=False)
    console.print(f"[green]\u2713 Scored {len(df)} rows \u2192 {output_file}[/green]")


@app.command("model-info")
def model_info():
    """Print model metadata + training report."""
    settings = get_settings()
    if not settings.model_path.exists():
        console.print(f"[red]\u2717 No model found at {settings.model_path}[/red]")
        raise typer.Exit(1)
    m = load_model(settings.model_path)
    console.print_json(json.dumps(m.metadata, default=str))


if __name__ == "__main__":
    app()
