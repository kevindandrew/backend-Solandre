import sys
from fastapi.testclient import TestClient
from app.main import app
from app.utils.dependencies import get_current_user
from app.models.usuario import Usuario
import random

# Mock admin user
def mock_get_current_user():
    return Usuario(usuario_id=1, email="admin@solandre.com", rol_id=1, nombre_completo="Admin")

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

def test_create_ingredient():
    print("Testing create ingredient endpoint...", flush=True)

    try:
        # Generate random name to avoid unique constraint error
        ing_name = f"Ingrediente Test {random.randint(1000, 9999)}"
        
        payload = {
            "nombre": ing_name,
            "stock_actual": 10.5,
            "unidad_medida": "kg",
            "stock_minimo": 2.0
        }

        print(f"\n[TEST] POST /admin/ingredientes with payload: {payload}", flush=True)
        response = client.post("/admin/ingredientes", json=payload)
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Success! Ingrediente created: {data['nombre']}", flush=True)
            # Verify if response includes new fields (it might not if IngredienteResponse wasn't updated)
            print(f"Response: {data}", flush=True)
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}", flush=True)

    except Exception as e:
        print(f"❌ Exception: {e}", flush=True)

if __name__ == "__main__":
    test_create_ingredient()
