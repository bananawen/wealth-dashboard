from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, holdings, transactions, portfolio, accounts, admin
from .middleware import LoggingMiddleware
from .logging_config import logger

# Initialize logging on startup
logger.info("Wealth API starting up...")

app = FastAPI(title="Wealth API", version="1.0.0")

# Add logging middleware
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 部署時改為具體網域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(holdings.router)
app.include_router(transactions.router)
app.include_router(portfolio.router)
app.include_router(admin.router)

logger.info("All routers registered successfully")


@app.get("/health")
def health():
    return {"status": "ok"}