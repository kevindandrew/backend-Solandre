from sqlmodel import SQLModel, Field


class PlatoIngrediente(SQLModel, table=True):
    __tablename__ = "plato_ingredientes"

    plato_id: int = Field(foreign_key="platos.plato_id",
                          primary_key=True, ondelete="CASCADE")
    ingrediente_id: int = Field(
        foreign_key="ingredientes.ingrediente_id", primary_key=True, ondelete="CASCADE")
