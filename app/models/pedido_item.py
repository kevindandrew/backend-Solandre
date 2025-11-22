from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal


class PedidoItem(SQLModel, table=True):
    __tablename__ = "pedido_items"

    item_id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedidos.pedido_id",
                           nullable=False, ondelete="CASCADE")
    menu_dia_id: int = Field(
        foreign_key="menu_dia.menu_dia_id", nullable=False)
    cantidad: int = Field(default=1, nullable=False)
    precio_unitario: Decimal = Field(
        nullable=False, max_digits=10, decimal_places=2)
