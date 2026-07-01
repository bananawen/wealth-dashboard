from fastapi import APIRouter, Depends, Query
from ..models import PortfolioPerformance, PortfolioSummary, SnapshotCreate
from ..database import get_db
from ..routers.auth import get_current_user
from ..services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/summary", response_model=PortfolioSummary)
def get_portfolio_summary(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    return PortfolioService.get_summary(user_id)


@router.get("/performance", response_model=PortfolioPerformance)
def get_portfolio_performance(
    range: str = Query("all", pattern="^(today|week|month|year|all)$"),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    return PortfolioService.get_performance(user_id, range_key=range)


@router.get("/history")
def get_history(current_user: dict = Depends(get_current_user)):
    """歷史總市值趨勢（從 portfolio_snapshots）"""
    user_id = current_user.get("user_id")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT date, total_value FROM portfolio_snapshots WHERE user_id = %s ORDER BY date",
            (user_id,)
        )
        rows = cur.fetchall()
        return [{"date": str(dict(r)["date"]), "value": float(dict(r)["total_value"])} for r in rows]


@router.post("/snapshot")
def create_snapshot(snap: SnapshotCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO portfolio_snapshots (date, total_value, user_id)
               VALUES (%s, %s, %s)
               ON CONFLICT (date, user_id) DO UPDATE SET total_value = EXCLUDED.total_value""",
            (snap.date, snap.total_value, user_id)
        )
    return {"ok": True}
