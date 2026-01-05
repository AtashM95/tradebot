from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Direction = Literal["LONG"]
SignalStrength = Literal["weak", "medium", "strong"]
OrderSide = Literal["buy", "sell"]
OrderType = Literal["market", "limit"]
RiskOutcome = Literal["approved", "veto"]


class Bar(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class BarSeries(BaseModel):
    symbol: str
    timeframe: str
    bars: List[Bar]


class Features(BaseModel):
    schema_version: str = "v1"
    symbol: str
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    values: Dict[str, float]


class SignalIntent(BaseModel):
    symbol: str
    direction: Direction = "LONG"
    confidence: float
    entry: float
    stop: float
    take_profit: float
    reasons: List[str]
    ts: datetime = Field(default_factory=datetime.utcnow)
    strategy: str
    strength: SignalStrength = "medium"


class FinalSignal(BaseModel):
    symbol: str
    direction: Direction = "LONG"
    score: float
    entry: float
    stop: float
    take_profit: float
    reasons: List[str]
    intents: List[SignalIntent]
    ts: datetime = Field(default_factory=datetime.utcnow)


class RiskDecision(BaseModel):
    symbol: str
    outcome: RiskOutcome
    approved: bool
    shares: int
    cash_required: float
    reasons: List[str]
    constraints: Dict[str, float]


class OrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType = "market"
    limit_price: Optional[float] = None
    time_in_force: Literal["day", "gtc"] = "day"
    client_order_id: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class OrderResult(BaseModel):
    order_id: str
    symbol: str
    status: str
    filled_qty: int
    average_fill_price: Optional[float] = None
    raw: Dict[str, str] = Field(default_factory=dict)


class FillEvent(BaseModel):
    order_id: str
    symbol: str
    quantity: int
    price: float
    filled_at: datetime


class FundingAlert(BaseModel):
    missing_cash: float
    proposed_actions: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, float] = Field(default_factory=dict)


class ModelVersionMeta(BaseModel):
    model_id: str
    trained_range: str
    feature_schema: str
    metrics: Dict[str, float]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ModelMeta(ModelVersionMeta):
    pass


class TestCenterCheck(BaseModel):
    name: str
    status: Literal["pass", "fail", "warn"]
    message: str
    next_step: Optional[str] = None
    details: Dict[str, str] = Field(default_factory=dict)
