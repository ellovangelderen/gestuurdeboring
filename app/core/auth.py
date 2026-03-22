import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.password import verify_password

logger = logging.getLogger(__name__)
security = HTTPBasic()

# Simple in-memory rate limiter voor auth failures
_auth_failures: dict[str, list[float]] = defaultdict(list)
_MAX_FAILURES = 10       # max pogingen
_WINDOW_SECONDS = 300    # per 5 minuten


def _check_rate_limit(username: str) -> None:
    """Block als te veel mislukte pogingen voor deze user."""
    now = time.time()
    _auth_failures[username] = [
        t for t in _auth_failures[username] if now - t < _WINDOW_SECONDS
    ]
    if len(_auth_failures[username]) >= _MAX_FAILURES:
        logger.warning("AUTH_RATE_LIMITED user=%s attempts=%d", username, len(_auth_failures[username]))
        raise HTTPException(
            status_code=429,
            detail="Te veel mislukte pogingen. Probeer het over 5 minuten opnieuw.",
        )


def get_current_user(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> str:
    """Authenticeer user via DB lookup + bcrypt."""
    _check_rate_limit(credentials.username)

    from app.admin.models import User
    user = db.query(User).filter_by(username=credentials.username, actief=True).first()

    if not user or not verify_password(credentials.password, user.wachtwoord_hash):
        _auth_failures[credentials.username].append(time.time())
        logger.warning(
            "AUTH_FAILURE user=%s reason=%s attempts=%d",
            credentials.username,
            "unknown_user" if not user else "wrong_password",
            len(_auth_failures[credentials.username]),
        )
        raise HTTPException(
            status_code=401,
            detail="Ongeldig wachtwoord",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Succesvolle login: reset failure counter
    _auth_failures.pop(credentials.username, None)

    # Update laatst_ingelogd in aparte sessie (mag nooit de hoofdsessie beïnvloeden)
    try:
        auth_db = SessionLocal()
        try:
            u = auth_db.query(User).filter_by(username=credentials.username).first()
            if u:
                u.laatst_ingelogd = datetime.now(timezone.utc).replace(tzinfo=None)
                auth_db.commit()
        finally:
            auth_db.close()
    except Exception:
        pass

    return credentials.username
