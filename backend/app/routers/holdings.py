from fastapi import APIRouter, HTTPException, Depends, Response
from ..models import HoldingCreate, HoldingUpdate, HoldingOut
from ..database import get_db
from ..routers.auth import get_current_user
from ..services.holding_service import HoldingService

router = APIRouter(prefix="/holdings", tags=["holdings"])


def _row_to_holding(row) -> HoldingOut:
    """Map a holdings DB row to HoldingOut (uses actual DB schema)."""
    d = dict(row)
    return HoldingOut(
        id=d["id"],
        symbol=d["symbol"],
        shares=float(d["shares"]),
        avg_cost=float(d["avg_cost"]),
        total_cost=float(d["total_cost"]),
        currency=d.get("currency", "TWD"),
    )


@router.get("", response_model=list[HoldingOut])
def list_holdings(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, symbol, shares, avg_cost, total_cost, currency "
            "FROM holdings WHERE shares > 0 AND user_id = %s ORDER BY id",
            (user_id,)
        )
        rows = cur.fetchall()
        return [_row_to_holding(row) for row in rows]


@router.post("", response_model=HoldingOut)
def create_holding(holding: HoldingCreate, current_user: dict = Depends(get_current_user)):
    raise HTTPException(
        status_code=410,
        detail="持倉是由交易自動計算的唯讀資料，請改用 /transactions 新增 BUY 交易",
    )


@router.put("/{holding_id}", response_model=HoldingOut)
def update_holding(holding_id: int, holding: HoldingUpdate, current_user: dict = Depends(get_current_user)):
    raise HTTPException(
        status_code=410,
        detail="持倉是由交易自動計算的唯讀資料，請改用 /transactions 修改交易",
    )


@router.get("/computed", response_model=list[dict])
def get_computed_holdings(response: Response, current_user: dict = Depends(get_current_user)):
    """Fetch all active holdings with real-time market prices computed."""
    # No cache - always return fresh data
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    user_id = current_user.get("user_id")
    return HoldingService.get_computed_holdings(user_id)


@router.delete("/{holding_id}")
def delete_holding(holding_id: int, current_user: dict = Depends(get_current_user)):
    raise HTTPException(
        status_code=410,
        detail="持倉是由交易自動計算的唯讀資料，請改用 /transactions 刪除或調整交易",
    )
