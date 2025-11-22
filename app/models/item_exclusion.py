from sqlmodel import SQLModel, Field


class ItemExclusion(SQLModel, table=True):
    __tablename__ = "item_exclusiones"

    item_id: int = Field(foreign_key="pedido_items.item_id",
                         primary_key=True, ondelete="CASCADE")
    ingrediente_id: int = Field(
        foreign_key="ingredientes.ingrediente_id", primary_key=True)
