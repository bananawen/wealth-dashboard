from __future__ import annotations

import io
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..models import TransactionCreate, TransactionUpdate, TransactionOut, TransactionImportResult
from ..database import get_db
from ..routers.auth import get_current_user
from ..services.audit import log_transaction
from ..services.holding_projection_service import HoldingProjectionService
from ..services.market_service import MarketService
from ..services.transaction_service import auto_backfill_symbol

router = APIRouter(prefix="/transactions", tags=["transactions"])
_EPSILON = 1e-9
TRANSACTION_CATEGORIES = {
    "long_term": "long_term",
    "long-term": "long_term",
    "長期投資": "long_term",
    "短線": "short_term",
    "short_term": "short_term",
    "short-term": "short_term",
    "ETF": "etf",
    "etf": "etf",
    "個股": "stock",
    "stock": "stock",
    "定期定額": "dca",
    "dca": "dca",
}
ASSET_CLASSES = {
    "股票": "equity",
    "equity": "equity",
    "stock": "equity",
    "stocks": "equity",
    "股市": "equity",
    "債券": "bond",
    "bond": "bond",
    "bonds": "bond",
    "固定收益": "bond",
    "貴金屬": "precious_metal",
    "黃金": "precious_metal",
    "白銀": "precious_metal",
    "precious_metal": "precious_metal",
    "precious-metal": "precious_metal",
    "metal": "precious_metal",
    "現金": "cash",
    "cash": "cash",
    "其他": "other",
    "other": "other",
}
SECTORS = {
    "半導體": "semiconductor",
    "semiconductor": "semiconductor",
    "科技": "technology",
    "technology": "technology",
    "金融": "financial",
    "financial": "financial",
    "通訊": "communication",
    "communication": "communication",
    "消費": "consumer",
    "consumer": "consumer",
    "工業": "industrial",
    "industrial": "industrial",
    "醫療保健": "healthcare",
    "healthcare": "healthcare",
    "能源": "energy",
    "energy": "energy",
    "原物料": "materials",
    "materials": "materials",
    "公用事業": "utilities",
    "utilities": "utilities",
    "不動產": "real_estate",
    "real_estate": "real_estate",
    "real-estate": "real_estate",
    "大盤ETF": "broad_market",
    "大盤etf": "broad_market",
    "broad_market": "broad_market",
    "broad-market": "broad_market",
    "高股息ETF": "high_dividend",
    "高股息etf": "high_dividend",
    "high_dividend": "high_dividend",
    "high-dividend": "high_dividend",
    "主題ETF": "thematic",
    "主題etf": "thematic",
    "thematic": "thematic",
    "其他": "other",
    "other": "other",
}


def _row_to_transaction(row) -> TransactionOut:
    d = dict(row)
    tx_date = d["date"]
    if hasattr(tx_date, "date"):
        tx_date = tx_date.date()
    return TransactionOut(
        id=d["id"],
        symbol=d["symbol"],
        type=d["type"],
        shares=float(d["shares"]),
        price=float(d["price"]),
        date=tx_date,
        notes=d.get("notes"),
        category=d.get("category"),
        asset_class=d.get("asset_class"),
        sector=d.get("sector"),
        fee=float(d["fee"]) if d.get("fee") is not None else 0.0,
        tax=float(d["tax"]) if d.get("tax") is not None else 0.0,
        realized_gain=float(d["realized_gain"]) if d["realized_gain"] else 0.0,
    )


def _normalize_symbol(symbol: str) -> str:
    return MarketService.normalize_symbol(symbol)


def _normalize_notes(notes: str | None) -> str | None:
    if notes is None:
        return None
    cleaned = notes.strip()
    return cleaned or None


def _normalize_category(category: str | None) -> str | None:
    if category is None:
        return None
    cleaned = category.strip()
    if not cleaned:
        return None
    normalized = TRANSACTION_CATEGORIES.get(cleaned, TRANSACTION_CATEGORIES.get(cleaned.lower()))
    if normalized is None:
        raise HTTPException(
            status_code=400,
            detail="交易分類必須是 長期投資、短線、ETF、個股 或 定期定額",
        )
    return normalized


