from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, Response
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
    # Base paths
    "/": True,
    "/docs": True,
    "/redoc": True,
    "/favicon.ico": True,
    "/static": True,
    "/login": True,
    
    # API paths (dengan format lengkap)
    "/api/v1/health": True,
    "/api/v1/auth/token": True,
    "/api/v1/openapi.json": True,
    "/api/v1/dashboard": True,
    "/api/v1/login": True,
    
    # Admin paths (dengan format lengkap)
    "/api/v1/admin/login": True,
    "/api/v1/admin/register": True,
    "/api/v1/admin/reset-password": True,
    
    # API paths (tanpa prefix)
    "/dashboard": True,
    "/health": True,
    "/auth/token": True,
    "/openapi.json": True,
    "/login": True,
    
    # Admin paths (tanpa prefix) 
    "/admin/login": True,
    "/admin/register": True,
    "/admin/reset-password": True
}

def get_current_time() -> str:
    """Get current time in UTC YYYY-MM-DD HH:MM:SS format"""
    return datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')

def get_current_user() -> str:
    """Get current user's login"""
    return "fdygg"

def format_log_message(message: str, request_id: str = "") -> str:
    """Format log message with consistent time and user info"""
    current_time = get_current_time()
    user = get_current_user()
    prefix = f"[{request_id}] " if request_id else ""
    cleaned_message = "\n".join(line.strip() for line in message.strip().split("\n"))
    
    return f"""
Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): {current_time}
Current User's Login: {user}
{prefix}{cleaned_message}"""

def skip_auth(func: Callable) -> Callable:
    """Decorator to skip authentication for specific endpoints"""
    setattr(func, "skip_auth", True)
    return func

def is_public_endpoint(path: str) -> bool:
    """Check if endpoint is public"""
    logger.debug(format_log_message(f"""
    Checking public endpoint:
    Path: {path}
    Raw match: {path in PUBLIC_ENDPOINTS}
    Is Admin Path: {path.startswith("/admin/") or path.startswith("/api/v1/admin/")}"""))
    
    # Exact match
    if path in PUBLIC_ENDPOINTS:
        return True
        
    # Check without /api/v1 prefix
    if path.startswith("/api/v1/"):
        base_path = path[7:]  # Remove /api/v1/
        if base_path in PUBLIC_ENDPOINTS or f"/api/v1{base_path}" in PUBLIC_ENDPOINTS:
            return True
    
    # Check special paths
    if path.startswith("/static") or path == "/favicon.ico" or path == "/login":
        return True
        
    # Check admin paths
    if path.startswith("/admin/") or path.startswith("/api/v1/admin/"):
        admin_path = path.replace("/api/v1", "")  # Remove API prefix if exists
        return admin_path in PUBLIC_ENDPOINTS
        
    return False

def sanitize_headers(headers: Headers) -> Dict:
    """Sanitize headers for logging"""
    sanitized = dict(headers)
    # Remove sensitive headers
    sensitive = ['authorization', 'cookie', 'x-api-key']
    for key in sensitive:
        if key in sanitized:
            sanitized[key] = "[REDACTED]"
    return sanitized

def create_error_response(status_code: int, message: str, request_id: str, 
                         error_type: str, path: str) -> JSONResponse:
    """Create standardized error response"""
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": "Request failed",
            "message": message,
            "type": error_type,
            "timestamp": get_current_time(),
            "request_id": request_id,
            "path": path
        },
        headers={
            "X-Request-ID": request_id,
            "X-Error-Type": error_type,
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
        }
    )

