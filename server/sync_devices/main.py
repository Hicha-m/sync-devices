"""ASGI entry point: uvicorn sync_devices.main:app."""
from .auth import create_app

app = create_app()
