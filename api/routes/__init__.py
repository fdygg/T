from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, UTC, timedelta
from typing import Optional, Dict, Any
import logging
import sys
import platform
import psutil
from ..config import config, API_VERSION

# Inisialisasi router utama dan logger
router = APIRouter()
logger = logging.getLogger(__name__)

# Import routes
from .balance import router as balance_router
from .stock import router as stock_router
from .transactions import router as transactions_router
from .admin import router as admin_router

# Include sub-routers dengan prefix dan tags
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
            "percent": memory.percent
        }
    except:
        memory_info = {"error": "Memory stats unavailable"}
        
    try:
        disk = psutil.disk_usage('/')
        disk_info = {
            "total": disk.total,
            "free": disk.free,
            "percent": disk.percent
        }
    except:
        disk_info = {"error": "Disk stats unavailable"}
        
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
    except:
        cpu_percent = None
        
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "timezone": "UTC",
        "memory": memory_info,
        "disk": disk_info,
        "cpu_percent": cpu_percent
    }

@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint
    Returns basic information about the API server status
    """
    try:
        current_time = datetime.now(UTC)
        system_info = get_system_info()
        
        response = {
            "status": "ok",
            "timestamp": current_time.isoformat(),
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
                "Expires": "0"
            }
        )
        
    except Exception as e:
        logger.error(f"""
        Health check error:
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Error: {str(e)}
        Client: {request.client.host}:{request.client.port}
        """)
        raise HTTPException(
            status_code=500,
            detail={
                "message": str(e),
                "type": "InternalServerError",
                "timestamp": datetime.now(UTC).isoformat()
            }
        )

@router.get("/routes")
async def list_routes():
    """List all available API routes"""
    routes = []
    for route in router.routes:
        routes.append({
            "path": f"/api/v1{route.path}",
            "name": route.name,
            "methods": list(route.methods) if route.methods else None,
            "tags": route.tags if hasattr(route, 'tags') else None,
            "description": route.description if hasattr(route, 'description') else None
        })
    
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_routes": len(routes),
        "routes": sorted(routes, key=lambda x: x['path'])
    }

@router.get("/stats")
async def get_stats():
    """Get API server statistics"""
    try:
        current_time = datetime.now(UTC)
        system_info = get_system_info()
        process = psutil.Process()
        
        return {
            "timestamp": current_time.isoformat(),
            "system": {
                "cpu_percent": system_info["cpu_percent"],
                "memory": system_info["memory"],
                "disk": system_info["disk"]
            },
            "process": {
                "memory": dict(process.memory_info()._asdict()),
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            }
        }
    except Exception as e:
        logger.error(f"""
        Error getting stats:
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Error: {str(e)}
        """)
        raise HTTPException(
            status_code=500,
            detail={
                "message": str(e),
                "type": "InternalServerError",
                "timestamp": datetime.now(UTC).isoformat()
            }
        )

@router.post("/auth/token")
async def get_access_token(
    username: str,
    api_key: str,
    expires_in: Optional[int] = None
):
    """Get JWT access token"""
    try:
        if not config.verify_api_key(api_key, username):
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "Invalid API key",
                    "type": "AuthenticationError",
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )
        
        # Use default expire time from config if not provided    
        if expires_in is None:
            expires_in = config.token_expire_minutes
            
        # Validate expire time
        if expires_in > config.max_token_expire_minutes:
            expires_in = config.max_token_expire_minutes
        elif expires_in < config.min_token_expire_minutes:
            expires_in = config.min_token_expire_minutes
            
        token = config.create_access_token(
            username=username,
            api_key=api_key,
            expires_delta=timedelta(minutes=expires_in)
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in * 60,
            "username": username,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"""
        Error creating token:
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Username: {username}
        Error: {str(e)}
        """)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error creating token",
                "type": "InternalServerError",
                "timestamp": datetime.now(UTC).isoformat()
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