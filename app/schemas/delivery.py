from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime, date
from app.models.enums import EstadoDelPedido, MetodoPago


class EntregaDeliveryResponse(BaseModel):
    """Pedido optimizado para vista de delivery en móvil"""
    pedido_id: int
    token_recoger: str
    estado: EstadoDelPedido

    # Información del cliente
    cliente_nombre: str
    cliente_telefono: Optional[str]

    # Ubicación para entrega
    zona_nombre: str
    direccion_referencia: Optional[str]
    google_maps_link: Optional[str]
    latitud: Optional[Decimal]
    longitud: Optional[Decimal]

    # Información de pago
    total_pedido: Decimal
    metodo_pago: MetodoPago
    esta_pagado: bool

    # Información útil para delivery
    cantidad_items: int
    fecha_pedido: Optional[datetime]
    fecha_listo_cocina: Optional[datetime]
    fecha_en_reparto: Optional[datetime]

    # Tiempo transcurrido
    minutos_desde_listo: Optional[int] = None

    class Config:
        from_attributes = True


class FinalizarEntregaRequest(BaseModel):
    """Request para finalizar una entrega"""
    confirmar_pago: bool = False  # True si recibió el efectivo o verificó el QR

    class Config:
        from_attributes = True


class EstadisticasDeliveryResponse(BaseModel):
    """Estadísticas de rendimiento del delivery"""
    fecha: date
    total_entregas_completadas: int
    entregas_pendientes: int
    # minutos desde listo hasta entregado
    tiempo_promedio_entrega: Optional[float] = None
    ingresos_del_dia: Decimal  # suma de pedidos entregados
    entrega_mas_rapida: Optional[int] = None  # minutos
    entrega_mas_lenta: Optional[int] = None  # minutos
