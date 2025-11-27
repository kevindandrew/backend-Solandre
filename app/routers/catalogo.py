from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List, Optional

from app.database import get_db
from app.models.zona_delivery import ZonaDelivery
from app.models.menu_dia import MenuDia
from app.models.plato import Plato
from app.models.ingrediente import Ingrediente
from app.models.plato_ingrediente import PlatoIngrediente
from app.schemas.catalogo import (
    ZonaResponse,
    MenuDiaResponse,
    PlatoSimpleResponse,
    PlatoCompletoResponse,
    IngredienteResponse,
    MenuIngredientesResponse
)

router = APIRouter(
    prefix="/catalogo",
    tags=["Catálogo Público"]
)


@router.get("/zonas", response_model=List[ZonaResponse])
def get_zonas(db: Session = Depends(get_db)):
    """
    Obtiene la lista de todas las zonas de delivery disponibles.
    Vital para el dropdown del formulario de pedido.
    """
    zonas = db.query(ZonaDelivery).all()
    return zonas


@router.get("/menus", response_model=List[MenuDiaResponse])
def listar_menus_publico(
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio del filtro"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin del filtro"),
    db: Session = Depends(get_db)
):
    """
    Lista todos los menús publicados con filtros de fecha opcionales.
    Permite ver el historial o futuros menús.
    """
    query = db.query(MenuDia).filter(MenuDia.publicado == True)

    if fecha_inicio:
        query = query.filter(MenuDia.fecha >= fecha_inicio)
    
    if fecha_fin:
        query = query.filter(MenuDia.fecha <= fecha_fin)

    menus = query.order_by(MenuDia.fecha.desc()).all()

    resultado = []
    for menu in menus:
        # Obtener los platos de cada menú
        plato_principal = db.query(Plato).filter(
            Plato.plato_id == menu.plato_principal_id).first()
            
        bebida = None
        if menu.bebida_id:
            bebida = db.query(Plato).filter(
                Plato.plato_id == menu.bebida_id).first()
                
        postre = None
        if menu.postre_id:
            postre = db.query(Plato).filter(
                Plato.plato_id == menu.postre_id).first()

        resultado.append(MenuDiaResponse(
            menu_dia_id=menu.menu_dia_id,
            fecha=menu.fecha,
            precio_menu=menu.precio_menu,
            cantidad_disponible=menu.cantidad_disponible,
            publicado=menu.publicado,
            info_nutricional=menu.info_nutricional,
            imagen_url=menu.imagen_url,
            plato_principal=PlatoSimpleResponse.from_orm(plato_principal),
            bebida=PlatoSimpleResponse.from_orm(bebida) if bebida else None,
            postre=PlatoSimpleResponse.from_orm(postre) if postre else None
        ))

    return resultado


@router.get("/menu-hoy", response_model=MenuDiaResponse)
def get_menu_hoy(db: Session = Depends(get_db)):
    """
    Obtiene el menú del día actual (foto, precio, platos).
    Verifica que esté publicado y tenga cantidad disponible.
    """
    hoy = date.today()

    menu = db.query(MenuDia).filter(
        MenuDia.fecha == hoy,
        MenuDia.publicado == True,
        MenuDia.cantidad_disponible > 0
    ).first()

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay menú disponible para hoy"
        )

    # Obtener los platos
    plato_principal = db.query(Plato).filter(
        Plato.plato_id == menu.plato_principal_id).first()
    
    bebida = None
    if menu.bebida_id:
        bebida = db.query(Plato).filter(Plato.plato_id == menu.bebida_id).first()
        
    postre = None
    if menu.postre_id:
        postre = db.query(Plato).filter(Plato.plato_id == menu.postre_id).first()

    return MenuDiaResponse(
        menu_dia_id=menu.menu_dia_id,
        fecha=menu.fecha,
        precio_menu=menu.precio_menu,
        cantidad_disponible=menu.cantidad_disponible,
        publicado=menu.publicado,
        info_nutricional=menu.info_nutricional,
        plato_principal=PlatoSimpleResponse.from_orm(plato_principal),
        bebida=PlatoSimpleResponse.from_orm(bebida) if bebida else None,
        postre=PlatoSimpleResponse.from_orm(postre) if postre else None
    )


