# api/middleware/auth.py
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from ..config import API_SECRET_KEY
from typing import Optional
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer()

async def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, API_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def auth_middleware(request: Request, call_next):
    """Middleware untuk autentikasi"""
    # Paths yang tidak memerlukan autentikasi
    PUBLIC_PATHS = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/admin/login",
        "/favicon.ico"
    ]
    
    # Skip autentikasi untuk public paths
    if any(request.url.path.startswith(path) for path in PUBLIC_PATHS):
        return await call_next(request)
    
    try:
        # Get token dari header atau query parameter
        token = None
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            # Cek query parameter
            token = request.query_params.get("token")
        
        if not token:
            raise HTTPException(
                status_code=401,
                detail="No authentication token provided"
            )
        
        # Verify token
        payload = await verify_token(token)
        
        # Tambahkan user info ke request state
        request.state.user = payload
        
        # Lanjutkan ke request berikutnya
        return await call_next(request)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )