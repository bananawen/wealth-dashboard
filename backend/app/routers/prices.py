from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..database import get_db
from ..routers.auth import get_current_user

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


class LatestPrice(BaseModel):
    symbol: str
    price_date: str
    close: float
    volume: int
    currency: str
    market: str


def _fetch_price_rows(table: str, symbol: str, days: int) -> list[PriceRecord]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days * 2)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT symbol, price_date, open, high, low, close, volume, currency
            FROM {table}
            WHERE symbol = %s
              AND price_date <= %s
              AND price_date >= %s
            ORDER BY price_date DESC
            LIMIT %s
            """,
            (symbol, end_date.isoformat(), start_date.isoformat(), days),
        )
        rows = cur.fetchall()

    return [
        PriceRecord(
            symbol=str(row["symbol"]),
            price_date=str(row["price_date"]),
            open=float(row["open"] or 0),
            high=float(row["high"] or 0),
            low=float(row["low"] or 0),
            close=float(row["close"] or 0),
            volume=int(row["volume"] or 0),
            currency=str(row["currency"] or ""),
        )
        for row in rows
    ]


@router.get("/tw", response_model=list[PriceRecord])
def get_taiwan_price(
    symbol: str = Query(..., description="Taiwan stock code, e.g. 2330"),
    days: int = Query(30, ge=1, le=3650),
    current_user: dict = Depends(get_current_user),
):
    del current_user
    return _fetch_price_rows("price_history_tw", symbol.strip().upper(), days)


@router.get("/us", response_model=list[PriceRecord])
def get_us_price(
    symbol: str = Query(..., description="US stock ticker, e.g. AAPL"),
    days: int = Query(30, ge=1, le=3650),
    current_user: dict = Depends(get_current_user),
):
    del current_user
    return _fetch_price_rows("price_history_us", symbol.strip().upper(), days)


@router.get("/latest", response_model=list[LatestPrice])
def get_latest_prices(current_user: dict = Depends(get_current_user)):
    del current_user

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT symbol, price_date, close, volume, currency, 'TW' AS market
            FROM (
                SELECT symbol, price_date, close, volume, currency,
                       ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY price_date DESC) AS rn
                FROM price_history_tw
            )
            WHERE rn = 1
            """
        )
        tw_rows = cur.fetchall()

        cur.execute(
            """
            SELECT symbol, price_date, close, volume, currency, 'US' AS market
            FROM (
                SELECT symbol, price_date, close, volume, currency,
                       ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY price_date DESC) AS rn
                FROM price_history_us
            )
            WHERE rn = 1
            """
        )
        us_rows = cur.fetchall()

    return [
        LatestPrice(
            symbol=str(row["symbol"]),
            price_date=str(row["price_date"]),
            close=float(row["close"] or 0),
            volume=int(row["volume"] or 0),
            currency=str(row["currency"] or ""),
            market=str(row["market"]),
        )
        for row in [*tw_rows, *us_rows]
    ]
