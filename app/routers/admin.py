from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, date

from app.database import get_db
from app.models.usuario import Usuario
from app.models.menu_dia import MenuDia
from app.models.plato import Plato
from app.models.ingrediente import Ingrediente
from app.models.plato_ingrediente import PlatoIngrediente
from app.models.role import Role
from app.models.zona_delivery import ZonaDelivery
from app.models.pedido import Pedido
from app.models.enums import EstadoDelPedido
from app.schemas.admin import (
    CrearMenuRequest,
    ActualizarMenuRequest,
    MenuResponse,
    CrearPlatoRequest,
    PlatoResponse,
    CrearIngredienteRequest,
    IngredienteResponse,
    CrearEmpleadoRequest,
    AsignarZonaRequest,
    EmpleadoResponse,
    PedidoDashboardResponse,
    ReasignarDeliveryRequest,
    KPIsResponse,
    CrearZonaRequest,
    ActualizarZonaRequest,
    ZonaResponse,
    ClienteResponse,
    ActualizarEstadoPedidoRequest,
    PlatoDetalleResponse,
    IngredienteEnPlatoResponse
)
from app.utils.dependencies import get_current_user
from app.utils.security import get_password_hash

router = APIRouter(
    prefix="/admin",
    tags=["Administración"]
)
def verificar_admin(current_user: Usuario):
    """Verifica que el usuario sea administrador"""
    if current_user.rol_id != 1:  # 1 = Administrador
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden acceder a esta sección"
        )


# ========== GESTIÓN DE MENÚS DEL DÍA ==========

@router.post("/menu", response_model=MenuResponse, status_code=status.HTTP_201_CREATED)
def crear_menu_dia(
    request: CrearMenuRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Crea la oferta del menú para un día específico.
    Define qué plato se ofrecerá, su stock y precios.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Verificar que los 3 platos existen
    plato_principal = db.query(Plato).filter(
        Plato.plato_id == request.plato_principal_id).first()
    
    if not plato_principal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plato principal no encontrado"
        )

    # Validar bebida si se proporciona
    if request.bebida_id:
        bebida = db.query(Plato).filter(
            Plato.plato_id == request.bebida_id).first()
        if not bebida:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bebida no encontrada"
            )

    # Validar postre si se proporciona
    if request.postre_id:
        postre = db.query(Plato).filter(
            Plato.plato_id == request.postre_id).first()
        if not postre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Postre no encontrado"
            )

    # Verificar que no exista ya un menú para esa fecha
    menu_existente = db.query(MenuDia).filter(
        MenuDia.fecha == request.fecha
    ).first()

    if menu_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un menú para la fecha {request.fecha}"
        )

    # Crear el menú
    nuevo_menu = MenuDia(
        fecha=request.fecha,
        plato_principal_id=request.plato_principal_id,
        bebida_id=request.bebida_id,
        postre_id=request.postre_id,
        info_nutricional=request.info_nutricional,
        cantidad_disponible=request.cantidad_disponible,
        precio_menu=request.precio_menu,
        imagen_url=request.imagen_url,
        publicado=request.publicado
    )

    db.add(nuevo_menu)
    db.commit()
    db.refresh(nuevo_menu)

    return MenuResponse.from_orm(nuevo_menu)


@router.put("/menu/{menu_id}", response_model=MenuResponse)
def actualizar_menu_dia(
    menu_id: int,
    request: ActualizarMenuRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualiza stock, precio o visibilidad de un menú existente.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar el menú
    menu = db.query(MenuDia).filter(MenuDia.menu_dia_id == menu_id).first()
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menú no encontrado"
        )

    # Actualizar campos si se proporcionan
    if request.cantidad_disponible is not None:
        menu.cantidad_disponible = request.cantidad_disponible

    if request.precio_menu is not None:
        menu.precio_menu = request.precio_menu

    if request.imagen_url is not None:
        menu.imagen_url = request.imagen_url

    if request.publicado is not None:
        menu.publicado = request.publicado

    db.commit()
    db.refresh(menu)

    return MenuResponse.from_orm(menu)


