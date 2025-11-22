# 🚀 Guía de Despliegue: Render + Neon

Esta guía te muestra cómo desplegar tu backend en **Render** con base de datos **Neon PostgreSQL**.

---

## 📋 **Resumen**

- **Backend**: Render (Web Service)
- **Base de Datos**: Neon PostgreSQL
- **Variables de Entorno**: Solo 5 esenciales

---

## 🗄️ **PASO 1: Configurar Neon (Base de Datos)**

### 1.1 Crear Cuenta en Neon

1. Ve a [neon.tech](https://neon.tech)
2. Regístrate con GitHub
3. Crea un nuevo proyecto: "Solandre"

### 1.2 Crear Base de Datos

1. En el dashboard de Neon, copia la **Connection String**
2. Debería verse así:
   ```
   postgresql://usuario:password@ep-xxx-xxx.us-east-2.aws.neon.tech/solandre?sslmode=require
   ```
3. **GUARDA ESTA URL** - la necesitarás en Render

### 1.3 Inicializar Tablas

Desde tu computadora local:

```bash
# 1. Actualiza tu .env LOCAL con la URL de Neon
DATABASE_URL=postgresql://usuario:password@xxx.neon.tech/solandre?sslmode=require

# 2. Ejecuta los scripts de inicialización
python -m app.init_db
python -m app.init_roles

# 3. Crea un admin (opcional)
python create_admin.py
```

---

## 🌐 **PASO 2: Configurar Render (Backend)**

### 2.1 Preparar Repositorio GitHub

```bash
# 1. Inicializar Git (si no lo hiciste)
git init
git add .
git commit -m "Initial commit"

# 2. Crear repo en GitHub y subir
git remote add origin https://github.com/tu-usuario/solandre-backend.git
git branch -M main
git push -u origin main
```

### 2.2 Crear Web Service en Render

1. Ve a [render.com](https://render.com)
2. Click en **"New +"** → **"Web Service"**
3. Conecta tu repositorio de GitHub
4. Configuración:

| Campo              | Valor                                              |
| ------------------ | -------------------------------------------------- |
| **Name**           | `solandre-api`                                     |
| **Region**         | `Ohio (US East)` o el más cercano                  |
| **Branch**         | `main`                                             |
| **Root Directory** | (vacío)                                            |
| **Runtime**        | `Python 3`                                         |
| **Build Command**  | `pip install -r requirements.txt`                  |
| **Start Command**  | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type**  | `Free` (para empezar)                              |

### 2.3 Configurar Variables de Entorno en Render

En el dashboard de Render, ve a **"Environment"** y agrega:

#### **Variables OBLIGATORIAS (5):**

```env
DATABASE_URL
postgresql://usuario:password@xxx.neon.tech/solandre?sslmode=require
(La URL completa de Neon que copiaste antes)

SECRET_KEY
(Genera una nueva con: openssl rand -hex 32)

DEBUG
False

CORS_ORIGINS
https://solandre-frontend.onrender.com
(Reemplaza con la URL de tu frontend cuando la tengas)

ACCESS_TOKEN_EXPIRE_MINUTES
1440
```

#### **Variables OPCIONALES (ya tienen defaults):**

```env
ALGORITHM=HS256
APP_NAME=Solandre API
APP_VERSION=1.0.0
```

### 2.4 Generar SECRET_KEY Único

**En tu terminal local:**

```bash
# Opción 1: OpenSSL
openssl rand -hex 32

# Opción 2: Python
python -c "import secrets; print(secrets.token_hex(32))"
```

Copia el resultado y úsalo como `SECRET_KEY` en Render.

---

## ✅ **PASO 3: Desplegar**

1. En Render, click en **"Create Web Service"**
2. Espera que termine el build (5-10 minutos)
3. Tu API estará en: `https://solandre-api.onrender.com`

---

## 🧪 **PASO 4: Verificar Despliegue**

### 4.1 Health Check

```bash
curl https://solandre-api.onrender.com/health
```

Debería responder:

```json
{
  "status": "healthy",
  "timestamp": "2025-11-22T...",
  "version": "1.0.0",
  "database": "connected"
}
```

### 4.2 Documentación

Visita en tu navegador:

```
https://solandre-api.onrender.com/docs
```

### 4.3 Probar Login

```bash
curl -X POST https://solandre-api.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@solandre.com","password":"tu_password"}'
```

---

## 🔧 **Configuración Avanzada (Opcional)**

### Habilitar Auto-Deploy desde GitHub

1. En Render → Settings → Build & Deploy
2. Activa **"Auto-Deploy"**
3. Ahora cada `git push` despliega automáticamente

### Agregar Dominio Personalizado

1. Render → Settings → Custom Domain
2. Agrega: `api.tudominio.com`
3. Configura DNS según instrucciones de Render

---

## 📊 **Monitoreo**

### Ver Logs en Tiempo Real

1. Render Dashboard → Logs
2. O usa el CLI:

```bash
render logs -s solandre-api
```

### Health Check Automático

Render verifica `/health` automáticamente cada 30 segundos.

---

## ⚠️ **Limitaciones del Plan FREE de Render**

- ❌ El servicio se "duerme" después de 15 minutos sin uso
- ❌ Primera request después de dormir tarda ~30 segundos
- ❌ 750 horas/mes gratis (suficiente para 1 servicio 24/7)
- ✅ Para producción real, considera plan **Starter ($7/mes)**

---

## 🐛 **Troubleshooting**

### Error: "Application failed to respond"

**Causa**: El puerto no está configurado correctamente
**Solución**: Verifica que el Start Command sea:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Error: "Database connection failed"

**Causa**: DATABASE_URL incorrecta o Neon suspendido
**Solución**:

1. Verifica la URL en Variables de Entorno
2. Asegúrate de incluir `?sslmode=require`

### Error: "CORS policy blocked"

**Causa**: Frontend no está en CORS_ORIGINS
**Solución**: Actualiza la variable en Render:

```env
CORS_ORIGINS=https://tu-frontend.vercel.app,https://tu-frontend.netlify.app
```

---

## 🔐 **Seguridad en Producción**

### ✅ Checklist de Seguridad

- [x] `DEBUG=False` en producción
- [x] `SECRET_KEY` único y seguro (32+ caracteres)
- [x] CORS configurado solo con dominios específicos (NO `*`)
- [x] DATABASE_URL con `?sslmode=require`
- [x] Contraseña de admin cambiada del ejemplo
- [x] Variables de entorno en Render (NO en código)

---

## 📱 **Conectar Frontend**

Una vez desplegado, tu frontend debe usar:

```javascript
// .env del frontend
VITE_API_URL=https://solandre-api.onrender.com
# o
NEXT_PUBLIC_API_URL=https://solandre-api.onrender.com
```

```javascript
// Ejemplo de fetch
const response = await fetch(`${import.meta.env.VITE_API_URL}/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password }),
});
```

---

## 🎯 **Resumen: Solo 5 Variables para Producción**

```env
DATABASE_URL=postgresql://xxx@xxx.neon.tech/solandre?sslmode=require
SECRET_KEY=tu_clave_generada_con_openssl
DEBUG=False
CORS_ORIGINS=https://tu-frontend.vercel.app
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

**¡Eso es todo!** 🎉

---

## 📞 **¿Necesitas Ayuda?**

- 📖 [Docs de Render](https://render.com/docs)
- 📖 [Docs de Neon](https://neon.tech/docs)
- 💬 Contacto: soporte@solandre.com
