from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.web.routes import pages_router, stream_router, api_router

def create_app(bot_instance) -> FastAPI:
    fastapi_app = FastAPI(
        title="MMW All-In-One Pro Stream Server",
        version="2.0.0",
        docs_url="/docs",
        redoc_url=None
    )
    fastapi_app.state.bot = bot_instance

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    fastapi_app.include_router(pages_router)
    fastapi_app.include_router(stream_router)
    fastapi_app.include_router(api_router)

    return fastapi_app