@router.get("/menu", response_model=List[MenuResponse])
def listar_menus(
    fecha_inicio: Optional[date] = Query(
        None, description="Fecha inicio del filtro"),
    fecha_fin: Optional[date] = Query(
        None, description="Fecha fin del filtro"),
    publicado: Optional[bool] = Query(
        None, description="Filtrar por publicado"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos los menús con filtros opcionales.
    Permite filtrar por rango de fechas y estado de publicación.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Construir query base
    query = db.query(MenuDia)

    # Aplicar filtros
    if fecha_inicio:
        query = query.filter(MenuDia.fecha >= fecha_inicio)

    if fecha_fin:
        query = query.filter(MenuDia.fecha <= fecha_fin)

    if publicado is not None:
        query = query.filter(MenuDia.publicado == publicado)

    # Ordenar por fecha
    menus = query.order_by(MenuDia.fecha.desc()).all()

    return [MenuResponse.from_orm(menu) for menu in menus]


@router.delete("/menu/{menu_id}")
def eliminar_menu(
    menu_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Elimina un menú si no tiene pedidos asociados.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar el menú
    menu = db.query(MenuDia).filter(MenuDia.menu_dia_id == menu_id).first()
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menú no encontrado"
        )

    # Verificar si tiene pedidos asociados
    from app.models.pedido_item import PedidoItem
    tiene_pedidos = db.query(PedidoItem).filter(
        PedidoItem.menu_dia_id == menu_id
    ).first()

    if tiene_pedidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un menú que tiene pedidos asociados"
        )

    # Eliminar
    db.delete(menu)
    db.commit()

    return {"message": "Menú eliminado exitosamente", "menu_dia_id": menu_id}


# ========== GESTIÓN DE PLATOS ==========

@router.post("/platos", response_model=PlatoResponse, status_code=status.HTTP_201_CREATED)
def crear_plato(
    request: CrearPlatoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Crea un nuevo plato en el catálogo.
    Opcionalmente puede incluir la lista de ingredientes que lo componen.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Verificar que no exista un plato con el mismo nombre
    plato_existente = db.query(Plato).filter(
        Plato.nombre == request.nombre).first()
    if plato_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un plato con el nombre '{request.nombre}'"
        )

    # Validar que los ingredientes existan
    if request.ingredientes:
        for ing_req in request.ingredientes:
            ingrediente = db.query(Ingrediente).filter(
                Ingrediente.ingrediente_id == ing_req.ingrediente_id
            ).first()
            if not ingrediente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ingrediente con ID {ing_req.ingrediente_id} no encontrado"
                )

    # Crear el plato
    nuevo_plato = Plato(
        nombre=request.nombre,
        descripcion=request.descripcion,
        imagen_url=request.imagen_url,
        tipo=request.tipo
    )
    db.add(nuevo_plato)
    db.commit()
    db.refresh(nuevo_plato)

    # Crear relaciones con ingredientes
    for ing_req in request.ingredientes:
        plato_ingrediente = PlatoIngrediente(
            plato_id=nuevo_plato.plato_id,
            ingrediente_id=ing_req.ingrediente_id
        )
        db.add(plato_ingrediente)

    db.commit()
    db.refresh(nuevo_plato)

    return PlatoResponse.from_orm(nuevo_plato)


@router.get("/platos", response_model=List[PlatoResponse])
def listar_platos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos los platos del catálogo.
    Solo administradores.
    """
    verificar_admin(current_user)

    platos = db.query(Plato).all()
    platos = db.query(Plato).all()
    return [PlatoResponse.from_orm(p) for p in platos]


@router.get("/platos/{plato_id}", response_model=PlatoDetalleResponse)
def obtener_plato(
    plato_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene el detalle completo de un plato, incluyendo ingredientes y cantidades.
    Solo administradores.
    """
    verificar_admin(current_user)

    plato = db.query(Plato).filter(Plato.plato_id == plato_id).first()
    if not plato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plato no encontrado"
        )

    # Obtener ingredientes con sus cantidades
    ingredientes_response = []
    plato_ingredientes = db.query(PlatoIngrediente).filter(
        PlatoIngrediente.plato_id == plato_id
    ).all()

    for pi in plato_ingredientes:
        ingrediente = db.query(Ingrediente).filter(
            Ingrediente.ingrediente_id == pi.ingrediente_id
        ).first()
        
        if ingrediente:
            ingredientes_response.append(IngredienteEnPlatoResponse(
                ingrediente_id=ingrediente.ingrediente_id,
                nombre=ingrediente.nombre
            ))

    return PlatoDetalleResponse(
        plato_id=plato.plato_id,
        nombre=plato.nombre,
        imagen_url=plato.imagen_url,
        descripcion=plato.descripcion,
        tipo=plato.tipo,
        ingredientes=ingredientes_response
    )


@router.put("/platos/{plato_id}", response_model=PlatoResponse)
def actualizar_plato(
    plato_id: int,
    request: CrearPlatoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualiza un plato existente.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar el plato
    plato = db.query(Plato).filter(Plato.plato_id == plato_id).first()
    if not plato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plato no encontrado"
        )

    # Actualizar campos
    plato.nombre = request.nombre
    plato.descripcion = request.descripcion
    plato.imagen_url = request.imagen_url
    plato.tipo = request.tipo

    # Actualizar ingredientes (eliminar los actuales y agregar los nuevos)
    if request.ingredientes:
        # Eliminar relaciones actuales
        db.query(PlatoIngrediente).filter(
            PlatoIngrediente.plato_id == plato_id
        ).delete()

        # Agregar nuevas relaciones
        for ing_req in request.ingredientes:
            plato_ingrediente = PlatoIngrediente(
                plato_id=plato_id,
                ingrediente_id=ing_req.ingrediente_id
            )
            db.add(plato_ingrediente)

    db.commit()
    db.refresh(plato)

    return PlatoResponse.from_orm(plato)


@router.delete("/platos/{plato_id}")
def eliminar_plato(
    plato_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Elimina un plato si no está en menús activos.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar el plato
    plato = db.query(Plato).filter(Plato.plato_id == plato_id).first()
    if not plato:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plato no encontrado"
        )

    # Verificar si está en menús activos (publicados o futuros)
    menu_activo = db.query(MenuDia).filter(
        MenuDia.plato_id == plato_id,
        MenuDia.publicado == True
    ).first()

    if menu_activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un plato que está en menús publicados"
        )

    # Eliminar
    db.delete(plato)
    db.commit()

    return {"message": "Plato eliminado exitosamente", "plato_id": plato_id}


# ========== GESTIÓN DE INGREDIENTES ==========

@router.post("/ingredientes", response_model=IngredienteResponse, status_code=status.HTTP_201_CREATED)
def crear_ingrediente(
    request: CrearIngredienteRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Crea un nuevo ingrediente en el sistema.
    Define nombre, unidad de medida y stock inicial.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Verificar que no exista un ingrediente con el mismo nombre
    ingrediente_existente = db.query(Ingrediente).filter(
        Ingrediente.nombre == request.nombre
    ).first()

    if ingrediente_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un ingrediente con el nombre '{request.nombre}'"
        )

    # Crear el ingrediente
    nuevo_ingrediente = Ingrediente(
        nombre=request.nombre,
        stock_actual=request.stock_actual
    )

    db.add(nuevo_ingrediente)
    db.commit()
    db.refresh(nuevo_ingrediente)

    return IngredienteResponse.from_orm(nuevo_ingrediente)


