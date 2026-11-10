from datetime import datetime, timezone
from typing import Annotated, Any, Dict, Optional
from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def validate_object_id(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        if ObjectId.is_valid(v):
            return v
        return v
    raise ValueError("Invalid ObjectId representation")


PyObjectId = Annotated[str, BeforeValidator(validate_object_id)]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BaseMongoModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    def to_mongo(self) -> Dict[str, Any]:
        """Convert Pydantic model into a dictionary suitable for MongoDB insertion/updating."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in data and isinstance(data["_id"], str) and ObjectId.is_valid(data["_id"]):
            data["_id"] = ObjectId(data["_id"])
        return data
