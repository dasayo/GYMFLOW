"""
Configuración central del backend (core, según AGENTS.md).
Lee variables de entorno / .env vía pydantic-settings.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    # docker-compose.yml/.env ya usan JWT_SECRET (no JWT_SECRET_KEY, el default de pydantic-settings).
    jwt_secret_key: str = Field(validation_alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    # Sesión del Miembro en el portal (011): access token corto + refresh token
    # con ventana de inactividad deslizante (valores confirmados por el equipo).
    member_access_token_minutes: int = 15
    member_refresh_days: int = 7
    # Zona horaria del gimnasio, usada para calcular "día calendario" (RN-02) y
    # ventanas temporales (RN-04). Centralizada aquí según plan.md de 001.
    timezone: str = "America/Bogota"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def now() -> datetime:
    """Hora actual en la zona horaria del gimnasio (tz-aware). Compartida por
    cualquier módulo que necesite "ahora"/"hoy" en vez de UTC del servidor."""
    return datetime.now(ZoneInfo(settings.timezone))
