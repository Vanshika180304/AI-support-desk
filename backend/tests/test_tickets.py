"""Tests for ticket CRUD endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _create_user_and_login(client: AsyncClient, email: str) -> str:
    """Helper: create a user and return their JWT token."""
    await client.post(
        "/auth/signup",
        json={"email": email, "password": "SecurePass123!"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": email, "password": "SecurePass123!"},
    )
    return resp.json()["access_token"]


async def test_create_ticket_returns_202(
    client: AsyncClient, sample_ticket_data: dict
) -> None:
    token = await _create_user_and_login(client, "ticket_create@example.com")
    response = await client.post(
        "/tickets",
        json=sample_ticket_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert data["status"] == "open"
    assert data["category"] == "unclassified"


async def test_create_ticket_requires_auth(
    client: AsyncClient, sample_ticket_data: dict
) -> None:
    response = await client.post("/tickets", json=sample_ticket_data)
    assert response.status_code in (401, 403)


async def test_create_ticket_validates_body(client: AsyncClient) -> None:
    token = await _create_user_and_login(client, "ticket_validate@example.com")
    # Subject too short
    response = await client.post(
        "/tickets",
        json={"subject": "Hi", "body": "x" * 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_get_ticket_by_id(
    client: AsyncClient, sample_ticket_data: dict
) -> None:
    token = await _create_user_and_login(client, "ticket_get@example.com")
    create_resp = await client.post(
        "/tickets",
        json=sample_ticket_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["id"]

    get_resp = await client.get(
        f"/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == ticket_id
    assert data["subject"] == sample_ticket_data["subject"]
    # Should include at least the initial user message
    assert len(data["messages"]) >= 1
    assert data["messages"][0]["sender"] == "user"


async def test_list_tickets_pagination(
    client: AsyncClient, sample_ticket_data: dict
) -> None:
    token = await _create_user_and_login(client, "ticket_list@example.com")
    # Create 3 tickets
    for _ in range(3):
        await client.post(
            "/tickets",
            json=sample_ticket_data,
            headers={"Authorization": f"Bearer {token}"},
        )

    resp = await client.get(
        "/tickets?page=1&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    assert data["total"] == 3


async def test_escalate_ticket(
    client: AsyncClient, sample_ticket_data: dict
) -> None:
    token = await _create_user_and_login(client, "ticket_escalate@example.com")
    create_resp = await client.post(
        "/tickets",
        json=sample_ticket_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["id"]

    escalate_resp = await client.post(
        f"/tickets/{ticket_id}/escalate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert escalate_resp.status_code == 200
    assert escalate_resp.json()["status"] == "escalated"


async def test_ticket_not_found_returns_404(client: AsyncClient) -> None:
    token = await _create_user_and_login(client, "ticket_404@example.com")
    import uuid
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"/tickets/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_customer_cannot_see_other_users_ticket(
    client: AsyncClient, sample_ticket_data: dict
) -> None:
    token_a = await _create_user_and_login(client, "user_a@example.com")
    token_b = await _create_user_and_login(client, "user_b@example.com")

    create_resp = await client.post(
        "/tickets",
        json=sample_ticket_data,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    ticket_id = create_resp.json()["id"]

    # User B should not be able to see User A's ticket
    resp = await client.get(
        f"/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403
