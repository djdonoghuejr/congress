from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Congress Trades MVP",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.get("/", include_in_schema=False)
    def trades_ui() -> FileResponse:
        return FileResponse(Path(__file__).parent / "ui" / "index.html", media_type="text/html")

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
