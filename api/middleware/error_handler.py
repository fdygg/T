import sys
import os

# Tambahkan root path ke sys.path
root_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if root_path not in sys.path:
    sys.path.append(root_path)

# Sekarang import exceptions dari bot
from ..utils.exceptions import APIError

async def add_error_handlers(app):
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message}
        )