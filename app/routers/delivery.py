from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from app.database import get_db
from app.models.pedido import Pedido
from app.models.pedido_item import PedidoItem
from app.models.usuario import Usuario
from app.models.zona_delivery import ZonaDelivery
from app.models.enums import EstadoDelPedido, MetodoPago
from app.schemas.delivery import (
    EntregaDeliveryResponse,
    FinalizarEntregaRequest,
    EstadisticasDeliveryResponse
)
from app.utils.dependencies import get_current_user
from app.utils.notificaciones import (
    notificar_cambio_estado,
    notificar_delivery_en_camino
)

router = APIRouter(
    prefix="/delivery",
    tags=["Operaciones de Delivery"]
)


@router.get("/mis-entregas", response_model=List[EntregaDeliveryResponse])
def obtener_mis_entregas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene los pedidos asignados al delivery autenticado.
    Muestra pedidos con estado: Listo para Entrega o En Reparto.
    Incluye link de Google Maps y toda la info necesaria para la entrega.
    """
    # Verificar que el usuario sea delivery
    if current_user.rol_id not in [1, 3]:  # 1 = Admin, 3 = Delivery
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores y deliveries pueden acceder a esta sección"
        )

    # Obtener pedidos asignados al delivery
    pedidos = db.query(Pedido).filter(
        Pedido.delivery_asignado_id == current_user.usuario_id,
        Pedido.estado.in_([
            EstadoDelPedido.LISTO_PARA_ENTREGA,
            EstadoDelPedido.EN_REPARTO
        ])
    ).order_by(Pedido.fecha_listo_cocina.asc()).all()

    resultado = []

    for pedido in pedidos:
        # Obtener cliente
        cliente = db.query(Usuario).filter(
            Usuario.usuario_id == pedido.usuario_id
        ).first()

        # Obtener zona
        zona = db.query(ZonaDelivery).filter(
            ZonaDelivery.zona_id == pedido.zona_id
        ).first()

        # Contar items
        cantidad_items = db.query(func.count(PedidoItem.item_id)).filter(
            PedidoItem.pedido_id == pedido.pedido_id
        ).scalar()

        # Calcular minutos desde que está listo
        minutos_desde_listo = None
        if pedido.fecha_listo_cocina:
            delta = datetime.now() - pedido.fecha_listo_cocina.replace(tzinfo=None)
            minutos_desde_listo = int(delta.total_seconds() / 60)

        resultado.append(EntregaDeliveryResponse(
            pedido_id=pedido.pedido_id,
            token_recoger=pedido.token_recoger,
            estado=pedido.estado,
            cliente_nombre=cliente.nombre_completo if cliente else "Desconocido",
            cliente_telefono=cliente.telefono if cliente else None,
            zona_nombre=zona.nombre_zona if zona else "N/A",
            direccion_referencia=pedido.direccion_referencia,
            google_maps_link=pedido.google_maps_link,
            latitud=pedido.latitud,
            longitud=pedido.longitud,
            total_pedido=pedido.total_pedido,
            metodo_pago=pedido.metodo_pago,
            esta_pagado=pedido.esta_pagado,
            cantidad_items=cantidad_items or 0,
            fecha_pedido=pedido.fecha_pedido,
            fecha_listo_cocina=pedido.fecha_listo_cocina,
            fecha_en_reparto=pedido.fecha_en_reparto,
            minutos_desde_listo=minutos_desde_listo
        ))

    return resultado


@router.patch("/pedidos/{pedido_id}/tomar", response_model=EntregaDeliveryResponse)
def tomar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Marca que el delivery ya recogió el paquete de cocina.
    Cambia el estado a "En Reparto" y actualiza fecha_en_reparto.
    """
    # Verificar que el usuario sea delivery o admin
    if current_user.rol_id not in [1, 3]:  # 1 = Admin, 3 = Delivery
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores y deliveries pueden entregar pedidos"
        )

    # Buscar pedido
    pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar que esté asignado a este delivery
    if pedido.delivery_asignado_id != current_user.usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este pedido no está asignado a ti"
        )

    # Verificar que esté en estado correcto
    if pedido.estado != EstadoDelPedido.LISTO_PARA_ENTREGA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El pedido debe estar en estado 'Listo para Entrega'. Estado actual: {pedido.estado.value}"
        )

    # Actualizar estado
    pedido.estado = EstadoDelPedido.EN_REPARTO
    pedido.fecha_en_reparto = datetime.now()

    db.commit()
    db.refresh(pedido)

    # 🔔 NOTIFICAR AL CLIENTE que el pedido va en camino
    notificar_delivery_en_camino(
        pedido_id=pedido.pedido_id,
        token=pedido.token_recoger,
        cliente_id=pedido.usuario_id,
        delivery_nombre=current_user.nombre_completo
    )

    notificar_cambio_estado(
        pedido_id=pedido.pedido_id,
        token=pedido.token_recoger,
        nuevo_estado="EN_REPARTO",
        cliente_id=pedido.usuario_id,
        cliente_nombre=""
    )

    # Construir respuesta
    cliente = db.query(Usuario).filter(
        Usuario.usuario_id == pedido.usuario_id).first()
    zona = db.query(ZonaDelivery).filter(
        ZonaDelivery.zona_id == pedido.zona_id).first()
    cantidad_items = db.query(func.count(PedidoItem.item_id)).filter(
        PedidoItem.pedido_id == pedido.pedido_id
    ).scalar()

    minutos_desde_listo = None
    if pedido.fecha_listo_cocina:
        delta = datetime.now() - pedido.fecha_listo_cocina.replace(tzinfo=None)
        minutos_desde_listo = int(delta.total_seconds() / 60)

    return EntregaDeliveryResponse(
        pedido_id=pedido.pedido_id,
        token_recoger=pedido.token_recoger,
        estado=pedido.estado,
        cliente_nombre=cliente.nombre_completo if cliente else "Desconocido",
        cliente_telefono=cliente.telefono if cliente else None,
        zona_nombre=zona.nombre_zona if zona else "N/A",
        direccion_referencia=pedido.direccion_referencia,
        google_maps_link=pedido.google_maps_link,
        latitud=pedido.latitud,
        longitud=pedido.longitud,
        total_pedido=pedido.total_pedido,
        metodo_pago=pedido.metodo_pago,
        esta_pagado=pedido.esta_pagado,
        cantidad_items=cantidad_items or 0,
        fecha_pedido=pedido.fecha_pedido,
        fecha_listo_cocina=pedido.fecha_listo_cocina,
        fecha_en_reparto=pedido.fecha_en_reparto,
        minutos_desde_listo=minutos_desde_listo
    )


