import random
import string
from sqlalchemy.orm import Session
from app.models.pedido import Pedido


def generar_token_unico(db: Session, longitud: int = 8) -> str:
    """
    Genera un token único alfanumérico de 8 caracteres para identificar pedidos.
    Verifica que no exista en la base de datos.

    Args:
        db: Sesión de base de datos
        longitud: Longitud del token (por defecto 8)

    Returns:
        Token único de 8 caracteres
    """
    caracteres = string.ascii_uppercase + string.digits
    max_intentos = 100

    for _ in range(max_intentos):
        token = ''.join(random.choices(caracteres, k=longitud))

        # Verificar que no exista en la base de datos
        existe = db.query(Pedido).filter(Pedido.token_recoger == token).first()
        if not existe:
            return token

    raise Exception(
        "No se pudo generar un token único después de múltiples intentos")
