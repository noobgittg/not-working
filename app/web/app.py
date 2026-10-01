import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.web.routes import pages_router, stream_router, api_router


def create_app(bot_instance) -> FastAPI:
    fastapi_app = FastAPI(
        title="MMW All-In-One Pro Stream Server",
        version="2.6.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    fastapi_app.state.bot = bot_instance

    raw_origins = os.environ.get("CORS_ORIGINS", "*").strip()
    origins = [item.strip() for item in raw_origins.split(",") if item.strip()] or ["*"]
    wildcard = origins == ["*"]

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=not wildcard,
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=["*"],
    )

    fastapi_app.include_router(pages_router)
    fastapi_app.include_router(stream_router)
    fastapi_app.include_router(api_router)

    return fastapi_app
