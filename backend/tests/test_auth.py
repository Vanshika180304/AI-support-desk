"""Tests for auth endpoints: signup, login, JWT validation."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_signup_creates_user(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/signup",
        json={"email": "newuser@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "customer"
    assert "id" in data


async def test_signup_duplicate_email_returns_409(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "password": "SecurePass123!"}
    await client.post("/auth/signup", json=payload)
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 409


async def test_signup_short_password_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/signup",
        json={"email": "short@example.com", "password": "abc"},
    )
    assert response.status_code == 422  # Pydantic validation error


async def test_login_returns_jwt(client: AsyncClient) -> None:
    # First create user
    await client.post(
        "/auth/signup",
        json={"email": "logintest@example.com", "password": "SecurePass123!"},
    )
    # Then login
    response = await client.post(
        "/auth/login",
        json={"email": "logintest@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post(
        "/auth/signup",
        json={"email": "wrongpw@example.com", "password": "SecurePass123!"},
    )
    response = await client.post(
        "/auth/login",
        json={"email": "wrongpw@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401


async def test_me_returns_profile(client: AsyncClient) -> None:
    # Create and login
    await client.post(
        "/auth/signup",
        json={"email": "me@example.com", "password": "SecurePass123!"},
    )
    login = await client.post(
        "/auth/login",
        json={"email": "me@example.com", "password": "SecurePass123!"},
    )
    token = login.json()["access_token"]

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


async def test_protected_route_without_token_returns_403(client: AsyncClient) -> None:
    response = await client.get("/tickets")
    # 403 (no credentials) or 401 — both are acceptable
    assert response.status_code in (401, 403)
