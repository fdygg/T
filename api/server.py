from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
import psutil
import platform
from datetime import datetime, UTC
import traceback
from threading import Thread
import os
from pathlib import Path
from .dependencies import set_bot
from .routes import router as api_router
from .middleware import setup_middleware
from .middleware.auth import auth_middleware
from .config import API_VERSION

logger = logging.getLogger(__name__)

class APIServer:
    def __init__(self, bot):
        self.app = FastAPI(
            title="Discord Bot API",
            description="Backend API for Growtopia Shop Bot",
            version=API_VERSION,
            docs_url=None,  # Disable default docs
            redoc_url=None,  # Disable default redoc
            openapi_url=None  # Disable default openapi.json
        )
        self.bot = bot
        self.startup_time = datetime.now(UTC)
        
        # Setup static files
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(exist_ok=True)
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        self.setup_api()
        logger.debug(f"""
        API Server initialized:
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Bot: {self.bot.__class__.__name__}
        FastAPI App: {self.app.__class__.__name__}
        Version: {API_VERSION}
        Python: {platform.python_version()}
        OS: {platform.platform()}
        """)

    def get_system_info(self):
        """Get system information with fallbacks"""
        try:
            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": round(memory.percent, 2)
            }
        except:
            memory_info = {"error": "Memory stats unavailable"}
            
        try:
            disk = psutil.disk_usage('/')
            disk_info = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": round(disk.percent, 2)
            }
        except:
            disk_info = {"error": "Disk stats unavailable"}
            
        try:
            # Give small interval for more accurate reading
            cpu_percent = round(psutil.cpu_percent(interval=0.1), 2)
        except:
            cpu_percent = 0.0
            
        return {
            "memory": memory_info,
            "disk": disk_info,
            "cpu_percent": cpu_percent
        }

    def setup_api(self):
        """Setup API routes and middleware"""
        logger.debug("Setting up API routes and middleware")
        
        try:
            # Setup CORS
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["GET", "POST", "PUT", "DELETE"],
                allow_headers=["*"],
                expose_headers=["X-Request-ID"]
            )
            
            # Add auth middleware
            self.app.middleware("http")(auth_middleware)
            
            # Set bot instance
            set_bot(self.bot)
            
            # Include routers with prefix
            self.app.include_router(
                api_router,
                prefix="/api/v1"
            )
            
            # Setup middleware and error handlers
            setup_middleware(self.app)
            
            # Add favicon endpoint
            @self.app.get("/favicon.ico", include_in_schema=False)
            async def favicon():
                favicon_path = Path(__file__).parent / "static/favicon.ico"
                if favicon_path.exists():
                    return FileResponse(str(favicon_path))
                return JSONResponse(
                    status_code=404,
                    content={
                        "detail": "Not Found",
                        "message": "Favicon not found",
                        "timestamp": datetime.now(UTC).isoformat()
                    }
                )
            
            # Add OpenAPI endpoint
            @self.app.get("/api/v1/openapi.json", include_in_schema=False)
            async def get_openapi_schema():
                openapi_schema = get_openapi(
                    title="Growtopia Shop Bot API",
                    version=API_VERSION,
                    description=f"""
                    Backend API for Growtopia Shop Discord Bot.
                    
                    API Version: {API_VERSION}
                    Server Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
                    
                    Authentication:
                    - All endpoints except public endpoints require authentication
                    - Use Bearer token authentication
                    - Get token from /api/v1/auth/token endpoint
                    """,
                    routes=self.app.routes,
                )
                return JSONResponse(openapi_schema)
            
            # Di dalam class APIServer, method setup_api()
            
            # Add health check endpoint
            @self.app.get("/")
            async def root(request: Request):
                uptime = datetime.now(UTC) - self.startup_time
                system_info = self.get_system_info()
                
                response_data = {
                    "status": "ok",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "version": API_VERSION,
                    "bot": {
                        "name": self.bot.user.name if self.bot.user else None,
                        "id": str(self.bot.user.id) if self.bot.user else None,
                        "startup_time": self.bot.startup_time.isoformat() if hasattr(self.bot, 'startup_time') else None,
                        "uptime": str(uptime),
                        "guilds": len(self.bot.guilds) if hasattr(self.bot, 'guilds') else 0
                    },
                    "server": {
                        "hostname": platform.node(),
                        "platform": platform.platform(),
                        "python": platform.python_version(),
                        **system_info
                    },
                    "client": {
                        "ip": request.client.host,
                        "port": request.client.port,
                        "user_agent": request.headers.get("user-agent")
                    }
                }
            
                return JSONResponse(
                    content=response_data,
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    }
                )
            # Add docs endpoints
            @self.app.get("/docs", include_in_schema=False)
            async def custom_swagger_ui_html():
                return get_swagger_ui_html(
                    openapi_url="/api/v1/openapi.json",
                    title=f"Bot API Documentation - {API_VERSION}",
                    swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
                    swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
                    swagger_favicon_url="/favicon.ico"
                )
            
            # Add debug routes endpoint
            @self.app.get("/api/v1/debug/routes", include_in_schema=False)
            async def list_routes(request: Request):
                routes = []
                for route in self.app.routes:
                    routes.append({
                        "path": route.path,
                        "name": route.name,
                        "methods": list(route.methods) if route.methods else None,
                        "tags": route.tags if hasattr(route, 'tags') else None,
                        "deprecated": route.deprecated if hasattr(route, 'deprecated') else False,
                        "description": route.description if hasattr(route, 'description') else None
                    })
                return {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "total_routes": len(routes),
                    "routes": sorted(routes, key=lambda x: x['path']),
                    "request": {
                        "client": request.client.host,
                        "method": request.method,
                        "url": str(request.url)
                    }
                }
                
            logger.info(f"""
            API routes and middleware setup completed:
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Total Routes: {len(self.app.routes)}
            Auth Enabled: True
            CORS Enabled: True
            Version: {API_VERSION}
            """)
            
        except Exception as e:
            logger.error(f"""
            API setup error:
            Error: {str(e)}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Stack Trace:
            {traceback.format_exc()}
            """)
            raise

