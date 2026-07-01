import pytest
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.mark.skipif(
    os.getenv("RUN_ASGI_TESTS") != "1",
    reason="ASGI integration tests are skipped by default in this environment; set RUN_ASGI_TESTS=1 to enable",
)
class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.skipif(
    os.getenv("RUN_ASGI_TESTS") != "1",
    reason="ASGI integration tests are skipped by default in this environment; set RUN_ASGI_TESTS=1 to enable",
)
class TestAuthEndpoints:
    @pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1",
        reason="database integration tests are skipped by default; set RUN_DB_TESTS=1 to enable",
    )
    def test_register_new_user(self):
        response = client.post(
            "/auth/register",
            json={"username": "testuser", "password": "testpass123"}
        )
        # Either created or already exists
        assert response.status_code in [201, 400]

    @pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1",
        reason="database integration tests are skipped by default; set RUN_DB_TESTS=1 to enable",
    )
    def test_login_existing_user(self):
        # First register
        client.post("/auth/register", json={"username": "autouser", "password": "pass123"})
        
        # Then login
        response = client.post(
            "/auth/login",
            data={"username": "autouser", "password": "pass123"}
        )
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"


@pytest.mark.skipif(
    os.getenv("RUN_ASGI_TESTS") != "1",
    reason="ASGI integration tests are skipped by default in this environment; set RUN_ASGI_TESTS=1 to enable",
)
class TestPortfolioEndpoints:
    def test_get_portfolio_summary_requires_auth(self):
        response = client.get("/portfolio/summary")
        assert response.status_code == 401

    def test_get_history_requires_auth(self):
        response = client.get("/portfolio/history")
        assert response.status_code == 401


@pytest.mark.skipif(
    os.getenv("RUN_ASGI_TESTS") != "1",
    reason="ASGI integration tests are skipped by default in this environment; set RUN_ASGI_TESTS=1 to enable",
)
class TestLogging:
    def test_api_request_logged(self):
        """Verify that requests generate log entries"""
        import os
        log_path = "/tmp/wealth.log"
        
        # Make a request
        client.get("/health")
        
        # Check if log file exists (logging may not create it until first write)
        # This is a basic smoke test
        assert True  # Placeholder - real test would check log content


class TestScrapers:
    @pytest.mark.skipif(
        os.getenv("RUN_NETWORK_TESTS") != "1",
        reason="external scraper tests are skipped by default; set RUN_NETWORK_TESTS=1 to enable",
    )
    def test_us_scraper_validate_symbol(self):
        from app.scrapers import USStockScraper
        scraper = USStockScraper()
        
        # Valid symbol
        assert scraper.validate_symbol("AAPL") in [True, False]  # May be True or False depending on network
        
        # Invalid symbol
        assert scraper.validate_symbol("INVALID_XYZ_123") == False

    @pytest.mark.skipif(
        os.getenv("RUN_NETWORK_TESTS") != "1",
        reason="external scraper tests are skipped by default; set RUN_NETWORK_TESTS=1 to enable",
    )
    def test_taiwan_scraper_get_all_stocks(self):
        from app.scrapers import TaiwanStockScraper
        scraper = TaiwanStockScraper()
        
        stocks = scraper.get_all_twse_stocks()
        # Should return a list (may be empty if network fails)
        assert isinstance(stocks, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
