from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, holdings, transactions, portfolio, admin, prices
from .middleware import LoggingMiddleware
from .logging_config import logger
from .scrapers.price_scheduler import collector_service
from .config import get_settings

# Initialize logging on startup
logger.info("Wealth API starting up...")

settings = get_settings()

app = FastAPI(title="Wealth API", version="1.0.0")

# Add logging middleware
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(holdings.router)
app.include_router(transactions.router)
app.include_router(portfolio.router)
app.include_router(prices.router)
app.include_router(admin.router)

logger.info("All routers registered successfully")


@app.on_event("startup")
def startup_event():
    if settings.ENABLE_PRICE_SCHEDULER:
        collector_service.start()
    else:
        logger.info("Price collector scheduler disabled")


@app.on_event("shutdown")
def shutdown_event():
    collector_service.stop()


@app.get("/health")
def health():
    return {"status": "ok"}
