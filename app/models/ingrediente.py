from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal


class Ingrediente(SQLModel, table=True):
    __tablename__ = "ingredientes"

    ingrediente_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=100, unique=True, nullable=False)
    stock_actual: Optional[Decimal] = Field(
        default=None, max_digits=10, decimal_places=2)
