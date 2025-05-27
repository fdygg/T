from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, UTC
from starlette.datastructures import Headers
import logging
import time
import traceback
import uuid
from typing import Callable, Dict, Optional
import json

logger = logging.getLogger(__name__)

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "/": True,
    "/docs": True,
    "/redoc": True,
    "/favicon.ico": True,
    "/static": True,
    "/api/v1/health": True,
    "/api/v1/auth/token": True,
    "/api/v1/openapi.json": True
}

def is_public_endpoint(path: str) -> bool:
    """Check if endpoint is public"""
    # Exact match
    if path in PUBLIC_ENDPOINTS:
        return True
        
    # Check if path starts with any public endpoint
    return any(
        path.startswith(public_path)
        for public_path in PUBLIC_ENDPOINTS
        if public_path.endswith("/static")
    )

def sanitize_headers(headers: Headers) -> Dict:
    """Sanitize headers for logging"""
    sanitized = dict(headers)
    # Remove sensitive headers
    sensitive = ['authorization', 'cookie', 'x-api-key']
    for key in sensitive:
        if key in sanitized:
            sanitized[key] = "[REDACTED]"
    return sanitized

async def logging_middleware(request: Request, call_next):
    """Request/Response logging middleware"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Add request ID to request state
    request.state.request_id = request_id
    
    # Log request
    logger.debug(f"""
    [{request_id}] Incoming Request:
    Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
    Method: {request.method}
    URL: {str(request.url)}
    Path: {request.url.path}
    Headers: {sanitize_headers(request.headers)}
    Query Params: {dict(request.query_params)}
    Client: {request.client}
    Client Host: {request.client.host}
    Client Port: {request.client.port}
    User: fdygg
    """)
    
    try:
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = JSONResponse(
                content={"message": "OK"},
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "86400",  # 24 hours
                }
            )
        else:
            response = await call_next(request)
        
        process_time = time.time() - start_time
        status_code = response.status_code
        
        # Log based on status code
        log_func = logger.info if status_code < 400 else logger.error
        
        # Get response body for logging if error
        response_body = ""
        if status_code >= 400:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            try:
                response_body = json.loads(response_body)
            except:
                response_body = response_body.decode()
        
        log_func(f"""
        [{request_id}] Response:
        Status: {status_code}
        Process Time: {process_time:.4f} sec
        Headers: {dict(response.headers)}
        Body: {response_body if status_code >= 400 else ""}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        User: fdygg
        """)
        
        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-API-Version"] = "1.0.0"
        
        # Add security headers
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'"
        })
        
        return response
        
    except Exception as e:
        logger.error(f"""
        [{request_id}] Error processing request:
        Path: {request.url.path}
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Stack Trace:
        {traceback.format_exc()}
        User: fdygg
        """)
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "message": str(e),
                "type": "InternalServerError",
                "timestamp": datetime.now(UTC).isoformat(),
                "request_id": request_id,
                "path": request.url.path
            },
            headers={
                "X-Request-ID": request_id,
                "X-Error-Type": type(e).__name__
            }
        )

async def error_handler(request: Request, exc: Exception):
    """Global error handler"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.error(f"""
    [{request_id}] Error handling request:
    Path: {request.url.path}
    Error: {str(exc)}
    Type: {type(exc).__name__}
    Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
    Stack Trace:
    {traceback.format_exc()}
    User: fdygg
    """)
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": "Request failed",
                "message": str(exc.detail),
                "type": type(exc).__name__,
                "timestamp": datetime.now(UTC).isoformat(),
                "request_id": request_id,
                "path": request.url.path
            },
            headers={
                "X-Request-ID": request_id,
                "X-Error-Type": type(exc).__name__
            }
        )
        
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc),
            "type": type(exc).__name__,
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
            "path": request.url.path
        },
        headers={
            "X-Request-ID": request_id,
            "X-Error-Type": type(exc).__name__
        }
    )

def setup_middleware(app):
    """Setup API middleware and error handlers"""
    logger.debug("Setting up API middleware and error handlers...")
    
    try:
        # Add logging middleware
        app.middleware("http")(logging_middleware)
        
        # Add error handler
        app.exception_handler(Exception)(error_handler)
        
        logger.info(f"""
        Middleware setup completed:
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Public Endpoints: {list(PUBLIC_ENDPOINTS.keys())}
        User: fdygg
        """)
        
    except Exception as e:
        logger.error(f"""
        Middleware setup error:
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Stack Trace:
        {traceback.format_exc()}
        User: fdygg
        """)
        raise

# Export public endpoints
__all__ = ["PUBLIC_ENDPOINTS", "is_public_endpoint"]