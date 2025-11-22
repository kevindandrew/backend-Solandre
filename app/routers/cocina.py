from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, date

from app.database import get_db
from app.models.pedido import Pedido
from app.models.pedido_item import PedidoItem
from app.models.item_exclusion import ItemExclusion
from app.models.menu_dia import MenuDia
from app.models.plato import Plato
from app.models.usuario import Usuario
from app.models.ingrediente import Ingrediente
from app.models.enums import EstadoDelPedido
from app.schemas.cocina import (
    PedidoCocinaResponse,
    ItemCocina,
    CambiarEstadoCocinaRequest,
    EstadisticasCocinaResponse
)
from app.utils.dependencies import get_current_user
from app.utils.notificaciones import (
    notificar_cambio_estado,
    notificar_pedido_listo
)

router = APIRouter(
    prefix="/cocina",
    tags=["Operaciones de Cocina"]
)


@router.get("/pendientes", response_model=List[PedidoCocinaResponse])
def obtener_pedidos_pendientes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos los pedidos que están en Confirmado o En Cocina.
    Muestra las exclusiones de ingredientes claramente para la cocina.
    Requiere rol de Cocina o Administrador.
    """
    # Verificar que el usuario tenga el rol adecuado
    if current_user.rol_id not in [1, 2]:  # 1=Admin, 2=Cocina
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a esta sección"
        )

    # Obtener pedidos pendientes
    pedidos = db.query(Pedido).filter(
        Pedido.estado.in_([EstadoDelPedido.CONFIRMADO,
                          EstadoDelPedido.EN_COCINA])
    ).order_by(Pedido.fecha_pedido.asc()).all()

    resultado = []

    for pedido in pedidos:
        # Obtener cliente
        cliente = db.query(Usuario).filter(
            Usuario.usuario_id == pedido.usuario_id
        ).first()

        # Obtener items del pedido
        items_pedido = db.query(PedidoItem).filter(
            PedidoItem.pedido_id == pedido.pedido_id
        ).all()

        items_cocina = []
        for item in items_pedido:
            # Obtener menú
            menu = db.query(MenuDia).filter(
                MenuDia.menu_dia_id == item.menu_dia_id
            ).first()

            if not menu:
                continue

            # Obtener platos del menú
            plato_principal = db.query(Plato).filter(
                Plato.plato_id == menu.plato_principal_id
            ).first()
            bebida = db.query(Plato).filter(
                Plato.plato_id == menu.bebida_id
            ).first()
            postre = db.query(Plato).filter(
                Plato.plato_id == menu.postre_id
            ).first()

            # Obtener exclusiones del item
            exclusiones_ids = db.query(ItemExclusion).filter(
                ItemExclusion.item_id == item.item_id
            ).all()

            exclusiones = []
            for excl in exclusiones_ids:
                ingrediente = db.query(Ingrediente).filter(
                    Ingrediente.ingrediente_id == excl.ingrediente_id
                ).first()
                if ingrediente:
                    exclusiones.append(f"Sin {ingrediente.nombre}")

            items_cocina.append(ItemCocina(
                item_id=item.item_id,
                cantidad=item.cantidad,
                menu_fecha=menu.fecha,
                plato_principal=plato_principal.nombre if plato_principal else "N/A",
                bebida=bebida.nombre if bebida else "N/A",
                postre=postre.nombre if postre else "N/A",
                exclusiones=exclusiones
            ))

        # Calcular minutos desde el pedido
        minutos_desde_pedido = None
        if pedido.fecha_pedido:
            delta = datetime.now() - pedido.fecha_pedido.replace(tzinfo=None)
            minutos_desde_pedido = int(delta.total_seconds() / 60)

        resultado.append(PedidoCocinaResponse(
            pedido_id=pedido.pedido_id,
            token_recoger=pedido.token_recoger,
            estado=pedido.estado,
            fecha_pedido=pedido.fecha_pedido,
            cliente_nombre=cliente.nombre_completo if cliente else "Desconocido",
            cliente_telefono=cliente.telefono if cliente else None,
            items=items_cocina,
            minutos_desde_pedido=minutos_desde_pedido
        ))

    return resultado


@router.patch("/pedidos/{pedido_id}/estado", response_model=PedidoCocinaResponse)
def cambiar_estado_pedido(
    pedido_id: int,
    request: CambiarEstadoCocinaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Cambia el estado de un pedido desde cocina.
    Estados permitidos: En Cocina, Listo para Entrega
    Actualiza automáticamente las fechas correspondientes.
    """
    # Verificar permisos
    if current_user.rol_id not in [1, 2]:  # 1=Admin, 2=Cocina
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción"
        )

    # Buscar pedido
    pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Validar transiciones de estado permitidas desde cocina
    estados_permitidos = [
        EstadoDelPedido.EN_COCINA,
        EstadoDelPedido.LISTO_PARA_ENTREGA
    ]

    if request.nuevo_estado not in estados_permitidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado no permitido desde cocina. Estados válidos: {[e.value for e in estados_permitidos]}"
        )

    # Actualizar estado y fechas
    pedido.estado = request.nuevo_estado

    if request.nuevo_estado == EstadoDelPedido.EN_COCINA and not pedido.fecha_listo_cocina:
        # Primer cambio a "En Cocina" (opcional, para tracking)
        pass

    if request.nuevo_estado == EstadoDelPedido.LISTO_PARA_ENTREGA:
        pedido.fecha_listo_cocina = datetime.now()

    db.commit()
    db.refresh(pedido)

    # 🔔 NOTIFICAR AL CLIENTE sobre cambio de estado
    cliente = db.query(Usuario).filter(
        Usuario.usuario_id == pedido.usuario_id).first()

    if cliente:
        notificar_cambio_estado(
            pedido_id=pedido.pedido_id,
            token=pedido.token_recoger,
            nuevo_estado=request.nuevo_estado.value,
            cliente_id=cliente.usuario_id,
            cliente_nombre=cliente.nombre_completo
        )

    # 🔔 Si está listo, notificar al delivery
    if request.nuevo_estado == EstadoDelPedido.LISTO_PARA_ENTREGA and pedido.delivery_asignado_id:
        delivery = db.query(Usuario).filter(
            Usuario.usuario_id == pedido.delivery_asignado_id
        ).first()

        if delivery:
            notificar_pedido_listo(
                pedido_id=pedido.pedido_id,
                token=pedido.token_recoger,
                delivery_id=delivery.usuario_id,
                delivery_nombre=delivery.nombre_completo
            )

    # Construir respuesta similar a la de pedidos pendientes
    items_pedido = db.query(PedidoItem).filter(
        PedidoItem.pedido_id == pedido.pedido_id).all()

    items_cocina = []
    for item in items_pedido:
        menu = db.query(MenuDia).filter(
            MenuDia.menu_dia_id == item.menu_dia_id).first()
        if not menu:
            continue

        plato_principal = db.query(Plato).filter(
            Plato.plato_id == menu.plato_principal_id).first()
        bebida = db.query(Plato).filter(
            Plato.plato_id == menu.bebida_id).first()
        postre = db.query(Plato).filter(
            Plato.plato_id == menu.postre_id).first()

        exclusiones_ids = db.query(ItemExclusion).filter(
            ItemExclusion.item_id == item.item_id).all()
        exclusiones = []
        for excl in exclusiones_ids:
            ingrediente = db.query(Ingrediente).filter(
                Ingrediente.ingrediente_id == excl.ingrediente_id).first()
            if ingrediente:
                exclusiones.append(f"Sin {ingrediente.nombre}")

        items_cocina.append(ItemCocina(
            item_id=item.item_id,
            cantidad=item.cantidad,
            menu_fecha=menu.fecha,
            plato_principal=plato_principal.nombre if plato_principal else "N/A",
            bebida=bebida.nombre if bebida else "N/A",
            postre=postre.nombre if postre else "N/A",
            exclusiones=exclusiones
        ))

    minutos_desde_pedido = None
    if pedido.fecha_pedido:
        delta = datetime.now() - pedido.fecha_pedido.replace(tzinfo=None)
        minutos_desde_pedido = int(delta.total_seconds() / 60)

    return PedidoCocinaResponse(
        pedido_id=pedido.pedido_id,
        token_recoger=pedido.token_recoger,
        estado=pedido.estado,
        fecha_pedido=pedido.fecha_pedido,
        cliente_nombre=cliente.nombre_completo if cliente else "Desconocido",
        cliente_telefono=cliente.telefono if cliente else None,
        items=items_cocina,
        minutos_desde_pedido=minutos_desde_pedido
    )


