from __future__ import annotations

from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from auth.jwt import ALGORITHM, SECRET_KEY


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Resolve active workspace and organization headers and attach them to request state."""

    async def dispatch(self, request: Request, call_next):
        workspace_id = request.headers.get("X-Workspace-ID")
        organization_id = request.headers.get("X-Organization-ID")

        auth_header = request.headers.get("authorization") or ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                if not workspace_id and payload.get("workspace_id"):
                    workspace_id = str(payload.get("workspace_id"))
                if not organization_id and payload.get("organization_id"):
                    organization_id = str(payload.get("organization_id"))
            except Exception:
                pass

        request.state.workspace_id = int(workspace_id) if workspace_id and workspace_id.isdigit() else None
        request.state.organization_id = int(organization_id) if organization_id and organization_id.isdigit() else None

        response = await call_next(request)
        if request.state.workspace_id is not None:
            response.headers["X-Workspace-ID"] = str(request.state.workspace_id)
        if request.state.organization_id is not None:
            response.headers["X-Organization-ID"] = str(request.state.organization_id)
        return response
