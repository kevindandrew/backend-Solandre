from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal
from datetime import date


class MenuDia(SQLModel, table=True):
    __tablename__ = "menu_dia"

    menu_dia_id: Optional[int] = Field(default=None, primary_key=True)
    fecha: date = Field(unique=True, nullable=False)
    plato_principal_id: int = Field(
        foreign_key="platos.plato_id", nullable=False)
    bebida_id: int = Field(foreign_key="platos.plato_id", nullable=False)
    postre_id: int = Field(foreign_key="platos.plato_id", nullable=False)
    info_nutricional: Optional[str] = Field(default=None)
    imagen_url: Optional[str] = Field(default=None, max_length=255)
    precio_menu: Decimal = Field(
        nullable=False, max_digits=10, decimal_places=2)
    publicado: bool = Field(default=False)
    cantidad_disponible: int = Field(default=0, nullable=False)
