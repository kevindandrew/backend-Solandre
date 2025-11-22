from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.pedido import Pedido
from app.models.pedido_item import PedidoItem
from app.models.item_exclusion import ItemExclusion
from app.models.menu_dia import MenuDia
from app.models.usuario import Usuario
from app.models.ingrediente import Ingrediente
from app.models.zona_delivery import ZonaDelivery
from app.schemas.pedido import (
    CrearPedidoRequest,
    PedidoResponse,
    MisPedidosResponse,
    TrackPedidoResponse,
    PedidoDetalleResponse,
    ItemPedidoResponse,
    MenuDiaSimple
)
from app.utils.dependencies import get_current_user
from app.utils.token_generator import generar_token_unico
from app.models.enums import EstadoDelPedido
from app.utils.notificaciones import (
    notificar_nuevo_pedido,
    notificar_cambio_estado,
    notificar_delivery_asignado
)
from app.utils.logger import logger, log_error

router = APIRouter(
    prefix="/pedidos",
    tags=["Pedidos de Clientes"]
)


@router.post("/", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
def crear_pedido(
    request: CrearPedidoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Crea un nuevo pedido. El proceso incluye:
    1. Validar stock disponible
    2. Generar token único
    3. Calcular total del pedido
    4. Asignar delivery automáticamente
    5. Crear pedido y sus items
    6. Registrar exclusiones
    7. Actualizar stock
    """

    # 1. Validar zona
    zona = db.query(ZonaDelivery).filter(
        ZonaDelivery.zona_id == request.zona_id).first()
    if not zona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zona no encontrada"
        )

    # 2. Validar y calcular total
    total_pedido = 0
    items_validados = []

    for item in request.items:
        menu = db.query(MenuDia).filter(
            MenuDia.menu_dia_id == item.menu_dia_id).first()

        if not menu:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menú {item.menu_dia_id} no encontrado"
            )

        if not menu.publicado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El menú del {menu.fecha} no está publicado"
            )

        if menu.cantidad_disponible < item.cantidad:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente para el menú del {menu.fecha}. Disponible: {menu.cantidad_disponible}"
            )

        total_pedido += menu.precio_menu * item.cantidad
        items_validados.append((menu, item))

    # 3. Generar token único
    token = generar_token_unico(db)

    # 4. Buscar delivery disponible en la zona
    delivery = db.query(Usuario).filter(
        Usuario.rol_id == 3,  # Rol Delivery
        Usuario.zona_reparto_id == request.zona_id
    ).first()

    # 5. Crear el pedido
    nuevo_pedido = Pedido(
        usuario_id=current_user.usuario_id,
        zona_id=request.zona_id,
        google_maps_link=request.google_maps_link,
        latitud=request.latitud,
        longitud=request.longitud,
        direccion_referencia=request.direccion_referencia,
        token_recoger=token,
        total_pedido=total_pedido,
        metodo_pago=request.metodo_pago,
        delivery_asignado_id=delivery.usuario_id if delivery else None,
        fecha_pedido=datetime.now()
    )

    db.add(nuevo_pedido)
    db.flush()  # Para obtener el pedido_id

    # 6. Crear items del pedido y actualizar stock
    for menu, item_request in items_validados:
        # Crear item
        item = PedidoItem(
            pedido_id=nuevo_pedido.pedido_id,
            menu_dia_id=menu.menu_dia_id,
            cantidad=item_request.cantidad,
            precio_unitario=menu.precio_menu
        )
        db.add(item)
        db.flush()  # Para obtener el item_id

        # Registrar exclusiones
        for ingrediente_id in item_request.exclusiones:
            exclusion = ItemExclusion(
                item_id=item.item_id,
                ingrediente_id=ingrediente_id
            )
            db.add(exclusion)

        # Actualizar stock del menú
        menu.cantidad_disponible -= item_request.cantidad

    db.commit()
    db.refresh(nuevo_pedido)

    # 7. 🔔 CREAR NOTIFICACIONES
    notificar_nuevo_pedido(
        pedido_id=nuevo_pedido.pedido_id,
        token=token,
        cliente_nombre=current_user.nombre_completo,
        items_count=len(request.items),
        total=float(total_pedido)
    )

    # Si se asignó delivery, notificarle
    if delivery:
        notificar_delivery_asignado(
            pedido_id=nuevo_pedido.pedido_id,
            token=token,
            delivery_id=delivery.usuario_id,
            delivery_nombre=delivery.nombre_completo,
            direccion=request.direccion_referencia
        )

    return PedidoResponse.from_orm(nuevo_pedido)


@router.get("/mis-pedidos", response_model=List[MisPedidosResponse])
def obtener_mis_pedidos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene el historial de pedidos del usuario autenticado.
    """
    pedidos = db.query(
        Pedido,
        func.count(PedidoItem.item_id).label('items_count')
    ).join(
        PedidoItem, Pedido.pedido_id == PedidoItem.pedido_id
    ).filter(
        Pedido.usuario_id == current_user.usuario_id
    ).group_by(
        Pedido.pedido_id
    ).order_by(
        Pedido.fecha_pedido.desc()
    ).all()

    resultado = []
    for pedido, items_count in pedidos:
        resultado.append(MisPedidosResponse(
            pedido_id=pedido.pedido_id,
            token_recoger=pedido.token_recoger,
            estado=pedido.estado,
            total_pedido=pedido.total_pedido,
            metodo_pago=pedido.metodo_pago,
            esta_pagado=pedido.esta_pagado,
            fecha_pedido=pedido.fecha_pedido,
            fecha_entrega=pedido.fecha_entrega,
            items_count=items_count
        ))

    return resultado


@router.get("/{token}/track", response_model=TrackPedidoResponse)
def rastrear_pedido(token: str, db: Session = Depends(get_db)):
    """
    Rastrea el estado de un pedido usando su token único.
    No requiere autenticación (el token es suficiente).
    """
    pedido = db.query(Pedido).filter(Pedido.token_recoger == token).first()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Obtener nombre del delivery si está asignado
    nombre_delivery = None
    if pedido.delivery_asignado_id:
        delivery = db.query(Usuario).filter(
            Usuario.usuario_id == pedido.delivery_asignado_id
        ).first()
        if delivery:
            nombre_delivery = delivery.nombre_completo

    return TrackPedidoResponse(
        pedido_id=pedido.pedido_id,
        token_recoger=pedido.token_recoger,
        estado=pedido.estado,
        total_pedido=pedido.total_pedido,
        metodo_pago=pedido.metodo_pago,
        esta_pagado=pedido.esta_pagado,
        fecha_pedido=pedido.fecha_pedido,
        fecha_confirmado=pedido.fecha_confirmado,
        fecha_listo_cocina=pedido.fecha_listo_cocina,
        fecha_en_reparto=pedido.fecha_en_reparto,
        fecha_entrega=pedido.fecha_entrega,
        delivery_asignado_id=pedido.delivery_asignado_id,
        nombre_delivery=nombre_delivery
    )


@router.get("/{pedido_id}/detalle", response_model=PedidoDetalleResponse)
def obtener_detalle_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene el detalle completo de un pedido con sus items y exclusiones.
    Solo el usuario dueño del pedido puede ver el detalle.
    """
    pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar que el pedido pertenezca al usuario
    if pedido.usuario_id != current_user.usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este pedido"
        )

    # Obtener items del pedido
    items_pedido = db.query(PedidoItem).filter(
        PedidoItem.pedido_id == pedido_id
    ).all()

    items_response = []
    for item in items_pedido:
        # Obtener menú
        menu = db.query(MenuDia).filter(
            MenuDia.menu_dia_id == item.menu_dia_id
        ).first()

        # Obtener exclusiones
        exclusiones_ids = db.query(ItemExclusion).filter(
            ItemExclusion.item_id == item.item_id
        ).all()

        exclusiones_nombres = []
        for excl in exclusiones_ids:
            ingrediente = db.query(Ingrediente).filter(
                Ingrediente.ingrediente_id == excl.ingrediente_id
            ).first()
            if ingrediente:
                exclusiones_nombres.append(ingrediente.nombre)

        items_response.append(ItemPedidoResponse(
            item_id=item.item_id,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            menu=MenuDiaSimple.from_orm(menu) if menu else None,
            exclusiones=exclusiones_nombres
        ))

    return PedidoDetalleResponse(
        pedido_id=pedido.pedido_id,
        token_recoger=pedido.token_recoger,
        estado=pedido.estado,
        total_pedido=pedido.total_pedido,
        metodo_pago=pedido.metodo_pago,
        esta_pagado=pedido.esta_pagado,
        zona_id=pedido.zona_id,
        direccion_referencia=pedido.direccion_referencia,
        google_maps_link=pedido.google_maps_link,
        latitud=pedido.latitud,
        longitud=pedido.longitud,
        fecha_pedido=pedido.fecha_pedido,
        fecha_confirmado=pedido.fecha_confirmado,
        fecha_listo_cocina=pedido.fecha_listo_cocina,
        fecha_en_reparto=pedido.fecha_en_reparto,
        fecha_entrega=pedido.fecha_entrega,
        items=items_response
    )


@router.delete("/{pedido_id}")
def cancelar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Cancela un pedido.
    Solo se puede cancelar si está en estado PENDIENTE.
    Devuelve el stock al menú.
    """
    pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()

    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar que el pedido pertenezca al usuario
    if pedido.usuario_id != current_user.usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para cancelar este pedido"
        )

    # Solo se puede cancelar si está pendiente
    if pedido.estado != EstadoDelPedido.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede cancelar un pedido en estado '{pedido.estado.value}'. Solo pedidos PENDIENTES pueden ser cancelados."
        )

    # Devolver stock a los menús
    items_pedido = db.query(PedidoItem).filter(
        PedidoItem.pedido_id == pedido_id
    ).all()

    for item in items_pedido:
        menu = db.query(MenuDia).filter(
            MenuDia.menu_dia_id == item.menu_dia_id
        ).first()
        if menu:
            menu.cantidad_disponible += item.cantidad

    # Eliminar el pedido y sus items (cascada)
    db.delete(pedido)
    db.commit()

    return {"message": "Pedido cancelado exitosamente", "pedido_id": pedido_id}
