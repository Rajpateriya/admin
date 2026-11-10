from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.product import Product, ProductStatus
from app.repositories.base import BaseMongoRepository


class ProductRepository(BaseMongoRepository[Product]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "products", Product)

    async def get_by_sku(self, sku: str) -> Optional[Product]:
        return await self.find_one({"sku": sku})

    async def get_by_slug(self, slug: str) -> Optional[Product]:
        return await self.find_one({"slug": slug})

    async def search_products(
        self,
        q: Optional[str] = None,
        category_id: Optional[str] = None,
        brand_id: Optional[str] = None,
        status: Optional[ProductStatus] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_featured: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: int = -1,
    ) -> Tuple[List[Product], int]:
        query: Dict[str, Any] = {}

        if q:
            query["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"sku": {"$regex": q, "$options": "i"}},
                {"tags": {"$regex": q, "$options": "i"}},
            ]

        if category_id:
            query["category_id"] = category_id
        if brand_id:
            query["brand_id"] = brand_id
        if status:
            query["status"] = status
        if is_featured is not None:
            query["is_featured"] = is_featured

        if min_price is not None or max_price is not None:
            price_query: Dict[str, Any] = {}
            if min_price is not None:
                price_query["$gte"] = min_price
            if max_price is not None:
                price_query["$lte"] = max_price
            query["base_price"] = price_query

        total = await self.count(query)
        items = await self.find_many(
            query=query,
            skip=skip,
            limit=limit,
            sort=[(sort_by, sort_order)],
        )
        return items, total

    async def get_low_stock_products(self, limit: int = 50) -> List[Product]:
        """Retrieve products whose stock is at or below their low stock threshold."""
        query = {
            "status": ProductStatus.PUBLISHED,
            "$expr": {"$lte": ["$stock_quantity", "$low_stock_threshold"]},
        }
        return await self.find_many(query, limit=limit, sort=[("stock_quantity", 1)])

    async def bulk_update_status(self, product_ids: List[str], status: ProductStatus) -> int:
        obj_ids = [self._parse_id(pid) for pid in product_ids]
        result = await self.collection.update_many(
            {"_id": {"$in": obj_ids}},
            {"$set": {"status": status.value}},
        )
        return result.modified_count

    async def update_stock(self, product_id: str, variant_id: Optional[str], delta: int) -> Optional[Product]:
        _id = self._parse_id(product_id)
        if variant_id:
            # Update specific variant stock and total stock
            result = await self.collection.find_one_and_update(
                {"_id": _id, "variants.id": variant_id},
                {
                    "$inc": {
                        "variants.$.stock_quantity": delta,
                        "stock_quantity": delta,
                    }
                },
                return_document=True,
            )
            return self._doc_to_model(result)
        else:
            # Update base product stock
            result = await self.collection.find_one_and_update(
                {"_id": _id},
                {"$inc": {"stock_quantity": delta}},
                return_document=True,
            )
            return self._doc_to_model(result)
