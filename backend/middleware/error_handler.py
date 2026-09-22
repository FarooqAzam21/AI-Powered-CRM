import logging
from typing import Any
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError, HTTPException as FastAPIHTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from middleware.correlation import get_current_request_id
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def create_error_response(status_code: int, code: str, message: Any, request_id: str, detail_override: Any = None) -> JSONResponse:
    """Helper to format standardized JSON error response with detail backward compatibility."""
    detail_val = detail_override if detail_override is not None else message
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail_val,
            "error": {
                "code": code,
                "message": str(message) if not isinstance(message, str) else message,
                "request_id": request_id,
            }
        },
    )


async def http_exception_handler(request: Request, exc: Any) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or get_current_request_id()
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("error") or str(detail)
        code = detail.get("error") or "HTTP_ERROR"
        detail_override = detail
    else:
        message = str(detail)
        code = "HTTP_ERROR"
        detail_override = detail

    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = detail.get("error", "UNAUTHORIZED") if isinstance(detail, dict) else "UNAUTHORIZED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = detail.get("error", "FORBIDDEN") if isinstance(detail, dict) else "FORBIDDEN"
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        code = detail.get("error", "NOT_FOUND") if isinstance(detail, dict) else "NOT_FOUND"
    elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        code = detail.get("error", "RATE_LIMIT_EXCEEDED") if isinstance(detail, dict) else "RATE_LIMIT_EXCEEDED"

    return create_error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        request_id=request_id,
        detail_override=detail_override,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or get_current_request_id()
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = f"Validation error at '{'.'.join(str(loc) for loc in first_error.get('loc', []))}': {first_error.get('msg', 'Invalid input')}"

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message=msg,
        request_id=request_id,
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or get_current_request_id()
    logger.error(f"Database error during request {request_id}: {exc}", exc_info=True)

    # Never expose raw SQL queries or DB traces in production
    msg = "A database operation error occurred." if settings.environment == "production" else str(exc)
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="DATABASE_ERROR",
        message=msg,
        request_id=request_id,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or get_current_request_id()
    logger.error(f"Unhandled exception during request {request_id}: {exc}", exc_info=True)

    msg = "An unexpected internal server error occurred." if settings.environment == "production" else f"Internal error: {str(exc)}"
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message=msg,
        request_id=request_id,
    )
