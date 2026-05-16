"""FastAPI app factory.

Run with:  uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from app.api.metrics import render_metrics
from app.api.routes_operator import mount_capabilities
from app.api.routes_operator import router as operator_router
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    get_logger("app").info("startup")
    mount_capabilities()
    app.include_router(operator_router)
    yield
    get_logger("app").info("shutdown")


app = FastAPI(title="maymayinvest v1", version="0.0.1", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/metrics")
async def metrics():
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
