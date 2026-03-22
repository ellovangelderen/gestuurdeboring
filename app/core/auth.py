import logging
import secrets
import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBasic()

# Simple in-memory rate limiter voor auth failures
_auth_failures: dict[str, list[float]] = defaultdict(list)
_MAX_FAILURES = 10       # max pogingen
_WINDOW_SECONDS = 300    # per 5 minuten


def get_users() -> dict[str, str]:
    users = {
        "martien": settings.USER_MARTIEN_PASSWORD,
        "sopa": settings.USER_SOPA_PASSWORD or settings.USER_MARTIEN_PASSWORD,
        "lucas": settings.USER_LUCAS_PASSWORD or settings.USER_MARTIEN_PASSWORD,
    }
    # Verwijder users zonder wachtwoord
    users = {k: v for k, v in users.items() if v}
    if settings.ENV in ("development", "staging") and settings.USER_TEST_PASSWORD:
        users["test"] = settings.USER_TEST_PASSWORD
    return users


def _check_rate_limit(username: str) -> None:
    """Block als te veel mislukte pogingen voor deze user."""
    now = time.time()
    # Verwijder oude entries
    _auth_failures[username] = [
        t for t in _auth_failures[username] if now - t < _WINDOW_SECONDS
    ]
    if len(_auth_failures[username]) >= _MAX_FAILURES:
        logger.warning("AUTH_RATE_LIMITED user=%s attempts=%d", username, len(_auth_failures[username]))
        raise HTTPException(
            status_code=429,
            detail="Te veel mislukte pogingen. Probeer het over 5 minuten opnieuw.",
        )


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    _check_rate_limit(credentials.username)

    users = get_users()
    password = users.get(credentials.username, "")
    if not password or not secrets.compare_digest(
        credentials.password.encode(), password.encode()
    ):
        _auth_failures[credentials.username].append(time.time())
        logger.warning(
            "AUTH_FAILURE user=%s reason=%s attempts=%d",
            credentials.username,
            "unknown_user" if not password else "wrong_password",
            len(_auth_failures[credentials.username]),
        )
        raise HTTPException(
            status_code=401,
            detail="Ongeldig wachtwoord",
            headers={"WWW-Authenticate": "Basic"},
        )
    # Succesvolle login: reset failure counter
    _auth_failures.pop(credentials.username, None)
    return credentials.username
