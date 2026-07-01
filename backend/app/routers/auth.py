import re

from fastapi import APIRouter, HTTPException, Depends, Body, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from ..models import UserCreate, UserOut, Token
from ..database import get_db
from ..config import get_settings
from ..services.audit import write_log

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

PASSWORD_MIN_LENGTH = 8


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def validate_password(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(status_code=400, detail=f"密碼至少需要 {PASSWORD_MIN_LENGTH} 個字元")
    if re.search(r"\s", password):
        raise HTTPException(status_code=400, detail="密碼不能包含空白字元")


def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _log_auth_event(action: str, level: str, message: str, **details) -> None:
    write_log(
        type="auth",
        level=level,
        message=message,
        details={"action": action, **{k: v for k, v in details.items() if v is not None}},
    )


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 無效")


def require_admin_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = get_current_user(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token 無效")

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        role = row["role"] if row and row["role"] else "user"

    if role != "admin":
        raise HTTPException(status_code=403, detail="需要系統管理權限")
    payload["role"] = role
    return payload


def _get_user_count() -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS total FROM users")
        row = cur.fetchone()
        return int(row["total"] if row else 0)


@router.post("/register", response_model=UserOut)
def register(request: Request, user: UserCreate):
    validate_password(user.password)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="帳號已存在")
        role = "admin" if _get_user_count() == 0 else "user"
        hashed = hash_password(user.password)
        cur.execute(
            "INSERT INTO users (username, hashed_password, role) VALUES (%s, %s, %s) RETURNING id, username",
            (user.username, hashed, role)
        )
        row = cur.fetchone()
    _log_auth_event(
        "register",
        "info",
        f"註冊成功: {user.username}",
        username=user.username,
        role=role,
        client_ip=request.client.host if request.client else None,
    )
    return UserOut(id=row["id"], username=row["username"])


@router.post("/login", response_model=Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, hashed_password, COALESCE(role, 'user') AS role FROM users WHERE username = %s",
            (form_data.username,),
        )
        row = cur.fetchone()
        if not row or not verify_password(form_data.password, row["hashed_password"]):
            _log_auth_event(
                "login_failed",
                "warning",
                f"登入失敗: {form_data.username}",
                username=form_data.username,
                client_ip=request.client.host if request and request.client else None,
            )
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
        token = create_access_token({"sub": row["username"], "user_id": row["id"], "role": row["role"] or "user"})
    _log_auth_event(
        "login",
        "info",
        f"登入成功: {row['username']}",
        username=row["username"],
        user_id=row["id"],
        role=row["role"] or "user",
        client_ip=request.client.host if request and request.client else None,
    )
    return Token(access_token=token, token_type="bearer")


@router.put("/password")
def change_password(
    old_password: str = Body(...),
    new_password: str = Body(...),
    token: str = Depends(oauth2_scheme)
):
    """更換當前用戶密碼"""
    validate_password(new_password)
    if old_password == new_password:
        raise HTTPException(status_code=400, detail="新密碼不能與舊密碼相同")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 無效")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token 無效")

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT hashed_password FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用戶不存在")

        if not verify_password(old_password, row["hashed_password"]):
            raise HTTPException(status_code=400, detail="舊密碼錯誤")

        hashed = hash_password(new_password)
        cur.execute("UPDATE users SET hashed_password = %s WHERE username = %s", (hashed, username))
    _log_auth_event("password_change", "info", f"密碼修改成功: {username}", username=username)
    return {"message": "密碼修改成功"}
