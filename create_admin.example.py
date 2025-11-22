"""
Script de ejemplo para crear usuario administrador.

IMPORTANTE: 
1. Copia este archivo a create_admin.py
2. Completa las credenciales
3. Ejecuta: python create_admin.py
4. ELIMINA create_admin.py después de usarlo

NO SUBAS create_admin.py a GitHub con credenciales reales.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.usuario import Usuario
from app.models.role import Role
from app.utils.security import get_password_hash
from app.config import settings

# Usar variables de entorno o cambiar estos valores
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@solandre.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "CAMBIAR_ESTO")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Administrador")
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "00000000")


def crear_admin():
    """Crea un usuario administrador en la base de datos"""

    # Conectar a la base de datos
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Verificar si ya existe un admin
        admin_existente = db.query(Usuario).filter(
            Usuario.email == ADMIN_EMAIL
        ).first()

        if admin_existente:
            print(f"❌ Ya existe un usuario con email {ADMIN_EMAIL}")
            return

        # Verificar que el rol Admin existe
        rol_admin = db.query(Role).filter(Role.rol_id == 1).first()
        if not rol_admin:
            print("❌ El rol de Administrador no existe en la base de datos")
            print("   Ejecuta primero: python -m app.init_roles")
            return

        # Crear admin
        nuevo_admin = Usuario(
            email=ADMIN_EMAIL,
            password_hash=get_password_hash(ADMIN_PASSWORD),
            nombre_completo=ADMIN_NAME,
            telefono=ADMIN_PHONE,
            rol_id=1  # 1 = Administrador
        )

        db.add(nuevo_admin)
        db.commit()
        db.refresh(nuevo_admin)

        print("✅ Usuario administrador creado exitosamente!")
        print(f"   Email: {ADMIN_EMAIL}")
        print(f"   Nombre: {ADMIN_NAME}")
        print("\n⚠️  IMPORTANTE: Elimina este archivo después de usarlo")
        print("   O al menos no lo subas a GitHub con credenciales reales")

    except Exception as e:
        print(f"❌ Error al crear administrador: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Verificar que se cambiaron las credenciales
    if ADMIN_PASSWORD == "CAMBIAR_ESTO":
        print("❌ ERROR: Debes cambiar las credenciales antes de ejecutar")
        print("   Edita este archivo o usa variables de entorno:")
        print("   $env:ADMIN_EMAIL='tu@email.com'")
        print("   $env:ADMIN_PASSWORD='tu_password'")
        print("   python create_admin.py")
    else:
        crear_admin()
