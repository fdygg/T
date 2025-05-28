from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import JSONResponse
from datetime import datetime, UTC
import logging
from ..config import config
from ..middleware import get_current_time, get_current_user, format_log_message

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/login")
async def login(request: Request):
    """Handle login form submission"""
    username = None
    
    try:
        form = await request.form()
        username = form.get("username")
        api_key = form.get("api_key")
        
        # Log login attempt
        logger.info(format_log_message(f"""
        Login attempt:
        IP: {request.client.host}
        User-Agent: {request.headers.get("user-agent")}
        Username: {username}"""))
        
        if not username or not api_key:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Username and API key are required",
                    "type": "ValidationError",
                    "timestamp": get_current_time(),
                    "path": request.url.path
                }
            )
        
        # Verify API key
        if not config.verify_api_key(api_key, username):
            logger.warning(format_log_message(f"""
            Invalid login attempt:
            Username: {username}
            IP: {request.client.host}"""))
            
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "Invalid credentials",
                    "type": "AuthenticationError",
                    "timestamp": get_current_time(),
                    "path": request.url.path
                }
            )
        
        # Create token
        token = config.create_access_token(username=username, api_key=api_key)
        
        # Log successful login
        logger.info(format_log_message(f"""
        Login successful:
        Username: {username}
        IP: {request.client.host}"""))
        
        return JSONResponse(
            content={
                "access_token": token,
                "token_type": "bearer",
                "username": username,
                "timestamp": get_current_time()
            },
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block"
            }
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(format_log_message(f"""
        Login error:
        Username: {username}
        Error: {str(e)}
        Path: {request.url.path}"""))
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Login failed",
                "type": "InternalServerError",
                "timestamp": get_current_time(),
                "path": request.url.path
            }
        )

@router.post("/admin/login")
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Handle admin login"""
    try:
        # Log admin login attempt
        logger.info(format_log_message(f"""
        Admin login attempt:
        IP: {request.client.host}
        Username: {username}"""))

        # Verify admin credentials
        if not config.verify_admin(username, password):
            logger.warning(format_log_message(f"""
            Invalid admin login attempt:
            Username: {username}
            IP: {request.client.host}"""))
            
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "Invalid credentials",
                    "type": "AuthenticationError",
                    "timestamp": get_current_time()
                }
            )
            
        # Create admin token
        token = config.create_admin_token(username)
        
        # Log successful login
        logger.info(format_log_message(f"""
        Admin login successful:
        Username: {username}
        IP: {request.client.host}"""))
        
        return JSONResponse(
            content={
                "access_token": token,
                "token_type": "bearer",
                "role": "admin",
                "username": username,
                "timestamp": get_current_time()
            },
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block"
            }
        )

    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(format_log_message(f"""
        Admin login error:
        Username: {username}
        Error: {str(e)}
        Path: {request.url.path}"""))
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Login failed",
                "type": "InternalServerError",
                "timestamp": get_current_time(),
                "path": request.url.path
            }
        )

@router.post("/logout")
async def logout(request: Request):
    """Handle logout"""
    try:
        # Log logout
        logger.info(format_log_message(f"""
        Logout:
        IP: {request.client.host}"""))
        
        return JSONResponse(
            content={
                "message": "Logged out successfully",
                "timestamp": get_current_time()
            },
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block"
            }
        )
        
    except Exception as e:
        logger.error(format_log_message(f"""
        Logout error:
        Error: {str(e)}
        Path: {request.url.path}"""))
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Logout failed",
                "type": "InternalServerError",
                "timestamp": get_current_time(),
                "path": request.url.path
            }
        )