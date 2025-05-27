import logging
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    request_id = str(time.time())
    
    logger.debug(f"""
    [{request_id}] Incoming Request:
    Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
    Method: {request.method}
    URL: {request.url}
    Path: {request.url.path}
    Headers: {dict(request.headers)}
    Query Params: {dict(request.query_params)}
    Client: {request.client}
    Client Host: {request.client.host}
    Client Port: {request.client.port}
    """)
    
    try:
        response = await call_next(request)
        
        process_time = time.time() - start_time
        status_code = response.status_code
        
        log_level = logging.INFO if status_code < 400 else logging.ERROR
        logger.log(log_level, f"""
        [{request_id}] Response:
        Status: {status_code}
        Process Time: {process_time:.4f} sec
        Headers: {dict(response.headers)}
        Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """)
        
        return response
        
    except Exception as e:
        logger.error(f"""
        [{request_id}] Error Processing Request:
        Error: {str(e)}
        Type: {type(e).__name__}
        Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        Stack Trace:
        {traceback.format_exc()}
        """)
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "message": str(e),
                "type": type(e).__name__,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

def setup_middleware(app):
    """Setup middleware for the application"""
    try:
        logger.debug("Setting up API middleware...")
        app.middleware("http")(logging_middleware)
        logger.info("API middleware setup completed")
    except Exception as e:
        logger.error(f"""
        Middleware setup error:
        Error: {str(e)}
        Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        Stack Trace:
        {traceback.format_exc()}
        """)
        raise