from typing import Optional
from pydantic import Field
from app.models.base import BaseMongoModel


class Category(BaseMongoModel):
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[str] = None  # Self-referencing category ID for trees
    image_url: Optional[str] = None
    is_active: bool = True
    sort_order: int = Field(default=0)
