from pydantic import BaseModel, Field
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


class HoldingCreate(BaseModel):
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
    symbol: str
    shares: float
    avg_cost: float
    total_cost: float
    currency: str


class TransactionCreate(BaseModel):
    symbol: str
    type: str  # 'buy' or 'sell'
    shares: float
    price: float
    date: date
    notes: Optional[str] = None
    category: Optional[str] = None
    asset_class: Optional[str] = None
    sector: Optional[str] = None
    fee: float = 0
    tax: float = 0


class TransactionUpdate(BaseModel):
    symbol: Optional[str] = None
    type: Optional[str] = None
    shares: Optional[float] = None
    price: Optional[float] = None
    date: Optional[date] = None
    notes: Optional[str] = None
    category: Optional[str] = None
    asset_class: Optional[str] = None
    sector: Optional[str] = None
    fee: Optional[float] = None
    tax: Optional[float] = None


class TransactionOut(BaseModel):
    id: int
    symbol: str
    type: str
    shares: float
    price: float
    date: date
    notes: Optional[str] = None
    category: Optional[str] = None
    asset_class: Optional[str] = None
    sector: Optional[str] = None
    fee: float = 0
    tax: float = 0
    realized_gain: float


class TransactionImportResult(BaseModel):
    created: int
    skipped: int
    errors: list[str]


class PortfolioSummary(BaseModel):
    total_value: float
    total_value_twd: Optional[float] = None
    total_value_by_currency: dict[str, float] = Field(default_factory=dict)
    total_cost: float
    total_cost_twd: Optional[float] = None
    total_cost_by_currency: dict[str, float] = Field(default_factory=dict)
    unrealized_gain: float
    unrealized_gain_twd: Optional[float] = None
    unrealized_gain_by_currency: dict[str, float] = Field(default_factory=dict)
    unrealized_pct: float
    realized_gain: float
    realized_gain_twd: Optional[float] = None
    realized_gain_by_currency: dict[str, float] = Field(default_factory=dict)
    realized_pct: Optional[float] = None
    annualized_return: Optional[float] = None
    annualized_return_status: Optional[str] = None
    annualized_return_message: Optional[str] = None
    day_change: float
    day_change_pct: float
    fx_rate: Optional[float] = None
    last_updated: Optional[str] = None


class PerformancePoint(BaseModel):
    date: str
    value: float
    normalized_value: float


class BenchmarkSeries(BaseModel):
    name: str
    symbol: str
    market: str
    points: list[PerformancePoint]


class PortfolioPerformance(BaseModel):
    range: str
    start_date: str
    end_date: str
    portfolio: list[PerformancePoint]
    benchmarks: list[BenchmarkSeries]


class SnapshotCreate(BaseModel):
    date: date
    total_value: float
