from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal


class ZonaDelivery(SQLModel, table=True):
    __tablename__ = "zonas_delivery"

    zona_id: Optional[int] = Field(default=None, primary_key=True)
    nombre_zona: str = Field(max_length=100, unique=True, nullable=False)
    costo_envio: Decimal = Field(default=0.00, max_digits=10, decimal_places=2)
