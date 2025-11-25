from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from app.config import settings
from app.routers.role import router as role_router
from app.routers.auth import router as auth_router
from app.routers.catalogo import router as catalogo_router
from app.routers.pedido import router as pedido_router
from app.routers.cocina import router as cocina_router
from app.routers.delivery import router as delivery_router
from app.routers.admin import router as admin_router
from app.routers.notificaciones import router as notificaciones_router
from app.routers.health import router as health_router
from app.routers.upload import router as upload_router
from app.utils.logger import logger, log_request, log_error

app = FastAPI(
    title=settings.APP_NAME,
    description="API para el sistema de pedidos de Solandre",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    contact={
        "name": "Solandre Team",
        "email": "soporte@solandre.com",
    }
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para registrar todas las requests"""
    start_time = time.time()

    # Log de request entrante
    logger.info(f"➡️  {request.method} {request.url.path}")

    try:
        response = await call_next(request)

        # Calcular duración
        duration = (time.time() - start_time) * 1000  # en milisegundos

        # Log de respuesta
        log_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration
        )

        return response

    except Exception as e:
        # Log de error
        duration = (time.time() - start_time) * 1000
        log_error(e, context=f"{request.method} {request.url.path}")

        # Retornar error 500
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Error interno del servidor",
                "path": request.url.path
            }
        )


# Event handlers
@app.on_event("startup")
async def startup_event():
    """Se ejecuta al iniciar la aplicación"""
    logger.info("🚀 Iniciando Solandre API...")
    logger.info(f"📌 Versión: {settings.APP_VERSION}")
    logger.info(f"🔧 Modo: {'Desarrollo' if settings.DEBUG else 'Producción'}")


@app.on_event("shutdown")
async def shutdown_event():
    """Se ejecuta al apagar la aplicación"""
    logger.info("🛑 Apagando Solandre API...")


# Incluir routers
app.include_router(health_router)  # Primero health (sin prefix)
app.include_router(auth_router)
app.include_router(catalogo_router)
app.include_router(pedido_router)
app.include_router(cocina_router)
app.include_router(delivery_router)
app.include_router(admin_router)
app.include_router(notificaciones_router)
app.include_router(role_router)
app.include_router(upload_router)


# Handler global de excepciones
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Maneja todas las excepciones no capturadas"""
    log_error(
        exc, context=f"Global handler - {request.method} {request.url.path}")

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "path": str(request.url.path)
        }
    )
