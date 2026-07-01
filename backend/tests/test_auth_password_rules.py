import pytest
from fastapi import HTTPException

from app.routers.auth import require_admin_user, validate_password


def test_validate_password_accepts_strong_password():
    validate_password("Passw0rd!")


@pytest.mark.parametrize(
    "password, expected_detail",
    [
        ("short", "密碼至少需要 8 個字元"),
        ("with space", "密碼不能包含空白字元"),
        ("tab\tspace", "密碼不能包含空白字元"),
    ],
)
def test_validate_password_rejects_invalid_passwords(password, expected_detail):
    with pytest.raises(HTTPException) as exc:
        validate_password(password)

    assert exc.value.status_code == 400
    assert exc.value.detail == expected_detail


def test_require_admin_user_rejects_non_admin_with_system_management_message(monkeypatch):
    class FakeCursor:
        def execute(self, sql, params=None):
            return None

        def fetchone(self):
            return {"role": "user"}

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    class FakeDbContext:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.routers.auth.get_current_user", lambda token: {"sub": "demo"})
    monkeypatch.setattr("app.routers.auth.get_db", lambda: FakeDbContext())

    with pytest.raises(HTTPException) as exc:
        require_admin_user(token="fake-token")

    assert exc.value.status_code == 403
    assert exc.value.detail == "需要系統管理權限"
