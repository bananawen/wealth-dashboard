from contextlib import contextmanager

from app.routers.admin import _audit_type_synonyms, _fetch_audit_logs, _normalize_audit_type


def test_normalize_audit_type_maps_legacy_values():
    assert _normalize_audit_type("scrape") == "scraper"
    assert _normalize_audit_type("db_change") == "transaction"
    assert _normalize_audit_type("api_call") == "admin"
    assert _normalize_audit_type("auth") == "auth"


def test_audit_type_synonyms_cover_legacy_filters():
    assert "scrape" in _audit_type_synonyms("scraper")
    assert "db_change" in _audit_type_synonyms("transaction")
    assert "api_call" in _audit_type_synonyms("admin")


def test_fetch_audit_logs_total_respects_filters(monkeypatch):
    rows = [
        {
            "id": 1,
            "type": "auth",
            "message": "login ok",
            "timestamp": "2026-06-27T12:00:00",
            "details": None,
            "symbol": None,
            "user_id": 1,
            "level": "INFO",
        }
    ]

    class FakeCursor:
        def __init__(self):
            self.step = 0

        def execute(self, sql, params=None):
            self.step += 1

        def fetchall(self):
            return rows

        def fetchone(self):
            return {"total": 1}

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    @contextmanager
    def fake_get_db():
        yield FakeConnection()

    monkeypatch.setattr("app.routers.admin.get_db", fake_get_db)

    logs, total = _fetch_audit_logs(log_type="auth", q="login", limit=50)

    assert len(logs) == 1
    assert total == 1
