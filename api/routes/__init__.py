from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, UTC, timedelta
from typing import Optional, Dict, Any
import logging
import sys
import platform
import psutil
from pathlib import Path
from ..middleware import skip_auth
from ..config import config, API_VERSION

# Initialize router and logger
router = APIRouter()
logger = logging.getLogger(__name__)

# Setup templates
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Import routes
from .auth import router as auth_router  # Tambahkan ini
from .balance import router as balance_router
from .stock import router as stock_router
from .transactions import router as transactions_router
from .admin import router as admin_router

# Include sub-routers with prefix and tags
router.include_router(
    auth_router,  # Tambahkan ini
    prefix="/auth",
    tags=["Auth"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Bad Request"}
    }
)
router.include_router(
    balance_router, 
    prefix="/balance", 
    tags=["Balance"],
    responses={404: {"description": "Balance not found"}}
)
router.include_router(
    stock_router, 
    prefix="/stock", 
    tags=["Stock"],
    responses={404: {"description": "Stock not found"}}
)
router.include_router(
    transactions_router, 
    prefix="/transactions", 
    tags=["Transactions"],
    responses={404: {"description": "Transaction not found"}}
)
router.include_router(
    admin_router, 
    prefix="/admin", 
    tags=["Admin"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"}
    }
)

def get_system_info() -> Dict[str, Any]:
    """Get system information with fallbacks"""
    try:
        memory = psutil.virtual_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "percent": round(memory.percent, 2)
        }
    except:
        memory_info = {"error": "Memory stats unavailable"}
        
    try:
        disk = psutil.disk_usage('/')
        disk_info = {
            "total": disk.total,
            "free": disk.free,
            "percent": round(disk.percent, 2)
        }
    except:
        disk_info = {"error": "Disk stats unavailable"}
        
    try:
        cpu_percent = round(psutil.cpu_percent(interval=0.1), 2)
    except:
        cpu_percent = 0.0
        
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "timezone": "UTC",
        "memory": memory_info,
        "disk": disk_info,
        "cpu_percent": cpu_percent
    }

@router.get("/dashboard", response_class=HTMLResponse)
@skip_auth
async def dashboard(request: Request):
    """Render dashboard page"""
    try:
        current_time = datetime.now(UTC)
        system_info = get_system_info()
        
        # Log dashboard access
        logger.info(f"""
        Dashboard access:
        Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
        IP: {request.client.host}
        User: {config._config["default_user"]}
        """)
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "title": "Dashboard - Bot Control Panel",
                "username": config._config["default_user"],
                "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "version": API_VERSION,
                "system": system_info,
                "endpoints": {
                    "base": "/api/v1",
                    "balance": "/api/v1/balance",
                    "stock": "/api/v1/stock",
                    "transactions": "/api/v1/transactions",
                    "admin": "/api/v1/admin"
                }
            }
        )
    except Exception as e:
        logger.error(f"""
        Dashboard error:
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Error: {str(e)}
        User: {config._config["default_user"]}
        """)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint
    Returns basic information about the API server status
    """
    try:
        current_time = datetime.now(UTC)
        system_info = get_system_info()
        
        # Log health check
        logger.info(f"""
        Health check:
        Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
        IP: {request.client.host}
        User: {config._config["default_user"]}
        """)
        
        response = {
            "status": "ok",
            "timestamp": current_time.strftime('%Y-%m-%d %H:%M:%S'),
            "user": config._config["default_user"],
            "version": API_VERSION,
            "system": system_info,
            "endpoints": {
                "base": "/api/v1",
                "balance": "/api/v1/balance",
                "stock": "/api/v1/stock",
                "transactions": "/api/v1/transactions",
                "admin": "/api/v1/admin"
            },
            "client": {
                "host": request.client.host,
                "port": request.client.port,
                "headers": dict(request.headers)
            }
        }
        
        return JSONResponse(
            content=response,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block"
            }
        )
        
    except Exception as e:
        logger.error(f"""
        Health check error:
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Error: {str(e)}
        Client: {request.client.host}:{request.client.port}
        User: {config._config["default_user"]}
        """)
        raise HTTPException(
            status_code=500,
            detail={
                "message": str(e),
                "type": "InternalServerError",
                "timestamp": datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
            }
        )

# Export router
__all__ = ['router']

# Log when module is loaded
logger.info(f"""
Routes module loaded:
Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
Total Routes: {len(router.routes)}
User: {config._config['default_user']}
Version: {API_VERSION}
""")