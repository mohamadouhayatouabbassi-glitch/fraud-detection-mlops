"""Public data contracts for transactions, predictions, and decisions.

These models are the boundary contract between the outside world and the
service. Any breaking change here must go through API versioning (/v1, /v2).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Reference data (kept small intentionally for the demo; in prod these come
# from a referential service or a feature store).
# ---------------------------------------------------------------------------
SUPPORTED_CURRENCIES = ("EUR", "USD", "GBP", "CHF", "JPY")
KNOWN_CHANNELS = ("POS", "ECOM", "ATM", "MOTO")  # MOTO = Mail Order/Telephone Order

# MCC (Merchant Category Code) — full list is 4-digit ISO 18245.
# We use a curated subset that matches realistic merchant categories.
KNOWN_MCC = (
    "5411",  # Grocery
    "5812",  # Restaurants
    "5541",  # Service stations
    "5732",  # Electronics
    "7995",  # Gambling
    "5912",  # Pharmacy
    "4111",  # Transport
    "5999",  # Misc retail
    "6011",  # ATM withdrawal
    "5967",  # Adult content / direct marketing
)


class Channel(str, Enum):
    POS = "POS"
    ECOM = "ECOM"
    ATM = "ATM"
    MOTO = "MOTO"


class Action(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    DECLINE = "DECLINE"


class Transaction(BaseModel):
    """Raw transaction payload received at scoring time."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    transaction_id: str = Field(..., min_length=4, max_length=64)
    timestamp: datetime
    customer_id: str = Field(..., min_length=1, max_length=64)
    card_id: str = Field(..., min_length=1, max_length=64)

    amount: float = Field(..., gt=0, lt=1_000_000)
    currency: Literal["EUR", "USD", "GBP", "CHF", "JPY"] = "EUR"

    merchant_id: str = Field(..., min_length=1, max_length=64)
    merchant_country: str = Field(..., min_length=2, max_length=2)  # ISO-3166 alpha-2
    merchant_mcc: str = Field(..., min_length=4, max_length=4)

    card_country: str = Field(..., min_length=2, max_length=2)
    channel: Channel = Channel.POS
    is_cnp: bool = False  # Card Not Present

    # Behavioural context (computed upstream by the feature store or sent by the PSP)
    customer_age_days: int = Field(..., ge=0)
    card_age_days: int = Field(..., ge=0)
    n_tx_last_1h: int = Field(0, ge=0)
    n_tx_last_24h: int = Field(0, ge=0)
    amount_avg_30d: float = Field(0.0, ge=0)
    amount_std_30d: float = Field(0.0, ge=0)
    distinct_countries_last_24h: int = Field(0, ge=0)

    @field_validator("merchant_country", "card_country")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


class RuleHit(BaseModel):
    """A single rule that triggered during the rules pass."""

    code: str
    severity: Literal["HARD_BLOCK", "SUSPECT", "INFO"]
    description: str


class DecisionResponse(BaseModel):
    """Final response sent back to the caller (PSP, acquirer, etc.)."""

    transaction_id: str
    action: Action
    fraud_probability: float = Field(..., ge=0.0, le=1.0)
    risk_score: int = Field(..., ge=0, le=1000)
    reasons: list[str] = Field(default_factory=list)
    rule_hits: list[RuleHit] = Field(default_factory=list)
    model_version: str
    latency_ms: float


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    model_loaded: bool
    model_version: str | None
    git_sha: str | None = None
