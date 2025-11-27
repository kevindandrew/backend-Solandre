from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import date
from app.models.enums import TipoPlato


class ZonaResponse(BaseModel):
    """Schema para la respuesta de zonas de delivery"""
    zona_id: int
    nombre_zona: str

    class Config:
        from_attributes = True


class PlatoSimpleResponse(BaseModel):
    """Schema simplificado de plato para el menú"""
    plato_id: int
    nombre: str
    descripcion: Optional[str]
    tipo: TipoPlato

    class Config:
        from_attributes = True



class IngredienteResponse(BaseModel):
    """Schema para la respuesta de ingredientes"""
    ingrediente_id: int
    nombre: str

    class Config:
        from_attributes = True


class PlatoCompletoResponse(BaseModel):
    """Schema completo de plato con imagen e ingredientes"""
    plato_id: int
    nombre: str
    descripcion: Optional[str]
    tipo: TipoPlato
    imagen_url: Optional[str]
    ingredientes: list[IngredienteResponse] = []

    class Config:
        from_attributes = True


class MenuDiaResponse(BaseModel):
    """Schema para la respuesta del menú del día"""
    menu_dia_id: int
    fecha: date
    precio_menu: Decimal
    cantidad_disponible: int
    publicado: bool
    info_nutricional: Optional[str]
    imagen_url: Optional[str]

    # Platos del menú
    plato_principal: PlatoSimpleResponse
    bebida: Optional[PlatoSimpleResponse]
    postre: Optional[PlatoSimpleResponse]

    class Config:
        from_attributes = True


class MenuIngredientesResponse(BaseModel):
    """Schema para la respuesta de ingredientes del menú"""
    menu_dia_id: int
    fecha: date
    plato_principal: PlatoSimpleResponse
    ingredientes: list[IngredienteResponse]

    class Config:
        from_attributes = True
