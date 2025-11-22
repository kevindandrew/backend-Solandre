from sqlmodel import SQLModel, Field
from typing import Optional


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    rol_id: Optional[int] = Field(default=None, primary_key=True)
    nombre_rol: str = Field(max_length=50, unique=True, nullable=False)
