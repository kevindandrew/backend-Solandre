from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date
from app.models.enums import EstadoDelPedido, MetodoPago


class ExclusionRequest(BaseModel):
    """Schema para las exclusiones de ingredientes en un item"""
    ingrediente_id: int


class ItemPedidoRequest(BaseModel):
    """Schema para cada item del pedido"""
    menu_dia_id: int
    cantidad: int = Field(ge=1, le=10)
    exclusiones: List[int] = Field(
        default_factory=list, description="IDs de ingredientes a excluir")


class CrearPedidoRequest(BaseModel):
    """Schema para crear un nuevo pedido"""
    zona_id: int
    google_maps_link: Optional[str] = None
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    direccion_referencia: Optional[str] = None
    metodo_pago: MetodoPago
    items: List[ItemPedidoRequest] = Field(min_length=1)


class MenuDiaSimple(BaseModel):
    """Schema simplificado del menú del día para respuestas"""
    menu_dia_id: int
    fecha: date
    precio_menu: Decimal

    class Config:
        from_attributes = True


class ItemPedidoResponse(BaseModel):
    """Schema para la respuesta de items del pedido"""
    item_id: int
    cantidad: int
    precio_unitario: Decimal
    menu: MenuDiaSimple
    exclusiones: List[str] = Field(
        default_factory=list, description="Nombres de ingredientes excluidos")

    class Config:
        from_attributes = True


class PedidoResponse(BaseModel):
    """Schema para la respuesta de un pedido creado"""
    pedido_id: int
    token_recoger: str
    estado: EstadoDelPedido
    total_pedido: Decimal
    metodo_pago: MetodoPago
    esta_pagado: bool
    zona_id: int
    direccion_referencia: Optional[str]
    fecha_pedido: Optional[datetime]

    class Config:
        from_attributes = True


class MisPedidosResponse(BaseModel):
    """Schema para el historial de pedidos del usuario"""
    pedido_id: int
    token_recoger: str
    estado: EstadoDelPedido
    total_pedido: Decimal
    metodo_pago: MetodoPago
    esta_pagado: bool
    fecha_pedido: Optional[datetime]
    fecha_entrega: Optional[datetime]
    items_count: int

    class Config:
        from_attributes = True


class TrackPedidoResponse(BaseModel):
    """Schema para el tracking del pedido"""
    pedido_id: int
    token_recoger: str
    estado: EstadoDelPedido
    total_pedido: Decimal
    metodo_pago: MetodoPago
    esta_pagado: bool

    # Timestamps del flujo
    fecha_pedido: Optional[datetime]
    fecha_confirmado: Optional[datetime]
    fecha_listo_cocina: Optional[datetime]
    fecha_en_reparto: Optional[datetime]
    fecha_entrega: Optional[datetime]

    # Información del delivery si está asignado
    delivery_asignado_id: Optional[int]
    nombre_delivery: Optional[str] = None

    class Config:
        from_attributes = True


class PedidoDetalleResponse(BaseModel):
    """Schema para el detalle completo de un pedido con items y exclusiones"""
    pedido_id: int
    token_recoger: str
    estado: EstadoDelPedido
    total_pedido: Decimal
    metodo_pago: MetodoPago
    esta_pagado: bool
    zona_id: int
    direccion_referencia: Optional[str]
    google_maps_link: Optional[str]
    latitud: Optional[Decimal]
    longitud: Optional[Decimal]
    fecha_pedido: Optional[datetime]
    fecha_confirmado: Optional[datetime]
    fecha_listo_cocina: Optional[datetime]
    fecha_en_reparto: Optional[datetime]
    fecha_entrega: Optional[datetime]
    items: List[ItemPedidoResponse]

    class Config:
        from_attributes = True
