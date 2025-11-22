"""
Sistema de notificaciones en memoria para eventos del sistema.
No requiere base de datos, almacena eventos temporalmente en memoria.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass, asdict
import threading


@dataclass
class Evento:
    """Representa un evento/notificación del sistema"""
    evento_id: str
    tipo: str  # 'NUEVO_PEDIDO', 'CAMBIO_ESTADO', 'DELIVERY_LLEGADA', etc.
    destinatario_rol: int  # 1=Admin, 2=Cocina, 3=Delivery, 4=Cliente
    # usuario_id específico (null = todos del rol)
    destinatario_id: Optional[int]
    titulo: str
    mensaje: str
    data: dict  # Información adicional (pedido_id, etc.)
    fecha_creacion: datetime

    def to_dict(self):
        """Convierte el evento a diccionario para JSON"""
        result = asdict(self)
        result['fecha_creacion'] = self.fecha_creacion.isoformat()
        return result


class GestorNotificaciones:
    """
    Gestor de notificaciones en memoria.
    Mantiene los últimos eventos durante 1 hora.
    """

    def __init__(self, max_eventos: int = 1000, tiempo_vida_minutos: int = 60):
        self.max_eventos = max_eventos
        self.tiempo_vida = timedelta(minutes=tiempo_vida_minutos)

        # Almacenamiento por rol (para consultas rápidas)
        self.eventos_por_rol: Dict[int, deque] = {
            1: deque(maxlen=max_eventos),  # Admin
            2: deque(maxlen=max_eventos),  # Cocina
            3: deque(maxlen=max_eventos),  # Delivery
            4: deque(maxlen=max_eventos),  # Cliente
        }

        # Almacenamiento por usuario específico
        self.eventos_por_usuario: Dict[int, deque] = {}

        # Lock para thread-safety
        self._lock = threading.Lock()

        # Contador para IDs únicos
        self._contador = 0

    def crear_evento(
        self,
        tipo: str,
        destinatario_rol: int,
        titulo: str,
        mensaje: str,
        data: dict = None,
        destinatario_id: Optional[int] = None
    ) -> Evento:
        """
        Crea un nuevo evento/notificación.

        Args:
            tipo: Tipo de evento (NUEVO_PEDIDO, CAMBIO_ESTADO, etc.)
            destinatario_rol: Rol del destinatario (1=Admin, 2=Cocina, 3=Delivery, 4=Cliente)
            titulo: Título de la notificación
            mensaje: Mensaje descriptivo
            data: Datos adicionales (pedido_id, estado, etc.)
            destinatario_id: ID de usuario específico (opcional)

        Returns:
            El evento creado
        """
        with self._lock:
            self._contador += 1
            evento_id = f"evt_{self._contador}_{int(datetime.now().timestamp())}"

            evento = Evento(
                evento_id=evento_id,
                tipo=tipo,
                destinatario_rol=destinatario_rol,
                destinatario_id=destinatario_id,
                titulo=titulo,
                mensaje=mensaje,
                data=data or {},
                fecha_creacion=datetime.now()
            )

            # Guardar por rol
            self.eventos_por_rol[destinatario_rol].append(evento)

            # Si es para usuario específico, guardar también ahí
            if destinatario_id:
                if destinatario_id not in self.eventos_por_usuario:
                    self.eventos_por_usuario[destinatario_id] = deque(
                        maxlen=self.max_eventos)
                self.eventos_por_usuario[destinatario_id].append(evento)

            return evento

    def obtener_eventos_recientes(
        self,
        rol_id: int,
        usuario_id: Optional[int] = None,
        desde: Optional[datetime] = None,
        tipo: Optional[str] = None,
        limit: int = 50
    ) -> List[Evento]:
        """
        Obtiene eventos recientes filtrados.

        Args:
            rol_id: Rol del usuario consultante
            usuario_id: ID del usuario (para eventos personales)
            desde: Fecha desde la cual buscar (default: últimos 5 minutos)
            tipo: Filtrar por tipo de evento
            limit: Máximo de eventos a retornar

        Returns:
            Lista de eventos que cumplen los criterios
        """
        with self._lock:
            # Determinar desde qué fecha buscar
            if desde is None:
                desde = datetime.now() - timedelta(minutes=5)

            eventos = []

            # Primero buscar eventos personales
            if usuario_id and usuario_id in self.eventos_por_usuario:
                eventos.extend(self.eventos_por_usuario[usuario_id])

            # Luego eventos del rol (broadcast)
            eventos.extend(self.eventos_por_rol[rol_id])

            # Filtrar por fecha y tipo
            eventos_filtrados = [
                e for e in eventos
                if e.fecha_creacion >= desde
                and (tipo is None or e.tipo == tipo)
                and (e.destinatario_id is None or e.destinatario_id == usuario_id)
            ]

            # Ordenar por fecha (más recientes primero)
            eventos_filtrados.sort(
                key=lambda x: x.fecha_creacion, reverse=True)

            # Limitar resultados
            return eventos_filtrados[:limit]

    def limpiar_eventos_antiguos(self):
        """Limpia eventos más antiguos que tiempo_vida"""
        with self._lock:
            fecha_limite = datetime.now() - self.tiempo_vida

            # Limpiar por rol
            for rol_id in self.eventos_por_rol:
                self.eventos_por_rol[rol_id] = deque(
                    (e for e in self.eventos_por_rol[rol_id]
                     if e.fecha_creacion >= fecha_limite),
                    maxlen=self.max_eventos
                )

            # Limpiar por usuario
            usuarios_vacios = []
            for usuario_id in self.eventos_por_usuario:
                self.eventos_por_usuario[usuario_id] = deque(
                    (e for e in self.eventos_por_usuario[usuario_id]
                     if e.fecha_creacion >= fecha_limite),
                    maxlen=self.max_eventos
                )
                if len(self.eventos_por_usuario[usuario_id]) == 0:
                    usuarios_vacios.append(usuario_id)

            # Eliminar usuarios sin eventos
            for usuario_id in usuarios_vacios:
                del self.eventos_por_usuario[usuario_id]

    def contador_no_vistos(
        self,
        rol_id: int,
        usuario_id: Optional[int] = None,
        desde: Optional[datetime] = None
    ) -> int:
        """
        Cuenta eventos no vistos desde una fecha.

        Args:
            rol_id: Rol del usuario
            usuario_id: ID del usuario
            desde: Fecha desde la cual contar

        Returns:
            Número de eventos nuevos
        """
        eventos = self.obtener_eventos_recientes(
            rol_id=rol_id,
            usuario_id=usuario_id,
            desde=desde
        )
        return len(eventos)


# Instancia global del gestor de notificaciones
gestor_notificaciones = GestorNotificaciones()


# ========== FUNCIONES HELPER PARA CREAR NOTIFICACIONES ==========

def notificar_nuevo_pedido(pedido_id: int, token: str, cliente_nombre: str, items_count: int, total: float):
    """Notifica a cocina y admin sobre nuevo pedido"""
    data = {
        "pedido_id": pedido_id,
        "token": token,
        "cliente": cliente_nombre,
        "items_count": items_count,
        "total": total
    }

    # Notificar a cocina
    gestor_notificaciones.crear_evento(
        tipo="NUEVO_PEDIDO",
        destinatario_rol=2,  # Cocina
        titulo="Nuevo Pedido",
        mensaje=f"Pedido #{pedido_id} - {cliente_nombre} ({items_count} items)",
        data=data
    )

    # Notificar a admin
    gestor_notificaciones.crear_evento(
        tipo="NUEVO_PEDIDO",
        destinatario_rol=1,  # Admin
        titulo="Nuevo Pedido",
        mensaje=f"Pedido #{pedido_id} de {cliente_nombre}",
        data=data
    )


def notificar_cambio_estado(
    pedido_id: int,
    token: str,
    nuevo_estado: str,
    cliente_id: int,
    cliente_nombre: str = ""
):
    """Notifica al cliente sobre cambio de estado de su pedido"""
    mensajes = {
        "CONFIRMADO": "Tu pedido ha sido confirmado y está en preparación",
        "EN_COCINA": "Tu pedido está siendo preparado en cocina",
        "LISTO_PARA_ENTREGA": "¡Tu pedido está listo! El delivery lo recogerá pronto",
        "EN_REPARTO": "Tu pedido está en camino",
        "ENTREGADO": "¡Tu pedido ha sido entregado! ¡Buen provecho!",
        "CANCELADO": "Tu pedido ha sido cancelado"
    }

    gestor_notificaciones.crear_evento(
        tipo="CAMBIO_ESTADO",
        destinatario_rol=4,  # Cliente
        destinatario_id=cliente_id,
        titulo=f"Pedido {token}",
        mensaje=mensajes.get(
            nuevo_estado, f"Estado actualizado a {nuevo_estado}"),
        data={
            "pedido_id": pedido_id,
            "token": token,
            "estado": nuevo_estado
        }
    )


def notificar_delivery_asignado(
    pedido_id: int,
    token: str,
    delivery_id: int,
    delivery_nombre: str,
    direccion: str
):
    """Notifica al delivery sobre nueva asignación"""
    gestor_notificaciones.crear_evento(
        tipo="PEDIDO_ASIGNADO",
        destinatario_rol=3,  # Delivery
        destinatario_id=delivery_id,
        titulo="Nueva Entrega Asignada",
        mensaje=f"Pedido {token} - {direccion}",
        data={
            "pedido_id": pedido_id,
            "token": token,
            "direccion": direccion
        }
    )


def notificar_pedido_listo(
    pedido_id: int,
    token: str,
    delivery_id: Optional[int],
    delivery_nombre: Optional[str]
):
    """Notifica al delivery que un pedido está listo para recoger"""
    if delivery_id:
        gestor_notificaciones.crear_evento(
            tipo="PEDIDO_LISTO",
            destinatario_rol=3,  # Delivery
            destinatario_id=delivery_id,
            titulo="Pedido Listo para Recoger",
            mensaje=f"Pedido {token} listo en cocina",
            data={
                "pedido_id": pedido_id,
                "token": token
            }
        )


def notificar_delivery_en_camino(
    pedido_id: int,
    token: str,
    cliente_id: int,
    delivery_nombre: str
):
    """Notifica al cliente que el delivery está en camino"""
    gestor_notificaciones.crear_evento(
        tipo="DELIVERY_EN_CAMINO",
        destinatario_rol=4,  # Cliente
        destinatario_id=cliente_id,
        titulo="Tu pedido va en camino",
        mensaje=f"{delivery_nombre} está llevando tu pedido",
        data={
            "pedido_id": pedido_id,
            "token": token,
            "delivery": delivery_nombre
        }
    )


def notificar_delivery_cerca(
    pedido_id: int,
    token: str,
    cliente_id: int,
    delivery_nombre: str
):
    """Notifica al cliente que el delivery está llegando"""
    gestor_notificaciones.crear_evento(
        tipo="DELIVERY_CERCA",
        destinatario_rol=4,  # Cliente
        destinatario_id=cliente_id,
        titulo="¡Tu delivery está llegando!",
        mensaje=f"{delivery_nombre} está afuera con tu pedido",
        data={
            "pedido_id": pedido_id,
            "token": token,
            "delivery": delivery_nombre
        }
    )
