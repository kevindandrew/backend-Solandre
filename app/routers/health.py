"""
Endpoints de salud y monitoreo del sistema.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Schema para respuesta de health check"""
    status: str
    timestamp: str
    version: str
    database: str
    error: Optional[str] = None


class InfoResponse(BaseModel):
    """Schema para información de la API"""
    name: str
    version: str
    description: str
    docs_url: str
    environment: str


@router.get("/", response_model=InfoResponse)
def root():
    """
    Endpoint raíz de la API.
    Retorna información básica sobre el servicio.
    """
    return InfoResponse(
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="API para sistema de delivery de comida Solandre",
        docs_url="/docs",
        environment="development" if settings.DEBUG else "production"
    )


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.

    Verifica que:
    - El servidor está respondiendo
    - La conexión a la base de datos está activa

    Útil para:
    - Monitoreo de la aplicación
    - Load balancers
    - Sistemas de orquestación (Kubernetes, Docker Swarm)

    Retorna:
    - 200 OK si todo está funcionando
    - Los detalles del error si algo falla
    """
    try:
        # Verificar conexión a base de datos
        db.execute(text("SELECT 1"))

        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version=settings.APP_VERSION,
            database="connected"
        )

    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            version=settings.APP_VERSION,
            database="disconnected",
            error=str(e)
        )


@router.get("/ping")
def ping():
    """
    Endpoint simple de ping.
    Útil para verificar que el servidor está activo sin consultar la BD.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }
