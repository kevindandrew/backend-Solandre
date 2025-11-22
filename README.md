# 🍽️ Solandre API - Backend

API REST para sistema de delivery de comida desarrollado con FastAPI y PostgreSQL.

## 📋 Características

- ✅ Sistema completo de autenticación JWT
- ✅ 4 roles de usuario (Admin, Cocina, Delivery, Cliente)
- ✅ Gestión de menús, pedidos y entregas
- ✅ Sistema de notificaciones en tiempo real
- ✅ Auto-asignación de deliveries
- ✅ Tracking público de pedidos
- ✅ Sistema de exclusiones de ingredientes
- ✅ KPIs y métricas
- ✅ Health checks
- ✅ Logging automático

## 🚀 Inicio Rápido

### Requisitos

- Python 3.10+
- PostgreSQL 14+

### Instalación

1. **Clonar el repositorio**

```bash
git clone <url-del-repo>
cd solandre-backend
```

2. **Crear entorno virtual**

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell
# o
source .venv/bin/activate    # Linux/Mac
```

3. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**

Crear archivo `.env` en la raíz:

```env
DATABASE_URL=postgresql://usuario:password@localhost:5432/solandre_db
SECRET_KEY=tu_clave_secreta_muy_segura_aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
APP_NAME=Solandre API
APP_VERSION=1.0.0
DEBUG=True
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

5. **Crear base de datos**

```sql
CREATE DATABASE solandre_db;
```

6. **Inicializar tablas**

```bash
python -m app.init_db
```

7. **Crear roles**

```bash
python -m app.init_roles
```

8. **Crear usuario admin** (opcional)

```bash
# Copiar el ejemplo
cp create_admin.example.py create_admin.py

# Editar create_admin.py con tus credenciales
# Luego ejecutar:
python create_admin.py

# Eliminar después de usar
rm create_admin.py
```

9. **Iniciar servidor**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 Documentación API

Una vez iniciado el servidor, accede a:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Ping**: http://localhost:8000/ping

## 🔑 Endpoints Principales

### Autenticación

- `POST /auth/register` - Registro de clientes
- `POST /auth/login` - Inicio de sesión
- `GET /auth/perfil` - Ver perfil
- `PATCH /auth/perfil` - Actualizar perfil
- `PATCH /auth/cambiar-password` - Cambiar contraseña

### Catálogo (Público)

- `GET /catalogo/zonas` - Zonas de delivery
- `GET /catalogo/menu-hoy` - Menú del día
- `GET /catalogo/menu-semanal` - Próximos 7 días
- `GET /catalogo/menu/{id}/ingredientes` - Ingredientes del plato

### Pedidos (Cliente)

- `POST /pedidos` - Crear pedido
- `GET /pedidos/mis-pedidos` - Historial
- `GET /pedidos/{token}/track` - Tracking público
- `DELETE /pedidos/{id}` - Cancelar pedido

### Cocina (Rol: Cocina/Admin)

- `GET /cocina/pendientes` - Pedidos pendientes
- `PATCH /cocina/pedidos/{id}/estado` - Cambiar estado
- `GET /cocina/historial` - Historial del día
- `GET /cocina/estadisticas` - Métricas de rendimiento

### Delivery (Rol: Delivery)

- `GET /delivery/mis-entregas` - Entregas asignadas
- `PATCH /delivery/pedidos/{id}/tomar` - Recoger pedido
- `PATCH /delivery/pedidos/{id}/finalizar` - Entregar
- `GET /delivery/historial` - Historial

### Admin (Rol: Admin)

- `POST /admin/menu` - Crear menú
- `GET /admin/menu` - Listar menús
- `POST /admin/platos` - Crear plato
- `POST /admin/ingredientes` - Crear ingrediente
- `POST /admin/empleados` - Crear empleado
- `GET /admin/pedidos` - Dashboard de pedidos
- `GET /admin/kpis` - KPIs del día

### Notificaciones (Todos los roles)

- `GET /notificaciones/mis-notificaciones` - Notificaciones del usuario
- `GET /notificaciones/contador` - Contador de nuevas
- `GET /notificaciones/cocina/nuevos-pedidos` - Especializado cocina
- `POST /notificaciones/delivery/notificar-llegada/{id}` - Delivery llegó

## 🗂️ Estructura del Proyecto

```
solandre-backend/
├── app/
│   ├── models/          # Modelos SQLModel
│   ├── routers/         # Endpoints por módulo
│   ├── schemas/         # Schemas Pydantic
│   ├── utils/           # Utilidades (auth, logger, notificaciones)
│   ├── config.py        # Configuración
│   ├── database.py      # Conexión a BD
│   ├── main.py          # App principal
│   └── init_db.py       # Inicialización de BD
├── logs/                # Logs de la aplicación (auto-generado)
├── .env                 # Variables de entorno (NO subir a Git)
├── .gitignore           # Archivos ignorados
├── requirements.txt     # Dependencias
└── README.md            # Este archivo
```

## 📊 Logs

Los logs se guardan automáticamente en:

- `logs/app.log` - Logs generales
- `logs/error.log` - Solo errores

## 🔐 Seguridad

- Contraseñas hasheadas con bcrypt
- Tokens JWT con expiración
- Validación de permisos por rol
- CORS configurado
- Sanitización de inputs con Pydantic

## 🚢 Despliegue

### Variables de entorno para producción

```env
DEBUG=False
DATABASE_URL=postgresql://usuario:password@host:5432/db_produccion
SECRET_KEY=clave_super_segura_generada_aleatoriamente
CORS_ORIGINS=https://tudominio.com,https://www.tudominio.com
```

### Comandos útiles

```bash
# Verificar salud del sistema
curl http://localhost:8000/health

# Ver logs en tiempo real
tail -f logs/app.log

# Limpiar caché de Python
find . -type d -name __pycache__ -exec rm -rf {} +
```

## 📝 Notas Importantes

- **NO subas el archivo `.env` a Git** - Contiene credenciales
- **NO subas `create_admin.py` con credenciales** - Usa el ejemplo
- Los logs se rotan automáticamente cada 10MB
- Las notificaciones se almacenan en memoria (última hora)
- El sistema auto-asigna delivery disponible en la zona

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/amazing-feature`)
3. Commit tus cambios (`git commit -m 'Add amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es privado y confidencial.

## 👥 Equipo

Desarrollado por el equipo de Solandre.

---

**¿Necesitas ayuda?** Contacta a soporte@solandre.com
