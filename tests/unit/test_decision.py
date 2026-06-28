"""Decision engine unit tests."""

from __future__ import annotations

from fraud_detection.data.schemas import Action, RuleHit
from fraud_detection.decision.engine import DecisionEngine, DecisionInputs


def test_hard_block_forces_decline_regardless_of_proba():
    engine = DecisionEngine(threshold_review=0.3, threshold_decline=0.7)
    out = engine.decide(
        DecisionInputs(
            fraud_probability=0.01,
            rule_hits=[RuleHit(code="R002", severity="HARD_BLOCK", description="x")],
        )
    )
    assert out.action == Action.DECLINE
    assert out.risk_score == 1000
    assert "rule:R002" in out.reasons


def test_low_proba_no_rules_approves():
    engine = DecisionEngine()
    out = engine.decide(DecisionInputs(fraud_probability=0.05, rule_hits=[]))
    assert out.action == Action.APPROVE
    assert out.risk_score == 50


def test_mid_proba_routes_to_review():
    engine = DecisionEngine(threshold_review=0.3, threshold_decline=0.7)
    out = engine.decide(DecisionInputs(fraud_probability=0.4, rule_hits=[]))
    assert out.action == Action.REVIEW


def test_suspect_rule_uplift_pushes_to_review():
    engine = DecisionEngine(
        threshold_review=0.3,
        threshold_decline=0.7,
        suspect_uplift_per_hit=0.1,
        max_suspect_uplift=0.3,
    )
    out = engine.decide(
        DecisionInputs(
            fraud_probability=0.25,
            rule_hits=[
                RuleHit(code="R001", severity="SUSPECT", description="x"),
            ],
        )
    )
    # 0.25 + 0.10 = 0.35 -> REVIEW
    assert out.action == Action.REVIEW
    assert "rule:R001" in out.reasons


def test_uplift_is_capped():
    engine = DecisionEngine(
        threshold_review=0.3,
        threshold_decline=0.7,
        suspect_uplift_per_hit=0.5,
        max_suspect_uplift=0.2,
    )
    out = engine.decide(
        DecisionInputs(
            fraud_probability=0.1,
            rule_hits=[
                RuleHit(code="A", severity="SUSPECT", description="x"),
                RuleHit(code="B", severity="SUSPECT", description="x"),
                RuleHit(code="C", severity="SUSPECT", description="x"),
            ],
        )
    )
    assert out.adjusted_probability == 0.1 + 0.2  # capped
