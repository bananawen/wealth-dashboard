from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str


class AccountCreate(BaseModel):
    name: str
    type: str  # 'brokerage', 'bank', 'crypto'
    currency: str = "TWD"


class AccountOut(BaseModel):
    id: int
    name: str
    type: str
    created_at: datetime


class HoldingCreate(BaseModel):
    account_id: int
    symbol: str
    shares: float
    avg_cost: float
    currency: str = "TWD"


class HoldingUpdate(BaseModel):
    symbol: Optional[str] = None
    shares: Optional[float] = None
    avg_cost: Optional[float] = None
    total_cost: Optional[float] = None
    currency: Optional[str] = None


class HoldingOut(BaseModel):
    id: int
    account_id: int
    symbol: str
    shares: float
    avg_cost: float
    total_cost: float
    currency: str


class TransactionCreate(BaseModel):
    account_id: int
    symbol: str
    type: str  # 'buy' or 'sell'
    shares: float
    price: float
    date: date


class TransactionOut(BaseModel):
    id: int
    account_id: int
    symbol: str
    type: str
    shares: float
    price: float
    date: date
    realized_gain: float


class PortfolioSummary(BaseModel):
    total_value: float
    total_value_twd: Optional[float] = None
    total_cost: float
    total_cost_twd: Optional[float] = None
    unrealized_gain: float
    unrealized_gain_twd: Optional[float] = None
    unrealized_pct: float
    realized_gain: float
    realized_gain_twd: Optional[float] = None
    realized_pct: Optional[float] = None
    annualized_return: Optional[float] = None
    day_change: float
    day_change_pct: float
    fx_rate: Optional[float] = None
    last_updated: Optional[str] = None


class SnapshotCreate(BaseModel):
    date: date
    total_value: float