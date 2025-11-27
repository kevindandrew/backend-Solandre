from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Enum as SQLAEnum
from typing import Optional
from decimal import Decimal
from datetime import datetime
from app.models.enums import EstadoDelPedido, MetodoPago


class Pedido(SQLModel, table=True):
    __tablename__ = "pedidos"

    pedido_id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuarios.usuario_id", nullable=False)

    # Logística y ubicación
    zona_id: int = Field(foreign_key="zonas_delivery.zona_id", nullable=False)
    google_maps_link: Optional[str] = Field(default=None)
    latitud: Optional[Decimal] = Field(
        default=None, max_digits=10, decimal_places=8)
    longitud: Optional[Decimal] = Field(
        default=None, max_digits=11, decimal_places=8)
    direccion_referencia: Optional[str] = Field(default=None)

    # Estados y control
    estado: EstadoDelPedido = Field(
        default=EstadoDelPedido.PENDIENTE,
        sa_column=Column(
            SQLAEnum(
                EstadoDelPedido,
                name="estado_del_pedido",
                create_type=False,
                native_enum=False,
                values_callable=lambda x: [e.value for e in x]
            )
        )
    )
    token_recoger: str = Field(max_length=8, unique=True, nullable=False)

    # Dinero
    total_pedido: Decimal = Field(
        nullable=False, max_digits=10, decimal_places=2)
    
    metodo_pago: MetodoPago = Field(
        sa_column=Column(
            SQLAEnum(
                MetodoPago,
                name="metodo_pago",
                create_type=False,
                native_enum=False,
                values_callable=lambda x: [e.value for e in x]
            ),
            nullable=False
        )
    )
    esta_pagado: bool = Field(default=False)

    # Asignación automática
    delivery_asignado_id: Optional[int] = Field(
        default=None, foreign_key="usuarios.usuario_id")

    # Métricas de tiempo (KPIs)
    fecha_pedido: Optional[datetime] = Field(default_factory=datetime.now)
    fecha_confirmado: Optional[datetime] = Field(default=None)
    fecha_listo_cocina: Optional[datetime] = Field(default=None)
    fecha_en_reparto: Optional[datetime] = Field(default=None)
    fecha_entrega: Optional[datetime] = Field(default=None)
