from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Enum as SQLAEnum
from typing import Optional
from app.models.enums import TipoPlato


class Plato(SQLModel, table=True):
    __tablename__ = "platos"

    plato_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=100, nullable=False)
    imagen_url: Optional[str] = Field(default=None, max_length=255)
    descripcion: Optional[str] = Field(default=None)
    tipo: TipoPlato = Field(
        default=TipoPlato.PRINCIPAL,
        sa_column=Column(
            SQLAEnum(
                TipoPlato,
                name="tipo_de_plato",
                create_type=False,
                native_enum=False,
                values_callable=lambda x: [e.value for e in x]
            )
        )
    )
    disponible: bool = Field(default=True)
