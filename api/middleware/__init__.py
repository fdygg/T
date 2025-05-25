from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .error_handler import add_error_handlers
from .auth import auth_middleware

def setup_middleware(app: FastAPI):
    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add authentication middleware
    app.middleware("http")(auth_middleware)
    
    # Add error handlers
    add_error_handlers(app)