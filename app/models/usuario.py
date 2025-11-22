from sqlmodel import SQLModel, Field
from typing import Optional


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    usuario_id: Optional[int] = Field(default=None, primary_key=True)
    rol_id: int = Field(foreign_key="roles.rol_id", nullable=False)
    nombre_completo: str = Field(max_length=100, nullable=False)
    email: str = Field(max_length=100, unique=True, nullable=False)
    password_hash: str = Field(max_length=255, nullable=False)
    telefono: Optional[str] = Field(default=None, max_length=20)
    zona_reparto_id: Optional[int] = Field(
        default=None, foreign_key="zonas_delivery.zona_id")
