from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./hdd.db"
    USER_MARTIEN_PASSWORD: str = ""
    USER_VISSER_PASSWORD: str = ""
    USER_TEST_PASSWORD: str = ""
    ANTHROPIC_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
