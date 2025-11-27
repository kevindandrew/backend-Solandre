from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_public_endpoints():
    print("Testing public endpoints...")

    # 1. Test GET /catalogo/zonas
    print("\n[TEST] GET /catalogo/zonas")
    response = client.get("/catalogo/zonas")
    if response.status_code == 200:
        print("✅ Success! Zonas found:", len(response.json()))
        print("Sample:", response.json()[0] if response.json() else "Empty list")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

    # 2. Test GET /catalogo/platos
    print("\n[TEST] GET /catalogo/platos")
    response = client.get("/catalogo/platos")
    if response.status_code == 200:
        print("✅ Success! Platos found:", len(response.json()))
        print("Sample:", response.json()[0] if response.json() else "Empty list")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

    # 3. Test GET /catalogo/menus (NEW)
    print("\n[TEST] GET /catalogo/menus")
    response = client.get("/catalogo/menus")
    if response.status_code == 200:
        print("✅ Success! Menus found:", len(response.json()))
        print("Sample:", response.json()[0] if response.json() else "Empty list")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_public_endpoints()
