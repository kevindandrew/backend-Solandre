from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings

# Configuración para hashear passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera un hash seguro de la contraseña
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token JWT con los datos proporcionados

    Args:
        data: Diccionario con los datos a incluir en el token (ej: user_id, rol_id)
        expires_delta: Tiempo de expiración personalizado (opcional)

    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un token JWT

    Args:
        token: Token JWT a decodificar

    Returns:
        Diccionario con los datos del token si es válido, None si no lo es
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY,
                             algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
