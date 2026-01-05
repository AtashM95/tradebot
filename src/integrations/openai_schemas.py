from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, conlist


class NewsRiskGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_flag: Literal["LOW", "MED", "HIGH"]
    trade_allowed: bool
    reasons: conlist(str, max_length=3) = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class TradeExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["ALLOW", "VETO", "REDUCE_SIZE"]
    bullets: conlist(str, max_length=5) = Field(default_factory=list)
    key_factors: conlist(str, max_length=5) = Field(default_factory=list)


class DailyOpsReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    pnl_today: Optional[float] = None
    drawdown: Optional[float] = None
    incidents: list[str] = Field(default_factory=list)


def schema_for(model: type[BaseModel]) -> dict:
    return {"name": model.__name__, "schema": model.model_json_schema(), "strict": True}
