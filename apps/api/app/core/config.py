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
    astrology_provider: str = "navamsha"
    navamsha_api_url: str = "https://api.navamsha.in/api/v1"
    navamsha_api_key: str = ""
    astrology_observation_point: str = "topocentric"
    astrology_node_type: str = "mean"
    vedastro_api_url: str = "https://api.vedastro.org/api/Calculate"
    vedastro_api_key: str = "FreeAPIUser"
    astrology_ayanamsha: str = "LAHIRI"
    geocoding_url: str = "https://nominatim.openstreetmap.org/search"
    geocoding_user_agent: str = "AstroLive/0.1 (local-prototype)"
    provider_timeout_seconds: float = 120.0
    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"
    openai_api_url: str = "https://api.openai.com/v1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
