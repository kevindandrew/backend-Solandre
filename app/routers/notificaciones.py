"""
Router para gestión de notificaciones en tiempo real.
Sistema basado en polling (sin WebSockets).
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.usuario import Usuario
from app.models.pedido import Pedido
from app.schemas.notificacion import (
    EventoResponse,
    ContadorEventosResponse,
    NotificarLlegadaRequest
)
from app.utils.dependencies import get_current_user
from app.utils.notificaciones import (
    gestor_notificaciones,
    notificar_delivery_cerca
)

router = APIRouter(
    prefix="/notificaciones",
    tags=["Notificaciones"]
)


@router.get("/mis-notificaciones", response_model=List[EventoResponse])
def obtener_mis_notificaciones(
    desde_minutos: int = Query(
        default=5, ge=1, le=60, description="Minutos hacia atrás"),
    tipo: Optional[str] = Query(
        default=None, description="Filtrar por tipo de evento"),
    limit: int = Query(default=50, ge=1, le=100,
                       description="Máximo de notificaciones"),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene las notificaciones recientes del usuario autenticado.

    El frontend puede consultar este endpoint cada 10-30 segundos para simular tiempo real.

    Parámetros:
    - desde_minutos: Buscar notificaciones de los últimos X minutos (default: 5)
    - tipo: Filtrar por tipo específico (NUEVO_PEDIDO, CAMBIO_ESTADO, etc.)
    - limit: Número máximo de notificaciones a retornar

    Ejemplos de uso:
    - Cocina: Consulta cada 10 segundos para ver nuevos pedidos
    - Cliente: Consulta cada 30 segundos para ver estado de su pedido
    - Delivery: Consulta cada 15 segundos para ver nuevas asignaciones
    """
    desde = datetime.now() - timedelta(minutes=desde_minutos)

    eventos = gestor_notificaciones.obtener_eventos_recientes(
        rol_id=current_user.rol_id,
        usuario_id=current_user.usuario_id,
        desde=desde,
        tipo=tipo,
        limit=limit
    )

    return [
        EventoResponse(
            evento_id=e.evento_id,
            tipo=e.tipo,
            titulo=e.titulo,
            mensaje=e.mensaje,
            data=e.data,
            fecha_creacion=e.fecha_creacion
        )
        for e in eventos
    ]


@router.get("/contador", response_model=ContadorEventosResponse)
def contador_notificaciones_nuevas(
    desde: Optional[datetime] = Query(
        default=None,
        description="Fecha desde la cual contar (ISO format)"
    ),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Cuenta las notificaciones nuevas desde una fecha específica.

    Útil para mostrar badge con número de notificaciones no vistas.

    Si no se proporciona 'desde', cuenta las de los últimos 5 minutos.

    El frontend puede:
    1. Guardar la última fecha de consulta en localStorage
    2. Consultar este endpoint para saber cuántas hay nuevas
    3. Mostrar badge: "🔔 3" si hay 3 notificaciones nuevas
    """
    if desde is None:
        desde = datetime.now() - timedelta(minutes=5)

    eventos = gestor_notificaciones.obtener_eventos_recientes(
        rol_id=current_user.rol_id,
        usuario_id=current_user.usuario_id,
        desde=desde
    )

    # Contar por tipo
    eventos_por_tipo = {}
    for evento in eventos:
        if evento.tipo not in eventos_por_tipo:
            eventos_por_tipo[evento.tipo] = 0
        eventos_por_tipo[evento.tipo] += 1

    return ContadorEventosResponse(
        total=len(eventos),
        desde=desde,
        eventos_por_tipo=eventos_por_tipo
    )


@router.get("/cocina/nuevos-pedidos", response_model=List[EventoResponse])
def obtener_nuevos_pedidos_cocina(
    desde_minutos: int = Query(default=10, ge=1, le=60),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint especializado para tablets de cocina.

    Retorna notificaciones de nuevos pedidos de los últimos X minutos.
    La tablet puede consultar esto cada 10 segundos y reproducir un sonido
    cuando detecta pedidos nuevos.

    Solo accesible por usuarios con rol Cocina (2) o Admin (1).
    """
    # Verificar permisos
    if current_user.rol_id not in [1, 2]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo cocina y administradores pueden acceder a este endpoint"
        )

    desde = datetime.now() - timedelta(minutes=desde_minutos)

    eventos = gestor_notificaciones.obtener_eventos_recientes(
        rol_id=2,  # Cocina
        desde=desde,
        tipo="NUEVO_PEDIDO"
    )

    return [
        EventoResponse(
            evento_id=e.evento_id,
            tipo=e.tipo,
            titulo=e.titulo,
            mensaje=e.mensaje,
            data=e.data,
            fecha_creacion=e.fecha_creacion
        )
        for e in eventos
    ]


