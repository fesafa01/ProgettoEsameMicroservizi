"""FastAPI application for the Knowledge Validator service."""

from __future__ import annotations

from fastapi import FastAPI

from kv.api import router

app = FastAPI(title="Knowledge Validator", version="0.1.0")
app.include_router(router, prefix="/api/v1")