def _normalize_asset_class(asset_class: str | None) -> str | None:
    if asset_class is None:
        return None
    cleaned = asset_class.strip()
    if not cleaned:
        return None
    normalized = ASSET_CLASSES.get(cleaned, ASSET_CLASSES.get(cleaned.lower()))
    if normalized is None:
        raise HTTPException(
            status_code=400,
            detail="資產類別必須是 股票、債券、貴金屬、現金 或 其他",
        )
    return normalized


def _normalize_sector(sector: str | None) -> str | None:
    if sector is None:
        return None
    cleaned = sector.strip()
    if not cleaned:
        return None
    normalized = SECTORS.get(cleaned, SECTORS.get(cleaned.lower()))
    if normalized is None:
        raise HTTPException(
            status_code=400,
            detail="產業類別必須是 半導體、科技、金融、通訊、消費、工業、醫療保健、能源、原物料、公用事業、不動產、大盤ETF、高股息ETF、主題ETF 或 其他",
        )
    return normalized


def _coerce_asset_class_and_sector(asset_class: str | None, sector: str | None) -> tuple[str | None, str | None]:
    normalized_asset_class = _normalize_asset_class(asset_class)
    normalized_sector = _normalize_sector(sector)
    if normalized_sector and normalized_asset_class is None:
        normalized_asset_class = "equity"
    if normalized_sector and normalized_asset_class != "equity":
        raise HTTPException(status_code=400, detail="只有股票類資產可以設定產業類別")
    return normalized_asset_class, normalized_sector


def _validate_transaction_fields(
    symbol: str,
    shares: float,
    price: float,
    tx_type: str,
    fee: float = 0.0,
    tax: float = 0.0,
) -> tuple[str, str]:
    normalized_symbol = _normalize_symbol(symbol)
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="股票代號不可空")
    if shares is None or shares <= 0:
        raise HTTPException(status_code=400, detail="股數必須大於 0")
    if price is None or price <= 0:
        raise HTTPException(status_code=400, detail="價格必須大於 0")
    if fee is not None and fee < 0:
        raise HTTPException(status_code=400, detail="手續費不能小於 0")
    if tax is not None and tax < 0:
        raise HTTPException(status_code=400, detail="稅費不能小於 0")

    normalized_type = (tx_type or "").strip().lower()
    if normalized_type not in {"buy", "sell"}:
        raise HTTPException(status_code=400, detail="交易類型必須是 buy 或 sell")

    return normalized_symbol, normalized_type


def _rebuild_symbol_transaction_state(conn, symbol: str, user_id: int) -> None:
    """
    Recompute realized gain for all transactions of one symbol in chronological order.

    This keeps realized gain aligned with average-cost accounting whenever a
    transaction is created, updated, or deleted.
    """
    normalized_symbol = _normalize_symbol(symbol)
    cur = conn.cursor()
    cur.execute(
        """SELECT id, LOWER(type) AS type, quantity AS shares, price, transaction_date AS date,
                  COALESCE(fee, 0) AS fee, COALESCE(tax, 0) AS tax
           FROM transactions
           WHERE user_id = %s AND UPPER(symbol) = %s
           ORDER BY transaction_date ASC, id ASC""",
        (user_id, normalized_symbol),
    )
    rows = cur.fetchall()

    position_shares = 0.0
    position_cost = 0.0

    for row in rows:
        tx = dict(row)
        tx_id = int(tx["id"])
        tx_type = str(tx["type"]).upper()
        shares = float(tx["shares"] or 0.0)
        price = float(tx["price"] or 0.0)
        fee = float(tx.get("fee") or 0.0)
        tax = float(tx.get("tax") or 0.0)

        if shares <= 0:
            raise HTTPException(status_code=400, detail="股數必須大於 0")
        if price <= 0:
            raise HTTPException(status_code=400, detail="價格必須大於 0")

        if tx_type == "BUY":
            realized_gain = 0.0
            position_shares += shares
            position_cost += shares * price + fee + tax
        elif tx_type == "SELL":
            if position_shares + _EPSILON < shares:
                raise HTTPException(
                    status_code=400,
                    detail=f"賣出股數不足：目前累計可賣出 {position_shares} 股，欲賣出 {shares} 股",
                )
            avg_cost = position_cost / position_shares if position_shares > 0 else 0.0
            realized_gain = (price - avg_cost) * shares - fee - tax
            position_shares -= shares
            position_cost -= avg_cost * shares
            if abs(position_shares) <= _EPSILON:
                position_shares = 0.0
                position_cost = 0.0
        else:
            raise HTTPException(status_code=400, detail="交易類型必須是 buy 或 sell")

        cur.execute(
            "UPDATE transactions SET realized_gain = %s WHERE id = %s AND user_id = %s",
            (realized_gain, tx_id, user_id),
        )

    HoldingProjectionService.recompute_holding(conn, normalized_symbol, user_id)


