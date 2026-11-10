import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_category_lifecycle_and_tree(client: AsyncClient, catalog_headers):
    # 1. Create parent category
    parent_res = await client.post(
        "/api/v1/categories",
        json={"name": "Computers & Laptops", "description": "Computing devices"},
        headers=catalog_headers,
    )
    assert parent_res.status_code == 200
    parent_data = parent_res.json()
    parent_id = parent_data["id"]
    assert parent_data["slug"] == "computers-laptops"

    # 2. Duplicate slug conflict
    dup_res = await client.post(
        "/api/v1/categories",
        json={"name": "Computers & Laptops"},
        headers=catalog_headers,
    )
    assert dup_res.status_code == 409

    # 3. Create child category
    child_res = await client.post(
        "/api/v1/categories",
        json={"name": "Gaming Laptops", "parent_id": parent_id},
        headers=catalog_headers,
    )
    assert child_res.status_code == 200
    child_id = child_res.json()["id"]

    # 4. Fetch category tree
    tree_res = await client.get("/api/v1/categories/tree", headers=catalog_headers)
    assert tree_res.status_code == 200
    tree_data = tree_res.json()
    assert any(c["id"] == parent_id and len(c["children"]) > 0 for c in tree_data)

    # 5. Prevent deleting parent with active children
    del_parent_res = await client.delete(f"/api/v1/categories/{parent_id}", headers=catalog_headers)
    assert del_parent_res.status_code == 400
    assert "subcategories" in del_parent_res.json()["message"].lower()

    # 6. Delete child then parent
    del_child = await client.delete(f"/api/v1/categories/{child_id}", headers=catalog_headers)
    assert del_child.status_code == 200

    del_parent = await client.delete(f"/api/v1/categories/{parent_id}", headers=catalog_headers)
    assert del_parent.status_code == 200


@pytest.mark.asyncio
async def test_brand_crud(client: AsyncClient, catalog_headers):
    # Create brand
    create_res = await client.post(
        "/api/v1/brands",
        json={"name": "Logitech", "website": "https://logitech.com"},
        headers=catalog_headers,
    )
    assert create_res.status_code == 200
    brand_data = create_res.json()
    brand_id = brand_data["id"]
    assert brand_data["slug"] == "logitech"

    # Duplicate brand slug conflict
    dup_res = await client.post(
        "/api/v1/brands",
        json={"name": "Logitech"},
        headers=catalog_headers,
    )
    assert dup_res.status_code == 409

    # Update brand
    put_res = await client.put(
        f"/api/v1/brands/{brand_id}",
        json={"name": "Logitech G Gaming"},
        headers=catalog_headers,
    )
    assert put_res.status_code == 200
    assert put_res.json()["name"] == "Logitech G Gaming"

    # List brands
    list_res = await client.get("/api/v1/brands", headers=catalog_headers)
    assert list_res.status_code == 200
    assert any(b["id"] == brand_id for b in list_res.json())

    # Delete brand
    del_res = await client.delete(f"/api/v1/brands/{brand_id}", headers=catalog_headers)
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_product_crud_and_search(client: AsyncClient, catalog_headers):
    # 1. Create Category
    cat_res = await client.post(
        "/api/v1/categories",
        json={"name": "Peripherals"},
        headers=catalog_headers,
    )
    category_id = cat_res.json()["id"]

    # 2. Create Product with Variants
    product_payload = {
        "title": "Logitech MX Master 3S",
        "sku": "LOGI-MX3S-BASE",
        "description": "Quiet clicks 8K DPI wireless mouse",
        "base_price": 99.99,
        "compare_at_price": 109.99,
        "category_id": category_id,
        "low_stock_threshold": 5,
        "variants": [
            {
                "title": "Space Gray",
                "sku": "LOGI-MX3S-GRY",
                "price": 99.99,
                "stock_quantity": 25,
                "attributes": {"color": "Space Gray"},
            },
            {
                "title": "Pale Gray",
                "sku": "LOGI-MX3S-WHT",
                "price": 99.99,
                "stock_quantity": 15,
                "attributes": {"color": "Pale Gray"},
            },
        ],
        "tags": ["mouse", "wireless", "logitech", "office"],
        "is_featured": True,
    }

    create_res = await client.post("/api/v1/products", json=product_payload, headers=catalog_headers)
    assert create_res.status_code == 200
    pdata = create_res.json()
    product_id = pdata["id"]
    assert pdata["stock_quantity"] == 40  # 25 + 15
    assert len(pdata["variants"]) == 2

    # 3. Duplicate SKU conflict
    dup_res = await client.post("/api/v1/products", json=product_payload, headers=catalog_headers)
    assert dup_res.status_code == 409

    # 4. Search products with query
    search_res = await client.get("/api/v1/products?q=Master", headers=catalog_headers)
    assert search_res.status_code == 200
    assert search_res.json()["total"] >= 1
    assert search_res.json()["items"][0]["sku"] == "LOGI-MX3S-BASE"

    # 5. Filter by price range
    filter_res = await client.get("/api/v1/products?min_price=50&max_price=120", headers=catalog_headers)
    assert filter_res.status_code == 200
    assert any(p["id"] == product_id for p in filter_res.json()["items"])

    # 6. Bulk status update
    bulk_res = await client.post(
        "/api/v1/products/bulk-status",
        json={"product_ids": [product_id], "status": "PUBLISHED"},
        headers=catalog_headers,
    )
    assert bulk_res.status_code == 200

    # Verify published
    get_res = await client.get(f"/api/v1/products/{product_id}", headers=catalog_headers)
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "PUBLISHED"

    # 7. Category deletion blocked because product is linked
    cat_del_res = await client.delete(f"/api/v1/categories/{category_id}", headers=catalog_headers)
    assert cat_del_res.status_code == 400
    assert "products" in cat_del_res.json()["message"].lower()

    # 8. Delete product
    del_prod = await client.delete(f"/api/v1/products/{product_id}", headers=catalog_headers)
    assert del_prod.status_code == 200
