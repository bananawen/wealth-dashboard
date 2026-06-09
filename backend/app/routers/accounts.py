from fastapi import APIRouter, HTTPException, Depends
from ..models import AccountCreate, AccountOut
from ..database import get_db
from ..routers.auth import get_current_user

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(current_user: dict = Depends(get_current_user)):
    """
    DEPRECATED: accounts concept removed.
    Returns empty list — each user holds stocks directly.
    """
    return []


@router.post("", response_model=AccountOut)
def create_account(account: AccountCreate, current_user: dict = Depends(get_current_user)):
    """
    DEPRECATED: accounts concept removed.
    Returns410 Gone — accounts are no longer supported.
    """
    raise HTTPException(
        status_code=410,
        detail="帳戶功能已移除，請直接使用「新增交易」來建立持股"
    )