@router.get("", response_model=list[TransactionOut])
def list_transactions(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, symbol, LOWER(type) AS type,
                      quantity AS shares, price, transaction_date AS date,
                      notes, category, asset_class, sector, fee, tax, realized_gain
               FROM transactions
               WHERE user_id = %s
               ORDER BY transaction_date DESC""",
            (user_id,)
        )
        rows = cur.fetchall()
        return [_row_to_transaction(row) for row in rows]


@router.post("", response_model=TransactionOut)
def create_transaction(tx: TransactionCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    notes = _normalize_notes(tx.notes)
    category = _normalize_category(tx.category)
    asset_class, sector = _coerce_asset_class_and_sector(tx.asset_class, tx.sector)
    fee = float(tx.fee or 0.0)
    tax = float(tx.tax or 0.0)
    symbol, tx_type = _validate_transaction_fields(tx.symbol, tx.shares, tx.price, tx.type, fee, tax)
    with get_db() as conn:
        cur = conn.cursor()
        profile = MarketService.ensure_symbol_profile(conn, symbol)
        currency = profile.currency

        cur.execute(
            """INSERT INTO transactions (symbol, type, quantity, price, fee, tax, transaction_date, notes, category, asset_class, sector, realized_gain, user_id, currency)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id, symbol, LOWER(type) AS type,
                         quantity AS shares, price, transaction_date AS date,
                         notes, category, asset_class, sector, fee, tax, realized_gain""",
            (symbol, tx_type.upper(), tx.shares, tx.price, fee, tax, tx.date, notes, category, asset_class, sector, 0.0, user_id, currency),
        )
        row = cur.fetchone()

        _rebuild_symbol_transaction_state(conn, symbol, user_id)
        cur.execute(
            """SELECT id, symbol, LOWER(type) AS type,
                      quantity AS shares, price, transaction_date AS date,
                      notes, category, asset_class, sector, fee, tax, realized_gain
               FROM transactions
               WHERE id = %s AND user_id = %s""",
            (row["id"], user_id),
        )
        row = cur.fetchone()

        result = _row_to_transaction(row)

    log_transaction(
        action="create",
        tx_id=result.id,
        symbol=symbol,
        tx_type=tx_type.upper(),
        user_id=user_id,
        details={"shares": tx.shares, "price": tx.price},
    )
    auto_backfill_symbol(symbol)

    return result


@router.put("/{transaction_id}", response_model=TransactionOut)
def update_transaction(transaction_id: int, tx: TransactionUpdate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, symbol, LOWER(type) AS type,
                      quantity AS shares, price, transaction_date AS date,
                      notes, category, asset_class, sector, fee, tax, realized_gain
               FROM transactions
               WHERE id = %s AND user_id = %s""",
            (transaction_id, user_id),
        )
        old_row = cur.fetchone()
        if not old_row:
            raise HTTPException(status_code=404, detail="找不到該交易")

        old = dict(old_row)
        symbol = _normalize_symbol(tx.symbol) if tx.symbol is not None else _normalize_symbol(old["symbol"])
        tx_type = (tx.type or old["type"]).strip().lower()
        shares = tx.shares if tx.shares is not None else float(old["shares"])
        price = tx.price if tx.price is not None else float(old["price"])
        tx_date = tx.date if tx.date is not None else old["date"]
        notes = _normalize_notes(tx.notes) if tx.notes is not None else old.get("notes")
        category = _normalize_category(tx.category) if tx.category is not None else old.get("category")
        requested_asset_class = tx.asset_class if tx.asset_class is not None else old.get("asset_class")
        requested_sector = tx.sector if tx.sector is not None else old.get("sector")
        asset_class, sector = _coerce_asset_class_and_sector(requested_asset_class, requested_sector)
        fee = float(tx.fee if tx.fee is not None else old.get("fee") or 0.0)
        tax = float(tx.tax if tx.tax is not None else old.get("tax") or 0.0)
        symbol, tx_type = _validate_transaction_fields(symbol, shares, price, tx_type, fee, tax)
        profile = MarketService.ensure_symbol_profile(conn, symbol)
        currency = profile.currency

        cur.execute(
            """UPDATE transactions
               SET symbol = %s, type = %s, quantity = %s, price = %s,
                   fee = %s, tax = %s, transaction_date = %s, notes = %s, category = %s, asset_class = %s, sector = %s,
                   realized_gain = %s, currency = %s
               WHERE id = %s AND user_id = %s
               RETURNING id, symbol, LOWER(type) AS type,
                         quantity AS shares, price, transaction_date AS date,
                         notes, category, asset_class, sector, fee, tax, realized_gain""",
            (symbol, tx_type.upper(), shares, price, fee, tax, tx_date, notes, category, asset_class, sector, 0.0, currency, transaction_id, user_id),
        )
        row = cur.fetchone()

        symbols_to_rebuild = {_normalize_symbol(old["symbol"]), symbol}
        for rebuilt_symbol in symbols_to_rebuild:
            _rebuild_symbol_transaction_state(conn, rebuilt_symbol, user_id)

        cur.execute(
            """SELECT id, symbol, LOWER(type) AS type,
                      quantity AS shares, price, transaction_date AS date, notes, category, asset_class, sector, fee, tax, realized_gain
               FROM transactions
               WHERE id = %s AND user_id = %s""",
            (transaction_id, user_id),
        )
        row = cur.fetchone()

        result = _row_to_transaction(row)

    log_transaction(
        action="update",
        tx_id=result.id,
        symbol=symbol,
        tx_type=tx_type,
        user_id=user_id,
        details={"shares": shares, "price": price},
    )
    return result


