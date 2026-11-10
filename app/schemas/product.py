from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.product import ProductStatus, ProductVariant


class ProductVariantCreate(BaseModel):
    id: Optional[str] = None  # Auto-generated if absent
    title: str
    sku: str
    barcode: Optional[str] = None
    price: float = Field(ge=0)
    compare_at_price: Optional[float] = Field(default=None, ge=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    attributes: Dict[str, str] = Field(default_factory=dict)
    image_url: Optional[str] = None


class ProductCreate(BaseModel):
    title: str = Field(min_length=2)
    slug: Optional[str] = None
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
    variants: List[ProductVariantCreate] = Field(default_factory=list)
    is_featured: bool = False
    weight_kg: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    status: Optional[ProductStatus] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    base_price: Optional[float] = Field(default=None, ge=0)
    compare_at_price: Optional[float] = Field(default=None, ge=0)
    cost_price: Optional[float] = Field(default=None, ge=0)
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    low_stock_threshold: Optional[int] = Field(default=None, ge=0)
    category_id: Optional[str] = None
    brand_id: Optional[str] = None
    tags: Optional[List[str]] = None
    images: Optional[List[str]] = None
    variants: Optional[List[ProductVariantCreate]] = None
    is_featured: Optional[bool] = None
    weight_kg: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ProductResponse(BaseModel):
    id: str
    title: str
    slug: str
    description: str
    short_description: Optional[str] = None
    status: ProductStatus
    sku: str
    barcode: Optional[str] = None
    base_price: float
    compare_at_price: Optional[float] = None
    cost_price: Optional[float] = None
    stock_quantity: int
    low_stock_threshold: int
    category_id: Optional[str] = None
    brand_id: Optional[str] = None
    tags: List[str]
    images: List[str]
    variants: List[ProductVariant]
    is_featured: bool
    weight_kg: Optional[float] = None
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BulkProductStatusUpdate(BaseModel):
    product_ids: List[str]
    status: ProductStatus