@router.get("/historial", response_model=List[PedidoCocinaResponse])
def obtener_historial_cocina(
    fecha: Optional[date] = Query(
        None, description="Fecha para filtrar (default: hoy)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene el historial de pedidos completados por cocina.
    Muestra pedidos que ya están listos para entrega o entregados.
    Útil para auditoría y revisión.
    """
    # Verificar permisos
    if current_user.rol_id not in [1, 2]:  # 1=Admin, 2=Cocina
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a esta sección"
        )

    # Si no se proporciona fecha, usar hoy
    if not fecha:
        fecha = date.today()

    # Obtener pedidos listos o entregados del día
    pedidos = db.query(Pedido).filter(
        func.date(Pedido.fecha_pedido) == fecha,
        Pedido.estado.in_([
            EstadoDelPedido.LISTO_PARA_ENTREGA,
            EstadoDelPedido.EN_REPARTO,
            EstadoDelPedido.ENTREGADO
        ])
    ).order_by(Pedido.fecha_listo_cocina.desc()).all()

    resultado = []

    for pedido in pedidos:
        cliente = db.query(Usuario).filter(
            Usuario.usuario_id == pedido.usuario_id
        ).first()

        items_pedido = db.query(PedidoItem).filter(
            PedidoItem.pedido_id == pedido.pedido_id
        ).all()

        items_cocina = []
        for item in items_pedido:
            menu = db.query(MenuDia).filter(
                MenuDia.menu_dia_id == item.menu_dia_id
            ).first()

            if not menu:
                continue

            plato_principal = db.query(Plato).filter(
                Plato.plato_id == menu.plato_principal_id
            ).first()
            bebida = db.query(Plato).filter(
                Plato.plato_id == menu.bebida_id
            ).first()
            postre = db.query(Plato).filter(
                Plato.plato_id == menu.postre_id
            ).first()

            exclusiones_ids = db.query(ItemExclusion).filter(
                ItemExclusion.item_id == item.item_id
            ).all()

            exclusiones = []
            for excl in exclusiones_ids:
                ingrediente = db.query(Ingrediente).filter(
                    Ingrediente.ingrediente_id == excl.ingrediente_id
                ).first()
                if ingrediente:
                    exclusiones.append(f"Sin {ingrediente.nombre}")

            items_cocina.append(ItemCocina(
                item_id=item.item_id,
                cantidad=item.cantidad,
                menu_fecha=menu.fecha,
                plato_principal=plato_principal.nombre if plato_principal else "N/A",
                bebida=bebida.nombre if bebida else "N/A",
                postre=postre.nombre if postre else "N/A",
                exclusiones=exclusiones
            ))

        minutos_desde_pedido = None
        if pedido.fecha_pedido:
            delta = datetime.now() - pedido.fecha_pedido.replace(tzinfo=None)
            minutos_desde_pedido = int(delta.total_seconds() / 60)

        resultado.append(PedidoCocinaResponse(
            pedido_id=pedido.pedido_id,
            token_recoger=pedido.token_recoger,
            estado=pedido.estado,
            fecha_pedido=pedido.fecha_pedido,
            cliente_nombre=cliente.nombre_completo if cliente else "Desconocido",
            cliente_telefono=cliente.telefono if cliente else None,
            items=items_cocina,
            minutos_desde_pedido=minutos_desde_pedido
        ))

    return resultado


@router.get("/estadisticas", response_model=EstadisticasCocinaResponse)
def obtener_estadisticas_cocina(
    fecha: Optional[date] = Query(
        None, description="Fecha para las estadísticas (default: hoy)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene estadísticas de rendimiento de cocina.
    Incluye tiempos promedio, pedidos procesados y velocidad.
    """
    # Verificar permisos
    if current_user.rol_id not in [1, 2]:  # 1=Admin, 2=Cocina
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a esta sección"
        )

    # Si no se proporciona fecha, usar hoy
    if not fecha:
        fecha = date.today()

    # Obtener pedidos del día
    pedidos_del_dia = db.query(Pedido).filter(
        func.date(Pedido.fecha_pedido) == fecha
    ).all()

    # Pedidos procesados (listos o más avanzados)
    pedidos_procesados = [
        p for p in pedidos_del_dia
        if p.estado in [
            EstadoDelPedido.LISTO_PARA_ENTREGA,
            EstadoDelPedido.EN_REPARTO,
            EstadoDelPedido.ENTREGADO
        ]
    ]

    # Pedidos en proceso
    pedidos_en_proceso = [
        p for p in pedidos_del_dia
        if p.estado in [EstadoDelPedido.CONFIRMADO, EstadoDelPedido.EN_COCINA]
    ]

    # Calcular tiempos de preparación
    tiempos_preparacion = []
    for p in pedidos_procesados:
        if p.fecha_listo_cocina and p.fecha_pedido:
            delta = p.fecha_listo_cocina.replace(
                tzinfo=None) - p.fecha_pedido.replace(tzinfo=None)
            minutos = delta.total_seconds() / 60
            tiempos_preparacion.append(minutos)

    tiempo_promedio = None
    pedido_mas_rapido = None
    pedido_mas_lento = None

    if tiempos_preparacion:
        tiempo_promedio = round(
            sum(tiempos_preparacion) / len(tiempos_preparacion), 1)
        pedido_mas_rapido = round(min(tiempos_preparacion), 1)
        pedido_mas_lento = round(max(tiempos_preparacion), 1)

    # Contar platos preparados
    platos_preparados = db.query(func.sum(PedidoItem.cantidad)).join(
        Pedido, PedidoItem.pedido_id == Pedido.pedido_id
    ).filter(
        func.date(Pedido.fecha_pedido) == fecha,
        Pedido.estado.in_([
            EstadoDelPedido.LISTO_PARA_ENTREGA,
            EstadoDelPedido.EN_REPARTO,
            EstadoDelPedido.ENTREGADO
        ])
    ).scalar() or 0

    return EstadisticasCocinaResponse(
        fecha=fecha,
        total_pedidos_procesados=len(pedidos_procesados),
        pedidos_en_proceso=len(pedidos_en_proceso),
        tiempo_promedio_preparacion=tiempo_promedio,
        pedido_mas_rapido=pedido_mas_rapido,
        pedido_mas_lento=pedido_mas_lento,
        platos_preparados=platos_preparados
    )
