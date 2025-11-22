from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from app.config import settings

# Crear el engine de SQLAlchemy usando la configuración
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,  # Verifica conexiones antes de usarlas
    pool_size=5,  # Número de conexiones en el pool
    max_overflow=10  # Conexiones adicionales permitidas
)

# Crear la sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency para obtener la sesión de base de datos


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