@router.get("/ingredientes", response_model=List[IngredienteResponse])
def listar_ingredientes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos los ingredientes con su stock.
    Solo administradores.
    """
    verificar_admin(current_user)

    ingredientes = db.query(Ingrediente).all()
    return [IngredienteResponse.from_orm(i) for i in ingredientes]


@router.get("/ingredientes/{ingrediente_id}", response_model=IngredienteResponse)
def obtener_ingrediente(
    ingrediente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene los detalles de un ingrediente específico.
    Solo administradores.
    """
    verificar_admin(current_user)

    ingrediente = db.query(Ingrediente).filter(
        Ingrediente.ingrediente_id == ingrediente_id
    ).first()

    if not ingrediente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingrediente no encontrado"
        )

    return IngredienteResponse.from_orm(ingrediente)


@router.put("/ingredientes/{ingrediente_id}", response_model=IngredienteResponse)
def actualizar_ingrediente(
    ingrediente_id: int,
    request: CrearIngredienteRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualiza un ingrediente existente.
    Permite actualizar stock, stock mínimo y unidad de medida.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar el ingrediente
    ingrediente = db.query(Ingrediente).filter(
        Ingrediente.ingrediente_id == ingrediente_id
    ).first()

    if not ingrediente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingrediente no encontrado"
        )

    # Actualizar campos
    ingrediente.nombre = request.nombre
    ingrediente.stock_actual = request.stock_actual

    db.commit()
    db.refresh(ingrediente)

    return IngredienteResponse.from_orm(ingrediente)





# ========== GESTIÓN DE PERSONAL ==========

@router.post("/empleados", response_model=EmpleadoResponse, status_code=status.HTTP_201_CREATED)
def crear_empleado(
    request: CrearEmpleadoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Crea un nuevo empleado con rol Cocina o Delivery.
    Si es Delivery, opcionalmente se puede asignar zona.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Validar que el rol sea Admin (1), Cocina (2) o Delivery (3)
    # No se permite crear clientes (4) desde este endpoint
    if request.rol_id not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden crear empleados con rol Admin (1), Cocina (2) o Delivery (3)"
        )

    # Verificar que el rol existe
    rol = db.query(Role).filter(Role.rol_id == request.rol_id).first()
    if not rol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )

    # Verificar que el email no esté en uso
    usuario_existente = db.query(Usuario).filter(
        Usuario.email == request.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un usuario con el email '{request.email}'"
        )

    # Si es Delivery y se proporciona zona, validar que exista
    zona_nombre = None
    if request.zona_reparto_id:
        if request.rol_id != 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo los Delivery pueden tener zona de reparto asignada"
            )
        zona = db.query(ZonaDelivery).filter(
            ZonaDelivery.zona_id == request.zona_reparto_id
        ).first()
        if not zona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Zona de delivery no encontrada"
            )
        zona_nombre = zona.nombre_zona

    # Crear el empleado
    nuevo_empleado = Usuario(
        email=request.email,
        password_hash=get_password_hash(request.password),
        nombre_completo=request.nombre_completo,
        telefono=request.telefono,
        rol_id=request.rol_id,
        zona_reparto_id=request.zona_reparto_id
    )

    db.add(nuevo_empleado)
    db.commit()
    db.refresh(nuevo_empleado)

    return EmpleadoResponse(
        usuario_id=nuevo_empleado.usuario_id,
        email=nuevo_empleado.email,
        nombre_completo=nuevo_empleado.nombre_completo,
        telefono=nuevo_empleado.telefono,
        rol_id=nuevo_empleado.rol_id,
        rol_nombre=rol.nombre_rol,
        zona_reparto_id=nuevo_empleado.zona_reparto_id,
        zona_nombre=zona_nombre
    )


@router.patch("/empleados/{empleado_id}/zona", response_model=EmpleadoResponse)
def asignar_zona_delivery(
    empleado_id: int,
    request: AsignarZonaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Asigna una zona de reparto a un delivery.
    Permite reasignar deliveries a diferentes zonas (ej: Marcos a Miraflores).
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar el empleado
    empleado = db.query(Usuario).filter(
        Usuario.usuario_id == empleado_id).first()
    if not empleado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )

    # Verificar que sea delivery
    if empleado.rol_id != 3:  # 3 = Delivery
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede asignar zona a empleados con rol Delivery"
        )

    # Validar que la zona existe
    zona = db.query(ZonaDelivery).filter(
        ZonaDelivery.zona_id == request.zona_reparto_id
    ).first()
    if not zona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zona de delivery no encontrada"
        )

    # Asignar zona
    empleado.zona_reparto_id = request.zona_reparto_id
    db.commit()
    db.refresh(empleado)

    # Obtener rol
    rol = db.query(Role).filter(Role.rol_id == empleado.rol_id).first()

    return EmpleadoResponse(
        usuario_id=empleado.usuario_id,
        email=empleado.email,
        nombre_completo=empleado.nombre_completo,
        telefono=empleado.telefono,
        rol_id=empleado.rol_id,
        rol_nombre=rol.nombre_rol if rol else "Desconocido",
        zona_reparto_id=empleado.zona_reparto_id,
        zona_nombre=zona.nombre_zona
    )


