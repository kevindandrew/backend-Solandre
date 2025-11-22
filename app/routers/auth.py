from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario
from app.models.role import Role
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    ActualizarPerfilRequest,
    CambiarPasswordRequest
)
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.utils.dependencies import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Inicia sesión con email y contraseña.
    Devuelve un token JWT con la información del usuario.
    """
    # Buscar usuario por email
    usuario = db.query(Usuario).filter(Usuario.email == request.email).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    # Verificar contraseña
    if not verify_password(request.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    # Obtener el rol del usuario
    rol = db.query(Role).filter(Role.rol_id == usuario.rol_id).first()

    # Crear token JWT
    access_token = create_access_token(
        data={
            "sub": str(usuario.usuario_id),
            "usuario_id": usuario.usuario_id,
            "rol_id": usuario.rol_id,
            "email": usuario.email
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        usuario_id=usuario.usuario_id,
        rol_id=usuario.rol_id,
        nombre_completo=usuario.nombre_completo,
        email=usuario.email
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario con rol de Cliente.
    Devuelve un token JWT para iniciar sesión automáticamente.
    """
    # Verificar si el email ya existe
    existing_user = db.query(Usuario).filter(
        Usuario.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )

    # Obtener el rol de "Cliente"
    rol_cliente = db.query(Role).filter(Role.nombre_rol == "Cliente").first()
    if not rol_cliente:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en la configuración del sistema: Rol Cliente no encontrado"
        )

    # Hashear la contraseña
    hashed_password = get_password_hash(request.password)

    # Crear nuevo usuario
    nuevo_usuario = Usuario(
        nombre_completo=request.nombre_completo,
        email=request.email,
        password_hash=hashed_password,
        telefono=request.telefono,
        rol_id=rol_cliente.rol_id
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    # Crear token JWT
    access_token = create_access_token(
        data={
            "sub": str(nuevo_usuario.usuario_id),
            "usuario_id": nuevo_usuario.usuario_id,
            "rol_id": nuevo_usuario.rol_id,
            "email": nuevo_usuario.email
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        usuario_id=nuevo_usuario.usuario_id,
        rol_id=nuevo_usuario.rol_id,
        nombre_completo=nuevo_usuario.nombre_completo,
        email=nuevo_usuario.email
    )


@router.get("/perfil", response_model=UserResponse)
def obtener_perfil(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene el perfil del usuario autenticado.
    Incluye información del rol.
    """
    # Obtener el rol del usuario
    rol = db.query(Role).filter(Role.rol_id == current_user.rol_id).first()

    return UserResponse(
        usuario_id=current_user.usuario_id,
        nombre_completo=current_user.nombre_completo,
        email=current_user.email,
        telefono=current_user.telefono,
        rol_id=current_user.rol_id,
        nombre_rol=rol.nombre_rol if rol else "Desconocido"
    )


@router.patch("/perfil", response_model=UserResponse)
def actualizar_perfil(
    request: ActualizarPerfilRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualiza los datos del perfil del usuario autenticado.
    Permite cambiar nombre completo y teléfono.
    """
    # Actualizar campos si se proporcionan
    if request.nombre_completo is not None:
        current_user.nombre_completo = request.nombre_completo

    if request.telefono is not None:
        current_user.telefono = request.telefono

    db.commit()
    db.refresh(current_user)

    # Obtener el rol del usuario
    rol = db.query(Role).filter(Role.rol_id == current_user.rol_id).first()

    return UserResponse(
        usuario_id=current_user.usuario_id,
        nombre_completo=current_user.nombre_completo,
        email=current_user.email,
        telefono=current_user.telefono,
        rol_id=current_user.rol_id,
        nombre_rol=rol.nombre_rol if rol else "Desconocido"
    )


@router.patch("/cambiar-password")
def cambiar_password(
    request: CambiarPasswordRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Cambia la contraseña del usuario autenticado.
    Requiere la contraseña actual para validación.
    """
    # Verificar contraseña actual
    if not verify_password(request.password_actual, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta"
        )

    # Actualizar contraseña
    current_user.password_hash = get_password_hash(request.password_nueva)

    db.commit()

    return {"message": "Contraseña actualizada exitosamente"}
