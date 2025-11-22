# 🔔 Sistema de Notificaciones en Tiempo Real - Guía de Uso

## **Resumen**

Sistema de notificaciones **sin base de datos** que funciona mediante **polling** (consultas periódicas). Compatible con aplicaciones web y móviles.

---

## **📋 Endpoints Disponibles**

### **1. Notificaciones Generales**

#### **GET /notificaciones/mis-notificaciones**

Obtiene las notificaciones del usuario autenticado según su rol.

**Parámetros:**

- `desde_minutos` (opcional, default: 5): Buscar notificaciones de los últimos X minutos
- `tipo` (opcional): Filtrar por tipo específico
- `limit` (opcional, default: 50): Máximo de notificaciones

**Ejemplo de request:**

```http
GET /notificaciones/mis-notificaciones?desde_minutos=10&tipo=NUEVO_PEDIDO
Authorization: Bearer {token}
```

**Ejemplo de response:**

```json
[
  {
    "evento_id": "evt_1_1732233600",
    "tipo": "NUEVO_PEDIDO",
    "titulo": "Nuevo Pedido",
    "mensaje": "Pedido #123 - Juan Pérez (2 items)",
    "data": {
      "pedido_id": 123,
      "token": "ABC12345",
      "cliente": "Juan Pérez",
      "items_count": 2,
      "total": 45.5
    },
    "fecha_creacion": "2025-11-22T14:30:00"
  }
]
```

---

#### **GET /notificaciones/contador**

Cuenta las notificaciones nuevas desde una fecha.

**Parámetros:**

- `desde` (opcional): Fecha ISO desde la cual contar

**Ejemplo de request:**

```http
GET /notificaciones/contador?desde=2025-11-22T14:00:00
Authorization: Bearer {token}
```

**Ejemplo de response:**

```json
{
  "total": 5,
  "desde": "2025-11-22T14:00:00",
  "eventos_por_tipo": {
    "NUEVO_PEDIDO": 3,
    "CAMBIO_ESTADO": 2
  }
}
```

---

### **2. Endpoints Especializados por Rol**

#### **GET /notificaciones/cocina/nuevos-pedidos** (Rol: Cocina/Admin)

Endpoint especializado para tablets de cocina.

**Ejemplo de uso:**

```javascript
// JavaScript - Consultar cada 10 segundos
setInterval(async () => {
  const response = await fetch(
    "/notificaciones/cocina/nuevos-pedidos?desde_minutos=1",
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );

  const notificaciones = await response.json();

  if (notificaciones.length > 0) {
    // Reproducir sonido
    new Audio("/assets/notification.mp3").play();

    // Mostrar alerta
    notificaciones.forEach((notif) => {
      showToast(notif.mensaje);
    });

    // Actualizar lista de pedidos
    fetchPedidosPendientes();
  }
}, 10000); // Cada 10 segundos
```

---

#### **GET /notificaciones/delivery/mis-asignaciones** (Rol: Delivery)

Para app móvil de delivery, obtiene pedidos recién asignados.

**Ejemplo Flutter:**

```dart
import 'dart:async';

Timer.periodic(Duration(seconds: 15), (timer) async {
  final response = await http.get(
    Uri.parse('$baseUrl/notificaciones/delivery/mis-asignaciones?desde_minutos=5'),
    headers: {'Authorization': 'Bearer $token'}
  );

  if (response.statusCode == 200) {
    final List notificaciones = json.decode(response.body);

    if (notificaciones.isNotEmpty) {
      // Mostrar notificación local
      await AwesomeNotifications().createNotification(
        content: NotificationContent(
          id: 10,
          channelKey: 'delivery_channel',
          title: 'Nueva Entrega Asignada',
          body: notificaciones[0]['mensaje'],
        )
      );

      // Actualizar UI
      setState(() {
        nuevasAsignaciones = notificaciones.length;
      });
    }
  }
});
```

---

#### **GET /notificaciones/cliente/mis-pedidos** (Rol: Cliente)

