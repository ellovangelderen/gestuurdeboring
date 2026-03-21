from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./hdd.db"
    USER_MARTIEN_PASSWORD: str = ""
    USER_VISSER_PASSWORD: str = ""
    USER_SOPA_PASSWORD: str = ""
    USER_LUCAS_PASSWORD: str = ""
    USER_TEST_PASSWORD: str = ""
    ANTHROPIC_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

# Zorg dat de database directory bestaat (Railway volume /data/)
if "sqlite:///" in settings.DATABASE_URL:
    from pathlib import Path
    db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite:", "")
    db_dir = Path(db_path).parent
    if not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)
