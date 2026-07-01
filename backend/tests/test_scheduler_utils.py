from datetime import date, timedelta
from contextlib import contextmanager

from app.scrapers.price_scheduler import _get_symbols_for_currency
from app.services.market_service import MarketService
from app.services.transaction_service import get_symbol_backfill_start_date


def test_get_symbols_for_currency_uses_transaction_currency_and_symbol_fallback(monkeypatch):
    rows = [
        {"symbol": "AAPL", "currency": "USD"},
        {"symbol": "0050", "currency": "TWD"},
        {"symbol": "MSFT", "currency": ""},
        {"symbol": "2330", "currency": None},
    ]

    class FakeCursor:
        def execute(self, sql, params=None):
            return None

        def fetchall(self):
            return rows

        def close(self):
            return None

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    @contextmanager
    def fake_get_db():
        yield FakeConnection()

    monkeypatch.setattr("app.database.get_db", fake_get_db)

    assert _get_symbols_for_currency("USD") == ["AAPL", "MSFT"]
    assert _get_symbols_for_currency("TWD") == ["0050", "2330"]


def test_get_symbol_backfill_start_date_prefers_first_buy(monkeypatch):
    row = {
        "first_buy_date": date(2024, 3, 15),
        "first_transaction_date": date(2024, 2, 1),
    }

    class FakeCursor:
        def execute(self, sql, params=None):
            return None

        def fetchone(self):
            return row

        def close(self):
            return None

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    @contextmanager
    def fake_get_db():
        yield FakeConnection()

    monkeypatch.setattr("app.database.get_db", fake_get_db)

    assert get_symbol_backfill_start_date("0050") == date(2024, 3, 15)


def test_get_symbol_backfill_start_date_falls_back_to_first_transaction(monkeypatch):
    row = {
        "first_buy_date": None,
        "first_transaction_date": date(2024, 5, 20),
    }

    class FakeCursor:
        def execute(self, sql, params=None):
            return None

        def fetchone(self):
            return row

        def close(self):
            return None

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    @contextmanager
    def fake_get_db():
        yield FakeConnection()

    monkeypatch.setattr("app.database.get_db", fake_get_db)

    assert get_symbol_backfill_start_date("0050") == date(2024, 5, 20)


def test_get_symbol_backfill_start_date_uses_five_year_fallback(monkeypatch):
    class FakeCursor:
        def execute(self, sql, params=None):
            return None

        def fetchone(self):
            return {"first_buy_date": None, "first_transaction_date": None}

        def close(self):
            return None

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    @contextmanager
    def fake_get_db():
        yield FakeConnection()

    monkeypatch.setattr("app.database.get_db", fake_get_db)

    result = get_symbol_backfill_start_date("0050")
    expected = date.today() - timedelta(days=365 * 5)
    assert abs((result - expected).days) <= 1


def test_market_service_normalizes_alias_symbol():
    assert MarketService.normalize_symbol("00631") == "00631L"
    assert MarketService.normalize_symbol("00631l") == "00631L"


def test_market_service_keeps_exact_taiwan_symbol(monkeypatch):
    monkeypatch.setattr(
        MarketService,
        "_load_tw_symbols",
        classmethod(lambda cls: ({"00631L"}, set())),
    )
    monkeypatch.setattr(MarketService, "_suffix_aliases", None)
    assert MarketService.normalize_symbol("00631L") == "00631L"


def test_market_service_auto_maps_unique_suffix_symbol(monkeypatch):
    monkeypatch.setattr(
        MarketService,
        "_load_tw_symbols",
        classmethod(lambda cls: ({"00631L"}, set())),
    )
    monkeypatch.setattr(MarketService, "_suffix_aliases", None)
    assert MarketService.normalize_symbol("00631") == "00631L"


def test_market_service_does_not_guess_ambiguous_suffix_symbol(monkeypatch):
    monkeypatch.setattr(
        MarketService,
        "_load_tw_symbols",
        classmethod(lambda cls: ({"03029U", "03029X"}, set())),
    )
    monkeypatch.setattr(MarketService, "_suffix_aliases", None)
    assert MarketService.normalize_symbol("03029") == "03029"


def test_market_service_infers_twse_for_taiwan_suffix_symbol(monkeypatch):
    monkeypatch.setattr(
        MarketService,
        "_load_tw_symbols",
        classmethod(lambda cls: ({"00631L"}, set())),
    )
    monkeypatch.setattr(MarketService, "_suffix_aliases", None)
    assert MarketService.infer_exchange("00631L") == "TWSE"
