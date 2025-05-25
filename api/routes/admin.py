# api/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta
import jwt
from ..config import API_SECRET_KEY, APIConfig
from ..utils.db import admin_db

router = APIRouter()
security = HTTPBearer()

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

@router.post("/admin/login")
async def login_admin(discord_id: str):
    """Login admin dan dapatkan token"""
    admin = admin_db.get_admin(discord_id)
    if not admin:
        raise HTTPException(
            status_code=401,
            detail="Admin not found"
        )
    
    if not admin["is_active"]:
        raise HTTPException(
            status_code=401,
            detail="Admin is not active"
        )
    
    # Create access token
    token_data = {
        "user_id": admin["discord_id"],
        "username": admin["username"]
    }
    token = create_access_token(token_data)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "admin": admin
    }

@router.get("/admin/auth")
async def verify_admin(token: str):
    """Verify admin token"""
    try:
        payload = jwt.decode(token, API_SECRET_KEY, algorithms=["HS256"])
        admin = admin_db.get_admin(payload["user_id"])
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

@router.get("/admin/me")
async def get_current_admin(token: str):
    """Get current admin info"""
    try:
        payload = jwt.decode(token, API_SECRET_KEY, algorithms=["HS256"])
        admin = admin_db.get_admin(payload["user_id"])
        if not admin:
            raise HTTPException(
                status_code=401,
                detail="Admin not found"
            )
        return admin
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )