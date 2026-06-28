"""Rules engine unit tests."""

from __future__ import annotations

from fraud_detection.features.build_features import transaction_to_feature_row
from fraud_detection.rules.engine import RulesEngine


def _row(tx):
    return transaction_to_feature_row(tx).iloc[0].to_dict()


def test_rules_yaml_loads(rules_config_path):
    engine = RulesEngine.from_yaml(rules_config_path)
    assert len(engine.rules) > 0
    codes = [r.code for r in engine.rules]
    assert "R002_VERY_HIGH_AMOUNT" in codes
    assert "R008_MULTI_COUNTRY_24H" in codes


def test_legit_transaction_has_no_hits(rules_config_path, sample_transaction):
    engine = RulesEngine.from_yaml(rules_config_path)
    hits = engine.evaluate(_row(sample_transaction))
    assert hits == []


def test_hard_block_high_amount(rules_config_path, hard_block_transaction):
    engine = RulesEngine.from_yaml(rules_config_path)
    hits = engine.evaluate(_row(hard_block_transaction))
    codes = [h.code for h in hits]
    assert "R002_VERY_HIGH_AMOUNT" in codes
    assert RulesEngine.has_hard_block(hits)


def test_suspect_rules_on_fraud_pattern(rules_config_path, fraud_transaction):
    engine = RulesEngine.from_yaml(rules_config_path)
    hits = engine.evaluate(_row(fraud_transaction))
    codes = [h.code for h in hits]
    # ECOM + geo mismatch
    assert "R003_GEO_MISMATCH_ECOM" in codes
    # CNP + amount >= 1000
    assert "R001_HIGH_AMOUNT_CNP" in codes
    # MCC 7995 = high risk
    assert "R005_HIGH_RISK_MCC" in codes


def test_velocity_burst_hard_block(rules_config_path, sample_transaction):
    """If we raise n_tx_last_1h, R004_VELOCITY_BURST should fire."""
    tx = sample_transaction.model_copy(update={"n_tx_last_1h": 12})
    engine = RulesEngine.from_yaml(rules_config_path)
    hits = engine.evaluate(_row(tx))
    assert any(h.code == "R004_VELOCITY_BURST" and h.severity == "HARD_BLOCK" for h in hits)
