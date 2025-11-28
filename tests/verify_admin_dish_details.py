import sys
from fastapi.testclient import TestClient
from app.main import app
from app.utils.dependencies import get_current_user
from app.models.usuario import Usuario

# Mock admin user
def mock_get_current_user():
    return Usuario(usuario_id=1, email="admin@solandre.com", rol_id=1, nombre_completo="Admin")

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

def test_admin_dish_details():
    print("Testing admin dish details endpoint...", flush=True)

    try:
        # 1. Get list of dishes to find a valid ID
        print("\n[TEST] Getting list of dishes to find an ID...", flush=True)
        response = client.get("/admin/platos")
        if response.status_code != 200:
            print(f"❌ Failed to list dishes: {response.status_code}", flush=True)
            return

        platos = response.json()
        if not platos:
            print("⚠️ No dishes found to test.", flush=True)
            return

        plato_id = platos[0]['plato_id']
        print(f"Testing with Plato ID: {plato_id}", flush=True)

        # 2. Test GET /admin/platos/{plato_id}
        print(f"\n[TEST] GET /admin/platos/{plato_id}", flush=True)
        response = client.get(f"/admin/platos/{plato_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Plato found: {data['nombre']}", flush=True)
            print(f"Ingredientes: {len(data.get('ingredientes', []))}", flush=True)
            for ing in data.get('ingredientes', []):
                print(f" - {ing['nombre']}: {ing['cantidad_requerida']} {ing.get('unidad_medida') or ''}", flush=True)
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}", flush=True)

    except Exception as e:
        print(f"❌ Exception: {e}", flush=True)

if __name__ == "__main__":
    test_admin_dish_details()
