from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
from datetime import datetime, UTC
import traceback

logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc):
    """Handle HTTP exceptions"""
    logger.warning(f"""
    HTTP Exception:
    Path: {request.url.path}
    Status: {exc.status_code}
    Detail: {exc.detail}
    Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
    """)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "timestamp": datetime.now(UTC).isoformat(),
            "path": request.url.path
        }
    )

async def validation_exception_handler(request: Request, exc):
    """Handle validation exceptions"""
    logger.error(f"""
    Validation Exception:
    Path: {request.url.path}
    Errors: {exc.errors()}
    Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
    """)
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "timestamp": datetime.now(UTC).isoformat(),
            "path": request.url.path
        }
    )

async def generic_exception_handler(request: Request, exc):
    """Handle all other exceptions"""
    logger.error(f"""
    Unhandled Exception:
    Path: {request.url.path}
    Error: {str(exc)}
    Type: {type(exc).__name__}
    Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
    Stack Trace:
    {traceback.format_exc()}
    """)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc),
            "type": type(exc).__name__,
            "timestamp": datetime.now(UTC).isoformat(),
            "path": request.url.path
        }
    )