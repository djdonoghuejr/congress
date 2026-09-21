from fastapi import APIRouter

from app.api.routes.filings import router as filings_router
from app.api.routes.health import router as health_router
from app.api.routes.trades import router as trades_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(trades_router, tags=["trades"])
api_router.include_router(filings_router, tags=["filings"])

