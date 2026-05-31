from fastapi import APIRouter, HTTPException, Depends
from ..models import AccountCreate, AccountOut
from ..database import get_db
from ..routers.auth import get_current_user

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", 1)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, type, created_at FROM accounts WHERE user_id = %s ORDER BY id",
            (user_id,)
        )
        rows = cur.fetchall()
        return [AccountOut(
            id=dict(r)["id"],
            name=dict(r)["name"],
            type=dict(r)["type"],
            created_at=dict(r)["created_at"]
        ) for r in rows]


@router.post("", response_model=AccountOut)
def create_account(account: AccountCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", 1)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO accounts (name, type, currency, user_id) VALUES (%s, %s, %s, %s) RETURNING id, name, type, created_at",
            (account.name, account.type, account.currency, user_id)
        )
        row = dict(cur.fetchone())
        return AccountOut(id=row["id"], name=row["name"], type=row["type"], created_at=row["created_at"])