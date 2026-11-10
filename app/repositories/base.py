from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from app.models.base import BaseMongoModel

T = TypeVar("T", bound=BaseMongoModel)


class BaseMongoRepository(Generic[T]):
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str, model_cls: Type[T]):
        self.db = db
        self.collection_name = collection_name
        self.collection: AsyncIOMotorCollection = db[collection_name]
        self.model_cls = model_cls

    def _parse_id(self, id_str: str) -> Any:
        if ObjectId.is_valid(id_str):
            return ObjectId(id_str)
        return id_str

    def _doc_to_model(self, doc: Optional[Dict[str, Any]]) -> Optional[T]:
        if not doc:
            return None
        # Convert ObjectId _id to string for Pydantic if needed
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return self.model_cls(**doc)

    async def get_by_id(self, id_str: str) -> Optional[T]:
        _id = self._parse_id(id_str)
        doc = await self.collection.find_one({"_id": _id})
        return self._doc_to_model(doc)

    async def find_one(self, query: Dict[str, Any]) -> Optional[T]:
        doc = await self.collection.find_one(query)
        return self._doc_to_model(doc)

    async def find_many(
        self,
        query: Dict[str, Any],
        skip: int = 0,
        limit: int = 20,
        sort: Optional[List[Tuple[str, int]]] = None,
        projection: Optional[Dict[str, int]] = None,
    ) -> List[T]:
        cursor = self.collection.find(query, projection)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)

        docs = await cursor.to_list(length=limit)
        return [self._doc_to_model(doc) for doc in docs if doc]

    async def count(self, query: Dict[str, Any]) -> int:
        return await self.collection.count_documents(query)

    async def create(self, model: T) -> T:
        doc = model.to_mongo()
        result = await self.collection.insert_one(doc)
        model.id = str(result.inserted_id)
        return model

    async def update(self, id_str: str, update_data: Dict[str, Any]) -> Optional[T]:
        _id = self._parse_id(id_str)
        update_data["updated_at"] = datetime.now(timezone.utc)
        doc = await self.collection.find_one_and_update(
            {"_id": _id},
            {"$set": update_data},
            return_document=True,
        )
        return self._doc_to_model(doc)

    async def delete(self, id_str: str) -> bool:
        _id = self._parse_id(id_str)
        result = await self.collection.delete_one({"_id": _id})
        return result.deleted_count > 0

    async def exists(self, query: Dict[str, Any]) -> bool:
        doc = await self.collection.find_one(query, {"_id": 1})
        return doc is not None
