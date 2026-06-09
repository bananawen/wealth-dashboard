from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from ..models import UserCreate, UserOut, Token
from ..database import get_db
from ..config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 無效")


@router.post("/register", response_model=UserOut)
def register(user: UserCreate):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s", (user.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="帳號已存在")
        hashed = hash_password(user.password)
        cur.execute(
            "INSERT INTO users (username, hashed_password) VALUES (%s, %s) RETURNING id, username",
            (user.username, hashed)
        )
        row = cur.fetchone()
        return UserOut(id=row["id"], username=row["username"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, hashed_password FROM users WHERE username = %s", (form_data.username,))
        row = cur.fetchone()
        if not row or not verify_password(form_data.password, row["hashed_password"]):
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
        token = create_access_token({"sub": row["username"], "user_id": row["id"]})
        return Token(access_token=token, token_type="bearer")


@router.put("/password")
def change_password(
    old_password: str = Body(...),
    new_password: str = Body(...),
    token: str = Depends(oauth2_scheme)
):
    """更換當前用戶密碼"""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
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

        if old_password == new_password:
            raise HTTPException(status_code=400, detail="新密碼不能與舊密碼相同")

        hashed = hash_password(new_password)
        cur.execute("UPDATE users SET hashed_password = %s WHERE username = %s", (hashed, username))
        return {"message": "密碼修改成功"}