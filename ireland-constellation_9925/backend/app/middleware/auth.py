"""
Verifies Firebase ID tokens on every request and attaches the decoded
identity to request.state.user. Downstream routers/middleware read
request.state.user instead of re-parsing the token.
"""

import firebase_admin
from firebase_admin import auth as firebase_auth
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

if not firebase_admin._apps:
    firebase_admin.initialize_app()

PUBLIC_PATHS = {"/health", "/docs", "/openapi.json"}


class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing bearer token"})

        id_token = auth_header.removeprefix("Bearer ").strip()
        try:
            decoded = firebase_auth.verify_id_token(id_token)
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        request.state.user = {
            "uid": decoded["uid"],
            "email": decoded.get("email"),
            "groups": decoded.get("groups", []),  # populate via custom claims
            "persona": decoded.get("persona", "analyst"),  # custom claim, defaulted
        }
        return await call_next(request)