@router.get("/empleados", response_model=List[EmpleadoResponse])
def listar_empleados(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos los empleados (Cocina y Delivery) con sus zonas asignadas.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Obtener empleados con rol Admin (1), Cocina (2) o Delivery (3)
    empleados = db.query(Usuario).filter(
        Usuario.rol_id.in_([1, 2, 3])
    ).all()

    resultado = []
    for empleado in empleados:
        # Obtener rol
        rol = db.query(Role).filter(Role.rol_id == empleado.rol_id).first()

        # Obtener zona si tiene
        zona_nombre = None
        if empleado.zona_reparto_id:
            zona = db.query(ZonaDelivery).filter(
                ZonaDelivery.zona_id == empleado.zona_reparto_id
            ).first()
            if zona:
                zona_nombre = zona.nombre_zona

        resultado.append(EmpleadoResponse(
            usuario_id=empleado.usuario_id,
            email=empleado.email,
            nombre_completo=empleado.nombre_completo,
            telefono=empleado.telefono,
            rol_id=empleado.rol_id,
            rol_nombre=rol.nombre_rol if rol else "Desconocido",
            zona_reparto_id=empleado.zona_reparto_id,
            zona_nombre=zona_nombre
        ))

    return resultado


@router.put("/empleados/{empleado_id}", response_model=EmpleadoResponse)
def actualizar_empleado(
    empleado_id: int,
    request: CrearEmpleadoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualiza datos de un empleado.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar empleado
    empleado = db.query(Usuario).filter(
        Usuario.usuario_id == empleado_id).first()
    if not empleado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )

    # Verificar que sea empleado (rol 2 o 3)
    if empleado.rol_id not in [2, 3]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden actualizar empleados con rol Cocina o Delivery"
        )

    # Actualizar campos
    empleado.email = request.email
    empleado.nombre_completo = request.nombre_completo
    empleado.telefono = request.telefono
    empleado.rol_id = request.rol_id
    empleado.zona_reparto_id = request.zona_reparto_id

    # Si cambió la contraseña
    if request.password:
        from app.utils.security import get_password_hash
        empleado.password_hash = get_password_hash(request.password)

    db.commit()
    db.refresh(empleado)

    # Obtener rol y zona
    rol = db.query(Role).filter(Role.rol_id == empleado.rol_id).first()
    zona_nombre = None
    if empleado.zona_reparto_id:
        zona = db.query(ZonaDelivery).filter(
            ZonaDelivery.zona_id == empleado.zona_reparto_id
        ).first()
        if zona:
            zona_nombre = zona.nombre_zona

    return EmpleadoResponse(
        usuario_id=empleado.usuario_id,
        email=empleado.email,
        nombre_completo=empleado.nombre_completo,
        telefono=empleado.telefono,
        rol_id=empleado.rol_id,
        rol_nombre=rol.nombre_rol if rol else "Desconocido",
        zona_reparto_id=empleado.zona_reparto_id,
        zona_nombre=zona_nombre
    )


@router.delete("/empleados/{empleado_id}")
def desactivar_empleado(
    empleado_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Desactiva (elimina) un empleado.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar empleado
    empleado = db.query(Usuario).filter(
        Usuario.usuario_id == empleado_id).first()
    if not empleado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )

    # Verificar que no se esté eliminando a sí mismo
    if empleado_id == current_user.usuario_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta"
        )

    # Verificar que sea empleado (rol 1, 2 o 3)
    if empleado.rol_id not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden desactivar empleados (Admin, Cocina, Delivery)"
        )

    # Verificar si tiene pedidos asignados activos (solo para delivery)
    if empleado.rol_id == 3:
        pedidos_activos = db.query(Pedido).filter(
            Pedido.delivery_asignado_id == empleado_id,
            Pedido.estado.in_([
                EstadoDelPedido.CONFIRMADO,
                EstadoDelPedido.EN_COCINA,
                EstadoDelPedido.LISTO_PARA_ENTREGA,
                EstadoDelPedido.EN_REPARTO
            ])
        ).first()

        if pedidos_activos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede desactivar un delivery con pedidos activos asignados"
            )

    # Eliminar
    db.delete(empleado)
    db.commit()

    return {"message": "Empleado desactivado exitosamente", "usuario_id": empleado_id}


