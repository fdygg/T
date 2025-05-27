from fastapi import APIRouter, HTTPException
from fastapi.security import HTTPBearer
from datetime import datetime, UTC
import jwt
import logging
import traceback
from ..dependencies import get_bot
from database import get_connection

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

@router.get("/auth")
async def verify_admin(token: str = None):
    """Verify admin token"""
    try:
        logger.debug(f"""
        Auth request received:
        Token: {token[:20]}... (truncated)
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        """)

        if not token:
            logger.warning("No token provided")
            raise HTTPException(
                status_code=401,
                detail="Token is required"
            )
            
        try:
            bot = get_bot()
            payload = jwt.decode(token, bot.config['token'], algorithms=["HS256"])
            logger.debug(f"Token decoded successfully: {payload}")
        except jwt.ExpiredSignatureError as e:
            logger.warning(f"Token expired: {e}")
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
            
        admin = await get_admin_data(payload.get('user_id'))
        if not admin:
            logger.warning(f"Admin not found: {payload.get('user_id')}")
            raise HTTPException(
                status_code=401,
                detail="Admin not found"
            )
            
        response = {
            "valid": True,
            "admin": admin
        }
        
        logger.info(f"Auth successful for admin: {admin['discord_id']}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"""
        Auth error:
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Stack Trace:
        {traceback.format_exc()}
        """)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

async def get_admin_data(discord_id: str):
    """Get admin data from database"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT rp.role_id, rp.permissions, ug.discord_id
            FROM role_permissions rp
            JOIN user_growid ug ON ug.discord_id = ?
            WHERE rp.role_id = 'admin'
        """
        
        cursor.execute(query, (discord_id,))
        result = cursor.fetchone()
        
        if result:
            return {
                "discord_id": result[2],
                "role": result[0],
                "permissions": result[1]
            }
            
        return None
        
    except Exception as e:
        logger.error(f"""
        Database error:
        Error: {str(e)}
        Discord ID: {discord_id}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Stack Trace:
        {traceback.format_exc()}
        """)
        raise
    finally:
        if conn:
            conn.close()