async def auth_middleware(request: Request, call_next):
    """Authentication middleware"""
    path = request.url.path
    
    logger.debug(format_log_message(f"""
    Auth Check:
    Path: {path}
    Is Public: {is_public_endpoint(path)}
    In PUBLIC_ENDPOINTS: {path in PUBLIC_ENDPOINTS}
    Has skip_auth: {getattr(request.scope.get("endpoint", None), "skip_auth", False)}
    Is Admin Path: {path.startswith("/admin/") or path.startswith("/api/v1/admin/")}"""))
    
    # Skip auth for public endpoints
    if is_public_endpoint(path):
        logger.debug(format_log_message(f"""
        Skipping auth for public endpoint:
        Path: {path}"""))
        return await call_next(request)
        
    # Skip auth if endpoint has skip_auth decorator
    endpoint = request.scope.get("endpoint", None)
    if endpoint and getattr(endpoint, "skip_auth", False):
        logger.debug(format_log_message(f"""
        Skipping auth for endpoint with skip_auth:
        Path: {path}"""))
        return await call_next(request)
        
    # Check auth header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        logger.debug(format_log_message(f"""
        Missing auth header for protected endpoint:
        Path: {path}"""))
        return create_error_response(
            status_code=401,
            message="Authorization header missing",
            request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
            error_type="AuthenticationError",
            path=path
        )
    
    # Continue with request
    return await call_next(request)

async def logging_middleware(request: Request, call_next):
    """Request/Response logging middleware"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Add request ID to request state
    request.state.request_id = request_id
    
    # Log request
    logger.debug(format_log_message(f"""
    Incoming Request:
    Method: {request.method}
    URL: {str(request.url)}
    Path: {request.url.path}
    Headers: {sanitize_headers(request.headers)}
    Query Params: {dict(request.query_params)}
    Client: {request.client}
    Client Host: {request.client.host}
    Client Port: {request.client.port}""", request_id))
    
    try:
        # Handle preflight requests
        if request.method == "OPTIONS":
            return JSONResponse(
                content={"message": "OK"},
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "86400",  # 24 hours
                    "X-Request-ID": request_id
                }
            )

        response = await call_next(request)
        
        process_time = time.time() - start_time
        status_code = response.status_code
        
        # Add custom headers
        headers = dict(response.headers)
        headers.update({
            "X-Request-ID": request_id,
            "X-Process-Time": f"{process_time:.4f}",
            "X-API-Version": "1.0.0",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'"
        })
        
        # Create new response with updated headers
        content = b""
        async for chunk in response.body_iterator:
            content += chunk
            
        # Log based on status code
        log_func = logger.info if status_code < 400 else logger.error
        
        # Handle response body logging
        content_type = response.headers.get("content-type", "")
        if content and "application/json" in content_type.lower():
            try:
                body = json.loads(content)
            except:
                body = "<invalid json>"
        elif content and "text/" in content_type.lower():
            try:
                body = content.decode('utf-8')
            except:
                body = "<binary content>"
        else:
            body = f"<binary content: {len(content)} bytes>"
            
        log_func(format_log_message(f"""
        Response:
        Status: {status_code}
        Process Time: {process_time:.4f} sec
        Headers: {headers}
        Content-Type: {content_type}
        Body: {body if status_code >= 400 or 'json' in content_type.lower() else ''}""", request_id))
        
        return Response(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=response.media_type
        )
        
    except Exception as e:
        logger.error(format_log_message(f"""
        Error processing request:
        Path: {request.url.path}
        Error: {str(e)}
        Stack Trace:
        {traceback.format_exc()}""", request_id))
        
        return create_error_response(
            status_code=500,
            message=str(e),
            request_id=request_id,
            error_type="InternalServerError",
            path=request.url.path
        )

async def error_handler(request: Request, exc: Exception):
    """Global error handler"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.error(format_log_message(f"""
    Error handling request:
    Path: {request.url.path}
    Error: {str(exc)}
    Type: {type(exc).__name__}
    Stack Trace:
    {traceback.format_exc()}""", request_id))
    
    if isinstance(exc, HTTPException):
        return create_error_response(
            status_code=exc.status_code,
            message=str(exc.detail),
            request_id=request_id,
            error_type=type(exc).__name__,
            path=request.url.path
        )
    
    return create_error_response(
        status_code=500,
        message=str(exc),
        request_id=request_id,
        error_type="InternalServerError",
        path=request.url.path
    )

def setup_middleware(app):
    """Setup API middleware and error handlers"""
    logger.debug(format_log_message("""
    Setting up API middleware and error handlers..."""))
    
    try:
        # Add auth middleware first
        app.middleware("http")(auth_middleware)
        
        # Add logging middleware
        app.middleware("http")(logging_middleware)
        
        # Add error handler
        app.exception_handler(Exception)(error_handler)
        
        logger.info(format_log_message(f"""
        Middleware setup completed:
        Public Endpoints: {list(PUBLIC_ENDPOINTS.keys())}"""))
        
    except Exception as e:
        logger.error(format_log_message(f"""
        Middleware setup error:
        Error: {str(e)}
        Stack Trace:
        {traceback.format_exc()}"""))
        raise

# Export functionality
__all__ = [
    "PUBLIC_ENDPOINTS",
    "is_public_endpoint", 
    "skip_auth",
    "setup_middleware",
    "get_current_time",
    "get_current_user"
]