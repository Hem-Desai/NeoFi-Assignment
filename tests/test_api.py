import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import json
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.db.repositories.user import UserRepository
from app.db.repositories.event import EventRepository
from app.db.repositories.permission import PermissionRepository
from app.schemas.user import UserCreate
from app.schemas.event import EventCreate, EventUpdate
from app.schemas.permission import PermissionCreate, PermissionUpdate

client = TestClient(app)


@pytest.mark.asyncio
async def test_root():
    """Test root endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to the Collaborative Event Management System API"}


@pytest.mark.asyncio
async def test_auth_flow(db: AsyncSession):
    user_repo = UserRepository()
    
    test_user = UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )
    
    response = client.post("/api/auth/register", json=test_user.dict())
    assert response.status_code == 201
    user_data = response.json()
    assert user_data["username"] == test_user.username
    assert user_data["email"] == test_user.email
    
    response = client.post(
        "/api/auth/login",
        data={"username": test_user.username, "password": test_user.password}
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": token_data["refresh_token"]}
    )
    assert response.status_code == 200
    new_token_data = response.json()
    assert "access_token" in new_token_data
    assert "refresh_token" in new_token_data
    
    response = client.post("/api/auth/logout")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_event_flow(db: AsyncSession):
    user_repo = UserRepository()
    event_repo = EventRepository()
    
    test_user = UserCreate(
        username="eventuser",
        email="event@example.com",
        password="testpass123"
    )
    
    response = client.post("/api/auth/register", json=test_user.dict())
    assert response.status_code == 201
    user_data = response.json()
    
    response = client.post(
        "/api/auth/login",
        data={"username": test_user.username, "password": test_user.password}
    )
    assert response.status_code == 200
    token_data = response.json()
    
    test_event = EventCreate(
        title="Test Event",
        description="Test Description",
        start_time="2024-01-01T10:00:00Z",
        end_time="2024-01-01T11:00:00Z",
        location="Test Location"
    )
    
    response = client.post(
        "/api/events",
        json=test_event.dict(),
        headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert response.status_code == 201
    event_data = response.json()
    assert event_data["title"] == test_event.title
    
    response = client.get(
        f"/api/events/{event_data['id']}",
        headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert response.status_code == 200
    retrieved_event = response.json()
    assert retrieved_event["id"] == event_data["id"]
    
    update_data = EventUpdate(
        title="Updated Event",
        description="Updated Description"
    )
    
    response = client.put(
        f"/api/events/{event_data['id']}",
        json=update_data.dict(exclude_unset=True),
        headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert response.status_code == 200
    updated_event = response.json()
    assert updated_event["title"] == update_data.title
    
    response = client.get(
        f"/api/events/{event_data['id']}/history",
        headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert response.status_code == 200
    history = response.json()
    assert len(history) > 0
    
    response = client.get(
        f"/api/events/{event_data['id']}/changelog",
        headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert response.status_code == 200
    changelog = response.json()
    assert len(changelog) > 0
    
    response = client.get(
        f"/api/events/{event_data['id']}/diff/1/2",
        headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert response.status_code == 200
    diff = response.json()
    assert len(diff) > 0
    
    response = client.delete(
        f"/api/events/{event_data['id']}",
        headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_collaboration_flow(db: AsyncSession):
    user_repo = UserRepository()
    event_repo = EventRepository()
    permission_repo = PermissionRepository()
    
    user1 = UserCreate(
        username="user1",
        email="user1@example.com",
        password="testpass123"
    )
    
    user2 = UserCreate(
        username="user2",
        email="user2@example.com",
        password="testpass123"
    )
    
    response = client.post("/api/auth/register", json=user1.dict())
    assert response.status_code == 201
    user1_data = response.json()
    
    response = client.post("/api/auth/register", json=user2.dict())
    assert response.status_code == 201
    user2_data = response.json()
    
    response = client.post(
        "/api/auth/login",
        data={"username": user1.username, "password": user1.password}
    )
    assert response.status_code == 200
    user1_token = response.json()
    
    response = client.post(
        "/api/auth/login",
        data={"username": user2.username, "password": user2.password}
    )
    assert response.status_code == 200
    user2_token = response.json()
    
    test_event = EventCreate(
        title="Collaborative Event",
        description="Test Description",
        start_time="2024-01-01T10:00:00Z",
        end_time="2024-01-01T11:00:00Z",
        location="Test Location"
    )
    
    response = client.post(
        "/api/events",
        json=test_event.dict(),
        headers={"Authorization": f"Bearer {user1_token['access_token']}"}
    )
    assert response.status_code == 201
    event_data = response.json()
    
    response = client.get(
        f"/api/events/{event_data['id']}",
        headers={"Authorization": f"Bearer {user2_token['access_token']}"}
    )
    assert response.status_code == 403
    
    share_data = PermissionCreate(
        user_id=user2_data["id"],
        role="EDITOR"
    )
    
    response = client.post(
        f"/api/events/{event_data['id']}/share",
        json=share_data.dict(),
        headers={"Authorization": f"Bearer {user1_token['access_token']}"}
    )
    assert response.status_code == 200
    
    response = client.get(
        f"/api/events/{event_data['id']}",
        headers={"Authorization": f"Bearer {user2_token['access_token']}"}
    )
    assert response.status_code == 200
    
    update_data = EventUpdate(
        title="Updated by User2",
        description="Updated Description"
    )
    
    response = client.put(
        f"/api/events/{event_data['id']}",
        json=update_data.dict(exclude_unset=True),
        headers={"Authorization": f"Bearer {user2_token['access_token']}"}
    )
    assert response.status_code == 200
    
    update_permission = PermissionUpdate(role="VIEWER")
    
    response = client.put(
        f"/api/events/{event_data['id']}/permissions/{user2_data['id']}",
        json=update_permission.dict(),
        headers={"Authorization": f"Bearer {user1_token['access_token']}"}
    )
    assert response.status_code == 200
    
    response = client.put(
        f"/api/events/{event_data['id']}",
        json=update_data.dict(exclude_unset=True),
        headers={"Authorization": f"Bearer {user2_token['access_token']}"}
    )
    assert response.status_code == 403
    
    response = client.delete(
        f"/api/events/{event_data['id']}/permissions/{user2_data['id']}",
        headers={"Authorization": f"Bearer {user1_token['access_token']}"}
    )
    assert response.status_code == 200
    
    response = client.get(
        f"/api/events/{event_data['id']}",
        headers={"Authorization": f"Bearer {user2_token['access_token']}"}
    )
    assert response.status_code == 403
