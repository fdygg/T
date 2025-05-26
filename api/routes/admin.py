# api/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta
import jwt
from ..config import API_SECRET_KEY, APIConfig
from database import get_connection

router = APIRouter()
security = HTTPBearer()

def get_admin(discord_id: str):
    """Get admin data from database"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Periksa apakah user adalah admin dari role_permissions
        cursor.execute("""
            SELECT rp.role_id, rp.permissions, ug.discord_id
            FROM role_permissions rp
            JOIN user_growid ug ON ug.discord_id = ?
            WHERE rp.role_id = 'admin'
        """, (discord_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                "discord_id": result[2],
                "role": result[0],
                "permissions": result[1],
                "is_active": True
            }
        return None
            
    except Exception as e:
        logger.error(f"Error getting admin: {e}")
        return None
            
    finally:
        if 'conn' in locals():
            conn.close()

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=APIConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, API_SECRET_KEY, algorithm="HS256")
    return encoded_jwt

@router.get("/auth")
async def verify_admin(token: str = None):
    """Verify admin token"""
    logger.debug(f"Received auth request with token: {token}")
    try:
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Token is required"
            )
            
        payload = jwt.decode(token, API_SECRET_KEY, algorithms=["HS256"])
        admin = get_admin(payload["user_id"])
        if not admin:
            raise HTTPException(
                status_code=401,
                detail="Admin not found"
            )
        return {
            "valid": True,
            "admin": admin
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Error in verify_admin: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.post("/login")
async def login_admin(discord_id: str):
    """Login admin dan dapatkan token"""
    try:
        admin = get_admin(discord_id)
        if not admin:
            raise HTTPException(
                status_code=401,
                detail="Admin not found"
            )
        
        # Create access token
        token_data = {
            "user_id": admin["discord_id"],
            "role": admin["role"]
        }
        token = create_access_token(token_data)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "admin": admin
        }
    except Exception as e:
        logger.error(f"Error in login_admin: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