@router.patch("/pedidos/{pedido_id}/finalizar", response_model=EntregaDeliveryResponse)
def finalizar_entrega(
    pedido_id: int,
    request: FinalizarEntregaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Marca el pedido como Entregado.
    Si el método de pago es Efectivo y confirmar_pago=True, marca esta_pagado=True.
    Actualiza fecha_entrega.
    """
    # Verificar que el usuario sea delivery
    if current_user.rol_id != 3:  # 3 = Delivery
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los delivery pueden realizar esta acción"
        )

    # Buscar pedido
    pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar que esté asignado a este delivery
    if pedido.delivery_asignado_id != current_user.usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este pedido no está asignado a ti"
        )

    # Verificar que esté en estado correcto
    if pedido.estado != EstadoDelPedido.EN_REPARTO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El pedido debe estar 'En Reparto'. Estado actual: {pedido.estado.value}"
        )

    # Actualizar estado
    pedido.estado = EstadoDelPedido.ENTREGADO
    pedido.fecha_entrega = datetime.now()

    # Si confirma pago (efectivo o QR verificado)
    if request.confirmar_pago:
        pedido.esta_pagado = True

    db.commit()
    db.refresh(pedido)

    # 🔔 NOTIFICAR AL CLIENTE que el pedido fue entregado
    notificar_cambio_estado(
        pedido_id=pedido.pedido_id,
        token=pedido.token_recoger,
        nuevo_estado="ENTREGADO",
        cliente_id=pedido.usuario_id,
        cliente_nombre=""
    )

    # Construir respuesta
    cliente = db.query(Usuario).filter(
        Usuario.usuario_id == pedido.usuario_id).first()
    zona = db.query(ZonaDelivery).filter(
        ZonaDelivery.zona_id == pedido.zona_id).first()
    cantidad_items = db.query(func.count(PedidoItem.item_id)).filter(
        PedidoItem.pedido_id == pedido.pedido_id
    ).scalar()

    minutos_desde_listo = None
    if pedido.fecha_listo_cocina:
        delta = datetime.now() - pedido.fecha_listo_cocina.replace(tzinfo=None)
        minutos_desde_listo = int(delta.total_seconds() / 60)

    return EntregaDeliveryResponse(
        pedido_id=pedido.pedido_id,
        token_recoger=pedido.token_recoger,
        estado=pedido.estado,
        cliente_nombre=cliente.nombre_completo if cliente else "Desconocido",
        cliente_telefono=cliente.telefono if cliente else None,
        zona_nombre=zona.nombre_zona if zona else "N/A",
        direccion_referencia=pedido.direccion_referencia,
        google_maps_link=pedido.google_maps_link,
        latitud=pedido.latitud,
        longitud=pedido.longitud,
        total_pedido=pedido.total_pedido,
        metodo_pago=pedido.metodo_pago,
        esta_pagado=pedido.esta_pagado,
        cantidad_items=cantidad_items or 0,
        fecha_pedido=pedido.fecha_pedido,
        fecha_listo_cocina=pedido.fecha_listo_cocina,
        fecha_en_reparto=pedido.fecha_en_reparto,
        minutos_desde_listo=minutos_desde_listo
    )
