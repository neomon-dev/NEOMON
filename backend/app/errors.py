import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

logger = logging.getLogger("neomon.api")


class BackendError(Exception):
    def __init__(self, message: str, status_code: int = 400, error: str = "backend_error") -> None:
        self.message = message
        self.status_code = status_code
        self.error = error


async def backend_error_handler(request: Request, exc: BackendError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "message": exc.message, "request_id": request_id},
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled backend error", extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "The server could not complete the request.",
            "request_id": request_id,
        },
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed.",
            "request_id": request_id,
            "details": jsonable_encoder(exc.errors()),
        },
    )