@router.get("/clientes", response_model=List[ClienteResponse])
def listar_clientes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos los clientes registrados (Rol 4).
    Solo administradores.
    """
    verificar_admin(current_user)

    clientes = db.query(Usuario).filter(Usuario.rol_id == 4).all()
    return [ClienteResponse.from_orm(c) for c in clientes]


@router.get("/clientes/{cliente_id}/historial", response_model=List[PedidoDashboardResponse])
def historial_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene el historial de pedidos de un cliente específico.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Verificar que el cliente existe
    cliente = db.query(Usuario).filter(Usuario.usuario_id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )

    # Obtener pedidos del cliente
    pedidos = db.query(Pedido).filter(
        Pedido.usuario_id == cliente_id
    ).order_by(Pedido.fecha_pedido.desc()).all()

    resultado = []
    for pedido in pedidos:
        # Obtener zona
        zona = db.query(ZonaDelivery).filter(
            ZonaDelivery.zona_id == pedido.zona_id).first()

        # Obtener delivery si está asignado
        delivery_nombre = None
        if pedido.delivery_asignado_id:
            delivery = db.query(Usuario).filter(
                Usuario.usuario_id == pedido.delivery_asignado_id
            ).first()
            if delivery:
                delivery_nombre = delivery.nombre_completo

        resultado.append(PedidoDashboardResponse(
            pedido_id=pedido.pedido_id,
            token_recoger=pedido.token_recoger,
            estado=pedido.estado,
            cliente_nombre=cliente.nombre_completo,
            cliente_email=cliente.email,
            zona_nombre=zona.nombre_zona if zona else "N/A",
            delivery_nombre=delivery_nombre,
            total_pedido=pedido.total_pedido,
            fecha_pedido=pedido.fecha_pedido,
            fecha_confirmado=pedido.fecha_confirmado,
            fecha_listo_cocina=pedido.fecha_listo_cocina,
            fecha_en_reparto=pedido.fecha_en_reparto,
            fecha_entrega=pedido.fecha_entrega
        ))

    return resultado


# ========== GESTIÓN DE PEDIDOS Y MÉTRICAS ==========

@router.get("/pedidos", response_model=List[PedidoDashboardResponse])
def obtener_dashboard_pedidos(
    fecha_inicio: Optional[date] = Query(
        None, description="Fecha inicio del filtro"),
    fecha_fin: Optional[date] = Query(
        None, description="Fecha fin del filtro"),
    estado: Optional[EstadoDelPedido] = Query(
        None, description="Filtrar por estado"),
    zona_id: Optional[int] = Query(None, description="Filtrar por zona"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Dashboard global de pedidos con filtros.
    Permite filtrar por fecha, estado y zona.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Construir query base
    query = db.query(Pedido)

    # Aplicar filtros
    if fecha_inicio:
        query = query.filter(func.date(Pedido.fecha_pedido) >= fecha_inicio)

    if fecha_fin:
        query = query.filter(func.date(Pedido.fecha_pedido) <= fecha_fin)

    if estado:
        query = query.filter(Pedido.estado == estado)

    if zona_id:
        query = query.filter(Pedido.zona_id == zona_id)

    # Ordenar por fecha descendente
    pedidos = query.order_by(Pedido.fecha_pedido.desc()).all()

    resultado = []
    for pedido in pedidos:
        # Obtener cliente
        cliente = db.query(Usuario).filter(
            Usuario.usuario_id == pedido.usuario_id).first()

        # Obtener zona
        zona = db.query(ZonaDelivery).filter(
            ZonaDelivery.zona_id == pedido.zona_id).first()

        # Obtener delivery si está asignado
        delivery_nombre = None
        if pedido.delivery_asignado_id:
            delivery = db.query(Usuario).filter(
                Usuario.usuario_id == pedido.delivery_asignado_id
            ).first()
            if delivery:
                delivery_nombre = delivery.nombre_completo

        resultado.append(PedidoDashboardResponse(
            pedido_id=pedido.pedido_id,
            token_recoger=pedido.token_recoger,
            estado=pedido.estado,
            cliente_nombre=cliente.nombre_completo if cliente else "Desconocido",
            cliente_email=cliente.email if cliente else "N/A",
            zona_nombre=zona.nombre_zona if zona else "N/A",
            delivery_nombre=delivery_nombre,
            total_pedido=pedido.total_pedido,
            fecha_pedido=pedido.fecha_pedido,
            fecha_confirmado=pedido.fecha_confirmado,
            fecha_listo_cocina=pedido.fecha_listo_cocina,
            fecha_en_reparto=pedido.fecha_en_reparto,
            fecha_entrega=pedido.fecha_entrega
        ))

    return resultado


@router.patch("/pedidos/{pedido_id}/confirmar", response_model=PedidoDashboardResponse)
def confirmar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Valida y confirma un pedido.
    Cambia el estado a 'Confirmado' y actualiza fecha_confirmado.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar el pedido
    pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar que esté en estado Pendiente
    if pedido.estado != EstadoDelPedido.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El pedido debe estar en estado 'Pendiente'. Estado actual: {pedido.estado.value}"
        )

    # Actualizar estado
    pedido.estado = EstadoDelPedido.CONFIRMADO
    pedido.fecha_confirmado = datetime.now()

    db.commit()
    db.refresh(pedido)

    # Construir respuesta
    cliente = db.query(Usuario).filter(
        Usuario.usuario_id == pedido.usuario_id).first()
    zona = db.query(ZonaDelivery).filter(
        ZonaDelivery.zona_id == pedido.zona_id).first()

    delivery_nombre = None
    if pedido.delivery_asignado_id:
        delivery = db.query(Usuario).filter(
            Usuario.usuario_id == pedido.delivery_asignado_id
        ).first()
        if delivery:
            delivery_nombre = delivery.nombre_completo

    return PedidoDashboardResponse(
        pedido_id=pedido.pedido_id,
        token_recoger=pedido.token_recoger,
        estado=pedido.estado,
        cliente_nombre=cliente.nombre_completo if cliente else "Desconocido",
        cliente_email=cliente.email if cliente else "N/A",
        zona_nombre=zona.nombre_zona if zona else "N/A",
        delivery_nombre=delivery_nombre,
        total_pedido=pedido.total_pedido,
        fecha_pedido=pedido.fecha_pedido,
        fecha_confirmado=pedido.fecha_confirmado,
        fecha_listo_cocina=pedido.fecha_listo_cocina,
        fecha_en_reparto=pedido.fecha_en_reparto,
        fecha_entrega=pedido.fecha_entrega
    )


@router.patch("/pedidos/{pedido_id}/reasignar", response_model=PedidoDashboardResponse)
def reasignar_delivery(
    pedido_id: int,
    request: ReasignarDeliveryRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Reasigna un pedido a otro delivery.
    Caso de emergencia: si Marcos se enferma, asignar a otro delivery.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar el pedido
    pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar que el nuevo delivery existe y es delivery
    nuevo_delivery = db.query(Usuario).filter(
        Usuario.usuario_id == request.nuevo_delivery_id
    ).first()

    if not nuevo_delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery no encontrado"
        )

    if nuevo_delivery.rol_id != 3:  # 3 = Delivery
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario seleccionado no es un delivery"
        )

    # Verificar que el delivery tenga asignada la misma zona del pedido
    if nuevo_delivery.zona_reparto_id != pedido.zona_id:
        # Advertencia pero permitir reasignación (caso de emergencia)
        pass

    # Reasignar
    pedido.delivery_asignado_id = request.nuevo_delivery_id

    db.commit()
    db.refresh(pedido)

    # Construir respuesta
    cliente = db.query(Usuario).filter(
        Usuario.usuario_id == pedido.usuario_id).first()
    zona = db.query(ZonaDelivery).filter(
        ZonaDelivery.zona_id == pedido.zona_id).first()

    return PedidoDashboardResponse(
        pedido_id=pedido.pedido_id,
        token_recoger=pedido.token_recoger,
        estado=pedido.estado,
        cliente_nombre=cliente.nombre_completo if cliente else "Desconocido",
        cliente_email=cliente.email if cliente else "N/A",
        zona_nombre=zona.nombre_zona if zona else "N/A",
        delivery_nombre=nuevo_delivery.nombre_completo,
        total_pedido=pedido.total_pedido,
        fecha_pedido=pedido.fecha_pedido,
        fecha_confirmado=pedido.fecha_confirmado,
        fecha_listo_cocina=pedido.fecha_listo_cocina,
        fecha_en_reparto=pedido.fecha_en_reparto,
        fecha_entrega=pedido.fecha_entrega
    )


@router.patch("/pedidos/{pedido_id}/estado", response_model=PedidoDashboardResponse)
def actualizar_estado_pedido(
    pedido_id: int,
    request: ActualizarEstadoPedidoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualiza manualmente el estado de un pedido.
    Actualiza también la fecha correspondiente al nuevo estado.
    Si se cancela, restaura el stock.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar el pedido
    pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    nuevo_estado = request.estado
    ahora = datetime.now()

    # Si el estado es el mismo, no hacer nada
    if pedido.estado == nuevo_estado:
        pass # Solo devolver el pedido actual

    # Si se cancela, restaurar stock (si no estaba ya cancelado)
    elif nuevo_estado == EstadoDelPedido.CANCELADO:
        if pedido.estado != EstadoDelPedido.CANCELADO:
            from app.models.pedido_item import PedidoItem
            items = db.query(PedidoItem).filter(
                PedidoItem.pedido_id == pedido_id).all()

            for item in items:
                menu = db.query(MenuDia).filter(
                    MenuDia.menu_dia_id == item.menu_dia_id).first()
                if menu:
                    menu.cantidad_disponible += item.cantidad
    
    # Actualizar fechas según el estado
    if nuevo_estado == EstadoDelPedido.CONFIRMADO:
        pedido.fecha_confirmado = ahora
    elif nuevo_estado == EstadoDelPedido.LISTO_PARA_ENTREGA:
        pedido.fecha_listo_cocina = ahora
    elif nuevo_estado == EstadoDelPedido.EN_REPARTO:
        pedido.fecha_en_reparto = ahora
    elif nuevo_estado == EstadoDelPedido.ENTREGADO:
        pedido.fecha_entrega = ahora
    
    # Actualizar estado
    pedido.estado = nuevo_estado
    
    db.commit()
    db.refresh(pedido)

    # Construir respuesta
    cliente = db.query(Usuario).filter(
        Usuario.usuario_id == pedido.usuario_id).first()
    zona = db.query(ZonaDelivery).filter(
        ZonaDelivery.zona_id == pedido.zona_id).first()

    delivery_nombre = None
    if pedido.delivery_asignado_id:
        delivery = db.query(Usuario).filter(
            Usuario.usuario_id == pedido.delivery_asignado_id
        ).first()
        if delivery:
            delivery_nombre = delivery.nombre_completo

    return PedidoDashboardResponse(
        pedido_id=pedido.pedido_id,
        token_recoger=pedido.token_recoger,
        estado=pedido.estado,
        cliente_nombre=cliente.nombre_completo if cliente else "Desconocido",
        cliente_email=cliente.email if cliente else "N/A",
        zona_nombre=zona.nombre_zona if zona else "N/A",
        delivery_nombre=delivery_nombre,
        total_pedido=pedido.total_pedido,
        fecha_pedido=pedido.fecha_pedido,
        fecha_confirmado=pedido.fecha_confirmado,
        fecha_listo_cocina=pedido.fecha_listo_cocina,
        fecha_en_reparto=pedido.fecha_en_reparto,
        fecha_entrega=pedido.fecha_entrega
    )


@router.get("/kpis", response_model=KPIsResponse)
def obtener_kpis(
    fecha: Optional[date] = Query(
        None, description="Fecha para el reporte (default: hoy)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene KPIs y métricas del día.
    Incluye: tiempos promedio, ventas, distribución por estado y método de pago.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Si no se proporciona fecha, usar hoy
    if not fecha:
        fecha = date.today()

    # Obtener pedidos del día
    pedidos = db.query(Pedido).filter(
        func.date(Pedido.fecha_pedido) == fecha
    ).all()

    total_pedidos = len(pedidos)

    # Pedidos por estado
    pedidos_por_estado = {}
    for estado in EstadoDelPedido:
        count = sum(1 for p in pedidos if p.estado == estado)
        pedidos_por_estado[estado.value] = count

    # Ventas totales
    ventas_totales = sum(p.total_pedido for p in pedidos)

    # Ventas por método de pago (Deshabilitado por falta de campo en BD)
    ventas_por_metodo_pago = {}
    # for p in pedidos:
    #     metodo = p.metodo_pago.value
    #     if metodo not in ventas_por_metodo_pago:
    #         ventas_por_metodo_pago[metodo] = 0
    #     ventas_por_metodo_pago[metodo] += float(p.total_pedido)

    # Calcular tiempos promedio
    tiempos_preparacion = []
    tiempos_entrega = []
    pedidos_con_tiempos = []

    for p in pedidos:
        # Tiempo de preparación (pedido -> listo cocina)
        if p.fecha_listo_cocina:
            delta = p.fecha_listo_cocina.replace(
                tzinfo=None) - p.fecha_pedido.replace(tzinfo=None)
            minutos = delta.total_seconds() / 60
            tiempos_preparacion.append(minutos)

        # Tiempo total de entrega (pedido -> entregado)
        if p.fecha_entrega:
            delta = p.fecha_entrega.replace(
                tzinfo=None) - p.fecha_pedido.replace(tzinfo=None)
            minutos = delta.total_seconds() / 60
            tiempos_entrega.append(minutos)

            pedidos_con_tiempos.append({
                "pedido_id": p.pedido_id,
                "token": p.token_recoger,
                "minutos_total": round(minutos, 1)
            })

    tiempo_promedio_preparacion = None
    if tiempos_preparacion:
        tiempo_promedio_preparacion = round(
            sum(tiempos_preparacion) / len(tiempos_preparacion), 1)

    tiempo_promedio_entrega = None
    if tiempos_entrega:
        tiempo_promedio_entrega = round(
            sum(tiempos_entrega) / len(tiempos_entrega), 1)

    # Top 5 más rápidos y más lentos
    pedidos_ordenados = sorted(
        pedidos_con_tiempos, key=lambda x: x["minutos_total"])
    pedidos_mas_rapidos = pedidos_ordenados[:5]
    pedidos_mas_lentos = list(reversed(pedidos_ordenados))[:5]

    return KPIsResponse(
        fecha=fecha,
        total_pedidos=total_pedidos,
        pedidos_por_estado=pedidos_por_estado,
        ventas_totales=ventas_totales,
        ventas_por_metodo_pago=ventas_por_metodo_pago,
        tiempo_promedio_preparacion=tiempo_promedio_preparacion,
        tiempo_promedio_entrega=tiempo_promedio_entrega,
        pedidos_mas_rapidos=pedidos_mas_rapidos,
        pedidos_mas_lentos=pedidos_mas_lentos
    )


@router.patch("/pedidos/{pedido_id}/cancelar")
def cancelar_pedido_admin(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Cancela un pedido desde el panel de administración.
    Cambia el estado a 'Cancelado' y restaura el stock al menú.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar el pedido
    pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Verificar que no esté ya cancelado o entregado
    if pedido.estado == EstadoDelPedido.CANCELADO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido ya está cancelado"
        )

    if pedido.estado == EstadoDelPedido.ENTREGADO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cancelar un pedido que ya fue entregado"
        )

    # Restaurar stock de los items
    from app.models.pedido_item import PedidoItem
    items = db.query(PedidoItem).filter(
        PedidoItem.pedido_id == pedido_id).all()

    for item in items:
        menu = db.query(MenuDia).filter(
            MenuDia.menu_dia_id == item.menu_dia_id).first()
        if menu:
            menu.cantidad_disponible += item.cantidad

    # Cambiar estado a cancelado
    pedido.estado = EstadoDelPedido.CANCELADO

    db.commit()

    return {
        "message": "Pedido cancelado exitosamente",
        "pedido_id": pedido_id,
        "stock_restaurado": True
    }


@router.get("/pedidos/{pedido_id}/detalle-completo")
def obtener_detalle_completo_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene el detalle completo de un pedido para análisis administrativo.
    Incluye items, exclusiones, información del cliente, delivery asignado, y todas las fechas.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar el pedido
    pedido = db.query(Pedido).filter(Pedido.pedido_id == pedido_id).first()
    if not pedido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado"
        )

    # Obtener items del pedido
    from app.models.pedido_item import PedidoItem
    from app.models.item_exclusion import ItemExclusion

    items = db.query(PedidoItem).filter(
        PedidoItem.pedido_id == pedido_id).all()

    items_detalle = []
    for item in items:
        # Obtener el menú y plato
        menu = db.query(MenuDia).filter(
            MenuDia.menu_dia_id == item.menu_dia_id).first()
        plato = None
        if menu:
            plato = db.query(Plato).filter(
                Plato.plato_id == menu.plato_id).first()

        # Obtener exclusiones de este item
        exclusiones = db.query(ItemExclusion).filter(
            ItemExclusion.pedido_item_id == item.pedido_item_id
        ).all()

        exclusiones_detalle = []
        for exc in exclusiones:
            ingrediente = db.query(Ingrediente).filter(
                Ingrediente.ingrediente_id == exc.ingrediente_id
            ).first()
            if ingrediente:
                exclusiones_detalle.append({
                    "ingrediente_id": ingrediente.ingrediente_id,
                    "nombre": ingrediente.nombre
                })

        items_detalle.append({
            "pedido_item_id": item.pedido_item_id,
            "menu_dia_id": item.menu_dia_id,
            "plato_nombre": plato.nombre if plato else "Desconocido",
            "cantidad": item.cantidad,
            "precio_unitario": float(item.precio_unitario),
            "subtotal": float(item.subtotal),
            "exclusiones": exclusiones_detalle
        })

    # Obtener cliente
    cliente = db.query(Usuario).filter(
        Usuario.usuario_id == pedido.usuario_id).first()

    # Obtener zona
    zona = db.query(ZonaDelivery).filter(
        ZonaDelivery.zona_id == pedido.zona_id).first()

    # Obtener delivery si está asignado
    delivery_info = None
    if pedido.delivery_asignado_id:
        delivery = db.query(Usuario).filter(
            Usuario.usuario_id == pedido.delivery_asignado_id
        ).first()
        if delivery:
            delivery_info = {
                "delivery_id": delivery.usuario_id,
                "nombre": delivery.nombre_completo,
                "email": delivery.email,
                "telefono": delivery.telefono
            }

    return {
        "pedido_id": pedido.pedido_id,
        "token_recoger": pedido.token_recoger,
        "estado": pedido.estado.value,
        "cliente": {
            "usuario_id": cliente.usuario_id if cliente else None,
            "nombre": cliente.nombre_completo if cliente else "Desconocido",
            "email": cliente.email if cliente else "N/A",
            "telefono": cliente.telefono if cliente else "N/A"
        },
        "zona": {
            "zona_id": zona.zona_id if zona else None,
            "nombre": zona.nombre_zona if zona else "N/A",
            "costo": float(zona.costo_delivery) if zona else 0
        },
        "delivery": delivery_info,
        "direccion_entrega": pedido.direccion_entrega,
        "items": items_detalle,
        "total_pedido": float(pedido.total_pedido),
        "instrucciones_entrega": pedido.instrucciones_entrega,
        "fecha_pedido": pedido.fecha_pedido.isoformat() if pedido.fecha_pedido else None,
        "fecha_confirmado": pedido.fecha_confirmado.isoformat() if pedido.fecha_confirmado else None,
        "fecha_listo_cocina": pedido.fecha_listo_cocina.isoformat() if pedido.fecha_listo_cocina else None,
        "fecha_en_reparto": pedido.fecha_en_reparto.isoformat() if pedido.fecha_en_reparto else None,
        "fecha_entrega": pedido.fecha_entrega.isoformat() if pedido.fecha_entrega else None
    }


# ========== GESTIÓN DE ZONAS DE DELIVERY ==========

@router.post("/zonas", response_model=ZonaResponse, status_code=status.HTTP_201_CREATED)
def crear_zona(
    request: CrearZonaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Crea una nueva zona de delivery.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Verificar que no exista una zona con ese nombre
    zona_existente = db.query(ZonaDelivery).filter(
        ZonaDelivery.nombre_zona == request.nombre_zona
    ).first()

    if zona_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una zona con el nombre '{request.nombre_zona}'"
        )

    # Crear la zona
    nueva_zona = ZonaDelivery(
        nombre_zona=request.nombre_zona
    )

    db.add(nueva_zona)
    db.commit()
    db.refresh(nueva_zona)

    return ZonaResponse.from_orm(nueva_zona)
def listar_zonas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todas las zonas de delivery.
    Solo administradores.
    """
    verificar_admin(current_user)

    zonas = db.query(ZonaDelivery).order_by(ZonaDelivery.nombre_zona).all()
    return [ZonaResponse.from_orm(z) for z in zonas]


