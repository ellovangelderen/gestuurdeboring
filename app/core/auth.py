import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings


security = HTTPBasic()


def get_users() -> dict[str, str]:
    users = {
        "martien": settings.USER_MARTIEN_PASSWORD,
        "visser": settings.USER_VISSER_PASSWORD,
    }
    if settings.ENV == "development" and settings.USER_TEST_PASSWORD:
        users["test"] = settings.USER_TEST_PASSWORD
    return users


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    users = get_users()
    password = users.get(credentials.username, "")
    if not password or not secrets.compare_digest(
        credentials.password.encode(), password.encode()
    ):
        raise HTTPException(
            status_code=401,
            detail="Ongeldig wachtwoord",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
