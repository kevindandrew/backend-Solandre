from sqlmodel import SQLModel, Field
from decimal import Decimal


class PlatoIngrediente(SQLModel, table=True):
    __tablename__ = "plato_ingredientes"

    plato_id: int = Field(foreign_key="platos.plato_id",
                          primary_key=True, ondelete="CASCADE")
    ingrediente_id: int = Field(
        foreign_key="ingredientes.ingrediente_id", primary_key=True, ondelete="CASCADE")
    cantidad_requerida: Decimal = Field(
        default=0, max_digits=10, decimal_places=2)