@router.get("/menu-semanal", response_model=List[MenuDiaResponse])
def get_menu_semanal(db: Session = Depends(get_db)):
    """
    Obtiene los menús de los próximos 7 días para mostrar la agenda semanal.
    Solo incluye menús publicados.
    """
    hoy = date.today()
    proximos_7_dias = hoy + timedelta(days=7)

    menus = db.query(MenuDia).filter(
        MenuDia.fecha >= hoy,
        MenuDia.fecha <= proximos_7_dias,
        MenuDia.publicado == True
    ).order_by(MenuDia.fecha).all()

    resultado = []
    for menu in menus:
        # Obtener los platos de cada menú
        plato_principal = db.query(Plato).filter(
            Plato.plato_id == menu.plato_principal_id).first()
            
        bebida = None
        if menu.bebida_id:
            bebida = db.query(Plato).filter(
                Plato.plato_id == menu.bebida_id).first()
                
        postre = None
        if menu.postre_id:
            postre = db.query(Plato).filter(
                Plato.plato_id == menu.postre_id).first()

        resultado.append(MenuDiaResponse(
            menu_dia_id=menu.menu_dia_id,
            fecha=menu.fecha,
            precio_menu=menu.precio_menu,
            cantidad_disponible=menu.cantidad_disponible,
            publicado=menu.publicado,
            info_nutricional=menu.info_nutricional,
            imagen_url=menu.imagen_url,
            plato_principal=PlatoSimpleResponse.from_orm(plato_principal),
            bebida=PlatoSimpleResponse.from_orm(bebida) if bebida else None,
            postre=PlatoSimpleResponse.from_orm(postre) if postre else None
        ))

    return resultado


@router.get("/menu/{menu_id}/ingredientes", response_model=MenuIngredientesResponse)
def get_menu_ingredientes(menu_id: int, db: Session = Depends(get_db)):
    """
    Obtiene la lista de ingredientes del plato principal del menú.
    Esto permite al usuario saber qué ingredientes puede excluir.
    """
    menu = db.query(MenuDia).filter(MenuDia.menu_dia_id == menu_id).first()

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menú no encontrado"
        )

    # Obtener el plato principal
    plato_principal = db.query(Plato).filter(
        Plato.plato_id == menu.plato_principal_id).first()

    # Obtener ingredientes del plato principal
    ingredientes_ids = db.query(PlatoIngrediente.ingrediente_id).filter(
        PlatoIngrediente.plato_id == menu.plato_principal_id
    ).all()

    ingredientes = []
    for (ing_id,) in ingredientes_ids:
        ingrediente = db.query(Ingrediente).filter(
            Ingrediente.ingrediente_id == ing_id).first()
        if ingrediente:
            ingredientes.append(IngredienteResponse.from_orm(ingrediente))

    return MenuIngredientesResponse(
        menu_dia_id=menu.menu_dia_id,
        fecha=menu.fecha,
        plato_principal=PlatoSimpleResponse.from_orm(plato_principal),
        ingredientes=ingredientes
    )


@router.get("/platos", response_model=List[PlatoCompletoResponse])
def get_platos(db: Session = Depends(get_db)):
    """
    Obtiene el catálogo completo de platos disponibles.
    Incluye la lista de ingredientes de cada plato.
    """
    platos = db.query(Plato).all()
    
    resultado = []
    for plato in platos:
        # Obtener ingredientes del plato
        ingredientes_ids = db.query(PlatoIngrediente.ingrediente_id).filter(
            PlatoIngrediente.plato_id == plato.plato_id
        ).all()

        ingredientes = []
        for (ing_id,) in ingredientes_ids:
            ingrediente = db.query(Ingrediente).filter(
                Ingrediente.ingrediente_id == ing_id).first()
            if ingrediente:
                ingredientes.append(IngredienteResponse.from_orm(ingrediente))
        
        # Crear respuesta manual para incluir ingredientes
        plato_response = PlatoCompletoResponse(
            plato_id=plato.plato_id,
            nombre=plato.nombre,
            descripcion=plato.descripcion,
            tipo=plato.tipo,
            imagen_url=plato.imagen_url,
            ingredientes=ingredientes
        )
        resultado.append(plato_response)

    return resultado


@router.get("/menu/{fecha}", response_model=MenuDiaResponse)
def get_menu_por_fecha(fecha: date, db: Session = Depends(get_db)):
    """
    Obtiene el menú de una fecha específica.
    Permite consultar menús futuros o pasados.
    """
    menu = db.query(MenuDia).filter(
        MenuDia.fecha == fecha,
        MenuDia.publicado == True
    ).first()

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay menú disponible para la fecha {fecha}"
        )

    # Obtener los platos
    plato_principal = db.query(Plato).filter(
        Plato.plato_id == menu.plato_principal_id).first()
    
    bebida = None
    if menu.bebida_id:
        bebida = db.query(Plato).filter(Plato.plato_id == menu.bebida_id).first()
        
    postre = None
    if menu.postre_id:
        postre = db.query(Plato).filter(Plato.plato_id == menu.postre_id).first()

    return MenuDiaResponse(
        menu_dia_id=menu.menu_dia_id,
        fecha=menu.fecha,
        precio_menu=menu.precio_menu,
        cantidad_disponible=menu.cantidad_disponible,
        publicado=menu.publicado,
        info_nutricional=menu.info_nutricional,
        imagen_url=menu.imagen_url,
        plato_principal=PlatoSimpleResponse.from_orm(plato_principal),
        bebida=PlatoSimpleResponse.from_orm(bebida) if bebida else None,
        postre=PlatoSimpleResponse.from_orm(postre) if postre else None
    )
