"""Business rules engine.

Rules are declarative (YAML), owned by the Risk team. The engine evaluates a
row of features against the configured rules and returns the list of hits.

The engine is intentionally simple: predicate names map to small Python
functions in `PREDICATES`. Adding a new predicate is a one-liner.

Design choices:
  * Rules return a list of hits (not a single verdict): the Decision engine is
    responsible for combining them with the ML score.
  * HARD_BLOCK hits short-circuit the ML call at the Decision layer (saves
    latency on obviously bad transactions).
  * Rules can never APPROVE a transaction by themselves — only the Decision
    engine can.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fraud_detection.data.schemas import RuleHit
from fraud_detection.utils.config import load_yaml
from fraud_detection.utils.logging import get_logger

log = get_logger(__name__)


# Each predicate takes (feature_row: dict, value: Any) -> bool
def _ge(field: str) -> Callable[[dict, Any], bool]:
    return lambda row, val: float(row.get(field, 0)) >= float(val)


def _lt(field: str) -> Callable[[dict, Any], bool]:
    return lambda row, val: float(row.get(field, 0)) < float(val)


def _eq_bool(field: str) -> Callable[[dict, Any], bool]:
    return lambda row, val: bool(row.get(field, False)) == bool(val)


def _in(field: str) -> Callable[[dict, Any], bool]:
    return lambda row, vals: str(row.get(field, "")) in {str(v) for v in vals}


def _between(field: str) -> Callable[[dict, Any], bool]:
    def _check(row: dict, val: Any) -> bool:
        low, high = val
        x = float(row.get(field, 0))
        return float(low) <= x <= float(high)

    return _check


def _geo_mismatch(_row_key: str = "") -> Callable[[dict, Any], bool]:
    def _check(row: dict, val: Any) -> bool:
        mc = str(row.get("merchant_country", "")).upper()
        cc = str(row.get("card_country", "")).upper()
        mismatch = mc != cc
        return mismatch == bool(val)

    return _check


# Mapping: predicate keyword in YAML  ->  predicate factory
PREDICATES: dict[str, Callable[[dict, Any], bool]] = {
    "amount_gte": _ge("amount"),
    "amount_zscore_30d_gte": _ge("amount_zscore_30d"),
    "n_tx_last_1h_gte": _ge("n_tx_last_1h"),
    "distinct_countries_last_24h_gte": _ge("distinct_countries_last_24h"),
    "card_age_days_lt": _lt("card_age_days"),
    "is_cnp": _eq_bool("is_cnp"),
    "channel_in": _in("channel"),
    "mcc_in": _in("merchant_mcc"),
    "hour_between": _between("hour"),
    "geo_mismatch": _geo_mismatch(),
}


@dataclass(frozen=True)
class Rule:
    code: str
    severity: str
    description: str
    conditions: dict[str, Any]

    def evaluate(self, row: dict) -> bool:
        """All conditions must hold (AND)."""
        for key, value in self.conditions.items():
            pred = PREDICATES.get(key)
            if pred is None:
                raise ValueError(f"Unknown predicate '{key}' in rule {self.code}")
            if not pred(row, value):
                return False
        return True


class RulesEngine:
    """Evaluates a feature row against a list of configured rules."""

    def __init__(self, rules: list[Rule]):
        self.rules = rules

    @classmethod
    def from_yaml(cls, path: Path) -> RulesEngine:
        config = load_yaml(path)
        rules = [
            Rule(
                code=r["code"],
                severity=r["severity"],
                description=r["description"],
                conditions=r.get("when", {}),
            )
            for r in config.get("rules", [])
        ]
        log.info("rules_loaded", count=len(rules), path=str(path))
        return cls(rules)

    def evaluate(self, row: dict) -> list[RuleHit]:
        hits: list[RuleHit] = []
        for rule in self.rules:
            try:
                if rule.evaluate(row):
                    hits.append(
                        RuleHit(
                            code=rule.code,
                            severity=rule.severity,  # type: ignore[arg-type]
                            description=rule.description,
                        )
                    )
            except Exception as e:  # pragma: no cover - defensive
                log.warning("rule_eval_failed", code=rule.code, error=str(e))
        return hits

    @staticmethod
    def has_hard_block(hits: list[RuleHit]) -> bool:
        return any(h.severity == "HARD_BLOCK" for h in hits)
