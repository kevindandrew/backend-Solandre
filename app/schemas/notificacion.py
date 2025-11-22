"""
Schemas para el sistema de notificaciones
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any


class EventoResponse(BaseModel):
    """Schema para respuesta de evento/notificación"""
    evento_id: str
    tipo: str
    titulo: str
    mensaje: str
    data: Dict[str, Any]
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)


class ContadorEventosResponse(BaseModel):
    """Schema para contador de eventos nuevos"""
    total: int
    desde: datetime
    eventos_por_tipo: Dict[str, int]


class NotificarLlegadaRequest(BaseModel):
    """Schema para endpoint de notificar llegada del delivery"""
    latitud: float
    longitud: float
    mensaje_adicional: Optional[str] = None
