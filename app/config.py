from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path

# Obtener el directorio raíz del proyecto (un nivel arriba de app/)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str

    # Seguridad
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas por defecto

    # Aplicación
    APP_NAME: str = "Solandre API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # CORS - Orígenes permitidos (separados por coma)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        """Convierte la cadena de orígenes CORS en una lista"""
        # Si es wildcard, retornar directamente
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        # Si no, convertir la cadena separada por comas en lista
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()
