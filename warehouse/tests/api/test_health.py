import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Service is operational"
    assert data["data"]["status"] == "healthy"
    assert data["data"]["app_name"] == "SLN Warehouse Management System"

    # Verify middleware response headers
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers
    assert data["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_ping_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/ping")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["ping"] == "pong"
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_custom_incoming_request_id_propagated(client: AsyncClient):
    custom_req_id = "custom-client-trace-id-12345"
    response = await client.get("/health", headers={"X-Request-ID": custom_req_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_req_id
    assert response.json()["request_id"] == custom_req_id