@router.get("/zonas/{zona_id}", response_model=ZonaResponse)
def obtener_zona(
    zona_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene una zona de delivery por ID.
    Solo administradores.
    """
    verificar_admin(current_user)

    zona = db.query(ZonaDelivery).filter(
        ZonaDelivery.zona_id == zona_id).first()
    if not zona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zona no encontrada"
        )

    return ZonaResponse.from_orm(zona)


@router.put("/zonas/{zona_id}", response_model=ZonaResponse)
def actualizar_zona(
    zona_id: int,
    request: ActualizarZonaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualiza el nombre de una zona de delivery.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar la zona
    zona = db.query(ZonaDelivery).filter(
        ZonaDelivery.zona_id == zona_id).first()
    if not zona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zona no encontrada"
        )

    # Verificar que no exista otra zona con ese nombre
    zona_existente = db.query(ZonaDelivery).filter(
        ZonaDelivery.nombre_zona == request.nombre_zona,
        ZonaDelivery.zona_id != zona_id
    ).first()

    if zona_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe otra zona con el nombre '{request.nombre_zona}'"
        )

    # Actualizar el nombre
    zona.nombre_zona = request.nombre_zona
    db.commit()
    db.refresh(zona)

    return ZonaResponse.from_orm(zona)


@router.delete("/zonas/{zona_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_zona(
    zona_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Elimina una zona de delivery si no tiene pedidos ni deliveries asignados.
    Solo administradores.
    """
    verificar_admin(current_user)

    # Buscar la zona
    zona = db.query(ZonaDelivery).filter(
        ZonaDelivery.zona_id == zona_id).first()
    if not zona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zona no encontrada"
        )

    # Verificar que no tenga pedidos asociados
    pedidos_count = db.query(Pedido).filter(Pedido.zona_id == zona_id).count()
    if pedidos_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar la zona porque tiene {pedidos_count} pedidos asociados"
        )

    # Verificar que no tenga deliveries asignados
    deliveries_count = db.query(Usuario).filter(
        Usuario.zona_reparto_id == zona_id
    ).count()
    if deliveries_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar la zona porque tiene {deliveries_count} deliveries asignados"
        )

    # Eliminar la zona
    db.delete(zona)
    db.commit()

    return None
