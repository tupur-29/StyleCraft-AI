"""
Main application package for StyleCraft AI.

This package contains all the core components of the FastAPI application,
including API endpoints (in main.py), Pydantic schemas (in schemas.py),
CRUD operations (in crud.py), database connection setup and ORM models
(in database.py), and AI core logic (in ai_core.py).

The FastAPI application instance 'app' is exported from this package
for use by ASGI servers like Uvicorn.
"""


from .main import app


__all__ = ["app"]
