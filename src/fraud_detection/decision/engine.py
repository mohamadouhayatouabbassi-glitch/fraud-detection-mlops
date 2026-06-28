"""Decision engine — combines business rules and ML probability into a final
APPROVE / REVIEW / DECLINE verdict.

Decision logic (in order):

  1. If any HARD_BLOCK rule fires → DECLINE immediately (audit reason = rules).
  2. Compute the adjusted probability:
         p_adj = min(1.0, p_ml + suspect_uplift_per_hit * n_suspect)
       (capped by max_suspect_uplift)
  3. If p_adj >= threshold_decline → DECLINE.
  4. Else if p_adj >= threshold_review → REVIEW.
  5. Else → APPROVE.

The "risk_score" exposed externally is an integer 0-1000 derived from p_adj.
This is what fraud analysts use in their tooling — they don't see raw probas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fraud_detection.data.schemas import Action, RuleHit


@dataclass
class DecisionInputs:
    fraud_probability: float
    rule_hits: list[RuleHit] = field(default_factory=list)


@dataclass
class DecisionOutput:
    action: Action
    fraud_probability: float
    adjusted_probability: float
    risk_score: int
    reasons: list[str]


@dataclass
class DecisionEngine:
    threshold_review: float = 0.30
    threshold_decline: float = 0.70
    suspect_uplift_per_hit: float = 0.05
    max_suspect_uplift: float = 0.20

    def decide(self, inputs: DecisionInputs) -> DecisionOutput:
        reasons: list[str] = []

        hard_blocks = [h for h in inputs.rule_hits if h.severity == "HARD_BLOCK"]
        if hard_blocks:
            reasons.extend(f"rule:{h.code}" for h in hard_blocks)
            return DecisionOutput(
                action=Action.DECLINE,
                fraud_probability=inputs.fraud_probability,
                adjusted_probability=1.0,
                risk_score=1000,
                reasons=reasons,
            )

        suspect_hits = [h for h in inputs.rule_hits if h.severity == "SUSPECT"]
        uplift = min(self.max_suspect_uplift, self.suspect_uplift_per_hit * len(suspect_hits))
        p_adj = min(1.0, inputs.fraud_probability + uplift)

        if suspect_hits:
            reasons.extend(f"rule:{h.code}" for h in suspect_hits)

        if p_adj >= self.threshold_decline:
            action = Action.DECLINE
            reasons.append(f"ml:p={p_adj:.3f}>=decline_threshold")
        elif p_adj >= self.threshold_review:
            action = Action.REVIEW
            reasons.append(f"ml:p={p_adj:.3f}>=review_threshold")
        else:
            action = Action.APPROVE
            reasons.append(f"ml:p={p_adj:.3f}<review_threshold")

        return DecisionOutput(
            action=action,
            fraud_probability=inputs.fraud_probability,
            adjusted_probability=p_adj,
            risk_score=int(round(p_adj * 1000)),
            reasons=reasons,
        )
