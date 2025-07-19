"""
API module for the transport optimization system.
"""

from .app import create_app
from .routes import router

__all__ = ["create_app", "router"] 