# ... kode sebelumnya tetap sama ...

    def run(self):
        """Run API server"""
        try:
            config = uvicorn.Config(
                self.app,
                host="0.0.0.0",
                port=8080,
                log_level="debug",
                access_log=True,
                reload=False,
                http="h11",
                loop="asyncio",
                timeout_keep_alive=5,
                timeout_notify=30,
                limit_concurrency=1000,
                limit_max_requests=10000,
                log_config={
                    "version": 1,
                    "disable_existing_loggers": False,
                    "formatters": {
                        "default": {
                            "format": "%(asctime)s UTC - %(name)s - %(levelname)s - [User: fdygg]\nMessage: %(message)s",
                            "datefmt": "%Y-%m-%d %H:%M:%S"
                        }
                    },
                    "handlers": {
                        "default": {
                            "formatter": "default",
                            "class": "logging.StreamHandler",
                            "stream": "ext://sys.stdout"
                        }
                    },
                    "loggers": {
                        "uvicorn": {"handlers": ["default"], "level": "INFO"},
                        "uvicorn.error": {"level": "INFO"},
                        "uvicorn.access": {
                            "handlers": ["default"],
                            "level": "INFO",
                            "propagate": False
                        }
                    }
                }
            )
            
            server = uvicorn.Server(config)
            
            logger.info(f"""
            Starting API server:
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Host: 0.0.0.0
            Port: 8080
            Debug: True
            Version: {API_VERSION}
            """)
            
            server.run()
            
        except Exception as e:
            logger.error(f"""
            Failed to start API server:
            Error: {str(e)}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Stack Trace:
            {traceback.format_exc()}
            """)
            raise

def create_api_server(bot) -> APIServer:
    """Create and start API server in a separate thread"""
    try:
        logger.debug(f"""
        Creating API server:
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Bot Type: {type(bot).__name__ if bot else 'None'}
        """)

        api = APIServer(bot)
        
        # Create and start server thread
        api_thread = Thread(
            target=api.run,
            daemon=True,
            name="APIServerThread"
        )
        api_thread.start()
        
        logger.info(f"""
        API server thread started:
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Thread ID: {api_thread.ident}
        Thread Name: {api_thread.name}
        Status: Running
        Version: {API_VERSION}
        """)
        
        return api
        
    except Exception as e:
        logger.error(f"""
        Error creating API server:
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Stack Trace:
        {traceback.format_exc()}
        """)
        raise

# Export api server creation function
__all__ = ["create_api_server"]