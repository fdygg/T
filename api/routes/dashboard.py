from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, UTC
import logging
from ..dependencies import get_bot_instance
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render dashboard page"""
    try:
        bot = get_bot_instance()
        uptime = datetime.now(UTC) - bot.startup_time
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "title": "Dashboard - Bot Control Panel",
                "username": "fdygg",
                "current_time": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                "bot_uptime": str(uptime).split('.')[0],
                "version": "1.0.0"
            }
        )
    except Exception as e:
        logger.error(f"""
        Dashboard error:
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        """)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/stats")
async def get_stats(request: Request):
    """Get real-time system stats"""
    try:
        bot = get_bot_instance()
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "bot": {
                "name": bot.user.name,
                "id": str(bot.user.id),
                "uptime": str(datetime.now(UTC) - bot.startup_time),
                "guilds": len(bot.guilds)
            },
            "stats": bot.get_system_info()
        }
    except Exception as e:
        logger.error(f"""
        Stats error:
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        """)
        raise HTTPException(status_code=500, detail=str(e))