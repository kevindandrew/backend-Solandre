from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from app.models.enums import TipoPlato, EstadoDelPedido, MetodoPago


# ========== MENÚ DEL DÍA ==========

class CrearMenuRequest(BaseModel):
    """Request para crear un menú del día"""
    fecha: date = Field(..., description="Fecha del menú")
    plato_principal_id: int = Field(..., description="ID del plato principal")
    bebida_id: Optional[int] = Field(None, description="ID de la bebida")
    postre_id: Optional[int] = Field(None, description="ID del postre")
    info_nutricional: Optional[str] = Field(
        None, description="Información nutricional")
    imagen_url: Optional[str] = Field(None, description="URL de la imagen del menú")
    cantidad_disponible: int = Field(50, gt=0, description="Stock inicial")
    precio_menu: Decimal = Field(..., gt=0, description="Precio del menú")
    publicado: bool = Field(
        default=False, description="Si está visible para clientes")


class ActualizarMenuRequest(BaseModel):
    """Request para actualizar stock o precio de un menú"""
    cantidad_disponible: Optional[int] = Field(
        None, ge=0, description="Nuevo stock")
    precio_menu: Optional[Decimal] = Field(
        None, gt=0, description="Nuevo precio")
    imagen_url: Optional[str] = Field(None, description="Nueva URL de imagen")
    publicado: Optional[bool] = Field(None, description="Cambiar visibilidad")


class MenuResponse(BaseModel):
    """Response de un menú del día"""
    menu_dia_id: int
    fecha: date
    plato_principal_id: int
    bebida_id: Optional[int]
    postre_id: Optional[int]
    cantidad_disponible: int
    precio_menu: Decimal
    imagen_url: Optional[str]
    publicado: bool

    model_config = ConfigDict(from_attributes=True)


# ========== PLATOS ==========

class IngredienteEnPlatoRequest(BaseModel):
    """Ingrediente que forma parte de un plato"""
    ingrediente_id: int = Field(..., description="ID del ingrediente")


class CrearPlatoRequest(BaseModel):
    """Request para crear un nuevo plato"""
    nombre: str = Field(..., min_length=1, max_length=100,
                        description="Nombre del plato")
    imagen_url: Optional[str] = Field(None, description="URL de la imagen del plato")
    descripcion: Optional[str] = Field(
        None, max_length=500, description="Descripción del plato")
    tipo: TipoPlato = Field(...,
                            description="Tipo de plato (Principal, Entrada, Postre, Bebida)")
    ingredientes: List[IngredienteEnPlatoRequest] = Field(
        default_factory=list,
        description="Lista de ingredientes del plato"
    )


class PlatoResponse(BaseModel):
    """Response de un plato"""
    plato_id: int
    nombre: str
    imagen_url: Optional[str]
    descripcion: Optional[str]
    tipo: TipoPlato

    model_config = ConfigDict(from_attributes=True)


class IngredienteEnPlatoResponse(BaseModel):
    """Response de ingrediente dentro de un plato (con cantidad)"""
    ingrediente_id: int
    nombre: str

    model_config = ConfigDict(from_attributes=True)


class PlatoDetalleResponse(BaseModel):
    """Response detallado de un plato con sus ingredientes"""
    plato_id: int
    nombre: str
    imagen_url: Optional[str]
    descripcion: Optional[str]
    tipo: TipoPlato
    ingredientes: List[IngredienteEnPlatoResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ========== INGREDIENTES ==========

class CrearIngredienteRequest(BaseModel):
    """Request para crear un ingrediente"""
    nombre: str = Field(..., min_length=1, max_length=100,
                        description="Nombre del ingrediente")
    stock_actual: Decimal = Field(default=Decimal(
        "0"), ge=0, description="Stock inicial")


class IngredienteResponse(BaseModel):
    """Response de un ingrediente"""
    ingrediente_id: int
    nombre: str
    stock_actual: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


# ========== GESTIÓN DE PERSONAL ==========

class CrearEmpleadoRequest(BaseModel):
    """Request para crear un empleado (Admin, Cocina o Delivery)"""
    email: str = Field(..., description="Email del empleado")
    password: str = Field(..., min_length=6, description="Contraseña")
    nombre_completo: str = Field(..., min_length=1,
                                 max_length=100, description="Nombre completo")
    telefono: Optional[str] = Field(
        None, max_length=20, description="Teléfono")
    rol_id: int = Field(...,
                        description="ID del rol (1=Admin, 2=Cocina, 3=Delivery)")
    zona_reparto_id: Optional[int] = Field(
        None, description="ID de zona para Delivery")


class AsignarZonaRequest(BaseModel):
    """Request para asignar zona a un delivery"""
    zona_reparto_id: int = Field(..., description="ID de la zona a asignar")


class EmpleadoResponse(BaseModel):
    """Response de un empleado"""
    usuario_id: int
    email: str
    nombre_completo: str
    telefono: Optional[str]
    rol_id: int
    rol_nombre: str
    zona_reparto_id: Optional[int]
    zona_nombre: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ClienteResponse(BaseModel):
    """Response de un cliente"""
    usuario_id: int
    email: str
    nombre_completo: str
    telefono: Optional[str]
    rol_id: int
    fecha_registro: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ========== GESTIÓN DE PEDIDOS Y MÉTRICAS ==========

class PedidoDashboardResponse(BaseModel):
    """Response para dashboard de pedidos"""
    pedido_id: int
    token_recoger: str
    estado: EstadoDelPedido
    cliente_nombre: str
    cliente_email: str
    zona_nombre: str
    delivery_nombre: Optional[str]
    total_pedido: Decimal
    fecha_pedido: datetime
    fecha_confirmado: Optional[datetime]
    fecha_listo_cocina: Optional[datetime]
    fecha_en_reparto: Optional[datetime]
    fecha_entrega: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ReasignarDeliveryRequest(BaseModel):
    """Request para reasignar delivery a un pedido"""
    nuevo_delivery_id: int = Field(...,
                                   description="ID del nuevo delivery a asignar")


class ActualizarEstadoPedidoRequest(BaseModel):
    """Request para actualizar el estado de un pedido manualmente"""
    estado: EstadoDelPedido = Field(..., description="Nuevo estado del pedido")


class KPIsResponse(BaseModel):
    """Response con KPIs y métricas del día"""
    fecha: date
    total_pedidos: int
    pedidos_por_estado: dict
    ventas_totales: Decimal
    ventas_por_metodo_pago: dict
    tiempo_promedio_preparacion: Optional[float] = Field(
        None, description="Minutos promedio entre pedido y listo para cocina"
    )
    tiempo_promedio_entrega: Optional[float] = Field(
        None, description="Minutos promedio entre pedido y entrega"
    )
    pedidos_mas_rapidos: List[dict] = Field(
        default_factory=list, description="Top 5 pedidos más rápidos"
    )
    pedidos_mas_lentos: List[dict] = Field(
        default_factory=list, description="Top 5 pedidos más lentos"
    )


# ========== GESTIÓN DE ZONAS ==========

class CrearZonaRequest(BaseModel):
    """Request para crear una zona de delivery"""
    nombre_zona: str = Field(..., min_length=1, max_length=100,
                             description="Nombre de la zona")


class ActualizarZonaRequest(BaseModel):
    """Request para actualizar una zona de delivery"""
    nombre_zona: str = Field(..., min_length=1, max_length=100,
                             description="Nuevo nombre de la zona")


class ZonaResponse(BaseModel):
    """Response de una zona de delivery"""
    zona_id: int
    nombre_zona: str

    model_config = ConfigDict(from_attributes=True)