@router.delete("/{transaction_id}", response_model=TransactionOut)
def delete_transaction(transaction_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, symbol, LOWER(type) AS type,
                      quantity AS shares, price, transaction_date AS date, notes, category, asset_class, sector, fee, tax, realized_gain
               FROM transactions
               WHERE id = %s AND user_id = %s""",
            (transaction_id, user_id)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="找不到該交易")
        symbol = row["symbol"]

        cur.execute(
            "DELETE FROM transactions WHERE id = %s AND user_id = %s",
            (transaction_id, user_id)
        )

        _rebuild_symbol_transaction_state(conn, symbol, user_id)

    log_transaction(
        action="delete",
        tx_id=transaction_id,
        symbol=symbol,
        tx_type=str(row["type"]).upper(),
        user_id=user_id,
        details={"reason": "user_deleted"},
    )
    return _row_to_transaction(row)


def _load_import_dataframe(file_name: str, raw_bytes: bytes) -> pd.DataFrame:
    lowered = file_name.lower()
    if lowered.endswith(".csv"):
        dataframe = pd.read_csv(io.BytesIO(raw_bytes))
    if lowered.endswith(".xlsx") or lowered.endswith(".xlsm"):
        dataframe = pd.read_excel(io.BytesIO(raw_bytes), engine="openpyxl")
    else:
        if not lowered.endswith(".csv"):
            raise HTTPException(status_code=400, detail="僅支援 CSV 或 Excel (.xlsx / .xlsm) 檔案")
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    return dataframe


def _extract_import_value(row: dict, *names: str):
    normalized_candidates = {name.lower().strip() for name in names}
    for name in names:
        if name in row and row[name] is not None and str(row[name]).strip() != "":
            return row[name]
    for key, value in row.items():
        if str(key).lower().strip() in normalized_candidates and value is not None and str(value).strip() != "":
            return value
    return None


def _parse_import_row(raw_row: dict, index: int) -> dict:
    symbol = _extract_import_value(raw_row, "symbol", "ticker", "股票代號", "代碼")
    tx_type = _extract_import_value(raw_row, "type", "transaction_type", "買賣", "交易類型")
    shares = _extract_import_value(raw_row, "shares", "quantity", "股數")
    price = _extract_import_value(raw_row, "price", "成交價", "價格")
    tx_date = _extract_import_value(raw_row, "date", "transaction_date", "交易日期")
    notes = _extract_import_value(raw_row, "notes", "note", "備註", "買入理由", "策略")
    category = _extract_import_value(raw_row, "category", "分類", "交易分類")
    asset_class = _extract_import_value(raw_row, "asset_class", "資產類別", "資產分類", "allocation")
    sector = _extract_import_value(raw_row, "sector", "產業", "產業類別", "sector_class")
    fee = _extract_import_value(raw_row, "fee", "手續費")
    tax = _extract_import_value(raw_row, "tax", "稅費", "taxes")

    if symbol is None or tx_type is None or shares is None or price is None or tx_date is None:
        raise ValueError(f"第 {index} 列缺少必要欄位")

    parsed_date = pd.to_datetime(tx_date).date()
    normalized_asset_class, normalized_sector = _coerce_asset_class_and_sector(
        None if asset_class is None else str(asset_class),
        None if sector is None else str(sector),
    )
    return {
        "symbol": str(symbol).strip(),
        "type": str(tx_type).strip(),
        "shares": float(shares),
        "price": float(price),
        "date": parsed_date,
        "notes": _normalize_notes(None if notes is None else str(notes)),
        "category": _normalize_category(None if category is None else str(category)),
        "asset_class": normalized_asset_class,
        "sector": normalized_sector,
        "fee": float(fee or 0.0),
        "tax": float(tax or 0.0),
    }


@router.post("/import", response_model=TransactionImportResult)
async def import_transactions(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    raw = await file.read()
    dataframe = _load_import_dataframe(file.filename or "transactions.csv", raw)
    if dataframe.empty:
        return TransactionImportResult(created=0, skipped=0, errors=["匯入檔案沒有資料列"])

    records = dataframe.where(pd.notnull(dataframe), None).to_dict(orient="records")
    created = 0
    skipped = 0
    errors: list[str] = []
    touched_symbols: set[str] = set()
    log_entries: list[dict] = []

    with get_db() as conn:
        cur = conn.cursor()
        for idx, raw_row in enumerate(records, start=2):
            try:
                row = _parse_import_row(raw_row, idx)
                symbol, tx_type = _validate_transaction_fields(
                    row["symbol"], row["shares"], row["price"], row["type"], row["fee"], row["tax"]
                )
                profile = MarketService.ensure_symbol_profile(conn, symbol)
                currency = profile.currency
                cur.execute(
                    """INSERT INTO transactions (symbol, type, quantity, price, fee, tax, transaction_date, notes, category, asset_class, sector, realized_gain, user_id, currency)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       RETURNING id""",
                    (
                        symbol,
                        tx_type.upper(),
                        row["shares"],
                        row["price"],
                        row["fee"],
                        row["tax"],
                        row["date"],
                        row["notes"],
                        row["category"],
                        row["asset_class"],
                        row["sector"],
                        0.0,
                        user_id,
                        currency,
                    ),
                )
                returned = cur.fetchone()
                touched_symbols.add(symbol)
                created += 1
                log_entries.append({
                    "tx_id": int(returned["id"]),
                    "symbol": symbol,
                    "tx_type": tx_type.upper(),
                    "shares": row["shares"],
                    "price": row["price"],
                })
            except Exception as exc:
                skipped += 1
                errors.append(f"第 {idx} 列：{exc}")

        for symbol in sorted(touched_symbols):
            _rebuild_symbol_transaction_state(conn, symbol, user_id)

    for entry in log_entries:
        log_transaction(
            action="create",
            tx_id=entry["tx_id"],
            symbol=entry["symbol"],
            tx_type=entry["tx_type"],
            user_id=user_id,
            details={
                "shares": entry["shares"],
                "price": entry["price"],
                "source": "bulk_import",
            },
        )

    for symbol in sorted(touched_symbols):
        auto_backfill_symbol(symbol)

    return TransactionImportResult(created=created, skipped=skipped, errors=errors)
