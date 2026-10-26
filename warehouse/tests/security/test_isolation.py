import pytest
from fastapi import APIRouter, Depends
from httpx import AsyncClient

from app.core.dependencies import (
    TenantContext,
    get_current_tenant_context,
    require_permission,
)
from app.core.response import success_response
from app.main import app
from app.models.user import User

# Ephemeral test router to test tenant context dependencies
security_test_router = APIRouter(prefix="/api/v1/test-security", tags=["Security Testing"])


@security_test_router.get("/tenant-scope")
async def handle_tenant_scope_endpoint(
    context: TenantContext = Depends(get_current_tenant_context),
):
    return success_response(
        data={
            "user_id": str(context.user_id),
            "company_id": str(context.company_id) if context.company_id else None,
            "branch_id": str(context.branch_id) if context.branch_id else None,
            "is_global": context.is_global_access,
        },
        message="Tenant access granted",
    )


@security_test_router.get("/inventory-read-permission")
async def handle_permission_endpoint(
    current_user: User = Depends(require_permission("inventory.read")),
):
    return success_response(
        data={"user": current_user.username},
        message="Permission granted",
    )


@security_test_router.get("/billing-write-permission")
async def handle_billing_permission_endpoint(
    current_user: User = Depends(require_permission("billing.write")),
):
    return success_response(
        data={"user": current_user.username},
        message="Permission granted",
    )


# Mount router once
app.include_router(security_test_router)


@pytest.mark.asyncio
async def test_authorized_company_and_branch_access(client: AsyncClient, seed_data: dict):
    # User Alpha has access to Company A and Branch A1
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_alpha", "password": "UserAlphaPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]
    company_a_id = str(seed_data["company_a"].id)
    branch_a1_id = str(seed_data["branch_a1"].id)

    response = await client.get(
        "/api/v1/test-security/tenant-scope",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Company-ID": company_a_id,
            "X-Branch-ID": branch_a1_id,
        },
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert res["data"]["company_id"] == company_a_id
    assert res["data"]["branch_id"] == branch_a1_id
    assert res["data"]["is_global"] is False


@pytest.mark.asyncio
async def test_cross_company_tampering_rejected_with_403(client: AsyncClient, seed_data: dict):
    """User Alpha belongs to Company A; requesting Company B header MUST be rejected with 403."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_alpha", "password": "UserAlphaPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]
    company_b_id = str(seed_data["company_b"].id)

    response = await client.get(
        "/api/v1/test-security/tenant-scope",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Company-ID": company_b_id,
        },
    )
    assert response.status_code == 403
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "CROSS_TENANT_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_cross_branch_tampering_rejected_with_403(client: AsyncClient, seed_data: dict):
    """User Alpha belongs to Branch A1; requesting Branch B1 or Branch A2 (unauthorized) MUST be rejected."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_alpha", "password": "UserAlphaPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]
    company_a_id = str(seed_data["company_a"].id)
    branch_b1_id = str(seed_data["branch_b1"].id)

    response = await client.get(
        "/api/v1/test-security/tenant-scope",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Company-ID": company_a_id,
            "X-Branch-ID": branch_b1_id,
        },
    )
    assert response.status_code == 403
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "CROSS_TENANT_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_superuser_global_access(client: AsyncClient, seed_data: dict):
    """Superuser can access any company or branch context."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "test_superadmin", "password": "SuperSecret123!"},
    )
    token = login_res.json()["data"]["access_token"]
    company_b_id = str(seed_data["company_b"].id)

    response = await client.get(
        "/api/v1/test-security/tenant-scope",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Company-ID": company_b_id,
        },
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert res["data"]["is_global"] is True


@pytest.mark.asyncio
async def test_permission_checker_granted(client: AsyncClient, seed_data: dict):
    """User Alpha has inventory.read permission via WAREHOUSE_MANAGER role."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_alpha", "password": "UserAlphaPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]

    response = await client.get(
        "/api/v1/test-security/inventory-read-permission",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True


@pytest.mark.asyncio
async def test_permission_checker_forbidden(client: AsyncClient, seed_data: dict):
    """User Alpha DOES NOT have billing.write permission; request must return 403."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_alpha", "password": "UserAlphaPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]

    response = await client.get(
        "/api/v1/test-security/billing-write-permission",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "INSUFFICIENT_PERMISSIONS"
