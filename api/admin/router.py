from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from .templates import templates
from ..dependencies import get_bot
from ..services.admin_service import AdminService
import jwt
from ..config import API_SECRET_KEY

router = APIRouter(prefix="/admin", tags=["Admin"])

async def verify_admin_token(request: Request):
    """Verify admin token from cookie"""
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=303, headers={"Location": "/admin/auth"})
    
    try:
        payload = jwt.decode(token, API_SECRET_KEY, algorithms=["HS256"])
        bot = get_bot_instance.get_bot()
        if str(bot.admin_id) != payload["user_id"]:
            raise HTTPException(status_code=403, detail="Invalid admin ID")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=303, headers={"Location": "/admin/auth"})
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token")

@router.get("/auth")
async def auth(request: Request, token: str):
    """Handle authentication with token from Discord bot"""
    try:
        # Verify token
        payload = jwt.decode(token, API_SECRET_KEY, algorithms=["HS256"])
        bot = get_bot_instance.get_bot()
        
        # Check if user is admin
        if str(bot.admin_id) != payload["user_id"]:
            raise HTTPException(status_code=403, detail="Unauthorized access")

        # Set cookie and redirect to dashboard
        response = RedirectResponse(url="/admin/dashboard")
        response.set_cookie(
            key="admin_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="strict"
        )
        return response

    except jwt.ExpiredSignatureError:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Link has expired. Please generate a new one using !db command."
            }
        )
    except jwt.InvalidTokenError:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Invalid authentication token."
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "An error occurred during authentication."
            }
        )

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    bot = Depends(get_bot),
    admin = Depends(verify_admin_token)
):
    admin_service = AdminService(bot)
    stats = await admin_service.get_dashboard_stats()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "current_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

# ... (route lainnya dengan Depends(verify_admin_token)) ...

@router.get("/logout")
async def logout():
    """Clear admin token cookie"""
    response = RedirectResponse(url="/admin/auth")
    response.delete_cookie("admin_token")
    return response