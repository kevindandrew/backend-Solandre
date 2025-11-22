from enum import Enum


class EstadoDelPedido(str, Enum):
    PENDIENTE = "Pendiente"
    CONFIRMADO = "Confirmado"
    EN_COCINA = "En Cocina"
    LISTO_PARA_ENTREGA = "Listo para Entrega"
    EN_REPARTO = "En Reparto"
    ENTREGADO = "Entregado"
    CANCELADO = "Cancelado"


class TipoPlato(str, Enum):
    PRINCIPAL = "Principal"
    ACOMPANAMIENTO = "Acompanamiento"
    BEBIDA = "Bebida"
    POSTRE = "Postre"


class MetodoPago(str, Enum):
    EFECTIVO = "Efectivo"
    QR = "QR"