Para app de clientes, rastrea el estado de sus pedidos.

**Ejemplo React:**

```javascript
import { useEffect, useState } from "react";

function PedidoTracking({ pedidoId }) {
  const [notificaciones, setNotificaciones] = useState([]);
  const [ultimaConsulta, setUltimaConsulta] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(async () => {
      const response = await fetch(
        `/notificaciones/cliente/mis-pedidos?desde_minutos=30`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const data = await response.json();

      // Filtrar solo las más recientes que la última consulta
      const nuevas = data.filter(
        (n) => new Date(n.fecha_creacion) > ultimaConsulta
      );

      if (nuevas.length > 0) {
        // Mostrar notificación push (si el navegador lo permite)
        if (Notification.permission === "granted") {
          new Notification(nuevas[0].titulo, {
            body: nuevas[0].mensaje,
            icon: "/logo.png",
          });
        }

        setNotificaciones([...nuevas, ...notificaciones]);
      }

      setUltimaConsulta(new Date());
    }, 30000); // Cada 30 segundos

    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      {notificaciones.map((notif) => (
        <div key={notif.evento_id} className="notification">
          <h4>{notif.titulo}</h4>
          <p>{notif.mensaje}</p>
        </div>
      ))}
    </div>
  );
}
```

---

### **3. Endpoint Especial: Notificar Llegada**

#### **POST /notificaciones/delivery/notificar-llegada/{pedido_id}** (Rol: Delivery)

El delivery notifica al cliente que llegó.

**Body:**

```json
{
  "latitud": -16.5,
  "longitud": -68.15,
  "mensaje_adicional": "Estoy afuera de tu casa"
}
```

**Ejemplo Flutter:**

```dart
// Botón manual
ElevatedButton(
  child: Text('Notificar que llegué'),
  onPressed: () async {
    final position = await Geolocator.getCurrentPosition();

    final response = await http.post(
      Uri.parse('$baseUrl/notificaciones/delivery/notificar-llegada/$pedidoId'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json'
      },
      body: json.encode({
        'latitud': position.latitude,
        'longitud': position.longitude,
        'mensaje_adicional': 'Estoy en la puerta'
      })
    );

    if (response.statusCode == 200) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Cliente notificado'))
      );
    }
  }
)

// O automático con geofencing
GeofencingManager.registerGeofence(
  GeofenceRegion(
    id: 'destino_$pedidoId',
    latitude: pedido.latitud,
    longitude: pedido.longitud,
    radius: 50, // 50 metros
  ),
  onEnter: () async {
    // Automáticamente notificar cuando llega
    await notificarLlegada(pedidoId);
  }
);
```

---

## **🎯 Tipos de Eventos**

| Tipo                 | Destinatario        | Cuándo se dispara         |
| -------------------- | ------------------- | ------------------------- |
| `NUEVO_PEDIDO`       | Cocina, Admin       | Cliente crea un pedido    |
| `CAMBIO_ESTADO`      | Cliente             | Pedido cambia de estado   |
| `PEDIDO_ASIGNADO`    | Delivery específico | Se le asigna un pedido    |
| `PEDIDO_LISTO`       | Delivery específico | Cocina marca pedido listo |
| `DELIVERY_EN_CAMINO` | Cliente específico  | Delivery recoge el pedido |
| `DELIVERY_CERCA`     | Cliente específico  | Delivery notifica llegada |

---

## **💡 Estrategias de Polling Recomendadas**

### **Por Tipo de App:**

| App                                 | Intervalo            | Endpoint                                    |
| ----------------------------------- | -------------------- | ------------------------------------------- |
| **Tablet Cocina**                   | 10-15 segundos       | `/notificaciones/cocina/nuevos-pedidos`     |
| **App Delivery**                    | 15-30 segundos       | `/notificaciones/delivery/mis-asignaciones` |
| **App Cliente (con pedido activo)** | 30 segundos          | `/notificaciones/cliente/mis-pedidos`       |
| **App Cliente (sin pedido)**        | 60 segundos o manual | `/notificaciones/contador`                  |
| **Dashboard Admin**                 | 20-30 segundos       | `/notificaciones/mis-notificaciones`        |

