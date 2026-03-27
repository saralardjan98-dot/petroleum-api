"""
Tests d'intégration pour les endpoints principaux.
Utilise une base de données SQLite en mémoire pour l'isolation.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.session import get_db, Base

# Use SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def registered_user(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "Secret123",
        "full_name": "Test User",
    })
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def auth_headers(client, registered_user):
    resp = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "Secret123",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────
# Auth tests
# ─────────────────────────────────────────────

class TestAuth:
    def test_register_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "username": "newuser",
            "password": "Secret123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert data["role"] == "user"

    def test_register_duplicate_email(self, client, registered_user):
        resp = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "username": "other",
            "password": "Secret123",
        })
        assert resp.status_code == 400

    def test_login_success(self, client, registered_user):
        resp = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "Secret123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client, registered_user):
        resp = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_get_me(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"

    def test_protected_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 403


# ─────────────────────────────────────────────
# Well tests
# ─────────────────────────────────────────────

WELL_PAYLOAD = {
    "name": "Puits Alpha-1",
    "code": "ALPHA-001",
    "field": "Hassi Messaoud",
    "zone": "Triasique",
    "latitude": 31.7,
    "longitude": 6.1,
    "well_type": "exploration",
    "status": "active",
}


class TestWells:
    def test_create_well(self, client, auth_headers):
        resp = client.post("/api/v1/wells/", json=WELL_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "ALPHA-001"
        assert data["field"] == "Hassi Messaoud"

    def test_create_duplicate_code(self, client, auth_headers):
        client.post("/api/v1/wells/", json=WELL_PAYLOAD, headers=auth_headers)
        resp = client.post("/api/v1/wells/", json=WELL_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 400

    def test_list_wells(self, client, auth_headers):
        client.post("/api/v1/wells/", json=WELL_PAYLOAD, headers=auth_headers)
        resp = client.get("/api/v1/wells/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_well(self, client, auth_headers):
        create = client.post("/api/v1/wells/", json=WELL_PAYLOAD, headers=auth_headers)
        well_id = create.json()["id"]
        resp = client.get(f"/api/v1/wells/{well_id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_update_well(self, client, auth_headers):
        create = client.post("/api/v1/wells/", json=WELL_PAYLOAD, headers=auth_headers)
        well_id = create.json()["id"]
        resp = client.put(f"/api/v1/wells/{well_id}",
                          json={"status": "abandoned"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "abandoned"

    def test_delete_well(self, client, auth_headers):
        create = client.post("/api/v1/wells/", json=WELL_PAYLOAD, headers=auth_headers)
        well_id = create.json()["id"]
        resp = client.delete(f"/api/v1/wells/{well_id}", headers=auth_headers)
        assert resp.status_code == 204
        # Verify it's gone
        get = client.get(f"/api/v1/wells/{well_id}", headers=auth_headers)
        assert get.status_code == 404

    def test_filter_by_field(self, client, auth_headers):
        client.post("/api/v1/wells/", json=WELL_PAYLOAD, headers=auth_headers)
        resp = client.get("/api/v1/wells/?field=Hassi", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_map_endpoint(self, client, auth_headers):
        client.post("/api/v1/wells/", json=WELL_PAYLOAD, headers=auth_headers)
        resp = client.get("/api/v1/wells/map", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
