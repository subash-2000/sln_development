import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seeds import seed_initial_permissions_and_roles
from app.models.rbac import Role


@pytest.mark.asyncio
async def test_list_roles_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/roles")
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "MISSING_TOKEN"


@pytest.mark.asyncio
async def test_list_roles_forbidden(client: AsyncClient, user_token_headers: dict):
    response = await client.get("/api/v1/roles", headers=user_token_headers)
    assert response.status_code == 403
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_list_roles_superadmin(client: AsyncClient, superadmin_token_headers: dict):
    response = await client.get("/api/v1/roles", headers=superadmin_token_headers)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert isinstance(res["data"], list)
    assert len(res["data"]) >= 1
    codes = [r["code"] for r in res["data"]]
    assert "WAREHOUSE_MANAGER" in codes


@pytest.mark.asyncio
async def test_list_permissions_catalog(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token_headers: dict,
):
    await seed_initial_permissions_and_roles(db_session)
    response = await client.get("/api/v1/permissions", headers=superadmin_token_headers)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert len(res["data"]) > 0
    perm_codes = [p["code"] for p in res["data"]]
    assert "system.user.read" in perm_codes
    assert "inventory.move" in perm_codes


@pytest.mark.asyncio
async def test_create_custom_role(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    payload = {
        "code": "QC_INSPECTOR",
        "name": "Quality Control Inspector",
        "description": "Inspects incoming and outgoing goods for defects",
        "permission_ids": [str(seed_data["perm_inv_read"].id)],
    }
    response = await client.post("/api/v1/roles", json=payload, headers=superadmin_token_headers)
    assert response.status_code == 201
    res = response.json()
    assert res["success"] is True
    assert res["data"]["code"] == "QC_INSPECTOR"
    assert res["data"]["is_system_role"] is False
    assert len(res["data"]["permissions"]) == 1
    assert res["data"]["permissions"][0]["code"] == "inventory.read"


@pytest.mark.asyncio
async def test_create_duplicate_role_code(client: AsyncClient, superadmin_token_headers: dict):
    payload = {
        "code": "WAREHOUSE_MANAGER",
        "name": "Another Manager",
    }
    response = await client.post("/api/v1/roles", json=payload, headers=superadmin_token_headers)
    assert response.status_code == 409
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "ROLE_CODE_EXISTS"


@pytest.mark.asyncio
async def test_get_and_update_role(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    role_id = str(seed_data["role_mgr"].id)
    # Get details
    get_res = await client.get(f"/api/v1/roles/{role_id}", headers=superadmin_token_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["code"] == "WAREHOUSE_MANAGER"

    # Update role
    update_res = await client.put(
        f"/api/v1/roles/{role_id}",
        json={"name": "Senior Warehouse Manager", "description": "Updated description"},
        headers=superadmin_token_headers,
    )
    assert update_res.status_code == 200
    res = update_res.json()
    assert res["data"]["name"] == "Senior Warehouse Manager"
    assert res["data"]["description"] == "Updated description"


@pytest.mark.asyncio
async def test_assign_permissions_and_validation(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    role_id = str(seed_data["role_mgr"].id)

    # 1. Invalid permission ID test
    fake_id = str(uuid.uuid4())
    bad_res = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_ids": [fake_id]},
        headers=superadmin_token_headers,
    )
    assert bad_res.status_code == 400
    assert bad_res.json()["error_code"] == "INVALID_PERMISSION_IDS"

    # 2. Valid permission assignment
    valid_res = await client.post(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permission_ids": [str(seed_data["perm_inv_read"].id)]},
        headers=superadmin_token_headers,
    )
    assert valid_res.status_code == 200
    assert len(valid_res.json()["data"]["permissions"]) == 1


@pytest.mark.asyncio
async def test_delete_role_and_system_protection(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token_headers: dict,
):
    # 1. System role cannot be deleted
    sys_role = Role(
        id=uuid.uuid4(),
        code="TEST_SYS_ROLE",
        name="System Protected",
        is_system_role=True,
    )
    db_session.add(sys_role)
    await db_session.commit()

    sys_res = await client.delete(f"/api/v1/roles/{sys_role.id}", headers=superadmin_token_headers)
    assert sys_res.status_code == 400
    assert sys_res.json()["error_code"] == "SYSTEM_ROLE_PROTECTED"

    # 2. Custom role can be deleted
    custom_role = Role(
        id=uuid.uuid4(),
        code="TEMP_CUSTOM_ROLE",
        name="Temporary Role",
        is_system_role=False,
    )
    db_session.add(custom_role)
    await db_session.commit()

    del_res = await client.delete(
        f"/api/v1/roles/{custom_role.id}", headers=superadmin_token_headers
    )
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 3. Verify it is deleted
    get_res = await client.get(f"/api/v1/roles/{custom_role.id}", headers=superadmin_token_headers)
    assert get_res.status_code == 404
