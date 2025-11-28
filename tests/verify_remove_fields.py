import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import get_db
from sqlmodel import SQLModel
from app.models.usuario import Usuario
from app.models.ingrediente import Ingrediente
from app.utils.security import create_access_token

# Setup test DB
if os.path.exists("./test_verify_remove.db"):
    os.remove("./test_verify_remove.db")

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_verify_remove.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def log(msg):
    print(msg)
    with open("verify_remove_output.txt", "a") as f:
        f.write(msg + "\n")

def verify_fix():
    # Create tables
    SQLModel.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create admin user
    admin = Usuario(
        email="admin@test.com",
        password_hash="hash",
        nombre_completo="Admin Test",
        rol_id=1
    )
    db.add(admin)
    db.commit()
    
    # Create dummy ingredient
    ingrediente = Ingrediente(
        nombre="Tomate",
        stock_actual=10.0
    )
    db.add(ingrediente)
    db.commit()
    db.refresh(ingrediente)

    # Get token
    token = create_access_token(data={"sub": admin.email})
    headers = {"Authorization": f"Bearer {token}"}

    log(f"Testing PUT /admin/ingredientes/{ingrediente.ingrediente_id}")
    
    # Payload WITHOUT unidad_medida and stock_minimo
    payload = {
        "nombre": "Tomate Cherry",
        "stock_actual": 15.0
    }
    
    response = client.put(
        f"/admin/ingredientes/{ingrediente.ingrediente_id}",
        json=payload,
        headers=headers
    )
    
    log(f"Status Code: {response.status_code}")
    log(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        if data["nombre"] == "Tomate Cherry" and data["stock_actual"] == 15.0:
             log("PASS: Ingredient updated successfully without extra fields")
        else:
             log("FAIL: Data mismatch")
    else:
        log("FAIL: Status code not 200")

    # Cleanup
    SQLModel.metadata.drop_all(bind=engine)
    db.close()

if __name__ == "__main__":
    if os.path.exists("verify_remove_output.txt"):
        os.remove("verify_remove_output.txt")
    try:
        verify_fix()
    except Exception as e:
        log(f"Error: {e}")
