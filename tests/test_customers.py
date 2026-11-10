import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_customer_crud_and_moderation(client: AsyncClient, superadmin_headers, order_headers):
    # 1. Create Customer
    payload = {
        "email": "bruce.wayne@waynecorp.com",
        "first_name": "Bruce",
        "last_name": "Wayne",
        "phone": "+1  Gotham-001",
        "tags": ["VIP", "Corporate"],
        "addresses": [
            {
                "first_name": "Bruce",
                "last_name": "Wayne",
                "address_line1": "1007 Mountain Drive",
                "city": "Gotham",
                "state": "NJ",
                "postal_code": "07001",
                "country": "US",
                "is_default": True,
            }
        ],
    }
    create_res = await client.post("/api/v1/customers", json=payload, headers=superadmin_headers)
    assert create_res.status_code == 200
    cust = create_res.json()
    customer_id = cust["id"]
    assert cust["email"] == "bruce.wayne@waynecorp.com"
    assert "VIP" in cust["tags"]

    # 2. Duplicate email rejected
    dup_res = await client.post("/api/v1/customers", json=payload, headers=superadmin_headers)
    assert dup_res.status_code == 409

    # 3. Update customer info & tags
    update_res = await client.put(
        f"/api/v1/customers/{customer_id}",
        json={"phone": "+1 212-555-0199", "tags": ["VIP", "High-Value"]},
        headers=superadmin_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["phone"] == "+1 212-555-0199"
    assert "High-Value" in update_res.json()["tags"]

    # 4. Moderate Status (ACTIVE -> FLAGGED -> SUSPENDED)
    mod_res = await client.patch(
        f"/api/v1/customers/{customer_id}/status",
        json={"status": "FLAGGED"},
        headers=superadmin_headers,
    )
    assert mod_res.status_code == 200
    assert mod_res.json()["status"] == "FLAGGED"

    # 5. Add internal CRM note
    note_res = await client.post(
        f"/api/v1/customers/{customer_id}/notes",
        json={"note": "Account flagged for unusual payment location; verified identity by phone."},
        headers=superadmin_headers,
    )
    assert note_res.status_code == 200
    assert len(note_res.json()["internal_notes"]) >= 1

    # 6. List and filter customers
    list_res = await client.get("/api/v1/customers?q=Wayne&status=FLAGGED", headers=superadmin_headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1
    assert list_res.json()["items"][0]["email"] == "bruce.wayne@waynecorp.com"

    # 7. Delete Customer (no orders yet, should succeed)
    del_res = await client.delete(f"/api/v1/customers/{customer_id}", headers=superadmin_headers)
    assert del_res.status_code == 200

    # Verify deleted
    get_res = await client.get(f"/api/v1/customers/{customer_id}", headers=superadmin_headers)
    assert get_res.status_code == 404
