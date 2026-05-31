"""
Thin async router — delegates all DB logic to service layer.
"""
from datetime import date, timedelta
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..database import get_session

router = APIRouter(prefix="/prices", tags=["prices"])


class PriceRecord(BaseModel):
    symbol: str
    price_date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    currency: str


# ── Taiwan ───────────────────────────────────────────────────────────────────

@router.get("/tw", response_model=List[PriceRecord])
async def get_taiwan_price(
    symbol: str = Query(..., description="Taiwan stock code, e.g. 2330"),
    days: int = Query(30, ge=1, le=3650),
    session: AsyncSession = Depends(get_session),
):
    """
    Taiwan stock historical OHLCV.
    Reads from price_history_tw (TWSE + TPEx data merged into one table).
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days * 2)

    result = await session.execute(
        text("""
            SELECT symbol, price_date::text, open, high, low, close, volume, currency
            FROM price_history_tw
            WHERE symbol = :symbol
              AND price_date <= :end_date
              AND price_date >= :start_date
            ORDER BY price_date DESC
            LIMIT :days
        """),
        {"symbol": symbol, "end_date": end_date, "start_date": start_date, "days": days},
    )
    rows = result.fetchall()

    return [
        PriceRecord(
            symbol=r[0],
            price_date=r[1],
            open=float(r[2]),
            high=float(r[3]),
            low=float(r[4]),
            close=float(r[5]),
            volume=int(r[6]),
            currency=r[7],
        )
        for r in rows
    ]


# ── US ───────────────────────────────────────────────────────────────────────

@router.get("/us", response_model=List[PriceRecord])
async def get_us_price(
    symbol: str = Query(..., description="US stock ticker, e.g. AAPL"),
    days: int = Query(30, ge=1, le=3650),
    session: AsyncSession = Depends(get_session),
):
    """
    US stock historical OHLCV.
    Reads from price_history_us.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days * 2)

    result = await session.execute(
        text("""
            SELECT symbol, price_date::text, open, high, low, close, volume, currency
            FROM price_history_us
            WHERE symbol = :symbol
              AND price_date <= :end_date
              AND price_date >= :start_date
            ORDER BY price_date DESC
            LIMIT :days
        """),
        {"symbol": symbol.upper(), "end_date": end_date, "start_date": start_date, "days": days},
    )
    rows = result.fetchall()

    return [
        PriceRecord(
            symbol=r[0],
            price_date=r[1],
            open=float(r[2]),
            high=float(r[3]),
            low=float(r[4]),
            close=float(r[5]),
            volume=int(r[6]),
            currency=r[7],
        )
        for r in rows
    ]


# ── Latest (union, for dashboard) ────────────────────────────────────────────

class LatestPrice(BaseModel):
    symbol: str
    price_date: str
    close: float
    volume: int
    currency: str
    market: str   # 'TW' or 'US'


@router.get("/latest", response_model=List[LatestPrice])
async def get_latest_prices(session: AsyncSession = Depends(get_session)):
    """
    Most recent closing price for every symbol in both price tables.
    Useful for dashboard instant-refresh without scraping.
    """
    # TW — latest per symbol
    tw_result = await session.execute(text("""
        SELECT DISTINCT ON (symbol)
            symbol, price_date::text, close, volume, currency, 'TW' AS market
        FROM price_history_tw
        ORDER BY symbol, price_date DESC
    """))
    tw_rows = tw_result.fetchall()

    # US — latest per symbol
    us_result = await session.execute(text("""
        SELECT DISTINCT ON (symbol)
            symbol, price_date::text, close, volume, currency, 'US' AS market
        FROM price_history_us
        ORDER BY symbol, price_date DESC
    """))
    us_rows = us_result.fetchall()

    return [
        LatestPrice(
            symbol=r[0],
            price_date=r[1],
            close=float(r[2]),
            volume=int(r[3]),
            currency=r[4],
            market=r[5],
        )
        for r in tw_rows + us_rows
    ]