@router.get("/delivery/mis-asignaciones", response_model=List[EventoResponse])
def obtener_mis_asignaciones_delivery(
    desde_minutos: int = Query(default=30, ge=1, le=120),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint especializado para app móvil de delivery.

    Retorna pedidos asignados recientemente al delivery.

    Solo accesible por usuarios con rol Delivery (3).
    """
    # Verificar permisos
    if current_user.rol_id not in [1, 3]:  # 1 = Admin, 3 = Delivery
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores y delivery pueden acceder a este endpoint"
        )

    desde = datetime.now() - timedelta(minutes=desde_minutos)

    eventos = gestor_notificaciones.obtener_eventos_recientes(
        rol_id=3,  # Delivery
        usuario_id=current_user.usuario_id,
        desde=desde,
        tipo="PEDIDO_ASIGNADO"
    )

    return [
        EventoResponse(
            evento_id=e.evento_id,
            tipo=e.tipo,
            titulo=e.titulo,
            mensaje=e.mensaje,
            data=e.data,
            fecha_creacion=e.fecha_creacion
        )
        for e in eventos
    ]


@router.post("/delivery/notificar-llegada/{pedido_id}")
def notificar_llegada_delivery(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    El delivery notifica que llegó a la ubicación del cliente.

    Esto crea una notificación para el cliente diciéndole que
    el delivery está afuera esperando.

    El delivery puede llamar a este endpoint:
    - Automáticamente cuando GPS detecta que llegó
    - Manualmente con un botón "Notificar que llegué"

    Solo accesible por usuarios con rol Delivery (3).
    """
    # Verificar permisos
    if current_user.rol_id not in [1, 3]:  # 1 = Admin, 3 = Delivery
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores y delivery pueden notificar llegadas"
        )

    # Buscar el pedido
    pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar que el pedido esté asignado a este delivery
    if pedido.delivery_asignado_id != current_user.usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este pedido no está asignado a ti"
        )

    # Crear notificación para el cliente
    notificar_delivery_cerca(
        pedido_id=pedido.pedido_id,
        token=pedido.token_recoger,
        cliente_id=pedido.usuario_id,
        delivery_nombre=current_user.nombre_completo
    )

    return {
        "message": "Cliente notificado exitosamente",
        "pedido_id": pedido_id,
        "cliente_id": pedido.usuario_id
    }


@router.get("/cliente/mis-pedidos", response_model=List[EventoResponse])
def obtener_notificaciones_mis_pedidos(
    desde_minutos: int = Query(default=60, ge=1, le=1440),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint especializado para clientes.

    Retorna notificaciones sobre sus pedidos activos.
    Incluye cambios de estado, delivery en camino, etc.

    Solo accesible por usuarios con rol Cliente (4).
    """
    # Verificar permisos
    if current_user.rol_id not in [1, 4]:  # 1 = Admin, 4 = Cliente
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores y clientes pueden acceder a este endpoint"
        )

    desde = datetime.now() - timedelta(minutes=desde_minutos)

    # Obtener todas las notificaciones del cliente
    eventos = gestor_notificaciones.obtener_eventos_recientes(
        rol_id=4,  # Cliente
        usuario_id=current_user.usuario_id,
        desde=desde
    )

    return [
        EventoResponse(
            evento_id=e.evento_id,
            tipo=e.tipo,
            titulo=e.titulo,
            mensaje=e.mensaje,
            data=e.data,
            fecha_creacion=e.fecha_creacion
        )
        for e in eventos
    ]


@router.delete("/limpiar-antiguas")
def limpiar_notificaciones_antiguas(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Limpia notificaciones antiguas del sistema.

    Solo accesible por administradores.
    Se ejecuta automáticamente cada hora, pero puede ejecutarse manualmente.
    """
    # Verificar que sea admin
    if current_user.rol_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden limpiar notificaciones"
        )

    gestor_notificaciones.limpiar_eventos_antiguos()

    return {
        "message": "Notificaciones antiguas eliminadas exitosamente"
    }
