from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2)
    slug: Optional[str] = None  # If not provided, will be auto-generated
    description: Optional[str] = None
    parent_id: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = None
    sort_order: Optional[int] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool
    sort_order: int
    children: Optional[List["CategoryResponse"]] = None
    created_at: datetime
    updated_at: datetime


class BrandCreate(BaseModel):
    name: str = Field(min_length=2)
    slug: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    is_active: bool = True


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    is_active: bool = None


class BrandResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