---

## **🔋 Optimización para Móviles**

### **Reducir consumo de batería:**

```dart
// Flutter: Pausar polling cuando app está en background
class NotificationService with WidgetsBindingObserver {
  Timer? _pollingTimer;

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused) {
      // App en background - pausar polling
      _pollingTimer?.cancel();
    } else if (state == AppLifecycleState.resumed) {
      // App en foreground - reanudar polling
      startPolling();
    }
  }

  void startPolling() {
    _pollingTimer = Timer.periodic(Duration(seconds: 30), (_) {
      fetchNotifications();
    });
  }
}
```

---

## **📊 Ejemplo Completo: Dashboard de Cocina**

```javascript
// React - Dashboard de Cocina con notificaciones en tiempo real

import React, { useState, useEffect } from "react";
import { toast } from "react-toastify";

function DashboardCocina() {
  const [pedidosPendientes, setPedidosPendientes] = useState([]);
  const [ultimaConsulta, setUltimaConsulta] = useState(new Date());

  // Polling de nuevos pedidos
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        // Consultar notificaciones nuevas
        const response = await fetch(
          `/notificaciones/cocina/nuevos-pedidos?desde_minutos=1`,
          {
            headers: { Authorization: `Bearer ${getToken()}` },
          }
        );

        const notificaciones = await response.json();

        if (notificaciones.length > 0) {
          // Reproducir sonido
          const audio = new Audio("/sounds/new-order.mp3");
          audio.play();

          // Mostrar toast
          notificaciones.forEach((notif) => {
            toast.success(notif.mensaje, {
              autoClose: 5000,
              position: "top-right",
            });
          });

          // Recargar lista de pedidos
          fetchPedidosPendientes();
        }

        setUltimaConsulta(new Date());
      } catch (error) {
        console.error("Error al consultar notificaciones:", error);
      }
    }, 10000); // Cada 10 segundos

    return () => clearInterval(interval);
  }, []);

  const fetchPedidosPendientes = async () => {
    const response = await fetch("/cocina/pendientes", {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    const data = await response.json();
    setPedidosPendientes(data);
  };

  return (
    <div className="cocina-dashboard">
      <h1>Pedidos Pendientes</h1>
      <div className="pedidos-grid">
        {pedidosPendientes.map((pedido) => (
          <PedidoCard key={pedido.pedido_id} pedido={pedido} />
        ))}
      </div>
    </div>
  );
}
```

---

## **🚀 Ventajas de Este Sistema**

✅ **Sin base de datos** - No requiere migraciones  
✅ **Compatible con web y móvil** - Funciona con polling simple  
✅ **Bajo overhead** - Solo almacena eventos recientes (última hora)  
✅ **Thread-safe** - Maneja múltiples consultas simultáneas  
✅ **Escalable** - Máximo 1000 eventos por rol en memoria  
✅ **Filtros flexibles** - Por tipo, fecha, usuario específico

---

## **⚠️ Limitaciones**

❌ **Temporal** - Solo guarda eventos de la última hora  
❌ **Sin historial** - Si el usuario no consulta, pierde la notificación  
❌ **Memoria** - Se reinicia si el servidor se reinicia

### **Migración Futura a BD:**

Cuando quieras persistencia, simplemente agrega una tabla `Notificaciones` y cambia las funciones en `app/utils/notificaciones.py` para guardar también en BD. Los endpoints no cambian.

---

## **🎓 Próximos Pasos**

1. Implementa polling en tu frontend
2. Agrega sonidos de notificación
3. Configura notificaciones push del navegador (web)
4. Integra Firebase Cloud Messaging (móvil)
5. Considera WebSockets para el futuro (tiempo real puro)
