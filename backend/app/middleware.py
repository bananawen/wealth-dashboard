"""
FastAPI middleware for request/response logging
"""
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .logging_config import logger
import json


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip logging for health checks to reduce noise
        if request.url.path == "/health":
            return await call_next(request)
        
        start_time = time.time()
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        
        # Log incoming request
        logger.info(f"→ {method} {url} from {client_ip}")
        
        # Process request
        try:
            response: Response = await call_next(request)
            duration = time.time() - start_time
            status_code = response.status_code
            
            # Log response
            logger.info(
                f"← {method} {url} | {status_code} | {duration:.3f}s"
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"✗ {method} {url} | ERROR: {type(e).__name__}: {str(e)} | {duration:.3f}s"
            )
            raise


def log_api_call(func_name: str, **kwargs):
    """Helper to log API function calls with parameters"""
    params = ", ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
    logger.debug(f"API call: {func_name}({params})")


def log_database_operation(operation: str, table: str, **kwargs):
    """Helper to log database operations"""
    record_info = ", ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
    logger.debug(f"DB {operation}: {table} | {record_info}")


def log_scraper_event(symbol: str, event: str, **kwargs):
    """Helper to log scraper events"""
    details = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"Scraper | {symbol} | {event} | {details}")