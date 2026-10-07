import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from neeka.brain.engine import NEEKAEngine
from neeka.brain.exceptions import NEEKAError
from neeka.services.control import ControlService
from .config import Settings
from .errors import internal_error_handler, neeka_error_handler
from .routes import router


def create_app(db_path: str | None = None, settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    engine = NEEKAEngine(db_path or config.database_url)
    app = FastAPI(title="NEEKA Work Engine API", version="1.0.0")
    app.state.engine = engine
    app.state.service = ControlService(engine)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logging.getLogger("neeka.api").info(
            "%s %s -> %s %.3fs request_id=%s", request.method, request.url.path,
            response.status_code, time.perf_counter() - started, request_id,
        )
        return response

    app.add_exception_handler(NEEKAError, neeka_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
    app.include_router(router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "neeka"}

    return app