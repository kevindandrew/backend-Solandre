from sqlmodel import SQLModel, Field
from typing import Optional


class ZonaDelivery(SQLModel, table=True):
    __tablename__ = "zonas_delivery"

    zona_id: Optional[int] = Field(default=None, primary_key=True)
    nombre_zona: str = Field(max_length=100, unique=True, nullable=False)
