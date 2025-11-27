import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_public_endpoints():
    print("Testing public endpoints...", flush=True)

    try:
        # 1. Test GET /catalogo/platos
        print("\n[TEST] GET /catalogo/platos", flush=True)
        response = client.get("/catalogo/platos")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Platos found: {len(data)}", flush=True)
            if data:
                print(f"Sample Plato: {data[0]['nombre']}", flush=True)
                print(f"Ingredientes: {data[0].get('ingredientes', 'MISSING')}", flush=True)
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}", flush=True)

    except Exception as e:
        print(f"❌ Exception: {e}", flush=True)

if __name__ == "__main__":
    test_public_endpoints()
