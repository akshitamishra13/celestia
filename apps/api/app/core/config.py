from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AstroLive API"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./astrolive.db"
    jwt_secret: str = "local-development-secret-change-before-deploy"
    jwt_algorithm: str = "HS256"
    session_minutes: int = 60 * 24 * 7
    frontend_origin: str = "http://127.0.0.1:3000"
    cookie_secure: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
