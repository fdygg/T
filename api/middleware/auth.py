from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import jwt
from datetime import datetime, UTC
import logging
from ..config import config
from . import PUBLIC_ENDPOINTS, is_public_endpoint

logger = logging.getLogger(__name__)
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials) -> dict:
    """Verify JWT token"""
    try:
        token = credentials.credentials
        
        # Try to decode with each user's secret
        decoded = None
        for username, key_data in config._keys.items():
            try:
                decoded = jwt.decode(
                    token,
                    key_data["api_secret"],
                    algorithms=["HS256"]
                )
                if decoded["sub"] == username:
                    break
            except jwt.InvalidTokenError:
                continue
                
        if not decoded:
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "Invalid token",
                    "type": "AuthenticationError",
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )
            
        # Verify API key
        if not config.verify_api_key(decoded["api_key"], decoded["sub"]):
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "Invalid API key",
                    "type": "AuthenticationError",
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )
            
        return decoded
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Token has expired",
                "type": "TokenExpiredError",
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Invalid token format",
                "type": "InvalidTokenError",
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
    except Exception as e:
        logger.error(f"""
        Token verification error:
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        """)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error verifying token",
                "type": "InternalServerError",
                "timestamp": datetime.now(UTC).isoformat()
            }
        )

async def auth_middleware(request: Request, call_next):
    """Authentication middleware"""
    try:
        # Skip auth for public endpoints
        path = request.url.path
        if is_public_endpoint(path):
            return await call_next(request)
            
        # Get token from header
        auth = request.headers.get("Authorization")
        if not auth:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication required",
                    "message": "Authorization header missing",
                    "type": "AuthenticationError",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "path": path
                }
            )
            
        scheme, token = auth.split()
        if scheme.lower() != "bearer":
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication failed",
                    "message": "Invalid authentication scheme",
                    "type": "AuthenticationError",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "path": path
                }
            )
            
        # Verify token
        decoded = await verify_token(HTTPAuthorizationCredentials(
            credentials=token,
            scheme=scheme
        ))
        
        # Add user info to request state
        request.state.user = decoded["sub"]
        request.state.api_key = decoded["api_key"]
        request.state.token_data = decoded
        
        # Add custom headers
        response = await call_next(request)
        response.headers["X-Rate-Limit"] = "60"
        response.headers["X-Rate-Remaining"] = "59"
        response.headers["X-Request-ID"] = token[:8]
        response.headers["X-User"] = decoded["sub"]
        return response
        
    except HTTPException as he:
        return JSONResponse(
            status_code=he.status_code,
            content={
                "detail": "Authentication failed",
                "message": he.detail["message"],
                "type": he.detail["type"],
                "timestamp": datetime.now(UTC).isoformat(),
                "path": request.url.path
            }
        )
    except Exception as e:
        logger.error(f"""
        Auth middleware error:
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Path: {request.url.path}
        Method: {request.method}
        Headers: {dict(request.headers)}
        """)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Authentication error",
                "message": str(e),
                "type": "InternalServerError",
                "timestamp": datetime.now(UTC).isoformat(),
                "path": request.url.path
            }
        )

# Export middleware
__all__ = ["auth_middleware"]