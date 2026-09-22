import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_CTX_KEY = "request_id"
request_id_var: ContextVar[str] = ContextVar(REQUEST_ID_CTX_KEY, default="")


def get_current_request_id() -> str:
    """Returns the request_id bound to the current async context execution."""
    return request_id_var.get()


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures every inbound HTTP request has a unique Request ID.
    Reads incoming 'X-Request-ID' or generates a new UUID4 prefix 'req_'.
    Binds the ID to request.state and ContextVar for logging and downstream processing.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_id = request.headers.get("X-Request-ID")
        if incoming_id:
            request_id = incoming_id.strip()[:64]
        else:
            request_id = f"req_{uuid.uuid4().hex[:16]}"

        request.state.request_id = request_id
        token = request_id_var.set(request_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token)
