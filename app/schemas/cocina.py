from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date
from app.models.enums import EstadoDelPedido


class ExclusionCocina(BaseModel):
    """Exclusión de ingrediente para mostrar en cocina"""
    ingrediente_nombre: str

    class Config:
        from_attributes = True


class ItemCocina(BaseModel):
    """Item del pedido para cocina con exclusiones destacadas"""
    item_id: int
    cantidad: int
    menu_fecha: date
    plato_principal: str
    bebida: str
    postre: str
    # Exclusiones claramente visibles (ej: "Sin cebolla", "Sin ají")
    exclusiones: List[str] = []

    class Config:
        from_attributes = True


class PedidoCocinaResponse(BaseModel):
    """Pedido optimizado para vista de cocina"""
    pedido_id: int
    token_recoger: str
    estado: EstadoDelPedido
    fecha_pedido: Optional[datetime]

    # Info del cliente
    cliente_nombre: str
    cliente_telefono: Optional[str]

    # Items con exclusiones destacadas
    items: List[ItemCocina]

    # Tiempo transcurrido (útil para KPIs)
    minutos_desde_pedido: Optional[int] = None

    class Config:
        from_attributes = True


class CambiarEstadoCocinaRequest(BaseModel):
    """Request para cambiar el estado de un pedido desde cocina"""
    nuevo_estado: EstadoDelPedido

    class Config:
        use_enum_values = True


class EstadisticasCocinaResponse(BaseModel):
    """Estadísticas de rendimiento de cocina"""
    fecha: date
    total_pedidos_procesados: int
    pedidos_en_proceso: int
    tiempo_promedio_preparacion: Optional[float] = None  # minutos
    pedido_mas_rapido: Optional[int] = None  # minutos
    pedido_mas_lento: Optional[int] = None  # minutos
    platos_preparados: int
