from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.base import BaseMongoModel


class ProductStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class ProductVariant(BaseModel):
    id: str = Field(description="Unique variant identifier")
    title: str = Field(description="Variant name, e.g. 'Red / XL'")
    sku: str = Field(description="Variant SKU")
    barcode: Optional[str] = None
    price: float = Field(ge=0, description="Selling price")
    compare_at_price: Optional[float] = Field(default=None, ge=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    attributes: Dict[str, str] = Field(default_factory=dict, description="e.g. {'color': 'Red', 'size': 'XL'}")
    image_url: Optional[str] = None


class Product(BaseMongoModel):
    title: str
    slug: str
    description: str
    short_description: Optional[str] = None
    status: ProductStatus = ProductStatus.DRAFT
    sku: str
    barcode: Optional[str] = None
    base_price: float = Field(ge=0)
    compare_at_price: Optional[float] = Field(default=None, ge=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)
    category_id: Optional[str] = None
    brand_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)
    variants: List[ProductVariant] = Field(default_factory=list)
    is_featured: bool = False
    weight_kg: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
