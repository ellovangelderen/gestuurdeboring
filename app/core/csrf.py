"""CSRF bescherming via Origin/Referer header check.

Bij HTTPBasic auth is cookie-gebaseerde CSRF niet van toepassing, maar een
kwaadaardige site kan een form POST doen met de browser-gecachete credentials.
Deze middleware checkt dat POST requests van ons eigen domein komen.
"""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Toegestane origins (productie + staging + lokaal)
ALLOWED_ORIGINS = {
    "https://hdd.inodus.nl",
    "https://hdd-staging.inodus.nl",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}


class CSRFMiddleware(BaseHTTPMiddleware):
    """Check Origin/Referer header bij POST/PUT/DELETE requests."""

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("origin", "")
            referer = request.headers.get("referer", "")

            # Sta API calls zonder browser toe (geen Origin/Referer)
            if not origin and not referer:
                # Waarschijnlijk een API client, niet een browser form
                return await call_next(request)

            # Check Origin header
            if origin and origin not in ALLOWED_ORIGINS:
                logger.warning("CSRF_BLOCKED origin=%s path=%s", origin, request.url.path)
                return JSONResponse(
                    {"detail": "CSRF: verzoek geblokkeerd (onbekende origin)"},
                    status_code=403,
                )

            # Check Referer header als Origin er niet is
            if not origin and referer:
                referer_ok = any(referer.startswith(o) for o in ALLOWED_ORIGINS)
                if not referer_ok:
                    logger.warning("CSRF_BLOCKED referer=%s path=%s", referer, request.url.path)
                    return JSONResponse(
                        {"detail": "CSRF: verzoek geblokkeerd (onbekende referer)"},
                        status_code=403,
                    )

        return await call_next(request)
