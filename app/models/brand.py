from typing import Optional
from app.models.base import BaseMongoModel


class Brand(BaseMongoModel):
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    is_active: bool = True
