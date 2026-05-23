"""FastAPI application for channel webhook endpoints."""
from __future__ import annotations

from fastapi import FastAPI

from app.integrations.webhooks import vk as vk_webhook


def create_web_app() -> FastAPI:
    app = FastAPI(title="PsySupport Channel Webhooks", docs_url=None, redoc_url=None)
    app.include_router(vk_webhook.router)
    return app
