"""
FastAPI application factory for the transport optimization API.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..core.config import Config
from .routes import router


def create_app(config: Config) -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Create FastAPI app
    app = FastAPI(
        title="Accra Public Transport Analysis API",
        description="AI-powered public transport efficiency analysis for Accra, Ghana",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get("api.cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files
    processed_dir = config.data_paths['processed_dir']
    if processed_dir.exists():
        app.mount("/data/processed", StaticFiles(directory=str(processed_dir)), name="processed")
    
    # Include routers
    app.include_router(router, prefix="/api/v1")
    
    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        logging.info("Starting Accra Transport Analysis API")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logging.info("Shutting down Accra Transport Analysis API")
    
    return app 